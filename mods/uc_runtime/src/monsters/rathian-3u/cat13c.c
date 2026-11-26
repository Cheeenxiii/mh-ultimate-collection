/*
 * cat13c.c: 3U Rathian's category 13, part 3 — 13/7, 13/8 and 13/9.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending.
 *
 * The source is MH3U USA's uEm002. Category 13's entry 0x00699b78 switches on the index (0 to
 * 9) to the case blocks. 13/7 (0x00699bf8) and 13/9 (0x00699c8c) are inline blocks that start
 * their motion and then fall into the base-class handler 0x00858b6c, which cat0.c exports as
 * mhuc_3u_base_0_3 (decision 0002's second amendment: a base-class handler is port code too,
 * so it is reused, not replaced). 13/8's case block (0x00699c84) tail-calls its own unit
 * 0x0069031c, the largest in the class (0xa58 bytes in the function table; its last state runs
 * on past that to 0x00690e0c), and this file translates the seventeen states.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The fields this slice
 * reads are the merged map's (reference/README.md, "The 3U work block on MH4U's layout"):
 * +0x5 -> +0x144 (the handler's state byte) and +0x28/+0x2c -> +0x1d4 (the frame timer; MH4U
 * keeps one value and the source's saved +0x2c is not kept). The frame delta the source
 * reaches through the pointer at work+0x30 is this+0x14 in both games.
 *
 * Motion numbers are MH3U's `file * 100 + slot`, written as MH4U's `file << 8 | slot` for her
 * converted motion lists. 0x1a, 0x3d, 0x1f, 0x20, 0x1b and 0x1c are file 0; 0xdb, 0xce and
 * 0xcf are file 2's slots 0x13, 0x06 and 0x07.
 *
 * Blocked or not carried, logged once when first reached (reference/README.md, "The 28 with no
 * MH4U counterpart"):
 *   0x005bf66c, 0x005bf77c, 0x005bf7bc, 0x005c0614, 0x005c34c0, 0x005c3f88, 0x005c6938
 *       and 0x005c7270 (#55) — the aim-point and trajectory helpers. They build the source's
 *       points and the uEm024 trajectory and gate several states on a distance comparison.
 *       MH4U's own 13/8 handler (0x006dc274) calls none of them; it spawns a factory shell
 *       (0x00661bc4) instead, which the port does not put in their place. The source's points
 *       and trajectories are therefore not built, and each gate is taken as the source's
 *       nonzero path so the move cannot stall.
 *   0x00161798, 0x0016052c and 0x005aef18 (#55) — 13/8's state-16 effect calls: the forward
 *       and the uEffect039 spawns, gated by 0x005aef18's two-float check, which has no MH4U
 *       field pair. They are named and skipped.
 *   The motion start's fifth stack argument (13/8's states 3, 12 and 13 pass 1; 13/7 and 13/9
 *       pass 0): MH4U's motion start 0x0094e318 takes none. The source's r3 (its own start's
 *       first float) is dead in its callee, and is not carried either.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE  0x0144u /* 3U +0x5:  the handler's state byte */
#define WORK_TIMER  0x01d4u /* 3U +0x28: the frame timer (3U's saved +0x2c is not kept) */

/* The frame delta: this+0x14 in both games (3U reaches it through the pointer at work+0x30). */
#define ENEMY_DELTA 0x0014u

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_ONE_SHOT    0x00922ca0u /* [0x0083d18c] set the one-shot byte */
#define FN_DATA_FLOAT  0x0093d870u /* [0x00852324] the action data's float, returned in s0 */
#define FN_APPLY_FALL  0x0092e99cu /* [0x00844124] advance the fall by s0, then set mode 1 */
#define FN_MOTION      0x0094e318u /* [0x00828828] start a motion (index r1, speed s0) */
#define FN_PER_MODE    0x0091aae4u /* [0x0083336c] the per-mode distance check */
#define FN_FLAG        0x00b05da4u /* [0x0083cbf4] the action's finish flag */

/* The source's motion numbers, as MH4U's `file << 8 | slot` for her converted lists. */
#define MOTION_1A   MHUC_MOTION(0, 0x1a)
#define MOTION_3D   MHUC_MOTION(0, 0x3d)
#define MOTION_1F   MHUC_MOTION(0, 0x1f)
#define MOTION_20   MHUC_MOTION(0, 0x20)
#define MOTION_1B   MHUC_MOTION(0, 0x1b)
#define MOTION_1C   MHUC_MOTION(0, 0x1c)
#define MOTION_DB   MHUC_MOTION(2, 0x13) /* 3U 0xdb */
#define MOTION_CE   MHUC_MOTION(2, 0x06) /* 3U 0xce */
#define MOTION_CF   MHUC_MOTION(2, 0x07) /* 3U 0xcf */

