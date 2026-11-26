/*
 * cat3b.c: category 3's part 2 on the fake host — 3/6, 3/7, 3/8, 3/12, 3/13, 3/16, 3/17,
 * 3/18, 3/19, 3/20, 3/21, 3/24, 3/25, 3/27, 3/28 and 3/29.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/
 * and builds it as tests/family-<stem>, so a slice adds its test file and edits nothing shared.
 * The shell's test (tests/test_rathian_3u.c) covers the factory association, the routing, the
 * ready line and the self-test; this one drives the sixteen ids' call sequences on the fake
 * host.
 *
 * The expected addresses, constants and frame values are written here and in
 * tests/rathian-3u/host.h, not read from the module, so a change in a handler fails the test
 * instead of moving the expectation with it. The extra work-block offsets and 3U-to-MH4U call
 * map this family needs are local to this file; the family test writes no other helper.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The work-block fields category 3's part 2 reads beyond host.h's list (MH4U's offsets, the
 * 3U offset each stands for in the family's comments). */
#define WORK_SUB      0x0145u  /* 3U +0x6 */
#define WORK_SUB2     0x0146u  /* 3U +0x7 */
#define WORK_TURN     0x01a8u  /* 3U +0x80 */
#define WORK_AIM_Y    0x0164u  /* 3U +0x264 */
#define WORK_AIM_Z    0x0168u  /* 3U +0x268 */
#define WORK_AIM_B_Z  0x0178u  /* 3U +0x278 */
#define WORK_TARGET_Z 0x0220u  /* 3U +0x28c */
#define WORK_LIMIT    0x0624u  /* 3U +0x120 */
#define WORK_MARKED   0x03c4u  /* 3U +0x7c9 */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_MOTION       0x0094e318u /* [0x00828828] */
#define FN_FLY          0x00922ca0u /* [0x0083d18c] */
#define FN_RATE         0x00923f90u /* [0x0083db3c] */
#define FN_CURVE        0x00922250u /* [0x0083c6e0] */
#define FN_ADVANCE_POS  0x00955440u /* [0x0082b268] */
#define FN_CLEAR_AIM_A  0x00916228u /* [0x0082fc8c] */
#define FN_CLEAR_AIM    0x0096e164u /* [0x00839968, 0x0084d790] */
#define FN_RANGE        0x0091aae4u /* [0x0083336c] */
#define FN_TURN_TO      0x0091db4cu /* [0x008357b0] */
#define FN_TURN_HOLD    0x0091b430u /* [0x00839ea0] */
#define FN_POINT_TURN   0x0092dcccu /* [0x008438e8] */
#define FN_SETUP_POINT  0x0092dc50u /* [0x008437f4] */
#define FN_TURN2        0x0092fc84u /* [0x0083d884] */
#define FN_START_ACTION 0x00935a90u /* [0x0084dc84] */
#define FN_NEXT_ACTION  0x0094ef64u /* [0x0082a06c] */
#define FN_SHELL        0x00914dc4u /* [0x00844a38] */
#define FN_PREP_FALL    0x0093cd70u /* [0x008509a0] */
#define FN_PREP_TURN    0x0093ce60u /* [0x00850a50] */
#define FN_CHECK        0x00942220u /* [0x0083369c] */
#define FN_TURN_DESCEND 0x00938f6cu /* [0x0084d7e4] */

/* The source's motions in MH4U's `file << 8 | slot` form and its next actions. */
#define MOTION_3_6     0x1au
#define MOTION_3_8_A   0x2du
#define MOTION_3_8_B   0x3du
#define MOTION_3_8_C   0x3eu
#define MOTION_3_12    0x3du
#define MOTION_3_27_A  0x1au
#define MOTION_3_27_B  0x1du
#define MOTION_3_27_C  0x207u  /* 3U 0xcf: file 2, slot 7 */
#define MOTION_3_27_D  0x219u  /* 3U 0xe1: file 2, slot 25 */
#define CURVE_3_6      0x00fd18a0u
#define TURN_RATE_3_7  0x100u
#define TURN_RATE_TWO  0x80u
#define TURN_RATE_ONE  0x40u

