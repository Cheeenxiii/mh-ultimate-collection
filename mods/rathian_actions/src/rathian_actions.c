/*
 * rathian_actions.c: GU Rathian's MHXX-only actions, run on MH4U's uEnemy.
 *
 * GU Rathian (MHXX v1.4, roEm001) has 13 action ids MH4U has no action for:
 * 3/98, 4/27 to 4/32, 8/0, 12/0 to 12/3 and category 17. This plugin carries all twelve
 * that need new C: 3/98 with the 12/1 to 12/3 chain around it, the six 4/27 to 4/32 ids that
 * share handler 0x0200e3b4, 8/0 with its combo tail, and category 17. 12/0 needs nothing:
 * MH4U's own category-12 case checks index 0 and runs its own handler 0x006d524c, the
 * handler its shared 3/2, 3/83 etc. use and the role pair of MHXX's 12/0.
 *
 * Category 17 is a gate plus a base-class update, not a per-index handler. MHXX's case
 * (0x020098b8) jumps to 0x008d5bd4, which reads the index byte at this+0x6bf1: 0 to 2
 * return, any other index tail-calls uEnemy's vtable slot 0x3d0 (0x008ae50c). MH4U's uEnemy
 * has 95 slots and no 244, but its slot 89 (0x00911b48) is the same routine on MH4U's
 * layout: the port calls it, and for 0 to 2 does nothing.
 *
 * 8/0 translates almost call for call onto MH4U's own 8/0 handler (0x006e9770), which is
 * the same action with the same frame values: MH4U's category-8 case runs it. The engine
 * calls below are the same functions the MH4U handler calls at the same points, and the
 * work-block fields are MH4U's (the MH4U handler's offsets), so the two bodies can be
 * read side by side. The exceptions are recorded in mods/rathian_actions/README.md.
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
#include <math.h>
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
 * ->0x0090ef74, and the finish flag this+0x6b00->work+0x1dc (the plugin README). It is
 * category 17's base update and the 4/27-32 finish flag's end-of-action. */
#define FN_BASE_UPDATE 0x00911b48u

/* 8/0's engine calls, each the MH4U function MH4U's own 8/0 handler (0x006e9770) calls
 * at the same point (the source address in the comment). Its data entry and per-mode check
 * are the 4/27-32 slice's FN_MODE and FN_MODE_CLEAR below. */
#define FN_MOVE_TO      0x00948674u  /* 0x008df28c: zero a velocity, aim at a point (s0, s1) */
#define FN_APPLY_MOVE   0x00955440u  /* 0x008f1f30: advance the position by the velocity */
#define FN_COUNTDOWN    0x00b0704cu  /* 0x008a78ec: count a float down by the frame rate */
#define FN_HIT_CHECK    0x009122fcu  /* 0x008ae8ec: hit check, three floats (s0-s2) */
#define FN_HIT_CHECK_R3 0x0092b2b0u /* 0x008c024c: hit check, mode in r3 */
#define FN_REQUEST_NEXT 0x0094ef64u /* 0x008ebab0: request the next action (category, index) */
#define FN_TAIL_DATA    0x0092f6e8u  /* 0x008c4184: the leaf, with its data table in r1 */

/* The motions 3/98 starts. 0x101 runs with s0 = 6.0, s1 = 0.0; 0x104 with s0 = 2.0 (the
 * source leaves s1 from the previous state, which is 0.0 while the move is current). */
#define MOTION_A 0x101u
#define MOTION_B 0x104u

/* ── the 4/27 to 4/32 slice: handler 0x0200e3b4, three states ────────────────────────
 * The six ids' case blocks (0x02018af8 to 0x02018bac) pass r1/r2 to the shared handler:
 * 4/27 2/0, 4/28 1/0, 4/29 2/1, 4/30 1/1, 4/31 2/0, 4/32 1/0. r1 picks the pair of sides
 * (mode 1 or 2) and r2 picks the ending: 0 waits for the finish flag and calls MHXX's
 * end-of-action (vtable slot 244), 1 starts the last motion and requests action 7/246 or
 * 7/247. Each case block also calls 0x00adb528 with 2, 2, 3, 3, 5, 5 (method 0x4c of the
 * object at this+0x6dc4); MH4U has no counterpart for it, so that call is not translated. */

