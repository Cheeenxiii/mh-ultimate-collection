/*
 * rathian_gu.c: GU Rathian's MHXX-only actions, run on MH4U's uEnemy.
 *
 * GU Rathian (MHXX v1.4, roEm001) has 13 action ids MH4U has no action for:
 * 3/98, 4/27 to 4/32, 8/0, 12/0 to 12/3 and category 17. This module carries the twelve that
 * need new C: 3/98 with the 12/1 to 12/3 chain around it, the six 4/27 to 4/32 ids that share
 * handler 0x0200e3b4, 8/0 with its combo tail, and category 17. 12/0 needs nothing: MH4U's own
 * category-12 case checks index 0 and runs its own handler 0x006d524c, the handler its shared
 * 3/2, 3/83 etc. use and the role pair of MHXX's 12/0. Under decision 0002's 2026-11-26
 * amendment her own handler for the shared ids is still owed; this step only moves the
 * translated actions, so 12/0 and the shared ids stay with the game for now.
 *
 * This is the module src/module.h describes: the runtime records the enemy that spawned as
 * the registry id (124, data/ids/registry.csv) and calls this file's dispatch for it, and
 * every other monster goes to the game's dispatcher. The code moved here from
 * mods/rathian_actions without a new translation: same handlers, frame values, work-block
 * offsets, log lines and settings. The engine calls now go through the runtime's ABI 4
 * helpers (mhuc_call / mhuc_call_f) instead of the old plugin's own guest stubs; the two calls
 * ABI 4 cannot make keep a guest stub, provided by the runtime (mhuc_read_s, mhuc_call_s2).
 *
 * Category 17 is a gate plus a base-class update, not a per-index handler. MHXX's case
 * (0x020098b8) jumps to 0x008d5bd4, which reads the index byte at this+0x6bf1: 0 to 2 return,
 * any other index tail-calls uEnemy's vtable slot 0x3d0 (0x008ae50c). MH4U's uEnemy has 95
 * slots and no 244, but its slot 89 (0x00911b48) is the same routine on MH4U's layout: the
 * module calls it, and for 0 to 2 does nothing.
 *
 * 8/0 translates almost call for call onto MH4U's own 8/0 handler (0x006e9770), which is the
 * same action with the same frame values: MH4U's category-8 case runs it. The engine calls
 * below are the same functions the MH4U handler calls at the same points, and the work-block
 * fields are MH4U's, so the two bodies can be read side by side. The exceptions are recorded
 * in the runtime's README.
 *
 * Floats: the runtime's helpers set the VFP registers through ABI 4's call2; the old plugin's
 * per-call guest stubs are gone, except for the caller's s0-s3 (which a hook still cannot
 * read) and 8/0's three-float hit check (s2 has no ABI 4 argument). The runtime keeps those
 * stubs once for every module.
 *
 * Settings (the runtime's mod.json "config", the player's config.ini over it):
 *   monster   the id the ready line names; the module answers the registry id it was built for
 *   selftest  "1": log what this module translates and what is still pending
 *
 * Licence: GPL-3.0-or-later.
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../module.h"

/* uEnemy's work block and the fields this slice reads (USA v1.3.0). MHXX's work block is
 * at this+0x10a8 and its +0x44/+0x1d0 are MH4U's +0x19c/+0x218. */
#define WORK_CATEGORY 0x01cau
#define WORK_INDEX    0x01cbu
#define WORK_Y        0x019cu
#define WORK_TARGET   0x0218u

/* MH4U engine functions this slice calls, and the MHXX function each stands for. */
#define FN_DATA_FLOAT  0x0093d870u  /* 0x008d21ac: the data value at the monster's entry */
#define FN_APPLY_FALL  0x0092e99cu  /* 0x008b1698: advance the fall by s0 */
#define FN_FALL_SNAP   0x0094a45cu  /* 0x008e192c: snap the fall to a target height */
#define FN_APPLY_RATE  0x0093ce60u  /* 0x008d1a0c: advance the fall by the frame's rate */
#define FN_SET_SPEED   0x00941d84u  /* 0x008d73e8: set a speed (s0) and its flag */
#define FN_FLAG        0x00b05da4u  /* 0x00aed11c: the action's finish flag */
#define FN_IDLE        0x0094dc84u  /* 0x008eb050: return to idle, 0/3 mode 2 */
#define FN_MOTION      0x0094e318u  /* 0x008eb108: start a motion (index r1, s0/s1) */
#define FN_HANDLER_3_9 0x006d5e98u  /* 0x02010aec, MH4U's shared 3/9 handler (also 3/5) */
#define FN_HANDLER_3_12 0x006d791cu /* 0x0201041c, MH4U's shared 3/12 handler */
/* MH4U's uEnemy vtable slot 89, the same routine as MHXX's slot 0x3d0 (0x008ae50c):
 * 0x008b1700->0x009167b4, 0x00add004->0x0092e960, 0x008ac5a0 (the action setter)
 * ->0x0090ef74, and the finish flag this+0x6b00->work+0x1dc. It is category 17's base update
 * and the 4/27-32 finish flag's end-of-action. */
