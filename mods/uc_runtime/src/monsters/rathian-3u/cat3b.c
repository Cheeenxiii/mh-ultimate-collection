/*
 * cat3b.c: 3U Rathian's ground actions, part 2 — 3/6, 3/7, 3/8, 3/12, 3/13, 3/16,
 * 3/17, 3/18, 3/19, 3/20, 3/21, 3/24, 3/25, 3/27, 3/28 and 3/29.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending. The handlers, their frame values and their call
 * order are the ones issue #220 translated.
 *
 * Four of her own handler units serve the sixteen ids (the arguments on each follow the case
 * block's tail call, i217's inventory):
 *   0x0068e448  r1, r2 = (0,0) 3/6, (1,0) 3/13, (0,1) 3/16
 *   0x0068e5e8  r1 = 0..5      3/7, 3/17, 3/18, 3/19, 3/24, 3/28
 *   0x0068e6e4  r1 = 0..4      3/12, 3/20, 3/21, 3/25, 3/29
 *   0x0068e8c8  —              3/27
 * and 3/8's handler 0x0082b37c is uEnemy base-class code, reimplemented here (0002's second
 * amendment). The two base handlers this family falls into, 0/3's 0x00858b6c and 0/2's
 * 0x0082d1cc, are cat0.c's (mhuc_3u_base_0_3 and mhuc_3u_base_0_2).
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The field map's rows
 * this family uses are marked on the defines below; the engine-call map is in the runtime's
 * README ([3U Rathian's module: category 0] and the sections after it).
 *
 * Two calls #55 still blocks are reached here, and each is logged once (see the log text):
 *   0x0064325c  in 3/6 and 3/16 (3/13 takes the other branch), a per-monster height value;
 *   0x00839598  in 3/8's fourth state, the signed byte at 3U work+0xef.
 * Both are left out and the port takes the branch that ends the action rather than stalling.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <string.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE          0x0144u  /* 3U +0x5:  the handler's state byte */
#define WORK_SUB            0x0145u  /* 3U +0x6:  its sub-state */
#define WORK_SUB2           0x0146u  /* 3U +0x7:  its third sub-state */
#define WORK_MODE           0x01c8u  /* 3U +0xdc: the mode byte */
#define WORK_CATEGORY       0x01cau  /* 3U +0xdf: the current category */
#define WORK_SET            0x01dcu  /* 3U +0xf2: "the action was set" */
#define WORK_TURN           0x01a8u  /* 3U +0x80: the turn slot 0x839ea0 turns */
#define WORK_AIM_Y          0x0164u  /* 3U +0x264: aim point A y */
#define WORK_AIM_Z          0x0168u  /* 3U +0x268: aim point A z */
#define WORK_AIM_B_Z        0x0178u  /* 3U +0x278: aim vector B z */
#define WORK_TARGET_Z       0x0220u  /* 3U +0x28c: the target point z */
#define WORK_POS_Y          0x019cu  /* 3U +0x3c: position y */
#define WORK_VERTICAL_LIMIT 0x0624u  /* 3U +0x120: the vertical limit 0x8509a0's loop uses */
#define WORK_MARKED         0x03c4u  /* 3U +0x7c9: the "flying" byte 0x8310f0 sets */
#define WORK_KIND           0x01c0u  /* 3U +0x3: the data record's kind (3/27's switch) */
#define WORK_ALT            0x014cu  /* 3U +0xdb: the selector 0x0064325c indexed */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_FLY          0x00922ca0u /* [0x0083d18c] set the action's flying byte */
#define FN_DATA_FLOAT   0x0093d870u /* [0x00852324] the action data's float, in s0 */
#define FN_APPLY_FALL   0x0092e99cu /* [0x00844124] advance the fall by s0, set mode 1 */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion (r1; s0 = speed, s1) */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_RATE         0x00923f90u /* [0x0083db3c] the rate 0x83db3c returns, in s0 */
#define FN_CLEAR_AIM    0x0096e164u /* [0x00839968, 0x0084d790] clear the aim points A and B */
#define FN_RANGE        0x0091aae4u /* [0x0083336c] the distance/height test (r1; s0, s1) */
#define FN_TURN_TO      0x0091db4cu /* [0x008357b0] turn toward the target at a rate in r1 */
#define FN_TURN_HOLD    0x0091b430u /* [0x00839ea0] turn and hold at the vertical limit */
#define FN_POINT_TURN   0x0092dcccu /* [0x008438e8] turn the two joints by a rate in r2 */
#define FN_SETUP_POINT  0x0092dc50u /* [0x008437f4] set up a turn's point */
#define FN_TURN2        0x0092fc84u /* [0x0083d884] turn the two joints toward the point */
#define FN_MODE         0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_START_ACTION 0x00935a90u /* [0x0084dc84] start an action (category, index, 2) */
#define FN_NEXT_ACTION  0x0094ef64u /* [0x0082a06c] request the next action (category, index) */
#define FN_CURVE        0x00922250u /* [0x0083c6e0] evaluate a value curve at the speed */
#define FN_ADVANCE_POS  0x00955440u /* [0x0082b268] advance the position by aim point A */
#define FN_CLEAR_AIM_A  0x00916228u /* [0x0082fc8c] clear aim point A only */
#define FN_SHELL        0x00914dc4u /* [0x00844a38] spawn the shared shell (r1, r2) */
#define FN_PREP_FALL    0x0093cd70u /* [0x008509a0] the 3/27 fall/height setup */
#define FN_PREP_TURN    0x0093ce60u /* [0x00850a50] the 3/27 turn and descent */
#define FN_CHECK        0x00942220u /* [0x0083369c] the height test, returns a flag */
#define FN_TURN_DESCEND 0x00938f6cu /* [0x0084d7e4] turn and descend */

