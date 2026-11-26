/*
 * test_module.c: GU Rathian's module through the runtime, on a fake host, with no game.
 *
 * The translated actions' call sequences are the ones docs/checks.md's T1b fixes: 3/98's
 * three frames, the 12/1-3 blocks, 4/27-32's states, 8/0's three states and category 17's
 * no-op and base-update paths. The test also checks the routing the module contract rests on:
 * the monster spawned as the registry id runs the module, and an MH4U id and a registered id
 * without a module go to the game's dispatcher unchanged.
 *
 * The fake host is tests/fake_host.c; the runtime's hooks are the ones it registers. The
 * expected constants (addresses, motion numbers, frame values) are written here, so a change
 * in the module fails the test instead of moving the expectation with it.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "../src/ids.h"
#include "../src/modules.h"
#include "fake_host.h"
#include "mh4u_plugin.h"

/* uEnemy's work block and the fields the module reads (USA v1.3.0). */
#define ENEMY_WORK    0x0e28u
#define WORK_ID       0x01c0u
#define WORK_CATEGORY 0x01cau
#define WORK_INDEX    0x01cbu
#define WORK_Y        0x019cu
#define WORK_TARGET   0x0218u
#define WORK_POS      0x0198u
#define WORK_POS_W    0x01a4u
#define WORK_HEADING  0x01acu
#define WORK_SAVED_HEADING 0x0248u
#define WORK_TIMER    0x01d4u
#define WORK_PENDING  0x01d9u
#define WORK_BYTE_A   0x0278u
#define WORK_BYTE_B   0x027cu
#define WORK_VELOCITY 0x0160u
#define WORK_FLAG_ZERO_A 0x7738u
#define WORK_FLAG_ZERO_B 0x7739u
#define WORK_FLAG_MODE 0x7a3cu
#define WORK_FLAG_TAIL 0x7993u
#define ENEMY_TARGET_LINE 0x08d88u
#define ENEMY_SPEED       0x0290u
#define ENEMY_TURN_SCALE  0x0014u
#define LINE_ORIGIN       0x0030u
#define LINE_DIR          0x0040u

/* The engine functions the module calls, by their USA v1.3.0 addresses. */
#define FN_DATA_FLOAT  0x0093d870u
#define FN_APPLY_FALL  0x0092e99cu
#define FN_FALL_SNAP   0x0094a45cu
#define FN_APPLY_RATE  0x0093ce60u
#define FN_SET_SPEED   0x00941d84u
#define FN_FLAG        0x00b05da4u
#define FN_IDLE        0x0094dc84u
#define FN_MOTION      0x0094e318u
#define FN_HANDLER_3_9 0x006d5e98u
#define FN_HANDLER_3_12 0x006d791cu
#define FN_BASE_UPDATE 0x00911b48u
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

/* The motion numbers and frame values the source handler passes. */
#define MOTION_3_98_A 0x101u
#define MOTION_3_98_B 0x104u
#define MOTION_TAKEOFF_1 0x417u
#define MOTION_TAKEOFF_2 0x418u
#define MOTION_FLY_1 0x909u
#define MOTION_FLY_2 0x90au
#define MOTION_END_1 0x90du
#define MOTION_END_2 0x90bu
#define MOTION_8_0 0x403u
#define TURN_STEP_SLOW 0x1c7u
#define TURN_STEP_FAST 0x00b6u

static int failures;
static int fail_mode_clear;
static int fake_hit_check = 1, fake_hit_r3 = 1;

static void fail(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "FAIL: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    failures++;
}

#define CHECK(cond, ...) do { if (!(cond)) fail(__VA_ARGS__); } while (0)

