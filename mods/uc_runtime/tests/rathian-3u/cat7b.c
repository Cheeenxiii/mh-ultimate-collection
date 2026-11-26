/*
 * cat7b.c: category 7 part 2's fake-host test — 7/3, 7/9, 7/13, 7/14, 7/17, 7/18, 7/21, 7/30,
 * 7/41, 7/43, 7/44, 7/53, 7/54, 7/55, 7/56, 7/72, 7/73, 7/78, 7/80, 7/83, 7/88 and 7/89, on
 * the units 0x00694474 (the veneer), 0x00694f4c, 0x006956e8, 0x00695e68 and 0x00696408.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/
 * and builds it as tests/family-<stem>. The shell's test (tests/test_rathian_3u.c) covers the
 * factory association, the routing, the ready line and the self-test; this one drives the ids'
 * call sequences and frame values on the fake host.
 *
 * The expected addresses, constants and frame values come from tests/rathian-3u/host.h and this
 * file, not from the module, so a change in a handler fails the test instead of moving the
 * expectation with it. The motion numbers are MH4U's file << 8 | slot: the source's 0xcd (file
 * 2, slot 5) is 0x0205.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The engine functions this family calls, in MH4U's addresses. */
#define FN_MOTION       0x0094e318u
#define FN_MOTION_ARGS  0x0093310cu
#define FN_MOTION_ARGS2 0x00914dc4u
#define FN_FLAG_TIME    0x00922c40u
#define FN_EXTRA        0x0096e164u
#define FN_TURN         0x0091db4cu
#define FN_TURN_STEP    0x0091b430u
#define FN_BLEND        0x0092dc50u
#define FN_LANDING      0x0092dcccu
#define FN_MODE_CHECK   0x0091aae4u
#define FN_PERMODE      0x00942220u
#define FN_SPEED        0x00916108u
#define FN_AIM_STEP     0x00911090u
#define FN_AIM_TOWARD   0x00912288u
#define FN_MODE_OUT     0x00922ca0u
#define FN_WORK_FLAG    0x00914de0u
#define FN_RUN_FLAG     0x0091b7b0u
#define FN_CAMERA       0x00916228u
#define FN_TARGET_Y     0x00923f90u
#define FN_ANGLE_POS    0x00568c64u
#define FN_DISTANCE     0x00aacd50u

/* The fields and motions the source's handlers use. */
#define WORK_SUBSTATE   0x0145u
#define WORK_TURN       0x01a8u
#define WORK_HEADING    0x01acu
#define WORK_UP         0x0180u
#define WORK_AIM_Y      0x0164u
#define WORK_AIM_Z      0x0168u
#define WORK_AIM_BZ     0x0178u
#define ENEMY_SPEED_2   0x029cu

#define MOTION_0_CD 0x0205u
#define MOTION_0_CE 0x0206u
#define MOTION_0_CF 0x0207u
#define MOTION_0_D2 0x020au
#define MOTION_0_E1 0x0219u
#define MOTION_0_E2 0x021au
#define MOTION_0_E3 0x021bu
#define MOTION_0_E4 0x021cu
#define MOTION_0_D6 0x020eu
#define MOTION_0_D7 0x020fu
#define MOTION_0_D8 0x0210u
#define MOTION_0_D9 0x0211u
#define MOTION_0_08 0x0008u
#define MOTION_0_1B 0x001bu
#define MOTION_0_2F 0x002fu
#define MOTION_0_36 0x0036u
#define MOTION_0_37 0x0037u

#define EXTRA_VALUE 0x7fu

/* What the engine answers. */
static int fake_flag = 1;
static int fake_permode = 1;
static int fake_mode_check[4];
static int fake_turn_if = 1;
static uint32_t fake_angle;
static float fake_distance = 100.0f;
static float fake_height = 1.0f;

static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)user;
    (void)s;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_MODE_CHECK:
        return (FakeResult){(uint32_t)fake_mode_check[r[1] & 3u], 0.0f};
    case FN_PERMODE:
        return (FakeResult){(uint32_t)fake_permode, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};
    case FN_LANDING:
        return (FakeResult){(uint32_t)fake_turn_if, 0.0f};
    case FN_ANGLE_POS:
        return (FakeResult){fake_angle, 0.0f};
    case FN_DISTANCE:
        return (FakeResult){0, fake_distance};
    case FN_TARGET_Y:
        return (FakeResult){0, fake_height};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* ── helpers ─────────────────────────────────────────────────────────────────────────── */

static uint32_t next_enemy = 0x1000000u;
static uint32_t next_work = 0x00200000u;

