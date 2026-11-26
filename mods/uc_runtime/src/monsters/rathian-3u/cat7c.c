/*
 * cat7c.c: 3U Rathian's category 7, part 3 — six handler units and the thirty-six ids they
 * carry: 7/22 to 7/29 and 7/57 (0x00696580), 7/31 (0x00696cd8), 7/33 (0x00696f4c),
 * 7/35, 7/46, 7/47, 7/48, 7/62, 7/63, 7/64 and 7/65 (0x006971c0), 7/36, 7/38, 7/39, 7/40,
 * 7/49, 7/50, 7/51, 7/52, 7/59 and 7/60 (0x0069747c), and 7/37, 7/84, 7/86, 7/87, 7/92, 7/93
 * and 7/96 (the 0x00686bcc stub into 0x00697888).
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h). The handlers,
 * their offsets, their frame values and their engine calls are the ones issue #223 translated
 * from MH3U USA's recompiled code; the runtime's README carries the field map, the call map,
 * the rows this slice adds and the calls it leaves blocked. MH4U's own handlers for the shared
 * ids were read beside the source's, as the paired-handler evidence the field map uses.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The state and
 * sub-state bytes are the game's own (MH4U work+0x144/+0x145), as category 0 uses them.
 *
 * Two ids' code is shared and can start more than one motion (7/36 to 7/40 and 7/49 to
 * 7/52), which is why R1 could not resolve their MH4U animation; with her own handler they
 * play their own. 7/64, 7/87 and 7/93 are three of the ids MH4U has no action for; this slice
 * gives them a handler instead of the old map.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <string.h>

#include "family.h"

/* ── the work block, MH4U's offsets and the 3U offset each stands for ─────────────────── */

#define WORK_STATE        0x0144u /* 3U +0x5:  the action's state byte */
#define WORK_SUBSTATE     0x0145u /* 3U +0x6:  its sub-state */
#define WORK_MODE         0x01c8u /* 3U +0xdc: the mode byte */
#define WORK_CATEGORY     0x01cau /* 3U +0xdf: the current category */
#define WORK_TIMER        0x01d4u /* 3U +0x28: the frame timer */
#define WORK_SPEED        0x0180u /* 3U +0x68: the speed accumulator */
#define WORK_TURN         0x01a8u /* 3U +0x80: the turn slot before the heading */
#define WORK_HEADING      0x01acu /* 3U +0x84: the heading */
#define WORK_AIM          0x0160u /* 3U +0x260: aim point A (x, y, z) */
#define WORK_AIM_Y        0x0164u /* 3U +0x264 */
#define WORK_AIM_Z        0x0168u /* 3U +0x268 */
#define WORK_AIM2_Z       0x0178u /* 3U +0x278: aim vector B's z */
#define WORK_TARGET       0x0218u /* 3U +0x288: the target point (x, y, z) */
#define WORK_TARGET_Y     0x021cu /* 3U +0x28c */
#define WORK_POS          0x0198u /* 3U +0x38: position (x, y, z) */
#define WORK_POS_Y        0x019cu /* 3U +0x3c */
#define WORK_KIND         0x01c0u /* 3U +0x3:  the enemy-data key */
#define WORK_FLIGHT       0x03e3u /* 3U +0x7eb: 0x83d18c's "this flight action ran" byte */
#define WORK_PHASE        0x03c4u /* 3U +0x7c9: 0x8310f0's byte */

/* ── the MH4U engine functions, and the 3U function each stands for ───────────────────── */

#define FN_FLIGHT_SET    0x00922ca0u /* [0x0083d18c] "this flight action ran" */
#define FN_MOTION        0x0094e318u /* [0x00828828] start a motion */
#define FN_MODE          0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_FLAG          0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_DATA          0x0093d870u /* [0x00852324] the action data's float */
#define FN_APPLY_FALL    0x0092e99cu /* [0x00844124] advance the fall, set mode 1 */
#define FN_VERTICAL      0x00915d44u /* [0x00833b2c] advance the speed/vertical value */
#define FN_SET_SPEED     0x00916108u /* [0x00833d88] set the speed */
#define FN_MODE_STEP     0x0091aae4u /* [0x0083336c] the per-mode speed/distance wrapper */
#define FN_ANGLE_STEP    0x0091aaf0u /* [0x008392d8] the same wrapper, an angle step in r3 */
#define FN_TURN          0x0091db4cu /* [0x008357b0] turn toward a point */
#define FN_TURN2         0x0091b430u /* [0x00839ea0] the turn with its two floats */
#define FN_ADVANCE       0x009114d4u /* [0x0082cee4] advance the position along the path */
#define FN_MOVE_BY_AIM   0x00955440u /* [0x0082b268] advance the position by aim point A */
#define FN_CLEAR_AIM     0x0091b3bcu /* [0x00839968] clear aim point A and vector B */
#define FN_CLEAR_AIM_A   0x00916228u /* [0x0082fc8c] clear aim point A */
#define FN_MOVE_Y        0x00955a5cu /* [0x0082b8f0] move y toward the target's y by s0 */
#define FN_ADVANCE_B     0x00911090u /* [0x00834098] advance A by B times the delta */
#define FN_GROUP         0x00914dc4u /* [0x00844a38] set a part group (r3 = 0) */
#define FN_GROUP4        0x0093310cu /* [0x00844a40] set a part group */
#define FN_DATA_GET      0x00923f90u /* [0x0083db3c] the data record's float */
#define FN_ANGLE_TO      0x00568c64u /* [0x00584cd8] the angle to a point (s0, s1) */
#define FN_DISTANCE      0x00aacd50u /* [0x005858f4] the distance to a point (r0, r1) */
#define FN_PART          0x0091b7b0u /* [0x008345f8] the part/type step, value in r1 */
#define FN_STALL_FLAG    0x0090f8fcu /* [0x0082c1c4] the action's stall flag, r1 in */
#define FN_TURN_LINE     0x0091656cu /* [0x00839514] advance the path, then the line */
#define FN_TIMER_ADD     0x00b05274u /* [0x008a78ec]'s add: timer += frame delta */