#define RECORD_ADDRESS 0x00050000u

static int fake_flag = 1;
static int fake_range = 1;
static int fake_turn = 1;
static int fake_turn_to = 1;
static int fake_point_turn = 1;
static int fake_check = 1;

/* What the engine answers this family's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};          /* the action data's float, in s0 */
    case FN_CURVE:
        return (FakeResult){0, 2.0f};          /* the curve's value at the speed, in s0 */
    case FN_RATE:
        return (FakeResult){0, 2.0f};          /* 0x83db3c's rate, in s0 */
    case FN_DATA_GET:
        return (FakeResult){RECORD_ADDRESS, 0.0f};
    case FN_RANGE:
        return (FakeResult){(uint32_t)fake_range, 0.0f};
    case FN_TURN_TO:
        return (FakeResult){(uint32_t)fake_turn_to, 0.0f};
    case FN_TURN_HOLD:
        return (FakeResult){(uint32_t)fake_turn, 0.0f};
    case FN_POINT_TURN:
        return (FakeResult){(uint32_t)fake_point_turn, 0.0f};
    case FN_CHECK:
        return (FakeResult){(uint32_t)fake_check, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* Check one guest call's function and integer arguments. */
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
    fake_mem_write32(ACTION_EXTRA_GLOBAL, EXTRA_POINTER);
    fake_mem_write8(EXTRA_POINTER + 0x2fu, 0x7fu);

    /* ── 3/6 (0x0068e448, r1 0 r2 0): the curve, the fall, the height test ─────────── */
    const uint32_t e06 = 0x30000u, w06 = 0x40000u;
    spawn(e06, w06, MHUC_MONSTER_ID_RATHIAN_3U, 1);

    fake_reset_calls();
    frame_with(e06, w06, 3, 6);              /* state 0 */
    CHECK(fake_call_count == 4, "3/6 state 0 made %d calls, want 4", fake_call_count);
    CALL(0, FN_DATA_FLOAT);
    CALL(1, FN_APPLY_FALL);
    CHECK(fake_calls[1].s0 == 1.5f, "3/6 doesn't advance the fall by the data float");
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == MOTION_3_6 && fake_calls[2].s0 == 6.0f
          && fake_calls[2].s1 == 0.0f, "3/6 doesn't request motion 0x1a at 6.0");
    CALL(3, FN_CLEAR_AIM_A);
    CHECK(fake_mem_read8(w06 + WORK_STATE) == 1 && fake_mem_read8(w06 + WORK_SUB) == 0
          && fake_mem_read8(w06 + WORK_SUB2) == 0, "3/6 doesn't set its state and sub-states");

    fake_reset_calls();
    fake_flag = 1;
    frame_with(e06, w06, 3, 6);              /* state 1, sub 0, third 0 */
    CHECK(fake_call_count == 3, "3/6 sub 0 made %d calls, want 3", fake_call_count);
    CALL(0, FN_CURVE);
    CHECK(fake_calls[0].r1 == CURVE_3_6, "3/6 doesn't pass MH4U's own 3/6 curve");
    CALL(1, FN_ADVANCE_POS);
    CHECK(fake_calls[1].s0 == 0.5f, "3/6 doesn't halve the source's 0.5 advance");
    CALL(2, FN_FLAG);
    CHECK(ffrom(fake_mem_read32(w06 + WORK_AIM_Y)) == 2.0f,
          "3/6 doesn't store the curve at aim A y");
    CHECK(fake_mem_read8(w06 + WORK_SUB2) == 1, "3/6 doesn't count the first flag");

    fake_reset_calls();
    frame_with(e06, w06, 3, 6);              /* state 1, sub 0, third 1 */
    CHECK(fake_call_count == 4 && fake_calls[3].fn == FN_CLEAR_AIM,
          "3/6 doesn't clear the aim after the second flag");
    CHECK(fake_mem_read8(w06 + WORK_SUB) == 1, "3/6 doesn't move to sub 1");

    /* sub 1: the turn and descent, then the blocked 0x0064325c's branch; y high ends in 0/3 */
    fake_reset_calls();
    fake_mem_write32(w06 + WORK_POS_Y, fbits(10000.0f));
    frame_with(e06, w06, 3, 6);
    CHECK(fake_call_count == 4, "3/6 sub 1 made %d calls, want 4", fake_call_count);
    CALL(0, FN_TURN_DESCEND);
    CALL(1, FN_DATA_GET);
    CALL(2, FN_MODE);
    CHECK(fake_calls[2].r1 == 1, "3/6 doesn't fall into 0/3's mode 1");
    CALL(3, FN_SET_ACTION);
    CHECK(fake_calls[3].r1 == 0 && fake_calls[3].r2 == 3 && fake_calls[3].r3 == 2,
          "3/6 doesn't fall into 0/3's action start");
    CHECK(fake_log_contains("0x0064325c"), "3/6 doesn't log the blocked 0x0064325c");

    /* ── 3/13 (r1 1): the target z + 1300 branch, no 0x0064325c ─────────────────────── */
    const uint32_t e13 = 0x50000u, w13 = 0x60000u;
    spawn(e13, w13, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w13 + WORK_STATE, 1);
    fake_mem_write8(w13 + WORK_SUB, 1);
    fake_mem_write32(w13 + WORK_POS_Y, fbits(10000.0f));
    fake_mem_write32(w13 + WORK_TARGET_Z, fbits(0.0f));
    fake_reset_calls();
    frame_with(e13, w13, 3, 13);
    CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_TURN_DESCEND
          && fake_calls[1].fn == FN_DATA_GET,
          "3/13's target z branch doesn't fall into 0/3's base handler");
    CHECK(fake_calls[2].r1 == 1 && fake_calls[3].r2 == 3,
          "3/13 doesn't start 0/3 through the target z branch");

    /* ── 3/16 (r1 0 r2 1): the conditional fly first, then the 3/6 handler ──────────── */
    const uint32_t e16 = 0x70000u, w16 = 0x80000u;
    spawn(e16, w16, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e16, w16, 3, 16);             /* state 0 */
    CHECK(fake_call_count == 5, "3/16 state 0 made %d calls, want 5", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(3, FN_MOTION);
    CHECK(fake_calls[3].r1 == MOTION_3_6, "3/16 doesn't request the 3/6 motion");

    /* ── 3/7 (0x0068e5e8, r1 0): motion 0x1a, then 0/3's base handler ────────────────── */
    const uint32_t e07 = 0x90000u, w07 = 0xa0000u;
    spawn(e07, w07, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e07, w07, 3, 7);              /* state 0 */
    CHECK(fake_call_count == 3, "3/7 state 0 made %d calls, want 3", fake_call_count);
    CALL(0, FN_DATA_FLOAT);
    CALL(1, FN_APPLY_FALL);
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == 0x1au && fake_calls[2].s0 == 6.0f,
          "3/7 doesn't request motion 0x1a at 6.0");
    fake_reset_calls();
    frame_with(e07, w07, 3, 7);              /* state 1 */
    CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_TURN_TO,
          "3/7 state 1 doesn't turn toward the target first");
    CHECK(fake_calls[0].r1 == TURN_RATE_3_7 && fake_calls[0].r2 == 0,
          "3/7 doesn't halve the source's turn rate 0x200");
    CHECK(fake_calls[1].fn == FN_DATA_GET && fake_calls[3].fn == FN_SET_ACTION,
          "3/7 doesn't fall into 0/3's base handler");

    /* 3/18 (r1 2) asks 3/0x14; the other r1s ask their own next action. */
    const uint32_t e18 = 0xb0000u, w18 = 0xc0000u;
    spawn(e18, w18, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w18 + WORK_STATE, 1);
    fake_reset_calls();
    frame_with(e18, w18, 3, 18);
    CHECK(fake_call_count == 2, "3/18 state 1 made %d calls, want 2", fake_call_count);
    CALL(0, FN_TURN_TO);
    CALL(1, FN_NEXT_ACTION);
    CHECK(fake_calls[1].r1 == 3 && fake_calls[1].r2 == 0x14,
          "3/18 doesn't ask for 3/0x14");
    fake_reset_calls();
    fake_mem_write8(w18 + WORK_STATE, 1);
    frame_with(e18, w18, 3, 19);             /* r1 3 -> 3/0x15 */
    CHECK(fake_call_count == 2 && fake_calls[1].r2 == 0x15,
          "3/19 doesn't ask for 3/0x15");
    /* A turn that hasn't arrived stops the handler after the turn call. */
    fake_reset_calls();
    fake_mem_write8(w18 + WORK_STATE, 1);
    fake_turn_to = 0;
    frame_with(e18, w18, 3, 18);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_TURN_TO,
          "3/7 runs past a turn that hasn't arrived (%d calls)", fake_call_count);
    fake_turn_to = 1;
    /* A state other than 0 and 1 does nothing. */
    fake_reset_calls();
    fake_mem_write8(w18 + WORK_STATE, 2);
    frame_with(e18, w18, 3, 18);
    CHECK(fake_call_count == 0, "a 3/7 state other than 0 and 1 made %d calls", fake_call_count);

    /* ── 3/12 (0x0068e6e4, r1 0): the distance test, aim, and the 3/11 start ────────── */
    const uint32_t e12 = 0xd0000u, w12 = 0xe0000u;
    spawn(e12, w12, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e12, w12, 3, 12);             /* state 0 */
    CHECK(fake_call_count == 4, "3/12 state 0 made %d calls, want 4", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(3, FN_MOTION);
    CHECK(fake_calls[3].r1 == MOTION_3_12, "3/12 doesn't request motion 0x3d");

    fake_reset_calls();
    fake_flag = 0;
    frame_with(e12, w12, 3, 12);             /* state 1 sub 0 */
    CHECK(fake_call_count == 4, "3/12 sub 0 made %d calls, want 4", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_RANGE);
    CHECK(fake_calls[1].r1 == 1 && fake_calls[1].s0 == 70.0f && fake_calls[1].s1 == 0.0f,
          "3/12 doesn't take the source's 70.0 distance");
    CALL(2, FN_CLEAR_AIM);
    CALL(3, FN_FLAG);
    CHECK(ffrom(fake_mem_read32(w12 + WORK_AIM_Z)) == 5.0f
          && ffrom(fake_mem_read32(w12 + WORK_AIM_B_Z)) == 3.0f,
          "3/12 doesn't set aim A z 5.0 and aim B z 3.0");
    CHECK(fake_mem_read8(w12 + WORK_SUB) == 1, "3/12 doesn't move to sub 1");

    /* A distance test that hasn't passed still reaches the flag check, without the setup. */
    const uint32_t e12r = 0x190000u, w12r = 0x1a0000u;
    spawn(e12r, w12r, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w12r + WORK_STATE, 1);
    fake_mem_write8(w12r + WORK_SUB, 0);
    fake_range = 0;
    fake_flag = 1;
    fake_reset_calls();
    frame_with(e12r, w12r, 3, 12);
    CHECK(fake_call_count == 6, "3/12's failed distance test made %d calls, want 6",
          fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_RANGE);
    CALL(2, FN_FLAG);
    CHECK(fake_calls[2].fn == FN_FLAG && fake_mem_read8(w12r + WORK_SUB) == 0,
          "3/12's failed distance test doesn't reach the flag check");
    fake_range = 1;

    fake_reset_calls();
    fake_flag = 1;
    fake_mem_write32(w12 + WORK_AIM_Z, fbits(200.0f));
    frame_with(e12, w12, 3, 12);             /* state 1 sub 1, r1 0 */
    CHECK(fake_call_count == 7, "3/12 sub 1 made %d calls, want 7", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_TURN_HOLD);
    CHECK(fake_calls[2].r1 == w12 + WORK_TURN && fake_calls[2].s0 == 1.5f
          && fake_calls[2].s1 == 1.0f, "3/12 doesn't turn at the data float");
    CHECK(ffrom(fake_mem_read32(w12 + WORK_AIM_Z)) == 90.0f,
          "3/12 doesn't clamp aim A z at 90.0");
    CALL(3, FN_FLAG);
    CALL(4, FN_DATA_FLOAT);
    CALL(5, FN_APPLY_FALL);
    CALL(6, FN_START_ACTION);
    CHECK(fake_calls[6].r1 == 3 && fake_calls[6].r2 == 0xb,
          "3/12 doesn't start 3/11 through 0x0084dc84");
    CHECK(fake_mem_read8(w12 + WORK_SET) == 1, "3/12 doesn't set the action's set byte");

    /* 3/20 (r1 1) asks 3/0x16 on its flag. */
    const uint32_t e20 = 0xf0000u, w20 = 0x100000u;
    spawn(e20, w20, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w20 + WORK_STATE, 1);
    fake_mem_write8(w20 + WORK_SUB, 1);
    fake_reset_calls();
    frame_with(e20, w20, 3, 20);
    CHECK(fake_call_count == 5, "3/20 made %d calls, want 5", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_TURN_HOLD);
    CALL(3, FN_FLAG);
    CALL(4, FN_NEXT_ACTION);
    CHECK(fake_calls[4].r1 == 3 && fake_calls[4].r2 == 0x16, "3/20 doesn't ask for 3/0x16");

    /* ── 3/27 (0x0068e8c8): the two setups, mode 3, the kind's motion, 0/2 ─────────── */
    const uint32_t e27 = 0x110000u, w27 = 0x120000u;
    spawn(e27, w27, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e27, w27, 3, 27);             /* state 0 */
    CHECK(fake_call_count == 4, "3/27 state 0 made %d calls, want 4", fake_call_count);
    CALL(0, FN_DATA_FLOAT);
    CALL(1, FN_APPLY_FALL);
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == MOTION_3_27_A, "3/27 doesn't request motion 0x1a");
    CALL(3, FN_PREP_FALL);

    fake_reset_calls();
    fake_check = 1;
    frame_with(e27, w27, 3, 27);             /* state 1 */
    CHECK(fake_call_count == 5, "3/27 state 1 made %d calls, want 5", fake_call_count);
    CALL(0, FN_PREP_TURN);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_CHECK);
    CHECK(fake_calls[2].s0 == 1.5f, "3/27's height test doesn't take the data float");
    CALL(3, FN_MODE);
    CHECK(fake_calls[3].r1 == 3, "3/27 doesn't set mode 3");
    CALL(4, FN_MOTION);
    CHECK(fake_calls[4].r1 == MOTION_3_27_B, "3/27 doesn't request motion 0x1d");

    fake_reset_calls();
    fake_mem_write8(w27 + WORK_KIND, 0x3f);
    frame_with(e27, w27, 3, 27);             /* state 2 */
    CHECK(fake_call_count == 5, "3/27 state 2 made %d calls, want 5", fake_call_count);
    CALL(0, FN_FLAG);
    CALL(1, FN_MODE);
    CHECK(fake_calls[1].r1 == 0, "3/27 doesn't return to mode 0");
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == MOTION_3_27_C,
          "3/27 doesn't convert 3U's motion 0xcf to MH4U's 0x207");
    CALL(3, FN_SHELL);
    CHECK(fake_calls[3].r1 == 0 && fake_calls[3].r2 == 0x16, "3/27 doesn't spawn the shell");
    CALL(4, FN_FLY);
    fake_reset_calls();
    const uint32_t e27b = 0x170000u, w27b = 0x180000u;
    spawn(e27b, w27b, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w27b + WORK_STATE, 2);
    fake_mem_write8(w27b + WORK_KIND, 2);
    frame_with(e27b, w27b, 3, 27);
    CHECK(fake_call_count == 5 && fake_calls[2].r1 == MOTION_3_27_D,
          "3/27 doesn't convert 3U's motion 0xe1 to MH4U's 0x219");

    fake_reset_calls();
    frame_with(e27, w27, 3, 27);             /* state 3 */
    CHECK(fake_call_count == 3, "3/27 state 3 made %d calls, want 3", fake_call_count);
    CALL(0, FN_FLAG);
    CALL(1, FN_MODE);
    CALL(2, FN_SET_ACTION);
    CHECK(fake_calls[1].r1 == 0 && fake_calls[2].r1 == 0,
          "3/27 state 3 doesn't fall into 0/2's base handler");

    /* ── 3/8 (base handler 0x0082b37c): five states ─────────────────────────────────── */
    const uint32_t e08 = 0x130000u, w08 = 0x140000u;
    spawn(e08, w08, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_reset_calls();
    frame_with(e08, w08, 3, 8);              /* state 0 */
    CHECK(fake_call_count == 4, "3/8 state 0 made %d calls, want 4", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_APPLY_FALL);
    CALL(3, FN_MOTION);
    CHECK(fake_calls[3].r1 == MOTION_3_8_A, "3/8 doesn't request motion 0x2d");

    fake_reset_calls();
    fake_mem_write32(w08 + WORK_TARGET_Z, fbits(10.0f));
    frame_with(e08, w08, 3, 8);              /* state 1 */
    CHECK(fake_call_count == 4, "3/8 state 1 made %d calls, want 4", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_FLAG);
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == MOTION_3_8_B, "3/8 doesn't request motion 0x3d");
    CALL(3, FN_RATE);
    CHECK(ffrom(fake_mem_read32(w08 + WORK_TARGET_Z)) == 10.0f + 2.0f * 500.0f,
          "3/8 doesn't add the rate at 500.0 to target z");
    CHECK(fake_mem_read8(w08 + WORK_SUB) == 0, "3/8 doesn't reset its third sub-state");

    fake_reset_calls();
    frame_with(e08, w08, 3, 8);              /* state 2 sub 0 */
    CHECK(fake_call_count == 7, "3/8 state 2 sub 0 made %d calls, want 7", fake_call_count);
    CHECK(fake_mem_read8(w08 + WORK_MARKED) == 1, "3/8 doesn't set the flying byte");
    CALL(0, FN_FLY);
    CALL(1, FN_TURN2);
    CHECK(fake_calls[1].r1 == TURN_RATE_TWO && fake_calls[1].r2 == TURN_RATE_TWO,
          "3/8 doesn't halve 0x83d884's two rates");
    CALL(2, FN_RANGE);
    CHECK(fake_calls[2].s0 == 30.0f, "3/8 doesn't take the source's 30.0 distance");
    CALL(3, FN_CLEAR_AIM);
    CALL(4, FN_SETUP_POINT);
    CHECK(fake_calls[4].r1 == 0x10 && fake_calls[4].s0 == -300.0f,
          "3/8 doesn't set up the turn point at -300.0");
    CALL(5, FN_FLAG);
    CALL(6, FN_MOTION);
    CHECK(fake_calls[6].r1 == MOTION_3_8_C, "3/8 doesn't request motion 0x3e");
    CHECK(ffrom(fake_mem_read32(w08 + WORK_AIM_Z)) == 5.0f
          && ffrom(fake_mem_read32(w08 + WORK_AIM_B_Z)) == 3.0f,
          "3/8 doesn't set aim A z 5.0 and aim B z 3.0");

    fake_reset_calls();
    frame_with(e08, w08, 3, 8);              /* state 3, the point turn arrives */
    CHECK(fake_call_count == 5, "3/8 state 3 made %d calls, want 5", fake_call_count);
    CHECK(fake_mem_read8(w08 + WORK_MARKED) == 1, "3/8 state 3 doesn't set the flying byte");
    CALL(0, FN_FLY);
    CALL(1, FN_POINT_TURN);
    CHECK(fake_calls[1].r2 == TURN_RATE_ONE, "3/8 doesn't halve 0x8438e8's rate");
    CALL(2, FN_MOTION);
    CHECK(fake_calls[2].r1 == MOTION_3_8_A, "3/8 state 3 doesn't request motion 0x2d again");
    CALL(3, FN_DATA_FLOAT);
    CALL(4, FN_TURN_HOLD);
    CHECK(ffrom(fake_mem_read32(w08 + WORK_AIM_Y)) == -10.0f
          && ffrom(fake_mem_read32(w08 + WORK_AIM_B_Z)) == -3.2f,
          "3/8 doesn't set aim A y -10.0 and aim B z -3.2");

    fake_reset_calls();
    fake_flag = 0;
    frame_with(e08, w08, 3, 8);              /* state 4 sub 0, the flag not set */
    CHECK(fake_call_count == 5, "3/8 state 4 sub 0 made %d calls, want 5", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_TURN_HOLD);
    CALL(3, FN_RANGE);
    CALL(4, FN_FLAG);
    CHECK(ffrom(fake_mem_read32(w08 + WORK_AIM_B_Z)) == -6.8f,
          "3/8 state 4 doesn't set aim B z -6.8");
    CHECK(fake_mem_read8(w08 + WORK_SUB) == 1, "3/8 state 4 doesn't move to sub 1");

    fake_reset_calls();
    fake_flag = 1;
    fake_turn = 1;
    frame_with(e08, w08, 3, 8);              /* state 4 sub 1, the turn arrived */
    CHECK(fake_call_count == 6, "3/8 state 4 sub 1 made %d calls, want 6", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_TURN_HOLD);
    CALL(3, FN_FLAG);
    CALL(4, FN_MODE);
    CHECK(fake_calls[4].r1 == 3, "3/8 doesn't set mode 3 before motion 0x1d");
    CALL(5, FN_MOTION);
    CHECK(fake_calls[5].r1 == MOTION_3_27_B, "3/8 doesn't request motion 0x1d");
    CHECK(fake_mem_read8(w08 + WORK_STATE) == 5, "3/8 doesn't move to state 5");

    fake_reset_calls();
    frame_with(e08, w08, 3, 8);              /* state 5 */
    CHECK(fake_call_count == 6, "3/8 state 5 made %d calls, want 6", fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_FLAG);
    CALL(2, FN_MODE);
    CHECK(fake_calls[2].r1 == 3, "3/8 state 5 doesn't set mode 3");
    CALL(3, FN_DATA_GET);
    CALL(4, FN_MODE);
    CHECK(fake_calls[4].r1 == 1, "3/8 state 5 doesn't fall into 0/3's mode 1");
    CALL(5, FN_SET_ACTION);
    CHECK(fake_calls[5].r2 == 3, "3/8 state 5 doesn't fall into 0/3's action start");

    /* The blocked 0x00839598 path: the turn did not arrive, so the port ends in 0/3. */
    const uint32_t e08b = 0x150000u, w08b = 0x160000u;
    spawn(e08b, w08b, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(w08b + WORK_STATE, 4);
    fake_mem_write8(w08b + WORK_SUB, 1);
    fake_turn = 0;
    fake_reset_calls();
    frame_with(e08b, w08b, 3, 8);
    CHECK(fake_call_count == 7, "3/8's blocked 0x839598 path made %d calls, want 7",
          fake_call_count);
    CALL(0, FN_FLY);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_TURN_HOLD);
    CALL(3, FN_FLAG);
    CALL(4, FN_DATA_GET);
    CALL(5, FN_MODE);
    CHECK(fake_calls[5].r1 == 1, "the blocked 0x839598 path doesn't fall into 0/3's mode 1");
    CALL(6, FN_SET_ACTION);
    CHECK(fake_log_contains("0x00839598"), "3/8 doesn't log the blocked 0x00839598");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 3's part 2 makes its calls across the sixteen ids\n");
    return 0;
}