/* The 3/6, 3/13 and 3/16 value curve. MH3U's is at 0x00c4eca8 and MH4U's own 3/6 handler
 * passes 0x00fd18a0 to 0x00922250; the two curves' keys are equal (checked key by key), so
 * MH4U's own curve is the converted one and the port passes it: no 3U data is carried. */
#define CURVE_3_6       0x00fd18a0u

/* The source's frame values, kept as the source passes them. The two rates halve because 3U's
 * turn helpers (0x8392d8) multiply by 0.5 where MH4U's (0x0091aaf0) do not; the position
 * advance halves for the same reason (0x82b268 multiplies the delta by 0.5, 0x00955440 does
 * not), so 0x82b268's s0 = 1.0 becomes 0.5. */
#define MOTION_SPEED     6.0f
#define RATE_3_8       500.0f
#define ADVANCE_HALF   0.5f      /* 0x82b268's fixed 0.5, which 0x00955440 lacks */
#define TURN_RATE_3_7 0x100u     /* 3U 0x200 halved for MH4U's turn helper */
#define TURN_RATE_TWO 0x80u      /* 3U 0x100 halved, 0x83d884's two joints */
#define TURN_RATE_ONE 0x40u      /* 3U 0x80 halved, 0x8438e8's rate */
#define TURN_SPEED    70.0f      /* 3/12's 0x83336c s0 */
#define TURN_SPEED_3_8 30.0f     /* 3/8's 0x83336c s0 */
#define CLAMP_3_12    90.0f      /* 3/12's aim A z clamp */
#define CLAMP_3_8     70.0f      /* 3/8's aim A z clamp */
#define AIM_A_Y_3_12   5.0f
#define AIM_B_Z_3_12   3.0f
#define AIM_A_Y_3_8    5.0f
#define AIM_B_Z_3_8    3.0f
#define AIM_A_Y_DOWN (-10.0f)    /* 3/8 state 3's aim A y */
#define AIM_B_Z_DOWN (-3.2f)     /* 3/8 state 3's aim B z */
#define AIM_B_Z_3_8_4 (-6.8f)    /* 3/8 state 4's aim B z */
#define SETUP_HEIGHT (-300.0f)   /* 3/8's 0x8437f4 s0 */
#define LIMIT_BIAS   1000.0f     /* 3/6's blocked height value minus 1000 */
#define LIMIT_OVER   2000.0f     /* the target kept this far above the vertical limit */
#define TARGET_Z_BIAS 1300.0f    /* 3/13's target z plus 1300 */

