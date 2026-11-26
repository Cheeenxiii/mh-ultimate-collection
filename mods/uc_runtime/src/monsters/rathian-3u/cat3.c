/*
 * cat3.c: 3U Rathian's category 3 — 3/0, 3/1, 3/2, 3/4, 3/5, 3/9, 3/10, 3/11, 3/14, 3/15,
 * 3/22, 3/23, 3/26 and 3/30 — and action 12, which runs 3/2's handler.
 *
 * The source units are MH3U's 0x0068d9ec (3/0), 0x0068db54 (3/1), 0x0082d054 (3/2 and 12,
 * base-class code reimplemented here per decision 0002's second 2026-11-26 amendment),
 * 0x0068dc60 (3/4), 0x0068dd78 (one handler for 3/5, 3/9, 3/14, 3/22, 3/23, 3/26 and 3/30,
 * told apart by the r1 its case block leaves), 0x0083b424 (3/11's case-block tail, the
 * "action was set" byte), the inline case block 0x00699964 (3/15) and 0x00858b6c (3/10, the
 * base handler cat0.c exports, which 3/10 and 3/15 end in).
 *
 * Engine calls go to MH4U's counterpart of each source function (reference/README.md's 73
 * and the base-helper map); a source function MH4U lacks, or one that takes MH3U image data,
 * is named, logged once and skipped. The calls this slice leaves blocked:
 *   - #55's 0x0083db24, 0x00833234, 0x00835f10, 0x0083dc14 and 0x00a347bc (the 3/5 family);
 *   - 0x00842a7c, which 3/4 calls and #55's list records as an unresolved hit resolution;
 *   - the action-start record the 3/5 readers take (0x0084704c / 0x00847134, #135): the
 *     record is MH3U's image data and the module has no rebuilt copy yet;
 *   - the value curve 3/0 and 3/1 evaluate (0x0083c6e0 with MH3U's 0x00c4ed80): source
 *     image data, no rebuilt table yet.
 * A blocked call answers 0, the source's "nothing found", so the state machines keep their
 * shape; the log names each one the first time it is reached.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The state bytes
 * work+0x144/+0x145/+0x146 are the source's +5/+6/+7, shared by every id here as in the
 * source. The offsets are reference/README.md's field map; the 3/5 family's own fields are
 * read by hand against MH4U's 3/5 handler (0x006d5e98), as the map asks because it flags that
 * pair as misaligned (see the WORK_3_5_* rows and WORK_SELECT below).
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* ── the work block, MH4U's offsets ─────────────────────────────────────────────────────── */
#define WORK_STATE      0x0144u /* 3U +0x5:  the action's state byte */
#define WORK_SUB        0x0145u /* 3U +0x6:  the 3/5 family's sub-state */
#define WORK_SUB2       0x0146u /* 3U +0x7:  the 3/5 family's third state */
#define WORK_SET        0x01dcu /* 3U +0xf2: "the action was set" */
#define WORK_COUNTDOWN  0x01d4u /* 3U +0x28: the frame timer; +0x2c keeps its start */
#define WORK_TURN       0x01a8u /* 3U +0x80: the turn slot before the heading */
#define WORK_HEADING    0x01acu /* 3U +0x84: the heading (a u16 angle in the word) */
#define WORK_POS        0x0198u /* 3U +0x38: position x, y, z */
#define WORK_TARGET     0x0218u /* 3U +0x288: the target point x, y, z */
#define WORK_OTHER      0x034cu /* 3U +0x381: the "other state" byte */
#define WORK_RATE_DELTA 0x0394u /* 3U +0x3d0: a 0-1 rate advanced by the frame delta */
#define WORK_TAIL       0x7993u /* 3U +0xe1: the tail flag: the next move (8/0, 9/0) */
#define WORK_SELECT     0x014cu /* 3U +0xdb: the selector byte the 3/5 pair compares */

/* The five fields the 3/5 pair fixes by hand (MH4U 0x006d5e98 against MH3U 0x0068dd78): */
#define WORK_3_5_ACTIVE 0x01eeu /* 3U +0xf4: "the action may advance", read before the loops */
#define WORK_3_5_TIMER  0x0520u /* 3U +0x944: the u16 the 3/5 loops compare with 0x12c */
#define WORK_3_5_LAST   0x0202u /* 3U +0xaec: the byte 3/5's variant 1 compares with +0xdb */
#define WORK_3_5_PART   0x027cu /* 3U +0x2b6: the part byte the hit setup reads */

