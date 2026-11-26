/*
 * cat1.c: 3U Rathian's category 1 — 1/0 to 1/14, the whole category.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending.
 *
 * The source is MH3U USA's uEm002. Its category-1 function 0x00686324 switches on the index
 * (0 to 0xf) to the case blocks below; four of them are inline and eight tail-call the five
 * handler units this file translates (three of them take a variant in r1). 1/4 and 1/13 share
 * the unit 0x00692a1c with r1 = 0, 1/7 takes it with r1 = 1; likewise 0x00692f14 serves 1/5
 * and 1/14 with r1 = 0 and 1/8 with r1 = 1, and 0x00693388 serves 1/11 with r1 = 0 and 1/12
 * with r1 = 1. 1/10's case block is inline and falls into the category-0 base handler
 * 0x0082d1cc, which cat0.c exports as mhuc_3u_base_0_2 (decision 0002's second amendment:
 * a base-class handler is port code too, so it is reused, not replaced).
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The fields this slice
 * reads are the merged map's (reference/README.md, "The 3U work block on MH4U's layout"):
 * +0x5 -> +0x144 (the handler's state byte), +0xdf/+0xe0 -> +0x1ca/+0x1cb (the action pair),
 * and +0x28/+0x2c -> +0x1d4 (the frame timer; MH4U keeps one value and counts it down with
 * 0x00b0704c). The frame delta the source reads through a pointer at +0x30 is this+0x14 in
 * both games. 3U's +0x28 is the timer in 1/4, 1/6 and 1/11 and an elapsed-time accumulator
 * in 1/0; both are +0x1d4 here.
 *
 * Engine calls are MH4U's counterparts, each the same call at the same point of the source
 * (the source address in the comment): the mode setter 0x009167b4 [0x0082fe88], the motion
 * start 0x0094e318 [0x00828828], the flag-clear query 0x0091aae4 [0x0083336c], the finish
 * flag 0x00b05da4 [0x0083cbf4], the next-action request 0x0094ef64 [0x0082a06c], the
 * countdown 0x00b0704c [the inline +0x28 arithmetic], 0x0093310c [0x00844a40], 0x00914dc4
 * [0x00844a38], 0x00922ca0 [0x0083d18c], 0x0093ba88 [0x0083c79c], 0x0091b0f8 [0x0031be10]
 * and 0x0093c938 [0x008440a4].
 *
 * #55's open calls. All eight ids on the three handlers 0x00692834, 0x00692a1c and
 * 0x00692f14 call the source's 0x0016052c, the uEffect039 spawn; MH4U has no uEffect039
 * class, so it is #55-blocked. 0x00161798 (1/0 and 1/9), 0x00847798 (the six ids whose
 * handler runs the r1 = 1 effect block) and 0x0016669c (1/7's type-9 effect factory, whose
 * MH4U factory takes a type where the source passes the monster) are blocked the same way,
 * and 0x005aef18's two-float gate has no MH4U field pair (the map gives one timer field).
 * The names are logged once and the calls are skipped; the moves play without their effects.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE      0x0144u /* 3U +0x5:  the handler's state byte */
#define WORK_CATEGORY   0x01cau /* 3U +0xdf: the current category */
#define WORK_INDEX      0x01cbu /* 3U +0xe0: the current index */
#define WORK_TIMER      0x01d4u /* 3U +0x28/+0x2c: the frame timer (or 1/0's accumulator) */

/* The frame delta: this+0x14 in both games (3U reaches it through the pointer at work+0x30). */
#define ENEMY_DELTA 0x0014u

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_MODE         0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion (index r1, speed s0, s1) */
#define FN_MODE_CLEAR   0x0091aae4u /* [0x0083336c] the flag-clear query, its r0 tested */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_REQUEST_NEXT 0x0094ef64u /* [0x0082a06c] request the next action (r1, r2) */
#define FN_COUNTDOWN    0x00b0704cu /* the source's inline +0x28 subtraction, 1 when spent */
#define FN_SET_1_0      0x0093310cu /* [0x00844a40] 1/0's (this, 1, 8, 5) */
#define FN_SET_1_0_2    0x00914dc4u /* [0x00844a38] 1/0's (this, 0, 0x13), r3 = 0 */
#define FN_1_4_SETUP    0x00922ca0u /* [0x0083d18c] 1/4's and 1/13's r1 = 0 byte */
#define FN_1_6_STEP     0x0093ba88u /* [0x0083c79c] 1/6's state 2 call */
#define FN_1_6_TAIL     0x0091b0f8u /* [0x0031be10] 1/6's state 1 tail */
#define FN_1_6_END      0x0093c938u /* [0x008440a4] 1/6's state 2 tail */

