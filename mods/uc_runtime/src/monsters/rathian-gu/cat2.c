/*
 * cat2.c: GU Rathian's category 2 — 2/0 to 2/29 — and the two category-9 ids that share its
 * 2/4 handler (9/3 and 9/4).
 *
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * The source is MHXX v1.4's uEm001_00 in roEm001.cro. Its category-2 function 0x02013f08
 * switches on the index to the case blocks below; five tail-call handler units, two are
 * inline:
 *
 *   2/0, 2/7, 2/9, 2/11, 2/18, 2/19, 2/24, 2/26, 2/28   0x0200f26c (r1 the mode, r2 the variant)
 *   2/1, 2/12, 2/25                                      0x02007a28 (r1 0 or 1)
 *   2/2                                                   inline
 *   2/3, 2/8, 2/10, 2/23, 2/27, 2/29                     0x0200f0d8 (r1 mode, r2 variant, r3)
 *   2/4, 2/5, 2/6, 9/3, 9/4                              0x0200f7a8 (r2 the kind, r3 the variant)
 *   2/13                                                  inline
 *   2/14 to 2/17, 2/20 to 2/22                           0x02011d94 (r1 the base index)
 *
 * 9/3 and 9/4 are category-9 case blocks that tail-call 0x0200f7a8 with (r2 = 1, r3 = 1) and
 * (r2 = 3, r3 = 1); the port runs the same translated handler for them.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x10a8) in MHXX). The fields, read off
 * the paired MH4U handlers for the same action ids:
 *
 *   MH4U work+0x144  <- MHXX work+0x1a1   the handler's state byte
 *   MH4U work+0x145  <- MHXX work+0x1a2   the handler's sub-state byte (2/14's next state)
 *   MH4U work+0x146  <- MHXX work+0x1a3   the kind/base byte (2/4's and 2/14's stores)
 *   MH4U work+0x1c0  <- MHXX this+0xa304/+0xa305   MH4U's data id (the source's pair)
 *   MH4U work+0x1d4  <- MHXX work+0x1bc   the action's timer (2/3, 2/11, 2/14)
 *   MH4U work+0x238  <- MHXX work+0x1f0   the clamped float (2/0, 2/3)
 *   MH4U work+0x168  <- MHXX work+0x18    the float a 2/4 setup writes
 *   MH4U work+0x178  <- MHXX work+0x28    the 0.25 factor a 2/4 state writes
 *   MH4U work+0x1a8  <- MHXX work+0x50    the point a 2/4 state advances
 *   MH4U this+0xca8  <- MHXX this+0xa308  the action's marker: MH4U sets bit 1 << value
 *                                          where MHXX stores the value (1/2/3/4)
 *
 * The engine calls are MH4U's counterparts of the same call site in the paired handler (the
 * MHXX address in the comment): 0x009167b4 [0x008b1700], 0x0094e318 [0x008eb108],
 * 0x00b05da4 [0x00aed11c], 0x00b0704c [0x008a78ec], 0x00922ca0 [0x008bba74],
 * 0x0092dc50 [0x008d... 2/0's set], 0x009128ac [0x008c...], 0x006e9a84 [0x020123b8],
 * 0x0092dccc [0x008c2c20], 0x00911b48 [0x008ae50c], 0x00911c0c [0x020004dc, the five-argument
 * data setup], 0x00922c40 [0x0201...], 0x0092f6e8 [0x020004ec, the table leaf],
 * 0x00911f20 [0x008c5c30], 0x0093ba70 [0x008d0444], 0x0091b0f8 [0x008d14dc],
 * 0x0093ba88 [0x008d057c], 0x0093c938 [0x008d14a0], 0x0091db4c [0x008b75d8],
 * 0x00916108 [0x008b11dc], 0x0091b3bc [0x008b52b8], 0x00922250 [0x008bb4f4],
 * 0x009114d4 [0x008ae314], 0x0093e558 [0x008ce...], 0x00916594 [0x008b1498],
 * 0x0090f8fc [0x008ad5c4], 0x00916b94 [0x020006cc], 0x0092b140 [0x008c0194] and
 * 0x0094ef64 [0x008ebab0].
 *
 * What is not carried:
 *   - **2/0, 2/1, 2/2, 2/3, 2/13's source-only fields.** 2/0's `this+0xa304/a305` and 2/3's
 *     `this+0x84 |= 0x80000` have no MH4U counterpart; the port uses MH4U's data id where the
 *     paired MH4U handler does, and skips the 2/3 store (MH4U's own 2/3 does not make it).
 *   - **2/4's attack selector (0x0201e190) and its 0x00adb528 multiplier.** 0x0201e190
 *     chooses the kind's attack; 0x00adb528 is the source object MH4U lacks (recorded for the
 *     4/27-32 slice too). The port plays 2/4's states and motions without them, and logs the
 *     two names once per action.
 *   - **2/4's 0x020044xx sub-branch.** The source's state 2 runs a long kind-specific setup
 *     (the hits and the flight); the port keeps its state order, its motions and its
 *     flag-driven tail. This is recorded in the README.
 *   - **2/14's 0x020006cc table.** The source passes the object at 0xd3d24c; MH4U's own 2/14
 *     passes none at that point, so the port calls 0x00916b94 without it.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block and this family's fields; the MHXX offset each stands for. */
