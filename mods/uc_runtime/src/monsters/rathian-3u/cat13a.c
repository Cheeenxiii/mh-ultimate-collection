/*
 * cat13a.c: 3U Rathian's category 13, part 1 — 13/0, 13/1, 13/2, 13/3 and 13/4.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending.
 *
 * The source is MH3U USA's uEm002. Its category-13 entry 0x00699b78 switches on the index
 * (0 to 9) to the case blocks below; 13/0 to 13/4 tail-call the five units this file
 * translates (0x0068eabc, 0x0068eca4, 0x0068f0fc, 0x0068f424 and 0x0068f66c). The units
 * ignore the registers the case blocks carry, so the family claims the five ids by the pair.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The fields this slice
 * reads are the merged map's (reference/README.md, "The 3U work block on MH4U's layout"):
 * +0x5/+0x6 -> +0x144/+0x145 (state and sub-state), +0xdc -> +0x1c8 (mode), +0x28 -> +0x1d4
 * (the frame timer; MH4U keeps one value and the source's saved +0x2c is not kept), +0x3c ->
 * +0x19c (position y), +0x38/+0x40 -> +0x198/+0x1a0 (position x/z), +0x80/+0x84 ->
 * +0x1a8/+0x1ac (turn slot and heading), +0x260/+0x264/+0x268 -> +0x160/+0x164/+0x168 (aim
 * point A), +0x278 -> +0x178 (aim vector B z), +0x288/+0x28c/+0x290 ->
 * +0x218/+0x21c/+0x220 (target point), +0x68 -> +0x180 (speed), +0xdb -> +0x14c (the
 * per-monster selector), and +0x3 -> +0x1c0 (the id byte). 3U's target-line struct at
 * this+0x1e70 is MH4U's *(this+0x8d88), as the field map records. The frame delta the source
 * reaches through the pointer at work+0x30 is this+0x14 in both games.
 *
 * Still unconfirmed: 3U's work+0x1c, +0xda and +0xaea have no MH4U offset (reference's "What
 * is not mapped"). +0xda is the index 0x00a347bc maps through the uCharacter table, and
 * +0xaea is the second selector 13/0 reads; neither is read through an MH4U offset here.
 *
 * Blocked or not carried, logged when first reached (the issue names them):
 *   0x00a347bc (#55)  the uCharacter table lookup of work+0xda, which 13/0, 13/1 and 13/2
 *                     call before their state machine. Its result is not available, so the
 *                     port never takes the 0xc branch: 13/0's second lookup, the size/one-shot
 *                     pair 0x0083d18c/0x00843c20 and 13/1's special flag are skipped.
 *   0x00843c20 (#55)  the scale and byte the 0xc branch sets; never reached here.
 *   0x00839598 (#55)  13/2's and 13/3's signed work+0xef byte; the port takes the source's
 *                     nonzero path so the move cannot stall.
 *   0x00835f10 (#55)  13/2's and 13/3's uEm066 position helper, called twice with the entry
 *                     byte 0x1b, 700.0 and 350.0; its result is taken as 0, so the source's
 *                     failure request runs.
 *   0x0084512c/0x00829620  not called by these five units: 0x00829620 is 13/4's, and
 *                     0x0084512c belongs to 8/0's unit 0x006870f4. 13/4's 0x00829620 is
 *                     named below; 0x0084512c is recorded as not reached.
 *   0x0085162c (#55)  13/4's entry: the float it sets at the monster's +0x97c.
 *   0x00829620 (#55)  13/4's per-frame helper over the source's action table.
 *   0x0082d278/0x0082d430 13/3's action-start record 0x00b0b0e8 is the source's data, which
 *                     the port does not carry; its setup and leaf are skipped.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <math.h>
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE       0x0144u /* 3U +0x5:  the handler's state byte */
#define WORK_STATE2      0x0145u /* 3U +0x6:  its sub-state byte */
#define WORK_MODE        0x01c8u /* 3U +0xdc: the monster's mode byte */
#define WORK_TIMER       0x01d4u /* 3U +0x28: the frame timer (3U's saved +0x2c is not kept) */
#define WORK_TURN        0x01a8u /* 3U +0x80: the turn slot before the heading */
#define WORK_HEADING     0x01acu /* 3U +0x84: the heading */
#define WORK_AIM_X       0x0160u /* 3U +0x260: the aim point A's x */
#define WORK_AIM_Y       0x0164u /* 3U +0x264: the aim point A's y */
#define WORK_AIM_Z       0x0168u /* 3U +0x268: the aim point A's z */
#define WORK_AIM_BZ      0x0178u /* 3U +0x278: the aim vector B's z */
#define WORK_POS_X       0x0198u /* 3U +0x38: position x */
#define WORK_POS_Y       0x019cu /* 3U +0x3c: position y */
#define WORK_POS_Z       0x01a0u /* 3U +0x40: position z */
#define WORK_TARGET_X    0x0218u /* 3U +0x288: the target point's x */
#define WORK_TARGET_Y    0x021cu /* 3U +0x28c: the target point's y */
#define WORK_TARGET_Z    0x0220u /* 3U +0x290: the target point's z */
#define WORK_SPEED       0x0180u /* 3U +0x68: the speed accumulator */
#define WORK_SET         0x01dcu /* 3U +0xf2: "the action was set" */
#define WORK_ID          0x01c0u /* 3U +0x3:  the id byte */
#define WORK_SELECTOR    0x014cu /* 3U +0xdb: the per-monster selector */
#define WORK_FLYING      0x03c4u /* 3U +0x7c9: 0x008310f0's "flying" byte */

