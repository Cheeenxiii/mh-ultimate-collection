/*
 * module.h: what the runtime offers a ported monster's module, and what a module exports.
 *
 * Decision 0013 makes the mod's native code one runtime, with one C module per ported
 * monster: src/monsters/<key>.c, named by the registry key in data/ids/registry.csv, with one
 * row in the generated src/modules.h. This header is the whole interface between the two.
 * The runtime provides it once for every module: the ABI 4 guest call (call2: r0-r3, the
 * floats s0/s1 and the float return), the per-monster state slots keyed by the enemy pointer,
 * the motion-number encoder, the work-block and object accessors, and the log. The
 * fake-host harness in tests/ is the other half: a module's dispatch entry can be driven
 * without the game (make test).
 *
 * A module exports one `const MhucModuleOps`: its registry id, its dispatch entry, and the
 * two log hooks (its ready line at init and its self-test on the first frame). It keeps its
 * per-monster state in the runtime's slots (mhuc_state), not in an array of its own. The
 * runtime runs a module only for the monster its id spawned, and hands every other enemy to
 * the game's dispatcher unchanged.
 *
 * Licence: GPL-3.0-or-later.
 */
#ifndef MHUC_MODULE_H
#define MHUC_MODULE_H

#include <stddef.h>
#include <stdint.h>

#include "ids.h"
#include "mh4u_plugin.h"

/* The MH4U motion number the engine's motion start takes: the motion list ("file") and the
 * animation slot in it, which MH4U keeps in one number as `file << 8 | slot`. A module names
 * its motions through this instead of writing the packed number. */
#define MHUC_MOTION(file, slot) (((uint32_t)(file) << 8) | ((uint32_t)(slot) & 0xffu))

/* Bytes a module may keep in one monster's state slot for its own use. */
#define MHUC_STATE_BYTES 12u

/* One live monster's state, keyed by the enemy pointer. The runtime owns the slots; a module
 * asks for its monster's slot with mhuc_state, which resets `state` and `data` when the action
 * pair changes. `state` is the action's own state and `data` the module's scratch. */
typedef struct MhucState {
    uint32_t enemy;      /* the monster's guest address */
    uint8_t used;        /* the slot holds a monster */
    uint8_t category;    /* the action pair the state belongs to */
    uint8_t index;
    uint8_t state;       /* the module's action state */
    uint8_t data[MHUC_STATE_BYTES];
} MhucState;

/* What a monster's module exports. src/modules.h names the one per registered id; a wrong id
 * here fails the runtime at start. */
typedef struct MhucModuleOps {
    uint32_t id;                       /* the registry id the module answers */
    void (*start)(void);               /* once at init: log the module's ready line */
    void (*self_test)(MH4UCall *call); /* once, first frame, `selftest = 1`: log what it carries */
    int (*dispatch)(MH4UCall *call, uint32_t enemy);  /* 1 when it ran a handler, 0 to fall through */
} MhucModuleOps;

/* ── the guest call, ABI 4 ────────────────────────────────────────────────────────────────
 * `r0_r3` holds r0 to r3 (NULL for zeroes), `s0_s1` the floats s0 and s1 (NULL for zeroes),
 * and `s0_out`, when not NULL, gets the function's s0 (its float return). mhuc_call and
 * mhuc_call_f are the same call with the arguments spelled out. The runtime refuses a host
 * older than ABI 4, so these are always present. */
uint32_t mhuc_call2(MH4UCall *call, uint32_t fn, const uint32_t *r0_r3,
                    const float *s0_s1, float *s0_out);
uint32_t mhuc_call(MH4UCall *call, uint32_t fn, uint32_t r0, uint32_t r1, uint32_t r2,
                   uint32_t r3);
uint32_t mhuc_call_f(MH4UCall *call, uint32_t fn, uint32_t r0, uint32_t r1, uint32_t r2,
                     uint32_t r3, float s0, float s1, float *s0_out);

/* A call ABI 4 cannot make: a third float argument in s2. It runs on a guest stub from the
 * game's heap (mhuc_stubs), so it needs that memory. 8/0's first hit check takes three
 * floats. */
uint32_t mhuc_call_s2(MH4UCall *call, uint32_t fn, uint32_t r0, uint32_t r1, uint32_t r2,
                      float s0, float s1, float s2);

/* The caller's floats s0 to s3, which a hook cannot read through ABI 4: a source case block
 * receives its target points there. Runs on a guest stub; a failure returns 0. */
uint32_t mhuc_read_s(MH4UCall *call, unsigned n);

/* The guest stub block's address, or 0 when the game's heap has none: allocates it once. The
 * s2 call and the s0-s3 reads run on it, and a module's self-test logs where it is. */
uint32_t mhuc_stubs(MH4UCall *call);
#define MHUC_STUB_BLOCK_SIZE 384u

/* 16 bytes of guest scratch for an engine function that fills a point (4/27-32's line
 * point), or 0 when there is no guest memory. */
uint32_t mhuc_scratch(MH4UCall *call);
#define MHUC_SCRATCH_SIZE 16u

/* ── the monster, its work block and its object ──────────────────────────────────────────
 * MH4U's monster keeps its work block at *(enemy + 0xe28) and the dispatcher reads the action
 * pair from it (+0x1ca the category, +0x1cb the index). An object field is a pointer at
 * enemy + offset (4/27-32's target line is at +0x8d88). */
uint32_t mhuc_work(MH4UCall *call, uint32_t enemy);
int mhuc_category(MH4UCall *call, uint32_t work);
int mhuc_index(MH4UCall *call, uint32_t work);
uint32_t mhuc_object(MH4UCall *call, uint32_t enemy, uint32_t offset);

/* Guest memory and its floats. */
uint32_t mhuc_read32(MH4UCall *call, uint32_t addr);
uint8_t mhuc_read8(MH4UCall *call, uint32_t addr);
void mhuc_write32(MH4UCall *call, uint32_t addr, uint32_t value);
void mhuc_write8(MH4UCall *call, uint32_t addr, uint32_t value);
float mhuc_f32(MH4UCall *call, uint32_t addr);
void mhuc_put_f32(MH4UCall *call, uint32_t addr, float value);

/* The state slot of `enemy`, with its state reset (and `changed` set, when not NULL) if the
 * slot is new for this monster or the action pair changed. 0 when the runtime has no slot. */
MhucState *mhuc_state(MH4UCall *call, uint32_t enemy, int category, int index, int *changed);

/* The mod's settings (host->config), for a module's start. Init only. */
const char *mhuc_config(const char *key);

/* One line in the port's log, prefixed by the mod's name. */
void mhuc_log(int level, const char *text);
void mhuc_logf(int level, const char *fmt, ...);

#endif
