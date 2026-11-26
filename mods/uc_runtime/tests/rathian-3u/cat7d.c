/*
 * cat7d.c: category 7's part 4 on the fake host — 7/45, 7/58, 7/66, 7/67, 7/68, 7/69, 7/70,
 * 7/71, 7/74, 7/75, 7/76, 7/81, 7/90, 7/91, 7/94 and 7/95.
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
 * map this family needs are local to this file.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The work-block fields category 7's part 4 reads beyond host.h's list (MH4U's offsets, the
 * 3U offset each stands for in the family's comments). */
#define WORK_SUB       0x0145u /* 3U +0x6 */
#define WORK_TURN      0x01a8u /* 3U +0x80 */
#define WORK_AIM_Y     0x0164u /* 3U +0x264 */
#define WORK_AIM_Z     0x0168u /* 3U +0x268 */
#define WORK_AIM_B_Z   0x0178u /* 3U +0x278 */
#define WORK_TARGET    0x0218u /* 3U +0x288 */
#define WORK_TARGET_Z  0x0220u /* 3U +0x28c */
#define WORK_POS       0x0198u /* 3U +0x38 */
#define WORK_MARKED    0x03c4u /* 3U +0x7c9 */
#define WORK_TIMER     0x01d4u /* 3U +0x28/+0x2c */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_MOTION       0x0094e318u /* [0x00828828] */
#define FN_DATA_FLOAT   0x0093d870u /* [0x00852324] */
#define FN_APPLY_FALL   0x0092e99cu /* [0x00844124] */
#define FN_GROUP        0x00914dc4u /* [0x00844a38] */
#define FN_GROUP4       0x0093310cu /* [0x00844a40] */
#define FN_FLIGHT       0x00922ca0u /* [0x0083d18c] */
#define FN_PART         0x0091b7b0u /* [0x008345f8] */
#define FN_RANGE        0x0091aae4u /* [0x0083336c] */
#define FN_TURN         0x0091db4cu /* [0x008357b0] */
#define FN_TURN_HOLD    0x0091b430u /* [0x00839ea0] */
#define FN_TURN_LINE    0x0091656cu /* [0x00839514] */
#define FN_ADVANCE      0x009114d4u /* [0x0082cee4] */
#define FN_ADVANCE_B    0x00911090u /* [0x00834098] */
#define FN_SPEED        0x00916108u /* [0x00833d88] */
#define FN_RATE         0x00923f90u /* [0x0083db3c] */
#define FN_CURVE        0x00922250u /* [0x0083c6e0] */
#define FN_VERTICAL     0x00915d44u /* [0x00833b2c] */
#define FN_TURN2        0x0092fc84u /* [0x0083d884] */
#define FN_POINT_TURN   0x0092dcccu /* [0x008438e8] */
#define FN_SETUP_POINT  0x0092dc50u /* [0x008437f4] */
#define FN_CLEAR_AIM    0x0091b3bcu /* [0x00839968] */
#define FN_NEXT_ACTION  0x0094ef64u /* [0x0082a06c] */
#define FN_SET_PAIR     0x00935f8cu /* [0x0082ffbc] */
#define FN_GET_BYTE     0x00918f38u /* [0x00837594] */
#define FN_STALL        0x0090f8fcu /* [0x0082c1c4] */
#define FN_CHECK        0x00942220u /* [0x0083369c] */
#define FN_DIST3        0x00aacc0cu /* [0x005852b4] */
#define FN_DIST2        0x00aacd50u /* [0x005858f4] */
#define FN_ANGLE        0x00568c64u /* [0x00584cd8] */
#define FN_SET_FLAG     0x00914de0u /* [0x00832670] */
#define FN_MODE         0x009167b4u /* [0x0082fe88] */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] */

/* The source's motions in MH4U's `file << 8 | slot` form (3U's file * 100 + slot). */
#define MOTION_7_45      0x38u
#define MOTION_7_58      0x213u  /* 3U 0xdb: file 2, slot 19 */
#define MOTION_7_66      0x215u  /* 3U 0xdd: file 2, slot 21 */
#define MOTION_7_67      0x216u  /* 3U 0xde: file 2, slot 22 */
#define MOTION_7_68      0x217u  /* 3U 0xdf: file 2, slot 23 */
#define MOTION_7_68_END  0x214u  /* 3U 0xdc: file 2, slot 20 */
#define MOTION_7_74_S0   0x215u  /* 3U 0xdd */
#define MOTION_7_74_V0   0x216u  /* 3U 0xde */
#define MOTION_7_74_V1   0x219u  /* 3U 0xe1: file 2, slot 25 */
#define MOTION_7_74_V2   0x21bu  /* 3U 0xe3: file 2, slot 27 */
#define MOTION_7_74_A    0x205u  /* 3U 0xcd: file 2, slot 5 */
#define MOTION_7_74_B    0x21au  /* 3U 0xe2: file 2, slot 26 */
#define MOTION_7_74_C    0x21cu  /* 3U 0xe4: file 2, slot 28 */
#define MOTION_7_74_D    0x206u  /* 3U 0xce: file 2, slot 6 */
#define MOTION_7_74_E    0x207u  /* 3U 0xcf: file 2, slot 7 */
#define MOTION_7_75_A    0x3du
#define MOTION_7_75_1    0x3eu
#define MOTION_7_75_B    0x2du
#define MOTION_7_76_A    0x209u  /* 3U 0xd1: file 2, slot 9 */
#define MOTION_7_76_B    0x208u  /* 3U 0xd0: file 2, slot 8 */
#define MOTION_7_81_A    0x213u  /* 3U 0xdb */
#define MOTION_7_81_B    0x1bu

/* The MH4U tables the family passes (the source's own curves). */
#define CURVE_7_45_A   0x00fd18f0u
#define CURVE_7_45_B   0x00fd1918u
#define CURVE_7_74     0x00fd1a28u