/* The motions the handlers start, as MH4U's `file << 8 | slot` for her converted lists.
 * MH3U writes `file * 100 + slot`, so all but 1/2's 0x7c are file 0's slots; 0x7c is file
 * 1, slot 24 (0x18). */
#define MOTION_1_0   MHUC_MOTION(0, 0x05) /* 0x006929cc */
#define MOTION_1_1   MHUC_MOTION(0, 0x12) /* 0x006863d4 */
#define MOTION_1_2   MHUC_MOTION(1, 0x18) /* 0x00686430: 3U 0x7c */
#define MOTION_1_3   MHUC_MOTION(0, 0x02) /* 0x00686490 */
#define MOTION_1_4   MHUC_MOTION(0, 0x13) /* 0x00692a7c */
#define MOTION_1_5   MHUC_MOTION(0, 0x14) /* 0x00692f74 */
#define MOTION_1_6_A MHUC_MOTION(0, 0x17) /* 0x006932a4, speed 6.0 */
#define MOTION_1_6_B MHUC_MOTION(0, 0x18) /* 0x006932d8, speed 0.0 */
#define MOTION_1_6_C MHUC_MOTION(0, 0x19) /* 0x0069335c, speed 4.0 */
#define MOTION_1_10  MHUC_MOTION(0, 0x11) /* 0x00686538 */
#define MOTION_1_11  MHUC_MOTION(0, 0x01) /* 0x00693408, speed 10.0 */
#define MOTION_1_12  MHUC_MOTION(0, 0x11) /* 0x0069341c, speed 6.0 */

/* The source's frame values. */
#define SPEED_1_0    10.0f
#define SPEED_1_1    10.0f
#define SPEED_1_2     2.0f
#define SPEED_1_3    50.0f
#define SPEED_1_4_5   6.0f
#define SPEED_1_6_B   0.0f
#define SPEED_1_6_C   4.0f
#define SPEED_1_10    6.0f
#define SPEED_1_11   10.0f
#define SPEED_1_12    6.0f

/* 1/4's and 1/13's three-second timer, 1/6's 1800 and 1/11's and 1/12's 20. The source
 * writes the delay to both +0x28 and +0x2c; MH4U keeps +0x1d4 only. */
#define DELAY_1_4      3.0f
#define DELAY_1_6   1800.0f
#define DELAY_1_11    20.0f

/* The animation queries, each 0x0083336c(mode, s0, s1); s1 is 0.0 where the source leaves it. */
#define QUERY_1_0_A  110.0f   /* twice, modes 0 */
#define QUERY_1_0_B  112.0f
#define QUERY_1_0_B2 214.0f
#define QUERY_1_3     52.0f
#define QUERY_1_4    176.0f
/* 1/4's r1 = 1 effect block, in source order. */
#define QUERY_1_4_E0  92.0f
#define QUERY_1_4_E1 262.0f
#define QUERY_1_4_E2  96.0f
#define QUERY_1_4_E3 136.0f
#define QUERY_1_4_E3B 152.0f
#define QUERY_1_4_E4 344.0f
#define QUERY_1_4_E4B 368.0f
#define QUERY_1_4_E5 156.0f
#define QUERY_1_4_E6 190.0f
#define QUERY_1_4_E7 386.0f
#define QUERY_1_4_E8 398.0f
#define QUERY_1_4_E8B 426.0f
#define QUERY_1_4_E9 458.0f
#define QUERY_1_4_E9B 478.0f
#define QUERY_1_4_EA 434.0f
/* 1/5's and 1/8's r1 = 1 effect block, in source order. */
#define QUERY_1_5_E0  12.0f
#define QUERY_1_5_E1  16.0f
#define QUERY_1_5_E1B 40.0f
#define QUERY_1_5_E2  46.0f
#define QUERY_1_5_E3  50.0f
#define QUERY_1_5_E3B 66.0f
#define QUERY_1_5_E4  72.0f
#define QUERY_1_5_E5  76.0f
#define QUERY_1_5_E5B 112.0f