/* The two base-class handlers' kind for their action start, and 0/3's record field (cat0.c's
 * set_action passes MH4U's per-action value; the source's 0x008412cc is #55's open item). */
#define ACTION_KIND 2u

/* The source's request ids: the motions its handlers start and the next actions they ask for.
 * A motion number is MH4U's `file << 8 | slot`; the three below 100 are file 0's slots (the
 * two games number file 0 the same), 0xcf and 0xe1 are 3U's file 2 slots 7 and 25. */
#define MOTION_3_6    0x1au
#define MOTION_3_7    0x1au
#define MOTION_3_8_A  0x2du
#define MOTION_3_8_B  0x3du
#define MOTION_3_8_C  0x3eu
#define MOTION_3_12   0x3du
#define MOTION_3_27_A 0x1au
#define MOTION_3_27_B 0x1du
#define MOTION_3_27_C 0x207u   /* 3U 0xcf: file 2, slot 7 */
#define MOTION_3_27_D 0x219u   /* 3U 0xe1: file 2, slot 25 */

#define NEXT_3_7_2    0x14u    /* 3/17 */
#define NEXT_3_7_3    0x15u    /* 3/18 */
#define NEXT_3_7_4    0x19u    /* 3/19 */
#define NEXT_3_7_5    0x1du    /* 3/28 */
#define NEXT_3_12_1   0x16u    /* 3/20 */
#define NEXT_3_12_2   0x17u    /* 3/21 */
#define NEXT_3_12_3   0x1au    /* 3/25 */
#define NEXT_3_12_4   0x1eu    /* 3/29 */
#define NEXT_3_12_DEF 0x0bu    /* 3/12 starts 3/11 through FN_START_ACTION */

/* ── the blocked calls (#55) ─────────────────────────────────────────────────────────── */

static int blocked_3_6_logged;
static int blocked_3_8_logged;

/* 3U 0x0064325c is one of #55's nineteen: it maps work+0xdb through a table and returns a
 * per-monster height from the monster's data block, and MH4U has no function with those steps.
 * The port skips it and takes its result as 0.0, so the target is the vertical limit plus
 * 2000 (the branch the source takes for a value below the limit) until #55 settles it. */
static void log_blocked_3_6(void) {
    if (blocked_3_6_logged) {
        return;
    }
    blocked_3_6_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "3/6 and 3/16: 3U's 0x0064325c (the per-monster height through work+0xdb) is "
             "not carried (#55); the height target is the vertical limit + 2000 for now");
}

/* 3U 0x00839598 returns the signed byte at 3U work+0xef; MH4U has no counterpart (#55, the 28
 * with no MH4U function). The port takes the source's nonzero path so the action ends in 0/3's
 * base handler instead of stalling: a handler that never ends its action freezes the AI. */
static void log_blocked_3_8(void) {
    if (blocked_3_8_logged) {
        return;
    }
    blocked_3_8_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "3/8: 3U's 0x00839598 (the signed byte at work+0xef) is not carried (#55); the "
             "port takes its nonzero path and ends in 0/3's base handler");
}

static uint32_t float_bits(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

/* ── shared steps ────────────────────────────────────────────────────────────────────── */

static void motion(MH4UCall *call, uint32_t enemy, uint32_t number) {
    mhuc_call_f(call, FN_MOTION, enemy, number, 0u, 0u, MOTION_SPEED, 0.0f, NULL);
}

static void data_float(MH4UCall *call, uint32_t enemy, float *out) {
    if (out) {
        *out = 0.0f;
    }
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, out);
}

