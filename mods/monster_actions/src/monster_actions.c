/*
 * monster_actions.c: runs the MH4U action whose handler has the same body as a source game
 * action that MH4U's monster class lacks.
 *
 * A shared action id already runs MH4U's own handler (docs/decisions.md 0002). 16 of the 17
 * 3U Rathian ids MH4U's uEm001 lacks reach the same handler function as a shared action
 * (reference/README.md's action-id map), so the port does not carry them as new C: this
 * plugin wraps MH4U's action setter (0x0090ef74) and, for a ported monster, replaces the
 * requested pair with the mapped MH4U pair from the generated table (src/actions.h,
 * reference/monster_handlers.py table). The game's setter then initializes the shared action,
 * and MH4U's own handler runs. The target's case block supplies its own variant arguments.
 *
 * The work block is this+0xe28, with the id byte at +0x1c0 and the current action at +0x1ca
 * and +0x1cb (mods/force_action; docs/checks.md R1p). Ids MH4U's own monsters use are not in
 * the table and pass through, as does action 4 (which needs new C) and every move still to
 * be translated.
 *
 * An action the table maps is skipped while the mapped action is already the current one:
 * MH4U calls the setter about twice a frame, and letting each call restart the move held it
 * on its first frame (force_action's R1p session, 2026-11-25).
 *
 * Logging: the first ready line, then one line per distinct translation. Nothing per frame.
 *
 * Build: cc -shared -fPIC -I<fork>/include src/monster_actions.c -o monster_actions.so
 * Licence: GPL-3.0-or-later.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "actions.h"
#include "mh4u_plugin.h"

/* Offsets in uEnemy and in the work block its +0xe28 points to (docs/checks.md, R1p). */
#define ENEMY_WORK 0xe28u
#define WORK_ID 0x1c0u
#define WORK_CATEGORY 0x1cau
#define WORK_INDEX 0x1cbu

/* The number of distinct translations logged for the in-game check. */
#define LOG_CAP 64

static const MH4UPluginHost *host;
static uint32_t translated[LOG_CAP];
static int translated_count;

static void say(int level, const char *text) {
    host->log(host, level, text);
}

/* The table generated for this monster id, or NULL when the id is MH4U's own. */
static const MhucPortedActions *table_for(unsigned id) {
    for (int i = 0; i < MHUC_PORTED_ACTIONS_COUNT; i++) {
        if (mhuc_ported_actions[i].id == id) {
            return &mhuc_ported_actions[i];
        }
    }
    return NULL;
}

/* The MH4U action that serves this source action, or NULL when the table does not map it. */
static const MhucAction *translation_for(const MhucPortedActions *table, unsigned category,
                                         unsigned index) {
    for (unsigned i = 0; i < table->entry_count; i++) {
        const MhucAction *entry = &table->entries[i];
        if (entry->category != category) {
            continue;
        }
        if (entry->index == MHUC_ACTION_NO_INDEX || entry->index == index) {
            return entry;
        }
    }
    return NULL;
}

static void log_translation(unsigned id, const MhucAction *entry) {
    char line[120];
    snprintf(line, sizeof line, "monster %u: action %u/%u -> %u/%u", id, entry->category,
             entry->index, entry->target_category, entry->target_index);
    say(MH4U_LOG_INFO, line);
}

/* Whether this translation was already logged. The first sight of a key is logged. */
static int first_time(uint32_t key) {
    for (int i = 0; i < translated_count; i++) {
        if (translated[i] == key) {
            return 0;
        }
    }
    if (translated_count >= LOG_CAP) {
        return 0;
    }
    translated[translated_count++] = key;
    return 1;
}

/* uEnemy::setAction(this, category, index, mode): r0 is the enemy, r1 and r2 the action. */
static void set_action(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t enemy = host->reg(call, 0);
    const uint32_t work = enemy ? host->read32(call, enemy + ENEMY_WORK) : 0;
    if (!work) {
        host->call_original(call);
        return;
    }
    const unsigned id = (unsigned)host->read8(call, work + WORK_ID);
    const MhucPortedActions *table = table_for(id);
    if (!table) {
        host->call_original(call);
        return;
    }
    const unsigned category = (unsigned)host->reg(call, 1) & 0xffu;
    const unsigned index = (unsigned)host->reg(call, 2) & 0xffu;
    const MhucAction *entry = translation_for(table, category, index);
    if (!entry) {
        host->call_original(call);
        return;
    }
    const unsigned current_category = (unsigned)host->read8(call, work + WORK_CATEGORY);
    const unsigned current_index = (unsigned)host->read8(call, work + WORK_INDEX);
    if (current_category == entry->target_category && current_index == entry->target_index) {
        /* Already running the action this id is served by: do not restart it. */
        host->skip_original(call);
        return;
    }
    host->set_reg(call, 1, entry->target_category);
    host->set_reg(call, 2, entry->target_index);
    const uint32_t key = ((uint32_t)entry->category << 24) | ((uint32_t)entry->index << 16) |
                         ((uint32_t)entry->target_category << 8) | entry->target_index;
    if (first_time(key)) {
        log_translation(id, entry);
    }
    host->call_original(call);
}

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 1 || plugin_host->size < offsetof(MH4UPluginHost, alloc)) {
        return 0;
    }
    host = plugin_host;
    if (!host->hook(host, "uEnemy::setAction", set_action, NULL)) {
        say(MH4U_LOG_ERROR, "uEnemy::setAction (0x0090ef74) isn't a hook point: the code "
                            "library needs building with this mod");
        return 0;
    }
    int entries = 0;
    for (int i = 0; i < MHUC_PORTED_ACTIONS_COUNT; i++) {
        entries += mhuc_ported_actions[i].entry_count;
    }
    char line[160];
    snprintf(line, sizeof line, "ready: translating %d source action id(s) for %d ported "
             "monster id(s); MH4U's own ids pass through", entries,
             MHUC_PORTED_ACTIONS_COUNT);
    say(MH4U_LOG_INFO, line);
    return 1;
}