/* The category-0 base handler's category test (0x0082d1cc refuses 0xb). */
static int blocked_logged;

/* #55's open calls: the uEffect039 spawn all eight ids make, and the other unmatched calls.
 * The names are logged once, on the first blocked call, and nothing is invented for them. */
static void log_blocked_effects_once(void) {
    if (blocked_logged) {
        return;
    }
    blocked_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "1/*: #55 blocks the source's effect calls — 0x0016052c (a uEffect039 spawn; MH4U "
             "lacks the class), 0x00161798, 0x00847798 (both need an MH4U trace) and 0x0016669c "
             "(its type-9 factory takes a different argument); 0x005aef18's two-float gate has "
             "no MH4U field pair. The eight ids 1/0, 1/4, 1/5, 1/7, 1/8, 1/9, 1/13 and 1/14 "
             "play without them");
}

/* 0x0083336c(mode, s0, s1): the source tests the return. MH4U's 0x0091aae4 is the same
 * flag-clear wrapper (r3 = r2, r2 = 0), so the call is made with r2 = r3 = 0. */
static int query(MH4UCall *call, uint32_t enemy, uint32_t mode, float s0, float s1) {
    return (int)mhuc_call_f(call, FN_MODE_CLEAR, enemy, mode, 0u, 0u, s0, s1, NULL);
}

/* ── the translated handlers ────────────────────────────────────────────────────────── */

/* 3U 0x00692834, 1/0 and 1/9.
 *   0: state 1, mode 0, the motion 5 at 10.0, the (0, 0x13) call and the accumulator cleared;
 *   1: the 110.0 query twice, the (1, 8, 5) call and the 0x00161798 forward on the first, the
 *      accumulator on the 112.0/214.0 query, then the finish flag and 0/2's base handler. */
static void run_1_0(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_0, 0u, 0u, SPEED_1_0, 0.0f, NULL);
        mhuc_call(call, FN_SET_1_0_2, enemy, 0u, 0x13u, 0u);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        return;
    }
    if (state != 1) {
        return;
    }
    if (query(call, enemy, 0u, QUERY_1_0_A, 0.0f)) {
        mhuc_call(call, FN_SET_1_0, enemy, 1u, 8u, 5u);
        log_blocked_effects_once(); /* 0x00161798 */
    }
    /* the point {0.0, -20.0, 80.0} is built here for the spawn below */
    if (query(call, enemy, 0u, QUERY_1_0_A, 0.0f)) {
        log_blocked_effects_once(); /* 0x0016052c, r2 = 0, s0 = 1.0 */
    }
    if (query(call, enemy, 3u, QUERY_1_0_B, QUERY_1_0_B2)) {
        log_blocked_effects_once(); /* 0x005aef18, then 0x0016052c r2 = 1, s0 = 1.0 */
        const float elapsed = mhuc_f32(call, work + WORK_TIMER);
        mhuc_put_f32(call, work + WORK_TIMER,
                     elapsed + mhuc_f32(call, enemy + ENEMY_DELTA));
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* 3U's inline 1/1 block (0x00686384).
 *   0: state 1, mode 0, the motion 0x12 at 10.0;
 *   1: the finish flag, then 0/2's base handler. */
static void run_1_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_1, 0u, 0u, SPEED_1_1, 0.0f, NULL);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* 3U's inline 1/2 block (0x006863e0).
 *   0: state 1, mode 0, the motion 0x7c (file 1, slot 24) at 2.0;
 *   1: the finish flag, then 0/2's base handler. */