/* The frame delta, and the target-line struct 3U embeds at this+0x1e70. */
#define ENEMY_DELTA      0x0014u
#define ENEMY_TARGET_LINE 0x8d88u

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_MODE         0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion (index r1, speed s0) */
#define FN_DATA_FLOAT   0x0093d870u /* [0x00852324] the action data's float, returned in s0 */
#define FN_APPLY_FALL   0x0092e99cu /* [0x00844124] advance the fall by s0, then set mode 1 */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_REQUEST      0x0094ef64u /* [0x0082a06c] request the next action (r1, r2) */
#define FN_VERTICAL     0x00915d44u /* [0x00833b2c] advance the vertical value by s0 * delta */
#define FN_TURN_STEP    0x0091db4cu /* [0x008357b0] turn toward the target at r1 */
#define FN_AIM_RESET    0x0096e164u /* [0x00839968] clear the aim point and vector */
#define FN_PER_MODE     0x0091aae4u /* [0x0083336c] the per-mode distance check */
#define FN_TURN_ANGLE   0x0091aaf0u /* [0x008392d8] turn by an angle step */
#define FN_AIM_WRAPPER  0x0091b430u /* [0x00839ea0, 0x00839514] aim step and clamp */
#define FN_BLEND        0x0092dc50u /* [0x008437f4] the vertical blend filter */
#define FN_LAND         0x0092dcccu /* [0x008438e8] the landing step */
#define FN_TAIL0        0x00914dc4u /* [0x00844a38] the per-slot tail step, r3 = 0 */
#define FN_SPEED        0x00916108u /* [0x00833d88] set the speed */
#define FN_DISTANCE     0x00aacd50u /* [0x005858f4] distance in x/z between two points */
#define FN_CURVE        0x00922250u /* [0x0083c6e0] the value-curve evaluator */
#define FN_ANGLE        0x00568c64u /* [0x00585384] the angle of a vector, returned in r0 */
#define FN_STATE_PRED   0x0092e960u /* [0x00844100] the state predicate */
#define FN_ORDER        0x0091b7b0u /* [0x008345f8] the order/phase step */
#define FN_RATE_A       0x0093ce60u /* [0x00850a50] the rate the height test applies */
#define FN_RATE_B       0x0093cd70u /* [0x008509a0] the rate the state 0 sets */
#define FN_TARGET_LINE  0x00948548u /* [0x005bde78] 13/2's target-line step */
#define FN_AIM_POINT    0x00948674u /* [0x0068d070] aim at the target with a lead */
#define FN_MOVE_POS     0x00955440u /* [0x0082b268] advance the position by the aim vector */
#define FN_ONE_SHOT     0x00922ca0u /* [0x0083d18c] set the one-shot byte */
#define FN_ACTION_STEP  0x00916228u /* [0x0082fc8c] 13/1's state-2 entry step */

/* The two MH4U value curves 13/2's source reads at 0x00c4edb8 and 0x00c4ee00. Their keys
 * were compared with MH4U's own 13/2 curves 0x00fd19b0 and 0x00fd19f8 and are equal, so the
 * port calls MH4U's evaluator with MH4U's own tables and carries no 3U data. */
#define CURVE_13_2_A 0x00fd19b0u
#define CURVE_13_2_B 0x00fd19f8u