/* The source's frame values. */
#define AIM_Y_7_22       (-2.0f)
#define AIM_Z_7_22        50.0f
#define MOVE_Y_STEP        5.0f
#define FLIGHT_TURN      0x600u
#define SPEED_STOP       200.0f
#define SPEED_FLOOR     (-200.0f)
#define PHASE_STEP        20.0f
#define CAP_7_22_1       120.0f
#define CAP_7_22_2       110.0f
#define DELAY_7_31        36.0f
#define DELAY_7_31_2      30.0f
#define TURN_7_31        0x100u
#define TURN_7_33        0x2d8u
#define RANGE_7_33        80.0f
#define VERTICAL_7_35     (-5.0f)
#define VERTICAL_FLOOR  (-75.0f)
#define VERTICAL_FLOOR_BITS 0xc2960000u
#define DELAY_7_35        55.0f
#define TURN_7_35        0x38eu
#define RANGE_7_35        82.0f
#define CAP_7_35         150.0f
#define TURN_7_36        0x40u
#define TURN_7_36_FAR    0x222u
#define RANGE_7_36        40.0f
#define DELAY_7_36_A      65.0f
#define TURN_7_36_A      0x250u
#define DELAY_7_36_B     110.0f
#define TURN_7_36_B      0x300u
#define DELAY_7_36_C      80.0f
#define TURN_7_36_C      0x300u
#define DELAY_7_36_D      60.0f
#define RANGE_7_36_D     100.0f
#define AIM_Z_7_36        30.0f
#define PHASE_7_37        20.0f
#define DELAY_7_37_A      65.0f
#define TURN_7_37_A      0x250u
#define DELAY_7_37_B     110.0f
#define TURN_7_37_B      0x300u
#define DELAY_7_37_C      60.0f
#define RANGE_7_37_C     100.0f
#define AIM_Z_7_37        30.0f
#define SPEED_7_37       150.0f
#define SPEED_END_7_37   200.0f

/* The motions the source asks for, MH3U's file * 100 + slot; start_motion converts them to
 * MH4U's file << 8 | slot. */
#define MOTION_7_22       0x45u
#define MOTION_7_22_1     0x3eu
#define MOTION_7_22_2     0x3fu
#define MOTION_7_22_3     0xd0u
#define MOTION_7_22_4A    0xddu
#define MOTION_7_22_4B    0x35u
#define MOTION_7_22_4C    0xd2u
#define MOTION_7_22_5A    0xdau
#define MOTION_7_22_5B    0x3cu
#define MOTION_7_31       0xc8u
#define MOTION_7_31_1     0xdcu
#define MOTION_7_33       0xd1u
#define MOTION_7_33_1     0xd4u
#define MOTION_7_35       0xcdu
#define MOTION_7_35_1     0xd4u
#define MOTION_7_36       0xd3u
#define MOTION_7_36_1     0xd4u
#define MOTION_7_36_2     0xd5u
#define MOTION_7_37       0xdbu
#define MOTION_7_37_1     0x1bu

/* ── the helpers every unit shares ───────────────────────────────────────────────────── */

/* MH3U's file * 100 + slot to MH4U's file << 8 | slot for her converted motion lists. */
static uint32_t motion_number(uint32_t m) {
    if (m < 100u) {
        return MHUC_MOTION(0u, m);
    }
    return MHUC_MOTION(m / 100u, m % 100u);
}

static void start_motion(MH4UCall *call, uint32_t enemy, uint32_t m) {
    mhuc_call(call, FN_MOTION, enemy, motion_number(m), 0u, 0u);
}

/* 3U 0x83d18c and its MH4U counterpart 0x00922ca0: the "this flight action ran" byte. */
static void set_flight_flag(MH4UCall *call, uint32_t enemy) {
    mhuc_call(call, FN_FLIGHT_SET, enemy, 0u, 0u, 0u);
}

/* 3U 0x8310f0: the source sets work+0x7c9 to 1 before the flight blend. MH4U's own 7/22
 * handler makes the same store at work+0x3c4, so the port does that. (The 73 table's
 * 0x008310f0 -> 0x0093d870 row is not this step; the paired handler is the evidence.) */
static void set_phase_byte(MH4UCall *call, uint32_t work) {
    mhuc_write8(call, work + WORK_PHASE, 1u);
}