static void run_1_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_2, 0u, 0u, SPEED_1_2, 0.0f, NULL);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* 3U's inline 1/3 block (0x0068643c).
 *   0: state 1, mode 0, the motion 2 at 50.0 (the source also passes a fifth stack argument,
 *      1, that MH4U's motion-start wrapper does not take);
 *   1: the 52.0 query at mode 1, then 0/2's base handler. */
static void run_1_3(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_3, 0u, 0u, SPEED_1_3, 0.0f, NULL);
    } else if (state == 1) {
        if (query(call, enemy, 1u, QUERY_1_3, 0.0f)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* 3U 0x00692a1c, 1/4 and 1/13 (r1 = 0) and 1/7 (r1 = 1).
 *   r1 = 0 calls 0x0083d18c first and returns after the setup; r1 = 1 runs the effect block.
 *   0: state 1, mode 0, the motion 0x13 at 6.0 and the three-second timer;
 *   1: the 176.0 query counts the timer down; while it runs, return; once it is spent, a
 *      request for 1/5 (index 4), 1/0x0e or, with r1 = 1 first, 1/8;
 *   r1 = 1's effect block: the twelve animation queries and their effect spawns. */
static void run_1_4(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    if (variant == 0) {
        mhuc_call(call, FN_1_4_SETUP, enemy, 0u, 0u, 0u);
    }
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_4, 0u, 0u, SPEED_1_4_5, 0.0f, NULL);
        mhuc_put_f32(call, work + WORK_TIMER, DELAY_1_4);
    } else if (state == 1) {
        int waiting;
        if (query(call, enemy, 0u, QUERY_1_4, 0.0f)) {
            waiting = !mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0u, 0u);
        } else {
            waiting = mhuc_f32(call, work + WORK_TIMER) > 0.0f;
        }
        if (!waiting) {
            if (variant == 1) {
                mhuc_call(call, FN_REQUEST_NEXT, enemy, 1u, 8u, 0u);
            } else if (mhuc_read8(call, work + WORK_INDEX) == 4u) {
                mhuc_call(call, FN_REQUEST_NEXT, enemy, 1u, 5u, 0u);
            } else {
                mhuc_call(call, FN_REQUEST_NEXT, enemy, 1u, 0x0eu, 0u);
            }
            return;
        }
    } else {
        return;
    }
    if (variant != 1) {
        return;
    }
    /* the r1 = 1 effect block (0x00692b68): the queries stay, the spawns are #55-blocked.
     * The points are {0.0, -30.0, 70.0} for 0x0016052c and {0.0, 0.0, 50.0} for 0x0016669c. */
    if (query(call, enemy, 0u, QUERY_1_4_E0, 0.0f) ||
        query(call, enemy, 0u, QUERY_1_4_E1, 0.0f)) {
        log_blocked_effects_once(); /* 0x0016052c, r2 = 0x33, s0 = 1.0 */
    }
    if (query(call, enemy, 0u, QUERY_1_4_E2, 0.0f)) {
        log_blocked_effects_once(); /* 0x0016669c, s0 = 1.4 */
    }
    if (query(call, enemy, 3u, QUERY_1_4_E3, QUERY_1_4_E3B) ||
        query(call, enemy, 3u, QUERY_1_4_E4, QUERY_1_4_E4B)) {
        log_blocked_effects_once(); /* 0x00847798, then 0x0016052c r2 = 0x34, s0 = 1.0 */
    }
    if (query(call, enemy, 0u, QUERY_1_4_E5, 0.0f) ||
        query(call, enemy, 0u, QUERY_1_4_E6, 0.0f) ||
        query(call, enemy, 0u, QUERY_1_4_E7, 0.0f)) {
        log_blocked_effects_once(); /* 0x0016052c, r2 = 0x33, s0 = 0.6 */
    }
    if (query(call, enemy, 0u, QUERY_1_4_E1, 0.0f)) {
        log_blocked_effects_once(); /* 0x0016669c, s0 = 1.4 */
    }
    if (query(call, enemy, 3u, QUERY_1_4_E8, QUERY_1_4_E8B) ||
        query(call, enemy, 3u, QUERY_1_4_E9, QUERY_1_4_E9B)) {
        log_blocked_effects_once(); /* 0x00847798, then 0x0016052c r2 = 0x34, s0 = 0.8 */
    }
    if (query(call, enemy, 0u, QUERY_1_4_EA, 0.0f)) {
        log_blocked_effects_once(); /* 0x0016052c, r2 = 0x33, s0 = 0.9 */
    }
}

