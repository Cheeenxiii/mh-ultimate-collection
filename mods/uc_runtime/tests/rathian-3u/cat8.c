/*
 * cat8.c: category 8 on the fake host — id 8, her handler 0x00687074.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/
 * and builds it as tests/family-<stem>, so a slice adds its test file and edits nothing shared.
 * The shell's test (tests/test_rathian_3u.c) covers the factory association, the routing, the
 * ready line and the self-test; this one drives 8's three states' call sequences.
 *
 * The expected addresses, constants and frame values are written here and in
 * tests/rathian-3u/host.h, not read from the module, so a change in a handler fails the test
 * instead of moving the expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The work-block fields category 8 reads beyond host.h's list (MH4U's offsets). */
#define WORK_SUB   0x0145u  /* 3U +0x6 */
#define WORK_TIMER 0x01d4u  /* 3U +0x28 */
#define WORK_TAIL  0x7993u  /* 3U +0xe1 */
#define WORK_CAP   0x03ecu  /* 3U +0x7fc */
#define WORK_SIDE  0x0278u  /* the hit check's side byte */
#define WORK_PART  0x027cu  /* 3U +0x2b6: the hit check's target index */
#define WORK_TARGET 0x0218u /* 3U +0x288 */
#define WORK_AIM   0x0160u  /* 3U +0x260 */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_DATA_SETUP 0x00911c0cu /* [0x0082d278] */
#define FN_AIM        0x00948674u /* [0x0068d070] */
#define FN_RANGE      0x0091aae4u /* [0x0083336c] */
#define FN_ADVANCE    0x00955440u /* [0x0082b268] */
#define FN_TAIL_DATA  0x0092f6e8u /* [0x0082d430] */
#define FN_MOTION     0x0094e318u /* [0x00828828] */
#define FN_COUNTDOWN  0x00b0704cu
#define FN_HIT_CHECK  0x009122fcu /* [0x00687ae0] */
#define FN_NEXT_ACTION 0x0094ef64u /* [0x0082a06c] */
#define FN_STATE_TEST 0x0092e960u /* [0x00844100] */
#define FN_RATE_ACCUM 0x00944c34u /* [0x00853b98] */
#define FN_PART_STEP  0x0091b7b0u /* [0x008345f8] */
#define FN_APPLY_VALUE 0x0093b9ecu /* [0x0083c7a0] */

/* MH4U's own action-start list, which its own 8/0 handler (0x006e9770) passes. */
#define MH4U_ACTION_LIST 0x00e094d8u

/* 8's frame values and its motion, in MH4U's `file << 8 | slot` form. */
#define AIM_SPEED   300.0f
#define AIM_HEIGHT   38.0f
#define RANGE_SPEED  12.0f
#define RANGE_HEIGHT 50.0f
#define ADVANCE_HALF  0.5f
#define TIMER_3U     90.0f
#define MOTION_SPEED 90.0f
#define HIT_RANGE   300.0f
#define HIT_HEIGHT  150.0f
#define MOTION_8     0xcau

static int fake_flag = 1;
static int fake_range = 1;
static int fake_hit = 1;
static int fake_state = 1;

/* What the engine answers category 8's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_RANGE:
        return (FakeResult){(uint32_t)fake_range, 0.0f};
    case FN_HIT_CHECK:
        return (FakeResult){(uint32_t)fake_hit, 0.0f};
    case FN_STATE_TEST:
        return (FakeResult){(uint32_t)fake_state, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* Check one guest call's function. */
