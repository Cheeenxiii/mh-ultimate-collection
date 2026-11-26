/*
 * cat1.c: GU Rathian's category 1 — 1/0 to 1/11, the whole category.
 *
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * The source is MHXX v1.4's uEm001_00 in roEm001.cro. Its category-1 function 0x02019220
 * switches on the index to the twelve case blocks below; 1/1, 1/2, 1/3, 1/10 and 1/11 are
 * inline and the rest tail-call three handler units:
 *
 *   1/0, 1/9  0x0200e200, the same handler with r1 = 0
 *   1/4, 1/7  0x02009ab8 with r1 = 0 and 1
 *   1/5, 1/8  0x02009bd8 with r1 = 0 and 1
 *   1/6       0x02009c8c
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x10a8) in MHXX). The fields this slice
 * reads are read off the paired MH4U handlers for the same action ids (the reference page's
 * method: a shared action's two handlers call the same engine functions in the same order, so
 * the fields around the calls correspond):
 *
 *   MH4U work+0x144  <- MHXX work+0x1a1   the handler's state byte (MH4U's own 1/0 etc.)
 *   MH4U work+0x145  <- MHXX work+0x1a2   the handler's sub-state/count byte
 *   MH4U work+0x1cb  <- MHXX this+0x6bf1  the current index (1/4's request choice)
 *   MH4U work+0x1d4  <- MHXX work+0x1bc   the action's timer (1/11 and 1/6)
 *   MH4U work+0x238  <- MHXX work+0x1f0   the clamped float (2/3's counterpart; not read here)
 *   MH4U this+0xca8  <- MHXX this+0xa308  the action's marker: MH4U sets bit 1 << value where
 *                                          MHXX stores the value 1, 2 or 3 (1/7, 1/8 store 3
 *                                          and MH4U's own 1/7/1/8 OR bit 8; 1/4's unit stores 3
 *                                          for the same path)
 *
 * The engine calls are MH4U's counterparts of the same call site in the paired handler (the
 * MHXX address in the comment): the mode setter 0x009167b4 [0x008b1700], the motion start
 * 0x0094e318 [0x008eb108], the finish flag 0x00b05da4 [0x00aed11c], the countdown 0x00b0704c
 * [0x008a78ec], the speed/rate setter 0x00941d84 [0x008d73e8], the mode-clear query
 * 0x0091aae4 [0x0083336c], the next-action request 0x0094ef64 [0x008ebab0], 0x00914dc4
 * [0x008b0194], 0x0093310c [0x008c8b60], 0x00922c40 [0x008d... / MH4U's own 1/4], 0x0091908c
 * [0x008b0ec4], 0x00911f20 [0x008c5c30], 0x00911b48 [0x008ae50c], and the 1/6 helpers
 * 0x0093ba70 [0x008d0444], 0x0091b0f8 [0x008d14dc], 0x0093ba88 [0x008d057c] and 0x0093c938
 * [0x008d14a0].
 *
 * What is not carried, once per action:
 *   - 1/0's and 1/1-1/11's no-op: MHXX's 1/0 and 1/5 units test the two bytes at
 *     this+0xa304/+0xa305 to pick a mode; MH4U's own handlers test the data id at work+0x1c0
 *     instead, so the port uses MH4U's choice (the fields have no pair).
 *   - 1/6's last call, 0x00903e84, after the base update: MH4U's own 1/6 handler has no such
 *     call and no counterpart was found. The move plays without it.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block and this family's fields; the MHXX offset each stands for in the
 * comment. */
#define WORK_STATE  0x0144u /* MHXX work+0x1a1: the handler's state byte */
#define WORK_SUB    0x0145u /* MHXX work+0x1a2: the handler's sub-state/count byte */
#define WORK_INDEX  0x01cbu /* MHXX this+0x6bf1: the current index */
#define WORK_TIMER  0x01d4u /* MHXX work+0x1bc: the action's timer */
#define WORK_DATAID 0x01c0u /* MHXX this+0xa304/+0xa305 stand for MH4U's data id */

/* MHXX's marker byte this+0xa308 is MH4U's bit 1 << value in the word at this+0xca8. */
#define ENEMY_MARKER 0x0ca8u