/* The source's frame values. */
#define QUERY_13_8_A    78.0f
#define QUERY_13_8_B    74.0f
#define QUERY_13_8_C    86.0f
#define QUERY_13_8_C2  204.0f
#define SPEED_13_8_3D   30.0f /* state 3's r2 = 0x1e */
#define SPEED_13_8_3D_B 10.0f /* state 7's r2 = 0xa */
#define SPEED_13_8_CF   20.0f /* state 12's r2 = 0x14 */
#define SPEED_13_8_1B    7.0f /* state 13's r2 = 7 */

/* The source's distance gates, named after the value 3U's 0x005c6938 compares with. */
#define GATE_13_8_1 0x15au
#define GATE_13_8_4 0x280u
#define GATE_13_8_8 0x3eeu
#define GATE_13_8_9 0x434u
#define GATE_13_8_10 0x468u
#define GATE_13_8_12 0x506u

/* ── the blocked calls, named and logged once each ───────────────────────────────────── */

static uint32_t blocked_seen;

static void log_blocked_once(unsigned bit, const char *line) {
    if (blocked_seen & (1u << bit)) {
        return;
    }
    blocked_seen |= 1u << bit;
    mhuc_log(MH4U_LOG_INFO, line);
}

/* 3U's aim-point and trajectory helpers: 0x005c34c0 copies a point from a global, 0x005bf77c
 * stores a three-float point, 0x005bf7bc turns floats into values, 0x005bf66c sets a byte,
 * 0x005c0614 clears and copies, 0x005c3f88 builds a point from a speed and a table entry,
 * 0x005c6938 compares a point's coordinate and 0x005c7270 sets up a trajectory. */
static void log_aim(MH4UCall *call) {
    (void)call;
    log_blocked_once(0,
                     "13/7, 13/8 and 13/9's aim and trajectory helpers are #55-blocked: "
                     "0x005bf66c, 0x005bf77c, 0x005bf7bc, 0x005c0614, 0x005c34c0, "
                     "0x005c3f88, 0x005c6938 and 0x005c7270 have no MH4U counterpart (the 28 "
                     "with none), so the source's points and trajectories are not built and "
                     "0x005c6938's gates are taken as the source's nonzero path");
}

/* 13/8's state-16 effects: 0x00161798 (the forward), 0x0016052c (the uEffect039 spawn) and
 * 0x005aef18 (its two-float gate, which has no MH4U field pair). */
static void log_effects(MH4UCall *call) {
    (void)call;
    log_blocked_once(1,
                     "13/8's state-16 effects are #55-blocked: 0x00161798 (the object forward), "
                     "0x0016052c (a uEffect039 spawn; MH4U lacks the class) and 0x005aef18 "
                     "(their two-float gate, which has no MH4U field pair); the port skips them "
                     "and the state still advances");
}

/* The source's motion start takes a fifth stack argument (1 in 13/8's states 3, 12 and 13,
 * 0 through its 0x00828828 veneer), and its r3 is the first float of its own callee. */
static void log_motion_arg(MH4UCall *call) {
    (void)call;
    log_blocked_once(2,
                     "13/8's states 3, 12 and 13 pass the source's motion-start fifth stack "
                     "argument (1); MH4U's 0x0094e318 takes none, so it is not carried and the "
                     "state plays the motion without it");
}

/* ── the shared helpers ─────────────────────────────────────────────────────────────── */

/* 3U's 0x00828828(this, motion, speed): the source's r2 is the speed, which MH4U takes in
 * s0. Its fifth stack argument is not representable (log_motion_arg). */
static void motion(MH4UCall *call, uint32_t enemy, uint32_t number, float speed) {
    mhuc_call_f(call, FN_MOTION, enemy, number, 0u, 0u, speed, 0.0f, NULL);
}

/* 3U's 0x00852324: the action data's float, returned in s0. */
static float data_float(MH4UCall *call, uint32_t enemy) {
    float value = 0.0f;
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &value);
    return value;
}

/* 3U's 0x00844124: advance the fall by the data float; it also sets mode 1. */
static void apply_fall(MH4UCall *call, uint32_t enemy, float data) {
    mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
}

