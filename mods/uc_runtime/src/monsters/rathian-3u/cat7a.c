/*
 * cat7a.c: 3U Rathian's category 7, part 1 — 7/0, 7/1, 7/2, 7/4, 7/5, 7/6, 7/7, 7/8, 7/10,
 * 7/11, 7/12, 7/15, 7/16, 7/19, 7/20, 7/32, 7/34, 7/42, 7/61, 7/77 and 7/85.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h). The seven
 * handler units it carries are issue #221's: 0x00693468 (7/0, 7/77), 0x00693be8 (7/1, 7/20,
 * 7/42), 0x00694180 (7/2, 7/10, 7/11, 7/15), 0x006944b8 (7/4, 7/12), 0x00694694 (7/5, 7/61),
 * 0x00694840 (7/6, 7/7, 7/16, 7/19, 7/32, 7/85) and 0x00694bf4 (7/8, 7/34).
 *
 * The class shares these units with Rathalos and the colour variants (MH3U ids 1, 2 and
 * 62 to 65; uEm002), and several branch on the monster id in the work block's +3 (MH4U's
 * +0x1c0). The ported monster is em001 (id 1); the branches only ids 62, 63 and 65 take are
 * the class's colour-variant attacks and are not carried — the source's own id-1 path runs
 * the rest of each unit. The action variant r1 the case block passes (0, 1, 2 …) is kept, and
 * it selects a motion, a speed, a timer value or a tail in five of the units.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The runtime's README
 * carries the field map and the engine-call map this file is written against, including the
 * two rows this slice adds: work+0xb81 -> work+0xca5 (MH4U's own 7/4 reads it there) and
 * work+0x2a8 -> work+0x238 (MH4U's own 7/6 clamps it there).
 *
 * Blocked or not carried, logged when first reached (the issue names them):
 *   0x0084161c (#55)  the effect's target check in 7/2's family and 7/8's family; the
 *                     effect spawn behind it is skipped.
 *   0x00688a20/0x00829950  the class's effect-structure builder and the spawn it feeds, in
 *                     the same two units; the structure is the source's data and its callee
 *                     has no MH4U counterpart, so the checks run and the spawn is skipped.
 *   0x00842a7c (#55)  only 0x00693468's id 0x3e/0x3f branches call it; the ported id's byte
 *                     is 1, so it is never reached and no call is made.
 *   0x00b0b1c0/0x00b0b1e8  the source's value curves 7/15 and 7/34 evaluate; the tables are
 *                     the source's data, which the port does not carry, so the timing value
 *                     is skipped.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28) and the offsets this family reads, with the 3U offset
 * each stands for (runtime README, "3U Rathian's module: category 7, part 1"). */
#define WORK_STATE       0x0144u /* 3U +0x5:  the handler's state byte */
#define WORK_STATE2      0x0145u /* 3U +0x6:  its sub-state byte */
#define WORK_MODE        0x01c8u /* 3U +0xdc: the monster's mode byte */
#define WORK_TIMER       0x01d4u /* 3U +0x28: the frame timer (3U's +0x2c is not kept) */
#define WORK_SPEED       0x0180u /* 3U +0x68: the speed accumulated from the frame delta */
#define WORK_TURN        0x01a8u /* 3U +0x80: the turn slot before the heading */
#define WORK_HEADING     0x01acu /* 3U +0x84: the heading */
#define WORK_AIM_Z       0x0168u /* 3U +0x268: the aim point A's z */
#define WORK_AIM_BZ      0x0178u /* 3U +0x278: the aim vector B's z */
#define WORK_2A8         0x0238u /* 3U +0x2a8: the value 7/16 clamps at 1000.0 */
#define WORK_B81         0x0ca5u /* 3U +0xb81: 7/4's and 7/12's second gate byte */