/* 3U 0x00692f14, 1/5 and 1/14 (r1 = 0) and 1/8 (r1 = 1).
 *   0: state 1, mode 0, the motion 0x14 at 6.0;
 *   1: r1 = 0 waits for the finish flag and falls into 0/2's base handler; r1 = 1 runs the six
 *      animation queries and their effect spawns first. */
static void run_1_5(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_5, 0u, 0u, SPEED_1_4_5, 0.0f, NULL);
        return;
    }
    if (state != 1) {
        return;
    }
    if (variant == 1) {
        /* the points are {0.0, -30.0, 70.0} for every 0x0016052c here. */
        if (query(call, enemy, 0u, QUERY_1_5_E0, 0.0f)) {
            log_blocked_effects_once(); /* r2 = 0x33, s0 = 0.8 */
        }
        if (query(call, enemy, 3u, QUERY_1_5_E1, QUERY_1_5_E1B)) {
            log_blocked_effects_once(); /* 0x00847798, then r2 = 0x34, s0 = 1.0 */
        }
        if (query(call, enemy, 0u, QUERY_1_5_E2, 0.0f)) {
            log_blocked_effects_once(); /* r2 = 0x33, s0 = 0.7 */
        }
        if (query(call, enemy, 3u, QUERY_1_5_E3, QUERY_1_5_E3B)) {
            log_blocked_effects_once(); /* 0x00847798, then r2 = 0x34, s0 = 1.0 */
        }
        if (query(call, enemy, 0u, QUERY_1_5_E4, 0.0f)) {
            log_blocked_effects_once(); /* r2 = 0x33, s0 = 1.0 */
        }
        if (query(call, enemy, 3u, QUERY_1_5_E5, QUERY_1_5_E5B)) {
            log_blocked_effects_once(); /* 0x00847798, then r2 = 0x34, s0 = 1.0 */
        }
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* 3U 0x0069322c, 1/6.
 *   0: state 1, mode 0, the motion 0x17 at 6.0;
 *   1: the finish flag, then state 2, the motion 0x18 at 0.0, the 1800.0 timer and 0x0031be10;
 *   2: the (1, 0xa, 0.6) call, the countdown, then state 3, the motion 0x19 at 4.0 and
 *      0x008440a4;
 *   3: the finish flag, then 0/2's base handler. */
static void run_1_6(MH4UCall *call, uint32_t enemy, uint32_t work) {
    switch ((int)mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6_A, 0u, 0u, SPEED_1_4_5, 0.0f, NULL);
        break;
    case 1:
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6_B, 0u, 0u, SPEED_1_6_B, 0.0f, NULL);
        mhuc_put_f32(call, work + WORK_TIMER, DELAY_1_6);
        mhuc_call(call, FN_1_6_TAIL, enemy, 0u, 0u, 0u);
        break;
    case 2:
        mhuc_call_f(call, FN_1_6_STEP, enemy, 1u, 0x0au, 0u, 0.6f, 0.0f, NULL);
        if (!mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_6_C, 0u, 0u, SPEED_1_6_C, 0.0f, NULL);
        mhuc_call(call, FN_1_6_END, enemy, 0u, 0u, 0u);
        break;
    case 3:
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
        break;
    default:
        break;
    }
}

/* 3U's inline 1/10 block (0x006864dc).
 *   0: state 1, mode 0, the motion 0x11 at 6.0;
 *   1: the finish flag, then 0/2's base handler (0x0082d1cc, cat0's mhuc_3u_base_0_2). */
