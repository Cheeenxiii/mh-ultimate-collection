/*
 * cat1.c: GU Rathian's category 1 fake-host test — the twelve ids' units and inline blocks.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives category 1's
 * states on the fake host.
 *
 * The expected addresses, motions and frame values come from tests/rathian-gu/host.h, not from
 * the module, so a change in a handler fails the test instead of moving the expectation with
 * it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

static int flag_result = 1;
static int speed_result = 1;
static int countdown_result = 1;
static int query_result = 1;

/* What the engine answers category 1's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG: return (FakeResult){(uint32_t)flag_result, 0.0f};
    case FN_SET_SPEED: return (FakeResult){(uint32_t)speed_result, 0.0f};
    case FN_COUNTDOWN: return (FakeResult){(uint32_t)countdown_result, 0.0f};
    case FN_MODE_CLEAR: return (FakeResult){(uint32_t)query_result, 0.0f};
    default: return (FakeResult){0, 0.0f};
    }
}

static void check_call(int i, uint32_t fn, const char *what) {
    CHECK(i < fake_call_count && fake_calls[i].fn == fn, "%s (call %d)", what, i);
}

int main(void) {
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    const uint32_t enemy = 0x300000u, work = 0x320000u;

    /* ── 1/0: state 0's motion 4 at 10.0, then the speed step and the (1, 0x32, 5) call ── */
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(enemy, work, 1, 0);
    CHECK(fake_call_count == 3, "1/0 state 0 made %d calls, want 3", fake_call_count);
    check_call(0, FN_MODE, "1/0 doesn't set mode 0");
    check_call(1, FN_MOTION, "1/0 doesn't start a motion");
    CHECK(fake_calls[1].r1 == 0x4u && fake_calls[1].s0 == 10.0f,
          "1/0 doesn't start motion 0x4 at 10.0");
    CHECK(fake_calls[2].fn == 0x00914dc4u && fake_calls[2].r2 == 0x13u,
          "1/0 doesn't make the 0x00914dc4 tail");

    fake_reset_calls();
    fake_mem_write8(work + WORK_DATAID, 5);
    frame_with(enemy, work, 1, 0);
    CHECK(fake_call_count == 4, "1/0 state 1 made %d calls, want 4", fake_call_count);
    check_call(0, FN_SET_SPEED, "1/0 doesn't make the 110.0 speed step");
    CHECK(fake_calls[0].s0 == 110.0f, "1/0 doesn't pass 110.0");
    CHECK(fake_calls[1].fn == 0x0093310cu && fake_calls[1].r1 == 1
          && fake_calls[1].r2 == 0x32u && fake_calls[1].r3 == 5,
          "1/0 doesn't make the (1, 0x32, 5) call for data id 5");
    check_call(2, FN_FLAG, "1/0 doesn't wait for the finish flag");
    check_call(3, FN_BASE_UPDATE, "1/0 doesn't end on the base update");

    /* ── 1/4 and 1/7: the same unit, r1 0 and 1; the sub-state counts three flags ── */
    const uint32_t enemy_4 = 0x330000u, work_4 = 0x350000u;
    spawn(enemy_4, work_4, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_4, work_4, 1, 4);
    CHECK(fake_mem_read32(enemy_4 + ENEMY_MARKER) == 0,
          "1/4 set the marker, which only 1/7 does");
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x10u && fake_calls[1].s0 == 6.0f,
          "1/4 doesn't start motion 0x10 at 6.0");
    for (int i = 0; i < 3; i++) {
        fake_reset_calls();
        frame_with(enemy_4, work_4, 1, 4);
    }
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_REQUEST_NEXT
          && fake_calls[1].r1 == 1 && fake_calls[1].r2 == 5,
          "1/4 doesn't request 1/5 after the third flag");

    const uint32_t enemy_7 = 0x360000u, work_7 = 0x380000u;
    spawn(enemy_7, work_7, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_7, work_7, 1, 7);
    CHECK(fake_mem_read32(enemy_7 + ENEMY_MARKER) == 8u,
          "1/7 doesn't set the marker's bit 3");
    for (int i = 0; i < 3; i++) {
        fake_reset_calls();
        frame_with(enemy_7, work_7, 1, 7);
    }
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_REQUEST_NEXT
          && fake_calls[1].r1 == 1 && fake_calls[1].r2 == 8,
          "1/7 doesn't request 1/8 after the third flag");

    /* ── 1/5 and 1/8: motion 0x11 at 6.0, then 0x00911f20; 1/8 sets the marker ── */
    const uint32_t enemy_5 = 0x390000u, work_5 = 0x3b0000u;
    spawn(enemy_5, work_5, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_5, work_5, 1, 5);
    CHECK(fake_call_count == 3, "1/5 state 0 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == 0x11u
          && fake_calls[1].s0 == 6.0f, "1/5 doesn't start motion 0x11 at 6.0");
    CHECK(fake_calls[2].fn == FN_1_5_TAIL && fake_calls[2].r1 == work_5 + WORK_POS
          && fake_calls[2].r2 == 0x64u,
          "1/5 doesn't make the (work+0x198, 0x64, 0) call");
    fake_reset_calls();
    frame_with(enemy_5, work_5, 1, 5);
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_BASE_UPDATE,
          "1/5 doesn't end on the base update");

    const uint32_t enemy_8 = 0x3c0000u, work_8 = 0x3e0000u;
    spawn(enemy_8, work_8, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_8, work_8, 1, 8);
    CHECK(fake_mem_read32(enemy_8 + ENEMY_MARKER) == 8u,
          "1/8 doesn't set the marker's bit 3");

    /* ── 1/6: the six states, motion 0x12/0x13/0x14/0x310 and the helpers ── */
    const uint32_t enemy_6 = 0x3f0000u, work_6 = 0x410000u;
    spawn(enemy_6, work_6, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_6, work_6, 1, 6);
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x12u && fake_calls[1].s0 == 6.0f,
          "1/6 state 0 doesn't start motion 0x12 at 6.0");
    fake_reset_calls();
    frame_with(enemy_6, work_6, 1, 6);
    CHECK(fake_call_count == 4, "1/6 state 1 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == 0x13u
          && fake_calls[1].s0 == 30.0f, "1/6 doesn't start motion 0x13 at 30.0");
    check_call(2, FN_1_6_A, "1/6 doesn't make 0x0093ba70");
    check_call(3, FN_1_6_B, "1/6 doesn't make 0x0091b0f8");

    fake_reset_calls();
    fake_mem_write8(work_6 + WORK_DATAID, 1);
    fake_mem_write32(work_6 + WORK_TIMER, fbits(0.0f));
    frame_with(enemy_6, work_6, 1, 6);
    CHECK(fake_call_count == 4, "1/6 state 2 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_1_6_C && fake_calls[0].r1 == 1 && fake_calls[0].r2 == 0x1eu
          && fake_calls[0].s0 == 0.4f, "1/6 doesn't make the (1, 0x1e, 0.4) motion step");
    check_call(1, FN_COUNTDOWN, "1/6 doesn't count the timer down");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == 0x14u
          && fake_calls[2].s0 == 0.0f && fake_calls[2].s1 == 4.0f,
          "1/6 doesn't start motion 0x14");
    check_call(3, FN_1_6_D, "1/6 doesn't make the 0x0093c938 tail");
    CHECK(fake_mem_read8(work_6 + WORK_STATE) == 3, "1/6's state 2 didn't move to 3");

    fake_reset_calls();
    frame_with(enemy_6, work_6, 1, 6);
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_MOTION
          && fake_calls[1].r1 == 0x310u && fake_calls[1].s0 == 0.0f,
          "1/6 state 3 doesn't start motion 0x310 at 0.0");
    fake_reset_calls();
    frame_with(enemy_6, work_6, 1, 6);
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_BASE_UPDATE,
          "1/6 state 4 doesn't end on the base update");

    /* ── the inline blocks: 1/1, 1/2, 1/3, 1/10 ── */
    const uint32_t e1 = 0x420000u, w1 = 0x440000u;
    spawn(e1, w1, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e1, w1, 1, 1);
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x0fu && fake_calls[1].s0 == 10.0f,
          "1/1 doesn't start motion 0xf at 10.0");
    fake_reset_calls();
    frame_with(e1, w1, 1, 1);
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_BASE_UPDATE,
          "1/1 doesn't end on the base update");

    const uint32_t e2 = 0x450000u, w2 = 0x470000u;
    spawn(e2, w2, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e2, w2, 1, 2);
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x310u && fake_calls[1].s0 == 6.0f,
          "1/2 doesn't start motion 0x310 at 6.0");

    const uint32_t e3 = 0x480000u, w3 = 0x4a0000u;
    spawn(e3, w3, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e3, w3, 1, 3);
    CHECK(fake_call_count == 2, "1/3 state 0 made %d calls, want 2", fake_call_count);
    CHECK(fake_calls[1].fn == FN_1_3_MOTION && fake_calls[1].r1 == 2 && fake_calls[1].r2 == 0x11u
          && fake_calls[1].s0 == 50.0f, "1/3 doesn't make the (2, 0x11, 50.0) motion");
    fake_reset_calls();
    query_result = 1;
    frame_with(e3, w3, 1, 3);
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_1_3_QUERY
          && fake_calls[0].s0 == 52.0f && fake_calls[1].fn == FN_BASE_UPDATE,
          "1/3 doesn't make the 52.0 query and end on the base update");

    const uint32_t e10 = 0x4b0000u, w10 = 0x4d0000u;
    spawn(e10, w10, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e10, w10, 1, 10);
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x0eu && fake_calls[1].s0 == 6.0f,
          "1/10 doesn't start motion 0xe at 6.0");

    /* ── 1/11: motion 1 at 10.0, the 20.0 timer and the 1.0 countdown ── */
    const uint32_t e11 = 0x4e0000u, w11 = 0x500000u;
    spawn(e11, w11, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e11, w11, 1, 11);
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 1 && fake_calls[1].s0 == 10.0f,
          "1/11 doesn't start motion 1 at 10.0");
    CHECK(ffrom(fake_mem_read32(w11 + WORK_TIMER)) == 20.0f,
          "1/11 doesn't arm the 20.0 timer");
    fake_reset_calls();
    flag_result = 0;
    countdown_result = 1;
    frame_with(e11, w11, 1, 11);
    CHECK(fake_call_count == 3, "1/11 state 1 made %d calls, want 3", fake_call_count);
    check_call(0, FN_FLAG, "1/11 doesn't wait for the finish flag");
    check_call(1, FN_COUNTDOWN, "1/11 doesn't count the timer down");
    check_call(2, FN_BASE_UPDATE, "1/11 doesn't end when the timer is spent");
    flag_result = 1;

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 1's twelve ids make their units' calls in order\n");
    return 0;
}
