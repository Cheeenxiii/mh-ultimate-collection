/*
 * test_module.c: GU Rathian's module shell through the runtime, on a fake host, with no game.
 *
 * The shell is what every action family shares: the factory association that records id 124's
 * monster, the dispatch that tries the generated family list and leaves a pair no family
 * carries to MH4U, the action log, the ready line and the self-test. This test checks them;
 * each action family's call sequences are its own program under tests/rathian-gu/, which
 * `make test` discovers and builds as tests/family-gu-<family>.
 *
 * Routing: 124 runs the module; an MH4U id and a registered id without a module fall through;
 * a shared id the module does not carry yet falls through too.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>

#include "fake_host.h"
#include "ids.h"

/* uEnemy's work block and the fields the shell reads (USA v1.3.0). */
#define ENEMY_WORK    0x0e28u
#define WORK_ID       0x01c0u
#define WORK_CATEGORY 0x01cau
#define WORK_INDEX    0x01cbu

static int failures;

static void fail(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "FAIL: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    failures++;
}

#define CHECK(cond, ...) do { if (!(cond)) fail(__VA_ARGS__); } while (0)

/* The shell's frames only need the engine to answer; the call sequences are the family tests'
 * business. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)fn;
    (void)r;
    (void)s;
    (void)user;
    return (FakeResult){0, 0.0f};
}

/* ── driving the runtime ─────────────────────────────────────────────────────────────── */

static void spawn(uint32_t enemy, uint32_t work, int original_id, uint32_t stand_in) {
    fake_reset_calls();
    fake_regs[0] = 0;
    fake_regs[1] = (uint32_t)original_id;
    fake_created_enemy = enemy;
    fake_factory_stand_in = stand_in;
    FakeHook *factory = fake_find_hook_last("uEnemyFactory::create");
    CHECK(factory != NULL, "the factory association isn't registered");
    factory->fn(NULL, factory->user);
    CHECK(fake_original_count == 1, "the factory association didn't run the rest of the chain");
    /* What the game's own block keeps: the stand-in's id byte. */
    fake_mem_write32(enemy + ENEMY_WORK, work);
    fake_mem_write8(work + WORK_ID, stand_in);
    fake_reset_calls();
}

static void frame_with(uint32_t enemy, uint32_t work, int category, int index) {
    fake_regs[0] = enemy;
    fake_mem_write32(enemy + ENEMY_WORK, work);
    fake_mem_write8(work + WORK_CATEGORY, (uint32_t)category);
    fake_mem_write8(work + WORK_INDEX, (uint32_t)index);
    FakeHook *dispatch = fake_find_hook_last("uEnemy::dispatchAction");
    CHECK(dispatch != NULL, "the action dispatcher isn't registered");
    dispatch->fn(NULL, dispatch->user);
}

/* ── the test ────────────────────────────────────────────────────────────────────────── */

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    CHECK(fake_find_hook("uEnemyFactory::create") != NULL, "the factory isn't hooked");
    CHECK(fake_find_hook_last("uEnemy::dispatchAction") != NULL, "the dispatcher isn't hooked");

    /* The first frame runs the id layer's work, then the module's self-test. */
    fake_frame();
    CHECK(fake_log_contains("ready: translating 12 of GU Rathian's 13 MHXX-only actions on "
                            "monster 124"), "the module's ready line is missing");
    CHECK(fake_log_contains("family file(s) discovered from src/monsters/rathian-gu/"),
          "the self-test doesn't report the discovered families");
    CHECK(fake_log_contains("selftest: 12 of the 13 actions"), "the self-test line is missing");
    CHECK(fake_log_contains("selftest: float stubs at 0x"), "the float stubs' line is missing");

    /* ── routing: the module's own monster runs it; every other monster doesn't ── */
    const uint32_t enemy_124 = 0x1b0000u, work_124 = 0x1c0000u;
    spawn(enemy_124, work_124, MHUC_MONSTER_ID_RATHIAN_GU, 1);

    /* A shared id (3/17) stays with the game even on the module's monster. */
    fake_reset_calls();
    frame_with(enemy_124, work_124, 3, 17);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "a shared action (3/17) isn't left to the game (%d calls, %d original, %d skipped)",
          fake_call_count, fake_original_count, fake_skip_count);

    /* An MH4U id has no module: 3/98 goes to the game's dispatcher. */
    const uint32_t enemy_1 = 0x1d0000u, work_1 = 0x1e0000u;
    spawn(enemy_1, work_1, 1, 1);
    fake_reset_calls();
    frame_with(enemy_1, work_1, 3, 98);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "an MH4U id isn't left to the game (%d calls, %d original, %d skipped)",
          fake_call_count, fake_original_count, fake_skip_count);

    /* Category 17 on MH4U's own Rathian is left to the game too. */
    fake_reset_calls();
    frame_with(enemy_1, work_1, 17, 3);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "category 17 on monster 1 isn't left to the game");

    /* A registered id without a module (126, Giadrome) has no action module either, even
     * when the game's work block happens to hold id 124: the routing comes from the factory,
     * not the block. */
    const uint32_t enemy_126 = 0x1e8000u, work_126 = 0x1f0000u;
    spawn(enemy_126, work_126, 126, 15);
    fake_mem_write8(work_126 + WORK_ID, 124);
    fake_reset_calls();
    frame_with(enemy_126, work_126, 3, 98);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "a registered id without a module isn't left to the game (%d calls, %d original)",
          fake_call_count, fake_original_count);

    /* The module's own monster claims a translated id and skips the game; this is the check
     * that fails if the factory association or the generated family list is broken. */
    fake_reset_calls();
    frame_with(enemy_124, work_124, 3, 98);
    CHECK(fake_skip_count == 1 && fake_original_count == 0,
          "the module's monster didn't claim 3/98 (%d original, %d skipped)",
          fake_original_count, fake_skip_count);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 124 routes to the module, the shared and foreign ids fall through, and the "
           "ready line and self-test are logged\n");
    return 0;
}
