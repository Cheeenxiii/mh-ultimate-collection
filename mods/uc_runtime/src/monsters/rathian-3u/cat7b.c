/*
 * cat7b.c: 3U Rathian's category 7, part 2 — 7/3, 7/9, 7/13, 7/14, 7/17, 7/18, 7/21, 7/30,
 * 7/41, 7/43, 7/44, 7/53, 7/54, 7/55, 7/56, 7/72, 7/73, 7/78, 7/80, 7/83, 7/88 and 7/89,
 * on the handler units 0x00694474 (the veneer), 0x00694f4c, 0x006956e8, 0x00695e68 and
 * 0x00696408.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending. Each handler is MH3U's own, reimplemented on MH4U's
 * uEnemy with MH4U's engine functions at the source's points (decision 0002's 2026-11-26
 * amendments), and the source's frame values. Nothing here calls MH4U's handler for the same
 * action: the port runs the source's.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). The offsets are the
 * ones the runtime's README maps for category 0 and the flight handlers; the rows this slice
 * adds are named in each comment. The motions are MH4U's file << 8 | slot for her converted
 * motion lists: MH3U packs file * 100 + slot, so 0xcd (205) is file 2, slot 5, i.e.
 * MHUC_MOTION(2, 5).
 *
 * The engine calls go to MH4U's counterparts through ABI 4's call2. The ones MH4U has no
 * counterpart for, or that need the source's own data, are named and logged once (see
 * log_blocked and the self-test): 0x00842a7c is #55's; 0x0083c6e0 is MH4U's 0x00922250 but
 * its argument is a source curve table (0x00c4ee30, 0x00c4ee70, 0x00c4ef98); the effect
 * spawn 0x00164f08/0x00688a20/0x00688870/0x0063cabc and the shell factory 0x0063e4ac take
 * the source's effect and shell ids and manager objects. 0x00584760 and 0x0084161c are not
 * reached by this slice's units.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* The MH4U work block *(enemy + 0xe28), its offsets, and the 3U offset each stands for. */
#define WORK_STATE      0x0144u  /* 3U +0x5:  the action's state byte */
#define WORK_SUBSTATE   0x0145u  /* 3U +0x6:  its second state byte */
#define WORK_KIND       0x01c0u  /* 3U +0x3:  the enemy-data key (MH4U's id byte) */
#define WORK_MODE       0x01c8u  /* 3U +0xdc: the mode byte */
#define WORK_TURN       0x01a8u  /* 3U +0x80: the turn slot */
#define WORK_HEADING    0x01acu  /* 3U +0x84: the heading (a u16 angle, not a float) */
#define WORK_UP         0x0180u  /* 3U +0x68: the vertical value 0/6 and these units step */
#define WORK_AIM_Y      0x0164u  /* 3U +0x264: the aim point's y */
#define WORK_AIM_Z      0x0168u  /* 3U +0x268: the aim point's z */
#define WORK_AIM_BZ     0x0178u  /* 3U +0x278: the aim vector's z */
#define WORK_FALL       0x019cu  /* 3U +0x3c: the fall height */
#define WORK_SET        0x01dcu  /* 3U +0xf2: "the action was set" */

/* The enemy's own fields (not the work block). */
#define ENEMY_TARGET    0x08d88u /* 3U this+0x1e70: the target-line struct's pointer */
#define ENEMY_SPEED_2   0x029cu  /* 3U this+0x284: the second speed 0x0083c6cc reads */

/* The MH4U engine functions this slice calls, and the 3U function each stands for. */
#define FN_MODE         0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION       0x0094e318u /* [0x00828828] start a motion (index r1, s0/s1) */
#define FN_MOTION_ARGS  0x0093310cu /* [0x00844a40] (r1, r2, r3): the motion/parameter pair */
#define FN_MOTION_ARGS2 0x00914dc4u /* [0x00844a38] (r1, r2) */
#define FN_FLAG         0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_DATA_FLOAT   0x0093d870u /* [0x00852324] the action data's float, in s0 */
#define FN_APPLY_FALL   0x0092e99cu /* [0x00844124] advance the fall by s0, set mode 1 */
#define FN_CLEAR_AIM    0x0096e164u /* [0x00839968] clear the aim point and vector */
#define FN_VERTICAL     0x00915d44u /* [0x00833b2c] advance the vertical value by s0 * delta */
#define FN_TURN         0x0091db4cu /* [0x008357b0] turn toward the target by r1 (r2 = 0) */
#define FN_TURN_STEP    0x0091b430u /* [0x00839ea0, 0x00839514] (this, slot, s0, s1) */
#define FN_BLEND        0x0092dc50u /* [0x008437f4] the vertical blend filter (this, r1, s0) */
#define FN_LANDING      0x0092dcccu /* [0x008438e8] the landing step (this, r1, r2) */
#define FN_MODE_CHECK   0x0091aae4u /* [0x0083336c] the per-mode check (this, r1, s0, s1) */
#define FN_PERMODE      0x00942220u /* [0x0083369c] the per-mode step (this, s0) */
#define FN_SPEED        0x00916108u /* [0x00833d88] speed += s0 * delta */
#define FN_AIM_ADVANCE  0x00911090u /* [0x00834098] advance the aim point by the aim vector */
#define FN_POSITION     0x00912288u /* [0x0082cee4] advance the position by a speed vector */
#define FN_ONE_SHOT     0x00922ca0u /* [0x0083d18c] set the action's one-shot byte */
#define FN_WORK_FLAG    0x00914de0u /* [0x00832670] set a flag byte in the work block */
#define FN_RUN_FLAG     0x0091b7b0u /* [0x008345f8] apply the action's run flag */
#define FN_CAMERA       0x00916228u /* [0x0082fc8c] the action's camera step */
#define FN_TARGET_Y     0x00923f90u /* [0x0083db3c] the target's height, in s0 */
#define FN_ANGLE_POS    0x00568c64u /* [0x00584cd8] the u16 angle from a point to a point */
#define FN_DISTANCE     0x00aacd50u /* [0x005858f4] the distance between two points */

