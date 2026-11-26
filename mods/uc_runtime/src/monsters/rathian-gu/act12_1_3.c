/*
 * act12_1_3.c: the 12/1 to 12/3 family — the target-point blocks and the shared handlers.
 *
 * MHXX 12/1, block 0x0201c1d0: fixed target points (the fourth is the caller's s1), then
 * the 3/98 handler; when the action has returned to idle it requests 12/2. MHXX 12/2, block
 * 0x0201c228: target points from the caller's s0-s3, MH4U's shared 3/12 handler (MHXX
 * 0x0201041c), then a request for 12/3 after category 3 index 11. MHXX 12/3, block
 * 0x0201c27c: target points from the caller's s0-s3, then MHXX's 3/5/3/9 unit
 * (0x02010aec); MH4U's own 3/9 handler is the pair, with the same r1=1, r2=0.
 *
 * The request helper (0x008ebab0) is not translated for 12/1 and 12/2: MH4U has neither its
 * work-block bytes nor its pending-action queue, so the chain stops after each move instead
 * of following on. The family logs that once per action, as the module did.
 *
 * This is one of the module's family files (family.h): src/monsters/rathian-gu.c iterates the
 * list tools/gen_families.py generates from this directory, so a slice adds a file here and
 * edits nothing else.
 *
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>

#include "family.h"

/* uEnemy's work block and the fields this family reads (USA v1.3.0). */
#define WORK_CATEGORY 0x01cau
#define WORK_INDEX    0x01cbu
#define WORK_TARGET   0x0218u

/* MH4U engine functions this family calls, and the MHXX function each stands for. */
#define FN_HANDLER_3_9  0x006d5e98u /* 0x02010aec, MH4U's shared 3/9 handler (also 3/5) */
#define FN_HANDLER_3_12 0x006d791cu /* 0x0201041c, MH4U's shared 3/12 handler */

/* The two requests the source makes through 0x008ebab0, logged once each. */
static int request_logged[4];

/* MHXX 12/1, block 0x0201c1d0: fixed target points (the fourth is the caller's s1), then
 * the 3/98 handler; when the action has returned to idle it requests 12/2. */
static void run_12_1(MH4UCall *call, uint32_t enemy, uint32_t work, MhucState *st) {
    mhuc_write32(call, work + WORK_TARGET + 0x0u, mhuc_gu_bits_of(5477.0f));
    mhuc_write32(call, work + WORK_TARGET + 0x4u, mhuc_gu_bits_of(3000.0f));
    mhuc_write32(call, work + WORK_TARGET + 0x8u, mhuc_gu_bits_of(4892.0f));
    mhuc_write32(call, work + WORK_TARGET + 0xcu, mhuc_read_s(call, 1));
    mhuc_gu_run_3_98(call, enemy, work, st);
    if (mhuc_read8(call, work + WORK_CATEGORY) == 0 && !request_logged[1]) {
        request_logged[1] = 1;
        mhuc_log(MH4U_LOG_INFO,
                 "12/1: the source now requests 12/2 through 0x008ebab0; that helper is not "
                 "translated, so the move returns to idle instead");
    }
}

/* MHXX 12/2, block 0x0201c228: target points from the caller's s0-s3, MH4U's shared 3/12
 * handler (MHXX 0x0201041c), then a request for 12/3 after category 3 index 11. */
static void run_12_2(MH4UCall *call, uint32_t enemy, uint32_t work) {
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

/* Runs the 12/1-3 block for the pair, or returns 0 so the module's dispatch can try the next
 * family. */
static int dispatch_act12_1_3(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                              int index) {
    if (category != 12 || index < 1 || index > 3) {
        return 0;
    }
    MhucState *st = mhuc_gu_state(call, enemy, category, index);
    if (!st) {
        return 0;
    }
    switch (index) {
    case 1: run_12_1(call, enemy, work, st); break;
    case 2: run_12_2(call, enemy, work); break;
    default: run_12_3(call, enemy, work); break;
    }
    return 1;
}

/* The family file's one export: src/monsters/rathian-gu.c reaches it through the generated
 * families.h. */
const MhucFamily mhuc_gu_family_act12_1_3 = {
    "act12_1_3", 3, dispatch_act12_1_3, 0,
};
