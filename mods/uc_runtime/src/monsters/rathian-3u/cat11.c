/*
 * cat11.c: 3U Rathian's category 11 — 11/0, 11/5, 11/15, 11/26 and 11/28, on the short
 * case-block wrappers 0x00687e6c, 0x00687e7c, 0x00687e98, 0x00687ea8 and 0x00687eb8, the
 * shared wrapper 0x00687e88 and the base-class handler 0x0084d864.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending. The handlers, their frame values and their call
 * order are the ones issue #225 translated.
 *
 * Every id's case block passes a source list, a mode in r2 and the action index in r3 to the
 * shared handler 0x008326dc (a four-byte veneer to 0x008326e0), then falls into 0x0084d864.
 * The shared handler is base-class code and MH4U's counterpart is 0x00919788, which MH4U's
 * own category-11 case (0x006e9d9c) runs with its own list 0x00fd2360 and the same mode; the
 * source's r3 is ignored by 0x008326e0. Under decision 0002's 2026-11-26 amendment the whole
 * path is reimplemented here:
 *   11/0    list 0x00c4d800, r2 = 0 -> 0x0084d864
 *   11/5    list 0x00c4d818, r2 = 1 -> 0x0084d864 (MH4U has no 11/5)
 *   11/15   list 0x00c4d850, r2 = 0 -> 0x0084d864 (MH4U has no 11/15)
 *   11/26   list 0x00c4d868, r2 = 0 -> 0x0084d864 (MH4U has no 11/26)
 *   11/28   list 0x00c4d880, r2 = 0 -> 0x0084d864 (MH4U has no 11/28)
 * The source's lists are her data and are not carried; the port passes MH4U's own list, the
 * same substitution the category 0 base handlers make for the action setter's per-action
 * value (#55's open item).
 *
 * 0x0084d864 is base-class code, reimplemented here (0002's second amendment). For the four
 * ids other than 11/28 it returns at its first test, so the wrapper's work is the shared
 * handler. For 11/28 its own steps run on work+0xe0 (index 0x1c) and work+1, then a bit test
 * (0x00a37b3c), a 45.0/0.5 float step on this+0x1a64, and 0x008477bc when the float is over
 * 45.0. Three parts of that branch have no mapped MH4U field or counterpart, named in the log
 * and in the runtime's README: the bit test's object field, this+0x1a64, and 0x008477bc.
 * The port takes the source's nonzero path for the bit test so the action cannot stall.
 *
 * Neither family here falls into category 0's three base handlers.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U); the field map is in
 * the runtime's README.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <string.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_MODE   0x01c8u  /* 3U +0x1: the tail's mode byte (the map's unverified proposal) */
#define WORK_INDEX  0x01cbu  /* 3U +0xe0: the current index */
#define WORK_HEIGHT 0x001cu  /* 3U +0x1c (this+0x1a64): the 45.0/0.5 accumulator, see below */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_SHARED_11 0x00919788u /* [0x008326dc] category 10/11's shared handler (list in r1,
                                  * mode in r2) */

/* MH4U's own list for category 11 (0x006e9d9c's default, which its 11/0 uses). The source's
 * per-id lists are her data and are not carried. */
#define MH4U_LIST_11 0x00fd2360u

/* The frame delta is at this+0x14 in both games. */
#define ENEMY_FRAME 0x0014u

/* 0x0084d864's frame values: the float step's ceiling and the half it advances by. */
#define HEIGHT_CEILING 0x42340000u  /* 45.0f, compared as the source compares its bits */
#define HEIGHT_HALF    0.5f

/* The index 0x0084d864's own branch runs for (11/28), and the source's tail flag. */
#define INDEX_11_28 0x1cu

/* ── the base-class handler's open items ────────────────────────────────────────────── */

static int bit_test_logged;
static int height_logged;
static int effect_logged;

/* 3U 0x00a37b3c tests bit 4 of the halfword at this+0x228+6. The object field has no mapped
 * MH4U offset; the port takes the source's nonzero path so the action cannot stall. */
static void log_bit_test(void) {
    if (bit_test_logged) {
        return;
    }
    bit_test_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "11/28: 3U's 0x00a37b3c (bit 4 of the halfword at this+0x22e) is not carried; "
             "the field has no mapped MH4U offset, and the port takes its nonzero path");
}

