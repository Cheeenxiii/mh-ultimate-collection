/*
 * cat2_9.c: 3U Rathian's categories 2 and 9 — the nineteen ids 2/0 to 2/13 and 9/0 to 9/4.
 *
 * This is a family file, one of the files under src/monsters/rathian-3u/ that the module's
 * build discovers (tools/gen_families.py). It exports one MhucFamily (family.h); the module's
 * dispatch (src/monsters/rathian-3u.c) tries the families in the generated list and logs a
 * pair none of them carries as pending.
 *
 * The source is MH3U's uEm002 dispatcher (0x00687d30): category 2's case blocks at 0x00699d4c
 * reach the handler units 0x00690e28 (2/0, 2/7, 2/9, 2/11), 0x00690f28 (2/3, 2/8, 2/10),
 * 0x00687398 (2/4, 2/5, 2/6) and the inline blocks 0x00699dbc (2/1), 0x00699e3c (2/2),
 * 0x00699f78 (2/12) and 0x00699fcc (2/13); category 9's at 0x00687dc8 reach 0x00691020 (9/0),
 * 0x0069119c (9/1), 0x00691384 (9/2) and, through 0x00687398 again, 9/3 and 9/4.
 *
 * The work block is *(enemy + 0xe28) in MH4U (*(this+0x1a48) in MH3U). Each offset below is
 * MH4U's and the source offset it stands for. The engine calls are MH4U's counterparts of the
 * source's, from reference/README.md's engine-call map; where a source call has no MH4U
 * counterpart yet (#55) or its argument is a pointer into the source's own data, the port
 * names it once in the log and skips it, as issue #218 asks.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <string.h>

#include "family.h"

/* ── the MH4U work block, its offsets, and the 3U offset each stands for ─────────────── */
#define WORK_STATE      0x0144u /* 3U +0x5:  the handler's state byte */
#define WORK_SUB        0x0145u /* 3U +0x6:  its sub-state */
#define WORK_MODE       0x01c8u /* 3U +0xdc: the mode byte */
#define WORK_KIND       0x01c0u /* 3U +0x3:  the data record's kind/id */
#define WORK_CLAMP_2    0x0238u /* 3U +0x2a8: the float category 2 clamps at 700.0 */
#define WORK_FLOAT_168  0x0168u /* 3U +0x268: the per-frame float the handlers store */
#define WORK_FLOAT_178  0x0178u /* 3U +0x278: the 0.5 the 0x687398 tail stores */
#define WORK_FLOAT_164  0x0164u /* 3U +0x264: the per-frame float 9/2 stores */
#define WORK_TURN       0x01a8u /* 3U +0x80:  the turn slot before the heading */
#define WORK_POS_X      0x0198u /* 3U +0x38:  position x */
#define WORK_POS_Y      0x019cu /* 3U +0x3c:  position y */
#define WORK_PART       0x0278u /* 3U +0x2b6: the part byte 9/0 and 9/1's hit check takes */
#define WORK_TAIL       0x7993u /* 3U +0xe1:  the tail flag: the next move */
#define WORK_SET_9      0x77e8u /* 3U +0x7eb: the byte 0x83d18c's counterpart marks */
#define WORK_MARK_9     0x3e3u  /* 3U +0x7eb, MH4U's own byte the mark sets */

