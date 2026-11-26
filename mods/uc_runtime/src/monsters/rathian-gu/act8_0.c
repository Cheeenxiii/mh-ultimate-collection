/*
 * act8_0.c: action 8/0's family — three states and the 9/1 or 2/6 combo tail.
 *
 * MHXX's handler 0x0201b460 is the same action as MH4U's own 8/0 handler 0x006e9770, with the
 * same frame values, so the calls below are the MH4U functions MH4U's own handler calls at the
 * same points and the work offsets are MH4U's.
 *   0: set up; copy the monster's data entry (mode 0), aim at the target at 300.0/38.0;
 *   1: per-mode speed/distance at 12.0/50.0; when it holds, advance the position by the
 *      velocity; wait for the finish flag, start motion 0x403 at 4.0 and arm the 180.0
 *      timer;
 *   2: count the timer down by the frame rate; when the pending-action mode is 1, run the
 *      two hit checks (300.0/0.0/150.0) and request 9/1, or request 2/6 when they fail,
 *      the timer is over, or the fallback check is 0.
 *
 * The four gaps are in the runtime README: the leaf 0x008c4184 (MH4U 0x0092f6e8) has no
 * table carried yet, 0x008ae5e4 (MH4U 0x00911c0c) waits on #134, 0x008d0528 has no
 * confirmed MH4U counterpart, and the source's 2/4 tail-flag branch has no MH4U bytes.
 *
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* 8/0's fields, at the offsets MH4U's own 8/0 handler (0x006e9770) uses for the same
 * fields: its state 2 counts down work+0x1d4, reads the pending-action mode at work+0x1d9,
 * and hands the two bytes at +0x278/+0x27c to the hit checks. */
#define WORK_TARGET      0x0218u
#define WORK_TIMER       0x01d4u
#define WORK_PENDING     0x01d9u
#define WORK_BYTE_A      0x0278u
#define WORK_BYTE_B      0x027cu
#define WORK_VELOCITY    0x0160u
#define WORK_FLAG_ZERO_A 0x7738u
#define WORK_FLAG_ZERO_B 0x7739u
#define WORK_FLAG_MODE   0x7a3cu
#define WORK_FLAG_TAIL   0x7993u

/* 8/0's engine calls, each the MH4U function MH4U's own 8/0 handler (0x006e9770) calls
 * at the same point (the source address in the comment). Its data entry and per-mode check
 * are the family's FN_MODE and FN_MODE_CLEAR below. */
#define FN_MOVE_TO      0x00948674u /* 0x008df28c: zero a velocity, aim at a point (s0, s1) */
#define FN_APPLY_MOVE   0x00955440u /* 0x008f1f30: advance the position by the velocity */
#define FN_COUNTDOWN    0x00b0704cu /* 0x008a78ec: count a float down by the frame rate */
#define FN_HIT_CHECK    0x009122fcu /* 0x008ae8ec: hit check, three floats (s0-s2) */
#define FN_HIT_CHECK_R3 0x0092b2b0u /* 0x008c024c: hit check, mode in r3 */
#define FN_REQUEST_NEXT 0x0094ef64u /* 0x008ebab0: request the next action (category, index) */
#define FN_TAIL_DATA    0x0092f6e8u /* 0x008c4184: the leaf, with its data table in r1 */
#define FN_MOTION       0x0094e318u /* 0x008eb108: start a motion (index r1, s0/s1) */
#define FN_MODE         0x009167b4u /* 0x008b1700: set the monster's mode (state 0, mode 0) */
#define FN_MODE_CLEAR   0x0091aae4u /* 0x008a7360: the flag-clear wrapper around 0x00b06b4c */
#define FN_FLAG         0x00b05da4u /* 0x00aed11c: the action's finish flag */

/* 8/0's motion and its frame values (the same constants MH4U's own 8/0 handler passes). */
#define MOTION_8_0 MHUC_MOTION(4, 0x03)