/* The source's motion numbers are `file * 100 + slot`; MH4U's are `file << 8 | slot`. */
#define MOTION_13_0  MHUC_MOTION(0, 0x1a)
#define MOTION_13_1A MHUC_MOTION(0, 0x3d)
#define MOTION_13_1B MHUC_MOTION(0, 0x3e)
#define MOTION_13_1C MHUC_MOTION(0, 0x2d)
#define MOTION_13_2A MHUC_MOTION(2, 0x00) /* 3U 0xc8 */
#define MOTION_13_2B MHUC_MOTION(2, 0x14) /* 3U 0xdc */
#define MOTION_13_3  MHUC_MOTION(2, 0x02) /* 3U 0xca */
#define MOTION_13_4  MHUC_MOTION(2, 0x03) /* 3U 0xcb */

/* The source's frame values. */
#define SPEED_13_0        10.0f
#define DELAY_13_0       300.0f
#define HEIGHT_HIGH_13_0 3500.0f
#define HEIGHT_LOW_13_0  2000.0f
#define STEP_13_0         10.0f
#define TURN_13_0        0x180u /* halved for 0x0091db4c (3U's helper halves its rate) */

#define SPEED_13_1         6.0f
#define AIM_13_1_A_Z     (-20.0f)
#define AIM_13_1_BZ        0.5f
#define AIM_13_1_B_Z      80.0f
#define AIM_13_1_B_Y     (-2.0f)
#define AIM_13_1_C_Y    (-15.0f)
#define AIM_13_1_C_BZ    (-6.2f)
#define AIM_13_1_C_Z_MAX 130.0f
#define AIM_13_1_D_BZ    (-6.8f)
#define QUERY_13_1        30.0f
#define BLEND_13_1     (-2500.0f)
#define BLEND_R1_13_1     0x12u
#define LAND_R2_13_1      0x80u /* halved for 0x0092dccc */
#define TURN_13_1_A       0x100u /* halved for 0x0091aaf0 */
#define TURN_13_1_B       0x40u  /* halved for 0x0091aaf0 */
#define ANGLE_BIAS_13_1   0x400u
#define ANGLE_MAX_13_1    0x3000u

#define SPEED_13_2        20.0f
#define SPEED_13_2_B       0.0f
#define LEAD_MAX_13_2      3.8f
#define LEAD_MIN_13_2      1.0f
#define LEAD_RANGE_13_2  450.0f
#define SPEED_FLOOR_13_2 (-50.0f)
#define QUERY_13_2        36.0f
#define QUERY_13_2_B      30.0f
#define TURN_13_2        0x100u /* halved for 0x0091db4c */
#define TARGET_R_13_2    700.0f
#define TARGET_S_13_2    350.0f

#define AIM_13_3_SPEED   300.0f
#define AIM_13_3_RANGE    38.0f
#define QUERY_13_3_A      12.0f
#define QUERY_13_3_A2     50.0f
#define MOVE_13_3          1.0f /* becomes 0.5 for 0x00955440 */
#define SPEED_13_3         4.0f
#define TARGET_R_13_3    700.0f
#define TARGET_S_13_3    350.0f

#define SPEED_13_4         4.0f
#define DELAY_13_4         4.0f
#define ORDER_13_4_A    1000u
#define ORDER_13_4_B     200u
#define HIT_ARG_13_4     100u

/* The source's request pairs, kept as the source asks for them. */
#define REQUEST_13_0 0x0du
#define REQUEST_13_1 0x0du
#define REQUEST_13_2 0x0du
#define REQUEST_13_3 0x0du
#define REQUEST_13_4 0x0du
#define REQUEST_1_3  0x01u
#define REQUEST_2_6  0x02u

/* ── the blocked calls, named and logged once each ───────────────────────────────────── */

static uint32_t blocked_seen;

static void log_blocked_once(unsigned bit, const char *line) {
    if (blocked_seen & (1u << bit)) {
        return;
    }
    blocked_seen |= 1u << bit;
    mhuc_log(MH4U_LOG_INFO, line);
}

/* 3U's 0x00a347bc, the uCharacter table lookup 13/0, 13/1 and 13/2 make before their state
 * machine. It reads work+0xda, which has no MH4U offset; the port takes the source's
 * non-0xc path, so the 0x00843c20 call behind it (scale +0x894, byte +0x923) is not made. */
static void log_gate(MH4UCall *call) {
    (void)call;
    log_blocked_once(0,
                     "13/0, 13/1 and 13/2's 0x00a347bc (#55) maps work+0xda through the "
                     "uCharacter table; work+0xda has no MH4U offset, so the port takes the "
                     "source's non-0xc path, does not call 0x00843c20 (#55), and 13/0's "
                     "second lookup and its work+0xaea (also unmapped) are skipped");
}