/* The data float, then 0x844124 advancing the fall by it (the pair 0/3's case block uses). */
static void data_float_and_fall(MH4UCall *call, uint32_t enemy) {
    float data;
    data_float(call, enemy, &data);
    mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
}

/* 3U 0x839ea0(this, &work+0x80, s0, s1): the wrapper hands s1 to 0x834098 and s0 to
 * 0x839540. MH4U's 0x0091b430 has one float, which its own handlers pass the data float in,
 * and it ignores it; the port passes the data float in s0 and 1.0 in s1 as the source does,
 * and its r0 is 0x839540's "reached the limit" flag (0x00922b34's in MH4U). */
static uint32_t turn_hold(MH4UCall *call, uint32_t enemy, uint32_t work, float data) {
    return mhuc_call_f(call, FN_TURN_HOLD, enemy, work + WORK_TURN, 0u, 0u, data, 1.0f, NULL);
}

/* ── 3U 0x0068e448: 3/6, 3/13 and 3/16 ──────────────────────────────────────────────── */

/*   0: state 1, sub and third 0, the data float, the fall, the request for motion 0x1a at
 *      6.0, then clear aim point A;
 *   1: sub 0 — the value curve at the speed into aim A y, the position advance, then the
 *      flag: the third sub-state counts two flags and then moves to sub 1 with the aim
 *      cleared; sub 1 — the turn and descent;
 *      then the height test: r1 = 0 takes the blocked 0x0064325c branch, r1 = 1 compares
 *      position y with target z + 1300; when y is not below it, 0/3's base handler. */
static void run_3_6(MH4UCall *call, uint32_t enemy, uint32_t work, int arg1, int arg2) {
    if (arg2 == 1) {
        mhuc_call(call, FN_FLY, enemy, 0u, 0u, 0u);
    }
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_write8(call, work + WORK_SUB2, 0u);
        data_float_and_fall(call, enemy);
        motion(call, enemy, MOTION_3_6);
        mhuc_call(call, FN_CLEAR_AIM_A, enemy, 0u, 0u, 0u);
        return;
    }
    if (state != 1) {
        return;
    }
    const int sub = (int)mhuc_read8(call, work + WORK_SUB);
    if (sub == 0) {
        float curve = 0.0f;
        mhuc_call_f(call, FN_CURVE, enemy, CURVE_3_6, 0u, 0u, 0.0f, 0.0f, &curve);
        mhuc_put_f32(call, work + WORK_AIM_Y, curve);
        mhuc_call_f(call, FN_ADVANCE_POS, enemy, 0u, 0u, 0u, ADVANCE_HALF, 0.0f, NULL);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            const uint32_t third = (mhuc_read8(call, work + WORK_SUB2) + 1u) & 0xffu;
            mhuc_write8(call, work + WORK_SUB2, third);
            if (third >= 2u) {
                mhuc_write8(call, work + WORK_SUB, (uint32_t)(sub + 1));
                mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
            }
        }
    } else if (sub == 1) {
        mhuc_call(call, FN_TURN_DESCEND, enemy, 0u, 0u, 0u);
    }
    if (arg1 == 1) {
        const float target = mhuc_f32(call, work + WORK_TARGET_Z) + TARGET_Z_BIAS;
        if (mhuc_f32(call, work + WORK_POS_Y) < target) {
            return;
        }
    } else {
        log_blocked_3_6();
        float target = 0.0f - LIMIT_BIAS;
        const float limit = mhuc_f32(call, work + WORK_VERTICAL_LIMIT);
        if ((int32_t)float_bits(target - limit) < (int32_t)0x44fa0000u) {
            target = limit + LIMIT_OVER;
        }
        if (mhuc_f32(call, work + WORK_POS_Y) < target) {
            return;
        }
    }
    mhuc_3u_base_0_3(call, enemy, work);
}

/* ── 3U 0x0068e5e8: 3/7, 3/17, 3/18, 3/19, 3/24 and 3/28 ──────────────────────────── */