#define WORK_STATE  0x0144u /* MHXX work+0x1a1 */
#define WORK_SUB    0x0145u /* MHXX work+0x1a2 */
#define WORK_KIND   0x0146u /* MHXX work+0x1a3 */
#define WORK_DATAID 0x01c0u /* MHXX this+0xa304/+0xa305 */
#define WORK_TIMER  0x01d4u /* MHXX work+0x1bc */
#define WORK_CLAMP  0x0238u /* MHXX work+0x1f0 */
#define WORK_F18    0x0168u /* MHXX work+0x18 */
#define WORK_F28    0x0178u /* MHXX work+0x28 */
#define WORK_POINT  0x01a8u /* MHXX work+0x50 */

#define ENEMY_MARKER 0x0ca8u /* MHXX this+0xa308 (value v -> bit 1 << v) */

/* MH4U engine functions this family calls, and the MHXX function each stands for. */
#define FN_PRE          0x00922ca0u /* [0x008bba74] the paired handlers' pre-call */
#define FN_MODE         0x009167b4u /* [0x008b1700] set the monster's mode */
#define FN_MOTION       0x0094e318u /* [0x008eb108] start a motion */
#define FN_FLAG         0x00b05da4u /* [0x00aed11c] the action's finish flag */
#define FN_COUNTDOWN    0x00b0704cu /* [0x008a78ec] count a float down */
#define FN_BASE_UPDATE  0x00911b48u /* [0x008ae50c] uEnemy vtable slot 89 */
#define FN_2_0_SET      0x0092dc50u /* [0x0200036c] 2/0's and 2/3's variant float setter */
#define FN_2_0_CHECK    0x009128acu /* [0x0200066c] 2/0's kind 3/4 check */
#define FN_CHECK        0x006e9a84u /* [0x020123b8] the small kind check */
#define FN_2_0_TAIL     0x0092dcccu /* [0x0200037c] 2/0's (0, r2) tail */
#define FN_1_4_STEP     0x00922c40u /* [0x0200043c] the 1.1 speed step */
#define FN_DATA_SETUP   0x00911c0cu /* [0x020004dc] the five-argument data setup */
#define FN_TABLE_LEAF   0x0092f6e8u /* [0x020004ec] the action table's leaf */
#define FN_TURN         0x0091db4cu /* [0x008b75d8] turn toward a target point */
#define FN_SET50        0x00916108u /* [0x008b11dc] 2/4's 50.0 setter */
#define FN_2_4_A        0x0091b3bcu /* [0x008b52b8] 2/4's state 1 call */
#define FN_2_4_TABLE    0x00922250u /* [0x008bb4f4] 2/4's action table read */
#define FN_2_4_POINT    0x009114d4u /* [0x008ae314] advance the 2/4 point */
#define FN_2_4_END      0x0093e558u /* [0x008ce...] 2/4's variant tail */
#define FN_2_4_STEP     0x00916594u /* [0x008b1498] 2/4's (work+0x1a8, 1) */
#define FN_2_14_SET     0x0093310cu /* [0x008b11dc] 2/14's (this, 0, 5, 3) */
#define FN_2_14_A       0x0090f8fcu /* [0x008ad5c4] 2/14's state 2 call */
#define FN_2_14_B       0x00916b94u /* [0x020006cc] 2/14's kind-1/3 call, five arguments */
#define FN_2_14_D       0x0092b140u /* [0x008c0194] 2/14's (4, 7) request */
#define FN_REQUEST      0x0094ef64u /* [0x008ebab0] request the next action */