#define FN_BASE_UPDATE 0x00911b48u

/* 8/0's engine calls, each the MH4U function MH4U's own 8/0 handler (0x006e9770) calls
 * at the same point (the source address in the comment). Its data entry and per-mode check
 * are the 4/27-32 slice's FN_MODE and FN_MODE_CLEAR below. */
#define FN_MOVE_TO      0x00948674u  /* 0x008df28c: zero a velocity, aim at a point (s0, s1) */
#define FN_APPLY_MOVE   0x00955440u  /* 0x008f1f30: advance the position by the velocity */
#define FN_COUNTDOWN    0x00b0704cu  /* 0x008a78ec: count a float down by the frame rate */
#define FN_HIT_CHECK    0x009122fcu  /* 0x008ae8ec: hit check, three floats (s0-s2) */
#define FN_HIT_CHECK_R3 0x0092b2b0u  /* 0x008c024c: hit check, mode in r3 */
#define FN_REQUEST_NEXT 0x0094ef64u  /* 0x008ebab0: request the next action (category, index) */
#define FN_TAIL_DATA    0x0092f6e8u  /* 0x008c4184: the leaf, with its data table in r1 */

/* The motions 3/98 starts. 0x101 runs with s0 = 6.0, s1 = 0.0; 0x104 with s0 = 2.0 (the
 * source leaves s1 from the previous state, which is 0.0 while the move is current). */
#define MOTION_A MHUC_MOTION(1, 0x01)
#define MOTION_B MHUC_MOTION(1, 0x04)

/* ── the 4/27 to 4/32 slice: handler 0x0200e3b4, three states ────────────────────────
 * The six ids' case blocks (0x02018af8 to 0x02018bac) pass r1/r2 to the shared handler:
 * 4/27 2/0, 4/28 1/0, 4/29 2/1, 4/30 1/1, 4/31 2/0, 4/32 1/0. r1 picks the pair of sides
 * (mode 1 or 2) and r2 picks the ending: 0 waits for the finish flag and calls MHXX's
 * end-of-action (vtable slot 244), 1 starts the last motion and requests action 7/246 or
 * 7/247. Each case block also calls 0x00adb528 with 2, 2, 3, 3, 5, 5 (method 0x4c of the
 * object at this+0x6dc4); MH4U has no counterpart for it, so that call is not translated. */

/* MH4U's work block is *(this+0xe28), MHXX's is *(this+0x10a8). The fields this slice
 * reads, MHXX -> MH4U, each confirmed by a paired function (see the runtime README's table):
 *   position x,y,z     +0x40/+0x44/+0x48 -> +0x198/+0x19c/+0x1a0
 *   position w         +0x4c             -> +0x1a4
 *   heading            +0x54             -> +0x1ac
 *   target point x,z   +0x1d0/+0x1d8     -> +0x218/+0x220
 *   heading saved      +0x200            -> +0x248
 *   speed (this)       +0x298            -> +0x290
 *   turn scale (this)  +0x1c             -> +0x14
 * The target-line struct *(this+0x8d88) (MHXX *(this+0xb770)) keeps the same layout in
 * both games: origin x,z at +0x30/+0x38, direction x,y,z,w at +0x40 to +0x4c. */
#define ENEMY_TARGET_LINE 0x08d88u
#define ENEMY_SPEED       0x0290u
#define ENEMY_TURN_SCALE  0x0014u
#define WORK_POS          0x0198u
#define WORK_POS_W        0x01a4u
#define WORK_HEADING      0x01acu
#define WORK_SAVED_HEADING 0x0248u
#define LINE_ORIGIN       0x0030u
#define LINE_DIR          0x0040u

/* 8/0's fields, at the offsets MH4U's own 8/0 handler (0x006e9770) uses for the same
 * fields: its state 2 counts down work+0x1d4, reads the pending-action mode at work+0x1d9,
 * and hands the two bytes at +0x278/+0x27c to the hit checks. */