/* ── the MH4U engine functions this slice calls, and the 3U function each stands for ── */
#define FN_MODE        0x009167b4u /* [0x0082fe88] the mode/state setter */
#define FN_MOTION      0x0094e318u /* [0x00828828] start a motion now (r1, s0, s1) */
#define FN_FLAG        0x00b05da4u /* [0x0083cbf4] the action's finish flag */
#define FN_DECEL       0x0092dc50u /* [0x008437f4] a speed/position step from s0 */
#define FN_SETUP       0x0092dcccu /* [0x008438e8] the per-frame setup test (r1, r2) */
#define FN_MARK        0x00922ca0u /* [0x0083d18c] mark the action's entry */
#define FN_FORCE       0x0091db4cu /* [0x008357b0] force a target step (r1) */
#define FN_SPEED       0x00916108u /* [0x00833d88] set the speed to s0 */
#define FN_DATA        0x0096e164u /* [0x00839968] a data/effect step */
#define FN_FLOAT       0x00922250u /* [0x0083c6e0] a per-monster float from a table (r1) */
#define FN_POS         0x00912288u /* [0x0082cee4] advance a point by s0 */
#define FN_TURN        0x00911090u /* [0x00834098] turn/aim at the slot in r1 by s0 */
#define FN_PER_MODE    0x0091aae4u /* [0x0083336c] per-mode distance/speed (r1, s0, s1) */
#define FN_GATE        0x00942220u /* [0x0083369c] a gate read from the block's state */
#define FN_MASK        0x0091a84cu /* [0x00838c28] test a bit mask in r1 */
#define FN_ACTION      0x00914dc4u /* [0x00844a38] an action/motion table step (r1, r2) */
#define FN_TURN2       0x0091b430u /* [0x00839ea0, 0x00839514] turn and advance (r1, s0, s1) */
#define FN_REQUEST_NEXT 0x0094ef64u /* [0x0082a06c] request the next action (r1, r2) */
#define FN_PENDING     0x0094f408u /* [0x0082a878] set the next motion (r1, s0, s1) */
#define FN_APPLY       0x00922c40u /* [0x0083cbfc] apply the action's 1.1 float */
#define FN_DATA_FLOAT  0x0093d870u /* [0x00852324] the action data's float, returned in s0 */
#define FN_FALL        0x0092e99cu /* [0x00844124] advance the fall by s0, set mode 1 */

/* The source's motion numbers, written MH4U's way. MH3U numbers a motion file * 100 + slot;
 * MH4U writes file << 8 | slot. All of these are in file 0 or file 2, and the port ships
 * slots 0-2 (data/ids/registry.csv). */
#define M_0_06   MHUC_MOTION(0, 6)   /* 0x006 */
#define M_0_07   MHUC_MOTION(0, 7)   /* 0x007 */
#define M_0_1b   MHUC_MOTION(0, 0x1b) /* 0x01b */
#define M_2_02   MHUC_MOTION(2, 2)   /* 0x0ca = 2*100 + 2 */
#define M_2_03   MHUC_MOTION(2, 3)   /* 0x0cb */
#define M_2_05   MHUC_MOTION(2, 5)   /* 0x0cd */
#define M_2_06   MHUC_MOTION(2, 6)   /* 0x0ce */
#define M_2_07   MHUC_MOTION(2, 7)   /* 0x0cf */
#define M_2_14   MHUC_MOTION(2, 14)  /* 0x0d6 */
#define M_2_15   MHUC_MOTION(2, 15)  /* 0x0d7 */
#define M_2_16   MHUC_MOTION(2, 16)  /* 0x0d8 */
#define M_2_17   MHUC_MOTION(2, 17)  /* 0x0d9 */

/* The source's case-block arguments. Categories 2 and 9 pass a sub-index in r1 and, for
 * 0x00690e28, a variant in r2 that adds the 0x83d18c mark at the unit's entry. */
#define SUB_0 0
#define SUB_1 1
#define SUB_2 2

/* 0x00687398's arguments: r1 is the mode, r2 the variant (0, 1, 3 for the five ids) and r3 a
 * flag that adds 0x829620/0x257628 and the 0x80 flag bit. */
#define VARIANT_2_4 0
#define VARIANT_2_5 0
#define VARIANT_9_3 1
#define VARIANT_9_4 3
#define EFFECT_FLAG 1

/* ── the blocked calls, named once ─────────────────────────────────────────────────── */

/* The source calls that still wait on #55, with the item each one is. The port names the
 * first one it meets and skips it; the action goes on, the step it would take is the gap. */
#define BLOCK_ENTRY_MARK \
    "0x00853c70 (set the halfword at +0x89c to 2) waits on #55"
#define BLOCK_STATE_BYTE \
    "0x00839598 (the signed byte at +0xef of the data block) waits on #55"
#define BLOCK_HIT \
    "0x0084512c (the hit check that walks the monster list) waits on #55"
#define BLOCK_PER_FRAME \
    "0x00829620 (the per-frame action-table walk) waits on #55"