/* The monster's own fields (3U this+0x278/+0x27c are MH4U's +0x290/+0x294). */
#define ENEMY_DELTA      0x0014u /* the frame delta (seconds), in both games */
#define ENEMY_SPEED_A    0x0290u /* 3U this+0x278 */
#define ENEMY_SPEED_B    0x0294u /* 3U this+0x27c */

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_MODE         0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion (r1, s0) */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_VERTICAL     0x00915d44u /* [0x00833b2c] advance the vertical value by s0*delta */
#define FN_SPEED        0x00916108u /* [0x00833d88] set the speed */
#define FN_AIM_ADVANCE  0x00911090u /* [0x00834098] advance the aim point by the aim vector */
#define FN_TURN_STEP    0x0091db4cu /* [0x008357b0] turn toward a target point */
#define FN_PER_MODE     0x0091aae4u /* [0x0083336c] the per-mode speed/distance check */
#define FN_LAND         0x0092dcccu /* [0x008438e8] the landing/blend step */
#define FN_BLEND        0x0092dc50u /* [0x008437f4] the vertical blend filter */
#define FN_CLEAR_SLOT   0x0090f8fcu /* [0x0082c1c4] clear an action slot by index */
#define FN_TAIL         0x0093310cu /* [0x00844a40] the per-slot tail step */
#define FN_TAIL0        0x00914dc4u /* [0x00844a38] the same with r3 = 0 */
#define FN_ORDER        0x0091b7b0u /* [0x008345f8] the action's order/phase step */
#define FN_TURN         0x00917570u /* [0x00850860] turn by an angle step */
#define FN_AIM_RESET    0x0096e164u /* [0x00839968] clear the aim point and vector */
#define FN_APPLY_NEXT   0x0092b140u /* [0x0084134c] apply the next action pair */
#define FN_EFFECT       0x00c0760cu /* [0x0015f410, 0x00164f08] the effect factory */
#define FN_FLAG_RATE    0x00922c40u /* [0x0083cbfc] store a rate at work+0x400+0x10 */
#define FN_RESET_ONE    0x00922ca0u /* [0x0083d18c] set work+0x3e3 to 1 */

/* The source's motion numbers are `file * 100 + slot`; MH4U's are `file << 8 | slot`. */
#define MOTION_7_0    MHUC_MOTION(0, 0x2f)
#define MOTION_7_1    MHUC_MOTION(2, 0x09)
#define MOTION_7_1b   MHUC_MOTION(2, 0x08)
#define MOTION_7_1c   MHUC_MOTION(2, 0x0a)
#define MOTION_7_1d   MHUC_MOTION(2, 0x18) /* the 0xda V1 finish */
#define MOTION_7_1e   MHUC_MOTION(2, 0x15) /* the 0xdd variant-1 state-2 motion */
#define MOTION_7_1f   MHUC_MOTION(0, 0x35) /* the 0x35 variant-2 state-2 motion */
#define MOTION_7_1g   MHUC_MOTION(0, 0x3c) /* the 0x3c variant-2 state-3 motion */
#define MOTION_7_2    MHUC_MOTION(0, 0x33)
#define MOTION_7_4a   MHUC_MOTION(0, 0x32)
#define MOTION_7_4b   MHUC_MOTION(0, 0x31)
#define MOTION_7_5    MHUC_MOTION(2, 0x06)
#define MOTION_7_5b   MHUC_MOTION(2, 0x07)
#define MOTION_7_6    MHUC_MOTION(0, 0x08)
#define MOTION_7_6b   MHUC_MOTION(0, 0x09)
#define MOTION_7_6c   MHUC_MOTION(0, 0x40)
#define MOTION_7_6d   MHUC_MOTION(0, 0x30)
#define MOTION_7_8    MHUC_MOTION(2, 0x08)

/* The source's frame values (the constants in the handler units). */
#define VERTICAL_7_1       (-3.3333333f) /* the source's -6.6666665, halved (0x833b2c) */
#define SPEED_MIN_7_1      (-200.0f)
#define AIM_Z_MAX_7_1       110.0f
#define TIMER_MAX_7_1       20.0f
#define TIMER_MAX_7_1_V2    10.0f
#define TIMER_BASE_7_1_V2    5.0f
#define SPEED_PCT_7_1      (-150.0f)
#define RATE_7_1              0.05f
#define RATE_7_1_V2           0.2f
#define AIM_BZ_7_1            3.0f
#define AIM_BZ_7_1_END       (-3.0f)

#define CHECK_7_2          2.0f
#define CHECK_7_2B         12.0f
#define CHECK_7_2C         36.0f
#define CHECK_7_2D         78.0f
#define EFFECT_7_2_A        3u
#define EFFECT_7_2_B        1u

