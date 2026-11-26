/*
 * cat2_9.c: categories 2 and 9's fake-host test — the nineteen ids 2/0 to 2/13 and 9/0 to
 * 9/4, their handler units' frame values and call order.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/
 * and builds it as tests/family-<stem>, so a slice adds its test file and edits nothing shared.
 * The shell's test (tests/test_rathian_3u.c) covers the factory association, the routing, the
 * ready line and the self-test; this one drives the nineteen ids' call sequences on the fake
 * host.
 *
 * The expected addresses, constants and frame values come from tests/rathian-3u/host.h, not
 * from the module, so a change in a handler fails the test instead of moving the expectation
 * with it. The blocked calls (#55 and the source's own data) are checked through the log: the
 * port names each once and skips it, and the test proves that it did.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The MH4U functions and fields categories 2 and 9 use. host.h holds the category-0 ones. */
#define FN_DECEL        0x0092dc50u
#define FN_SETUP        0x0092dcccu
#define FN_MARK         0x00922ca0u
#define FN_FORCE        0x0091db4cu
#define FN_MOTION       0x0094e318u
#define FN_SPEED        0x00916108u
#define FN_DATA         0x0096e164u
#define FN_FLOAT        0x00922250u
#define FN_POS          0x00912288u
#define FN_TURN         0x00911090u
#define FN_PER_MODE     0x0091aae4u
#define FN_GATE         0x00942220u
#define FN_MASK         0x0091a84cu
#define FN_ACTION       0x00914dc4u
#define FN_TURN2        0x0091b430u
#define FN_REQUEST_NEXT 0x0094ef64u
#define FN_APPLY        0x00922c40u
#define FN_FALL         0x0092e99cu

#define WORK_SUB        0x0145u
#define WORK_CLAMP_2    0x0238u
#define WORK_FLOAT_168  0x0168u
#define WORK_FLOAT_178  0x0178u
#define WORK_TURN       0x01a8u
#define WORK_PART       0x0278u
#define WORK_TAIL       0x7993u

/* MH4U's form of the source's motion numbers (file << 8 | slot). */
#define M_0_06 0x006u
#define M_0_07 0x007u
#define M_0_1b 0x01bu
#define M_2_02 0x202u
#define M_2_03 0x203u
#define M_2_05 0x205u
#define M_2_06 0x206u
#define M_2_07 0x207u
#define M_2_14 0x20eu
#define M_2_15 0x20fu
#define M_2_16 0x210u
#define M_2_17 0x211u

static int fake_flag = 1;
static int fake_setup = 1;
static int fake_per_mode = 0;
static int fake_gate = 0;
static int fake_mask = 0;

/* What the engine answers categories 2 and 9's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_SETUP:
        return (FakeResult){(uint32_t)fake_setup, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};
    case FN_PER_MODE:
        return (FakeResult){(uint32_t)fake_per_mode, 0.0f};
    case FN_GATE:
        return (FakeResult){(uint32_t)fake_gate, 0.0f};
    case FN_MASK:
        return (FakeResult){(uint32_t)fake_mask, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* One frame of an action whose state the test sets itself, and the calls it made. */
