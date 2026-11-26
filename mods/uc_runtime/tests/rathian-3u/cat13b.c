/*
 * cat13b.c: category 13 part 2's fake-host test — 13/5 and 13/6.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-3u/ and builds it as tests/family-<stem>, so a slice adds its test file and
 * edits nothing shared. The shell's test (tests/test_rathian_3u.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the two units'
 * call sequences on the fake host.
 *
 * The expected addresses, offsets, frame values and motion numbers come from
 * tests/rathian-3u/host.h and this file's own constants, not from the module, so a change in
 * a handler fails the test instead of moving the expectation with it. A motion number is
 * MH4U's `file << 8 | slot` of the source's `file * 100 + slot`.
 *
 * 13/6's state progression is gated by 0x005c6938, a #55-blocked helper the port does not
 * call (it takes the result as 0). The test therefore writes the state byte for the states
 * the gate would reach, so their bodies' calls and frame values are checked too; the gate's
 * own log line is checked where it is reached.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The MH4U engine functions the family calls. */
#define FN_MOTION       0x0094e318u
#define FN_DATA_FLOAT   0x0093d870u
#define FN_APPLY_FALL   0x0092e99cu
#define FN_PER_MODE     0x0091aae4u
#define FN_TAIL0        0x00914dc4u

#define MOTION_13_5   ((0u << 8) | 0x13u)
#define MOTION_13_6_0 ((0u << 8) | 0x1au)
#define MOTION_13_6_2 ((0u << 8) | 0x3du)
#define MOTION_13_6_4 ((2u << 8) | 0x00u)
#define MOTION_13_6_5 ((0u << 8) | 0x13u)
#define MOTION_13_6_6 ((0u << 8) | 0x12u)
#define MOTION_13_6_7 ((0u << 8) | 0x29u)
#define MOTION_13_6_8 ((0u << 8) | 0x43u)
#define MOTION_13_6_9 ((0u << 8) | 0x1au)

static float fake_data = 1.0f;
static int query_on;
static int query_all;
static uint32_t query_r1;
static float query_s0;
static float query_s1;

