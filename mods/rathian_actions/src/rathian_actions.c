/*
 * rathian_actions.c: GU Rathian's MHXX-only actions, run on MH4U's uEnemy.
 *
 * GU Rathian (MHXX v1.4, roEm001) has 13 action ids MH4U has no action for:
 * 3/98, 4/27 to 4/32, 8/0, 12/0 to 12/3 and category 17. This plugin carries 3/98, the
 * 12/1 to 12/3 chain around it and category 17. 12/0 needs nothing: MH4U's own category-12
 * case checks index 0 and runs its own handler 0x006d524c, the handler its shared 3/2, 3/83
 * etc. use and the role pair of MHXX's 12/0. The other slices are 4/27-32 and 8/0 (separate
 * issues).
 *
 * Category 17 is a gate plus a base-class update, not a per-index handler. MHXX's case
 * (0x020098b8) jumps to 0x008d5bd4, which reads the index byte at this+0x6bf1: 0 to 2
 * return, any other index tail-calls uEnemy's vtable slot 0x3d0 (0x008ae50c). MH4U's uEnemy
 * has 95 slots and no 244, but its slot 89 (0x00911b48) is the same routine on MH4U's
 * layout: the port calls it, and for 0 to 2 does nothing.
 *
 * The dispatcher (vtable slot 44, 0x006e9cac) reads the action pair from the monster's
 * work block; for the ported monster and one of this slice's pairs the plugin runs the
 * translated handler instead and returns without the rest of the chain. The handler keeps
 * its own state per monster, calls MH4U's engine functions by address through the host's
 * ABI 3 call, and uses MH4U's work-block offsets. Shared action ids are never touched.
 *
 * Floats: `call` sets r0-r2 only, while MH4U's engine functions take their motion speed
 * and positions in VFP registers (s0, s1). So the plugin builds tiny ARM stubs in a block
 * from the game's heap (alloc, ABI 2) that load s0/s1 from the values the source handler
 * passed and branch to the engine function; a stub that has to hand a float back moves it
 * to r0 (`vmov r0, s0`) after the call. The port runs code that isn't recompiled in its
 * interpreter (port/src/arm_recomp.cpp, Interpret), so a block from alloc is executable;
 * P3's headless run proves the call, and T1's proves the stub (docs/checks.md).
 *
 * Settings (mod.json "config", the player's config.ini over it):
 *   monster   the id to translate the actions for; default 124 (the registry's GU Rathian),
 *             "any" for every monster, or an MH4U id such as 1 for MH4U's own Rathian
 *   selftest  "1": log what this build translates and what is still pending
 *
 * Build: cc -shared -fPIC -I<fork>/include src/rathian_actions.c -o rathian_actions.so
 * Licence: GPL-3.0-or-later.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mh4u_plugin.h"

#define HOOK_DISPATCH "uEnemy::dispatchAction"

/* uEnemy's work block and the fields this slice reads (USA v1.3.0). MHXX's work block is
 * at this+0x10a8 and its +0x44/+0x1d0 are MH4U's +0x19c/+0x218. */
#define ENEMY_WORK    0x0e28u
#define WORK_ID       0x01c0u
#define WORK_CATEGORY 0x01cau
#define WORK_INDEX    0x01cbu
#define WORK_Y        0x019cu
#define WORK_TARGET   0x0218u

/* MH4U engine functions this slice calls, and the MHXX function each stands for. */
#define FN_DATA_FLOAT  0x0093d870u  /* 0x008d21ac: the data value at the monster's entry */
#define FN_APPLY_FALL  0x0092e99cu  /* 0x008b1698: advance the fall by s0 */
#define FN_FALL_SNAP   0x0094a45cu  /* 0x008e192c: snap the fall to a target height */
#define FN_APPLY_RATE  0x0093ce60u  /* 0x008d1a0c: advance the fall by the frame's rate */
#define FN_SET_SPEED   0x00941d84u  /* 0x008d73e8: set a speed (s0) and its flag */
#define FN_FLAG        0x00b05da4u  /* 0x00aed11c: the action's finish flag */
#define FN_IDLE        0x0094dc84u  /* 0x008eb050: return to idle, 0/3 mode 2 */
#define FN_MOTION      0x0094e318u  /* 0x008eb108: start a motion (index r1, s0/s1) */
#define FN_HANDLER_3_9 0x006d5e98u  /* 0x02010aec, MH4U's shared 3/9 handler (also 3/5) */
#define FN_HANDLER_3_12 0x006d791cu /* 0x0201041c, MH4U's shared 3/12 handler */
/* MH4U's uEnemy vtable slot 89, the same routine as MHXX's slot 0x3d0 (0x008ae50c):
 * 0x008b1700->0x009167b4, 0x00add004->0x0092e960, 0x008ac5a0 (the action setter)
 * ->0x0090ef74, and the finish flag this+0x6b00->work+0x1dc (the plugin README). */
