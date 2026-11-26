/*
 * act12_1_3.c: the 12/1 to 12/3 family's fake-host test — the target points and the shared
 * handlers.
 *
 * One test program per action family: make test discovers every .c file under
 * tests/rathian-gu/ and builds it as tests/family-gu-<stem>, so a slice adds its test file
 * and edits nothing shared. The shell's test (tests/test_module.c) covers the factory
 * association, the routing, the ready line and the self-test; this one drives the blocks'
 * call sequences on the fake host.
 *
 * The expected addresses, target points and frame values come from tests/rathian-gu/host.h,
 * not from the module, so a change in a handler fails the test instead of moving the
 * expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

/* What the engine answers the chain's calls: 12/1 falls into 3/98's handler, so the data
 * value, the speed setter and the finish flag answer as they do there. */
static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)r;
    (void)s;
    (void)user;
    switch (fn) {
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};
    case FN_SET_SPEED:
    case FN_FLAG:
        return (FakeResult){1, 0.0f};
    default:
        return (FakeResult){0, 0.0f};
    }
}

int main(void) {
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }

    const uint32_t enemy = 0x50000u, work = 0x60000u;
    spawn(enemy, work, MHUC_MONSTER_ID_RATHIAN_GU, 1);

    /* ── 12/3: target points and MH4U's 3/9 handler ── */
    fake_reset_calls();
    fake_s[0] = 1.0f; fake_s[1] = 2.0f; fake_s[2] = 3.0f; fake_s[3] = 4.0f;
    frame_with(enemy, work, 12, 3);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_HANDLER_3_9
          && fake_calls[0].r1 == 1 && fake_calls[0].r2 == 0,
          "12/3 doesn't call MH4U's 3/9 handler with r1=1, r2=0");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 0u)) == 1.0f, "12/3 target +0");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 4u)) == 3.0f, "12/3 target +4");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 8u)) == 4.0f, "12/3 target +8");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 12u)) == 2.0f, "12/3 target +12");

    /* ── 12/2: MH4U's shared 3/12 handler ── */
    fake_reset_calls();
    frame_with(enemy, work, 12, 2);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_HANDLER_3_12 && fake_calls[0].r1 == 0,
          "12/2 doesn't call MH4U's shared 3/12 handler with r1=0");

    /* ── 12/1: fixed target points, then 3/98's handler ── */
    fake_reset_calls();
    frame_with(enemy, work, 12, 1);
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 0u)) == 5477.0f, "12/1 target +0");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 4u)) == 3000.0f, "12/1 target +4");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 8u)) == 4892.0f, "12/1 target +8");
    CHECK(ffrom(fake_mem_read32(work + WORK_TARGET + 12u)) == 2.0f,
          "12/1 target +12 is the caller's s1");
    CHECK(fake_call_count >= 4 && fake_calls[0].fn == FN_DATA_FLOAT,
          "12/1 doesn't run the 3/98 handler");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: 12/1 to 12/3 write their target points and reach the shared handlers\n");
    return 0;
}
