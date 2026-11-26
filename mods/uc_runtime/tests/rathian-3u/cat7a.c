/*
 * cat7a.c: category 7 part 1's fake-host test — 7/0, 7/1, 7/2, 7/4, 7/5, 7/6, 7/7, 7/8,
 * 7/10, 7/11, 7/12, 7/15, 7/16, 7/19, 7/20, 7/32, 7/34, 7/42, 7/61, 7/77 and 7/85.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-3u/ and builds it as tests/family-<stem>, so a slice adds its test file and
 * edits nothing shared. The shell's test (tests/test_rathian_3u.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the seven
 * handler units' call sequences on the fake host, id by id and variant by variant.
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

/* The family's work-block offsets the expectations read (the runtime README's field map). */
#define WORK_STATE2     0x0145u
#define WORK_SPEED      0x0180u
#define WORK_TIMER      0x01d4u
#define WORK_AIM_Z      0x0168u
#define WORK_AIM_BZ     0x0178u
#define WORK_2A8        0x0238u
#define WORK_B81        0x0ca5u
#define WORK_TURN       0x01a8u

/* The MH4U engine functions the family calls. */
#define FN_MOTION       0x0094e318u
#define FN_VERTICAL     0x00915d44u
#define FN_SPEED        0x00916108u
#define FN_AIM_ADVANCE  0x00911090u
#define FN_TURN_STEP    0x0091db4cu
#define FN_PER_MODE     0x0091aae4u
#define FN_LAND         0x0092dcccu
#define FN_BLEND        0x0092dc50u
#define FN_CLEAR_SLOT   0x0090f8fcu
#define FN_TAIL         0x0093310cu
#define FN_TAIL0        0x00914dc4u
#define FN_ORDER        0x0091b7b0u
#define FN_TURN         0x00917570u
#define FN_AIM_RESET    0x0096e164u
#define FN_APPLY_NEXT   0x0092b140u
#define FN_EFFECT       0x00c0760cu
#define FN_RESET_ONE    0x00922ca0u

#define MOTION_7_0   ((0u << 8) | 0x2fu)
#define MOTION_7_1   ((2u << 8) | 0x09u)
#define MOTION_7_1b  ((2u << 8) | 0x08u)
#define MOTION_7_1c  ((2u << 8) | 0x0au)
#define MOTION_7_1d  ((2u << 8) | 0x18u)
#define MOTION_7_1e  ((2u << 8) | 0x15u)
#define MOTION_7_1f  ((0u << 8) | 0x35u)
#define MOTION_7_1g  ((0u << 8) | 0x3cu)
#define MOTION_7_2   ((0u << 8) | 0x33u)
#define MOTION_7_4b  ((0u << 8) | 0x31u)
#define MOTION_7_4a  ((0u << 8) | 0x32u)
#define MOTION_7_5   ((2u << 8) | 0x06u)
#define MOTION_7_5b  ((2u << 8) | 0x07u)
#define MOTION_7_6   ((0u << 8) | 0x08u)
#define MOTION_7_6b  ((0u << 8) | 0x09u)
#define MOTION_7_6c  ((0u << 8) | 0x40u)
#define MOTION_7_6d  ((0u << 8) | 0x30u)
#define MOTION_7_8   ((2u << 8) | 0x08u)

static int fake_flag;
static int fake_land;
static int per_mode_on;
static float per_mode_value;

/* What the engine answers category 7 part 1's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_LAND:
        return (FakeResult){(uint32_t)fake_land, 0.0f};
    case FN_PER_MODE:
        return (FakeResult){per_mode_on && s[0] == per_mode_value ? 1u : 0u, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* The call counter the section checks start at. */
