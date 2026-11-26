/*
 * cat13c.c: category 13 part 3's fake-host test — 13/7, 13/8 and 13/9.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-3u/ and builds it as tests/family-<stem>, so a slice adds its test file and
 * edits nothing shared. The shell's test (tests/test_rathian_3u.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the three ids'
 * call sequences on the fake host.
 *
 * The expected addresses, offsets, frame values and motion numbers come from
 * tests/rathian-3u/host.h and this file's own constants, not from the module, so a change in
 * a handler fails the test instead of moving the expectation with it. A motion number is
 * MH4U's `file << 8 | slot` of the source's `file * 100 + slot`.
 *
 * 13/7 and 13/9 are case blocks that start a motion and then fall into the base-class handler
 * 0x00858b6c (cat0.c's mhuc_3u_base_0_3); 13/9 tests the finish flag first and 13/7 does not.
 * 13/8 is the seventeen-state unit 0x0069031c.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The family's work-block offsets (the runtime README's field map). */
#define WORK_STATE  0x0144u
#define WORK_TIMER  0x01d4u
#define ENEMY_DELTA 0x0014u

/* The MH4U engine functions the family calls. */
#define FN_ONE_SHOT    0x00922ca0u
#define FN_DATA_FLOAT  0x0093d870u
#define FN_APPLY_FALL  0x0092e99cu
#define FN_MOTION      0x0094e318u
#define FN_PER_MODE    0x0091aae4u
#define FN_FLAG        0x00b05da4u
#define FN_MODE        0x009167b4u
#define FN_DATA_GET    0x0068882cu
#define FN_SET_ACTION  0x0090ef74u

#define MOTION_1A ((0u << 8) | 0x1au)
#define MOTION_3D ((0u << 8) | 0x3du)
#define MOTION_1F ((0u << 8) | 0x1fu)
#define MOTION_20 ((0u << 8) | 0x20u)
#define MOTION_1B ((0u << 8) | 0x1bu)
#define MOTION_1C ((0u << 8) | 0x1cu)
#define MOTION_DB ((2u << 8) | 0x13u) /* 3U 0xdb */
#define MOTION_CE ((2u << 8) | 0x06u) /* 3U 0xce */
#define MOTION_CF ((2u << 8) | 0x07u) /* 3U 0xcf */

static int fake_flag = 1;
static int per_mode_on;
static float per_mode_value;
static float fake_data = 1.5f;

/* What the engine answers category 13 part 3's calls. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)user;
    switch (fn) {
    case FN_FLAG:
        return (FakeResult){(uint32_t)fake_flag, 0.0f};
    case FN_PER_MODE:
        return (FakeResult){per_mode_on && s[0] == per_mode_value ? 1u : 0u, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0u, fake_data};
    case FN_DATA_GET:
        return (FakeResult){RECORD_ADDRESS, 0.0f};
    default:
        return (FakeResult){0u, 0.0f};
    }
}

/* One call's function, for a readable failure. */
static int call_fn(int i) {
    return i < fake_call_count ? (int)fake_calls[i].fn : -1;
}