/* What the engine answers the two units' calls. A query returns 1 only for the one
 * (mode, s0, s1) the section asked for, or for every query when query_all is set. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)user;
    switch (fn) {
    case FN_PER_MODE:
        if (query_all) {
            return (FakeResult){1u, 0.0f};
        }
        if (query_on && r[1] == query_r1 && s[0] == query_s0 && s[1] == query_s1) {
            return (FakeResult){1u, 0.0f};
        }
        return (FakeResult){0u, 0.0f};
    case FN_DATA_FLOAT:
        return (FakeResult){0u, fake_data};
    default:
        return (FakeResult){0u, 0.0f};
    }
}

static void query_for(uint32_t mode, float s0, float s1) {
    query_on = 1;
    query_all = 0;
    query_r1 = mode;
    query_s0 = s0;
    query_s1 = s1;
}

static void query_none(void) {
    query_on = 0;
    query_all = 0;
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

    /* ── 0x0068f818: 13/5 — motion 0x13 at 6.0, then the query/effect choreography ─ */
    {
        const uint32_t enemy = 0x100000u, work = 0x101000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        fake_clear_log();
        query_none();
        frame_with(enemy, work, 13, 5);
        CHECK(fake_call_count == 2, "13/5 state 0 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_MODE && fake_calls[0].r1 == 0u,
              "13/5 state 0 doesn't set mode 0");
        CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_13_5
              && fake_calls[1].s0 == 6.0f,
              "13/5 state 0 doesn't start motion 0x13 at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/5 doesn't advance its state");

        /* State 1, every query false: the twelve queries in source order, no effect. */
        fake_reset_calls();
        query_none();
        frame_with(enemy, work, 13, 5);
        CHECK(fake_call_count == 12, "13/5 state 1 (all false) made %d calls, want 12",
              fake_call_count);
        {
            static const uint32_t modes[12] =
                {0u, 0u, 0u, 3u, 0u, 0u, 0u, 0u, 3u, 3u, 0u, 3u};
            static const float s0[12] =
                {92.0f, 262.0f, 96.0f, 136.0f, 156.0f, 190.0f, 386.0f, 262.0f,
                 344.0f, 398.0f, 434.0f, 458.0f};
            static const float s1[12] =
                {0.0f, 0.0f, 0.0f, 152.0f, 0.0f, 0.0f, 0.0f, 0.0f,
                 368.0f, 426.0f, 0.0f, 478.0f};
            for (int i = 0; i < 12; i++) {
                CHECK(call_fn(i) == (int)FN_PER_MODE, "13/5's query %d isn't 0x0091aae4", i);
                CHECK(fake_calls[i].r1 == modes[i] && fake_calls[i].s0 == s0[i]
                      && fake_calls[i].s1 == s1[i],
                      "13/5's query %d isn't (mode %u, %g, %g)", i, modes[i], s0[i], s1[i]);
            }
        }
        CHECK(!fake_log_contains("0x0016052c") && !fake_log_contains("0x0016669c")
              && !fake_log_contains("0x00847798"),
              "13/5 names an effect it never reached");

        /* State 1, the 92.0 query true: effect A and the rest in order. */
        fake_reset_calls();
        query_for(0u, 92.0f, 0.0f);
        frame_with(enemy, work, 13, 5);
        CHECK(fake_call_count == 11, "13/5 state 1 (92.0) made %d calls, want 11",
              fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].s0 == 92.0f,
              "13/5's 92.0 query is missing");
        CHECK(call_fn(1) == (int)FN_PER_MODE && fake_calls[1].s0 == 96.0f,
              "13/5 skips the 92.0-true path's next query");
        CHECK(fake_log_contains("0x0016052c"), "13/5 doesn't name the blocked 0x0016052c");

        /* State 1, the 156.0 query true: the 156/190/386 short circuit still reaches the
         * 0x33 effect and then the later queries. */
        fake_reset_calls();
        query_for(0u, 156.0f, 0.0f);
        frame_with(enemy, work, 13, 5);
        CHECK(fake_call_count == 10, "13/5 state 1 (156.0) made %d calls, want 10",
              fake_call_count);
        CHECK(call_fn(3) == (int)FN_PER_MODE && fake_calls[3].s0 == 136.0f,
              "13/5's 136.0 query is missing");
        CHECK(call_fn(4) == (int)FN_PER_MODE && fake_calls[4].s0 == 156.0f,
              "13/5's 156.0 query is missing");

        /* State 1, the 262.0 query true (alone): effect A and the second 0x0016669c. */
        fake_reset_calls();
        query_for(0u, 262.0f, 0.0f);
        frame_with(enemy, work, 13, 5);
        CHECK(fake_call_count == 12, "13/5 state 1 (262.0) made %d calls, want 12",
              fake_call_count);
        CHECK(fake_calls[0].s0 == 92.0f && fake_calls[1].s0 == 262.0f,
              "13/5's q92/q262 pair is out of order");
        CHECK(fake_log_contains("0x0016669c"), "13/5 doesn't name the blocked 0x0016669c");

        /* State 1, all queries true: every query short circuit and all three blocked
         * helpers. */
        fake_reset_calls();
        query_none();
        query_all = 1;
        frame_with(enemy, work, 13, 5);
        CHECK(fake_call_count == 9, "13/5 state 1 (all true) made %d calls, want 9",
              fake_call_count);
        CHECK(fake_log_contains("0x0016052c") && fake_log_contains("0x0016669c")
              && fake_log_contains("0x00847798"),
              "13/5 doesn't name all of its blocked helpers");
        CHECK(fake_calls[0].s0 == 92.0f && fake_calls[1].s0 == 96.0f
              && fake_calls[2].s0 == 136.0f && fake_calls[3].s0 == 156.0f
              && fake_calls[4].s0 == 262.0f && fake_calls[5].s0 == 344.0f
              && fake_calls[6].s0 == 398.0f && fake_calls[7].s0 == 434.0f
              && fake_calls[8].s0 == 458.0f,
              "13/5's all-true query order is wrong");
    }

    /* ── 0x0068fcc0: 13/6 — motion 0x1a at 0.0, then the eleven gated states ─────── */
    {
        const uint32_t enemy = 0x110000u, work = 0x111000u;
        spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);
        fake_reset_calls();
        fake_data = 1.0f;
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 3, "13/6 state 0 made %d calls, want 3", fake_call_count);
        CHECK(call_fn(0) == (int)FN_DATA_FLOAT, "13/6 state 0 doesn't read the data float");
        CHECK(call_fn(1) == (int)FN_APPLY_FALL && fake_calls[1].s0 == 1.0f,
              "13/6 state 0 doesn't advance the fall by the data float");
        CHECK(call_fn(2) == (int)FN_MOTION && fake_calls[2].r1 == MOTION_13_6_0
              && fake_calls[2].s0 == 0.0f && fake_calls[2].s1 == 0.0f,
              "13/6 state 0 doesn't start motion 0x1a at 0.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/6 doesn't advance its state");
        CHECK(fake_log_contains("0x005c0614"), "13/6 doesn't name the blocked 0x005c0614");

        /* State 1: the 0x5c6938 gate is blocked and returns 0, so the state stays. */
        fake_reset_calls();
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 0, "13/6 state 1 made %d calls, want 0", fake_call_count);
        CHECK(fake_mem_read8(work + WORK_STATE) == 1, "13/6 passes the blocked gate");
        CHECK(fake_log_contains("0x005c6938"), "13/6 doesn't name the blocked 0x005c6938");

        /* State 3: the 90.0 query true advances to state 4 and clears the aim block. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 3u);
        query_for(0u, 90.0f, 0.0f);
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 1, "13/6 state 3 made %d calls, want 1", fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].r1 == 0u
              && fake_calls[0].s0 == 90.0f,
              "13/6 state 3 doesn't run the 90.0 query");
        CHECK(fake_mem_read8(work + WORK_STATE) == 4, "13/6 state 3 doesn't advance");
        CHECK(fake_log_contains("0x005c34c0") && fake_log_contains("0x005c3f88")
              && fake_log_contains("0x005c0614"),
              "13/6 state 3 doesn't name its blocked helpers");

        /* State 5: the 56.0 query and the (0, 0x17) tail run, then the blocked gate
         * stops the state change. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 5u);
        query_for(0u, 56.0f, 0.0f);
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 2, "13/6 state 5 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].s0 == 56.0f,
              "13/6 state 5 doesn't run the 56.0 query");
        CHECK(call_fn(1) == (int)FN_TAIL0 && fake_calls[1].r1 == 0u
              && fake_calls[1].r2 == 0x17u,
              "13/6 state 5 doesn't make the (0, 0x17) tail");
        CHECK(fake_mem_read8(work + WORK_STATE) == 5, "13/6 passes the blocked 0x41a gate");
        CHECK(fake_log_contains("0x005c6938"), "13/6 state 5 doesn't name the gate");

        /* State 4: the aim helpers run before the gate, then the gate returns 0; the
         * motion 0xc8 and its start frame are unreachable until #55 traces the gate. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 4u);
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 0, "13/6 state 4 made %d calls, want 0", fake_call_count);
        CHECK(fake_mem_read8(work + WORK_STATE) == 4, "13/6 passes the blocked 0x3a2 gate");
        CHECK(fake_log_contains("0x005c34c0") && fake_log_contains("0x005c3f88")
              && fake_log_contains("0x005c6938"),
              "13/6 state 4 doesn't name its blocked helpers");

        /* State 8: the 114.0 query true advances and starts motion 0x43 at 6.0. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 8u);
        query_for(0u, 114.0f, 0.0f);
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 2, "13/6 state 8 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].s0 == 114.0f,
              "13/6 state 8 doesn't run the 114.0 query");
        CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_13_6_8
              && fake_calls[1].s0 == 6.0f,
              "13/6 state 8 doesn't start motion 0x43 at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 9, "13/6 state 8 doesn't advance");

        /* State 9: the blocked trajectory, the 48.0 query and motion 0x1a at 6.0. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 9u);
        query_for(0u, 48.0f, 0.0f);
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 2, "13/6 state 9 made %d calls, want 2", fake_call_count);
        CHECK(call_fn(0) == (int)FN_PER_MODE && fake_calls[0].s0 == 48.0f,
              "13/6 state 9 doesn't run the 48.0 query");
        CHECK(call_fn(1) == (int)FN_MOTION && fake_calls[1].r1 == MOTION_13_6_9
              && fake_calls[1].s0 == 6.0f,
              "13/6 state 9 doesn't start motion 0x1a at 6.0");
        CHECK(fake_mem_read8(work + WORK_STATE) == 10, "13/6 state 9 doesn't advance");
        CHECK(fake_log_contains("0x005c7270"), "13/6 state 9 doesn't name the blocked 0x5c7270");

        /* State 10: the trajectory setup alone. */
        fake_reset_calls();
        fake_mem_write8(work + WORK_STATE, 10u);
        frame_with(enemy, work, 13, 6);
        CHECK(fake_call_count == 0, "13/6 state 10 made %d calls, want 0", fake_call_count);
        CHECK(fake_log_contains("0x005c34c0") && fake_log_contains("0x005c7270"),
              "13/6 state 10 doesn't name its blocked helpers");
    }

    /* ── every id in the slice runs the module's handler ──────────────────────────── */
    {
        static const int ids[] = {5, 6};
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

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 13/5 runs its query/effect sequence and 13/6 its gated states\n");
    return 0;
}