/* A fresh monster and work block; the factory records it for the module's id. */
static void new_monster(uint32_t *enemy, uint32_t *work) {
    *enemy = next_enemy;
    *work = next_work;
    next_enemy += 0x10000u;
    next_work += 0x10000u;
    spawn(*enemy, *work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
}

static void expect(int i, uint32_t fn, const char *what) {
    CHECK(i < fake_call_count, "%s: call %d is missing (%d calls)", what, i + 1,
          fake_call_count);
    if (i < fake_call_count) {
        CHECK(fake_calls[i].fn == fn, "%s: call %d is 0x%08x, not 0x%08x", what, i + 1,
              fake_calls[i].fn, fn);
    }
}

static void expect_int(int i, uint32_t fn, uint32_t r1, const char *what) {
    expect(i, fn, what);
    if (i < fake_call_count && fake_calls[i].fn == fn) {
        CHECK(fake_calls[i].r1 == r1, "%s: r1 is 0x%x, not 0x%x", what, fake_calls[i].r1, r1);
    }
}

static void expect_float(int i, uint32_t fn, float s0, float s1, const char *what) {
    expect(i, fn, what);
    if (i < fake_call_count && fake_calls[i].fn == fn) {
        CHECK(fake_calls[i].has_s0 && fake_calls[i].s0 == s0,
              "%s: s0 is %g, not %g", what, fake_calls[i].s0, s0);
        if (fake_calls[i].has_s1) {
            CHECK(fake_calls[i].s1 == s1, "%s: s1 is %g, not %g", what, fake_calls[i].s1, s1);
        }
    }
}

static void expect_close(float got, float want, const char *what) {
    const float diff = got - want;
    CHECK(diff < 1e-4f && diff > -1e-4f, "%s: %g, not %g", what, got, want);
}

static void expect_state(uint32_t work, int state, const char *what) {
    CHECK(fake_mem_read8(work + WORK_STATE) == (uint32_t)state, "%s: state is %u, not %d", what,
          fake_mem_read8(work + WORK_STATE), state);
}

/* ── 0x00694474 -> 0x00687398: 7/3 and its nine siblings ────────────────────────────── */

/* Walk 7/3 to a state with the given work values. */
static void run_7_3_state(uint32_t enemy, uint32_t work, int state) {
    fake_mem_write8(work + WORK_STATE, (uint32_t)state);
    frame_with(enemy, work, 7, 3);
}

static void test_687398(void) {
    uint32_t enemy, work;

    /* State 0: mode 0 and motion 0xd6 (file 2, slot 14) at 4.0. */
    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 3);
    CHECK(fake_call_count == 2, "7/3 state 0 made %d calls, want 2", fake_call_count);
    expect_int(0, FN_MODE, 0, "7/3 state 0 doesn't set mode 0");
    expect_float(1, FN_MOTION, 4.0f, 0.0f, "7/3 state 0 doesn't start motion 0x20e at 4.0");
    CHECK(fake_calls[1].r1 == MOTION_0_D6, "7/3 state 0 starts motion 0x%x, not 0x20e",
          fake_calls[1].r1);
    expect_state(work, 1, "7/3 state 0");

    /* State 1: the flag, mode 3, speed 50.0, motion 0xd7 at 0.0, the extra step and the aim
     * step; the curve call is blocked. */
    new_monster(&enemy, &work);
    run_7_3_state(enemy, work, 1);
    CHECK(fake_call_count == 6, "7/3 state 1 made %d calls, want 6", fake_call_count);
    expect(0, FN_FLAG, "7/3 state 1 doesn't wait for the flag");
    expect_int(1, FN_MODE, 3, "7/3 state 1 doesn't set mode 3");
    expect_float(2, FN_SPEED, 50.0f, 0.0f, "7/3 state 1 doesn't add speed 50.0");
    expect(3, FN_MOTION, "7/3 state 1 doesn't start the second motion");
    CHECK(fake_calls[3].r1 == MOTION_0_D7, "7/3 state 1 starts motion 0x%x, not 0x20f",
          fake_calls[3].r1);
    expect(4, FN_EXTRA, "7/3 state 1 doesn't run the extra step");
    expect_float(5, FN_AIM_TOWARD, 1.0f, 0.0f, "7/3 state 1 doesn't advance the aim");
    CHECK(fake_calls[5].r1 == work + WORK_TURN, "7/3 state 1's aim call gets 0x%x, not work+0x1a8",
          fake_calls[5].r1);
    CHECK(fake_log_contains("0x0083c6e0's curve table"), "7/3 state 1 doesn't log the curve block");
    expect_state(work, 2, "7/3 state 1");

    /* State 2 with the per-mode check false: finish flag, the aim step, motion 0x1b, and the
     * substate/aim-vector stores. */
    new_monster(&enemy, &work);
    fake_mode_check[0] = 0;
    run_7_3_state(enemy, work, 2);
    CHECK(fake_call_count == 4, "7/3 state 2 made %d calls, want 4", fake_call_count);
    expect_float(0, FN_MODE_CHECK, 6.0f, 0.0f, "7/3 state 2 doesn't run the 6.0 mode check");
    expect(1, FN_FLAG, "7/3 state 2 doesn't wait for the flag");
    expect_float(2, FN_AIM_STEP, 1.0f, 0.0f, "7/3 state 2 doesn't advance the aim step");
    expect(3, FN_MOTION, "7/3 state 2 doesn't start motion 0x1b");
    CHECK(fake_calls[3].r1 == MOTION_0_1B, "7/3 state 2 starts motion 0x%x, not 0x1b",
          fake_calls[3].r1);
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == 0.5f,
          "7/3 state 2 doesn't set the aim vector's z to 0.5");
    CHECK(fake_mem_read8(work + WORK_SUBSTATE) == 1, "7/3 state 2 doesn't set the substate 1");
    expect_state(work, 3, "7/3 state 2");

    /* The same state with the per-mode check true reaches the blocked effect spawn, then the
     * same finish. */
    new_monster(&enemy, &work);
    fake_mode_check[0] = 1;
    run_7_3_state(enemy, work, 2);
    CHECK(fake_log_contains("point 0x1c72"), "7/3's effect block isn't logged");
    fake_mode_check[0] = 0;

    /* State 3, substate 0: the aim step, the aim z clamped from +2.0 to 0.0, the flag, the
     * substate and motion 0x1b. */
    new_monster(&enemy, &work);
    fake_mem_write32(work + WORK_AIM_Z, fbits(2.0f));
    run_7_3_state(enemy, work, 3);
    CHECK(fake_call_count == 3, "7/3 state 3 substate 0 made %d calls, want 3", fake_call_count);
    expect_float(0, FN_AIM_STEP, 1.0f, 0.0f, "7/3 state 3 doesn't advance the aim step");
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 0.0f,
          "7/3 state 3 doesn't clamp a positive aim z to 0.0");
    expect(1, FN_FLAG, "7/3 state 3 doesn't wait for the flag");
    expect(2, FN_MOTION, "7/3 state 3 doesn't start motion 0x1b");
    CHECK(fake_mem_read8(work + WORK_SUBSTATE) == 1, "7/3 state 3 doesn't set the substate");

    /* State 3, substate 1: the state advances and the motion is 0xd8. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_SUBSTATE, 1);
    run_7_3_state(enemy, work, 3);
    expect(2, FN_MOTION, "7/3 state 3 substate 1 doesn't start motion 0xd8");
    CHECK(fake_calls[2].r1 == MOTION_0_D8, "7/3 state 3 substate 1 starts 0x%x, not 0x210",
          fake_calls[2].r1);
    expect_state(work, 4, "7/3 state 3 substate 1");

    /* State 4: mode 0, motion 0xd9. */
    new_monster(&enemy, &work);
    run_7_3_state(enemy, work, 4);
    CHECK(fake_call_count == 3, "7/3 state 4 made %d calls, want 3", fake_call_count);
    expect(0, FN_FLAG, "7/3 state 4 doesn't wait for the flag");
    expect_int(1, FN_MODE, 0, "7/3 state 4 doesn't set mode 0");
    expect(2, FN_MOTION, "7/3 state 4 doesn't start motion 0xd9");
    CHECK(fake_calls[2].r1 == MOTION_0_D9, "7/3 state 4 starts 0x%x, not 0x211",
          fake_calls[2].r1);

    /* State 5: the finish flag falls into 0/2's base handler (the cat0 family). */
    new_monster(&enemy, &work);
    run_7_3_state(enemy, work, 5);
    CHECK(fake_call_count == 3, "7/3 state 5 made %d calls, want 3", fake_call_count);
    expect(0, FN_FLAG, "7/3 state 5 doesn't wait for the flag");
    expect_int(1, FN_MODE, 0, "7/3 state 5 doesn't run 0/2's mode 0");
    expect(2, FN_SET_ACTION, "7/3 state 5 doesn't fall into 0/2's base handler");
    CHECK(fake_calls[2].r2 == 0 && fake_calls[2].r3 == 2,
          "7/3 state 5's base handler starts %u/%u, not 0/2", fake_calls[2].r2,
          fake_calls[2].r3);

    /* 7/41 (r1 = 1) state 3 runs 0/6's base handler instead. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 3);
    frame_with(enemy, work, 7, 41);
    CHECK(fake_call_count == 4, "7/41 state 3 made %d calls, want 4", fake_call_count);
    expect_float(0, FN_AIM_STEP, 1.0f, 0.0f, "7/41 state 3 doesn't advance the aim step");
    expect(1, FN_FLAG, "7/41 state 3 doesn't wait for the flag");
    expect_int(2, FN_MODE, 3, "7/41 state 3 doesn't run 0/6's mode 3");
    expect(3, FN_SET_ACTION, "7/41 state 3 doesn't fall into 0/6's base handler");
    CHECK(fake_calls[3].r2 == 6 && fake_calls[3].r3 == 2,
          "7/41 state 3's base handler starts %u/%u, not 6/2", fake_calls[3].r2,
          fake_calls[3].r3);

    /* 7/43 (selector 2) turns toward the target first. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 43);
    CHECK(fake_call_count == 7, "7/43 state 1 made %d calls, want 7", fake_call_count);
    expect_int(0, FN_TURN, 0x400, "7/43 state 1 doesn't turn by 0x400");
    CHECK(fake_calls[0].r2 == 0, "7/43 state 1's turn gets r2 %u, not 0", fake_calls[0].r2);

    /* 7/53 (selector 3) does not turn. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 53);
    CHECK(fake_call_count == 6, "7/53 state 1 made %d calls, want 6", fake_call_count);
    expect(0, FN_FLAG, "7/53 state 1 doesn't wait for the flag");

    /* 7/72 (selector 5) state 2 goes through the 0x1555 point path: the mode check at 6.0,
     * then the finish. */
    new_monster(&enemy, &work);
    fake_mode_check[0] = 1;
    fake_mem_write8(work + WORK_STATE, 2);
    frame_with(enemy, work, 7, 72);
    CHECK(fake_call_count == 4, "7/72 state 2 made %d calls, want 4", fake_call_count);
    expect_float(0, FN_MODE_CHECK, 6.0f, 0.0f, "7/72 state 2 doesn't run the 6.0 mode check");
    CHECK(fake_log_contains("point 0x1555"),
          "7/72 state 2 doesn't take the source's 0x1555 point path");
    expect(1, FN_FLAG, "7/72 state 2 doesn't wait for the flag");
    fake_mode_check[0] = 0;
}