/*   0: state 1, the data float, the fall, the request for motion 0x1a at 6.0;
 *   1: the turn toward the target at 0x200 (3U's rate, halved as MH4U's helper takes it, and
 *      scoped to the turn slot); when it arrives, r1 2 to 5 ask the next action 3/0x14,
 *      3/0x15, 3/0x19 and 3/0x1d, and 0 and 1 fall into 0/3's base handler. */
static void run_3_7(MH4UCall *call, uint32_t enemy, uint32_t work, int arg1) {
    if (arg1 == 1) {
        mhuc_call(call, FN_FLY, enemy, 0u, 0u, 0u);
    }
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        data_float_and_fall(call, enemy);
        motion(call, enemy, MOTION_3_7);
        return;
    }
    if (state != 1) {
        return;
    }
    if (!mhuc_call(call, FN_TURN_TO, enemy, TURN_RATE_3_7, 0u, 0u)) {
        return;
    }
    switch (arg1) {
    case 2: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_7_2, 0u); return;
    case 3: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_7_3, 0u); return;
    case 4: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_7_4, 0u); return;
    case 5: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_7_5, 0u); return;
    default: mhuc_3u_base_0_3(call, enemy, work); return;
    }
}

/* ── 3U 0x0068e6e4: 3/12, 3/20, 3/21, 3/25 and 3/29 ────────────────────────────────── */

/*   0: state 1, sub 0, the data float, the fall, the request for motion 0x3d at 6.0;
 *   1: sub 0 — the 70.0 distance test, then aim A z 5.0 and aim B z 3.0 with the aim
 *      cleared; sub 1 — the data float and the turn, aim A z clamped at 90.0; then the flag:
 *      r1 1 to 4 ask the next action 3/0x16, 3/0x17, 3/0x1a and 3/0x1e, and r1 0 starts
 *      3/11 (0x0084dc84) and sets the action's set byte (0x0083b424). */
static void run_3_12(MH4UCall *call, uint32_t enemy, uint32_t work, int arg1) {
    mhuc_call(call, FN_FLY, enemy, 0u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        data_float_and_fall(call, enemy);
        motion(call, enemy, MOTION_3_12);
        return;
    }
    if (state != 1) {
        return;
    }
    const int sub = (int)mhuc_read8(call, work + WORK_SUB);
    if (sub == 0) {
        if (mhuc_call_f(call, FN_RANGE, enemy, 1u, 0u, 0u, TURN_SPEED, 0.0f, NULL)) {
            mhuc_write8(call, work + WORK_SUB, 1u);
            mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
            mhuc_put_f32(call, work + WORK_AIM_Z, AIM_A_Y_3_12);
            mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_3_12);
        }
    } else if (sub == 1) {
        float data;
        data_float(call, enemy, &data);
        turn_hold(call, enemy, work, data);
        if (mhuc_f32(call, work + WORK_AIM_Z) > CLAMP_3_12) {
            mhuc_put_f32(call, work + WORK_AIM_Z, CLAMP_3_12);
        }
    }
    if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        return;
    }
    switch (arg1) {
    case 1: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_12_1, 0u); return;
    case 2: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_12_2, 0u); return;
    case 3: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_12_3, 0u); return;
    case 4: mhuc_call(call, FN_NEXT_ACTION, enemy, 3u, NEXT_3_12_4, 0u); return;
    default:
        data_float_and_fall(call, enemy);
        mhuc_call(call, FN_START_ACTION, enemy, 3u, NEXT_3_12_DEF, 0u);
        mhuc_write8(call, work + WORK_SET, 1u);
        return;
    }
}

/* ── 3U 0x0068e8c8: 3/27 ────────────────────────────────────────────────────────────── */