/* The MH4U action tables the source's data pointers stand for. 2/1 and 2/2/2/13 pass a
 * table to 0x00911c0c and 0x0092f6e8; MH4U's own handlers pass these. */
#define TABLE_2_1  0x00e09458u
#define TABLE_2_2  0x00e09498u
#define TABLE_2_4  0x00fd1a68u

/* The motions the category starts, in MH4U's `file << 8 | slot` form. */
#define MOTION_2_0     MHUC_MOTION(0, 0x05) /* 5 at 6.0 */
#define MOTION_2_0_END MHUC_MOTION(0, 0x01) /* 1 at 10.0 */
#define MOTION_2_3     MHUC_MOTION(0, 0x06) /* 6 at 10.0 */
#define MOTION_2_3_END MHUC_MOTION(0, 0x01) /* 1 at 10.0 */
#define MOTION_2_4A    MHUC_MOTION(4, 0x0c) /* 0x40c at 4.0, kind 0/1/2/5/6/7 */
#define MOTION_2_4A_2  MHUC_MOTION(4, 0x1f) /* 0x41f at 4.0, kind 2/4/6 on MH4U's data */
#define MOTION_2_4B    MHUC_MOTION(4, 0x0e) /* 0x40e at 0.0 */
#define MOTION_2_4B_2  MHUC_MOTION(4, 0x21) /* 0x421 */
#define MOTION_2_4C    MHUC_MOTION(1, 0x02) /* 0x102 at 12.0 */
#define MOTION_2_4D    MHUC_MOTION(4, 0x0f) /* 0x40f at 0.0 */
#define MOTION_2_4D_2  MHUC_MOTION(4, 0x22) /* 0x422 */
#define MOTION_2_14    MHUC_MOTION(0, 0x07) /* 7 at 4.0 */

/* The two 2/4 gaps, logged once per action. */
static int gap_2_4_logged, gap_2_3_logged;

static void log_2_4_gaps_once(void) {
    if (gap_2_4_logged) {
        return;
    }
    gap_2_4_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "2/4: the source's attack selector 0x0201e190 and its 0x00adb528 multiplier "
             "have no MH4U counterpart (the object MH4U lacks, as in 4/27-32); the port plays "
             "the states and motions without them");
}

static void log_2_3_once(void) {
    if (gap_2_3_logged) {
        return;
    }
    gap_2_3_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "2/3: the source sets this+0x84's 0x80000 bit; MH4U's own 2/3 does not and the "
             "field has no pair, so the port skips it");
}

/* MHXX's marker byte is MH4U's bit 1 << value in this+0xca8. */
static void set_marker(MH4UCall *call, uint32_t enemy, uint32_t value) {
    const uint32_t old = mhuc_read32(call, enemy + ENEMY_MARKER);
    mhuc_write32(call, enemy + ENEMY_MARKER, old | (1u << value));
}

static int data_id_is(MH4UCall *call, uint32_t work, uint32_t a) {
    return mhuc_read8(call, work + WORK_DATAID) == a;
}

/* 2/0's variant setter: the source calls 0x0200036c(this, 0, 0, s0) and, for kind 2, clamps
 * the float at work+0x1f0 to 700.0 afterwards. */
static void set_variant(MH4UCall *call, uint32_t enemy, uint32_t work, float s0, int clamp) {
    mhuc_call_f(call, FN_2_0_SET, enemy, 0, 0, 0, s0, 0.0f, NULL);
    if (clamp) {
        const float value = mhuc_f32(call, work + WORK_CLAMP);
        if (value > 700.0f) {
            mhuc_put_f32(call, work + WORK_CLAMP, 700.0f);
        }
    }
}

/* ── 2/0, 2/7, 2/9, 2/11, 2/18, 2/19, 2/24, 2/26, 2/28: 0x0200f26c ───────────────────── */
/*   0: state 1, mode 0, the kind's variant call, then motion 5 at 6.0;
 *   1: the kind's pre-check, then 0x0092dccc(this, 0, 0x20); when it holds, motion 1 at 10.0
 *      and the base update. */
