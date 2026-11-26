/*
 * test_runtime.c: the runtime's id layer on a fake host, with no game.
 *
 * The move of the id layer into the runtime must not change what it answers
 * (docs/checks.md#ported-monster-ids, check P1): the runtime asks the code library for the
 * same 21 hook points in the same order, answers a registered id with its stand-in, passes
 * MH4U's own ids through, and puts a monster's own id back after a work-block reader.
 *
 * Build and run: make test, in the runtime's folder.
 * Licence: GPL-3.0-or-later.
 */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ids.h"
#include "mh4u_plugin.h"
#include "runtime.h"

/* The plugin entry point the port calls by name (MH4U_PLUGIN_INIT_SYMBOL). */
int mh4u_plugin_init(const MH4UPluginHost *host, uint32_t abi);

/* The hook list mod.json names: the runtime must ask for exactly these, in the order
 * src/ids.c registers them (the build only needs the set, not the order). */
static const char *const expected_hooks[] = {
    "uEnemyFactory::create",
    "enemyData::load",
    "enemyData::get",
    "getCrown",
    "dropRecord::get",
    "dropRecord::getForMonster",
    "dropBaseA::getForMonster",
    "dropBaseB::getForMonster",
    "enemyResource::get",
    "enemyResource::load",
    "enemyResource::effectLists",
    "monsterIcon::get",
    "monsterIcon::put",
    "monsterListOrder::position",
    "message::getFormat",
    "message::getRecord",
    "message::getRecordById",
    "QuestFlow::startQuest",
    "uc_questTask",
    "aQuest::endSequence",
    "uc_dataPath",
};

/* Guest memory: the arguments, the monster's work block and its id byte live here. */
#define GUEST_BASE 0x08000000u
#define GUEST_SIZE 0x00010000u

typedef struct FakeCall {
    uint32_t reg[16];
} FakeCall;

typedef struct FakeHook {
    char name[64];
    MH4UHookFn fn;
    void *user;
} FakeHook;

static FakeHook hooks[32];
static int hook_count;
static int frame_registered;
static int original_calls;
static int skipped;
static uint32_t probe_address;
static uint32_t probe_at_original;
static char logged[8192];
static size_t logged_used;

static uint8_t guest_pool[GUEST_SIZE];

static uint8_t *guest(uint32_t addr) {
    if (addr < GUEST_BASE || addr >= GUEST_BASE + GUEST_SIZE) {
        return NULL;
    }
    return &guest_pool[addr - GUEST_BASE];
}

static uint32_t mem_read8(uint32_t addr) {
    const uint8_t *p = guest(addr);
    return p ? *p : 0;
}

static uint32_t mem_read16(uint32_t addr) {
    uint32_t value = 0;
    for (unsigned i = 0; i < 2; i++) {
        value |= mem_read8(addr + i) << (8 * i);
    }
    return value;
}

static uint32_t mem_read32(uint32_t addr) {
    uint32_t value = 0;
    for (unsigned i = 0; i < 4; i++) {
        value |= mem_read8(addr + i) << (8 * i);
    }
    return value;
}

static void mem_write8(uint32_t addr, uint32_t value) {
    uint8_t *p = guest(addr);
    if (p) {
        *p = (uint8_t)value;
    }
}

static void mem_write16(uint32_t addr, uint32_t value) {
    for (unsigned i = 0; i < 2; i++) {
        mem_write8(addr + i, value >> (8 * i));
    }
}

static void mem_write32(uint32_t addr, uint32_t value) {
    for (unsigned i = 0; i < 4; i++) {
        mem_write8(addr + i, value >> (8 * i));
    }
}

static int fake_hook(const MH4UPluginHost *self, const char *name, MH4UHookFn fn, void *user) {
    (void)self;
    if (hook_count >= (int)(sizeof hooks / sizeof hooks[0])) {
        return 0;
    }
    snprintf(hooks[hook_count].name, sizeof hooks[hook_count].name, "%s", name);
    hooks[hook_count].fn = fn;
    hooks[hook_count].user = user;
    hook_count++;
    return 1;
}

static void fake_call_original(MH4UCall *call) {
    (void)call;
    original_calls++;
    if (probe_address) {
        probe_at_original = mem_read8(probe_address);
    }
}

static void fake_skip_original(MH4UCall *call) {
    (void)call;
    skipped = 1;
}

static uint32_t fake_reg(MH4UCall *call, unsigned n) {
    return ((FakeCall *)call)->reg[n & 15u];
}

static void fake_set_reg(MH4UCall *call, unsigned n, uint32_t value) {
    ((FakeCall *)call)->reg[n & 15u] = value;
}

static uint32_t fake_read32(MH4UCall *call, uint32_t addr) {
    (void)call;
    return mem_read32(addr);
}

static uint32_t fake_read16(MH4UCall *call, uint32_t addr) {
    (void)call;
    return mem_read16(addr);
}

static uint32_t fake_read8(MH4UCall *call, uint32_t addr) {
    (void)call;
    return mem_read8(addr);
}

static void fake_write32(MH4UCall *call, uint32_t addr, uint32_t value) {
    (void)call;
    mem_write32(addr, value);
}

static void fake_write16(MH4UCall *call, uint32_t addr, uint32_t value) {
    (void)call;
    mem_write16(addr, value);
}

