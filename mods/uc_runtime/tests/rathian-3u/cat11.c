/*
 * cat11.c: category 11 on the fake host — 11/0, 11/5, 11/15, 11/26 and 11/28, the shared
 * wrapper 0x00687e88 and the base-class handler 0x0084d864.
 *
 * One test program per action family: make test discovers every .c file under tests/rathian-3u/
 * and builds it as tests/family-<stem>, so a slice adds its test file and edits nothing shared.
 * The shell's test (tests/test_rathian_3u.c) covers the factory association, the routing, the
 * ready line and the self-test; this one drives the five ids' call sequences.
 *
 * The expected addresses and constants are written here and in tests/rathian-3u/host.h, not
 * read from the module, so a change in a handler fails the test instead of moving the
 * expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* The work-block fields category 11 reads beyond host.h's list (MH4U's offsets). */
#define WORK_MODE   0x01c8u  /* 3U +0x1: the tail's mode byte */
#define WORK_HEIGHT 0x001cu  /* 3U +0x1c (this+0x1a64): the 45.0/0.5 accumulator */
#define ENEMY_FRAME 0x0014u  /* 3U +0x14: the frame delta */

/* MH4U's category-11 shared handler and its own list. */
#define FN_SHARED_11 0x00919788u /* [0x008326dc] */
#define MH4U_LIST_11 0x00fd2360u

/* 0x0084d864's frame values. */
#define HEIGHT_CEILING 45.0f
#define HEIGHT_HALF    0.5f

/* Check one guest call's function. */
#define CALL(i, want) do { \
    CHECK(fake_calls[i].fn == (want), "call %d is 0x%08x, want 0x%08x", (i), \
          (unsigned)fake_calls[i].fn, (unsigned)(want)); \
} while (0)

static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)fn;
    (void)r;
    (void)s;
    (void)user;
    return (FakeResult){0, 0.0f};
}

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    const uint32_t enemy = 0x30000u, work = 0x40000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_3U, 1);

    /* ── 11/0: the shared handler with MH4U's own list and mode 0 ────────────────────── */
    fake_reset_calls();
    frame_with(enemy, work, 11, 0);
    CHECK(fake_call_count == 1, "11/0 made %d calls, want 1", fake_call_count);
    CALL(0, FN_SHARED_11);
    CHECK(fake_calls[0].r1 == MH4U_LIST_11 && fake_calls[0].r2 == 0,
          "11/0 doesn't pass MH4U's own list and mode 0");
    CHECK(fake_mem_read32(work + WORK_HEIGHT) == 0u,
          "11/0's tail must return at its index test");

    /* 11/5: the same handler with mode 1. */
    fake_reset_calls();
    frame_with(enemy, work, 11, 5);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_SHARED_11
          && fake_calls[0].r2 == 1, "11/5 doesn't pass mode 1");

    /* 11/15 and 11/26: mode 0, and their tails return. */
    fake_reset_calls();
    frame_with(enemy, work, 11, 15);
    CHECK(fake_call_count == 1 && fake_calls[0].r1 == MH4U_LIST_11
          && fake_calls[0].r2 == 0, "11/15 doesn't run the shared handler with mode 0");
    fake_reset_calls();
    frame_with(enemy, work, 11, 26);
    CHECK(fake_call_count == 1 && fake_calls[0].r1 == MH4U_LIST_11
          && fake_calls[0].r2 == 0, "11/26 doesn't run the shared handler with mode 0");

    /* ── 11/28: the shared handler, then 0x0084d864's own branch ────────────────────── */
    fake_reset_calls();
    frame_with(enemy, work, 11, 28);           /* the mode byte is 0: the tail returns */
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_SHARED_11
          && fake_calls[0].r2 == 0, "11/28 doesn't run the shared handler with mode 0");

    fake_mem_write8(work + WORK_MODE, 1);
    fake_mem_write32(work + WORK_HEIGHT, fbits(10.0f));
    fake_mem_write32(enemy + ENEMY_FRAME, fbits(2.0f));
    fake_reset_calls();
    frame_with(enemy, work, 11, 28);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_SHARED_11,
          "11/28's tail made a guest call, want 0");
    CHECK(ffrom(fake_mem_read32(work + WORK_HEIGHT)) == 10.0f + 2.0f * HEIGHT_HALF,
          "11/28 doesn't advance the 45.0/0.5 height");
    CHECK(fake_log_contains("0x00a37b3c"), "11/28 doesn't log the blocked 0x00a37b3c");
    CHECK(fake_log_contains("this+0x1a64"), "11/28 doesn't log the unverified height field");

    /* Above 45.0 the step calls 0x008477bc, which is not carried: the height stays. */
    fake_mem_write32(work + WORK_HEIGHT, fbits(HEIGHT_CEILING + 1.0f));
    fake_reset_calls();
    frame_with(enemy, work, 11, 28);
    CHECK(ffrom(fake_mem_read32(work + WORK_HEIGHT)) == HEIGHT_CEILING + 1.0f,
          "11/28's step above 45.0 must not advance the height");
    CHECK(fake_log_contains("0x008477bc"), "11/28 doesn't log the blocked 0x008477bc");

    /* A category-11 index the source does not have falls through to the module's pending log. */
    fake_reset_calls();
    frame_with(enemy, work, 11, 1);
    CHECK(fake_call_count == 0 && fake_original_count == 1,
          "11/1 isn't left to MH4U's dispatcher");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: category 11 makes its calls across the five ids\n");
    return 0;
}
