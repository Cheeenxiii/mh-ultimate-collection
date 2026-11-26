/*
 * cat7d.c: 3U Rathian's category 7, part 4 — the sixteen ids on nine handler units and one
 * inline block: 7/45 (0x00697e78), 7/58 (0x00697ff0), 7/66 (0x00698144), 7/67, 7/69 and 7/70
 * (0x00698408 with r1 = 0, 1, 2), 7/68 (0x006986b8), 7/71 (0x00698c48), 7/74, 7/90 and 7/91
 * (0x00698db8 with r1 = 0, 1, 2), 7/75 and 7/94 (the base-class 0x00829c88 with r1 = 0, 1),
 * 7/76 and 7/95 (0x006993fc with r1 = 0, 1) and the inline case block 0x00686bb8 (7/81, into
 * 0x00697888 with r1 = 1, r2 = 0, r3 = 2 and 0 on the stack).
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h). The handlers,
 * their offsets, their frame values and their call order are the ones issue #224 translated
 * from MH3U USA's recompiled code; the runtime's README carries the field map, the call map,
 * the rows this slice adds and the calls it leaves blocked. MH4U's own handlers for the same
 * ids were read beside the source's as the paired-handler evidence.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The state and
 * sub-state bytes are the game's own (MH4U work+0x144/+0x145/+0x146), as category 0 uses them.
 * The target-line struct is MH4U's *(enemy + 0x8d88) (3U's this+0x1e70). Two base handlers
 * this family falls into are cat0.c's: 0/2's 0x0082d1cc (mhuc_3u_base_0_2) and 0/6's
 * 0x0082b7dc (mhuc_3u_base_0_6).
 *
 * The source's own helpers 0x006872ec (the enemy-data kind to a part value) and 0x00697888
 * (the flight attack) are translated here too. Calls #55 still blocks are named and logged
 * once, never invented: 0x00842a7c (a hit/attack resolution), 0x0083c6cc (a float from the
 * source's block), 0x00839598 (the signed byte at +0xef), the effect setup 0x00688a20 /
 * 0x00688870 with their 0x0015f410/0x00164f08 factories, and the table interpolations
 * 0x00584760 and 0x0083c6e0 where their argument is MH3U data.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <string.h>

#include "family.h"

/* ── the MH4U work block, its offsets and the 3U offset each stands for ──────────────── */
#define WORK_STATE        0x0144u /* 3U +0x5:  the handler's state byte */
#define WORK_SUB          0x0145u /* 3U +0x6:  its sub-state */
#define WORK_SUB2         0x0146u /* 3U +0x7:  a third sub-state */
#define WORK_MODE         0x01c8u /* 3U +0xdc: the mode byte */
#define WORK_SET          0x01dcu /* 3U +0xf2: "the action was set" */
#define WORK_TIMER        0x01d4u /* 3U +0x28/+0x2c: the frame timer */
#define WORK_SPEED        0x0180u /* 3U +0x68: the speed accumulated by the vertical step */
#define WORK_TURN         0x01a8u /* 3U +0x80: the turn slot before the heading */
#define WORK_HEADING      0x01acu /* 3U +0x84: the heading */
#define WORK_AIM_X        0x0160u /* 3U +0x260: aim point A x */
#define WORK_AIM_Y        0x0164u /* 3U +0x264: aim point A y */
#define WORK_AIM_Z        0x0168u /* 3U +0x268: aim point A z */
#define WORK_AIM_B_Z      0x0178u /* 3U +0x278: aim vector B z */
#define WORK_TARGET       0x0218u /* 3U +0x288: the target point x */
#define WORK_TARGET_Z     0x0220u /* 3U +0x28c: the target point z */
#define WORK_POS          0x0198u /* 3U +0x38: position x, y, z */
#define WORK_POS_Y        0x019cu /* 3U +0x3c: position y */
#define WORK_VERTICAL_LIMIT 0x0624u /* 3U +0x120: the vertical limit */
#define WORK_MARKED       0x03c4u /* 3U +0x7c9: the "flying" byte 0x8310f0 sets */
#define WORK_KIND         0x01c0u /* 3U +0x3: the enemy-data kind */
#define WORK_FLAG_BYTE    0x0559u /* 0x832670's flag byte */
#define WORK_FRAME_PTR    0x0030u /* 3U +0x30: the pointer to the frame delta (3U only) */

/* The MH4U engine functions this family calls, and the 3U function each stands for. */
#define FN_MODE          0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION        0x0094e318u /* [0x00828828] start a motion (index r1; s0 speed) */
#define FN_FLAG          0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_DATA_FLOAT    0x0093d870u /* [0x00852324] the action data's float, in s0 */
#define FN_APPLY_FALL    0x0092e99cu /* [0x00844124] advance the fall by s0, set mode 1 */
#define FN_GROUP         0x00914dc4u /* [0x00844a38] a part group / the shared shell (r1, r2) */
#define FN_GROUP4        0x0093310cu /* [0x00844a40] a part group with r1, r2, r3 */
#define FN_FLIGHT        0x00922ca0u /* [0x0083d18c] mark the action's flight byte */
#define FN_PART          0x0091b7b0u /* [0x008345f8] the part/type step, value in r1 */
#define FN_RANGE         0x0091aae4u /* [0x0083336c] the per-mode distance gate (r1; s0, s1) */
#define FN_TURN          0x0091db4cu /* [0x008357b0] turn toward the target at a rate in r1 */
#define FN_TURN_HOLD     0x0091b430u /* [0x00839ea0] turn and hold at the vertical limit */
#define FN_TURN_LINE     0x0091656cu /* [0x00839514] advance by s1, then the limit step of s0 */
#define FN_ADVANCE       0x009114d4u /* [0x0082cee4] advance the position along the path */
#define FN_ADVANCE_B     0x00911090u /* [0x00834098] advance A by B times the delta */
#define FN_SPEED         0x00916108u /* [0x00833d88] set the speed to s0 */
#define FN_RATE          0x00923f90u /* [0x0083db3c] the per-monster rate, in s0 */
#define FN_CURVE         0x00922250u /* [0x0083c6e0] evaluate a table at this speed */
#define FN_VERTICAL      0x00915d44u /* [0x00833b2c] advance the vertical value by s0 */
#define FN_TURN2         0x0092fc84u /* [0x0083d884] turn the two joints by r1/r2 */
#define FN_POINT_TURN    0x0092dcccu /* [0x008438e8] turn the two joints by a rate in r2 */
#define FN_SETUP_POINT   0x0092dc50u /* [0x008437f4] set up a turn's point */
#define FN_CLEAR_AIM     0x0091b3bcu /* [0x00839968] clear aim point A and vector B */
#define FN_NEXT_ACTION   0x0094ef64u /* [0x0082a06c] request the next action (r1, r2) */
#define FN_SET_PAIR      0x00935f8cu /* [0x0082ffbc] the r1/r2/r3 action pair */
#define FN_GET_BYTE      0x00918f38u /* [0x00837594] the per-part byte in r0 */
#define FN_STALL         0x0090f8fcu /* [0x0082c1c4] the action's stall flag */
#define FN_CHECK         0x00942220u /* [0x0083369c] the height test, returns a flag */
#define FN_DIST3         0x00aacc0cu /* [0x005852b4] the 3D distance between two points */
#define FN_DIST2         0x00aacd50u /* [0x005858f4] the x/z distance between two points */
#define FN_ANGLE         0x00568c64u /* [0x00584cd8] the angle from a point to a point */
#define FN_SET_FLAG      0x00914de0u /* [0x00832670] set a work flag bit */