/* 3U 0x6872ec: pick a small value from the enemy-data kind and the mode, then 0x8345f8.
 * MH4U's 0x0091b7b0 is the counterpart of 0x8345f8: it reads work+0x51e and calls 0x93bf90. */
static void flight_part_step(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int kind = (int)mhuc_read8(call, work + WORK_KIND);
    const int mode = (int)mhuc_read8(call, work + WORK_MODE);
    int value;
    switch (kind) {
    case 1:
        value = -14;
        break;
    case 2:
        value = (mode == 3) ? -10 : -15;
        break;
    case 0x3e:
    case 0x3f:
        value = (mode == 3) ? -7 : -10;
        break;
    case 0x40:
    case 0x41:
        value = (mode == 3) ? -7 : -14;
        break;
    default:
        return;
    }
    mhuc_call(call, FN_PART, enemy, (uint32_t)(int32_t)value, 0u, 0u);
}

/* The angle from one point to another, as 3U's 0x584cd8 does it and MH4U's own 7/22 handler
 * computes it: the difference's x in s0 and z in s1 to 0x00568c64. */
static uint32_t angle_to(MH4UCall *call, uint32_t work, uint32_t from, uint32_t to) {
    const float dx = mhuc_f32(call, work + to) - mhuc_f32(call, work + from);
    const float dz = mhuc_f32(call, work + to + 8u) - mhuc_f32(call, work + from + 8u);
    return mhuc_call_f(call, FN_ANGLE_TO, 0u, 0u, 0u, 0u, dx, dz, NULL);
}

/* The distance between two points, as 3U's 0x5858f4 and MH4U's 0x92e408 use 0x00aacd50. */
static float distance_to(MH4UCall *call, uint32_t work, uint32_t from, uint32_t to) {
    float out = 0.0f;
    mhuc_call_f(call, FN_DISTANCE, work + from, work + to, 0u, 0u, 0.0f, 0.0f, &out);
    return out;
}

static void timer_add(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_TIMER_ADD, enemy, work + WORK_TIMER, 0u, 0u);
}

static void timer_sub(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_put_f32(call, work + WORK_TIMER,
                 mhuc_f32(call, work + WORK_TIMER) - mhuc_f32(call, enemy + 0x14u));
}

/* 0x844004's ratio: distance / s2 clamped to [s1, s0].  It returns s0, which ABI 4's
 * mhuc_call_s2 cannot read back, so the port computes the same clamp from the distance call
 * the function itself makes.  Recorded as an open item in the README. */
static float distance_ratio(MH4UCall *call, uint32_t work, float low, float high, float span) {
    float ratio = distance_to(call, work, WORK_POS, WORK_TARGET) / span;
    if (ratio > high) {
        ratio = high;
    }
    if (ratio < low) {
        ratio = low;
    }
    return ratio;
}

static int blocked_tables_logged;
static void blocked_table_step(void) {
    if (!blocked_tables_logged) {
        blocked_tables_logged = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "blocked: the source's table interpolation (0x0083c6e0 / 0x00584760, MH4U's "
                 "0x00922250 / 0x00be1d90) reads MH3U data the port does not carry; the step "
                 "is skipped");
    }
}

static int blocked_effect_logged;
static void blocked_effect_step(void) {
    if (!blocked_effect_logged) {
        blocked_effect_logged = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "blocked: the source's effect spawn (0x00164f08 through the setup built by "
                 "0x00688a20/0x00688870, whose 0x00199d00/0x0063cabc/0x00829950 have no MH4U "
                 "counterpart) is skipped; MH4U's shell factory takes its own setup block");
    }
}

static int blocked_55_logged;
static void blocked_55_call(uint32_t address) {
    if (!blocked_55_logged) {
        blocked_55_logged = 1;
        mhuc_logf(MH4U_LOG_INFO,
                  "blocked: the source's 0x%08x has no MH4U counterpart (#55); its step is "
                  "skipped", (unsigned)address);
    }
}

/* The module's own 12 bytes keep 3U's work+0x70 point for 7/37: the map gives that field no
 * MH4U offset, and the source writes it in state 0 and reads it in state 2. */
static void slot_put_point(MhucState *slot, uint32_t work, MH4UCall *call) {
    float point[3];
    point[0] = mhuc_f32(call, work + WORK_POS);
    point[1] = mhuc_f32(call, work + WORK_POS + 4u);
    point[2] = mhuc_f32(call, work + WORK_POS + 8u);
    memcpy(slot->data, point, sizeof point);
}

static void slot_get_point(const MhucState *slot, float point[3]) {
    memcpy(point, slot->data, sizeof(float) * 3u);
}

/* ── 7/22 to 7/29 and 7/57: 0x00696580 ───────────────────────────────────────────────────
 * A five-state flight machine.  The case block's r1 (a) is the flight variant and its r2 (b)
 * the direction: 7/22 to 7/29 use (0/1 x 0..3), 7/57 (2, 3).
 */
