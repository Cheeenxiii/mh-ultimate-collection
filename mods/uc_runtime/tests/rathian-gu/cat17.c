/*
 * cat17.c: category 17's fake-host test — the gate's 0-2 no-op and the base action update.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the category's
 * calls on the fake host.
 *
 * The expected addresses and constants come from tests/rathian-gu/host.h, not from the
 * module, so a change in a handler fails the test instead of moving the expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* Category 17's only engine call is the base update; the test needs no other answer. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)fn;
    (void)r;
    (void)s;
    (void)user;
    return (FakeResult){0, 0.0f};
}

int main(void) {
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    const uint32_t enemy = 0x10000u, work = 0x20000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_GU, 1);

    /* 17/0 to 17/2: MHXX's gate returns, so the action is claimed and nothing is called. */
    for (int index = 0; index <= 2; index++) {
        fake_reset_calls();
        frame_with(enemy, work, 17, index);
        CHECK(fake_call_count == 0 && fake_skip_count == 1 && fake_original_count == 0,
              "17/%d isn't a no-op (%d calls, %d skipped, %d original)", index, fake_call_count,
              fake_skip_count, fake_original_count);
    }

    /* 17/3 and 17/9: MH4U's base action update, with the monster in r0. */
    fake_reset_calls();
    frame_with(enemy, work, 17, 3);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_BASE_UPDATE
          && fake_calls[0].r0 == enemy,
          "17/3 doesn't run MH4U's base action update with the monster in r0");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "17/3 doesn't skip the dispatcher");
    fake_reset_calls();
    frame_with(enemy, work, 17, 9);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_BASE_UPDATE,
          "17/9 doesn't run the base update");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 17 is a no-op for 0 to 2 and the base update for the rest\n");
    return 0;
}
