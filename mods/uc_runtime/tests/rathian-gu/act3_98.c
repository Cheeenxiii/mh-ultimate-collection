/*
 * act3_98.c: action 3/98's fake-host test — its three states and the motions 0x101/0x104.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the action's
 * call sequences on the fake host.
 *
 * The expected addresses, motions and frame values come from tests/rathian-gu/host.h, not from
 * the module, so a change in a handler fails the test instead of moving the expectation with
 * it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* What the engine answers 3/98's calls: the data value, the speed setter and the finish
 * flag. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};      /* the entry's data value, handed back in s0 */
    case FN_SET_SPEED:
    case FN_FLAG:
        return (FakeResult){1, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

int main(void) {
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    /* ── 3/98, three frames ── */
    const uint32_t enemy = 0x10000u, work = 0x20000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(work + WORK_TARGET + 4u, fbits(10.0f));
    fake_mem_write32(work + WORK_Y, fbits(5.0f));

    fake_reset_calls();
    frame_with(enemy, work, 3, 98);
    CHECK(fake_call_count == 4, "3/98 state 0 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_DATA_FLOAT, "first call is 0x%08x", fake_calls[0].fn);
    CHECK(fake_calls[1].fn == FN_APPLY_FALL && ffrom(fbits(fake_calls[1].s0)) == 1.5f,
          "the data float 1.5 isn't passed to the fall");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_3_98_A
          && fake_calls[2].s0 == 6.0f && fake_calls[2].s1 == 0.0f,
          "3/98 doesn't start motion 0x101 at 6.0");
    CHECK(fake_calls[3].fn == FN_FALL_SNAP && fake_calls[3].s0 == 10.0f,
          "the target height isn't handed to the fall snap");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "3/98 didn't skip the dispatcher");

    fake_reset_calls();
    frame_with(enemy, work, 3, 98);
    CHECK(fake_call_count == 3, "3/98 state 1 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_APPLY_RATE, "state 1 doesn't advance the rate first");
    CHECK(ffrom(fake_mem_read32(work + WORK_Y)) == 10.0f,
          "the position isn't snapped to the target");
    CHECK(fake_calls[1].fn == FN_SET_SPEED && fake_calls[1].s0 == 2.0f,
          "state 1 doesn't set the speed 2.0");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_3_98_B
          && fake_calls[2].s0 == 2.0f, "state 1 doesn't start motion 0x104 at 2.0");

    fake_reset_calls();
    frame_with(enemy, work, 3, 98);
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_FLAG && fake_calls[1].fn == FN_IDLE,
          "state 2 doesn't wait for the flag and return to idle");

    /* ── 3/98 state 1 stops above the target (a fresh monster, so state 0 runs first) ── */
    const uint32_t enemy_b = 0x30000u, work_b = 0x40000u;
    spawn(enemy_b, work_b, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(work_b + WORK_TARGET + 4u, fbits(10.0f));
    fake_mem_write32(work_b + WORK_Y, fbits(5.0f));
    fake_reset_calls();
    frame_with(enemy_b, work_b, 3, 98);        /* state 0 */
    fake_reset_calls();
    fake_mem_write32(work_b + WORK_Y, fbits(20.0f));
    frame_with(enemy_b, work_b, 3, 98);        /* state 1, above the target */
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_APPLY_RATE,
          "state 1 runs on past the target height (%d calls)", fake_call_count);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 3/98's three states make their calls\n");
    return 0;
}