#define BLOCK_TARGET_BYTE \
    "0x00257628 (set the byte at +0x1c8 of the object at +0x14) waits on #55"
#define BLOCK_FLOAT_GET \
    "0x0083c6cc (the float at this+0x284 times a constant) waits on #55"
#define BLOCK_FLOAT_TABLE \
    "0x0083c6e0's argument is a pointer into MH3U's own data (0x00c4ee70), so the port cannot carry the table yet"
#define BLOCK_ACTION_DATA \
    "0x0082d430's argument is a pointer into MH3U's own action data (0x00b0b068/0x00b0b0a8), so the port cannot carry the table yet"
#define BLOCK_PENDING_DATA \
    "0x0082d278's argument is a pointer into MH3U's own action data (0x00b0b068/0x00b0b0a8), so the port cannot carry the table yet"
#define BLOCK_EFFECT_SETUP \
    "9/3 and 9/4's effect setup (0x00688a20, 0x00688870 and their 0x00199d00, 0x00829950 and 0x0063cabc callees) has no MH4U counterpart yet"

static const char *blocked_seen[16];
static int blocked_count;

static void block_once(MH4UCall *call, const char *what) {
    (void)call;
    for (int i = 0; i < blocked_count; i++) {
        if (strcmp(blocked_seen[i], what) == 0) {
            return;
        }
    }
    if (blocked_count < (int)(sizeof blocked_seen / sizeof blocked_seen[0])) {
        blocked_seen[blocked_count++] = what;
    }
    mhuc_logf(MH4U_LOG_INFO, "3U Rathian action: %s; the step is named and skipped", what);
}

/* ── small wrappers over the engine calls, so the handlers read like the source ──────── */

static void set_mode(MH4UCall *call, uint32_t enemy, uint32_t mode) {
    mhuc_call(call, FN_MODE, enemy, mode, 0u, 0u);
}

static void start_motion(MH4UCall *call, uint32_t enemy, uint32_t motion, float speed) {
    mhuc_call_f(call, FN_MOTION, enemy, motion, 0u, 0u, speed, 0.0f, NULL);
}

/* The 0x8437f4/0x92dc50 step: r1 flags, s0 the value. sub 0 passes -500.0, sub 1 0.0 and
 * sub 2 0.0 plus the 700.0 clamp, as 0x00690e28 and 0x00690f28 do. */
static void decel_sub(MH4UCall *call, uint32_t enemy, uint32_t work, int sub) {
    mhuc_call_f(call, FN_DECEL, enemy, 0u, 0u, 0u, sub == 0 ? -500.0f : 0.0f, 0.0f, NULL);
    if (sub == 2 && mhuc_f32(call, work + WORK_CLAMP_2) > 700.0f) {
        mhuc_put_f32(call, work + WORK_CLAMP_2, 700.0f);
    }
}

/* The state-1 step both 2/x units share: 0x8438e8(r1=0, r2=0x40), then 0/2's base handler
 * when it answers yes. */
static void tail_state_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    if (mhuc_call(call, FN_SETUP, enemy, 0u, 0x40u, 0u)) {
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* ── 0x00690e28: 2/0, 2/7, 2/9 and 2/11 ───────────────────────────────────────────── */

/* 3U 0x00690e28. The case blocks pass r1 = sub (0, 1, 2) and r2 = variant (1 only for
 * 2/11, which adds the 0x83d18c mark at the entry).
 *   0: state 1, mode 0, the sub's decel value, the request for motion 6 at speed 6.0;
 *   1: the 0x8438e8 test and, when it answers yes, 0/2's base handler. */
static void run_2_0_7_9_11(MH4UCall *call, uint32_t enemy, uint32_t work, int sub, int variant) {
    if (variant == 1) {
        mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
    }
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        decel_sub(call, enemy, work, sub);
        start_motion(call, enemy, M_0_06, 6.0f);
    } else if (state == 1) {
        tail_state_1(call, enemy, work);
    }
}

/* ── 0x00690f28: 2/3, 2/8 and 2/10 ─────────────────────────────────────────────────── */

