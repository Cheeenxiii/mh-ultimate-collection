/*
 * cat1.c: category 1's fake-host test — 1/0 to 1/14.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/ and
 * builds it as tests/family-<stem>, so a slice adds its test file and edits nothing shared.
 * The shell's test (tests/test_rathian_3u.c) covers the factory association, the routing, the
 * ready line and the self-test; this one drives the fifteen ids' call sequences on the fake
 * host.
 *
 * The expected addresses and frame values are written here and in tests/rathian-3u/host.h,
 * not read from the module, so a change in a handler fails the test instead of moving the
 * expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* MH4U's counterparts for this family's engine calls (host.h holds category 0's). */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion (r1, speed s0) */
#define FN_MODE_CLEAR   0x0091aae4u /* [0x0083336c] the flag-clear query, its r0 tested */
#define FN_REQUEST_NEXT 0x0094ef64u /* [0x0082a06c] request the next action (r1, r2) */
#define FN_SET_1_0      0x0093310cu /* [0x00844a40] 1/0's (1, 8, 5) */
#define FN_SET_1_0_2    0x00914dc4u /* [0x00844a38] 1/0's (0, 0x13) */
#define FN_1_4_SETUP    0x00922ca0u /* [0x0083d18c] 1/4's and 1/13's r1 = 0 byte */
#define FN_1_6_STEP     0x0093ba88u /* [0x0083c79c] 1/6's state 2 call */
#define FN_1_6_TAIL     0x0091b0f8u /* [0x0031be10] 1/6's state 1 tail */
#define FN_1_6_END      0x0093c938u /* [0x008440a4] 1/6's state 2 tail */

/* The work block's timer (3U's +0x28/+0x2c, host.h holds category 0's fields) and MH4U's
 * motion number, file << 8 | slot. */
#define WORK_TIMER 0x01d4u
#define TEST_MOTION(file, slot) (((uint32_t)(file) << 8) | ((uint32_t)(slot) & 0xffu))

static int fake_flag = 1;
static int fake_countdown = 1;
static int fake_query = 0;

/* What the engine answers category 1's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_COUNTDOWN:
        return (FakeResult){(uint32_t)fake_countdown, 0.0f};
    case FN_MODE_CLEAR:
        return (FakeResult){(uint32_t)fake_query, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* One call's function and integer argument, for a readable failure. */
