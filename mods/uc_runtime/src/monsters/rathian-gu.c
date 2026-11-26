/*
 * rathian-gu.c: GU Rathian's module, the home of her action families.
 *
 * GU Rathian (MHXX v1.4, roEm001) has 13 action ids MH4U has no action for (3/98, 4/27 to
 * 4/32, 8/0, 12/0 to 12/3 and category 17) and 273 shared ones. Decision 0002's 2026-11-26
 * amendment makes every one of her 301 ids run her own handler, so the module carries the
 * twelve MHXX-only ids that need new C (12/0 stays MH4U's own handler) and the shared ids as
 * slices: category 1 and category 2 (with 9/3 and 9/4) so far.
 *
 * The handlers are ported in slices, one action family per file under
 * src/monsters/rathian-gu/: cat17.c holds category 17's gate and base update, act3_98.c
 * action 3/98, act12_1_3.c the 12/1 to 12/3 chain, act4_27_32.c the six 4/27 to 4/32 ids,
 * act8_0.c action 8/0, cat1.c category 1 and cat2.c category 2. The coming slices add their
 * own file there and edit nothing shared.
 *
 * This file holds what every family shares: the factory association's entry (the runtime calls
 * `dispatch` for the monster it recorded as id 124), the action log, the ready line and the
 * self-test. The family list is not written here: the build discovers the files in
 * src/monsters/rathian-gu/ with tools/gen_families.py and writes the generated families.h,
 * which this file includes. A family file exports one `const MhucFamily` (family.h), and its
 * `dispatch` returns 1 when it ran the pair or 0 to let the next family try. A pair no family
 * carries goes to MH4U's dispatcher.
 *
 * The engine calls go through the runtime's ABI 4 helpers (mhuc_call / mhuc_call_f) instead of
 * the old plugin's own guest stubs; the two calls ABI 4 cannot make keep a guest stub,
 * provided by the runtime (mhuc_read_s, mhuc_call_s2). The module adds no hook of its own.
 *
 * Settings (the runtime's mod.json "config", the player's config.ini over it):
 *   monster   the id the ready line names; the module answers the registry id it was built for
 *   selftest  "1": log what this module translates and what is still pending
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "../module.h"
#include "rathian-gu/families.h"

/* The MH4U addresses the self-test names, by the function each stands for. */
#define FN_HANDLER_3_9  0x006d5e98u /* MH4U's shared 3/9 handler (also 3/5) */
#define FN_HANDLER_3_12 0x006d791cu /* MH4U's shared 3/12 handler */
#define FN_BASE_UPDATE  0x00911b48u /* uEnemy vtable slot 89, category 17's base update */

static int action_logged;

static void log_action_once(int category, int index) {
    if (action_logged) {
        return;
    }
    action_logged = 1;
    mhuc_logf(MH4U_LOG_INFO, "running the translated action %d/%d", category, index);
}

/* A family asks for the pair's state through this: the module's one state slot and the
 * "running the translated action" line, written once per action change whichever family ran
 * it. Returns NULL when the runtime has no guest memory for the stubs or no state slot, so the
 * family leaves the pair to the game exactly as the module did. */
MhucState *mhuc_gu_state(MH4UCall *call, uint32_t enemy, int category, int index) {
    if (!mhuc_stubs(call)) {
        return NULL;
    }
    int changed = 0;
    MhucState *st = mhuc_state(call, enemy, category, index, &changed);
    if (!st) {
        return NULL;
    }
    if (changed) {
        action_logged = 0;
        log_action_once(category, index);
    }
    return st;
}

/* The module's dispatch entry. The runtime recorded the enemy at the factory and calls this
 * for each action; the family list is the one the build discovered. */
static int dispatch(MH4UCall *call, uint32_t enemy) {
    const uint32_t work = mhuc_work(call, enemy);
    if (!work) {
        return 0;
    }
    const int category = mhuc_category(call, work);
    const int index = mhuc_index(call, work);
    for (unsigned i = 0; i < MHUC_GU_FAMILY_COUNT; i++) {
        const MhucFamily *family = mhuc_gu_families[i];
        if (family && family->dispatch &&
            family->dispatch(call, enemy, work, category, index)) {
            return 1;
        }
    }
    return 0;
}