static void run_7_22(MH4UCall *call, uint32_t enemy, uint32_t work, int a, int b) {
    set_flight_flag(call, enemy);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        flight_part_step(call, enemy, work);
        start_motion(call, enemy, MOTION_7_22);
        mhuc_write8(call, work + WORK_SUBSTATE, 0u);
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_AIM_Y, AIM_Y_7_22);
        mhuc_put_f32(call, work + WORK_AIM_Z, AIM_Z_7_22);
        return;
    }
    case 1: {
        set_phase_byte(call, work);
        mhuc_call_f(call, FN_MOVE_Y, enemy, 0u, 0u, 0u, MOVE_Y_STEP, 0.0f, NULL);
        uint32_t angle;
        if (b == 0) {
            angle = 0x2800u;
        } else if (b == 1) {
            angle = 0x2000u;
        } else if (b == 2) {
            angle = 0x1800u;
        } else {
            angle = angle_to(call, work, WORK_POS, WORK_TARGET);
            if (angle > 0x3000u) {
                angle = 0x3000u;
            }
        }
        const uint32_t turn = mhuc_call(call, FN_ANGLE_STEP, enemy, angle,
                                        mhuc_read32(call, work + WORK_TURN), 0x180u);
        mhuc_write32(call, work + WORK_TURN, turn);
        mhuc_call(call, FN_TURN, enemy, FLIGHT_TURN, 0u, 0u);
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_TURN2, enemy, work + WORK_TURN, 0u, 0u, data - SPEED_STOP, 1.0f,
                    NULL);
        if (mhuc_f32(call, work + WORK_AIM_Z) > CAP_7_22_1) {
            mhuc_put_f32(call, work + WORK_AIM_Z, CAP_7_22_1);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            start_motion(call, enemy, MOTION_7_22_1);
            mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
            mhuc_call(call, FN_GROUP4, enemy, 0u, 0x0eu, 3u);
            mhuc_put_f32(call, work + WORK_AIM2_Z, 3.0f);
        }
        return;
    }
    case 2: {
        set_phase_byte(call, work);
        timer_add(call, enemy, work);
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        if (mhuc_call_f(call, FN_TURN2, enemy, work + WORK_TURN, 0u, 0u, data - SPEED_STOP,
                        1.0f, NULL)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
            start_motion(call, enemy, MOTION_7_22_2);
            mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, SPEED_FLOOR, 0.0f, NULL);
        } else if (mhuc_f32(call, work + WORK_TIMER) > 150.0f) {
            /* 0x839598 (the signed byte at work+0xef) is one of the 19 calls #55 owes. */
            blocked_55_call(0x00839598u);
        }
        if (mhuc_f32(call, work + WORK_AIM_Z) > CAP_7_22_2) {
            mhuc_put_f32(call, work + WORK_AIM_Z, CAP_7_22_2);
        }
        return;
    }
    case 3: {
        mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, SPEED_FLOOR, 0.0f, NULL);
        mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            start_motion(call, enemy, MOTION_7_22_3);
            mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        }
        return;
    }
    case 4: {
        mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, SPEED_FLOOR, 0.0f, NULL);
        mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        timer_add(call, enemy, work);
        if ((int)mhuc_f32(call, work + WORK_TIMER) <= 6) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        mhuc_write8(call, work + WORK_SUBSTATE, 0u);
        if (a == 1) {
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            start_motion(call, enemy, MOTION_7_22_4A);
            mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, 0.0f, 0.0f, NULL);
        } else if (a == 2) {
            start_motion(call, enemy, MOTION_7_22_4B);
        } else {
            start_motion(call, enemy, MOTION_7_22_4C);
            mhuc_put_f32(call, work + WORK_AIM2_Z, -3.5f);
            mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        }
        return;
    }
    case 5:
        if (a == 1) {
            const int sub = (int)mhuc_read8(call, work + WORK_SUBSTATE);
            if (sub == 0) {
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_write8(call, work + WORK_SUBSTATE, 1u);
                    start_motion(call, enemy, MOTION_7_22_5A);
                }
            } else if (sub == 1) {
                if (mhuc_call_f(call, FN_MODE_STEP, enemy, 0u, 0u, 0u, 30.0f, 0.0f, NULL)) {
                    mhuc_call(call, FN_STALL_FLAG, enemy, 0u, 0u, 0u);
                }
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_3u_base_0_2(call, enemy, work);
                }
            }
        } else if (a == 2) {
            const int sub = (int)mhuc_read8(call, work + WORK_SUBSTATE);
            if (sub == 0) {
                if (mhuc_f32(call, work + WORK_TIMER) < 10.0f) {
                    timer_add(call, enemy, work);
                    const float step = (MOVE_Y_STEP - mhuc_f32(call, work + WORK_TIMER)) *
                                       SPEED_FLOOR * 0.2f;
                    mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, step, 0.0f, NULL);
                }
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_write8(call, work + WORK_SUBSTATE, 1u);
                    mhuc_call(call, FN_STALL_FLAG, enemy, 0u, 0u, 0u);
                    mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
                    start_motion(call, enemy, MOTION_7_22_5B);
                }
            } else if (sub == 1) {
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_3u_base_0_2(call, enemy, work);
                }
            }
        } else {
            if (mhuc_f32(call, work + WORK_TIMER) < PHASE_STEP) {
                timer_add(call, enemy, work);
                const float step = (PHASE_STEP - mhuc_f32(call, work + WORK_TIMER)) *
                                    -150.0f * 0.05f;
                mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, step, 0.0f, NULL);
            }
            if (mhuc_call_f(call, FN_MODE_STEP, enemy, 0u, 0u, 0u, 30.0f, 0.0f, NULL)) {
                mhuc_call(call, FN_STALL_FLAG, enemy, 0u, 0u, 0u);
            }
            mhuc_call_f(call, FN_ADVANCE_B, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
            if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
            }
            if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                mhuc_3u_base_0_6(call, enemy, work);
            }
        }
        return;
    default:
        return;
    }
}