/* MH4U engine functions this family calls, and the MHXX function each stands for. */
#define FN_MODE         0x009167b4u /* [0x008b1700] set the monster's mode (r1) */
#define FN_MOTION       0x0094e318u /* [0x008eb108] start a motion (index r1, s0/s1) */
#define FN_FLAG         0x00b05da4u /* [0x00aed11c] the action's finish flag */
#define FN_COUNTDOWN    0x00b0704cu /* [0x008a78ec] count a float down by the frame rate */
#define FN_SET_SPEED    0x00941d84u /* [0x008d73e8] set a speed (s0) and its flag */
#define FN_MODE_CLEAR   0x0091aae4u /* [0x0083336c] the flag-clear query, its r0 tested */
#define FN_REQUEST_NEXT 0x0094ef64u /* [0x008ebab0] request the next action (r1, r2) */
#define FN_1_0_TAIL     0x00914dc4u /* [0x008b0194] 1/0's state 0 (this, 0, 0x13) */
#define FN_1_0_SET      0x0093310cu /* [0x008c8b60] 1/0's (this, 1, r2, 5) */
#define FN_1_3_QUERY    0x0091aae4u /* [0x0083336c] 1/3's 52.0 query */
#define FN_1_3_MOTION   0x0091908cu /* [0x008b0ec4] 1/3's (2, 0x11, 50.0) */
#define FN_1_5_TAIL     0x00911f20u /* [0x008c5c30] 1/5's (work+0x198, r2, 0) */
#define FN_1_6_A        0x0093ba70u /* [0x008d0444] 1/6's state 1 first call */
#define FN_1_6_B        0x0091b0f8u /* [0x008d14dc] 1/6's state 1 tail */
#define FN_1_6_C        0x0093ba88u /* [0x008d057c] 1/6's state 2 motion step */
#define FN_1_6_D        0x0093c938u /* [0x008d14a0] 1/6's state 2 tail */
#define FN_BASE_UPDATE  0x00911b48u /* [0x008ae50c] uEnemy vtable slot 89 (MHXX 0x3d0) */

/* The motions the category starts, in MH4U's `file << 8 | slot` form (R2: the same index on
 * every comparable id, so MHXX's packed number is already MH4U's). */
#define MOTION_1_0  MHUC_MOTION(0, 0x04) /* 0x4, 10.0 */
#define MOTION_1_1  MHUC_MOTION(0, 0x0f) /* 0xf, 10.0 */
#define MOTION_1_2  MHUC_MOTION(3, 0x10) /* 0x310, 6.0 */
#define MOTION_1_4  MHUC_MOTION(0, 0x10) /* 0x10, 6.0 */
#define MOTION_1_5  MHUC_MOTION(0, 0x11) /* 0x11, 6.0 */
#define MOTION_1_6A MHUC_MOTION(0, 0x12) /* 0x12, 6.0 */
#define MOTION_1_6B MHUC_MOTION(0, 0x13) /* 0x13, 30.0 */
#define MOTION_1_6C MHUC_MOTION(0, 0x14) /* 0x14, 0.0 */
#define MOTION_1_6D MHUC_MOTION(3, 0x10) /* 0x310, 0.0 */
#define MOTION_1_10 MHUC_MOTION(0, 0x0e) /* 0xe, 6.0 */
#define MOTION_1_11 MHUC_MOTION(0, 0x01) /* 0x1, 10.0 */

/* The two gaps, logged once for the family. */
static int gap_logged;

static void log_gaps_once(void) {
    if (gap_logged) {
        return;
    }
    gap_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "1/*: the source's this+0xa304/+0xa305 tests (1/0, 1/5, 1/8) and 1/6's "
             "post-update 0x00903e84 have no MH4U field or call; the port uses MH4U's own "
             "data-id choice and skips the last call");
}

/* MH4U's own 1/4 and 1/7 place the source's marker 3 as bit 3 of this+0xca8. */
static void set_marker(MH4UCall *call, uint32_t enemy, uint32_t value) {
    const uint32_t old = mhuc_read32(call, enemy + ENEMY_MARKER);
    mhuc_write32(call, enemy + ENEMY_MARKER, old | (1u << value));
}

/* MH4U's own 1/0 and 1/4 handlers take the mode from the data id at work+0x1c0 (MHXX tests
 * this+0xa304/+0xa305); this returns MH4U's own choice. */