static int call_fn(int i) {
    return i < fake_call_count ? (int)fake_calls[i].fn : -1;
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    fake_mem_write32(ACTION_EXTRA_GLOBAL, EXTRA_POINTER);
    fake_mem_write8(EXTRA_POINTER + 0x2fu, 0x7fu);

    /* ── 1/0 and 1/9: 0x00692834 ──────────────────────────────────────────────────── */
    const uint32_t enemy_10 = 0x30000u, work_10 = 0x40000u;
    spawn(enemy_10, work_10, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    fake_query = 0;
    frame_with(enemy_10, work_10, 1, 0);       /* state 0 */
    CHECK(fake_call_count == 3, "1/0 state 0 made %d calls, want 3", fake_call_count);
    CHECK(call_fn(0) == (int)FN_MODE && fake_calls[0].r1 == 0,
          "1/0 state 0 doesn't set mode 0");
    CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 5
          && fake_calls[1].s0 == 10.0f && fake_calls[1].s1 == 0.0f,
          "1/0 state 0 doesn't start motion 5 at 10.0");
    CHECK(call_fn(2) == (int)FN_SET_1_0_2 && fake_calls[2].r1 == 0
          && fake_calls[2].r2 == 0x13,
          "1/0 state 0 doesn't make its (0, 0x13) call");
    CHECK(ffrom(fake_mem_read32(work_10 + WORK_TIMER)) == 0.0f,
          "1/0 state 0 doesn't clear the accumulator");
    CHECK(fake_mem_read8(work_10 + WORK_STATE) == 1, "1/0 doesn't advance its state byte");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "1/0 didn't skip the dispatcher");

    /* state 1, every query false: the three queries and the flag, nothing else. */
    fake_reset_calls();
    frame_with(enemy_10, work_10, 1, 0);
    CHECK(fake_call_count == 4, "1/0 state 1 made %d calls, want 4", fake_call_count);
    CHECK(call_fn(0) == (int)FN_MODE_CLEAR && fake_calls[0].r1 == 0
          && fake_calls[0].s0 == 110.0f && fake_calls[0].s1 == 0.0f,
          "1/0's first 110.0 query isn't in the source's form");
    CHECK(call_fn(1) == (int)FN_MODE_CLEAR && fake_calls[1].s0 == 110.0f,
          "1/0's second 110.0 query isn't in the source's form");
    CHECK(call_fn(2) == (int)FN_MODE_CLEAR && fake_calls[2].r1 == 3
          && fake_calls[2].s0 == 112.0f && fake_calls[2].s1 == 214.0f,
          "1/0's 112.0/214.0 query isn't in the source's form");
    CHECK(call_fn(3) == (int)FN_FLAG, "1/0 state 1 doesn't test the finish flag");

    /* state 1, every query true: the (1, 8, 5) call and the accumulator. */
    fake_reset_calls();
    fake_query = 1;
    fake_mem_write32(enemy_10 + 0x14u, fbits(2.5f));
    frame_with(enemy_10, work_10, 1, 0);
    CHECK(fake_call_count == 5, "1/0's query-true frame made %d calls, want 5",
          fake_call_count);
    CHECK(call_fn(1) == (int)FN_SET_1_0 && fake_calls[1].r1 == 1 && fake_calls[1].r2 == 8
          && fake_calls[1].r3 == 5, "1/0 doesn't make its (1, 8, 5) call");
    CHECK(ffrom(fake_mem_read32(work_10 + WORK_TIMER)) == 2.5f,
          "1/0 doesn't add the frame delta to the accumulator");
    CHECK(fake_log_contains("0x0016052c"), "the #55-blocked effect isn't named in the log");
    CHECK(fake_log_contains("1/0, 1/4, 1/5, 1/7, 1/8, 1/9, 1/13 and 1/14"),
          "the blocked line doesn't name the eight affected ids");
    fake_reset_calls();
    frame_with(enemy_10, work_10, 1, 0);
    fake_clear_log();
    fake_reset_calls();
    frame_with(enemy_10, work_10, 1, 0);
    CHECK(!fake_log_contains("0x0016052c"), "the blocked effect is logged more than once");
    fake_query = 0;

    /* 1/9 shares the handler. */
    const uint32_t enemy_19 = 0x50000u, work_19 = 0x60000u;
    spawn(enemy_19, work_19, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(enemy_19, work_19, 1, 9);
    CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 5,
          "1/9 doesn't run the 1/0 handler");

    /* ── 1/1: its inline block ────────────────────────────────────────────────────── */
    const uint32_t enemy_11 = 0x70000u, work_11 = 0x80000u;
    spawn(enemy_11, work_11, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    frame_with(enemy_11, work_11, 1, 1);
    CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_MODE
          && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 0x12
          && fake_calls[1].s0 == 10.0f,
          "1/1 state 0 doesn't set mode 0 and start motion 0x12 at 10.0");
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_11, work_11, 1, 1);
    CHECK(call_fn(0) == (int)FN_FLAG && call_fn(1) == (int)FN_MODE
          && call_fn(2) == (int)FN_SET_ACTION,
          "1/1 state 1 doesn't fall into 0/2's base handler");

    /* ── 1/2: its inline block ────────────────────────────────────────────────────── */
    const uint32_t enemy_12 = 0x90000u, work_12 = 0xa0000u;
    spawn(enemy_12, work_12, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    frame_with(enemy_12, work_12, 1, 2);
    CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
          && fake_calls[1].r1 == TEST_MOTION(1, 0x18) && fake_calls[1].s0 == 2.0f,
          "1/2 state 0 doesn't start the source's 0x7c (file 1 slot 0x18) at 2.0");

    /* ── 1/3: its inline block ────────────────────────────────────────────────────── */
    const uint32_t enemy_13 = 0xb0000u, work_13 = 0xc0000u;
    spawn(enemy_13, work_13, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    fake_query = 0;
    frame_with(enemy_13, work_13, 1, 3);
    CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_MODE
          && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 2
          && fake_calls[1].s0 == 50.0f,
          "1/3 state 0 doesn't set mode 0 and start motion 2 at 50.0");
    fake_reset_calls();
    fake_query = 1;
    frame_with(enemy_13, work_13, 1, 3);
    CHECK(call_fn(0) == (int)FN_MODE_CLEAR && fake_calls[0].r1 == 1
          && fake_calls[0].s0 == 52.0f && call_fn(1) == (int)FN_MODE
          && call_fn(2) == (int)FN_SET_ACTION,
          "1/3 state 1 doesn't query at 52.0 and fall into 0/2's base handler");
    fake_query = 0;

    /* ── 1/4: 0x00692a1c with r1 = 0 ─────────────────────────────────────────────── */
    const uint32_t enemy_14 = 0xd0000u, work_14 = 0xe0000u;
    spawn(enemy_14, work_14, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    frame_with(enemy_14, work_14, 1, 4);
    CHECK(fake_call_count == 3, "1/4 state 0 made %d calls, want 3", fake_call_count);
    CHECK(call_fn(0) == (int)FN_1_4_SETUP,
          "1/4's r1 = 0 byte (0x0083d18c) isn't called first");
    CHECK(call_fn(1) == (int)FN_MODE && fake_calls[1].r1 == 0,
          "1/4 state 0 doesn't set mode 0");
    CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == 0x13
          && fake_calls[2].s0 == 6.0f, "1/4 state 0 doesn't start motion 0x13 at 6.0");
    CHECK(ffrom(fake_mem_read32(work_14 + WORK_TIMER)) == 3.0f,
          "1/4 doesn't arm the three-second timer");

    /* the timer running with the query false: the setup byte and the query, no countdown. */
    fake_mem_write32(work_14 + WORK_TIMER, fbits(5.0f));
    fake_reset_calls();
    frame_with(enemy_14, work_14, 1, 4);
    CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_1_4_SETUP
          && call_fn(1) == (int)FN_MODE_CLEAR && fake_calls[1].s0 == 176.0f,
          "1/4 state 1 doesn't make its setup call and the 176.0 query");

    /* the query true and the countdown still running: setup, query, countdown, return. */
    fake_mem_write32(work_14 + WORK_TIMER, fbits(5.0f));
    fake_reset_calls();
    fake_query = 1;
    fake_countdown = 0;
    frame_with(enemy_14, work_14, 1, 4);
    CHECK(fake_call_count == 3 && call_fn(2) == (int)FN_COUNTDOWN
          && fake_calls[2].r1 == work_14 + WORK_TIMER,
          "1/4 doesn't count its timer down");

    /* the query true and the countdown spent: the request for 1/5 (index 4). */
    fake_reset_calls();
    fake_countdown = 1;
    frame_with(enemy_14, work_14, 1, 4);
    CHECK(fake_call_count == 4 && call_fn(3) == (int)FN_REQUEST_NEXT
          && fake_calls[3].r1 == 1 && fake_calls[3].r2 == 5,
          "1/4 doesn't request 1/5 once its timer is spent");

    /* ── 1/13: the same unit with r1 = 0 and the 1/0x0e request ─────────────────── */
    const uint32_t enemy_113 = 0xf0000u, work_113 = 0x100000u;
    spawn(enemy_113, work_113, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_countdown = 1;
    frame_with(enemy_113, work_113, 1, 13);    /* state 0 */
    CHECK(call_fn(0) == (int)FN_1_4_SETUP, "1/13's r1 = 0 byte isn't called first");
    fake_reset_calls();
    frame_with(enemy_113, work_113, 1, 13);    /* state 1, the timer spent */
    CHECK(fake_call_count == 4 && call_fn(3) == (int)FN_REQUEST_NEXT
          && fake_calls[3].r2 == 0x0e,
          "1/13 doesn't request 1/0x0e");

    /* ── 1/7: 0x00692a1c with r1 = 1, the effect block ──────────────────────────── */
    const uint32_t enemy_17 = 0x110000u, work_17 = 0x120000u;
    spawn(enemy_17, work_17, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    fake_query = 0;
    frame_with(enemy_17, work_17, 1, 7);       /* state 0, then the effect block */
    CHECK(call_fn(0) == (int)FN_MODE && call_fn(1) == (int)FN_MOTION,
          "1/7 state 0 doesn't set mode 0 and start motion 0x13");
    CHECK(fake_calls[1].r1 == 0x13 && fake_calls[1].s0 == 6.0f,
          "1/7 state 0 doesn't start motion 0x13 at 6.0");
    CHECK(fake_call_count == 14, "1/7's effect block made %d calls, want 14",
          fake_call_count);
    CHECK(fake_calls[2].s0 == 92.0f && fake_calls[3].s0 == 262.0f
          && fake_calls[4].s0 == 96.0f
          && fake_calls[5].r1 == 3 && fake_calls[5].s0 == 136.0f
          && fake_calls[5].s1 == 152.0f,
          "1/7's first effect queries aren't in the source's order");
    CHECK(fake_calls[11].s0 == 398.0f && fake_calls[11].s1 == 426.0f
          && fake_calls[12].s0 == 458.0f && fake_calls[12].s1 == 478.0f
          && fake_calls[13].s0 == 434.0f,
          "1/7's last effect queries aren't in the source's order");
    CHECK(fake_mem_read8(work_17 + WORK_STATE) == 1, "1/7 doesn't advance its state byte");

    /* state 1 with the timer running: the 176.0 query, the effect block, no request. */
    fake_mem_write32(work_17 + WORK_TIMER, fbits(5.0f));
    fake_reset_calls();
    frame_with(enemy_17, work_17, 1, 7);
    CHECK(fake_call_count == 13, "1/7's waiting frame made %d calls, want 13",
          fake_call_count);
    CHECK(fake_calls[0].s0 == 176.0f, "1/7 doesn't make its 176.0 query first");
    CHECK(fake_calls[12].s0 == 434.0f, "1/7's waiting frame doesn't end on its last query");

    /* the timer spent: the request for 1/8, before the effect block. */
    fake_reset_calls();
    fake_query = 1;
    fake_countdown = 1;
    frame_with(enemy_17, work_17, 1, 7);
    CHECK(fake_call_count == 3 && call_fn(2) == (int)FN_REQUEST_NEXT
          && fake_calls[2].r2 == 8,
          "1/7 doesn't request 1/8 once its timer is spent");

    /* ── 1/5 and 1/14: 0x00692f14 with r1 = 0 ────────────────────────────────────── */
    const uint32_t enemy_15 = 0x130000u, work_15 = 0x140000u;
    spawn(enemy_15, work_15, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    fake_query = 0;
    frame_with(enemy_15, work_15, 1, 5);
    CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_MODE
          && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 0x14
          && fake_calls[1].s0 == 6.0f,
          "1/5 state 0 doesn't set mode 0 and start motion 0x14 at 6.0");
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_15, work_15, 1, 5);
    CHECK(fake_call_count == 3 && call_fn(0) == (int)FN_FLAG
          && call_fn(1) == (int)FN_MODE && call_fn(2) == (int)FN_SET_ACTION,
          "1/5 state 1 doesn't fall into 0/2's base handler");

    const uint32_t enemy_114 = 0x170000u, work_114 = 0x180000u;
    spawn(enemy_114, work_114, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_114, work_114, 1, 14);
    CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 0x14,
          "1/14 doesn't run the 1/5 handler");

    /* ── 1/8: 0x00692f14 with r1 = 1, the six effect queries ───────────────────── */
    const uint32_t enemy_18 = 0x150000u, work_18 = 0x160000u;
    spawn(enemy_18, work_18, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 0;
    fake_query = 0;
    frame_with(enemy_18, work_18, 1, 8);       /* state 0 */
    fake_reset_calls();
    frame_with(enemy_18, work_18, 1, 8);       /* state 1, every query false */
    CHECK(fake_call_count == 7, "1/8's waiting frame made %d calls, want 7",
          fake_call_count);
    CHECK(call_fn(0) == (int)FN_MODE_CLEAR && fake_calls[0].r1 == 0
          && fake_calls[0].s0 == 12.0f && fake_calls[0].s1 == 0.0f,
          "1/8's first effect query isn't in the source's form");
    CHECK(fake_calls[1].r1 == 3 && fake_calls[1].s0 == 16.0f && fake_calls[1].s1 == 40.0f
          && fake_calls[2].s0 == 46.0f
          && fake_calls[3].r1 == 3 && fake_calls[3].s0 == 50.0f && fake_calls[3].s1 == 66.0f,
          "1/8's middle effect queries aren't in the source's form");
    CHECK(fake_calls[4].s0 == 72.0f
          && fake_calls[5].r1 == 3 && fake_calls[5].s0 == 76.0f && fake_calls[5].s1 == 112.0f,
          "1/8's last effect queries aren't in the source's form");
    CHECK(call_fn(6) == (int)FN_FLAG, "1/8 state 1 doesn't test the finish flag last");

    /* ── 1/6: 0x0069322c, three states ──────────────────────────────────────────── */
    const uint32_t enemy_16 = 0x190000u, work_16 = 0x1a0000u;
    spawn(enemy_16, work_16, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_16, work_16, 1, 6);       /* state 0 */
    CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
          && fake_calls[1].r1 == 0x17 && fake_calls[1].s0 == 6.0f,
          "1/6 state 0 doesn't start motion 0x17 at 6.0");
    fake_reset_calls();
    frame_with(enemy_16, work_16, 1, 6);       /* state 1 */
    CHECK(fake_call_count == 3, "1/6 state 1 made %d calls, want 3", fake_call_count);
    CHECK(call_fn(0) == (int)FN_FLAG, "1/6 state 1 doesn't test the finish flag");
    CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == 0x18
          && fake_calls[1].s0 == 0.0f, "1/6 state 1 doesn't start motion 0x18 at 0.0");
    CHECK(call_fn(2) == (int)FN_1_6_TAIL, "1/6 state 1 doesn't make its (0x0031be10) call");
    CHECK(ffrom(fake_mem_read32(work_16 + WORK_TIMER)) == 1800.0f,
          "1/6 state 1 doesn't arm the 1800.0 timer");
    fake_reset_calls();
    fake_countdown = 1;
    frame_with(enemy_16, work_16, 1, 6);       /* state 2 */
    CHECK(fake_call_count == 4, "1/6 state 2 made %d calls, want 4", fake_call_count);
    CHECK(call_fn(0) == (int)FN_1_6_STEP && fake_calls[0].r1 == 1 && fake_calls[0].r2 == 0x0a
          && fake_calls[0].s0 == 0.6f, "1/6 state 2 doesn't make its (1, 0xa, 0.6) call");
    CHECK(call_fn(1) == (int)FN_COUNTDOWN && fake_calls[1].r1 == work_16 + WORK_TIMER,
          "1/6 state 2 doesn't count its timer down");
    CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == 0x19
          && fake_calls[2].s0 == 4.0f, "1/6 state 2 doesn't start motion 0x19 at 4.0");
    CHECK(call_fn(3) == (int)FN_1_6_END, "1/6 state 2 doesn't make its (0x008440a4) call");
    fake_reset_calls();
    frame_with(enemy_16, work_16, 1, 6);       /* state 3 */
    CHECK(call_fn(0) == (int)FN_FLAG && call_fn(1) == (int)FN_MODE
          && call_fn(2) == (int)FN_SET_ACTION,
          "1/6 state 3 doesn't fall into 0/2's base handler");

    /* ── 1/10: its inline block, reusing cat0's base handler ────────────────────── */
    const uint32_t enemy_110 = 0x1b0000u, work_110 = 0x1c0000u;
    spawn(enemy_110, work_110, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_110, work_110, 1, 10);
    CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
          && fake_calls[1].r1 == 0x11 && fake_calls[1].s0 == 6.0f,
          "1/10 state 0 doesn't start motion 0x11 at 6.0");
    fake_reset_calls();
    frame_with(enemy_110, work_110, 1, 10);
    CHECK(call_fn(0) == (int)FN_FLAG && call_fn(1) == (int)FN_MODE
          && call_fn(2) == (int)FN_SET_ACTION,
          "1/10 state 1 doesn't fall into 0/2's base handler");

    /* ── 1/11 and 1/12: 0x00693388, the two variants ────────────────────────────── */
    const uint32_t enemy_111 = 0x1d0000u, work_111 = 0x1e0000u;
    spawn(enemy_111, work_111, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_111, work_111, 1, 11);
    CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
          && fake_calls[1].r1 == 1 && fake_calls[1].s0 == 10.0f,
          "1/11 state 0 doesn't start motion 1 at 10.0");
    CHECK(ffrom(fake_mem_read32(work_111 + WORK_TIMER)) == 20.0f,
          "1/11 doesn't arm the 20.0 timer");
    fake_reset_calls();
    frame_with(enemy_111, work_111, 1, 11);    /* state 1, the flag set */
    CHECK(fake_call_count == 3 && call_fn(0) == (int)FN_FLAG
          && call_fn(1) == (int)FN_MODE && call_fn(2) == (int)FN_SET_ACTION,
          "1/11 state 1 doesn't fall into 0/2's base handler");

    const uint32_t enemy_112 = 0x1f0000u, work_112 = 0x200000u;
    spawn(enemy_112, work_112, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    fake_flag = 1;
    frame_with(enemy_112, work_112, 1, 12);
    CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
          && fake_calls[1].r1 == 0x11 && fake_calls[1].s0 == 6.0f,
          "1/12 state 0 doesn't start motion 0x11 at 6.0");
    fake_reset_calls();
    fake_flag = 0;
    fake_countdown = 1;
    frame_with(enemy_112, work_112, 1, 12);    /* state 1, the timer spent */
    CHECK(fake_call_count == 4 && call_fn(0) == (int)FN_FLAG
          && call_fn(1) == (int)FN_COUNTDOWN && fake_calls[1].r1 == work_112 + WORK_TIMER
          && call_fn(2) == (int)FN_MODE && call_fn(3) == (int)FN_SET_ACTION,
          "1/12's spent timer doesn't fall into 0/2's base handler");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 1's fifteen ids make their calls\n");
    return 0;
}