/* MH4U's per-monster speed the 3/4 part check takes (3U's this+0x278). */
#define ENEMY_SPEED     0x0290u

/* ── MH4U's engine functions and the 3U function each stands for ────────────────────────── */
#define FN_MODE         0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_DATA_FLOAT   0x0093d870u /* [0x00852324] the action data's float, in s0 */
#define FN_APPLY_FALL   0x0092e99cu /* [0x00844124] advance the fall by s0, then mode 1 */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion: r1, then r2/r3 as s0/s1 */
#define FN_REQUEST      0x0094f408u /* [0x0082a878] set the next motion/state (r1, s0, s1) */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_COUNTDOWN    0x00b0704cu /* the source's inline frame-delta subtraction */
#define FN_CLEAR_AIM    0x00916228u /* [0x0082fc8c] clear the aim point A */
#define FN_TURN         0x0091656cu /* [0x00839514] the turn/advance wrapper (this, slot, r2) */
#define FN_TURN_TO      0x0091db4cu /* [0x008357b0] turn toward the target by a step in r1 */
#define FN_SET_ACTION_1 0x0092b140u /* [0x0084134c] set an action immediately, kind 1 */
#define FN_SET_ACTION_2 0x00935a90u /* [0x0084dc84] set an action immediately, kind 2 */
#define FN_NEXT_ACTION  0x0094ef64u /* [0x0082a06c] request the next action (r1, r2) */
#define FN_MARK         0x00922ca0u /* [0x0083d18c] set the work+0x3e3 byte */
#define FN_PREDICATE    0x0092dcccu /* [0x008438e8] the 3/5 "may advance" predicate */
#define FN_HIT_START    0x0092dc50u /* [0x008437f4] the 3/5 action-start call (0x19, s0) */
#define FN_LOOP         0x00947d0cu /* [0x008565d8] the same loop as the source's */
#define FN_END          0x00939988u /* [0x0084c1ac] the same end step */
#define FN_RATE_A       0x0093cd70u /* [0x008509a0] 3/2's state-0 end step */
#define FN_RATE_B       0x0093ce60u /* [0x00850a50] 3/2's state-1 opening step */
#define FN_HOLD_CHECK   0x00942220u /* [0x0083369c] the hold/fall test 3/2 state 1 takes */
#define FN_TURN_RATE    0x00918e48u /* [0x00836c04] turn by s0 with s1's rate (map pair) */
#define FN_ANGLE        0x00568c64u /* [0x00584cd8] the angle from dx/dz (s0, s1) */
#define FN_DIST2        0x00aacd84u /* [0x00585f30] the squared distance between two points */
#define FN_STATE_PRED   0x0092e960u /* [0x00844100] the state 2/3 predicate */
#define FN_AIM_ADVANCE  0x00918ef0u /* [0x00832690] advance the aim point A by B */
#define FN_HIT_CHECK    0x00935fb8u /* [0x0084e74c] the part check (parts, s0, s1) */
#define FN_PART_FLAG    0x0092e4f8u /* [0x0083d1a4] set the per-action flag (r1) */
#define FN_HIT_SETUP    0x00916b94u /* [0x0082ffbc] the hit setup (r1, r2, r3, stack 0). The
                                     * 73 names 0x00935f8c, its re-encoding wrapper, but
                                     * MH4U's own 3/5 calls this with the source's arguments */

/* ── the source's frame values ─────────────────────────────────────────────────────────── */
#define MOTION_3_START    0x29u    /* 3/0 and 3/1: the first motion */
#define MOTION_3_SECOND   0x43u    /* 3/0 and 3/1: after the finish flag, at 0.0 */
#define MOTION_3_0_THIRD  0x1au    /* 3/0 */
#define MOTION_3_2_START  0x1au
#define MOTION_3_2_SECOND 0x1du
#define MOTION_3_2_THIRD  0x2eu
#define MOTION_3_2_FOURTH 0x41u
#define MOTION_3_4_START  0x1fu
#define MOTION_3_10_START 0x2du    /* the shared block 3/10 and 3/15 start with */
#define MOTION_3_11_START 0x1fu
#define SPEED_FOUR        4.0f
#define SPEED_ONE         1.0f
#define TURN_STEP_3_0     0x100u
#define TURN_STEP_3_15    0x180u
#define TIMER_3_11        60.0f
#define ANGLE_SCALE_360   360.0f
#define ANGLE_SCALE_16    1.52587890625e-05f  /* 2^-16 */
#define ANGLE_SCALE_60    0.016666667f        /* 1/60 */
#define TURN_RATE_3_4     0.04f
#define DIST_THRESHOLD    0x4b742400u         /* the source's 16000000.0f, compared as bits */