/* The source's motion numbers, in MH4U's form (its file << 8 | slot). */
#define MOTION_0_CD  MHUC_MOTION(2, 5)   /* 3U 0xcd */
#define MOTION_0_CE  MHUC_MOTION(2, 6)   /* 3U 0xce */
#define MOTION_0_CF  MHUC_MOTION(2, 7)   /* 3U 0xcf */
#define MOTION_0_D2  MHUC_MOTION(2, 10)  /* 3U 0xd2 */
#define MOTION_0_E1  MHUC_MOTION(2, 25)  /* 3U 0xe1 */
#define MOTION_0_E2  MHUC_MOTION(2, 26)  /* 3U 0xe2 */
#define MOTION_0_E3  MHUC_MOTION(2, 27)  /* 3U 0xe3 */
#define MOTION_0_E4  MHUC_MOTION(2, 28)  /* 3U 0xe4 */
#define MOTION_0_D6  MHUC_MOTION(2, 14)  /* 3U 0xd6 */
#define MOTION_0_D7  MHUC_MOTION(2, 15)  /* 3U 0xd7 */
#define MOTION_0_D8  MHUC_MOTION(2, 16)  /* 3U 0xd8 */
#define MOTION_0_D9  MHUC_MOTION(2, 17)  /* 3U 0xd9 */
#define MOTION_0_08  MHUC_MOTION(0, 8)   /* 3U 8 */
#define MOTION_0_1B  MHUC_MOTION(0, 27)  /* 3U 0x1b */
#define MOTION_0_2F  MHUC_MOTION(0, 47)  /* 3U 0x2f */
#define MOTION_0_36  MHUC_MOTION(0, 54)  /* 3U 0x36 */
#define MOTION_0_37  MHUC_MOTION(0, 55)  /* 3U 0x37 */

/* The source's frame values. */
#define VERTICAL_STEP   (-2.5f)  /* the source's -5.0, halved as 3U's 0x00833b2c does */
#define VERTICAL_CLAMP  (-75.0f)
#define VERTICAL_CLAMP_BITS 0xc2960000u
#define FALL_STEP_398   398.31f  /* the 0x6952a4 literal */
#define AIM_STEP_60     60.0f
#define AIM_STEP_64     64.0f
#define AIM_STEP_69     69.0f
#define AIM_STEP_74     74.0f
#define AIM_STEP_78     78.0f
#define AIM_STEP_82     82.0f
#define AIM_STEP_6      6.0f
#define AIM_STEP_16     16.0f
#define AIM_STEP_120    120.0f
#define AIM_STEP_184    184.0f
#define AIM_STEP_1      1.0f
#define AIM_LIMIT_34    34.0f
#define AIM_LIMIT_NEG3  (-3.0f)
#define AIM_LIMIT_5     5.0f
#define AIM_LIMIT_BITS  0x40a00000u
#define TURN_0x400      0x400u
#define TURN_0xED       0xedu
#define TURN_0x40       0x40u
#define TURN_0x150      0x150u
#define CATEGORY_NONE   0x0bu

/* The 3U kind values these handlers test, read from MH4U's work+0x1c0: the ported 3U Rathian
 * is the stand-in's em001 (id 1), exactly as the source's is. 0x3e to 0x41 are the colour
 * variants (em062 to em065), which this port does not run. */
#define KIND_RATHIAN    1
#define KIND_RATHALOS   2
#define KIND_VARIANT_3E 0x3eu
#define KIND_VARIANT_3F 0x3fu
#define KIND_VARIANT_40 0x40u
#define KIND_VARIANT_41 0x41u

/* ── the blocked calls ─────────────────────────────────────────────────────────────── */

