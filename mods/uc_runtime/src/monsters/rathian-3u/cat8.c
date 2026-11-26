/*
 * cat8.c: 3U Rathian's category 8 — id 8, on her handler 0x00687074.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending. The handler, its frame values and its call order are
 * the ones issue #225 translated.
 *
 * 8 is one of the action ids MH4U also has, and its MH4U handler (0x006e9770, the pair
 * monster_actions.py finds) does the same move with MH4U's own constants. Under decision
 * 0002's 2026-11-26 amendment the port runs the source's handler with the source's values:
 * 8's frame values are 300.0/38.0 for the aim, 12.0/50.0 for the distance test, a 90.0 timer,
 * motion 0xca at 90.0, the hit check at 300.0/0.0/150.0, and the tail's request for 9/1 or
 * 2/6.
 *
 * 8 reaches four of #55's nineteen calls, each left out and logged once:
 *   0x00853c70  every frame at entry: sets a halfword at 3U work+0x89c to 2;
 *   0x00839598  3U work+0xef's signed byte, the state-2 gate;
 *   0x0084512c  the target's part/action check before the tail;
 *   0x00257628  a byte on the object at a global's +0x14.
 * The source's other data, the action-start list 0x00b0b0e8 that 0x0082d278 and 0x0082d430
 * pass, is not carried either: the port passes MH4U's own list 0x00e094d8, which is what
 * MH4U's own 8/0 handler passes (the same step the category 0 base handlers take with the
 * action setter's per-action value, #55's open item).
 *
 * Three calls into her class's own helpers are translated here, because the source's handler
 * reaches them and MH4U's handler delegates their steps to engine functions at the same
 * points: 0x0068d070 (the aim, MH4U 0x00948674), 0x00687ae0 (the hit check, MH4U
 * 0x009122fc), and 0x0068d940 (the part/effect step, MH4U's 0x0092e960, 0x00944c34 or 0x0091b7b0
 * and 0x0093b9ec). The last one's inner guard 0x008532a0 has no confirmed counterpart; the
 * port calls the accumulator as MH4U's own 9/0 handler does (its 8/0 uses 0x0093ba88, the same
 * clamp with its delta step) and says so once.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U); the field map is in
 * the runtime's README.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE      0x0144u  /* 3U +0x5:  the handler's state byte */
#define WORK_SUB        0x0145u  /* 3U +0x6:  its sub-state */
#define WORK_TIMER      0x01d4u  /* 3U +0x28: the 90.0 timer (MH4U's own 8/0 uses it) */
#define WORK_TAIL       0x7993u  /* 3U +0xe1: the tail flag, set to 3 for 9/1 */
#define WORK_CAP        0x03ecu  /* 3U +0x7fc: the count the part step scales by 0.015 */
#define WORK_SIDE       0x0278u  /* the hit check's side/mode byte (MH4U's own 8/0 reads it) */
#define WORK_PART       0x027cu  /* 3U +0x2b6: the hit check's target index */
#define WORK_TARGET     0x0218u  /* 3U +0x288: the target point (MH4U's own 8/0 names it) */
#define WORK_AIM        0x0160u  /* 3U +0x260: aim point A (MH4U's own 8/0 names it) */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_MODE        0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_DATA_SETUP  0x00911c0cu /* [0x0082d278] the action-start data setup (list in r1,
                                    * r3 = 1 and the fifth argument on the stack) */