/* 0x00696cd8, 7/31: three states and a sub-state, over the target line. */
static void run_7_31(MH4UCall *call, uint32_t enemy, uint32_t work) {
    set_flight_flag(call, enemy);
    const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        flight_part_step(call, enemy, work);
        start_motion(call, enemy, MOTION_7_31);
        mhuc_call(call, FN_GROUP, enemy, 0u, 0x17u, 0u);
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
        const float ratio = distance_ratio(call, work, 0.0f, 3.8f, 450.0f);
        if (line) {
            mhuc_put_f32(call, line, ratio);
        }
        return;
    }
    case 1: {
        /* The source's 0x83c6e0 table lookups feed the vertical step and aim A's z. */
        blocked_table_step();
        const uint32_t bits = mhuc_read32(call, work + WORK_SPEED);
        if (bits > 0xc2480000u) {
            mhuc_put_f32(call, work + WORK_SPEED, -50.0f);
        }
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_TURN_LINE, enemy, work + WORK_TURN, 0u, 0u, data, 0.0f, NULL);
        if (!mhuc_call_f(call, FN_MODE_STEP, enemy, 1u, 0u, 0u, DELAY_7_31, 1.0f, NULL)) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_31, 0u, 0u);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            start_motion(call, enemy, MOTION_7_31_1);
        }
        return;
    }
    case 2: {
        if ((int)mhuc_read8(call, work + WORK_SUBSTATE) == 0) {
            if (!mhuc_call_f(call, FN_MODE_STEP, enemy, 1u, 0u, 0u, DELAY_7_31_2, 1.0f, NULL)) {
                return;
            }
            mhuc_write8(call, work + WORK_SUBSTATE, 1u);
        }
        /* 0x839598 gates the source's request for 1/3 or 1/8; #55 owes it. */
        blocked_55_call(0x00839598u);
        return;
    }
    default:
        return;
    }
}

/* 0x00696f4c, 7/33: four states; the last state's four table lookups are blocked. */
static void run_7_33(MH4UCall *call, uint32_t enemy, uint32_t work) {
    set_flight_flag(call, enemy);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        flight_part_step(call, enemy, work);
        start_motion(call, enemy, MOTION_7_33);
        mhuc_call(call, FN_GROUP4, enemy, 0u, 6u, 8u);
        mhuc_call(call, FN_GROUP4, enemy, 1u, 3u, 0x10u);
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_SET_SPEED, enemy, 0u, 0u, 0u, 0.0f, 0.0f, NULL);
        return;
    }
    case 1: {
        mhuc_call(call, FN_TURN, enemy, TURN_7_33, 0u, 0u);
        blocked_55_call(0x00842a7cu);
        if (!mhuc_call_f(call, FN_MODE_STEP, enemy, 0u, 0u, 0u, RANGE_7_33, 0.0f, NULL)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        return;
    }
    case 2: {
        blocked_table_step();
        const uint32_t r0 = mhuc_call_f(call, FN_MODE_STEP, enemy, 1u, 0u, 0u, CAP_7_35, 0.0f,
                                        NULL);
        const uint32_t bits = mhuc_read32(call, work + WORK_SPEED);
        if (r0) {
            if (bits > 0x80000000u) {
                mhuc_put_f32(call, work + WORK_SPEED, 0.0f);
            }
        } else if (bits > 0xc2480000u) {
            mhuc_put_f32(call, work + WORK_SPEED, SPEED_FLOOR);
        }
        mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            start_motion(call, enemy, MOTION_7_33_1);
        }
        return;
    }
    default:
        return;
    }
}

/* 0x006971c0, 7/35 and its seven siblings: the vertical step runs every frame, then two
 * states.  a = the case block's r1 (0..3), b = its r2 (0/1). */
static void run_7_35(MH4UCall *call, uint32_t enemy, uint32_t work, int a, int b) {
    (void)a;
    mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, VERTICAL_7_35, 0.0f, NULL);
    if (mhuc_read32(call, work + WORK_SPEED) > VERTICAL_FLOOR_BITS) {
        mhuc_put_f32(call, work + WORK_SPEED, VERTICAL_FLOOR);
    }
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        flight_part_step(call, enemy, work);
        start_motion(call, enemy, MOTION_7_35);
        mhuc_call(call, FN_CLEAR_AIM_A, enemy, 0u, 0u, 0u);
        return;
    }
    case 1: {
        if (!mhuc_call_f(call, FN_MODE_STEP, enemy, 1u, 0u, 0u, DELAY_7_35, 0.0f, NULL)) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_35, 0u, 0u);
            blocked_55_call(0x00842a7cu);
        }
        if (b == 0) {
            blocked_table_step();
        }
        if (mhuc_call_f(call, FN_MODE_STEP, enemy, 0u, 0u, 0u, RANGE_7_35, 0.0f, NULL)) {
            blocked_effect_step();
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_6(call, enemy, work);
        }
        return;
    }
    case 2: {
        blocked_table_step();
        const uint32_t r0 = mhuc_call_f(call, FN_MODE_STEP, enemy, 1u, 0u, 0u, CAP_7_35, 0.0f,
                                        NULL);
        const uint32_t bits = mhuc_read32(call, work + WORK_SPEED);
        if (r0) {
            if (bits > 0x80000000u) {
                mhuc_put_f32(call, work + WORK_SPEED, 0.0f);
            }
        } else if (bits > 0xc2480000u) {
            mhuc_put_f32(call, work + WORK_SPEED, SPEED_FLOOR);
        }
        mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            start_motion(call, enemy, MOTION_7_35_1);
        }
        return;
    }
    default:
        return;
    }
}