/* 3U's 0x0083336c(this, r1, s0, s1): the per-mode distance check, its r0 tested. */
static int per_mode(MH4UCall *call, uint32_t enemy, uint32_t r1, float s0, float s1) {
    return (int)mhuc_call_f(call, FN_PER_MODE, enemy, r1, 0u, 0u, s0, s1, NULL);
}

static int flag(MH4UCall *call, uint32_t enemy) {
    return (int)mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u);
}

/* ── the translated handlers ────────────────────────────────────────────────────────── */

/* 3U's 13/7 case block, 0x00699bf8. Its one-shot byte runs every frame before the state
 * switch.
 *   0: state 1, the data float and the fall it advances, motion 0x1a at 0.0, the blocked
 *      0x005bf77c/0x005bf7bc aim calls;
 *   1: the base-class handler 0x00858b6c (cat0.c's mhuc_3u_base_0_3).
 */
static void run_13_7(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        apply_fall(call, enemy, data_float(call, enemy));
        motion(call, enemy, MOTION_1A, 0.0f);
        log_aim(call);
        return;
    }
    if (state == 1) {
        mhuc_3u_base_0_3(call, enemy, work);
    }
}

/* 3U's 13/9 case block, 0x00699c8c. MH4U has no 13/9 action, so this is its own handler.
 *   0: state 1, the data float and the fall, motion 0x1a at 0.0, the blocked
 *      0x005bf77c/0x005bf7bc aim calls;
 *   1: the finish flag, then the base-class handler 0x00858b6c (cat0.c's
 *      mhuc_3u_base_0_3) once it is set.
 */
static void run_13_9(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        apply_fall(call, enemy, data_float(call, enemy));
        motion(call, enemy, MOTION_1A, 0.0f);
        log_aim(call);
        return;
    }
    if (state == 1) {
        if (flag(call, enemy)) {
            mhuc_3u_base_0_3(call, enemy, work);
        }
    }
}

/* 3U 0x0069031c, 13/8, seventeen states.
 *   0: state 1, the data float and the fall, motion 0x1a at 0.0, the blocked 0x005bf7bc and
 *      0x005c0614 aim calls;
 *   1: the blocked 0x005c6938 gate (taken as nonzero), state 2, motion 0x1a, 0x005bf77c,
 *      0x005c34c0, 0x005c7270 and 0x005bf66c;
 *   2: 0x005c34c0/0x005c7270, the flag, state 3, motion 0x1a;
 *   3: 0x005c34c0/0x005c7270, the 78.0 query, state 4, motion 0x3d at 30.0 (fifth argument);
 *   4: 0x005c34c0/0x005c7270, the 0x280 gate, state 5, motion 0x1f, 0x005c3f88;
 *   5, 6: 0x005c34c0/0x005c3f88, the flag, state++, motion 0x20 then 0x1f;
 *   7: 0x005c34c0/0x005c3f88, the 74.0 query, state 8, motion 0x3d at 10.0;
 *   8: 0x005c34c0/0x005c3f88, the 0x3ee gate, state 9, motion 0xdb, 0x005c3f88 and
 *      0x005bf7bc;
 *   9: 0x005c34c0/0x005c3f88, the 0x434 gate, state 10, motion 0x1b, 0x005c7270;
 *   10: 0x005c34c0/0x005c7270, the 0x468 gate, state 11, motion 0xce;
 *   11: 0x005c34c0/0x005c7270, the flag, state 12, motion 0xcf;
 *   12: 0x005c34c0/0x005c7270, the 0x506 gate, state 13, motion 0xcf at 20.0 (fifth argument),
 *       the blocked 0x005bf77c with its three floats and 0x005c7270;
 *   13: 0x005c34c0/0x005c7270, the flag, state 14, motion 0x1b at 7.0 (fifth argument);
 *   14: 0x005c34c0/0x005c7270, the flag, state 15, motion 0x1b at 0.0;
 *   15: 0x005c34c0/0x005c7270, the flag, state 16, motion 0x1c and the timer cleared;
 *   16: the 86.0/204.0 queries and the blocked effect calls, the timer advanced by the frame
 *      delta, then 0x005c34c0/0x005c7270.
 */