#define FN_AIM         0x00948674u /* [0x0068d070] aim point A at the target (s0, s1) */
#define FN_RANGE       0x0091aae4u /* [0x0083336c] the distance/height test (r1; s0, s1) */
#define FN_ADVANCE     0x00955440u /* [0x0082b268] advance the position by aim point A */
#define FN_TAIL_DATA   0x0092f6e8u /* [0x0082d430] the action-start leaf (list in r1) */
#define FN_FLAG        0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_MOTION      0x0094e318u /* [0x00828828] start a motion (r1; s0 = speed, s1) */
#define FN_COUNTDOWN   0x00b0704cu /* the source's inline timer subtraction */
#define FN_HIT_CHECK   0x009122fcu /* [0x00687ae0] the hit check (s0 range, s2 height) */
#define FN_REQUEST     0x0094ef64u /* [0x0082a06c] request the next action (category, index) */
#define FN_STATE_TEST  0x0092e960u /* [0x00844100] the monster's state is 2 or 3 */
#define FN_RATE_ACCUM  0x00944c34u /* [0x00853b98] advance and clamp the state's rate */
#define FN_PART_STEP   0x0091b7b0u /* [0x008345f8] the part-state step (r1 = 0x32) */
#define FN_APPLY_VALUE 0x0093b9ecu /* [0x0083c7a0] accumulate the per-action value, clamped */

/* MH4U's own action-start list for 8/0, which MH4U's own handler (0x006e9770) passes to
 * 0x00911c0c and 0x0092f6e8. The source's 0x00b0b0e8 is her data and is not carried. */
#define MH4U_ACTION_LIST 0x00e094d8u

/* The source's frame values, kept as the source passes them. The 150.0 hit check and the
 * 300.0/38.0 aim are MH4U's own 8/0 values too; the 90.0 timer and motion speed are 3U's. */
#define AIM_SPEED      300.0f
#define AIM_HEIGHT      38.0f
#define RANGE_SPEED     12.0f
#define RANGE_HEIGHT    50.0f
#define ADVANCE_HALF     0.5f   /* 0x82b268's fixed 0.5, which 0x955440 lacks */
#define TIMER_3U        90.0f
#define MOTION_SPEED    90.0f
#define HIT_RANGE      300.0f
#define HIT_HEIGHT     150.0f
#define HIT_UNUSED       0.0f

/* 8's motion, in MH4U's `file << 8 | slot` form: 3U 0xca, file 0 slot 0xca. */
#define MOTION_8       0xcau

#define REQUEST_9_1    9u, 1u   /* the tail when the hit lands */
#define REQUEST_2_6    2u, 6u   /* the tail when it does not */

/* The source's part-step input and the count's scale (0x015 as a double in 3U's image). */
#define PART_STEP_ARG 0x32u
#define CAP_SCALE      0.015

/* ── the blocked calls (#55) ─────────────────────────────────────────────────────────── */

static int blocked_entry_logged;
static int blocked_gate_logged;
static int blocked_part_logged;
static int blocked_object_logged;
static int guard_logged;

static void log_blocked_entry(void) {
    if (blocked_entry_logged) {
        return;
    }
    blocked_entry_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "8: 3U's 0x00853c70 (the halfword at work+0x89c set to 2, every frame at entry) "
             "is not carried (#55); the halfword has no mapped MH4U offset");
}

static void log_blocked_gate(void) {
    if (blocked_gate_logged) {
        return;
    }
    blocked_gate_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "8: 3U's 0x00839598 (the signed byte at work+0xef, state 2's gate) is not carried "
             "(#55); the port takes its nonzero path so the action cannot stall");
}

static void log_blocked_part(void) {
    if (blocked_part_logged) {
        return;
    }
    blocked_part_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "8: 3U's 0x0084512c (the target's part/action check before the tail, "
             "work+0x2b6) is not carried (#55); the port takes its nonzero path, so the hit "
             "sets the tail flag and asks for 9/1");
}

static void log_blocked_object(void) {
    if (blocked_object_logged) {
        return;
    }
    blocked_object_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "8: 3U's 0x00257628 (a byte on the object at global 0x00c3b9cc +0x14) is not "
             "carried (#55); state 0 ends after the aim without it");
}

/* 0x0068d940's 0x0083c7a0 calls 0x008532a0 as its guard, which has no confirmed MH4U
 * counterpart; MH4U's own 9/0 handler calls the accumulator without one (its 8/0 uses
 * 0x0093ba88, the same clamp with its delta step). */