/* The four gaps, logged once per action. */
static int gap_logged;

static void run_8_0(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    if (!gap_logged) {
        gap_logged = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "8/0: 0x008c4184 is MH4U's 0x0092f6e8, but its MHXX table 0x20220ac is "
                 "not carried yet; 0x008d0528 and the 0x8ae5e4 data setup wait on #134");
    }
    /* The stores MHXX's handler makes every frame; MH4U's own 8/0 handler clears the same
     * fields at MH4U's offsets before its state switch. */
    mhuc_write8(call, work + WORK_FLAG_ZERO_A, 0);
    mhuc_write8(call, work + WORK_FLAG_ZERO_B, 0);
    mhuc_write8(call, work + WORK_FLAG_MODE, 2);
    switch (st->state) {
    case 0: {
        st->state = 1;
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        /* 0x008ae5e4 (MH4U 0x00911c0c) takes its 4th and 5th arguments in r3 and on the
         * stack, which ABI 4 cannot set: it waits on #134. */
        mhuc_call_f(call, FN_MOVE_TO, enemy, work + WORK_VELOCITY, work + WORK_TARGET, 0,
                    300.0f, 38.0f, NULL);
        break;
    }
    case 1: {
        if (mhuc_call_f(call, FN_MODE_CLEAR, enemy, 3, 0, 0, 12.0f, 50.0f, NULL)) {
            mhuc_call(call, FN_APPLY_MOVE, enemy, 0, 0, 0);
            /* 0x008c4184's counterpart is MH4U's 0x0092f6e8, but its table (MHXX's
             * 0x20220ac, MH4U's 0x00e094d8) is the port's data, not carried yet. */
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        st->state = 2;
        mhuc_write32(call, work + WORK_TIMER, mhuc_gu_bits_of(180.0f));
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_8_0, 0, 0, 4.0f, 0.0f, NULL);
        break;
    }
    default: {
        mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0, 0);
        if (mhuc_read8(call, work + WORK_PENDING) != 1) {
            return;
        }
        const uint32_t a = mhuc_read8(call, work + WORK_BYTE_A);
        const uint32_t b = mhuc_read8(call, work + WORK_BYTE_B);
        if (!mhuc_call_s2(call, FN_HIT_CHECK, enemy, b, a, 300.0f, 0.0f, 150.0f)) {
            goto timer_check;
        }
        if (!mhuc_call(call, FN_HIT_CHECK_R3, enemy, 1, b, a)) {
            goto timer_check;
        }
        /* MHXX keeps a value of 1 when two enemy bytes are 2/4; the MH4U handler has no
         * such branch, so the port takes the source's other path. 0x008d0528 has no
         * confirmed MH4U counterpart and is not called. */
        mhuc_write8(call, work + WORK_FLAG_TAIL, 3);
        mhuc_call(call, FN_REQUEST_NEXT, enemy, 9, 1, 0);
        return;
    timer_check:
        if (!(mhuc_f32(call, work + WORK_TIMER) > 0.0f)) {
            mhuc_call(call, FN_REQUEST_NEXT, enemy, 2, 6, 0);
            return;
        }
        if (mhuc_call(call, FN_HIT_CHECK_R3, enemy, 0, b, a)) {
            return;
        }
        mhuc_call(call, FN_REQUEST_NEXT, enemy, 2, 6, 0);
        break;
    }
    }
}

/* Runs 8/0's handler for the pair, or returns 0 so the module's dispatch can try the next
 * family. */
static int dispatch_act8_0(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                           int index) {
    if (category != 8 || index != 0) {
        return 0;
    }
    MhucState *st = mhuc_gu_state(call, enemy, category, index);
    if (!st) {
        return 0;
    }
    run_8_0(call, enemy, work, st);
    return 1;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_gu_family_act8_0 = {
    "act8_0", 1, dispatch_act8_0, 0,
};
