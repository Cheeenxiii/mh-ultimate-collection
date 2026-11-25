/*
 * monster_ids.c: answers MH4U's monster-id-indexed tables for the ported monsters' ids.
 *
 * MH4U looks a monster up by id in tables that have 124 rows (0 to 123):
 * reference/README.md#mh4u-monster-tables lists them. Ids from 124 up come from the mod's
 * registry (data/ids/registry.csv, generated into src/ids.h): each one records the MH4U
 * monster id whose rows answer for it until the port ships the monster's own rows.
 *
 * The plugin wraps the readers of those tables (docs/decisions.md#0003, chosen way: hooks on
 * the readers, falling through to the game's function for MH4U's own ids). For a registered
 * id it calls the same function with the stand-in id; for 0 to 123 it calls it unchanged.
 *
 * Two reader shapes:
 *   - the id is an argument (factory, loadEnemyData, getCrown, the drops' getters, the
 *     resource and icon getters, the monster-list position): rewrite that register;
 *   - the id is read from the monster's data block (`this+0xe28` + 0x1c0): swap the byte for
 *     the stand-in, call the game's function, and put the real id back. The block is the
 *     game's own, so it must never be left holding the stand-in.
 *
 * What is not answered yet (left undone on #47): the name and notes text (`emName` and
 * `emExp` message N names id N; its reader is the message layer, not one per-monster getter),
 * and the Hunter's Notes list that walks all 124 rows (0x0061df4c). The stand-in also means
 * the spawned monster is MH4U's own (the data block keeps its own id byte) until #48/#49's
 * converted files and the port's own rows replace it.
 *
 * Settings (mod.json "config", the player's config.ini over it):
 *   selftest  "1": on the first frame, log what the reader hooks answer for each registered
 *             id and that MH4U's own ids pass through; for a headless check (docs/checks.md)
 *
 * Build: cc -shared -fPIC -I<fork>/include src/monster_ids.c -o monster_ids.so
 * Licence: GPL-3.0-or-later.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ids.h"
#include "mh4u_plugin.h"

/* A monster's data block is at this+0xe28, and its id at +0x1c0 (reference/README.md). */
#define ENEMY_WORK 0xe28u
#define WORK_ID 0x1c0u
/* The file path a stand-in's data is loaded from (reference/README.md#mh4u-monster-tables). */
#define ENEMY_DATA_PATH_INDEX 0x00efc268u

typedef struct HookInfo {
    const char *name;   /* what the reader is, for the log */
    unsigned reg;       /* the register that holds the id, or NO_REG for a work-block reader */
    int seen_new, seen_old;
} HookInfo;

#define NO_REG 0xffu

static const MH4UPluginHost *host;
static int selftest;

/* The stand-in rows for a registered id, or NULL. */
static const MhucMonsterId *find(uint32_t id) {
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        if (mhuc_monster_ids[i].id == id) {
            return &mhuc_monster_ids[i];
        }
    }
    return NULL;
}

static void say(int level, const char *text) {
    host->log(host, level, text);
}

/* One line the first time a reader answers a registered id, one the first time it passes an
 * MH4U id through: a full log would be thousands of lines. */
static void note(HookInfo *info, uint32_t id, uint32_t stand_in) {
    char line[160];
    if (!info->seen_new) {
        info->seen_new = 1;
        snprintf(line, sizeof line, "%s: id %u -> stand-in %u", info->name, (unsigned)id,
                 (unsigned)stand_in);
        say(MH4U_LOG_INFO, line);
    }
}

static void note_old(HookInfo *info, uint32_t id) {
    char line[160];
    if (!info->seen_old) {
        info->seen_old = 1;
        snprintf(line, sizeof line, "%s: id %u is MH4U's own; passed through", info->name,
                 (unsigned)id);
        say(MH4U_LOG_INFO, line);
    }
}

/* A reader that takes the id in a register: rewrite it for a registered id, leave MH4U's
 * alone, and run the game's function either way. */
static void argument_reader(MH4UCall *call, void *user) {
    HookInfo *info = user;
    const uint32_t id = host->reg(call, info->reg);
    const MhucMonsterId *row = find(id);
    if (row) {
        host->set_reg(call, info->reg, row->stand_in);
        note(info, id, row->stand_in);
    } else if (id <= MHUC_MONSTER_FIRST - 1) {
        note_old(info, id);
    }
    host->call_original(call);
}