#define CHECK_7_4         120.0f /* the turn's speed range */
#define TURN_7_4          0x8000

#define CHECK_7_5         200.0f
#define TURN_7_5         (-150.0f)

#define TIMER_7_6_A        20.0f
#define TIMER_7_6_B        10.0f
#define BLEND_7_6_A     (-300.0f)
#define BLEND_7_6_B     (-900.0f)
#define BLEND_7_6_C    (-2000.0f)
#define BLEND_7_6_D     (-600.0f)
#define CLAMP_7_6        1000.0f
#define CHECK_7_6          36.0f
#define CHECK_7_6B        120.0f

#define CHECK_7_8_A         2.0f
#define CHECK_7_8_B        12.0f
#define CHECK_7_8_C        36.0f
#define CHECK_7_8_D        78.0f
#define CHECK_7_8_E       120.0f
#define CHECK_7_8_F       164.0f

/* ── the shared helpers ─────────────────────────────────────────────────────────────── */

/* The source's 0x008345f8(this, -14): uEm002's order/phase step for Rathian (id 1). The
 * wrapper picks -14 for id 1 and other values for Rathalos and the variants; only the
 * ported id's is carried. */
static void order_rathian(MH4UCall *call, uint32_t enemy) {
    mhuc_call(call, FN_ORDER, enemy, (uint32_t)(int32_t)-14, 0u, 0u);
}

/* 0x00828828(this, motion, r2, r3): the source's r2 is the speed in its motion helper's
 * units and r3 is 0 in every call this family makes. MH4U's motion start takes the speed in
 * s0, so it is passed as the source writes it (category 0's convention). */
static void motion(MH4UCall *call, uint32_t enemy, uint32_t number, float speed) {
    mhuc_call_f(call, FN_MOTION, enemy, number, 0u, 0u, speed, 0.0f, NULL);
}

/* 0x00844a40(this, r1, r2, r3), and 0x00844a38(this, r1, r2) = the same with r3 = 0. */
static void tail_step(MH4UCall *call, uint32_t enemy, uint32_t r1, uint32_t r2, uint32_t r3) {
    mhuc_call(call, FN_TAIL, enemy, r1, r2, r3);
}

static void tail_step0(MH4UCall *call, uint32_t enemy, uint32_t r1, uint32_t r2) {
    mhuc_call(call, FN_TAIL0, enemy, r1, r2, 0u);
}

/* 0x0083336c(this, r1, s0, s1): the per-mode distance check. */
static int per_mode(MH4UCall *call, uint32_t enemy, uint32_t r1, float s0, float s1) {
    return (int)mhuc_call_f(call, FN_PER_MODE, enemy, r1, 0u, 0u, s0, s1, NULL);
}

/* 0x008437f4(this, r1, s0): the vertical blend filter. */
static void blend(MH4UCall *call, uint32_t enemy, uint32_t r1, float value) {
    mhuc_call_f(call, FN_BLEND, enemy, r1, 0u, 0u, value, 0.0f, NULL);
}

/* 0x0015f410(global, this, type): the effect factory. MH4U's 0xc0760c takes (global, type,
 * this, r3), so the type moves from 3U's r2 to MH4U's r1. */
static void spawn_effect(MH4UCall *call, uint32_t enemy, uint32_t type) {
    mhuc_call(call, FN_EFFECT, 0u, type, enemy, 0u);
}

/* ── the blocked calls, named and logged once each ───────────────────────────────────── */

static uint32_t blocked_seen;

static void log_blocked_once(unsigned bit, const char *line) {
    if (blocked_seen & (1u << bit)) {
        return;
    }
    blocked_seen |= 1u << bit;
    mhuc_log(MH4U_LOG_INFO, line);
}

static void log_target_check(MH4UCall *call) {
    (void)call;
    log_blocked_once(0,
                     "7/2's and 7/8's effect target check 0x0084161c is #55: its call is "
                     "named and skipped, and the effect behind it is not spawned");
}

static void log_effect_builder(MH4UCall *call) {
    (void)call;
    log_blocked_once(1,
                     "the class's effect structure builder 0x00688a20 and its spawn 0x00829950 "
                     "are the source's data and have no MH4U counterpart: the structure is not "
                     "built and the spawn is skipped");
}