static void run_2_0(MH4UCall *call, uint32_t enemy, uint32_t work, int mode, int variant) {
    if (variant <= 1) {
        mhuc_call(call, FN_PRE, enemy, 0, 0, 0);
    }
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        switch (mode) {
        case 0: set_variant(call, enemy, work, -500.0f, 0); break;
        case 1: set_variant(call, enemy, work, 0.0f, 0); break;
        case 2: set_variant(call, enemy, work, 0.0f, 1); break;
        case 3: mhuc_call(call, FN_2_0_CHECK, enemy, 0, 0x10000u, 4); break;
        case 4: mhuc_call(call, FN_2_0_CHECK, enemy, 0, 0x400u, 4); break;
        case 5: set_variant(call, enemy, work, -500.0f, 0); break;
        case 6:
        case 7:
            if (mhuc_call(call, FN_CHECK, enemy, 0, 0, 0)) {
                return;
            }
            break;
        default:
            return;
        }
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_0, 0, 0, 6.0f, 0.0f, NULL);
        return;
    }
    case 1: {
        uint32_t r6 = 0xffffffffu;
        int skip = 0;
        switch (mode) {
        case 0:
            if (variant == 1 && mhuc_call(call, FN_CHECK, enemy, 0, 0, 0)) {
                return;
            }
            break;
        case 1:
        case 3:
        case 4:
        case 7:
            if (variant == 0 && mhuc_call(call, FN_CHECK, enemy, 0, 0, 0)) {
                return;
            }
            break;
        case 5:
            if (variant == 1 && mhuc_call(call, FN_CHECK, enemy, 0, 0, 0)) {
                return;
            }
            break;
        case 6:
            if (mhuc_call(call, FN_CHECK, enemy, 0, 0, 0)) {
                return;
            }
            break;
        default:
            return;
        }
        if (mode == 3) {
            r6 = mhuc_call(call, FN_2_0_CHECK, enemy, 0, 0x10000u, 4);
        } else if (mode == 4) {
            r6 = mhuc_call(call, FN_2_0_CHECK, enemy, 0, 0x400u, 4);
        }
        const uint32_t r0 = mhuc_call(call, FN_2_0_TAIL, enemy, 0, 0x20u, 0);
        skip = (r0 == 0 && r6 == 1);
        if (skip) {
            return;
        }
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_0_END, 0, 0, 10.0f, 0.0f, NULL);
        mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        return;
    }
    default:
        return;
    }
}

/* ── 2/1, 2/12, 2/25: 0x02007a28 ────────────────────────────────────────────────────── */
/*   0: state 1, mode 0, the five-argument data setup with MH4U's table;
 *   1: the 1.1 speed step when MH4U's data id is 5, then the table leaf; when it holds, the
 *      base update. */
static void run_2_1(MH4UCall *call, uint32_t enemy, uint32_t work, int mode) {
    if (mode == 1) {
        mhuc_call(call, FN_PRE, enemy, 0, 0, 0);
    }
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call5(call, FN_DATA_SETUP, enemy, TABLE_2_1, 0, 1, 0);
        return;
    case 1:
        if (data_id_is(call, work, 5)) {
            mhuc_call_f(call, FN_1_4_STEP, enemy, 0, 0, 0, 1.1f, 0.0f, NULL);
        }
        if (mhuc_call(call, FN_TABLE_LEAF, enemy, TABLE_2_1, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

/* ── 2/2 (inline) and 2/13 (inline) ─────────────────────────────────────────────────── */
/* 2/2's block (0x02013fa8): state 1, mode 0, the data setup; state 1 the 1.1 step when the
 * data id is 5, the table leaf, then the base update. 2/13's block (0x0201411c) is the same
 * with the pre-call first. */
static void run_2_2(MH4UCall *call, uint32_t enemy, uint32_t work, int pre) {
    if (pre) {
        mhuc_call(call, FN_PRE, enemy, 0, 0, 0);
    }
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call5(call, FN_DATA_SETUP, enemy, TABLE_2_2, 0, 1, 0);
        return;
    case 1:
        if (data_id_is(call, work, 5)) {
            mhuc_call_f(call, FN_1_4_STEP, enemy, 0, 0, 0, 1.1f, 0.0f, NULL);
        }
        if (mhuc_call(call, FN_TABLE_LEAF, enemy, TABLE_2_2, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    default:
        return;
    }
}

/* ── 2/3, 2/8, 2/10, 2/23, 2/27, 2/29: 0x0200f0d8 ─────────────────────────────────── */
/*   0: state 1, mode 0, the mode's variant call, motion 6 at 10.0 and, on a 0x020066c
 *      success, the base update; on r2 = 1 MH4U's own handler arms the 210.0 timer;
 *   1: the mode 1/3 check, the variant's countdown, 0x0092dccc(this, 0, 0x20), then motion 1
 *      at 10.0 and the base update. */
static void run_2_3(MH4UCall *call, uint32_t enemy, uint32_t work, int mode, int variant,
                    int r3) {
    log_2_3_once();
    if (r3 == 1) {
        mhuc_call(call, FN_PRE, enemy, 0, 0, 0);
    }
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        switch (mode) {
        case 1: set_variant(call, enemy, work, 0.0f, 0); break;
        case 2: set_variant(call, enemy, work, 0.0f, 1); break;
        default: set_variant(call, enemy, work, -500.0f, 0); break;
        }
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_3, 0, 0, 10.0f, 0.0f, NULL);
        if (variant == 1) {
            mhuc_put_f32(call, work + WORK_TIMER, 210.0f);
        }
        return;
    }
    case 1: {
        if ((mode == 1 || mode == 3) && mhuc_call(call, FN_CHECK, enemy, 0, 0, 0)) {
            return;
        }
        uint32_t r7 = 0;
        if (variant == 1) {
            r7 = mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0, 0);
        }
        const uint32_t r0 = mhuc_call(call, FN_2_0_TAIL, enemy, 0, 0x20u, 0);
        if ((r0 | r7) == 0) {
            return;
        }
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_3_END, 0, 0, 10.0f, 0.0f, NULL);
        mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        return;
    }
    default:
        return;
    }
}

