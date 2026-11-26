/*
 * cat13b.c: 3U Rathian's category 13, part 2 — 13/5 and 13/6.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending.
 *
 * The source is MH3U USA's uEm002. Its category-13 entry 0x00699b78 switches on the index
 * (0 to 9) and tail-calls each unit; 13/5 reaches 0x0068f818 and 13/6 reaches 0x0068fcc0.
 * The units ignore the case blocks' registers, so the family claims the two ids by the pair.
 * These are two of the three ids R1 found starting a different animation from MH4U's version
 * (13/5, 13/6 and 13/8; checks.md, "Monster actions"). MH4U's own handler for 13/5 is
 * 0x006dbec0 and for 13/6 0x006dbffc; the port runs the source's handler instead (decision
 * 0002's 2026-11-26 amendment) and starts her converted motions.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). This slice reads only
 * the handler's state byte (+0x5 -> +0x144); it adds no field-map row.
 *
 * 13/5 is one state-0 setup and one state-1 effect choreography: motion 0x13 at 6.0, then
 * twelve 0x0083336c queries, each with the source's frame values, and nine conditional
 * effect spawns (0x0016052c or 0x0016669c, guarded by 0x00847798 for four of them). None of
 * the effect calls is carried: MH4U lacks the uEffect039 class, its type-9 factory takes a
 * different argument, and decision 0015 leaves the source's effects to #259. They are named
 * once in the log and skipped.
 *
 * 13/6 is an eleven-state sequence: motion 0x1a at 0.0, then the aim helpers and the
 * trajectory tables of 3U's uEm024, the per-state motions 0x3d, 0xc8 (start frame 30), 0x13,
 * 0x12, 0x29, 0x43 and 0x1a, and four 0x0083336c queries. The state progression is gated by
 * 0x005c6938, which compares a point of the game's global object (the point 0x005c34c0
 * copies) with 0x1d6, 0x2da, 0x3a2, 0x41a, 0x578 and 0x6a4 halved. That point and the aim
 * helpers have no MH4U counterpart (reference/README.md, "The 28 with no MH4U counterpart"),
 * so the port names them and takes the gate's result as 0: the move plays its first motion
 * and stops at the first gate until #55 traces the helpers. The fake-host test drives each
 * state by writing the state byte, so the state bodies the gate would reach are still
 * checked for their calls and frame values.
 *
 * Blocked calls, each named once in the log (all #55):
 *   0x0016052c  the uEffect039 spawn 13/5 makes six times (MH4U has no such class)
 *   0x0016669c  the type-9 effect factory 13/5 calls twice (its argument differs from MH4U's)
 *   0x00847798  the effect gate 13/5 calls four times; the port takes its result as 0
 *   0x005bf66c 13/6's +0xd61 byte set
 *   0x005bf77c 13/6's aim point store and copy
 *   0x005bf7bc 13/6's three-float conversion into +0xde0/+0xde4/+0xde8
 *   0x005c0614 13/6's aim block clear and point copy
 *   0x005c34c0 13/6's copy of the global point
 *   0x005c3f88 13/6's uEm024 aim build from the source's tables 0x00c4d890/0x00c4da20
 *   0x005c6938 13/6's progress gate over the global point
 *   0x005c7270 13/6's uEm024 trajectory setup from the source's table 0x00c4dbe0
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offset, and the 3U offset it stands for. */
#define WORK_STATE 0x0144u /* 3U +0x5: the handler's state byte */

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_MODE        0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION      0x0094e318u /* [0x00828828] start a motion (r1; s0 speed, s1 start) */
#define FN_DATA_FLOAT  0x0093d870u /* [0x00852324] the action data's float, returned in s0 */
#define FN_APPLY_FALL  0x0092e99cu /* [0x00844124] advance the fall by s0, then set mode 1 */
#define FN_PER_MODE    0x0091aae4u /* [0x0083336c] the per-mode distance query */
#define FN_TAIL0       0x00914dc4u /* [0x00844a38] the per-slot tail step, r3 = 0 */