static void fake_write8(MH4UCall *call, uint32_t addr, uint32_t value) {
    (void)call;
    mem_write8(addr, value);
}

static void *fake_guest_pointer(MH4UCall *call, uint32_t addr, uint32_t size) {
    (void)call;
    if (!guest(addr) || !guest(addr + size - 1)) {
        return NULL;
    }
    return guest(addr);
}

static void fake_log(const MH4UPluginHost *self, int level, const char *message) {
    (void)self;
    if (logged_used + 1 < sizeof logged) {
        const int n = snprintf(logged + logged_used, sizeof logged - logged_used, "%d:%s\n",
                               level, message);
        if (n > 0 && (size_t)n < sizeof logged - logged_used) {
            logged_used += (size_t)n;
        }
    }
}

static const char *fake_config(const MH4UPluginHost *self, const char *key) {
    (void)self;
    return strcmp(key, "selftest") == 0 ? "0" : NULL;
}

static int fake_on_frame(const MH4UPluginHost *self, MH4UFrameFn fn, void *user) {
    (void)self;
    (void)fn;
    (void)user;
    frame_registered = 1;
    return 1;
}

static uint32_t alloc_at = GUEST_BASE + 0x8000u;

static uint32_t fake_alloc(MH4UCall *call, uint32_t size, uint32_t align) {
    (void)call;
    const uint32_t mask = (align ? align : 16u) - 1u;
    alloc_at = (alloc_at + mask) & ~mask;
    const uint32_t block = alloc_at;
    alloc_at += size;
    return block + size < GUEST_BASE + GUEST_SIZE ? block : 0;
}

static void fake_free(MH4UCall *call, uint32_t addr) {
    (void)call;
    (void)addr;
}

static uint32_t fake_call(MH4UCall *call, uint32_t addr, uint32_t a0, uint32_t a1, uint32_t a2) {
    (void)call;
    (void)addr;
    (void)a0;
    (void)a1;
    (void)a2;
    return 0;
}

static FakeHook *find_hook(const char *name) {
    for (int i = 0; i < hook_count; i++) {
        if (strcmp(hooks[i].name, name) == 0) {
            return &hooks[i];
        }
    }
    return NULL;
}

int main(void) {
    MH4UPluginHost host = {
        .abi = MH4U_PLUGIN_ABI,
        .size = sizeof(MH4UPluginHost),
        .mod_name = "UC runtime",
        .mod_dir = ".",
        .program_id = 0x0004000000126300u,
        .hook = fake_hook,
        .call_original = fake_call_original,
        .skip_original = fake_skip_original,
        .reg = fake_reg,
        .set_reg = fake_set_reg,
        .read32 = fake_read32,
        .read16 = fake_read16,
        .read8 = fake_read8,
        .write32 = fake_write32,
        .write16 = fake_write16,
        .write8 = fake_write8,
        .guest_pointer = fake_guest_pointer,
        .log = fake_log,
        .config = fake_config,
        .on_frame = fake_on_frame,
        .alloc = fake_alloc,
        .free = fake_free,
        .call = fake_call,
    };

    assert(mh4u_plugin_init(&host, MH4U_PLUGIN_ABI) == 1);
    assert(hook_count == (int)(sizeof expected_hooks / sizeof expected_hooks[0]));
    for (int i = 0; i < hook_count; i++) {
        assert(strcmp(hooks[i].name, expected_hooks[i]) == 0);
    }
    assert(frame_registered == 1);

    /* A registered id is answered with its stand-in; MH4U's own ids pass through. */
    FakeCall call;
    memset(&call, 0, sizeof call);
    call.reg[1] = 124;
    find_hook("uEnemyFactory::create")->fn((MH4UCall *)&call, find_hook("uEnemyFactory::create")->user);
    assert(original_calls == 1);
    assert(call.reg[1] == 1);
    assert(strstr(logged, "factory: id 124 -> stand-in 1") != NULL);

    memset(&call, 0, sizeof call);
    call.reg[1] = 1;
    find_hook("uEnemyFactory::create")->fn((MH4UCall *)&call, find_hook("uEnemyFactory::create")->user);
    assert(original_calls == 2);
    assert(call.reg[1] == 1);
    assert(strstr(logged, "factory: id 1 is MH4U's own; passed through") != NULL);

    /* The work-block readers swap the byte for the stand-in, run the game's function, and
     * put the monster's own id back: the block belongs to the game's own monster. */
    const uint32_t self = GUEST_BASE + 0x1000u;
    const uint32_t work = GUEST_BASE + 0x2000u;
    mem_write32(self + 0xe28u, work);
    mem_write8(work + 0x1c0u, 125u);
    probe_address = work + 0x1c0u;
    probe_at_original = 0;
    memset(&call, 0, sizeof call);
    call.reg[0] = self;
    find_hook("dropRecord::getForMonster")->fn((MH4UCall *)&call,
                                              find_hook("dropRecord::getForMonster")->user);
    assert(probe_at_original == 1);
    assert(mem_read8(work + 0x1c0u) == 125);
    assert(strstr(logged, "drop records: id 125 -> stand-in 1") != NULL);

    printf("ok: %d hooks, a registered id answered with its stand-in and an MH4U id passed "
           "through\n", hook_count);
    return 0;
}
