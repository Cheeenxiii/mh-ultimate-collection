/*
 * cat3.c: category 3's fake-host test — 3/0, 3/1, 3/2, 3/4, 3/5, 3/9, 3/10, 3/11, 3/14,
 * 3/15, 3/22, 3/23, 3/26, 3/30 and action 12.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-3u/ and builds it as tests/family-<stem>, so a slice adds its test file and
 * edits nothing shared. The shell's test (tests/test_rathian_3u.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the fifteen
 * ids' call sequences on the fake host.
 *
 * The expected addresses, constants and frame values are written here, not read from the
 * module, so a change in a handler fails the test instead of moving the expectation with it.
 * host.h holds the constants cat0's test shares; this file names category 3's own, because
 * the slice adds only its two files.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <math.h>

#include "host.h"

/* The MH4U work offsets category 3 reads (host.h's are cat0's; the overlapping names keep
 * the same values). */
#define WORK_SUB        0x0145u
#define WORK_SUB2       0x0146u
#define WORK_TURN       0x01a8u
#define WORK_HEADING    0x01acu
#define WORK_POS        0x0198u
#define WORK_TARGET     0x0218u
#define WORK_OTHER      0x034cu
#define WORK_RATE_DELTA 0x0394u
#define WORK_TAIL       0x7993u
#define WORK_SELECT     0x014cu
#define WORK_3_5_ACTIVE 0x01eeu
#define WORK_3_5_TIMER  0x0520u
#define WORK_3_5_LAST   0x0202u
#define WORK_3_5_PART   0x027cu
#define ENEMY_SPEED     0x0290u

/* The MH4U engine functions category 3 calls. */
#define FN_MOTION       0x0094e318u
#define FN_CLEAR_AIM    0x00916228u
#define FN_TURN         0x0091656cu
#define FN_TURN_TO      0x0091db4cu
#define FN_SET_ACTION_1 0x0092b140u
#define FN_SET_ACTION_2 0x00935a90u
#define FN_NEXT_ACTION  0x0094ef64u
#define FN_MARK         0x00922ca0u
#define FN_PREDICATE    0x0092dcccu
#define FN_HIT_START    0x0092dc50u
#define FN_LOOP         0x00947d0cu
#define FN_END          0x00939988u
#define FN_RATE_A       0x0093cd70u
#define FN_RATE_B       0x0093ce60u
#define FN_HOLD_CHECK   0x00942220u
#define FN_TURN_RATE    0x00918e48u
#define FN_ANGLE        0x00568c64u
#define FN_DIST2        0x00aacd84u
#define FN_STATE_PRED   0x0092e960u
#define FN_AIM_ADVANCE  0x00918ef0u
#define FN_HIT_CHECK    0x00935fb8u
#define FN_PART_FLAG    0x0092e4f8u
#define FN_HIT_SETUP    0x00916b94u

/* The source's frame values. */
#define MOTION_3_START    0x29u
#define MOTION_3_SECOND   0x43u
#define MOTION_3_0_THIRD  0x1au
#define MOTION_3_2_START  0x1au
#define MOTION_3_2_SECOND 0x1du
#define MOTION_3_2_THIRD  0x2eu
#define MOTION_3_2_FOURTH 0x41u
#define MOTION_3_4_START  0x1fu
#define MOTION_3_10_START 0x2du
#define MOTION_3_11_START 0x1fu
#define DATA_VALUE        1.5f
#define TURN_RATE_3_4     0.04f

static int fake_flag = 1;
static int fake_countdown = 1;
static int fake_predicate = 1;
static int fake_hold = 1;
static int fake_state_pred = 1;
static int fake_loop = 1;
static uint32_t fake_angle;
static float fake_dist2;
static float fake_data = DATA_VALUE;

/* What the engine answers category 3's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_COUNTDOWN:
        return (FakeResult){(uint32_t)fake_countdown, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0, fake_data};
    case FN_DATA_GET:
        return (FakeResult){RECORD_ADDRESS, 0.0f};
    case FN_PREDICATE:
        return (FakeResult){(uint32_t)fake_predicate, 0.0f};
    case FN_HOLD_CHECK:
        return (FakeResult){(uint32_t)fake_hold, 0.0f};
    case FN_STATE_PRED:
        return (FakeResult){(uint32_t)fake_state_pred, 0.0f};
    case FN_ANGLE:
        return (FakeResult){fake_angle, 0.0f};
    case FN_DIST2:
        return (FakeResult){0, fake_dist2};
    case FN_LOOP:
        return (FakeResult){(uint32_t)fake_loop, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

static void check_call(int i, uint32_t fn, const char *what) {
    CHECK(i < fake_call_count && fake_calls[i].fn == fn, "%s (call %d is 0x%08x)", what, i,
          i < fake_call_count ? fake_calls[i].fn : 0u);
}

static void check_count(int want, const char *what) {
    if (fake_call_count != want) {
        fprintf(stderr, "  %s made %d calls, want %d: ", what, fake_call_count, want);
        for (int i = 0; i < fake_call_count; i++) {
            fprintf(stderr, "0x%08x ", fake_calls[i].fn);
        }
        fprintf(stderr, "\n");
        fail("%s made %d calls, want %d", what, fake_call_count, want);
    }
}

/* No blocked source function is ever called: these are MH3U addresses, and none is a
 * function the module may run. */
