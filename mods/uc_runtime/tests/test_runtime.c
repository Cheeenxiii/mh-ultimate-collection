/*
 * test_runtime.c: the runtime's id layer on a fake host, with no game.
 *
 * The id layer moved into the runtime must answer what it did in mods/monster_ids
 * (docs/checks.md#ported-monster-ids, check P1): the runtime asks the code library for the
 * same hook points, answers a registered id with its stand-in, passes MH4U's own ids through,
 * and puts a monster's own id back after a work-block reader.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../src/ids.h"
#include "../src/modules.h"
#include "fake_host.h"
#include "mh4u_plugin.h"

/* The id layer's hooks mod.json names, in the order src/ids.c registers them, then the module
 * side's two (the factory association and the action dispatcher). */
static const char *const expected_hooks[] = {
    "uEnemyFactory::create",
    "enemyData::load",
    "enemyData::get",
    "getCrown",
    "dropRecord::get",
    "dropRecord::getForMonster",
    "dropBaseA::getForMonster",
    "dropBaseB::getForMonster",
    "enemyResource::get",
    "enemyResource::load",
    "enemyResource::effectLists",
    "monsterIcon::get",
    "monsterIcon::put",
    "monsterListOrder::position",
    "message::getFormat",
    "message::getRecord",
    "message::getRecordById",
    "QuestFlow::startQuest",
    "uc_questTask",
    "aQuest::endSequence",
    "uc_dataPath",
    "notesList::pages",
    "notesList::page",
    "notesList::detail",
    "uEnemyFactory::create",
    "uEnemy::dispatchAction",
};

/* The Hunter's Notes list's tables, at their USA v1.3.0 addresses, and the test's own page
 * object and UI object (the game's are at 0x01090868 and on the notes UI object). */
#define ORDER_TABLE 0x00df35b0u
#define NOTES_PAGE 0x01090868u
#define NOTES_UI 0x01100000u

/* MH4U's monsterListOrder: `visible` rows have a name index, the rest have none (as rows 91
 * to 123 do). The runtime's fallback page count is ceil(visible/8). */
static void notes_guest(unsigned visible) {
    for (unsigned i = 0; i < 124; i++) {
        fake_mem_write8(ORDER_TABLE + i * 8u, i);
        fake_mem_write16(ORDER_TABLE + i * 8u + 4u, 0);
    }
    for (unsigned i = 0; i < visible; i++) {
        fake_mem_write16(ORDER_TABLE + i * 8u + 4u, i + 1u);
    }
}

static FakeCall *find_call(uint32_t fn) {
    for (int i = 0; i < fake_call_count; i++) {
        if (fake_calls[i].fn == fn) {
            return &fake_calls[i];
        }
    }
    return NULL;
}

/* The notes list: a page MH4U's rows cover runs unchanged; a page after them carries the
 * registered ids and their names; the detail maps a registered slot to its stand-in's
 * position and then answers the ported id's own name and notes. */
static void test_notes_list(void) {
    notes_guest(8);   /* 8 visible rows: one MH4U page, the 9th row's page is the mod's */
    FakeHook *walk = fake_find_hook("notesList::page");
    FakeHook *pages = fake_find_hook("notesList::pages");
    FakeHook *detail = fake_find_hook("notesList::detail");
    assert(walk && pages && detail);

    /* The runtime's first page: the registry's ids, in registry order. */
    fake_reset_calls();
    fake_regs[0] = 1;   /* MH4U's page 0 is the rows page; page 1 is the mod's */
    walk->fn(NULL, walk->user);
    assert(fake_skip_count == 1);
    assert(fake_original_count == 0);
    assert(fake_mem_read32(NOTES_PAGE + 0x30u) == MHUC_MONSTER_COUNT);
    for (int i = 0; i < MHUC_MONSTER_COUNT; i++) {
        assert(fake_mem_read32(NOTES_PAGE + 0x34u + (uint32_t)i * 4u) == mhuc_monster_ids[i].id);
    }
    assert(fake_log_contains("notes list: id 124 -> its own record"));

    /* MH4U's own page passes through: the page object keeps what the game's builder wrote. */
    fake_reset_calls();
    fake_mem_write32(NOTES_PAGE + 0x30u, 0x12345678u);
    fake_regs[0] = 0;
    walk->fn(NULL, walk->user);
    assert(fake_original_count == 1);
    assert(fake_mem_read32(NOTES_PAGE + 0x30u) == 0x12345678u);

    /* The page init: MH4U's page count stays the game's, plus one page for the mod's ids. */
    fake_reset_calls();
    fake_mem_write8(NOTES_UI + 0x1f7u, 1);
    fake_regs[0] = NOTES_UI;
    pages->fn(NULL, pages->user);
    assert(fake_original_count == 1);
    assert(fake_mem_read8(NOTES_UI + 0x1f7u) ==
           1u + (MHUC_MONSTER_COUNT + 7u) / 8u);

    /* A registered page slot: the game's detail runs for the stand-in's position, then the
     * two text objects are set to the ported id, so the message getters answer its text. */
    fake_reset_calls();
    fake_regs[0] = mhuc_monster_ids[0].id;
    detail->fn(NULL, detail->user);
    assert(fake_original_count == 1);
    assert(fake_regs[0] == 1);   /* stand-in 1's order position is row 1 */
    FakeCall *name = find_call(0x005a9184u);
    FakeCall *notes = find_call(0x005a8698u);
    assert(name && name->r1 == mhuc_monster_ids[0].id);
    assert(notes && notes->r1 == mhuc_monster_ids[0].id);
    assert(fake_log_contains("notes detail: id 124 -> its own record"));

    /* An MH4U position passes through, with no text of the mod's set. */
    fake_reset_calls();
    fake_regs[0] = 1;
    detail->fn(NULL, detail->user);
    assert(fake_original_count == 1);
    assert(fake_regs[0] == 1);
    assert(fake_call_count == 0);
}

