/*
 * probe.c: a family the module does not ship, for the family-discovery test.
 *
 * The test puts this file in a directory of its own beside the generated families.h and checks
 * that the generator discovered it and that its dispatch entry runs its pair. Dropping a file
 * into src/monsters/rathian-3u/ is what a slice does, so the test is the same step with a
 * family that handles a made-up pair (category 240, index 1) and counts its runs.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

int mhuc_3u_probe_runs;

static int dispatch_probe(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    (void)call;
    (void)enemy;
    (void)work;
    if (category != 240 || index != 1) {
        return 0;
    }
    mhuc_3u_probe_runs++;
    return 1;
}

const MhucFamily mhuc_3u_family_probe = {
    "probe", 0, dispatch_probe, 0,
};
