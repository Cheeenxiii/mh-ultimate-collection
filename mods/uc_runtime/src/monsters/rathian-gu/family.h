/*
 * family.h: one family of GU Rathian's actions, as the module's dispatch sees it.
 *
 * The module is split one file per family under src/monsters/rathian-gu/, because the
 * coming slices add her other ids in parallel: each adds one file and nothing else shared.
 * A family file exports one `const MhucFamily`; the module's build discovers the files in
 * the directory with tools/gen_families.py and writes the list into the generated
 * families.h, which src/monsters/rathian-gu.c iterates. A slice therefore never edits a
 * list, the module's dispatch or another family.
 *
 * The family's `dispatch` gets the MH4U work block and the action pair; it runs its handler
 * and returns 1, or returns 0 so the module tries the next family. A pair no family carries
 * goes to MH4U's dispatcher.
 *
 * Licence: GPL-3.0-or-later.
 */
#ifndef MHUC_RATHIAN_GU_FAMILY_H
#define MHUC_RATHIAN_GU_FAMILY_H

#include <stdint.h>
#include <string.h>

#include "module.h"

/* The bit twiddling the translated handlers share: the source passes floats in the engine
 * calls and reads them back out of guest memory. */
static inline uint32_t mhuc_gu_bits_of(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

static inline float mhuc_gu_f32_of(uint32_t bits) {
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

/* The source's `vcvt.u32.f32` saturates: a negative is 0, anything past 2^32 is all ones. */
static inline uint32_t mhuc_gu_f32_to_u8(float value) {
    if (!(value > 0.0f)) {
        return 0;
    }
    if (value >= 4294967296.0f) {
        return 0xffu;
    }
    return (uint32_t)value & 0xffu;
}

typedef struct MhucFamily {
    const char *name;    /* the family's name, for the log */
    unsigned translated; /* the action ids the family carries, for the ready line */
    /* Runs the family's handler for the pair (category is work+0x1ca, index work+0x1cb), or
     * returns 0 when the pair isn't the family's. */
    int (*dispatch)(MH4UCall *call, uint32_t enemy, uint32_t work, int category, int index);
    /* The family's self-test lines, run with the other families' on the first frame when the
     * setting asks for it; NULL for none. */
    void (*self_test)(MH4UCall *call);
} MhucFamily;

/* 3/98's handler, exported from act3_98.c: 12/1's block runs it before it asks for 12/2. */
void mhuc_gu_run_3_98(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st);

/* The module's state slot and action log for a pair a family carries, from the shell
 * (src/monsters/rathian-gu.c): the state, or NULL when there is no guest memory or no slot.
 * The shell owns the "running the translated action" log, so the line is written once per
 * action change whichever family ran it. */
MhucState *mhuc_gu_state(MH4UCall *call, uint32_t enemy, int category, int index);

#endif