#define WORK_TIMER       0x01d4u
#define WORK_PENDING     0x01d9u
#define WORK_BYTE_A      0x0278u
#define WORK_BYTE_B      0x027cu
#define WORK_VELOCITY    0x0160u
#define WORK_FLAG_ZERO_A 0x7738u
#define WORK_FLAG_ZERO_B 0x7739u
#define WORK_FLAG_MODE   0x7a3cu
#define WORK_FLAG_TAIL   0x7993u

/* The handler's engine calls, MH4U address <- MHXX address (the MHXX one in brackets). */
#define FN_FLIGHT_SETUP 0x006e7be8u  /* [0x0201262c] the flight's setup, from the height data */
#define FN_MODE         0x009167b4u  /* [0x008b1700] set the monster's mode (0, 1, 2, 3, 5, 6) */
#define FN_TURN         0x00917570u  /* [0x008b2210] turn by an angle step, s0/s1 the speed range */
#define FN_MODE_CLEAR   0x0091aae4u  /* [0x008a7360] the flag-clear wrapper around 0x00b06b4c */
#define FN_TARGET_POINT 0x0092d09cu  /* [0x008c21f8] build a target point from an index */
#define FN_TURN_TO      0x0091db4cu  /* [0x008b75d8] turn toward a target point, at a step in r3 */
#define FN_LINE_POINT   0x006e5608u  /* [0x020063fc] a point on the target line at a fraction */
#define FN_ROTATE       0x00aad55cu  /* [0x0201277c] rotate a direction by an angle */

/* The motions the six start: r1 = 1 (mode 1) or 2 (mode 2) selects the side. */
#define MOTION_TAKEOFF_1 MHUC_MOTION(4, 0x17)  /* state 0, s0 = 6.0 */
#define MOTION_TAKEOFF_2 MHUC_MOTION(4, 0x18)  /* state 0, s0 = 6.0 */
#define MOTION_FLY_1     MHUC_MOTION(9, 0x09)  /* state 1, s0 = 0.0 */
#define MOTION_FLY_2     MHUC_MOTION(9, 0x0a)  /* state 1, s0 = 0.0 */
#define MOTION_END_1     MHUC_MOTION(9, 0x0d)  /* state 2, variant 1, s0 = 2.0 */
#define MOTION_END_2     MHUC_MOTION(9, 0x0b)  /* state 2, variant 1, s0 = 2.0 */
#define PENDING_ACTION_1 0xf6u  /* the action 4/30 requests next: 7/246 */
#define PENDING_ACTION_2 0xf7u  /* the action 4/29 requests next: 7/247 */

/* 8/0's motion and its frame values (the same constants MH4U's own 8/0 handler passes). */
#define MOTION_8_0 MHUC_MOTION(4, 0x03)

/* The turn steps 0x008b75d8 takes in r1: the slow one when the mode-clear call succeeded,
 * the fast one when it did not. */
#define TURN_STEP_SLOW 0x1c7u
#define TURN_STEP_FAST 0x00b6u