/* The calls this slice cannot make yet, each logged once. They are named in the self-test and
 * the PR that added the family. */
enum {
    BLOCK_842A7C = 1u << 0,  /* MH4U has no counterpart (#55) */
    BLOCK_CURVE  = 1u << 1,  /* 0x0083c6e0's source curve table */
    BLOCK_EFFECT_A = 1u << 2, /* 0x00164f08's effect spawn, the 0x1c72 point */
    BLOCK_EFFECT_B = 1u << 6, /* the same with the 0x1555 point (selectors 5 and 6) */
    BLOCK_SHELL  = 1u << 3,  /* 0x0063e4ac's source shell ids and manager */
    BLOCK_GLOBAL = 1u << 4,  /* the source's manager count at *[0x00c1bff8]+0x4044 */
    BLOCK_U16    = 1u << 5,  /* work+0x140 -> the target line's +0x6a (unmapped) */
};

static unsigned blocked_mask;

static int block_once(MH4UCall *call, unsigned bit, const char *text) {
    (void)call;
    if (blocked_mask & bit) {
        return 0;
    }
    blocked_mask |= bit;
    mhuc_log(MH4U_LOG_INFO, text);
    return 1;
}

/* The source's 0x0083c6e0: MH4U's 0x00922250 has the same body, but the call takes one of the
 * source's curve tables and MH4U's counterpart curves by MH4U's own. The source's table is not
 * carried, so the aim coordinate keeps its previous value until the curves are. */
static void log_curve_blocked(MH4UCall *call) {
    block_once(call, BLOCK_CURVE,
               "open: 0x0083c6e0's curve table (0x00c4ee30/0x00c4ee70/0x00c4ef98) is MH3U's "
               "data; MH4U's 0x00922250 curves by its own, so the aim coordinate keeps its "
               "value");
}

/* The source's state-2 effect spawn: 0x00688a20 builds a point from 0x00199d00 and
 * 0x00829950, 0x00688870 chooses the effect's part, 0x00164f08 spawns it, and the shell
 * factory 0x0063e4ac takes a point and the source's type. None of the point helpers has an
 * MH4U counterpart (the whole-code map's best is 0x00829950 -> 0x00c74624 at 0.35), and the
 * effect/shell ids and the manager globals are the source's. */
static void log_effect_blocked(MH4UCall *call, uint32_t point_selector) {
    /* The source builds the point at the effect spawn; its selector (0x1c72 for selectors 1
     * to 4, 0x1555 for 5 and 6) is in the line, so a run says which path a move took. */
    if (point_selector == 0x1555u) {
        block_once(call, BLOCK_EFFECT_B,
                   "open: 0x00164f08's effect spawn (point 0x1555, with 0x00688a20, "
                   "0x00688870 and 0x0063cabc) is not carried: 0x00199d00 and 0x00829950 "
                   "have no MH4U counterpart and the effect ids 0x17/2/4 are the source's");
    } else {
        block_once(call, BLOCK_EFFECT_A,
                   "open: 0x00164f08's effect spawn (point 0x1c72, with 0x00688a20, "
                   "0x00688870 and 0x0063cabc) is not carried: 0x00199d00 and 0x00829950 "
                   "have no MH4U counterpart and the effect ids 0x17/2/4 are the source's");
    }
    blocked_mask |= BLOCK_SHELL;  /* the same block's shell factory; one line covers it */
}

static void log_842a7c_blocked(MH4UCall *call) {
    block_once(call, BLOCK_842A7C,
               "open: 0x00842a7c (with 0x0084161c, not reached here) has no MH4U counterpart; "
               "#55's trace settles it");
}

static void log_global_blocked(MH4UCall *call) {
    block_once(call, BLOCK_GLOBAL,
               "open: the source's manager count at *[0x00c1bff8]+0x4044 (the spawn gate) has "
               "no MH4U counterpart; the port takes the smaller count");
}

/* ── the shared engine steps ────────────────────────────────────────────────────────── */

/* 3U's 0x00828828: the motion start. The source's wrapper converts the caller's r3 to a float
 * for the real function (0x0083771c) and computes its second float from work+0x814, which the
 * port does not map; its caller's r2 is an extra argument MH4U's wrapper has no place for
 * (0x0094e318 forces r2=0). The motion number is the source's file/slot; the speed is the
 * value MH4U's own handler gives the counterpart call at the same step (4.0, 6.0 or 0.0), or
 * the source's own r3 when it sets one (0x46, 70.0). */
static void motion(MH4UCall *call, uint32_t enemy, uint32_t index, float speed) {
    mhuc_call_f(call, FN_MOTION, enemy, index, 0u, 0u, speed, 0.0f, NULL);
}

/* The vertical step and the -75.0 clamp (3U 0x00833b2c, halved; then the unsigned bit
 * compare the source makes). */
