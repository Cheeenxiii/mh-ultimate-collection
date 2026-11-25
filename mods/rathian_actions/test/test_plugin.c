/*
 * test_plugin.c: the translated actions' call sequences, without the game.
 *
 * Includes the plugin source (so the test sees its static handlers) and gives it a fake
 * host: guest memory is a plain array, alloc hands out a block in it, and `call` decodes the
 * float stubs the plugin writes and records each engine call with its registers and s0/s1.
 * It checks the frames of 3/98, the 12/1-3 blocks and 4/27-32 against the source's call
 * order and values, and that shared and unregistered actions are left to the game.
 *
 * Build and run: make -C mods/rathian_actions test
 * Licence: GPL-3.0-or-later.
 */
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "../src/rathian_actions.c"

#define MEM_SIZE (1u << 20)
#define HEAP_AT  0x00080000u
static uint8_t mem[MEM_SIZE];
static uint32_t regs[16];
static uint32_t fake_s[4];
static int original_calls, skipped_calls;
static int fail_mode_clear;
static int failures;
static char logs[16][512];
static int nlogs;

typedef struct {
    uint32_t fn, a0, a1, a2, s0, s1;
    int has_s0, has_s1;
} Call;
static Call calls[64];
static int ncalls;

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

static uint32_t fbits(float f);
static float ffrom(uint32_t u);

/* ── fake host ─────────────────────────────────────────────────────────────────────── */
static uint32_t h_alloc(MH4UCall *call, uint32_t size, uint32_t align) {
    (void)call; (void)align;
    static uint32_t at = HEAP_AT;
    const uint32_t out = at;
    at += (size + 15u) & ~15u;
    memset(mem + out, 0, size);
    return out;
}
static void h_free(MH4UCall *call, uint32_t addr) { (void)call; (void)addr; }
static uint32_t h_read32(MH4UCall *c, uint32_t a) { (void)c; return (uint32_t)mem[a] | (uint32_t)mem[a+1] << 8 | (uint32_t)mem[a+2] << 16 | (uint32_t)mem[a+3] << 24; }
static uint32_t h_read16(MH4UCall *c, uint32_t a) { (void)c; return (uint32_t)mem[a] | (uint32_t)mem[a+1] << 8; }
static uint32_t h_read8(MH4UCall *c, uint32_t a) { (void)c; return mem[a]; }
static void h_write32(MH4UCall *c, uint32_t a, uint32_t v) { (void)c; mem[a]=v; mem[a+1]=v>>8; mem[a+2]=v>>16; mem[a+3]=v>>24; }
static void h_write16(MH4UCall *c, uint32_t a, uint32_t v) { (void)c; mem[a]=v; mem[a+1]=v>>8; }
static void h_write8(MH4UCall *c, uint32_t a, uint32_t v) { (void)c; mem[a]=(uint8_t)v; }