static uint32_t bits_of(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

static float f32_of(uint32_t bits) {
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

/* The source's `vcvt.u32.f32` saturates: a negative is 0, anything past 2^32 is all ones. */
static uint32_t f32_to_u8(float value) {
    if (!(value > 0.0f)) {
        return 0;
    }
    if (value >= 4294967296.0f) {
        return 0xffu;
    }
    return (uint32_t)value & 0xffu;
}

/* ── the translated handlers ────────────────────────────────────────────────────────── */

static int action_logged;

static void log_action_once(int category, int index) {
    if (action_logged) {
        return;
    }
    action_logged = 1;
    mhuc_logf(MH4U_LOG_INFO, "running the translated action %d/%d", category, index);
}

/* Category 17: one line per index, whether the gate's 0-2 no-op or the base update. The
 * module has no per-monster state to keep here, and the first line is the evidence that the
 * forced index reached the translation. */
static uint8_t cat17_logged[256];
static void log_cat17_once(int index) {
    if (cat17_logged[index]) {
        return;
    }
    cat17_logged[index] = 1;
    if (index <= 2) {
        mhuc_logf(MH4U_LOG_INFO, "17/%d: nothing (the gate returns for 0 to 2)", index);
    } else {
        mhuc_logf(MH4U_LOG_INFO, "17/%d: running MH4U's base action update 0x%08x", index,
                  (unsigned)FN_BASE_UPDATE);
    }
}

/* MHXX 3/98, handler 0x020062d4: three states.
 *   0: remember the data float, advance the fall by it, start motion 0x101 at 6.0, snap
 *      the fall to the target height;
 *   1: advance the fall by the frame's rate, stop when the position reaches the target
 *      height, set the speed 2.0, start motion 0x104;
 *   2: wait for the finish flag, then return to idle. */
static void run_3_98(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    switch (st->state) {
    case 0: {
        st->state = 1;
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0, 0, 0, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0, 0, 0, data, 0.0f, NULL);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_A, 0, 0, 6.0f, 0.0f, NULL);
        const uint32_t target_y = mhuc_read32(call, work + WORK_TARGET + 4u);
        mhuc_call_f(call, FN_FALL_SNAP, enemy, 0, 0, 0, f32_of(target_y), 0.0f, NULL);
        break;
    }
    case 1: {
        mhuc_call(call, FN_APPLY_RATE, enemy, 0, 0, 0);
        const float y = mhuc_f32(call, work + WORK_Y);
        const uint32_t target_y = mhuc_read32(call, work + WORK_TARGET + 4u);
        if (y > f32_of(target_y)) {
            return;
        }
        mhuc_write32(call, work + WORK_Y, target_y);
        if (!mhuc_call_f(call, FN_SET_SPEED, enemy, 0, 0, 0, 2.0f, 0.0f, NULL)) {
            return;
        }
        st->state = 2;
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_B, 0, 0, 2.0f, 0.0f, NULL);
        break;
    }
    default: {
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        mhuc_call(call, FN_IDLE, enemy, 0, 0, 0);
        break;
    }
    }
}

/* MHXX 12/1, block 0x0201c1d0: fixed target points (the fourth is the caller's s1), then
 * the 3/98 handler; when the action has returned to idle it requests 12/2. The request
 * helper (0x008ebab0) is not translated: MH4U has neither its work-block bytes nor its
 * pending-action queue, so the chain stops after this move instead of following on. */
static int request_logged[4];

static void run_12_1(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    mhuc_write32(call, work + WORK_TARGET + 0x0u, bits_of(5477.0f));
    mhuc_write32(call, work + WORK_TARGET + 0x4u, bits_of(3000.0f));
    mhuc_write32(call, work + WORK_TARGET + 0x8u, bits_of(4892.0f));
    mhuc_write32(call, work + WORK_TARGET + 0xcu, mhuc_read_s(call, 1));
    run_3_98(call, enemy, work, st);
    if (mhuc_read8(call, work + WORK_CATEGORY) == 0 && !request_logged[1]) {
        request_logged[1] = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "12/1: the source now requests 12/2 through 0x008ebab0; that helper is not "
                 "translated, so the move returns to idle instead");
    }
}

/* MHXX 12/2, block 0x0201c228: target points from the caller's s0-s3, MH4U's shared 3/12
 * handler (MHXX 0x0201041c), then a request for 12/3 after category 3 index 11. The request
 * is not translated, as for 12/1. */
static void run_12_2(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    (void)st;
    mhuc_write32(call, work + WORK_TARGET + 0x0u, mhuc_read_s(call, 0));
    mhuc_write32(call, work + WORK_TARGET + 0xcu, mhuc_read_s(call, 1));
    mhuc_write32(call, work + WORK_TARGET + 0x4u, mhuc_read_s(call, 2));
    mhuc_write32(call, work + WORK_TARGET + 0x8u, mhuc_read_s(call, 3));
    mhuc_call(call, FN_HANDLER_3_12, enemy, 0, 0, 0);
    if (mhuc_read8(call, work + WORK_CATEGORY) == 3 &&
        mhuc_read8(call, work + WORK_INDEX) == 0x0b && !request_logged[2]) {
        request_logged[2] = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "12/2: the source now requests 12/3 through 0x008ebab0; that helper is not "
                 "translated, so the move returns to idle instead");
    }
}

/* MHXX 12/3, block 0x0201c27c: target points from the caller's s0-s3, then MHXX's 3/5/3/9
 * unit (0x02010aec). MH4U's own 3/9 handler is the pair, with the same r1=1, r2=0. */
static void run_12_3(MH4UCall *call, uint32_t enemy, uint32_t work) {
    mhuc_write32(call, work + WORK_TARGET + 0x0u, mhuc_read_s(call, 0));
    mhuc_write32(call, work + WORK_TARGET + 0xcu, mhuc_read_s(call, 1));
    mhuc_write32(call, work + WORK_TARGET + 0x4u, mhuc_read_s(call, 2));
    mhuc_write32(call, work + WORK_TARGET + 0x8u, mhuc_read_s(call, 3));
    mhuc_call(call, FN_HANDLER_3_9, enemy, 1, 0, 0);
}