/* 3U's 0x00839598, the signed work+0xef byte 13/2 and 13/3 test before their target loop. */
static void log_signed_byte(MH4UCall *call) {
    (void)call;
    log_blocked_once(1,
                     "13/2's and 13/3's 0x00839598 (#55) returns the signed byte at 3U "
                     "work+0xef, which has no MH4U offset; the port takes the source's "
                     "nonzero path so the move cannot stall");
}

/* 3U's 0x00835f10, the uEm066 helper the two-entry target loop calls. */
static void log_target_helper(MH4UCall *call) {
    (void)call;
    log_blocked_once(2,
                     "13/2's and 13/3's 0x00835f10 (#55) is the uEm066 target/position "
                     "helper, called twice with 0x1b, 700.0 and 350.0; its result is not "
                     "available, so the port takes 0 and the source's failure request runs");
}

/* 3U's 0x0082d278 and 0x0082d430, 13/3's action-start record 0x00b0b0e8. */
static void log_record(MH4UCall *call) {
    (void)call;
    log_blocked_once(3,
                     "13/3's action-start record 0x00b0b0e8 is the source's data, not "
                     "carried: its setup 0x0082d278 and leaf 0x0082d430 are not called");
}

/* 3U's 0x0085162c and 0x00829620, 13/4's entry and per-frame helper. */
static void log_13_4(MH4UCall *call) {
    (void)call;
    log_blocked_once(4,
                     "13/4's 0x0085162c (#55, the float at the monster's +0x97c) and "
                     "0x00829620 (#55, the per-frame action-table helper) are not called");
}

/* 13/1's special flag is 0 without the blocked 0x00a347bc; the source's 0x0084512c is not
 * reached by these units at all. The self-test names the second fact; this line is the
 * first one's, logged with the gate. */

/* ── the shared helpers ─────────────────────────────────────────────────────────────── */

/* 3U's 0x00828828(this, motion, r2, r3=0): the source's r2 is the speed, which MH4U takes in
 * s0. */
static void motion(MH4UCall *call, uint32_t enemy, uint32_t number, float speed) {
    mhuc_call_f(call, FN_MOTION, enemy, number, 0u, 0u, speed, 0.0f, NULL);
}

/* 3U's 0x00852324: the action data's float, returned in s0. */
static float data_float(MH4UCall *call, uint32_t enemy) {
    float value = 0.0f;
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &value);
    return value;
}

static int flag(MH4UCall *call, uint32_t enemy) {
    return (int)mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u);
}

/* 3U's 0x0083336c(this, r1, s0, s1): the per-mode distance check. */
static int per_mode(MH4UCall *call, uint32_t enemy, uint32_t r1, float s0, float s1) {
    return (int)mhuc_call_f(call, FN_PER_MODE, enemy, r1, 0u, 0u, s0, s1, NULL);
}

/* 3U's 0x00839ea0 and 0x00839514: the aim step and the vertical clamp. Both wrappers take
 * the source's s0/s1; MH4U's 0x0091b430 takes one float, and the port passes the source's
 * s0 (the clamp factor, the value MH4U's own 13/1 passes), with the heading slot at r1. */
static uint32_t aim_step(MH4UCall *call, uint32_t enemy, uint32_t work, float data) {
    return mhuc_call_f(call, FN_AIM_WRAPPER, enemy, work + WORK_TURN, 0u, 0u, data, 1.0f,
                       NULL);
}

/* 3U's 0x0083336c's state predicate counterpart 0x0092e960, used by 13/4. */
static int state_predicate(MH4UCall *call, uint32_t enemy) {
    return (int)mhuc_call(call, FN_STATE_PRED, enemy, 0u, 0u, 0u);
}

/* 3U's 0x008345f8(this, r1): the order/phase step. */
static void order_step(MH4UCall *call, uint32_t enemy, uint32_t value) {
    mhuc_call(call, FN_ORDER, enemy, value, 0u, 0u);
}

/* 3U's 0x008568f4's counterpart: the distance in x/z between two points, in s0. */
static float distance_xz(MH4UCall *call, uint32_t a, uint32_t b) {
    float value = 0.0f;
    mhuc_call_f(call, FN_DISTANCE, a, b, 0u, 0u, 0.0f, 0.0f, &value);
    return value;
}

/* 3U's 0x0083c6e0(this, table): the value curve's evaluation at the monster's speed. */
static float curve(MH4UCall *call, uint32_t enemy, uint32_t table) {
    float value = 0.0f;
    mhuc_call_f(call, FN_CURVE, enemy, table, 0u, 0u, 0.0f, 0.0f, &value);
    return value;
}