/* The MH4U tables that stand for the source's, where the two games' data is identical: the
 * 7/45 curves 0x00c4ecf8/0x00c4ed20 are MH4U's 0x00fd18f0/0x00fd1918 word for word, and
 * 7/74's 0x00c4ee30 is MH4U's 0x00fd1a28 (20 words compared). MH4U's own 7/45 handler passes
 * its own two; no 3U data is carried. */
#define CURVE_7_45_A     0x00fd18f0u
#define CURVE_7_45_B     0x00fd1918u
#define CURVE_7_74       0x00fd1a28u

/* The source's frame values, kept as the source passes them. A turn rate is halved for MH4U:
 * 3U's turn helper 0x8392d8 multiplies the rate by 0.5 in its own body, MH4U's 0x0091aaf0
 * does not. The vertical step -5.0 is halved for the same reason (0x833b2c halves, 0x00915d44
 * does not); the 7/45 clamp keeps the source's -300.0/0.0. */
#define MOTION_SPEED      4.0f
#define MOTION_SPEED_6    6.0f
#define MOTION_SPEED_0    0.0f
#define TURN_7_45        0x080u   /* 3U 0x100 */
#define TURN_7_67        0x040u   /* 3U 0x80 */
#define TURN_7_66        0x02du   /* 3U 0x5b halved (0x2d.5, truncated by the integer rate) */
#define TURN_7_71        0x111u   /* 3U 0x222 */
#define TURN_7_74        0x111u   /* 3U 0x222 */
#define TURN_7_74_A      0x0a8u   /* 3U 0x150 */
#define TURN_7_75        0x100u   /* 3U 0x200 */
#define TURN_7_75_3      0x300u   /* 3U 0x600 */
#define TURN_7_76        0x100u   /* 3U 0x200 */
#define TURN_7_81        0x180u   /* 3U 0x300 */
#define VERTICAL_STEP    (-2.5f)  /* the source's -5.0, halved as 3U's 0x833b2c does */
#define VERTICAL_CLAMP   (-75.0f)
#define VERTICAL_CLAMP_BITS 0xc2960000u
#define LIMIT_OVER        350.0f  /* the target kept this far above the vertical limit */
#define LIMIT_BIAS        200.0f  /* 7/76's -200.0 speed/vertical floor */
#define AIM_Y_7_75        5.0f
#define AIM_B_Z_7_75      3.0f
#define AIM_CLAMP_7_75    70.0f
#define AIM_B_Z_7_75_3    (-3.2f)
#define AIM_B_Z_7_75_4    (-6.8f)
#define AIM_Y_7_74        (-10.0f)
#define SETUP_HEIGHT      (-850.0f)
#define RATE_500          500.0f
#define FALL_7_74         398.31f
#define AIM_Z_7_74_A      34.0f
#define AIM_B_Z_7_74_A    (-3.0f)
#define CHECK_CLAMP       110.0f
#define CHECK_CLAMP_BITS  0xc3480000u /* -200.0 */
#define WAIT_7_81         20.0f
#define RANGE_7_81_A      80.0f
#define RANGE_7_81_B      60.0f
#define RANGE_7_81_C      100.0f
#define RANGE_7_81_D      150.0f
#define DIST_BIAS_7_81    100.0f
#define AIM_MIN_7_81      30.0f
#define SPEED_7_81        200.0f
#define THIRD_7_74        0x64u   /* the source's r3 = 0x64 on 7/74's 0xcd motion */

/* The source's motion numbers, MH3U's file * 100 + slot; motion() converts them to MH4U's
 * file << 8 | slot. All but 0x38 and 0x3d are file 2's. */
#define MOTION_7_45       0x38u
#define MOTION_7_58       0xdbu   /* file 2, slot 19 */
#define MOTION_7_66       0xddu   /* file 2, slot 21 */
#define MOTION_7_67       0xdeu   /* file 2, slot 22 */
#define MOTION_7_68       0xdfu   /* file 2, slot 23 */
#define MOTION_7_68_END   0xdcu   /* file 2, slot 20 */
#define MOTION_7_74       0xe1u   /* file 2, slot 33 */
#define MOTION_7_74_2     0xe3u   /* file 2, slot 35 */
#define MOTION_7_74_3     0xdeu   /* file 2, slot 22 */
#define MOTION_7_74_A     0xcdu   /* file 2, slot 5 */
#define MOTION_7_74_B     0xe2u   /* file 2, slot 34 */
#define MOTION_7_74_C     0xe4u   /* file 2, slot 36 */
#define MOTION_7_74_D     0xceu   /* file 2, slot 14 */
#define MOTION_7_74_E     0xcfu   /* file 2, slot 15 */
#define MOTION_7_75       0x3du   /* file 0, slot 61 */
#define MOTION_7_75_1     0x3eu   /* file 0, slot 62 */
#define MOTION_7_75_2     0x2du   /* file 0, slot 45 */
#define MOTION_7_76       0xd1u   /* file 2, slot 17 */
#define MOTION_7_76_2     0xd0u   /* file 2, slot 16 */
#define MOTION_7_81       0xdbu   /* file 2, slot 19 */
#define MOTION_7_81_2     0x1bu   /* file 0, slot 27 */

/* ── the blocked calls (#55) ─────────────────────────────────────────────────────────── */

static uint32_t blocked_seen[8];
static int blocked_count;
static int blocked_effects_logged;

/* Name one source call that #55 still blocks, once per address; its step is skipped and
 * nothing is invented for it. */
static void blocked_once(MH4UCall *call, uint32_t address, const char *what) {
    (void)call;
    for (int i = 0; i < blocked_count; i++) {
        if (blocked_seen[i] == address) {
            return;
        }
    }
    if (blocked_count < (int)(sizeof blocked_seen / sizeof blocked_seen[0])) {
        blocked_seen[blocked_count++] = address;
    }
    mhuc_logf(MH4U_LOG_INFO,
              "blocked: the source's 0x%08x (%s) has no MH4U counterpart (#55); its step is "
              "skipped", (unsigned)address, what);
}

/* 0x00688a20 builds a 0x14-byte point struct and its callees 0x00199d00/0x00829950 register a
 * uEffect via 0x0063cabc; 0x00688870 picks a sound/effect id by the enemy-data kind. MH4U's
 * effect factory takes its own setup block and no counterpart for the chain was found, so the
 * whole setup is named and skipped, as #218 did for the same chain on 2/4 to 2/6 and 9/3-4. */
static void blocked_effect_setup(MH4UCall *call) {
    (void)call;
    if (blocked_effects_logged) {
        return;
    }
    blocked_effects_logged = 1;
    mhuc_log(MH4U_LOG_INFO,
             "blocked: the source's effect setup (0x00688a20, 0x00688870 and their 0x00199d00, "
             "0x00829950, 0x0063cabc callees) has no MH4U counterpart yet; the effects are "
             "skipped and the moves play without them");
}

/* ── the shared engine steps ────────────────────────────────────────────────────────── */

