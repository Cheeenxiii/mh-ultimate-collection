/*
 * test_rathian_3u.c: the 3U Rathian's module shell through the runtime, on a fake host, with
 * no game.
 *
 * The shell is what every action family shares (issue #265): the factory association that
 * records id 125's monster, the dispatch that tries the families and leaves an id no family
 * carries to MH4U, the ready line and the self-test. This test checks them; each action
 * family's call sequences are its own program under tests/rathian-3u/, which `make test`
 * discovers and builds (issue #268).
 *
 * Routing: 125 runs the module; an MH4U id and a registered id without a module fall through;
 * an id the module does not carry yet is logged once and falls through.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "rathian-3u/host.h"

/* The shell's frame only needs the engine to answer; the call sequences are the family tests'
 * business. */
static FakeResult noop_guest(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)fn;
    (void)r;
    (void)s;
    (void)user;
    return (FakeResult){0, 0.0f};
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = noop_guest;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    CHECK(fake_find_hook("uEnemyFactory::create") != NULL, "the factory isn't hooked");
    CHECK(fake_find_hook_last("uEnemy::dispatchAction") != NULL, "the dispatcher isn't hooked");

    /* The module's ready line names its own registry id, 125, and the self-test logs the
     * slice and its open item. */
    fake_frame();
    CHECK(fake_log_contains("ready: translating 22 of 3U Rathian's 191 actions on monster 125"),
          "the 3U module's ready line is missing");
    CHECK(fake_log_contains("selftest: 6 of the 191 actions"), "the self-test line is missing");
    CHECK(fake_log_contains("field map anchors"), "the field-map line is missing");
    CHECK(fake_log_contains("selftest: open: 0x008412cc"), "the open-item line is missing");

    /* ── routing: 125 runs the module; every other monster doesn't ── */
    const uint32_t enemy_125 = 0x1b0000u, work_125 = 0x1c0000u;
    spawn(enemy_125, work_125, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(enemy_125, work_125, 0, 0);     /* a translated id: category 0 falls to cat0 */
    CHECK(fake_skip_count == 1 && fake_original_count == 0,
          "the module's monster didn't run a translated action (%d original, %d skipped)",
          fake_original_count, fake_skip_count);

    /* An MH4U id has no module: 0/0 goes to the game's dispatcher. */
    const uint32_t enemy_1 = 0x1d0000u, work_1 = 0x1e0000u;
    spawn(enemy_1, work_1, 1, 1);
    fake_reset_calls();
    frame_with(enemy_1, work_1, 0, 0);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "an MH4U id isn't left to the game (%d calls, %d original, %d skipped)",
          fake_call_count, fake_original_count, fake_skip_count);

    /* A registered id without a module (127, Great Wroggi) has no action module either,
     * even when the game's work block happens to hold 125: the routing comes from the
     * factory, not the block. */
    const uint32_t enemy_127 = 0x1f0000u, work_127 = 0x200000u;
    spawn(enemy_127, work_127, MHUC_MONSTER_ID_GREAT_WROGGI_3U, 15);
    fake_mem_write8(work_127 + WORK_KIND, 125);
    fake_reset_calls();
    frame_with(enemy_127, work_127, 0, 0);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "a registered id without a module isn't left to the game (%d calls, %d original)",
          fake_call_count, fake_original_count);

    /* An id no family carries is logged once and left to MH4U's dispatcher. */
    fake_reset_calls();
    frame_with(enemy_125, work_125, 1, 0);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "a pending id (1/0) isn't left to the game");
    CHECK(fake_log_contains("pending action 1/0"), "the pending id isn't logged");
    fake_clear_log();
    frame_with(enemy_125, work_125, 1, 0);
    CHECK(!fake_log_contains("pending action 1/0"), "the pending id is logged more than once");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 125 routes to the module, the pending and foreign ids fall through, and the "
           "ready line and self-test are logged\n");
    return 0;
}
