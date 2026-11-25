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
 * The resource record. MH4U loads a monster's own files from the paths in the record that
 * `enemyResourceIndex[id]` (0x00efbd08) points to. The record is 0x2c bytes: eleven pointers
 * to path slots, where a slot holds 0 or a pointer to a path string. Its fields are the
 * model (+0x00), the six motion lists (+0x04), the camera (+0x08), a second motion list
 * (+0x0c), the tail model (+0x10), the motion effects (+0x14), an unused field (+0x18), the
 * sound (+0x1c), four extra paths (+0x20, the command/EMC at +0x20 slot 3), the effect lists
 * (+0x24) and a second effect list (+0x28). The stand-in's record names `enemy\em001\...`
 * paths; answering a ported id with it would load MH4U's own files. So on the first frame the
 * plugin builds, for every registered id, a record of its own from the stand-in's: every path
 * is copied and its monster-id token rewritten to the ported id (`em001` -> `em124`, and the
 * camera's `e001` -> `e124`), so the port's files live under its own id's paths. The record,
 * its slots and its strings are guest memory from the game's own heap (alloc, ABI 2).
 *
 * The two readers of the record are answered with the built one:
 *   - `enemyResource::get` (0x0068d8c8) returns one field of the record; the hook returns the
 *     field of the built record instead;
 *   - `enemyResource::load` (0x00682ca0) reads the whole record from `enemyResourceIndex`
 *     itself, so the hook points the stand-in's table row at the built record for the call and
 *     puts the row back afterwards. A record is not relocated into the table: ids 124 and up
 *     have no row there, and the table ends where `enemyDataPaths` begins.
 *
 * The data path (`enemyDataPathIndex`, 0x00efc268) still answers with the stand-in's: the
 * ports ship no MH4U-format `.emd`/`.etd` yet (mods/monster_ids/README.md), so the stand-in's
 * data row is what loads their monster data.
 *
 * What is not answered yet (left undone): the name and notes text (`emName` and
 * `emExp` message N names id N; its reader is the message layer, not one per-monster getter),
 * the Hunter's Notes list that walks all 124 rows (0x0061df4c), and the third reader of
 * `enemyResourceIndex` (0x00c0b830, which reads the record's effect lists and is called with
 * the spawned monster's own id after `enemyResource::load`). The stand-in also means the
 * spawned monster is MH4U's own (the data block keeps its own id byte) until #48/#49's
 * converted files and the port's own rows replace it.
 *
 * Settings (mod.json "config", the player's config.ini over it):
 *   selftest  "1": on the first frame, log what the reader hooks answer for each registered
 *             id, the paths the built resource record names, and that MH4U's own ids pass
 *             through; for a headless check (docs/checks.md)
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
/* The per-id resource records: 124 pointers to 0x2c-byte records (reference/README.md). */
#define ENEMY_RESOURCE_INDEX 0x00efbd08u

/* The record's shape, from its readers: field_slots[f] path slots at offset f*4, and the
 * second motion list (+0x0c) ends at its first empty slot instead of a fixed count. */
#define RECORD_SIZE 0x2cu
#define RECORD_FIELDS 11u
#define RECORD_SLOTS_MAX 6u
#define PATH_MAX 128u
#define FIELD_MOTION_EFFECTS 5u   /* +0x14, what enemyResource::get returns */

static const uint8_t field_slots[RECORD_FIELDS] = {1, 6, 1, 6, 2, 2, 1, 1, 4, 1, 1};
static const uint8_t field_ends_at_null[RECORD_FIELDS] = {0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0};

typedef struct HookInfo {
    const char *name;   /* what the reader is, for the log */
    unsigned reg;       /* the register that holds the id, or NO_REG for a work-block reader */
    int seen_new, seen_old;
} HookInfo;

#define NO_REG 0xffu

/* One registered id's built resource record. */
typedef struct PortedRecord {
    uint32_t address;   /* guest address of the 0x2c record, 0 until it is built */
    int warned;         /* the first failure was logged already */
} PortedRecord;

static const MH4UPluginHost *host;
static int selftest;
static PortedRecord records[MHUC_MONSTER_COUNT];

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


/* The row for a registered id, or NULL. */
static const MhucMonsterId *find(uint32_t id) {
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        if (mhuc_monster_ids[i].id == id) {
            return &mhuc_monster_ids[i];
        }
    }
    return NULL;
}

/* The row index for a registered id, or -1. */
static int find_index(uint32_t id) {
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        if (mhuc_monster_ids[i].id == id) {
            return i;
        }
    }
    return -1;
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

/* The same, for a reader answered with the ported id's own rows instead of the stand-in's. */
static void note_own(HookInfo *info, uint32_t id) {
    char line[160];
    if (!info->seen_new) {
        info->seen_new = 1;
        snprintf(line, sizeof line, "%s: id %u -> its own record", info->name, (unsigned)id);
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

/* A guest C string. */
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

static int is_digit(uint8_t c) {
    return c >= '0' && c <= '9';
}

/* A stand-in path with the ported id in it: every `emNNN` and camera `eNNN` token becomes the
 * ported id's (`em001` -> `em124`, `e001_cam` -> `e124_cam`); other numbers, like an effect
 * list's trailing `_000`, stay. Returns the length, or -1 when it doesn't fit. */
static int rewrite_path(MH4UCall *call, uint32_t src, unsigned id, char *out, size_t size) {
    size_t n = 0;
    for (uint32_t i = 0; i < 256; i++) {
        const uint8_t c = (uint8_t)host->read8(call, src + i);
        if (!c) {
            break;
        }
        const uint8_t next = (uint8_t)host->read8(call, src + i + 1);
        if (c == 'e' && next == 'm'
            && is_digit((uint8_t)host->read8(call, src + i + 2))
            && is_digit((uint8_t)host->read8(call, src + i + 3))
            && is_digit((uint8_t)host->read8(call, src + i + 4))) {
            if (n + 6 > size) {
                return -1;
            }
            n += (size_t)snprintf(out + n, size - n, "em%03u", id);
            i += 4;
        } else if (c == 'e'
                   && is_digit(next)
                   && is_digit((uint8_t)host->read8(call, src + i + 2))
                   && is_digit((uint8_t)host->read8(call, src + i + 3))) {
            if (n + 5 > size) {
                return -1;
            }
            n += (size_t)snprintf(out + n, size - n, "e%03u", id);
            i += 3;
        } else {
            if (n + 2 > size) {
                return -1;
            }
            out[n++] = (char)c;
        }
    }
    out[n] = '\0';
    return (int)n;
}

/* Room for one record's path strings while it is built. */
static char staged[RECORD_FIELDS][RECORD_SLOTS_MAX][PATH_MAX];

/* Builds one registered id's record from its stand-in's in guest memory: the same fields and
 * slots, every path rewritten to the ported id. Returns the record's guest address, or 0. */
static uint32_t build_record(MH4UCall *call, int which) {
    const MhucMonsterId *row = &mhuc_monster_ids[which];
    const uint32_t src = host->read32(call, ENEMY_RESOURCE_INDEX + (uint32_t)row->stand_in * 4u);
    if (!src) {
        return 0;
    }
    size_t words = 0, text = 0;
    memset(staged, 0, sizeof staged);
    for (unsigned f = 0; f < RECORD_FIELDS; f++) {
        const uint32_t field = host->read32(call, src + f * 4u);
        if (!field) {
            continue;
        }
        words += field_slots[f];
        for (unsigned k = 0; k < field_slots[f]; k++) {
            const uint32_t slot = host->read32(call, field + k * 4u);
            if (!slot) {
                if (field_ends_at_null[f]) {
                    break;
                }
                continue;
            }
            if (rewrite_path(call, slot, row->id, staged[f][k], PATH_MAX) < 0) {
                return 0;
            }
            text += strlen(staged[f][k]) + 1;
        }
    }
    const uint32_t block = host->alloc(call, RECORD_SIZE + (uint32_t)words * 4u + (uint32_t)text,
                                       4);
    if (!block) {
        return 0;
    }
    uint32_t slot_at = block + RECORD_SIZE;
    uint32_t char_at = block + RECORD_SIZE + (uint32_t)words * 4u;
    for (unsigned f = 0; f < RECORD_FIELDS; f++) {
        const uint32_t field = host->read32(call, src + f * 4u);
        if (!field) {
            host->write32(call, block + f * 4u, 0);
            continue;
        }
        host->write32(call, block + f * 4u, slot_at);
        for (unsigned k = 0; k < field_slots[f]; k++) {
            if (!staged[f][k][0]) {
                host->write32(call, slot_at + k * 4u, 0);
                continue;
            }
            host->write32(call, slot_at + k * 4u, char_at);
            for (const char *p = staged[f][k];; p++) {
                host->write8(call, char_at++, (uint8_t)*p);
                if (!*p) {
                    break;
                }
            }
        }
        slot_at += field_slots[f] * 4u;
    }
    return block;
}

/* Builds every record that isn't built yet (the heap may not be up on the first frame).
 * Returns how many are ready. */
static int build_records(MH4UCall *call) {
    int ready = 0;
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        if (!records[i].address) {
            records[i].address = build_record(call, i);
        }
        if (records[i].address) {
            ready++;
        } else if (!records[i].warned) {
            char line[200];
            records[i].warned = 1;
            snprintf(line, sizeof line, "id %u: no resource record built from stand-in %u (no "
                     "row, no heap, or a path didn't fit)", (unsigned)mhuc_monster_ids[i].id,
                     (unsigned)mhuc_monster_ids[i].stand_in);
            say(MH4U_LOG_WARNING, line);
        }
    }
    return ready;
}

/* The paths a built record names, read back from guest memory for the self-test. */
static void record_paths(MH4UCall *call, uint32_t record, char *out, size_t size) {
    char path[PATH_MAX];
    size_t used = 0;
    out[0] = '\0';
    for (unsigned f = 0; f < RECORD_FIELDS; f++) {
        const uint32_t field = host->read32(call, record + f * 4u);
        if (!field) {
            continue;
        }
        for (unsigned k = 0; k < field_slots[f]; k++) {
            const uint32_t slot = host->read32(call, field + k * 4u);
            if (!slot || !read_text(call, slot, path, sizeof path)) {
                continue;
            }
            const int n = snprintf(out + used, size - used, "%s%s", used ? "; " : "", path);
            if (n < 0 || (size_t)n >= size - used) {
                return;
            }
            used += (size_t)n;
        }
    }
}

/* The resource record's getter returns one field of the record: answer a registered id with
 * its own record's field, read from the record built on the first frame. */
static void resource_get_reader(MH4UCall *call, void *user) {
    HookInfo *info = user;
    const uint32_t id = host->reg(call, 1);
    const int which = find_index(id);
    if (which >= 0 && records[which].address) {
        note_own(info, id);
        host->set_reg(call, 0,
                      host->read32(call, records[which].address + FIELD_MOTION_EFFECTS * 4u));
        host->skip_original(call);
        return;
    }
    if (which >= 0) {
        host->set_reg(call, 1, mhuc_monster_ids[which].stand_in);
        note(info, id, mhuc_monster_ids[which].stand_in);
    } else if (id <= MHUC_MONSTER_FIRST - 1) {
        note_old(info, id);
    }
    host->call_original(call);
}

/* The resource loader reads the whole record from the table itself. Point the stand-in's row
 * at the ported id's record for the call, run the game's loader as the stand-in, and put the
 * row back: ids 124 and up have no row of their own to point anywhere. */
static void resource_load_reader(MH4UCall *call, void *user) {
    HookInfo *info = user;
    const uint32_t id = host->reg(call, 2);
    const int which = find_index(id);
    if (which >= 0 && records[which].address) {
        const uint32_t row_at =
            ENEMY_RESOURCE_INDEX + (uint32_t)mhuc_monster_ids[which].stand_in * 4u;
        const uint32_t was = host->read32(call, row_at);
        host->write32(call, row_at, records[which].address);
        host->set_reg(call, 2, mhuc_monster_ids[which].stand_in);
        note_own(info, id);
        host->call_original(call);
        host->write32(call, row_at, was);
        return;
    }
    if (which >= 0) {
        host->set_reg(call, 2, mhuc_monster_ids[which].stand_in);
        note(info, id, mhuc_monster_ids[which].stand_in);
    } else if (id <= MHUC_MONSTER_FIRST - 1) {
        note_old(info, id);
    }
    host->call_original(call);
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

/* Log what the readers answer, without a monster to load: the mapping itself, the paths the
 * built resource records name, and the path the stand-in's data comes from. The hooks use the
 * same records, so this shows what they will do for 124 up and that 0 to 123 are left alone. */
static void self_test(MH4UCall *call) {
    char ids[96], path[160], line[640], texts[512];
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
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        if (!records[i].address) {
            snprintf(line, sizeof line, "self-test: id %u has no resource record: its paths "
                     "would come from stand-in %u", (unsigned)mhuc_monster_ids[i].id,
                     (unsigned)mhuc_monster_ids[i].stand_in);
            say(MH4U_LOG_WARNING, line);
            continue;
        }
        record_paths(call, records[i].address, texts, sizeof texts);
        snprintf(line, sizeof line, "self-test: id %u resource record at 0x%08x, built from "
                 "stand-in %u, names: %s", (unsigned)mhuc_monster_ids[i].id,
                 (unsigned)records[i].address, (unsigned)mhuc_monster_ids[i].stand_in, texts);
        say(MH4U_LOG_INFO, line);
    }
    for (size_t i = 0; i < sizeof readers / sizeof readers[0]; i++) {
        if (readers[i] == &h_icon_ui) {
            continue;   /* the same table as the icon getter above; one line is enough */
        }
        if (readers[i] == &h_res) {
            snprintf(line, sizeof line, "self-test: %s answers a ported id with its own "
                     "record's +0x%x field; ids 0..%u pass through", readers[i]->name,
                     (unsigned)(FIELD_MOTION_EFFECTS * 4u),
                     (unsigned)(MHUC_MONSTER_FIRST - 1));
        } else if (readers[i] == &h_resload) {
            snprintf(line, sizeof line, "self-test: %s answers a ported id with its own record, "
                     "read as stand-in %u; ids 0..%u pass through", readers[i]->name,
                     (unsigned)(MHUC_MONSTER_COUNT ? mhuc_monster_ids[0].stand_in : 0),
                     (unsigned)(MHUC_MONSTER_FIRST - 1));
        } else if (readers[i] == &h_factory || readers[i] == &h_load) {
            stand_in_path(call, mhuc_monster_ids[0].stand_in, path, sizeof path);
            snprintf(line, sizeof line, "self-test: %s answers %s from %s; ids 0..%u pass through",
                     readers[i]->name, ids, path[0] ? path : "(no path)",
                     (unsigned)(MHUC_MONSTER_FIRST - 1));
        } else {
            snprintf(line, sizeof line, "self-test: %s answers %s; ids 0..%u pass through",
                     readers[i]->name, ids, (unsigned)(MHUC_MONSTER_FIRST - 1));
        }
        say(MH4U_LOG_INFO, line);
    }
}

static int first_frame = 1;
static int logged;

static void frame(MH4UCall *call, void *user) {
    (void)user;
    if (!first_frame && logged) {
        return;
    }
    first_frame = 0;
    build_records(call);
    if (selftest && !logged) {
        logged = 1;
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
    {"enemyResource::get", "0x0068d8c8", resource_get_reader, &h_res},
    {"enemyResource::load", "0x00682ca0", resource_load_reader, &h_resload},
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
             "%u and up, with their own resource record and the stand-in's other rows",
             MHUC_MONSTER_COUNT, (unsigned)MHUC_MONSTER_FIRST);
    say(MH4U_LOG_INFO, line);
    return 1;
}