/* ── blocked calls, named and logged once each ─────────────────────────────────────────── */
static int logged_record_a, logged_record_b, logged_curve, logged_842a7c;
static int logged_83db24, logged_833234, logged_835f10, logged_83dc14, logged_a347bc;

static void log_once(MH4UCall *call, int *seen, const char *what, const char *why) {
    (void)call;
    if (*seen) {
        return;
    }
    *seen = 1;
    mhuc_logf(MH4U_LOG_INFO, "3U Rathian's category 3: %s is blocked: %s", what, why);
}

/* 3/0's and 3/1's value curve (0x0083c6e0 with MH3U's 0x00c4ed80). The curve and the A.y
 * store that reads its result are skipped; the source's frame values after it still run. */
static void curve_step(MH4UCall *call) {
    log_once(call, &logged_curve, "the value curve 0x00c4ed80 (0x0083c6e0)",
             "it is MH3U image data and no rebuilt curve ships with the module");
}

/* 3/4's 0x00842a7c(this, 0): #55's unresolved hit resolution. */
static void attack_3_4(MH4UCall *call) {
    log_once(call, &logged_842a7c, "0x00842a7c (3/4's hit resolution)",
             "it is one of #55's 28 calls MH4U has no counterpart for");
}

/* 3/5's action-start record readers (0x0084704c and 0x00847134) take MH3U's 0x00b0b168.
 * #135 rebuilt the record, but the module has no copy of it, so both readers are skipped. */
static void record_3_5(MH4UCall *call, int reader) {
    if (reader == 0) {
        log_once(call, &logged_record_a, "the action-start record reader 0x0084704c (#135)",
                 "the record is MH3U image data and the module carries no rebuilt copy");
    } else {
        log_once(call, &logged_record_b, "the action-start record reader 0x00847134 (#135)",
                 "the record is MH3U image data and the module carries no rebuilt copy");
    }
}

static void blocked_3_5(MH4UCall *call, int which) {
    switch (which) {
    case 0:
        log_once(call, &logged_83db24, "0x0083db24 (3/5's entry step)",
                 "it is one of #55's 28 calls MH4U has no counterpart for");
        break;
    case 1:
        log_once(call, &logged_833234, "0x00833234 (3/5's monster-list entry)",
                 "it is one of #55's 28 calls MH4U has no counterpart for");
        break;
    case 2:
        log_once(call, &logged_835f10, "0x00835f10 (3/5's target check)",
                 "it is one of #55's 28 calls MH4U has no counterpart for");
        break;
    default:
        log_once(call, &logged_83dc14, "0x0083dc14 (3/5's monster-list test)",
                 "it is one of #55's 28 calls MH4U has no counterpart for");
        break;
    }
}

/* ── small helpers over the engine calls ───────────────────────────────────────────────── */
static uint16_t read_u16(MH4UCall *call, uint32_t addr) {
    return (uint16_t)(mhuc_read8(call, addr) | (mhuc_read8(call, addr + 1u) << 8));
}

static void set_motion(MH4UCall *call, uint32_t enemy, uint32_t motion, uint32_t speed) {
    mhuc_call_f(call, FN_MOTION, enemy, motion, 0u, 0u, (float)speed, 0.0f, NULL);
}

/* 0x00852324 returns the action data's float in s0; the source leaves it there for the call
 * that follows (the fall, the hold test or the turn wrapper), so every caller keeps it. */
static float data_float(MH4UCall *call, uint32_t enemy) {
    float value = 0.0f;
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &value);
    return value;
}

static void apply_fall(MH4UCall *call, uint32_t enemy, float value) {
    mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, value, 0.0f, NULL);
}

static void set_mode(MH4UCall *call, uint32_t enemy, uint32_t mode) {
    mhuc_call(call, FN_MODE, enemy, mode, 0u, 0u);
}

/* 0x00839514(this, work+0x80, s0, s1=1.0): the source's turn/advance wrapper. Its MH4U
 * counterpart is 0x0091656c, which MH4U's own 3/0, 3/1 and 3/5 handlers call at the same
 * point and which tails into the same 0x00922b34; the 73 also names 0x0091b430 as a body
 * match of the wrapper, but that one carries no r2 mode argument. */