/* 3U's 0x00585384(vector, &angle1, &angle2): the vector's two angles. MH4U's 0x00568c64 is
 * the same conversion on two floats, as MH4U's own 13/1 uses it, so the port calls it twice:
 * the heading from (dx, dz) and the pitch from (-dy, horizontal). */
static uint32_t vector_angle(MH4UCall *call, float a, float b) {
    return mhuc_call_f(call, FN_ANGLE, 0u, 0u, 0u, 0u, a, b, NULL);
}

/* 3U's 0x00845004's counterpart 0x0092e408: the target-line factor, clamped to [1.0, 3.8].
 * MH4U's function takes its third float in s2, which ABI 4 cannot set; the port reproduces
 * its two steps with the distance counterpart 0x00aacd50 (3U 0x005858f4) instead. */
static float target_line_factor(MH4UCall *call, uint32_t work) {
    const float units = distance_xz(call, work + WORK_POS_X, work + WORK_TARGET_X);
    float value = units / LEAD_RANGE_13_2;
    if (value > LEAD_MAX_13_2) {
        value = LEAD_MAX_13_2;
    } else if (value < LEAD_MIN_13_2) {
        value = LEAD_MIN_13_2;
    }
    return value;
}

/* 3U's 0x00839ea0/0x00839514's aim step in 13/1's state 1 and 13/2's state 1: the data
 * float, then the wrapper's return (the clamp flag). */
static uint32_t aim_with_data(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const float data = data_float(call, enemy);
    return aim_step(call, enemy, work, data);
}

/* 3U's 0x008310f0: it sets 3U's work+0x7c9, which MH4U has no function for; MH4U's own 3/8
 * handler stores the same byte at work+0x3c4 inline, so the port writes that. */
static void set_flying(MH4UCall *call, uint32_t work) {
    mhuc_write8(call, work + WORK_FLYING, 1u);
}

/* ── the translated handlers ────────────────────────────────────────────────────────── */

/* 3U 0x0068eabc, 13/0.
 *   0: state 1, the data float and the fall it advances, motion 0x1a at 10.0, the rate, the
 *      300.0 timer;
 *   1: the height above the target, the high/low height branches (the rate above 3500, the
 *      +10.0 step at or below 2000), the timer countdown and the 0x180 turn, then a request
 *      for 13/1.
 */
static void run_13_0(MH4UCall *call, uint32_t enemy, uint32_t work) {
    log_gate(call);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        const float data = data_float(call, enemy);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        motion(call, enemy, MOTION_13_0, SPEED_13_0);
        mhuc_call(call, FN_RATE_B, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_TIMER, DELAY_13_0);
        return;
    }
    if (state != 1) {
        return;
    }
    const float height = mhuc_f32(call, work + WORK_POS_Y) -
                         mhuc_f32(call, work + WORK_TARGET_Y);
    if (height >= HEIGHT_HIGH_13_0) {
        mhuc_call(call, FN_RATE_A, enemy, 0u, 0u, 0u);
    } else if (height <= HEIGHT_LOW_13_0) {
        mhuc_put_f32(call, work + WORK_POS_Y,
                     mhuc_f32(call, work + WORK_POS_Y) + STEP_13_0);
    }
    const float old = mhuc_f32(call, work + WORK_TIMER);
    const float delta = mhuc_f32(call, enemy + ENEMY_DELTA);
    const float timer = old - delta;
    mhuc_put_f32(call, work + WORK_TIMER, timer);
    if ((int32_t)timer <= 0) {
        mhuc_call(call, FN_REQUEST, enemy, REQUEST_13_0, 1u, 0u);
        return;
    }
    if (!mhuc_call(call, FN_TURN_STEP, enemy, TURN_13_0 / 2u, 0u, 0u)) {
        return;
    }
    if (height > HEIGHT_HIGH_13_0) {
        return;
    }
    if (height < HEIGHT_LOW_13_0) {
        return;
    }
    mhuc_call(call, FN_REQUEST, enemy, REQUEST_13_0, 1u, 0u);
}

/* 3U 0x0068eca4, 13/1.
 *   0: state 1, the data float and the fall, motion 0x3d at 6.0, the aim reset, aim A z
 *      -20.0 and aim B z 0.5;
 *   1: the aim step, the heading and pitch turns, then motion 0x3e at 6.0, the aim stores
 *      and the -2500.0 blend;
 *   2: the landing step and motion 0x2d at 6.0, or the 130.0 aim clamp;
 *   3: the 30.0 query and the 0x00839598/0x00835f10-free tail: the special flag is 0 (the
 *      blocked 0x00a347bc cannot set it), so the flag ends in 0/3's base handler or the
 *      request for 13/2.
 */
