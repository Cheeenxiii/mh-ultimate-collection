/*
 * act4_27_32.c: the 4/27 to 4/32 family's fake-host test — one handler, three states, r1/r2
 * per id.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the six ids'
 * states on the fake host.
 *
 * The expected addresses, motions, turn steps and frame values come from
 * tests/rathian-gu/host.h, not from the module, so a change in a handler fails the test
 * instead of moving the expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

static int fail_mode_clear;

/* What the engine answers the handler's calls: the mode-clear call can be made to fail, and
 * the line point is filled ten further along x from the monster's position. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)user;
    (void)s;
    switch (fn) {
    case FN_MODE_CLEAR:
        if (fail_mode_clear) {
            fail_mode_clear = 0;
            return (FakeResult){0, 0.0f};
        }
        return (FakeResult){1, 0.0f};
    case FN_FLAG:
        return (FakeResult){1, 0.0f};
    case FN_LINE_POINT: {
        const uint32_t work = fake_mem_read32(r[0] + ENEMY_WORK);
        fake_mem_write32(r[1], fbits(ffrom(fake_mem_read32(work + WORK_POS)) + 10.0f));
        fake_mem_write32(r[1] + 4, fake_mem_read32(work + WORK_POS + 4u));
        fake_mem_write32(r[1] + 8, fake_mem_read32(work + WORK_POS + 8u));
        fake_mem_write32(r[1] + 12, 0);
        return (FakeResult){0, 0.0f};
    }
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

    /* ── 4/27: state 0, r1=2, r2=0 ── */
    const uint32_t enemy = 0x70000u, work = 0x90000u, line = 0xa0000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy + ENEMY_TARGET_LINE, line);
    fake_mem_write32(enemy + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(enemy + ENEMY_TURN_SCALE, fbits(0.05f));
    fake_mem_write32(work + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work + WORK_POS + 4u, fbits(7.0f));
    fake_mem_write32(work + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work + WORK_TARGET + 8u, fbits(10.0f));
    fake_mem_write32(work + WORK_HEADING, 0x1234u);
    fake_s[0] = 500.0f;                        /* (int)(500 * 0.01) = 5 percent */

    fake_reset_calls();
    frame_with(enemy, work, 4, 27);
    CHECK(fake_call_count == 4, "4/27 state 0 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLIGHT_SETUP, "4/27 state 0 doesn't set the flight up first");
    CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 3,
          "4/27 state 0 doesn't set mode 3");
    CHECK(fake_calls[2].fn == FN_ROTATE && fake_calls[2].r0 == line + LINE_DIR
          && fake_calls[2].r1 == 0xc001, "4/27 state 0 doesn't rotate the line by 0xc001");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_TAKEOFF_2
          && fake_calls[3].s0 == 6.0f && fake_calls[3].s1 == 0.0f,
          "4/27 state 0 doesn't start motion 0x418 at 6.0");
    CHECK(ffrom(fake_mem_read32(line + LINE_ORIGIN)) == 5.0f
          && ffrom(fake_mem_read32(line + LINE_ORIGIN + 8u)) == 10.0f,
          "the line's origin isn't the monster's position");
    CHECK(ffrom(fake_mem_read32(line + LINE_DIR)) == 1.0f
          && ffrom(fake_mem_read32(line + LINE_DIR + 4u)) == 0.0f
          && ffrom(fake_mem_read32(line + LINE_DIR + 8u)) == 0.0f,
          "the line's direction isn't normalised from the target point");
    CHECK(fake_mem_read32(line + LINE_DIR + 0xcu) == 0
          && fake_mem_read32(work + WORK_SAVED_HEADING) == 0x1234u,
          "the heading isn't saved for the action");
    CHECK(fake_log_contains("4/27: the source's case block calls 0x00adb528"),
          "4/27 doesn't log the untranslated case-block call once");

    fake_reset_calls();
    frame_with(enemy, work, 4, 27);             /* state 1 */
    CHECK(fake_call_count == 8, "4/27 state 1 made %d calls, want 8", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLIGHT_SETUP, "4/27 state 1 doesn't set the flight up first");
    CHECK(fake_calls[1].fn == FN_TARGET_POINT && fake_calls[1].r1 == 0 && fake_calls[1].r2 == 0,
          "4/27 state 1 doesn't build target point 0");
    CHECK(fake_calls[2].fn == FN_MODE_CLEAR && fake_calls[2].r1 == 2 && fake_calls[2].s0 == 78.0f,
          "4/27 state 1 doesn't make the mode-clear call at 78.0");
    CHECK(fake_calls[3].fn == FN_TURN_TO && fake_calls[3].r1 == TURN_STEP_SLOW
          && fake_calls[3].r2 == 0xe001,
          "4/27 state 1 doesn't turn to the target at the slow step, offset 0xe001");
    CHECK(fake_calls[4].fn == FN_LINE_POINT && fake_calls[4].r2 == 5u
          && fake_calls[4].s0 == 1.0f,
          "4/27 state 1 doesn't take the line point at 5 percent with speed/88");
    CHECK(ffrom(fake_mem_read32(work + WORK_POS)) == 5.5f
          && ffrom(fake_mem_read32(work + WORK_POS + 4u)) == 7.0f
          && ffrom(fake_mem_read32(work + WORK_POS + 8u)) == 10.0f,
          "4/27 state 1 doesn't step 10 * (this+0x14) toward the line point");
    CHECK(fake_calls[5].fn == FN_MODE_CLEAR && fake_calls[5].r1 == 1 && fake_calls[5].s0 == 2.0f,
          "4/27 state 1 doesn't make the mode-clear call at 2.0");
    CHECK(fake_calls[6].fn == FN_MODE && fake_calls[6].r1 == 0,
          "4/27 state 1 doesn't set mode 0");
    CHECK(fake_calls[7].fn == FN_MOTION && fake_calls[7].r1 == MOTION_FLY_2
          && fake_calls[7].s0 == 0.0f && fake_calls[7].s1 == 0.0f,
          "4/27 state 1 doesn't start motion 0x90a at 0.0");

    fake_reset_calls();
    frame_with(enemy, work, 4, 27);             /* state 2, variant 0: the finish flag */
    CHECK(fake_call_count == 3, "4/27 state 2 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_TURN && fake_calls[0].r1 == 0x2000u
          && fake_calls[0].s0 == 2.0f && fake_calls[0].s1 == 10.0f,
          "4/27 state 2 doesn't turn by 0x2000 at 2.0..10.0");
    CHECK(fake_calls[1].fn == FN_FLAG, "4/27 state 2 doesn't wait for the finish flag");
    CHECK(fake_calls[2].fn == FN_BASE_UPDATE, "4/27 state 2 doesn't end the action on the flag");

    /* ── 4/28 is the other side: motion 0x417 and the 0x4000 rotation ── */
    const uint32_t enemy_28 = 0xb0000u, work_28 = 0xc0000u, line_28 = 0xd0000u;
    spawn(enemy_28, work_28, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_28 + ENEMY_TARGET_LINE, line_28);
    fake_mem_write32(enemy_28 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_28 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_28 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_28 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_28 + WORK_TARGET + 8u, fbits(10.0f));
    fake_reset_calls();
    frame_with(enemy_28, work_28, 4, 28);
    CHECK(fake_call_count == 4 && fake_calls[2].r1 == 0x4000u,
          "4/28 doesn't rotate the line by 0x4000");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_TAKEOFF_1,
          "4/28 doesn't start motion 0x417");

    /* ── 4/29 (r1=2, r2=1) and 4/30 (r1=1, r2=1) end by starting motion 0x90b/0x90d ── */
    const uint32_t enemy_29 = 0xe0000u, work_29 = 0xf0000u, line_29 = 0x100000u;
    spawn(enemy_29, work_29, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_29 + ENEMY_TARGET_LINE, line_29);
    fake_mem_write32(enemy_29 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_29 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_29 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_29 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_29 + WORK_TARGET + 8u, fbits(10.0f));
    for (int i = 0; i < 2; i++) {              /* states 0 and 1 */
        frame_with(enemy_29, work_29, 4, 29);
    }
    fake_reset_calls();
    frame_with(enemy_29, work_29, 4, 29);       /* state 2, variant 1 */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_TURN && fake_calls[0].r1 == 0x2000u,
          "4/29 state 2 doesn't start with the turn");
    CHECK(fake_calls[1].fn == FN_MODE_CLEAR && fake_calls[1].r1 == 1
          && fake_calls[1].s0 == 30.0f,
          "4/29 state 2 doesn't make the mode-clear call at 30.0");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_END_2
          && fake_calls[2].s0 == 2.0f && fake_calls[2].s1 == 0.0f,
          "4/29 state 2 doesn't start motion 0x90b at 2.0");
    CHECK(fake_log_contains("requests action 7/247"),
          "4/29 doesn't log the untranslated 7/247 request once");

    const uint32_t enemy_30 = 0x110000u, work_30 = 0x120000u, line_30 = 0x130000u;
    spawn(enemy_30, work_30, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_30 + ENEMY_TARGET_LINE, line_30);
    fake_mem_write32(enemy_30 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_30 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_30 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_30 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_30 + WORK_TARGET + 8u, fbits(10.0f));
    for (int i = 0; i < 2; i++) {
        frame_with(enemy_30, work_30, 4, 30);
    }
    fake_reset_calls();
    frame_with(enemy_30, work_30, 4, 30);
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_TURN
          && fake_calls[0].r1 == 0xffffe000u, "4/30 state 2 doesn't turn by -0x2000");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_END_1,
          "4/30 state 2 doesn't start motion 0x90d");

    /* ── 4/31: when the mode-clear call at 78.0 fails, the turn takes the fast step ── */
    const uint32_t enemy_31 = 0x140000u, work_31 = 0x150000u, line_31 = 0x160000u;
    spawn(enemy_31, work_31, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_31 + ENEMY_TARGET_LINE, line_31);
    fake_mem_write32(enemy_31 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_31 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_31 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_31 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_31 + WORK_TARGET + 8u, fbits(10.0f));
    frame_with(enemy_31, work_31, 4, 31);       /* state 0 */
    fail_mode_clear = 1;
    fake_reset_calls();
    frame_with(enemy_31, work_31, 4, 31);       /* state 1, the mode-clear call fails */
    CHECK(fake_calls[3].fn == FN_TURN_TO && fake_calls[3].r1 == TURN_STEP_FAST,
          "4/31 doesn't take the fast turn step when the mode-clear call fails");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 4/27 to 4/32 make their calls in all three states\n");
    return 0;
}