static void turn_step(MH4UCall *call, uint32_t enemy, uint32_t work, float s0) {
    mhuc_call_f(call, FN_TURN, enemy, work + WORK_TURN, 0u, 0u, s0, SPEED_ONE, NULL);
}

static void set_action_kind1(MH4UCall *call, uint32_t enemy, uint32_t category,
                             uint32_t index) {
    mhuc_call(call, FN_SET_ACTION_1, enemy, category, index, 0u);
}

static void set_action_kind2(MH4UCall *call, uint32_t enemy, uint32_t category,
                             uint32_t index) {
    mhuc_call(call, FN_SET_ACTION_2, enemy, category, index, 0u);
}

static void next_action(MH4UCall *call, uint32_t enemy, uint32_t category, uint32_t index) {
    mhuc_call(call, FN_NEXT_ACTION, enemy, category, index, 0u);
}

/* ── 3/0 ───────────────────────────────────────────────────────────────────────────────── */
/* 3U 0x0068d9ec, four states on work+5.
 *   0: state 1, mode 0, motion 0x29 at 6.0;
 *   1: the finish flag, then state 2, the data float, the fall, motion 0x43 at 0.0 and A
 *      cleared;
 *   2: the value curve (blocked), the data float, the turn at 1.0, then the finish flag,
 *      state 3 and motion 0x1a at 6.0;
 *   3: turn toward the target by 0x100, then the finish flag and the immediate action 3/2.
 */
static void run_3_0(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        set_motion(call, enemy, MOTION_3_START, 6u);
    } else if (state == 1) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        apply_fall(call, enemy, data_float(call, enemy));
        set_motion(call, enemy, MOTION_3_SECOND, 0u);
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
    } else if (state == 2) {
        curve_step(call);
        const float data = data_float(call, enemy);
        turn_step(call, enemy, work, data);
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        set_motion(call, enemy, MOTION_3_0_THIRD, 6u);
    } else if (state == 3) {
        mhuc_call(call, FN_TURN_TO, enemy, TURN_STEP_3_0, 0u, 0u);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            set_action_kind1(call, enemy, 3u, 2u);
        }
    }
}

/* ── 3/1 ───────────────────────────────────────────────────────────────────────────────── */
/* 3U 0x0068db54, three states; the same opening as 3/0, then:
 *   2: the curve (blocked), the data float, the turn at 1.0, the finish flag, then the 0/3
 *      base handler cat0.c exports (0x00858b6c).
 */
static void run_3_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        set_motion(call, enemy, MOTION_3_START, 6u);
    } else if (state == 1) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        apply_fall(call, enemy, data_float(call, enemy));
        set_motion(call, enemy, MOTION_3_SECOND, 0u);
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
    } else if (state == 2) {
        curve_step(call);
        const float data = data_float(call, enemy);
        turn_step(call, enemy, work, data);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_3(call, enemy, work);
        }
    }
}

/* ── 3/2 and 12 ────────────────────────────────────────────────────────────────────────── */
/* 3U 0x0082d054, base-class code, five states on work+5:
 *   0: state 1, the data float, the fall, motion 0x1a at 6.0, then 0x008509a0;
 *   1: 0x00850a50, the data float, the 0x0083369c test (its s0 is the data float); when it
 *      passes, state 2, mode 3 and motion 0x1d at 6.0;
 *   2: the finish flag, state 3, motion 0x2e at 6.0;
 *   3: the finish flag, state 4, mode 0, motion 0x41 at 0.0;
 *   4: the finish flag, then 0/2's base handler cat0.c exports (0x0082d1cc).
 */
static void run_3_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        apply_fall(call, enemy, data_float(call, enemy));
        set_motion(call, enemy, MOTION_3_2_START, 6u);
        mhuc_call(call, FN_RATE_A, enemy, 0u, 0u, 0u);
    } else if (state == 1) {
        mhuc_call(call, FN_RATE_B, enemy, 0u, 0u, 0u);
        const float data = data_float(call, enemy);
        if (!mhuc_call_f(call, FN_HOLD_CHECK, enemy, 0u, 0u, 0u, data, 0.0f, NULL)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        set_mode(call, enemy, 3u);
        set_motion(call, enemy, MOTION_3_2_SECOND, 6u);
    } else if (state == 2) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        set_motion(call, enemy, MOTION_3_2_THIRD, 6u);
    } else if (state == 3) {
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 4u);
        set_mode(call, enemy, 0u);
        set_motion(call, enemy, MOTION_3_2_FOURTH, 0u);
    } else if (state == 4) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* ── 3/4 ───────────────────────────────────────────────────────────────────────────────── */