/* MH4U's work block is *(this+0xe28), MHXX's is *(this+0x10a8). The fields this slice
 * reads, MHXX -> MH4U, each confirmed by a paired function (see the README's table):
 *   position x,y,z     +0x40/+0x44/+0x48 -> +0x198/+0x19c/+0x1a0
 *   position w         +0x4c             -> +0x1a4
 *   heading            +0x54             -> +0x1ac
 *   target point x,z   +0x1d0/+0x1d8     -> +0x218/+0x220
 *   heading saved      +0x200            -> +0x248
 *   speed (this)       +0x298            -> +0x290
 *   turn scale (this)  +0x1c             -> +0x14
 * The target-line struct *(this+0x8d88) (MHXX *(this+0xb770)) keeps the same layout in
 * both games: origin x,z at +0x30/+0x38, direction x,y,z,w at +0x40 to +0x4c. */
#define ENEMY_TARGET_LINE 0x08d88u
#define ENEMY_SPEED       0x0290u
#define ENEMY_TURN_SCALE  0x0014u
#define WORK_POS          0x0198u
#define WORK_POS_W        0x01a4u
#define WORK_HEADING      0x01acu
#define WORK_SAVED_HEADING 0x0248u
#define LINE_ORIGIN       0x0030u
#define LINE_DIR          0x0040u

/* 8/0's fields, at the offsets MH4U's own 8/0 handler (0x006e9770) uses for the same
 * fields: its state 2 counts down work+0x1d4, reads the pending-action mode at work+0x1d9,
 * and hands the two bytes at +0x278/+0x27c to the hit checks. */
#define WORK_TIMER       0x01d4u
#define WORK_PENDING     0x01d9u
#define WORK_BYTE_A      0x0278u
#define WORK_BYTE_B      0x027cu
#define WORK_VELOCITY    0x0160u
#define WORK_FLAG_ZERO_A 0x7738u
#define WORK_FLAG_ZERO_B 0x7739u
#define WORK_FLAG_MODE   0x7a3cu
#define WORK_FLAG_TAIL   0x7993u

/* The handler's engine calls, MH4U address <- MHXX address (the MHXX one in brackets). */
#define FN_FLIGHT_SETUP 0x006e7be8u  /* [0x0201262c] the flight's setup, from the height data */
#define FN_MODE         0x009167b4u  /* [0x008b1700] set the monster's mode (0, 1, 2, 3, 5, 6) */
#define FN_TURN         0x00917570u  /* [0x008b2210] turn by an angle step, s0/s1 the speed range */
#define FN_MODE_CLEAR   0x0091aae4u  /* [0x008a7360] the flag-clear wrapper around 0x00b06b4c */
#define FN_TARGET_POINT 0x0092d09cu  /* [0x008c21f8] build a target point from an index */
#define FN_TURN_TO      0x0091db4cu  /* [0x008b75d8] turn toward a target point, at a step in r3 */
#define FN_LINE_POINT   0x006e5608u  /* [0x020063fc] a point on the target line at a fraction */
#define FN_ROTATE       0x00aad55cu  /* [0x0201277c] rotate a direction by an angle */

/* The motions the six start: r1 = 1 (mode 1) or 2 (mode 2) selects the side. */
#define MOTION_TAKEOFF_1 0x417u  /* state 0, s0 = 6.0 */
#define MOTION_TAKEOFF_2 0x418u  /* state 0, s0 = 6.0 */
#define MOTION_FLY_1     0x909u  /* state 1, s0 = 0.0 */
#define MOTION_FLY_2     0x90au  /* state 1, s0 = 0.0 */
#define MOTION_END_1     0x90du  /* state 2, variant 1, s0 = 2.0 */
#define MOTION_END_2     0x90bu  /* state 2, variant 1, s0 = 2.0 */
#define PENDING_ACTION_1 0xf6u  /* the action 4/30 requests next: 7/246 */
#define PENDING_ACTION_2 0xf7u  /* the action 4/29 requests next: 7/247 */

