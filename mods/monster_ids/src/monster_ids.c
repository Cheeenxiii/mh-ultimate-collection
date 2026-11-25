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
 * The id pool. The engine keeps a monster's id in one byte, so 124 to 223 are permanent and
 * 224 to 255 are lent per quest (docs/decisions.md#0003's amendment). A monster ported after
 * the permanent range is full has a registry id from 256 up, which a quest's u32 monster list
 * records. When a quest loads, the plugin finds the quest's loaded `.mib` among the quest
 * holder's quest-file resources, reads its large-monster waves, and rewrites each pooled id it
 * names in place to a free byte of 224 to 255. The reader hooks then answer that lent byte
 * with the pooled monster's rows, exactly as they answer a permanent id. The bytes are freed
 * when the quest ends (its end sequence sets the holder's status to 4), and are reused for the
 * next quest. No pooled monster ships yet, so the shipped registry has none.
 *
 * Finding the quest's data uses the engine's own quest holder, the same object the port's
 * quest-start workaround reads (MH4UltimateDC-fork port/src/hooks.cpp, QuestFlow::startQuest):
 * 0x00fbeffc is the holder, its loaded quest-file resources are at +0xe608 (+0xe610 their
 * count), and a resource's file contents at +0x64. The `.mib` header's large-monster list is
 * at +0x28 and its quest id at +0xc0 (specs/quest.md). All guest addresses here are MH4U USA
 * v1.3.0's.
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
 * The three readers of the record are answered with the built one:
 *   - `enemyResource::get` (0x0068d8c8) returns one field of the record; the hook returns the
 *     field of the built record instead;
 *   - `enemyResource::load` (0x00682ca0) and `enemyResource::effectLists` (0x00c0b830) read
 *     the whole record from `enemyResourceIndex` themselves, so the hook points the stand-in's
 *     table row at the built record for the call and puts the row back afterwards. A record
 *     is not relocated into the table: ids 124 and up have no row there, and the table ends
 *     where `enemyDataPaths` begins.
 *
 * The data path (`enemyDataPathIndex`, 0x00efc268) still answers with the stand-in's: the
 * ports ship no MH4U-format `.emd`/`.etd` yet (mods/monster_ids/README.md), so the stand-in's
 * data row is what loads their monster data.
 *
 * What is not answered yet (left undone): the name and notes text (`emName` and
 * `emExp` message N names id N; its reader is the message layer, not one per-monster getter)
 * and the Hunter's Notes list that walks all 124 rows (0x0061df4c). The stand-in also means
 * the spawned monster is MH4U's own (the data block keeps its own id byte) until #48/#49's
 * converted files and the port's own rows replace it.
 *
 * Settings (mod.json "config", the player's config.ini over it):
 *   selftest  "1": on the first frame, log what the reader hooks answer for each registered
 *             id, the paths the built resource records name, that MH4U's own ids pass
 *             through, and a pooled id lent and answered by a synthetic quest; for a headless
 *             check (docs/checks.md)
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

/* The quest holder and its loaded quest-file resources (MH4UltimateDC-fork
 * port/src/hooks.cpp, QuestFlow::startQuest; USA v1.3.0). */
#define QUEST_HOLDER 0x00fbeffcu
#define QUEST_HOLDER_TABLE 0xe604u       /* holder: u16 quest ids, 0-terminated */
#define QUEST_HOLDER_LIST 0xe608u        /* holder: the resources found for them */
#define QUEST_HOLDER_COUNT 0xe610u       /* holder: how many resources the list has */
#define QUEST_RESOURCE_BUFFER 0x64u      /* resource: its file contents */
#define QUEST_HOLDER_STATUS 0xad24u      /* u8: 3/7 complete, 4 the return, 5/6 failed/abandoned */
#define QUEST_FLOW_PARAMS 0x00edbe90u    /* [this]+0x9788: the quest 0x00b7c010 starts */
#define QUEST_FLOW_OFFSET 0x9788u
#define QUEST_FLOW_USE_ID 0x18u          /* u8: the flow carries a quest id */
#define QUEST_FLOW_ID 0x1au              /* u16, 0xffff when the id is an arena one */
#define QUEST_FLOW_WHICH 0x19u           /* u8: the arena quest, 3 of them */
#define QUEST_FLOW_RANKED 0x89u          /* u8: the other branch */
#define QUEST_FLOW_RANKED_ID 0x8cu
#define QUEST_FLOW_SELECTED_ID 0x3cu
#define QUEST_STATUS_RETURNED 4u

/* The .mib header and the large-monster waves (specs/quest.md). A file is a few KiB; the
 * bounds stop a malformed one from walking guest memory. */
#define MIB_MAX_SIZE 0x10000u
#define MIB_QUEST_ID 0x20u               /* data[header] + 0x20 is the u16 quest id */
#define MIB_LARGE_MONSTERS 0x28u
#define MIB_QUEST_ID_AT 0xc0u
#define MONSTER_DEF_SIZE 0x28u
#define MONSTER_LIST_END 0xffffffffu
#define MONSTER_MAX_WAVES 64u
#define MONSTER_MAX_DEFS 64u

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

/* One registered id's built resource record. The permanent ids' records come first in the
 * array, then the pooled ids'. */
typedef struct PortedRecord {
    uint32_t address;   /* guest address of the 0x2c record, 0 until it is built */
    int warned;         /* the first failure was logged already */
} PortedRecord;

static const MH4UPluginHost *host;
static int selftest;
static PortedRecord records[MHUC_MONSTER_COUNT + MHUC_POOLED_MONSTER_COUNT];

/* The pool: lent_row[i] is the pooled registry row a lent byte
 * MHUC_MONSTER_POOL_FIRST + i answers for, or -1 while the byte is free. */
static int lent_row[MHUC_MONSTER_POOL_SIZE];
static uint32_t active_quest;     /* the quest that holds the lent bytes, or 0 */
static uint32_t warned_quest;     /* the quest whose missing data was logged */
static int warned_no_data;

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
static HookInfo h_effects = {"effect lists", 2, 0, 0};     /* enemyResource::effectLists(_, _, id) */
static HookInfo h_icon = {"monster icon", 1, 0, 0};        /* monsterIcon::get(id) */
static HookInfo h_icon_ui = {"monster icon", 2, 0, 0};     /* monsterIcon::put(_, out, id) */
static HookInfo h_order = {"list order", 0, 0, 0};         /* monsterListOrder::position(id) */

static HookInfo *const readers[] = {
    &h_factory, &h_load, &h_data, &h_crown, &h_droprec, &h_droprec_m, &h_dropa_m,
    &h_dropb_m, &h_res, &h_resload, &h_effects, &h_icon, &h_icon_ui, &h_order,
};


/* The pool row a lent byte answers for, or -1. */
static int lent_index(uint32_t id) {
    if (id < MHUC_MONSTER_POOL_FIRST || id > MHUC_MONSTER_POOL_LAST) {
        return -1;
    }
    return lent_row[id - MHUC_MONSTER_POOL_FIRST];
}

/* The registered row an id answers from: a permanent id, or a byte the pool lent for the
 * active quest. `index` is the row's place in `records`. */
static const MhucMonsterId *lookup(uint32_t id, int *index) {
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        if (mhuc_monster_ids[i].id == id) {
            if (index) {
                *index = i;
            }
            return &mhuc_monster_ids[i];
        }
    }
    const int lent = lent_index(id);
    if (lent >= 0 && lent < MHUC_POOLED_MONSTER_COUNT) {
        if (index) {
            *index = MHUC_MONSTER_COUNT + lent;
        }
        return &mhuc_pooled_monster_ids[lent];
    }
    return NULL;
}

/* The pooled row with registry id `id`, or -1. */
static int pooled_row(uint32_t id) {
    for (int i = 0; i < MHUC_POOLED_MONSTER_COUNT; i++) {
        if (mhuc_pooled_monster_ids[i].id == id) {
            return i;
        }
    }
    return -1;
}

/* The byte row `row` already holds, or -1. */
static int held_byte(int row) {
    for (int i = 0; i < MHUC_MONSTER_POOL_SIZE; i++) {
        if (lent_row[i] == row) {
            return MHUC_MONSTER_POOL_FIRST + i;
        }
    }
    return -1;
}

/* The byte row `row` already holds, or a free one, or -1 when the pool is full. */
static int lent_byte(int row) {
    const int held = held_byte(row);
    if (held >= 0) {
        return held;
    }
    for (int i = 0; i < MHUC_MONSTER_POOL_SIZE; i++) {
        if (lent_row[i] < 0) {
            lent_row[i] = row;
            return MHUC_MONSTER_POOL_FIRST + i;
        }
    }
    return -1;
}

/* The stand-in of the first permanent row, for the self-test's reader lines. */
static uint32_t first_stand_in(void) {
    return MHUC_MONSTER_COUNT ? mhuc_monster_ids[0].stand_in : 0;
}

static void say(int level, const char *text) {
    host->log(host, level, text);
}

static void pool_clear(void) {
    for (int i = 0; i < MHUC_MONSTER_POOL_SIZE; i++) {
        lent_row[i] = -1;
    }
}

/* Frees every byte the active quest lent, and logs the quest that held them. */
static void free_quest(MH4UCall *call, int log_it) {
    (void)call;
    char line[200];
    char bytes[96];
    size_t used = 0;
    bytes[0] = '\0';
    for (int i = 0; i < MHUC_MONSTER_POOL_SIZE; i++) {
        if (lent_row[i] >= 0) {
            const int n = snprintf(bytes + used, sizeof bytes - used, "%s%u", used ? ", " : "",
                                   (unsigned)(MHUC_MONSTER_POOL_FIRST + i));
            if (n > 0 && (size_t)n < sizeof bytes - used) {
                used += (size_t)n;
            }
            lent_row[i] = -1;
        }
    }
    if (log_it && used) {
        snprintf(line, sizeof line, "quest %u ends: freed the pool byte(s) %s",
                 (unsigned)active_quest, bytes);
        say(MH4U_LOG_INFO, line);
    }
    active_quest = 0;
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
    const MhucMonsterId *row = lookup(id, NULL);
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
    const MhucMonsterId *row = lookup(id, NULL);
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
static uint32_t build_record(MH4UCall *call, const MhucMonsterId *row) {
    const uint32_t src = host->read32(call, ENEMY_RESOURCE_INDEX + row->stand_in * 4u);
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

/* Builds the record for one registered row, once (the heap may not be up on the first
 * frame). */
static void build_one(MH4UCall *call, const MhucMonsterId *row, PortedRecord *record) {
    if (record->address) {
        return;
    }
    record->address = build_record(call, row);
    if (!record->address && !record->warned) {
        char line[200];
        record->warned = 1;
        snprintf(line, sizeof line, "id %u: no resource record built from stand-in %u (no "
                 "row, no heap, or a path didn't fit)", (unsigned)row->id,
                 (unsigned)row->stand_in);
        say(MH4U_LOG_WARNING, line);
    }
}

/* Builds every record that isn't built yet. Returns how many are ready. */
static int build_records(MH4UCall *call) {
    int ready = 0;
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        build_one(call, &mhuc_monster_ids[i], &records[i]);
        if (records[i].address) {
            ready++;
        }
    }
    for (int i = 0; i < MHUC_POOLED_MONSTER_COUNT; i++) {
        PortedRecord *record = &records[MHUC_MONSTER_COUNT + i];
        build_one(call, &mhuc_pooled_monster_ids[i], record);
        if (record->address) {
            ready++;
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
    int which = -1;
    const MhucMonsterId *row = lookup(id, &which);
    if (row && records[which].address) {
        note_own(info, id);
        host->set_reg(call, 0,
                      host->read32(call, records[which].address + FIELD_MOTION_EFFECTS * 4u));
        host->skip_original(call);
        return;
    }
    if (row) {
        host->set_reg(call, 1, row->stand_in);
        note(info, id, row->stand_in);
    } else if (id <= MHUC_MONSTER_FIRST - 1) {
        note_old(info, id);
    }
    host->call_original(call);
}

/* A reader that reads the whole record from the table itself (the loader and the effect-list
 * reader, both with the id in r2). Point the stand-in's row at the ported id's record for the
 * call, run the game's function as the stand-in, and put the row back: ids 124 and up have no
 * row of their own to point anywhere. */
static void record_reader(MH4UCall *call, void *user) {
    HookInfo *info = user;
    const uint32_t id = host->reg(call, info->reg);
    int which = -1;
    const MhucMonsterId *row = lookup(id, &which);
    if (row && records[which].address) {
        const uint32_t row_at = ENEMY_RESOURCE_INDEX + (uint32_t)row->stand_in * 4u;
        const uint32_t was = host->read32(call, row_at);
        host->write32(call, row_at, records[which].address);
        host->set_reg(call, info->reg, row->stand_in);
        note_own(info, id);
        host->call_original(call);
        host->write32(call, row_at, was);
        return;
    }
    if (row) {
        host->set_reg(call, info->reg, row->stand_in);
        note(info, id, row->stand_in);
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

/* The quest id 0x00b7c010 is about to start, read the way the port's StartQuest does
 * (MH4UltimateDC-fork port/src/hooks.cpp). */
static uint32_t next_quest_id(MH4UCall *call) {
    const uint32_t base = host->read32(call, QUEST_FLOW_PARAMS);
    if (!base) {
        return 0;
    }
    const uint32_t p = base + QUEST_FLOW_OFFSET;
    if (host->read8(call, p + QUEST_FLOW_USE_ID)) {
        const uint32_t id = host->read16(call, p + QUEST_FLOW_ID);
        if (id != 0xffff) {
            return id;
        }
        const uint32_t which = host->read8(call, p + QUEST_FLOW_WHICH);
        return which < 3 ? 0xafc8 + which : 0;
    }
    return host->read8(call, p + QUEST_FLOW_RANKED) ? host->read16(call, p + QUEST_FLOW_RANKED_ID)
                                                    : host->read16(call, p + QUEST_FLOW_SELECTED_ID);
}

/* The `.mib` data of the quest `id` among the holder's loaded quest-file resources, or 0. */
static uint32_t quest_data(MH4UCall *call, uint32_t id) {
    const uint32_t holder = host->read32(call, QUEST_HOLDER);
    if (!holder) {
        return 0;
    }
    const uint32_t list = host->read32(call, holder + QUEST_HOLDER_LIST);
    const uint32_t count = host->read32(call, holder + QUEST_HOLDER_COUNT);
    if (!list || count > 4096u) {
        return 0;
    }
    for (uint32_t i = 0; i < count; i++) {
        const uint32_t res = host->read32(call, list + i * 4u);
        if (!res) {
            continue;
        }
        const uint32_t data = host->read32(call, res + QUEST_RESOURCE_BUFFER);
        if (!data) {
            continue;
        }
        const uint32_t header = host->read32(call, data);
        if (header >= MIB_MAX_SIZE) {
            continue;
        }
        if (host->read16(call, data + header + MIB_QUEST_ID) == id) {
            return data;
        }
    }
    return 0;
}

/* Rewrites the pooled ids in the quest's large-monster waves to the bytes the pool lends
 * them. The first call for a quest starts its pool; a later call for the same quest (the
 * port rebuilds the quest list when a file is late) reuses the bytes it already lent. */
static int lend_quest(MH4UCall *call, uint32_t quest, uint32_t data) {
    if (active_quest != quest) {
        free_quest(call, 1);
        active_quest = quest;
    }
    const uint32_t waves = host->read32(call, data + MIB_LARGE_MONSTERS);
    if (!waves || waves >= MIB_MAX_SIZE) {
        return 0;
    }
    int lent = 0;
    char line[200];
    for (uint32_t w = 0; w < MONSTER_MAX_WAVES; w++) {
        const uint32_t wave = host->read32(call, data + waves + w * 4u);
        if (!wave) {
            break;
        }
        if (wave >= MIB_MAX_SIZE) {
            return lent;
        }
        for (uint32_t d = 0; d < MONSTER_MAX_DEFS; d++) {
            const uint32_t at = data + wave + d * MONSTER_DEF_SIZE;
            const uint32_t id = host->read32(call, at);
            if (id == MONSTER_LIST_END) {
                break;
            }
            if (id < MHUC_REGISTRY_POOL_FIRST) {
                continue;
            }
            const int row = pooled_row(id);
            if (row < 0) {
                snprintf(line, sizeof line, "quest %u names id %u, which isn't a pooled "
                         "monster in the registry", (unsigned)quest, (unsigned)id);
                say(MH4U_LOG_WARNING, line);
                continue;
            }
            const int already = held_byte(row);
            const int before = lent_byte(row);
            if (before < 0) {
                snprintf(line, sizeof line, "quest %u: no free pool byte for pooled id %u",
                         (unsigned)quest, (unsigned)id);
                say(MH4U_LOG_WARNING, line);
                continue;
            }
            host->write32(call, at, (uint32_t)before);
            if (already < 0) {
                snprintf(line, sizeof line, "quest %u: pooled id %u -> lent %d",
                         (unsigned)quest, (unsigned)id, before);
                say(MH4U_LOG_INFO, line);
            }
            lent++;
        }
    }
    return lent;
}

/* QuestFlow::startQuest: lend the pooled monsters the starting quest names before the game
 * copies its data out of the quest list. */
static void quest_start_reader(MH4UCall *call, void *user) {
    (void)user;
    const uint32_t id = next_quest_id(call);
    if (id) {
        const uint32_t data = quest_data(call, id);
        if (data) {
            if (MHUC_POOLED_MONSTER_COUNT > 0) {
                lend_quest(call, id, data);
            }
        } else if (MHUC_POOLED_MONSTER_COUNT > 0 && (warned_quest != id || !warned_no_data)) {
            char line[200];
            warned_quest = id;
            warned_no_data = 1;
            snprintf(line, sizeof line, "quest %u: its loaded .mib wasn't found among the "
                     "quest holder's resources; a pooled monster in it keeps its registry id",
                     (unsigned)id);
            say(MH4U_LOG_WARNING, line);
        }
    }
    host->call_original(call);
}

/* aQuest::endSequence: once it sets the holder's status to 4 the quest is over and the pool
 * bytes can be lent again. It runs every frame of the wait before the return, so this frees
 * only when that final status is set. */
static void quest_end_reader(MH4UCall *call, void *user) {
    (void)user;
    host->call_original(call);
    if (!active_quest) {
        return;
    }
    const uint32_t holder = host->read32(call, QUEST_HOLDER);
    if (holder && host->read8(call, holder + QUEST_HOLDER_STATUS) == QUEST_STATUS_RETURNED) {
        free_quest(call, 1);
    }
}

/* A synthetic quest that names the first pooled id, to show the lend, the answer and the free
 * without a shipped pooled monster (docs/checks.md, check P1). Its .mib is laid out as
 * specs/quest.md describes: a large-monster list at +0x28 holding one wave, and in that wave
 * one 0x28-byte monster definition, ended by 0xffffffff. */
static void self_test_pool(MH4UCall *call) {
    char line[400];
    if (MHUC_POOLED_MONSTER_COUNT < 1) {
        say(MH4U_LOG_INFO, "self-test: the pool 224..255 is unused: no pooled monster id is "
                           "registered");
        return;
    }
    const MhucMonsterId *row = &mhuc_pooled_monster_ids[0];
    const uint32_t data = host->alloc(call, 0x100u, 4);
    if (!data) {
        say(MH4U_LOG_WARNING, "self-test: no guest memory to build a synthetic quest");
        return;
    }
    host->write32(call, data, 0xa0u);                         /* header: flags at 0xa0 */
    host->write32(call, data + MIB_LARGE_MONSTERS, 0x80u);    /* one wave, at 0x80 */
    host->write32(call, data + 0x80u, 0x88u);                 /* the wave's first definition */
    host->write32(call, data + 0x84u, 0u);                    /* end of the wave list */
    host->write32(call, data + 0x88u, row->id);               /* the monster's id */
    host->write32(call, data + 0x8cu, 1u);                    /* spawn count */
    host->write32(call, data + 0x88u + MONSTER_DEF_SIZE, MONSTER_LIST_END);
    host->write16(call, data + MIB_QUEST_ID_AT, 60001u);
    const int lent = lend_quest(call, 60001u, data);
    const uint32_t rewritten = host->read32(call, data + 0x88u);
    int which = -1;
    const MhucMonsterId *left = lookup(rewritten, &which);
    if (lent == 1 && left && which == MHUC_MONSTER_COUNT && records[which].address) {
        snprintf(line, sizeof line, "self-test: quest 60001 names pooled id %u; lent %u; the "
                 "readers answer %u -> pooled id %u, stand-in %u, its own record",
                 (unsigned)row->id, (unsigned)rewritten, (unsigned)rewritten, (unsigned)row->id,
                 (unsigned)left->stand_in);
        say(MH4U_LOG_INFO, line);
        free_quest(call, 1);
        if (lookup(rewritten, NULL)) {
            say(MH4U_LOG_WARNING, "self-test: the lent byte is still held after the quest");
        } else {
            snprintf(line, sizeof line, "self-test: the quest ended, so byte %u is free again",
                     (unsigned)rewritten);
            say(MH4U_LOG_INFO, line);
        }
    } else {
        snprintf(line, sizeof line, "self-test: the synthetic quest lent %d byte(s); the "
                 "monster list holds id %u afterwards", lent, (unsigned)rewritten);
        say(MH4U_LOG_ERROR, line);
        free_quest(call, 1);
    }
    host->free(call, data);
}

/* Log what the readers answer, without a monster to load: the mapping itself, the paths the
 * built resource records name, the path the stand-in's data comes from, and the pool lent to
 * a synthetic quest. The hooks use the same records, so this shows what they will do for 124
 * up, for a lent pooled byte, and that 0 to 123 are left alone. */
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
    snprintf(line, sizeof line, "self-test: %d permanent and %d pooled registered monster id(s): "
             "%s; ids 0..%u are MH4U's own", MHUC_MONSTER_COUNT, MHUC_POOLED_MONSTER_COUNT, ids,
             (unsigned)(MHUC_MONSTER_FIRST - 1));
    say(MH4U_LOG_INFO, line);
    for (int i = 0; i < MHUC_MONSTER_COUNT + MHUC_POOLED_MONSTER_COUNT; i++) {
        const MhucMonsterId *row = i < MHUC_MONSTER_COUNT ? &mhuc_monster_ids[i]
                                                         : &mhuc_pooled_monster_ids[i - MHUC_MONSTER_COUNT];
        if (!records[i].address) {
            snprintf(line, sizeof line, "self-test: id %u has no resource record: its paths "
                     "would come from stand-in %u", (unsigned)row->id, (unsigned)row->stand_in);
            say(MH4U_LOG_WARNING, line);
            continue;
        }
        record_paths(call, records[i].address, texts, sizeof texts);
        snprintf(line, sizeof line, "self-test: id %u resource record at 0x%08x, built from "
                 "stand-in %u, names: %s", (unsigned)row->id, (unsigned)records[i].address,
                 (unsigned)row->stand_in, texts);
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
        } else if (readers[i] == &h_resload || readers[i] == &h_effects) {
            snprintf(line, sizeof line, "self-test: %s answers a ported id with its own record, "
                     "read as stand-in %u; ids 0..%u pass through", readers[i]->name,
                     (unsigned)first_stand_in(), (unsigned)(MHUC_MONSTER_FIRST - 1));
        } else if (readers[i] == &h_factory || readers[i] == &h_load) {
            stand_in_path(call, first_stand_in(), path, sizeof path);
            snprintf(line, sizeof line, "self-test: %s answers %s from %s; ids 0..%u pass through",
                     readers[i]->name, ids, path[0] ? path : "(no path)",
                     (unsigned)(MHUC_MONSTER_FIRST - 1));
        } else {
            snprintf(line, sizeof line, "self-test: %s answers %s; ids 0..%u pass through",
                     readers[i]->name, ids, (unsigned)(MHUC_MONSTER_FIRST - 1));
        }
        say(MH4U_LOG_INFO, line);
    }
    self_test_pool(call);
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
    {"enemyResource::load", "0x00682ca0", record_reader, &h_resload},
    {"enemyResource::effectLists", "0x00c0b830", record_reader, &h_effects},
    {"monsterIcon::get", "0x00c0e800", argument_reader, &h_icon},
    {"monsterIcon::put", "0x00c0e164", argument_reader, &h_icon_ui},
    {"monsterListOrder::position", "0x0061dc58", argument_reader, &h_order},
    {"QuestFlow::startQuest", "0x00b7c010", quest_start_reader, NULL},
    {"aQuest::endSequence", "0x0065a378", quest_end_reader, NULL},
};

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 1 || plugin_host->size < offsetof(MH4UPluginHost, alloc)) {
        return 0;
    }
    host = plugin_host;
#if MHUC_MONSTER_COUNT + MHUC_POOLED_MONSTER_COUNT < 1
#error "the registry has no ported monster id: nothing to answer"
#endif
    pool_clear();
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
    char line[220];
    snprintf(line, sizeof line, "ready: answering MH4U's monster tables for %d permanent and %d "
             "pooled id(s), %u and up, lending %u..%u per quest",
             MHUC_MONSTER_COUNT, MHUC_POOLED_MONSTER_COUNT, (unsigned)MHUC_MONSTER_FIRST,
             (unsigned)MHUC_MONSTER_POOL_FIRST, (unsigned)MHUC_MONSTER_POOL_LAST);
    say(MH4U_LOG_INFO, line);
    return 1;
}