/* MHXX 4/27-32, handler 0x0200e3b4: three states, one state per frame.
 *   mode is the case block's r1 (1 or 2), variant its r2 (0 or 1), and s20 the handler's
 *   incoming s0.
 *   state 0: the flight setup, mode 3, the target line built from the position and the target
 *            point and rotated 90 degrees, motion 0x417/0x418 at 6.0, and the heading saved;
 *   state 1: build target point 0, speed/88, the mode-clear call at 78.0 and a turn toward
 *            the target at the slow or fast step, a point on the line at (s20 * 0.01) percent,
 *            one step of 10 * (this+0x14) toward it, the mode-clear call at 2.0, then the
 *            flight motion 0x909/0x90a at 0.0;
 *   state 2: a turn by +-0x2000 at 2.0..10.0; variant 0 waits for the finish flag and then
 *            calls MH4U's end-of-action, variant 1 makes the mode-clear call at 30.0, starts
 *            motion 0x90b/0x90d at 2.0 and requests action 7/247 or 7/246.
 *
 * The source's case blocks call 0x00adb528 (the object at this+0x6dc4, method 0x4c) before
 * the handler, and its state-2 request goes through 0x008ebab0. MH4U has neither object nor
 * queue, so both are left out and logged once per action. */
static int precall_logged, pending_logged;

static void log_precall_once(int index) {
    const unsigned bit = 1u << (unsigned)(index - 27);
    if (precall_logged & (int)bit) {
        return;
    }
    precall_logged |= (int)bit;
    mhuc_logf(MH4U_LOG_INFO,
              "4/%d: the source's case block calls 0x00adb528 (an object MH4U lacks) before the "
              "handler; it is not translated", index);
}

static void log_pending_once(int index) {
    if (pending_logged) {
        return;
    }
    pending_logged = 1;
    mhuc_logf(MH4U_LOG_INFO,
              "4/%d: the source now requests action 7/%d through 0x008ebab0; that helper is not "
              "translated", index, index == 30 ? (int)PENDING_ACTION_1 : (int)PENDING_ACTION_2);
}