static void run_13_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    log_gate(call);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        const float data = data_float(call, enemy);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        motion(call, enemy, MOTION_13_1A, SPEED_13_1);
        mhuc_call(call, FN_AIM_RESET, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_AIM_Z, AIM_13_1_A_Z);
        mhuc_put_f32(call, work + WORK_AIM_BZ, AIM_13_1_BZ);
        return;
    }
    if (state == 1) {
        set_flying(call, work);
        (void)aim_with_data(call, enemy, work);
        const float dx = mhuc_f32(call, work + WORK_TARGET_X) -
                         mhuc_f32(call, work + WORK_POS_X);
        const float dy = mhuc_f32(call, work + WORK_TARGET_Y) -
                         mhuc_f32(call, work + WORK_POS_Y);
        const float dz = mhuc_f32(call, work + WORK_TARGET_Z) -
                         mhuc_f32(call, work + WORK_POS_Z);
        uint32_t heading = vector_angle(call, dx, dz);
        const uint32_t pitch = vector_angle(call, -dy, sqrtf(dx * dx + dz * dz));
        heading = (heading + ANGLE_BIAS_13_1) & 0xffffu;
        if (heading > ANGLE_MAX_13_1) {
            heading = ANGLE_MAX_13_1;
        }
        const uint32_t turned = mhuc_call(call, FN_TURN_ANGLE, enemy,
                                          heading & 0xffffu,
                                          mhuc_read32(call, work + WORK_TURN) & 0xffffu,
                                          TURN_13_1_A / 2u);
        mhuc_write32(call, work + WORK_TURN, turned);
        const uint32_t pitched = mhuc_call(call, FN_TURN_ANGLE, enemy,
                                           pitch & 0xffffu,
                                           mhuc_read32(call, work + WORK_HEADING) & 0xffffu,
                                           TURN_13_1_B / 2u);
        mhuc_write32(call, work + WORK_HEADING, pitched);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call(call, FN_ACTION_STEP, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_AIM_Z, AIM_13_1_B_Z);
        mhuc_put_f32(call, work + WORK_AIM_BZ, AIM_13_1_BZ);
        mhuc_put_f32(call, work + WORK_AIM_Y, AIM_13_1_B_Y);
        motion(call, enemy, MOTION_13_1B, SPEED_13_1);
        mhuc_call_f(call, FN_BLEND, enemy, BLEND_R1_13_1, 0u, 0u, BLEND_13_1, 0.0f, NULL);
        return;
    }
    if (state == 2) {
        set_flying(call, work);
        if (mhuc_call(call, FN_LAND, enemy, 0u, LAND_R2_13_1 / 2u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, 3u);
            mhuc_write8(call, work + WORK_STATE2, 0u);
            motion(call, enemy, MOTION_13_1C, SPEED_13_1);
            mhuc_put_f32(call, work + WORK_AIM_Y, AIM_13_1_C_Y);
            mhuc_put_f32(call, work + WORK_AIM_BZ, AIM_13_1_C_BZ);
            (void)aim_with_data(call, enemy, work);
            return;
        }
        (void)aim_with_data(call, enemy, work);
        if ((int32_t)mhuc_read32(call, work + WORK_AIM_Z) > (int32_t)0x43020000u) {
            mhuc_put_f32(call, work + WORK_AIM_Z, AIM_13_1_C_Z_MAX);
        }
        return;
    }
    if (state != 3) {
        return;
    }
    uint32_t clamped = 0;
    if (mhuc_read8(call, work + WORK_STATE2) == 1u) {
        clamped = aim_with_data(call, enemy, work);
        if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
            mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
        }
    } else {
        clamped = aim_with_data(call, enemy, work);
        if (per_mode(call, enemy, 1u, QUERY_13_1, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE2, 1u);
            mhuc_put_f32(call, work + WORK_AIM_BZ, AIM_13_1_D_BZ);
        }
    }
    if (!flag(call, enemy)) {
        return;
    }
    if (clamped == 0u) {
        mhuc_3u_base_0_3(call, enemy, work);
        return;
    }
    mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
    mhuc_call(call, FN_REQUEST, enemy, REQUEST_13_1, 2u, 0u);
}

