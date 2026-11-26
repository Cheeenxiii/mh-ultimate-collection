/*
 * act3_98.c: action 3/98's family — three states, motions 0x101 and 0x104.
 *
 * MHXX's handler 0x020062d4, block 0x020089a8:
 *   0: remember the data float, advance the fall by it, start motion 0x101 at 6.0, snap
 *      the fall to the target height;
 *   1: advance the fall by the frame's rate, stop when the position reaches the target
 *      height, set the speed 2.0, start motion 0x104;
 *   2: wait for the finish flag, then return to idle.
 *
 * The family exports its handler (mhuc_gu_run_3_98) because 12/1's block runs it before it
 * asks for 12/2 (family.h).
 *
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* uEnemy's work block and the fields this family reads (USA v1.3.0). MHXX's work block is at
 * this+0x10a8 and its +0x44/+0x1d0 are MH4U's +0x19c/+0x218. */
#define WORK_Y      0x019cu
#define WORK_TARGET 0x0218u

/* MH4U engine functions this family calls, and the MHXX function each stands for. */
#define FN_DATA_FLOAT 0x0093d870u /* 0x008d21ac: the data value at the monster's entry */
#define FN_APPLY_FALL 0x0092e99cu /* 0x008b1698: advance the fall by s0 */
#define FN_FALL_SNAP  0x0094a45cu /* 0x008e192c: snap the fall to a target height */
#define FN_APPLY_RATE 0x0093ce60u /* 0x008d1a0c: advance the fall by the frame's rate */
#define FN_SET_SPEED  0x00941d84u /* 0x008d73e8: set a speed (s0) and its flag */
#define FN_FLAG       0x00b05da4u /* 0x00aed11c: the action's finish flag */
#define FN_IDLE       0x0094dc84u /* 0x008eb050: return to idle, 0/3 mode 2 */
#define FN_MOTION     0x0094e318u /* 0x008eb108: start a motion (index r1, s0/s1) */

/* The motions 3/98 starts. 0x101 runs with s0 = 6.0, s1 = 0.0; 0x104 with s0 = 2.0 (the
 * source leaves s1 from the previous state, which is 0.0 while the move is current). */
#define MOTION_A MHUC_MOTION(1, 0x01)
#define MOTION_B MHUC_MOTION(1, 0x04)

/* MHXX 3/98, handler 0x020062d4: three states. */
void mhuc_gu_run_3_98(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    switch (st->state) {
    case 0: {
        st->state = 1;
        float data = 0.0f;
        mhuc_call_f(call, FN_DATA_FLOAT, enemy, 0, 0, 0, 0.0f, 0.0f, &data);
        mhuc_call_f(call, FN_APPLY_FALL, enemy, 0, 0, 0, data, 0.0f, NULL);
        mhuc_call_f(call, FN_MOTION, enemy, MOTION_A, 0, 0, 6.0f, 0.0f, NULL);
        const uint32_t target_y = mhuc_read32(call, work + WORK_TARGET + 4u);
        mhuc_call_f(call, FN_FALL_SNAP, enemy, 0, 0, 0, mhuc_gu_f32_of(target_y), 0.0f, NULL);
        break;
    }
    case 1: {
        mhuc_call(call, FN_APPLY_RATE, enemy, 0, 0, 0);
        const float y = mhuc_f32(call, work + WORK_Y);
        const uint32_t target_y = mhuc_read32(call, work + WORK_TARGET + 4u);
        if (y > mhuc_gu_f32_of(target_y)) {
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

/* Runs 3/98's handler for the pair, or returns 0 so the module's dispatch can try the next
 * family. */
static int dispatch_act3_98(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                            int index) {
    if (category != 3 || index != 98) {
        return 0;
    }
    MhucState *st = mhuc_gu_state(call, enemy, category, index);
    if (!st) {
        return 0;
    }
    mhuc_gu_run_3_98(call, enemy, work, st);
    return 1;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_gu_family_act3_98 = {
    "act3_98", 1, dispatch_act3_98, 0,
};