static void run_1_10(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_10, 0u, 0u, SPEED_1_10, 0.0f, NULL);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* 3U 0x00693388, 1/11 (r1 = 0) and 1/12 (r1 = 1).
 *   0: state 1, mode 0, the 20.0 timer, then motion 1 at 10.0 (r1 = 0) or 0x11 at 6.0 (r1 = 1);
 *   1: the finish flag or the spent timer, then 0/2's base handler. */
static void run_1_11(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_TIMER, DELAY_1_11);
        if (variant == 1) {
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_12, 0u, 0u, SPEED_1_12, 0.0f, NULL);
        } else {
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_1_11, 0u, 0u, SPEED_1_11, 0.0f, NULL);
        }
        return;
    }
    if (state != 1) {
        return;
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
        return;
    }
    if (!mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0u, 0u)) {
        return;
    }
    mhuc_3u_base_0_2(call, enemy, work);
}

/* ── the family's dispatch and self-test ────────────────────────────────────────────── */

/* Runs category 1's handler for the pair, or returns 0 so the module's dispatch can try the
 * next family. The category has fifteen ids and all fifteen are here. */
static int dispatch_cat1(MH4UCall *call, uint32_t enemy, uint32_t work, int category, int index) {
    if (category != 1) {
        return 0;
    }
    switch (index) {
    case 0: case 9: run_1_0(call, enemy, work); return 1;
    case 1: run_1_1(call, enemy, work); return 1;
    case 2: run_1_2(call, enemy, work); return 1;
    case 3: run_1_3(call, enemy, work); return 1;
    case 4: case 13: run_1_4(call, enemy, work, 0); return 1;
    case 5: case 14: run_1_5(call, enemy, work, 0); return 1;
    case 6: run_1_6(call, enemy, work); return 1;
    case 7: run_1_4(call, enemy, work, 1); return 1;
    case 8: run_1_5(call, enemy, work, 1); return 1;
    case 10: run_1_10(call, enemy, work); return 1;
    case 11: run_1_11(call, enemy, work, 0); return 1;
    case 12: run_1_11(call, enemy, work, 1); return 1;
    default: return 0;
    }
}

/* What this family carries: its units, their ids, the frame values, the MH4U counterparts and
 * the #55-blocked calls. The module's self-test calls this with the other families'. */
static void self_test_cat1(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 15 of the 191 actions: category 1's five units and four inline blocks — "
             "1/0 and 1/9 <- 0x00692834 (motion 5 at 10.0, the 110.0/112.0/214.0 queries, the "
             "accumulator, 0/2's base handler); 1/4, 1/7 and 1/13 <- 0x00692a1c (the 3.0 timer "
             "and a request for 1/5, 1/0x0e or 1/8); 1/5, 1/8 and 1/14 <- 0x00692f14 (the six "
             "effect queries); 1/6 <- 0x0069322c (motions 0x17/0x18/0x19 and the 1800.0 timer); "
             "1/11 and 1/12 <- 0x00693388 (the 20.0 timer); 1/1, 1/2, 1/3 and 1/10 inline");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine calls are MH4U's: mode 0x%08x, motion 0x%08x, flag-clear "
              "0x%08x, flag 0x%08x, request 0x%08x, countdown 0x%08x",
              (unsigned)FN_MODE, (unsigned)FN_MOTION, (unsigned)FN_MODE_CLEAR,
              (unsigned)FN_FLAG, (unsigned)FN_REQUEST_NEXT, (unsigned)FN_COUNTDOWN);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: *(this+0x1a48) -> *(this+0xe28), +0x5 -> +0x144, "
             "+0xdf/+0xe0 -> +0x1ca/+0x1cb, +0x28/+0x2c -> +0x1d4, this+0x14 -> this+0x14; "
             "1/2's motion 0x7c is file 1 slot 24");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: #55 blocks 0x0016052c (uEffect039), 0x00161798, 0x00847798 and "
             "0x0016669c, and 0x005aef18's two-float gate has no MH4U field pair; 1/3's fifth "
             "motion-start stack argument is not carried");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat1 = {
    "cat1", 15, dispatch_cat1, self_test_cat1,
};
