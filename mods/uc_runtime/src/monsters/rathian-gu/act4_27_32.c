/*
 * act4_27_32.c: the 4/27 to 4/32 family — one handler, three states.
 *
 * The six ids' case blocks (0x02018af8 to 0x02018bac) pass r1/r2 to the shared handler
 * 0x0200e3b4: 4/27 2/0, 4/28 1/0, 4/29 2/1, 4/30 1/1, 4/31 2/0, 4/32 1/0. r1 picks the pair
 * of sides (mode 1 or 2) and r2 picks the ending: 0 waits for the finish flag and calls
 * MHXX's end-of-action (vtable slot 244), 1 starts the last motion and requests action 7/246
 * or 7/247. Each case block also calls 0x00adb528 with 2, 2, 3, 3, 5, 5 (method 0x4c of the
 * object at this+0x6dc4); MH4U has no counterpart for it, so that call is not translated and
 * logged once per action. The state-2 request goes through the same 0x008ebab0 helper as
 * 12/1 and 12/2, and is left out and logged once for the same reason.
 *
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
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <math.h>
#include <stdint.h>

#include "family.h"

/* MH4U's work block is *(this+0xe28), MHXX's is *(this+0x10a8). The fields this family
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
#define ENEMY_TARGET_LINE  0x08d88u
#define ENEMY_SPEED        0x0290u
#define ENEMY_TURN_SCALE   0x0014u
#define WORK_POS           0x0198u
#define WORK_POS_W         0x01a4u
#define WORK_HEADING       0x01acu
#define WORK_SAVED_HEADING 0x0248u
#define WORK_TARGET        0x0218u
#define LINE_ORIGIN        0x0030u
#define LINE_DIR           0x0040u

/* The handler's engine calls, MH4U address <- MHXX address (the MHXX one in brackets). */
#define FN_FLIGHT_SETUP 0x006e7be8u /* [0x0201262c] the flight's setup, from the height data */
#define FN_MODE         0x009167b4u /* [0x008b1700] set the monster's mode (0, 1, 2, 3, 5, 6) */
#define FN_TURN         0x00917570u /* [0x008b2210] turn by an angle step, s0/s1 the speed range */
#define FN_MODE_CLEAR   0x0091aae4u /* [0x008a7360] the flag-clear wrapper around 0x00b06b4c */
#define FN_TARGET_POINT 0x0092d09cu /* [0x008c21f8] build a target point from an index */
#define FN_TURN_TO      0x0091db4cu /* [0x008b75d8] turn toward a target point, at a step in r3 */
#define FN_LINE_POINT   0x006e5608u /* [0x020063fc] a point on the target line at a fraction */
#define FN_ROTATE       0x00aad55cu /* [0x0201277c] rotate a direction by an angle */
#define FN_MOTION       0x0094e318u /* [0x008eb108] start a motion (index r1, s0/s1) */
#define FN_FLAG         0x00b05da4u /* [0x00aed11c] the action's finish flag */
/* MH4U's uEnemy vtable slot 89, the same routine as MHXX's slot 0x3d0 (0x008ae50c): it is
 * the 4/27-32 finish flag's end-of-action and category 17's base update. */
#define FN_BASE_UPDATE 0x00911b48u

/* The motions the six start: r1 = 1 (mode 1) or 2 (mode 2) selects the side. */
#define MOTION_TAKEOFF_1 MHUC_MOTION(4, 0x17) /* state 0, s0 = 6.0 */
#define MOTION_TAKEOFF_2 MHUC_MOTION(4, 0x18) /* state 0, s0 = 6.0 */
#define MOTION_FLY_1     MHUC_MOTION(9, 0x09) /* state 1, s0 = 0.0 */
#define MOTION_FLY_2     MHUC_MOTION(9, 0x0a) /* state 1, s0 = 0.0 */
#define MOTION_END_1     MHUC_MOTION(9, 0x0d) /* state 2, variant 1, s0 = 2.0 */
#define MOTION_END_2     MHUC_MOTION(9, 0x0b) /* state 2, variant 1, s0 = 2.0 */
#define PENDING_ACTION_1 0xf6u /* the action 4/30 requests next: 7/246 */
#define PENDING_ACTION_2 0xf7u /* the action 4/29 requests next: 7/247 */

/* The turn steps 0x008b75d8 takes in r1: the slow one when the mode-clear call succeeded,
 * the fast one when it did not. */
#define TURN_STEP_SLOW 0x1c7u
#define TURN_STEP_FAST 0x00b6u

/* The two untranslated calls, logged once per action. */
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

/* MHXX 4/27-32, handler 0x0200e3b4: three states, one state per frame.
 *   mode is the case block's r1 (1 or 2), variant its r2 (0 or 1), and s0arg the handler's
 *   incoming s0. */
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
            mhuc_write32(call, line + LINE_ORIGIN, mhuc_gu_bits_of(px));
            mhuc_write32(call, line + LINE_ORIGIN + 8u, mhuc_gu_bits_of(pz));
            float vx = tx - px;
            float vy = mhuc_f32(call, line + LINE_DIR + 4u);
            float vz = tz - pz;
            const float len = sqrtf(vx * vx + vy * vy + vz * vz);
            if (len >= 1.1920929e-07f) {
                vx /= len;
                vy /= len;
                vz /= len;
            }
            mhuc_write32(call, line + LINE_DIR, mhuc_gu_bits_of(vx));
            mhuc_write32(call, line + LINE_DIR + 4u, mhuc_gu_bits_of(vy));
            mhuc_write32(call, line + LINE_DIR + 8u, mhuc_gu_bits_of(vz));
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
        const uint32_t fraction = mhuc_gu_f32_to_u8(mhuc_gu_f32_of(s0arg) * 0.01f);
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

/* Runs the shared handler for the pair, or returns 0 so the module's dispatch can try the
 * next family. 4/27-32 land on 127-132 in the module's old routing so that no other slice's
 * id could take their place; the parity and the two variant ids are the case blocks' r1/r2:
 * r1 = 2 on the odd ids and 1 on the even ones, r2 = 1 on 4/29 and 4/30. */
static int dispatch_act4_27_32(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                              int index) {
    if (category != 4 || index < 27 || index > 32) {
        return 0;
    }
    MhucState *st = mhuc_gu_state(call, enemy, category, index);
    if (!st) {
        return 0;
    }
    const int mode = (index % 2 == 0) ? 1 : 2;
    const int variant = (index == 29 || index == 30) ? 1 : 0;
    log_precall_once(index);
    run_4_27(call, enemy, work, st, index, mode, variant, mhuc_read_s(call, 0));
    return 1;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_gu_family_act4_27_32 = {
    "act4_27_32", 6, dispatch_act4_27_32, 0,
};
