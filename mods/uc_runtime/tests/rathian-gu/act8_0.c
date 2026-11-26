/*
 * act8_0.c: action 8/0's fake-host test — its three states and the 9/1 or 2/6 combo tail.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the action's
 * states on the fake host.
 *
 * The expected addresses, motions, frame values and tail ids come from
 * tests/rathian-gu/host.h, not from the module, so a change in a handler fails the test
 * instead of moving the expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

static int fail_mode_clear;
static int fake_hit_check = 1, fake_hit_r3 = 1;

/* What the engine answers 8/0's calls: the finish flag and the two hit checks. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_MODE_CLEAR:
        if (fail_mode_clear) {
            fail_mode_clear = 0;
            return (FakeResult){0, 0.0f};
        }
        return (FakeResult){1, 0.0f};
    case FN_FLAG:
        return (FakeResult){1, 0.0f};
    case FN_HIT_CHECK:
        return (FakeResult){(uint32_t)fake_hit_check, 0.0f};
    case FN_HIT_CHECK_R3:
        return (FakeResult){(uint32_t)fake_hit_r3, 0.0f};
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

    /* ── 8/0: three frames, then the 9/1 tail ── */
    const uint32_t enemy = 0x170000u, work = 0x180000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(enemy, work, 8, 0);              /* state 0 */
    CHECK(fake_call_count == 2, "8/0 state 0 made %d calls, want 2", fake_call_count);
    CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0,
          "8/0 doesn't copy the data entry with mode 0");
    CHECK(fake_calls[1].fn == FN_MOVE_TO && fake_calls[1].r1 == work + WORK_VELOCITY
          && fake_calls[1].r2 == work + WORK_TARGET
          && fake_calls[1].s0 == 300.0f && fake_calls[1].s1 == 38.0f,
          "8/0 doesn't aim the velocity at the target at 300.0/38.0");
    CHECK(fake_mem_read8(work + WORK_FLAG_ZERO_A) == 0
          && fake_mem_read8(work + WORK_FLAG_ZERO_B) == 0
          && fake_mem_read8(work + WORK_FLAG_MODE) == 2,
          "8/0 doesn't clear the entry flags");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "8/0 didn't skip the dispatcher");

    fake_reset_calls();
    frame_with(enemy, work, 8, 0);              /* state 1 */
    CHECK(fake_call_count == 4, "8/0 state 1 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_MODE_CLEAR && fake_calls[0].r1 == 3 && fake_calls[0].r2 == 0
          && fake_calls[0].s0 == 12.0f && fake_calls[0].s1 == 50.0f,
          "8/0 doesn't run the per-mode speed check at 12.0/50.0");
    CHECK(fake_calls[1].fn == FN_APPLY_MOVE,
          "8/0 doesn't advance the position when the check holds");
    CHECK(fake_calls[2].fn == FN_FLAG, "8/0 doesn't wait for the finish flag");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_8_0
          && fake_calls[3].s0 == 4.0f && fake_calls[3].s1 == 0.0f,
          "8/0 doesn't start motion 0x403 at 4.0");
    CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 180.0f,
          "8/0 doesn't arm the 180.0 timer");

    fake_reset_calls();
    fake_mem_write8(work + WORK_PENDING, 1);
    fake_mem_write8(work + WORK_BYTE_A, 2);
    fake_mem_write8(work + WORK_BYTE_B, 4);
    frame_with(enemy, work, 8, 0);              /* state 2: the 9/1 tail */
    CHECK(fake_call_count == 4, "8/0 state 2 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_COUNTDOWN && fake_calls[0].r1 == work + WORK_TIMER,
          "8/0 doesn't count the timer down");
    CHECK(fake_calls[1].fn == FN_HIT_CHECK && fake_calls[1].r1 == 4 && fake_calls[1].r2 == 2
          && fake_calls[1].s0 == 300.0f && fake_calls[1].s1 == 0.0f
          && fake_calls[1].s2 == 150.0f && fake_calls[1].has_s2,
          "8/0 doesn't run the first hit check at 300.0/0.0/150.0");
    CHECK(fake_calls[2].fn == FN_HIT_CHECK_R3 && fake_calls[2].r1 == 1 && fake_calls[2].r2 == 4
          && fake_calls[2].r3 == 2, "8/0 doesn't run the second hit check with mode 1");
    CHECK(fake_calls[3].fn == FN_REQUEST_NEXT && fake_calls[3].r1 == 9 && fake_calls[3].r2 == 1,
          "8/0 doesn't request the 9/1 combo tail");
    CHECK(fake_mem_read8(work + WORK_FLAG_TAIL) == 3, "8/0 doesn't set the tail flag");

    /* ── 8/0: a failed hit check and a spent timer request 2/6 ── */
    fake_reset_calls();
    fake_mem_write8(work + WORK_PENDING, 1);
    fake_mem_write32(work + WORK_TIMER, fbits(0.0f));
    fake_hit_check = 0;
    frame_with(enemy, work, 8, 0);              /* state 2: hit check fails, timer spent */
    CHECK(fake_call_count == 3, "8/0's spent timer path made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_COUNTDOWN && fake_calls[1].fn == FN_HIT_CHECK
          && fake_calls[2].fn == FN_REQUEST_NEXT && fake_calls[2].r1 == 2
          && fake_calls[2].r2 == 6,
          "8/0 doesn't request 2/6 when the hit check fails and the timer is spent");
    fake_hit_check = 1;

    /* ── 8/0: a failed fallback check while the timer runs also requests 2/6 ── */
    fake_reset_calls();
    fake_mem_write32(work + WORK_TIMER, fbits(10.0f));
    fake_hit_check = 0;
    fake_hit_r3 = 0;
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 4, "8/0's fallback path made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[1].fn == FN_HIT_CHECK && fake_calls[2].fn == FN_HIT_CHECK_R3
          && fake_calls[2].r1 == 0 && fake_calls[3].fn == FN_REQUEST_NEXT
          && fake_calls[3].r1 == 2 && fake_calls[3].r2 == 6,
          "8/0 doesn't request 2/6 when the fallback check fails");
    fake_hit_check = 1;
    fake_hit_r3 = 1;

    /* ── 8/0: the gate closed leaves the velocity alone, the flag still starts the motion ── */
    const uint32_t enemy_b = 0x190000u, work_b = 0x1a0000u;
    spawn(enemy_b, work_b, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_b, work_b, 8, 0);          /* state 0 */
    fail_mode_clear = 1;
    fake_reset_calls();
    frame_with(enemy_b, work_b, 8, 0);          /* state 1, the gate closed */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_MODE_CLEAR
          && fake_calls[1].fn == FN_FLAG && fake_calls[2].fn == FN_MOTION,
          "8/0 doesn't skip the position step when the per-mode check fails");
    fail_mode_clear = 0;

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 8/0's three states and its 9/1 or 2/6 tail make their calls\n");
    return 0;
}
