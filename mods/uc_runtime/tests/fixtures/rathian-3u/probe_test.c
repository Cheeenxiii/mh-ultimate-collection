/*
 * probe_test.c: a family test the module does not ship, for the family tests' discovery.
 *
 * The test-list discovery target puts this file in a directory of its own (as a slice puts
 * tests/rathian-3u/<family>.c in the real one), lets make discover and build it, and runs it.
 * It is a real family test — it initialises the fake host and checks the module's ready line —
 * so a test that builds and runs proves the discovery end to end, not just that a name was
 * listed.
 *
 * Licence: GPL-3.0-or-later.
 */
#include "host.h"

int main(void) {
    fake_set_config("selftest", "1");
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    fake_frame();
    CHECK(fake_log_contains("ready: translating 6 of 3U Rathian's 191 actions on monster 125"),
          "the probe family test didn't reach the module");
    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: the probe family test was discovered and ran\n");
    return 0;
}