/* 3U 0x0068dc60, two states:
 *   0: state 1, the data float, the fall, 0x00832690, motion 0x1f at 0.0;
 *   1: the hit resolution (blocked), the angle from the position to the target, the heading
 *      difference scaled by 360 * 2^-16 / 60 and turned at 0.04, then the part check
 *      0x0084e74c(this, 0x23, 0x24, (int)this+0x278, work+0x3d0).
 */
static void run_3_4(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        apply_fall(call, enemy, data_float(call, enemy));
        mhuc_call(call, FN_AIM_ADVANCE, enemy, 0u, 0u, 0u);
        set_motion(call, enemy, MOTION_3_4_START, 0u);
    } else if (state == 1) {
        attack_3_4(call);

        /* 0x00584cd8(work+0x38, work+0x288): the angle from the position to the target. Its
         * x/z difference goes in s0/s1 for MH4U's 0x00568c64. */
        const float dx = mhuc_f32(call, work + WORK_TARGET) - mhuc_f32(call, work + WORK_POS);
        const float dz = mhuc_f32(call, work + WORK_TARGET + 8u) -
                         mhuc_f32(call, work + WORK_POS + 8u);
        const uint32_t angle = mhuc_call_f(call, FN_ANGLE, 0u, 0u, 0u, 0u, dx, dz, NULL);
        const uint16_t diff = (uint16_t)(angle - mhuc_read32(call, work + WORK_HEADING));
        float turn = 0.0f;
        if (diff != 0u) {
            turn = (float)(int16_t)diff * ANGLE_SCALE_360 * ANGLE_SCALE_16 * ANGLE_SCALE_60;
        }
        mhuc_call_f(call, FN_TURN_RATE, enemy, 0u, 0u, 0u, turn, TURN_RATE_3_4, NULL);

        /* The source's this+0x278 speed as an int, and work+0x3d0's rate; MH4U's part check
         * takes the speed as s0 and the rate as s1 (its own 3/4 does the same). */
        const float speed = mhuc_f32(call, enemy + ENEMY_SPEED);
        const float speed_int = (float)(int32_t)speed;
        mhuc_call_f(call, FN_HIT_CHECK, enemy, 0x23u, 0x24u, 0u, speed_int,
                    mhuc_f32(call, work + WORK_RATE_DELTA), NULL);
    }
}

/* ── 3/5, 3/9, 3/14, 3/22, 3/23, 3/26, 3/30 ────────────────────────────────────────────── */
/* The source's 0x687efc(this, sp) point: MH3U's work+0xda mapped through 0x00a347bc (#55)
 * and two constants. The mapping is blocked, so the descriptor keeps the generic 0x1b entry
 * and a zero third byte, and the loops read the same shape. */
#define POINT_ENTRY 0x1bu

static void run_3_5_common(MH4UCall *call, uint32_t enemy, uint32_t work, int variant);

/* 0x68e420: the data float and the turn wrapper, the state-0 tail and the record path. */
static void run_3_5_float_turn(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const float data = data_float(call, enemy);
    turn_step(call, enemy, work, data);
}

/* 0x68e3b0: the second record reader (its r1 is the variant's 0, 1 or 2; the reader is
 * blocked), then the data float and the turn. */
static void run_3_5_record_turn(MH4UCall *call, uint32_t enemy, uint32_t work) {
    record_3_5(call, 1);
    run_3_5_float_turn(call, enemy, work);
}

/* 0x0068de34: the state-1 sub-machine variant 1 (3/9) only; every path ends in the common
 * tail, except the hit path's immediate next action, which returns.
 *
 * The loops read the point's bytes; 0x833234 (does an entry exist?), 0x835f10 (is it in
 * range?) and 0x83dc14 (its state test) are #55's and answer 0, so a loop that finds
 * nothing falls through to the common tail. */
