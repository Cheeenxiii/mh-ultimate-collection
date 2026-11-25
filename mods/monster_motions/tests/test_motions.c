/*
 * test_motions.c: drives mods/monster_motions' plugin on a fake host, without the game.
 *
 * The plugin is included so its static lookups and log dedupe are tested directly; the fake
 * host gives it a guest memory (the enemy's work block), registers and a log, and records
 * call_original. The real numbers come from the generated src/motions.h: 13/5 asks motion 2
 * and her animation is at 0x13, 13/6 asks 2 and hers is at 0x1a, 13/8 asks 0x13 and hers is
 * at 0x1a, and 7/36 is one of the category-7 ids the table leaves out.
 *
 * Build: cc -std=c99 -I<fork>/include tests/test_motions.c -o test_motions
 * Run:   ./test_motions        exit 0 on success
 * Licence: GPL-3.0-or-later.
 */
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* The host's call is opaque; the fake host is the only thing that needs its shape. */
struct MH4UCall {
    uint32_t r[16];
};

#include "../src/monster_motions.c"

static uint8_t memory[0x10000];
static char logged[4096];
static MH4UHookFn hooked, hooked_factory;
static void *hooked_user;
static int hook_calls, original_calls, failures;

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
static uint32_t h_read16(MH4UCall *call, uint32_t a) { (void)call; return memory[a] | (memory[a + 1] << 8); }
static uint32_t h_read8(MH4UCall *call, uint32_t a) { (void)call; return memory[a]; }
static void h_write32(MH4UCall *call, uint32_t a, uint32_t v) { (void)call; write32_at(a, v); }
static void h_write16(MH4UCall *call, uint32_t a, uint32_t v) { (void)call; memory[a] = (uint8_t)v; memory[a + 1] = (uint8_t)(v >> 8); }
static void h_write8(MH4UCall *call, uint32_t a, uint32_t v) { (void)call; memory[a] = (uint8_t)v; }
static void *h_guest_pointer(MH4UCall *call, uint32_t a, uint32_t size) {
    (void)call; (void)a; (void)size; return NULL;
}
static void h_call_original(MH4UCall *call) { (void)call; original_calls++; }
static void h_skip_original(MH4UCall *call) { (void)call; }
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
static void h_log(const MH4UPluginHost *self, int level, const char *text) {
    (void)self; (void)level;
    if (logged[0]) {
        strncat(logged, "\n", sizeof logged - strlen(logged) - 1);
    }
    strncat(logged, text, sizeof logged - strlen(logged) - 1);
}
static int h_hook(const MH4UPluginHost *self, const char *name, MH4UHookFn fn, void *user) {
    (void)self;
    if (strcmp(name, "uEnemyFactory::create") == 0) {
        hooked_factory = fn;
        hook_calls++;
        return 1;
    }
    if (strcmp(name, "uEnemy::startMotion") != 0) {
        return 0;
    }
    hooked = fn;
    hooked_user = user;
    hook_calls++;
    return 1;
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

/* A ported monster with a current action and a motion number: the hook sees r0 = enemy,
 * r1 = motion, and the enemy's work block carries the id and the action bytes. */
static void place(unsigned id, unsigned category, unsigned index, uint32_t motion) {
    memset(memory, 0, sizeof memory);
    memset(&call, 0, sizeof call);
    logged[0] = '\0';
    original_calls = 0;
    translated_count = 0;
    missing_count = 0;
    call.r[0] = ENEMY;
    call.r[1] = motion;
    write32_at(ENEMY + 0xe28, WORK);
    memory[WORK + 0x1c0] = (uint8_t)id;
    memory[WORK + 0x1ca] = (uint8_t)category;
    memory[WORK + 0x1cb] = (uint8_t)index;
}

static void run(void) {
    hooked(&call, hooked_user);
}

/* The factory asked for `id` and returns `enemy` (the fake chain leaves r0 as set). */
static void create(unsigned id, uint32_t enemy) {
    MH4UCall made;
    memset(&made, 0, sizeof made);
    made.r[0] = enemy;
    made.r[1] = id;
    hooked_factory(&made, NULL);
}

int main(void) {
    CHECK(mh4u_plugin_init(&fake_host, MH4U_PLUGIN_ABI) == 1);
    CHECK(hook_calls == 2);
    CHECK(hooked_factory != NULL);
    CHECK(hooked != NULL);
    CHECK(strstr(logged, "ready: translating motion numbers") != NULL);

    /* 13/5: MH4U asks motion 2, her animation is at 0x13. */
    place(125, 13, 5, 2);
    run();
    CHECK(call.r[1] == 0x13);
    CHECK(original_calls == 1);
    CHECK(occurrences("action 13/5 asks motion 0x002 -> source 0x013") == 1);

    /* The same translation again is not logged twice. */
    place(125, 13, 5, 2);
    run();
    CHECK(call.r[1] == 0x13);
    run();
    CHECK(call.r[1] == 0x13);
    CHECK(occurrences("action 13/5 asks motion 0x002 -> source 0x013") == 1);

    /* 13/6 asks the same MH4U motion and needs her other animation. */
    place(125, 13, 6, 2);
    run();
    CHECK(call.r[1] == 0x1a);

    /* 13/8 asks MH4U's 0x13 and needs her 0x1a, so the two actions keep their own animations. */
    place(125, 13, 8, 0x13);
    run();
    CHECK(call.r[1] == 0x1a);
    CHECK(occurrences("action 13/8 asks motion 0x013 -> source 0x01a") == 1);

    /* A category-only action (index 0x100) matches any index byte the game holds. */
    place(125, 8, 0, 0x403);
    run();
    CHECK(call.r[1] == 0x202);

    /* 7/36 is one of the ids the table leaves out: pass through, log the first time only. */
    place(125, 7, 36, 0x41c);
    run();
    CHECK(call.r[1] == 0x41c);
    CHECK(occurrences("no entry for action 7/36 motion 0x41c") == 1);
    run();
    CHECK(call.r[1] == 0x41c);
    CHECK(occurrences("no entry for action 7/36 motion 0x41c") == 1);

    /* MH4U's own monsters are untouched and not logged. */
    place(1, 3, 17, 0x101);
    run();
    CHECK(call.r[1] == 0x101);
    CHECK(logged[0] == '\0');

    /* 7/1 is found elsewhere: MH4U asks 0x41a and her animation is at her file 2 slot 9,
     * which the converted lists address as MH4U's 0x209. */
    place(125, 7, 1, 0x41a);
    run();
    CHECK(call.r[1] == 0x209);

    /* A ported monster is created as its stand-in: its id byte holds 1. The factory call for
     * 125 is what marks it, and only that enemy. */
    place(1, 13, 5, 2);
    run();
    CHECK(call.r[1] == 2);                      /* not created through the factory: MH4U's */
    create(125, ENEMY);
    place(1, 13, 5, 2);
    run();
    CHECK(call.r[1] == 0x13);
    CHECK(occurrences("monster 125: action 13/5 asks motion 0x002 -> source 0x013") == 1);
    /* The same address handed out again for MH4U's own Rathian forgets the mark. */
    create(1, ENEMY);
    place(1, 13, 5, 2);
    run();
    CHECK(call.r[1] == 2);

    if (failures) {
        fprintf(stderr, "%d check(s) failed\n", failures);
        return 1;
    }
    printf("motion plugin ok\n");
    return 0;
}