/* ── 2/4, 2/5, 2/6, 9/3, 9/4: 0x0200f7a8 ───────────────────────────────────────────── */
/* The kind (the source's r2) is 0 for 2/4-2/6, 1 for 9/3 and 3 for 9/4; the variant (r3) is
 * 0 for 2/4-2/6 and 1 for 9/3 and 9/4. The handler's own state keeps the flight:
 *   0: marker for the kind, mode 0, the kind's motion at 4.0;
 *   1: the kind's turn (2/4, 2/6 and kind 5), the finish flag; on it state 2, mode 3, the
 *      50.0 setter, the side motion, 0x0091b3bc, the action table read into work+0x168, the
 *      0x009114d4 point, and 0x0093e558 for the variant;
 *   2: the source's attack selector is not carried; the finish flag moves on to state 3, the
 *      0.25 factor at work+0x178 and the point step, then motion 0x102 at 12.0;
 *   3: the point step, the float clamped at 0; the finish flag leads to the sub-state's
 *      motion (0x102 at 0.0, then the side motion at 6.0) or to state 4;
 *   4: the finish flag, state 5, mode 0, the end motion at 0.0;
 *   5: the finish flag, then the base update. */
static void run_2_4(MH4UCall *call, uint32_t enemy, uint32_t work, int kind, int variant) {
    log_2_4_gaps_once();
    /* MH4U's own 2/4 picks the two motion sets from the data id (2, 4 and 6 use the
     * 0x41f/0x420/0x421/0x422 set; the rest 0x40c to 0x40f). The source picks from
     * this+0xa304, which has no pair, so the port uses MH4U's choice. */
    const int fast = data_id_is(call, work, 2) || data_id_is(call, work, 4) ||
                     data_id_is(call, work, 6);
    const uint32_t motion_a = fast ? MOTION_2_4A_2 : MOTION_2_4A;
    const uint32_t motion_b = fast ? MOTION_2_4B_2 : MOTION_2_4B;
    const uint32_t motion_d = fast ? MOTION_2_4D_2 : MOTION_2_4D;
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        if (kind >= 1 && kind <= 4) {
            set_marker(call, enemy, (uint32_t)kind);
        }
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, motion_a, 0, 0, 4.0f, 0.0f, NULL);
        return;
    case 1:
        if (kind == 2 || kind == 4 || kind == 5) {
            mhuc_call(call, FN_TURN, enemy, 0x200u, 0, 0);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call(call, FN_MODE, enemy, 3, 0, 0);
        mhuc_call_f(call, FN_SET50, enemy, 0, 0, 0, 50.0f, 0.0f, NULL);
        mhuc_call_f(call, FN_MOTION, enemy, motion_b, 0, 0, 0.0f, 0.0f, NULL);
        mhuc_call(call, FN_2_4_A, enemy, 0, 0, 0);
        {
            float value = 0.0f;
            mhuc_call_f(call, FN_2_4_TABLE, enemy, TABLE_2_4, 0, 0, 0.0f, 0.0f, &value);
            mhuc_put_f32(call, work + WORK_F18, value);
        }
        mhuc_call(call, FN_2_4_POINT, enemy, work + WORK_POINT, 0, 0);
        if (variant == 1) {
            mhuc_call(call, FN_2_4_END, enemy, 0, 0, 0);
        }
        return;
    case 2:
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        mhuc_write8(call, work + WORK_SUB, data_id_is(call, work, 4) ? 1u : 0u);
        mhuc_put_f32(call, work + WORK_F28, 0.25f);
        mhuc_call(call, FN_2_4_STEP, enemy, work + WORK_POINT, 1, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_4C, 0, 0, 12.0f, 0.0f, NULL);
        return;
    case 3: {
        mhuc_call(call, FN_2_4_STEP, enemy, work + WORK_POINT, 1, 0);
        const float f = mhuc_f32(call, work + WORK_F18);
        if (f > 0.0f) {
            mhuc_put_f32(call, work + WORK_F18, 0.0f);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        if (mhuc_read8(call, work + WORK_SUB) == 0) {
            mhuc_write8(call, work + WORK_SUB, 1u);
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_4C, 0, 0, 0.0f, 0.0f, NULL);
        } else {
            mhuc_write8(call, work + WORK_STATE, 4u);
            mhuc_call_f(call, FN_MOTION, enemy, motion_a, 0, 0, 6.0f, 0.0f, NULL);
        }
        return;
    }
    case 4:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_write8(call, work + WORK_STATE, 5u);
            mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
            mhuc_call_f(call, FN_MOTION, enemy, motion_d, 0, 0, 0.0f, 0.0f, NULL);
        }
        return;
    default:
        if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return;
    }
}

