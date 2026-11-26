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
    "uEnemyFactory::create",
    "uEnemy::dispatchAction",
};

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

    printf("ok: %d hooks, id 124 answered with stand-in 1, id 1 passed through, and the module "
           "table names two modules\n", fake_hook_count);
    return 0;
}
