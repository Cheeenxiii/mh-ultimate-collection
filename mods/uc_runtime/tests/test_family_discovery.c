/*
 * test_family_discovery.c: a family file added to the directory, with no other edit, is
 * discovered by the build and routes its action pair.
 *
 * The module's family list is not written by hand: tools/gen_families.py discovers
 * the .c files in src/monsters/rathian-3u/ and the build writes families.h. This test is the same step with
 * a directory that holds only tests/fixtures/rathian-3u/probe.c: the generator wrote
 * tests/family-probe/families.h, and the test checks the list names the probe family and calls
 * the dispatch entry the list found. That is the guarantee a slice relies on — add the file,
 * nothing else.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <stdio.h>

#include "families.h"
#include "family.h"

/* The probe family's counter (tests/fixtures/rathian-3u/probe.c). */
extern int mhuc_3u_probe_runs;

static int failures;

static void fail(const char *text) {
    fprintf(stderr, "FAIL: %s\n", text);
    failures++;
}

int main(void) {
    if (MHUC_3U_FAMILY_COUNT != 1) {
        fail("the generated list doesn't hold the one family file in the directory");
        return 1;
    }
    if (mhuc_3u_families[0] != &mhuc_3u_family_probe) {
        fail("the generated list doesn't name the probe family");
        return 1;
    }
    if (mhuc_3u_families[0]->name == NULL || mhuc_3u_families[0]->dispatch == NULL) {
        fail("the discovered family has no name or dispatch entry");
        return 1;
    }
    if (mhuc_3u_probe_runs != 0) {
        fail("the probe ran before it was called");
    }
    if (mhuc_3u_families[0]->dispatch(NULL, 0, 0, 240, 1) != 1) {
        fail("the discovered family doesn't route its own pair");
    }
    if (mhuc_3u_probe_runs != 1) {
        fail("the discovered family's dispatch entry didn't run");
    }
    if (mhuc_3u_families[0]->dispatch(NULL, 0, 0, 240, 0) != 0) {
        fail("the discovered family claims a pair it doesn't carry");
    }
    if (failures) {
        return 1;
    }
    printf("ok: a newly added family file is discovered and routes its pair, with no other "
           "edit\n");
    return 0;
}