static int data_id_is(MH4UCall *call, uint32_t work, uint32_t a) {
    return mhuc_read8(call, work + WORK_DATAID) == a;
}

/* ── 1/0 and 1/9: 0x0200e200 ──────────────────────────────────────────────────────────── */
/*   0: state 1, mode 0, motion 4 at 10.0, then 0x00914dc4(this, 0, 0x13);
 *   1: the 110.0 speed step; when it holds, the (1, r2, 5) call with r2 0x32 when MH4U's
 *      data id is 5 or 6, else 8; then the finish flag and the base update. */
static void run_1_0(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    log_gaps_once();
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_0, 0, 0, 10.0f, 0.0f, NULL);
        mhuc_call(call, FN_1_0_TAIL, enemy, 0, 0x13u, 0);
        return;
    case 1:
        if (mhuc_call_f(call, FN_SET_SPEED, enemy, 0, 0, 0, 110.0f, 0.0f, NULL)) {
            const uint32_t r2 = (data_id_is(call, work, 5) || data_id_is(call, work, 6)) ? 0x32u : 8u;
            mhuc_call(call, FN_1_0_SET, enemy, 1, r2, 5);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

/* ── 1/4 and 1/7: 0x02009ab8 ────────────────────────────────────────────────────────── */
/*   0: state 1, sub 0, mode 0, motion 0x10 at 6.0;
 *   1: the finish flag bumps the sub-state; when it reaches 3 the source asks for 1/8 on
 *      r1 = 1, else for 1/5 when the index is 4 and 1/14 otherwise. */
static void run_1_4(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    if (mode == 1) {
        set_marker(call, enemy, 3);
    }
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_4, 0, 0, 6.0f, 0.0f, NULL);
        return;
    case 1: {
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_write8(call, work + WORK_SUB, mhuc_read8(call, work + WORK_SUB) + 1u);
        }
        if (mhuc_read8(call, work + WORK_SUB) < 3) {
            return;
        }
        if (mode == 1) {
            mhuc_call(call, FN_REQUEST_NEXT, enemy, 1, 8, 0);
        } else if (index == 4) {
            mhuc_call(call, FN_REQUEST_NEXT, enemy, 1, 5, 0);
        } else {
            mhuc_call(call, FN_REQUEST_NEXT, enemy, 1, 0xe, 0);
        }
        return;
    }
    default:
        return;
    }
}

/* ── 1/5 and 1/8: 0x02009bd8 ────────────────────────────────────────────────────────── */
/*   0: state 1, mode 0, motion 0x11 at 6.0, then 0x00911f20(this, work+0x198, r2, 0) with r2
 *      0x64 (the source narrows it to 0x1e when this+0xa305 is 4; that byte has no MH4U
 *      counterpart, so MH4U's own 0x64 is used);
 *   1: the finish flag, then the base update. */
static void run_1_5(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    log_gaps_once();
    if (mode == 1) {
        set_marker(call, enemy, 3);
    }
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_5, 0, 0, 6.0f, 0.0f, NULL);
        mhuc_call(call, FN_1_5_TAIL, enemy, work + 0x198u, 0x64u, 0);
        return;
    case 1:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

/* ── 1/6: 0x02009c8c ────────────────────────────────────────────────────────────────── */
/*   0: state 1, mode 0, motion 0x12 at 6.0;
 *   1: the finish flag, state 2, motion 0x13 at 30.0, 0x0093ba70, then 0x0091b0f8;
 *   2: the motion step 0x0093ba88(this, 1, r2, 0.4) with r2 by MH4U's data id (0x1e for 1/2,
 *      0x14 for 3/4, 0xf otherwise), the 1.0 countdown at work+0x1d4, then state 3, motion
 *      0x14 and 0x0093c938(this, 0, the part byte from *(work)+0x14c);
 *   3: the finish flag, state 4, motion 0x310 at 0.0;
 *   4: the finish flag, the base update, then the source's 0x00903e84 (not carried). */
