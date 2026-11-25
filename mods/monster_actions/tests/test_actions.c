/*
 * test_actions.c: drives mods/monster_actions' plugin on a fake host, without the game.
 *
 * The plugin is included so its table lookup, pass-through and skip are tested directly; the
 * fake host gives it a guest memory (the enemy's work block), registers and a log, and
 * records call_original and skip_original. The entries come from the generated
 * src/actions.h: 0/4 -> 0/0, 7/87 -> 7/92, 11/5 -> 11/0 and 13/9 -> 0/3, and 7/35, action 4
 * and MH4U's own ids pass through.
 *
 * Build: cc -std=c99 -I<fork>/include tests/test_actions.c -o test_actions
 * Run:   ./test_actions        exit 0 on success
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* The host's call is opaque; the fake host is the only thing that needs its shape. */
struct MH4UCall {
    uint32_t r[16];
};

#include "../src/monster_actions.c"

static uint8_t memory[0x10000];
static char logged[4096];
static MH4UHookFn hooked;
static void *hooked_user;
static int hook_calls, original_calls, skipped_calls, failures;

#define ENEMY 0x1000u
#define WORK 0x2000u
#define CHECK(cond) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #cond); \
        failures++; \
    } \
} while (0)

static uint32_t read32_at(uint32_t a) {
    return (uint32_t)memory[a] | ((uint32_t)memory[a + 1] << 8) |
           ((uint32_t)memory[a + 2] << 16) | ((uint32_t)memory[a + 3] << 24);
}

static void write32_at(uint32_t a, uint32_t v) {
    memory[a] = (uint8_t)v;
    memory[a + 1] = (uint8_t)(v >> 8);
    memory[a + 2] = (uint8_t)(v >> 16);
    memory[a + 3] = (uint8_t)(v >> 24);
}

static uint32_t h_reg(MH4UCall *call, unsigned n) { return call->r[n]; }
static void h_set_reg(MH4UCall *call, unsigned n, uint32_t value) { call->r[n] = value; }
static uint32_t h_read32(MH4UCall *call, uint32_t a) { (void)call; return read32_at(a); }
static uint32_t h_read8(MH4UCall *call, uint32_t a) { (void)call; return memory[a]; }
static void h_call_original(MH4UCall *call) { (void)call; original_calls++; }
static void h_skip_original(MH4UCall *call) { (void)call; skipped_calls++; }
static void h_log(const MH4UPluginHost *self, int level, const char *text) {
    (void)self; (void)level;
    if (logged[0]) {
        strncat(logged, "\n", sizeof logged - strlen(logged) - 1);
    }
    strncat(logged, text, sizeof logged - strlen(logged) - 1);
}
static int h_hook(const MH4UPluginHost *self, const char *name, MH4UHookFn fn, void *user) {
    (void)self;
    if (strcmp(name, "uEnemy::setAction") != 0) {
        return 0;
    }
    hooked = fn;
    hooked_user = user;
    hook_calls++;
    return 1;
}
static uint32_t h_alloc(MH4UCall *call, uint32_t size, uint32_t align) {
    (void)call; (void)size; (void)align; return 0;
}
static void h_free(MH4UCall *call, uint32_t addr) { (void)call; (void)addr; }
static uint32_t h_call(MH4UCall *call, uint32_t addr, uint32_t a0, uint32_t a1, uint32_t a2) {
    (void)call; (void)addr; (void)a0; (void)a1; (void)a2; return 0;
}
static const char *h_config(const MH4UPluginHost *self, const char *key) {
    (void)self; (void)key; return NULL;
}
static uint32_t h_read16(MH4UCall *call, uint32_t a) {
    (void)call; return memory[a] | (memory[a + 1] << 8);
}
static void h_write32(MH4UCall *call, uint32_t a, uint32_t v) { (void)call; write32_at(a, v); }
static void h_write16(MH4UCall *call, uint32_t a, uint32_t v) {
    (void)call; memory[a] = (uint8_t)v; memory[a + 1] = (uint8_t)(v >> 8);
}
static void h_write8(MH4UCall *call, uint32_t a, uint32_t v) {
    (void)call; memory[a] = (uint8_t)v;
}
static void *h_guest_pointer(MH4UCall *call, uint32_t a, uint32_t size) {
    (void)call; (void)a; (void)size; return NULL;
}
static int h_on_frame(const MH4UPluginHost *self, MH4UFrameFn fn, void *user) {
    (void)self; (void)fn; (void)user; return 1;
}

