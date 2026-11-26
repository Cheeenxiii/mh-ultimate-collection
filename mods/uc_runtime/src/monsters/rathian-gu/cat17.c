/*
 * cat17.c: category 17's family — a gate plus MH4U's base action update.
 *
 * MHXX's dispatcher case for 17 (0x020098b8) jumps to 0x008d5bd4, which reads the index byte
 * at this+0x6bf1: 0 to 2 return, any other index tail-calls uEnemy's vtable slot 0x3d0
 * (0x008ae50c). MH4U's uEnemy has 95 slots and no 244, but its slot 89 (0x00911b48) is the
 * same routine on MH4U's layout: the family calls it, and for 0 to 2 does nothing.
 *
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* MH4U's uEnemy vtable slot 89, the same routine as MHXX's slot 0x3d0 (0x008ae50c):
 * 0x008b1700->0x009167b4, 0x00add004->0x0092e960, 0x008ac5a0 (the action setter)
 * ->0x0090ef74, and the finish flag this+0x6b00->work+0x1dc. It is category 17's base update
 * and the 4/27-32 finish flag's end-of-action. */
#define FN_BASE_UPDATE 0x00911b48u

/* Category 17: one line per index, whether the gate's 0-2 no-op or the base update. The
 * family has no per-monster state to keep here, and the first line is the evidence that the
 * forced index reached the translation. */
static uint8_t cat17_logged[256];

static void log_cat17_once(int index) {
    if (cat17_logged[index]) {
        return;
    }
    cat17_logged[index] = 1;
    if (index <= 2) {
        mhuc_logf(MH4U_LOG_INFO, "17/%d: nothing (the gate returns for 0 to 2)", index);
    } else {
        mhuc_logf(MH4U_LOG_INFO, "17/%d: running MH4U's base action update 0x%08x", index,
                  (unsigned)FN_BASE_UPDATE);
    }
}

/* Category 17 is the gate first: MHXX's dispatcher case (0x020098b8) jumps to 0x008d5bd4,
 * which reads the index (this+0x6bf1 there, MH4U's work+0x1cb here), returns for 0 to 2 and
 * otherwise tail-calls uEnemy's slot 0x3d0 (0x008ae50c). MH4U has no such slot; its slot 89
 * (0x00911b48) is the same routine and runs the ported action. */
static int dispatch_cat17(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    (void)work;
    if (category != 17) {
        return 0;
    }
    if (index > 2) {
        mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
    }
    log_cat17_once(index);
    return 1;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. Category 17 is one id in the ready line's count, as the module counted it. */
const MhucFamily mhuc_gu_family_cat17 = {
    "cat17", 1, dispatch_cat17, 0,
};
