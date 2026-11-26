/*
 * cat0.c: 3U Rathian's category 0 — 0/0, 0/1, 0/2, 0/3, 0/4 and 0/6, and the three
 * base-class handlers they reach.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending. The handlers, their offsets and their engine calls
 * are the ones issue #216 translated; moving them here changed no behaviour.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The state byte is the
 * game's own (MH4U work+0x144), because the source's category-0 case blocks share it across
 * the six ids. The runtime's README carries the field map and the engine-call map, and the
 * three open items: 0x008412cc, 0x00833b2c's 0.5 factor, and 0/0's second delay field.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE        0x0144u  /* 3U +0x5:  the action's state byte, shared by category 0 */
#define WORK_CATEGORY     0x01cau  /* 3U +0xdf: the current category */
#define WORK_MODE         0x01c8u  /* 3U +0xdc: the mode byte */
#define WORK_SET          0x01dcu  /* 3U +0xf2: "the action was set" */
#define WORK_COUNTDOWN    0x01d4u  /* 3U +0x28: the 0/0 delay (MH4U's own 0/0 uses it) */
#define WORK_VERTICAL     0x0180u  /* 3U +0x68: the vertical step 0/6 advances */
#define WORK_0_2_STATE    0x051cu  /* 3U +0x941: the state the 0/2 base handler tests */
#define WORK_FLAGS        0x01b4u  /* 3U +0x8c: its bit 0x40 */
#define WORK_OTHER_STATE  0x034cu  /* 3U +0x381: the other state byte */
#define WORK_KIND         0x01c0u  /* 3U +0x3: the data record's kind/id */
#define WORK_DATA_INDEX   0x797eu  /* 3U +0xa: the data record's index */
#define WORK_RATE         0x01b8u  /* 3U +0x90: the fall rate */
#define WORK_RATE_2       0x01bcu  /* 3U +0x94: its second factor */
#define WORK_POS_Y        0x019cu  /* 3U +0x3c: the fall height the data float advances */
#define WORK_APPLIED      0x01c7u  /* 3U +0xd9: 0x00833b2c's "applied" byte */

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_MODE        0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_REQUEST     0x0094f408u /* [0x0082a878] set the next motion/state (r1, s0, s1) */
#define FN_FLAG        0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_VERTICAL    0x00915d44u /* [0x00833b2c] advance the vertical value by s0 * delta */
#define FN_DATA_FLOAT  0x0093d870u /* [0x00852324] the action data's float, returned in s0 */
#define FN_APPLY_FALL  0x0092e99cu /* [0x00844124] advance the fall by s0, then set mode 1 */
#define FN_DATA_GET    0x0068882cu /* [0x00a33b50] the monster's data record */
#define FN_SET_ACTION  0x0090ef74u /* [0x00827d54] start an action (the fifth argument is
                                    * the per-action value, on the stack) */
#define FN_COUNTDOWN   0x00b0704cu /* the source's 0/0 inlines 0x008a78ec's subtraction */

/* The globals MH4U's own 0/2, 0/3 and 0/6 handlers use: the data table the record lookup
 * starts from, and the signed byte the action setter takes as its per-action value. */
#define DATA_TABLE_GLOBAL  0x00f32004u
#define ACTION_EXTRA_GLOBAL 0x00fb6b7cu

/* The source's request ids (its r1), kept as the source asks for them. All are below 100,
 * i.e. motion file 0's slots, and the two games number file 0 the same (MH3U's
 * file * 100 + slot is MH4U's file << 8 | slot for file 0), so no motion translation is
 * needed here; a request into another file would be MH4U's form of the same slot. */
#define REQUEST_0_0 0x01u
#define REQUEST_0_1 0x02u
#define REQUEST_0_2 0x11u
#define REQUEST_0_3 0x1au
#define REQUEST_0_6 0x1bu

/* The source's frame values. 0/0's delay is 150.0 (the float at 0x00699b74); the request's
 * third and fourth arguments are 0xa/0 or 6/0, which MH4U's helper takes as s0/s1. 0/6's
 * vertical step is -5.0, halved because 3U's helper halves it and MH4U's does not. */
#define DELAY_0_0      150.0f
#define REQUEST_SPEED  10.0f
#define FALL_RATE       6.0f
#define VERTICAL_STEP  (-2.5f)  /* the source's -5.0, halved as 3U's 0x00833b2c does */
#define VERTICAL_CLAMP (-75.0f)
#define VERTICAL_CLAMP_BITS 0xc2960000u
#define CATEGORY_NONE 0x0bu       /* the category the three base handlers refuse */

#define DATA_RECORD_FLOAT 0x64u   /* 3U's record+0x70 */
#define ACTION_KIND       2u      /* the kind byte the three base handlers pass */