static void run_1_6(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    log_gaps_once();
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6A, 0, 0, 6.0f, 0.0f, NULL);
        return;
    case 1:
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6B, 0, 0, 30.0f, 0.0f, NULL);
        mhuc_call(call, FN_1_6_A, enemy, 0, 0, 0);
        mhuc_call(call, FN_1_6_B, enemy, 0, 0, 0);
        return;
    case 2: {
        const uint32_t id = mhuc_read8(call, work + WORK_DATAID);
        const uint32_t r2 = (id == 1 || id == 2) ? 0x1eu : (id == 3 || id == 4) ? 0x14u : 0x0fu;
        mhuc_call_f(call, FN_1_6_C, enemy, 1, r2, 0, 0.4f, 0.0f, NULL);
        if (mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0, 0)) {
            mhuc_write8(call, work + WORK_STATE, 3u);
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6C, 0, 0, 0.0f, 4.0f, NULL);
            const uint32_t object = mhuc_read32(call, work);
            const uint32_t part = object ? mhuc_read8(call, object + 0x14cu) : 0u;
            mhuc_call(call, FN_1_6_D, enemy, 0, part, 0);
        }
        return;
    }
    case 3:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_write8(call, work + WORK_STATE, 4u);
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6D, 0, 0, 0.0f, 4.0f, NULL);
        }
        return;
    default:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    }
}

/* ── the inline case blocks ──────────────────────────────────────────────────────────── */
/* 1/1 (0x02019314) and 1/2 (0x02019378): state 1, mode 0, the motion at 10.0 or 6.0; state 1
 * is the finish flag and the base update. */
static void run_inline_motion(MH4UCall *call, uint32_t enemy, uint32_t work, uint32_t motion,
                              float s0) {
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, motion, 0, 0, s0, 0.0f, NULL);
        return;
    case 1:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

static void run_1_1(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    run_inline_motion(call, enemy, work, MOTION_1_1, 10.0f);
}

static void run_1_2(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    run_inline_motion(call, enemy, work, MOTION_1_2, 6.0f);
}

/* 1/3 (0x020193dc): state 1, mode 0, 0x0091908c(this, 2, 0x11, 50.0); state 1 the 52.0 query
 * and, when it holds, the base update. */
static void run_1_3(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_1_3_MOTION, enemy, 2, 0x11u, 0, 50.0f, 0.0f, NULL);
        return;
    case 1:
        if (mhuc_call_f(call, FN_1_3_QUERY, enemy, 1, 0, 0, 52.0f, 0.0f, NULL)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

/* 1/10 (0x02019490): state 1, mode 0, motion 0xe at 6.0; state 1 the finish flag and the base
 * update. */
static void run_1_10(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    run_inline_motion(call, enemy, work, MOTION_1_10, 6.0f);
}

/* 1/11 (0x020194f4): state 1, mode 0, motion 1 at 10.0 and the 20.0 timer; state 1 the finish
 * flag, else the 1.0 countdown, then the base update when the timer is spent. */
static void run_1_11(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode) {
    (void)index;
    (void)mode;
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_11, 0, 0, 10.0f, 0.0f, NULL);
        mhuc_put_f32(call, work + WORK_TIMER, 20.0f);
        return;
    case 1:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
            return;
        }
        if (mhuc_call_f(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0, 0, 1.0f, 0.0f, NULL)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

/* Runs the block for the pair, or returns 0 so the module's dispatch can try the next
 * family. The unit's mode (r1) is 1 for 1/7 and 1/8, 0 everywhere else. */
static int dispatch_cat1(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                         int index) {
    if (category != 1) {
        return 0;
    }
    void (*run)(MH4UCall *call, uint32_t enemy, uint32_t work, int index, int mode);
    int mode = 0;
    switch (index) {
    case 0: case 9: run = run_1_0; break;
    case 1: run = run_1_1; break;
    case 2: run = run_1_2; break;
    case 3: run = run_1_3; break;
    case 4: run = run_1_4; break;
    case 7: run = run_1_4; mode = 1; break;
    case 5: run = run_1_5; break;
    case 8: run = run_1_5; mode = 1; break;
    case 6: run = run_1_6; break;
    case 10: run = run_1_10; break;
    case 11: run = run_1_11; break;
    default: return 0; /* a category-1 index MHXX's dispatcher doesn't handle */
    }
    MhucState *st = mhuc_gu_state(call, enemy, category, index);
    if (!st) {
        return 0;
    }
    run(call, enemy, work, index, mode);
    return 1;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. The ready line counts the twelve ids. */
const MhucFamily mhuc_gu_family_cat1 = {
    "cat1", 12, dispatch_cat1, 0,
};