/* The motions the handlers start, as MH4U's `file << 8 | slot` for her converted lists.
 * MH3U writes `file * 100 + slot`, so 0x13/0x1a/0x3d/0x12/0x29/0x43 are file 0's slots and
 * 0xc8 is file 2, slot 0. */
#define MOTION_13_5   MHUC_MOTION(0, 0x13)
#define MOTION_13_6_0 MHUC_MOTION(0, 0x1a)
#define MOTION_13_6_2 MHUC_MOTION(0, 0x3d)
#define MOTION_13_6_4 MHUC_MOTION(2, 0x00) /* 3U 0xc8 */
#define MOTION_13_6_5 MHUC_MOTION(0, 0x13)
#define MOTION_13_6_6 MHUC_MOTION(0, 0x12)
#define MOTION_13_6_7 MHUC_MOTION(0, 0x29)
#define MOTION_13_6_8 MHUC_MOTION(0, 0x43)
#define MOTION_13_6_9 MHUC_MOTION(0, 0x1a)

/* 13/5's frame values: the motion's speed, the twelve query values in source order and the
 * effects' scales. A scale is passed in s0; the point is {0.0, -30.0, 70.0} for 0x0016052c
 * and {0.0, 0.0, 50.0} for 0x0016669c. */
#define SPEED_13_5       6.0f
#define QUERY_13_5_A    92.0f
#define QUERY_13_5_B   262.0f
#define QUERY_13_5_C    96.0f
#define QUERY_13_5_D   136.0f
#define QUERY_13_5_D2  152.0f
#define QUERY_13_5_E   156.0f
#define QUERY_13_5_F   190.0f
#define QUERY_13_5_G   386.0f
#define QUERY_13_5_H   344.0f
#define QUERY_13_5_H2  368.0f
#define QUERY_13_5_I   398.0f
#define QUERY_13_5_I2  426.0f
#define QUERY_13_5_J   434.0f
#define QUERY_13_5_K   458.0f
#define QUERY_13_5_K2  478.0f
#define SCALE_13_5_A     1.0f
#define SCALE_13_5_B     1.4f
#define SCALE_13_5_C     0.6f
#define SCALE_13_5_D     0.8f
#define SCALE_13_5_E     0.9f
#define EFFECT_13_5_33  0x33u
#define EFFECT_13_5_34  0x34u
#define EFFECT_13_5_TYPE9 3u
#define EFFECT_13_5_2F  0x2fu

/* 13/6's frame values: the motions' speeds, the start frame state 4 passes, the four query
 * values, the tail step's argument and the gate's thresholds. */
#define SPEED_13_6      0.0f
#define SPEED_13_6_FAST 6.0f
#define START_13_6_4   30.0f /* the source's r3 = 0x1e, its motion manager's start frame */
#define QUERY_13_6_3   90.0f
#define QUERY_13_6_5   56.0f
#define QUERY_13_6_8  114.0f
#define QUERY_13_6_9   48.0f
#define TAIL_13_6_5    0x17u
#define GATE_13_6_1   0x1d6u
#define GATE_13_6_2   0x2dau
#define GATE_13_6_4   0x3a2u
#define GATE_13_6_5   0x41au
#define GATE_13_6_6   0x578u
#define GATE_13_6_7   0x6a4u

/* ── the blocked calls, named and logged once each ───────────────────────────────────── */

static uint32_t blocked_seen;

static void log_blocked_once(unsigned bit, const char *line) {
    if (blocked_seen & (1u << bit)) {
        return;
    }
    blocked_seen |= 1u << bit;
    mhuc_log(MH4U_LOG_INFO, line);
}

