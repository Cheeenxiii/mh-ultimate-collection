/*
 * host.h: what the GU Rathian's fake-host tests share.
 *
 * The module's tests are one program per action family under tests/rathian-gu/, plus the
 * shell's test in tests/test_module.c. This header holds the guest answers' helpers, the
 * work-block and engine-call constants the families' expectations are written against, and the
 * two steps that drive the runtime (spawn a monster at the factory, run one action frame).
 * The constants are written here, not read from the module, so a change in a handler fails a
 * test instead of moving the expectation with it.
 *
 * A family test defines its own guest_fn (what the engine answers that family's calls) and its
 * own main; it writes no other helper.
 *
 * Licence: GPL-3.0-or-later.
 */
#ifndef MHUC_RATHIAN_GU_TEST_HOST_H
#define MHUC_RATHIAN_GU_TEST_HOST_H

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../fake_host.h"
#include "ids.h"

/* The MH4U work block *(enemy + 0xe28) and the fields the test expects a family to read. */
#define ENEMY_WORK        0x0e28u
#define WORK_ID           0x01c0u
#define WORK_CATEGORY     0x01cau
#define WORK_INDEX        0x01cbu
#define WORK_Y            0x019cu
#define WORK_TARGET       0x0218u
#define WORK_POS          0x0198u
#define WORK_POS_W        0x01a4u
#define WORK_HEADING      0x01acu
#define WORK_SAVED_HEADING 0x0248u
#define WORK_STATE        0x0144u
#define WORK_DATAID       0x01c0u
#define WORK_TIMER        0x01d4u
#define WORK_PENDING      0x01d9u
#define WORK_BYTE_A       0x0278u
#define WORK_BYTE_B       0x027cu
#define WORK_VELOCITY     0x0160u
#define WORK_FLAG_ZERO_A  0x7738u
#define WORK_FLAG_ZERO_B  0x7739u
#define WORK_FLAG_MODE    0x7a3cu
#define WORK_FLAG_TAIL    0x7993u
#define ENEMY_MARKER      0x0ca8u
#define ENEMY_TARGET_LINE 0x08d88u
#define ENEMY_SPEED       0x0290u
#define ENEMY_TURN_SCALE  0x0014u
#define LINE_ORIGIN       0x0030u
#define LINE_DIR          0x0040u

/* The MH4U engine functions the families call, by their USA v1.3.0 addresses. */
#define FN_DATA_FLOAT   0x0093d870u
#define FN_APPLY_FALL   0x0092e99cu
#define FN_FALL_SNAP    0x0094a45cu
#define FN_APPLY_RATE   0x0093ce60u
#define FN_SET_SPEED    0x00941d84u
#define FN_FLAG         0x00b05da4u
#define FN_IDLE         0x0094dc84u
#define FN_MOTION       0x0094e318u
#define FN_HANDLER_3_9  0x006d5e98u
#define FN_HANDLER_3_12 0x006d791cu
#define FN_BASE_UPDATE  0x00911b48u
#define FN_MOVE_TO      0x00948674u
#define FN_APPLY_MOVE   0x00955440u
#define FN_COUNTDOWN    0x00b0704cu
#define FN_HIT_CHECK    0x009122fcu
#define FN_HIT_CHECK_R3 0x0092b2b0u
#define FN_REQUEST_NEXT 0x0094ef64u
#define FN_FLIGHT_SETUP 0x006e7be8u
#define FN_MODE         0x009167b4u
#define FN_TURN         0x00917570u
#define FN_MODE_CLEAR   0x0091aae4u
#define FN_TARGET_POINT 0x0092d09cu
#define FN_TURN_TO      0x0091db4cu
#define FN_LINE_POINT   0x006e5608u
#define FN_ROTATE       0x00aad55cu
#define FN_SET_SPEED    0x00941d84u
#define FN_COUNTDOWN    0x00b0704cu
#define FN_1_5_TAIL     0x00911f20u
#define FN_1_6_A        0x0093ba70u
#define FN_1_6_B        0x0091b0f8u
#define FN_1_6_C        0x0093ba88u
#define FN_1_6_D        0x0093c938u
#define FN_1_3_MOTION   0x0091908cu
#define FN_1_3_QUERY    0x0091aae4u
#define FN_MODE_CLEAR   0x0091aae4u
#define FN_PRE          0x00922ca0u
#define FN_2_0_SET      0x0092dc50u
#define FN_2_0_CHECK    0x009128acu
#define FN_CHECK        0x006e9a84u
#define FN_2_0_TAIL     0x0092dcccu
#define FN_1_4_STEP     0x00922c40u
#define FN_DATA_SETUP   0x00911c0cu
#define FN_TABLE_LEAF   0x0092f6e8u
#define FN_SET50        0x00916108u
#define FN_2_4_A        0x0091b3bcu
#define FN_2_4_TABLE    0x00922250u
#define FN_2_4_POINT    0x009114d4u
#define FN_2_4_END      0x0093e558u
#define FN_2_4_STEP     0x00916594u
#define FN_2_14_SET     0x0093310cu
#define FN_2_14_A       0x0090f8fcu
#define FN_2_14_B       0x00916b94u
#define TABLE_2_1       0x00e09458u
#define TABLE_2_2       0x00e09498u
#define TABLE_2_4       0x00fd1a68u