/* A reader that reads the id from the monster's data block: swap the byte for the stand-in,
 * run the game's function, and give the block its id back (the block is shared with the
 * game's own monster). */
static void work_block_reader(MH4UCall *call, void *user) {
    HookInfo *info = user;
    const uint32_t self = host->reg(call, 0);
    const uint32_t work = self ? host->read32(call, self + ENEMY_WORK) : 0;
    if (!work) {
        host->call_original(call);
        return;
    }
    const uint32_t id = host->read8(call, work + WORK_ID);
    const MhucMonsterId *row = find(id);
    if (row) {
        host->write8(call, work + WORK_ID, row->stand_in);
        note(info, id, row->stand_in);
        host->call_original(call);
        host->write8(call, work + WORK_ID, id);
        return;
    }
    if (id <= MHUC_MONSTER_FIRST - 1) {
        note_old(info, id);
    }
    host->call_original(call);
}

static HookInfo h_factory = {"factory", 1, 0, 0};          /* uEnemyFactory::create(owner, id, a2, a3) */
static HookInfo h_load = {"data path", 1, 0, 0};           /* loadEnemyData(this, id, slot) */
static HookInfo h_data = {"enemy data", 1, 0, 0};          /* enemyData::get(id) */
static HookInfo h_crown = {"crown size", 0, 0, 0};         /* getCrown(id, size, out) */
static HookInfo h_droprec = {"drop records", 1, 0, 0};     /* dropRecord::get(id) */
static HookInfo h_droprec_m = {"drop records", NO_REG, 0, 0};  /* by the monster's own id */
static HookInfo h_dropa_m = {"drop base A", NO_REG, 0, 0};
static HookInfo h_dropb_m = {"drop base B", NO_REG, 0, 0};
static HookInfo h_res = {"resource index", 1, 0, 0};       /* enemyResource::get(id) */
static HookInfo h_resload = {"resource load", 2, 0, 0};    /* enemyResource::load(a, out, id) */
static HookInfo h_icon = {"monster icon", 1, 0, 0};        /* monsterIcon::get(id) */
static HookInfo h_icon_ui = {"monster icon", 2, 0, 0};     /* monsterIcon::put(_, out, id) */
static HookInfo h_order = {"list order", 0, 0, 0};         /* monsterListOrder::position(id) */

static HookInfo *const readers[] = {
    &h_factory, &h_load, &h_data, &h_crown, &h_droprec, &h_droprec_m, &h_dropa_m,
    &h_dropb_m, &h_res, &h_resload, &h_icon, &h_icon_ui, &h_order,
};

/* A guest C string, for the stand-in's data path in the self-test log. */
static int read_text(MH4UCall *call, uint32_t addr, char *out, size_t size) {
    size_t i;
    if (!addr || !size) {
        return 0;
    }
    for (i = 0; i + 1 < size; i++) {
        const uint8_t c = (uint8_t)host->read8(call, addr + (uint32_t)i);
        if (!c) {
            break;
        }
        out[i] = (char)c;
    }
    out[i] = '\0';
    return i != 0;
}

/* The path the game loads a stand-in monster's data from: enemyDataPathIndex[id] -> row ->
 * path string. Empty when the table or the path isn't there. */
static void stand_in_path(MH4UCall *call, uint32_t stand_in, char *out, size_t size) {
    const uint32_t row = host->read32(call, ENEMY_DATA_PATH_INDEX + stand_in * 4u);
    out[0] = '\0';
    if (row) {
        read_text(call, host->read32(call, row), out, size);
    }
}

/* Log what the readers answer, without a monster to load: the mapping itself, and the path
 * the stand-in's data comes from. The hooks use the same table, so this shows what they will
 * do for 124 up and that 0 to 123 are left alone. */