#define FN_BASE_UPDATE 0x00911b48u

/* The motions 3/98 starts. 0x101 runs with s0 = 6.0, s1 = 0.0; 0x104 with s0 = 2.0 (the
 * source leaves s1 from the previous state, which is 0.0 while the move is current). */
#define MOTION_A 0x101u
#define MOTION_B 0x104u

static const MH4UPluginHost *host;
static int any_monster, monster_id = 124;

/* ── guest stubs: set s0/s1, call, and hand a float back ─────────────────────────────
 * One 256-byte block from the game's heap holds the stubs. A stub's literals are
 * rewritten for each call; the port runs them in its interpreter, which reads the bytes
 * each time, so no code cache is in the way. */
#define STUB_BLOCK_SIZE 256u
#define STUB_S0        0u
#define STUB_S01       32u
#define STUB_RET_S0    64u
#define STUB_CALL_RET  72u
#define STUB_READ      128u

static uint32_t stub_block;
static int stub_failed, stub_logged;

static int ensure_stubs(MH4UCall *call) {
    if (stub_block || stub_failed) {
        return stub_block != 0;
    }
    stub_block = host->alloc(call, STUB_BLOCK_SIZE, 16);
    if (!stub_block) {
        stub_failed = 1;
        if (!stub_logged) {
            stub_logged = 1;
            host->log(host, MH4U_LOG_WARNING,
                      "no guest memory for the float stubs: the MH4U engine calls stay unmade");
        }
        return 0;
    }
    return 1;
}

static uint32_t run_stub(MH4UCall *call, uint32_t at, uint32_t a0, uint32_t a1, uint32_t a2) {
    return host->call(call, at, a0, a1, a2);
}