/* MH3U's file * 100 + slot to MH4U's file << 8 | slot for her converted motion lists. */
static uint32_t motion_number(uint32_t m) {
    if (m < 100u) {
        return MHUC_MOTION(0u, m);
    }
    return MHUC_MOTION(m / 100u, m % 100u);
}

/* 3U 0x00828828: the source's r2 is the speed (its worker turns it into the motion's first
 * float); r3's float is the worker's other blend input, which MH4U's wrapper has no place for
 * and the port leaves at 0.0, as category 0 and category 3's part 2 do. */
static void motion(MH4UCall *call, uint32_t enemy, uint32_t m, float speed) {
    mhuc_call_f(call, FN_MOTION, enemy, motion_number(m), 0u, 0u, speed, 0.0f, NULL);
}

/* 3U 0x0083336c(mode, s0, s1): MH4U's 0x0091aae4 is the same wrapper (r3 = r2, r2 = 0). */
static int query(MH4UCall *call, uint32_t enemy, uint32_t mode, float s0, float s1) {
    return (int)mhuc_call_f(call, FN_RANGE, enemy, mode, 0u, 0u, s0, s1, NULL);
}

static int flag(MH4UCall *call, uint32_t enemy) {
    return (int)mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u);
}

/* 3U 0x00852324: the action data's float, in s0. */
static float data_float(MH4UCall *call, uint32_t enemy) {
    float out = 0.0f;
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &out);
    return out;
}

static void data_float_and_fall(MH4UCall *call, uint32_t enemy) {
    mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data_float(call, enemy), 0.0f, NULL);
}

/* 3U 0x0083db3c: the per-monster rate, in s0. */
static float rate(MH4UCall *call, uint32_t enemy) {
    float out = 0.0f;
    mhuc_call_f(call, FN_RATE, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &out);
    return out;
}

/* 3U 0x006872ec: the enemy-data kind and the mode pick a small part value, then 0x8345f8
 * (MH4U's 0x0091b7b0) applies it. The values are the source's; the switch is 0x6872ec's. */
static void part_step(MH4UCall *call, uint32_t enemy, uint32_t work) {
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

/* 3U 0x00839ea0(this, &work+0x80, s0, s1): the wrapper hands s1 to 0x834098 and s0 to the
 * vertical limit step. MH4U's 0x0091b430 keeps the r0 return of the limit step. */
static uint32_t turn_hold(MH4UCall *call, uint32_t enemy, uint32_t work, float s0, float s1) {
    return mhuc_call_f(call, FN_TURN_HOLD, enemy, work + WORK_TURN, 0u, 0u, s0, s1, NULL);
}

/* 3U 0x00839514(this, &work+0x80, s0, s1): advance by s1, then the limit step of s0. */
static void turn_line(MH4UCall *call, uint32_t enemy, uint32_t work, float s0, float s1) {
    mhuc_call_f(call, FN_TURN_LINE, enemy, work + WORK_TURN, 0u, 0u, s0, s1, NULL);
}

/* 3U 0x0082cee4(this, &work+0x80, s0): advance the position along the path. MH4U's
 * 0x009114d4 takes the turn slot's address (work+0x1a8) and ignores s0 (it always passes 1.0
 * to the same step), so the source's s0 = 1.0 is not carried. */
static void advance(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call_f(call, FN_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
}

/* 3U 0x00834098(this, &work+0x80, s0): advance aim A by aim B times the delta. */
static void advance_b(MH4UCall *call, uint32_t enemy, uint32_t work, float s0) {
    mhuc_call_f(call, FN_ADVANCE_B, enemy, work + WORK_TURN, 0u, 0u, s0, 0.0f, NULL);
}

/* 3U 0x00839968: clear aim point A and vector B. MH4U's 0x0091b3bc is the same store on the
 * work block (its own 7/45 handler calls it at the same point; the 73's 0x0096e164 clears a
 * different block). */
static void clear_aim(MH4UCall *call, uint32_t enemy) {
    mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
}

/* 3U 0x008310f0 sets 3U work+0x7c9; MH4U's own 3/8 handler stores the same at work+0x3c4
 * inline (the 73's 0x008310f0 -> 0x0093d870 row is not this step), so the port writes it. */
static void mark_flying(MH4UCall *call, uint32_t work) {
    mhuc_write8(call, work + WORK_MARKED, 1u);
}

/* 3U 0x00833b2c(-2.5) then the source's lower clamp at -75.0. */
static void step_vertical(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, VERTICAL_STEP, 0.0f, NULL);
    if (mhuc_read32(call, work + WORK_SPEED) > VERTICAL_CLAMP_BITS) {
        mhuc_put_f32(call, work + WORK_SPEED, VERTICAL_CLAMP);
    }
}

/* 3U 0x00697888's timer arithmetic: (float)(int16_t)(int)(a / b), as the source's
 * vcvt/vmov/sxth chain does it. A blocked divisor yields 0 rather than a trap. */
static float source_ratio(float numerator, float divisor) {
    if (divisor == 0.0f) {
        return 0.0f;
    }
    return (float)(int16_t)(int)(numerator / divisor);
}

/* 3U 0x005852b4: the 3D distance between two points; 3U 0x005858f4: its x/z form. */
static float distance3(MH4UCall *call, uint32_t a, uint32_t b) {
    float out = 0.0f;
    mhuc_call_f(call, FN_DIST3, a, b, 0u, 0u, 0.0f, 0.0f, &out);
    return out;
}

static float distance2(MH4UCall *call, uint32_t a, uint32_t b) {
    float out = 0.0f;
    mhuc_call_f(call, FN_DIST2, a, b, 0u, 0u, 0.0f, 0.0f, &out);
    return out;
}

/* 3U 0x00584cd8: the x/z angle from point r0 to point r1, as u16. MH4U's 0x00568c64 takes the
 * two differences in s0/s1 and returns the same angle. */
static uint32_t angle_to(MH4UCall *call, uint32_t from, uint32_t to) {
    const float dx = mhuc_f32(call, to) - mhuc_f32(call, from);
    const float dz = mhuc_f32(call, to + 8u) - mhuc_f32(call, from + 8u);
    return mhuc_call_f(call, FN_ANGLE, 0u, 0u, 0u, 0u, dx, dz, NULL);
}

/* A u16 in guest memory (the module has no 16-bit accessor): the copy 7/74 state 4 makes. */
static uint32_t read16(MH4UCall *call, uint32_t addr) {
    return mhuc_read8(call, addr) | (mhuc_read8(call, addr + 1u) << 8);
}

static void write16(MH4UCall *call, uint32_t addr, uint32_t value) {
    mhuc_write8(call, addr, value & 0xffu);
    mhuc_write8(call, addr + 1u, (value >> 8) & 0xffu);
}

/* ── 3U 0x00697e78: 7/45 ───────────────────────────────────────────────────────────── */

/*   0: state 1, mode 3, the part step, motion 0x38 at 6.0, the aim cleared, the speed 0.0,
 *      the shell (0, 0x1e);
 *   1: the 50.0 distance gate (a failed one turns at 0x100); the curve at 0x00fd18f0 into the
 *      vertical step, clamped to [-300.0, 0.0]; the curve at 0x00fd1918 into aim A z; the
 *      position advance; the flag, then 0/6's base handler. */
static void run_7_45(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_45, MOTION_SPEED_6);
        clear_aim(call, enemy);
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, 0.0f, 0.0f, NULL);
        mhuc_call(call, FN_GROUP, enemy, 0u, 0x1eu, 0u);
        return;
    }
    if (state != 1) {
        return;
    }
    if (!query(call, enemy, 1u, 50.0f, 0.0f)) {
        mhuc_call(call, FN_TURN, enemy, TURN_7_45, 0u, 0u);
    }
    float curve = 0.0f;
    mhuc_call_f(call, FN_CURVE, enemy, CURVE_7_45_A, 0u, 0u, 0.0f, 0.0f, &curve);
    mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, curve, 0.0f, NULL);
    if (mhuc_f32(call, work + WORK_SPEED) > 0.0f) {
        mhuc_put_f32(call, work + WORK_SPEED, 0.0f);
    } else if (mhuc_read32(call, work + WORK_SPEED) > 0xc3960000u) {
        mhuc_put_f32(call, work + WORK_SPEED, -300.0f);
    }
    float aim = 0.0f;
    mhuc_call_f(call, FN_CURVE, enemy, CURVE_7_45_B, 0u, 0u, 0.0f, 0.0f, &aim);
    mhuc_put_f32(call, work + WORK_AIM_Z, aim);
    advance(call, enemy, work);
    if (flag(call, enemy)) {
        mhuc_3u_base_0_6(call, enemy, work);
    }
}