static void step_vertical(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_call_f(call, FN_VERTICAL, enemy, 0u, 0u, 0u, VERTICAL_STEP, 0.0f, NULL);
    if (mhuc_read32(call, work + WORK_UP) > VERTICAL_CLAMP_BITS) {
        mhuc_put_f32(call, work + WORK_UP, VERTICAL_CLAMP);
    }
}

/* 3U's 0x0083c6cc: this+0x284 times 2.0, which the field map puts at MH4U's this+0x29c (the
 * same twin 0x0083c6e0/0x00922250 reads both speeds). */
static float speed_2(MH4UCall *call, uint32_t enemy) {
    return mhuc_f32(call, enemy + ENEMY_SPEED_2) * 2.0f;
}

/* 3U's 0x0068872ec: the per-kind, per-mode run flag 0x008345f8 applies. Its values are the
 * source's -14, -15, -10 and -7 (mvn #0xd, #0xe, #9, #6). */
static void run_flag_6872ec(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int kind = (int)mhuc_read8(call, work + WORK_KIND);
    const int mode = (int)mhuc_read8(call, work + WORK_MODE);
    int flag;
    if (kind == KIND_RATHIAN) {
        flag = -14;
    } else if (kind == KIND_RATHALOS) {
        flag = (mode == 3) ? -10 : -15;
    } else if (kind == KIND_VARIANT_3E || kind == KIND_VARIANT_3F) {
        flag = (mode == 3) ? -7 : -10;
    } else if (kind == KIND_VARIANT_40 || kind == KIND_VARIANT_41) {
        flag = (mode == 3) ? -7 : -14;
    } else {
        return;
    }
    mhuc_call(call, FN_RUN_FLAG, enemy, (uint32_t)(int32_t)flag, 0u, 0u);
}

/* ── 0x00687398: the state machine the veneer reaches (7/3 and its nine siblings) ──── */

/* 3U 0x00687398. The veneer 0x00694474 turns the case block's (r2, r3) into the selector and
 * forces r3 to 0, so the `r6` branches below never run for these ids (they are the direct
 * category-2 calls, which pass r3=1). r1 is the source's extra flag, used in state 3. */
