/*
 * family.h: one family of 3U Rathian's actions, as the module's dispatch sees it.
 *
 * The module is split one file per family under src/monsters/rathian-3u/, because the ten
 * action-slice issues (#217 to #229, and action 4's #136) add handlers in parallel: each adds
 * one file and nothing else shared. A family file exports one `const MhucFamily`; the module's
 * build discovers the files in the directory with tools/gen_families.py and writes the list
 * into the generated families.h, which src/monsters/rathian-3u.c iterates. A slice therefore
 * never edits a list, the module's dispatch or another family.
 *
 * The family's `dispatch` gets the MH4U work block and the action pair; it runs its handler
 * and returns 1, or returns 0 so the module tries the next family. A pair no family carries
 * goes to MH4U's dispatcher and is logged once, so a forced id that does nothing says so.
 *
 * Licence: GPL-3.0-or-later.
 */
#ifndef MHUC_RATHIAN_3U_FAMILY_H
#define MHUC_RATHIAN_3U_FAMILY_H

#include <stdint.h>

#include "module.h"

/* The three base-class handlers category 0 reaches (3U 0x0082d1cc, 0x00858b6c and 0x0082b7dc),
 * exported from cat0.c because a later family whose source falls into one calls it here: 1/10
 * and 2/13 run 0/2's, 3/10, 13/7 and 13/9 run 0/3's. Each runs the base handler's steps and
 * returns nothing; the caller's family dispatch returns 1 afterwards. */
void mhuc_3u_base_0_2(MH4UCall *call, uint32_t enemy, uint32_t work);
void mhuc_3u_base_0_3(MH4UCall *call, uint32_t enemy, uint32_t work);
void mhuc_3u_base_0_6(MH4UCall *call, uint32_t enemy, uint32_t work);

typedef struct MhucFamily {
    const char *name;   /* the family's name, for the log */
    unsigned translated; /* the action ids the family carries, for the ready line */
    /* Runs the family's handler for the pair (category is work+0x1ca, index work+0x1cb), or
     * returns 0 when the pair isn't the family's. */
    int (*dispatch)(MH4UCall *call, uint32_t enemy, uint32_t work, int category, int index);
    /* The family's self-test lines, run with the other families' on the first frame when the
     * setting asks for it; NULL for none. */
    void (*self_test)(MH4UCall *call);
} MhucFamily;

#endif