/* 8/0's motion and its frame values (the same constants MH4U's own 8/0 handler passes). */
#define MOTION_8_0 0x403u

/* The turn steps 0x008b75d8 takes in r1: the slow one when the mode-clear call succeeded,
 * the fast one when it did not. */
#define TURN_STEP_SLOW 0x1c7u
#define TURN_STEP_FAST 0x00b6u

static const MH4UPluginHost *host;
static int any_monster, monster_id = 124;

/* ── guest stubs: set s0/s1, call, and hand a float back ─────────────────────────────
 * One 384-byte block from the game's heap holds the stubs. A stub's literals are
 * rewritten for each call; the port runs them in its interpreter, which reads the bytes
 * each time, so no code cache is in the way. */
#define STUB_S0        0u
#define STUB_S01       32u
#define STUB_RET_S0    64u
#define STUB_CALL_RET  72u
#define STUB_READ      128u
#define STUB_BLOCK_SIZE 384u
#define STUB_S012      160u   /* s0/s1/s2, 40 bytes: after the readers */
#define STUB_SCRATCH   208u   /* 16 bytes of guest memory for a point the engine fills */
#define STUB_R3        240u   /* r3, 20 bytes: after the scratch */

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

/* vldr s0,[pc,#16]; vldr s1,[pc,#16]; vldr s2,[pc,#16]; ldr pc,[pc,#16]; pad; pad;
 * <s0>; <s1>; <s2>; <function> */