/* ── 0x00694f4c: 7/9, 7/14, 7/30, 7/80, 7/83, 7/88, 7/89 ───────────────────────────── */

static void test_694f4c(void) {
    uint32_t enemy, work;

    /* 7/9 (variant 0) state 0: the work-block flag, mode 0, the run flag -14 and motion 0xcd
     * at 6.0. */
    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 9);
    CHECK(fake_call_count == 4, "7/9 state 0 made %d calls, want 4", fake_call_count);
    expect_int(0, FN_WORK_FLAG, 0x20, "7/9 state 0 doesn't set the work flag 0x20");
    expect_int(1, FN_MODE, 0, "7/9 state 0 doesn't set mode 0");
    expect_int(2, FN_RUN_FLAG, (uint32_t)-14, "7/9 state 0 doesn't apply run flag -14");
    expect_float(3, FN_MOTION, 6.0f, 0.0f, "7/9 state 0 doesn't start motion 0x205 at 6.0");
    CHECK(fake_calls[3].r1 == MOTION_0_CD, "7/9 state 0 starts 0x%x, not 0x205", fake_calls[3].r1);

    /* 7/9 state 1: the flag, the data float, the fall, motion 0xce, the pair (0, 7), the
     * extra step, and the two speeds derived from this+0x29c * 2.0. */
    new_monster(&enemy, &work);
    fake_mem_write32(enemy + ENEMY_SPEED_2, fbits(0.5f));
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 9);
    CHECK(fake_call_count == 7, "7/9 state 1 made %d calls, want 7", fake_call_count);
    expect(0, FN_WORK_FLAG, "7/9 state 1 doesn't set the work flag first");
    expect(1, FN_FLAG, "7/9 state 1 doesn't wait for the flag");
    expect_float(2, FN_DATA_FLOAT, 0.0f, 0.0f, "7/9 state 1 doesn't read the data float");
    expect_float(3, FN_APPLY_FALL, 1.5f, 0.0f, "7/9 state 1 doesn't apply the data float");
    expect(4, FN_MOTION, "7/9 state 1 doesn't start motion 0xce");
    CHECK(fake_calls[4].r1 == MOTION_0_CE, "7/9 state 1 starts 0x%x, not 0x206", fake_calls[4].r1);
    expect(5, FN_MOTION_ARGS2, "7/9 state 1 doesn't call the pair (0, 7)");
    CHECK(fake_calls[5].r1 == 0 && fake_calls[5].r2 == 7, "7/9 state 1's pair is (%u, %u), not (0, 7)",
          fake_calls[5].r1, fake_calls[5].r2);
    expect(6, FN_EXTRA, "7/9 state 1 doesn't run the extra step");
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 1.0f * 34.0f,
          "7/9 state 1's aim z is %g, not 34.0", ffrom(fake_mem_read32(work + WORK_AIM_Z)));
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == 1.0f * -3.0f,
          "7/9 state 1's aim vector z is %g, not -3.0",
          ffrom(fake_mem_read32(work + WORK_AIM_BZ)));

    /* 7/9 state 2: the curve call is blocked; the turn step, the 16.0 mode check, the
     * per-mode step, then variant 0's own tail (motion 0xcf, the pair (0, 0x16), the mode
     * out). */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 2);
    fake_mem_write32(work + WORK_AIM_Z, fbits(-1.0f));
    frame_with(enemy, work, 7, 9);
    CHECK(fake_call_count == 10, "7/9 state 2 made %d calls, want 10", fake_call_count);
    expect(0, FN_WORK_FLAG, "7/9 state 2 doesn't set the work flag first");
    expect_float(1, FN_DATA_FLOAT, 0.0f, 0.0f, "7/9 state 2 doesn't read the data float");
    expect_float(2, FN_TURN_STEP, 1.5f, 1.0f, "7/9 state 2 doesn't turn at 1.5");
    CHECK(fake_calls[2].r1 == work + WORK_TURN, "7/9 state 2's turn slot is 0x%x, not work+0x1a8",
          fake_calls[2].r1);
    expect_float(3, FN_MODE_CHECK, 16.0f, 0.0f, "7/9 state 2 doesn't run the 16.0 mode check");
    CHECK(fake_calls[3].r1 == 1, "7/9 state 2's mode check gets mode %u, not 1", fake_calls[3].r1);
    expect_float(4, FN_PERMODE, 1.5f, 0.0f, "7/9 state 2 doesn't run the per-mode step");
    expect(5, FN_FLAG, "7/9 state 2 doesn't wait for the flag");
    expect_int(6, FN_MODE, 0, "7/9 state 2 doesn't set mode 0");
    expect(7, FN_MOTION, "7/9 state 2 doesn't start motion 0xcf");
    CHECK(fake_calls[7].r1 == MOTION_0_CF, "7/9 state 2 starts 0x%x, not 0x207", fake_calls[7].r1);
    expect(8, FN_MOTION_ARGS2, "7/9 state 2 doesn't call the pair (0, 0x16)");
    CHECK(fake_calls[8].r2 == 0x16, "7/9 state 2's pair r2 is 0x%x, not 0x16", fake_calls[8].r2);
    expect(9, FN_MODE_OUT, "7/9 state 2 doesn't run the mode-out step");
    CHECK(fake_mem_read8(work + WORK_SUBSTATE) == 1,
          "7/9 state 2 doesn't advance its substate");
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 0.0f,
          "7/9 state 2 doesn't zero a negative aim z");

    /* 7/14 (variant 1) state 2 ends with mode 3 and motion 0x1b, not the variant-0 tail. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 2);
    frame_with(enemy, work, 7, 14);
    const int n14 = fake_call_count;
    CHECK(n14 >= 2, "7/14 state 2 made only %d calls", n14);
    CHECK(fake_calls[n14 - 2].fn == FN_MODE && fake_calls[n14 - 2].r1 == 3,
          "7/14 state 2 doesn't end with mode 3");
    CHECK(fake_calls[n14 - 1].fn == FN_MOTION && fake_calls[n14 - 1].r1 == MOTION_0_1B,
          "7/14 state 2 doesn't end with motion 0x1b");

    /* 7/30 (variant 2) state 3: the mode out, the flag, the state advance and motion 0xcd
     * with the source's own 0x46 (70.0) as the speed. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 3);
    frame_with(enemy, work, 7, 30);
    CHECK(fake_call_count == 4, "7/30 state 3 made %d calls, want 4", fake_call_count);
    expect(0, FN_WORK_FLAG, "7/30 state 3 doesn't set the work flag first");
    expect(1, FN_MODE_OUT, "7/30 state 3 doesn't run the mode-out step");
    expect(2, FN_FLAG, "7/30 state 3 doesn't wait for the flag");
    expect_float(3, FN_MOTION, 70.0f, 0.0f, "7/30 state 3 doesn't start motion 0xcd at 70.0");
    CHECK(fake_calls[3].r1 == MOTION_0_CD, "7/30 state 3 starts 0x%x, not 0x205",
          fake_calls[3].r1);

    /* 7/80 (variant 3) state 0 starts motion 0xe1 at 0.0. */
    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 80);
    CHECK(fake_call_count == 4, "7/80 state 0 made %d calls, want 4", fake_call_count);
    expect_float(3, FN_MOTION, 0.0f, 0.0f, "7/80 state 0 doesn't start motion 0xe1 at 0.0");
    CHECK(fake_calls[3].r1 == MOTION_0_E1, "7/80 state 0 starts 0x%x, not 0x219",
          fake_calls[3].r1);

    /* 7/80 state 1: the 398.31 fall step, motion 0xe2, the pair (0, 0x26), the extra step and
     * the logged, unmapped u16 copy. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 80);
    CHECK(fake_call_count == 6, "7/80 state 1 made %d calls, want 6", fake_call_count);
    expect(1, FN_FLAG, "7/80 state 1 doesn't wait for the flag");
    expect_float(2, FN_APPLY_FALL, 398.31f, 0.0f, "7/80 state 1 doesn't apply the 398.31 fall");
    expect(3, FN_MOTION, "7/80 state 1 doesn't start motion 0xe2");
    CHECK(fake_calls[3].r1 == MOTION_0_E2, "7/80 state 1 starts 0x%x, not 0x21a",
          fake_calls[3].r1);
    CHECK(fake_calls[4].fn == FN_MOTION_ARGS2 && fake_calls[4].r2 == 0x26,
          "7/80 state 1's pair isn't (0, 0x26)");
    expect(5, FN_EXTRA, "7/80 state 1 doesn't run the extra step");
    CHECK(fake_log_contains("work+0x140"), "7/80 state 1 doesn't log the unmapped u16 copy");

    /* 7/80 state 2: the 64.0 check (which reaches the blocked 0x00842a7c and the 0x150 turn),
     * the (3, 120.0, 184.0) check, the blocked curve, the turn step and the 0.0 clamp, then
     * the (0, 184.0, 0.0) check. */
    new_monster(&enemy, &work);
    fake_mode_check[1] = 1;
    fake_mode_check[3] = 1;
    fake_mode_check[0] = 0;
    fake_mem_write8(work + WORK_STATE, 2);
    fake_mem_write32(work + WORK_AIM_Z, fbits(-2.0f));
    frame_with(enemy, work, 7, 80);
    CHECK(fake_call_count == 7, "7/80 state 2 made %d calls, want 7", fake_call_count);
    expect_float(1, FN_MODE_CHECK, 64.0f, 0.0f, "7/80 state 2 doesn't run the 64.0 check");
    expect_int(2, FN_TURN, 0x150, "7/80 state 2 doesn't turn by 0x150 after the blocked call");
    expect_float(3, FN_MODE_CHECK, 120.0f, 184.0f, "7/80 state 2 doesn't run the 120/184 check");
    CHECK(fake_calls[3].r1 == 3, "7/80 state 2's second check gets mode %u, not 3",
          fake_calls[3].r1);
    CHECK(fake_log_contains("0x00842a7c"), "7/80 state 2 doesn't log the blocked 0x00842a7c");
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 0.0f,
          "7/80 state 2 doesn't clamp the negative aim z to 0.0");
    CHECK(fake_calls[fake_call_count - 1].fn == FN_MODE_CHECK &&
              fake_calls[fake_call_count - 1].r1 == 0,
          "7/80 state 2's last check isn't mode 0");
    fake_mode_check[1] = 0;
    fake_mode_check[3] = 0;

    /* 7/80 state 3: the -2.5 vertical step, the -75.0 clamp and 0/6's base handler. */
    new_monster(&enemy, &work);
    fake_mem_write32(work + WORK_UP, fbits(-100.0f));
    fake_mem_write8(work + WORK_STATE, 3);
    frame_with(enemy, work, 7, 80);
    CHECK(fake_call_count == 5, "7/80 state 3 made %d calls, want 5", fake_call_count);
    expect_float(1, FN_VERTICAL, -2.5f, 0.0f, "7/80 state 3 doesn't step the vertical value");
    CHECK(ffrom(fake_mem_read32(work + WORK_UP)) == -75.0f,
          "7/80 state 3 doesn't clamp the vertical value at -75.0");
    expect(2, FN_FLAG, "7/80 state 3 doesn't wait for the flag");
    expect(4, FN_SET_ACTION, "7/80 state 3 doesn't fall into 0/6's base handler");
    CHECK(fake_calls[4].r2 == 6 && fake_calls[4].r3 == 2,
          "7/80 state 3's base handler starts %u/%u, not 6/2", fake_calls[4].r2,
          fake_calls[4].r3);

    /* 7/88 (variant 5) state 2 ends with the state advance and variant 0's tail, as the
     * source's 5/6 branch does. */
    new_monster(&enemy, &work);
    fake_mode_check[1] = 1;
    fake_mode_check[3] = 1;
    fake_mode_check[0] = 1;
    fake_mem_write8(work + WORK_STATE, 2);
    frame_with(enemy, work, 7, 88);
    expect_state(work, 3, "7/88 state 2");
    {
        int tail = fake_call_count;
        CHECK(tail >= 4, "7/88 state 2 made only %d calls", tail);
        CHECK(fake_calls[tail - 4].fn == FN_MODE && fake_calls[tail - 4].r1 == 0,
              "7/88 state 2 doesn't end with mode 0");
        CHECK(fake_calls[tail - 3].fn == FN_MOTION &&
                  fake_calls[tail - 3].r1 == MOTION_0_CF,
              "7/88 state 2 doesn't end with motion 0xcf");
        CHECK(fake_calls[tail - 2].fn == FN_MOTION_ARGS2 && fake_calls[tail - 2].r2 == 0x16,
              "7/88 state 2 doesn't end with the pair (0, 0x16)");
        CHECK(fake_calls[tail - 1].fn == FN_MODE_OUT, "7/88 state 2 doesn't end with the mode out");
    }
    fake_mode_check[1] = 0;
    fake_mode_check[3] = 0;
    fake_mode_check[0] = 0;

    /* 7/83 (variant 4) state 2's other tail: mode 3, motion 0x1b and the set byte. */
    new_monster(&enemy, &work);
    fake_mode_check[1] = 1;
    fake_mode_check[3] = 1;
    fake_mode_check[0] = 1;
    fake_mem_write8(work + WORK_STATE, 2);
    frame_with(enemy, work, 7, 83);
    {
        int tail = fake_call_count;
        CHECK(tail >= 3, "7/83 state 2 made only %d calls", tail);
        CHECK(fake_calls[tail - 2].fn == FN_MODE && fake_calls[tail - 2].r1 == 3,
              "7/83 state 2 doesn't end with mode 3");
        CHECK(fake_calls[tail - 1].fn == FN_MOTION && fake_calls[tail - 1].r1 == MOTION_0_1B,
              "7/83 state 2 doesn't end with motion 0x1b");
        CHECK(fake_mem_read8(work + WORK_SET) == 1, "7/83 state 2 doesn't set the set byte");
    }
    fake_mode_check[1] = 0;
    fake_mode_check[3] = 0;
    fake_mode_check[0] = 0;

    /* 7/9 state 6: the mode out, the flag and 0/2's base handler. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 6);
    frame_with(enemy, work, 7, 9);
    CHECK(fake_call_count == 5, "7/9 state 6 made %d calls, want 5", fake_call_count);
    expect(1, FN_MODE_OUT, "7/9 state 6 doesn't run the mode-out step");
    expect(2, FN_FLAG, "7/9 state 6 doesn't wait for the flag");
    expect(3, FN_MODE, "7/9 state 6 doesn't fall into 0/2's base handler");
    expect(4, FN_SET_ACTION, "7/9 state 6 doesn't fall into 0/2's base handler");
}

/* ── 0x006956e8: 7/13 ──────────────────────────────────────────────────────────────── */