static void run_13_8(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        apply_fall(call, enemy, data_float(call, enemy));
        motion(call, enemy, MOTION_1A, 0.0f);
        log_aim(call);
        return;
    case 1:
        log_aim(call); /* the 0x005c6938 gate, taken as the source's nonzero path */
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1A, 0.0f);
        return;
    case 2:
        log_aim(call);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1A, 0.0f);
        return;
    case 3:
        log_aim(call);
        if (!per_mode(call, enemy, 0u, QUERY_13_8_A, 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_3D, SPEED_13_8_3D);
        log_motion_arg(call);
        return;
    case 4:
        log_aim(call); /* the 0x005c6938 gate, GATE_13_8_4 */
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1F, 0.0f);
        return;
    case 5:
    case 6:
        log_aim(call);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, state == 5 ? MOTION_20 : MOTION_1F, 0.0f);
        return;
    case 7:
        log_aim(call);
        if (!per_mode(call, enemy, 0u, QUERY_13_8_B, 0.0f)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_3D, SPEED_13_8_3D_B);
        return;
    case 8:
        log_aim(call); /* the 0x005c6938 gate, GATE_13_8_8 */
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_DB, 0.0f);
        return;
    case 9:
        log_aim(call); /* the 0x005c6938 gate, GATE_13_8_9 */
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1B, 0.0f);
        return;
    case 10:
        log_aim(call); /* the 0x005c6938 gate, GATE_13_8_10 */
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_CE, 0.0f);
        return;
    case 11:
        log_aim(call);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_CF, 0.0f);
        return;
    case 12:
        log_aim(call); /* the 0x005c6938 gate, GATE_13_8_12, then 0x005bf77c */
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_CF, SPEED_13_8_CF);
        log_motion_arg(call);
        return;
    case 13:
        log_aim(call);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1B, SPEED_13_8_1B);
        log_motion_arg(call);
        return;
    case 14:
        log_aim(call);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1B, 0.0f);
        return;
    case 15:
        log_aim(call);
        if (!flag(call, enemy)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint32_t)(state + 1));
        motion(call, enemy, MOTION_1C, 0.0f);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        return;
    case 16: {
        log_aim(call);
        log_effects(call);
        (void)per_mode(call, enemy, 0u, QUERY_13_8_C, 0.0f);
        (void)per_mode(call, enemy, 0u, QUERY_13_8_C, 0.0f);
        (void)per_mode(call, enemy, 3u, QUERY_13_8_C, QUERY_13_8_C2);
        /* The source's 0x005aef18 gate is #55-blocked; the port takes 0, so the second
         * uEffect039 spawn is skipped with the first. The saved +0x2c it reads is not kept:
         * MH4U's timer is one field, and the accumulation below is the source's +0x28 step. */
        const float old = mhuc_f32(call, work + WORK_TIMER);
        mhuc_put_f32(call, work + WORK_TIMER, old + mhuc_f32(call, enemy + ENEMY_DELTA));
        return;
    }
    default:
        return;
    }
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────── */

static int dispatch_cat13c(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                           int index) {
    if (category != 13) {
        return 0;
    }
    switch (index) {
    case 7: run_13_7(call, enemy, work); return 1;
    case 8: run_13_8(call, enemy, work); return 1;
    case 9: run_13_9(call, enemy, work); return 1;
    default: return 0;
    }
}

/* What this family carries: the three ids, their units, the field-map anchors, the blocked
 * calls and the one motion-start argument MH4U has no place for. The module's self-test calls
 * this with the others'. */
static void self_test_cat13c(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 3 of the 191 actions: 13/7 <- its block 0x00699bf8 (motion 0x1a at "
             "0.0, the blocked 0x005bf77c/0x005bf7bc aim calls) and the base handler "
             "0x00858b6c; 13/8 <- 0x0069031c (17 states, motions 0x1a/0x1f/0x20/0x1b/0x1c at "
             "0.0, 0x3d at 30.0 and 10.0, and 0x213/0x206/0x207, the 78.0 and 74.0 queries, "
             "the 86.0/204.0 queries and the timer); 13/9 <- its block 0x00699c8c (motion 0x1a "
             "at 0.0, then the base handler 0x00858b6c)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 13 part 3's field map: +0x5 -> +0x144 and +0x28/+0x2c -> "
             "+0x1d4 (MH4U keeps one timer value); the frame delta through 3U work+0x30 is "
             "this+0x14");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 13 part 3's blocked calls: 0x005bf66c, 0x005bf77c, "
             "0x005bf7bc, 0x005c0614, 0x005c34c0, 0x005c3f88, 0x005c6938 and 0x005c7270 "
             "(#55, the aim and trajectory helpers), and 0x00161798, 0x0016052c and 0x005aef18 "
             "(#55, 13/8's state-16 effects); 13/7 and 13/9 reuse cat0.c's "
             "mhuc_3u_base_0_3 for 0x00858b6c");
}

const MhucFamily mhuc_3u_family_cat13c = {
    "cat13c", 3, dispatch_cat13c, self_test_cat13c,
};