/* ── 3U 0x00697ff0: 7/58 ───────────────────────────────────────────────────────────── */

/*   0: state 1, mode 0, the part step, motion 0xdb at 4.0;
 *   1: the 4.0 distance gate (a type-0x16 effect spawn), then the 108.0 gate with the effect
 *      setup and its type-0x15 spawn, then the flag and 0/2's base handler. Every effect call
 *      is #55-blocked and skipped; the two gates stay with their frame values. */
static void run_7_58(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_58, MOTION_SPEED);
        return;
    }
    if (state != 1) {
        return;
    }
    if (query(call, enemy, 0u, 4.0f, 0.0f)) {
        blocked_once(call, 0x0015f410u, "the type-0x16 effect spawn");
    }
    if (query(call, enemy, 0u, 108.0f, 0.0f)) {
        blocked_effect_setup(call); /* 0x00688a20, then 0x00164f08 and 0x00688870 */
    }
    if (flag(call, enemy)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── 3U 0x00698144: 7/66 ───────────────────────────────────────────────────────────── */

/*   0: state 1, mode 0, the part step, motion 0xdd at 4.0;
 *   1: the (3, 0.0, 60.0) gate (blocked 0x842a7c and a turn at 0x5b), then the (0, 116.0)
 *      gate: state 2 and the effect setup (a type 0xaab);
 *   2: the (3, 140.0, 160.0) gate and turn, the (0, 168.0) gate: state 3, the setup 0x11c7;
 *   3: the (3, 200.0, 220.0) gate and turn, the (0, 226.0) gate: state 4, the setup 0x18e4;
 *   4: the flag, then 0/2's base handler. */
static void run_7_66(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_66, MOTION_SPEED);
        return;
    }
    if (state >= 1 && state <= 3) {
        static const float ranges[3][2] = {{0.0f, 60.0f}, {140.0f, 160.0f}, {200.0f, 220.0f}};
        static const float after[3] = {116.0f, 168.0f, 226.0f};
        const int i = state - 1;
        if (query(call, enemy, 3u, ranges[i][0], ranges[i][1])) {
            blocked_once(call, 0x00842a7cu, "the attack resolution");
            mhuc_call(call, FN_TURN, enemy, TURN_7_66, 0u, 0u);
        }
        if (!query(call, enemy, 0u, after[i], 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        blocked_effect_setup(call); /* the setup 0xaab, 0x11c7 or 0x18e4 by state */
        return;
    }
    if (state == 4) {
        if (flag(call, enemy)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* ── 3U 0x00698408: 7/67, 7/69 and 7/70 ────────────────────────────────────────────── */

/*   0: state 1, mode 3, the part step, the aim cleared, the speed 0.0, motion 0xde at 4.0;
 *   1: the turn at 0x80, the blocked 0x842a7c, the curve samples (MH3U data: blocked, taken as
 *      0.0), the three distance gates, aim A from the sample difference, the advance, the
 *      vertical limit, the 80.0 gate with its 0x38e turn, then the flag, state 2, mode 0 and
 *      motion 0xdc. */
static void run_7_67(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        part_step(call, enemy, work);
        clear_aim(call, enemy);
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, 0.0f, 0.0f, NULL);
        motion(call, enemy, MOTION_7_67, MOTION_SPEED);
        return;
    }
    if (state != 1) {
        return;
    }
    mhuc_call(call, FN_TURN, enemy, TURN_7_67, 0u, 0u);
    blocked_once(call, 0x00842a7cu, "the attack resolution");
    /* The three samples 0x00c4d4fc/0x00c4d508/0x00c4d514 at this speed and at speed + 2.0
     * build the aim direction; those tables are MH3U data the port does not carry (no MH4U
     * table with the same keys was found), so each lookup is taken as 0.0. */
    blocked_once(call, 0x00584760u, "the table interpolation on MH3U data");
    const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
    float bias = 0.0f;
    float aim_x = 0.0f;
    float aim_y = 0.0f;
    float aim_z = 0.0f;
    if (query(call, enemy, 1u, 90.0f, 0.0f)) {
        if (!query(call, enemy, 1u, 130.0f, 0.0f)) {
            if (query(call, enemy, 1u, 120.0f, 0.0f)) {
                if (line) {
                    bias = mhuc_f32(call, line + 0x60u);
                    bias = (bias > 0.0f) ? bias - mhuc_f32(call, enemy + 0x14u) * 6.0f : 0.0f;
                    mhuc_put_f32(call, line + 0x60u, bias);
                }
            } else if (line) {
                bias = 0.0f;
                mhuc_put_f32(call, line + 0x60u, 0.0f);
            }
        } else if (line) {
            bias = 0.0f;
            mhuc_put_f32(call, line + 0x60u, 0.0f);
        }
        if (query(call, enemy, 2u, 120.0f, 0.0f)) {
            /* the third sample (this+0x27c) and the two distances; the samples are the
             * blocked 0.0, so the difference is 0.0 and the angle comparison leaves the bias
             * as it is. The two distance calls stay in order. */
            (void)distance3(call, work + WORK_POS, work + WORK_TARGET);
            (void)distance3(call, work + WORK_POS, work + WORK_POS);
        }
    }
    mhuc_put_f32(call, work + WORK_AIM_X, aim_x);
    mhuc_put_f32(call, work + WORK_AIM_Y, aim_y);
    mhuc_put_f32(call, work + WORK_AIM_Z, aim_z + bias);
    if (query(call, enemy, 1u, 90.0f, 0.0f)) {
        advance(call, enemy, work);
        const float limit = mhuc_f32(call, work + WORK_VERTICAL_LIMIT);
        if (limit < mhuc_f32(call, work + WORK_POS_Y)) {
            mhuc_put_f32(call, work + WORK_POS_Y, limit);
        }
        if (mhuc_f32(call, work + WORK_POS_Y) < limit + LIMIT_OVER) {
            mhuc_put_f32(call, work + WORK_POS_Y, limit + LIMIT_OVER);
        }
    } else {
        turn_line(call, enemy, work, mhuc_f32(call, work + WORK_VERTICAL_LIMIT) + LIMIT_OVER,
                  1.0f);
    }
    if (!query(call, enemy, 1u, 80.0f, 0.0f)) {
        mhuc_call(call, FN_TURN, enemy, 0x38eu, 0u, 0u);
    }
    if (flag(call, enemy)) {
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_7_68_END, MOTION_SPEED_0);
    }
}

/* ── 3U 0x006986b8: 7/68 ───────────────────────────────────────────────────────────── */

/*   0: state 1, mode 1, the part step, motion 0xdf at 6.0, the shell (0, 0x24), the aim
 *      cleared, the flight byte, the target line's +0x60 cleared;
 *   1: the aim direction from the three MH3U curve tables (blocked, taken as 0.0), the
 *      90.0/130.0/120.0/120.0 gates and the bias correction, aim A, the advance and the
 *      vertical limit, the 80.0 gate with its 0x38e turn, then the flag, state 2, mode 0 and
 *      motion 0xdc;
 *   2: the 30.0 gate, then the blocked 0x839598 (taken nonzero) and the request for 1/3 or
 *      8/0. */
static void run_7_68(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 1u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_68, MOTION_SPEED_6);
        mhuc_call(call, FN_GROUP, enemy, 0u, 0x24u, 0u);
        clear_aim(call, enemy);
        mhuc_call(call, FN_FLIGHT, enemy, 0u, 0u, 0u);
        const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
        if (line) {
            mhuc_put_f32(call, line + 0x60u, 0.0f);
        }
        return;
    }
    if (state == 1) {
        /* The three MH3U curve structs (0x00c4d4fc/0x00c4d508/0x00c4d514) at this speed and
         * at speed + 2.0 are blocked, taken as 0.0. */
        blocked_once(call, 0x00584760u, "the table interpolation on MH3U data");
        const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
        float bias = line ? mhuc_f32(call, line + 0x60u) : 0.0f;
        if (query(call, enemy, 1u, 90.0f, 0.0f)) {
            if (!query(call, enemy, 1u, 130.0f, 0.0f)) {
                if (query(call, enemy, 1u, 120.0f, 0.0f)) {
                    if (bias > 0.0f) {
                        bias -= mhuc_f32(call, enemy + 0x14u) * 6.0f;
                    } else {
                        bias = 0.0f;
                    }
                    if (line) {
                        mhuc_put_f32(call, line + 0x60u, bias);
                    }
                } else {
                    bias = 0.0f;
                    if (line) {
                        mhuc_put_f32(call, line + 0x60u, 0.0f);
                    }
                }
            } else {
                bias = 0.0f;
                if (line) {
                    mhuc_put_f32(call, line + 0x60u, 0.0f);
                }
            }
            if (query(call, enemy, 2u, 120.0f, 0.0f)) {
                /* the third sample and the two distances; with the samples at 0.0 the
                 * difference is 0.0, so the bias correction takes the middle branch. */
                (void)distance3(call, work + WORK_POS, work + WORK_TARGET);
                (void)distance3(call, work + WORK_POS, work + WORK_POS);
            }
        }
        /* aim A = the blocked difference, with the bias on z. */
        mhuc_put_f32(call, work + WORK_AIM_X, 0.0f);
        mhuc_put_f32(call, work + WORK_AIM_Y, 0.0f);
        mhuc_put_f32(call, work + WORK_AIM_Z, bias);
        if (query(call, enemy, 1u, 90.0f, 0.0f)) {
            advance(call, enemy, work);
            const float limit = mhuc_f32(call, work + WORK_VERTICAL_LIMIT);
            if (limit < mhuc_f32(call, work + WORK_POS_Y)) {
                mhuc_put_f32(call, work + WORK_POS_Y, limit);
            }
            if (mhuc_f32(call, work + WORK_POS_Y) < limit + LIMIT_OVER) {
                mhuc_put_f32(call, work + WORK_POS_Y, limit + LIMIT_OVER);
            }
        } else {
            turn_line(call, enemy, work,
                      mhuc_f32(call, work + WORK_VERTICAL_LIMIT) + LIMIT_OVER, 1.0f);
        }
        if (!query(call, enemy, 1u, 80.0f, 0.0f)) {
            mhuc_call(call, FN_TURN, enemy, 0x38eu, 0u, 0u);
        }
        if (flag(call, enemy)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_7_68_END, MOTION_SPEED_0);
        }
        return;
    }
    if (state == 2) {
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            if (!query(call, enemy, 1u, 30.0f, 0.0f)) {
                return;
            }
            mhuc_write8(call, work + WORK_SUB, 1u);
        } else if (sub != 1) {
            return;
        }
        /* 0x839598's signed byte waits on #55; the nonzero path ends the action in a request
         * rather than stalling, as category 3's part 2 does. */
        blocked_once(call, 0x00839598u, "the signed byte at 3U work+0xef");
        const uint32_t byte = mhuc_call(call, FN_GET_BYTE, enemy, 1u, 0u, 0u);
        if (byte != 0xffu) {
            mhuc_call(call, FN_SET_PAIR, enemy, 1u, 2u, byte);
            mhuc_call(call, FN_NEXT_ACTION, enemy, 8u, 0u, 0u);
        } else {
            mhuc_call(call, FN_NEXT_ACTION, enemy, 1u, 3u, 0u);
        }
    }
}