/*   0: state 1, the data float, the fall, the request for motion 0x1a at 6.0, then the fall
 *      and height setup 0x8509a0;
 *   1: the turn and descent 0x850a50, the data float, the height test 0x83369c; when it
 *      passes, state 2, mode 3 and motion 0x1d;
 *   2: the flag, then mode 0 and the data record's kind: 0x3e, 0x3f and 1 start motion
 *      0xcf (MH4U 0x0207), 2, 0x40 and 0x41 start 0xe1 (MH4U 0x0219); then the shell 0x844a38
 *      and the flying flag 0x83d18c;
 *   3: the flag, then 0/2's base handler. */
static void run_3_27(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        data_float_and_fall(call, enemy);
        motion(call, enemy, MOTION_3_27_A);
        mhuc_call(call, FN_PREP_FALL, enemy, 0u, 0u, 0u);
        return;
    }
    if (state == 1) {
        float data;
        mhuc_call(call, FN_PREP_TURN, enemy, 0u, 0u, 0u);
        data_float(call, enemy, &data);
        if (!mhuc_call_f(call, FN_CHECK, enemy, 0u, 0u, 0u, data, 0.0f, NULL)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        motion(call, enemy, MOTION_3_27_B);
        return;
    }
    if (state == 2) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        const uint32_t kind = mhuc_read8(call, work + WORK_KIND);
        if (kind == 0x3eu || kind == 0x3fu || kind == 1u) {
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_3_27_C, 0u, 0u, 0.0f, 0.0f, NULL);
        } else if (kind == 2u || kind == 0x40u || kind == 0x41u) {
            mhuc_call_f(call, FN_MOTION, enemy, MOTION_3_27_D, 0u, 0u, 0.0f, 0.0f, NULL);
        }
        mhuc_call(call, FN_SHELL, enemy, 0u, 0x16u, 0u);
        mhuc_call(call, FN_FLY, enemy, 0u, 0u, 0u);
        return;
    }
    if (state == 3) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* ── 3U 0x0082b37c: 3/8, the base-class handler ─────────────────────────────────────── */

/* 3U 0x8310f0 sets work+0x7c9 and returns; MH4U's own 3/8 handler stores the same at
 * work+0x3c4 inline (no function to call), so the port writes the field. */
static void mark_flying(MH4UCall *call, uint32_t work) {
    mhuc_write8(call, work + WORK_MARKED, 1u);
}

/* 3U 0x8438e8(this, 0, rate): the rate halves as 0x8392d8 does, so MH4U's 0x0092dccc takes
 * 0x40 where the source passes 0x80. */
static uint32_t point_turn(MH4UCall *call, uint32_t enemy, uint32_t rate) {
    return mhuc_call(call, FN_POINT_TURN, enemy, 0u, rate, 0u);
}

/* State 2 sub 1 and state 3's no-transition path: the data float, the turn, aim A z clamped
 * at the source's 70.0. */
static void turn_and_clamp_3_8(MH4UCall *call, uint32_t enemy, uint32_t work) {
    float data;
    data_float(call, enemy, &data);
    turn_hold(call, enemy, work, data);
    if (mhuc_f32(call, work + WORK_AIM_Z) > CLAMP_3_8) {
        mhuc_put_f32(call, work + WORK_AIM_Z, CLAMP_3_8);
    }
}

/*   0: state 1, the data float, the fall, the request for motion 0x2d at 6.0;
 *   1: the flag, state 2, the request for 0x3d, the rate at target z + 500, third sub-state 0;
 *   2: mark the flying byte; sub 0 — turn the two joints at 0x100 (halved to 0x80), the
 *      30.0 distance test; when it passes, clear the aim, aim A z 5.0, aim B z 3.0, set up
 *      the turn point at -300.0; sub 1 — the data float, the turn, the two-joint turn at
 *      0x80 (halved to 0x40), aim A z clamped at 70.0; then the flag, state 3 and motion
 *      0x3e;
 *   3: mark the flying byte; the two-joint turn at 0x80 (halved); when it arrives, state 4,
 *      motion 0x2d, third 0, aim A y -10.0 and aim B z -3.2, then the data float and the
 *      turn; otherwise the data float, the turn and the 70.0 clamp;
 *   4: sub 0 — the data float, the turn (the first joint's flag kept), the 30.0 distance
 *      test, aim B z -6.8; sub 1 — the data float, the turn, the 0.0 floor, the flag; when
 *      the turn arrived, state 5, mode 3 and motion 0x1d, otherwise 3U 0x839598's blocked
 *      test and 0/3's base handler;
 *   5: the flag, mode 3, 0/3's base handler. */