static int base;
#define NEXT() (base++)

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

    /* ── every id in the slice runs the module's handler (state 0 sets the state byte) ── */
    {
        static const int ids[] = {0, 77, 1, 20, 42, 2, 10, 11, 15, 4, 12, 5, 61,
                                  6, 7, 16, 19, 32, 85, 8, 34};
        const uint32_t modes[] = {0, 0, 3, 3, 3, 0, 0, 0, 0, 0, 0, 3, 3,
                                  0, 0, 0, 0, 0, 0, 0, 0};
        for (unsigned i = 0; i < sizeof ids / sizeof ids[0]; i++) {
            const uint32_t enemy = 0x30000u + i * 0x2000u;
            const uint32_t work = 0x40000u + i * 0x2000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            frame_with(enemy, work, 7, ids[i]);
            CHECK(fake_skip_count == 1 && fake_original_count == 0,
                  "7/%d didn't run the module (%d original, %d skipped)", ids[i],
                  fake_original_count, fake_skip_count);
            CHECK(fake_call_count >= 2 && fake_calls[0].fn == FN_MODE
                  && fake_calls[0].r1 == modes[i],
                  "7/%d's state 0 doesn't set mode %u", ids[i], modes[i]);
            CHECK(fake_mem_read8(work + WORK_STATE) == 1, "7/%d doesn't advance its state",
                  ids[i]);
        }
    }

    /* ── 0x00693468: 7/0 and 7/77 — motion 0x2f at 4.0, two tail steps, then 0/2 ── */
    {
        const uint32_t enemy = 0x100000u, work = 0x101000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 7, 0);
        CHECK(fake_call_count == 4, "7/0 state 0 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0,
              "7/0 doesn't set mode 0");
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == MOTION_7_0
              && fake_calls[1].s0 == 4.0f,
              "7/0 doesn't start motion 0x2f at 4.0");
        CHECK(fake_calls[2].fn == FN_TAIL0 && fake_calls[2].r1 == 0 && fake_calls[2].r2 == 1,
              "7/0's first tail step is 0,1");
        CHECK(fake_calls[3].fn == FN_TAIL0 && fake_calls[3].r1 == 1 && fake_calls[3].r2 == 9,
              "7/0's second tail step is 1,9");
        CHECK(fake_log_contains("0x00842a7c"), "7/0 doesn't name the variants' blocked call");
        /* State 1 waits for the flag and falls into 0/2's base handler. */
        fake_reset_calls();
        fake_flag = 1;
        fake_mem_write8(work + WORK_0_2_STATE, 2);
        fake_mem_write32(work + WORK_FLAGS, 0x40);
        frame_with(enemy, work, 7, 0);
        CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_FLAG
              && fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 0
              && fake_calls[2].fn == FN_SET_ACTION && fake_calls[2].r2 == 2,
              "7/0 state 1 doesn't fall into 0/2's base handler");
        /* 7/77 is the same handler and the same state-0 calls for this monster. */
        const uint32_t enemy77 = 0x102000u, work77 = 0x103000u;
        spawn(enemy77, work77, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy77, work77, 7, 77);
        CHECK(fake_call_count == 4 && fake_calls[1].fn == FN_MOTION
              && fake_calls[1].r1 == MOTION_7_0,
              "7/77 doesn't run the 0x00693468 handler");
    }

    /* ── 0x00693be8: 7/1 — the 20.0 timer drive, then 0/6 ── */
    {
        const uint32_t enemy = 0x110000u, work = 0x111000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 7, 1);
        CHECK(fake_call_count == 3, "7/1 state 0 made %d calls, want 3", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 3,
              "7/1 doesn't set mode 3");
        CHECK(fake_calls[1].fn == FN_ORDER && fake_calls[1].r1 == (uint32_t)-14,
              "7/1 doesn't take the id-1 order step -14");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_7_1
              && fake_calls[2].s0 == 6.0f,
              "7/1 doesn't start motion 0xd1 at 6.0");
        CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 0.0f,
              "7/1 doesn't clear the timer");
        /* State 1 sub-state 0: the vertical step, the speed floor, the 0x100 turn and the
         * 50.0 check that latches the tail and the blend. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_SPEED, fbits(-300.0f));
        fake_mem_write8(work + WORK_STATE2, 0);
        per_mode_on = 1;
        per_mode_value = 50.0f;
        frame_with(enemy, work, 7, 1);
        CHECK(fake_call_count == 6, "7/1 state 1/0 made %d calls, want 6", fake_call_count);
        CHECK(fake_calls[0].fn == FN_VERTICAL && fake_calls[0].s0 == -3.3333333f,
              "7/1 doesn't take the source's -6.6666665 halved");
        CHECK(ffrom(fake_mem_read32(work + WORK_SPEED)) == -200.0f,
              "7/1 doesn't floor the speed at -200.0");
        CHECK(fake_calls[1].fn == FN_TURN_STEP && fake_calls[1].r1 == 0x100,
              "7/1 doesn't turn toward the 0x100 point");
        CHECK(fake_calls[2].fn == FN_PER_MODE && fake_calls[2].r1 == 1
              && fake_calls[2].s0 == 50.0f, "7/1 doesn't run the 50.0 per-mode check");
        CHECK(fake_calls[3].fn == FN_AIM_RESET,
              "7/1 doesn't clear the aim point and vector");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == 3.0f,
              "7/1 doesn't store the aim vector's 3.0");
        CHECK(fake_calls[4].fn == FN_BLEND && fake_calls[4].r1 == 0x10
              && fake_calls[4].s0 == 0.0f, "7/1's variant 0 blend isn't 0x10, 0.0");
        CHECK(fake_calls[5].fn == FN_TAIL && fake_calls[5].r1 == 0
              && fake_calls[5].r2 == 0x0e && fake_calls[5].r3 == 3,
              "7/1 doesn't end the latch with the 0,0xe,3 tail step");
        /* The same frame's sub-state 1: the aim advance, the 110.0 clamp and the flag
         * that starts motion 0xd0. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_AIM_Z, fbits(150.0f));
        fake_flag = 1;
        frame_with(enemy, work, 7, 1);
        CHECK(fake_call_count == 4, "7/1 state 1/1 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_VERTICAL, "7/1 state 1/1 doesn't step the vertical value");
        CHECK(fake_calls[1].fn == FN_AIM_ADVANCE && fake_calls[1].s0 == 1.0f,
              "7/1 doesn't advance the aim point at 1.0");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_Z)) == 110.0f,
              "7/1 doesn't clamp the aim point at 110.0");
        CHECK(fake_calls[2].fn == FN_FLAG,
              "7/1 state 1/1 doesn't wait for the flag");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_7_1b
              && fake_calls[3].s0 == 6.0f, "7/1 doesn't start motion 0xd0 at 6.0");
        /* State 2: the -200 speed, the aim step and the landing step, then motion 0xd2. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_AIM_Z, 0);
        fake_land = 1;
        frame_with(enemy, work, 7, 1);
        CHECK(fake_call_count == 4, "7/1 state 2 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_SPEED && fake_calls[0].s0 == -200.0f,
              "7/1 state 2 doesn't set the speed -200.0");
        CHECK(fake_calls[1].fn == FN_AIM_ADVANCE,
              "7/1 state 2 doesn't advance the aim point");
        CHECK(fake_calls[2].fn == FN_LAND && fake_calls[2].r1 == 0
              && fake_calls[2].r2 == 0, "7/1 state 2 doesn't run the 0,0 landing step");
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_7_1c
              && fake_calls[3].s0 == 6.0f, "7/1 state 2 doesn't start motion 0xd2 at 6.0");
        CHECK(ffrom(fake_mem_read32(work + WORK_AIM_BZ)) == -3.0f,
              "7/1 state 2 doesn't store the aim vector's -3.0");
        /* State 3: the timer drive at 20.0 (delta 0.5), the 110.0 check that clears the
         * slot, and the flag that reaches 0/6's base handler. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_TIMER, 0);
        fake_mem_write32(enemy + 0x14, fbits(0.5f));
        per_mode_on = 1;
        per_mode_value = 110.0f;
        fake_flag = 1;
        frame_with(enemy, work, 7, 1);
        CHECK(fake_call_count == 7, "7/1 state 3 made %d calls, want 7", fake_call_count);
        CHECK(fake_calls[0].fn == FN_SPEED
              && fake_calls[0].s0 == (20.0f - 0.5f) * -150.0f * 0.05f,
              "7/1 state 3 doesn't make the 20.0 timer's speed step");
        CHECK(fake_calls[1].fn == FN_PER_MODE && fake_calls[1].s0 == 110.0f,
              "7/1 state 3 doesn't run the 110.0 check");
        CHECK(fake_calls[2].fn == FN_CLEAR_SLOT && fake_calls[2].r1 == 0,
              "7/1 state 3 doesn't clear action slot 0");
        CHECK(fake_calls[3].fn == FN_AIM_ADVANCE,
              "7/1 state 3 doesn't advance the aim point");
        CHECK(fake_calls[4].fn == FN_FLAG, "7/1 state 3 doesn't test the flag");
        CHECK(fake_calls[5].fn == FN_MODE && fake_calls[5].r1 == 3
              && fake_calls[6].fn == FN_SET_ACTION && fake_calls[6].r2 == 6,
              "7/1 state 3 doesn't end in 0/6's base handler");
    }

    /* ── 0x00693be8 via 7/20 and 7/42: the other two state-3 variants ── */
    {
        /* 7/20's state 2: the -200.0 speed, the aim step and the landing step, then mode 0
         * and motion 0xdd at 0.0. */
        const uint32_t enemy2 = 0x124000u, work2 = 0x125000u;
        spawn(enemy2, work2, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work2 + WORK_STATE, 2);
        fake_mem_write8(work2 + WORK_STATE2, 0);
        fake_mem_write32(work2 + WORK_AIM_Z, 0);
        fake_land = 1;
        frame_with(enemy2, work2, 7, 20);
        CHECK(fake_call_count == 6 && fake_calls[0].fn == FN_SPEED
              && fake_calls[1].fn == FN_AIM_ADVANCE && fake_calls[2].fn == FN_LAND
              && fake_calls[3].fn == FN_MODE && fake_calls[3].r1 == 0
              && fake_calls[4].fn == FN_MOTION && fake_calls[4].r1 == MOTION_7_1e
              && fake_calls[4].s0 == 0.0f && fake_calls[5].fn == FN_SPEED
              && fake_calls[5].s0 == 0.0f,
              "7/20 state 2 doesn't finish into mode 0, motion 0xdd and speed 0.0");
        /* 7/42's state 2 finishes into motion 0x35 at 10.0. */
        const uint32_t enemy42s = 0x126000u, work42s = 0x127000u;
        spawn(enemy42s, work42s, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work42s + WORK_STATE, 2);
        fake_mem_write8(work42s + WORK_STATE2, 0);
        fake_mem_write32(work42s + WORK_AIM_Z, 0);
        fake_land = 1;
        frame_with(enemy42s, work42s, 7, 42);
        CHECK(fake_call_count == 4 && fake_calls[0].fn == FN_SPEED
              && fake_calls[1].fn == FN_AIM_ADVANCE && fake_calls[2].fn == FN_LAND
              && fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_7_1f
              && fake_calls[3].s0 == 10.0f,
              "7/42 state 2 doesn't finish into motion 0x35 at 10.0");
        const uint32_t enemy = 0x120000u, work = 0x121000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work + WORK_STATE, 3);
        fake_mem_write8(work + WORK_STATE2, 0);
        fake_flag = 1;
        frame_with(enemy, work, 7, 20); /* variant 1: motion 0xda at 0.0 */
        CHECK(fake_calls[0].fn == FN_FLAG, "7/20's state 3 doesn't wait for the flag");
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == MOTION_7_1d
              && fake_calls[1].s0 == 0.0f, "7/20 doesn't start motion 0xda at 0.0");
        /* Next frame, sub-state 1: the 30.0 check, the slot clear, then the 0/2 base. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE2, 1);
        per_mode_on = 1;
        per_mode_value = 30.0f;
        frame_with(enemy, work, 7, 20);
        CHECK(fake_calls[0].fn == FN_PER_MODE && fake_calls[0].s0 == 30.0f,
              "7/20 doesn't run the 30.0 check");
        CHECK(fake_calls[1].fn == FN_CLEAR_SLOT,
              "7/20's 30.0 check doesn't clear the slot");
        CHECK(fake_calls[4].fn == FN_SET_ACTION,
              "7/20 doesn't end in 0/2's base handler");

        const uint32_t enemy42 = 0x122000u, work42 = 0x123000u;
        spawn(enemy42, work42, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work42 + WORK_STATE, 3);
        fake_mem_write8(work42 + WORK_STATE2, 0);
        fake_mem_write32(enemy42 + 0x14, fbits(1.0f));
        fake_mem_write32(work42 + WORK_TIMER, 0);
        fake_flag = 1;
        frame_with(enemy42, work42, 7, 42); /* variant 2: the 10.0/5.0 timer */
        CHECK(fake_calls[0].fn == FN_SPEED
              && fake_calls[0].s0 == (5.0f - 1.0f) * -200.0f * 0.2f,
              "7/42's state 3 doesn't make the 10.0/5.0 speed step");
        CHECK(fake_calls[1].fn == FN_FLAG, "7/42's state 3 doesn't wait for the flag");
        CHECK(fake_calls[2].fn == FN_CLEAR_SLOT, "7/42 doesn't clear the action slot");
        CHECK(fake_calls[3].fn == FN_MODE && fake_calls[3].r1 == 0,
              "7/42 doesn't set mode 0");
        CHECK(fake_calls[4].fn == FN_MOTION && fake_calls[4].r1 == MOTION_7_1g
              && fake_calls[4].s0 == 0.0f, "7/42 doesn't start motion 0x3c at 0.0");
    }

    /* ── 0x00694180: 7/2 — motion 0x33 at 6.0 and the four checks ── */
    {
        const uint32_t enemy = 0x130000u, work = 0x131000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 7, 2);
        CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_MODE
              && fake_calls[1].fn == FN_ORDER && fake_calls[2].fn == FN_MOTION
              && fake_calls[2].r1 == MOTION_7_2 && fake_calls[2].s0 == 6.0f,
              "7/2 state 0 doesn't set mode 0, the order step and motion 0x33 at 6.0");
        /* State 1 with only the 12.0 check true: the four checks run in order and only
         * 12.0's effect is spawned; the flag is tested last. */
        fake_reset_calls();
        fake_flag = 0;
        per_mode_on = 1;
        per_mode_value = 12.0f;
        frame_with(enemy, work, 7, 2);
        CHECK(fake_call_count == 6, "7/2 state 1 made %d calls, want 6", fake_call_count);
        CHECK(fake_calls[0].fn == FN_PER_MODE && fake_calls[0].s0 == 2.0f,
              "7/2 doesn't run the 2.0 check first");
        CHECK(fake_calls[1].fn == FN_PER_MODE && fake_calls[1].s0 == 12.0f,
              "7/2 doesn't run the 12.0 check second");
        CHECK(fake_calls[2].fn == FN_EFFECT && fake_calls[2].r1 == 1
              && fake_calls[2].r2 == enemy, "7/2's 12.0 check doesn't spawn effect type 1");
        CHECK(fake_calls[3].fn == FN_PER_MODE && fake_calls[3].s0 == 36.0f,
              "7/2 doesn't run the 36.0 check third");
        CHECK(fake_calls[4].fn == FN_PER_MODE && fake_calls[4].s0 == 78.0f,
              "7/2 doesn't run the 78.0 check fourth");
        CHECK(fake_calls[5].fn == FN_FLAG, "7/2 doesn't test the finish flag last");
        /* The 78.0 check names the two blocked pieces and makes no 0x0084161c call. */
        fake_reset_calls();
        per_mode_value = 78.0f;
        frame_with(enemy, work, 7, 2);
        CHECK(fake_log_contains("0x0084161c"), "7/2 doesn't name the blocked target check");
        CHECK(fake_log_contains("0x00688a20"), "7/2 doesn't name the blocked effect builder");
        /* 7/15 (variant 3) keeps the order step out of state 0 and names the source curve. */
        const uint32_t enemy15 = 0x132000u, work15 = 0x133000u;
        spawn(enemy15, work15, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy15, work15, 7, 15);
        CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_MODE
              && fake_calls[1].fn == FN_MOTION, "7/15's state 0 doesn't skip the order step");
        fake_reset_calls();
        per_mode_on = 0;
        frame_with(enemy15, work15, 7, 15);
        CHECK(fake_log_contains("0x00b0b1c0"),
              "7/15 doesn't name the source value curve it cannot carry");
    }

    /* ── 0x006944b8: 7/4 and 7/12 — the motion, the three tail steps and the turn ── */
    {
        const uint32_t enemy = 0x140000u, work = 0x141000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 7, 4);
        CHECK(fake_call_count == 4, "7/4 state 0 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0,
              "7/4 doesn't set mode 0");
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == MOTION_7_4a
              && fake_calls[1].s0 == 4.0f, "7/4 doesn't start motion 0x32 at 4.0");
        CHECK(fake_calls[2].fn == FN_TAIL && fake_calls[2].r1 == 0
              && fake_calls[2].r2 == 0x1d && fake_calls[2].r3 == 8,
              "7/4's first tail step is 0,0x1d,8");
        CHECK(fake_calls[3].fn == FN_TAIL && fake_calls[3].r1 == 1
              && fake_calls[3].r2 == 0x22 && fake_calls[3].r3 == 0x18,
              "7/4's second tail step is 1,0x22,0x18");
        /* The third tail step is the state 1 latch's, not state 0's. */
        /* State 1: the turn at -0x8000 over 0..120, then the flag moves to state 2. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_B81, 0);
        fake_mem_write8(work + WORK_STATE2, 1); /* the latch already taken */
        fake_flag = 1;
        frame_with(enemy, work, 7, 4);
        CHECK(fake_calls[0].fn == FN_TURN && fake_calls[0].r1 == (uint32_t)-0x8000
              && fake_calls[0].s0 == 0.0f && fake_calls[0].s1 == 120.0f,
              "7/4 doesn't turn by -0x8000 over 0..120");
        CHECK(fake_calls[1].fn == FN_FLAG, "7/4 state 1 doesn't wait for the flag");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_7_4a,
              "7/4 state 1 doesn't restart motion 0x32");
        /* The b81 gate: 7/12's second tail step is the variant-1 one. */
        const uint32_t enemy12 = 0x142000u, work12 = 0x143000u;
        spawn(enemy12, work12, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work12 + WORK_B81, 1);
        frame_with(enemy12, work12, 7, 12);
        CHECK(fake_calls[1].fn == FN_MOTION && fake_calls[1].r1 == MOTION_7_4b,
              "7/12 doesn't start motion 0x31");
        CHECK(fake_calls[2].fn == FN_TAIL && fake_calls[2].r2 == 4,
              "7/12's first tail step isn't the variant-1 4");
    }

    /* ── 0x00694694: 7/5 and 7/61 — motion 0xce at 10.0, 0xcf or 0/6 ── */
    {
        const uint32_t enemy = 0x150000u, work = 0x151000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 7, 5);
        CHECK(fake_call_count == 4, "7/5 state 0 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 3,
              "7/5 doesn't set mode 3");
        CHECK(fake_calls[1].fn == FN_ORDER, "7/5 doesn't take the order step");
        CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_7_5
              && fake_calls[2].s0 == 10.0f, "7/5 doesn't start motion 0xce at 10.0");
        CHECK(fake_calls[3].fn == FN_TAIL0 && fake_calls[3].r1 == 0
              && fake_calls[3].r2 == 0x1b, "7/5's tail step isn't 0,0x1b");
        /* State 1 while the flag is clear: the aim reset and the 200.0 speed ratio. */
        fake_reset_calls();
        fake_flag = 0;
        per_mode_on = 1;
        per_mode_value = 200.0f;
        fake_mem_write32(enemy + 0x290, fbits(300.0f));
        fake_mem_write32(enemy + 0x294, fbits(250.0f));
        base = 0;
        frame_with(enemy, work, 7, 5);
        CHECK(fake_call_count == 4, "7/5 state 1 made %d calls, want 4", fake_call_count);
        CHECK(fake_calls[0].fn == FN_RESET_ONE, "7/5 doesn't run the one-shot reset");
        CHECK(fake_calls[1].fn == FN_FLAG, "7/5 state 1 doesn't test the flag");
        CHECK(fake_calls[2].fn == FN_PER_MODE && fake_calls[2].s0 == 200.0f,
              "7/5 doesn't run the 200.0 check");
        CHECK(fake_calls[3].fn == FN_SPEED
              && fake_calls[3].s0 == ((300.0f - 200.0f) / (250.0f - 200.0f)) * -150.0f,
              "7/5's speed ratio isn't (A-200)/(B-200) * -150");
        /* The flag then sends 7/5 into motion 0xcf and a second state. */
        fake_reset_calls();
        fake_flag = 1;
        frame_with(enemy, work, 7, 5);
        CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_7_5b
              && fake_calls[3].s0 == 0.0f, "7/5 doesn't start motion 0xcf at 0.0");
        /* 7/61 (variant 1) ends in 0/6's base instead. */
        const uint32_t enemy61 = 0x152000u, work61 = 0x153000u;
        spawn(enemy61, work61, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_mem_write8(work61 + WORK_STATE, 1);
        fake_reset_calls();
        frame_with(enemy61, work61, 7, 61);
        CHECK(fake_calls[0].fn == FN_RESET_ONE, "7/61 doesn't run the one-shot reset");
        CHECK(fake_calls[1].fn == FN_FLAG, "7/61 doesn't wait for the flag");
        CHECK(fake_calls[2].fn == FN_MODE && fake_calls[2].r1 == 3,
              "7/61 doesn't set mode 3 before 0/6's base");
        CHECK(fake_calls[fake_call_count - 1].fn == FN_SET_ACTION
              && fake_calls[fake_call_count - 1].r2 == 6,
              "7/61 doesn't end in 0/6's base handler");
    }

    /* ── 0x00694840: the six variants' state 0 and their next motions ── */
    {
        static const int ids[] = {6, 7, 16, 19, 32, 85};
        const float blends[] = {-300.0f, -900.0f, -300.0f, -300.0f, -2000.0f, -600.0f};
        const uint32_t filters[] = {0x10u, 0x10u, 0u, 0u, 0x10u, 0x10u};
        const float timers[] = {20.0f, 0.0f, 0.0f, 0.0f, 0.0f, 0.0f};
        for (unsigned i = 0; i < sizeof ids / sizeof ids[0]; i++) {
            const uint32_t enemy = 0x160000u + i * 0x2000u;
            const uint32_t work = 0x170000u + i * 0x2000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            base = 0;
            frame_with(enemy, work, 7, ids[i]);
            CHECK(fake_calls[NEXT()].fn == FN_MODE && fake_calls[0].r1 == 0,
                  "7/%d doesn't set mode 0", ids[i]);
            CHECK(fake_calls[NEXT()].fn == FN_ORDER, "7/%d doesn't take the order step",
                  ids[i]);
            CHECK(fake_calls[NEXT()].fn == FN_MOTION && fake_calls[2].r1 == MOTION_7_6
                  && fake_calls[2].s0 == 4.0f, "7/%d doesn't start motion 0x8 at 4.0",
                  ids[i]);
            CHECK(fake_calls[NEXT()].fn == FN_TAIL && fake_calls[3].r1 == 0
                  && fake_calls[3].r2 == 5 && fake_calls[3].r3 == 3,
                  "7/%d's tail step isn't 0,5,3", ids[i]);
            CHECK(fake_calls[NEXT()].fn == FN_BLEND && fake_calls[4].r1 == filters[i]
                  && fake_calls[4].s0 == blends[i],
                  "7/%d's blend isn't %u, %g", ids[i], filters[i], (double)blends[i]);
            CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == timers[i],
                  "7/%d's timer isn't %g", ids[i], (double)timers[i]);
        }
        /* 7/16's state 0 clamps work+0x2a8 at 1000.0. */
        {
            const uint32_t enemy = 0x174000u, work = 0x175000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            fake_mem_write32(work + WORK_2A8, fbits(2000.0f));
            frame_with(enemy, work, 7, 16);
            CHECK(ffrom(fake_mem_read32(work + WORK_2A8)) == 1000.0f,
                  "7/16 doesn't clamp work+0x2a8 at 1000.0");
        }
        /* State 1: the 20.0 timer (delta 0.5), the landing step with 0x80 for 7/6, then
         * motion 0x9 once it is spent. */
        {
            const uint32_t enemy = 0x176000u, work = 0x177000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            fake_mem_write8(work + WORK_STATE, 1);
            fake_mem_write32(work + WORK_TIMER, fbits(20.0f));
            fake_mem_write32(enemy + 0x14, fbits(0.5f));
            fake_land = 0;
            frame_with(enemy, work, 7, 6);
            CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_LAND
                  && fake_calls[0].r1 == 0 && fake_calls[0].r2 == 0x80,
                  "7/6's landing step isn't 0,0x80");
            CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 19.5f,
                  "7/6 doesn't count the 20.0 timer down by the frame delta");
            fake_reset_calls();
            fake_land = 1;
            frame_with(enemy, work, 7, 6);
            CHECK(fake_call_count == 1 && ffrom(fake_mem_read32(work + WORK_TIMER)) == 19.0f,
                  "7/6 runs past its unspent timer");
            fake_reset_calls();
            fake_mem_write32(work + WORK_TIMER, fbits(0.1f));
            frame_with(enemy, work, 7, 6);
            CHECK(fake_calls[1].fn == FN_CLEAR_SLOT, "7/6 doesn't clear the slot");
            CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_7_6b
                  && fake_calls[2].s0 == 4.0f, "7/6 doesn't start motion 0x9 at 4.0");
            CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 0.0f,
                  "7/6 doesn't zero the spent timer");
        }
        /* The other variants' state 1 landing flags and state 1 motions. */
        {
            const uint32_t enemy = 0x178000u, work = 0x179000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            fake_mem_write8(work + WORK_STATE, 1);
            fake_mem_write32(work + WORK_TIMER, 0);
            fake_land = 0;
            frame_with(enemy, work, 7, 7);
            CHECK(fake_calls[0].fn == FN_LAND && fake_calls[0].r2 == 0x40,
                  "7/7's landing step isn't 0x40");
            const uint32_t motions[] = {MOTION_7_6b, MOTION_7_6c, MOTION_7_6d, 0, MOTION_7_6b};
            const int variants[] = {7, 16, 19, 32, 85};
            for (unsigned i = 0; i < 5; i++) {
                const uint32_t e = 0x17a000u + i * 0x2000u;
                const uint32_t w = 0x17b000u + i * 0x2000u;
                spawn(e, w, MHUC_MONSTER_ID_RATHIAN_3U, 1);
                fake_mem_write8(w + WORK_STATE, 1);
                fake_mem_write32(w + WORK_TIMER, 0);
                fake_land = 1;
                base = 0;
                frame_with(e, w, 7, variants[i]);
                if (variants[i] == 32) {
                    CHECK(fake_calls[1].fn == FN_CLEAR_SLOT
                          && fake_calls[2].fn == FN_APPLY_NEXT
                          && fake_calls[2].r1 == 4 && fake_calls[2].r2 == 7,
                          "7/32 doesn't apply 4/7");
                } else if (variants[i] == 16 || variants[i] == 19) {
                    CHECK(fake_calls[1].fn == FN_MOTION
                          && fake_calls[1].r1 == motions[i],
                          "7/%d's state 1 doesn't start the expected motion", variants[i]);
                } else {
                    CHECK(fake_calls[1].fn == FN_CLEAR_SLOT
                          && fake_calls[2].fn == FN_MOTION
                          && fake_calls[2].r1 == motions[i],
                          "7/%d's state 1 doesn't clear the slot and start its motion",
                          variants[i]);
                }
            }
        }
        /* State 2: the 36.0 check and the 0xd tail for 7/6, the 120.0 check for 7/16. */
        {
            const uint32_t enemy = 0x18e000u, work = 0x18f000u;
            spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
            fake_mem_write8(work + WORK_STATE, 2);
            fake_mem_write8(work + WORK_STATE2, 0);
            fake_flag = 0;
            per_mode_on = 1;
            per_mode_value = 36.0f;
            base = 0;
            frame_with(enemy, work, 7, 6);
            CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[0].r1 == 1
                  && fake_calls[0].s0 == 36.0f, "7/6 state 2 doesn't run the 36.0 check");
            CHECK(fake_calls[NEXT()].fn == FN_TAIL0 && fake_calls[1].r1 == 0
                  && fake_calls[1].r2 == 0x0d, "7/6's 36.0 check doesn't run tail 0,0xd");
            fake_reset_calls();
            fake_mem_write8(work + WORK_STATE2, 0);
            per_mode_value = 120.0f;
            frame_with(enemy, work, 7, 16);
            CHECK(fake_calls[0].fn == FN_PER_MODE && fake_calls[0].s0 == 120.0f,
                  "7/16 state 2 doesn't run the 120.0 check");
            CHECK(fake_calls[1].fn == FN_CLEAR_SLOT,
                  "7/16's 120.0 check doesn't clear the slot");
        }
    }

    /* ── 0x00694bf4: 7/8 and 7/34 — motion 0xd0 at 4.0 and the 2/12/36 checks ── */
    {
        const uint32_t enemy = 0x190000u, work = 0x191000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy, work, 7, 8);
        CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_MODE
              && fake_calls[1].fn == FN_ORDER && fake_calls[2].fn == FN_MOTION
              && fake_calls[2].r1 == MOTION_7_8 && fake_calls[2].s0 == 4.0f,
              "7/8 state 0 doesn't set mode 0, the order step and motion 0xd0 at 4.0");
        /* State 1: the 2/12/36 checks spawn effects; 78 is where the blocked structure
         * begins. */
        fake_reset_calls();
        fake_flag = 0;
        per_mode_on = 1;
        per_mode_value = 2.0f;
        base = 0;
        frame_with(enemy, work, 7, 8);
        CHECK(fake_call_count == 8, "7/8 state 1 made %d calls, want 8", fake_call_count);
        CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[0].s0 == 2.0f,
              "7/8 doesn't run the 2.0 check first");
        CHECK(fake_calls[NEXT()].fn == FN_EFFECT && fake_calls[1].r1 == 3,
              "7/8's 2.0 check doesn't spawn effect type 3");
        CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[2].s0 == 12.0f,
              "7/8 doesn't run the 12.0 check");
        CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[3].s0 == 36.0f,
              "7/8 doesn't run the 36.0 check");
        CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[4].s0 == 78.0f,
              "7/8 doesn't run the 78.0 check");
        CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[5].s0 == 120.0f,
              "7/8 doesn't run the 120.0 check");
        CHECK(fake_calls[NEXT()].fn == FN_PER_MODE && fake_calls[6].s0 == 164.0f,
              "7/8 doesn't run the 164.0 check");
        CHECK(fake_log_contains("0x0084161c"), "7/8 doesn't name the blocked target check");
        /* 7/34 adds the source value curve and names it. */
        const uint32_t enemy34 = 0x192000u, work34 = 0x193000u;
        spawn(enemy34, work34, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        frame_with(enemy34, work34, 7, 34);
        fake_reset_calls();
        per_mode_on = 0;
        frame_with(enemy34, work34, 7, 34);
        CHECK(fake_log_contains("0x00b0b1e8"),
              "7/34 doesn't name the source value curve it cannot carry");
    }

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 7 part 1's seven units make their calls, id by id\n");
    return 0;
}