/* 13/5's uEffect039 spawn, 3U 0x0016052c(global, this, type, 3, point, scale). */
static void effect_13_5_16052c(MH4UCall *call) {
    (void)call;
    log_blocked_once(0,
                     "13/5's 0x0016052c (#55) is the uEffect039 spawn (MH4U has no uEffect039 "
                     "class): the seven 0x33/0x34 spawns at {0.0, -30.0, 70.0} are named and "
                     "skipped, and decision 0015 leaves the source's effects to #259");
}

/* 13/5's type-9 effect factory, 3U 0x0016669c(global, this, 3, 0x2f, {0.0, 0.0, 50.0},
 * s0 = 1.4). */
static void effect_13_5_16669c(MH4UCall *call) {
    (void)call;
    log_blocked_once(1,
                     "13/5's 0x0016669c (#55) is the type-9 effect factory at {0.0, 0.0, "
                     "50.0} and s0 = 1.4; MH4U's factory takes the type where the source "
                     "passes the monster, so both calls are named and skipped");
}

/* 13/5's 3U 0x00847798(this, 3, 0), the effect gate before four spawns. */
static int gate_13_5_847798(MH4UCall *call) {
    (void)call;
    log_blocked_once(2,
                     "13/5's 0x00847798 (#55) gates four effect spawns and needs an MH4U "
                     "trace; the port takes its result as 0, so those spawns are not reached");
    return 0;
}

/* 13/6's progress gate, 3U 0x005c6938(global, threshold): it compares the global point's x
 * with the threshold halved. */
static int gate_13_6(MH4UCall *call) {
    (void)call;
    log_blocked_once(3,
                     "13/6's 0x005c6938 (#55) compares the global point's x with 0x1d6/0x2da/"
                     "0x3a2/0x41a/0x578/0x6a4 halved; it has no MH4U counterpart, so the "
                     "port takes its result as 0 and the move stops at the first gate until "
                     "#55 traces it");
    return 0;
}

/* The other seven uEnemy/uEm024 helpers 13/6 calls: each is one of the 28 without an MH4U
 * counterpart, and each takes its source arguments (recorded at the call sites below). */
static void blocked_5bf66c(MH4UCall *call) {
    (void)call;
    log_blocked_once(4,
                     "13/6's 0x005bf66c (#55) sets the +0xd61 byte; MH4U's own 13/6 handler "
                     "calls none of these aim helpers (reference, the 28), so it is skipped");
}

static void blocked_5bf77c(MH4UCall *call) {
    (void)call;
    log_blocked_once(5,
                     "13/6's 0x005bf77c (#55) stores the 3-float aim point at "
                     "(this+0xc00)+0x198 and copies the +0xd60 point; it is skipped");
}

static void blocked_5bf7bc(MH4UCall *call) {
    (void)call;
    log_blocked_once(6,
                     "13/6's 0x005bf7bc (#55) turns three floats into +0xde0/+0xde4/+0xde8 "
                     "through 0x005c4080; it is skipped");
}

static void blocked_5c0614(MH4UCall *call) {
    (void)call;
    log_blocked_once(7,
                     "13/6's 0x005c0614 (#55) clears +0xd61 and copies a 2-float point and a "
                     "scale into the +0xd60 block; it is skipped");
}

static void blocked_5c34c0(MH4UCall *call) {
    (void)call;
    log_blocked_once(8,
                     "13/6's 0x005c34c0 (#55) copies the point at the global object's +0x18 "
                     "through 0x00886ef8; the point is not available, so the port skips it");
}

static void blocked_5c3f88(MH4UCall *call) {
    (void)call;
    log_blocked_once(9,
                     "13/6's 0x005c3f88 (#55) is uEm024's aim build from the source's tables "
                     "0x00c4d890 and 0x00c4da20, which the port does not carry; it is skipped");
}

static void blocked_5c7270(MH4UCall *call) {
    (void)call;
    log_blocked_once(10,
                     "13/6's 0x005c7270 (#55) is uEm024's trajectory setup from the source's "
                     "table 0x00c4dbe0, which the port does not carry; it is skipped");
}

