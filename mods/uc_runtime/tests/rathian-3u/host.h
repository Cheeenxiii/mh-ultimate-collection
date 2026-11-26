/*
 * host.h: what the 3U Rathian's fake-host tests share.
 *
 * The module's tests are one program per action family under tests/rathian-3u/, plus the
 * shell's test in tests/test_rathian_3u.c. This header holds the guest answers' helpers, the
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
#ifndef MHUC_RATHIAN_3U_TEST_HOST_H
#define MHUC_RATHIAN_3U_TEST_HOST_H

#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../fake_host.h"
#include "ids.h"

/* The MH4U work block *(enemy + 0xe28) and the fields the test expects a family to read. */
#define ENEMY_WORK      0x0e28u
#define WORK_STATE      0x0144u
#define WORK_CATEGORY   0x01cau
#define WORK_INDEX      0x01cbu
#define WORK_MODE       0x01c8u
#define WORK_SET        0x01dcu
#define WORK_COUNTDOWN  0x01d4u
#define WORK_VERTICAL   0x0180u
#define WORK_0_2_STATE  0x051cu
#define WORK_FLAGS      0x01b4u
#define WORK_OTHER      0x034cu
#define WORK_KIND       0x01c0u
#define WORK_DATA_INDEX 0x797eu
#define WORK_RATE       0x01b8u
#define WORK_RATE_2     0x01bcu
#define WORK_POS_Y      0x019cu

/* The MH4U engine functions and globals the module calls. */
#define FN_MODE        0x009167b4u
#define FN_REQUEST     0x0094f408u
#define FN_FLAG        0x00b05da4u
#define FN_VERTICAL    0x00915d44u
#define FN_DATA_FLOAT  0x0093d870u
#define FN_APPLY_FALL  0x0092e99cu
#define FN_DATA_GET    0x0068882cu
#define FN_SET_ACTION  0x0090ef74u
#define FN_COUNTDOWN   0x00b0704cu
#define ACTION_EXTRA_GLOBAL 0x00fb6b7cu
#define EXTRA_POINTER 0x00001000u

/* The frame values and request ids category 0's source asks for. */
#define DELAY_0_0 150.0f
#define REQUEST_SPEED 10.0f
#define FALL_RATE 6.0f
#define REQUEST_0_0 1u
#define REQUEST_0_1 2u
#define REQUEST_0_2 0x11u
#define REQUEST_0_3 0x1au
#define REQUEST_0_6 0x1bu

#define RECORD_ADDRESS 0x00050000u

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
    fake_mem_write8(work + WORK_KIND, stand_in);
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
