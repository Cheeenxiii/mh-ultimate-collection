/*
 * cat2.c: GU Rathian's category 2 fake-host test — the nine category-2 units and 9/3, 9/4.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives category 2's
 * states on the fake host.
 *
 * The expected addresses, motions and frame values come from tests/rathian-gu/host.h, not from
 * the module, so a change in a handler fails the test instead of moving the expectation with
 * it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

static int flag_result = 1;
static int check_result;
static int tail_result = 1;
static int check1_result = -1;
static int leaf_result = 1;
static int countdown_result = 1;

/* What the engine answers category 2's calls. FN_2_4_TABLE fills its float return. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG: return (FakeResult){(uint32_t)flag_result, 0.0f};
    case FN_CHECK: return (FakeResult){(uint32_t)check_result, 0.0f};
    case FN_2_0_TAIL: return (FakeResult){(uint32_t)tail_result, 0.0f};
    case FN_2_0_CHECK: return (FakeResult){(uint32_t)check1_result, 0.0f};
    case FN_TABLE_LEAF: return (FakeResult){(uint32_t)leaf_result, 0.0f};
    case FN_COUNTDOWN: return (FakeResult){(uint32_t)countdown_result, 0.0f};
    case FN_2_4_TABLE: return (FakeResult){0, 3.0f};
    default: return (FakeResult){0, 0.0f};
    }
}

static void check_call(int i, uint32_t fn, const char *what) {
    CHECK(i < fake_call_count && fake_calls[i].fn == fn, "%s (call %d)", what, i);
}

int main(void) {
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    /* ── 2/0: the pre-call, the (-500) setter, motion 5 at 6.0; then motion 1 at 10.0 ── */
    const uint32_t e20 = 0x600000u, w20 = 0x620000u;
    spawn(e20, w20, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(e20, w20, 2, 0);
    CHECK(fake_call_count == 4, "2/0 state 0 made %d calls, want 4", fake_call_count);
    check_call(0, FN_PRE, "2/0 doesn't make the variant pre-call");
    check_call(1, FN_MODE, "2/0 doesn't set mode 0");
    check_call(2, FN_2_0_SET, "2/0 doesn't make the variant setter");
    CHECK(fake_calls[2].s0 == -500.0f, "2/0's kind 0 doesn't pass -500.0");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == 0x5u
          && fake_calls[3].s0 == 6.0f, "2/0 doesn't start motion 5 at 6.0");
    fake_reset_calls();
    frame_with(e20, w20, 2, 0);
    CHECK(fake_call_count == 4, "2/0 state 1 made %d calls, want 4", fake_call_count);
    check_call(0, FN_PRE, "2/0 doesn't make the variant pre-call every frame");
    check_call(1, FN_2_0_TAIL, "2/0 doesn't make its (0, 0x20) tail");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == 0x1u
          && fake_calls[2].s0 == 10.0f, "2/0 doesn't start motion 1 at 10.0");
    check_call(3, FN_BASE_UPDATE, "2/0 doesn't end on the base update");

    /* 2/11 (kind 5, variant 1): the check runs and stops the frame. */
    const uint32_t e211 = 0x630000u, w211 = 0x650000u;
    spawn(e211, w211, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e211, w211, 2, 11);
    CHECK(fake_call_count == 4 && fake_calls[2].s0 == -500.0f,
          "2/11's kind 5 doesn't pass -500.0");
    fake_reset_calls();
    check_result = 1;
    frame_with(e211, w211, 2, 11);
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_PRE
          && fake_calls[1].fn == FN_CHECK,
          "2/11's variant 1 doesn't run the pre-call and the kind check first");
    check_result = 0;

    /* ── 2/1: the five-argument data setup, the 1.1 step and the table leaf ── */
    const uint32_t e21 = 0x660000u, w21 = 0x680000u;
    spawn(e21, w21, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(e21, w21, 2, 1);
    CHECK(fake_call_count == 2, "2/1 state 0 made %d calls, want 2", fake_call_count);
    check_call(0, FN_MODE, "2/1 doesn't set mode 0");
    CHECK(fake_calls[1].fn == FN_DATA_SETUP && fake_calls[1].r1 == TABLE_2_1
          && fake_calls[1].r2 == 0 && fake_calls[1].r3 == 1 && fake_calls[1].has_r4
          && fake_calls[1].r4 == 0,
          "2/1 doesn't make the five-argument data setup with MH4U's table");
    fake_reset_calls();
    fake_mem_write8(w21 + WORK_DATAID, 5);
    frame_with(e21, w21, 2, 1);
    CHECK(fake_call_count == 3, "2/1 state 1 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_1_4_STEP && fake_calls[0].s0 == 1.1f,
          "2/1 doesn't make the 1.1 speed step for data id 5");
    CHECK(fake_calls[1].fn == FN_TABLE_LEAF && fake_calls[1].r1 == TABLE_2_1,
          "2/1 doesn't read the action table");
    check_call(2, FN_BASE_UPDATE, "2/1 doesn't end on the base update");

    /* ── 2/2 and 2/13: the same data setup with the second table; 2/13 pre-calls ── */
    const uint32_t e22 = 0x690000u, w22 = 0x6b0000u;
    spawn(e22, w22, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e22, w22, 2, 2);
    CHECK(fake_call_count == 2 && fake_calls[1].fn == FN_DATA_SETUP
          && fake_calls[1].r1 == TABLE_2_2,
          "2/2 doesn't make the data setup with MH4U's second table");
    fake_reset_calls();
    fake_mem_write8(w22 + WORK_DATAID, 5);
    frame_with(e22, w22, 2, 2);
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_1_4_STEP
          && fake_calls[2].fn == FN_BASE_UPDATE,
          "2/2 doesn't follow the 1.1 step and the leaf to the base update");

    const uint32_t e213 = 0x6c0000u, w213 = 0x6e0000u;
    spawn(e213, w213, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(e213, w213, 2, 13);
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_PRE
          && fake_calls[1].fn == FN_MODE && fake_calls[2].fn == FN_DATA_SETUP,
          "2/13 doesn't pre-call, set the mode and make the data setup");

    /* ── 2/3: the (-500) setter, motion 6 at 10.0; the 210.0 timer on variant 1 ── */
    const uint32_t e23 = 0x6f0000u, w23 = 0x710000u;
    spawn(e23, w23, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e23, w23, 2, 3);
    CHECK(fake_call_count == 3, "2/3 state 0 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == 0x6u
          && fake_calls[2].s0 == 10.0f, "2/3 doesn't start motion 6 at 10.0");
    CHECK(fake_log_contains("2/3: the source sets this+0x84's 0x80000 bit"),
          "2/3 doesn't log the source-only store");
    fake_reset_calls();
    tail_result = 1;
    frame_with(e23, w23, 2, 3);
    CHECK(fake_call_count == 3 && fake_calls[2].fn == FN_BASE_UPDATE,
          "2/3 doesn't follow its tail to the base update");

    const uint32_t e223 = 0x720000u, w223 = 0x740000u;
    spawn(e223, w223, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e223, w223, 2, 23);
    CHECK(ffrom(fake_mem_read32(w223 + WORK_TIMER)) == 210.0f,
          "2/23 doesn't arm the 210.0 timer on variant 1");

    /* ── 2/4: the kind's marker, motion 0x40c at 4.0, the state 1 steps, 0x102 at 12.0 ── */
    const uint32_t e24 = 0x750000u, w24 = 0x770000u;
    spawn(e24, w24, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(e24, w24, 2, 4);
    CHECK(fake_call_count == 2, "2/4 state 0 made %d calls, want 2", fake_call_count);
    CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == 0x40cu
          && fake_calls[1].s0 == 4.0f, "2/4 doesn't start motion 0x40c at 4.0");
    fake_reset_calls();
    frame_with(e24, w24, 2, 4);
    CHECK(fake_call_count == 7, "2/4 state 1 made %d calls, want 7", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLAG, "2/4 doesn't wait for the finish flag");
    CHECK(fake_calls[2].fn == FN_SET50 && fake_calls[2].s0 == 50.0f,
          "2/4 doesn't make the 50.0 setter");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == 0x40eu,
          "2/4 doesn't start motion 0x40e");
    CHECK(fake_calls[4].fn == FN_2_4_A, "2/4 doesn't make 0x0091b3bc");
    CHECK(fake_calls[5].fn == FN_2_4_TABLE && fake_calls[5].r1 == TABLE_2_4,
          "2/4 doesn't read its action table");
    CHECK(fake_calls[6].fn == FN_2_4_POINT && fake_calls[6].r1 == w24 + 0x1a8u,
          "2/4 doesn't advance its point");
    CHECK(fake_log_contains("2/4: the source's attack selector 0x0201e190"),
          "2/4 doesn't log its two gaps once");
    fake_reset_calls();
    frame_with(e24, w24, 2, 4);
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG
          && fake_calls[1].fn == FN_2_4_STEP
          && fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == 0x102u
          && fake_calls[2].s0 == 12.0f,
          "2/4 state 2 doesn't step and start motion 0x102 at 12.0");

    /* ── 9/3 and 9/4: the 2/4 unit with kind 1/3 and variant 1 ── */
    const uint32_t e93 = 0x780000u, w93 = 0x7a0000u;
    spawn(e93, w93, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e93, w93, 9, 3);
    CHECK(fake_mem_read32(e93 + ENEMY_MARKER) == 2u,
          "9/3 doesn't set the marker's bit 1");
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x40cu,
          "9/3 doesn't start motion 0x40c");
    fake_reset_calls();
    frame_with(e93, w93, 9, 3);
    CHECK(fake_call_count == 8 && fake_calls[7].fn == FN_2_4_END,
          "9/3 doesn't end its state 1 with 0x0093e558");

    const uint32_t e94 = 0x7b0000u, w94 = 0x7d0000u;
    spawn(e94, w94, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    /* The fast motion set is MH4U's data-id choice; id 2 selects it. */
    fake_mem_write8(w94 + WORK_DATAID, 2);
    frame_with(e94, w94, 9, 4);
    CHECK(fake_mem_read32(e94 + ENEMY_MARKER) == 8u,
          "9/4 doesn't set the marker's bit 3");
    CHECK(fake_call_count == 2 && fake_calls[1].r1 == 0x41fu,
          "9/4 doesn't start motion 0x41f on MH4U's data id 2");

    /* ── 2/14: the base's setter, the timer, the check and the 2/2 request ── */
    const uint32_t e214 = 0x7e0000u, w214 = 0x800000u;
    spawn(e214, w214, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(e214, w214, 2, 14);
    CHECK(fake_call_count == 4, "2/14 state 0 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == 0x7u
          && fake_calls[1].s0 == 4.0f, "2/14 doesn't start motion 7 at 4.0");
    CHECK(fake_calls[2].fn == FN_2_14_SET && fake_calls[2].r2 == 5 && fake_calls[2].r3 == 3,
          "2/14 doesn't make the (0, 5, 3) setter");
    CHECK(fake_calls[3].fn == FN_2_0_SET && fake_calls[3].r1 == 0x10u
          && fake_calls[3].s0 == 0.0f, "2/14's base 5 doesn't make the (0x10, 0, 0) setter");
    fake_reset_calls();
    frame_with(e214, w214, 2, 14);
    CHECK(fake_call_count == 5, "2/14 state 1 made %d calls, want 5", fake_call_count);
    CHECK(fake_calls[0].fn == FN_COUNTDOWN && fake_calls[0].s0 == 1.0f,
          "2/14 doesn't count its timer down by 1.0");
    CHECK(fake_calls[1].fn == FN_2_0_CHECK && fake_calls[1].r2 == 0x10000u,
          "2/14's base 5 doesn't make the 0x10000 check");
    CHECK(fake_calls[2].fn == FN_2_0_TAIL && fake_calls[2].r2 == 0x40u,
          "2/14 doesn't make its 0x40 tail");
    CHECK(fake_calls[3].fn == FN_2_14_A, "2/14 doesn't make 0x0090f8fc in state 2");
    CHECK(fake_calls[4].fn == FN_REQUEST_NEXT && fake_calls[4].r1 == 2
          && fake_calls[4].r2 == 2, "2/14 doesn't request action 2/2");

    const uint32_t e216 = 0x810000u, w216 = 0x830000u;
    spawn(e216, w216, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(e216, w216, 2, 16);
    CHECK(fake_calls[3].fn == FN_2_0_SET && fake_calls[3].r1 == 0
          && fake_calls[3].s0 == -300.0f,
          "2/16's base 7 doesn't make the (0, 0, -300.0) setter");

    const uint32_t e220 = 0x840000u, w220 = 0x860000u;
    spawn(e220, w220, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(e220, w220, 2, 20);
    CHECK(fake_call_count == 4 && fake_calls[3].r1 == 0x10u,
          "2/20's base 9 doesn't make the (0x10, 0, 0) setter");
    fake_reset_calls();
    frame_with(e220, w220, 2, 20);
    CHECK(fake_call_count == 5 && fake_calls[1].fn == FN_CHECK
          && fake_calls[1].r1 == 0,
          "2/20's base 9 doesn't make the 0-r1 check");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 2's units and 9/3, 9/4 make their calls in order\n");
    return 0;
}
