/*
 * force_action.c: makes a monster perform a chosen action, for the plugin's check R1p
 * (docs/checks.md). It is the mod's first native plugin.
 *
 * The game's action setter is uEnemy::setAction (0x0090ef74): it takes (this, category,
 * index, mode), and the AI calls it when it changes a monster's action. It is also what
 * initializes the action's state. The plugin wraps it and, for the chosen monster, replaces
 * its category and index arguments with the forced pair, so the AI's change becomes the
 * forced action and the handler gets its state. That is what lets the move play.
 *
 * The action dispatcher (vtable slot 44, 0x006e9cac) is only the fallback, for a code
 * library built without the setter hook. Writing the pair there cannot win: the AI's setter
 * has already reset the action state, so the handler stays on its first frame and the
 * monster holds a pose. The log says when the fallback is in use, and that library needs
 * rebuilding.
 *
 * Settings (mod.json "config", the player's config.ini over it):
 *   action   the action to force, "category/index" (decimal or 0x...); default 3/17
 *   monster  the id of the monster to force it on (the work block's byte at +0x1c0), or
 *            "any"; default 1, Rathian (uEm001)
 *   hold     "1": keep the monster on the forced action, starting it again after each end
 *            (default); "0": force the first setter call once, then leave the AI alone
 *
 * Logging: one "first force" line, then one "setter" line per distinct call (at most 64),
 * never one per frame.
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

/* The hook points, as mod.json lists them. Neither function has a name in the project's
 * symbols, so the mod gives them names. */
#define HOOK_SETTER   "uEnemy::setAction"
#define HOOK_DISPATCH "uEnemy::dispatchAction"

/* Offsets in uEnemy, and in the work block its +0xe28 points to (docs/checks.md, R1p). */
#define ENEMY_WORK 0xe28u
#define WORK_ID    0x1c0u
#define WORK_CATEGORY 0x1cau
#define WORK_INDEX    0x1cbu

static const MH4UPluginHost *host;
static uint8_t category = 3, index = 17;
static int monster_id = 1;
static int hold = 1, forced, logged, via_setter;
static int last_ai_category = -1, last_ai_index = -1;
#define END_SKIPS 300 /* about five seconds of frames */
static int end_skips;

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

/* The enemy is in r0; its work block is the pointer at this+0xe28. -1 when there is none. */
static int monster_work(MH4UCall *call, uint32_t *work_out) {
    const uint32_t enemy = host->reg(call, 0);
    const uint32_t work = host->read32(call, enemy + ENEMY_WORK);
    if (!work) {
        return -1;
    }
    *work_out = work;
    return (int)host->read8(call, work + WORK_ID);
}

/* The first force, then one line per change of the action the AI asked for. */
static void log_force(int id, int ai_category, int ai_index) {
    char line[160];
    if (!logged) {
        snprintf(line, sizeof line, "first force: monster %d %u/%u over %u/%u", id,
                 (unsigned)category, (unsigned)index, (unsigned)ai_category, (unsigned)ai_index);
        logged = 1;
    } else {
        snprintf(line, sizeof line, "monster %d: %u/%u over %u/%u", id,
                 (unsigned)category, (unsigned)index, (unsigned)ai_category, (unsigned)ai_index);
    }
    last_ai_category = ai_category;
    last_ai_index = ai_index;
    say(MH4U_LOG_INFO, line);
}

/* One line per distinct (current action, requested action, mode, caller), at most 64, to see
 * who calls the setter while the forced move runs. */
static void log_call(int id, int cur_c, int cur_i, int ai_c, int ai_i, uint32_t mode, uint32_t lr,
                     const char *what) {
    static uint32_t seen[64];
    static int nseen;
    const uint32_t key = ((uint32_t)cur_c << 24) ^ ((uint32_t)cur_i << 16) ^ ((uint32_t)ai_c << 8) ^
                         (uint32_t)ai_i ^ (mode << 28) ^ (lr * 2654435761u);
    for (int k = 0; k < nseen; k++) {
        if (seen[k] == key) {
            return;
        }
    }
    if (nseen == 64) {
        return;
    }
    seen[nseen++] = key;
    char line[200];
    snprintf(line, sizeof line, "monster %d: setter %d/%d -> %d/%d mode %u from 0x%08x: %s", id,
             cur_c, cur_i, ai_c, ai_i, (unsigned)mode, (unsigned)lr, what);
    say(MH4U_LOG_INFO, line);
}