/* ── 2/14 to 2/17 and 2/20 to 2/22: 0x02011d94 ─────────────────────────────────────── */
/* The case blocks pass r1 = 0 to 6; the unit maps that to its own base 5 to 11.
 *   0: state 1, mode 0, motion 7 at 4.0, 0x0093310c(this, 0, 5, 3), the timer cleared, then
 *      the base's setter: 0x0092dc50(this, 0x10, 0, 0.0) for bases 5, 6 and 9 to 11, and
 *      (0, 0, -300.0) for bases 7 and 8;
 *   1: the 1.0 countdown; the base's check (0x009128ac for 0 to 3, 0x006e9a84 for 4 to 6);
 *      the 0x0092dccc tail; when the timer is over, state 2 and work+0x145 cleared;
 *   2: 0x0090f8fc(this, 0); for the bases 6 and 8 the 0x00916b94 call with the kind byte, then
 *      the request for action 2/2. */
static void run_2_14(MH4UCall *call, uint32_t enemy, uint32_t work, int base) {
    switch (mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_2_14, 0, 0, 4.0f, 0.0f, NULL);
        mhuc_call(call, FN_2_14_SET, enemy, 0, 5, 3);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        if (base == 7 || base == 8) {
            mhuc_call_f(call, FN_2_0_SET, enemy, 0, 0, 0, -300.0f, 0.0f, NULL);
        } else {
            mhuc_call_f(call, FN_2_0_SET, enemy, 0x10u, 0, 0, 0.0f, 0.0f, NULL);
        }
        return;
    case 1: {
        mhuc_call_f(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0, 0, 1.0f, 0.0f, NULL);
        const uint32_t r8 = 0x40u;
        uint32_t r6 = 0xffffffffu;
        if (base == 5 || base == 6) {
            r6 = mhuc_call(call, FN_2_0_CHECK, enemy, 0, 0x10000u, 4);
            if (r6 != 0xffffffffu && base == 6) {
                mhuc_write8(call, work + WORK_KIND, (r6 + 0x8000u) >> 8);
            }
        } else if (base == 7 || base == 8) {
            r6 = mhuc_call(call, FN_2_0_CHECK, enemy, 0, 0x400u, 4);
            if (r6 != 0xffffffffu && base == 8) {
                mhuc_write8(call, work + WORK_KIND, (r6 + 0x8000u) >> 8);
            }
        } else {
            if (mhuc_call(call, FN_CHECK, enemy, (uint32_t)(base - 9), 0, 0)) {
                return;
            }
        }
        const uint32_t r0 = mhuc_call(call, FN_2_0_TAIL, enemy, 0, r8, 0);
        if (r0 == 0 && r6 == 0xffffffffu) {
            return;
        }
        if (mhuc_f32(call, work + WORK_TIMER) > 0.0f) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        goto state_2;
    }
    case 2:
state_2:
        mhuc_call(call, FN_2_14_A, enemy, 0, 0, 0);
        if ((base == 6 || base == 8) && mhuc_read8(call, work + WORK_KIND) != 0) {
            mhuc_call5(call, FN_2_14_B, enemy, 5, 0xb, mhuc_read8(call, work + WORK_KIND), 0);
        }
        mhuc_call(call, FN_REQUEST, enemy, 2, 2, 0);
        return;
    default:
        return;
    }
}