/* vldr s0,[pc,#4]; ldr pc,[pc,#4]; pad; <s0>; <function> */
static uint32_t call_s0(MH4UCall *call, uint32_t fn, uint32_t a0, uint32_t a1, uint32_t a2,
                        uint32_t s0) {
    if (!ensure_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_S0;
    host->write32(call, at + 0, 0xED9F0A01u);
    host->write32(call, at + 4, 0xE59FF004u);
    host->write32(call, at + 8, 0xE1A01001u);
    host->write32(call, at + 12, s0);
    host->write32(call, at + 16, fn);
    return run_stub(call, at, a0, a1, a2);
}

/* vldr s0,[pc,#8]; vldr s1,[pc,#8]; ldr pc,[pc,#8]; pad; <s0>; <s1>; <function> */
static uint32_t call_s01(MH4UCall *call, uint32_t fn, uint32_t a0, uint32_t a1, uint32_t a2,
                         uint32_t s0, uint32_t s1) {
    if (!ensure_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_S01;
    host->write32(call, at + 0, 0xED9F0A02u);
    host->write32(call, at + 4, 0xED9F1A02u);
    host->write32(call, at + 8, 0xE59FF008u);
    host->write32(call, at + 12, 0xE1A01001u);
    host->write32(call, at + 16, s0);
    host->write32(call, at + 20, s1);
    host->write32(call, at + 24, fn);
    return run_stub(call, at, a0, a1, a2);
}

/* Call a function that hands a float back in s0: set s0, call it, continue at a stub that
 * moves s0 to r0 and returns to the hook. */
static uint32_t call_s0_ret0(MH4UCall *call, uint32_t fn, uint32_t a0, uint32_t a1, uint32_t a2,
                             uint32_t s0) {
    if (!ensure_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_CALL_RET;
    const uint32_t back = host->reg(call, 14);
    host->write32(call, at + 0, 0xED9F0A03u);   /* vldr s0,[pc,#12]  -> +20 */
    host->write32(call, at + 4, 0xE59F4010u);   /* ldr r4,[pc,#16]   -> +28 (return address) */
    host->write32(call, at + 8, 0xE59FE014u);   /* ldr lr,[pc,#20]   -> +36 (continuation) */
    host->write32(call, at + 12, 0xE59FF00Cu);  /* ldr pc,[pc,#12]   -> +32 (function) */
    host->write32(call, at + 16, 0xE1A01001u);  /* pad */
    host->write32(call, at + 20, s0);
    host->write32(call, at + 24, 0xE1A01001u);  /* pad */
    host->write32(call, at + 28, back);
    host->write32(call, at + 32, fn);
    host->write32(call, at + 36, 0xE1A0E004u);  /* mov lr, r4 */
    host->write32(call, at + 40, 0xEE100A10u);  /* vmov r0, s0 */
    host->write32(call, at + 44, 0xE12FFF1Eu);  /* bx lr */
    return run_stub(call, at, a0, a1, a2);
}

/* vmov r0, sN; bx lr: one float the dispatcher's caller passed in s0-s3. */
static uint32_t read_s(MH4UCall *call, int n) {
    if (n < 0 || n > 3 || !ensure_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_READ + 8u * (uint32_t)n;
    host->write32(call, at + 0, 0xEE100A10u | ((uint32_t)n << 16));
    host->write32(call, at + 4, 0xE12FFF1Eu);
    return run_stub(call, at, 0, 0, 0);
}

static uint32_t bits_of(float f) {
    uint32_t u;
    memcpy(&u, &f, sizeof u);
    return u;
}

static int f32_gt(uint32_t a, uint32_t b) {
    float x, y;
    memcpy(&x, &a, sizeof x);
    memcpy(&y, &b, sizeof y);
    return x > y;
}

/* ── the translated handlers ────────────────────────────────────────────────────────── */

/* The monster's action state, one entry per live monster. The source keeps it in the work
 * block's byte +0x1a1; the plugin keeps its own, reset when the action pair changes. */
#define MAX_MONSTERS 8
typedef struct {
    uint32_t enemy;
    uint8_t category, index, state, used;
} MonsterState;
static MonsterState states[MAX_MONSTERS];
static int action_logged, request_logged[4];

static MonsterState *state_for(uint32_t enemy, int category, int index) {
    MonsterState *free_slot = NULL;
    for (int i = 0; i < MAX_MONSTERS; i++) {
        MonsterState *s = &states[i];
        if (!s->used) {
            if (!free_slot) {
                free_slot = s;
            }
            continue;
        }
        if (s->enemy != enemy) {
            continue;
        }
        if (s->category != category || s->index != index) {
            s->category = (uint8_t)category;
            s->index = (uint8_t)index;
            s->state = 0;
            action_logged = 0;
        }
        return s;
    }
    MonsterState *s = free_slot ? free_slot : &states[0];
    s->enemy = enemy;
    s->category = (uint8_t)category;
    s->index = (uint8_t)index;
    s->state = 0;
    s->used = 1;
    action_logged = 0;
    return s;
}

static void log_action_once(int category, int index) {
    if (action_logged) {
        return;
    }
    action_logged = 1;
    char line[128];
    snprintf(line, sizeof line, "running the translated action %d/%d", category, index);
    host->log(host, MH4U_LOG_INFO, line);
}

/* Category 17: one line per index, whether the gate's 0-2 no-op or the base update. The
 * plugin has no per-monster state to keep here, and the first line is the evidence that the
 * forced index reached the translation. */
static uint8_t cat17_logged[256];
static void log_cat17_once(int index) {
    if (cat17_logged[index]) {
        return;
    }
    cat17_logged[index] = 1;
    char line[160];
    if (index <= 2) {
        snprintf(line, sizeof line, "17/%d: nothing (the gate returns for 0 to 2)", index);
    } else {
        snprintf(line, sizeof line, "17/%d: running MH4U's base action update 0x%08x", index,
                 (unsigned)FN_BASE_UPDATE);
    }
    host->log(host, MH4U_LOG_INFO, line);
}

/* MHXX 3/98, handler 0x020062d4: three states.
 *   0: remember the data float, advance the fall by it, start motion 0x101 at 6.0, snap
 *      the fall to the target height;
 *   1: advance the fall by the frame's rate, stop when the position reaches the target
 *      height, set the speed 2.0, start motion 0x104;
 *   2: wait for the finish flag, then return to idle. */
static void run_3_98(MH4UCall *call, uint32_t enemy, uint32_t work, MonsterState *st) {
    switch (st->state) {
    case 0: {
        st->state = 1;
        const uint32_t data = call_s0_ret0(call, FN_DATA_FLOAT, enemy, 0, 0, 0);
        call_s0(call, FN_APPLY_FALL, enemy, 0, 0, data);
        call_s01(call, FN_MOTION, enemy, MOTION_A, 0, bits_of(6.0f), bits_of(0.0f));
        const uint32_t target_y = host->read32(call, work + WORK_TARGET + 4u);
        call_s0(call, FN_FALL_SNAP, enemy, 0, 0, target_y);
        break;
    }
    case 1: {
        host->call(call, FN_APPLY_RATE, enemy, 0, 0);
        const uint32_t y = host->read32(call, work + WORK_Y);
        const uint32_t target_y = host->read32(call, work + WORK_TARGET + 4u);
        if (f32_gt(y, target_y)) {
            return;
        }
        host->write32(call, work + WORK_Y, target_y);
        if (!call_s0(call, FN_SET_SPEED, enemy, 0, 0, bits_of(2.0f))) {
            return;
        }
        st->state = 2;
        call_s01(call, FN_MOTION, enemy, MOTION_B, 0, bits_of(2.0f), bits_of(0.0f));
        break;
    }
    default: {
        if (!host->call(call, FN_FLAG, enemy, 0, 0)) {
            return;
        }
        host->call(call, FN_IDLE, enemy, 0, 0);
        break;
    }
    }
}

/* MHXX 12/1, block 0x0201c1d0: fixed target points (the fourth is the caller's s1), then
 * the 3/98 handler; when the action has returned to idle it requests 12/2. The request
 * helper (0x008ebab0) is not translated: MH4U has neither its work-block bytes nor its
 * pending-action queue, so the chain stops after this move instead of following on. */
static void run_12_1(MH4UCall *call, uint32_t enemy, uint32_t work, MonsterState *st) {
    host->write32(call, work + WORK_TARGET + 0x0u, bits_of(5477.0f));
    host->write32(call, work + WORK_TARGET + 0x4u, bits_of(3000.0f));
    host->write32(call, work + WORK_TARGET + 0x8u, bits_of(4892.0f));
    host->write32(call, work + WORK_TARGET + 0xcu, read_s(call, 1));
    run_3_98(call, enemy, work, st);
    if (host->read8(call, work + WORK_CATEGORY) == 0 && !request_logged[1]) {
        request_logged[1] = 1;
        host->log(host, MH4U_LOG_INFO,
                  "12/1: the source now requests 12/2 through 0x008ebab0; that helper is not "
                  "translated, so the move returns to idle instead");
    }
}

/* MHXX 12/2, block 0x0201c228: target points from the caller's s0-s3, MH4U's shared 3/12
 * handler (MHXX 0x0201041c), then a request for 12/3 after category 3 index 11. The request
 * is not translated, as for 12/1. */
static void run_12_2(MH4UCall *call, uint32_t enemy, uint32_t work, MonsterState *st) {
    (void)st;
    host->write32(call, work + WORK_TARGET + 0x0u, read_s(call, 0));
    host->write32(call, work + WORK_TARGET + 0xcu, read_s(call, 1));
    host->write32(call, work + WORK_TARGET + 0x4u, read_s(call, 2));
    host->write32(call, work + WORK_TARGET + 0x8u, read_s(call, 3));
    host->call(call, FN_HANDLER_3_12, enemy, 0, 0);
    if (host->read8(call, work + WORK_CATEGORY) == 3 &&
        host->read8(call, work + WORK_INDEX) == 0x0b && !request_logged[2]) {
        request_logged[2] = 1;
        host->log(host, MH4U_LOG_INFO,
                  "12/2: the source now requests 12/3 through 0x008ebab0; that helper is not "
                  "translated, so the move returns to idle instead");
    }
}

/* MHXX 12/3, block 0x0201c27c: target points from the caller's s0-s3, then MHXX's 3/5/3/9
 * unit (0x02010aec). MH4U's own 3/9 handler is the pair, with the same r1=1, r2=0. */
static void run_12_3(MH4UCall *call, uint32_t enemy, uint32_t work) {
    host->write32(call, work + WORK_TARGET + 0x0u, read_s(call, 0));
    host->write32(call, work + WORK_TARGET + 0xcu, read_s(call, 1));
    host->write32(call, work + WORK_TARGET + 0x4u, read_s(call, 2));
    host->write32(call, work + WORK_TARGET + 0x8u, read_s(call, 3));
    host->call(call, FN_HANDLER_3_9, enemy, 1, 0);
}

/* ── the dispatcher hook ───────────────────────────────────────────────────────────── */
static void dispatch_action(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t enemy = host->reg(call, 0);
    const uint32_t work = host->read32(call, enemy + ENEMY_WORK);
    if (!work) {
        host->call_original(call);
        return;
    }
    const int id = (int)host->read8(call, work + WORK_ID);
    if (!any_monster && id != monster_id) {
        host->call_original(call);
        return;
    }
    const int category = (int)host->read8(call, work + WORK_CATEGORY);
    const int index = (int)host->read8(call, work + WORK_INDEX);
    /* Category 17 is the gate first: MHXX's dispatcher case (0x020098b8) jumps to
     * 0x008d5bd4, which reads the index (this+0x6bf1 there, MH4U's work+0x1cb here), returns
     * for 0 to 2 and otherwise tail-calls uEnemy's slot 0x3d0 (0x008ae50c). MH4U has no such
     * slot; its slot 89 (0x00911b48) is the same routine and runs the ported action. */
    if (category == 17) {
        if (index > 2) {
            host->call(call, FN_BASE_UPDATE, enemy, 0, 0);
        }
        log_cat17_once(index);
        host->skip_original(call);
        return;
    }
    const int which = (category == 3 && index == 98) ? 98
                    : (category == 12 && index >= 1 && index <= 3) ? index
                    : -1;
    if (which < 0 || !ensure_stubs(call)) {
        host->call_original(call);
        return;
    }
    MonsterState *st = state_for(enemy, category, index);
    log_action_once(category, index);
    switch (which) {
    case 98: run_3_98(call, enemy, work, st); break;
    case 1: run_12_1(call, enemy, work, st); break;
    case 2: run_12_2(call, enemy, work, st); break;
    default: run_12_3(call, enemy, work); break;
    }
    host->skip_original(call);
}

/* ── self-test (the headless check) ────────────────────────────────────────────────── */
static void self_test(MH4UCall *call) {
    char line[512];
    snprintf(line, sizeof line,
             "selftest: 5 of the 13 actions: 3/98 <- 0x020062d4 (3 states, motions 0x101 and "
             "0x104), 12/1 <- 0x0201c1d0 + 0x020062d4, 12/2 <- 0x0201c228 + 0x0201041c->0x%08x, "
             "12/3 <- 0x0201c27c + 0x02010aec->0x%08x, 17 <- the gate 0x008d5bd4 + MH4U's base "
             "update 0x%08x (slot 89, MHXX's slot 244)",
             (unsigned)FN_HANDLER_3_12, (unsigned)FN_HANDLER_3_9, (unsigned)FN_BASE_UPDATE);
    host->log(host, MH4U_LOG_INFO, line);
    snprintf(line, sizeof line,
             "selftest: category 17 does nothing for indexes 0 to 2; 12/0 is MH4U's own "
             "category-12 handler 0x006d524c; pending: 4/27-32 (0x0200e3b4), 8/0 (0x0201b460)");
    host->log(host, MH4U_LOG_INFO, line);
    if (stub_block) {
        snprintf(line, sizeof line, "selftest: float stubs at 0x%08x (%u bytes, the game's heap)",
                 (unsigned)stub_block, (unsigned)STUB_BLOCK_SIZE);
        host->log(host, MH4U_LOG_INFO, line);
    } else {
        host->log(host, MH4U_LOG_WARNING, "selftest: no float stubs (no guest memory)");
    }
    (void)call;
}

static int selftest;

static void frame(MH4UCall *call, void *user) {
    (void)user;
    if (ensure_stubs(call) && selftest) {
        selftest = 0;
        self_test(call);
    }
}

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 3 || plugin_host->size < offsetof(MH4UPluginHost, call) + sizeof(plugin_host->call)) {
        return 0;   /* the translated handlers need call (ABI 3) */
    }
    host = plugin_host;
    const char *monster = host->config(host, "monster");
    if (monster && *monster) {
        if (strcmp(monster, "any") == 0) {
            any_monster = 1;
        } else {
            char *end;
            const long id = strtol(monster, &end, 0);
            if (*end != '\0' || id < 0 || id > 255) {
                host->log(host, MH4U_LOG_ERROR,
                          "bad monster: write an id from 0 to 255, or any");
                return 0;
            }
            monster_id = (int)id;
            any_monster = 0;
        }
    }
    const char *test = host->config(host, "selftest");
    selftest = test && strcmp(test, "0") != 0;
    if (!host->hook(host, HOOK_DISPATCH, dispatch_action, NULL)) {
        host->log(host, MH4U_LOG_ERROR,
                  "the action dispatcher isn't a hook point: the code library needs building "
                  "with this mod");
        return 0;
    }
    if (!host->on_frame(host, frame, NULL)) {
        host->log(host, MH4U_LOG_WARNING, "no frame calls: the self-test waits for a hooked action");
    }
    char line[200];
    if (any_monster) {
        snprintf(line, sizeof line,
                 "ready: translating 5 of GU Rathian's 13 MHXX-only actions on every monster");
    } else {
        snprintf(line, sizeof line,
                 "ready: translating 5 of GU Rathian's 13 MHXX-only actions on monster %d",
                 monster_id);
    }
    host->log(host, MH4U_LOG_INFO, line);
    return 1;
}