static uint32_t call_s012(MH4UCall *call, uint32_t fn, uint32_t a0, uint32_t a1, uint32_t a2,
                          uint32_t s0, uint32_t s1, uint32_t s2) {
    if (!ensure_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_S012;
    host->write32(call, at + 0, 0xED9F0A04u);
    host->write32(call, at + 4, 0xED9F1A04u);
    host->write32(call, at + 8, 0xED9F2A04u);
    host->write32(call, at + 12, 0xE59FF010u);
    host->write32(call, at + 16, 0xE1A01001u);
    host->write32(call, at + 20, 0xE1A01001u);
    host->write32(call, at + 24, s0);
    host->write32(call, at + 28, s1);
    host->write32(call, at + 32, s2);
    host->write32(call, at + 36, fn);
    return run_stub(call, at, a0, a1, a2);
}

/* ldr r3,[pc,#4]; ldr pc,[pc,#4]; pad; <r3>; <function> */
static uint32_t call_r3(MH4UCall *call, uint32_t fn, uint32_t a0, uint32_t a1, uint32_t a2,
                        uint32_t r3) {
    if (!ensure_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_R3;
    host->write32(call, at + 0, 0xE59F3004u);
    host->write32(call, at + 4, 0xE59FF004u);
    host->write32(call, at + 8, 0xE1A01001u);
    host->write32(call, at + 12, r3);
    host->write32(call, at + 16, fn);
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

static float f32_of(uint32_t u) {
    float f;
    memcpy(&f, &u, sizeof f);
    return f;
}

static uint32_t read_f32(MH4UCall *call, uint32_t addr) {
    return host->read32(call, addr);
}

static void write_f32(MH4UCall *call, uint32_t addr, float f) {
    host->write32(call, addr, bits_of(f));
}

/* The source's `vcvt.u32.f32` saturates: a negative is 0, anything past 2^32 is all ones. */
static uint32_t f32_to_u8(float f) {
    if (!(f > 0.0f)) {
        return 0;
    }
    if (f >= 4294967296.0f) {
        return 0xffu;
    }
    return (uint32_t)f & 0xffu;
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

/* MHXX 4/27-32, handler 0x0200e3b4: three states, one state per frame.
 *   mode is the case block's r1 (1 or 2), variant its r2 (0 or 1), and s20 the handler's
 *   incoming s0.
 *   state 0: the flight setup, mode 3, the target line built from the position and the target
 *            point and rotated 90 degrees, motion 0x417/0x418 at 6.0, and the heading saved;
 *   state 1: build target point 0, speed/88, the mode-clear call at 78.0 and a turn toward
 *            the target at the slow or fast step, a point on the line at (s20 * 0.01) percent,
 *            one step of 10 * (this+0x14) toward it, the mode-clear call at 2.0, then the
 *            flight motion 0x909/0x90a at 0.0;
 *   state 2: a turn by +-0x2000 at 2.0..10.0; variant 0 waits for the finish flag and then
 *            calls MH4U's end-of-action, variant 1 makes the mode-clear call at 30.0, starts
 *            motion 0x90b/0x90d at 2.0 and requests action 7/247 or 7/246.
 *
 * The source's case blocks call 0x00adb528 (the object at this+0x6dc4, method 0x4c) before
 * the handler, and its state-2 request goes through 0x008ebab0. MH4U has neither object nor
 * queue, so both are left out and logged once per action. */
static int precall_logged, pending_logged;

static void log_precall_once(int index) {
    const unsigned bit = 1u << (unsigned)(index - 27);
    if (precall_logged & (int)bit) {
        return;
    }
    precall_logged |= (int)bit;
    char line[160];
    snprintf(line, sizeof line,
             "4/%d: the source's case block calls 0x00adb528 (an object MH4U lacks) before the "
             "handler; it is not translated", index);
    host->log(host, MH4U_LOG_INFO, line);
}

static void log_pending_once(int index) {
    if (pending_logged) {
        return;
    }
    pending_logged = 1;
    char line[160];
    snprintf(line, sizeof line,
             "4/%d: the source now requests action 7/%d through 0x008ebab0; that helper is not "
             "translated", index, index == 30 ? (int)PENDING_ACTION_1 : (int)PENDING_ACTION_2);
    host->log(host, MH4U_LOG_INFO, line);
}

static void run_4_27(MH4UCall *call, uint32_t enemy, uint32_t work, MonsterState *st,
                     int index, int mode, int variant, uint32_t s0arg) {
    switch (st->state) {
    case 0: {
        st->state = 1;
        host->call(call, FN_FLIGHT_SETUP, enemy, 0, 0);
        host->call(call, FN_MODE, enemy, 3, 0);
        const uint32_t line = host->read32(call, enemy + ENEMY_TARGET_LINE);
        if (line) {
            const float px = f32_of(read_f32(call, work + WORK_POS));
            const float pz = f32_of(read_f32(call, work + WORK_POS + 8u));
            const float tx = f32_of(read_f32(call, work + WORK_TARGET));
            const float tz = f32_of(read_f32(call, work + WORK_TARGET + 8u));
            host->write32(call, line + LINE_ORIGIN, bits_of(px));
            host->write32(call, line + LINE_ORIGIN + 8u, bits_of(pz));
            float vx = tx - px;
            float vy = f32_of(read_f32(call, line + LINE_DIR + 4u));
            float vz = tz - pz;
            const float len = sqrtf(vx * vx + vy * vy + vz * vz);
            if (len >= 1.1920929e-07f) {
                vx /= len;
                vy /= len;
                vz /= len;
            }
            host->write32(call, line + LINE_DIR, bits_of(vx));
            host->write32(call, line + LINE_DIR + 4u, bits_of(vy));
            host->write32(call, line + LINE_DIR + 8u, bits_of(vz));
            host->write32(call, line + LINE_DIR + 0xcu, 0);
            host->call(call, FN_ROTATE, line + LINE_DIR, mode == 1 ? 0x4000u : 0xc001u, 0);
        }
        call_s01(call, FN_MOTION, enemy, mode == 1 ? MOTION_TAKEOFF_1 : MOTION_TAKEOFF_2, 0,
                 bits_of(6.0f), bits_of(0.0f));
        host->write32(call, work + WORK_SAVED_HEADING, host->read32(call, work + WORK_HEADING));
        break;
    }
    case 1: {
        const uint32_t offset = mode == 1 ? 0x2000u : 0xe001u;
        host->call(call, FN_FLIGHT_SETUP, enemy, 0, 0);
        host->call(call, FN_TARGET_POINT, enemy, 0, 0);
        const float speed = f32_of(read_f32(call, enemy + ENEMY_SPEED));
        const uint32_t fraction = f32_to_u8(f32_of(s0arg) * 0.01f);
        if (call_s01(call, FN_MODE_CLEAR, enemy, 2, 0, bits_of(78.0f), 0)) {
            host->call(call, FN_TURN_TO, enemy, TURN_STEP_SLOW, offset);
        } else {
            host->call(call, FN_TURN_TO, enemy, TURN_STEP_FAST, offset);
        }
        const uint32_t scratch = stub_block + STUB_SCRATCH;
        call_s0(call, FN_LINE_POINT, enemy, scratch, fraction, bits_of(speed / 88.0f));
        const float ox = f32_of(read_f32(call, scratch));
        const float oy = f32_of(read_f32(call, scratch + 4u));
        const float oz = f32_of(read_f32(call, scratch + 8u));
        const float px = f32_of(read_f32(call, work + WORK_POS));
        const float py = f32_of(read_f32(call, work + WORK_POS + 4u));
        const float pz = f32_of(read_f32(call, work + WORK_POS + 8u));
        const float dx = ox - px;
        const float dz = oz - pz;
        const float dist = sqrtf(dx * dx + dz * dz);
        const float scale = f32_of(read_f32(call, enemy + ENEMY_TURN_SCALE));
        float nx = ox, ny = oy, nz = oz;
        if (!(scale * 75.0f >= dist)) {
            float mx = ox - px, my = oy - py, mz = oz - pz;
            const float len = sqrtf(mx * mx + my * my + mz * mz);
            if (len >= 1.1920929e-07f) {
                mx /= len;
                my /= len;
                mz /= len;
            }
            nx = px + mx * 10.0f * scale;
            ny = py + my * 10.0f * scale;
            nz = pz + mz * 10.0f * scale;
        }
        write_f32(call, work + WORK_POS, nx);
        write_f32(call, work + WORK_POS + 4u, ny);
        write_f32(call, work + WORK_POS + 8u, nz);
        host->write32(call, work + WORK_POS_W, 0);
        if (!call_s01(call, FN_MODE_CLEAR, enemy, 1, 0, bits_of(2.0f), 0)) {
            return;
        }
        st->state = 2;
        host->call(call, FN_MODE, enemy, 0, 0);
        call_s01(call, FN_MOTION, enemy, mode == 1 ? MOTION_FLY_1 : MOTION_FLY_2, 0,
                 bits_of(0.0f), bits_of(0.0f));
        break;
    }
    default: {
        if (mode == 1) {
            call_s01(call, FN_TURN, enemy, 0xffffe000u, 0, bits_of(2.0f), bits_of(10.0f));
        } else {
            call_s01(call, FN_TURN, enemy, 0x2000u, 0, bits_of(2.0f), bits_of(10.0f));
        }
        if (!variant) {
            if (host->call(call, FN_FLAG, enemy, 0, 0)) {
                host->call(call, FN_BASE_UPDATE, enemy, 0, 0);
            }
            break;
        }
        if (!call_s01(call, FN_MODE_CLEAR, enemy, 1, 0, bits_of(30.0f), 0)) {
            return;
        }
        st->state = 3;
        call_s01(call, FN_MOTION, enemy, mode == 1 ? MOTION_END_1 : MOTION_END_2, 0,
                 bits_of(2.0f), bits_of(0.0f));
        log_pending_once(index);
        break;
    }
    }
}


/* MHXX 8/0, handler 0x0201b460: the same action as MH4U's own 8/0 handler 0x006e9770,
 * with the same frame values. Three states.
 *   0: set up; copy the monster's data entry (mode 0), aim at the target at 300.0/38.0;
 *   1: per-mode speed/distance at 12.0/50.0; when it holds, advance the position by the
 *      velocity; wait for the finish flag, start motion 0x403 at 4.0 and arm the 180.0
 *      timer;
 *   2: count the timer down by the frame rate; when the pending-action mode is 1, run the
 *      two hit checks (300.0/0.0/150.0) and request 9/1, or request 2/6 when they fail,
 *      the timer is over, or the fallback check is 0.
 * The calls and work offsets are the ones MH4U's own handler uses (0x006e9770), which is
 * why each has an MH4U counterpart; the four gaps are in the plugin README. */
static int gap_logged;

static void run_8_0(MH4UCall *call, uint32_t enemy, uint32_t work, MonsterState *st) {
    if (!gap_logged) {
        gap_logged = 1;
        host->log(host, MH4U_LOG_INFO,
                  "8/0: 0x008c4184 is MH4U's 0x0092f6e8, but its MHXX table 0x20220ac is "
                  "not carried yet; 0x008d0528 and the 0x8ae5e4 data setup wait on #134");
    }
    /* The stores MHXX's handler makes every frame; MH4U's own 8/0 handler clears the same
     * fields at MH4U's offsets before its state switch. */
    host->write8(call, work + WORK_FLAG_ZERO_A, 0);
    host->write8(call, work + WORK_FLAG_ZERO_B, 0);
    host->write8(call, work + WORK_FLAG_MODE, 2);
    switch (st->state) {
    case 0: {
        st->state = 1;
        host->call(call, FN_MODE, enemy, 0, 0);
        /* 0x008ae5e4 (MH4U 0x00911c0c) takes its 4th and 5th arguments in r3 and on the
         * stack, which the ABI 3 call cannot set: it waits on #134. */
        call_s01(call, FN_MOVE_TO, enemy, work + WORK_VELOCITY, work + WORK_TARGET,
                 bits_of(300.0f), bits_of(38.0f));
        break;
    }
    case 1: {
        if (call_s01(call, FN_MODE_CLEAR, enemy, 3, 0, bits_of(12.0f), bits_of(50.0f))) {
            host->call(call, FN_APPLY_MOVE, enemy, 0, 0);
            /* 0x008c4184's counterpart is MH4U's 0x0092f6e8, but its table (MHXX's
             * 0x20220ac, MH4U's 0x00e094d8) is the port's data, not carried yet. */
        }
        if (!host->call(call, FN_FLAG, enemy, 0, 0)) {
            return;
        }
        st->state = 2;
        host->write32(call, work + WORK_TIMER, bits_of(180.0f));
        call_s01(call, FN_MOTION, enemy, MOTION_8_0, 0, bits_of(4.0f), bits_of(0.0f));
        break;
    }
    default: {
        host->call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0);
        if (host->read8(call, work + WORK_PENDING) != 1) {
            return;
        }
        const uint32_t a = host->read8(call, work + WORK_BYTE_A);
        const uint32_t b = host->read8(call, work + WORK_BYTE_B);
        if (!call_s012(call, FN_HIT_CHECK, enemy, b, a,
                       bits_of(300.0f), bits_of(0.0f), bits_of(150.0f))) {
            goto timer_check;
        }
        if (!call_r3(call, FN_HIT_CHECK_R3, enemy, 1, b, a)) {
            goto timer_check;
        }
        /* MHXX keeps a value of 1 when two enemy bytes are 2/4; the MH4U handler has no
         * such branch, so the port takes the source's other path. 0x008d0528 has no
         * confirmed MH4U counterpart and is not called. */
        host->write8(call, work + WORK_FLAG_TAIL, 3);
        host->call(call, FN_REQUEST_NEXT, enemy, 9, 1);
        return;
    timer_check:
        if (!f32_gt(host->read32(call, work + WORK_TIMER), bits_of(0.0f))) {
            host->call(call, FN_REQUEST_NEXT, enemy, 2, 6);
            return;
        }
        if (call_r3(call, FN_HIT_CHECK_R3, enemy, 0, b, a)) {
            return;
        }
        host->call(call, FN_REQUEST_NEXT, enemy, 2, 6);
        break;
    }
    }
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
    /* 4/27-32 land on 127-132 so that no other slice's id can take their place. */
    const int which = (category == 3 && index == 98) ? 98
                    : (category == 12 && index >= 1 && index <= 3) ? index
                    : (category == 4 && index >= 27 && index <= 32) ? 100 + index
                    : (category == 8 && index == 0) ? 80
                    : -1;
    if (which < 0 || !ensure_stubs(call)) {
        host->call_original(call);
        return;
    }
    MonsterState *st = state_for(enemy, category, index);
    log_action_once(category, index);
    if (which >= 127) {
        /* 4/27-32: r1 = 2 on the odd ids, 1 on the even ones; r2 = 1 on 4/29 and 4/30. */
        const int mode = (index % 2 == 0) ? 1 : 2;
        const int variant = (index == 29 || index == 30) ? 1 : 0;
        log_precall_once(index);
        run_4_27(call, enemy, work, st, index, mode, variant, read_s(call, 0));
    } else {
        switch (which) {
        case 98: run_3_98(call, enemy, work, st); break;
        case 1: run_12_1(call, enemy, work, st); break;
        case 2: run_12_2(call, enemy, work, st); break;
        case 3: run_12_3(call, enemy, work); break;
        default: run_8_0(call, enemy, work, st); break;
        }
    }
    host->skip_original(call);
}

/* ── self-test (the headless check) ────────────────────────────────────────────────── */
static void self_test(MH4UCall *call) {
    char line[768];
    snprintf(line, sizeof line,
             "selftest: 12 of the 13 actions: 3/98 <- 0x020062d4 (3 states, motions 0x101 and "
             "0x104), 12/1 <- 0x0201c1d0 + 0x020062d4, 12/2 <- 0x0201c228 + 0x0201041c->0x%08x, "
             "12/3 <- 0x0201c27c + 0x02010aec->0x%08x, 4/27-32 <- 0x0200e3b4 (3 states, motions "
             "0x417/0x418, 0x909/0x90a, 0x90b/0x90d, r1/r2 per id), 8/0 <- 0x0201b460 (3 states, "
             "motion 0x403 at 4.0, 12.0/50.0, 300.0/38.0, 180.0, tail 9/1 or 2/6), 17 <- the "
             "gate 0x008d5bd4 + MH4U's base update 0x%08x (slot 89, MHXX's slot 244)",
             (unsigned)FN_HANDLER_3_12, (unsigned)FN_HANDLER_3_9, (unsigned)FN_BASE_UPDATE);
    host->log(host, MH4U_LOG_INFO, line);
    snprintf(line, sizeof line,
             "selftest: category 17 does nothing for indexes 0 to 2; 12/0 is MH4U's own "
             "category-12 handler 0x006d524c; 8/0's leaf 0x008c4184 is MH4U's 0x%08x, "
             "its table not carried", (unsigned)FN_TAIL_DATA);
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
                 "ready: translating 12 of GU Rathian's 13 MHXX-only actions on every monster");
    } else {
        snprintf(line, sizeof line,
                 "ready: translating 12 of GU Rathian's 13 MHXX-only actions on monster %d",
                 monster_id);
    }
    host->log(host, MH4U_LOG_INFO, line);
    return 1;
}