static void log_curve(MH4UCall *call, uint32_t table) {
    (void)call;
    log_blocked_once(2 + (table == 0x00b0b1e8u ? 1u : 0u),
                     "the source's value curve 0x00b0b1c0/0x00b0b1e8 is the source's data, "
                     "not carried: the timing value its evaluation supplies is skipped");
}

/* 0x00693468's id 0x3e/0x3f branches (the colour variants) are not carried. The ported
 * monster's id byte is 1, so they never run; the issue's 0x00842a7c (#55) is only reached
 * from them. */
static void log_variants_not_carried(MH4UCall *call) {
    (void)call;
    log_blocked_once(4,
                     "0x00693468's id 0x3e/0x3f branches and their 0x00842a7c (#55) call are "
                     "the class's colour-variant attacks; this port runs the id-1 path");
}

/* ── 0x00693468: 7/0 and 7/77 ───────────────────────────────────────────────────────── */

/* State 0 starts motion 0x2f at 4.0 and two tail steps; the colour variants add a timer
 * there, and their id-branch is the only caller of 0x00842a7c. State 1 (id 1) waits for
 * the finish flag and falls into 0/2's base handler. The r1 the case block passes (0 for
 * 7/0, 1 for 7/77) is only read inside the id 0x41 branch, so it does not split the two
 * ids for this monster. */
static void run_7_0_77(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        log_variants_not_carried(call);
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_7_0, 4.0f);
        tail_step0(call, enemy, 0u, 1u);
        tail_step0(call, enemy, 1u, 9u);
    } else if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* ── 0x00693be8: 7/1, 7/20 and 7/42 ────────────────────────────────────────────────── */

/* The first three states are shared; state 3 is where the action variant splits:
 *   variant 0 (7/1):  a 20.0 timer that speeds the monster toward it, then 0/6's base;
 *   variant 1 (7/20): a flag, motion 0xda, then a 30.0 check and 0/2's base;
 *   variant 2 (7/42): a 10.0/5.0 timer drive, motion 0x3c, then 0/2's base. */