static void run_3_5_variant1_state1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const uint8_t sub = mhuc_read8(call, work + WORK_SUB);
    if (sub == 0) {
        if (mhuc_read8(call, work + WORK_3_5_ACTIVE) != 0) {
            run_3_5_common(call, enemy, work, 1);
            return;
        }
        mhuc_write8(call, work + WORK_SUB, 1u);
        if (!mhuc_call(call, FN_STATE_PRED, enemy, 0u, 0u, 0u) &&
            read_u16(call, work + WORK_3_5_TIMER) >= 0x12cu) {
            goto after_loops;
        }
        /* 0x68de88: the two point entries. 0x833234 is blocked and answers 0, so no entry is
         * found; 0x835f10's test is named for the same path. */
        for (unsigned i = 0; i < 2u; i++) {
            const uint8_t entry = (i == 0u) ? POINT_ENTRY : 0u;
            if (entry == 0u) {
                break;
            }
            blocked_3_5(call, 1);
            blocked_3_5(call, 2);
        }
    after_loops:
        /* 0x68defc: the other state byte and 0x008565d8. */
        if (mhuc_read8(call, work + WORK_OTHER) == 1u &&
            mhuc_call(call, FN_LOOP, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_SUB2, 2u);
        }
        run_3_5_common(call, enemy, work, 1);
        return;
    }
    if (sub == 1) {
        const uint8_t third = mhuc_read8(call, work + WORK_SUB2);
        if (third == 1u) {
            /* 0x68df30: the part test. 0x833234 and 0x83dc14 are blocked and answer 0, so
             * the loop finds nothing and falls through. */
            for (unsigned i = 0; i < 2u; i++) {
                const uint8_t entry = (i == 0u) ? POINT_ENTRY : 0u;
                if (entry == 0u) {
                    break;
                }
                blocked_3_5(call, 1);
                blocked_3_5(call, 3);
            }
            run_3_5_common(call, enemy, work, 1);
            return;
        }
        if (third == 2u) {
            /* 0x68e01c: the squared distance to the target, its bits against the source's
             * 0x4b742400. Over it, the common tail; under it, the immediate 3/8 and the end
             * step, which returns. */
            const float dist2 = mhuc_call_f(call, FN_DIST2, 0u, work + WORK_POS,
                                            work + WORK_TARGET, 0u, 0.0f, 0.0f, NULL);
            union { float f; uint32_t u; } bits;
            bits.f = dist2;
            if (bits.u > DIST_THRESHOLD) {
                run_3_5_common(call, enemy, work, 1);
                return;
            }
            next_action(call, enemy, 3u, 8u);
            mhuc_call(call, FN_END, enemy, 0u, 0u, 0u);
            return;
        }
        run_3_5_common(call, enemy, work, 1);
        return;
    }
    run_3_5_common(call, enemy, work, 1);
}

/* The common tail's per-variant steps (0x68e0b4, 0x68e0f0, 0x68e140 and the e19c switch). */
static void run_3_5_variant_tail(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    if (variant == 0) {
        /* 0x68e0b4: the data float, the fall, the immediate 3/11 and the set byte. */
        apply_fall(call, enemy, data_float(call, enemy));
        set_action_kind2(call, enemy, 3u, 0xbu);
        mhuc_write8(call, work + WORK_SET, 1u);
        return;
    }
    if (variant == 1) {
        /* 0x68e0f0: the selector byte picks 3/9 or 3/10. */
        const uint8_t select = mhuc_read8(call, work + WORK_SELECT);
        const uint8_t last = mhuc_read8(call, work + WORK_3_5_LAST);
        if (select != last && last != 0xffu) {
            next_action(call, enemy, 3u, 9u);
        } else {
            next_action(call, enemy, 3u, 0xau);
        }
        return;
    }
    if (mhuc_read8(call, work + WORK_TAIL) != 0) {
        /* 0x68e180 and the 0x68e340-0x68e394 tails: the immediate next action. */
        static const uint8_t indexes[5] = {0x0eu, 0x16u, 0x17u, 0x1au, 0x1eu};
        mhuc_call(call, FN_PART_FLAG, enemy, 0u, 0u, 0u);
        set_action_kind1(call, enemy, 3u, indexes[variant - 2]);
        return;
    }
    if (variant == 2) {
        /* The default (2) branch falls back to variant 0's step. */
        apply_fall(call, enemy, data_float(call, enemy));
        set_action_kind2(call, enemy, 3u, 0xbu);
        mhuc_write8(call, work + WORK_SET, 1u);
        return;
    }
    /* 0x68e1bc, 0x68e1e4, 0x68e238 and 0x68e2bc: the hit setup, then the part byte's 0xff
     * retry, then the next action (7/0x5e, 7/0x1c, 7/0x39 or 7/0x1d, 7/0x4b). */
    mhuc_call5(call, FN_HIT_SETUP, enemy, 0u, 0u, 0u, 0u);
    if (mhuc_read8(call, work + WORK_3_5_PART) == 0xffu) {
        mhuc_call5(call, FN_HIT_SETUP, enemy, 5u, 9u, 0u, 0u);
    }
    if (variant == 4) {
        if (mhuc_call(call, FN_STATE_PRED, enemy, 0u, 0u, 0u)) {
            next_action(call, enemy, 7u, 0x39u);
        } else {
            next_action(call, enemy, 7u, 0x1du);
        }
        return;
    }
    {
        static const uint8_t next_index[3] = {0x5eu, 0x1cu, 0x4bu}; /* variants 6, 3, 5 */
        const uint32_t index = (variant == 6) ? next_index[0]
                              : (variant == 3) ? next_index[1]
                                               : next_index[2];
        next_action(call, enemy, 7u, index);
    }
}