/* 3U this+0x1a64 is a float 0x1c bytes past the work pointer, and the reference has no
 * confirmed MH4U offset for it; the port keeps it at MH4U's work+0x1c as a stopgap. */
static void log_height(void) {
    if (height_logged) {
        return;
    }
    height_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "11/28: 3U's this+0x1a64 (a float at work+0x1c) has no confirmed MH4U offset; "
             "the port keeps it at MH4U's work+0x1c until the field map settles it");
}

/* 3U 0x008477bc (the record's +0xa0 effect/attack step) has no confirmed MH4U counterpart;
 * the port logs it once and leaves it out. */
static void log_effect(void) {
    if (effect_logged) {
        return;
    }
    effect_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "11/28: 3U's 0x008477bc (the record's +0xa0 effect/attack step) is not carried; "
             "no MH4U counterpart for its steps was found, so the step above 45.0 is left out");
}

/* ── the base-class handler 0x0084d864 and the shared wrapper ───────────────────────── */

/* 3U 0x0084d864(this), the tail every category-11 case block falls into. Only 11/28's index
 * goes past its first test:
 *   - the index is 0x1c, and work+1 is nonzero;
 *   - 0x00a37b3c's bit test (unmapped, taken nonzero);
 *   - this+0x1a64 (work+0x1c, the port's stopgap): while the float's bits are not above
 *     45.0f's, advance it by 0.5 x the frame delta; above it, 0x008477bc (not carried).
 */
static void run_11_tail(MH4UCall *call, uint32_t enemy, uint32_t work, int index) {
    if (index != INDEX_11_28) {
        return;
    }
    if (mhuc_read8(call, work + WORK_MODE) == 0u) {
        return;
    }
    log_bit_test();
    log_height();
    const float height = mhuc_f32(call, work + WORK_HEIGHT);
    uint32_t bits;
    memcpy(&bits, &height, sizeof bits);
    if ((int32_t)bits > (int32_t)HEIGHT_CEILING) {
        log_effect();
        return;
    }
    mhuc_put_f32(call, work + WORK_HEIGHT,
                 height + mhuc_f32(call, enemy + ENEMY_FRAME) * HEIGHT_HALF);
}

/* Every category-11 case block: the shared handler with one of MH4U's own lists and the
 * source's mode, then 0x0084d864's tail. */
static void run_11(MH4UCall *call, uint32_t enemy, uint32_t work, int index) {
    const uint32_t mode = index == 5 ? 1u : 0u;
    mhuc_call(call, FN_SHARED_11, enemy, MH4U_LIST_11, mode, 0u);
    run_11_tail(call, enemy, work, index);
}

/* ── the family's dispatch and self-test ────────────────────────────────────────────── */

/* Runs category 11's handler for the pair, or returns 0 so the module's dispatch can try the
 * next family. The source's category-11 case block has the five ids 0, 5, 15, 26 and 28. */
static int dispatch_cat11(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    if (category != 11) {
        return 0;
    }
    switch (index) {
    case 0: case 5: case 15: case 26: case 28:
        run_11(call, enemy, work, index);
        return 1;
    default:
        return 0;
    }
}

/* What this family carries: the five ids, the shared handler, the base-class tail and the
 * three open items of 11/28's branch. The module's self-test calls this with the others'. */
static void self_test_cat11(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 5 of the 191 actions: 11/0, 11/5, 11/15, 11/26 and 11/28 <- the "
             "wrapper 0x00687e88 and the base-class 0x0084d864 (the shared handler, then "
             "11/28's 45.0/0.5 step); 11/5, 11/15, 11/26 and 11/28 are ids MH4U has no action "
             "for");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine call is MH4U's: category 11's shared handler 0x%08x with "
              "MH4U's own list 0x%08x", (unsigned)FN_SHARED_11, (unsigned)MH4U_LIST_11);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: the work block *(this+0x1a48) -> *(this+0xe28), "
             "+0x1 -> +0x1c8 (unverified), +0xe0 -> +0x1cb, this+0x1a64 -> work+0x1c "
             "(stopgap); open: 0x00a37b3c's bit, this+0x1a64 and 0x008477bc of 11/28's branch");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat11 = {
    "cat11", 5, dispatch_cat11, self_test_cat11,
};