/* The motion numbers, turn steps and frame values the source handlers pass. */
#define MOTION_3_98_A    0x101u
#define MOTION_3_98_B    0x104u
#define MOTION_TAKEOFF_1 0x417u
#define MOTION_TAKEOFF_2 0x418u
#define MOTION_FLY_1     0x909u
#define MOTION_FLY_2     0x90au
#define MOTION_END_1     0x90du
#define MOTION_END_2     0x90bu
#define MOTION_8_0       0x403u
#define TURN_STEP_SLOW   0x1c7u
#define TURN_STEP_FAST   0x00b6u

/* The failures a test has reported; 0 at the end is a pass. */
static int failures;

static inline void fail(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "FAIL: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    failures++;
}

#define CHECK(cond, ...) do { if (!(cond)) fail(__VA_ARGS__); } while (0)

static inline uint32_t fbits(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

static inline float ffrom(uint32_t bits) {
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

/* ── driving the runtime ─────────────────────────────────────────────────────────────── */

/* A monster the factory spawned as `original_id` (the id the module association reads before
 * the id layer rewrites it). */
static inline void spawn(uint32_t enemy, uint32_t work, int original_id, uint32_t stand_in) {
    fake_reset_calls();
    fake_regs[0] = 0;
    fake_regs[1] = (uint32_t)original_id;
    fake_created_enemy = enemy;
    fake_factory_stand_in = stand_in;
    FakeHook *factory = fake_find_hook_last("uEnemyFactory::create");
    CHECK(factory != NULL, "the factory association isn't registered");
    factory->fn(NULL, factory->user);
    CHECK(fake_original_count == 1, "the factory association didn't run the rest of the chain");
    fake_mem_write32(enemy + ENEMY_WORK, work);
    fake_mem_write8(work + WORK_ID, stand_in);
    fake_reset_calls();
}

/* One action frame of the monster's dispatcher, with the pair in its work block. */
static inline void frame_with(uint32_t enemy, uint32_t work, int category, int index) {
    fake_regs[0] = enemy;
    fake_mem_write32(enemy + ENEMY_WORK, work);
    fake_mem_write8(work + WORK_CATEGORY, (uint32_t)category);
    fake_mem_write8(work + WORK_INDEX, (uint32_t)index);
    FakeHook *dispatch = fake_find_hook_last("uEnemy::dispatchAction");
    CHECK(dispatch != NULL, "the action dispatcher isn't registered");
    dispatch->fn(NULL, dispatch->user);
}

#endif
