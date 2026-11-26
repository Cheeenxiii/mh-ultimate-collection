/*
 * module.c: the runtime's side of the monster-module interface.
 *
 * Decision 0013 puts every ported monster's action code in the runtime as a module
 * (src/monsters/<key>.c, one row per registry id in the generated src/modules.h). This file
 * is the machinery every module shares, written once (src/module.h is what a module sees):
 *
 *   - the factory association. uEnemyFactory::create is called with the ported id in r1, and
 *     the id layer's reader rewrites that register to the stand-in before the game creates the
 *     monster. This hook is registered after the id layer's, so it runs first: it keeps the
 *     original id, calls the rest of the chain (the id layer answers the stand-in, then the
 *     game creates the enemy), and records the returned enemy pointer against the module its
 *     registry id names. An id no module answers is not recorded and falls through.
 *   - the action dispatcher. uEnemy::dispatchAction runs the module recorded for r0's enemy;
 *     the module reads the action pair, runs the handler it carries, and returns 0 for a pair
 *     it does not, so the game's dispatcher runs unchanged. Every other monster has no module
 *     recorded and goes to the game too.
 *   - the per-monster state slots, keyed by the enemy pointer, that a module keeps its action
 *     state in.
 *   - the guest call: ABI 4's call2 (r0-r3, s0/s1, the s0 return) and the guest stubs for the
 *     two things it cannot do, a third float argument (s2) and reading the caller's s0-s3.
 *   - the motion-number encoder and the work-block/object accessors, in src/module.h.
 *
 * The runtime's one hook list is the id layer's names plus these two; a module adds no hook.
 * Licence: GPL-3.0-or-later.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "module.h"
#include "modules.h"
#include "runtime.h"

/* The runtime's per-monster state slots: one per live monster, keyed by the enemy pointer. */
#define MHUC_STATE_SLOTS 8

static const MH4UPluginHost *host;
static int selftest;
static int self_test_done;

static MhucState states[MHUC_STATE_SLOTS];

/* The spawned monsters the runtime knows: the enemy pointer and the module it answers. A new
 * monster reuses a free row, then the oldest one, which keeps the table small: a quest fields
 * a few monsters, and every create overwrites its own row. */
#define MHUC_ASSOCIATIONS 16
typedef struct Association {
    uint32_t enemy;
    const MhucModuleOps *ops;
} Association;
static Association associations[MHUC_ASSOCIATIONS];
static unsigned association_next;

static void associate(uint32_t enemy, const MhucModuleOps *ops) {
    const unsigned start = association_next;
    for (unsigned i = 0; i < MHUC_ASSOCIATIONS; i++) {
        const unsigned at = (start + i) % MHUC_ASSOCIATIONS;
        if (!associations[at].enemy || associations[at].enemy == enemy) {
            associations[at].enemy = enemy;
            associations[at].ops = ops;
            association_next = (at + 1) % MHUC_ASSOCIATIONS;
            return;
        }
    }
    associations[start].enemy = enemy;
    associations[start].ops = ops;
    association_next = (start + 1) % MHUC_ASSOCIATIONS;
}

static const MhucModuleOps *module_of(uint32_t enemy) {
    if (!enemy) {
        return 0;
    }
    for (unsigned i = 0; i < MHUC_ASSOCIATIONS; i++) {
        if (associations[i].enemy == enemy) {
            return associations[i].ops;
        }
    }
    return 0;
}

/* ── the guest stubs ────────────────────────────────────────────────────────────────────
 * ABI 4 sets r0-r3 and s0/s1. Two things need a small ARM stub written into a block from the
 * game's heap (alloc, ABI 2): a call with a third float in s2 (8/0's hit check), and reading
 * the dispatcher caller's s0-s3 (a source case block receives target points there). The port
 * runs code it hasn't recompiled in its interpreter (port/src/arm_recomp.cpp, Interpret),
 * which reads the bytes each time, so the literals can be rewritten per call. */
#define STUB_READ     128u   /* s0-s3 readers, 32 bytes */
#define STUB_S012     160u   /* s0/s1/s2, 40 bytes */
#define STUB_SCRATCH  208u   /* 16 bytes of guest memory for a point an engine function fills */

static uint32_t stub_block;
static int stub_failed, stub_logged;

uint32_t mhuc_stubs(MH4UCall *call) {
    if (stub_block || stub_failed) {
        return stub_block;
    }
    stub_block = host->alloc(call, MHUC_STUB_BLOCK_SIZE, 16);
    if (!stub_block) {
        stub_failed = 1;
        if (!stub_logged) {
            stub_logged = 1;
            mhuc_log(MH4U_LOG_WARNING,
                     "no guest memory for the float stubs: the calls ABI 4 can't make stay "
                     "unmade");
        }
        return 0;
    }
    return stub_block;
}

uint32_t mhuc_scratch(MH4UCall *call) {
    return mhuc_stubs(call) ? stub_block + STUB_SCRATCH : 0;
}