static void run_4_27(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st,
                     int index, int mode, int variant, uint32_t s0arg) {
    switch (st->state) {
    case 0: {
        st->state = 1;
        mhuc_call(call, FN_FLIGHT_SETUP, enemy, 0, 0, 0);
        mhuc_call(call, FN_MODE, enemy, 3, 0, 0);
        const uint32_t line = mhuc_object(call, enemy, ENEMY_TARGET_LINE);
        if (line) {
            const float px = mhuc_f32(call, work + WORK_POS);
            const float pz = mhuc_f32(call, work + WORK_POS + 8u);
            const float tx = mhuc_f32(call, work + WORK_TARGET);
            const float tz = mhuc_f32(call, work + WORK_TARGET + 8u);
            mhuc_write32(call, line + LINE_ORIGIN, bits_of(px));
            mhuc_write32(call, line + LINE_ORIGIN + 8u, bits_of(pz));
            float vx = tx - px;
            float vy = mhuc_f32(call, line + LINE_DIR + 4u);
            float vz = tz - pz;
            const float len = sqrtf(vx * vx + vy * vy + vz * vz);
            if (len >= 1.1920929e-07f) {
                vx /= len;
                vy /= len;
                vz /= len;
            }
            mhuc_write32(call, line + LINE_DIR, bits_of(vx));
            mhuc_write32(call, line + LINE_DIR + 4u, bits_of(vy));
            mhuc_write32(call, line + LINE_DIR + 8u, bits_of(vz));
            mhuc_write32(call, line + LINE_DIR + 0xcu, 0);
            mhuc_call(call, FN_ROTATE, line + LINE_DIR, mode == 1 ? 0x4000u : 0xc001u, 0, 0);
        }
        mhuc_call_f(call, FN_MOTION, enemy,
                    mode == 1 ? MOTION_TAKEOFF_1 : MOTION_TAKEOFF_2, 0, 0, 6.0f, 0.0f, NULL);
        mhuc_write32(call, work + WORK_SAVED_HEADING, mhuc_read32(call, work + WORK_HEADING));
        break;
    }
    case 1: {
        const uint32_t offset = mode == 1 ? 0x2000u : 0xe001u;
        mhuc_call(call, FN_FLIGHT_SETUP, enemy, 0, 0, 0);
        mhuc_call(call, FN_TARGET_POINT, enemy, 0, 0, 0);
        const float speed = mhuc_f32(call, enemy + ENEMY_SPEED);
        const uint32_t fraction = f32_to_u8(f32_of(s0arg) * 0.01f);
        if (mhuc_call_f(call, FN_MODE_CLEAR, enemy, 2, 0, 0, 78.0f, 0.0f, NULL)) {
            mhuc_call(call, FN_TURN_TO, enemy, TURN_STEP_SLOW, offset, 0);
        } else {
            mhuc_call(call, FN_TURN_TO, enemy, TURN_STEP_FAST, offset, 0);
        }
        const uint32_t scratch = mhuc_scratch(call);
        if (!scratch) {
            return;
        }
        mhuc_call_f(call, FN_LINE_POINT, enemy, scratch, fraction, 0, speed / 88.0f, 0.0f, NULL);
        const float ox = mhuc_f32(call, scratch);
        const float oy = mhuc_f32(call, scratch + 4u);
        const float oz = mhuc_f32(call, scratch + 8u);
        const float px = mhuc_f32(call, work + WORK_POS);
        const float py = mhuc_f32(call, work + WORK_POS + 4u);
        const float pz = mhuc_f32(call, work + WORK_POS + 8u);
        const float dx = ox - px;
        const float dz = oz - pz;
        const float dist = sqrtf(dx * dx + dz * dz);
        const float scale = mhuc_f32(call, enemy + ENEMY_TURN_SCALE);
        float nx = ox, ny = oy, nz = oz;
        if (!(scale * 75.0f >= dist)) {
            float mx = ox - px, my = oy - py, mz = oz - pz;
            const float len = sqrtf(mx * mx + my * my + mz * mz);
            if (len >= 1.1920929e-07f) {
                mx /= len;
                my /= len;
                mz /= len;
            }
            nx = px + mx * 10.0f * scale;
            ny = py + my * 10.0f * scale;
            nz = pz + mz * 10.0f * scale;
        }
        mhuc_put_f32(call, work + WORK_POS, nx);
        mhuc_put_f32(call, work + WORK_POS + 4u, ny);
        mhuc_put_f32(call, work + WORK_POS + 8u, nz);
        mhuc_write32(call, work + WORK_POS_W, 0);
        if (!mhuc_call_f(call, FN_MODE_CLEAR, enemy, 1, 0, 0, 2.0f, 0.0f, NULL)) {
            return;
        }
        st->state = 2;
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        mhuc_call_f(call, FN_MOTION, enemy, mode == 1 ? MOTION_FLY_1 : MOTION_FLY_2, 0, 0,
                    0.0f, 0.0f, NULL);
        break;
    }
    default: {
        if (mode == 1) {
            mhuc_call_f(call, FN_TURN, enemy, 0xffffe000u, 0, 0, 2.0f, 10.0f, NULL);
        } else {
            mhuc_call_f(call, FN_TURN, enemy, 0x2000u, 0, 0, 2.0f, 10.0f, NULL);
        }
        if (!variant) {
            if (mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
                mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
            }
            break;
        }
        if (!mhuc_call_f(call, FN_MODE_CLEAR, enemy, 1, 0, 0, 30.0f, 0.0f, NULL)) {
            return;
        }
        st->state = 3;
        mhuc_call_f(call, FN_MOTION, enemy, mode == 1 ? MOTION_END_1 : MOTION_END_2, 0, 0,
                    2.0f, 0.0f, NULL);
        log_pending_once(index);
        break;
    }
    }
}

/* MHXX 8/0, handler 0x0201b460: the same action as MH4U's own 8/0 handler 0x006e9770,
 * with the same frame values. Three states.
 *   0: set up; copy the monster's data entry (mode 0), aim at the target at 300.0/38.0;
 *   1: per-mode speed/distance at 12.0/50.0; when it holds, advance the position by the
 *      velocity; wait for the finish flag, start motion 0x403 at 4.0 and arm the 180.0
 *      timer;
 *   2: count the timer down by the frame rate; when the pending-action mode is 1, run the
 *      two hit checks (300.0/0.0/150.0) and request 9/1, or request 2/6 when they fail,
 *      the timer is over, or the fallback check is 0.
 * The calls and work offsets are the ones MH4U's own handler uses (0x006e9770), which is
 * why each has an MH4U counterpart; the four gaps are in the runtime README. */
static int gap_logged;