/* ── the translated handlers ────────────────────────────────────────────────────────── */

/* The action start all three base handlers end with: 0x00827d54(this, 0, index, 2). MH4U's
 * setter 0x0090ef74 takes one more argument than 3U's, a per-action signed byte from a global
 * on the stack; it is the same value MH4U's own 0/2, 0/3 and 0/6 handlers pass. The source's
 * 0x008412cc applier is the open item above. */
static int applier_logged;

static void set_action(MH4UCall *call, uint32_t enemy, uint32_t index) {
    if (!applier_logged) {
        applier_logged = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "the source's per-action value step (0x008412cc) is not carried: MH4U's "
                 "setter 0x0090ef74 takes its per-action value as a stack argument, and the "
                 "module passes MH4U's own; #55's trace settles whether they are one step");
    }
    const int8_t extra = (int8_t)mhuc_read8(
        call, mhuc_read32(call, ACTION_EXTRA_GLOBAL) + 0x2fu);
    mhuc_call5(call, FN_SET_ACTION, enemy, 0u, index, ACTION_KIND, (uint32_t)(int32_t)extra);
}

/* 3U 0x0082d1cc, 0/2's base handler, which 0/0, 0/1 and 0/2 fall into.
 *   0: mode 0; the state byte and the flags pick the start's index: 2 when the state is 2 or
 *      3 and bit 0x40 is set, else 1 when the other state byte is 1, else 0; unless the
 *      category is 0xb, the per-action value and the action start; then the set byte.
 */
void mhuc_3u_base_0_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_0_2_STATE);
    const uint32_t flags = mhuc_read32(call, work + WORK_FLAGS);
    uint32_t index;
    if ((state == 2 || state == 3) && (flags & 0x40u)) {
        index = 2u;
    } else if (mhuc_read8(call, work + WORK_OTHER_STATE) == 1u) {
        index = 1u;
    } else {
        index = 0u;
    }
    if (mhuc_read8(call, work + WORK_CATEGORY) != CATEGORY_NONE) {
        set_action(call, enemy, index);
    }
    mhuc_write8(call, work + WORK_SET, 1u);
}

/* 3U 0x00699ad4, 0/0 and 0/4.
 *   0: state 1, mode 0, the 150.0 delay, the request for 1 (speed 10.0);
 *   1: count the delay down; when it is spent, fall into 0/2's base handler.
 */
static void run_0_0_4(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_COUNTDOWN, DELAY_0_0);
        mhuc_call_f(call, FN_REQUEST, enemy, REQUEST_0_0, 0u, 0u, REQUEST_SPEED, 0.0f, NULL);
    } else if (state == 1) {
        if (!mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_COUNTDOWN, 0u, 0u)) {
            return;
        }
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* 3U's 0/1 case block (0x006916b4, inline).
 *   0: state 1, mode 0, the request for 2 (speed 10.0);
 *   1: wait for the finish flag, then fall into 0/2's base handler.
 */
static void run_0_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_REQUEST, enemy, REQUEST_0_1, 0u, 0u, REQUEST_SPEED, 0.0f, NULL);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* 3U's 0/2 case block (0x00691710).
 *   0: state 1, mode 0, the request for 0x11 (speed 6.0);
 *   1: wait for the finish flag, then 0x0082d1cc.
 */
static void run_0_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_REQUEST, enemy, REQUEST_0_2, 0u, 0u, FALL_RATE, 0.0f, NULL);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* 3U 0x00858b6c, 0/3's base handler.
 *   The data record's +0x64 float; while the mode is 0 or 3, the fall height advances by it
 *   times the block's rate; mode 1; unless the category is 0xb, the per-action value and the
 *   action start; then the set byte.
 */
void mhuc_3u_base_0_3(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const uint32_t table = mhuc_read32(call, DATA_TABLE_GLOBAL);
    const uint32_t record = mhuc_call(call, FN_DATA_GET, table,
                                      mhuc_read8(call, work + WORK_KIND),
                                      mhuc_read8(call, work + WORK_DATA_INDEX), 0u);
    const float data = mhuc_f32(call, record + DATA_RECORD_FLOAT);
    const int mode = (int)mhuc_read8(call, work + WORK_MODE);
    if (mode == 0 || mode == 3) {
        const float rate = mhuc_f32(call, work + WORK_RATE) *
                           mhuc_f32(call, work + WORK_RATE_2);
        mhuc_put_f32(call, work + WORK_POS_Y,
                     mhuc_f32(call, work + WORK_POS_Y) + data * rate);
    }
    mhuc_call(call, FN_MODE, enemy, 1u, 0u, 0u);
    if (mhuc_read8(call, work + WORK_CATEGORY) != CATEGORY_NONE) {
        set_action(call, enemy, 3u);
    }
    mhuc_write8(call, work + WORK_SET, 1u);
}