/* uEnemy::setAction(this, category, index, mode). Overriding its arguments makes the game's
 * own setter initialize the forced action, which is what the dispatcher hook cannot do.
 *
 * The setter also (re)starts the action it is given, and the game calls it about twice a
 * frame while a monster changes action. Forcing every call restarted the move each time and
 * held it on its first frame (the maintainer's first R1p session, 2026-11-25). So the forced
 * pair is started only from another action: a call while the forced move runs is let through
 * unchanged when it asks for something else (the move ending), and skipped when it asks for
 * the forced pair again. With hold = 1 the next change after the move ends is forced again,
 * so the move loops. */
static void set_action(MH4UCall *call, void *user) {
    (void)user;
    uint32_t work;
    const int id = monster_work(call, &work);
    const int ai_category = (int)(host->reg(call, 1) & 0xffu);
    const int ai_index = (int)(host->reg(call, 2) & 0xffu);
    if (id < 0 || (monster_id >= 0 && id != monster_id) || (!hold && forced)) {
        host->call_original(call);
        return;
    }
    const int cur_category = (int)host->read8(call, work + WORK_CATEGORY);
    const int cur_index = (int)host->read8(call, work + WORK_INDEX);
    const uint32_t mode = host->reg(call, 3), lr = host->reg(call, 14);
    const int running = cur_category == category && cur_index == index;
    if (running && ai_category == category && ai_index == index) {
        log_call(id, cur_category, cur_index, ai_category, ai_index, mode, lr, "skipped (already running)");
        host->skip_original(call);
        return;
    }
    /* Once a monster has a target, its idle routine (0x0094dc84) runs every frame even while
     * the forced move is current, and returns the monster to idle (0/3, mode 2) before the AI
     * picks again: the move restarted each frame (second R1p session, 2026-11-25). While the
     * forced move runs, that return is skipped, and so is the AI's own next pick (third session:
     * letting the picks through mixed the AI's moves into the forced one), for at most END_SKIPS
     * calls in a row so a move that really ends cannot hang the monster. */
    if (running && end_skips < END_SKIPS) {
        end_skips++;
        log_call(id, cur_category, cur_index, ai_category, ai_index, mode, lr,
                 mode == 2 && ai_category == 0 && ai_index == 3 ? "skipped (idle return)" : "skipped (AI change)");
        host->skip_original(call);
        return;
    }
    end_skips = 0;
    if (running) {
        log_call(id, cur_category, cur_index, ai_category, ai_index, mode, lr, "let through (move ends)");
        host->call_original(call);
        return;
    }
    log_call(id, cur_category, cur_index, ai_category, ai_index, mode, lr, "forced");
    host->set_reg(call, 1, category);
    host->set_reg(call, 2, index);
    if (!logged || ai_category != last_ai_category || ai_index != last_ai_index) {
        log_force(id, ai_category, ai_index);
    }
    forced = 1;
    host->call_original(call);
}

/* Fallback: uEnemy::dispatchAction (vtable slot 44, 0x006e9cac). It writes the pair after
 * the AI's setter has reset the action, so it cannot make a move play; keep it only for a
 * library built before the setter hook existed. */
static void dispatch_action(MH4UCall *call, void *user) {
    (void)user;
    uint32_t work;
    const int id = monster_work(call, &work);
    if (id < 0) {
        host->call_original(call);
        return;
    }
    const int ai_category = (int)host->read8(call, work + WORK_CATEGORY);
    const int ai_index = (int)host->read8(call, work + WORK_INDEX);
    if ((monster_id < 0 || id == monster_id) && (hold || !forced)) {
        host->write8(call, work + WORK_CATEGORY, category);
        host->write8(call, work + WORK_INDEX, index);
        if (!logged || ai_category != last_ai_category || ai_index != last_ai_index) {
            log_force(id, ai_category, ai_index);
        }
        forced = 1;
    }
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
    via_setter = host->hook(host, HOOK_SETTER, set_action, NULL);
    if (!via_setter && !host->hook(host, HOOK_DISPATCH, dispatch_action, NULL)) {
        say(MH4U_LOG_ERROR, "neither the action setter nor the dispatcher is a hook point: "
                            "the code library needs building with this mod");
        return 0;
    }
    if (!via_setter) {
        say(MH4U_LOG_WARNING, "the action setter isn't a hook point: the code library needs "
                              "rebuilding; using the dispatcher, which cannot stop the AI "
                              "resetting the action each frame");
    }
    char line[200];
    const char *route = via_setter ? "the action setter" : "the dispatcher";
    if (monster_id < 0) {
        snprintf(line, sizeof line, "ready: forcing action %u/%u on every monster via %s",
                 (unsigned)category, (unsigned)index, route);
    } else {
        snprintf(line, sizeof line, "ready: forcing action %u/%u on monster %d via %s",
                 (unsigned)category, (unsigned)index, monster_id, route);
    }
    say(MH4U_LOG_INFO, line);
    return 1;
}