static uint32_t h_call(MH4UCall *c, uint32_t addr, uint32_t a0, uint32_t a1, uint32_t a2) {
    (void)c;
    if (addr >= HEAP_AT && addr < HEAP_AT + 256) {
        const uint32_t w0 = h_read32(c, addr);
        const uint32_t fn = (w0 == 0xED9F0A01u) ? h_read32(c, addr + 16)
                          : (w0 == 0xED9F0A02u) ? h_read32(c, addr + 24)
                          : (w0 == 0xED9F0A03u) ? h_read32(c, addr + 32) : 0;
        uint32_t got = (fn == FN_SET_SPEED || fn == FN_FLAG || fn == FN_MODE_CLEAR) ? 1u
                     : (fn == FN_DATA_FLOAT) ? 0x3fc00000u : 0u;
        if (fn == FN_MODE_CLEAR && fail_mode_clear) {
            fail_mode_clear = 0;
            got = 0;
        }
        if (w0 == 0xED9F0A01u) {                 /* set s0, branch */
            Call k = {h_read32(c, addr + 16), a0, a1, a2, h_read32(c, addr + 12), 0, 1, 0};
            calls[ncalls++] = k;
            if (k.fn == FN_LINE_POINT) {         /* the engine fills the caller's point */
                const uint32_t w = h_read32(c, a0 + ENEMY_WORK);
                h_write32(c, a1 + 0, fbits(ffrom(h_read32(c, w + WORK_POS)) + 10.0f));
                h_write32(c, a1 + 4, h_read32(c, w + WORK_POS + 4));
                h_write32(c, a1 + 8, h_read32(c, w + WORK_POS + 8));
                h_write32(c, a1 + 12, 0);
            }
            return got;
        }
        if (w0 == 0xED9F0A02u) {                 /* set s0 and s1, branch */
            Call k = {h_read32(c, addr + 24), a0, a1, a2, h_read32(c, addr + 16), h_read32(c, addr + 20), 1, 1};
            calls[ncalls++] = k;
            return got;
        }
        if (w0 == 0xED9F0A03u) {                 /* set s0, call, hand s0 back */
            Call k = {h_read32(c, addr + 32), a0, a1, a2, h_read32(c, addr + 20), 0, 1, 0};
            calls[ncalls++] = k;
            return k.fn == FN_DATA_FLOAT ? (uint32_t)0x3fc00000u : 0;
        }
        if ((w0 & 0xFFF0FFFFu) == 0xEE100A10u) { /* vmov r0,sN; bx lr */
            return fake_s[(w0 >> 16) & 3u];
        }
        fail("unknown stub at 0x%08x: %08x", addr, w0);
        return 0;
    }
    if (addr == FN_DATA_FLOAT) {
        Call k = {addr, a0, a1, a2, 0, 0, 0, 0};
        calls[ncalls++] = k;
        return 0x3fc00000u;                      /* 1.5f, handed back through s0 */
    }
    if (addr == FN_SET_SPEED || addr == FN_FLAG) {
        Call k = {addr, a0, a1, a2, 0, 0, 0, 0};
        calls[ncalls++] = k;
        return 1;
    }
    Call k = {addr, a0, a1, a2, 0, 0, 0, 0};
    calls[ncalls++] = k;
    return 0;
}

static void h_call_original(MH4UCall *c) { (void)c; original_calls++; }
static void h_skip_original(MH4UCall *c) { (void)c; skipped_calls++; }
static uint32_t h_reg(MH4UCall *c, unsigned n) { (void)c; return n < 16 ? regs[n] : 0; }
static void h_set_reg(MH4UCall *c, unsigned n, uint32_t v) { (void)c; if (n < 16) regs[n] = v; }
static void *h_guest_pointer(MH4UCall *c, uint32_t a, uint32_t s) { (void)c; (void)s; return mem + a; }
static MH4UHookFn hooked_dispatch;
static MH4UFrameFn hooked_frame;

static void h_log(const MH4UPluginHost *h, int level, const char *text) {
    (void)h; (void)level;
    if (nlogs < 16) snprintf(logs[nlogs++], sizeof logs[0], "%s", text);
}
static const char *h_config(const MH4UPluginHost *h, const char *key) {
    (void)h;
    if (strcmp(key, "monster") == 0) return "124";
    if (strcmp(key, "selftest") == 0) return "1";
    return NULL;
}
static int h_hook(const MH4UPluginHost *h, const char *name, MH4UHookFn fn, void *user) {
    (void)h; (void)user;
    if (strcmp(name, HOOK_DISPATCH) == 0) { hooked_dispatch = fn; return 1; }
    return 0;
}
static int h_on_frame(const MH4UPluginHost *h, MH4UFrameFn fn, void *user) {
    (void)h; (void)user; hooked_frame = fn; return 1;
}

static MH4UPluginHost fake_host = {
    .abi = 3,
    .size = sizeof(MH4UPluginHost),
    .mod_name = "test", .mod_dir = ".", .program_id = 0x0004000000126300ull,
    .hook = h_hook, .call_original = h_call_original, .skip_original = h_skip_original,
    .reg = h_reg, .set_reg = h_set_reg,
    .read32 = h_read32, .read16 = h_read16, .read8 = h_read8,
    .write32 = h_write32, .write16 = h_write16, .write8 = h_write8,
    .guest_pointer = h_guest_pointer, .log = h_log, .config = h_config,
    .on_frame = h_on_frame,
    .alloc = h_alloc, .free = h_free, .call = h_call,
};

/* ── the monster under test ────────────────────────────────────────────────────────── */
static uint32_t enemy = 0x00010000u;
static uint32_t work  = 0x00020000u;