static void self_test(MH4UCall *call) {
    char ids[96], path[160], line[320];
    size_t used = 0;
    ids[0] = '\0';
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        const int n = snprintf(ids + used, sizeof ids - used, "%sid %u -> %u", i ? ", " : "",
                               (unsigned)mhuc_monster_ids[i].id,
                               (unsigned)mhuc_monster_ids[i].stand_in);
        if (n < 0 || (size_t)n >= sizeof ids - used) {
            break;
        }
        used += (size_t)n;
    }
    snprintf(line, sizeof line, "self-test: %d ported monster id(s): %s; ids 0..%u are MH4U's own",
             MHUC_MONSTER_COUNT, ids, (unsigned)(MHUC_MONSTER_FIRST - 1));
    say(MH4U_LOG_INFO, line);
    for (size_t i = 0; i < sizeof readers / sizeof readers[0]; i++) {
        if (readers[i] == &h_icon_ui) {
            continue;   /* the same table as the icon getter above; one line is enough */
        }
        if (readers[i] == &h_factory || readers[i] == &h_load) {
            stand_in_path(call, mhuc_monster_ids[0].stand_in, path, sizeof path);
            snprintf(line, sizeof line, "self-test: %s answers %s from %s; ids 0..%u pass through",
                     readers[i]->name, ids, path[0] ? path : "(no path)", (unsigned)(MHUC_MONSTER_FIRST - 1));
        } else {
            snprintf(line, sizeof line, "self-test: %s answers %s; ids 0..%u pass through",
                     readers[i]->name, ids, (unsigned)(MHUC_MONSTER_FIRST - 1));
        }
        say(MH4U_LOG_INFO, line);
    }
}

static int first_frame = 1;

static void frame(MH4UCall *call, void *user) {
    (void)user;
    if (!first_frame) {
        return;
    }
    first_frame = 0;
    if (selftest) {
        self_test(call);
    }
}

/* Hook name, address (USA v1.3.0), the reader's shape and its log label. */
static const struct {
    const char *hook;
    const char *address;
    MH4UHookFn fn;
    HookInfo *info;
} hooks[] = {
    {"uEnemyFactory::create", "0x006901f4", argument_reader, &h_factory},
    {"enemyData::load", "0x00689490", argument_reader, &h_load},
    {"enemyData::get", "0x0068882c", argument_reader, &h_data},
    {"getCrown", "0x0068877c", argument_reader, &h_crown},
    {"dropRecord::get", "0x00684b40", argument_reader, &h_droprec},
    {"dropRecord::getForMonster", "0x0092600c", work_block_reader, &h_droprec_m},
    {"dropBaseA::getForMonster", "0x00911f20", work_block_reader, &h_dropa_m},
    {"dropBaseB::getForMonster", "0x009357b4", work_block_reader, &h_dropb_m},
    {"enemyResource::get", "0x0068d8c8", argument_reader, &h_res},
    {"enemyResource::load", "0x00682ca0", argument_reader, &h_resload},
    {"monsterIcon::get", "0x00c0e800", argument_reader, &h_icon},
    {"monsterIcon::put", "0x00c0e164", argument_reader, &h_icon_ui},
    {"monsterListOrder::position", "0x0061dc58", argument_reader, &h_order},
};

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 1 || plugin_host->size < offsetof(MH4UPluginHost, alloc)) {
        return 0;
    }
    host = plugin_host;
#if MHUC_MONSTER_COUNT < 1
#error "the registry has no ported monster id: nothing to answer"
#endif
    const char *test = host->config(host, "selftest");
    selftest = test && strcmp(test, "1") == 0;
    int missing = 0;
    for (size_t i = 0; i < sizeof hooks / sizeof hooks[0]; i++) {
        if (!host->hook(host, hooks[i].hook, hooks[i].fn, hooks[i].info)) {
            char line[200];
            snprintf(line, sizeof line, "%s (0x%s) isn't a hook point: the code library needs "
                     "building with this mod", hooks[i].hook, hooks[i].address);
            say(MH4U_LOG_ERROR, line);
            missing++;
        }
    }
    if (missing == (int)(sizeof hooks / sizeof hooks[0])) {
        return 0;
    }
    if (missing) {
        say(MH4U_LOG_WARNING, "some readers aren't hook points: the code library needs rebuilding "
                              "with this mod; the rest answer");
    }
    if (!host->on_frame(host, frame, NULL)) {
        say(MH4U_LOG_WARNING, "no frame call point: the self-test can't run");
    }
    char line[200];
    snprintf(line, sizeof line, "ready: answering MH4U's monster tables for %d ported id(s), "
             "%u and up, standing in with MH4U's own rows", MHUC_MONSTER_COUNT,
             (unsigned)MHUC_MONSTER_FIRST);
    say(MH4U_LOG_INFO, line);
    return 1;
}