static void run_7_1_3(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_STATE2, 0u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        order_rathian(call, enemy);
        motion(call, enemy, MOTION_7_1, 6.0f);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        return;
    }
    if (state == 1) {
        mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, VERTICAL_7_1, 0.0f, NULL);
        if (mhuc_read32(call, work + WORK_SPEED) > 0xc3480000u) { /* -200.0's bits */
            mhuc_put_f32(call, work + WORK_SPEED, SPEED_MIN_7_1);
        }
        switch ((int)mhuc_read8(call, work + WORK_STATE2)) {
        case 0:
            mhuc_call(call, FN_TURN_STEP, enemy, 0x100u, 0u, 0u);
            if (per_mode(call, enemy, 1u, 50.0f, 0.0f)) {
                mhuc_write8(call, work + WORK_STATE2, 1u);
                mhuc_call(call, FN_AIM_RESET, enemy, 0u, 0u, 0u);
                mhuc_put_f32(call, work + WORK_AIM_BZ, AIM_BZ_7_1);
                blend(call, enemy, 0x10u, variant == 0 ? 0.0f : -15.0f);
                tail_step(call, enemy, 0u, 0x0eu, 3u);
            }
            return;
        case 1:
            mhuc_call_f(call, FN_AIM_ADVANCE, enemy, 0u, 0u, 0u, 1.0f, 0.0f, NULL);
            if (mhuc_read32(call, work + WORK_AIM_Z) > 0x42dc0000u) { /* 110.0's bits */
                mhuc_put_f32(call, work + WORK_AIM_Z, AIM_Z_MAX_7_1);
            }
            if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                mhuc_write8(call, work + WORK_STATE, 2u);
                motion(call, enemy, MOTION_7_1b, 6.0f);
            }
            return;
        default:
            return;
        }
    }
    if (state == 2) {
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, SPEED_MIN_7_1, 0.0f, NULL);
        mhuc_call_f(call, FN_AIM_ADVANCE, enemy, 0u, 0u, 0u, 1.0f, 0.0f, NULL);
        if (mhuc_read32(call, work + WORK_AIM_Z) > 0x42dc0000u) {
            mhuc_put_f32(call, work + WORK_AIM_Z, AIM_Z_MAX_7_1);
        }
        if ((int)mhuc_call(call, FN_LAND, enemy, 0u, 0u, 0u) != 1) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 3u);
        mhuc_write8(call, work + WORK_STATE2, 0u);
        if (variant == 1) {
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_7_1e, 0.0f);
            mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, 0.0f, 0.0f, NULL);
            return;
        }
        if (variant == 2) {
            motion(call, enemy, MOTION_7_1f, 10.0f);
            return;
        }
        motion(call, enemy, MOTION_7_1c, 6.0f);
        mhuc_put_f32(call, work + WORK_AIM_BZ, AIM_BZ_7_1_END);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        return;
    }
    if (state == 3) {
        if (variant == 1) {
            if (mhuc_read8(call, work + WORK_STATE2) == 0u) {
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_write8(call, work + WORK_STATE2, 1u);
                    motion(call, enemy, MOTION_7_1d, 0.0f);
                }
                return;
            }
            if (per_mode(call, enemy, 0u, 30.0f, 0.0f)) {
                mhuc_call(call, FN_CLEAR_SLOT, enemy, 0u, 0u, 0u);
            }
            if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                mhuc_3u_base_0_2(call, enemy, work);
            }
            return;
        }
        if (variant == 2) {
            if (mhuc_read8(call, work + WORK_STATE2) == 0u) {
                const float timer = mhuc_f32(call, work + WORK_TIMER);
                if (timer < TIMER_MAX_7_1_V2) {
                    const float now = timer + mhuc_f32(call, enemy + ENEMY_DELTA);
                    mhuc_put_f32(call, work + WORK_TIMER, now);
                    mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u,
                                (TIMER_BASE_7_1_V2 - now) * SPEED_MIN_7_1 * RATE_7_1_V2,
                                0.0f, NULL);
                }
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_write8(call, work + WORK_STATE2, 1u);
                    mhuc_call(call, FN_CLEAR_SLOT, enemy, 0u, 0u, 0u);
                    mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
                    motion(call, enemy, MOTION_7_1g, 0.0f);
                }
                return;
            }
            if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                mhuc_3u_base_0_2(call, enemy, work);
            }
            return;
        }
        /* variant 0 */
        {
            const float timer = mhuc_f32(call, work + WORK_TIMER);
            if (timer < TIMER_MAX_7_1) {
                const float now = timer + mhuc_f32(call, enemy + ENEMY_DELTA);
                mhuc_put_f32(call, work + WORK_TIMER, now);
                mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u,
                            (TIMER_MAX_7_1 - now) * SPEED_PCT_7_1 * RATE_7_1, 0.0f, NULL);
            }
        }
        if (per_mode(call, enemy, 0u, 110.0f, 0.0f)) {
            mhuc_call(call, FN_CLEAR_SLOT, enemy, 0u, 0u, 0u);
        }
        mhuc_call_f(call, FN_AIM_ADVANCE, enemy, 0u, 0u, 0u, 1.0f, 0.0f, NULL);
        if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
            mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_6(call, enemy, work);
        }
    }
}

/* ── 0x00694180: 7/2, 7/10, 7/11 and 7/15 ──────────────────────────────────────────── */

/* State 0 starts motion 0x33 at 6.0 (7/15 keeps the order step out). State 1 runs the
 * four distance checks at 2.0, 12.0, 36.0 and 78.0; the first three spawn an effect and the
 * last builds the attack structure whose target check is #55's 0x0084161c. */
