/*
 * cat7c.c: category 7, part 3's fake-host test — the six handler units and the thirty-six ids
 * of 7/22 to 7/29, 7/31, 7/33, 7/35, 7/36, 7/37 and 7/57 and their siblings.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/
 * and builds it as tests/family-<stem>. The shell's test (tests/test_rathian_3u.c) covers the
 * factory association, the routing, the ready line and the self-test; this one drives the six
 * units' call sequences and the per-id dispatch.
 *
 * The expected addresses, constants and frame values are written here and in host.h, not read
 * from the module, so a change in a handler fails the test instead of moving the expectation
 * with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <string.h>

#include "host.h"

/* The work-block fields category 7 adds to host.h's list (host.h keeps cat0's). */
#define W_SUBSTATE 0x0145u
#define W_TIMER    0x01d4u
#define W_SPEED    0x0180u
#define W_TURN     0x01a8u
#define W_HEADING  0x01acu
#define W_AIM      0x0160u
#define W_AIM_Y    0x0164u
#define W_AIM_Z    0x0168u
#define W_AIM2_Z   0x0178u
#define W_TARGET   0x0218u
#define W_TARGET_Y 0x021cu
#define W_POS      0x0198u
#define W_POS_Y    0x019cu
#define W_KIND     0x01c0u
#define W_PHASE    0x03c4u

/* The MH4U engine functions category 7 calls. */
#define F_FLIGHT_SET 0x00922ca0u
#define F_MOTION     0x0094e318u
#define F_DATA       0x0093d870u
#define F_APPLY_FALL 0x0092e99cu
#define F_VERTICAL   0x00915d44u
#define F_SET_SPEED  0x00916108u
#define F_MODE_STEP  0x0091aae4u
#define F_ANGLE_STEP 0x0091aaf0u
#define F_TURN       0x0091db4cu
#define F_TURN2      0x0091b430u
#define F_ADVANCE    0x009114d4u
#define F_MOVE_BY_A  0x00955440u
#define F_CLEAR_AIM  0x0091b3bcu
#define F_CLEAR_AIM_A 0x00916228u
#define F_MOVE_Y     0x00955a5cu
#define F_GROUP      0x00914dc4u
#define F_GROUP4     0x0093310cu
#define F_DATA_GET   0x00923f90u
#define F_ANGLE_TO   0x00568c64u
#define F_DISTANCE   0x00aacd50u
#define F_PART       0x0091b7b0u
#define F_STALL_FLAG 0x0090f8fcu
#define F_TURN_LINE  0x0091656cu
#define F_TIMER_ADD  0x00b05274u

#define LINE_ADDRESS 0x00200000u

static int fake_flag = 1;
static int fake_mode_step;
static uint32_t fake_angle_step = 0x2000u;

/* What the engine answers category 7's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case F_DATA:
        return (FakeResult){0, 1.5f};
    case F_ANGLE_TO:
        return (FakeResult){0x1234u, 0.0f};
    case F_DISTANCE:
        return (FakeResult){0, 450.0f};
    case F_DATA_GET:
        return (FakeResult){0, 2.0f};
    case F_ANGLE_STEP:
        return (FakeResult){fake_angle_step, 0.0f};
    case F_MODE_STEP:
        return (FakeResult){(uint32_t)fake_mode_step, 0.0f};
    case F_TURN2:
        return (FakeResult){1u, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* One call at index i made the guest function `fn`, with `r1` when it matters. */
static void want_call(int i, uint32_t fn, uint32_t r0, const char *what) {
    CHECK(i < fake_call_count, "%s: only %d call(s)", what, fake_call_count);
    if (i >= fake_call_count) {
        return;
    }
    CHECK(fake_calls[i].fn == fn, "%s: call %d is 0x%08x, want 0x%08x", what, i,
          fake_calls[i].fn, fn);
    CHECK(fake_calls[i].r0 == r0, "%s: call %d's r0 is 0x%x, want 0x%x", what, i,
          fake_calls[i].r0, r0);
}