/* 0x0069747c, 7/36 and its nine siblings: four states.  a = the case block's r1 (0..4),
 * b = its r2 (0/1). */
static void run_7_36(MH4UCall *call, uint32_t enemy, uint32_t work, int a, int b) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        flight_part_step(call, enemy, work);
        start_motion(call, enemy, MOTION_7_36);
        if (a == 2 || a == 3) {
            mhuc_call(call, FN_CLEAR_AIM_A, enemy, 0u, 0u, 0u);
            mhuc_put_f32(call, work + WORK_AIM_Z, 10.0f);
        } else if (a == 4) {
            mhuc_call(call, FN_CLEAR_AIM_A, enemy, 0u, 0u, 0u);
            mhuc_put_f32(call, work + WORK_AIM_Z, -10.0f);
        }
        return;
    }
    case 1: {
        mhuc_call(call, FN_TURN, enemy, TURN_7_36, 0u, 0u);
        if (a >= 2) {
            mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            mhuc_write8(call, work + WORK_SUBSTATE, 0u);
            start_motion(call, enemy, MOTION_7_36_1);
        }
        return;
    }
    case 2: {
        if (a == 1) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_36, 0u, 0u);
        } else if (a == 2) {
            mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        } else if (a == 3 || a == 4) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_36_FAR, 0u, 0u);
            mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
            blocked_55_call(0x00842a7cu);
        }
        if (mhuc_call_f(call, FN_MODE_STEP, enemy, 0u, 0u, 0u, RANGE_7_36, 0.0f, NULL)) {
            if (a != 1 && mhuc_read8(call, work + WORK_KIND) == 0x41u) {
                mhuc_log(MH4U_LOG_INFO,
                         "blocked: 7/36's part bytes work+0x2b4/+0x2b6 have no MH4U offset; the "
                         "turn step keeps the source's default");
            }
            if (b != 0) {
                blocked_effect_step();
                mhuc_write8(call, work + WORK_SUBSTATE,
                            (uint32_t)(mhuc_read8(call, work + WORK_SUBSTATE) + 1u));
            }
        }
        if ((a == 1 || a == 3 || a == 4) && (int)mhuc_read8(call, work + WORK_SUBSTATE) < 3) {
            return;
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            start_motion(call, enemy, MOTION_7_36_2);
        }
        return;
    }
    default:
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_3(call, enemy, work);
        }
        return;
    }
}

/* 0x00697888 through the 0x00686bcc stub, 7/37 and its six siblings.  a = r1 (0..5), b = r2
 * (0/1), c = r3 (0..3, the part group) and d = the stacked fifth argument (0/1). */