static void run_7_2(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        if (variant != 3) {
            order_rathian(call, enemy);
        }
        motion(call, enemy, MOTION_7_2, 6.0f);
        return;
    }
    if (state != 1) {
        return;
    }
    if (variant == 3) {
        log_curve(call, 0x00b0b1c0u);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_2, 0.0f)) {
        spawn_effect(call, enemy, EFFECT_7_2_A);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_2B, 0.0f)) {
        spawn_effect(call, enemy, EFFECT_7_2_B);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_2C, 0.0f)) {
        spawn_effect(call, enemy, EFFECT_7_2_B);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_2D, 0.0f)) {
        log_effect_builder(call);
        log_target_check(call);
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── 0x006944b8: 7/4 and 7/12 ──────────────────────────────────────────────────────── */

/* The variant chooses the motion (0x32/0x31), the three tail arguments and the turn step
 * (+0x8000/-0x8000). States 1 and 2 turn by that step at 0..120, latch the tail once while
 * work+0x6 and work+0xb81 are clear, and state 2 ends on the finish flag into 0/2's base. */
static void run_7_4(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const uint32_t motion_number = variant == 1 ? MOTION_7_4b : MOTION_7_4a;
    const uint32_t c1 = variant == 1 ? 4u : 0x1du;
    const uint32_t c2 = variant == 1 ? 0x20u : 0x22u;
    const uint32_t c3 = variant == 1 ? 0x21u : 0x23u;
    const int32_t turn = variant == 1 ? TURN_7_4 : -TURN_7_4;
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_STATE2, 0u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, motion_number, 4.0f);
        tail_step(call, enemy, 0u, c1, 8u);
        tail_step(call, enemy, 1u, c2, 0x18u);
        return;
    }
    if (state != 1 && state != 2) {
        return;
    }
    mhuc_call_f(call, FN_TURN, enemy, (uint32_t)turn, 0u, 0u, 0.0f, CHECK_7_4, NULL);
    if (mhuc_read8(call, work + WORK_STATE2) == 0u && mhuc_read8(call, work + WORK_B81) == 0u) {
        mhuc_write8(call, work + WORK_STATE2, 1u);
        tail_step(call, enemy, 1u, c3, 0x10u);
    }
    if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        return;
    }
    if (state == 1) {
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_write8(call, work + WORK_STATE2, 0u);
        motion(call, enemy, motion_number, 4.0f);
        tail_step(call, enemy, 0u, c1, 8u);
        tail_step(call, enemy, 1u, c2, 0x18u);
    } else {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── 0x00694694: 7/5 and 7/61 ──────────────────────────────────────────────────────── */

/* State 0 starts motion 0xce at 10.0 and a tail. While the flag is clear, state 1 runs the
 * 200.0 check and the speed ratio; when it sets, 7/61 (variant 1) ends in 0/6's base while
 * 7/5 (variant 0) starts motion 0xcf and waits a second state for 0/2's. */
static void run_7_5(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        order_rathian(call, enemy);
        motion(call, enemy, MOTION_7_5, 10.0f);
        tail_step0(call, enemy, 0u, 0x1bu);
        return;
    }
    if (state == 1) {
        mhuc_call(call, FN_RESET_ONE, enemy, 0u, 0u, 0u);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE, 2u);
            if (variant != 0) {
                mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
                mhuc_3u_base_0_6(call, enemy, work);
            } else {
                mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
                motion(call, enemy, MOTION_7_5b, 0.0f);
                tail_step0(call, enemy, 0u, 0x16u);
                mhuc_call(call, FN_RESET_ONE, enemy, 0u, 0u, 0u);
            }
            return;
        }
        if (per_mode(call, enemy, 1u, CHECK_7_5, 0.0f)) {
            const float a = mhuc_f32(call, enemy + ENEMY_SPEED_A) - CHECK_7_5;
            const float b = mhuc_f32(call, enemy + ENEMY_SPEED_B) - CHECK_7_5;
            mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, (a / b) * TURN_7_5, 0.0f, NULL);
        }
        return;
    }
    if (state == 2) {
        mhuc_call(call, FN_RESET_ONE, enemy, 0u, 0u, 0u);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* ── 0x00694840: 7/6, 7/7, 7/16, 7/19, 7/32 and 7/85 ─────────────────────────────── */

/* State 0 starts motion 0x8 at 4.0, a tail, and the variant's blend: 7/6 arms a 20.0 timer
 * at -300.0, 7/7 -900.0, 7/16 clamps work+0x2a8 at 1000.0, 7/19 -300.0 without a timer,
 * 7/32 -2000.0 and 7/85 -600.0. State 1 counts the timer down by the frame delta and runs
 * the landing step with 0x80 for 7/6 and 7/85, 0x40 for the rest; when it returns and the
 * timer is spent the variant picks its next motion (or 7/32 applies 4/7). */
static void run_7_6(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        order_rathian(call, enemy);
        motion(call, enemy, MOTION_7_6, 4.0f);
        tail_step(call, enemy, 0u, 5u, 3u);
        mhuc_put_f32(call, work + WORK_TIMER, 0.0f);
        switch (variant) {
        case 0:
            blend(call, enemy, 0x10u, BLEND_7_6_A);
            mhuc_put_f32(call, work + WORK_TIMER, TIMER_7_6_A);
            break;
        case 1:
            blend(call, enemy, 0x10u, BLEND_7_6_B);
            break;
        case 2:
            blend(call, enemy, 0u, BLEND_7_6_A);
            if (mhuc_read32(call, work + WORK_2A8) >= 0x447a0000u) { /* 1000.0's bits */
                mhuc_put_f32(call, work + WORK_2A8, CLAMP_7_6);
            }
            break;
        case 3:
            blend(call, enemy, 0u, BLEND_7_6_A);
            break;
        case 4:
            blend(call, enemy, 0x10u, BLEND_7_6_C);
            break;
        default: /* 5 */
            blend(call, enemy, 0x10u, BLEND_7_6_D);
            break;
        }
        return;
    }
    if (state == 1) {
        const float delta = mhuc_f32(call, enemy + ENEMY_DELTA);
        float timer = mhuc_f32(call, work + WORK_TIMER) - delta;
        if ((int32_t)timer <= 0) {
            timer = 0.0f;
        }
        mhuc_put_f32(call, work + WORK_TIMER, timer);
        if ((int)mhuc_call(call, FN_LAND, enemy, 0u,
                           (variant == 0 || variant == 5) ? 0x80u : 0x40u, 0u) == 0) {
            return;
        }
        if (timer > 0.0f) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, 2u);
        mhuc_write8(call, work + WORK_STATE2, 0u);
        switch (variant) {
        case 2:
            motion(call, enemy, MOTION_7_6c, 4.0f);
            return;
        case 3:
            motion(call, enemy, MOTION_7_6d, 4.0f);
            return;
        case 4:
            mhuc_call(call, FN_CLEAR_SLOT, enemy, 0u, 0u, 0u);
            mhuc_call(call, FN_APPLY_NEXT, enemy, 4u, 7u, 0u);
            return;
        default:
            mhuc_call(call, FN_CLEAR_SLOT, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_7_6b, 4.0f);
            return;
        }
    }
    if (state == 2) {
        if (mhuc_read8(call, work + WORK_STATE2) == 0u) {
            if (per_mode(call, enemy, 1u, variant == 2 ? CHECK_7_6B : CHECK_7_6, 0.0f)) {
                mhuc_write8(call, work + WORK_STATE2, 1u);
                if (variant == 2) {
                    mhuc_call(call, FN_CLEAR_SLOT, enemy, 0u, 0u, 0u);
                } else {
                    tail_step0(call, enemy, 0u, 0x0du);
                }
            }
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
    }
}