/* The motion a call index passes, for the per-id dispatch section. */
static int saw_motion(uint32_t motion) {
    for (int i = 0; i < fake_call_count; i++) {
        if (fake_calls[i].fn == F_MOTION && fake_calls[i].r1 == motion) {
            return 1;
        }
    }
    return 0;
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "125");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    fake_mem_write32(ACTION_EXTRA_GLOBAL, EXTRA_POINTER);
    fake_mem_write8(EXTRA_POINTER + 0x2fu, 0x7fu);

    /* ── 7/22: state 0, the launch ------------------------------------------------- */
    const uint32_t e22 = 0x300000u, w22 = 0x310000u;
    spawn(e22, w22, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e22, w22, 7, 22);
    CHECK(fake_call_count == 6, "7/22 state 0 made %d calls, want 6", fake_call_count);
    want_call(0, F_FLIGHT_SET, e22, "7/22 state 0");
    want_call(1, F_DATA, e22, "7/22 state 0");
    CHECK(fake_calls[2].fn == F_APPLY_FALL && fake_calls[2].s0 == 1.5f,
          "7/22 state 0 doesn't apply the data float to the fall");
    CHECK(fake_calls[3].fn == F_PART && fake_calls[3].r1 == 0xfffffff2u,
          "7/22 state 0 doesn't take the kind-1 part value -14 (0x%x)",
          fake_calls[3].r1);
    CHECK(fake_calls[4].fn == F_MOTION && fake_calls[4].r1 == 0x45u,
          "7/22 state 0 doesn't start motion 0x45");
    want_call(5, F_CLEAR_AIM, e22, "7/22 state 0");
    CHECK(ffrom(fake_mem_read32(w22 + W_AIM_Y)) == -2.0f
          && ffrom(fake_mem_read32(w22 + W_AIM_Z)) == 50.0f,
          "7/22 state 0 doesn't seed aim point A at -2.0/50.0");
    CHECK(fake_mem_read8(w22 + WORK_STATE) == 1, "7/22 doesn't advance its state byte");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "7/22 didn't skip the dispatcher");

    /* ── 7/22: state 1, the turn and the finish flag -------------------------------- */
    fake_reset_calls();
    fake_flag = 1;
    fake_angle_step = 0x2000u;
    fake_mem_write32(w22 + W_AIM_Z, fbits(0.0f));
    frame_with(e22, w22, 7, 22);
    CHECK(fake_call_count == 9, "7/22 state 1 made %d calls, want 9", fake_call_count);
    want_call(0, F_FLIGHT_SET, e22, "7/22 state 1");
    CHECK(fake_calls[1].fn == F_MOVE_Y && fake_calls[1].s0 == 5.0f,
          "7/22 state 1 doesn't move y by the source's 5.0");
    CHECK(fake_calls[2].fn == F_ANGLE_STEP && fake_calls[2].r1 == 0x2800u
          && fake_calls[2].r3 == 0x180u,
          "7/22 state 1 doesn't take the r2=0 turn value 0x2800 at 0x180 (r1 0x%x, r3 0x%x)",
          fake_calls[2].r1, fake_calls[2].r3);
    CHECK(fake_calls[3].fn == F_TURN && fake_calls[3].r1 == 0x600u,
          "7/22 state 1 doesn't turn at 0x600");
    CHECK(fake_calls[4].fn == F_DATA, "7/22 state 1 doesn't read the data float");
    CHECK(fake_calls[5].fn == F_TURN2 && fake_calls[5].r1 == w22 + W_TURN
          && fake_calls[5].s0 == -198.5f && fake_calls[5].s1 == 1.0f,
          "7/22 state 1 doesn't run the turn at the data float - 200.0");
    CHECK(fake_calls[6].fn == FN_FLAG, "7/22 state 1 doesn't test the finish flag");
    CHECK(fake_calls[7].fn == F_MOTION && fake_calls[7].r1 == 0x3eu,
          "7/22 state 1 doesn't start motion 0x3e");
    CHECK(fake_calls[8].fn == F_GROUP4 && fake_calls[8].r2 == 0x0eu
          && fake_calls[8].r3 == 3u,
          "7/22 state 1 doesn't set part group 0xe/3");
    CHECK(fake_mem_read32(w22 + W_TURN) == 0x2000u, "7/22 state 1 doesn't keep the turn value");
    CHECK(fake_mem_read8(w22 + WORK_STATE) == 2, "7/22 state 1 doesn't advance its state");
    CHECK(fake_mem_read8(w22 + W_PHASE) == 1, "7/22 state 1 doesn't set the phase byte");
    CHECK(ffrom(fake_mem_read32(w22 + W_AIM2_Z)) == 3.0f,
          "7/22 state 1 doesn't set aim vector B's z to 3.0");

    /* ── 7/22: state 2, the timer and the second motion ----------------------------- */
    fake_reset_calls();
    fake_mem_write8(w22 + WORK_STATE, 2);
    fake_mem_write32(w22 + W_TIMER, fbits(0.0f));
    frame_with(e22, w22, 7, 22);
    CHECK(fake_call_count == 7, "7/22 state 2 made %d calls, want 7", fake_call_count);
    want_call(0, F_FLIGHT_SET, e22, "7/22 state 2");
    CHECK(fake_calls[1].fn == F_TIMER_ADD && fake_calls[1].r1 == w22 + W_TIMER,
          "7/22 state 2 doesn't add the frame delta to its timer");
    CHECK(fake_calls[2].fn == F_DATA && fake_calls[3].fn == F_TURN2
          && fake_calls[3].s0 == -198.5f,
          "7/22 state 2 doesn't run the turn at the data float - 200.0");
    CHECK(fake_calls[4].fn == FN_MODE && fake_calls[4].r1 == 3u,
          "7/22 state 2 doesn't set mode 3");
    CHECK(fake_calls[5].fn == F_MOTION && fake_calls[5].r1 == 0x3fu,
          "7/22 state 2 doesn't start motion 0x3f");
    CHECK(fake_calls[6].fn == F_SET_SPEED && fake_calls[6].s0 == -200.0f,
          "7/22 state 2 doesn't set the speed to -200.0");
    CHECK(fake_mem_read8(w22 + WORK_STATE) == 3, "7/22 state 2 doesn't advance its state");

    /* ── 7/22: state 3, the third motion -------------------------------------------- */
    fake_reset_calls();
    fake_mem_write8(w22 + WORK_STATE, 3);
    frame_with(e22, w22, 7, 22);
    CHECK(fake_call_count == 5, "7/22 state 3 made %d calls, want 5", fake_call_count);
    CHECK(fake_calls[1].fn == F_SET_SPEED && fake_calls[1].s0 == -200.0f,
          "7/22 state 3 doesn't set the speed to -200.0");
    CHECK(fake_calls[2].fn == F_ADVANCE && fake_calls[2].r1 == w22 + W_TURN
          && fake_calls[2].s0 == 1.0f,
          "7/22 state 3 doesn't advance along the path at 1.0");
    CHECK(fake_calls[3].fn == FN_FLAG && fake_calls[4].fn == F_MOTION
          && fake_calls[4].r1 == 0x208u,
          "7/22 state 3 doesn't start motion 0xd0 as MH4U's 0x208");
    CHECK(fake_mem_read8(w22 + WORK_STATE) == 4, "7/22 state 3 doesn't advance its state");

    /* ── 7/57: the a=2 variant's state 4 motion ------------------------------------- */
    const uint32_t e57 = 0x320000u, w57 = 0x330000u;
    spawn(e57, w57, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w57 + WORK_STATE, 4);
    fake_mem_write32(w57 + W_TIMER, fbits(7.0f));
    fake_reset_calls();
    frame_with(e57, w57, 7, 57);
    CHECK(fake_call_count == 5, "7/57 state 4 made %d calls, want 5", fake_call_count);
    CHECK(fake_calls[1].fn == F_SET_SPEED && fake_calls[2].fn == F_ADVANCE
          && fake_calls[3].fn == F_TIMER_ADD,
          "7/57 state 4 doesn't run the speed, the advance and the timer");
    CHECK(fake_calls[4].fn == F_MOTION && fake_calls[4].r1 == 0x35u,
          "7/57 state 4 doesn't start motion 0x35 (r1 0x%x)", fake_calls[4].r1);
    CHECK(fake_mem_read8(w57 + WORK_STATE) == 5 && fake_mem_read8(w57 + W_SUBSTATE) == 0,
          "7/57 state 4 doesn't advance to state 5");

    /* ── 7/57: state 5's 150-timer substate and the 0/2 base handler ---------------- */
    fake_reset_calls();
    fake_mem_write32(w57 + W_TIMER, fbits(0.0f));
    frame_with(e57, w57, 7, 57);
    CHECK(fake_call_count == 7, "7/57 state 5 sub 0 made %d calls, want 7", fake_call_count);
    CHECK(fake_calls[1].fn == F_TIMER_ADD, "7/57 sub 0 doesn't add the frame delta");
    CHECK(fake_calls[2].fn == F_SET_SPEED && fake_calls[2].s0 == -200.0f,
          "7/57 sub 0 doesn't set the source's (5.0 - timer) * -200.0 * 0.2 (s0 %g)",
          (double)fake_calls[2].s0);
    CHECK(fake_calls[3].fn == FN_FLAG && fake_calls[4].fn == F_STALL_FLAG
          && fake_calls[5].fn == FN_MODE && fake_calls[6].fn == F_MOTION
          && fake_calls[6].r1 == 0x3cu,
          "7/57 sub 0 doesn't finish into motion 0x3c");
    CHECK(fake_mem_read8(w57 + W_SUBSTATE) == 1, "7/57 sub 0 doesn't advance its sub-state");

    fake_reset_calls();
    fake_mem_write8(w57 + W_SUBSTATE, 1);
    frame_with(e57, w57, 7, 57);
    /* The flag, then 0/2's base handler: mode 0 and the action setter. */
    CHECK(fake_calls[1].fn == FN_FLAG, "7/57 sub 1 doesn't test the flag");
    CHECK(fake_calls[2].fn == FN_MODE && fake_calls[2].r1 == 0,
          "7/57 sub 1 doesn't fall into 0/2's mode 0");
    CHECK(fake_calls[3].fn == FN_SET_ACTION, "7/57 sub 1 doesn't reach 0/2's action setter");

    /* ── 7/31: the target line, the ratio and the three states ---------------------- */
    const uint32_t e31 = 0x340000u, w31 = 0x350000u;
    spawn(e31, w31, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write32(e31 + 0x8d88u, LINE_ADDRESS);
    fake_reset_calls();
    frame_with(e31, w31, 7, 31);
    CHECK(fake_call_count == 7, "7/31 state 0 made %d calls, want 7", fake_call_count);
    want_call(0, F_FLIGHT_SET, e31, "7/31 state 0");
    CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 3u,
          "7/31 state 0 doesn't set mode 3");
    CHECK(fake_calls[2].fn == F_PART, "7/31 state 0 doesn't run the part step");
    CHECK(fake_calls[3].fn == F_MOTION && fake_calls[3].r1 == 0x200u,
          "7/31 state 0 doesn't start motion 0xc8 as MH4U's 0x200");
    CHECK(fake_calls[4].fn == F_GROUP && fake_calls[4].r2 == 0x17u,
          "7/31 state 0 doesn't set part group 0x17");
    CHECK(fake_calls[5].fn == F_CLEAR_AIM, "7/31 state 0 doesn't clear the aim");
    CHECK(fake_calls[6].fn == F_DISTANCE, "7/31 state 0 doesn't measure to the target");
    CHECK(ffrom(fake_mem_read32(LINE_ADDRESS)) == 1.0f,
          "7/31 state 0 doesn't store the distance ratio 1.0 in the line's first float");
    CHECK(fake_mem_read8(w31 + WORK_STATE) == 1, "7/31 doesn't advance its state byte");

    fake_reset_calls();
    fake_mem_write32(w31 + W_SPEED, 0);
    frame_with(e31, w31, 7, 31);
    CHECK(fake_call_count == 8, "7/31 state 1 made %d calls, want 8", fake_call_count);
    want_call(0, F_FLIGHT_SET, e31, "7/31 state 1");
    CHECK(fake_calls[1].fn == F_DATA, "7/31 state 1 doesn't read the data float");
    CHECK(fake_calls[2].fn == F_TURN_LINE && fake_calls[2].r1 == w31 + W_TURN
          && fake_calls[2].s0 == 1.5f && fake_calls[2].s1 == 0.0f,
          "7/31 state 1 doesn't run the line turn at the data float");
    CHECK(fake_calls[3].fn == F_MODE_STEP && fake_calls[3].r1 == 1u
          && fake_calls[3].s0 == 36.0f && fake_calls[3].s1 == 1.0f,
          "7/31 state 1 doesn't check the source's 36.0/1.0");
    CHECK(fake_calls[4].fn == F_TURN && fake_calls[4].r1 == 0x100u,
          "7/31 state 1 doesn't turn at 0x100");
    CHECK(fake_calls[5].fn == FN_FLAG, "7/31 state 1 doesn't test the flag");
    CHECK(fake_calls[6].fn == FN_MODE && fake_calls[6].r1 == 0u,
          "7/31 state 1 doesn't set mode 0");
    CHECK(fake_calls[7].fn == F_MOTION && fake_calls[7].r1 == 0x214u,
          "7/31 state 1 doesn't start motion 0xdc as MH4U's 0x214");
    CHECK(fake_mem_read8(w31 + WORK_STATE) == 2, "7/31 state 1 doesn't advance to state 2");

    fake_reset_calls();
    fake_mode_step = 1;
    fake_mem_write8(w31 + W_SUBSTATE, 0);
    frame_with(e31, w31, 7, 31);
    CHECK(fake_calls[0].fn == F_FLIGHT_SET, "7/31 state 2 sub 0 doesn't start with the flight byte");
    CHECK(fake_calls[1].fn == F_MODE_STEP && fake_calls[1].s0 == 30.0f
          && fake_calls[1].s1 == 1.0f,
          "7/31 state 2 sub 0 doesn't check the source's 30.0/1.0");
    CHECK(fake_mem_read8(w31 + W_SUBSTATE) == 1,
          "7/31 state 2 sub 0 doesn't advance its sub-state");
    fake_mode_step = 0;

    /* ── 7/33: the four states ------------------------------------------------------- */
    const uint32_t e33 = 0x360000u, w33 = 0x370000u;
    spawn(e33, w33, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e33, w33, 7, 33);
    CHECK(fake_call_count == 8, "7/33 state 0 made %d calls, want 8", fake_call_count);
    want_call(0, F_FLIGHT_SET, e33, "7/33 state 0");
    CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 3u, "7/33 state 0's mode");
    CHECK(fake_calls[2].fn == F_PART, "7/33 state 0's part step");
    CHECK(fake_calls[3].fn == F_MOTION && fake_calls[3].r1 == 0x209u,
          "7/33 state 0 doesn't start motion 0xd1 as MH4U's 0x209");
    CHECK(fake_calls[4].fn == F_GROUP4 && fake_calls[4].r1 == 0u && fake_calls[4].r2 == 6u
          && fake_calls[4].r3 == 8u, "7/33 state 0's first part group");
    CHECK(fake_calls[5].fn == F_GROUP4 && fake_calls[5].r1 == 1u && fake_calls[5].r2 == 3u
          && fake_calls[5].r3 == 0x10u, "7/33 state 0's second part group");
    CHECK(fake_calls[6].fn == F_CLEAR_AIM, "7/33 state 0's clear aim");
    CHECK(fake_calls[7].fn == F_SET_SPEED && fake_calls[7].s0 == 0.0f,
          "7/33 state 0's speed 0.0");

    fake_reset_calls();
    fake_mode_step = 1;
    fake_mem_write8(w33 + WORK_STATE, 1);
    frame_with(e33, w33, 7, 33);
    CHECK(fake_call_count == 3, "7/33 state 1 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[1].fn == F_TURN && fake_calls[1].r1 == 0x2d8u,
          "7/33 state 1 doesn't turn at 0x2d8");
    CHECK(fake_calls[2].fn == F_MODE_STEP && fake_calls[2].s0 == 80.0f,
          "7/33 state 1 doesn't check the source's 80.0");
    CHECK(fake_mem_read8(w33 + WORK_STATE) == 2, "7/33 state 1 doesn't advance to state 2");
    fake_mode_step = 0;

    /* ── 7/35: the per-frame vertical step and the two states ----------------------- */
    const uint32_t e35 = 0x380000u, w35 = 0x390000u;
    spawn(e35, w35, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write32(w35 + W_SPEED, fbits(-100.0f));
    fake_reset_calls();
    frame_with(e35, w35, 7, 35);
    CHECK(fake_call_count == 5, "7/35 state 0 made %d calls, want 5", fake_call_count);
    CHECK(fake_calls[0].fn == F_VERTICAL && fake_calls[0].s0 == -5.0f,
          "7/35 doesn't take the source's -5.0 vertical step");
    CHECK(ffrom(fake_mem_read32(w35 + W_SPEED)) == -75.0f,
          "7/35 doesn't clamp the vertical value at -75.0");
    CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 3u, "7/35 state 0's mode 3");
    CHECK(fake_calls[2].fn == F_PART, "7/35 state 0's part step");
    CHECK(fake_calls[3].fn == F_MOTION && fake_calls[3].r1 == 0x205u,
          "7/35 state 0 doesn't start motion 0xcd as MH4U's 0x205");
    CHECK(fake_calls[4].fn == F_CLEAR_AIM_A, "7/35 state 0 doesn't clear aim point A");

    fake_reset_calls();
    fake_mode_step = 1;
    fake_mem_write8(w35 + WORK_STATE, 1);
    frame_with(e35, w35, 7, 35);
    CHECK(fake_call_count == 6, "7/35 state 1 made %d calls, want 6", fake_call_count);
    CHECK(fake_calls[0].fn == F_VERTICAL, "7/35 state 1 lacks the vertical step");
    CHECK(fake_calls[1].fn == F_MODE_STEP && fake_calls[1].r1 == 1u
          && fake_calls[1].s0 == 55.0f, "7/35 state 1 doesn't check the source's 55.0");
    CHECK(fake_calls[2].fn == F_MODE_STEP && fake_calls[2].r1 == 0u
          && fake_calls[2].s0 == 82.0f, "7/35 state 1 doesn't check the source's 82.0");
    CHECK(fake_calls[3].fn == FN_FLAG, "7/35 state 1 doesn't test the flag");
    CHECK(fake_calls[4].fn == FN_MODE && fake_calls[4].r1 == 3u,
          "7/35 state 1 doesn't fall into 0/6's mode 3");
    CHECK(fake_calls[5].fn == FN_SET_ACTION, "7/35 state 1 doesn't reach 0/6's action setter");
    fake_mode_step = 0;

    /* ── 7/36: the four states, on the a=2 id 7/39 ------------------------------- */
    const uint32_t e39 = 0x3a0000u, w39 = 0x3b0000u;
    spawn(e39, w39, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e39, w39, 7, 39);
    CHECK(fake_call_count == 5, "7/39 state 0 made %d calls, want 5", fake_call_count);
    CHECK(fake_calls[0].fn == F_DATA && fake_calls[1].fn == F_APPLY_FALL,
          "7/39 state 0 doesn't read and apply the data float");
    CHECK(fake_calls[2].fn == F_PART, "7/39 state 0's part step");
    CHECK(fake_calls[3].fn == F_MOTION && fake_calls[3].r1 == 0x20bu,
          "7/39 state 0 doesn't start motion 0xd3 as MH4U's 0x20b");
    CHECK(fake_calls[4].fn == F_CLEAR_AIM_A, "7/39 state 0 doesn't clear aim point A");
    CHECK(ffrom(fake_mem_read32(w39 + W_AIM_Z)) == 10.0f,
          "7/39 state 0 doesn't set aim z to the source's 10.0");

    fake_reset_calls();
    fake_mem_write8(w39 + WORK_STATE, 1);
    frame_with(e39, w39, 7, 39);
    CHECK(fake_call_count == 4, "7/39 state 1 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == F_TURN && fake_calls[0].r1 == 0x40u,
          "7/39 state 1 doesn't turn at 0x40");
    CHECK(fake_calls[1].fn == F_ADVANCE && fake_calls[1].s0 == 1.0f,
          "7/39 state 1 doesn't advance along the path");
    CHECK(fake_calls[2].fn == FN_FLAG && fake_calls[3].fn == F_MOTION
          && fake_calls[3].r1 == 0x20cu,
          "7/39 state 1 doesn't start motion 0xd4 as MH4U's 0x20c");
    CHECK(fake_mem_read8(w39 + WORK_STATE) == 2 && fake_mem_read8(w39 + W_SUBSTATE) == 0,
          "7/39 state 1 doesn't advance to state 2");

    fake_reset_calls();
    fake_mode_step = 1;
    frame_with(e39, w39, 7, 39);
    CHECK(fake_call_count == 4, "7/39 state 2 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == F_ADVANCE, "7/39 state 2 doesn't advance along the path");
    CHECK(fake_calls[1].fn == F_MODE_STEP && fake_calls[1].s0 == 40.0f,
          "7/39 state 2 doesn't check the source's 40.0");
    CHECK(fake_calls[2].fn == FN_FLAG && fake_calls[3].fn == F_MOTION
          && fake_calls[3].r1 == 0x20du,
          "7/39 state 2 doesn't start motion 0xd5 as MH4U's 0x20d");
    CHECK(fake_mem_read8(w39 + WORK_STATE) == 3, "7/39 state 2 doesn't advance to state 3");
    fake_mode_step = 0;

    /* ── 7/37: the stored point, the target line and the part group ----------------- */
    const uint32_t e37 = 0x3c0000u, w37 = 0x3d0000u;
    spawn(e37, w37, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write32(e37 + 0x8d88u, LINE_ADDRESS);
    fake_mem_write32(e37 + 0x29cu, fbits(2.0f));
    fake_reset_calls();
    frame_with(e37, w37, 7, 37);
    CHECK(fake_call_count == 7, "7/37 state 0 made %d calls, want 7", fake_call_count);
    CHECK(fake_calls[0].fn == F_GROUP && fake_calls[0].r1 == 0x20u,
          "7/37 doesn't take the r1=0x20 part group every frame");
    CHECK(fake_calls[1].fn == F_DATA && fake_calls[2].fn == F_APPLY_FALL,
          "7/37 state 0 doesn't read and apply the data float");
    CHECK(fake_calls[3].fn == F_PART, "7/37 state 0's part step");
    CHECK(fake_calls[4].fn == F_MOTION && fake_calls[4].r1 == 0x213u,
          "7/37 state 0 doesn't start motion 0xdb as MH4U's 0x213");
    CHECK(fake_calls[5].fn == F_GROUP && fake_calls[5].r2 == 0x1fu,
          "7/37 state 0 doesn't set part group 0x1f");
    CHECK(fake_calls[6].fn == F_CLEAR_AIM, "7/37 state 0 doesn't clear the aim");
    CHECK(ffrom(fake_mem_read32(w37 + W_TIMER)) == 10.0f,
          "7/37 state 0 doesn't start the timer at 20.0 / the monster's speed");

    /* State 2 reads the point state 0 kept: put the monster at 3.0 first. */
    fake_reset_calls();
    fake_mem_write8(w37 + WORK_STATE, 2);
    fake_mem_write32(w37 + W_TIMER, fbits(1.0f));
    fake_mem_write32(w37 + W_POS, fbits(3.0f));
    frame_with(e37, w37, 7, 37);
    CHECK(fake_calls[0].fn == F_GROUP && fake_calls[0].r1 == 0x20u,
          "7/37 state 2 lacks the per-frame part group");
    CHECK(fake_calls[1].fn == F_ANGLE_STEP && fake_calls[1].r3 == 0x300u,
          "7/37 state 2 doesn't turn toward the line's heading");
    CHECK(fake_calls[2].fn == F_CLEAR_AIM_A, "7/37 state 2 doesn't clear aim point A");
    CHECK(fake_calls[3].fn == F_MOVE_BY_A && fake_calls[3].s0 == 1.0f,
          "7/37 state 2 doesn't advance by aim point A at 1.0");
    CHECK(ffrom(fake_mem_read32(w37 + W_AIM)) == -3.0f,
          "7/37 state 2 doesn't compute aim x from the point state 0 kept (got %g)",
          (double)ffrom(fake_mem_read32(w37 + W_AIM)));
    CHECK(fake_mem_read32(w37 + W_HEADING) == 0x2000u,
          "7/37 state 2 doesn't keep the angle step's result as the heading");
    CHECK(fake_calls[4].fn == FN_FLAG, "7/37 state 2 doesn't test the flag");

    /* 7/84 runs the same unit with (0,1,1,1): part group 0x2a, no heading turn. */
    const uint32_t e84 = 0x3e0000u, w84 = 0x3f0000u;
    spawn(e84, w84, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e84, w84, 7, 84);
    CHECK(fake_calls[5].fn == F_GROUP && fake_calls[5].r2 == 0x2au,
          "7/84 state 0 doesn't set part group 0x2a (r2 0x%x)", fake_calls[5].r2);

    /* 7/86 runs a=2: state 2's flag goes to mode 3 and motion 0x1b. */
    const uint32_t e86 = 0x400000u, w86 = 0x410000u;
    spawn(e86, w86, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w86 + WORK_STATE, 2);
    fake_reset_calls();
    frame_with(e86, w86, 7, 86);
    CHECK(fake_calls[0].fn == F_GROUP && fake_calls[0].r1 == 0x20u, "7/86 state 2's part group");
    int seen_mode = 0, seen_motion = 0;
    for (int i = 0; i < fake_call_count; i++) {
        if (fake_calls[i].fn == FN_MODE && fake_calls[i].r1 == 3u) {
            seen_mode = 1;
        }
        if (fake_calls[i].fn == F_MOTION && fake_calls[i].r1 == 0x1bu) {
            seen_motion = 1;
        }
    }
    CHECK(seen_mode && seen_motion,
          "7/86 state 2 doesn't finish into mode 3 and motion 0x1b");
    CHECK(fake_mem_read8(w86 + WORK_STATE) == 3, "7/86 state 2 doesn't advance to state 3");

    /* ── every id reaches its unit's first motion, and the dispatcher is skipped ---- */
    static const struct {
        int id;
        uint32_t motion;
    } first_motion[] = {
        {22, 0x45u}, {23, 0x45u}, {24, 0x45u}, {25, 0x45u}, {26, 0x45u}, {27, 0x45u},
        {28, 0x45u}, {29, 0x45u}, {57, 0x45u}, {31, 0x200u}, {33, 0x209u},
        {35, 0x205u}, {46, 0x205u}, {47, 0x205u}, {48, 0x205u}, {62, 0x205u},
        {63, 0x205u}, {64, 0x205u}, {65, 0x205u},
        {36, 0x20bu}, {38, 0x20bu}, {39, 0x20bu}, {40, 0x20bu}, {49, 0x20bu},
        {50, 0x20bu}, {51, 0x20bu}, {52, 0x20bu}, {59, 0x20bu}, {60, 0x20bu},
        {37, 0x213u}, {84, 0x213u}, {86, 0x213u}, {87, 0x213u}, {92, 0x213u},
        {93, 0x213u}, {96, 0x213u},
    };
    const size_t count = sizeof first_motion / sizeof first_motion[0];
    CHECK(count == 36, "the per-id table has %zu ids, want 36", count);
    for (size_t i = 0; i < count; i++) {
        const uint32_t enemy = 0x500000u + (uint32_t)i * 0x20000u;
        const uint32_t work = enemy + 0x10000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 7, first_motion[i].id);
        CHECK(fake_skip_count == 1 && fake_original_count == 0,
              "7/%d didn't run the module's handler", first_motion[i].id);
        CHECK(saw_motion(first_motion[i].motion),
              "7/%d didn't start its unit's first motion 0x%x", first_motion[i].id,
              first_motion[i].motion);
    }

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 7 part 3's six units and thirty-six ids make their calls\n");
    return 0;
}