static void run_3_8(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_FLY, enemy, 0u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        data_float_and_fall(call, enemy);
        motion(call, enemy, MOTION_3_8_A);
        return;
    }
    if (state == 1) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        motion(call, enemy, MOTION_3_8_B);
        float rate = 0.0f;
        mhuc_call_f(call, FN_RATE, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &rate);
        mhuc_put_f32(call, work + WORK_TARGET_Z,
                     mhuc_f32(call, work + WORK_TARGET_Z) + rate * RATE_3_8);
        mhuc_write8(call, work + WORK_SUB, 0u);
        return;
    }
    if (state == 2) {
        mark_flying(call, work);
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            mhuc_call(call, FN_TURN2, enemy, TURN_RATE_TWO, TURN_RATE_TWO, 0u);
            if (mhuc_call_f(call, FN_RANGE, enemy, 1u, 0u, 0u, TURN_SPEED_3_8, 0.0f, NULL)) {
                mhuc_write8(call, work + WORK_SUB, 1u);
                mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
                mhuc_put_f32(call, work + WORK_AIM_Z, AIM_A_Y_3_8);
                mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_3_8);
                mhuc_call_f(call, FN_SETUP_POINT, enemy, 0x10u, 0u, 0u, SETUP_HEIGHT, 0.0f,
                            NULL);
            }
        } else if (sub == 1) {
            float data;
            data_float(call, enemy, &data);
            turn_hold(call, enemy, work, data);
            point_turn(call, enemy, TURN_RATE_ONE);
            if (mhuc_f32(call, work + WORK_AIM_Z) > CLAMP_3_8) {
                mhuc_put_f32(call, work + WORK_AIM_Z, CLAMP_3_8);
            }
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        motion(call, enemy, MOTION_3_8_C);
        return;
    }
    if (state == 3) {
        mark_flying(call, work);
        if (!point_turn(call, enemy, TURN_RATE_ONE)) {
            turn_and_clamp_3_8(call, enemy, work);
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 4u);
        motion(call, enemy, MOTION_3_8_A);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_put_f32(call, work + WORK_AIM_Y, AIM_A_Y_DOWN);
        mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_DOWN);
        float data;
        data_float(call, enemy, &data);
        turn_hold(call, enemy, work, data);
        return;
    }
    if (state == 4) {
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        uint32_t limit;
        if (sub == 0) {
            float data;
            data_float(call, enemy, &data);
            limit = turn_hold(call, enemy, work, data);
            if (mhuc_call_f(call, FN_RANGE, enemy, 1u, 0u, 0u, TURN_SPEED_3_8, 0.0f, NULL)) {
                mhuc_write8(call, work + WORK_SUB, 1u);
                mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_3_8_4);
            }
        } else if (sub == 1) {
            float data;
            data_float(call, enemy, &data);
            limit = turn_hold(call, enemy, work, data);
            if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
            }
        } else {
            return;
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        if (limit != 0u) {
            mhuc_write8(call, work + WORK_STATE, 5u);
            mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
            motion(call, enemy, MOTION_3_27_B);
            return;
        }
        log_blocked_3_8();
        mhuc_3u_base_0_3(call, enemy, work);
        return;
    }
    if (state == 5) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        mhuc_3u_base_0_3(call, enemy, work);
    }
}

/* ── the family's dispatch and self-test ────────────────────────────────────────────── */

/* Runs category 3's part-2 handler for the pair, or returns 0 so the module's dispatch can
 * try the next family. The ids not listed belong to category 3's other slice (#219). */