/* Runs the block for the pair, or returns 0 so the module's dispatch can try the next
 * family. Category 9's 9/3 and 9/4 are this family's, through the same 2/4 unit. */
static int dispatch_cat2(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                         int index) {
    int kind = 0, variant = 0, mode = 0, r3 = 0, base = 0;
    if (category == 2) {
        switch (index) {
        case 0: mode = 0; variant = 0; break;
        case 7: mode = 1; variant = 0; break;
        case 9: mode = 2; variant = 0; break;
        case 11: mode = 5; variant = 1; break;
        case 18: mode = 3; variant = 0; break;
        case 19: mode = 4; variant = 0; break;
        case 24: mode = 6; variant = 0; break;
        case 26: mode = 0; variant = 1; break;
        case 28: mode = 7; variant = 1; break;
        default: mode = -1; break;
        }
        if (mode >= 0) {
            MhucState *st = mhuc_gu_state(call, enemy, category, index);
            if (!st) {
                return 0;
            }
            run_2_0(call, enemy, work, mode, variant);
            return 1;
        }
        switch (index) {
        case 1: mode = 0; break;
        case 12: mode = 1; break;
        case 25: mode = 0; break;
        default: mode = -1; break;
        }
        if (mode >= 0) {
            MhucState *st = mhuc_gu_state(call, enemy, category, index);
            if (!st) {
                return 0;
            }
            run_2_1(call, enemy, work, mode);
            return 1;
        }
        switch (index) {
        case 2:
            if (!mhuc_gu_state(call, enemy, category, index)) {
                return 0;
            }
            run_2_2(call, enemy, work, 0);
            return 1;
        case 3: mode = 0; variant = 0; r3 = 0; break;
        case 8: mode = 1; variant = 0; r3 = 0; break;
        case 10: mode = 2; variant = 0; r3 = 0; break;
        case 23: mode = 1; variant = 1; r3 = 0; break;
        case 27: mode = 3; variant = 0; r3 = 1; break;
        case 29: mode = 1; variant = 0; r3 = 1; break;
        default: mode = -1; break;
        }
        if (mode >= 0) {
            if (!mhuc_gu_state(call, enemy, category, index)) {
                return 0;
            }
            run_2_3(call, enemy, work, mode, variant, r3);
            return 1;
        }
        switch (index) {
        case 4: case 5: case 6: kind = 0; variant = 0; break;
        default: kind = -1; break;
        }
        if (kind >= 0) {
            if (!mhuc_gu_state(call, enemy, category, index)) {
                return 0;
            }
            run_2_4(call, enemy, work, kind, variant);
            return 1;
        }
        switch (index) {
        case 13:
            if (!mhuc_gu_state(call, enemy, category, index)) {
                return 0;
            }
            run_2_2(call, enemy, work, 1);
            return 1;
        case 14: case 15: case 16: case 17: base = index - 9; break; /* 5 to 8 */
        case 20: case 21: case 22: base = index - 11; break;          /* 9 to 11 */
        default: return 0;
        }
        if (!mhuc_gu_state(call, enemy, category, index)) {
            return 0;
        }
        run_2_14(call, enemy, work, base);
        return 1;
    }
    if (category == 9 && (index == 3 || index == 4)) {
        if (!mhuc_gu_state(call, enemy, category, index)) {
            return 0;
        }
        /* 9/3 passes (r2 = 1, r3 = 1), 9/4 (r2 = 3, r3 = 1) to the 2/4 handler. */
        run_2_4(call, enemy, work, index == 3 ? 1 : 3, 1);
        return 1;
    }
    return 0;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. The ready line counts the thirty category-2 ids and the two category-9 ids. */
const MhucFamily mhuc_gu_family_cat2 = {
    "cat2", 32, dispatch_cat2, 0,
};