static void run_7_37(MH4UCall *call, uint32_t enemy, uint32_t work, int a, int b, int c,
                     int d, int index) {
    mhuc_call(call, FN_GROUP, enemy, 0x20u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0: {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUBSTATE, 0u);
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        flight_part_step(call, enemy, work);
        start_motion(call, enemy, MOTION_7_37);
        switch (c) {
        case 1: mhuc_call(call, FN_GROUP, enemy, 0u, 0x2au, 0u); break;
        case 2: mhuc_call(call, FN_GROUP, enemy, 0u, 0x2bu, 0u); break;
        case 3: mhuc_call(call, FN_GROUP, enemy, 0u, 0x2cu, 0u); break;
        default: mhuc_call(call, FN_GROUP, enemy, 0u, 0x1fu, 0u); break;
        }
        if (a == 0 || a == 3 || a == 5) {
            MhucState *slot = mhuc_state(call, enemy, 7, index, NULL);
            if (slot) {
                slot_put_point(slot, work, call);
            }
            const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
            if (line) {
                const uint32_t heading = mhuc_read32(call, work + WORK_HEADING);
                mhuc_write32(call, line + 4u,
                             (mhuc_read32(call, line + 4u) & 0xffff0000u) | (heading & 0xffffu));
            }
        }
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
        const float timer = PHASE_7_37 / mhuc_f32(call, enemy + 0x29cu);
        mhuc_put_f32(call, work + WORK_TIMER, timer);
        return;
    }
    case 1: {
        set_flight_flag(call, enemy);
        blocked_55_call(0x00842a7cu);
        if (a == 2 || a == 3) {
            if (mhuc_call_f(call, FN_MODE_STEP, enemy, 2u, 0u, 0u, DELAY_7_37_A, 0.0f, NULL)) {
                mhuc_call(call, FN_TURN, enemy, TURN_7_37_A, 0u, 0u);
            }
        } else if (a == 4 || a == 5) {
            if (mhuc_call_f(call, FN_MODE_STEP, enemy, 2u, 0u, 0u, DELAY_7_37_B, 0.0f, NULL)) {
                mhuc_call(call, FN_TURN, enemy, TURN_7_37_B, 0u, 0u);
            }
        } else if (mhuc_call_f(call, FN_MODE_STEP, enemy, 2u, 0u, 0u, RANGE_7_37_C, 0.0f,
                               NULL)) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_37_B, 0u, 0u);
        }
        if (!mhuc_call_f(call, FN_MODE_STEP, enemy, 3u, 0u, 0u, DELAY_7_37_C, RANGE_7_37_C,
                         NULL)) {
            const float timer = mhuc_f32(call, work + WORK_TIMER);
            if (timer > 0.0f) {
                float data = 0.0f;
                mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
                float record = 0.0f;
                mhuc_call_f(call, FN_DATA_GET, enemy, (uint32_t)a, 0u, 0u, 0.0f, 0.0f, &record);
                mhuc_put_f32(call, work + WORK_AIM, 0.0f);
                mhuc_put_f32(call, work + WORK_AIM_Y,
                             (mhuc_f32(call, work + WORK_TARGET_Y) -
                              mhuc_f32(call, work + WORK_POS_Y) +
                              (data - 100.0f) * record) / timer);
                if (mhuc_f32(call, work + WORK_AIM_Y) > 0.0f) {
                    mhuc_put_f32(call, work + WORK_AIM_Y, 0.0f);
                }
                const uint32_t angle = angle_to(call, work, WORK_POS, WORK_TARGET);
                const uint32_t rel = (angle - mhuc_read32(call, work + WORK_HEADING) + 0x4000u) &
                                     0xffffu;
                if (rel < 0x8000u) {
                    const float dist = distance_to(call, work, WORK_POS, WORK_TARGET);
                    float record2 = 0.0f;
                    mhuc_call_f(call, FN_DATA_GET, enemy, (uint32_t)a, 0u, 0u, 0.0f, 0.0f,
                                &record2);
                    mhuc_put_f32(call, work + WORK_AIM_Z,
                                 (dist - record2 * 100.0f) / timer);
                    if (mhuc_f32(call, work + WORK_AIM_Z) <= AIM_Z_7_37) {
                        mhuc_put_f32(call, work + WORK_AIM_Z, AIM_Z_7_37);
                    }
                } else {
                    mhuc_put_f32(call, work + WORK_AIM_Z, AIM_Z_7_37);
                }
                float data2 = 0.0f;
                mhuc_call_f(call, FN_DATA, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data2);
                mhuc_call_f(call, FN_TURN_LINE, enemy, work + WORK_TURN, 0u, 0u, data2, 100.0f,
                            NULL);
            }
        }
        timer_sub(call, enemy, work);
        if (!mhuc_call_f(call, FN_MODE_STEP, enemy, 1u, 0u, 0u, SPEED_7_37, 0.0f, NULL)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        blocked_55_call(0x0083c6ccu);
        return;
    }
    case 2: {
        if (a == 0 || a == 3 || a == 5) {
            if (b == 0) {
                const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
                const uint32_t dest = line ? (mhuc_read32(call, line + 4u) & 0xffffu)
                                           : (mhuc_read32(call, work + WORK_HEADING) & 0xffffu);
                const uint32_t turn = mhuc_call(call, FN_ANGLE_STEP, enemy, dest,
                                                mhuc_read32(call, work + WORK_HEADING), 0x300u);
                mhuc_write32(call, work + WORK_HEADING, turn);
            }
            mhuc_call(call, FN_CLEAR_AIM_A, enemy, 0u, 0u, 0u);
            const float timer = mhuc_f32(call, work + WORK_TIMER);
            if (timer > 0.0f) {
                MhucState *slot = mhuc_state(call, enemy, 7, index, NULL);
                float point[3] = {0.0f, 0.0f, 0.0f};
                if (slot) {
                    slot_get_point(slot, point);
                }
                mhuc_put_f32(call, work + WORK_AIM,
                             (point[0] - mhuc_f32(call, work + WORK_POS)) / timer);
                mhuc_put_f32(call, work + WORK_AIM_Y,
                             (point[1] - mhuc_f32(call, work + WORK_POS_Y)) / timer);
                mhuc_put_f32(call, work + WORK_AIM_Z,
                             (point[2] - mhuc_f32(call, work + WORK_POS + 8u)) / timer);
                mhuc_call_f(call, FN_MOVE_BY_AIM, enemy, 0u, 0u, 0u, 1.0f, 0.0f, NULL);
            }
            timer_sub(call, enemy, work);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            if (a == 1 || a == 2 || (a == 4 && d == 1)) {
                mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
                start_motion(call, enemy, MOTION_7_37_1);
                mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
            } else {
                mhuc_3u_base_0_3(call, enemy, work);
            }
        }
        return;
    }
    default:
        mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, VERTICAL_7_35, 0.0f, NULL);
        if (mhuc_read32(call, work + WORK_SPEED) > VERTICAL_FLOOR_BITS) {
            mhuc_put_f32(call, work + WORK_SPEED, VERTICAL_FLOOR);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_6(call, enemy, work);
        }
        return;
    }
}