/* ── 3U 0x00698c48: 7/71 ───────────────────────────────────────────────────────────── */

/*   0: state 1, mode 0, the part step, motion 0xdb at 4.0;
 *   1: the turn at 0x222, the (0, 40.0) gate: state 2;
 *   2: the (0, 108.0) gate: state 3 and the effect setup 0x11c7 (blocked);
 *   3: the flag, then 0/2's base handler. */
static void run_7_71(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_58, MOTION_SPEED);
        return;
    }
    if (state == 1) {
        mhuc_call(call, FN_TURN, enemy, TURN_7_71, 0u, 0u);
        if (query(call, enemy, 0u, 40.0f, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
        }
        return;
    }
    if (state == 2) {
        if (query(call, enemy, 0u, 108.0f, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE, 3u);
            blocked_effect_setup(call); /* the setup 0x11c7 */
        }
        return;
    }
    if (state == 3 && flag(call, enemy)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── 3U 0x00698db8: 7/74, 7/90 and 7/91 ───────────────────────────────────────────── */

/* The part value the kind picks, applied before the state machine. */
static void run_7_74(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    mhuc_call(call, FN_SET_FLAG, enemy, 0x20u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_66, MOTION_SPEED);
        return;
    case 1:
        if (query(call, enemy, 0u, 116.0f, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
            blocked_effect_setup(call); /* the setup 0xaab */
        }
        return;
    case 2:
        if (query(call, enemy, 0u, 168.0f, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE, 3u);
            blocked_effect_setup(call); /* the setup 0x11c7 */
        }
        return;
    case 3:
        if (!query(call, enemy, 0u, 186.0f, 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 4u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        if (variant == 1) {
            motion(call, enemy, MOTION_7_74, MOTION_SPEED);
        } else if (variant == 2) {
            motion(call, enemy, MOTION_7_74_2, MOTION_SPEED);
        } else {
            motion(call, enemy, MOTION_7_74_3, MOTION_SPEED);
        }
        return;
    case 4:
        mhuc_call(call, FN_TURN, enemy, TURN_7_74, 0u, 0u);
        blocked_once(call, 0x00842a7cu, "the attack resolution");
        if (!flag(call, enemy)) {
            return;
        }
        if (variant == 0) {
            mhuc_write8(call, work + WORK_STATE, 5u);
            /* 0xcd with the source's r2 = 0 (speed 0.0); its r3 = 0x64 is the wrapper's
             * other blend input, which MH4U's has no place for. */
            motion(call, enemy, MOTION_7_74_A, MOTION_SPEED_0);
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 6u);
        if (variant == 1) {
            mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, FALL_7_74, 0.0f, NULL);
            motion(call, enemy, MOTION_7_74_B, MOTION_SPEED_0);
        } else {
            mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, FALL_7_74, 0.0f, NULL);
            motion(call, enemy, MOTION_7_74_C, MOTION_SPEED_0);
        }
        mhuc_call(call, FN_GROUP, enemy, 0u, 0x26u, 0u);
        clear_aim(call, enemy);
        {
            const uint32_t line = mhuc_object(call, enemy, 0x8d88u);
            if (line) {
                write16(call, line + 0x6au, read16(call, work + 0x51cu));
            }
        }
        return;
    case 5: {
        if (!flag(call, enemy)) {
            return;
        }
        if (variant == 1 || variant == 2) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 6u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        data_float_and_fall(call, enemy);
        motion(call, enemy, MOTION_7_74_D, MOTION_SPEED_6);
        mhuc_call(call, FN_GROUP, enemy, 0u, 7u, 0u);
        clear_aim(call, enemy);
        /* 0x83c6cc's float is #55-blocked; taken as 0.0, so both aims are 0.0. */
        blocked_once(call, 0x0083c6ccu, "the float from the source's block");
        mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
        mhuc_put_f32(call, work + WORK_AIM_B_Z, 0.0f);
        return;
    }
    case 6: {
        if (variant == 1 || variant == 2) {
            if (query(call, enemy, 1u, 64.0f, 0.0f)) {
                blocked_once(call, 0x00842a7cu, "the attack resolution");
                mhuc_call(call, FN_TURN, enemy, TURN_7_74_A, 0u, 0u);
            }
            if (query(call, enemy, 3u, 120.0f, 184.0f)) {
                /* 0x00c4ef98 has no MH4U table: the aim y is taken as 0.0. */
                blocked_once(call, 0x0083c6e0u, "the table interpolation on MH3U data");
                mhuc_put_f32(call, work + WORK_AIM_Y, 0.0f);
                const float data = data_float(call, enemy);
                turn_hold(call, enemy, work, data, 1.0f);
                if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                    mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
                }
            }
            if (!query(call, enemy, 0u, 184.0f, 0.0f)) {
                return;
            }
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_7_74_E, MOTION_SPEED_0);
            mhuc_call(call, FN_GROUP, enemy, 0u, 0x16u, 0u);
            mhuc_call(call, FN_FLIGHT, enemy, 0u, 0u, 0u);
            return;
        }
        {
            float curve = 0.0f;
            mhuc_call_f(call, FN_CURVE, enemy, CURVE_7_74, 0u, 0u, 0.0f, 0.0f, &curve);
            mhuc_put_f32(call, work + WORK_AIM_Y, curve);
        }
        const float data = data_float(call, enemy);
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            turn_hold(call, enemy, work, data, 1.0f);
            if (query(call, enemy, 1u, 16.0f, 0.0f)) {
                mhuc_write8(call, work + WORK_SUB,
                            (uint32_t)(mhuc_read8(call, work + WORK_SUB) + 1u));
                mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
            } else if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                mhuc_write8(call, work + WORK_SUB,
                            (uint32_t)(mhuc_read8(call, work + WORK_SUB) + 1u));
                mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
            }
        } else if (sub == 1) {
            turn_line(call, enemy, work, data, 1.0f);
        }
        if (!mhuc_call_f(call, FN_CHECK, enemy, 0u, 0u, 0u, data, 0.0f, NULL)) {
            return;
        }
        if (flag(call, enemy)) {
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_7_74_E, MOTION_SPEED_0);
            mhuc_call(call, FN_GROUP, enemy, 0u, 0x16u, 0u);
            mhuc_call(call, FN_FLIGHT, enemy, 0u, 0u, 0u);
        }
        return;
    }
    case 7:
        mhuc_call(call, FN_FLIGHT, enemy, 0u, 0u, 0u);
        if (flag(call, enemy)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
        return;
    default:
        return;
    }
}