static void reset_run(void) {
    ncalls = original_calls = skipped_calls = nlogs = 0;
    memset(calls, 0, sizeof calls);
}
static void frame_with(int cat, int idx) {
    regs[0] = enemy;
    h_write32(NULL, enemy + ENEMY_WORK, work);
    h_write8(NULL, work + WORK_ID, 124);
    h_write8(NULL, work + WORK_CATEGORY, (uint32_t)cat);
    h_write8(NULL, work + WORK_INDEX, (uint32_t)idx);
    hooked_dispatch(NULL, NULL);
}
static uint32_t fbits(float f) { uint32_t u; memcpy(&u, &f, 4); return u; }
static float ffrom(uint32_t u) { float f; memcpy(&f, &u, 4); return f; }

int main(void) {
    uint32_t boot_regs[16];
    memset(boot_regs, 0, sizeof boot_regs);
    memcpy(regs, boot_regs, sizeof regs);
    if (!mh4u_plugin_init(&fake_host, 3)) {
        fail("init refused");
        return 1;
    }
    CHECK(hooked_dispatch != NULL, "dispatcher not hooked");
    CHECK(hooked_frame != NULL, "no frame hook");
    hooked_frame(NULL, NULL);                 /* allocates the stubs and runs the self-test */
    int saw_selftest = 0;
    for (int i = 0; i < nlogs; i++) if (strstr(logs[i], "selftest: 11 of the 13")) saw_selftest = 1;
    CHECK(saw_selftest, "the self-test didn't log the translated actions");

    /* ── 3/98, three frames ── */
    reset_run();
    h_write32(NULL, work + WORK_TARGET + 4u, fbits(10.0f));
    h_write32(NULL, work + WORK_Y, fbits(5.0f));
    frame_with(3, 98);
    CHECK(ncalls == 4, "3/98 state 0 made %d calls, want 4", ncalls);
    CHECK(calls[0].fn == FN_DATA_FLOAT, "first call is 0x%08x", calls[0].fn);
    CHECK(calls[1].fn == FN_APPLY_FALL && ffrom(calls[1].s0) == 1.5f,
          "the data float 1.5 isn't passed to the fall");
    CHECK(calls[2].fn == FN_MOTION && calls[2].a1 == MOTION_A && ffrom(calls[2].s0) == 6.0f
          && ffrom(calls[2].s1) == 0.0f, "3/98 doesn't start motion 0x101 at 6.0");
    CHECK(calls[3].fn == FN_FALL_SNAP && ffrom(calls[3].s0) == 10.0f,
          "the target height isn't handed to the fall snap");
    CHECK(skipped_calls == 1 && original_calls == 0, "3/98 didn't skip the dispatcher");

    reset_run();
    frame_with(3, 98);
    CHECK(ncalls == 3, "3/98 state 1 made %d calls, want 3", ncalls);
    CHECK(calls[0].fn == FN_APPLY_RATE, "state 1 doesn't advance the rate first");
    CHECK(ffrom(h_read32(NULL, work + WORK_Y)) == 10.0f, "the position isn't snapped to the target");
    CHECK(calls[1].fn == FN_SET_SPEED && ffrom(calls[1].s0) == 2.0f,
          "state 1 doesn't set the speed 2.0");
    CHECK(calls[2].fn == FN_MOTION && calls[2].a1 == MOTION_B && ffrom(calls[2].s0) == 2.0f,
          "state 1 doesn't start motion 0x104 at 2.0");

    reset_run();
    frame_with(3, 98);
    CHECK(ncalls == 2 && calls[0].fn == FN_FLAG && calls[1].fn == FN_IDLE,
          "state 2 doesn't wait for the flag and return to idle");

    /* ── 3/98 state 1 stops above the target (a fresh monster, so state 0 runs first) ── */
    reset_run();
    const uint32_t enemy2 = 0x00030000u, work2 = 0x00040000u;
    enemy = enemy2;
    h_write32(NULL, enemy2 + ENEMY_WORK, work2);
    h_write8(NULL, work2 + WORK_ID, 124);
    h_write8(NULL, work2 + WORK_CATEGORY, 3);
    h_write8(NULL, work2 + WORK_INDEX, 98);
    h_write32(NULL, work2 + WORK_TARGET + 4u, fbits(10.0f));
    h_write32(NULL, work2 + WORK_Y, fbits(5.0f));
    regs[0] = enemy2;
    hooked_dispatch(NULL, NULL);        /* state 0 */
    reset_run();
    h_write32(NULL, work2 + WORK_Y, fbits(20.0f));
    hooked_dispatch(NULL, NULL);        /* state 1, above the target */
    CHECK(ncalls == 1 && calls[0].fn == FN_APPLY_RATE,
          "state 1 runs on past the target height (%d calls)", ncalls);
    enemy = 0x00010000u;

    /* ── 12/3: target points and MH4U's 3/9 handler ── */
    reset_run();
    fake_s[0] = fbits(1.0f); fake_s[1] = fbits(2.0f);
    fake_s[2] = fbits(3.0f); fake_s[3] = fbits(4.0f);
    frame_with(12, 3);
    CHECK(ncalls == 1 && calls[0].fn == FN_HANDLER_3_9 && calls[0].a1 == 1 && calls[0].a2 == 0,
          "12/3 doesn't call MH4U's 3/9 handler with r1=1, r2=0");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 0u)) == 1.0f, "12/3 target +0");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 4u)) == 3.0f, "12/3 target +4");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 8u)) == 4.0f, "12/3 target +8");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 12u)) == 2.0f, "12/3 target +12");

    /* ── 12/2: MH4U's shared 3/12 handler ── */
    reset_run();
    frame_with(12, 2);
    CHECK(ncalls == 1 && calls[0].fn == FN_HANDLER_3_12 && calls[0].a1 == 0,
          "12/2 doesn't call MH4U's shared 3/12 handler with r1=0");

    /* ── 12/1: fixed target points, then 3/98's handler ── */
    reset_run();
    frame_with(12, 1);
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 0u)) == 5477.0f, "12/1 target +0");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 4u)) == 3000.0f, "12/1 target +4");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 8u)) == 4892.0f, "12/1 target +8");
    CHECK(ffrom(h_read32(NULL, work + WORK_TARGET + 12u)) == 2.0f, "12/1 target +12 is the caller's s1");
    CHECK(ncalls >= 4 && calls[0].fn == FN_DATA_FLOAT, "12/1 doesn't run the 3/98 handler");

    /* ── category 17: a gate plus MH4U's base action update ── */
    for (int idx = 0; idx <= 2; idx++) {
        reset_run();
        frame_with(17, idx);
        CHECK(ncalls == 0 && skipped_calls == 1 && original_calls == 0,
              "17/%d isn't a no-op (%d calls, %d skipped, %d original)", idx, ncalls,
              skipped_calls, original_calls);
    }
    reset_run();
    frame_with(17, 3);
    CHECK(ncalls == 1 && calls[0].fn == FN_BASE_UPDATE && calls[0].a0 == enemy,
          "17/3 doesn't run MH4U's base action update with the monster in r0");
    CHECK(skipped_calls == 1 && original_calls == 0, "17/3 doesn't skip the dispatcher");
    reset_run();
    frame_with(17, 9);
    CHECK(ncalls == 1 && calls[0].fn == FN_BASE_UPDATE, "17/9 doesn't run the base update");

    /* ── category 17 on MH4U's own Rathian is left to the game ── */
    reset_run();
    h_write8(NULL, work + WORK_ID, 1);
    h_write8(NULL, work + WORK_CATEGORY, 17);
    h_write8(NULL, work + WORK_INDEX, 3);
    regs[0] = enemy;
    h_write32(NULL, enemy + ENEMY_WORK, work);
    hooked_dispatch(NULL, NULL);
    CHECK(original_calls == 1 && ncalls == 0 && skipped_calls == 0,
          "category 17 on monster 1 isn't left to the game");
    h_write8(NULL, work + WORK_ID, 124);

    /* ── 4/27-32: one handler, three states, r1/r2 per id ── */
    const uint32_t line1 = 0x00050000u;
    h_write32(NULL, enemy + ENEMY_TARGET_LINE, line1);
    h_write32(NULL, enemy + ENEMY_SPEED, fbits(88.0f));
    h_write32(NULL, enemy + ENEMY_TURN_SCALE, fbits(0.05f));
    h_write32(NULL, work + WORK_POS + 0u, fbits(5.0f));
    h_write32(NULL, work + WORK_POS + 4u, fbits(7.0f));
    h_write32(NULL, work + WORK_POS + 8u, fbits(10.0f));
    h_write32(NULL, work + WORK_TARGET + 0u, fbits(15.0f));
    h_write32(NULL, work + WORK_TARGET + 8u, fbits(10.0f));
    h_write32(NULL, work + WORK_HEADING, 0x1234u);
    fake_s[0] = fbits(500.0f);                  /* (int)(500 * 0.01) = 5 percent */

    reset_run();
    frame_with(4, 27);                          /* state 0, r1=2, r2=0 */
    CHECK(ncalls == 4, "4/27 state 0 made %d calls, want 4", ncalls);
    CHECK(calls[0].fn == FN_FLIGHT_SETUP, "4/27 state 0 doesn't set the flight up first");
    CHECK(calls[1].fn == FN_MODE && calls[1].a1 == 3, "4/27 state 0 doesn't set mode 3");
    CHECK(calls[2].fn == FN_ROTATE && calls[2].a0 == line1 + LINE_DIR && calls[2].a1 == 0xc001,
          "4/27 state 0 doesn't rotate the line by 0xc001");
    CHECK(calls[3].fn == FN_MOTION && calls[3].a1 == MOTION_TAKEOFF_2
          && ffrom(calls[3].s0) == 6.0f && ffrom(calls[3].s1) == 0.0f,
          "4/27 state 0 doesn't start motion 0x418 at 6.0");
    CHECK(ffrom(h_read32(NULL, line1 + LINE_ORIGIN)) == 5.0f
          && ffrom(h_read32(NULL, line1 + LINE_ORIGIN + 8u)) == 10.0f,
          "the line's origin isn't the monster's position");
    CHECK(ffrom(h_read32(NULL, line1 + LINE_DIR)) == 1.0f
          && ffrom(h_read32(NULL, line1 + LINE_DIR + 4u)) == 0.0f
          && ffrom(h_read32(NULL, line1 + LINE_DIR + 8u)) == 0.0f,
          "the line's direction isn't normalised from the target point");
    CHECK(h_read32(NULL, line1 + LINE_DIR + 0xcu) == 0 && h_read32(NULL, work + WORK_SAVED_HEADING) == 0x1234u,
          "the heading isn't saved for the action");
    int saw_precall = 0;
    for (int i = 0; i < nlogs; i++) if (strstr(logs[i], "4/27: the source's case block")) saw_precall = 1;
    CHECK(saw_precall, "4/27 doesn't log the untranslated case-block call once");

    reset_run();
    frame_with(4, 27);                          /* state 1 */
    CHECK(ncalls == 8, "4/27 state 1 made %d calls, want 8", ncalls);
    CHECK(calls[0].fn == FN_FLIGHT_SETUP, "4/27 state 1 doesn't set the flight up first");
    CHECK(calls[1].fn == FN_TARGET_POINT && calls[1].a1 == 0 && calls[1].a2 == 0,
          "4/27 state 1 doesn't build target point 0");
    CHECK(calls[2].fn == FN_MODE_CLEAR && calls[2].a1 == 2 && ffrom(calls[2].s0) == 78.0f,
          "4/27 state 1 doesn't make the mode-clear call at 78.0");
    CHECK(calls[3].fn == FN_TURN_TO && calls[3].a1 == TURN_STEP_SLOW && calls[3].a2 == 0xe001,
          "4/27 state 1 doesn't turn to the target at the slow step, offset 0xe001");
    CHECK(calls[4].fn == FN_LINE_POINT && calls[4].a2 == 5u
          && ffrom(calls[4].s0) == 1.0f,
          "4/27 state 1 doesn't take the line point at 5 percent with speed/88");
    CHECK(ffrom(h_read32(NULL, work + WORK_POS)) == 5.5f
          && ffrom(h_read32(NULL, work + WORK_POS + 4u)) == 7.0f
          && ffrom(h_read32(NULL, work + WORK_POS + 8u)) == 10.0f,
          "4/27 state 1 doesn't step 10 * (this+0x14) toward the line point");
    CHECK(calls[5].fn == FN_MODE_CLEAR && calls[5].a1 == 1 && ffrom(calls[5].s0) == 2.0f,
          "4/27 state 1 doesn't make the mode-clear call at 2.0");
    CHECK(calls[6].fn == FN_MODE && calls[6].a1 == 0, "4/27 state 1 doesn't set mode 0");
    CHECK(calls[7].fn == FN_MOTION && calls[7].a1 == MOTION_FLY_2
          && ffrom(calls[7].s0) == 0.0f && ffrom(calls[7].s1) == 0.0f,
          "4/27 state 1 doesn't start motion 0x90a at 0.0");

    reset_run();
    frame_with(4, 27);                          /* state 2, variant 0: the finish flag */
    CHECK(ncalls == 3, "4/27 state 2 made %d calls, want 3", ncalls);
    CHECK(calls[0].fn == FN_TURN && calls[0].a1 == 0x2000u
          && ffrom(calls[0].s0) == 2.0f && ffrom(calls[0].s1) == 10.0f,
          "4/27 state 2 doesn't turn by 0x2000 at 2.0..10.0");
    CHECK(calls[1].fn == FN_FLAG, "4/27 state 2 doesn't wait for the finish flag");
    CHECK(calls[2].fn == FN_BASE_UPDATE, "4/27 state 2 doesn't end the action on the flag");

    /* 4/28 is the other side: motion 0x417 and the 0x4000 rotation. */
    const uint32_t enemy28 = 0x00030000u, work28 = 0x00040000u, line28 = 0x00060000u;
    h_write32(NULL, enemy28 + ENEMY_WORK, work28);
    h_write8(NULL, work28 + WORK_ID, 124);
    h_write32(NULL, enemy28 + ENEMY_TARGET_LINE, line28);
    h_write32(NULL, enemy28 + ENEMY_SPEED, fbits(88.0f));
    h_write32(NULL, work28 + WORK_POS + 0u, fbits(5.0f));
    h_write32(NULL, work28 + WORK_POS + 8u, fbits(10.0f));
    h_write32(NULL, work28 + WORK_TARGET + 0u, fbits(15.0f));
    h_write32(NULL, work28 + WORK_TARGET + 8u, fbits(10.0f));
    regs[0] = enemy28;
    h_write8(NULL, work28 + WORK_CATEGORY, 4);
    h_write8(NULL, work28 + WORK_INDEX, 28);
    reset_run();
    hooked_dispatch(NULL, NULL);
    CHECK(ncalls == 4 && calls[2].a1 == 0x4000u, "4/28 doesn't rotate the line by 0x4000");
    CHECK(calls[3].fn == FN_MOTION && calls[3].a1 == MOTION_TAKEOFF_1,
          "4/28 doesn't start motion 0x417");

    /* 4/29 (r1=2, r2=1) and 4/30 (r1=1, r2=1) end by starting motion 0x90b/0x90d. */
    const uint32_t enemy29 = 0x00050000u, work29 = 0x00060000u, line29 = 0x00070000u;
    h_write32(NULL, enemy29 + ENEMY_WORK, work29);
    h_write8(NULL, work29 + WORK_ID, 124);
    h_write32(NULL, enemy29 + ENEMY_TARGET_LINE, line29);
    h_write32(NULL, enemy29 + ENEMY_SPEED, fbits(88.0f));
    h_write32(NULL, work29 + WORK_POS + 0u, fbits(5.0f));
    h_write32(NULL, work29 + WORK_POS + 8u, fbits(10.0f));
    h_write32(NULL, work29 + WORK_TARGET + 0u, fbits(15.0f));
    h_write32(NULL, work29 + WORK_TARGET + 8u, fbits(10.0f));
    for (int i = 0; i < 2; i++) {              /* states 0 and 1 */
        regs[0] = enemy29;
        h_write8(NULL, work29 + WORK_CATEGORY, 4);
        h_write8(NULL, work29 + WORK_INDEX, 29);
        hooked_dispatch(NULL, NULL);
    }
    reset_run();
    regs[0] = enemy29;
    h_write8(NULL, work29 + WORK_CATEGORY, 4);
    h_write8(NULL, work29 + WORK_INDEX, 29);
    hooked_dispatch(NULL, NULL);                /* state 2, variant 1 */
    CHECK(ncalls == 3 && calls[0].fn == FN_TURN && calls[0].a1 == 0x2000u,
          "4/29 state 2 doesn't start with the turn");
    CHECK(calls[1].fn == FN_MODE_CLEAR && calls[1].a1 == 1 && ffrom(calls[1].s0) == 30.0f,
          "4/29 state 2 doesn't make the mode-clear call at 30.0");
    CHECK(calls[2].fn == FN_MOTION && calls[2].a1 == MOTION_END_2
          && ffrom(calls[2].s0) == 2.0f && ffrom(calls[2].s1) == 0.0f,
          "4/29 state 2 doesn't start motion 0x90b at 2.0");
    int saw_pending = 0;
    for (int i = 0; i < nlogs; i++) if (strstr(logs[i], "requests action 7/247")) saw_pending = 1;
    CHECK(saw_pending, "4/29 doesn't log the untranslated 7/247 request once");

    const uint32_t enemy30 = 0x00070000u, work30 = 0x00080000u, line30 = 0x00090000u;
    h_write32(NULL, enemy30 + ENEMY_WORK, work30);
    h_write8(NULL, work30 + WORK_ID, 124);
    h_write32(NULL, enemy30 + ENEMY_TARGET_LINE, line30);
    h_write32(NULL, enemy30 + ENEMY_SPEED, fbits(88.0f));
    h_write32(NULL, work30 + WORK_POS + 0u, fbits(5.0f));
    h_write32(NULL, work30 + WORK_POS + 8u, fbits(10.0f));
    h_write32(NULL, work30 + WORK_TARGET + 0u, fbits(15.0f));
    h_write32(NULL, work30 + WORK_TARGET + 8u, fbits(10.0f));
    for (int i = 0; i < 2; i++) {
        regs[0] = enemy30;
        h_write8(NULL, work30 + WORK_CATEGORY, 4);
        h_write8(NULL, work30 + WORK_INDEX, 30);
        hooked_dispatch(NULL, NULL);
    }
    reset_run();
    regs[0] = enemy30;
    h_write8(NULL, work30 + WORK_CATEGORY, 4);
    h_write8(NULL, work30 + WORK_INDEX, 30);
    hooked_dispatch(NULL, NULL);
    CHECK(ncalls == 3 && calls[0].fn == FN_TURN && calls[0].a1 == 0xffffe000u,
          "4/30 state 2 doesn't turn by -0x2000");
    CHECK(calls[2].fn == FN_MOTION && calls[2].a1 == MOTION_END_1,
          "4/30 state 2 doesn't start motion 0x90d");

    /* 4/31: when the mode-clear call at 78.0 fails, the turn takes the fast step. */
    const uint32_t enemy31 = 0x00090000u, work31 = 0x000a0000u, line31 = 0x000b0000u;
    h_write32(NULL, enemy31 + ENEMY_WORK, work31);
    h_write8(NULL, work31 + WORK_ID, 124);
    h_write32(NULL, enemy31 + ENEMY_TARGET_LINE, line31);
    h_write32(NULL, enemy31 + ENEMY_SPEED, fbits(88.0f));
    h_write32(NULL, work31 + WORK_POS + 0u, fbits(5.0f));
    h_write32(NULL, work31 + WORK_POS + 8u, fbits(10.0f));
    h_write32(NULL, work31 + WORK_TARGET + 0u, fbits(15.0f));
    h_write32(NULL, work31 + WORK_TARGET + 8u, fbits(10.0f));
    regs[0] = enemy31;
    h_write8(NULL, work31 + WORK_CATEGORY, 4);
    h_write8(NULL, work31 + WORK_INDEX, 31);
    hooked_dispatch(NULL, NULL);                /* state 0 */
    fail_mode_clear = 1;
    reset_run();
    hooked_dispatch(NULL, NULL);                /* state 1, the mode-clear call fails */
    CHECK(calls[3].fn == FN_TURN_TO && calls[3].a1 == TURN_STEP_FAST,
          "4/31 doesn't take the fast turn step when the mode-clear call fails");

    /* ── shared ids and other monsters fall through ── */
    reset_run();
    frame_with(3, 17);
    CHECK(original_calls == 1 && ncalls == 0 && skipped_calls == 0,
          "a shared action (3/17) isn't left to the game");

    reset_run();
    h_write8(NULL, work + WORK_ID, 1);
    regs[0] = enemy;
    h_write32(NULL, enemy + ENEMY_WORK, work);
    h_write8(NULL, work + WORK_CATEGORY, 3);
    h_write8(NULL, work + WORK_INDEX, 98);
    hooked_dispatch(NULL, NULL);
    CHECK(original_calls == 1 && ncalls == 0, "monster 1 isn't left to the game");

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("ok: the call sequences checked across 3/98, 12/1-3, 4/27-32 and category 17\n");
    return 0;
}
