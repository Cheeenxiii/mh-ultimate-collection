/*
 * force_action.c: makes a monster perform a chosen action, for check R1
 * (docs/checks.md). It is the mod's first native plugin.
 *
 * The game runs a monster's current action from two bytes of its work block: the action's
 * category and its index. uEnemy's action dispatcher (vtable slot 44, 0x006e9cac) loads the
 * work block from this+0xe28 and branches on the category byte at +0x1ca; the case block it
 * reaches switches on the index byte at +0x1cb. The plugin wraps the dispatcher and writes
 * the two bytes before the game reads them, so the chosen action plays instead of whatever
 * the AI picked.
 *
 * Settings (mod.json "config", the player's config.ini over it):
 *   action   the action to force, "category/index" (decimal or 0x...); default 3/17
 *   monster  the id of the monster to force it on (the work block's byte at +0x1c0), or
 *            "any"; default 1, Rathian (uEm001)
 *   hold     "1": force the action again each time the AI changes it, so it replays
 *            (default); "0": force it once, then leave the monster to the AI
 *
 * Build: cc -shared -fPIC -I<fork>/include src/force_action.c -o force_action.so
 * Licence: GPL-3.0-or-later.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mh4u_plugin.h"

/* A hook point's name, as mod.json lists it: the dispatcher has no name in the project's
 * symbols, so the mod gives it one. */
#define HOOK_NAME "uEnemy::dispatchAction"

/* Offsets in uEnemy, and in the work block its +0xe28 points to (docs/checks.md, R1). */
#define ENEMY_WORK 0xe28u
#define WORK_ID    0x1c0u
#define WORK_CATEGORY 0x1cau
#define WORK_INDEX    0x1cbu

static const MH4UPluginHost *host;
static uint8_t category = 3, index = 17;
static int monster_id = 1;
static int hold = 1, forced;

/* "3/17", "0x03/0x11": two bytes, decimal or hexadecimal. */
static int parse_action(const char *text, uint8_t *out_category, uint8_t *out_index) {
    char *end;
    const char *index_text;
    long cat, idx;
    if (!text || !*text) {
        return 0;
    }
    cat = strtol(text, &end, 0);
    if (end == text || (*end != '/' && *end != ':') || cat < 0 || cat > 255) {
        return 0;
    }
    index_text = end + 1;
    idx = strtol(index_text, &end, 0);
    if (end == index_text || *end != '\0' || idx < 0 || idx > 255) {
        return 0;
    }
    *out_category = (uint8_t)cat;
    *out_index = (uint8_t)idx;
    return 1;
}

static void say(int level, const char *text) {
    host->log(host, level, text);
}

/* Wraps the dispatcher: r0 is the enemy (the game reads this+0xe28 in the function itself). */
static void dispatch(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t enemy = host->reg(call, 0);
    const uint32_t work = host->read32(call, enemy + ENEMY_WORK);
    if (!work) {
        host->call_original(call);
        return;
    }
    const int id = (int)host->read8(call, work + WORK_ID);
    const int match = monster_id < 0 || id == monster_id;
    const uint8_t was_category = (uint8_t)host->read8(call, work + WORK_CATEGORY);
    const uint8_t was_index = (uint8_t)host->read8(call, work + WORK_INDEX);
    const int unchanged = was_category == category && was_index == index;
    if (match && (hold ? !unchanged : !forced)) {
        host->write8(call, work + WORK_CATEGORY, category);
        host->write8(call, work + WORK_INDEX, index);
        char line[128];
        snprintf(line, sizeof line, "monster %d: forced %u/%u over %u/%u", id,
                 (unsigned)category, (unsigned)index, (unsigned)was_category, (unsigned)was_index);
        say(MH4U_LOG_INFO, line);
    }
    forced = forced || match;
    host->call_original(call);
}

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    /* The members this plugin uses are all in the first table; refuse an older host. */
    if (abi < 1 || plugin_host->size < offsetof(MH4UPluginHost, alloc)) {
        return 0;
    }
    host = plugin_host;
    const char *text = host->config(host, "action");
    if (text && *text && !parse_action(text, &category, &index)) {
        char line[160];
        snprintf(line, sizeof line, "bad action \"%s\": write a category and an index, as 3/17", text);
        say(MH4U_LOG_ERROR, line);
        return 0;
    }
    const char *monster = host->config(host, "monster");
    if (monster && *monster) {
        if (strcmp(monster, "any") == 0) {
            monster_id = -1;
        } else {
            char *end;
            const long id = strtol(monster, &end, 0);
            if (*end != '\0' || id < 0 || id > 255) {
                say(MH4U_LOG_ERROR, "bad monster: write an id from 0 to 255, or any");
                return 0;
            }
            monster_id = (int)id;
        }
    }
    const char *holding = host->config(host, "hold");
    if (holding && *holding) {
        if (strcmp(holding, "0") != 0 && strcmp(holding, "1") != 0) {
            say(MH4U_LOG_ERROR, "bad hold: write 1 to hold the action, or 0 to force it once");
            return 0;
        }
        hold = strcmp(holding, "1") == 0;
    }
    if (!host->hook(host, HOOK_NAME, dispatch, NULL)) {
        say(MH4U_LOG_WARNING, "the dispatcher isn't a hook point: the code library needs building with this mod");
        return 0;
    }
    char line[160];
    if (monster_id < 0) {
        snprintf(line, sizeof line, "ready: forcing action %u/%u on every monster", (unsigned)category,
                 (unsigned)index);
    } else {
        snprintf(line, sizeof line, "ready: forcing action %u/%u on monster %d", (unsigned)category,
                 (unsigned)index, monster_id);
    }
    say(MH4U_LOG_INFO, line);
    return 1;
}