static void log_guard(void) {
    if (guard_logged) {
        return;
    }
    guard_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "8: 3U's 0x0083c7a0 guards its accumulator with 0x008532a0, which has no "
             "confirmed MH4U counterpart; the port calls 0x0093b9ec directly as MH4U's own "
             "9/0 handler does (its 8/0 uses 0x0093ba88, the same clamp with a delta step)");
}

/* ── the class helpers 8 reaches ────────────────────────────────────────────────────── */

/* 3U 0x0068d070: the aim. Its body fills aim point A from the target and the rate; MH4U's
 * own 8/0 handler calls 0x00948674 with the same two points and the same 300.0/38.0 at the
 * same point. */
static void aim_at_target(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call_f(call, FN_AIM, enemy, work + WORK_AIM, work + WORK_TARGET, 0u, AIM_SPEED,
                AIM_HEIGHT, NULL);
}

/* 3U 0x0068d940: the hit's part/effect step. It computes a value from the action's count
 * (0.015 x work+0x7fc, an int16) and then, through 0x0083c7a0, accumulates it clamped. The
 * state test and the two rate/part branches are the same block MH4U's own 8/0 and 9/0
 * handlers run before their accumulator (0x0092e960, then 0x00944c34 at -900 or 0x0091b7b0
 * at 0x32, then 0x0093b9ec). */
static void hit_step(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int32_t count = (int32_t)mhuc_read32(call, work + WORK_CAP);
    const int16_t value = (int16_t)(int)((double)count * CAP_SCALE);
    if (mhuc_call(call, FN_STATE_TEST, enemy, 0u, 0u, 0u)) {
        mhuc_call_f(call, FN_RATE_ACCUM, enemy, 0u, 0u, 0u, -900.0f, 0.0f, NULL);
    } else {
        mhuc_call(call, FN_PART_STEP, enemy, PART_STEP_ARG, 0u, 0u);
    }
    log_guard();
    mhuc_call(call, FN_APPLY_VALUE, enemy, (uint32_t)(int32_t)value, 0u, 0u);
}

/* 3U 0x00687ae0: the hit check. It takes the target's list index (3U work+0x2b6) and tests
 * the horizontal distance against 300.0 x the rate and the vertical difference against 150.0;
 * MH4U's 0x009122fc does the same steps at the same point in MH4U's own 8/0 and 9/0 handlers.
 * The source's index byte has no settled MH4U offset (3U +0x2b6 is +0x27c or +0x278); the
 * port passes MH4U's own +0x27c in r1 and +0x278 in r2, the pair MH4U's handlers pass. */
static int hit_check(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const uint32_t target = mhuc_read8(call, work + WORK_PART);
    const uint32_t side = mhuc_read8(call, work + WORK_SIDE);
    return mhuc_call_s2(call, FN_HIT_CHECK, enemy, target, side, HIT_RANGE, HIT_UNUSED,
                        HIT_HEIGHT) != 0u;
}

/* ── the translated handler ────────────────────────────────────────────────────────── */

/* 3U 0x00687074, id 8. Three states on work+0x5:
 *   0: state 1, mode 0, the action-start data setup with MH4U's own list, the aim at the
 *      target at 300.0/38.0, then 0x00257628 (blocked);
 *   1: the 12.0/50.0 distance test; when it holds, advance the position by 0.5 and run the
 *      action-start leaf; on the finish flag, state 2, the 90.0 timer and motion 0xca at
 *      90.0;
 *   2: count the timer down and clamp it at 0; 0x00839598 (blocked, taken nonzero); the hit
 *      check at 300.0/0.0/150.0, or 2/6 when it fails; 0x0084512c (blocked, taken nonzero);
 *      the tail flag 3, the part step and the request for 9/1. */