/* ── the shared helpers ─────────────────────────────────────────────────────────────── */

/* 3U's 0x00828828(this, motion, r2 speed, r3 start frame). MH4U's 0x0094e318 takes the speed
 * in s0 and a second float in s1; MH4U's own 13/6 passes its motion's start frame there at the
 * same call, so the source's r3 goes to s1 (0.0 wherever the source leaves it 0). */
static void motion(MH4UCall *call, uint32_t enemy, uint32_t number, float speed, float start) {
    mhuc_call_f(call, FN_MOTION, enemy, number, 0u, 0u, speed, start, NULL);
}

/* 3U's 0x00852324: the action data's float, returned in s0. */
static float data_float(MH4UCall *call, uint32_t enemy) {
    float value = 0.0f;
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &value);
    return value;
}

/* 3U's 0x0083336c(this, r1, s0, s1): the per-mode distance query. */
static int per_mode(MH4UCall *call, uint32_t enemy, uint32_t r1, float s0, float s1) {
    return (int)mhuc_call_f(call, FN_PER_MODE, enemy, r1, 0u, 0u, s0, s1, NULL);
}

/* ── the translated handlers ────────────────────────────────────────────────────────── */

/* 3U 0x0068f818, 13/5.
 *   0: state 1, mode 0, motion 0x13 at 6.0;
 *   1: the twelve 0x0083336c queries and the nine effect spawns they gate, in source order.
 *      The 0x33 spawns are at {0.0, -30.0, 70.0} with s0 1.0/0.6/0.9; the 0x34 ones follow
 *      0x00847798 and are at the same point with s0 1.0/0.8; the 0x0016669c spawns are at
 *      {0.0, 0.0, 50.0} with s0 1.4. None is carried (#55). */
static void run_13_5(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_13_5, SPEED_13_5, 0.0f);
        return;
    }
    if (state != 1) {
        return;
    }
    if (per_mode(call, enemy, 0u, QUERY_13_5_A, 0.0f) ||
        per_mode(call, enemy, 0u, QUERY_13_5_B, 0.0f)) {
        effect_13_5_16052c(call); /* 0x33, s0 1.0 */
    }
    if (per_mode(call, enemy, 0u, QUERY_13_5_C, 0.0f)) {
        effect_13_5_16669c(call);
    }
    if (per_mode(call, enemy, 3u, QUERY_13_5_D, QUERY_13_5_D2) &&
        gate_13_5_847798(call)) {
        effect_13_5_16052c(call); /* 0x34, s0 1.0 */
    }
    if (per_mode(call, enemy, 0u, QUERY_13_5_E, 0.0f) ||
        per_mode(call, enemy, 0u, QUERY_13_5_F, 0.0f) ||
        per_mode(call, enemy, 0u, QUERY_13_5_G, 0.0f)) {
        effect_13_5_16052c(call); /* 0x33, s0 0.6 */
    }
    if (per_mode(call, enemy, 0u, QUERY_13_5_B, 0.0f)) {
        effect_13_5_16669c(call);
    }
    if (per_mode(call, enemy, 3u, QUERY_13_5_H, QUERY_13_5_H2) &&
        gate_13_5_847798(call)) {
        effect_13_5_16052c(call); /* 0x34, s0 1.0 */
    }
    if (per_mode(call, enemy, 3u, QUERY_13_5_I, QUERY_13_5_I2) &&
        gate_13_5_847798(call)) {
        effect_13_5_16052c(call); /* 0x34, s0 0.8 */
    }
    if (per_mode(call, enemy, 0u, QUERY_13_5_J, 0.0f)) {
        effect_13_5_16052c(call); /* 0x33, s0 0.9 */
    }
    if (per_mode(call, enemy, 3u, QUERY_13_5_K, QUERY_13_5_K2) &&
        gate_13_5_847798(call)) {
        effect_13_5_16052c(call); /* 0x34, s0 0.8 */
    }
}