#define ENEMY_SPEED    0x290u  /* 3U this+0x278 */
#define ENEMY_RATE     0x29cu  /* 3U this+0x284 */
#define ENEMY_DELTA    0x14u   /* the frame delta */

static int fake_flag = 1;
static int fake_range = 1;
/* 7/81's (1, 150.0) gate, which closes the state-1 frame after the timer countdown. */
static int fake_range_150;
static int fake_point_turn = 1;
static int fake_check = 1;
static uint32_t fake_byte = 0x12;
static uint32_t fake_angle = 0;
static float fake_dist = 10.0f;

/* What the engine answers this family's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};
    case FN_RATE:
        return (FakeResult){0, 2.0f};
    case FN_CURVE:
        return (FakeResult){0, 2.0f};
    case FN_RANGE:
        if (s[0] == 150.0f) {
            return (FakeResult){(uint32_t)fake_range_150, 0.0f};
        }
        return (FakeResult){(uint32_t)fake_range, 0.0f};
    case FN_POINT_TURN:
        return (FakeResult){(uint32_t)fake_point_turn, 0.0f};
    case FN_CHECK:
        return (FakeResult){(uint32_t)fake_check, 0.0f};
    case FN_GET_BYTE:
        return (FakeResult){fake_byte, 0.0f};
    case FN_ANGLE:
        return (FakeResult){fake_angle, 0.0f};
    case FN_DIST3:
    case FN_DIST2:
        return (FakeResult){0, fake_dist};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* Check one guest call's function and integer arguments. */
#define CALL(i, want) do { \
    CHECK(fake_calls[i].fn == (want), "call %d is 0x%08x, want 0x%08x", (i), \
          (unsigned)fake_calls[i].fn, (unsigned)(want)); \
} while (0)

/* The first call with `fn` at or after `from`, or -1. */
static int find_call(uint32_t fn, int from) {
    for (int i = from; i < fake_call_count; i++) {
        if (fake_calls[i].fn == fn) {
            return i;
        }
    }
    return -1;
}