/* Prepare one monster and the record the base handler reads. */
static void prepare(uint32_t enemy, uint32_t work) {
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
    fake_mem_write8(work + WORK_KIND, 1);
    fake_mem_write32(RECORD_ADDRESS + 0x64u, fbits(1.5f));
    fake_mem_write32(work + WORK_RATE, fbits(2.0f));
    fake_mem_write32(work + WORK_RATE_2, fbits(3.0f));
    fake_mem_write32(work + WORK_POS_Y, fbits(100.0f));
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
        static const int ids[] = {7, 8, 9};
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

    /* ── 13/7's block 0x00699bf8: one-shot, motion 0x1a, then 0x00858b6c ───────── */
    {
        const uint32_t enemy = 0x100000u, work = 0x101000u;
        prepare(enemy, work);
        fake_reset_calls();
        frame_with(enemy, work, 13, 7);
        CHECK(fake_call_count == 4, "13/7 state 0 made %d calls, want 4", fake_call_count);
        CHECK(call_fn(0) == (int)FN_ONE_SHOT, "13/7 doesn't set the one-shot byte first");
        CHECK(call_fn(1) == (int)FN_DATA_FLOAT, "13/7 state 0 doesn't read the data float");
        CHECK(call_fn(2) == (int)FN_APPLY_FALL && fake_calls[2].s0 == fake_data,
              "13/7 state 0 doesn't advance the fall by the data float");
        CHECK(call_fn(3) == (int)FN_MOTION && fake_calls[3].r1 == MOTION_1A
              && fake_calls[3].s0 == 0.0f, "13/7 state 0 doesn't start motion 0x1a at 0.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/7 doesn't advance its state");
        CHECK(fake_log_contains("0x005bf77c"), "13/7 doesn't name the blocked 0x005bf77c");
        CHECK(fake_log_contains("0x005bf7bc"), "13/7 doesn't name the blocked 0x005bf7bc");

        /* State 1 runs the base handler every frame, with no flag first. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 7);
        CHECK(fake_call_count == 4, "13/7 state 1 made %d calls, want 4", fake_call_count);
        CHECK(call_fn(0) == (int)FN_ONE_SHOT, "13/7 state 1 doesn't keep the one-shot call");
        CHECK(call_fn(1) == (int)FN_DATA_GET, "13/7 state 1 doesn't look the record up");
        CHECK(call_fn(2) == (int)FN_MODE && fake_calls[2].r1 == 1u,
              "13/7 state 1 doesn't set mode 1");
        CHECK(call_fn(3) == (int)FN_SET_ACTION && fake_calls[3].r1 == 0u
              && fake_calls[3].r2 == 3u && fake_calls[3].r3 == 2u,
              "13/7 state 1 doesn't start the base handler's action 3");
        CHECK(fake_calls[3].has_r4 && fake_calls[3].r4 == 0x7fu,
              "13/7's action setter lost MH4U's per-action stack argument");
        CHECK(ffrom(fake_mem_read32(work + WORK_POS_Y)) == 109.0f,
              "13/7's base handler doesn't add the record's float times the rate");
        CHECK(fake_mem_read8(work + WORK_SET) == 1, "13/7's base handler doesn't set the byte");
    }

    /* ── 13/9's block 0x00699c8c: motion 0x1a, then the flag into 0x00858b6c ────── */
    {
        const uint32_t enemy = 0x110000u, work = 0x111000u;
        prepare(enemy, work);
        fake_reset_calls();
        frame_with(enemy, work, 13, 9);
        CHECK(fake_call_count == 3, "13/9 state 0 made %d calls, want 3", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT && call_fn(1) == (int)FN_APPLY_FALL,
              "13/9 state 0 doesn't take the data float and the fall");
        CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == MOTION_1A
              && fake_calls[2].s0 == 0.0f, "13/9 state 0 doesn't start motion 0x1a at 0.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/9 doesn't advance its state");
        CHECK(fake_log_contains("0x005bf77c"), "13/9 doesn't name the blocked 0x005bf77c");

        /* State 1 waits for the finish flag before the base handler. */
        fake_reset_calls();
        fake_flag = 0;
        frame_with(enemy, work, 13, 9);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_FLAG,
              "13/9 state 1 doesn't wait for the finish flag");
        fake_reset_calls();
        fake_flag = 1;
        frame_with(enemy, work, 13, 9);
        CHECK(fake_call_count == 4, "13/9 state 1 (flag set) made %d calls, want 4",
              fake_call_count);
        CHECK(call_fn(0) == (int)FN_FLAG && call_fn(1) == (int)FN_DATA_GET
              && call_fn(2) == (int)FN_MODE && call_fn(3) == (int)FN_SET_ACTION
              && fake_calls[3].r2 == 3u,
              "13/9 state 1 doesn't fall into the base handler's action 3");
    }

    /* ── 13/8 0x0069031c, states 0 to 16 ─────────────────────────────────────────── */
    {
        const uint32_t enemy = 0x120000u, work = 0x121000u;
        prepare(enemy, work);
        fake_flag = 1;
        per_mode_on = 0;

        /* State 0: the data float, the fall and motion 0x1a at 0.0. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 3, "13/8 state 0 made %d calls, want 3", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT && call_fn(1) == (int)FN_APPLY_FALL
              && call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == MOTION_1A
              && fake_calls[2].s0 == 0.0f,
              "13/8 state 0 doesn't take the fall and start motion 0x1a at 0.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/8 doesn't advance to state 1");
        CHECK(fake_log_contains("0x005bf7bc") && fake_log_contains("0x005c0614"),
              "13/8 state 0 doesn't name the blocked aim calls");

        /* State 1: the blocked gate is taken as nonzero, then motion 0x1a again. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_MOTION
              && fake_calls[0].r1 == MOTION_1A,
              "13/8 state 1 doesn't advance through 0x005c6938 to motion 0x1a");
        CHECK(fake_mem_read8(work + WORK_STATE) == 2, "13/8 doesn't advance to state 2");
        CHECK(fake_log_contains("0x005c6938"), "13/8 doesn't name the blocked 0x005c6938");

        /* State 2 waits for the flag, then motion 0x1a. */
        fake_reset_calls();
        fake_flag = 0;
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_FLAG,
              "13/8 state 2 doesn't wait for the flag");
        fake_reset_calls();
        fake_flag = 1;
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_FLAG
              && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_1A,
              "13/8 state 2 doesn't start motion 0x1a after the flag");
        CHECK(fake_mem_read8(work + WORK_STATE) == 3, "13/8 doesn't advance to state 3");

        /* State 3: the 78.0 query, then motion 0x3d at 30.0. */
        fake_reset_calls();
        per_mode_on = 0;
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_PER_MODE
              && fake_calls[0].r1 == 0u && fake_calls[0].s0 == 78.0f
              && fake_calls[0].s1 == 0.0f,
              "13/8 state 3 doesn't run the 0/78.0/0 query");
        CHECK(fake_mem_read8(work + WORK_STATE) == 3, "13/8 state 3 advances without the query");
        fake_reset_calls();
        per_mode_on = 1;
        per_mode_value = 78.0f;
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_PER_MODE
              && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_3D
              && fake_calls[1].s0 == 30.0f,
              "13/8 state 3 doesn't start motion 0x3d at 30.0 after the query");
        CHECK(fake_mem_read8(work + WORK_STATE) == 4, "13/8 doesn't advance to state 4");
        CHECK(fake_log_contains("fifth stack argument"),
              "13/8 state 3 doesn't name the motion start's fifth argument");

        /* State 4: the blocked 0x280 gate, motion 0x1f. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_MOTION
              && fake_calls[0].r1 == MOTION_1F && fake_calls[0].s0 == 0.0f,
              "13/8 state 4 doesn't advance to motion 0x1f");
        CHECK(fake_mem_read8(work + WORK_STATE) == 5, "13/8 doesn't advance to state 5");

        /* State 5 and 6: the flag, then motions 0x20 and 0x1f. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_FLAG
              && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_20,
              "13/8 state 5 doesn't start motion 0x20 after the flag");
        CHECK(fake_mem_read8(work + WORK_STATE) == 6, "13/8 doesn't advance to state 6");
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
              && fake_calls[1].r1 == MOTION_1F,
              "13/8 state 6 doesn't start motion 0x1f after the flag");
        CHECK(fake_mem_read8(work + WORK_STATE) == 7, "13/8 doesn't advance to state 7");

        /* State 7: the 74.0 query, then motion 0x3d at 10.0. */
        fake_reset_calls();
        per_mode_on = 1;
        per_mode_value = 74.0f;
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_PER_MODE
              && fake_calls[0].s0 == 74.0f && call_fn(1) == (int)FN_MOTION
              && fake_calls[1].r1 == MOTION_3D && fake_calls[1].s0 == 10.0f,
              "13/8 state 7 doesn't start motion 0x3d at 10.0 after the 74.0 query");
        CHECK(fake_mem_read8(work + WORK_STATE) == 8, "13/8 doesn't advance to state 8");

        /* State 8: the 0x3ee gate, motion 0x213 (3U 0xdb). */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_MOTION
              && fake_calls[0].r1 == MOTION_DB && fake_calls[0].s0 == 0.0f,
              "13/8 state 8 doesn't advance to motion 0xdb (MH4U 0x213)");
        CHECK(fake_mem_read8(work + WORK_STATE) == 9, "13/8 doesn't advance to state 9");

        /* State 9: the 0x434 gate, motion 0x1b. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_MOTION
              && fake_calls[0].r1 == MOTION_1B,
              "13/8 state 9 doesn't advance to motion 0x1b");
        CHECK(fake_mem_read8(work + WORK_STATE) == 10, "13/8 doesn't advance to state 10");

        /* State 10: the 0x468 gate, motion 0x206 (3U 0xce). */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_MOTION
              && fake_calls[0].r1 == MOTION_CE,
              "13/8 state 10 doesn't advance to motion 0xce (MH4U 0x206)");
        CHECK(fake_mem_read8(work + WORK_STATE) == 11, "13/8 doesn't advance to state 11");

        /* State 11: the flag, motion 0x207 (3U 0xcf). */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_FLAG
              && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_CF,
              "13/8 state 11 doesn't start motion 0xcf (MH4U 0x207) after the flag");
        CHECK(fake_mem_read8(work + WORK_STATE) == 12, "13/8 doesn't advance to state 12");

        /* State 12: the 0x506 gate, motion 0x207 at 20.0 and the blocked 0x005bf77c. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 1 && call_fn(0) == (int)FN_MOTION
              && fake_calls[0].r1 == MOTION_CF && fake_calls[0].s0 == 20.0f,
              "13/8 state 12 doesn't start motion 0xcf at 20.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 13, "13/8 doesn't advance to state 13");
        CHECK(fake_log_contains("0x005bf77c"), "13/8 state 12 doesn't name 0x005bf77c");

        /* State 13: the flag, motion 0x1b at 7.0. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(0) == (int)FN_FLAG
              && call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_1B
              && fake_calls[1].s0 == 7.0f,
              "13/8 state 13 doesn't start motion 0x1b at 7.0 after the flag");
        CHECK(fake_mem_read8(work + WORK_STATE) == 14, "13/8 doesn't advance to state 14");

        /* State 14: the flag, motion 0x1b at 0.0. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
              && fake_calls[1].r1 == MOTION_1B && fake_calls[1].s0 == 0.0f,
              "13/8 state 14 doesn't start motion 0x1b at 0.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 15, "13/8 doesn't advance to state 15");

        /* State 15: the flag, motion 0x1c and the timer cleared. */
        fake_reset_calls();
        fake_mem_write32(work + WORK_TIMER, fbits(9.0f));
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 2 && call_fn(1) == (int)FN_MOTION
              && fake_calls[1].r1 == MOTION_1C,
              "13/8 state 15 doesn't start motion 0x1c");
        CHECK(fake_mem_read8(work + WORK_STATE) == 16, "13/8 doesn't advance to state 16");
        CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 0.0f,
              "13/8 state 15 doesn't clear the timer");

        /* State 16: the three queries, then the timer advanced by the frame delta. */
        fake_reset_calls();
        per_mode_on = 0;
        fake_mem_write32(work + WORK_TIMER, fbits(2.0f));
        fake_mem_write32(enemy + ENEMY_DELTA, fbits(0.5f));
        frame_with(enemy, work, 13, 8);
        CHECK(fake_call_count == 3, "13/8 state 16 made %d calls, want 3", fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].r1 == 0u
              && fake_calls[0].s0 == 86.0f && fake_calls[0].s1 == 0.0f,
              "13/8 state 16 doesn't run the first 0/86.0/0 query");
        CHECK(call_fn(1) == (int)FN_PER_MODE && fake_calls[1].r1 == 0u
              && fake_calls[1].s0 == 86.0f && fake_calls[1].s1 == 0.0f,
              "13/8 state 16 doesn't run the second 0/86.0/0 query");
        CHECK(call_fn(2) == (int)FN_PER_MODE && fake_calls[2].r1 == 3u
              && fake_calls[2].s0 == 86.0f && fake_calls[2].s1 == 204.0f,
              "13/8 state 16 doesn't run the 3/86.0/204.0 query");
        CHECK(ffrom(fake_mem_read32(work + WORK_TIMER)) == 2.5f,
              "13/8 state 16 doesn't advance the timer by the frame delta");
        CHECK(fake_mem_read8(work + WORK_STATE) == 16, "13/8 state 16 advanced its state");
        CHECK(fake_log_contains("0x0016052c"), "13/8 doesn't name the blocked 0x0016052c");
        CHECK(fake_log_contains("0x00161798"), "13/8 doesn't name the blocked 0x00161798");
        CHECK(fake_log_contains("0x005aef18"), "13/8 doesn't name the blocked 0x005aef18");
    }

    if (failures) {
        fprintf(stderr, "%d failures\n", failures);
        return 1;
    }
    printf("cat13c: ok\n");
    return 0;
}