static void run_8_0(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    if (!gap_logged) {
        gap_logged = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "8/0: 0x008c4184 is MH4U's 0x0092f6e8, but its MHXX table 0x20220ac is "
                 "not carried yet; 0x008d0528 and the 0x8ae5e4 data setup wait on #134");
    }
    /* The stores MHXX's handler makes every frame; MH4U's own 8/0 handler clears the same
     * fields at MH4U's offsets before its state switch. */
    mhuc_write8(call, work + WORK_FLAG_ZERO_A, 0);
    mhuc_write8(call, work + WORK_FLAG_ZERO_B, 0);
    mhuc_write8(call, work + WORK_FLAG_MODE, 2);
    switch (st->state) {
    case 0: {
        st->state = 1;
        mhuc_call(call, FN_MODE, enemy, 0, 0, 0);
        /* 0x008ae5e4 (MH4U 0x00911c0c) takes its 4th and 5th arguments in r3 and on the
         * stack, which ABI 4 cannot set: it waits on #134. */
        mhuc_call_f(call, FN_MOVE_TO, enemy, work + WORK_VELOCITY, work + WORK_TARGET, 0,
                    300.0f, 38.0f, NULL);
        break;
    }
    case 1: {
        if (mhuc_call_f(call, FN_MODE_CLEAR, enemy, 3, 0, 0, 12.0f, 50.0f, NULL)) {
            mhuc_call(call, FN_APPLY_MOVE, enemy, 0, 0, 0);
            /* 0x008c4184's counterpart is MH4U's 0x0092f6e8, but its table (MHXX's
             * 0x20220ac, MH4U's 0x00e094d8) is the port's data, not carried yet. */
        }
        if (!mhuc_call(call, FN_FLAG, enemy, 0, 0, 0)) {
            return;
        }
        st->state = 2;
        mhuc_write32(call, work + WORK_TIMER, bits_of(180.0f));
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_8_0, 0, 0, 4.0f, 0.0f, NULL);
        break;
    }
    default: {
        mhuc_call(call, FN_COUNTDOWN, enemy, work + WORK_TIMER, 0, 0);
        if (mhuc_read8(call, work + WORK_PENDING) != 1) {
            return;
        }
        const uint32_t a = mhuc_read8(call, work + WORK_BYTE_A);
        const uint32_t b = mhuc_read8(call, work + WORK_BYTE_B);
        if (!mhuc_call_s2(call, FN_HIT_CHECK, enemy, b, a, 300.0f, 0.0f, 150.0f)) {
            goto timer_check;
        }
        if (!mhuc_call(call, FN_HIT_CHECK_R3, enemy, 1, b, a)) {
            goto timer_check;
        }
        /* MHXX keeps a value of 1 when two enemy bytes are 2/4; the MH4U handler has no
         * such branch, so the port takes the source's other path. 0x008d0528 has no
         * confirmed MH4U counterpart and is not called. */
        mhuc_write8(call, work + WORK_FLAG_TAIL, 3);
        mhuc_call(call, FN_REQUEST_NEXT, enemy, 9, 1, 0);
        return;
    timer_check:
        if (!(mhuc_f32(call, work + WORK_TIMER) > 0.0f)) {
            mhuc_call(call, FN_REQUEST_NEXT, enemy, 2, 6, 0);
            return;
        }
        if (mhuc_call(call, FN_HIT_CHECK_R3, enemy, 0, b, a)) {
            return;
        }
        mhuc_call(call, FN_REQUEST_NEXT, enemy, 2, 6, 0);
        break;
    }
    }
}

/* ── the dispatch entry and the module's hooks ────────────────────────────────────────── */

/* Called for every action of the monster the runtime recorded as this module's registry id.
 * Read the pair, run the handler the module carries, and return 1; return 0 for a pair that
 * stays with the game (a shared id, 12/0, category 17 has its own path). */