/* 3U 0x0068fcc0, 13/6.
 *   0: state 1, the data float and the fall, motion 0x1a at 0.0, then 0x005c0614;
 *   1: gate 0x1d6, then 0x005bf77c(-6961, 5735, 1112), 0x005bf7bc(0, 100, 0), 0x005bf66c;
 *   2: gate 0x2da, motion 0x3d at 0.0, 0x005c34c0, 0x005c3f88(0x00c4d890), 0x005bf7bc(0, 100, 0);
 *   3: 0x005c34c0, 0x005c3f88(0x00c4d890), the 90.0 query, then state 4 and 0x005c0614;
 *   4: 0x005c34c0, 0x005c3f88(0x00c4d890), gate 0x3a2, motion 0xc8 at 0.0 with start frame 30,
 *      0x005bf66c, 0x005c34c0, 0x005c3f88(0x00c4da20), 0x005bf7bc(0, 178, 0);
 *   5: the 56.0 query and the (0, 0x17) tail, 0x005c34c0, 0x005c3f88(0x00c4da20), gate 0x41a,
 *      motion 0x13 at 0.0, 0x005bf77c(-5845, 0, -504), 0x005bf7bc(0, 90, 0);
 *   6: gate 0x578, motion 0x12 at 0.0, 0x005bf77c(-5845, 0, -504), 0x005bf7bc(0, 90, 0);
 *   7: gate 0x6a4, motion 0x29 at 0.0, 0x005bf77c(-5845, 0, -504);
 *   8: the 114.0 query, then state 9 and motion 0x43 at 6.0;
 *   9: 0x005c34c0, the +1.0 point and 0x005c7270(0x00c4dbe0), the 48.0 query, state 10 and
 *      motion 0x1a at 6.0;
 *  10: 0x005c34c0, the +1.0 point and 0x005c7270(0x00c4dbe0). */