#define CALL(i, want) do { \
    CHECK(fake_calls[i].fn == (want), "call %d is 0x%08x, want 0x%08x", (i), \
          (unsigned)fake_calls[i].fn, (unsigned)(want)); \
} while (0)

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    const uint32_t enemy = 0x30000u, work = 0x40000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);

    /* ── state 0: mode 0, the data setup, the aim at 300.0/38.0 ─────────────────────── */
    fake_reset_calls();
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 3, "8 state 0 made %d calls, want 3", fake_call_count);
    CALL(0, FN_MODE);
    CHECK(fake_calls[0].r1 == 0, "8 doesn't set mode 0");
    CALL(1, FN_DATA_SETUP);
    CHECK(fake_calls[1].r1 == MH4U_ACTION_LIST && fake_calls[1].r2 == 0
          && fake_calls[1].r3 == 1, "8 doesn't pass MH4U's own action-start list");
    CHECK(fake_calls[1].has_r4 && fake_calls[1].r4 == 0,
          "the data setup's fifth stack argument isn't set");
    CALL(2, FN_AIM);
    CHECK(fake_calls[2].r1 == work + WORK_AIM && fake_calls[2].r2 == work + WORK_TARGET
          && fake_calls[2].s0 == AIM_SPEED && fake_calls[2].s1 == AIM_HEIGHT,
          "8 doesn't aim at the target at 300.0/38.0");
    CHECK(fake_mem_read8(work + WORK_STATE) == 1 && fake_mem_read8(work + WORK_SUB) == 0,
          "8 doesn't set its state and sub-state");
    CHECK(fake_log_contains("0x00853c70"), "8 doesn't log the blocked 0x00853c70");
    CHECK(fake_log_contains("0x00257628"), "8 doesn't log the blocked 0x00257628");

    /* ── state 1: the distance test, the advance and the leaf, then the flag ─────────── */
    fake_reset_calls();
    fake_range = 1;
    fake_flag = 0;
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 4, "8 state 1 made %d calls, want 4", fake_call_count);
    CALL(0, FN_RANGE);
    CHECK(fake_calls[0].r1 == 3 && fake_calls[0].s0 == RANGE_SPEED
          && fake_calls[0].s1 == RANGE_HEIGHT, "8 doesn't take the source's 12.0/50.0");
    CALL(1, FN_ADVANCE);
    CHECK(fake_calls[1].s0 == ADVANCE_HALF,
          "8 doesn't halve the source's 1.0 position advance");
    CALL(2, FN_TAIL_DATA);
    CHECK(fake_calls[2].r1 == MH4U_ACTION_LIST, "8's leaf doesn't take MH4U's own list");
    CALL(3, FN_FLAG);

    fake_reset_calls();
    fake_range = 0;
    fake_flag = 1;
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 3, "8's finished distance test made %d calls, want 3",
          fake_call_count);
    CALL(0, FN_RANGE);
    CALL(1, FN_FLAG);
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == MOTION_8 && fake_calls[2].s0 == MOTION_SPEED,
          "8 doesn't request motion 0xca at 90.0");
    CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == TIMER_3U,
          "8 doesn't arm the 90.0 timer");
    CHECK(fake_mem_read8(work + WORK_STATE) == 2, "8 doesn't move to state 2");

    /* ── state 2: the countdown, the hit check, the part step and 9/1 ────────────────── */
    fake_mem_write32(work + WORK_TIMER, fbits(5.0f));
    fake_mem_write32(work + WORK_CAP, 100);
    fake_mem_write8(work + WORK_PART, 2);
    fake_mem_write8(work + WORK_SIDE, 1);
    fake_reset_calls();
    fake_hit = 1;
    fake_state = 1;
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 6, "8 state 2 made %d calls, want 6", fake_call_count);
    CALL(0, FN_COUNTDOWN);
    CHECK(fake_calls[0].r1 == work + WORK_TIMER, "8 doesn't count its 90.0 timer down");
    CALL(1, FN_HIT_CHECK);
    CHECK(fake_calls[1].r1 == 2 && fake_calls[1].r2 == 1,
          "8's hit check doesn't take the part and side bytes");
    CHECK(fake_calls[1].has_s2 && fake_calls[1].s0 == HIT_RANGE && fake_calls[1].s1 == 0.0f
          && fake_calls[1].s2 == HIT_HEIGHT,
          "8's hit check isn't at 300.0/0.0/150.0");
    CALL(2, FN_STATE_TEST);
    CALL(3, FN_RATE_ACCUM);
    CHECK(fake_calls[3].s0 == -900.0f, "8's state step doesn't take the source's -900.0");
    CALL(4, FN_APPLY_VALUE);
    CHECK(fake_calls[4].r1 == 1, "8's part step doesn't scale the count by 0.015 (r1=%u)",
          (unsigned)fake_calls[4].r1);
    CALL(5, FN_NEXT_ACTION);
    CHECK(fake_calls[5].r1 == 9 && fake_calls[5].r2 == 1, "8's hit doesn't ask for 9/1");
    CHECK(fake_mem_read8(work + WORK_TAIL) == 3, "8 doesn't set the tail flag to 3");
    CHECK(fake_log_contains("0x00839598"), "8 doesn't log the blocked 0x00839598");
    CHECK(fake_log_contains("0x0084512c"), "8 doesn't log the blocked 0x0084512c");

    /* The state test's other branch: the part step at 0x32, then the same accumulator. */
    fake_reset_calls();
    fake_state = 0;
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 6, "8's part-step branch made %d calls, want 6", fake_call_count);
    CALL(2, FN_STATE_TEST);
    CALL(3, FN_PART_STEP);
    CHECK(fake_calls[3].r1 == 0x32, "8's part step doesn't take 0x32");
    CALL(4, FN_APPLY_VALUE);

    /* ── the hit check's failure asks for 2/6 ────────────────────────────────────────── */
    fake_reset_calls();
    fake_hit = 0;
    fake_state = 1;
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 3, "8's failed hit check made %d calls, want 3", fake_call_count);
    CALL(0, FN_COUNTDOWN);
    CALL(1, FN_HIT_CHECK);
    CALL(2, FN_NEXT_ACTION);
    CHECK(fake_calls[2].r1 == 2 && fake_calls[2].r2 == 6,
          "8's failed hit check doesn't ask for 2/6");

    /* The timer is clamped at 0 after the countdown. */
    fake_mem_write32(work + WORK_TIMER, fbits(-5.0f));
    fake_reset_calls();
    fake_hit = 0;
    frame_with(enemy, work, 8, 0);
    CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 0.0f,
          "8 doesn't clamp its timer at 0");

    /* A state other than 0, 1 and 2 does nothing. */
    fake_mem_write8(work + WORK_STATE, 3);
    fake_reset_calls();
    frame_with(enemy, work, 8, 0);
    CHECK(fake_call_count == 0, "8's state 3 made %d calls, want 0", fake_call_count);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 8 makes its calls across id 8's three states\n");
    return 0;
}