/* 3U 0x00690f28. The case blocks pass r1 = sub (0, 1, 2).
 *   0: state 1, mode 0, the sub's decel value, the request for motion 7 at speed 10.0;
 *   1: the 0x8438e8 test and, when it answers yes, 0/2's base handler. */
static void run_2_3_8_10(MH4UCall *call, uint32_t enemy, uint32_t work, int sub) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        decel_sub(call, enemy, work, sub);
        start_motion(call, enemy, M_0_07, 10.0f);
    } else if (state == 1) {
        tail_state_1(call, enemy, work);
    }
}

/* ── 0x00687398: 2/4, 2/5, 2/6, 9/3 and 9/4 ───────────────────────────────────────── */

/* The five ids share one six-state handler. Unlike the other units its dispatch takes an
 * argument per id: r1 mode (0 for all five), r2 variant (0, 0, 0, 1, 3) and r3 the effect
 * flag (0 for 2/4-2/6, 1 for 9/3 and 9/4). 2/6 also runs 0x83d18c before the handler. */
static void run_2_4(MH4UCall *call, uint32_t enemy, uint32_t work, uint32_t mode, int variant,
                    int effect_flag) {
    (void)mode;
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0:
        /* work+5 = 1, mode 0, the request for motion 0xd6 at speed 4.0. */
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        start_motion(call, enemy, M_2_14, 4.0f);
        break;
    case 1:
        /* The source's 0x8357b0 call only runs for variants 2, 4 and 5, which none of these
         * five ids is. Then the finish flag, the next state, mode 3 and the sequence below. */
        if (variant == 2 || variant == 4 || variant == 5) {
            mhuc_call(call, FN_FORCE, enemy, 0x400u, 0u, 0u);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE,
                    (uint8_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        set_mode(call, enemy, 3u);
        mhuc_call_f(call, FN_SPEED, enemy, 0u, 0u, 0u, 50.0f, 0.0f, NULL);
        start_motion(call, enemy, M_2_15, 0.0f);
        mhuc_call(call, FN_DATA, enemy, 0u, 0u, 0u);
        /* 0x83c6e0's table pointer is the source's own data; the store it feeds (work+0x168)
         * and the 0x82cee4 step wait for it. The turn step is still the source's. */
        block_once(call, BLOCK_FLOAT_TABLE);
        mhuc_call_f(call, FN_POS, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        if (effect_flag == 1) {
            /* 0x829620(this, work+0x38, 0x64) and 0x257628's global step wait on #55. */
            block_once(call, BLOCK_PER_FRAME);
            block_once(call, BLOCK_TARGET_BYTE);
        }
        break;
    case 2:
        /* The source's effect branch (r2 = 1 or 3, 9/3 and 9/4) builds a point and a shell
         * through helpers that have no MH4U counterpart. The check before it is translated;
         * when it answers yes the effect setup is named and skipped, then the common tail
         * below always runs. */
        if (variant == 1 || variant == 3) {
            if (mhuc_call_f(call, FN_PER_MODE, enemy, 0u, 0u, 0u, 6.0f, 0.0f, NULL)) {
                block_once(call, BLOCK_EFFECT_SETUP);
            }
        }
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_write8(call, work + WORK_STATE,
                        (uint8_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
            mhuc_write8(call, work + WORK_SUB, 0u);
            mhuc_put_f32(call, work + WORK_FLOAT_178, 0.5f);
            mhuc_call_f(call, FN_TURN, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
            start_motion(call, enemy, M_0_1b, 6.0f);
        } else {
            block_once(call, BLOCK_FLOAT_TABLE);
            mhuc_call_f(call, FN_POS, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        }
        break;
    case 3:
        /* The turn step every frame, the clamp of work+0x168, then the finish flag. A non-zero
         * r1 goes to 0/6's base handler (2/5); the rest walks two sub-states. */
        mhuc_call_f(call, FN_TURN, enemy, work + WORK_TURN, 0u, 0u, 1.0f, 0.0f, NULL);
        if (mhuc_f32(call, work + WORK_FLOAT_168) > 0.0f) {
            mhuc_put_f32(call, work + WORK_FLOAT_168, 0.0f);
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        if (mode != 0) {
            if (mode == 1) {
                mhuc_3u_base_0_6(call, enemy, work);
            }
            return;
        }
        {
            const int sub = (int)mhuc_read8(call, work + WORK_SUB);
            if (sub == 0) {
                mhuc_write8(call, work + WORK_SUB, 1u);
                start_motion(call, enemy, M_0_1b, 0.0f);
            } else if (sub == 1) {
                mhuc_write8(call, work + WORK_STATE,
                            (uint8_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
                start_motion(call, enemy, M_2_16, 6.0f);
            }
        }
        break;
    case 4:
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint8_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        set_mode(call, enemy, 0u);
        start_motion(call, enemy, M_2_17, 0.0f);
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

/* ── the category-2 inline blocks: 2/1, 2/2, 2/12 and 2/13 ─────────────────────────── */

/* The four inline blocks share one shape. They set the state and mode, call 0x82d278 with a
 * pointer into the source's action data, and on the next state test the kind, apply 1.1
 * through 0x83cbfc and call 0x82d430 with the same pointer; when that answers yes they fall
 * into 0/2's base handler.
 *
 * The two data calls (0x82d278, 0x82d430) cannot be carried: their argument is a pointer into
 * MH3U's own data. The port names them once and skips them. The 0x82d430 guard then has no
 * value to test, and the port takes its continuation (0/2's base handler) so the action still
 * resolves instead of stalling; the code says so where it does it. */
static void run_inline_2(MH4UCall *call, uint32_t enemy, uint32_t work, int mark_entry,
                         int data_index, int sub_arg) {
    if (mark_entry) {
        mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
    }
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        /* 0x82d278(this, data, 0, sub_arg, 0) is the source's data setup. */
        (void)data_index;
        (void)sub_arg;
        block_once(call, BLOCK_PENDING_DATA);
    } else if (state == 1) {
        if (mhuc_read8(call, work + WORK_KIND) == 0x3fu) {
            mhuc_call_f(call, FN_APPLY, enemy, 0u, 0u, 0u, 1.1f, 0.0f, NULL);
        }
        /* 0x82d430(this, data) is the source's guard; without the data the port takes its
         * continuation, which is the base handler below. */
        block_once(call, BLOCK_ACTION_DATA);
        mhuc_3u_base_0_2(call, enemy, work);
    }
}

/* 3U 0x00699dbc (2/1): no entry mark, the 0xb0b068 data, sub-argument 0. */
static void run_2_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    run_inline_2(call, enemy, work, 0, 0, 0);
}

/* 3U 0x00699e3c (2/2): no entry mark, the 0xb0b0a8 data, sub-argument 1. */
static void run_2_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    run_inline_2(call, enemy, work, 0, 1, 1);
}

/* 3U 0x00699f78 (2/12): the 0x83d18c entry mark, the 0xb0b068 data, sub-argument 0. */
static void run_2_12(MH4UCall *call, uint32_t enemy, uint32_t work) {
    run_inline_2(call, enemy, work, 1, 0, 0);
}

/* 3U 0x00699fcc (2/13): the 0x83d18c entry mark, the 0xb0b0a8 data, then 0/2's base
 * handler. Its ledger handler is 0x0082d1cc, the base handler cat0.c exports. */
static void run_2_13(MH4UCall *call, uint32_t enemy, uint32_t work) {
    run_inline_2(call, enemy, work, 1, 1, 1);
}

/* ── 9/0, 9/1 and 9/2 ──────────────────────────────────────────────────────────────── */

/* 3U 0x00691020 (9/0).
 *   0: state 1, mode 0, the request for motion 0xca at speed 4.0;
 *   1: the finish flag, then the two #55 checks and the counter; when the counter is spent
 *      the kind picks 9/2 or 9/3, otherwise 9/1, or 2/6 when a check fails.
 * The 0x839598 and 0x84512c checks wait on #55, and the success path also needs her own
 * 0x687ae0 and 0x68d940. The port names the two checks once and takes the source's own
 * fallback, 2/6, which is translated here. */
static void run_9_0(MH4UCall *call, uint32_t enemy, uint32_t work) {
    block_once(call, BLOCK_ENTRY_MARK);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        set_mode(call, enemy, 0u);
        start_motion(call, enemy, M_2_02, 4.0f);
    } else if (state == 1) {
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            /* 9/0 advances the sub-state here without a motion request; only 9/1 asks for
             * 0xca. It then falls through into the checks in the same frame. */
            if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                return;
            }
            mhuc_write8(call, work + WORK_SUB, (uint8_t)(sub + 1));
        } else if (sub != 1) {
            return;
        }
        block_once(call, BLOCK_STATE_BYTE);
        block_once(call, BLOCK_HIT);
        /* The checks cannot answer, so the source's failure tail is taken. */
        mhuc_call(call, FN_REQUEST_NEXT, enemy, 2u, 6u, 0u);
    }
}

/* 3U 0x0069119c (9/1).
 *   0: state 1, mode 0, the request for 0xcb at speed 4.0, then the kind and the tail flag
 *      pick the 0x844a38 id (0x18-0x1a, or 0x27-0x29 when the kind is 0x3f);
 *   1: the finish flag, the request for 0xca, then the same two #55 checks as 9/0; on
 *      success it requests 9/0, otherwise 2/6. */
static void run_9_1(MH4UCall *call, uint32_t enemy, uint32_t work) {
    block_once(call, BLOCK_ENTRY_MARK);
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    if (state == 0) {
        mhuc_write8(call, work + WORK_STATE, 1u);
        mhuc_write8(call, work + WORK_SUB, 0u);
        set_mode(call, enemy, 0u);
        start_motion(call, enemy, M_2_03, 4.0f);
        {
            const int kind_3f = mhuc_read8(call, work + WORK_KIND) == 0x3fu;
            const int tail = (int)mhuc_read8(call, work + WORK_TAIL);
            if (kind_3f) {
                if (tail == 1) {
                    mhuc_call(call, FN_ACTION, enemy, 0u, 0x29u, 0u);
                } else if (tail == 2) {
                    mhuc_call(call, FN_ACTION, enemy, 0u, 0x28u, 0u);
                } else if (tail == 3) {
                    mhuc_call(call, FN_ACTION, enemy, 0u, 0x27u, 0u);
                }
            } else {
                if (tail == 1) {
                    mhuc_call(call, FN_ACTION, enemy, 0u, 0x1au, 0u);
                } else if (tail == 2) {
                    mhuc_call(call, FN_ACTION, enemy, 0u, 0x19u, 0u);
                } else if (tail == 3) {
                    mhuc_call(call, FN_ACTION, enemy, 0u, 0x18u, 0u);
                }
            }
        }
    } else if (state == 1) {
        const int sub = (int)mhuc_read8(call, work + WORK_SUB);
        if (sub == 0) {
            if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                return;
            }
            mhuc_write8(call, work + WORK_SUB, (uint8_t)(sub + 1));
            start_motion(call, enemy, M_2_02, 4.0f);
        } else if (sub != 1) {
            return;
        }
        block_once(call, BLOCK_STATE_BYTE);
        block_once(call, BLOCK_HIT);
        /* As 9/0: the checks cannot answer, so the source's failure tail is taken. */
        mhuc_call(call, FN_REQUEST_NEXT, enemy, 2u, 6u, 0u);
    }
}

/* 3U 0x00691384 (9/2), three states plus the base handler.
 *   0: state 1, mode 0, the request for 0xcd at speed 6.0;
 *   1: the finish flag, then 0x829620 (#55), the data float and the fall, the request for
 *      0xce, the two 0x844a38 ids, 0x839968, the two 0x83c6cc floats (#55) and 0x257628
 *      (#55);
 *   2: the per-monster float, the data float, the sub-state turn and the 0x83336c gate, then
 *      0x83369c, the finish flag, mode 0, the request for 0xcf and 0x838c28;
 *   3: the entry mark, the finish flag and 0/2's base handler. */
static void run_9_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
    const int state = (int)mhuc_read8(call, work + WORK_STATE);
    switch (state) {
    case 0:
        mhuc_write8(call, work + WORK_STATE, 1u);
        set_mode(call, enemy, 0u);
        start_motion(call, enemy, M_2_05, 6.0f);
        break;
    case 1:
        if (!mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            return;
        }
        mhuc_write8(call, work + WORK_STATE, (uint8_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
        mhuc_write8(call, work + WORK_SUB, 0u);
        block_once(call, BLOCK_PER_FRAME);
        {
            float data = 0.0f;
            mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &data);
            mhuc_call_f(call, FN_FALL, enemy, 0u, 0u, 0u, data, 0.0f, NULL);
        }
        start_motion(call, enemy, M_2_06, 0.0f);
        mhuc_call(call, FN_ACTION, enemy, 0u, 0x1cu, 0u);
        mhuc_call(call, FN_ACTION, enemy, 1u, 0x25u, 0u);
        mhuc_call(call, FN_DATA, enemy, 0u, 0u, 0u);
        block_once(call, BLOCK_FLOAT_GET);
        block_once(call, BLOCK_TARGET_BYTE);
        break;
    case 2:
        block_once(call, BLOCK_FLOAT_TABLE);
        {
            /* The source's 0x83c6e0 returns the float the branch works on; with its table
             * missing the branch's own value is the action data's float. */
            float s17 = 0.0f;
            mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0u, 0u, 0u, 0.0f, 0.0f, &s17);
            const int sub = (int)mhuc_read8(call, work + WORK_SUB);
            if (sub == 0) {
                mhuc_call_f(call, FN_TURN2, enemy, work + WORK_TURN, 0u, 0u, s17, 1.0f, NULL);
                /* 0x83336c's answer, or the negative per-frame float, advances the sub-state. */
                if (mhuc_call_f(call, FN_PER_MODE, enemy, 1u, 0u, 0u, 16.0f, 0.0f, NULL) != 0 ||
                    mhuc_f32(call, work + WORK_FLOAT_168) < 0.0f) {
                    mhuc_write8(call, work + WORK_SUB, (uint8_t)(sub + 1));
                    mhuc_put_f32(call, work + WORK_FLOAT_168, 0.0f);
                }
            } else if (sub == 1) {
                mhuc_call_f(call, FN_TURN2, enemy, work + WORK_TURN, 0u, 0u, s17, 1.0f, NULL);
            }
            if (mhuc_call_f(call, FN_GATE, enemy, 0u, 0u, 0u, s17, 0.0f, NULL)) {
                if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
                    mhuc_write8(call, work + WORK_STATE,
                                (uint8_t)(mhuc_read8(call, work + WORK_STATE) + 1u));
                    set_mode(call, enemy, 0u);
                    start_motion(call, enemy, M_2_07, 0.0f);
                    if (!mhuc_call(call, FN_MASK, enemy, 1u, 0u, 0u)) {
                        mhuc_call(call, FN_ACTION, enemy, 0u, 0x16u, 0u);
                    }
                    mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
                }
            }
        }
        break;
    case 3:
        mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
        if (mhuc_call(call, FN_FLAG, enemy, 0u, 0u, 0u)) {
            mhuc_3u_base_0_2(call, enemy, work);
        }
        break;
    default:
        break;
    }
}

/* ── the family's dispatch and self-test ───────────────────────────────────────────── */

/* Runs the pair's handler, or returns 0 so the module's dispatch can try the next family.
 * 2/5 is 0x00687398's variant with mode 0 and the effect flag off; 2/6 adds the 0x83d18c
 * mark at its case block. */
static int dispatch_cat2_9(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                           int index) {
    if (category == 2) {
        switch (index) {
        case 0: run_2_0_7_9_11(call, enemy, work, SUB_0, 0); return 1;
        case 1: run_2_1(call, enemy, work); return 1;
        case 2: run_2_2(call, enemy, work); return 1;
        case 3: run_2_3_8_10(call, enemy, work, SUB_0); return 1;
        case 4: run_2_4(call, enemy, work, 0u, VARIANT_2_4, 0); return 1;
        case 5: run_2_4(call, enemy, work, 1u, VARIANT_2_5, 0); return 1;
        case 6:
            mhuc_call(call, FN_MARK, enemy, 0u, 0u, 0u);
            run_2_4(call, enemy, work, 0u, 0, 0);
            return 1;
        case 7: run_2_0_7_9_11(call, enemy, work, SUB_1, 0); return 1;
        case 8: run_2_3_8_10(call, enemy, work, SUB_1); return 1;
        case 9: run_2_0_7_9_11(call, enemy, work, SUB_2, 0); return 1;
        case 10: run_2_3_8_10(call, enemy, work, SUB_2); return 1;
        case 11: run_2_0_7_9_11(call, enemy, work, SUB_0, 1); return 1;
        case 12: run_2_12(call, enemy, work); return 1;
        case 13: run_2_13(call, enemy, work); return 1;
        default: return 0;
        }
    }
    if (category == 9) {
        switch (index) {
        case 0: run_9_0(call, enemy, work); return 1;
        case 1: run_9_1(call, enemy, work); return 1;
        case 2: run_9_2(call, enemy, work); return 1;
        case 3: run_2_4(call, enemy, work, 0u, VARIANT_9_3, EFFECT_FLAG); return 1;
        case 4: run_2_4(call, enemy, work, 0u, VARIANT_9_4, EFFECT_FLAG); return 1;
        default: return 0;
        }
    }
    return 0;
}

/* The family's self-test lines, run with the others' on the first frame when the setting
 * asks for it. */
static void self_test_cat2_9(MH4UCall *call) {
    (void)call;
    mhuc_log(MH4U_LOG_INFO,
             "selftest: 19 of the 191 actions: category 2's 2/0, 2/7, 2/9 and 2/11 <- "
             "0x00690e28 (mode 0, the sub's -500/0/700 clamp, motion 6 at 6.0, the 0x8438e8 "
             "test into 0/2); 2/3, 2/8 and 2/10 <- 0x00690f28 (the same steps, motion 7 at "
             "10.0); 2/4, 2/5, 2/6, 9/3 and 9/4 <- 0x00687398 (six states, motions 0xd6, 0xd7, "
             "0x1b, 0xd8 and 0xd9); 2/1 <- 0x00699dbc, 2/2 <- 0x00699e3c, 2/12 <- 0x00699f78 "
             "and 2/13 <- 0x00699fcc (the inline data setup, then 0/2's base handler); 9/0 <- "
             "0x00691020, 9/1 <- 0x0069119c and 9/2 <- 0x00691384 (motions 0xca-0xcf)");
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: the engine calls are MH4U's: mode 0x%08x, motion 0x%08x, flag 0x%08x, "
              "decel 0x%08x, setup 0x%08x, mark 0x%08x, float 0x%08x, turn 0x%08x, per-mode "
              "0x%08x, action 0x%08x, next 0x%08x",
              (unsigned)FN_MODE, (unsigned)FN_MOTION, (unsigned)FN_FLAG, (unsigned)FN_DECEL,
              (unsigned)FN_SETUP, (unsigned)FN_MARK, (unsigned)FN_FLOAT, (unsigned)FN_TURN,
              (unsigned)FN_PER_MODE, (unsigned)FN_ACTION, (unsigned)FN_REQUEST_NEXT);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: field map anchors: +0x5 -> +0x144, +0x6 -> +0x145, +0xdc -> +0x1c8, "
             "+0x3 -> +0x1c0, +0x2a8 -> +0x238, +0x268 -> +0x168, +0x278 -> +0x178, +0x80 -> "
             "+0x1a8, +0x38 -> +0x198, +0x2b6 -> +0x278, +0xe1 -> +0x7993");
    mhuc_log(MH4U_LOG_INFO,
             "selftest: blocked: 0x00853c70, 0x00839598, 0x0084512c, 0x00829620 and "
             "0x00257628 (#55); 0x0083c6cc (#55); 0x0083c6e0's, 0x0082d430's and 0x0082d278's "
             "source data; 9/3 and 9/4's effect setup (0x00688a20/0x00688870)");
}

/* The family file's one export: src/monsters/rathian-3u.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_3u_family_cat2_9 = {
    "cat2_9", 19, dispatch_cat2_9, self_test_cat2_9,
};