static void check_motion(int i, uint32_t motion, float speed, const char *what) {
    CALL(i, FN_MOTION);
    CHECK(fake_calls[i].r1 == motion, "%s requests motion 0x%x, want 0x%x", what,
          (unsigned)fake_calls[i].r1, (unsigned)motion);
    CHECK(fake_calls[i].s0 == speed, "%s requests the speed %g, want %g", what,
          (double)fake_calls[i].s0, (double)speed);
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    /* ── 7/45 (0x00697e78): mode 3, motion 0x38, the two curves, the 0/6 fall-through ── */
    const uint32_t e45 = 0x30000u, w45 = 0x40000u;
    spawn(e45, w45, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(e45, w45, 7, 45);              /* state 0 */
    CHECK(fake_call_count == 6, "7/45 state 0 made %d calls, want 6", fake_call_count);
    CALL(0, FN_MODE);
    CHECK(fake_calls[0].r1 == 3, "7/45 doesn't set mode 3");
    CALL(1, FN_PART);
    CHECK((int32_t)fake_calls[1].r1 == -14, "7/45's part step is %d, want -14",
          (int)fake_calls[1].r1);
    check_motion(2, MOTION_7_45, 6.0f, "7/45");
    CALL(3, FN_CLEAR_AIM);
    CALL(4, FN_SPEED);
    CALL(5, FN_GROUP);
    CHECK(fake_calls[5].r1 == 0 && fake_calls[5].r2 == 0x1e, "7/45 doesn't spawn the shell");

    fake_reset_calls();
    fake_range = 1;
    frame_with(e45, w45, 7, 45);              /* state 1: the gate passed */
    CHECK(fake_call_count == 8, "7/45 state 1 made %d calls, want 8", fake_call_count);
    CALL(0, FN_RANGE);
    CHECK(fake_calls[0].r1 == 1 && fake_calls[0].s0 == 50.0f, "7/45 doesn't take the 50.0 gate");
    CALL(1, FN_CURVE);
    CHECK(fake_calls[1].r1 == CURVE_7_45_A, "7/45 doesn't pass MH4U's own first curve");
    CALL(2, FN_VERTICAL);
    CHECK(fake_calls[2].s0 == 2.0f, "7/45 doesn't advance the vertical by the curve");
    CALL(3, FN_CURVE);
    CHECK(fake_calls[3].r1 == CURVE_7_45_B, "7/45 doesn't pass MH4U's own second curve");
    CHECK(ffrom(fake_mem_read32(w45 + WORK_AIM_Z)) == 2.0f, "7/45 doesn't store aim A z");
    CALL(4, FN_ADVANCE);
    CHECK(fake_calls[4].r1 == w45 + WORK_TURN, "7/45 doesn't advance the turn slot");
    CALL(5, FN_FLAG);
    CALL(6, FN_MODE);
    CHECK(fake_calls[6].r1 == 3, "7/45 doesn't fall into 0/6's mode 3");
    CALL(7, 0x0090ef74u);                     /* 0/6's action start */
    CHECK(fake_mem_read8(w45 + WORK_STATE) == 1, "7/45's state isn't 1");

    fake_reset_calls();
    fake_range = 0;
    frame_with(e45, w45, 7, 45);              /* state 1: the gate failed */
    CHECK(fake_call_count == 9, "7/45's failed gate made %d calls, want 9", fake_call_count);
    CALL(0, FN_RANGE);
    CALL(1, FN_TURN);
    CHECK(fake_calls[1].r1 == 0x80u, "7/45 doesn't halve the source's 0x100 turn rate");
    fake_range = 1;

    /* ── 7/58 (0x00697ff0): motion 0xdb, the two effect gates ──────────────────────── */
    const uint32_t e58 = 0x50000u, w58 = 0x60000u;
    spawn(e58, w58, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(e58, w58, 7, 58);              /* state 0 */
    CHECK(fake_call_count == 3, "7/58 state 0 made %d calls, want 3", fake_call_count);
    CALL(0, FN_MODE);
    CHECK(fake_calls[0].r1 == 0, "7/58 doesn't set mode 0");
    CALL(1, FN_PART);
    check_motion(2, MOTION_7_58, 4.0f, "7/58");
    fake_reset_calls();
    frame_with(e58, w58, 7, 58);              /* state 1 */
    CHECK(fake_call_count == 5, "7/58 state 1 made %d calls, want 5", fake_call_count);
    CALL(0, FN_RANGE);
    CHECK(fake_calls[0].s0 == 4.0f, "7/58's first gate isn't the source's 4.0");
    CALL(1, FN_RANGE);
    CHECK(fake_calls[1].s0 == 108.0f, "7/58's second gate isn't the source's 108.0");
    CALL(2, FN_FLAG);
    CHECK(fake_log_contains("0x0015f410"), "7/58 doesn't name the blocked effect spawn");
    CHECK(fake_log_contains("0x00688a20"), "7/58 doesn't name the blocked effect setup");

    /* ── 7/66 (0x00698144): motion 0xdd and the three range pairs ──────────────────── */
    const uint32_t e66 = 0x70000u, w66 = 0x80000u;
    spawn(e66, w66, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(e66, w66, 7, 66);              /* state 0 */
    CHECK(fake_call_count == 3, "7/66 state 0 made %d calls, want 3", fake_call_count);
    check_motion(2, MOTION_7_66, 4.0f, "7/66");
    for (int st = 1; st <= 3; st++) {
        const float want[3][2] = {{0.0f, 60.0f}, {140.0f, 160.0f}, {200.0f, 220.0f}};
        const float after[3] = {116.0f, 168.0f, 226.0f};
        fake_reset_calls();
        fake_range = 1;
        frame_with(e66, w66, 7, 66);
        CHECK(fake_call_count == 3, "7/66 state %d made %d calls, want 3", st, fake_call_count);
        CALL(0, FN_RANGE);
        CHECK(fake_calls[0].r1 == 3 && fake_calls[0].s0 == want[st - 1][0]
              && fake_calls[0].s1 == want[st - 1][1], "7/66 state %d's 3-mode gate", st);
        CALL(1, FN_TURN);
        CHECK(fake_calls[1].r1 == 0x2du, "7/66 doesn't halve the source's 0x5b turn rate");
        CALL(2, FN_RANGE);
        CHECK(fake_calls[2].s0 == after[st - 1], "7/66 state %d's second gate", st);
        CHECK(fake_mem_read8(w66 + WORK_STATE) == (uint32_t)(st + 1),
              "7/66 state %d doesn't advance", st);
    }
    CHECK(fake_log_contains("0x00842a7c"), "7/66 doesn't name the blocked 0x842a7c");
    CHECK(fake_log_contains("0x00688a20"), "7/66 doesn't name the blocked effect setup");
    fake_reset_calls();
    frame_with(e66, w66, 7, 66);              /* state 4 */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG,
          "7/66 state 4 doesn't fall into 0/2's base handler");
    CALL(1, FN_MODE);
    CALL(2, 0x0090ef74u);

    /* ── 7/67, 7/69 and 7/70 (0x00698408): the curve path and the 0xdc tail ─────────── */
    const uint32_t e67 = 0x90000u, w67 = 0xa0000u;
    spawn(e67, w67, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(e67, w67, 7, 67);              /* state 0 */
    CHECK(fake_call_count == 5, "7/67 state 0 made %d calls, want 5", fake_call_count);
    CALL(0, FN_MODE);
    CHECK(fake_calls[0].r1 == 3, "7/67 doesn't set mode 3");
    CALL(1, FN_PART);
    CALL(2, FN_CLEAR_AIM);
    CALL(3, FN_SPEED);
    check_motion(4, MOTION_7_67, 4.0f, "7/67's unit");
    fake_reset_calls();
    fake_range = 1;
    fake_mem_write32(w67 + WORK_POS_Y, fbits(1000.0f));
    frame_with(e67, w67, 7, 67);              /* state 1 */
    CHECK(fake_call_count == 12, "7/67 state 1 made %d calls, want 12", fake_call_count);
    CALL(0, FN_TURN);
    CHECK(fake_calls[0].r1 == 0x40u, "7/67 doesn't halve the source's 0x80 turn rate");
    CALL(1, FN_RANGE);                        /* (1, 90.0) */
    CALL(2, FN_RANGE);                        /* (1, 130.0) */
    CALL(3, FN_RANGE);                        /* (2, 120.0) */
    CHECK(fake_calls[3].r1 == 2 && fake_calls[3].s0 == 120.0f, "7/67's (2, 120.0) gate");
    CALL(4, FN_DIST3);
    CHECK(fake_calls[4].r0 == w67 + WORK_POS && fake_calls[4].r1 == w67 + WORK_TARGET,
          "7/67's first distance is position to target");
    CALL(5, FN_DIST3);
    CALL(6, FN_RANGE);                        /* (1, 90.0) again */
    CALL(7, FN_ADVANCE);
    CHECK(fake_calls[7].r1 == w67 + WORK_TURN, "7/67 doesn't advance the turn slot");
    CALL(8, FN_RANGE);                        /* (1, 80.0) */
    CALL(9, FN_FLAG);
    CALL(10, FN_MODE);
    check_motion(11, MOTION_7_68_END, 0.0f, "7/67's tail");
    CHECK(fake_log_contains("0x00584760"), "7/67 doesn't name the blocked table step");
    CHECK(fake_mem_read8(w67 + WORK_STATE) == 2, "7/67 doesn't move to state 2");
    /* 7/69 and 7/70 reach the same unit: their state 0's motion is the same. */
    for (int idx = 69; idx <= 70; idx++) {
        const uint32_t e = e67 + (uint32_t)idx * 0x1000u;
        const uint32_t w = w67 + (uint32_t)idx * 0x1000u;
        spawn(e, w, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(e, w, 7, idx);
        CHECK(fake_call_count == 5, "7/%d state 0 made %d calls, want 5", idx, fake_call_count);
        check_motion(4, MOTION_7_67, 4.0f, "7/67's unit");
    }
    /* The failed 90.0 gate leaves the 80.0 gate's turn in place and still ends the action. */
    {
        const uint32_t e = 0x2e0000u, w = 0x2f0000u;
        spawn(e, w, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(w + WORK_STATE, 1);
        fake_mem_write32(w + WORK_POS_Y, fbits(1000.0f));
        fake_range = 0;
        frame_with(e, w, 7, 67);
        const int turn = find_call(FN_TURN, 0);
        CHECK(turn >= 0, "7/67's failed gates take no turn");
        /* TURN (0x40), the gates, the two distances, then the 0x38e turn, the flag. */
        const int last_turn = find_call(FN_TURN, turn + 1);
        CHECK(last_turn >= 0 && fake_calls[last_turn].r1 == 0x38eu,
              "7/67 doesn't turn at 0x38e when the 80.0 gate fails");
        fake_range = 1;
    }

    /* ── 7/68 (0x006986b8): motion 0xdf, the 8/0 or 1/3 request ────────────────────── */
    const uint32_t e68 = 0xb0000u, w68 = 0xc0000u;
    spawn(e68, w68, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(e68, w68, 7, 68);              /* state 0 */
    CHECK(fake_call_count == 6, "7/68 state 0 made %d calls, want 6", fake_call_count);
    CALL(0, FN_MODE);
    CHECK(fake_calls[0].r1 == 1, "7/68 doesn't set mode 1");
    CALL(1, FN_PART);
    check_motion(2, MOTION_7_68, 6.0f, "7/68");
    CALL(3, FN_GROUP);
    CHECK(fake_calls[3].r2 == 0x24u, "7/68 doesn't spawn the shell");
    CALL(4, FN_CLEAR_AIM);
    CALL(5, FN_FLIGHT);
    fake_reset_calls();
    frame_with(e68, w68, 7, 68);              /* state 1 */
    CHECK(find_call(FN_FLIGHT, 0) < 0, "7/68 state 1 repeats the flight byte");
    CHECK(find_call(FN_ADVANCE, 0) >= 0, "7/68 state 1 doesn't advance the position");
    CHECK(fake_mem_read8(w68 + WORK_STATE) == 2, "7/68 doesn't move to state 2");
    CHECK(fake_log_contains("0x00584760"), "7/68 doesn't name the blocked table step");
    fake_reset_calls();
    fake_byte = 0x12;
    fake_mem_write8(w68 + WORK_SUB, 0);
    frame_with(e68, w68, 7, 68);              /* state 2 */
    int in = find_call(FN_NEXT_ACTION, 0);
    CHECK(in >= 0, "7/68 state 2 makes no next-action request");
    CHECK(fake_calls[in].r1 == 8 && fake_calls[in].r2 == 0,
          "7/68's nonzero byte doesn't request 8/0");
    CHECK(find_call(FN_SET_PAIR, 0) >= 0, "7/68 doesn't pass the byte to the action pair");
    CHECK(fake_log_contains("0x00839598"), "7/68 doesn't name the blocked 0x839598");
    fake_reset_calls();
    fake_byte = 0xff;
    fake_mem_write8(w68 + WORK_SUB, 1);
    frame_with(e68, w68, 7, 68);              /* state 2, the other byte */
    in = find_call(FN_NEXT_ACTION, 0);
    CHECK(in >= 0 && fake_calls[in].r1 == 1 && fake_calls[in].r2 == 3,
          "7/68's 0xff byte doesn't request 1/3");
    fake_byte = 0x12;

    /* ── 7/71 (0x00698c48): motion 0xdb, the 40.0 and 108.0 gates ──────────────────── */
    const uint32_t e71 = 0xd0000u, w71 = 0xe0000u;
    spawn(e71, w71, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    frame_with(e71, w71, 7, 71);              /* state 0 */
    CHECK(fake_call_count == 3, "7/71 state 0 made %d calls, want 3", fake_call_count);
    check_motion(2, MOTION_7_58, 4.0f, "7/71");
    fake_reset_calls();
    frame_with(e71, w71, 7, 71);              /* state 1 */
    CHECK(fake_call_count == 2, "7/71 state 1 made %d calls, want 2", fake_call_count);
    CALL(0, FN_TURN);
    CHECK(fake_calls[0].r1 == 0x111u, "7/71 doesn't halve the source's 0x222 turn rate");
    CALL(1, FN_RANGE);
    CHECK(fake_calls[1].s0 == 40.0f, "7/71's first gate isn't 40.0");
    CHECK(fake_mem_read8(w71 + WORK_STATE) == 2, "7/71 doesn't move to state 2");
    fake_reset_calls();
    frame_with(e71, w71, 7, 71);              /* state 2 */
    CHECK(fake_call_count == 1, "7/71 state 2 made %d calls, want 1", fake_call_count);
    CALL(0, FN_RANGE);
    CHECK(fake_calls[0].s0 == 108.0f, "7/71's second gate isn't 108.0");
    CHECK(fake_mem_read8(w71 + WORK_STATE) == 3, "7/71 doesn't move to state 3");
    CHECK(fake_log_contains("0x00688a20"), "7/71 doesn't name the blocked effect setup");
    fake_reset_calls();
    frame_with(e71, w71, 7, 71);              /* state 3 */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG,
          "7/71 state 3 doesn't fall into 0/2's base handler");

    /* ── 7/74, 7/90 and 7/91 (0x00698db8): the eight states, three variants ────────── */
    const uint32_t e74 = 0xf0000u, w74 = 0x100000u;
    for (int variant = 0; variant < 3; variant++) {
        const uint32_t e = e74 + (uint32_t)variant * 0x40000u;
        const uint32_t w = w74 + (uint32_t)variant * 0x40000u;
        const int idx = (variant == 0) ? 74 : (variant == 1 ? 90 : 91);
        spawn(e, w, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 0 */
        CHECK(fake_call_count == 4, "7/%d state 0 made %d calls, want 4", idx, fake_call_count);
        CALL(0, FN_SET_FLAG);
        CHECK(fake_calls[0].r1 == 0x20u, "7/%d doesn't set the 0x20 flag", idx);
        CALL(1, FN_MODE);
        CALL(2, FN_PART);
        check_motion(3, MOTION_7_74_S0, 4.0f, "7/74's unit");
        for (int st = 1; st <= 3; st++) {
            const float want[3] = {116.0f, 168.0f, 186.0f};
            fake_reset_calls();
            frame_with(e, w, 7, idx);         /* state 1..3 */
            CALL(0, FN_SET_FLAG);
            CALL(1, FN_RANGE);
            CHECK(fake_calls[1].s0 == want[st - 1], "7/%d state %d's gate is %g", idx, st,
                  (double)fake_calls[1].s0);
            if (st < 3) {
                CHECK(fake_call_count == 2, "7/%d state %d made %d calls, want 2", idx, st,
                      fake_call_count);
            } else {
                CHECK(fake_call_count == 4, "7/%d state 3 made %d calls, want 4", idx,
                      fake_call_count);
                CALL(2, FN_MODE);
                CALL(3, FN_MOTION);
                CHECK(fake_calls[3].r1 == (variant == 0 ? MOTION_7_74_V0
                                          : variant == 1 ? MOTION_7_74_V1
                                                         : MOTION_7_74_V2),
                      "7/%d state 3 requests the wrong motion", idx);
            }
            CHECK(fake_mem_read8(w + WORK_STATE) == (uint32_t)(st + 1),
                  "7/%d state %d doesn't advance", idx, st);
        }
        CHECK(fake_log_contains("0x00688a20"), "7/%d doesn't name the effect setup", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 4 */
        CALL(0, FN_SET_FLAG);
        CALL(1, FN_TURN);
        CHECK(fake_calls[1].r1 == 0x111u, "7/%d doesn't halve the 0x222 turn rate", idx);
        const int motion_call = find_call(FN_MOTION, 0);
        const uint32_t want_motion = (variant == 0) ? MOTION_7_74_A
                                     : (variant == 1) ? MOTION_7_74_B : MOTION_7_74_C;
        CHECK(motion_call >= 0, "7/%d state 4 makes no motion call", idx);
        CHECK(fake_calls[motion_call].r1 == want_motion,
              "7/%d state 4 requests motion 0x%x, want 0x%x", idx,
              (unsigned)fake_calls[motion_call].r1, (unsigned)want_motion);
        if (variant == 0) {
            /* state 5: motion 0xcd at 0.0, the two blocked 0x83c6cc aims */
            CHECK(fake_mem_read8(w + WORK_STATE) == 5, "7/74 doesn't move to state 5");
            fake_reset_calls();
            frame_with(e, w, 7, idx);         /* state 5 */
            CHECK(fake_call_count == 7, "7/74 state 5 made %d calls, want 7", fake_call_count);
            CALL(0, FN_SET_FLAG);
            CALL(1, FN_FLAG);
            CALL(2, FN_DATA_FLOAT);
            CALL(3, FN_APPLY_FALL);
            check_motion(4, MOTION_7_74_D, 6.0f, "7/74's state 5");
            CALL(5, FN_GROUP);
            CALL(6, FN_CLEAR_AIM);
            CHECK(fake_log_contains("0x0083c6cc"), "7/74 doesn't name the blocked 0x83c6cc");
            CHECK(fake_mem_read8(w + WORK_STATE) == 6, "7/74 doesn't move to state 6");
            /* state 6 sub 0: the MH4U 0xfd1a28 curve, the turn, the 16.0 gate; the flag
             * leads through mode 0 and motion 0xcf to state 7. */
            fake_reset_calls();
            frame_with(e, w, 7, idx);         /* state 6 sub 0 */
            CHECK(fake_call_count == 11, "7/74 state 6 made %d calls, want 11", fake_call_count);
            CALL(0, FN_SET_FLAG);
            CALL(1, FN_CURVE);
            CHECK(fake_calls[1].r1 == CURVE_7_74, "7/74 doesn't pass MH4U's own table");
            CALL(2, FN_DATA_FLOAT);
            CALL(3, FN_TURN_HOLD);
            CALL(4, FN_RANGE);
            CHECK(fake_calls[4].s0 == 16.0f, "7/74 state 6's 16.0 gate");
            CALL(5, FN_CHECK);
            CALL(6, FN_FLAG);
            CALL(7, FN_MODE);
            CALL(8, FN_MOTION);
            CHECK(fake_calls[8].r1 == MOTION_7_74_E, "7/74 doesn't request motion 0xcf");
            CALL(9, FN_GROUP);
            CHECK(fake_calls[9].r2 == 0x16u, "7/74 doesn't spawn the 0x16 group");
            CALL(10, FN_FLIGHT);
            CHECK(ffrom(fake_mem_read32(w + WORK_AIM_Y)) == 2.0f,
                  "7/74 doesn't store the curve at aim A y");
            CHECK(fake_mem_read8(w + WORK_STATE) == 7, "7/74 doesn't move to state 7");
            fake_reset_calls();
            frame_with(e, w, 7, idx);         /* state 7 */
            CHECK(fake_call_count == 5 && fake_calls[1].fn == FN_FLIGHT
                  && fake_calls[2].fn == FN_FLAG,
                  "7/74 state 7 doesn't fall into 0/2's base handler");
        } else {
            /* states 4, 5 and 6 run together: the fall, the motion and the 0x26 group. */
            CHECK(fake_mem_read8(w + WORK_STATE) == 6, "7/%d doesn't move to state 6", idx);
            const int fall = find_call(FN_APPLY_FALL, 0);
            CHECK(fall >= 0, "7/%d makes no 398.31 fall", idx);
            CHECK(fake_calls[fall].s0 == 398.31f,
                  "7/%d's fall isn't the source's 398.31", idx);
            const int group = find_call(FN_GROUP, 0);
            CHECK(group >= 0 && fake_calls[group].r2 == 0x26u,
                  "7/%d doesn't spawn the 0x26 group", idx);
            CHECK(find_call(FN_CLEAR_AIM, 0) >= 0, "7/%d doesn't clear the aim", idx);
            /* state 6: the 64.0 gate, the (3, 120.0, 184.0) gate and the 184.0 request. */
            fake_reset_calls();
            frame_with(e, w, 7, idx);         /* state 6 */
            int c = 1;
            CALL(0, FN_SET_FLAG);
            CALL(c, FN_RANGE);
            CHECK(fake_calls[c].r1 == 1 && fake_calls[c].s0 == 64.0f,
                  "7/%d's 64.0 gate", idx);
            c++;
            CALL(c, FN_TURN);
            CHECK(fake_calls[c].r1 == 0xa8u, "7/%d's 0x150 turn", idx);
            c++;
            CALL(c, FN_RANGE);
            CHECK(fake_calls[c].r1 == 3 && fake_calls[c].s0 == 120.0f
                  && fake_calls[c].s1 == 184.0f, "7/%d's (3, 120.0, 184.0) gate", idx);
            c++;
            CALL(c, FN_DATA_FLOAT);
            c++;
            CALL(c, FN_TURN_HOLD);
            c++;
            CALL(c, FN_RANGE);
            CHECK(fake_calls[c].s0 == 184.0f, "7/%d's 184.0 gate", idx);
            c++;
            CALL(c, FN_MODE);
            c++;
            CALL(c, FN_MOTION);
            CHECK(fake_calls[c].r1 == MOTION_7_74_E, "7/%d's motion 0xcf", idx);
            c++;
            CALL(c, FN_GROUP);
            CHECK(fake_calls[c].r2 == 0x16u, "7/%d's 0x16 group", idx);
            c++;
            CALL(c, FN_FLIGHT);
            c++;
            CHECK(fake_call_count == c, "7/%d state 6 made %d calls, want %d", idx,
                  fake_call_count, c);
            CHECK(fake_mem_read8(w + WORK_STATE) == 7, "7/%d doesn't move to state 7", idx);
        }
    }

    /* ── 7/75 and 7/94 (the base-class 0x00829c88): four states, two variants ───────── */
    const uint32_t e75 = 0x1c0000u, w75 = 0x1d0000u;
    for (int variant = 0; variant < 2; variant++) {
        const uint32_t e = e75 + (uint32_t)variant * 0x40000u;
        const uint32_t w = w75 + (uint32_t)variant * 0x40000u;
        const int idx = (variant == 0) ? 75 : 94;
        spawn(e, w, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 0 */
        CHECK(fake_call_count == 4, "7/%d state 0 made %d calls, want 4", idx, fake_call_count);
        CALL(0, FN_DATA_FLOAT);
        CALL(1, FN_APPLY_FALL);
        CHECK(fake_calls[1].s0 == 1.5f, "7/%d doesn't fall by the data float", idx);
        check_motion(2, MOTION_7_75_A, 6.0f, "7/75's unit");
        CALL(3, FN_RATE);
        CHECK(ffrom(fake_mem_read32(w + WORK_TARGET_Z)) == 1000.0f,
              "7/%d doesn't add the rate at 500.0 to target z", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 1 sub 0 */
        CHECK(fake_call_count == 6, "7/%d state 1 sub 0 made %d calls, want 6", idx,
              fake_call_count);
        CALL(0, FN_TURN2);
        CHECK(fake_calls[0].r1 == 0x100u && fake_calls[0].r2 == 0x100u,
              "7/%d doesn't halve the source's two 0x200 joint rates", idx);
        CALL(1, FN_RANGE);
        CALL(2, FN_CLEAR_AIM);
        CALL(3, FN_SETUP_POINT);
        CHECK(fake_calls[3].r1 == 0x10u && fake_calls[3].s0 == -850.0f,
              "7/%d doesn't set up the -850.0 turn point", idx);
        CALL(4, FN_FLAG);
        CALL(5, FN_MOTION);
        CHECK(fake_calls[5].r1 == MOTION_7_75_1, "7/%d state 1 requests motion 0x3e", idx);
        CHECK(ffrom(fake_mem_read32(w + WORK_AIM_Z)) == 5.0f
              && ffrom(fake_mem_read32(w + WORK_AIM_B_Z)) == 3.0f,
              "7/%d doesn't set aim A z 5.0 and aim B z 3.0", idx);
        CHECK(fake_mem_read8(w + WORK_STATE) == 2, "7/%d doesn't move to state 2", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 2 */
        CHECK(fake_call_count == 5, "7/%d state 2 made %d calls, want 5", idx, fake_call_count);
        CALL(0, FN_TURN);
        CHECK(fake_calls[0].r1 == 0x100u, "7/%d doesn't halve the source's 0x200 turn", idx);
        CALL(1, FN_POINT_TURN);
        CHECK(fake_calls[1].r2 == 0x80u, "7/%d doesn't pass the source's 0x80 point turn", idx);
        CALL(2, FN_MOTION);
        CHECK(fake_calls[2].r1 == MOTION_7_75_B, "7/%d state 2 requests motion 0x2d", idx);
        CALL(3, FN_DATA_FLOAT);
        CALL(4, FN_TURN_HOLD);
        CHECK(fake_mem_read8(w + WORK_MARKED) == 1, "7/%d doesn't set the flying byte", idx);
        CHECK(fake_mem_read8(w + WORK_STATE) == 3, "7/%d doesn't move to state 3", idx);
        CHECK(ffrom(fake_mem_read32(w + WORK_AIM_Y)) == -10.0f
              && ffrom(fake_mem_read32(w + WORK_AIM_B_Z)) == -3.2f,
              "7/%d doesn't set aim A y -10.0 and aim B z -3.2", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 3 */
        CHECK(fake_call_count == 5, "7/%d state 3 made %d calls, want 5", idx, fake_call_count);
        CALL(0, FN_TURN);
        CHECK(fake_calls[0].r1 == 0x300u, "7/%d doesn't halve the source's 0x600 turn", idx);
        CALL(1, FN_DATA_FLOAT);
        CALL(2, FN_TURN_HOLD);
        CALL(3, FN_RANGE);
        CHECK(fake_calls[3].s0 == 30.0f, "7/%d's 30.0 gate", idx);
        CALL(4, FN_FLAG);
        CHECK(fake_mem_read8(w + WORK_SUB) == 1, "7/%d doesn't move to sub 1", idx);
        CHECK(ffrom(fake_mem_read32(w + WORK_AIM_B_Z)) == -6.8f,
              "7/%d doesn't set aim B z -6.8", idx);
        CHECK(fake_mem_read8(w + WORK_STATE) == 4, "7/%d doesn't move to state 4", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 4 */
        const int next = find_call(FN_NEXT_ACTION, 0);
        CHECK(next >= 0, "7/%d state 4 makes no next-action request", idx);
        CHECK(fake_calls[next].r1 == 7u, "7/%d doesn't request a category-7 action", idx);
        CHECK(fake_calls[next].r2 == (variant != 0 ? 0x60u : 0x54u),
              "7/%d requests the wrong next action", idx);
    }

    /* ── 7/76 and 7/95 (0x006993fc): the -200.0 speed and the two requests ─────────── */
    const uint32_t e76 = 0x240000u, w76 = 0x250000u;
    for (int variant = 0; variant < 2; variant++) {
        const uint32_t e = e76 + (uint32_t)variant * 0x40000u;
        const uint32_t w = w76 + (uint32_t)variant * 0x40000u;
        const int idx = (variant == 0) ? 76 : 95;
        spawn(e, w, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 0 */
        CHECK(fake_call_count == 4, "7/%d state 0 made %d calls, want 4", idx, fake_call_count);
        CALL(0, FN_SET_FLAG);
        CALL(1, FN_MODE);
        CHECK(fake_calls[1].r1 == 3, "7/%d doesn't set mode 3", idx);
        CALL(2, FN_PART);
        check_motion(3, MOTION_7_76_A, 6.0f, "7/76's unit");
        CHECK(ffrom(fake_mem_read32(w + WORK_TIMER)) == 0.0f, "7/%d doesn't clear the timer",
              idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 1 sub 0 */
        CHECK(fake_call_count == 6, "7/%d state 1 sub 0 made %d calls, want 6", idx,
              fake_call_count);
        CALL(0, FN_SET_FLAG);
        CALL(1, FN_TURN);
        CHECK(fake_calls[1].r1 == 0x100u, "7/%d doesn't halve the source's 0x200 turn", idx);
        CALL(2, FN_RANGE);
        CHECK(fake_calls[2].s0 == 50.0f, "7/%d's 50.0 gate", idx);
        CALL(3, FN_CLEAR_AIM);
        CALL(4, FN_SETUP_POINT);
        CALL(5, FN_GROUP4);
        CHECK(fake_calls[5].r1 == 0u && fake_calls[5].r2 == 0xeu && fake_calls[5].r3 == 3u,
              "7/%d doesn't set the (0, 0xe, 3) part group", idx);
        CHECK(fake_mem_read8(w + WORK_SUB) == 1, "7/%d doesn't move to sub 1", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 1 sub 1 */
        CHECK(fake_log_contains("0x0083c6cc"), "7/%d doesn't name the blocked 0x83c6cc", idx);
        CHECK(fake_call_count == 5, "7/%d state 1 sub 1 made %d calls, want 5", idx,
              fake_call_count);
        CALL(0, FN_SET_FLAG);
        CALL(1, FN_VERTICAL);
        CHECK(fake_calls[1].s0 == 0.0f, "7/%d doesn't run the blocked vertical as 0.0", idx);
        CALL(2, FN_ADVANCE_B);
        CHECK(fake_calls[2].s0 == 1.0f, "7/%d doesn't advance aim A", idx);
        CALL(3, FN_FLAG);
        CALL(4, FN_MOTION);
        CHECK(fake_calls[4].r1 == MOTION_7_76_B, "7/%d doesn't request motion 0xd0", idx);
        CHECK(fake_mem_read8(w + WORK_STATE) == 2, "7/%d doesn't move to state 2", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 2 */
        CHECK(fake_call_count == 5, "7/%d state 2 made %d calls, want 5", idx, fake_call_count);
        CALL(0, FN_SET_FLAG);
        CALL(1, FN_SPEED);
        CHECK(fake_calls[1].s0 == -200.0f, "7/%d doesn't set the -200.0 speed", idx);
        CALL(2, FN_ADVANCE_B);
        CALL(3, FN_POINT_TURN);
        CALL(4, FN_STALL);
        CHECK(fake_log_contains("0x00842a7c"), "7/%d doesn't name the blocked 0x842a7c", idx);
        CHECK(fake_log_contains("0x0082d278"), "7/%d doesn't name the blocked 0x82d278", idx);
        CHECK(fake_mem_read8(w + WORK_STATE) == 3, "7/%d doesn't move to state 3", idx);
        fake_reset_calls();
        frame_with(e, w, 7, idx);             /* state 3 */
        CHECK(fake_log_contains("0x0082d430"), "7/%d doesn't name the blocked 0x82d430", idx);
        const int next = find_call(FN_NEXT_ACTION, 0);
        CHECK(next >= 0, "7/%d state 3 makes no next-action request", idx);
        CHECK(fake_calls[next].r1 == 7u
              && fake_calls[next].r2 == (variant != 0 ? 0x60u : 0x54u),
              "7/%d requests the wrong next action", idx);
    }

    /* ── 7/81 (the inline 0x00686bb8 into 0x00697888): the flight attack ───────────── */
    const uint32_t e81 = 0x2c0000u, w81 = 0x2d0000u;
    spawn(e81, w81, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write32(e81 + ENEMY_RATE, fbits(2.0f));       /* the timer 20.0 / 2.0 */
    fake_reset_calls();
    frame_with(e81, w81, 7, 81);              /* state 0 */
    CHECK(fake_call_count == 7, "7/81 state 0 made %d calls, want 7", fake_call_count);
    CALL(0, FN_SET_FLAG);
    CALL(1, FN_DATA_FLOAT);
    CALL(2, FN_APPLY_FALL);
    CALL(3, FN_PART);
    check_motion(4, MOTION_7_81_A, 6.0f, "7/81");
    CALL(5, FN_GROUP);
    CHECK(fake_calls[5].r2 == 0x2bu, "7/81 doesn't spawn the 0x2b group");
    CALL(6, FN_CLEAR_AIM);
    CHECK(ffrom(fake_mem_read32(w81 + WORK_TIMER)) == 10.0f,
          "7/81's timer isn't the source's int16(20.0 / this+0x29c)");
    /* state 1 with the timer above 20.0: the trajectory and the countdown run. */
    fake_reset_calls();
    fake_mem_write32(w81 + WORK_TIMER, fbits(30.0f));
    fake_mem_write32(e81 + ENEMY_DELTA, fbits(0.5f));
    frame_with(e81, w81, 7, 81);              /* state 1, the timer above 20.0 */
    const int turn = find_call(FN_TURN, 0);
    CHECK(turn >= 0 && fake_calls[turn].r1 == 0x180u,
          "7/81 doesn't halve the source's 0x300 turn rate");
    CHECK(find_call(FN_FLIGHT, 0) >= 0, "7/81 doesn't mark the flight");
    CHECK(fake_log_contains("0x00842a7c"), "7/81 doesn't name the blocked 0x842a7c");
    CHECK(find_call(FN_TURN_LINE, 0) >= 0, "7/81 doesn't run the trajectory's turn line");
    CHECK(find_call(FN_DIST2, 0) >= 0, "7/81 doesn't take the x/z distance");
    CHECK(find_call(FN_ANGLE, 0) >= 0, "7/81 doesn't take the angle to the target");
    CHECK(ffrom(fake_mem_read32(w81 + WORK_TIMER)) == 29.5f,
          "7/81 doesn't count the timer down by the frame delta");
    CHECK(fake_mem_read8(w81 + WORK_STATE) == 1, "7/81's closed 150.0 gate still advances");
    /* The 150.0 gate then passes: state 2 and its own timer (the blocked divisor gives 0.0). */
    fake_range_150 = 1;
    fake_reset_calls();
    frame_with(e81, w81, 7, 81);
    CHECK(fake_call_count == 13, "7/81 state 1's hard gate made %d calls, want 13",
          fake_call_count);
    CHECK(fake_mem_read8(w81 + WORK_STATE) == 2, "7/81 doesn't move to state 2");
    CHECK(fake_log_contains("0x0083c6cc"), "7/81 doesn't name the blocked 0x83c6cc");
    CHECK(ffrom(fake_mem_read32(w81 + WORK_TIMER)) == 0.0f,
          "7/81's blocked state-2 timer isn't 0.0");
    fake_reset_calls();
    frame_with(e81, w81, 7, 81);              /* state 2 */
    CHECK(fake_call_count == 4, "7/81 state 2 made %d calls, want 4", fake_call_count);
    CALL(0, FN_SET_FLAG);
    CALL(1, FN_FLAG);
    CALL(2, FN_MODE);
    CHECK(fake_calls[2].r1 == 3, "7/81 doesn't set mode 3");
    CALL(3, FN_MOTION);
    CHECK(fake_calls[3].r1 == MOTION_7_81_B, "7/81 doesn't request motion 0x1b");
    CHECK(fake_mem_read8(w81 + WORK_STATE) == 3, "7/81 doesn't move to state 3");
    fake_reset_calls();
    frame_with(e81, w81, 7, 81);              /* state 3 */
    CHECK(fake_call_count == 5, "7/81 state 3 made %d calls, want 5", fake_call_count);
    CALL(0, FN_SET_FLAG);
    CALL(1, FN_VERTICAL);
    CHECK(fake_calls[1].s0 == -2.5f, "7/81 doesn't halve the source's -5.0 vertical step");
    CALL(2, FN_FLAG);
    CALL(3, FN_MODE);
    CALL(4, 0x0090ef74u);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 7's part 4 makes its calls across the sixteen ids\n");
    return 0;
}