static int dispatch_cat3b(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    if (category != 3) {
        return 0;
    }
    switch (index) {
    case 6: run_3_6(call, enemy, work, 0, 0); return 1;
    case 13: run_3_6(call, enemy, work, 1, 0); return 1;
    case 16: run_3_6(call, enemy, work, 0, 1); return 1;
    case 7: run_3_7(call, enemy, work, 0); return 1;
    case 17: run_3_7(call, enemy, work, 1); return 1;
    case 18: run_3_7(call, enemy, work, 2); return 1;
    case 19: run_3_7(call, enemy, work, 3); return 1;
    case 24: run_3_7(call, enemy, work, 4); return 1;
    case 28: run_3_7(call, enemy, work, 5); return 1;
    case 12: run_3_12(call, enemy, work, 0); return 1;
    case 20: run_3_12(call, enemy, work, 1); return 1;
    case 21: run_3_12(call, enemy, work, 2); return 1;
    case 25: run_3_12(call, enemy, work, 3); return 1;
    case 29: run_3_12(call, enemy, work, 4); return 1;
    case 27: run_3_27(call, enemy, work); return 1;
    case 8: run_3_8(call, enemy, work); return 1;
    default: return 0;
    }
}

/* What this family carries: the sixteen ids, the four handler units and 3/8's base handler,
 * the two base handlers reused from cat0.c and the two #55 calls it leaves out. The module's
 * self-test calls this with the others'. */
static void self_test_cat3b(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 16 of the 191 actions: 3/6, 3/13 and 3/16 <- 0x0068e448 (the curve at "
             "aim A y, the position advance, the height test; 3/13 compares target z + 1300); "
             "3/7, 3/17, 3/18, 3/19, 3/24 and 3/28 <- 0x0068e5e8 (the turn at 0x200, then the "
             "next action 3/0x14, 3/0x15, 3/0x19 or 3/0x1d); 3/12, 3/20, 3/21, 3/25 and 3/29 "
             "<- 0x0068e6e4 (the 70.0 distance test, the aim at 5.0/3.0 and 90.0, then 3/11 "
             "or the next action 3/0x16 to 3/0x1e); 3/27 <- 0x0068e8c8 (0x8509a0 and 0x850a50, "
             "mode 3, motions 0x1a/0x1d/0xcf/0xe1); 3/8 <- 0x0082b37c (the base-class "
             "handler: five states, 30.0/70.0, motion 0x2d/0x3d/0x3e/0x1d)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine calls are MH4U's: fly 0x%08x, data 0x%08x, fall 0x%08x, "
              "motion 0x%08x, flag 0x%08x, mode 0x%08x, set action 0x%08x, next action 0x%08x, "
              "curve 0x%08x, turn 0x%08x/0x%08x",
              (unsigned)FN_FLY, (unsigned)FN_DATA_FLOAT, (unsigned)FN_APPLY_FALL,
              (unsigned)FN_MOTION, (unsigned)FN_FLAG, (unsigned)FN_MODE,
              (unsigned)FN_START_ACTION, (unsigned)FN_NEXT_ACTION, (unsigned)FN_CURVE,
              (unsigned)FN_TURN_TO, (unsigned)FN_TURN_HOLD);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: +0x5/6/7 -> +0x144/145/146, +0x264/+0x268 -> "
             "+0x164/+0x168, +0x278 -> +0x178, +0x28c -> +0x220, +0x80 -> +0x1a8, +0x3c -> "
             "+0x19c, +0x120 -> +0x624, +0x7c9 -> +0x3c4, +0xdb -> +0x14c, +0x3 -> +0x1c0");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: 3U's 0x0064325c (#55) is left out of 3/6/3/16, and 0x00839598 "
             "(#55) of 3/8; the value curve is MH4U's own 3/6 curve 0x00fd18a0 (3U's 0x00c4eca8 "
             "has the same keys)");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat3b = {
    "cat3b", 16, dispatch_cat3b, self_test_cat3b,
};