static void test_6956e8(void) {
    uint32_t enemy, work;

    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 13);
    CHECK(fake_call_count == 5, "7/13 state 0 made %d calls, want 5", fake_call_count);
    expect_int(0, FN_MODE, 0, "7/13 state 0 doesn't set mode 0");
    expect_int(1, FN_RUN_FLAG, (uint32_t)-14, "7/13 state 0 doesn't apply run flag -14");
    expect_float(2, FN_MOTION, 0.0f, 0.0f, "7/13 state 0 doesn't start motion 8 at 0.0");
    CHECK(fake_calls[2].r1 == MOTION_0_08, "7/13 state 0 starts 0x%x, not 8", fake_calls[2].r1);
    expect(3, FN_MOTION_ARGS, "7/13 state 0 doesn't call the motion pair");
    CHECK(fake_calls[3].r1 == 0 && fake_calls[3].r2 == 5 && fake_calls[3].r3 == 2,
          "7/13 state 0's motion pair is (%u, %u, %u), not (0, 5, 2)", fake_calls[3].r1,
          fake_calls[3].r2, fake_calls[3].r3);
    expect_float(4, FN_BLEND, -300.0f, 0.0f, "7/13 state 0 doesn't run the blend filter at -300");
    expect_state(work, 1, "7/13 state 0");

    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 13);
    CHECK(fake_call_count == 4, "7/13 state 1 made %d calls, want 4", fake_call_count);
    expect(0, FN_LANDING, "7/13 state 1 doesn't run the landing step");
    CHECK(fake_calls[0].r2 == 0x40, "7/13 state 1's landing step is mode 0x%x, not 0x40",
          fake_calls[0].r2);
    expect_float(1, FN_MOTION, 0.0f, 0.0f, "7/13 state 1 doesn't start motion 0x2f");
    CHECK(fake_calls[1].r1 == MOTION_0_2F, "7/13 state 1 starts 0x%x, not 0x2f", fake_calls[1].r1);
    CHECK(fake_calls[2].fn == FN_MOTION_ARGS2 && fake_calls[2].r2 == 1,
          "7/13 state 1's first pair isn't (0, 1)");
    CHECK(fake_calls[3].fn == FN_MOTION_ARGS2 && fake_calls[3].r1 == 1 && fake_calls[3].r2 == 9,
          "7/13 state 1's second pair isn't (1, 9)");
    expect_state(work, 2, "7/13 state 1");

    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 2);
    frame_with(enemy, work, 7, 13);
    CHECK(fake_call_count == 3, "7/13 state 2 made %d calls, want 3", fake_call_count);
    expect(0, FN_FLAG, "7/13 state 2 doesn't wait for the flag");
    expect(1, FN_MODE, "7/13 state 2 doesn't fall into 0/2's base handler");
    expect(2, FN_SET_ACTION, "7/13 state 2 doesn't fall into 0/2's base handler");

    /* The turn condition false stops the handler after its call. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    fake_turn_if = 0;
    frame_with(enemy, work, 7, 13);
    CHECK(fake_call_count == 1, "7/13 state 1 without the landing step made %d calls, want 1",
          fake_call_count);
    fake_turn_if = 1;
}

/* ── 0x00695e68: 7/17 and 7/78 ─────────────────────────────────────────────────────── */