static void check_no_blocked(const char *what) {
    static const uint32_t blocked[] = {0x0083db24u, 0x00833234u, 0x00835f10u, 0x0083dc14u,
                                       0x00a347bcu, 0x00842a7cu, 0x00938748u, 0x00938834u,
                                       0x00922250u};
    for (int c = 0; c < fake_call_count; c++) {
        for (unsigned b = 0; b < sizeof blocked / sizeof blocked[0]; b++) {
            CHECK(fake_calls[c].fn != blocked[b], "%s called blocked 0x%08x", what,
                  blocked[b]);
        }
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

    /* The action setters read MH4U's own per-action global; point it at memory the test owns,
     * as cat0's test does for the 0/2 and 0/3 base handlers. */
    fake_mem_write32(ACTION_EXTRA_GLOBAL, EXTRA_POINTER);
    fake_mem_write8(EXTRA_POINTER + 0x2fu, 0x7fu);

    /* ── 3/0: four states ── */
    {
        const uint32_t enemy = 0x30000u, work = 0x40000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);

        fake_reset_calls();
        frame_with(enemy, work, 3, 0);
        check_count(2, "3/0 state 0");
        check_call(0, FN_MODE, "3/0 state 0 doesn't set mode 0");
        CHECK(fake_calls[0].r1 == 0, "3/0 state 0 mode is %u, want 0", fake_calls[0].r1);
        check_call(1, FN_MOTION, "3/0 state 0 doesn't start a motion");
        CHECK(fake_calls[1].r1 == MOTION_3_START && fake_calls[1].s0 == 6.0f
              && fake_calls[1].s1 == 0.0f,
              "3/0 state 0 motion is 0x%x at %g/%g, want 0x29 at 6/0", fake_calls[1].r1,
              fake_calls[1].s0, fake_calls[1].s1);
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "3/0 doesn't advance its state byte");

        fake_reset_calls();
        frame_with(enemy, work, 3, 0);
        check_count(5, "3/0 state 1");
        check_call(0, FN_FLAG, "3/0 state 1 doesn't wait for the finish flag");
        check_call(1, FN_DATA_FLOAT, "3/0 state 1 doesn't read the data float");
        check_call(2, FN_APPLY_FALL, "3/0 state 1 doesn't apply the fall");
        CHECK(fake_calls[2].s0 == DATA_VALUE, "3/0's fall takes %g, want the data float %g",
              fake_calls[2].s0, DATA_VALUE);
        check_call(3, FN_MOTION, "3/0 state 1 doesn't start the second motion");
        CHECK(fake_calls[3].r1 == MOTION_3_SECOND && fake_calls[3].s0 == 0.0f,
              "3/0's second motion is 0x%x at %g, want 0x43 at 0", fake_calls[3].r1,
              fake_calls[3].s0);
        check_call(4, FN_CLEAR_AIM, "3/0 state 1 doesn't clear the aim point");

        fake_reset_calls();
        fake_clear_log();
        frame_with(enemy, work, 3, 0);
        check_count(4, "3/0 state 2");
        /* The curve is logged the first time state 2 runs. */
        CHECK(fake_log_contains("0x00c4ed80"), "3/0 doesn't log the skipped value curve");
        check_call(0, FN_DATA_FLOAT, "3/0 state 2 doesn't read the data float");
        check_call(1, FN_TURN, "3/0 state 2 doesn't run the turn");
        CHECK(fake_calls[1].r1 == work + WORK_TURN && fake_calls[1].s0 == DATA_VALUE
              && fake_calls[1].s1 == 1.0f,
              "3/0's turn is (%08x, %g, %g), want (work+0x1a8, 1.5, 1)", fake_calls[1].r1,
              fake_calls[1].s0, fake_calls[1].s1);
        check_call(2, FN_FLAG, "3/0 state 2 doesn't wait for the flag");
        check_call(3, FN_MOTION, "3/0 state 2 doesn't start the third motion");
        CHECK(fake_calls[3].r1 == MOTION_3_0_THIRD && fake_calls[3].s0 == 6.0f,
              "3/0's third motion is 0x%x at %g, want 0x1a at 6", fake_calls[3].r1,
              fake_calls[3].s0);

        fake_reset_calls();
        frame_with(enemy, work, 3, 0);
        check_count(3, "3/0 state 3");
        check_call(0, FN_TURN_TO, "3/0 state 3 doesn't turn toward the target");
        CHECK(fake_calls[0].r1 == 0x100, "3/0's turn step is 0x%x, want 0x100",
              fake_calls[0].r1);
        check_call(1, FN_FLAG, "3/0 state 3 doesn't wait for the flag");
        check_call(2, FN_SET_ACTION_1, "3/0 state 3 doesn't set the immediate action");
        CHECK(fake_calls[2].r1 == 3 && fake_calls[2].r2 == 2,
              "3/0's immediate action is %u/%u, want 3/2", fake_calls[2].r1,
              fake_calls[2].r2);
        check_no_blocked("3/0");
    }

    /* ── 3/1: the same opening, then the 0/3 base handler ── */
    {
        const uint32_t enemy = 0x50000u, work = 0x60000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work + WORK_KIND, 0x20);
        fake_mem_write8(work + WORK_DATA_INDEX, 7);
        fake_mem_write32(RECORD_ADDRESS + 0x64u, fbits(4.0f));

        fake_reset_calls();
        frame_with(enemy, work, 3, 1);
        check_count(2, "3/1 state 0");
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == MOTION_3_START
              && fake_calls[1].s0 == 6.0f,
              "3/1 state 0 doesn't start motion 0x29 at 6");

        fake_reset_calls();
        frame_with(enemy, work, 3, 1);
        check_count(5, "3/1 state 1");
        CHECK(fake_calls[2].fn == FN_APPLY_FALL && fake_calls[2].s0 == DATA_VALUE,
              "3/1 state 1 doesn't apply the data float to the fall");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_3_SECOND
              && fake_calls[3].s0 == 0.0f,
              "3/1 state 1 doesn't start motion 0x43 at 0");

        fake_reset_calls();
        frame_with(enemy, work, 3, 1);
        check_count(6, "3/1 state 2");
        CHECK(fake_calls[0].fn == FN_DATA_FLOAT && fake_calls[1].fn == FN_TURN
              && fake_calls[1].s0 == DATA_VALUE,
              "3/1 state 2 doesn't turn with the data float");
        check_call(2, FN_FLAG, "3/1 state 2 doesn't wait for the flag");
        check_call(3, FN_DATA_GET, "3/1's 0/3 base handler doesn't look the record up");
        check_call(4, FN_MODE, "3/1's 0/3 base handler doesn't set mode 1");
        CHECK(fake_calls[4].r1 == 1, "3/1's 0/3 base handler mode is %u, want 1",
              fake_calls[4].r1);
        check_call(5, FN_SET_ACTION, "3/1's 0/3 base handler doesn't start the action");
        CHECK(fake_calls[5].r2 == 3 && fake_calls[5].r3 == 2,
              "3/1's 0/3 base handler starts %u/%u, want 0/3 (kind 2)", fake_calls[5].r1,
              fake_calls[5].r2);
        check_no_blocked("3/1");
    }

    /* ── 3/2 and 12: the five states ── */
    {
        const uint32_t enemy = 0x70000u, work = 0x80000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);

        fake_reset_calls();
        frame_with(enemy, work, 3, 2);
        check_count(4, "3/2 state 0");
        CHECK(fake_calls[0].fn == FN_DATA_FLOAT && fake_calls[1].fn == FN_APPLY_FALL
              && fake_calls[1].s0 == DATA_VALUE,
              "3/2 state 0 doesn't apply the data float to the fall");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_3_2_START
              && fake_calls[2].s0 == 6.0f,
              "3/2 state 0 doesn't start motion 0x1a at 6");
        check_call(3, FN_RATE_A, "3/2 state 0 doesn't run 0x008509a0's step");

        fake_reset_calls();
        fake_hold = 0;
        frame_with(enemy, work, 3, 2);
        check_count(3, "3/2 state 1 with the hold test failing");
        CHECK(fake_calls[0].fn == FN_RATE_B, "3/2 state 1 doesn't run 0x00850a50's step");
        CHECK(fake_calls[1].fn == FN_DATA_FLOAT && fake_calls[2].fn == FN_HOLD_CHECK
              && fake_calls[2].s0 == DATA_VALUE,
              "3/2 state 1 doesn't pass the data float to the 0x0083369c test");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "3/2 advances on a failed hold test");

        fake_reset_calls();
        fake_hold = 1;
        frame_with(enemy, work, 3, 2);
        check_count(5, "3/2 state 1 with the hold test passing");
        CHECK(fake_calls[3].fn == FN_MODE && fake_calls[3].r1 == 3,
              "3/2 state 1 doesn't set mode 3");
        CHECK(fake_calls[4].fn == FN_MOTION && fake_calls[4].r1 == MOTION_3_2_SECOND
              && fake_calls[4].s0 == 6.0f,
              "3/2 state 1 doesn't start motion 0x1d at 6");
        (void)fake_calls[5];

        fake_reset_calls();
        frame_with(enemy, work, 3, 2);
        check_count(2, "3/2 state 2");
        CHECK(fake_calls[0].fn == FN_FLAG && fake_calls[1].fn == FN_MOTION
              && fake_calls[1].r1 == MOTION_3_2_THIRD && fake_calls[1].s0 == 6.0f,
              "3/2 state 2 doesn't start motion 0x2e at 6");

        fake_reset_calls();
        frame_with(enemy, work, 3, 2);
        check_count(3, "3/2 state 3");
        CHECK(fake_calls[0].fn == FN_FLAG && fake_calls[1].fn == FN_MODE
              && fake_calls[1].r1 == 0,
              "3/2 state 3 doesn't set mode 0");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_3_2_FOURTH
              && fake_calls[2].s0 == 0.0f,
              "3/2 state 3 doesn't start motion 0x41 at 0");

        fake_reset_calls();
        frame_with(enemy, work, 3, 2);
        check_count(3, "3/2 state 4");
        CHECK(fake_calls[0].fn == FN_FLAG, "3/2 state 4 doesn't wait for the flag");
        CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 0,
              "3/2 state 4 doesn't fall into 0/2's mode 0");
        CHECK(fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r3 == 2,
              "3/2 state 4 doesn't fall into 0/2's base handler");
        check_no_blocked("3/2");

        /* Action 12 runs the same handler. */
        const uint32_t enemy12 = 0x90000u, work12 = 0xa0000u;
        spawn(enemy12, work12, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy12, work12, 12, 0);
        check_count(4, "12 state 0");
        CHECK(fake_calls[0].fn == FN_DATA_FLOAT && fake_calls[2].fn == FN_MOTION,
              "12 doesn't run 3/2's state 0");
    }

    /* ── 3/4: the angle and the part check ── */
    {
        const uint32_t enemy = 0xb0000u, work = 0xc0000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);

        fake_reset_calls();
        frame_with(enemy, work, 3, 4);
        check_count(4, "3/4 state 0");
        CHECK(fake_calls[0].fn == FN_DATA_FLOAT && fake_calls[1].fn == FN_APPLY_FALL
              && fake_calls[1].s0 == DATA_VALUE,
              "3/4 state 0 doesn't apply the data float to the fall");
        check_call(2, FN_AIM_ADVANCE, "3/4 state 0 doesn't advance the aim point");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_3_4_START
              && fake_calls[3].s0 == 0.0f,
              "3/4 state 0 doesn't start motion 0x1f at 0");

        fake_mem_write32(work + WORK_POS, fbits(10.0f));
        fake_mem_write32(work + WORK_POS + 8u, fbits(20.0f));
        fake_mem_write32(work + WORK_TARGET, fbits(13.0f));
        fake_mem_write32(work + WORK_TARGET + 8u, fbits(24.0f));
        fake_mem_write32(work + WORK_HEADING, 0);
        fake_mem_write32(work + WORK_RATE_DELTA, fbits(0.5f));
        fake_mem_write32(enemy + ENEMY_SPEED, fbits(2.7f));
        fake_angle = 6554u;                     /* 36 degrees in MH3U's angle units */
        fake_clear_log();
        fake_reset_calls();
        frame_with(enemy, work, 3, 4);
        check_count(3, "3/4 state 1");
        check_call(0, FN_ANGLE, "3/4 state 1 doesn't take the angle to the target");
        CHECK(fake_calls[0].s0 == 3.0f && fake_calls[0].s1 == 4.0f,
              "3/4's angle takes (%g, %g), want the x/z difference (3, 4)",
              fake_calls[0].s0, fake_calls[0].s1);
        check_call(1, FN_TURN_RATE, "3/4 state 1 doesn't turn");
        CHECK(fabsf(fake_calls[1].s0 - 0.6f) < 1e-4f,
              "3/4's turn is %g, want 6554 angle units * 360 * 2^-16 / 60 = 0.6",
              fake_calls[1].s0);
        CHECK(fake_calls[1].s1 == TURN_RATE_3_4, "3/4's turn rate is %g, want 0.04",
              fake_calls[1].s1);
        check_call(2, FN_HIT_CHECK, "3/4 state 1 doesn't run the part check");
        CHECK(fake_calls[2].r1 == 0x23 && fake_calls[2].r2 == 0x24,
              "3/4's part check is (%u, %u), want (0x23, 0x24)", fake_calls[2].r1,
              fake_calls[2].r2);
        CHECK(fake_calls[2].s0 == 2.0f && fake_calls[2].s1 == 0.5f,
              "3/4's part check takes (%g, %g), want the speed 2.0 and the rate 0.5",
              fake_calls[2].s0, fake_calls[2].s1);
        check_no_blocked("3/4");
        CHECK(fake_log_contains("0x00842a7c"), "3/4 doesn't log the skipped hit resolution");

        /* A heading difference of 0 keeps the turn at 0. */
        fake_mem_write32(work + WORK_HEADING, fake_angle);
        fake_reset_calls();
        frame_with(enemy, work, 3, 4);
        CHECK(fake_calls[1].fn == FN_TURN_RATE && fake_calls[1].s0 == 0.0f,
              "3/4's zero heading difference doesn't turn by 0");
    }

    /* ── 3/5 (variant 0): the record path, then the immediate 3/11 ── */
    {
        const uint32_t enemy = 0xd0000u, work = 0xe0000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);

        fake_reset_calls();
        fake_clear_log();
        frame_with(enemy, work, 3, 5);
        check_count(4, "3/5 state 0");
        check_call(0, FN_MARK, "3/5 doesn't set the work+0x3e3 mark");
        check_call(1, FN_HIT_START, "3/5 state 0 doesn't run the 0x008437f4 start");
        CHECK(fake_calls[1].r1 == 0x19 && fake_calls[1].s0 == 1.0f,
              "3/5's start takes (%u, %g), want (0x19, 1)", fake_calls[1].r1,
              fake_calls[1].s0);
        CHECK(fake_calls[2].fn == FN_DATA_FLOAT && fake_calls[3].fn == FN_TURN
              && fake_calls[3].s0 == DATA_VALUE,
              "3/5 state 0 doesn't finish with the data float and the turn");
        CHECK(fake_log_contains("0x0084704c"), "3/5 doesn't log the skipped record reader");
        check_no_blocked("3/5");

        fake_reset_calls();
        frame_with(enemy, work, 3, 5);
        check_count(5, "3/5 state 1");
        check_call(0, FN_MARK, "3/5 state 1 doesn't mark again");
        check_call(1, FN_PREDICATE, "3/5 state 1 doesn't run the 0x008438e8 predicate");
        CHECK(fake_calls[2].fn == FN_DATA_FLOAT && fake_calls[3].fn == FN_APPLY_FALL
              && fake_calls[3].s0 == DATA_VALUE,
              "3/5's variant 0 tail doesn't apply the data float to the fall");
        CHECK(fake_calls[4].fn == FN_SET_ACTION_2 && fake_calls[4].r1 == 3
              && fake_calls[4].r2 == 0xb,
              "3/5's variant 0 tail doesn't set the immediate action 3/11");
        CHECK(fake_mem_read8(work + WORK_SET) == 1, "3/5 doesn't set the work+0x1dc byte");
    }

    /* ── 3/9 (variant 1): the sub-machine, the selector and the next action ── */
    {
        const uint32_t enemy = 0xf0000u, work = 0x100000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 3, 9);          /* state 0 */
        check_count(4, "3/9 state 0");

        fake_reset_calls();
        fake_clear_log();
        fake_mem_write32(work + WORK_3_5_ACTIVE, 0);
        fake_mem_write8(work + WORK_SELECT, 0);
        fake_mem_write8(work + WORK_3_5_LAST, 1);
        frame_with(enemy, work, 3, 9);
        check_count(4, "3/9 state 1, sub-state 0");
        check_call(0, FN_MARK, "3/9 state 1 doesn't mark");
        check_call(1, FN_STATE_PRED, "3/9's sub-machine doesn't test the state predicate");
        check_call(2, FN_PREDICATE, "3/9's sub-machine doesn't reach the common predicate");
        check_call(3, FN_NEXT_ACTION, "3/9 doesn't request the next action");
        CHECK(fake_calls[3].r1 == 3 && fake_calls[3].r2 == 9,
              "3/9 requests %u/%u, want 3/9", fake_calls[3].r1, fake_calls[3].r2);
        CHECK(fake_mem_read8(work + WORK_SUB) == 1, "3/9's sub-state isn't set to 1");
        CHECK(fake_log_contains("0x00833234") && fake_log_contains("0x00835f10"),
              "3/9 doesn't log the blocked hit loop");
        check_no_blocked("3/9");

        /* The selector matching the last byte moves to 3/10. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_3_5_LAST, 0);
        frame_with(enemy, work, 3, 9);
        CHECK(fake_calls[fake_call_count - 1].fn == FN_NEXT_ACTION &&
              fake_calls[fake_call_count - 1].r2 == 0xa,
              "3/9 doesn't request 3/10 when the selector matches");

        /* A live "may advance" byte skips the sub-machine (in sub-state 0). */
        fake_reset_calls();
        fake_mem_write8(work + WORK_SUB, 0);
        fake_mem_write8(work + WORK_3_5_ACTIVE, 1);
        frame_with(enemy, work, 3, 9);
        check_count(3, "3/9 with the advance byte set");
        check_call(1, FN_PREDICATE, "3/9's advance byte doesn't go straight to the tail");

        /* The 0x008565d8 end step sets the third state. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_SUB, 0);
        fake_mem_write8(work + WORK_3_5_ACTIVE, 0);
        fake_mem_write8(work + WORK_OTHER, 1);
        fake_mem_write8(work + WORK_3_5_TIMER, 0x2c);   /* below 0x12c */
        frame_with(enemy, work, 3, 9);
        CHECK(fake_mem_read8(work + WORK_SUB2) == 2,
              "3/9's 0x008565d8 end step doesn't set the third state");

        /* The third state's close-range branch asks for 3/8 and runs the end step. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_SUB, 1);
        fake_mem_write8(work + WORK_SUB2, 2);
        fake_mem_write32(work + WORK_POS, fbits(1.0f));
        fake_mem_write32(work + WORK_POS + 8u, fbits(2.0f));
        fake_mem_write32(work + WORK_TARGET, fbits(2.0f));
        fake_mem_write32(work + WORK_TARGET + 8u, fbits(2.0f));
        frame_with(enemy, work, 3, 9);
        check_count(4, "3/9's third state, close range");
        check_call(1, FN_DIST2, "3/9's third state doesn't take the squared distance");
        CHECK(fake_calls[2].fn == FN_NEXT_ACTION && fake_calls[2].r1 == 3
              && fake_calls[2].r2 == 8,
              "3/9's close-range branch doesn't request 3/8");
        check_call(3, FN_END, "3/9's close-range branch doesn't run the end step");

        /* The predicate clear runs the second record reader and the turn. */
        fake_reset_calls();
        fake_clear_log();
        fake_predicate = 0;
        fake_mem_write8(work + WORK_SUB, 1);
        fake_mem_write8(work + WORK_SUB2, 0);
        frame_with(enemy, work, 3, 9);
        CHECK(fake_log_contains("0x00847134"), "3/9 doesn't log the second record path");
        fake_predicate = 1;
    }

    /* ── 3/10 and 3/15: the shared state 0, then the 0/3 base handler ── */
    {
        const uint32_t enemy = 0x110000u, work = 0x120000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work + WORK_KIND, 0x20);
        fake_mem_write8(work + WORK_DATA_INDEX, 7);
        fake_mem_write32(RECORD_ADDRESS + 0x64u, fbits(4.0f));

        fake_reset_calls();
        frame_with(enemy, work, 3, 10);
        check_count(4, "3/10 state 0");
        check_call(0, FN_MARK, "3/10 doesn't set the mark");
        CHECK(fake_calls[1].fn == FN_DATA_FLOAT && fake_calls[2].fn == FN_APPLY_FALL
              && fake_calls[2].s0 == DATA_VALUE,
              "3/10 state 0 doesn't apply the data float to the fall");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_3_10_START
              && fake_calls[3].s0 == 6.0f,
              "3/10 state 0 doesn't start motion 0x2d at 6");

        fake_reset_calls();
        frame_with(enemy, work, 3, 10);
        check_count(5, "3/10 state 1");
        CHECK(fake_calls[1].fn == FN_FLAG, "3/10 state 1 doesn't wait for the flag");
        check_call(2, FN_DATA_GET, "3/10's 0/3 base handler doesn't look the record up");
        CHECK(fake_calls[3].fn == FN_MODE && fake_calls[3].r1 == 1,
              "3/10's 0/3 base handler doesn't set mode 1");
        CHECK(fake_calls[4].fn == FN_SET_ACTION && fake_calls[4].r2 == 3,
              "3/10's 0/3 base handler doesn't start action 0/3");

        const uint32_t enemy2 = 0x130000u, work2 = 0x140000u;
        spawn(enemy2, work2, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work2 + WORK_KIND, 0x20);
        fake_mem_write8(work2 + WORK_DATA_INDEX, 7);
        fake_mem_write32(RECORD_ADDRESS + 0x64u, fbits(4.0f));
        fake_reset_calls();
        frame_with(enemy2, work2, 3, 15);
        check_count(4, "3/15 state 0");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_3_10_START,
              "3/15 state 0 doesn't start motion 0x2d");

        fake_reset_calls();
        frame_with(enemy2, work2, 3, 15);
        check_count(6, "3/15 state 1");
        check_call(0, FN_MARK, "3/15 state 1 doesn't mark");
        check_call(1, FN_TURN_TO, "3/15 state 1 doesn't turn toward the target");
        CHECK(fake_calls[1].r1 == 0x180, "3/15's turn step is 0x%x, want 0x180",
              fake_calls[1].r1);
        CHECK(fake_calls[2].fn == FN_FLAG, "3/15 state 1 doesn't wait for the flag");
        CHECK(fake_calls[3].fn == FN_DATA_GET && fake_calls[5].fn == FN_SET_ACTION,
              "3/15 doesn't end in the 0/3 base handler");
    }

    /* ── 3/11: the 60.0 timer and the immediate 3/11 ── */
    {
        const uint32_t enemy = 0x150000u, work = 0x160000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 3, 11);
        check_count(3, "3/11 state 0");
        CHECK(fake_calls[0].fn == FN_DATA_FLOAT && fake_calls[1].fn == FN_APPLY_FALL
              && fake_calls[1].s0 == DATA_VALUE,
              "3/11 state 0 doesn't apply the data float to the fall");
        CHECK(fake_calls[2].fn == FN_REQUEST && fake_calls[2].r1 == MOTION_3_11_START
              && fake_calls[2].s0 == 4.0f,
              "3/11 state 0 doesn't request motion 0x1f at 4");
        CHECK(ffrom(fake_mem_read32(work + WORK_COUNTDOWN)) == 60.0f,
              "3/11 doesn't arm the 60.0 timer");

        fake_reset_calls();
        fake_countdown = 0;
        frame_with(enemy, work, 3, 11);
        check_count(1, "3/11 state 1 with the timer running");
        check_call(0, FN_COUNTDOWN, "3/11 state 1 doesn't count the timer down");
        CHECK(fake_calls[0].r1 == work + WORK_COUNTDOWN,
              "3/11 counts down at 0x%08x, want work+0x1d4", fake_calls[0].r1);

        fake_reset_calls();
        fake_countdown = 1;
        frame_with(enemy, work, 3, 11);
        check_count(4, "3/11 state 1 with the timer spent");
        CHECK(fake_calls[0].fn == FN_COUNTDOWN, "3/11 doesn't count the timer first");
        CHECK(fake_calls[1].fn == FN_DATA_FLOAT && fake_calls[2].fn == FN_APPLY_FALL,
              "3/11's spent timer doesn't apply the data float to the fall");
        CHECK(fake_calls[3].fn == FN_SET_ACTION_2 && fake_calls[3].r1 == 3
              && fake_calls[3].r2 == 0xb,
              "3/11's spent timer doesn't set the immediate action 3/11");
        CHECK(fake_mem_read8(work + WORK_SET) == 1, "3/11 doesn't set the work+0x1dc byte");
    }

    /* ── 3/14 (variant 2): the tail flag clear falls back to the 3/11 step ── */
    {
        const uint32_t enemy = 0x170000u, work = 0x180000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 3, 14);         /* state 0 */
        check_count(4, "3/14 state 0");
        fake_reset_calls();
        fake_mem_write8(work + WORK_TAIL, 0);
        frame_with(enemy, work, 3, 14);
        check_count(5, "3/14 state 1, tail flag clear");
        CHECK(fake_calls[2].fn == FN_DATA_FLOAT && fake_calls[3].fn == FN_APPLY_FALL,
              "3/14's tail doesn't apply the data float to the fall");
        CHECK(fake_calls[4].fn == FN_SET_ACTION_2 && fake_calls[4].r2 == 0xb,
              "3/14's tail doesn't set the immediate 3/11");
    }

    /* ── 3/22, 3/23, 3/26, 3/30 (variants 3-6) ── */
    {
        const uint32_t enemy = 0x190000u, work = 0x1a0000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        fake_clear_log();
        frame_with(enemy, work, 3, 22);         /* state 0 */
        check_count(4, "3/22 state 0");
        check_call(0, FN_MARK, "3/22 doesn't mark");
        check_call(1, FN_HIT_START, "3/22 state 0 doesn't run the 0x008437f4 start");
        CHECK(fake_log_contains("0x0083db24"), "3/22 doesn't log the skipped entry step");
        check_no_blocked("3/22");

        fake_reset_calls();
        frame_with(enemy, work, 3, 22);         /* state 1, tail flag clear */
        check_count(4, "3/22 state 1, tail flag clear");
        check_call(0, FN_MARK, "3/22 state 1 doesn't mark");
        check_call(1, FN_PREDICATE, "3/22 state 1 doesn't run the predicate");
        check_call(2, FN_HIT_SETUP, "3/22 doesn't run the hit setup");
        CHECK(fake_calls[2].r1 == 0 && fake_calls[2].has_r4 && fake_calls[2].r4 == 0,
              "3/22's hit setup isn't (0, 0, 0, stack 0)");
        check_call(3, FN_NEXT_ACTION, "3/22 doesn't request the next action");
        CHECK(fake_calls[3].r1 == 7 && fake_calls[3].r2 == 0x1c,
              "3/22 requests %u/%u, want 7/0x1c", fake_calls[3].r1, fake_calls[3].r2);

        fake_reset_calls();
        fake_mem_write8(work + WORK_TAIL, 1);
        frame_with(enemy, work, 3, 22);
        check_count(4, "3/22 state 1, tail flag set");
        check_call(2, FN_PART_FLAG, "3/22's tail doesn't set the per-action flag");
        CHECK(fake_calls[3].fn == FN_SET_ACTION_1 && fake_calls[3].r1 == 3
              && fake_calls[3].r2 == 0x16,
              "3/22's tail requests %u/%u, want 3/0x16", fake_calls[3].r1,
              fake_calls[3].r2);

        /* 3/23 (variant 4): the state predicate picks 7/0x39 or 7/0x1d. */
        const uint32_t enemy23 = 0x1b0000u, work23 = 0x1c0000u;
        spawn(enemy23, work23, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy23, work23, 3, 23);
        fake_reset_calls();
        fake_mem_write8(work23 + WORK_TAIL, 0);
        fake_mem_write8(work23 + WORK_3_5_PART, 0);
        fake_state_pred = 0;
        frame_with(enemy23, work23, 3, 23);
        check_count(5, "3/23 state 1, state predicate clear");
        check_call(3, FN_STATE_PRED, "3/23's tail doesn't test the state predicate");
        CHECK(fake_calls[4].fn == FN_NEXT_ACTION && fake_calls[4].r2 == 0x1d,
              "3/23 doesn't request 7/0x1d when the state predicate is clear");
        fake_reset_calls();
        fake_state_pred = 1;
        frame_with(enemy23, work23, 3, 23);
        CHECK(fake_calls[4].fn == FN_NEXT_ACTION && fake_calls[4].r2 == 0x39,
              "3/23 doesn't request 7/0x39 when the state predicate is set");
        fake_state_pred = 1;

        /* 3/30 (variant 6): the part byte's 0xff retry runs the hit setup twice. */
        const uint32_t enemy30 = 0x1d0000u, work30 = 0x1e0000u;
        spawn(enemy30, work30, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy30, work30, 3, 30);
        fake_reset_calls();
        fake_mem_write8(work30 + WORK_TAIL, 0);
        fake_mem_write8(work30 + WORK_3_5_PART, 0xff);
        frame_with(enemy30, work30, 3, 30);
        check_count(5, "3/30 state 1 with the part byte 0xff");
        CHECK(fake_calls[2].fn == FN_HIT_SETUP && fake_calls[3].fn == FN_HIT_SETUP,
              "3/30 doesn't retry the hit setup on the 0xff part");
        CHECK(fake_calls[3].r1 == 5 && fake_calls[3].r2 == 9,
              "3/30's retry is (%u, %u), want (5, 9)", fake_calls[3].r1, fake_calls[3].r2);
        CHECK(fake_calls[4].fn == FN_NEXT_ACTION && fake_calls[4].r2 == 0x5e,
              "3/30 doesn't request 7/0x5e");

        /* 3/26 (variant 5): the tail flag set picks 3/0x1a. */
        const uint32_t enemy26 = 0x1f0000u, work26 = 0x200000u;
        spawn(enemy26, work26, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy26, work26, 3, 26);
        fake_reset_calls();
        fake_mem_write8(work26 + WORK_TAIL, 1);
        frame_with(enemy26, work26, 3, 26);
        CHECK(fake_calls[3].fn == FN_SET_ACTION_1 && fake_calls[3].r2 == 0x1a,
              "3/26's tail doesn't set 3/0x1a");
    }

    /* ── the record path: the predicate clear runs the second reader and the turn ── */
    {
        const uint32_t enemy = 0x210000u, work = 0x220000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 3, 14);
        fake_reset_calls();
        fake_clear_log();
        fake_predicate = 0;
        frame_with(enemy, work, 3, 14);
        check_count(4, "3/14 with the predicate clear");
        CHECK(fake_calls[2].fn == FN_DATA_FLOAT && fake_calls[3].fn == FN_TURN
              && fake_calls[3].s0 == DATA_VALUE,
              "the record path doesn't finish with the data float and the turn");
        check_no_blocked("the record path");
        fake_predicate = 1;
    }

    /* ── an id no family carries falls through ── */
    {
        const uint32_t enemy = 0x230000u, work = 0x240000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 15, 0);          /* no family carries category 15 */
        check_count(0, "an id no family carries");
        CHECK(fake_original_count == 1 && fake_skip_count == 0 && fake_call_count == 0,
              "an id no family carries doesn't fall to MH4U's dispatcher");
    }

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 3's fifteen ids and action 12 make their calls\n");
    return 0;
}