/* ── the family's dispatch and self-test ────────────────────────────────────────────── */

static int dispatch_cat7c(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    if (category != 7) {
        return 0;
    }
    switch (index) {
    case 22: run_7_22(call, enemy, work, 0, 0); return 1;
    case 23: run_7_22(call, enemy, work, 1, 0); return 1;
    case 24: run_7_22(call, enemy, work, 0, 1); return 1;
    case 25: run_7_22(call, enemy, work, 1, 1); return 1;
    case 26: run_7_22(call, enemy, work, 0, 2); return 1;
    case 27: run_7_22(call, enemy, work, 1, 2); return 1;
    case 28: run_7_22(call, enemy, work, 0, 3); return 1;
    case 29: run_7_22(call, enemy, work, 1, 3); return 1;
    case 31: run_7_31(call, enemy, work); return 1;
    case 33: run_7_33(call, enemy, work); return 1;
    case 35: run_7_35(call, enemy, work, 0, 0); return 1;
    case 46: run_7_35(call, enemy, work, 1, 0); return 1;
    case 47: run_7_35(call, enemy, work, 2, 0); return 1;
    case 48: run_7_35(call, enemy, work, 3, 0); return 1;
    case 62: run_7_35(call, enemy, work, 0, 1); return 1;
    case 63: run_7_35(call, enemy, work, 1, 1); return 1;
    case 64: run_7_35(call, enemy, work, 2, 1); return 1;
    case 65: run_7_35(call, enemy, work, 3, 1); return 1;
    case 36: run_7_36(call, enemy, work, 0, 0); return 1;
    case 38: run_7_36(call, enemy, work, 1, 0); return 1;
    case 39: run_7_36(call, enemy, work, 2, 0); return 1;
    case 40: run_7_36(call, enemy, work, 3, 0); return 1;
    case 49: run_7_36(call, enemy, work, 0, 1); return 1;
    case 50: run_7_36(call, enemy, work, 1, 1); return 1;
    case 51: run_7_36(call, enemy, work, 2, 1); return 1;
    case 52: run_7_36(call, enemy, work, 3, 1); return 1;
    case 57: run_7_22(call, enemy, work, 2, 3); return 1;
    case 59: run_7_36(call, enemy, work, 4, 0); return 1;
    case 60: run_7_36(call, enemy, work, 4, 1); return 1;
    case 37: run_7_37(call, enemy, work, 0, 0, 0, 0, index); return 1;
    case 84: run_7_37(call, enemy, work, 0, 1, 1, 1, index); return 1;
    case 86: run_7_37(call, enemy, work, 2, 0, 2, 0, index); return 1;
    case 87: run_7_37(call, enemy, work, 3, 0, 3, 0, index); return 1;
    case 92: run_7_37(call, enemy, work, 4, 0, 2, 0, index); return 1;
    case 93: run_7_37(call, enemy, work, 5, 0, 2, 0, index); return 1;
    case 96: run_7_37(call, enemy, work, 5, 1, 1, 1, index); return 1;
    default: return 0;
    }
}

/* What this family carries.  The module's self-test calls this with the other families'. */
static void self_test_cat7c(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 36 of the 191 actions: 7/22-7/29 and 7/57 <- 0x00696580 (five states, "
             "the flight byte at +0x3e3 and the phase byte at +0x3c4); 7/31 <- 0x00696cd8 "
             "(three states, the target line); 7/33 <- 0x00696f4c (four states); 7/35, "
             "7/46-7/48 and 7/62-7/65 <- 0x006971c0 (two states, a vertical step every frame); "
             "7/36, 7/38-7/40, 7/49-7/52 and 7/59-7/60 <- 0x0069747c (four states); 7/37, "
             "7/84, 7/86-7/87, 7/92-7/93 and 7/96 <- 0x00686bcc/0x00697888 (three states, the "
             "part group from r3)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: category 7's engine calls are MH4U's: flight set 0x%08x, motion "
              "0x%08x, mode 0x%08x, flag 0x%08x, data 0x%08x, fall 0x%08x",
              (unsigned)FN_FLIGHT_SET, (unsigned)FN_MOTION, (unsigned)FN_MODE,
              (unsigned)FN_FLAG, (unsigned)FN_DATA, (unsigned)FN_APPLY_FALL);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: +0x5/+0x6 -> +0x144/+0x145, +0x28 -> +0x1d4, "
             "+0x68 -> +0x180, +0x80/+0x84 -> +0x1a8/+0x1ac, +0x260/+0x268 -> +0x160/+0x168, "
             "+0x288 -> +0x218, +0x7c9 -> +0x3c4, +0x7eb -> +0x3e3, this+0x1e70 -> "
             "*(this+0x8d88)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: blocked: 0x00842a7c, 0x00839598 and 0x0083c6cc (#55); the table "
             "interpolation 0x0083c6e0/0x00584760 and the effect spawn 0x00164f08 (source "
             "data); work+0x2b4/+0x2b6 and work+0x70 (no MH4U offset)");
}

/* The family file's one export. */
const MhucFamily mhuc_3u_family_cat7c = {
    "cat7c", 36, dispatch_cat7c, self_test_cat7c,
};