int main(void) {
    fake_set_config("selftest", "0");
    fake_set_config("monster", "124");
    assert(fake_init() == 1);

    assert(fake_hook_count == (int)(sizeof expected_hooks / sizeof expected_hooks[0]));
    for (int i = 0; i < fake_hook_count; i++) {
        assert(strcmp(fake_hooks[i].name, expected_hooks[i]) == 0);
    }

    /* A registered id is answered with its stand-in; MH4U's own ids pass through. The id
     * layer's factory reader is the first one registered; the module's runs before it in the
     * real chain and is tested in test_module.c. */
    fake_reset_calls();
    fake_factory_stand_in = 1;
    fake_regs[1] = 124;
    FakeHook *factory = fake_find_hook("uEnemyFactory::create");
    factory->fn(NULL, factory->user);
    assert(fake_original_count == 1);
    assert(fake_regs[1] == 1);
    assert(fake_log_contains("factory: id 124 -> stand-in 1"));

    fake_reset_calls();
    fake_regs[1] = 1;
    factory->fn(NULL, factory->user);
    assert(fake_original_count == 1);
    assert(fake_regs[1] == 1);
    assert(fake_log_contains("factory: id 1 is MH4U's own; passed through"));

    /* The work-block readers swap the byte for the stand-in, run the game's function, and
     * put the monster's own id back: the block belongs to the game's own monster. */
    const uint32_t self = 0x00010000u;
    const uint32_t work = 0x00020000u;
    fake_mem_write32(self + 0xe28u, work);
    fake_mem_write8(work + 0x1c0u, 125u);
    fake_reset_calls();
    fake_probe_address = work + 0x1c0u;
    fake_regs[0] = self;
    FakeHook *drop = fake_find_hook("dropRecord::getForMonster");
    drop->fn(NULL, drop->user);
    assert(fake_probe_value == 1);
    assert(fake_mem_read8(work + 0x1c0u) == 125);
    assert(fake_log_contains("drop records: id 125 -> stand-in 1"));

    /* The generated table names the modules: 124's code is in src/monsters/rathian-gu.c and
     * 125's in src/monsters/rathian-3u.c; the other registered ids have none and their actions
     * stay with the game. */
    assert(MHUC_MODULE_COUNT == 4);
    assert(mhuc_modules[0].id == MHUC_MONSTER_ID_RATHIAN_GU);
    assert(mhuc_modules[0].ops != NULL);
    assert(mhuc_modules[1].id == MHUC_MONSTER_ID_RATHIAN_3U);
    assert(mhuc_modules[1].ops != NULL);
    for (int i = 2; i < MHUC_MODULE_COUNT; i++) {
        assert(mhuc_modules[i].ops == NULL);
    }

    test_notes_list();

    printf("ok: %d hooks, id 124 answered with stand-in 1, id 1 passed through, the module "
           "table names two modules, and the notes list adds the registered ids\n",
           fake_hook_count);
    return 0;
}