static void run_3_5_common(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    if (!mhuc_call(call, FN_PREDICATE, enemy, 0u, 0u, 0u)) {
        run_3_5_record_turn(call, enemy, work);
        return;
    }
    run_3_5_variant_tail(call, enemy, work, variant);
}

/* 3U 0x0068dd78: one handler for the seven ids, told apart by the r1 its case block leaves:
 * 3/5=0, 3/9=1, 3/14=2, 3/22=3, 3/23=4, 3/26=5, 3/30=6.
 *   entry: 0x83d18c, then 0x83db24 for variants 3 to 6, then 0x687efc's point;
 *   state 0: state 1, sub-states 0, the records (blocked), then the data float and the turn;
 *   state 1: variant 1 runs its sub-machine first; every variant then ends in the common
 *            tail.
 */
static void run_3_5(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
    if (variant >= 3) {
        blocked_3_5(call, 0);
    }
    log_once(call, &logged_a347bc, "0x00a347bc (3/5's point mapping)",
             "it is one of #55's 28 calls MH4U has no counterpart for");

    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_write8(call, work + WORK_SUB2, 0u);
        record_3_5(call, 0);
        mhuc_call_f(call, FN_HIT_START, enemy, 0x19u, 0u, 0u, SPEED_ONE, 0.0f, NULL);
        run_3_5_float_turn(call, enemy, work);
        return;
    }
    if (state != 1) {
        return;
    }
    if (variant == 1) {
        run_3_5_variant1_state1(call, enemy, work);
    } else {
        run_3_5_common(call, enemy, work, variant);
    }
}

/* ── 3/10 and 3/15 ─────────────────────────────────────────────────────────────────────── */
/* The shared state 0 (MH3U 0x006999ac, used by both case blocks): state 1, the data float,
 * the fall, motion 0x2d at 6.0. Returns 1 when it ran (the caller then returns). */
static int run_3_10_15_state0(MH4UCall *call, uint32_t enemy, uint32_t work) {
    if ((int)mhuc_read8(call, work + WORK_STATE) != 0) {
        return 0;
    }
    mhuc_write8(call, work + WORK_STATE, 1u);
    apply_fall(call, enemy, data_float(call, enemy));
    set_motion(call, enemy, MOTION_3_10_START, 6u);
    return 1;
}

/* 3/10: MH3U's case block 0x0069983c — 0x83d18c, the shared state 0, then state 1's finish
 * flag and the 0/3 base handler. */
static void run_3_10(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
    if (run_3_10_15_state0(call, enemy, work)) {
        return;
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_3(call, enemy, work);
    }
}

/* 3/15: the inline block 0x00699964 — 0x83d18c, the shared state 0, then state 1's turn
 * toward the target by 0x180, the finish flag and the 0/3 base handler. */
static void run_3_15(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
    if (run_3_10_15_state0(call, enemy, work)) {
        return;
    }
    mhuc_call(call, FN_TURN_TO, enemy, TURN_STEP_3_15, 0u, 0u);
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_3(call, enemy, work);
    }
}

/* ── 3/11 ──────────────────────────────────────────────────────────────────────────────── */
/* MH3U 0x0083b424 is the handler its case block (0x0069987c) tail-calls: it sets the
 * "action was set" byte and returns. The case block is the state machine:
 *   0: state 1, the data float, the fall, the request for motion 0x1f at 4.0, and the 60.0
 *      timer (the source keeps the start at +0x2c too; MH4U's countdown worker keeps one
 *      value, so the port keeps +0x1d4 only);
 *   1: count the timer down; when spent, the data float, the fall, the immediate 3/11 and
 *      the set byte.
 */