static void test_695e68(void) {
    uint32_t enemy, work;

    new_monster(&enemy, &work);
    fake_angle = 0;
    fake_mem_write32(work + WORK_HEADING, 0);
    frame_with(enemy, work, 7, 17);
    CHECK(fake_call_count == 9, "7/17 state 0 made %d calls, want 9", fake_call_count);
    expect_float(0, FN_VERTICAL, -2.5f, 0.0f, "7/17 state 0 doesn't step the vertical value");
    expect_int(1, FN_MODE, 3, "7/17 state 0 doesn't set mode 3");
    expect_int(2, FN_RUN_FLAG, (uint32_t)-14, "7/17 state 0 doesn't apply run flag -14");
    expect_float(3, FN_MOTION, 4.0f, 0.0f, "7/17 state 0 doesn't start motion 0x36 at 4.0");
    CHECK(fake_calls[3].r1 == MOTION_0_36, "7/17 state 0 starts 0x%x, not 0x36", fake_calls[3].r1);
    CHECK(fake_calls[4].fn == FN_MOTION_ARGS2 && fake_calls[4].r2 == 0x0c,
          "7/17 state 0's motion pair isn't (0, 0xc)");
    expect(5, FN_CAMERA, "7/17 state 0 doesn't run the camera step");
    expect(6, FN_ANGLE_POS, "7/17 state 0 doesn't read the angle to the target");
    expect(7, FN_DISTANCE, "7/17 state 0 doesn't read the distance to the target");
    expect(8, FN_TARGET_Y, "7/17 state 0 doesn't read the target's height");
    expect_close(ffrom(fake_mem_read32(work + WORK_AIM_Z)),
                 (100.0f - 1.0f * 200.0f) / 60.0f, "7/17 state 0's aim z");
    expect_state(work, 1, "7/17 state 0");

    /* The other side of the circle (the angle difference at 0x8000) has no 5.0 clamp. */
    new_monster(&enemy, &work);
    fake_angle = 0;
    fake_mem_write32(work + WORK_HEADING, 0xc000u);
    frame_with(enemy, work, 7, 17);
    expect_close(ffrom(fake_mem_read32(work + WORK_AIM_Z)),
                 (-200.0f - 100.0f) / 60.0f, "7/17's other side");

    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 17);
    CHECK(fake_call_count == 7, "7/17 state 1 made %d calls, want 7", fake_call_count);
    expect_float(1, FN_MODE_CHECK, 60.0f, 0.0f, "7/17 state 1 doesn't run the 60.0 check");
    expect_int(2, FN_TURN, 0x40, "7/17 state 1 doesn't turn by 0x40");
    expect_float(3, FN_AIM_TOWARD, 1.0f, 0.0f, "7/17 state 1 doesn't advance the aim");
    expect(4, FN_FLAG, "7/17 state 1 doesn't wait for the flag");
    expect_int(5, FN_MODE, 3, "7/17 state 1 doesn't fall into 0/6's mode 3");
    expect(6, FN_SET_ACTION, "7/17 state 1 doesn't fall into 0/6's base handler");

    /* 7/78 runs the same unit, which ignores its r1. */
    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 78);
    CHECK(fake_call_count == 9 && fake_calls[3].fn == FN_MOTION &&
              fake_calls[3].r1 == MOTION_0_36,
          "7/78 doesn't run 0x695e68's state 0");
}