/* vmov r0, sN; bx lr: one float the dispatcher's caller passed in s0-s3. */
uint32_t mhuc_read_s(MH4UCall *call, unsigned n) {
    if (n > 3 || !mhuc_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_READ + 8u * n;
    const uint32_t args[4] = {0, 0, 0, 0};
    host->write32(call, at + 0, 0xEE100A10u | (n << 16));
    host->write32(call, at + 4, 0xE12FFF1Eu);
    return host->call2(call, at, args, NULL, NULL);
}

/* vldr s0,[pc,#16]; vldr s1,[pc,#16]; vldr s2,[pc,#16]; ldr pc,[pc,#16]; pad; pad;
 * <s0>; <s1>; <s2>; <function> */
uint32_t mhuc_call_s2(MH4UCall *call, uint32_t fn, uint32_t r0, uint32_t r1, uint32_t r2,
                      float s0, float s1, float s2) {
    if (!mhuc_stubs(call)) {
        return 0;
    }
    const uint32_t at = stub_block + STUB_S012;
    uint32_t s0_bits, s1_bits, s2_bits;
    memcpy(&s0_bits, &s0, sizeof s0_bits);
    memcpy(&s1_bits, &s1, sizeof s1_bits);
    memcpy(&s2_bits, &s2, sizeof s2_bits);
    host->write32(call, at + 0, 0xED9F0A04u);
    host->write32(call, at + 4, 0xED9F1A04u);
    host->write32(call, at + 8, 0xED9F2A04u);
    host->write32(call, at + 12, 0xE59FF010u);
    host->write32(call, at + 16, 0xE1A01001u);
    host->write32(call, at + 20, 0xE1A01001u);
    host->write32(call, at + 24, s0_bits);
    host->write32(call, at + 28, s1_bits);
    host->write32(call, at + 32, s2_bits);
    host->write32(call, at + 36, fn);
    const uint32_t args[4] = {r0, r1, r2, 0};
    return host->call2(call, at, args, NULL, NULL);
}

/* ── the guest call ───────────────────────────────────────────────────────────────────── */

uint32_t mhuc_call2(MH4UCall *call, uint32_t fn, const uint32_t *r0_r3,
                    const float *s0_s1, float *s0_out) {
    return host->call2(call, fn, r0_r3, s0_s1, s0_out);
}

uint32_t mhuc_call(MH4UCall *call, uint32_t fn, uint32_t r0, uint32_t r1, uint32_t r2,
                   uint32_t r3) {
    const uint32_t args[4] = {r0, r1, r2, r3};
    return host->call2(call, fn, args, NULL, NULL);
}

uint32_t mhuc_call_f(MH4UCall *call, uint32_t fn, uint32_t r0, uint32_t r1, uint32_t r2,
                     uint32_t r3, float s0, float s1, float *s0_out) {
    const uint32_t args[4] = {r0, r1, r2, r3};
    const float floats[2] = {s0, s1};
    return host->call2(call, fn, args, floats, s0_out);
}

/* ── the monster, its work block and its object ──────────────────────────────────────── */

#define ENEMY_WORK    0x0e28u
#define WORK_CATEGORY 0x01cau
#define WORK_INDEX    0x01cbu

uint32_t mhuc_work(MH4UCall *call, uint32_t enemy) {
    return enemy ? host->read32(call, enemy + ENEMY_WORK) : 0;
}

int mhuc_category(MH4UCall *call, uint32_t work) {
    return work ? (int)host->read8(call, work + WORK_CATEGORY) : 0;
}

int mhuc_index(MH4UCall *call, uint32_t work) {
    return work ? (int)host->read8(call, work + WORK_INDEX) : 0;
}

uint32_t mhuc_object(MH4UCall *call, uint32_t enemy, uint32_t offset) {
    return host->read32(call, enemy + offset);
}

uint32_t mhuc_read32(MH4UCall *call, uint32_t addr) {
    return host->read32(call, addr);
}

uint8_t mhuc_read8(MH4UCall *call, uint32_t addr) {
    return (uint8_t)host->read8(call, addr);
}

void mhuc_write32(MH4UCall *call, uint32_t addr, uint32_t value) {
    host->write32(call, addr, value);
}

void mhuc_write8(MH4UCall *call, uint32_t addr, uint32_t value) {
    host->write8(call, addr, value);
}

float mhuc_f32(MH4UCall *call, uint32_t addr) {
    uint32_t bits = host->read32(call, addr);
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

void mhuc_put_f32(MH4UCall *call, uint32_t addr, float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    host->write32(call, addr, bits);
}

/* ── the per-monster state slots ─────────────────────────────────────────────────────── */

MhucState *mhuc_state(MH4UCall *call, uint32_t enemy, int category, int index, int *changed) {
    (void)call;
    MhucState *free_slot = 0;
    for (unsigned i = 0; i < MHUC_STATE_SLOTS; i++) {
        MhucState *slot = &states[i];
        if (!slot->used) {
            if (!free_slot) {
                free_slot = slot;
            }
            continue;
        }
        if (slot->enemy != enemy) {
            continue;
        }
        if (slot->category != category || slot->index != index) {
            slot->category = (uint8_t)category;
            slot->index = (uint8_t)index;
            slot->state = 0;
            memset(slot->data, 0, sizeof slot->data);
            if (changed) {
                *changed = 1;
            }
        } else if (changed) {
            *changed = 0;
        }
        return slot;
    }
    MhucState *slot = free_slot ? free_slot : &states[0];
    slot->enemy = enemy;
    slot->category = (uint8_t)category;
    slot->index = (uint8_t)index;
    slot->state = 0;
    memset(slot->data, 0, sizeof slot->data);
    slot->used = 1;
    if (changed) {
        *changed = 1;
    }
    return slot;
}

/* ── the settings and the log ────────────────────────────────────────────────────────── */

const char *mhuc_config(const char *key) {
    return host ? host->config(host, key) : 0;
}

void mhuc_log(int level, const char *text) {
    if (host) {
        host->log(host, level, text);
    }
}

void mhuc_logf(int level, const char *fmt, ...) {
    char line[768];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(line, sizeof line, fmt, ap);
    va_end(ap);
    mhuc_log(level, line);
}

/* ── the factory association ─────────────────────────────────────────────────────────── */

/* uEnemyFactory::create: the ported id is in r1 before the id layer's reader, registered
 * earlier, rewrites it to the stand-in. Keep it, run the rest of the chain, and record the
 * enemy the game returns against the module the id names. */
static void on_create(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t original = host->reg(call, 1);
    host->call_original(call);
    const uint32_t enemy = host->reg(call, 0);
    if (!enemy) {
        return;
    }
    const uint32_t registry = mhuc_ids_registry_id(original);
    if (!registry) {
        return;   /* MH4U's own id, or a free pool byte */
    }
    const MhucModule *module = mhuc_module_for(registry);
    if (module && module->ops) {
        associate(enemy, module->ops);
    }
}

/* uEnemy::dispatchAction: run the module recorded for this monster, or the game's dispatcher. */
static void on_dispatch(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t enemy = host->reg(call, 0);
    const MhucModuleOps *ops = module_of(enemy);
    if (!ops || !ops->dispatch || !ops->dispatch(call, enemy)) {
        host->call_original(call);
        return;
    }
    host->skip_original(call);
}

/* The runtime's own hooks, registered after the id layer's: the host puts a later hook first
 * in a function's chain, so the factory association sees the id before the id layer rewrites
 * it. */
static const MhucHook hooks[] = {
    {"uEnemyFactory::create", "0x006901f4", on_create, NULL},
    {"uEnemy::dispatchAction", "0x006e9cac", on_dispatch, NULL},
};

const MhucHook *mhuc_modules_hooks(size_t *count) {
    *count = sizeof hooks / sizeof hooks[0];
    return hooks;
}

/* Takes the host, reads the module settings and calls each module's start (its ready line).
 * Returns 0 when a setting is bad, which refuses the plugin as the old action plugin did. */
int mhuc_modules_start(const MH4UPluginHost *plugin_host) {
    host = plugin_host;
    const char *test = host->config(host, "selftest");
    selftest = test && strcmp(test, "0") != 0;
    const char *monster = host->config(host, "monster");
    if (monster && *monster && strcmp(monster, "any") != 0) {
        char *end;
        const long id = strtol(monster, &end, 0);
        if (*end != '\0' || id < 0 || id > 255) {
            mhuc_log(MH4U_LOG_ERROR, "bad monster: write an id from 0 to 255, or any");
            return 0;
        }
        int named = 0;
        for (unsigned i = 0; i < MHUC_MODULE_COUNT; i++) {
            if (mhuc_modules[i].id == (uint32_t)id && mhuc_modules[i].ops) {
                named = 1;
            }
        }
        if (!named) {
            mhuc_logf(MH4U_LOG_WARNING,
                      "monster %ld has no module: a module answers the registry id it was "
                      "built for, so the setting no longer chooses another monster", id);
        }
    }
    for (unsigned i = 0; i < MHUC_MODULE_COUNT; i++) {
        if (mhuc_modules[i].ops && mhuc_modules[i].ops->start) {
            mhuc_modules[i].ops->start();
        }
    }
    return 1;
}

/* Once a frame: each module's self-test on the first frame, when the setting asks for it. The
 * runtime.c frame calls this after the id layer's. */
void mhuc_modules_frame(MH4UCall *call, void *user) {
    (void)user;
    if (self_test_done || !selftest) {
        return;
    }
    self_test_done = 1;
    for (unsigned i = 0; i < MHUC_MODULE_COUNT; i++) {
        if (mhuc_modules[i].ops && mhuc_modules[i].ops->self_test) {
            mhuc_modules[i].ops->self_test(call);
        }
    }
}