static int dispatch(MH4UCall *call, uint32_t enemy) {
    const uint32_t work = mhuc_work(call, enemy);
    if (!work) {
        return 0;
    }
    const int category = mhuc_category(call, work);
    const int index = mhuc_index(call, work);
    /* Category 17 is the gate first: MHXX's dispatcher case (0x020098b8) jumps to
     * 0x008d5bd4, which reads the index (this+0x6bf1 there, MH4U's work+0x1cb here), returns
     * for 0 to 2 and otherwise tail-calls uEnemy's slot 0x3d0 (0x008ae50c). MH4U has no such
     * slot; its slot 89 (0x00911b48) is the same routine and runs the ported action. */
    if (category == 17) {
        if (index > 2) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        log_cat17_once(index);
        return 1;
    }
    /* 4/27-32 land on 127-132 so that no other slice's id can take their place. */
    const int which = (category == 3 && index == 98) ? 98
                    : (category == 12 && index >= 1 && index <= 3) ? index
                    : (category == 4 && index >= 27 && index <= 32) ? 100 + index
                    : (category == 8 && index == 0) ? 80
                    : -1;
    if (which < 0 || !mhuc_stubs(call)) {
        return 0;
    }
    int changed = 0;
    MhucState *st = mhuc_state(call, enemy, category, index, &changed);
    if (!st) {
        return 0;
    }
    if (changed) {
        action_logged = 0;
        log_action_once(category, index);
    }
    if (which >= 127) {
        /* 4/27-32: r1 = 2 on the odd ids, 1 on the even ones; r2 = 1 on 4/29 and 4/30. */
        const int mode = (index % 2 == 0) ? 1 : 2;
        const int variant = (index == 29 || index == 30) ? 1 : 0;
        log_precall_once(index);
        run_4_27(call, enemy, work, st, index, mode, variant, mhuc_read_s(call, 0));
    } else {
        switch (which) {
        case 98: run_3_98(call, enemy, work, st); break;
        case 1: run_12_1(call, enemy, work, st); break;
        case 2: run_12_2(call, enemy, work, st); break;
        case 3: run_12_3(call, enemy, work); break;
        default: run_8_0(call, enemy, work, st); break;
        }
    }
    return 1;
}

/* The module's ready line, at init: the same line the old plugin logged. The setting's id is
 * what the line names; the module answers its registry id whatever it says (the runtime warns
 * when the setting names no module). */
static void start(void) {
    int monster_id = (int)MHUC_MONSTER_ID_RATHIAN_GU;
    const char *monster = mhuc_config("monster");
    if (monster && *monster && strcmp(monster, "any") != 0) {
        char *end;
        const long id = strtol(monster, &end, 0);
        if (*end == '\0' && id >= 0 && id <= 255) {
            monster_id = (int)id;
        }
    }
    mhuc_logf(MH4U_LOG_INFO,
              "ready: translating 12 of GU Rathian's 13 MHXX-only actions on monster %d",
              monster_id);
}

/* The self-test the headless check reads: what the module carries, what 12/0 is, and where
 * the runtime's guest stubs are. */
static void self_test(MH4UCall *call) {
    mhuc_logf(MH4U_LOG_INFO,
              "selftest: 12 of the 13 actions: 3/98 <- 0x020062d4 (3 states, motions 0x101 and "
              "0x104), 12/1 <- 0x0201c1d0 + 0x020062d4, 12/2 <- 0x0201c228 + 0x0201041c->0x%08x, "
              "12/3 <- 0x0201c27c + 0x02010aec->0x%08x, 4/27-32 <- 0x0200e3b4 (3 states, motions "
              "0x417/0x418, 0x909/0x90a, 0x90b/0x90d, r1/r2 per id), 8/0 <- 0x0201b460 (3 states, "
              "motion 0x403 at 4.0, 12.0/50.0, 300.0/38.0, 180.0, tail 9/1 or 2/6), 17 <- the "
              "gate 0x008d5bd4 + MH4U's base update 0x%08x (slot 89, MHXX's slot 244)",
              (unsigned)FN_HANDLER_3_12, (unsigned)FN_HANDLER_3_9, (unsigned)FN_BASE_UPDATE);
    mhuc_log(MH4U_LOG_INFO,
             "selftest: category 17 does nothing for indexes 0 to 2; 12/0 is MH4U's own "
             "category-12 handler 0x006d524c; 8/0's leaf 0x008c4184 is MH4U's 0x0092f6e8, "
             "its table not carried");
    const uint32_t stubs = mhuc_stubs(call);
    if (stubs) {
        mhuc_logf(MH4U_LOG_INFO,
                  "selftest: float stubs at 0x%08x (%u bytes, the game's heap)", (unsigned)stubs,
                  (unsigned)MHUC_STUB_BLOCK_SIZE);
    } else {
        mhuc_log(MH4U_LOG_WARNING, "selftest: no float stubs (no guest memory)");
    }
}

/* The module's one export: src/modules.h names it in the row for id 124. */
const struct MhucModuleOps mhuc_module_rathian_gu = {
    MHUC_MONSTER_ID_RATHIAN_GU,
    start,
    self_test,
    dispatch,
};