static void run_13_6(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        const float data = data_float(call, enemy);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        motion(call, enemy, MOTION_13_6_0, SPEED_13_6, 0.0f);
        blocked_5c0614(call); /* (global, this, 0) */
        return;
    case 1:
        if (!gate_13_6(call)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        blocked_5bf77c(call); /* s0 -6961.0, s1 5735.0, s2 1112.0 */
        blocked_5bf7bc(call); /* s0 0.0, s1 100.0, s2 0.0 */
        blocked_5bf66c(call);
        return;
    case 2:
        if (!gate_13_6(call)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        motion(call, enemy, MOTION_13_6_2, SPEED_13_6, 0.0f);
        blocked_5c34c0(call);
        blocked_5c3f88(call); /* the point, table 0x00c4d890 */
        blocked_5bf7bc(call); /* s0 0.0, s1 100.0, s2 0.0 */
        return;
    case 3:
        blocked_5c34c0(call);
        blocked_5c3f88(call); /* the point, table 0x00c4d890 */
        if (per_mode(call, enemy, 0u, QUERY_13_6_3, 0.0f)) {
            mhuc_write8(call, work + WORK_STATE, 4u);
            blocked_5c0614(call); /* (global, this, 0) */
        }
        return;
    case 4:
        blocked_5c34c0(call);
        blocked_5c3f88(call); /* the point, table 0x00c4d890 */
        if (!gate_13_6(call)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 5u);
        motion(call, enemy, MOTION_13_6_4, SPEED_13_6, START_13_6_4);
        blocked_5bf66c(call);
        blocked_5c34c0(call);
        blocked_5c3f88(call); /* the second point, table 0x00c4da20 */
        blocked_5bf7bc(call); /* s0 0.0, s1 178.0, s2 0.0 */
        return;
    case 5:
        if (per_mode(call, enemy, 0u, QUERY_13_6_5, 0.0f)) {
            mhuc_call(call, FN_TAIL0, enemy, 0u, TAIL_13_6_5, 0u);
        }
        blocked_5c34c0(call);
        blocked_5c3f88(call); /* the point, table 0x00c4da20 */
        if (!gate_13_6(call)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 6u);
        motion(call, enemy, MOTION_13_6_5, SPEED_13_6, 0.0f);
        blocked_5bf77c(call); /* s0 -5845.0, s1 0.0, s2 -504.0 */
        blocked_5bf7bc(call); /* s0 0.0, s1 90.0, s2 0.0 */
        return;
    case 6:
        if (!gate_13_6(call)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 7u);
        motion(call, enemy, MOTION_13_6_6, SPEED_13_6, 0.0f);
        blocked_5bf77c(call); /* s0 -5845.0, s1 0.0, s2 -504.0 */
        blocked_5bf7bc(call); /* s0 0.0, s1 90.0, s2 0.0 */
        return;
    case 7:
        if (!gate_13_6(call)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 8u);
        motion(call, enemy, MOTION_13_6_7, SPEED_13_6, 0.0f);
        blocked_5bf77c(call); /* s0 -5845.0, s1 0.0, s2 -504.0 */
        return;
    case 8:
        if (!per_mode(call, enemy, 0u, QUERY_13_6_8, 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 9u);
        motion(call, enemy, MOTION_13_6_8, SPEED_13_6_FAST, 0.0f);
        return;
    case 9:
        blocked_5c34c0(call);
        blocked_5c7270(call); /* the point, table 0x00c4dbe0, the +1.0 step */
        if (!per_mode(call, enemy, 0u, QUERY_13_6_9, 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 10u);
        motion(call, enemy, MOTION_13_6_9, SPEED_13_6_FAST, 0.0f);
        return;
    case 10:
        blocked_5c34c0(call);
        blocked_5c7270(call); /* the point, table 0x00c4dbe0, the +1.0 step */
        return;
    default:
        return;
    }
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────── */

static int dispatch_cat13b(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                           int index) {
    if (category != 13) {
        return 0;
    }
    switch (index) {
    case 5: run_13_5(call, enemy, work); return 1;
    case 6: run_13_6(call, enemy, work); return 1;
    default: return 0;
    }
}

/* What this family carries: the two ids, their units, the field-map anchor, the blocked
 * calls and the reason the gate stops 13/6. The module's self-test calls this with the
 * others'. */
static void self_test_cat13b(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 2 of the 191 actions: 13/5 <- 0x0068f818 (motion 0x13 at 6.0, the "
             "twelve 0x0083336c queries at 92/262/96/136-152/156/190/386/344-368/398-426/"
             "434/458-478, the nine effect spawns); 13/6 <- 0x0068fcc0 (motion 0x1a at 0.0, "
             "the eleven states and their motions 0x3d/0xc8 with start frame 30/0x13/0x12/"
             "0x29/0x43/0x1a, the 90/56/114/48 queries, the 0x5bf/0x5c aim helpers and the "
             "0x1d6/0x2da/0x3a2/0x41a/0x578/0x6a4 gates)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 13 part 2's field map: +0x5 -> +0x144 only; the slice adds "
             "no row (13/6's points and tables are the source's data, not carried)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 13 part 2's blocked calls: 13/5's 0x0016052c, 0x0016669c "
             "and 0x00847798 (#55, the effects); 13/6's 0x005bf66c, 0x005bf77c, 0x005bf7bc, "
             "0x005c0614, 0x005c34c0, 0x005c3f88, 0x005c6938 and 0x005c7270 (#55); the "
             "0x005c6938 gate's result is taken as 0, so 13/6 stops after its first motion "
             "until #55 traces it");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 0x0016052c and 0x00847798 are 13/5's, not 13/6's: 13/6 reaches the "
             "eight 0x5bf/0x5c helpers and 0x0083336c instead");
}

const MhucFamily mhuc_3u_family_cat13b = {
    "cat13b", 2, dispatch_cat13b, self_test_cat13b,
};