/* ── 3U 0x00829c88: 7/75 and 7/94 (base-class code, 0002's second amendment) ───────── */

/*   0: state 1, the data float and its fall, motion 0x3d at 6.0, the rate at target z + 500.0;
 *   1: the flight byte, sub 0: the two-joint turn at 0x100/0x100, the 30.0 gate, aim A z 5.0,
 *      aim B z 3.0 and the turn point at -850.0; sub 1: the data float, the turn and the
 *      0x80 point turn, aim A z clamped at 70.0; then the flag, state 2, motion 0x3e at 6.0;
 *   2: the flight byte, the turn at 0x200, the 0x80 point turn: a miss ends with the data
 *      float and the 70.0 clamp, a hit sets state 3, motion 0x2d, aim A y -10.0, aim B z -3.2;
 *   3: the turn at 0x600, sub 0: the 30.0 gate, aim B z -6.8; sub 1: the data float and the
 *      0.0 floor; then the flag and state 4;
 *   4: the request for 7/0x60 (r1 = 1, 7/94) or 7/0x54 (r1 = 0, 7/75). */
static void run_7_75(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data_float(call, enemy), 0.0f,
                    NULL);
        motion(call, enemy, MOTION_7_75, MOTION_SPEED_6);
        const float r = rate(call, enemy);
        mhuc_put_f32(call, work + WORK_TARGET_Z,
                     mhuc_f32(call, work + WORK_TARGET_Z) + r * RATE_500);
        mhuc_write8(call, work + WORK_SUB, 0u);
        return;
    }
    if (state == 1) {
        mark_flying(call, work);
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            mhuc_call(call, FN_TURN2, enemy, 0x100u, 0x100u, 0u);
            if (query(call, enemy, 1u, 30.0f, 0.0f)) {
                mhuc_write8(call, work + WORK_SUB, 1u);
                clear_aim(call, enemy);
                mhuc_put_f32(call, work + WORK_AIM_Z, AIM_Y_7_75);
                mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_7_75);
                mhuc_call_f(call, FN_SETUP_POINT, enemy, 0x10u, 0u, 0u, SETUP_HEIGHT, 0.0f,
                            NULL);
            }
        } else if (sub == 1) {
            const float data = data_float(call, enemy);
            turn_hold(call, enemy, work, data, 1.0f);
            mhuc_call(call, FN_POINT_TURN, enemy, 0u, 0x80u, 0u);
            if (mhuc_f32(call, work + WORK_AIM_Z) > AIM_CLAMP_7_75) {
                mhuc_put_f32(call, work + WORK_AIM_Z, AIM_CLAMP_7_75);
            }
        }
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        motion(call, enemy, MOTION_7_75_1, MOTION_SPEED_6);
        return;
    }
    if (state == 2) {
        mark_flying(call, work);
        mhuc_call(call, FN_TURN, enemy, TURN_7_75, 0u, 0u);
        if (!mhuc_call(call, FN_POINT_TURN, enemy, 0u, 0x80u, 0u)) {
            const float data = data_float(call, enemy);
            turn_hold(call, enemy, work, data, 1.0f);
            if (mhuc_f32(call, work + WORK_AIM_Z) > AIM_CLAMP_7_75) {
                mhuc_put_f32(call, work + WORK_AIM_Z, AIM_CLAMP_7_75);
            }
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        motion(call, enemy, MOTION_7_75_2, MOTION_SPEED_6);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_put_f32(call, work + WORK_AIM_Y, AIM_Y_7_74);
        mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_7_75_3);
        const float data = data_float(call, enemy);
        turn_hold(call, enemy, work, data, 1.0f);
        return;
    }
    if (state == 3) {
        mhuc_call(call, FN_TURN, enemy, TURN_7_75_3, 0u, 0u);
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            const float data = data_float(call, enemy);
            turn_hold(call, enemy, work, data, 1.0f);
            if (query(call, enemy, 1u, 30.0f, 0.0f)) {
                mhuc_write8(call, work + WORK_SUB, 1u);
                mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_7_75_4);
            }
        } else if (sub == 1) {
            const float data = data_float(call, enemy);
            turn_hold(call, enemy, work, data, 1.0f);
            if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
            }
        }
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE,
                    (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        return;
    }
    if (state == 4) {
        mhuc_call(call, FN_NEXT_ACTION, enemy, 7u, (variant != 0) ? 0x60u : 0x54u, 0u);
    }
}

