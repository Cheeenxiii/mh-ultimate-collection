/*
 * monster_motions.c: translates the motion number a ported monster's MH4U handler asks into
 * the source game's animation, at run time.
 *
 * The port runs MH4U's own handler for every action id the two games share (docs/decisions.md
 * 0002), so the handler asks for an MH4U motion index. The converted motion lists keep the
 * source game's grouping, so that index names another animation or an empty slot. This plugin
 * wraps MH4U's motion-start wrapper (0x0094e318, R1's) and, when the monster is a ported one,
 * replaces the number in r1 with the source game's animation from a generated table
 * (src/motions.h, reference/monster_motions.py table). The mapping is keyed by the monster's
 * current action (the category and index bytes in its work block) and by the number MH4U's
 * handler asks; a missing entry passes the number through unchanged and is logged once.
 *
 * The work block is this+0xe28, with the id byte at +0x1c0 and the current action at +0x1ca
 * and +0x1cb (mods/force_action; docs/checks.md R1p). A ported monster is created as its
 * stand-in (mods/monster_ids rewrites the factory's id), so its id byte holds the stand-in's
 * id. The plugin therefore also wraps the factory (uEnemyFactory::create, 0x006901f4) and
 * remembers each enemy the factory makes for a ported id; this mod comes after
 * mods/monster_ids in the mod order, so its hook runs first and sees the id the quest asked
 * for. Every other enemy is MH4U's own and is left alone.
 *
 * Logging, each line once and at most 64 of each: the first ready line, one line per distinct
 * translation, and one line per distinct missing entry. Nothing is logged per frame.
 *
 * Build: cc -shared -fPIC -I<fork>/include src/monster_motions.c -o monster_motions.so
 * Licence: GPL-3.0-or-later.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "motions.h"
#include "mh4u_plugin.h"

/* Offsets in uEnemy and in the work block its +0xe28 points to (docs/checks.md, R1p). */
#define ENEMY_WORK 0xe28u
#define WORK_ID 0x1c0u
#define WORK_CATEGORY 0x1cau
#define WORK_INDEX 0x1cbu

/* The number of distinct lines logged for translations and for missing entries. */
#define LOG_CAP 64
/* The table's index for a category-only action: the game's index byte is unused. */
#define NO_INDEX 0x100u

static const MH4UPluginHost *host;
static uint32_t translated[LOG_CAP];
static int translated_count;
static uint32_t missing[LOG_CAP];
static int missing_count;

/* The enemies the factory made for a ported id, and that id. A slot is reused when the
 * factory hands the same address out again, for a ported id or not. */
#define PORTED_CAP 32
static struct {
    uint32_t enemy;
    unsigned id;
} ported[PORTED_CAP];

static void say(int level, const char *text) {
    host->log(host, level, text);
}

/* The table generated for this monster id, or NULL when the id is MH4U's own. */
static const MhucPortedMotions *table_for(unsigned id) {
    for (int i = 0; i < MHUC_PORTED_MOTIONS_COUNT; i++) {
        if (mhuc_ported_motions[i].id == id) {
            return &mhuc_ported_motions[i];
        }
    }
    return NULL;
}

/* The source animation for (action, the number MH4U's handler asks), or NULL. */
static const MhucMotion *translation_for(const MhucPortedMotions *table, unsigned category,
                                         unsigned index, unsigned motion) {
    for (unsigned i = 0; i < table->entry_count; i++) {
        const MhucMotion *entry = &table->entries[i];
        if (entry->category != category || entry->motion != motion) {
            continue;
        }
        if (entry->index == NO_INDEX || entry->index == index) {
            return entry;
        }
    }
    return NULL;
}

static void log_translation(unsigned id, unsigned category, unsigned index, unsigned motion,
                            unsigned source) {
    char line[160];
    snprintf(line, sizeof line, "monster %u: action %u/%u asks motion 0x%03x -> source 0x%03x",
             id, category, index, motion, source);
    say(MH4U_LOG_INFO, line);
}

static void log_missing(unsigned id, unsigned category, unsigned index, unsigned motion) {
    char line[200];
    snprintf(line, sizeof line,
             "monster %u: no entry for action %u/%u motion 0x%03x; passing it through", id,
             category, index, motion);
    say(MH4U_LOG_WARNING, line);
}