/* The module's ready line, at init: the same line the old plugin logged, with the source's
 * whole action set as the denominator since 0002's 2026-11-26 amendment makes every id hers.
 * The setting's id is what the line names; the module answers its registry id whatever it
 * says (the runtime warns when the setting names no module). Each family declares its own
 * count, so a slice's file is the only one that names it. */
static void start(void) {
    unsigned translated = 0;
    for (unsigned i = 0; i < MHUC_GU_FAMILY_COUNT; i++) {
        if (mhuc_gu_families[i]) {
            translated += mhuc_gu_families[i]->translated;
        }
    }
    int monster_id = (int)MHUC_MONSTER_ID_RATHIAN_GU;
    const char *monster = mhuc_config("monster");
    if (monster && *monster && strcmp(monster, "any") != 0) {
        char *end;
        const long id = strtol(monster, &end, 0);
        if (*end == '\0' && id >= 0 && id <= 255) {
            monster_id = (int)id;
        }
    }
    mhuc_logf(MH4U_LOG_INFO,
              "ready: translating %u of GU Rathian's 301 actions on monster %d",
              translated, monster_id);
}

/* The self-test the headless check reads: the families the build discovered, what the module
 * carries, what 12/0 is, and where the runtime's guest stubs are. */
static void self_test(MH4UCall *call) {
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: %u family file(s) discovered from src/monsters/rathian-gu/",
              (unsigned)MHUC_GU_FAMILY_COUNT);
    unsigned translated = 0;
    for (unsigned i = 0; i < MHUC_GU_FAMILY_COUNT; i++) {
        if (mhuc_gu_families[i]) {
            translated += mhuc_gu_families[i]->translated;
        }
    }
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: %u of the 301 actions: 3/98 <- 0x020062d4 (3 states, motions 0x101 and "
              "0x104), 12/1 <- 0x0201c1d0 + 0x020062d4, 12/2 <- 0x0201c228 + 0x0201041c->0x%08x, "
              "12/3 <- 0x0201c27c + 0x02010aec->0x%08x, 4/27-32 <- 0x0200e3b4 (3 states, motions "
              "0x417/0x418, 0x909/0x90a, 0x90b/0x90d, r1/r2 per id), 8/0 <- 0x0201b460 (3 states, "
              "motion 0x403 at 4.0, 12.0/50.0, 300.0/38.0, 180.0, tail 9/1 or 2/6), 17 <- the "
              "gate 0x008d5bd4 + MH4U's base update 0x%08x (slot 89, MHXX's slot 244), and the "
              "shared ids: category 1's twelve and category 2's thirty plus 9/3 and 9/4",
              translated, (unsigned)FN_HANDLER_3_12, (unsigned)FN_HANDLER_3_9,
              (unsigned)FN_BASE_UPDATE);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 17 does nothing for indexes 0 to 2; 12/0 is MH4U's own "
             "category-12 handler 0x006d524c; 8/0's leaf 0x008c4184 is MH4U's 0x0092f6e8, "
             "its table not carried");
    for (unsigned i = 0; i < MHUC_GU_FAMILY_COUNT; i++) {
        const MhucFamily *family = mhuc_gu_families[i];
        if (family && family->self_test) {
            family->self_test(call);
        }
    }
    const uint32_t stubs = mhuc_stubs(call);
    if (stubs) {
        mhuc_logf(MH4U_LOG_INFO,
                  "selftest: float stubs at 0x%08x (%u bytes, the game's heap)", (unsigned)stubs,
                  (unsigned)MHUC_STUB_BLOCK_SIZE);
    } else {
        mhuc_log(MH4U_LOG_WARNING, "selftest: no float stubs (no guest memory)");
    }
}

/* The module's one export: src/modules.h names it in the row for id 124. */
const struct MhucModuleOps mhuc_module_rathian_gu = {
    MHUC_MONSTER_ID_RATHIAN_GU,
    start,
    self_test,
    dispatch,
};