static const MH4UPluginHost fake_host = {
    .abi = MH4U_PLUGIN_ABI,
    .size = sizeof(MH4UPluginHost),
    .mod_name = "test",
    .mod_dir = "",
    .program_id = 0x0004000000126300ull,
    .hook = h_hook,
    .call_original = h_call_original,
    .skip_original = h_skip_original,
    .reg = h_reg,
    .set_reg = h_set_reg,
    .read32 = h_read32,
    .read16 = h_read16,
    .read8 = h_read8,
    .write32 = h_write32,
    .write16 = h_write16,
    .write8 = h_write8,
    .guest_pointer = h_guest_pointer,
    .log = h_log,
    .config = h_config,
    .on_frame = h_on_frame,
    .alloc = h_alloc,
    .free = h_free,
    .call = h_call,
};

static MH4UCall call;

static int occurrences(const char *needle) {
    int n = 0;
    for (const char *p = logged; (p = strstr(p, needle)) != NULL; p++) {
        n++;
    }
    return n;
}

/* A ported monster with a current action and a requested action: the hook sees r0 = enemy,
 * r1 = requested category, r2 = requested index, and the work block carries the id and the
 * current action bytes. */
static void place(unsigned id, unsigned current_category, unsigned current_index,
                  unsigned category, unsigned index) {
    memset(memory, 0, sizeof memory);
    memset(&call, 0, sizeof call);
    logged[0] = '\0';
    original_calls = skipped_calls = 0;
    translated_count = 0;
    call.r[0] = ENEMY;
    call.r[1] = category;
    call.r[2] = index;
    write32_at(ENEMY + 0xe28, WORK);
    memory[WORK + 0x1c0] = (uint8_t)id;
    memory[WORK + 0x1ca] = (uint8_t)current_category;
    memory[WORK + 0x1cb] = (uint8_t)current_index;
}

static void run(void) {
    hooked(&call, hooked_user);
}

int main(void) {
    CHECK(mh4u_plugin_init(&fake_host, MH4U_PLUGIN_ABI) == 1);
    CHECK(hook_calls == 1);
    CHECK(hooked != NULL);
    CHECK(strstr(logged, "ready: translating 16 source action id(s)") != NULL);

    /* 0/4 is sent to 0/0, whose MH4U case block is inline. */
    place(125, 0, 3, 0, 4);
    run();
    CHECK(call.r[1] == 0 && call.r[2] == 0);
    CHECK(original_calls == 1 && skipped_calls == 0);
    CHECK(occurrences("action 0/4 -> 0/0") == 1);

    /* The same translation again is not logged twice. */
    place(125, 0, 3, 0, 4);
    run();
    CHECK(call.r[1] == 0 && call.r[2] == 0);
    CHECK(occurrences("action 0/4 -> 0/0") == 1);

    /* 7/87 and 7/93 share the wrapper's tail: both go to 7/92. */
    place(125, 0, 3, 7, 87);
    run();
    CHECK(call.r[1] == 7 && call.r[2] == 92);
    place(125, 0, 3, 7, 93);
    run();
    CHECK(call.r[1] == 7 && call.r[2] == 92);

    /* 11/5 goes to the shared 11/0, and 13/9 to 0/3. */
    place(125, 0, 3, 11, 5);
    run();
    CHECK(call.r[1] == 11 && call.r[2] == 0);
    place(125, 0, 0, 13, 9);
    run();
    CHECK(call.r[1] == 0 && call.r[2] == 3);

    /* The mapped action already running: skip the setter so the move is not restarted. */
    place(125, 7, 92, 7, 87);
    run();
    CHECK(skipped_calls == 1 && original_calls == 0);
    CHECK(call.r[1] == 7 && call.r[2] == 87);

    /* A shared id the table does not name passes through and is not logged. */
    place(125, 0, 3, 7, 35);
    run();
    CHECK(original_calls == 1 && skipped_calls == 0);
    CHECK(call.r[1] == 7 && call.r[2] == 35);
    CHECK(logged[0] == '\0');

    /* Action 4 needs new C: the table has no entry, so it passes through. */
    place(125, 0, 3, 4, 0);
    run();
    CHECK(call.r[1] == 4 && call.r[2] == 0);
    CHECK(logged[0] == '\0');

    /* MH4U's own monsters are untouched. */
    place(1, 0, 3, 0, 4);
    run();
    CHECK(original_calls == 1);
    CHECK(call.r[1] == 0 && call.r[2] == 4);
    CHECK(logged[0] == '\0');

    /* A call before the work block exists goes to the game unchanged. */
    memset(&call, 0, sizeof call);
    call.r[0] = ENEMY;
    original_calls = skipped_calls = 0;
    run();
    CHECK(original_calls == 1);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("action plugin ok\n");
    return 0;
}