/* Whether this (action, motion) was already logged. The first sight of a key is logged. */
static int first_time(uint32_t *keys, int *count, uint32_t key) {
    for (int i = 0; i < *count; i++) {
        if (keys[i] == key) {
            return 0;
        }
    }
    if (*count >= LOG_CAP) {
        return 0;
    }
    keys[(*count)++] = key;
    return 1;
}

/* The ported id the factory made `enemy` for, or 0. */
static unsigned ported_id(uint32_t enemy) {
    for (int i = 0; i < PORTED_CAP; i++) {
        if (ported[i].enemy == enemy) {
            return ported[i].id;
        }
    }
    return 0;
}

/* uEnemyFactory::create(owner, id, ...): r1 is the id the quest asked for (this hook runs
 * before mods/monster_ids rewrites it to the stand-in's), r0 the enemy on return. */
static void factory(MH4UCall *call, void *user) {
    (void)user;
    const unsigned id = (unsigned)host->reg(call, 1);
    host->call_original(call);
    const uint32_t enemy = host->reg(call, 0);
    if (!enemy) {
        return;
    }
    int slot = -1;
    for (int i = 0; i < PORTED_CAP; i++) {
        if (ported[i].enemy == enemy) {
            slot = i;
            break;
        }
    }
    if (!table_for(id)) {
        if (slot >= 0) {
            ported[slot].enemy = 0;
            ported[slot].id = 0;
        }
        return;
    }
    for (int i = 0; slot < 0 && i < PORTED_CAP; i++) {
        if (!ported[i].enemy) {
            slot = i;
        }
    }
    if (slot < 0) {
        say(MH4U_LOG_WARNING, "more ported enemies than the plugin tracks; this one keeps "
                              "MH4U's motion numbers");
        return;
    }
    ported[slot].enemy = enemy;
    ported[slot].id = id;
}

/* uEnemy::startMotion(this, motion, flags): r0 is the enemy, r1 the motion number. */
static void start_motion(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t enemy = host->reg(call, 0);
    const uint32_t work = enemy ? host->read32(call, enemy + ENEMY_WORK) : 0;
    if (!work) {
        host->call_original(call);
        return;
    }
    unsigned id = (unsigned)host->read8(call, work + WORK_ID);
    if (!table_for(id)) {
        id = ported_id(enemy);
    }
    const MhucPortedMotions *table = id ? table_for(id) : NULL;
    if (!table) {
        host->call_original(call);
        return;
    }
    const unsigned category = (unsigned)host->read8(call, work + WORK_CATEGORY);
    const unsigned index = (unsigned)host->read8(call, work + WORK_INDEX);
    const unsigned motion = (unsigned)host->reg(call, 1);
    const uint32_t key = ((uint32_t)category << 24) ^ ((uint32_t)index << 16) ^ motion;
    const MhucMotion *entry = translation_for(table, category, index, motion);
    if (entry) {
        host->set_reg(call, 1, entry->source);
        if (first_time(translated, &translated_count, key)) {
            log_translation(id, category, index, motion, entry->source);
        }
    } else if (first_time(missing, &missing_count, key)) {
        /* A distinct missing entry is logged once; the cap keeps a hunt's log readable. */
        log_missing(id, category, index, motion);
    }
    host->call_original(call);
}

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 1 || plugin_host->size < offsetof(MH4UPluginHost, alloc)) {
        return 0;
    }
    host = plugin_host;
#if MHUC_PORTED_MOTIONS_COUNT < 1
#error "the registry has no ported monster: nothing to translate"
#endif
    if (!host->hook(host, "uEnemy::startMotion", start_motion, NULL)) {
        say(MH4U_LOG_ERROR, "uEnemy::startMotion (0x0094e318) isn't a hook point: the code "
                            "library needs building with this mod");
        return 0;
    }
    if (!host->hook(host, "uEnemyFactory::create", factory, NULL)) {
        say(MH4U_LOG_ERROR, "uEnemyFactory::create (0x006901f4) isn't a hook point: a ported "
                            "monster created as its stand-in can't be told apart");
        return 0;
    }
    int entries = 0;
    for (int i = 0; i < MHUC_PORTED_MOTIONS_COUNT; i++) {
        entries += mhuc_ported_motions[i].entry_count;
    }
    char line[200];
    snprintf(line, sizeof line, "ready: translating motion numbers for %d ported monster id(s), "
             "%u entries; MH4U's own ids pass through", MHUC_PORTED_MOTIONS_COUNT, entries);
    say(MH4U_LOG_INFO, line);
    return 1;
}
