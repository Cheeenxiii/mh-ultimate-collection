/*
 * rathian-3u.c: 3U Rathian's module, the home of her action families.
 *
 * The module runs her own handlers, reimplemented on MH4U's uEnemy with MH4U's engine
 * functions and the source's frame values and call order (decision 0002's 2026-11-26
 * amendment). Her 191 action ids are ported in slices, one action family per file under
 * src/monsters/rathian-3u/: cat0.c holds category 0's six ids and the three base handlers they
 * reach. The ten slice issues (#217 to #229, and action 4's #136) each add one file there and
 * edit nothing else.
 *
 * This file holds what every family shares: the factory association's entry (the runtime calls
 * `dispatch` for the monster it recorded as id 125), the pending log, the ready line and the
 * self-test that calls each family's. The family list is not written here: the build discovers
 * the files in src/monsters/rathian-3u/ with tools/gen_families.py and writes the generated
 * families.h, which this file includes. A family file exports one `const MhucFamily`
 * (family.h), and its `dispatch` returns 1 when it ran the pair or 0 to let the next family
 * try. A pair no family carries goes to MH4U's dispatcher once and is logged, so a forced id
 * that does nothing says so.
 *
 * Adding a slice: write src/monsters/rathian-3u/<family>.c with its handlers and its
 * `const MhucFamily mhuc_3u_family_<family>`, and mark its ids in data/actions/rathian-3u.csv.
 * Nothing else changes; `make` regenerates the list. The runtime's README has the family
 * interface, the field map and the engine-call map.
 *
 * Settings (the runtime's mod.json "config", the player's config.ini over it):
 *   selftest  "1": log this module's families and each family's self-test
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "../module.h"
#include "rathian-3u/families.h"

/* An id no family carries goes to MH4U's dispatcher and is logged once, so a forced id that
 * does nothing says so. */
#define PENDING_SEEN 256
static uint16_t pending_seen[PENDING_SEEN];
static int pending_count;

static void log_pending_once(int category, int index) {
    const uint16_t pair = (uint16_t)(((unsigned)category << 8) | (unsigned)index);
    for (int i = 0; i < pending_count; i++) {
        if (pending_seen[i] == pair) {
            return;
        }
    }
    if (pending_count < PENDING_SEEN) {
        pending_seen[pending_count++] = pair;
    }
    mhuc_logf(MH4U_LOG_INFO,
              "pending action %d/%d: no family carries it, MH4U's dispatcher runs it", category,
              index);
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
    for (unsigned i = 0; i < MHUC_3U_FAMILY_COUNT; i++) {
        const MhucFamily *family = mhuc_3u_families[i];
        if (family && family->dispatch &&
            family->dispatch(call, enemy, work, category, index)) {
            return 1;
        }
    }
    log_pending_once(category, index);
    return 0;
}

/* The module's ready line: the ids the families carry, out of the source's 191, on the id it
 * answers. Each family declares its own count, so a slice's file is the only one that names
 * it. */
static void start(void) {
    unsigned translated = 0;
    for (unsigned i = 0; i < MHUC_3U_FAMILY_COUNT; i++) {
        if (mhuc_3u_families[i]) {
            translated += mhuc_3u_families[i]->translated;
        }
    }
    mhuc_logf(MH4U_LOG_INFO,
              "ready: translating %u of 3U Rathian's 191 actions on monster %u", translated,
              (unsigned)MHUC_MONSTER_ID_RATHIAN_3U);
}

/* The self-test the headless check reads: the families the build discovered, then each
 * family's own lines, then the runtime's stubs. */
static void self_test(MH4UCall *call) {
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: %u family file(s) discovered from src/monsters/rathian-3u/",
              (unsigned)MHUC_3U_FAMILY_COUNT);
    for (unsigned i = 0; i < MHUC_3U_FAMILY_COUNT; i++) {
        const MhucFamily *family = mhuc_3u_families[i];
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

/* The module's one export: src/modules.h names it in the row for id 125. */
const struct MhucModuleOps mhuc_module_rathian_3u = {
    MHUC_MONSTER_ID_RATHIAN_3U,
    start,
    self_test,
    dispatch,
};