/* ── 3U 0x006993fc: 7/76 and 7/95 ──────────────────────────────────────────────────── */

/*   0: state 1, mode 3, the part step, motion 0xd1 at 6.0, the timer cleared;
 *   1: sub 0: the turn at 0x200, the 50.0 gate, the aim cleared, aim B z 3.0, the turn point
 *      at 0.0 and the (0, 0xe, 3) part group; sub 1: the blocked 0x83c6cc, the vertical step
 *      with its -200.0 clamp, the aim advance, aim A z clamped at 110.0, then the flag,
 *      state 2, motion 0xd0 at 6.0;
 *   2: the speed -200.0, the aim advance, the 110.0 clamp, the zero point turn, then state 3,
 *      the blocked 0x842a7c and 0x82d278 and the stall flag;
 *   3: the blocked 0x82d430, the flag, state 4, the part step and the request for 7/0x60
 *      (r1 = 1) or 7/0x54 (r1 = 0). */
static void run_7_76(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    mhuc_call(call, FN_SET_FLAG, enemy, 0x20u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_76, MOTION_SPEED_6);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        return;
    }
    if (state == 1) {
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_76, 0u, 0u);
            if (!query(call, enemy, 1u, 50.0f, 0.0f)) {
                return;
            }
            mhuc_write8(call, work + WORK_SUB, 1u);
            clear_aim(call, enemy);
            mhuc_put_f32(call, work + WORK_AIM_B_Z, AIM_B_Z_7_75);
            mhuc_call_f(call, FN_SETUP_POINT, enemy, 0x10u, 0u, 0u, 0.0f, 0.0f, NULL);
            mhuc_call(call, FN_GROUP4, enemy, 0u, 0xeu, 3u);
            return;
        }
        if (sub != 1) {
            return;
        }
        /* 0x83c6cc's float is #55-blocked, taken as 0.0. */
        blocked_once(call, 0x0083c6ccu, "the float from the source's block");
        mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, 0.0f, 0.0f, NULL);
        if (mhuc_read32(call, work + WORK_SPEED) > CHECK_CLAMP_BITS) {
            mhuc_put_f32(call, work + WORK_SPEED, -200.0f);
        }
        advance_b(call, enemy, work, 1.0f);
        if (mhuc_f32(call, work + WORK_AIM_Z) > CHECK_CLAMP) {
            mhuc_put_f32(call, work + WORK_AIM_Z, CHECK_CLAMP);
        }
        if (flag(call, enemy)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
            motion(call, enemy, MOTION_7_76_2, MOTION_SPEED_6);
        }
        return;
    }
    if (state == 2) {
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, -200.0f, 0.0f, NULL);
        advance_b(call, enemy, work, 1.0f);
        if (mhuc_f32(call, work + WORK_AIM_Z) > CHECK_CLAMP) {
            mhuc_put_f32(call, work + WORK_AIM_Z, CHECK_CLAMP);
        }
        if (!mhuc_call(call, FN_POINT_TURN, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        blocked_once(call, 0x00842a7cu, "the attack resolution");
        mhuc_write8(call, work + WORK_SUB, 0u);
        blocked_once(call, 0x0082d278u, "the action-data call on MH3U data");
        mhuc_call(call, FN_STALL, enemy, 0u, 0u, 0u);
        return;
    }
    if (state == 3) {
        blocked_once(call, 0x0082d430u, "the action-data call on MH3U data");
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE,
                    (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        part_step(call, enemy, work);
        mhuc_call(call, FN_NEXT_ACTION, enemy, 7u, (variant != 0) ? 0x60u : 0x54u, 0u);
    }
}

/* ── 3U 0x00697888 through 0x00686bb8: 7/81 ────────────────────────────────────────── */

/* The inline case block passes r1 = 1, r2 = 0, r3 = 2 and 0 on the stack, so the handler is
 * specialised to those values: the part group 0x2b, no point copy (r1 is not 0/3/5), and the
 * r1 = 1 path through states 1 and 2.
 *   0: state 1, sub 0, the data float and its fall, the part step, motion 0xdb at 6.0, the
 *      shell (0, 0x2b), the aim cleared, the timer (int16)(20.0 / this+0x29c);
 *   1: the flight byte, the blocked 0x842a7c, the (2, 80.0) gate with its 0x300 turn, the
 *      (3, 60.0, 100.0) gate and its trajectory (the source's rate, the distance and the
 *      30.0 floor), the timer countdown, then the (1, 150.0) gate: state 2 and the timer
 *      (int16)((200.0 - this+0x290) / the blocked 0x83c6cc);
 *   2: the flag, mode 3, motion 0x1b at 6.0 and state 3;
 *   3: the vertical step, the -75.0 clamp, the flag, then 0/6's base handler. */
static void run_7_81(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_SET_FLAG, enemy, 0x20u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        data_float_and_fall(call, enemy);
        part_step(call, enemy, work);
        motion(call, enemy, MOTION_7_81, MOTION_SPEED_6);
        mhuc_call(call, FN_GROUP, enemy, 0u, 0x2bu, 0u);
        clear_aim(call, enemy);
        mhuc_put_f32(call, work + WORK_TIMER,
                     source_ratio(WAIT_7_81, mhuc_f32(call, enemy + 0x29cu)));
        return;
    }
    if (state == 1) {
        mhuc_call(call, FN_FLIGHT, enemy, 0u, 0u, 0u);
        blocked_once(call, 0x00842a7cu, "the attack resolution");
        if (query(call, enemy, 2u, RANGE_7_81_A, 0.0f)) {
            mhuc_call(call, FN_TURN, enemy, TURN_7_81, 0u, 0u);
        }
        if (query(call, enemy, 3u, RANGE_7_81_B, RANGE_7_81_C)) {
            if (mhuc_f32(call, work + WORK_TIMER) > WAIT_7_81) {
                mhuc_put_f32(call, work + WORK_AIM_X, WAIT_7_81);
                const float data = data_float(call, enemy);
                const float r = rate(call, enemy);
                const float delta_aim = data - DIST_BIAS_7_81;
                float aim = mhuc_f32(call, work + WORK_TARGET_Z) -
                            mhuc_f32(call, work + WORK_POS_Y);
                aim = (aim + delta_aim * r) / mhuc_f32(call, work + WORK_TIMER);
                if (aim > WAIT_7_81) {
                    aim = WAIT_7_81;
                }
                mhuc_put_f32(call, work + WORK_AIM_Y, aim);
                const uint32_t turn =
                    angle_to(call, work + WORK_POS, work + WORK_TARGET) -
                    (uint32_t)mhuc_read32(call, work + WORK_HEADING) + 0x4000u;
                if ((turn & 0xffffu) < 0x8000u) {
                    float dist = distance2(call, work + WORK_TARGET, work + WORK_POS);
                    dist -= rate(call, enemy) * DIST_BIAS_7_81;
                    float aim_z = dist / mhuc_f32(call, work + WORK_TIMER);
                    if (!(aim_z > AIM_MIN_7_81)) {
                        aim_z = AIM_MIN_7_81;
                    }
                    mhuc_put_f32(call, work + WORK_AIM_Z, aim_z);
                } else {
                    mhuc_put_f32(call, work + WORK_AIM_Z, AIM_MIN_7_81);
                }
                const float data2 = data_float(call, enemy);
                turn_line(call, enemy, work, data2, 1.0f);
            }
            mhuc_put_f32(call, work + WORK_TIMER,
                         mhuc_f32(call, work + WORK_TIMER) -
                             mhuc_f32(call, enemy + 0x14u));
        }
        if (query(call, enemy, 1u, RANGE_7_81_D, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
            /* 0x83c6cc's float is #55-blocked, taken as 0.0, so the timer is 0.0. */
            blocked_once(call, 0x0083c6ccu, "the float from the source's block");
            mhuc_put_f32(call, work + WORK_TIMER,
                         source_ratio(SPEED_7_81 - mhuc_f32(call, enemy + 0x290u), 0.0f));
        }
        return;
    }
    if (state == 2) {
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        motion(call, enemy, MOTION_7_81_2, MOTION_SPEED_6);
        mhuc_write8(call, work + WORK_STATE, 3u);
        return;
    }
    if (state == 3) {
        step_vertical(call, enemy, work);
        if (flag(call, enemy)) {
            mhuc_3u_base_0_6(call, enemy, work);
        }
    }
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────── */

/* Runs category 7's part-4 handler for the pair, or returns 0 so the module's dispatch can
 * try the next family. */
static int dispatch_cat7d(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    if (category != 7) {
        return 0;
    }
    switch (index) {
    case 45: run_7_45(call, enemy, work); return 1;
    case 58: run_7_58(call, enemy, work); return 1;
    case 66: run_7_66(call, enemy, work); return 1;
    case 67: run_7_67(call, enemy, work); return 1;
    case 69: run_7_67(call, enemy, work); return 1;
    case 70: run_7_67(call, enemy, work); return 1;
    case 68: run_7_68(call, enemy, work); return 1;
    case 71: run_7_71(call, enemy, work); return 1;
    case 74: run_7_74(call, enemy, work, 0); return 1;
    case 90: run_7_74(call, enemy, work, 1); return 1;
    case 91: run_7_74(call, enemy, work, 2); return 1;
    case 75: run_7_75(call, enemy, work, 0); return 1;
    case 94: run_7_75(call, enemy, work, 1); return 1;
    case 76: run_7_76(call, enemy, work, 0); return 1;
    case 95: run_7_76(call, enemy, work, 1); return 1;
    case 81: run_7_81(call, enemy, work); return 1;
    default: return 0;
    }
}

/* What this family carries: the sixteen ids, the nine units and the inline block, the two
 * base handlers reused from cat0.c, the MH4U tables that stand for the source's curves, and
 * the calls #55 still blocks. */
static void self_test_cat7d(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 16 of the 191 actions: 7/45 <- 0x00697e78 (mode 3, motion 0x38, the "
             "two MH4U curves and the vertical clamp); 7/58 <- 0x00697ff0 (motion 0xdb, the "
             "4.0 and 108.0 gates); 7/66 <- 0x00698144 (motion 0xdd, the three range pairs); "
             "7/67, 7/69 and 7/70 <- 0x00698408 (motion 0xde, the curve samples, the 90.0 "
             "advance, the 80.0 turn, motion 0xdc); 7/68 <- 0x006986b8 (motion 0xdf, the "
             "bias, the 8/0 or 1/3 request); 7/71 <- 0x00698c48 (motion 0xdb, the 40.0 and "
             "108.0 gates); 7/74, 7/90 and 7/91 <- 0x00698db8 (motion 0xdd, the 116.0/168.0/"
             "186.0 gates, 0xcd/0xe2/0xe4/0xcf by the id); 7/75 and 7/94 <- the base-class "
             "0x00829c88 (motions 0x3d, 0x2d and 0x3e, the 30.0/70.0/110.0 aims); 7/76 and "
             "7/95 <- 0x006993fc (motions 0xd1 and 0xd0, the -200.0 speed); 7/81 <- the "
             "inline 0x00686bb8 into 0x00697888 (motion 0xdb and 0x1b, the 20.0 timer)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine calls are MH4U's: mode 0x%08x, motion 0x%08x, flag 0x%08x, "
              "data 0x%08x, fall 0x%08x, turn 0x%08x, point turn 0x%08x, check 0x%08x, next "
              "action 0x%08x, curve 0x%08x",
              (unsigned)FN_MODE, (unsigned)FN_MOTION, (unsigned)FN_FLAG,
              (unsigned)FN_DATA_FLOAT, (unsigned)FN_APPLY_FALL, (unsigned)FN_TURN,
              (unsigned)FN_POINT_TURN, (unsigned)FN_CHECK, (unsigned)FN_NEXT_ACTION,
              (unsigned)FN_CURVE);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: +0x5/6/7 -> +0x144/145/146, +0xdc -> +0x1c8, +0x38 "
             "-> +0x198, +0x3c -> +0x19c, +0x68 -> +0x180, +0x80 -> +0x1a8, +0x84 -> +0x1ac, "
             "+0x260/264/268 -> +0x160/164/168, +0x278 -> +0x178, +0x288/28c -> +0x218/220, "
             "+0x28 -> +0x1d4, +0x7c9 -> +0x3c4, +0x3 -> +0x1c0, +0x1e70 -> *(this+0x8d88)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: #55 blocks 0x00842a7c, 0x0083c6cc, 0x00839598, the effect setup "
             "0x00688a20/0x00688870 and the MH3U table interpolations; the 7/45 curves are "
             "MH4U's own 0x00fd18f0/0x00fd1918 and 7/74's is 0x00fd1a28 (identical data)");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat7d = {
    "cat7d", 16, dispatch_cat7d, self_test_cat7d,
};