static void frame_state(uint32_t enemy, uint32_t work, int category, int index, int state,
                        int sub) {
    fake_mem_write8(work + WORK_STATE, (uint32_t)state);
    fake_mem_write8(work + WORK_SUB, (uint32_t)sub);
    fake_reset_calls();
    frame_with(enemy, work, category, index);
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

    /* ── 2/0: mode, the -500.0 sub, the request for motion 6 at 6.0 ── */
    {
        const uint32_t enemy = 0x130000u, work = 0x140000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 0);
        CHECK(fake_call_count == 3, "2/0 state 0 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0, "2/0 doesn't set mode 0");
        CHECK(fake_calls[1].fn == FN_DECEL && fake_calls[1].r1 == 0
              && fake_calls[1].s0 == -500.0f, "2/0 doesn't take the -500.0 decel");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == M_0_06
              && fake_calls[2].s0 == 6.0f, "2/0 doesn't request motion 6 at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "2/0 doesn't advance its state");

        /* state 1: the 0x8438e8 test (it is the source's completion test, not the finish
         * flag), then 0/2's base handler. */
        fake_reset_calls();
        frame_with(enemy, work, 2, 0);
        CHECK(fake_call_count == 3, "2/0 state 1 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_SETUP && fake_calls[0].r1 == 0 && fake_calls[0].r2 == 0x40,
              "2/0 state 1 doesn't run the 0x8438e8 test with 0/0x40");
        CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 0
              && fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r2 == 0
              && fake_calls[2].r3 == 2,
              "2/0 state 1 doesn't fall into 0/2's base handler");
        CHECK(fake_mem_read8(work + WORK_SET) == 1, "2/0's set byte isn't set");
    }

    /* ── 2/7: the 0.0 sub ── */
    {
        const uint32_t enemy = 0x150000u, work = 0x160000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 7);
        CHECK(fake_call_count == 3, "2/7 state 0 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[1].fn == FN_DECEL && fake_calls[1].s0 == 0.0f,
              "2/7 doesn't take the 0.0 decel");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == M_0_06,
              "2/7 doesn't request motion 6");
    }

    /* ── 2/9: the 0.0 sub and the 700.0 clamp ── */
    {
        const uint32_t enemy = 0x170000u, work = 0x180000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write32(work + WORK_CLAMP_2, fbits(1000.0f));
        fake_reset_calls();
        frame_with(enemy, work, 2, 9);
        CHECK(fake_call_count == 3, "2/9 state 0 made %d calls, want 3", fake_call_count);
        CHECK(ffrom(fake_mem_read32(work + WORK_CLAMP_2)) == 700.0f,
              "2/9 doesn't clamp the category-2 float at 700.0");
    }

    /* ── 2/11: the 0x83d18c mark, then the -500.0 sub ── */
    {
        const uint32_t enemy = 0x190000u, work = 0x1a0000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 11);
        CHECK(fake_call_count == 4, "2/11 state 0 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MARK, "2/11 doesn't mark its entry");
        CHECK(fake_calls[1].fn == FN_MODE && fake_calls[2].fn == FN_DECEL
              && fake_calls[2].s0 == -500.0f, "2/11 doesn't take the -500.0 decel");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == M_0_06,
              "2/11 doesn't request motion 6");
    }

    /* ── 2/3, 2/8 and 2/10: one unit, motion 7 at 10.0 ── */
    {
        const uint32_t enemy = 0x1b0000u, work = 0x1c0000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 3);
        CHECK(fake_call_count == 3, "2/3 state 0 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[1].fn == FN_DECEL && fake_calls[1].s0 == -500.0f,
              "2/3 doesn't take the -500.0 decel");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == M_0_07
              && fake_calls[2].s0 == 10.0f, "2/3 doesn't request motion 7 at 10.0");

        const uint32_t enemy8 = 0x1d0000u, work8 = 0x1e0000u;
        spawn(enemy8, work8, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy8, work8, 2, 8);
        CHECK(fake_calls[1].fn == FN_DECEL && fake_calls[1].s0 == 0.0f,
              "2/8 doesn't take the 0.0 decel");

        const uint32_t enemy10 = 0x1f0000u, work10 = 0x200000u;
        spawn(enemy10, work10, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write32(work10 + WORK_CLAMP_2, fbits(1000.0f));
        fake_reset_calls();
        frame_with(enemy10, work10, 2, 10);
        CHECK(ffrom(fake_mem_read32(work10 + WORK_CLAMP_2)) == 700.0f,
              "2/10 doesn't clamp the category-2 float at 700.0");

        /* state 1 is the same 0/2 fallback. */
        fake_reset_calls();
        frame_with(enemy10, work10, 2, 10);
        CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_SETUP,
              "2/10 state 1 doesn't run the 0x8438e8 test");
    }

    /* ── 2/4: 0x00687398's six states ── */
    {
        const uint32_t enemy = 0x210000u, work = 0x220000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 4);
        CHECK(fake_call_count == 2, "2/4 state 0 made %d calls, want 2", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0, "2/4 doesn't set mode 0");
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == M_2_14
              && fake_calls[1].s0 == 4.0f, "2/4 doesn't request motion 0xd6 at 4.0");

        /* state 1: the flag, mode 3, 50.0, motion 0xd7, 0x839968, the blocked float table,
         * the turn step. */
        fake_flag = 1;
        frame_state(enemy, work, 2, 4, 1, 0);
        CHECK(fake_call_count == 6, "2/4 state 1 made %d calls, want 6", fake_call_count);
        CHECK(fake_calls[0].fn == FN_FLAG, "2/4 state 1 doesn't wait for the flag");
        CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 3, "2/4 state 1 doesn't set mode 3");
        CHECK(fake_calls[2].fn == FN_SPEED && fake_calls[2].s0 == 50.0f,
              "2/4 state 1 doesn't set the speed to 50.0");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == M_2_15,
              "2/4 state 1 doesn't request motion 0xd7");
        CHECK(fake_calls[4].fn == FN_DATA, "2/4 state 1 doesn't run the data step");
        CHECK(fake_calls[5].fn == FN_POS && fake_calls[5].r1 == work + WORK_TURN
              && fake_calls[5].s0 == 1.0f, "2/4 state 1 doesn't advance the turn slot");
        CHECK(fake_log_contains("0x0083c6e0"), "2/4 state 1 doesn't name the blocked float table");
        CHECK(fake_mem_read8(work + WORK_STATE) == 2, "2/4 state 1 doesn't advance its state");

        /* state 2, flag clear: the turn step only. */
        fake_flag = 0;
        frame_state(enemy, work, 2, 4, 2, 0);
        CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_FLAG && fake_calls[1].fn == FN_POS,
              "2/4 state 2 with the flag clear doesn't make the turn step");

        /* state 2, flag set: state 3, the 0.5 float, the turn step, motion 0x1b. */
        fake_flag = 1;
        frame_state(enemy, work, 2, 4, 2, 0);
        CHECK(fake_call_count == 3, "2/4 state 2 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[1].fn == FN_TURN && fake_calls[1].r1 == work + WORK_TURN
              && fake_calls[1].s0 == 1.0f, "2/4 state 2 doesn't turn the slot");
        CHECK(ffrom(fake_mem_read32(work + WORK_FLOAT_178)) == 0.5f,
              "2/4 state 2 doesn't store the 0.5 float");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == M_0_1b
              && fake_calls[2].s0 == 6.0f, "2/4 state 2 doesn't request motion 0x1b at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 3, "2/4 state 2 doesn't advance to 3");

        /* state 3 sub 0: the turn step, the flag, the sub's motion 0x1b at 0.0. */
        fake_mem_write32(work + WORK_FLOAT_168, fbits(5.0f));
        frame_state(enemy, work, 2, 4, 3, 0);
        CHECK(fake_call_count == 3, "2/4 state 3 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_TURN && fake_calls[0].r1 == work + WORK_TURN,
              "2/4 state 3 doesn't turn the slot");
        CHECK(ffrom(fake_mem_read32(work + WORK_FLOAT_168)) == 0.0f,
              "2/4 state 3 doesn't clamp the per-frame float at 0.0");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == M_0_1b
              && fake_calls[2].s0 == 0.0f, "2/4 state 3 doesn't request motion 0x1b at 0.0");
        CHECK(fake_mem_read8(work + WORK_SUB) == 1, "2/4 state 3 sub 0 doesn't set its sub-state");

        /* state 3 sub 1: state 4 and motion 0xd8 at 6.0. */
        frame_state(enemy, work, 2, 4, 3, 1);
        CHECK(fake_call_count == 3 && fake_calls[2].fn == FN_MOTION
              && fake_calls[2].r1 == M_2_16 && fake_calls[2].s0 == 6.0f,
              "2/4 state 3 sub 1 doesn't request motion 0xd8 at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 4, "2/4 state 3 sub 1 doesn't advance to 4");

        /* state 4: mode 0 and motion 0xd9. */
        frame_state(enemy, work, 2, 4, 4, 0);
        CHECK(fake_call_count == 3 && fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 0
              && fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == M_2_17,
              "2/4 state 4 doesn't set mode 0 and request motion 0xd9");
        CHECK(fake_mem_read8(work + WORK_STATE) == 5, "2/4 state 4 doesn't advance to 5");

        /* state 5: the finish flag and 0/2's base handler. */
        frame_state(enemy, work, 2, 4, 5, 0);
        CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG
              && fake_calls[1].fn == FN_MODE && fake_calls[2].fn == FN_SET_ACTION
              && fake_calls[2].r2 == 0,
              "2/4 state 5 doesn't fall into 0/2's base handler");
    }

    /* ── 2/5: the same handler with mode 1, so state 3 runs 0/6's base handler ── */
    {
        const uint32_t enemy = 0x230000u, work = 0x240000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_state(enemy, work, 2, 5, 3, 0);
        CHECK(fake_call_count == 4, "2/5 state 3 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_TURN, "2/5 state 3 doesn't turn the slot");
        CHECK(fake_calls[2].fn == FN_MODE && fake_calls[2].r1 == 3,
              "2/5 state 3 doesn't set 0/6's mode 3");
        CHECK(fake_calls[3].fn == FN_SET_ACTION && fake_calls[3].r2 == 6,
              "2/5 state 3 doesn't start 0/6");
    }

    /* ── 2/6: the 0x83d18c mark before the same handler ── */
    {
        const uint32_t enemy = 0x250000u, work = 0x260000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 6);
        CHECK(fake_call_count == 3, "2/6 state 0 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MARK, "2/6 doesn't mark its entry");
        CHECK(fake_calls[1].fn == FN_MODE && fake_calls[2].fn == FN_MOTION
              && fake_calls[2].r1 == M_2_14, "2/6 doesn't run 0x00687398's state 0");
    }

    /* ── 9/3 and 9/4: the effect flag and the variant's effect branch ── */
    {
        const uint32_t enemy = 0x270000u, work = 0x280000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_flag = 1;
        fake_per_mode = 1;
        frame_state(enemy, work, 9, 3, 2, 0);
        CHECK(fake_call_count == 4, "9/3 state 2 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_PER_MODE && fake_calls[0].r1 == 0
              && fake_calls[0].s0 == 6.0f, "9/3 state 2 doesn't run the 0x83336c check at 6.0");
        CHECK(fake_calls[1].fn == FN_FLAG, "9/3 state 2 doesn't wait for the flag");
        CHECK(fake_calls[2].fn == FN_TURN && fake_calls[3].fn == FN_MOTION
              && fake_calls[3].r1 == M_0_1b, "9/3 state 2 doesn't run the common tail");
        CHECK(fake_log_contains("0x00688a20"),
              "9/3 state 2 doesn't name its blocked effect setup");

        const uint32_t enemy4 = 0x290000u, work4 = 0x2a0000u;
        spawn(enemy4, work4, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_state(enemy4, work4, 9, 4, 2, 0);
        CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_PER_MODE
              && fake_calls[3].fn == FN_MOTION,
              "9/4 state 2 doesn't run the same effect branch and tail");
    }

    /* ── 2/1, 2/2, 2/12, 2/13: the inline data setup and 0/2's fallback ── */
    {
        /* 2/1: state 0 is mode 0 and the named data call; state 1 applies 1.1 and falls
         * into 0/2. */
        const uint32_t enemy = 0x2b0000u, work = 0x2c0000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 2, 1);
        CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_MODE,
              "2/1 state 0 doesn't just set mode 0");
        CHECK(fake_log_contains("0x0082d278"), "2/1 doesn't name the blocked pending-data call");

        fake_mem_write8(work + WORK_KIND, 0x3f);
        fake_reset_calls();
        frame_with(enemy, work, 2, 1);
        CHECK(fake_call_count == 3, "2/1 state 1 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_APPLY && fake_calls[0].s0 == 1.1f,
              "2/1 state 1 doesn't apply the 1.1 float");
        CHECK(fake_calls[1].fn == FN_MODE && fake_calls[2].fn == FN_SET_ACTION,
              "2/1 state 1 doesn't fall into 0/2's base handler");

        /* 2/2: the same, with a non-0x3f kind so the float is not applied. */
        const uint32_t enemy2 = 0x2d0000u, work2 = 0x2e0000u;
        spawn(enemy2, work2, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_state(enemy2, work2, 2, 2, 1, 0);
        CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MODE
              && fake_calls[1].fn == FN_SET_ACTION,
              "2/2 state 1 doesn't fall into 0/2 without the 1.1 float");

        /* 2/12: the entry mark, then the data setup and 0/2. */
        const uint32_t enemy12 = 0x2f0000u, work12 = 0x300000u;
        spawn(enemy12, work12, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy12, work12, 2, 12);
        CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MARK
              && fake_calls[1].fn == FN_MODE, "2/12 state 0 doesn't mark and set mode 0");
        fake_mem_write8(work12 + WORK_KIND, 0x3f);
        frame_state(enemy12, work12, 2, 12, 1, 0);
        CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_MARK
              && fake_calls[1].fn == FN_APPLY && fake_calls[3].fn == FN_SET_ACTION,
              "2/12 state 1 doesn't mark, apply 1.1 and fall into 0/2");

        /* 2/13: the same inline block, then 0/2's base handler. */
        const uint32_t enemy13 = 0x310000u, work13 = 0x320000u;
        spawn(enemy13, work13, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy13, work13, 2, 13);
        CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MARK
              && fake_calls[1].fn == FN_MODE, "2/13 state 0 doesn't mark and set mode 0");
        fake_mem_write8(work13 + WORK_KIND, 0x3f);
        frame_state(enemy13, work13, 2, 13, 1, 0);
        CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_MARK
              && fake_calls[1].fn == FN_APPLY && fake_calls[3].fn == FN_SET_ACTION,
              "2/13 state 1 doesn't mark, apply 1.1 and fall into 0/2");
    }

    /* ── 9/0: mode, motion 0xca, then the blocked checks' 2/6 fallback ── */
    {
        const uint32_t enemy = 0x330000u, work = 0x340000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 9, 0);
        CHECK(fake_call_count == 2, "9/0 state 0 made %d calls, want 2", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0, "9/0 doesn't set mode 0");
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == M_2_02
              && fake_calls[1].s0 == 4.0f, "9/0 doesn't request motion 0xca at 4.0");
        CHECK(fake_log_contains("0x00853c70"), "9/0 doesn't name the blocked entry call");

        fake_flag = 1;
        frame_state(enemy, work, 9, 0, 1, 0);
        CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_FLAG
              && fake_calls[1].fn == FN_REQUEST_NEXT && fake_calls[1].r1 == 2
              && fake_calls[1].r2 == 6,
              "9/0 state 1 sub 0 doesn't wait for the flag and take the checks' 2/6 tail");
        CHECK(fake_mem_read8(work + WORK_SUB) == 1, "9/0 doesn't advance its sub-state");

        frame_state(enemy, work, 9, 0, 1, 1);
        CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_REQUEST_NEXT
              && fake_calls[0].r1 == 2 && fake_calls[0].r2 == 6,
              "9/0 state 1 sub 1 doesn't take the 2/6 fallback");
        CHECK(fake_log_contains("0x00839598") && fake_log_contains("0x0084512c"),
              "9/0 doesn't name the blocked checks");
    }

    /* ── 9/1: motion 0xcb and the tail-flag action, then the blocked checks' fallback ── */
    {
        const uint32_t enemy = 0x350000u, work = 0x360000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work + WORK_KIND, 0x20);
        fake_mem_write8(work + WORK_TAIL, 1);
        fake_reset_calls();
        frame_with(enemy, work, 9, 1);
        CHECK(fake_call_count == 3, "9/1 state 0 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[1].fn == FN_MOTION
              && fake_calls[1].r1 == M_2_03 && fake_calls[1].s0 == 4.0f,
              "9/1 doesn't set mode 0 and request motion 0xcb at 4.0");
        CHECK(fake_calls[2].fn == FN_ACTION && fake_calls[2].r1 == 0
              && fake_calls[2].r2 == 0x1a,
              "9/1 doesn't pick the 0x1a action from the tail flag");

        /* the kind 0x3f branch: tail 2 picks 0x28. */
        fake_mem_write8(work + WORK_KIND, 0x3f);
        fake_mem_write8(work + WORK_TAIL, 2);
        frame_state(enemy, work, 9, 1, 0, 0);
        CHECK(fake_call_count == 3 && fake_calls[2].fn == FN_ACTION
              && fake_calls[2].r2 == 0x28,
              "9/1 doesn't pick the 0x28 action for kind 0x3f and tail 2");

        fake_flag = 1;
        frame_state(enemy, work, 9, 1, 1, 0);
        CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG
              && fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == M_2_02
              && fake_calls[2].fn == FN_REQUEST_NEXT && fake_calls[2].r1 == 2
              && fake_calls[2].r2 == 6,
              "9/1 state 1 sub 0 doesn't request 0xca and take the checks' 2/6 tail");

        frame_state(enemy, work, 9, 1, 1, 1);
        CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_REQUEST_NEXT
              && fake_calls[0].r1 == 2 && fake_calls[0].r2 == 6,
              "9/1 state 1 sub 1 doesn't take the 2/6 fallback");
    }

    /* ── 9/2: motion 0xcd, the data/fall sequence, the turn states and 0/2 ── */
    {
        const uint32_t enemy = 0x370000u, work = 0x380000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        frame_with(enemy, work, 9, 2);
        CHECK(fake_call_count == 2, "9/2 state 0 made %d calls, want 2", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[1].fn == FN_MOTION
              && fake_calls[1].r1 == M_2_05 && fake_calls[1].s0 == 6.0f,
              "9/2 doesn't set mode 0 and request motion 0xcd at 6.0");

        fake_flag = 1;
        frame_state(enemy, work, 9, 2, 1, 0);
        CHECK(fake_call_count == 7, "9/2 state 1 made %d calls, want 7", fake_call_count);
        CHECK(fake_calls[0].fn == FN_FLAG, "9/2 state 1 doesn't wait for the flag");
        CHECK(fake_calls[1].fn == FN_DATA_FLOAT, "9/2 state 1 doesn't read the data float");
        CHECK(fake_calls[2].fn == FN_FALL && fake_calls[2].s0 == 1.5f,
              "9/2 state 1 doesn't apply the data float to the fall");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == M_2_06,
              "9/2 state 1 doesn't request motion 0xce");
        CHECK(fake_calls[4].fn == FN_ACTION && fake_calls[4].r2 == 0x1c
              && fake_calls[5].fn == FN_ACTION && fake_calls[5].r1 == 1
              && fake_calls[5].r2 == 0x25,
              "9/2 state 1 doesn't run the two 0x844a38 steps");
        CHECK(fake_calls[6].fn == FN_DATA, "9/2 state 1 doesn't run the data step");
        CHECK(fake_log_contains("0x00829620") && fake_log_contains("0x0083c6cc"),
              "9/2 state 1 doesn't name its blocked #55 calls");

        /* state 2: the data float, the turn, the gate, then state 3 and motion 0xcf. */
        fake_gate = 1;
        fake_mask = 0;
        fake_per_mode = 1;
        frame_state(enemy, work, 9, 2, 2, 0);
        CHECK(fake_call_count == 10, "9/2 state 2 made %d calls, want 10", fake_call_count);
        CHECK(fake_calls[0].fn == FN_DATA_FLOAT, "9/2 state 2 doesn't read the data float");
        CHECK(fake_calls[1].fn == FN_TURN2 && fake_calls[1].r1 == work + WORK_TURN
              && fake_calls[1].s0 == 1.5f && fake_calls[1].s1 == 1.0f,
              "9/2 state 2 doesn't run the sub-0 turn with the data float");
        CHECK(fake_calls[2].fn == FN_PER_MODE && fake_calls[2].r1 == 1
              && fake_calls[2].s0 == 16.0f, "9/2 state 2 doesn't run the 0x83336c gate at 16.0");
        CHECK(fake_calls[3].fn == FN_GATE && fake_calls[3].s0 == 1.5f,
              "9/2 state 2 doesn't run the 0x83369c gate");
        CHECK(fake_calls[5].fn == FN_MODE && fake_calls[5].r1 == 0,
              "9/2 state 2 doesn't set mode 0");
        CHECK(fake_calls[6].fn == FN_MOTION && fake_calls[6].r1 == M_2_07,
              "9/2 state 2 doesn't request motion 0xcf");
        CHECK(fake_calls[7].fn == FN_MASK && fake_calls[7].r1 == 1,
              "9/2 state 2 doesn't run the 0x838c28 mask");
        CHECK(fake_calls[8].fn == FN_ACTION && fake_calls[8].r2 == 0x16,
              "9/2 state 2 doesn't run the 0x16 action when the mask is clear");
        CHECK(fake_calls[9].fn == FN_MARK, "9/2 state 2 doesn't mark its entry");
        CHECK(fake_mem_read8(work + WORK_STATE) == 3, "9/2 state 2 doesn't advance to 3");

        /* state 3: the mark, the flag and 0/2's base handler. */
        frame_state(enemy, work, 9, 2, 3, 0);
        CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_MARK
              && fake_calls[1].fn == FN_FLAG && fake_calls[3].fn == FN_SET_ACTION,
              "9/2 state 3 doesn't mark, wait for the flag and fall into 0/2");
    }

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: categories 2 and 9's nineteen ids make their calls\n");
    return 0;
}