static uint32_t fbits(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

static float ffrom(uint32_t bits) {
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

/* ── the guest's answers ─────────────────────────────────────────────────────────────── */

static FakeResult guest_fn(uint32_t fn, const uint32_t r[4], const float s[3], void *user) {
    (void)user;
    (void)s;
    switch (fn) {
    case FN_DATA_FLOAT:
        return (FakeResult){0, 1.5f};      /* the entry's data value, handed back in s0 */
    case FN_SET_SPEED:
    case FN_FLAG:
        return (FakeResult){1, 0.0f};
    case FN_MODE_CLEAR:
        if (fail_mode_clear) {
            fail_mode_clear = 0;
            return (FakeResult){0, 0.0f};
        }
        return (FakeResult){1, 0.0f};
    case FN_HIT_CHECK:
        return (FakeResult){(uint32_t)fake_hit_check, 0.0f};
    case FN_HIT_CHECK_R3:
        return (FakeResult){(uint32_t)fake_hit_r3, 0.0f};
    case FN_LINE_POINT: {
        /* The engine fills the caller's point: 10 further along x, the same y and z. */
        const uint32_t work = fake_mem_read32(r[0] + ENEMY_WORK);
        fake_mem_write32(r[1], fbits(ffrom(fake_mem_read32(work + WORK_POS)) + 10.0f));
        fake_mem_write32(r[1] + 4, fake_mem_read32(work + WORK_POS + 4u));
        fake_mem_write32(r[1] + 8, fake_mem_read32(work + WORK_POS + 8u));
        fake_mem_write32(r[1] + 12, 0);
        return (FakeResult){0, 0.0f};
    }
    default:
        return (FakeResult){0, 0.0f};
    }
}

/* ── driving the runtime ─────────────────────────────────────────────────────────────── */

static void spawn(uint32_t enemy, uint32_t work, int original_id, uint32_t stand_in) {
    fake_reset_calls();
    fake_regs[0] = 0;
    fake_regs[1] = (uint32_t)original_id;
    fake_created_enemy = enemy;
    fake_factory_stand_in = stand_in;
    FakeHook *factory = fake_find_hook_last("uEnemyFactory::create");
    CHECK(factory != NULL, "the factory association isn't registered");
    factory->fn(NULL, factory->user);
    CHECK(fake_original_count == 1, "the factory association didn't run the rest of the chain");
    /* What the game's own block keeps: the stand-in's id byte. */
    fake_mem_write32(enemy + ENEMY_WORK, work);
    fake_mem_write8(work + WORK_ID, stand_in);
    fake_reset_calls();
}

static void frame_with(uint32_t enemy, uint32_t work, int category, int index) {
    fake_regs[0] = enemy;
    fake_mem_write32(enemy + ENEMY_WORK, work);
    fake_mem_write8(work + WORK_CATEGORY, (uint32_t)category);
    fake_mem_write8(work + WORK_INDEX, (uint32_t)index);
    FakeHook *dispatch = fake_find_hook_last("uEnemy::dispatchAction");
    CHECK(dispatch != NULL, "the action dispatcher isn't registered");
    dispatch->fn(NULL, dispatch->user);
}

/* ── the test ────────────────────────────────────────────────────────────────────────── */

int main(void) {
    fake_set_config("selftest", "1");
    fake_set_config("monster", "124");
    fake_guest_fn = guest_fn;
    if (!fake_init()) {
        fail("init refused");
        return 1;
    }
    CHECK(fake_find_hook("uEnemyFactory::create") != NULL, "the factory isn't hooked");
    CHECK(fake_find_hook_last("uEnemy::dispatchAction") != NULL, "the dispatcher isn't hooked");

    /* The first frame runs the id layer's work, then the module's self-test. */
    fake_frame();
    CHECK(fake_log_contains("ready: translating 12 of GU Rathian's 13 MHXX-only actions on "
                            "monster 124"), "the module's ready line is missing");
    CHECK(fake_log_contains("selftest: 12 of the 13 actions"), "the self-test line is missing");
    CHECK(fake_log_contains("selftest: float stubs at 0x"), "the float stubs' line is missing");

    /* ── routing: the module's own monster runs it; every other monster doesn't ── */
    const uint32_t enemy_124 = 0x1b0000u, work_124 = 0x1c0000u;
    spawn(enemy_124, work_124, MHUC_MONSTER_ID_RATHIAN_GU, 1);

    /* A shared id (3/17) stays with the game even on the module's monster. */
    fake_reset_calls();
    frame_with(enemy_124, work_124, 3, 17);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "a shared action (3/17) isn't left to the game (%d calls, %d original, %d skipped)",
          fake_call_count, fake_original_count, fake_skip_count);

    /* An MH4U id has no module: 3/98 goes to the game's dispatcher. */
    const uint32_t enemy_1 = 0x1d0000u, work_1 = 0x1e0000u;
    spawn(enemy_1, work_1, 1, 1);
    fake_reset_calls();
    frame_with(enemy_1, work_1, 3, 98);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "an MH4U id isn't left to the game (%d calls, %d original, %d skipped)",
          fake_call_count, fake_original_count, fake_skip_count);

    /* A registered id without a module (126, Giadrome) has no action module either, even
     * when the game's work block happens to hold id 124: the routing comes from the factory,
     * not the block. */
    const uint32_t enemy_126 = 0x1e8000u, work_126 = 0x1f0000u;
    spawn(enemy_126, work_126, 126, 15);
    fake_mem_write8(work_126 + WORK_ID, 124);
    fake_reset_calls();
    frame_with(enemy_126, work_126, 3, 98);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "a registered id without a module isn't left to the game (%d calls, %d original)",
          fake_call_count, fake_original_count);

    /* The module's own monster runs a translated id, and this is the check that fails if the
     * factory association is broken. */
    fake_reset_calls();
    frame_with(enemy_124, work_124, 3, 98);
    CHECK(fake_skip_count == 1 && fake_original_count == 0 && fake_call_count == 4,
          "the module's monster didn't run 3/98 (%d calls, %d original, %d skipped)",
          fake_call_count, fake_original_count, fake_skip_count);

    /* ── 3/98, three frames ── */
    const uint32_t enemy_98 = 0x10000u, work_98 = 0x20000u;
    spawn(enemy_98, work_98, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(work_98 + WORK_TARGET + 4u, fbits(10.0f));
    fake_mem_write32(work_98 + WORK_Y, fbits(5.0f));

    fake_reset_calls();
    frame_with(enemy_98, work_98, 3, 98);
    CHECK(fake_call_count == 4, "3/98 state 0 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_DATA_FLOAT, "first call is 0x%08x", fake_calls[0].fn);
    CHECK(fake_calls[1].fn == FN_APPLY_FALL && ffrom(fbits(fake_calls[1].s0)) == 1.5f,
          "the data float 1.5 isn't passed to the fall");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_3_98_A
          && fake_calls[2].s0 == 6.0f && fake_calls[2].s1 == 0.0f,
          "3/98 doesn't start motion 0x101 at 6.0");
    CHECK(fake_calls[3].fn == FN_FALL_SNAP && fake_calls[3].s0 == 10.0f,
          "the target height isn't handed to the fall snap");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "3/98 didn't skip the dispatcher");

    fake_reset_calls();
    frame_with(enemy_98, work_98, 3, 98);
    CHECK(fake_call_count == 3, "3/98 state 1 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_APPLY_RATE, "state 1 doesn't advance the rate first");
    CHECK(ffrom(fake_mem_read32(work_98 + WORK_Y)) == 10.0f,
          "the position isn't snapped to the target");
    CHECK(fake_calls[1].fn == FN_SET_SPEED && fake_calls[1].s0 == 2.0f,
          "state 1 doesn't set the speed 2.0");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_3_98_B
          && fake_calls[2].s0 == 2.0f, "state 1 doesn't start motion 0x104 at 2.0");

    fake_reset_calls();
    frame_with(enemy_98, work_98, 3, 98);
    CHECK(fake_call_count == 2 && fake_calls[0].fn == FN_FLAG && fake_calls[1].fn == FN_IDLE,
          "state 2 doesn't wait for the flag and return to idle");

    /* ── 3/98 state 1 stops above the target (a fresh monster, so state 0 runs first) ── */
    const uint32_t enemy_98b = 0x30000u, work_98b = 0x40000u;
    spawn(enemy_98b, work_98b, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(work_98b + WORK_TARGET + 4u, fbits(10.0f));
    fake_mem_write32(work_98b + WORK_Y, fbits(5.0f));
    fake_reset_calls();
    frame_with(enemy_98b, work_98b, 3, 98);      /* state 0 */
    fake_reset_calls();
    fake_mem_write32(work_98b + WORK_Y, fbits(20.0f));
    frame_with(enemy_98b, work_98b, 3, 98);      /* state 1, above the target */
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_APPLY_RATE,
          "state 1 runs on past the target height (%d calls)", fake_call_count);

    /* ── 12/3: target points and MH4U's 3/9 handler ── */
    const uint32_t enemy_12 = 0x50000u, work_12 = 0x60000u;
    spawn(enemy_12, work_12, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    fake_s[0] = 1.0f; fake_s[1] = 2.0f; fake_s[2] = 3.0f; fake_s[3] = 4.0f;
    frame_with(enemy_12, work_12, 12, 3);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_HANDLER_3_9
          && fake_calls[0].r1 == 1 && fake_calls[0].r2 == 0,
          "12/3 doesn't call MH4U's 3/9 handler with r1=1, r2=0");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 0u)) == 1.0f, "12/3 target +0");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 4u)) == 3.0f, "12/3 target +4");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 8u)) == 4.0f, "12/3 target +8");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 12u)) == 2.0f, "12/3 target +12");

    /* ── 12/2: MH4U's shared 3/12 handler ── */
    fake_reset_calls();
    frame_with(enemy_12, work_12, 12, 2);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_HANDLER_3_12 && fake_calls[0].r1 == 0,
          "12/2 doesn't call MH4U's shared 3/12 handler with r1=0");

    /* ── 12/1: fixed target points, then 3/98's handler ── */
    fake_reset_calls();
    frame_with(enemy_12, work_12, 12, 1);
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 0u)) == 5477.0f, "12/1 target +0");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 4u)) == 3000.0f, "12/1 target +4");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 8u)) == 4892.0f, "12/1 target +8");
    CHECK(ffrom(fake_mem_read32(work_12 + WORK_TARGET + 12u)) == 2.0f,
          "12/1 target +12 is the caller's s1");
    CHECK(fake_call_count >= 4 && fake_calls[0].fn == FN_DATA_FLOAT,
          "12/1 doesn't run the 3/98 handler");

    /* ── category 17: a gate plus MH4U's base action update ── */
    for (int index = 0; index <= 2; index++) {
        fake_reset_calls();
        frame_with(enemy_124, work_124, 17, index);
        CHECK(fake_call_count == 0 && fake_skip_count == 1 && fake_original_count == 0,
              "17/%d isn't a no-op (%d calls, %d skipped, %d original)", index, fake_call_count,
              fake_skip_count, fake_original_count);
    }
    fake_reset_calls();
    frame_with(enemy_124, work_124, 17, 3);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_BASE_UPDATE
          && fake_calls[0].r0 == enemy_124,
          "17/3 doesn't run MH4U's base action update with the monster in r0");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "17/3 doesn't skip the dispatcher");
    fake_reset_calls();
    frame_with(enemy_124, work_124, 17, 9);
    CHECK(fake_call_count == 1 && fake_calls[0].fn == FN_BASE_UPDATE,
          "17/9 doesn't run the base update");

    /* ── category 17 on MH4U's own Rathian is left to the game ── */
    fake_reset_calls();
    frame_with(enemy_1, work_1, 17, 3);
    CHECK(fake_original_count == 1 && fake_call_count == 0 && fake_skip_count == 0,
          "category 17 on monster 1 isn't left to the game");

    /* ── 4/27-32: one handler, three states, r1/r2 per id ── */
    const uint32_t enemy_27 = 0x70000u, work_27 = 0x90000u, line_27 = 0xa0000u;
    spawn(enemy_27, work_27, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_27 + ENEMY_TARGET_LINE, line_27);
    fake_mem_write32(enemy_27 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(enemy_27 + ENEMY_TURN_SCALE, fbits(0.05f));
    fake_mem_write32(work_27 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_27 + WORK_POS + 4u, fbits(7.0f));
    fake_mem_write32(work_27 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_27 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_27 + WORK_TARGET + 8u, fbits(10.0f));
    fake_mem_write32(work_27 + WORK_HEADING, 0x1234u);
    fake_s[0] = 500.0f;                        /* (int)(500 * 0.01) = 5 percent */

    fake_reset_calls();
    frame_with(enemy_27, work_27, 4, 27);       /* state 0, r1=2, r2=0 */
    CHECK(fake_call_count == 4, "4/27 state 0 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLIGHT_SETUP, "4/27 state 0 doesn't set the flight up first");
    CHECK(fake_calls[1].fn == FN_MODE && fake_calls[1].r1 == 3,
          "4/27 state 0 doesn't set mode 3");
    CHECK(fake_calls[2].fn == FN_ROTATE && fake_calls[2].r0 == line_27 + LINE_DIR
          && fake_calls[2].r1 == 0xc001, "4/27 state 0 doesn't rotate the line by 0xc001");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_TAKEOFF_2
          && fake_calls[3].s0 == 6.0f && fake_calls[3].s1 == 0.0f,
          "4/27 state 0 doesn't start motion 0x418 at 6.0");
    CHECK(ffrom(fake_mem_read32(line_27 + LINE_ORIGIN)) == 5.0f
          && ffrom(fake_mem_read32(line_27 + LINE_ORIGIN + 8u)) == 10.0f,
          "the line's origin isn't the monster's position");
    CHECK(ffrom(fake_mem_read32(line_27 + LINE_DIR)) == 1.0f
          && ffrom(fake_mem_read32(line_27 + LINE_DIR + 4u)) == 0.0f
          && ffrom(fake_mem_read32(line_27 + LINE_DIR + 8u)) == 0.0f,
          "the line's direction isn't normalised from the target point");
    CHECK(fake_mem_read32(line_27 + LINE_DIR + 0xcu) == 0
          && fake_mem_read32(work_27 + WORK_SAVED_HEADING) == 0x1234u,
          "the heading isn't saved for the action");
    CHECK(fake_log_contains("4/27: the source's case block calls 0x00adb528"),
          "4/27 doesn't log the untranslated case-block call once");

    fake_reset_calls();
    frame_with(enemy_27, work_27, 4, 27);       /* state 1 */
    CHECK(fake_call_count == 8, "4/27 state 1 made %d calls, want 8", fake_call_count);
    CHECK(fake_calls[0].fn == FN_FLIGHT_SETUP, "4/27 state 1 doesn't set the flight up first");
    CHECK(fake_calls[1].fn == FN_TARGET_POINT && fake_calls[1].r1 == 0 && fake_calls[1].r2 == 0,
          "4/27 state 1 doesn't build target point 0");
    CHECK(fake_calls[2].fn == FN_MODE_CLEAR && fake_calls[2].r1 == 2 && fake_calls[2].s0 == 78.0f,
          "4/27 state 1 doesn't make the mode-clear call at 78.0");
    CHECK(fake_calls[3].fn == FN_TURN_TO && fake_calls[3].r1 == TURN_STEP_SLOW
          && fake_calls[3].r2 == 0xe001,
          "4/27 state 1 doesn't turn to the target at the slow step, offset 0xe001");
    CHECK(fake_calls[4].fn == FN_LINE_POINT && fake_calls[4].r2 == 5u
          && fake_calls[4].s0 == 1.0f,
          "4/27 state 1 doesn't take the line point at 5 percent with speed/88");
    CHECK(ffrom(fake_mem_read32(work_27 + WORK_POS)) == 5.5f
          && ffrom(fake_mem_read32(work_27 + WORK_POS + 4u)) == 7.0f
          && ffrom(fake_mem_read32(work_27 + WORK_POS + 8u)) == 10.0f,
          "4/27 state 1 doesn't step 10 * (this+0x14) toward the line point");
    CHECK(fake_calls[5].fn == FN_MODE_CLEAR && fake_calls[5].r1 == 1 && fake_calls[5].s0 == 2.0f,
          "4/27 state 1 doesn't make the mode-clear call at 2.0");
    CHECK(fake_calls[6].fn == FN_MODE && fake_calls[6].r1 == 0,
          "4/27 state 1 doesn't set mode 0");
    CHECK(fake_calls[7].fn == FN_MOTION && fake_calls[7].r1 == MOTION_FLY_2
          && fake_calls[7].s0 == 0.0f && fake_calls[7].s1 == 0.0f,
          "4/27 state 1 doesn't start motion 0x90a at 0.0");

    fake_reset_calls();
    frame_with(enemy_27, work_27, 4, 27);       /* state 2, variant 0: the finish flag */
    CHECK(fake_call_count == 3, "4/27 state 2 made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_TURN && fake_calls[0].r1 == 0x2000u
          && fake_calls[0].s0 == 2.0f && fake_calls[0].s1 == 10.0f,
          "4/27 state 2 doesn't turn by 0x2000 at 2.0..10.0");
    CHECK(fake_calls[1].fn == FN_FLAG, "4/27 state 2 doesn't wait for the finish flag");
    CHECK(fake_calls[2].fn == FN_BASE_UPDATE, "4/27 state 2 doesn't end the action on the flag");

    /* 4/28 is the other side: motion 0x417 and the 0x4000 rotation. */
    const uint32_t enemy_28 = 0xb0000u, work_28 = 0xc0000u, line_28 = 0xd0000u;
    spawn(enemy_28, work_28, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_28 + ENEMY_TARGET_LINE, line_28);
    fake_mem_write32(enemy_28 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_28 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_28 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_28 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_28 + WORK_TARGET + 8u, fbits(10.0f));
    fake_reset_calls();
    frame_with(enemy_28, work_28, 4, 28);
    CHECK(fake_call_count == 4 && fake_calls[2].r1 == 0x4000u,
          "4/28 doesn't rotate the line by 0x4000");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_TAKEOFF_1,
          "4/28 doesn't start motion 0x417");

    /* 4/29 (r1=2, r2=1) and 4/30 (r1=1, r2=1) end by starting motion 0x90b/0x90d. */
    const uint32_t enemy_29 = 0xe0000u, work_29 = 0xf0000u, line_29 = 0x100000u;
    spawn(enemy_29, work_29, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_29 + ENEMY_TARGET_LINE, line_29);
    fake_mem_write32(enemy_29 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_29 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_29 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_29 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_29 + WORK_TARGET + 8u, fbits(10.0f));
    for (int i = 0; i < 2; i++) {              /* states 0 and 1 */
        frame_with(enemy_29, work_29, 4, 29);
    }
    fake_reset_calls();
    frame_with(enemy_29, work_29, 4, 29);       /* state 2, variant 1 */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_TURN && fake_calls[0].r1 == 0x2000u,
          "4/29 state 2 doesn't start with the turn");
    CHECK(fake_calls[1].fn == FN_MODE_CLEAR && fake_calls[1].r1 == 1
          && fake_calls[1].s0 == 30.0f,
          "4/29 state 2 doesn't make the mode-clear call at 30.0");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_END_2
          && fake_calls[2].s0 == 2.0f && fake_calls[2].s1 == 0.0f,
          "4/29 state 2 doesn't start motion 0x90b at 2.0");
    CHECK(fake_log_contains("requests action 7/247"),
          "4/29 doesn't log the untranslated 7/247 request once");

    const uint32_t enemy_30 = 0x110000u, work_30 = 0x120000u, line_30 = 0x130000u;
    spawn(enemy_30, work_30, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_30 + ENEMY_TARGET_LINE, line_30);
    fake_mem_write32(enemy_30 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_30 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_30 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_30 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_30 + WORK_TARGET + 8u, fbits(10.0f));
    for (int i = 0; i < 2; i++) {
        frame_with(enemy_30, work_30, 4, 30);
    }
    fake_reset_calls();
    frame_with(enemy_30, work_30, 4, 30);
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_TURN
          && fake_calls[0].r1 == 0xffffe000u, "4/30 state 2 doesn't turn by -0x2000");
    CHECK(fake_calls[2].fn == FN_MOTION && fake_calls[2].r1 == MOTION_END_1,
          "4/30 state 2 doesn't start motion 0x90d");

    /* 4/31: when the mode-clear call at 78.0 fails, the turn takes the fast step. */
    const uint32_t enemy_31 = 0x140000u, work_31 = 0x150000u, line_31 = 0x160000u;
    spawn(enemy_31, work_31, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_mem_write32(enemy_31 + ENEMY_TARGET_LINE, line_31);
    fake_mem_write32(enemy_31 + ENEMY_SPEED, fbits(88.0f));
    fake_mem_write32(work_31 + WORK_POS + 0u, fbits(5.0f));
    fake_mem_write32(work_31 + WORK_POS + 8u, fbits(10.0f));
    fake_mem_write32(work_31 + WORK_TARGET + 0u, fbits(15.0f));
    fake_mem_write32(work_31 + WORK_TARGET + 8u, fbits(10.0f));
    frame_with(enemy_31, work_31, 4, 31);       /* state 0 */
    fail_mode_clear = 1;
    fake_reset_calls();
    frame_with(enemy_31, work_31, 4, 31);       /* state 1, the mode-clear call fails */
    CHECK(fake_calls[3].fn == FN_TURN_TO && fake_calls[3].r1 == TURN_STEP_FAST,
          "4/31 doesn't take the fast turn step when the mode-clear call fails");

    /* ── 8/0: three frames, then the 9/1 tail ── */
    const uint32_t enemy_80 = 0x170000u, work_80 = 0x180000u;
    spawn(enemy_80, work_80, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    fake_reset_calls();
    frame_with(enemy_80, work_80, 8, 0);        /* state 0 */
    CHECK(fake_call_count == 2, "8/0 state 0 made %d calls, want 2", fake_call_count);
    CHECK(fake_calls[0].fn == FN_MODE && fake_calls[0].r1 == 0,
          "8/0 doesn't copy the data entry with mode 0");
    CHECK(fake_calls[1].fn == FN_MOVE_TO && fake_calls[1].r1 == work_80 + WORK_VELOCITY
          && fake_calls[1].r2 == work_80 + WORK_TARGET
          && fake_calls[1].s0 == 300.0f && fake_calls[1].s1 == 38.0f,
          "8/0 doesn't aim the velocity at the target at 300.0/38.0");
    CHECK(fake_mem_read8(work_80 + WORK_FLAG_ZERO_A) == 0
          && fake_mem_read8(work_80 + WORK_FLAG_ZERO_B) == 0
          && fake_mem_read8(work_80 + WORK_FLAG_MODE) == 2,
          "8/0 doesn't clear the entry flags");
    CHECK(fake_skip_count == 1 && fake_original_count == 0, "8/0 didn't skip the dispatcher");

    fake_reset_calls();
    frame_with(enemy_80, work_80, 8, 0);        /* state 1 */
    CHECK(fake_call_count == 4, "8/0 state 1 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_MODE_CLEAR && fake_calls[0].r1 == 3 && fake_calls[0].r2 == 0
          && fake_calls[0].s0 == 12.0f && fake_calls[0].s1 == 50.0f,
          "8/0 doesn't run the per-mode speed check at 12.0/50.0");
    CHECK(fake_calls[1].fn == FN_APPLY_MOVE,
          "8/0 doesn't advance the position when the check holds");
    CHECK(fake_calls[2].fn == FN_FLAG, "8/0 doesn't wait for the finish flag");
    CHECK(fake_calls[3].fn == FN_MOTION && fake_calls[3].r1 == MOTION_8_0
          && fake_calls[3].s0 == 4.0f && fake_calls[3].s1 == 0.0f,
          "8/0 doesn't start motion 0x403 at 4.0");
    CHECK(ffrom(fake_mem_read32(work_80 + WORK_TIMER)) == 180.0f,
          "8/0 doesn't arm the 180.0 timer");

    fake_reset_calls();
    fake_mem_write8(work_80 + WORK_PENDING, 1);
    fake_mem_write8(work_80 + WORK_BYTE_A, 2);
    fake_mem_write8(work_80 + WORK_BYTE_B, 4);
    frame_with(enemy_80, work_80, 8, 0);        /* state 2: the 9/1 tail */
    CHECK(fake_call_count == 4, "8/0 state 2 made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[0].fn == FN_COUNTDOWN && fake_calls[0].r1 == work_80 + WORK_TIMER,
          "8/0 doesn't count the timer down");
    CHECK(fake_calls[1].fn == FN_HIT_CHECK && fake_calls[1].r1 == 4 && fake_calls[1].r2 == 2
          && fake_calls[1].s0 == 300.0f && fake_calls[1].s1 == 0.0f
          && fake_calls[1].s2 == 150.0f && fake_calls[1].has_s2,
          "8/0 doesn't run the first hit check at 300.0/0.0/150.0");
    CHECK(fake_calls[2].fn == FN_HIT_CHECK_R3 && fake_calls[2].r1 == 1 && fake_calls[2].r2 == 4
          && fake_calls[2].r3 == 2, "8/0 doesn't run the second hit check with mode 1");
    CHECK(fake_calls[3].fn == FN_REQUEST_NEXT && fake_calls[3].r1 == 9 && fake_calls[3].r2 == 1,
          "8/0 doesn't request the 9/1 combo tail");
    CHECK(fake_mem_read8(work_80 + WORK_FLAG_TAIL) == 3, "8/0 doesn't set the tail flag");

    /* ── 8/0: a failed hit check and a spent timer request 2/6 ── */
    fake_reset_calls();
    fake_mem_write8(work_80 + WORK_PENDING, 1);
    fake_mem_write32(work_80 + WORK_TIMER, fbits(0.0f));
    fake_hit_check = 0;
    frame_with(enemy_80, work_80, 8, 0);        /* state 2: hit check fails, timer spent */
    CHECK(fake_call_count == 3, "8/0's spent timer path made %d calls, want 3", fake_call_count);
    CHECK(fake_calls[0].fn == FN_COUNTDOWN && fake_calls[1].fn == FN_HIT_CHECK
          && fake_calls[2].fn == FN_REQUEST_NEXT && fake_calls[2].r1 == 2
          && fake_calls[2].r2 == 6,
          "8/0 doesn't request 2/6 when the hit check fails and the timer is spent");
    fake_hit_check = 1;

    /* ── 8/0: a failed fallback check while the timer runs also requests 2/6 ── */
    fake_reset_calls();
    fake_mem_write32(work_80 + WORK_TIMER, fbits(10.0f));
    fake_hit_check = 0;
    fake_hit_r3 = 0;
    frame_with(enemy_80, work_80, 8, 0);
    CHECK(fake_call_count == 4, "8/0's fallback path made %d calls, want 4", fake_call_count);
    CHECK(fake_calls[1].fn == FN_HIT_CHECK && fake_calls[2].fn == FN_HIT_CHECK_R3
          && fake_calls[2].r1 == 0 && fake_calls[3].fn == FN_REQUEST_NEXT
          && fake_calls[3].r1 == 2 && fake_calls[3].r2 == 6,
          "8/0 doesn't request 2/6 when the fallback check fails");
    fake_hit_check = 1;
    fake_hit_r3 = 1;

    /* ── 8/0: the gate closed leaves the velocity alone, the flag still starts the motion ── */
    const uint32_t enemy_80b = 0x190000u, work_80b = 0x1a0000u;
    spawn(enemy_80b, work_80b, MHUC_MONSTER_ID_RATHIAN_GU, 1);
    frame_with(enemy_80b, work_80b, 8, 0);      /* state 0 */
    fail_mode_clear = 1;
    fake_reset_calls();
    frame_with(enemy_80b, work_80b, 8, 0);      /* state 1, the gate closed */
    CHECK(fake_call_count == 3 && fake_calls[0].fn == FN_MODE_CLEAR
          && fake_calls[1].fn == FN_FLAG && fake_calls[2].fn == FN_MOTION,
          "8/0 doesn't skip the position step when the per-mode check fails");
    fail_mode_clear = 0;

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: the routing and the call sequences checked across 3/98, 12/1-3, 4/27-32, 8/0 "
           "and category 17\n");
    return 0;
}