static void run_8(MH4UCall *call, uint32_t enemy, uint32_t work) {
    log_blocked_entry();
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_call5(call, FN_DATA_SETUP, enemy, MH4U_ACTION_LIST, 0u, 1u, 0u);
        aim_at_target(call, enemy, work);
        log_blocked_object();
        return;
    }
    if (state == 1) {
        if (mhuc_call_f(call, FN_RANGE, enemy, 3u, 0u, 0u, RANGE_SPEED, RANGE_HEIGHT, NULL)) {
            mhuc_call_f(call, FN_ADVANCE, enemy, 0u, 0u, 0u, ADVANCE_HALF, 0.0f, NULL);
            mhuc_call(call, FN_TAIL_DATA, enemy, MH4U_ACTION_LIST, 0u, 0u);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_put_f32(call, work + WORK_TIMER, TIMER_3U);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_8, 0u, 0u, MOTION_SPEED, 0.0f, NULL);
        return;
    }
    if (state != 2) {
        return;
    }
    mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0u, 0u);
    if (mhuc_f32(call, work + WORK_TIMER) < 0.0f) {
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
    }
    log_blocked_gate();
    if (!hit_check(call, enemy, work)) {
        mhuc_call(call, FN_REQUEST, enemy, REQUEST_2_6, 0u);
        return;
    }
    log_blocked_part();
    mhuc_write8(call, work + WORK_TAIL, 3u);
    hit_step(call, enemy, work);
    mhuc_call(call, FN_REQUEST, enemy, REQUEST_9_1, 0u);
}

/* ── the family's dispatch and self-test ────────────────────────────────────────────── */

/* Runs 8's handler for the pair, or returns 0 so the module's dispatch can try the next
 * family. The source's category-8 case block runs 0x00687074 for index 0 only. */
static int dispatch_cat8(MH4UCall *call, uint32_t enemy, uint32_t work, int category, int index) {
    if (category != 8 || index != 0) {
        return 0;
    }
    run_8(call, enemy, work);
    return 1;
}

/* What this family carries: the one id, its three states, its frame values and the four #55
 * calls it leaves out. The module's self-test calls this with the others'. */
static void self_test_cat8(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 1 of the 191 actions: 8 <- 0x00687074 (mode 0 and the action-start "
             "data setup; the aim at 300.0/38.0; the 12.0/50.0 distance test and the position "
             "advance at 0.5; the finish flag, a 90.0 timer and motion 0xca at 90.0; the "
             "300.0/0.0/150.0 hit check, the part step and 9/1 or 2/6)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine calls are MH4U's: mode 0x%08x, data setup 0x%08x, aim "
              "0x%08x, range 0x%08x, advance 0x%08x, leaf 0x%08x, flag 0x%08x, motion 0x%08x, "
              "hit check 0x%08x, request 0x%08x, part step 0x%08x/0x%08x/0x%08x",
              (unsigned)FN_MODE, (unsigned)FN_DATA_SETUP, (unsigned)FN_AIM, (unsigned)FN_RANGE,
              (unsigned)FN_ADVANCE, (unsigned)FN_TAIL_DATA, (unsigned)FN_FLAG,
              (unsigned)FN_MOTION, (unsigned)FN_HIT_CHECK, (unsigned)FN_REQUEST,
              (unsigned)FN_STATE_TEST, (unsigned)FN_RATE_ACCUM, (unsigned)FN_APPLY_VALUE);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: the work block *(this+0x1a48) -> *(this+0xe28), "
             "+0x5/+0x6 -> +0x144/+0x145, +0x28 -> +0x1d4, +0xe1 -> +0x7993, +0x7fc -> +0x3ec, "
             "+0x260/+0x288 -> +0x160/+0x218, +0x2b6 -> +0x27c");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: 8 reaches four of #55's nineteen (0x00853c70, 0x00839598, "
             "0x0084512c, 0x00257628), and the action-start list is MH4U's own 0x00e094d8");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat8 = {
    "cat8", 1, dispatch_cat8, self_test_cat8,
};