/* 3U 0x0068f0fc, 13/2.
 *   0: state 1, mode 3, motion 0xc8 at 20.0, the (0, 0xb) tail, the aim reset, speed 0, the
 *      target-line factor and the target-line step;
 *   1: the two value curves, the vertical step and the speed floor, the aim step, the 36.0
 *      query and the 0x100 turn, then motion 0xdc at 0.0;
 *   2: the 30.0 query, the signed work+0xef byte, the two-entry target loop, and the
 *      request for 13/3 or 1/3.
 */
static void run_13_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    log_gate(call);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        motion(call, enemy, MOTION_13_2A, SPEED_13_2);
        mhuc_call(call, FN_TAIL0, enemy, 0u, 0x0bu, 0u);
        mhuc_call(call, FN_AIM_RESET, enemy, 0u, 0u, 0u);
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, SPEED_13_2_B, 0.0f, NULL);
        const float lead = target_line_factor(call, work);
        const uint32_t line = mhuc_object(call, enemy, ENEMY_TARGET_LINE);
        if (line) {
            mhuc_put_f32(call, line, lead);
        }
        mhuc_call(call, FN_TARGET_LINE, enemy, 0u, 0u, 0u);
        return;
    }
    if (state == 1) {
        const float first = curve(call, enemy, CURVE_13_2_A);
        mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, first * 0.5f, 0.0f, NULL);
        if (mhuc_f32(call, work + WORK_SPEED) < SPEED_FLOOR_13_2) {
            mhuc_put_f32(call, work + WORK_SPEED, SPEED_FLOOR_13_2);
        }
        const float second = curve(call, enemy, CURVE_13_2_B);
        const uint32_t line = mhuc_object(call, enemy, ENEMY_TARGET_LINE);
        const float factor = line ? mhuc_f32(call, line) : 0.0f;
        mhuc_put_f32(call, work + WORK_AIM_Z, second * factor);
        (void)aim_with_data(call, enemy, work);
        if (!per_mode(call, enemy, 1u, QUERY_13_2, 0.0f)) {
            mhuc_call(call, FN_TURN_STEP, enemy, TURN_13_2 / 2u, 0u, 0u);
        }
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_13_2B, 0.0f);
        return;
    }
    if (state != 2) {
        return;
    }
    if (mhuc_read8(call, work + WORK_STATE2) == 0u) {
        if (!per_mode(call, enemy, 1u, QUERY_13_2_B, 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE2, 1u);
    } else if (mhuc_read8(call, work + WORK_STATE2) != 1u) {
        return;
    }
    log_signed_byte(call);
    log_target_helper(call);
    /* The source calls 0x00835f10 for its two target entries here; the helper is #55 and
     * the port takes its result as 0, so the source's failure request runs. */
    mhuc_call(call, FN_REQUEST, enemy, REQUEST_1_3, 3u, 0u);
}

/* 3U 0x0068f424, 13/3.
 *   0: state 1, sub-state 0, mode 0, the source's action-start record (not carried), and
 *      the aim at the target at 300.0/38.0;
 *   1: the 12.0/50.0 query, the speed-derived aim range, the 0.5 move, the record's leaf
 *      (not carried), then motion 0xca at 4.0;
 *   2: the signed work+0xef byte, the two-entry target loop, and the request for 13/4 or
 *      2/6.
 */
static void run_13_3(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_STATE2, 0u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        log_record(call);
        mhuc_call_f(call, FN_AIM_POINT, enemy, work + WORK_AIM_X, work + WORK_TARGET_X,
                    0u, AIM_13_3_SPEED, AIM_13_3_RANGE, NULL);
        return;
    }
    if (state == 1) {
        if (per_mode(call, enemy, 3u, QUERY_13_3_A, QUERY_13_3_A2)) {
            float range = mhuc_f32(call, work + WORK_AIM_BZ) - QUERY_13_3_A;
            if (range < 0.0f) {
                range = 0.0f;
            } else if (range > AIM_13_3_RANGE) {
                range = AIM_13_3_RANGE;
            }
            mhuc_call_f(call, FN_AIM_POINT, enemy, work + WORK_AIM_X, work + WORK_TARGET_X,
                        0u, AIM_13_3_SPEED, AIM_13_3_RANGE - range, NULL);
            mhuc_call_f(call, FN_MOVE_POS, enemy, 0u, 0u, 0u, MOVE_13_3 / 2.0f, 0.0f, NULL);
            log_record(call);
        }
        if (flag(call, enemy)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
            motion(call, enemy, MOTION_13_3, SPEED_13_3);
        }
        return;
    }
    if (state != 2) {
        return;
    }
    log_signed_byte(call);
    log_target_helper(call);
    /* The source calls 0x00835f10 for its two target entries here; the helper is #55 and
     * the port takes its result as 0, so the source's failure request runs. */
    mhuc_call(call, FN_REQUEST, enemy, REQUEST_2_6, 6u, 0u);
}