/* 3U's 0/3 case block (0x00691774).
 *   0: state 1, the data record's float (0x00852324), the fall it advances (0x00844124, which
 *      also sets mode 1), the request for 0x1a (speed 6.0);
 *   1: wait for the finish flag, then 0x00858b6c.
 */
static void run_0_3(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        mhuc_call_f(call, FN_REQUEST, enemy, REQUEST_0_3, 0u, 0u, FALL_RATE, 0.0f, NULL);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_3(call, enemy, work);
        }
    }
}

/* The vertical step and the lower clamp 3U's 0/6 case block makes before its request and its
 * flag test: 0x00833b2c(-2.5), then if the value's bits are above -75.0's, set -75.0. */
static void step_0_6_vertical(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, VERTICAL_STEP, 0.0f, NULL);
    if (mhuc_read32(call, work + WORK_VERTICAL) > VERTICAL_CLAMP_BITS) {
        mhuc_put_f32(call, work + WORK_VERTICAL, VERTICAL_CLAMP);
    }
}

/* 3U 0x0082b7dc, 0/6's base handler: mode 3, then unless the category is 0xb, the per-action
 * value and the action start; then the set byte. */
void mhuc_3u_base_0_6(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
    if (mhuc_read8(call, work + WORK_CATEGORY) != CATEGORY_NONE) {
        set_action(call, enemy, 6u);
    }
    mhuc_write8(call, work + WORK_SET, 1u);
}

/* 3U's 0/6 case block (0x006917f0).
 *   0: state 1, mode 3, the vertical step, the request for 0x1b (speed 6.0);
 *   1: the vertical step, then wait for the finish flag, then 0x0082b7dc. */
static void run_0_6(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        step_0_6_vertical(call, enemy, work);
        mhuc_call_f(call, FN_REQUEST, enemy, REQUEST_0_6, 0u, 0u, FALL_RATE, 0.0f, NULL);
    } else if (state == 1) {
        step_0_6_vertical(call, enemy, work);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_6(call, enemy, work);
        }
    }
}

/* ── the family's dispatch and self-test ────────────────────────────────────────────── */

/* Runs category 0's handler for the pair, or returns 0 so the module's dispatch can try the
 * next family. 0/5 is not an id the source has, so it falls through too. */
static int dispatch_cat0(MH4UCall *call, uint32_t enemy, uint32_t work, int category, int index) {
    if (category != 0) {
        return 0;
    }
    switch (index) {
    case 0: case 4: run_0_0_4(call, enemy, work); return 1;
    case 1: run_0_1(call, enemy, work); return 1;
    case 2: run_0_2(call, enemy, work); return 1;
    case 3: run_0_3(call, enemy, work); return 1;
    case 6: run_0_6(call, enemy, work); return 1;
    default: return 0;
    }
}

/* What this family carries: the six ids, the three base handlers and their MH4U counterparts,
 * the field map's anchors and the open item. The module's self-test calls this with the
 * others'. */
static void self_test_cat0(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 6 of the 191 actions: 0/0 and 0/4 <- 0x00699ad4 (mode 0, a 150.0 "
             "delay, falls into 0/2); 0/1 <- its inline case block (the same delay); 0/2 <- "
             "0x0082d1cc (mode 0, the state test at +0x51c/+0x1b4/+0x34c, the action start); "
             "0/3 <- 0x00858b6c (the record's +0x64, the rate at +0x1b8/+0x1bc, mode 1, the "
             "action start); 0/6 <- 0x0082b7dc (mode 3, the vertical step at +0x180, the "
             "action start)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the base handlers are port code (0002's second amendment); their "
              "engine calls are MH4U's: mode 0x%08x, request 0x%08x, flag 0x%08x, data "
              "0x%08x, vertical 0x%08x, set action 0x%08x",
              (unsigned)FN_MODE, (unsigned)FN_REQUEST, (unsigned)FN_FLAG,
              (unsigned)FN_DATA_GET, (unsigned)FN_VERTICAL, (unsigned)FN_SET_ACTION);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: *(this+0x1a48) -> *(this+0xe28), +0xdf/+0xe0 -> "
             "+0x1ca/+0x1cb, +0x5 -> +0x144, +0xdc -> +0x1c8, +0xf2 -> +0x1dc, +0x3/+0xa -> "
             "+0x1c0/+0x797e, +0x68 -> +0x180");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: 0x008412cc's per-action value is MH4U's setter's stack argument "
             "for now (#55); 0x00833b2c's 0.5 factor is passed halved (-2.5)");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat0 = {
    "cat0", 6, dispatch_cat0, self_test_cat0,
};