/* ── 0x00694bf4: 7/8 and 7/34 ──────────────────────────────────────────────────────── */

/* State 0 starts motion 0xd0 at 4.0. State 1 runs the distance checks at 2, 12 and 36
 * (effects), then 78, 120 and 164 build the attack structure (0x00688a20) and enter the
 * target check at 0x0084161c; both are named as blocked above. 7/34 (variant 1) adds the
 * source curve's rate step first. */
static void run_7_8(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        order_rathian(call, enemy);
        motion(call, enemy, MOTION_7_8, 4.0f);
        return;
    }
    if (state != 1) {
        return;
    }
    if (variant == 1) {
        log_curve(call, 0x00b0b1e8u);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_8_A, 0.0f)) {
        spawn_effect(call, enemy, 3u);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_8_B, 0.0f)) {
        spawn_effect(call, enemy, 1u);
    }
    if (per_mode(call, enemy, 0u, CHECK_7_8_C, 0.0f)) {
        spawn_effect(call, enemy, 1u);
    }
    int reached = 0;
    if (per_mode(call, enemy, 0u, CHECK_7_8_D, 0.0f)) {
        reached = 1;
    }
    if (per_mode(call, enemy, 0u, CHECK_7_8_E, 0.0f)) {
        reached = 1;
    }
    if (per_mode(call, enemy, 0u, CHECK_7_8_F, 0.0f)) {
        reached = 2;
    }
    if (reached != 0) {
        log_effect_builder(call);
        log_target_check(call);
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── the family's dispatch and self-test ──────────────────────────────────────────── */

/* Runs category 7's part 1 for the pair, or returns 0 so the module's dispatch tries the
 * next family. The r1 the source's case block passes becomes `variant`; it selects the
 * motion, speed or tail in five of the seven units. */
static int dispatch_cat7a(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    if (category != 7) {
        return 0;
    }
    switch (index) {
    case 0: case 77: run_7_0_77(call, enemy, work); return 1;
    case 1: run_7_1_3(call, enemy, work, 0); return 1;
    case 20: run_7_1_3(call, enemy, work, 1); return 1;
    case 42: run_7_1_3(call, enemy, work, 2); return 1;
    case 2: run_7_2(call, enemy, work, 0); return 1;
    case 10: run_7_2(call, enemy, work, 1); return 1;
    case 11: run_7_2(call, enemy, work, 2); return 1;
    case 15: run_7_2(call, enemy, work, 3); return 1;
    case 4: run_7_4(call, enemy, work, 0); return 1;
    case 12: run_7_4(call, enemy, work, 1); return 1;
    case 5: run_7_5(call, enemy, work, 0); return 1;
    case 61: run_7_5(call, enemy, work, 1); return 1;
    case 6: run_7_6(call, enemy, work, 0); return 1;
    case 7: run_7_6(call, enemy, work, 1); return 1;
    case 16: run_7_6(call, enemy, work, 2); return 1;
    case 19: run_7_6(call, enemy, work, 3); return 1;
    case 32: run_7_6(call, enemy, work, 4); return 1;
    case 85: run_7_6(call, enemy, work, 5); return 1;
    case 8: run_7_8(call, enemy, work, 0); return 1;
    case 34: run_7_8(call, enemy, work, 1); return 1;
    default: return 0;
    }
}

/* What this family carries: the seven units, their ids, the frame values that split the
 * variants, the two field-map rows this slice adds and the calls still blocked. The
 * module's self-test calls this with the others'. */
static void self_test_cat7a(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 21 of the 191 actions: 7/0 and 7/77 <- 0x00693468 (motion 0x2f at "
             "4.0); 7/1, 7/20 and 7/42 <- 0x00693be8 (motion 0xd1 at 6.0, a 20.0/10.0 timer "
             "or the 0xda finish); 7/2, 7/10, 7/11 and 7/15 <- 0x00694180 (motion 0x33 at "
             "6.0, the 2/12/36/78 checks); 7/4 and 7/12 <- 0x006944b8 (motion 0x32/0x31 at "
             "4.0, turn +-0x8000 at 0..120); 7/5 and 7/61 <- 0x00694694 (motion 0xce at "
             "10.0, 0xcf or the 0/6 base); 7/6, 7/7, 7/16, 7/19, 7/32 and 7/85 <- "
             "0x00694840 (motion 0x8 at 4.0, six blends and motions 0x9/0x40/0x30); 7/8 "
             "and 7/34 <- 0x00694bf4 (motion 0xd0 at 4.0, the 2/12/36 checks)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine calls are MH4U's: mode 0x%08x, motion 0x%08x, flag "
              "0x%08x, per-mode 0x%08x, aim advance 0x%08x, land 0x%08x, blend 0x%08x, "
              "effect 0x%08x, base 0/2 and 0/6 from cat0",
              (unsigned)FN_MODE, (unsigned)FN_MOTION, (unsigned)FN_FLAG,
              (unsigned)FN_PER_MODE, (unsigned)FN_AIM_ADVANCE, (unsigned)FN_LAND,
              (unsigned)FN_BLEND, (unsigned)FN_EFFECT);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: +0x5/+0x6 -> +0x144/+0x145, +0x28 -> +0x1d4, "
             "+0x68 -> +0x180, +0x80/+0x84 -> +0x1a8/+0x1ac, +0x268/+0x278 -> "
             "+0x168/+0x178, +0x2a8 -> +0x238, +0xb81 -> +0xca5");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: 0x0084161c (#55) and 0x00688a20/0x00829950 block the effect "
             "spawn of 7/2's and 7/8's 78.0 check; 0x00842a7c (#55) is only the colour "
             "variants' branch; the source's curves 0x00b0b1c0/0x00b0b1e8 are not carried");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat7a = {
    "cat7a", 21, dispatch_cat7a, self_test_cat7a,
};