/* ── 0x00696408: 7/18 and 7/21 ─────────────────────────────────────────────────────── */

static void test_696408(void) {
    uint32_t enemy, work;

    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 18);
    CHECK(fake_call_count == 5, "7/18 state 0 made %d calls, want 5", fake_call_count);
    expect_float(0, FN_VERTICAL, -2.5f, 0.0f, "7/18 state 0 doesn't step the vertical value");
    expect_int(1, FN_MODE, 3, "7/18 state 0 doesn't set mode 3");
    expect_int(2, FN_RUN_FLAG, (uint32_t)-14, "7/18 state 0 doesn't apply run flag -14");
    expect_float(3, FN_MOTION, 4.0f, 0.0f, "7/18 state 0 doesn't start motion 0x37 at 4.0");
    CHECK(fake_calls[3].r1 == MOTION_0_37, "7/18 state 0 starts 0x%x, not 0x37", fake_calls[3].r1);
    CHECK(fake_calls[4].fn == FN_MOTION_ARGS2 && fake_calls[4].r2 == 2,
          "7/18 state 0's motion pair isn't (0, 2)");

    new_monster(&enemy, &work);
    frame_with(enemy, work, 7, 21);
    CHECK(fake_call_count == 6, "7/21 state 0 made %d calls, want 6", fake_call_count);
    expect(5, FN_EXTRA, "7/21 state 0 doesn't run the extra step");
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 20.0f,
          "7/21 state 0's aim z is %g, not 20.0",
          ffrom(fake_mem_read32(work + WORK_AIM_Z)));
    CHECK(ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == -0.5f,
          "7/21 state 0's aim vector z is %g, not -0.5",
          ffrom(fake_mem_read32(work + WORK_AIM_BZ)));

    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    frame_with(enemy, work, 7, 18);
    CHECK(fake_call_count == 4, "7/18 state 1 made %d calls, want 4", fake_call_count);
    expect_float(0, FN_VERTICAL, -2.5f, 0.0f, "7/18 state 1 doesn't step the vertical value");
    expect(1, FN_FLAG, "7/18 state 1 doesn't wait for the flag");
    expect_int(2, FN_MODE, 3, "7/18 state 1 doesn't fall into 0/6's mode 3");
    expect(3, FN_SET_ACTION, "7/18 state 1 doesn't fall into 0/6's base handler");

    /* The unspent flag keeps the handler in its state. */
    new_monster(&enemy, &work);
    fake_mem_write8(work + WORK_STATE, 1);
    fake_flag = 0;
    frame_with(enemy, work, 7, 18);
    CHECK(fake_call_count == 2, "7/18 state 1 without the flag made %d calls, want 2",
          fake_call_count);
    fake_flag = 1;
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "125");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    /* The action setter's per-action value comes from MH4U's own global: point it at guest
     * memory the test controls. */
    fake_mem_write32(ACTION_EXTRA_GLOBAL, EXTRA_POINTER);
    fake_mem_write8(EXTRA_POINTER + 0x2fu, EXTRA_VALUE);

    test_687398();
    test_694f4c();
    test_6956e8();
    test_695e68();
    test_696408();

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 7 part 2's 22 ids make their calls in the source's order\n");
    return 0;
}