static void run_687398(MH4UCall *call, uint32_t enemy, uint32_t work, int r1, int r2,
                       int r3) {
    const int extra = r3;
    const int selector = r2;
    const int flag_arg = r1;
    (void)extra;  /* 0 for every id this family runs: the veneer zeroes it */

    switch ((int)mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_0_D6, 4.0f);  /* MH4U's own 7/3 step: 4.0 */
        break;
    case 1:
        if (selector == 2 || selector == 4 || selector == 5) {
            mhuc_call(call, FN_TURN, enemy, TURN_0x400, 0u, 0u);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE,
                    (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, 50.0f, 0.0f, NULL);
        motion(call, enemy, MOTION_0_D7, 0.0f);
        mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
        log_curve_blocked(call);
        mhuc_call_f(call, FN_POSITION, enemy, work + WORK_TURN, 0u, 0u, AIM_STEP_1, 0.0f, NULL);
        break;
    case 2:
        switch (selector) {
        case 0:
            goto finish;
        case 1: case 2: case 3: case 4: {
            if (!mhuc_call_f(call, FN_MODE_CHECK, enemy, 0u, 0u, 0u, AIM_STEP_6, 0.0f,
                             NULL)) {
                goto finish;
            }
            /* 0x00688a20's point struct and 0x00688870's effect part, then the effect
             * factory: all blocked. The 0x0040/0x0080 byte the source sets belongs to that
             * struct. */
            log_effect_blocked(call, 0x1c72u);
            goto finish;
        }
        case 5: case 6: {
            if (!mhuc_call_f(call, FN_MODE_CHECK, enemy, 0u, 0u, 0u, AIM_STEP_6, 0.0f,
                             NULL)) {
                goto finish;
            }
            log_effect_blocked(call, 0x1555u);
            goto finish;
        }
        default:
            goto finish;
        }
    finish:
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_write8(call, work + WORK_SUBSTATE, 1u);
            mhuc_put_f32(call, work + WORK_AIM_BZ, 0.5f);
            mhuc_call_f(call, FN_AIM_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, AIM_STEP_1, 0.0f, NULL);
            motion(call, enemy, MOTION_0_1B, 0.0f);
        } else {
            log_curve_blocked(call);
            mhuc_call_f(call, FN_POSITION, enemy, work + WORK_TURN, 0u, 0u, AIM_STEP_1, 0.0f, NULL);
        }
        break;
    case 3:
        mhuc_call_f(call, FN_AIM_ADVANCE, enemy, work + WORK_TURN, 0u, 0u, AIM_STEP_1, 0.0f, NULL);
        if (mhuc_f32(call, work + WORK_AIM_Z) > 0.0f) {
            mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        if (flag_arg != 0) {
            if (flag_arg == 1) {
                mhuc_3u_base_0_6(call, enemy, work);
            }
            return;
        }
        if (mhuc_read8(call, work + WORK_SUBSTATE) == 0) {
            mhuc_write8(call, work + WORK_SUBSTATE, 1u);
            motion(call, enemy, MOTION_0_1B, 0.0f);
        } else if (mhuc_read8(call, work + WORK_SUBSTATE) == 1) {
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            motion(call, enemy, MOTION_0_D8, 0.0f);
        }
        break;
    case 4:
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE,
                    (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        motion(call, enemy, MOTION_0_D9, 0.0f);
        break;
    case 5:
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
        break;
    default:
        break;
    }
}

/* 3U 0x00694474: the case block's veneer. It turns (r2, r3) into 0x00687398's selector and
 * forces r3 to 0. */
static void run_694474(MH4UCall *call, uint32_t enemy, uint32_t work, int r1, int r2, int r3) {
    int selector;
    if (r2 == 0) {
        selector = (r3 == 0) ? 1 : 3;
    } else if (r2 == 1) {
        selector = (r3 == 0) ? 2 : 4;
    } else if (r2 == 2) {
        selector = 5;
    } else {
        selector = 6;
    }
    run_687398(call, enemy, work, r1, selector, 0);
}

/* ── 0x00694f4c: the seven-variant state machine (7/9, 7/14, 7/30, 7/80, 7/83, 7/88, 7/89) ── */

/* The source's state 1/4 block (0x6950ac): the state advances, the data float advances the fall,
 * then motion 0xce, the parameter pair, the extra step and the two speeds. */
static void run_694f4c_advance(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_write8(call, work + WORK_STATE,
                (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
    mhuc_write8(call, work + WORK_SUBSTATE, 0u);
    float data = 0.0f;
    mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
    mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
    motion(call, enemy, MOTION_0_CE, 0.0f);
    mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 7u, 0u);
    mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
    mhuc_put_f32(call, work + WORK_AIM_Z, speed_2(call, enemy) * AIM_LIMIT_34);
    mhuc_put_f32(call, work + WORK_AIM_BZ, speed_2(call, enemy) * AIM_LIMIT_NEG3);
}

/* 0x00694f4c, one frame. `variant` is the case block's r1: 0 for 7/9, 1 for 7/14, 2 for 7/30,
 * 3 for 7/80, 4 for 7/83, 5 for 7/88 and 6 for 7/89. */
static void run_694f4c(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    /* The prologue's flag byte (0x00832670 with 0x20). */
    mhuc_call(call, FN_WORK_FLAG, enemy, 0x20u, 0u, 0u);

    switch ((int)mhuc_read8(call, work + WORK_STATE)) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        run_flag_6872ec(call, enemy, work);
        if (variant == 3 || variant == 4 || variant == 5 || variant == 6) {
            motion(call, enemy, (variant == 3 || variant == 5) ? MOTION_0_E1 : MOTION_0_E3,
                   0.0f);
        } else {
            motion(call, enemy, MOTION_0_CD, 6.0f);  /* MH4U's own 7/9 step: 6.0 */
        }
        break;
    case 1:
        if (variant == 3 || variant == 4 || variant == 5 || variant == 6) {
            if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                return;
            }
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_call_f(call, FN_APPLY_FALL, enemy, 0u, 0u, 0u, FALL_STEP_398, 0.0f, NULL);
            motion(call, enemy, (variant == 3 || variant == 5) ? MOTION_0_E2 : MOTION_0_E4,
                   0.0f);
            mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 0x26u, 0u);
            mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
            /* 0x6951a8 copies work+0x140's u16 into the target-line struct's +0x6a. The
             * field has no map row, and MH4U's own handler has no such step. */
            block_once(call, BLOCK_U16,
                       "open: work+0x140 -> the target line's +0x6a is unmapped and MH4U's own "
                       "7/80-family handler has no such step; the copy is left out");
            break;
        }
        if (mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_3F) {
            mhuc_call(call, FN_TURN, enemy, TURN_0xED, 0u, 0u);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        run_694f4c_advance(call, enemy, work);
        break;
    case 2:
        if (variant == 3 || variant == 4 || variant == 5 || variant == 6) {
            /* 0x6953bc: the mode checks, the blocked 0x00842a7c, and the blocked curve and
             * effect steps. */
            if (mhuc_call_f(call, FN_MODE_CHECK, enemy, 1u, 0u, 0u, AIM_STEP_64, 0.0f, NULL)) {
                log_842a7c_blocked(call);
                mhuc_call(call, FN_TURN, enemy, TURN_0x150, 0u, 0u);
            }
            if (mhuc_call_f(call, FN_MODE_CHECK, enemy, 3u, 0u, 0u, AIM_STEP_120, AIM_STEP_184,
                            NULL)) {
                log_curve_blocked(call);
                float data = 0.0f;
                mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
                mhuc_call_f(call, FN_TURN_STEP, enemy, work + WORK_TURN, 0u, 0u, data, AIM_STEP_1,
                            NULL);
                if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                    mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
                }
            }
            if (!mhuc_call_f(call, FN_MODE_CHECK, enemy, 0u, 0u, 0u, AIM_STEP_184, 0.0f, NULL)) {
                return;
            }
            if (variant == 5 || variant == 6) {
                mhuc_write8(call, work + WORK_STATE,
                            (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
                mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
                motion(call, enemy, MOTION_0_CF, 0.0f);
                mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 0x16u, 0u);
                mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
            } else {
                mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
                motion(call, enemy, MOTION_0_1B, 0.0f);
                mhuc_write8(call, work + WORK_SET, 1u);  /* 3U 0x0083b424 */
            }
            break;
        }
        log_curve_blocked(call);
        {
            float data = 0.0f;
            mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
            const int substate = (int)mhuc_read8(call, work + WORK_SUBSTATE);
            if (substate == 0) {
                mhuc_call_f(call, FN_TURN_STEP, enemy, work + WORK_TURN, 0u, 0u, data, AIM_STEP_1,
                            NULL);
                if (!mhuc_call_f(call, FN_MODE_CHECK, enemy, 1u, 0u, 0u, AIM_STEP_16, 0.0f,
                                 NULL)) {
                    if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                        mhuc_write8(call, work + WORK_SUBSTATE, 1u);
                        mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
                    }
                } else {
                    mhuc_write8(call, work + WORK_SUBSTATE, 1u);
                    mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
                }
            } else if (substate == 1) {
                mhuc_call_f(call, FN_TURN_STEP, enemy, work + WORK_TURN, 0u, 0u, data, AIM_STEP_1,
                            NULL);
            }
            if (!mhuc_call_f(call, FN_PERMODE, enemy, 0u, 0u, 0u, data, 0.0f, NULL)) {
                return;
            }
            if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                return;
            }
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        }
        if (variant == 0) {
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_0_CF, 0.0f);
            mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 0x16u, 0u);
            mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
        } else if (variant == 1) {
            mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
            motion(call, enemy, MOTION_0_1B, 0.0f);
        } else {
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_0_D2, 0.0f);
            mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 0x16u, 0u);
            mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
        }
        break;
    case 3:
        if (variant == 0 || variant == 5 || variant == 6) {
            mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
            if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                mhuc_3u_base_0_2(call, enemy, work);
            }
        } else if (variant == 2) {
            mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
            if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                return;
            }
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            /* The source's own r3 = 0x46, which its wrapper turns into the first float. */
            motion(call, enemy, MOTION_0_CD, 70.0f);
        } else {
            step_vertical(call, enemy, work);
            if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                mhuc_3u_base_0_6(call, enemy, work);
            }
        }
        break;
    case 4:
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            run_694f4c_advance(call, enemy, work);
        }
        break;
    case 5:
        log_curve_blocked(call);
        {
            float data = 0.0f;
            mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
            const int substate = (int)mhuc_read8(call, work + WORK_SUBSTATE);
            if (substate == 0) {
                mhuc_call_f(call, FN_TURN_STEP, enemy, work + WORK_TURN, 0u, 0u, data, AIM_STEP_1,
                            NULL);
                if (!mhuc_call_f(call, FN_MODE_CHECK, enemy, 1u, 0u, 0u, AIM_STEP_16, 0.0f,
                                 NULL)) {
                    if (mhuc_f32(call, work + WORK_AIM_Z) < 0.0f) {
                        mhuc_write8(call, work + WORK_SUBSTATE, 1u);
                        mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
                    }
                } else {
                    mhuc_write8(call, work + WORK_SUBSTATE, 1u);
                    mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
                }
            } else if (substate == 1) {
                mhuc_call_f(call, FN_TURN_STEP, enemy, work + WORK_TURN, 0u, 0u, data, AIM_STEP_1,
                            NULL);
            }
            if (!mhuc_call_f(call, FN_PERMODE, enemy, 0u, 0u, 0u, data, 0.0f, NULL)) {
                return;
            }
            if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                return;
            }
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
            motion(call, enemy, MOTION_0_CF, 0.0f);
            mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 0x16u, 0u);
            mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
        }
        break;
    case 6:
        mhuc_call(call, FN_ONE_SHOT, enemy, 0u, 0u, 0u);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
        break;
    default:
        break;
    }
}

