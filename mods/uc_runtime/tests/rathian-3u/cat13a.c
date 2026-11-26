/*
 * cat13a.c: category 13 part 1's fake-host test — 13/0, 13/1, 13/2, 13/3 and 13/4.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-3u/ and builds it as tests/family-<stem>, so a slice adds its test file and
 * edits nothing shared. The shell's test (tests/test_rathian_3u.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the five
 * units' call sequences on the fake host.
 *
 * The expected addresses, offsets, frame values and motion numbers come from
 * tests/rathian-3u/host.h and this file's own constants, not from the module, so a change in
 * a handler fails the test instead of moving the expectation with it. A motion number is
 * MH4U's `file << 8 | slot` of the source's `file * 100 + slot`.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The family's work-block offsets (the runtime README's field map). */
#define WORK_STATE2   0x0145u
#define WORK_TURN     0x01a8u
#define WORK_HEADING  0x01acu
#define WORK_AIM_X    0x0160u
#define WORK_AIM_Y    0x0164u
#define WORK_AIM_Z    0x0168u
#define WORK_AIM_BZ   0x0178u
#define WORK_POS_X    0x0198u
#define WORK_POS_Y    0x019cu
#define WORK_POS_Z    0x01a0u
#define WORK_TARGET_X 0x0218u
#define WORK_TARGET_Y 0x021cu
#define WORK_TARGET_Z 0x0220u
#define WORK_SPEED    0x0180u
#define WORK_TIMER    0x01d4u
#define WORK_ID       0x01c0u
#define WORK_FLYING   0x03c4u
#define ENEMY_DELTA   0x0014u
#define TARGET_LINE   0x8d88u

/* The MH4U engine functions the family calls. */
#define FN_MOTION       0x0094e318u
#define FN_DATA_FLOAT   0x0093d870u
#define FN_APPLY_FALL   0x0092e99cu
#define FN_FLAG         0x00b05da4u
#define FN_REQUEST_NEXT 0x0094ef64u
#define FN_VERTICAL     0x00915d44u
#define FN_TURN_STEP    0x0091db4cu
#define FN_AIM_RESET    0x0096e164u
#define FN_PER_MODE     0x0091aae4u
#define FN_TURN_ANGLE   0x0091aaf0u
#define FN_AIM_WRAPPER  0x0091b430u
#define FN_BLEND        0x0092dc50u
#define FN_LAND         0x0092dcccu
#define FN_TAIL0        0x00914dc4u
#define FN_SPEED        0x00916108u
#define FN_DISTANCE     0x00aacd50u
#define FN_CURVE        0x00922250u
#define FN_ANGLE        0x00568c64u
#define FN_STATE_PRED   0x0092e960u
#define FN_ORDER        0x0091b7b0u
#define FN_RATE_A       0x0093ce60u
#define FN_RATE_B       0x0093cd70u
#define FN_TARGET_LINE  0x00948548u
#define FN_AIM_POINT    0x00948674u
#define FN_MOVE_POS     0x00955440u
#define FN_ACTION_STEP  0x00916228u

#define CURVE_13_2_A 0x00fd19b0u
#define CURVE_13_2_B 0x00fd19f8u

#define MOTION_13_0  ((0u << 8) | 0x1au)
#define MOTION_13_1A ((0u << 8) | 0x3du)
#define MOTION_13_1B ((0u << 8) | 0x3eu)
#define MOTION_13_1C ((0u << 8) | 0x2du)
#define MOTION_13_2A ((2u << 8) | 0x00u)
#define MOTION_13_2B ((2u << 8) | 0x14u)
#define MOTION_13_3  ((2u << 8) | 0x02u)
#define MOTION_13_4  ((2u << 8) | 0x03u)

static int fake_flag = 1;
static int fake_land;
static int fake_state_pred;
static int fake_turn;
static int per_mode_on;
static float per_mode_value;
static float fake_data = 1.0f;
static float fake_curve_a = 1.0f;
static float fake_curve_b = 2.0f;
static float fake_distance;
static uint32_t fake_aim_return;
static uint32_t fake_angles[2];
static int fake_angle_index;

