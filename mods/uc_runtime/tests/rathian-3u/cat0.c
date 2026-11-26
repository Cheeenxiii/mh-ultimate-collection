/*
 * cat0.c: category 0's fake-host test — 0/0, 0/1, 0/2, 0/3, 0/4 and 0/6, and the three
 * base-class handlers they fall into.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/ and
 * builds it as tests/family-<stem>, so a slice adds its test file and edits nothing shared.
 * The shell's test (tests/test_rathian_3u.c) covers the factory association, the routing, the
 * ready line and the self-test; this one drives the six ids' call sequences on the fake host.
 *
 * The expected addresses, constants and frame values come from tests/rathian-3u/host.h, not
 * from the module, so a change in a handler fails the test instead of moving the expectation
 * with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

static int fake_flag = 1;
static int fake_countdown = 1;

/* What the engine answers category 0's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)user;
    (void)s;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_COUNTDOWN:
        return (FakeResult){(uint32_t)fake_countdown, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};          /* the record's float, in s0 */
    case FN_DATA_GET:
        (void)r;
        return (FakeResult){RECORD_ADDRESS, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    /* The setter's per-action value comes from MH4U's own global: point it at guest memory
     * the test controls. */
    fake_mem_write32(ACTION_EXTRA_GLOBAL, EXTRA_POINTER);
    fake_mem_write8(EXTRA_POINTER + 0x2fu, 0x7fu);

    /* ── 0/0 and 0/4: the 150.0 delay, then 0/2's base handler ── */
    const uint32_t enemy_00 = 0x30000u, work_00 = 0x40000u;
    spawn(enemy_00, work_00, MHUC_MONSTER_ID_RATHIAN_3U, 1);

    fake_reset_calls();
    frame_with(enemy_00, work_00, 0, 0);       /* state 0 */
    CHECK(fake_call_count == 2, "0/0 state 0 made %d calls, want 2", fake_call_count);
    CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0,
          "0/0 state 0 doesn't set mode 0");
    CHECK(fake_calls[1].fn == FN_REQUEST && fake_calls[1].r1 == REQUEST_0_0
          && fake_calls[1].s0 == REQUEST_SPEED && fake_calls[1].s1 == 0.0f,
          "0/0 state 0 doesn't request motion 1 at speed 10.0");
    CHECK(ffrom(fake_mem_read32(work_00 + WORK_COUNTDOWN)) == DELAY_0_0,
          "0/0 doesn't arm the 150.0 delay");
    CHECK(fake_mem_read8(work_00 + WORK_STATE) == 1, "0/0 doesn't advance its state byte");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "0/0 didn't skip the dispatcher");

    fake_reset_calls();
    fake_countdown = 1;
    fake_mem_write8(work_00 + WORK_0_2_STATE, 2);
    fake_mem_write32(work_00 + WORK_FLAGS, 0x40);
    frame_with(enemy_00, work_00, 0, 0);       /* state 1, the delay spent */
    CHECK(fake_call_count == 3, "0/0 state 1 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_COUNTDOWN && fake_calls[0].r1 == work_00 + WORK_COUNTDOWN,
          "0/0 state 1 doesn't count the delay down");
    CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 0,
          "0/0 state 1 doesn't run 0/2's mode 0");
    CHECK(fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r1 == 0 && fake_calls[2].r2 == 2
          && fake_calls[2].r3 == 2, "0/0 state 1 doesn't start the sub-state 2 action");
    CHECK(fake_calls[2].has_r4 && fake_calls[2].r4 == 0x7fu,
          "the action setter's per-action stack argument isn't MH4U's own (0x%x)",
          fake_calls[2].r4);
    CHECK(fake_mem_read8(work_00 + WORK_SET) == 1, "the set byte isn't set");

    /* The same handler runs on 0/4. */
    const uint32_t enemy_04 = 0x50000u, work_04 = 0x60000u;
    spawn(enemy_04, work_04, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(enemy_04, work_04, 0, 4);
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MODE
          && fake_calls[1].fn == FN_REQUEST && fake_calls[1].r1 == REQUEST_0_0,
          "0/4 doesn't run the 0/0 handler");

    /* ── 0/1: its inline delay, then 0/2's base handler ── */
    const uint32_t enemy_01 = 0x70000u, work_01 = 0x80000u;
    spawn(enemy_01, work_01, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(enemy_01, work_01, 0, 1);       /* state 0 */
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MODE
          && fake_calls[1].fn == FN_REQUEST && fake_calls[1].r1 == REQUEST_0_1
          && fake_calls[1].s0 == REQUEST_SPEED,
          "0/1 state 0 doesn't set mode 0 and request motion 2");

    fake_reset_calls();
    fake_flag = 1;
    fake_mem_write8(work_01 + WORK_0_2_STATE, 3);
    fake_mem_write32(work_01 + WORK_FLAGS, 0x40);
    frame_with(enemy_01, work_01, 0, 1);       /* state 1, the flag set */
    CHECK(fake_call_count == 3, "0/1 state 1 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLAG, "0/1 state 1 doesn't wait for the flag");
    CHECK(fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r2 == 2,
          "0/1 state 1 doesn't fall into 0/2's base handler");

    /* The base handler's other two sub-state branches. */
    fake_reset_calls();
    fake_mem_write8(work_01 + WORK_0_2_STATE, 0);
    fake_mem_write32(work_01 + WORK_FLAGS, 0);
    fake_mem_write8(work_01 + WORK_OTHER, 1);
    frame_with(enemy_01, work_01, 0, 1);
    CHECK(fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r2 == 1,
          "0/2's base handler doesn't take sub-state 1 from the other state byte");
    fake_reset_calls();
    fake_mem_write8(work_01 + WORK_OTHER, 0);
    frame_with(enemy_01, work_01, 0, 1);
    CHECK(fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r2 == 0,
          "0/2's base handler doesn't take sub-state 0");

    /* ── 0/2: mode 0, then 0/2's base handler ── */
    const uint32_t enemy_02 = 0x90000u, work_02 = 0xa0000u;
    spawn(enemy_02, work_02, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(enemy_02, work_02, 0, 2);       /* state 0 */
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MODE
          && fake_calls[1].fn == FN_REQUEST && fake_calls[1].r1 == REQUEST_0_2
          && fake_calls[1].s0 == FALL_RATE,
          "0/2 state 0 doesn't set mode 0 and request motion 0x11 at 6.0");
    fake_reset_calls();
    fake_flag = 1;
    fake_mem_write8(work_02 + WORK_0_2_STATE, 2);
    fake_mem_write32(work_02 + WORK_FLAGS, 0x40);
    frame_with(enemy_02, work_02, 0, 2);       /* state 1 */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG
          && fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r2 == 2,
          "0/2 state 1 doesn't fall into 0/2's base handler");

    /* ── 0/3: the data float, the fall rate, mode 1, then the record and the action start ── */
    const uint32_t enemy_03 = 0xb0000u, work_03 = 0xc0000u;
    spawn(enemy_03, work_03, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write32(work_03 + WORK_MODE, 0);
    fake_mem_write32(work_03 + WORK_RATE, fbits(2.0f));
    fake_mem_write32(work_03 + WORK_RATE_2, fbits(3.0f));
    fake_mem_write32(RECORD_ADDRESS + 0x64u, fbits(4.0f));
    fake_mem_write8(work_03 + WORK_KIND, 0x20);
    fake_mem_write8(work_03 + WORK_DATA_INDEX, 7);
    fake_reset_calls();
    frame_with(enemy_03, work_03, 0, 3);       /* state 0 */
    CHECK(fake_call_count == 3, "0/3 state 0 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_DATA_FLOAT, "0/3 state 0 doesn't read the data float");
    CHECK(fake_calls[1].fn == FN_APPLY_FALL && fake_calls[1].s0 == 1.5f,
          "0/3 state 0 doesn't apply the data float to the fall");
    CHECK(fake_calls[2].fn == FN_REQUEST && fake_calls[2].r1 == REQUEST_0_3
          && fake_calls[2].s0 == FALL_RATE,
          "0/3 state 0 doesn't request motion 0x1a at 6.0");

    fake_reset_calls();
    fake_flag = 1;
    fake_mem_write32(work_03 + WORK_POS_Y, fbits(1.0f));
    frame_with(enemy_03, work_03, 0, 3);       /* state 1: the flag, then the base handler */
    CHECK(fake_call_count == 4, "0/3 state 1 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLAG, "0/3 state 1 doesn't wait for the flag");
    CHECK(fake_calls[1].fn == FN_DATA_GET && fake_calls[1].r1 == 0x20
          && fake_calls[1].r2 == 7,
          "0/3's base handler doesn't look the data record up by id 0x20 and index 7");
    CHECK(ffrom(fake_mem_read32(work_03 + WORK_POS_Y)) == 1.0f + 4.0f * (2.0f * 3.0f),
          "0/3's base handler doesn't add the record's float times the rate");
    CHECK(fake_calls[2].fn == FN_MODE && fake_calls[2].r1 == 1,
          "0/3's base handler doesn't set mode 1");
    CHECK(fake_calls[3].fn == FN_SET_ACTION && fake_calls[3].r1 == 0
          && fake_calls[3].r2 == 3 && fake_calls[3].r3 == 2,
          "0/3's base handler doesn't start action 0/3");

    /* ── 0/6: mode 3 and the vertical step, then the action start ── */
    const uint32_t enemy_06 = 0xd0000u, work_06 = 0xe0000u;
    spawn(enemy_06, work_06, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write32(work_06 + WORK_VERTICAL, fbits(-100.0f));
    fake_reset_calls();
    frame_with(enemy_06, work_06, 0, 6);       /* state 0 */
    CHECK(fake_call_count == 3, "0/6 state 0 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 3,
          "0/6 state 0 doesn't set mode 3");
    CHECK(fake_calls[1].fn == FN_VERTICAL && fake_calls[1].s0 == -2.5f,
          "0/6 state 0 doesn't take the source's -5.0 halved");
    CHECK(ffrom(fake_mem_read32(work_06 + WORK_VERTICAL)) == -75.0f,
          "0/6 doesn't clamp the vertical value at -75.0");
    CHECK(fake_calls[2].fn == FN_REQUEST && fake_calls[2].r1 == REQUEST_0_6
          && fake_calls[2].s0 == FALL_RATE,
          "0/6 state 0 doesn't request motion 0x1b at 6.0");

    fake_reset_calls();
    fake_flag = 1;
    fake_mem_write32(work_06 + WORK_VERTICAL, 0);
    frame_with(enemy_06, work_06, 0, 6);       /* state 1 */
    CHECK(fake_call_count == 4, "0/6 state 1 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_VERTICAL, "0/6 state 1 doesn't step the vertical value");
    CHECK(fake_calls[1].fn == FN_FLAG, "0/6 state 1 doesn't wait for the flag");
    CHECK(fake_calls[2].fn == FN_MODE && fake_calls[2].r1 == 3,
          "0/6's base handler doesn't set mode 3");
    CHECK(fake_calls[3].fn == FN_SET_ACTION && fake_calls[3].r2 == 6,
          "0/6's base handler doesn't start action 0/6");

    /* The delay keeps 0/0 in its first state while the countdown is not spent. */
    const uint32_t enemy_c = 0x110000u, work_c = 0x120000u;
    spawn(enemy_c, work_c, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(enemy_c, work_c, 0, 0);         /* state 0 */
    fake_reset_calls();
    fake_countdown = 0;
    frame_with(enemy_c, work_c, 0, 0);         /* state 1, the delay still running */
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_COUNTDOWN,
          "0/0 runs past its delay (%d calls)", fake_call_count);
    fake_countdown = 1;

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 0's six ids and three base handlers make their calls\n");
    return 0;
}