/* 3U 0x0068f66c, 13/4.
 *   0: state 1, sub-state 0, mode 0, motion 0xcb at 4.0, the source's 0x00829620 (not
 *      carried) and the 4.0 timer;
 *   1: the flag, the timer crossing test, the 1000/200 order step and the request for 13/2.
 */
static void run_13_4(MH4UCall *call, uint32_t enemy, uint32_t work) {
    log_13_4(call);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_13_4, SPEED_13_4);
        mhuc_put_f32(call, work + WORK_TIMER, DELAY_13_4);
        return;
    }
    if (state != 1) {
        return;
    }
    if (!flag(call, enemy)) {
        return;
    }
    const float old = mhuc_f32(call, work + WORK_TIMER);
    const float delta = mhuc_f32(call, enemy + ENEMY_DELTA);
    const float timer = old - delta;
    mhuc_put_f32(call, work + WORK_TIMER, timer);
    const int crossed = (old < 0.0f && timer >= 0.0f) ||
                        (timer <= 0.0f && old > 0.0f) ||
                        (timer == 0.0f && old == 0.0f);
    if (crossed) {
        if (state_predicate(call, enemy)) {
            order_step(call, enemy, ORDER_13_4_A);
        } else {
            const int id = (int)mhuc_read8(call, work + WORK_ID);
            if (id == 1 || id == 2 || id == 0x3e || id == 0x3f || id == 0x40 ||
                id == 0x41) {
                order_step(call, enemy, ORDER_13_4_B);
            }
        }
    }
    mhuc_call(call, FN_REQUEST, enemy, REQUEST_13_4, 2u, 0u);
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────── */

static int dispatch_cat13a(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                           int index) {
    if (category != 13) {
        return 0;
    }
    switch (index) {
    case 0: run_13_0(call, enemy, work); return 1;
    case 1: run_13_1(call, enemy, work); return 1;
    case 2: run_13_2(call, enemy, work); return 1;
    case 3: run_13_3(call, enemy, work); return 1;
    case 4: run_13_4(call, enemy, work); return 1;
    default: return 0;
    }
}

/* What this family carries: the five ids, their units, the field-map anchors, the blocked
 * calls and the one call the issue lists that these units do not reach. The module's
 * self-test calls this with the others'. */
static void self_test_cat13a(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 5 of the 191 actions: 13/0 <- 0x0068eabc (motion 0x1a at 10.0, the "
             "300.0 timer, the 3500/2000 height branches, the 0x180 turn); 13/1 <- "
             "0x0068eca4 (the four states, motions 0x3d/0x3e/0x2d at 6.0, the heading and "
             "pitch turns, the -2500.0 blend); 13/2 <- 0x0068f0fc (mode 3, motion 0xc8 at "
             "20.0, the two value curves, the target loop, motion 0xdc); 13/3 <- "
             "0x0068f424 (the 300.0/38.0 aim, the 12.0/50.0 query, motion 0xca at 4.0, the "
             "target loop); 13/4 <- 0x0068f66c (motion 0xcb at 4.0, the 4.0 timer, the "
             "1000/200 order step)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 13's field map: +0x5/+0x6 -> +0x144/+0x145, +0xdc -> "
             "+0x1c8, +0x28 -> +0x1d4, +0x38/+0x3c/+0x40 -> +0x198/+0x19c/+0x1a0, "
             "+0x80/+0x84 -> +0x1a8/+0x1ac, +0x260..+0x290 -> +0x160..+0x220, +0x68 -> "
             "+0x180, +0xdb -> +0x14c, +0x3 -> +0x1c0, +0x7c9 -> +0x3c4; this+0x1e70 -> "
             "*(this+0x8d88)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 13's blocked calls: 0x00a347bc and 0x00843c20 (#55, the "
             "work+0xda gate), 0x00839598 and 0x00835f10 (#55, 13/2's and 13/3's target "
             "loop), 0x0085162c and 0x00829620 (#55, 13/4), and 13/3's record 0x00b0b0e8 "
             "(its setup 0x0082d278 and leaf 0x0082d430 are the source's data)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 0x0084512c is not reached by these five units (it is 8/0's unit "
             "0x006870f4); 0x00829620 is reached by 13/4 only");
}

const MhucFamily mhuc_3u_family_cat13a = {
    "cat13a", 5, dispatch_cat13a, self_test_cat13a,
};