/* What the engine answers category 13 part 1's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_LAND:
        return (FakeResult){(uint32_t)fake_land, 0.0f};
    case FN_PER_MODE:
        return (FakeResult){per_mode_on && s[0] == per_mode_value ? 1u : 0u, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0u, fake_data};
    case FN_CURVE:
        return (FakeResult){0u, r[1] == CURVE_13_2_A ? fake_curve_a : fake_curve_b};
    case FN_DISTANCE:
        return (FakeResult){0u, fake_distance};
    case FN_ANGLE: {
        const uint32_t value = fake_angles[fake_angle_index & 1];
        fake_angle_index++;
        return (FakeResult){value, 0.0f};
    }
    case FN_AIM_WRAPPER:
        return (FakeResult){fake_aim_return, 0.0f};
    case FN_STATE_PRED:
        return (FakeResult){(uint32_t)fake_state_pred, 0.0f};
    case FN_TURN_STEP:
        return (FakeResult){(uint32_t)fake_turn, 0.0f};
    default:
        return (FakeResult){0u, 0.0f};
    }
}

/* One call's function, for a readable failure. */
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

    /* ── every id in the slice runs the module's handler ──────────────────────────── */
    {
        static const int ids[] = {0, 1, 2, 3, 4};
        for (unsigned i = 0; i < sizeof ids / sizeof ids[0]; i++) {
            const uint32_t enemy = 0x30000u + i * 0x2000u;
            const uint32_t work = 0x40000u + i * 0x2000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            frame_with(enemy, work, 13, ids[i]);
            CHECK(fake_skip_count == 1 && fake_original_count == 0,
                  "13/%d didn't run the module (%d original, %d skipped)", ids[i],
                  fake_original_count, fake_skip_count);
        }
    }

    /* ── 0x0068eabc: 13/0 — the fall, motion 0x1a at 10.0 and the 300.0 timer ────── */
    {
        const uint32_t enemy = 0x100000u, work = 0x101000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 13, 0);
        CHECK(fake_call_count == 4, "13/0 state 0 made %d calls, want 4", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT, "13/0 state 0 doesn't read the data float");
        CHECK(call_fn(1) == (int)FN_APPLY_FALL && fake_calls[1].s0 == 1.0f,
              "13/0 state 0 doesn't advance the fall by the data float");
        CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == MOTION_13_0
              && fake_calls[2].s0 == 10.0f,
              "13/0 state 0 doesn't start motion 0x1a at 10.0");
        CHECK(call_fn(3) == (int)FN_RATE_B, "13/0 state 0 doesn't set the rate");
        CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 300.0f,
              "13/0 state 0 doesn't set the 300.0 timer");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/0 doesn't advance its state");
        CHECK(fake_log_contains("0x00a347bc"), "13/0 doesn't name the blocked 0x00a347bc");
        CHECK(fake_log_contains("0x00843c20"), "13/0 doesn't name the blocked 0x00843c20");

        /* State 1, height above 3500: the rate and the 0x180 turn, then the height test
         * returns before the request. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_POS_Y, fbits(4000.0f));
        fake_mem_write32(work + WORK_TARGET_Y, fbits(0.0f));
        fake_mem_write32(work + WORK_TIMER, fbits(2.0f));
        fake_mem_write32(enemy + ENEMY_DELTA, fbits(0.5f));
        fake_turn = 1;
        frame_with(enemy, work, 13, 0);
        CHECK(fake_call_count == 2, "13/0 state 1 (high) made %d calls, want 2",
              fake_call_count);
        CHECK(call_fn(0) == (int)FN_RATE_A, "13/0's height above 3500 doesn't set the rate");
        CHECK(call_fn(1) == (int)FN_TURN_STEP && fake_calls[1].r1 == 0xc0,
              "13/0 doesn't turn at the source's 0x180 (halved to 0xc0)");

        /* State 1, height at or below 2000: the +10.0 step, the spent timer and the
         * request for 13/1. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_POS_Y, fbits(1000.0f));
        fake_mem_write32(work + WORK_TIMER, fbits(0.1f));
        frame_with(enemy, work, 13, 0);
        CHECK(ffrom(fake_mem_read32(work + WORK_POS_Y)) == 1010.0f,
              "13/0 doesn't make the source's +10.0 height step");
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_REQUEST_NEXT
              && fake_calls[0].r1 == 0x0du && fake_calls[0].r2 == 1u,
              "13/0's spent timer doesn't request 13/1");
    }

    /* ── 0x0068eca4: 13/1 — four states, motions 0x3d/0x3e/0x2d ─────────────────── */
    {
        const uint32_t enemy = 0x110000u, work = 0x111000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        fake_aim_return = 0;
        fake_land = 0;
        per_mode_on = 0;
        fake_flag = 1;
        frame_with(enemy, work, 13, 1);
        CHECK(fake_call_count == 4, "13/1 state 0 made %d calls, want 4", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT && call_fn(1) == (int)FN_APPLY_FALL,
              "13/1 state 0 doesn't take the data float and the fall");
        CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == MOTION_13_1A
              && fake_calls[2].s0 == 6.0f,
              "13/1 state 0 doesn't start motion 0x3d at 6.0");
        CHECK(call_fn(3) == (int)FN_AIM_RESET, "13/1 state 0 doesn't clear the aim");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == -20.0f
              && ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == 0.5f,
              "13/1 state 0 doesn't set aim A z -20.0 and aim B z 0.5");

        /* State 1: the aim step, the heading and pitch turns, then the second motion and
         * the blend. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_POS_X, fbits(0.0f));
        fake_mem_write32(work + WORK_POS_Y, fbits(0.0f));
        fake_mem_write32(work + WORK_POS_Z, fbits(0.0f));
        fake_mem_write32(work + WORK_TARGET_X, fbits(100.0f));
        fake_mem_write32(work + WORK_TARGET_Y, fbits(0.0f));
        fake_mem_write32(work + WORK_TARGET_Z, fbits(100.0f));
        fake_mem_write32(work + WORK_TURN, 0x10u);
        fake_mem_write32(work + WORK_HEADING, 0x20u);
        fake_angles[0] = 0x1000u;
        fake_angles[1] = 0x2000u;
        fake_angle_index = 0;
        frame_with(enemy, work, 13, 1);
        CHECK(fake_call_count == 10, "13/1 state 1 made %d calls, want 10", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT && call_fn(1) == (int)FN_AIM_WRAPPER
              && fake_calls[1].r1 == work + WORK_TURN && fake_calls[1].s0 == 1.0f,
              "13/1 state 1 doesn't run the aim step with the data float");
        CHECK(call_fn(2) == (int)FN_ANGLE && call_fn(3) == (int)FN_ANGLE,
              "13/1 state 1 doesn't take the vector's two angles");
        CHECK(call_fn(4) == (int)FN_TURN_ANGLE && fake_calls[4].r1 == 0x1400u
              && fake_calls[4].r2 == 0x10u && fake_calls[4].r3 == 0x80u,
              "13/1's heading turn isn't (0x1000 + 0x400, 0x10, 0x80)");
        CHECK(call_fn(5) == (int)FN_TURN_ANGLE && fake_calls[5].r1 == 0x2000u
              && fake_calls[5].r2 == 0x20u && fake_calls[5].r3 == 0x20u,
              "13/1's pitch turn isn't (0x2000, 0x20, 0x20)");
        CHECK(call_fn(6) == (int)FN_FLAG, "13/1 state 1 doesn't test the flag");
        CHECK(call_fn(7) == (int)FN_ACTION_STEP, "13/1 state 1 doesn't run 0x916228");
        CHECK(call_fn(8) == (int)FN_MOTION && fake_calls[8].r1 == MOTION_13_1B
              && fake_calls[8].s0 == 6.0f,
              "13/1 state 1 doesn't start motion 0x3e at 6.0");
        CHECK(call_fn(9) == (int)FN_BLEND && fake_calls[9].r1 == 0x12u
              && fake_calls[9].s0 == -2500.0f,
              "13/1 state 1 doesn't apply the 0x12/-2500.0 blend");
        CHECK(fake_mem_read8(work + WORK_STATE) == 2, "13/1 doesn't advance to state 2");
        CHECK(fake_mem_read8(work + WORK_FLYING) == 1, "13/1 doesn't set the flying byte");

        /* State 2, the landing step returns 1: state 3, motion 0x2d and the aim stores. */
        fake_reset_calls();
        fake_land = 1;
        frame_with(enemy, work, 13, 1);
        CHECK(fake_call_count == 4, "13/1 state 2 (landing) made %d calls, want 4",
              fake_call_count);
        CHECK(call_fn(0) == (int)FN_LAND && fake_calls[0].r1 == 0u
              && fake_calls[0].r2 == 0x40u,
              "13/1's landing step isn't (0, 0x80 halved to 0x40)");
        CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_13_1C
              && fake_calls[1].s0 == 6.0f,
              "13/1 state 2 doesn't start motion 0x2d at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 3 && fake_mem_read8(work + WORK_STATE2) == 0,
              "13/1 doesn't advance to state 3/0");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Y)) == -15.0f
              && ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == -6.2f,
              "13/1 state 2 doesn't set aim A y -15.0 and aim B z -6.2");

        /* State 3/0: the 30.0 query true, the aim clamp flag set, then mode 3 and the
         * request for 13/2. */
        fake_reset_calls();
        fake_aim_return = 1;
        per_mode_on = 1;
        per_mode_value = 30.0f;
        frame_with(enemy, work, 13, 1);
        CHECK(fake_call_count == 6, "13/1 state 3/0 made %d calls, want 6", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT && call_fn(1) == (int)FN_AIM_WRAPPER,
              "13/1 state 3 doesn't run the aim step");
        CHECK(call_fn(2) == (int)FN_PER_MODE && fake_calls[2].r1 == 1u
              && fake_calls[2].s0 == 30.0f && fake_calls[2].s1 == 0.0f,
              "13/1 state 3 doesn't run the 1/30.0 per-mode query");
        CHECK(call_fn(3) == (int)FN_FLAG, "13/1 state 3 doesn't test the flag");
        CHECK(call_fn(4) == (int)FN_MODE && fake_calls[4].r1 == 3u,
              "13/1 state 3 doesn't set mode 3");
        CHECK(call_fn(5) == (int)FN_REQUEST_NEXT && fake_calls[5].r1 == 0x0du
              && fake_calls[5].r2 == 2u, "13/1 state 3 doesn't request 13/2");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == -6.8f,
              "13/1 state 3/0 doesn't set aim B z -6.8");
    }

    /* ── 0x0068f0fc: 13/2 — mode 3, motion 0xc8, the curves and the target loop ──── */
    {
        const uint32_t enemy = 0x120000u, work = 0x121000u;
        const uint32_t line = 0x130000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write32(enemy + TARGET_LINE, line);
        fake_reset_calls();
        fake_distance = 900.0f;
        frame_with(enemy, work, 13, 2);
        CHECK(fake_call_count == 7, "13/2 state 0 made %d calls, want 7", fake_call_count);
        CHECK(call_fn(0) == (int)FN_MODE && fake_calls[0].r1 == 3u,
              "13/2 state 0 doesn't set mode 3");
        CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_13_2A
              && fake_calls[1].s0 == 20.0f,
              "13/2 state 0 doesn't start motion 0xc8 at 20.0");
        CHECK(call_fn(2) == (int)FN_TAIL0 && fake_calls[2].r1 == 0u
              && fake_calls[2].r2 == 0x0bu, "13/2 state 0 doesn't make the (0, 0xb) tail");
        CHECK(call_fn(3) == (int)FN_AIM_RESET, "13/2 state 0 doesn't clear the aim");
        CHECK(call_fn(4) == (int)FN_SPEED && fake_calls[4].s0 == 0.0f,
              "13/2 state 0 doesn't clear the speed");
        CHECK(call_fn(5) == (int)FN_DISTANCE && fake_calls[5].r0 == work + WORK_POS_X
              && fake_calls[5].r1 == work + WORK_TARGET_X,
              "13/2 doesn't take the distance between the position and the target");
        CHECK(call_fn(6) == (int)FN_TARGET_LINE, "13/2 state 0 doesn't run 0x948548");
        CHECK(ffrom(fake_mem_read32(line)) == 2.0f,
              "13/2 doesn't store the distance/450 lead (2.0)");

        /* State 1: the two curves, the halved vertical step, the -50 speed floor, the aim
         * step, the 36.0 query and the flag. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 1u);
        fake_mem_write32(line, fbits(3.0f));
        fake_mem_write32(work + WORK_SPEED, fbits(-100.0f));
        fake_curve_a = 1.0f;
        fake_curve_b = 2.0f;
        per_mode_on = 1;
        per_mode_value = 36.0f;
        frame_with(enemy, work, 13, 2);
        CHECK(fake_call_count == 9, "13/2 state 1 made %d calls, want 9", fake_call_count);
        CHECK(call_fn(0) == (int)FN_CURVE && fake_calls[0].r1 == CURVE_13_2_A,
              "13/2 state 1 doesn't read the first curve");
        CHECK(call_fn(1) == (int)FN_VERTICAL && fake_calls[1].s0 == 0.5f,
              "13/2 doesn't halve the first curve for the vertical step");
        CHECK(ffrom(fake_mem_read32(work + WORK_SPEED)) == -50.0f,
              "13/2 doesn't floor the speed at -50.0");
        CHECK(call_fn(2) == (int)FN_CURVE && fake_calls[2].r1 == CURVE_13_2_B,
              "13/2 state 1 doesn't read the second curve");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 6.0f,
              "13/2 doesn't store curve2 * the target-line factor");
        CHECK(call_fn(3) == (int)FN_DATA_FLOAT && call_fn(4) == (int)FN_AIM_WRAPPER,
              "13/2 state 1 doesn't run the aim step");
        CHECK(call_fn(5) == (int)FN_PER_MODE && fake_calls[5].r1 == 1u
              && fake_calls[5].s0 == 36.0f, "13/2 doesn't run the 36.0 per-mode query");
        CHECK(call_fn(6) == (int)FN_FLAG, "13/2 state 1 doesn't test the flag");
        CHECK(call_fn(7) == (int)FN_MODE && fake_calls[7].r1 == 0u,
              "13/2 state 1 doesn't set mode 0");
        CHECK(call_fn(8) == (int)FN_MOTION && fake_calls[8].r1 == MOTION_13_2B
              && fake_calls[8].s0 == 0.0f,
              "13/2 state 1 doesn't start motion 0xdc at 0.0");

        /* State 2: the 30.0 query, the blocked signed byte and target loop, and the
         * source's failure request 1/3. */
        fake_reset_calls();
        per_mode_on = 1;
        per_mode_value = 30.0f;
        frame_with(enemy, work, 13, 2);
        CHECK(fake_call_count == 2, "13/2 state 2 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].s0 == 30.0f,
              "13/2 state 2 doesn't run the 30.0 per-mode query");
        CHECK(call_fn(1) == (int)FN_REQUEST_NEXT && fake_calls[1].r1 == 1u
              && fake_calls[1].r2 == 3u, "13/2 state 2 doesn't request 1/3");
        CHECK(fake_log_contains("0x00839598"), "13/2 doesn't name the blocked 0x00839598");
        CHECK(fake_log_contains("0x00835f10"), "13/2 doesn't name the blocked 0x00835f10");
    }

    /* ── 0x0068f424: 13/3 — the aim, the 12.0/50.0 query and the target loop ────── */
    {
        const uint32_t enemy = 0x140000u, work = 0x141000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 13, 3);
        CHECK(fake_call_count == 2, "13/3 state 0 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_MODE && fake_calls[0].r1 == 0u,
              "13/3 state 0 doesn't set mode 0");
        CHECK(call_fn(1) == (int)FN_AIM_POINT && fake_calls[1].r1 == work + WORK_AIM_X
              && fake_calls[1].r2 == work + WORK_TARGET_X
              && fake_calls[1].s0 == 300.0f && fake_calls[1].s1 == 38.0f,
              "13/3 state 0 doesn't aim at the target at 300.0/38.0");
        CHECK(fake_log_contains("0x0082d278"), "13/3 doesn't name the blocked 0x0082d278");
        CHECK(!fake_log_contains("0x00911c0c"),
              "13/3 calls MH4U's record setup with the source's data");

        /* State 1, the query false: the flag alone starts motion 0xca. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 1u);
        per_mode_on = 0;
        fake_flag = 1;
        frame_with(enemy, work, 13, 3);
        CHECK(fake_call_count == 3, "13/3 state 1 (query false) made %d calls, want 3",
              fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].r1 == 3u
              && fake_calls[0].s0 == 12.0f && fake_calls[0].s1 == 50.0f,
              "13/3 doesn't run the 3/12.0/50.0 per-mode query");
        CHECK(call_fn(1) == (int)FN_FLAG, "13/3 state 1 doesn't test the flag");
        CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == MOTION_13_3
              && fake_calls[2].s0 == 4.0f,
              "13/3 state 1 doesn't start motion 0xca at 4.0");

        /* State 1, the query true: the speed-derived aim range and the halved move. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 1u);
        per_mode_on = 1;
        per_mode_value = 12.0f;
        fake_mem_write32(work + WORK_AIM_BZ, fbits(32.0f));
        frame_with(enemy, work, 13, 3);
        CHECK(fake_call_count == 5, "13/3 state 1 (query true) made %d calls, want 5",
              fake_call_count);
        CHECK(call_fn(1) == (int)FN_AIM_POINT && fake_calls[1].s1 == 18.0f,
              "13/3's aim range isn't 38 - (32 - 12) = 18");
        CHECK(call_fn(2) == (int)FN_MOVE_POS && fake_calls[2].s0 == 0.5f,
              "13/3 doesn't halve the source's 1.0 move");
        CHECK(fake_log_contains("0x0082d430"), "13/3 doesn't name the blocked 0x0082d430");

        /* State 2: the blocked signed byte and target loop, then the failure request 2/6. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 2u);
        frame_with(enemy, work, 13, 3);
        CHECK(fake_call_count == 1, "13/3 state 2 made %d calls, want 1", fake_call_count);
        CHECK(call_fn(0) == (int)FN_REQUEST_NEXT && fake_calls[0].r1 == 2u
              && fake_calls[0].r2 == 6u, "13/3 state 2 doesn't request 2/6");
        CHECK(fake_log_contains("0x00839598"), "13/3 doesn't name the blocked 0x00839598");
        CHECK(fake_log_contains("0x00835f10"), "13/3 doesn't name the blocked 0x00835f10");
    }

    /* ── 0x0068f66c: 13/4 — motion 0xcb at 4.0, the 4.0 timer and the order step ──── */
    {
        const uint32_t enemy = 0x150000u, work = 0x151000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 13, 4);
        CHECK(fake_call_count == 2, "13/4 state 0 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_MODE && fake_calls[0].r1 == 0u,
              "13/4 state 0 doesn't set mode 0");
        CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_13_4
              && fake_calls[1].s0 == 4.0f,
              "13/4 state 0 doesn't start motion 0xcb at 4.0");
        CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 4.0f,
              "13/4 state 0 doesn't set the 4.0 timer");
        CHECK(fake_log_contains("0x0085162c"), "13/4 doesn't name the blocked 0x0085162c");
        CHECK(fake_log_contains("0x00829620"), "13/4 doesn't name the blocked 0x00829620");

        /* State 1, no crossing: the request alone. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 1u);
        fake_mem_write32(work + WORK_TIMER, fbits(4.0f));
        fake_mem_write32(enemy + ENEMY_DELTA, fbits(1.0f));
        fake_state_pred = 1;
        frame_with(enemy, work, 13, 4);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_FLAG
              && call_fn(1) == (int)FN_REQUEST_NEXT
              && fake_calls[1].r1 == 0x0du && fake_calls[1].r2 == 2u,
              "13/4's uncrossed timer doesn't request 13/2 after the flag");

        /* State 1, crossing zero with the state predicate set: the 1000 order step and
         * the request. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_TIMER, fbits(0.5f));
        frame_with(enemy, work, 13, 4);
        CHECK(fake_call_count == 4, "13/4's crossed timer made %d calls, want 4",
              fake_call_count);
        CHECK(call_fn(0) == (int)FN_FLAG, "13/4 doesn't test the flag first");
        CHECK(call_fn(1) == (int)FN_STATE_PRED,
              "13/4's crossed timer doesn't test the state predicate");
        CHECK(call_fn(2) == (int)FN_ORDER && fake_calls[2].r1 == 1000u,
              "13/4's crossed timer doesn't take the 1000 order step");
        CHECK(call_fn(3) == (int)FN_REQUEST_NEXT && fake_calls[3].r2 == 2u,
              "13/4's crossed timer doesn't request 13/2");

        /* State 1, crossing zero without the predicate: the ported id 1 takes the 200
         * step. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_TIMER, fbits(0.5f));
        fake_state_pred = 0;
        frame_with(enemy, work, 13, 4);
        CHECK(fake_call_count == 4 && call_fn(2) == (int)FN_ORDER
              && fake_calls[2].r1 == 200u,
              "13/4's id 1 doesn't take the 200 order step");
    }

    if (failures) {
        fprintf(stderr, "%d failures\n", failures);
        return 1;
    }
    printf("cat13a: ok\n");
    return 0;
}