/* ── 0x006956e8: 7/13 ──────────────────────────────────────────────────────────────── */

/* 3U 0x006956e8. It ignores r1. The effect and shell spawns it holds are gated on the source's
 * kind (0x3e/0x3f/0x41); the ported Rathian is kind 1, so the source takes none of them. */
static void run_6956e8(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 0u, 0u, 0u);
        run_flag_6872ec(call, enemy, work);
        motion(call, enemy, MOTION_0_08, 0.0f);
        mhuc_call(call, FN_MOTION_ARGS, enemy, 0u, 5u, 2u);
        mhuc_call_f(call, FN_BLEND, enemy, 0u, 0u, 0u, -300.0f, 0.0f, NULL);
        return;
    }
    if (state == 1) {
        if (!mhuc_call(call, FN_LANDING, enemy, 0u, TURN_0x40, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE,
                    (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        motion(call, enemy, MOTION_0_2F, 0.0f);
        mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 1u, 0u);
        mhuc_call(call, FN_MOTION_ARGS2, enemy, 1u, 9u, 0u);
        /* kind 1 takes neither 0x83cbfc branch: the source tests 0x3e with the manager count
         * and 0x3f alone. */
        return;
    }
    if (state != 2) {
        return;
    }
    if (mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_3F ||
        mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_3E) {
        log_global_blocked(call);
        log_effect_blocked(call, 0x1c72u);
    }
    if (mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_41) {
        log_global_blocked(call);
        log_effect_blocked(call, 0x1c72u);
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── 0x00695e68: 7/17 and 7/78 ─────────────────────────────────────────────────────── */

/* The distance and direction step 0x695e68 shares with MH4U's own 7/17: the z speed is
 * (distance - target height * 200) / 60, clamped at 5.0 from below; the other side of the
 * circle is (target height * -200 - distance) / 60 with no clamp. */
static void run_695e68_speed(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const uint32_t point_a = work + 0x198u;  /* 3U work+0x38 */
    const uint32_t point_b = work + 0x218u;  /* 3U work+0x288 */
    const uint32_t angle = mhuc_call(call, FN_ANGLE_POS, point_b, point_a, 0u, 0u);
    const uint32_t heading = mhuc_read32(call, work + WORK_HEADING);
    const uint32_t diff = ((angle - heading) + 0x4000u) & 0xffffu;

    float distance = 0.0f;
    mhuc_call_f(call, FN_DISTANCE, point_b, point_a, 0u, 0u, 0.0f, 0.0f, &distance);
    float height = 0.0f;
    mhuc_call_f(call, FN_TARGET_Y, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &height);
    if (diff < 0x8000u) {
        const float value = distance - height * 200.0f;
        mhuc_put_f32(call, work + WORK_AIM_Z, value * (1.0f / 60.0f));
        if (mhuc_read32(call, work + WORK_AIM_Z) <= AIM_LIMIT_BITS) {
            mhuc_put_f32(call, work + WORK_AIM_Z, 0.0f);
        }
    } else {
        const float value = (height * -200.0f) - distance;
        mhuc_put_f32(call, work + WORK_AIM_Z, value * (1.0f / 60.0f));
    }
}

/* 3U 0x00695e68, one frame; it ignores r1, so 7/17 and 7/78 run it alike. */
static void run_695e68(MH4UCall *call, uint32_t enemy, uint32_t work) {
    step_vertical(call, enemy, work);  /* the entry's -5.0 and its clamp */

    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        run_flag_6872ec(call, enemy, work);
        motion(call, enemy, MOTION_0_36, 4.0f);  /* MH4U's own 7/17 step: 4.0 */
        mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 0x0cu, 0u);
        mhuc_call(call, FN_CAMERA, enemy, 0u, 0u, 0u);
        run_695e68_speed(call, enemy, work);
        return;
    }
    if (state != 1) {
        return;
    }
    /* kind 1 does not take the 0x41 branch (with its blocked 0x00842a7c). */
    if (mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_41) {
        log_global_blocked(call);
        log_842a7c_blocked(call);
    }
    if (!mhuc_call_f(call, FN_MODE_CHECK, enemy, 1u, 0u, 0u, AIM_STEP_60, 0.0f, NULL)) {
        mhuc_call(call, FN_TURN, enemy, TURN_0x40, 0u, 0u);
        mhuc_call_f(call, FN_POSITION, enemy, work + WORK_TURN, 0u, 0u, AIM_STEP_1, 0.0f, NULL);
    }
    /* The spawn gate: kind 0x41 and 0x40 (the colour variants) only. */
    if (mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_41 ||
        mhuc_read8(call, work + WORK_KIND) == KIND_VARIANT_40) {
        log_global_blocked(call);
        log_effect_blocked(call, 0x1c72u);
    }
    if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
        mhuc_write8(call, work + WORK_STATE,
                    (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        mhuc_3u_base_0_6(call, enemy, work);
    }
}

/* ── 0x00696408: 7/18 and 7/21 ─────────────────────────────────────────────────────── */

/* 3U 0x00696408; `variant` is the case block's r1 (0 for 7/18, 1 for 7/21). */
static void run_696408(MH4UCall *call, uint32_t enemy, uint32_t work, int variant) {
    step_vertical(call, enemy, work);

    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_call(call, FN_MODE, enemy, 3u, 0u, 0u);
        run_flag_6872ec(call, enemy, work);
        motion(call, enemy, MOTION_0_37, 4.0f);  /* MH4U's own 7/18 step: 4.0 */
        mhuc_call(call, FN_MOTION_ARGS2, enemy, 0u, 2u, 0u);
        if (variant == 1) {
            mhuc_call(call, FN_CLEAR_AIM, enemy, 0u, 0u, 0u);
            mhuc_put_f32(call, work + WORK_AIM_Z, 20.0f);
            mhuc_put_f32(call, work + WORK_AIM_BZ, -0.5f);
        }
        return;
    }
    if (state == 1) {
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE,
                        (uint32_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_3u_base_0_6(call, enemy, work);
        }
    }
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────── */

/* Runs category 7's part-2 handler for the pair, or returns 0 so the module's dispatch can try
 * the next family. The veneer's r2/r3 are the source case blocks' values (7/3 0,0; 7/41 1,0;
 * 7/43 0,1; 7/44 1,1; 7/53 0,0 with r3=1; 7/54 1,0 r3=1; 7/55 0,1 r3=1; 7/56 1,1 r3=1; 7/72
 * 1,2; 7/73 1,3). */
static int dispatch_cat7b(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                          int index) {
    if (category != 7) {
        return 0;
    }
    switch (index) {
    case 3:  run_694474(call, enemy, work, 0, 0, 0); return 1;
    case 41: run_694474(call, enemy, work, 1, 0, 0); return 1;
    case 43: run_694474(call, enemy, work, 0, 1, 0); return 1;
    case 44: run_694474(call, enemy, work, 1, 1, 0); return 1;
    case 53: run_694474(call, enemy, work, 0, 0, 1); return 1;
    case 54: run_694474(call, enemy, work, 1, 0, 1); return 1;
    case 55: run_694474(call, enemy, work, 0, 1, 1); return 1;
    case 56: run_694474(call, enemy, work, 1, 1, 1); return 1;
    case 72: run_694474(call, enemy, work, 1, 2, 0); return 1;
    case 73: run_694474(call, enemy, work, 1, 3, 0); return 1;
    case 9:  run_694f4c(call, enemy, work, 0); return 1;
    case 14: run_694f4c(call, enemy, work, 1); return 1;
    case 30: run_694f4c(call, enemy, work, 2); return 1;
    case 80: run_694f4c(call, enemy, work, 3); return 1;
    case 83: run_694f4c(call, enemy, work, 4); return 1;
    case 88: run_694f4c(call, enemy, work, 5); return 1;
    case 89: run_694f4c(call, enemy, work, 6); return 1;
    case 13: run_6956e8(call, enemy, work); return 1;
    case 17: run_695e68(call, enemy, work); return 1;
    case 78: run_695e68(call, enemy, work); return 1;
    case 18: run_696408(call, enemy, work, 0); return 1;
    case 21: run_696408(call, enemy, work, 1); return 1;
    default: return 0;
    }
}

/* What this family carries: the ids, their handler units, the field-map rows this slice adds
 * and the calls still blocked. The module's self-test calls this with the others'. */
static void self_test_cat7b(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 22 of the 191 actions: 7/3, 7/41, 7/43, 7/44, 7/53, 7/54, 7/55, 7/56, "
             "7/72 and 7/73 <- the veneer 0x00694474 -> 0x00687398 (the six-state flight "
             "machine); 7/9, 7/14, 7/30, 7/80, 7/83, 7/88 and 7/89 <- 0x00694f4c (the "
             "seven-variant machine); 7/13 <- 0x006956e8; 7/17 and 7/78 <- 0x00695e68; 7/18 "
             "and 7/21 <- 0x00696408");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: category 7 part 2's engine calls are MH4U's: motion 0x%08x, flag "
              "0x%08x, mode 0x%08x, turn 0x%08x, per-mode 0x%08x, fall 0x%08x, data 0x%08x, "
              "base 0/2 and 0/6 reused from cat0",
              (unsigned)FN_MOTION, (unsigned)FN_FLAG, (unsigned)FN_MODE, (unsigned)FN_TURN,
              (unsigned)FN_MODE_CHECK, (unsigned)FN_APPLY_FALL, (unsigned)FN_DATA_FLOAT);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map rows added: +0x80 -> +0x1a8 (the turn slot), +0x84 -> "
             "+0x1ac (the heading, a u16 angle), +0x264/+0x268/+0x278 -> +0x164/+0x168/+0x178 "
             "(the aim point and vector), this+0x284 -> this+0x29c (0x0083c6cc's speed), "
             "+0x68 -> +0x180 (the vertical step)");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: open: 0x00842a7c has no MH4U counterpart (#55); 0x0083c6e0's curve "
             "table is the source's data; 0x00164f08's effect spawn (0x00688a20, 0x00688870, "
             "0x0063cabc) and 0x0063e4ac's shell factory take the source's ids and manager; "
             "work+0x140's copy is unmapped");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat7b = {
    "cat7b", 22, dispatch_cat7b, self_test_cat7b,
};