static void run_3_11(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        apply_fall(call, enemy, data_float(call, enemy));
        mhuc_call_f(call, FN_REQUEST, enemy, MOTION_3_11_START, 0u, 0u, SPEED_FOUR, 0.0f,
                    NULL);
        mhuc_put_f32(call, work + WORK_COUNTDOWN, TIMER_3_11);
    } else if (state == 1) {
        if (!mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_COUNTDOWN, 0u, 0u)) {
            return;
        }
        apply_fall(call, enemy, data_float(call, enemy));
        set_action_kind2(call, enemy, 3u, 0xbu);
        mhuc_write8(call, work + WORK_SET, 1u);
    }
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────────── */
static int dispatch_cat3(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                         int index) {
    if (category == 12) {
        run_3_2(call, enemy, work);
        return 1;
    }
    if (category != 3) {
        return 0;
    }
    switch (index) {
    case 0: run_3_0(call, enemy, work); return 1;
    case 1: run_3_1(call, enemy, work); return 1;
    case 2: run_3_2(call, enemy, work); return 1;
    case 4: run_3_4(call, enemy, work); return 1;
    case 5: run_3_5(call, enemy, work, 0); return 1;
    case 9: run_3_5(call, enemy, work, 1); return 1;
    case 10: run_3_10(call, enemy, work); return 1;
    case 11: run_3_11(call, enemy, work); return 1;
    case 14: run_3_5(call, enemy, work, 2); return 1;
    case 15: run_3_15(call, enemy, work); return 1;
    case 22: run_3_5(call, enemy, work, 3); return 1;
    case 23: run_3_5(call, enemy, work, 4); return 1;
    case 26: run_3_5(call, enemy, work, 5); return 1;
    case 30: run_3_5(call, enemy, work, 6); return 1;
    default: return 0;
    }
}

static void self_test_cat3(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 15 of the 191 actions: 3/0 <- 0x0068d9ec (four states); 3/1 <- "
             "0x0068db54 (three); 3/2 and 12 <- 0x0082d054 (base-class code, five states); "
             "3/4 <- 0x0068dc60 (the angle and the 0x23/0x24 part check); 3/5, 3/9, 3/14, "
             "3/22, 3/23, 3/26 and 3/30 <- 0x0068dd78 (seven variants on r1); 3/10 <- "
             "0x00858b6c's case block; 3/11 <- 0x0083b424's case block (the 60.0 timer); "
             "3/15 <- the inline block 0x00699964");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: category 3's engine calls are MH4U's: mode 0x%08x, data float "
              "0x%08x, fall 0x%08x, motion 0x%08x, request 0x%08x, flag 0x%08x, turn "
              "0x%08x, immediate 0x%08x/0x%08x, next action 0x%08x",
              (unsigned)FN_MODE, (unsigned)FN_DATA_FLOAT, (unsigned)FN_APPLY_FALL,
              (unsigned)FN_MOTION, (unsigned)FN_REQUEST, (unsigned)FN_FLAG,
              (unsigned)FN_TURN, (unsigned)FN_SET_ACTION_1, (unsigned)FN_SET_ACTION_2,
              (unsigned)FN_NEXT_ACTION);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors read by hand against MH4U's 3/5 (0x006d5e98): "
             "+0x5/+0x6/+0x7 -> +0x144/+0x145/+0x146, +0xdf -> +0x1ca, +0xf2 -> +0x1dc, "
             "+0x28 -> +0x1d4, +0x80/+0x84 -> +0x1a8/+0x1ac, +0x38 -> +0x198, +0x288 -> "
             "+0x218, +0x68 -> +0x180, +0x3d0 -> +0x394, +0x381 -> +0x34c, and the 3/5 "
             "pair's own +0xf4 -> +0x1ee, +0x944 -> +0x520, +0xdb -> +0x14c, +0xaec -> "
             "+0x202, +0x2b6 -> +0x27c");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: blocked and logged: #55's 0x0083db24, 0x00833234, 0x00835f10, "
             "0x0083dc14, 0x00a347bc and 0x00842a7c; the action-start record readers "
             "0x0084704c/0x00847134 (#135's record is MH3U image data); the value curve "
             "0x0083c6e0 with 0x00c4ed80");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat3 = {
    "cat3", 15, dispatch_cat3, self_test_cat3,
};
