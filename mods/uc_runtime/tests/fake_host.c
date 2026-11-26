/*
 * fake_host.c: the runtime's fake plugin host, with no game.
 *
 * Guest memory is a plain array; the heap starts at FAKE_HEAP_AT and alloc hands out blocks in
 * it; call and call2 decode the runtime's guest stubs (the caller's s0-s3 readers and the
 * three-float call the ABI 4 call cannot make) and record every engine call with its
 * registers and floats. The test supplies what each guest function returns through
 * fake_guest_fn.
 *
 * Licence: GPL-3.0-or-later.
 */
#include "fake_host.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

/* The plugin entry point (MH4U_PLUGIN_INIT_SYMBOL). */
int mh4u_plugin_init(const MH4UPluginHost *host, uint32_t abi);

static uint8_t memory[FAKE_MEM_SIZE];
static uint32_t heap_at = FAKE_HEAP_AT;

FakeCall fake_calls[FAKE_CALLS];
int fake_call_count;
int fake_original_count;
int fake_skip_count;
uint32_t fake_regs[16];
float fake_s[4];
FakeHook fake_hooks[FAKE_HOOKS];
int fake_hook_count;
char fake_log[FAKE_LOG_SIZE];
size_t fake_log_used;
FakeGuestFn fake_guest_fn;
void *fake_guest_user;
uint32_t fake_created_enemy;
uint32_t fake_factory_stand_in;
uint32_t fake_probe_address;
uint32_t fake_probe_value;

static MH4UHookFn frame_fn;
static void *frame_user;
static int unknown_stub;

typedef struct Setting {
    char key[32];
    char value[64];
} Setting;
static Setting settings[16];
static int setting_count;

uint8_t *fake_guest(uint32_t addr) {
    return addr < FAKE_MEM_SIZE ? &memory[addr] : NULL;
}

uint32_t fake_mem_read8(uint32_t addr) {
    const uint8_t *p = fake_guest(addr);
    return p ? *p : 0;
}

uint32_t fake_mem_read16(uint32_t addr) {
    uint32_t value = 0;
    for (unsigned i = 0; i < 2; i++) {
        value |= fake_mem_read8(addr + i) << (8 * i);
    }
    return value;
}

uint32_t fake_mem_read32(uint32_t addr) {
    uint32_t value = 0;
    for (unsigned i = 0; i < 4; i++) {
        value |= fake_mem_read8(addr + i) << (8 * i);
    }
    return value;
}

void fake_mem_write8(uint32_t addr, uint32_t value) {
    uint8_t *p = fake_guest(addr);
    if (p) {
        *p = (uint8_t)value;
    }
}

void fake_mem_write16(uint32_t addr, uint32_t value) {
    for (unsigned i = 0; i < 2; i++) {
        fake_mem_write8(addr + i, value >> (8 * i));
    }
}

void fake_mem_write32(uint32_t addr, uint32_t value) {
    for (unsigned i = 0; i < 4; i++) {
        fake_mem_write8(addr + i, value >> (8 * i));
    }
}

static float float_at(uint32_t addr) {
    const uint32_t bits = fake_mem_read32(addr);
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

static uint32_t float_bits(float value) {
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return bits;
}

/* ── recording ───────────────────────────────────────────────────────────────────────── */

static void record_call(uint32_t fn, const uint32_t r[4], const float s[3], int has_s0,
                        int has_s1, int has_s2) {
    if (fake_call_count >= FAKE_CALLS) {
        return;
    }
    FakeCall *call = &fake_calls[fake_call_count++];
    memset(call, 0, sizeof *call);
    call->fn = fn;
    call->r0 = r[0];
    call->r1 = r[1];
    call->r2 = r[2];
    call->r3 = r[3];
    call->s0 = s[0];
    call->s1 = s[1];
    call->s2 = s[2];
    call->has_s0 = has_s0;
    call->has_s1 = has_s1;
    call->has_s2 = has_s2;
}

/* ── the host table ──────────────────────────────────────────────────────────────────── */

static uint32_t host_alloc(MH4UCall *call, uint32_t size, uint32_t align) {
    (void)call;
    const uint32_t mask = (align ? align : 16u) - 1u;
    heap_at = (heap_at + mask) & ~mask;
    const uint32_t block = heap_at;
    if (block + size >= FAKE_MEM_SIZE) {
        return 0;
    }
    heap_at += size;
    memset(memory + block, 0, size);
    return block;
}

static void host_free(MH4UCall *call, uint32_t addr) {
    (void)call;
    (void)addr;
}

static uint32_t host_read32(MH4UCall *call, uint32_t addr) {
    (void)call;
    return fake_mem_read32(addr);
}

static uint32_t host_read16(MH4UCall *call, uint32_t addr) {
    (void)call;
    return fake_mem_read16(addr);
}

static uint32_t host_read8(MH4UCall *call, uint32_t addr) {
    (void)call;
    return fake_mem_read8(addr);
}

static void host_write32(MH4UCall *call, uint32_t addr, uint32_t value) {
    (void)call;
    fake_mem_write32(addr, value);
}

static void host_write16(MH4UCall *call, uint32_t addr, uint32_t value) {
    (void)call;
    fake_mem_write16(addr, value);
}

static void host_write8(MH4UCall *call, uint32_t addr, uint32_t value) {
    (void)call;
    fake_mem_write8(addr, value);
}

static void *host_guest_pointer(MH4UCall *call, uint32_t addr, uint32_t size) {
    (void)call;
    if (!fake_guest(addr) || !fake_guest(addr + size - 1)) {
        return NULL;
    }
    return fake_guest(addr);
}

static void host_log(const MH4UPluginHost *self, int level, const char *message) {
    (void)self;
    if (fake_log_used + 1 < sizeof fake_log) {
        const int n = snprintf(fake_log + fake_log_used, sizeof fake_log - fake_log_used,
                               "%d:%s\n", level, message);
        if (n > 0 && (size_t)n < sizeof fake_log - fake_log_used) {
            fake_log_used += (size_t)n;
        }
    }
}

static const char *host_config(const MH4UPluginHost *self, const char *key) {
    (void)self;
    for (int i = 0; i < setting_count; i++) {
        if (strcmp(settings[i].key, key) == 0) {
            return settings[i].value;
        }
    }
    return NULL;
}

static int host_hook(const MH4UPluginHost *self, const char *name, MH4UHookFn fn, void *user) {
    (void)self;
    if (fake_hook_count >= FAKE_HOOKS) {
        return 0;
    }
    FakeHook *hook = &fake_hooks[fake_hook_count++];
    snprintf(hook->name, sizeof hook->name, "%s", name);
    hook->fn = fn;
    hook->user = user;
    return 1;
}

static int host_on_frame(const MH4UPluginHost *self, MH4UFrameFn fn, void *user) {
    (void)self;
    frame_fn = fn;
    frame_user = user;
    return 1;
}

static uint32_t host_reg(MH4UCall *call, unsigned n) {
    (void)call;
    return fake_regs[n & 15u];
}

static void host_set_reg(MH4UCall *call, unsigned n, uint32_t value) {
    (void)call;
    fake_regs[n & 15u] = value;
}

static void host_call_original(MH4UCall *call) {
    (void)call;
    fake_original_count++;
    if (fake_probe_address) {
        fake_probe_value = fake_mem_read8(fake_probe_address);
    }
    if (fake_created_enemy) {
        if (fake_factory_stand_in) {
            fake_regs[1] = fake_factory_stand_in;   /* the id layer's factory reader */
        }
        fake_regs[0] = fake_created_enemy;
    }
}

static void host_skip_original(MH4UCall *call) {
    (void)call;
    fake_skip_count++;
}

/* The runtime's guest stubs: the caller's s0-s3 readers at the stub block's read area, and the
 * s0/s1/s2 call after it. */
/* `s` is the guest's VFP state the stub runs with: call leaves the caller's s0-s3, call2
 * sets s0/s1 (to 0.0 when its floats are NULL) and leaves s2/s3. */
static uint32_t run_stub(uint32_t addr, const uint32_t *r0_r3, const float s[4]) {
    const uint32_t w0 = fake_mem_read32(addr);
    if ((w0 & 0xFFF0FFFFu) == 0xEE100A10u) {          /* vmov r0,sN; bx lr */
        const unsigned n = (w0 >> 16) & 3u;
        return float_bits(s[n]);
    }
    if (w0 == 0xED9F0A04u) {                          /* vldr s0/s1/s2; ldr pc; ... */
        const uint32_t fn = fake_mem_read32(addr + 36);
        uint32_t r[4] = {0, 0, 0, 0};
        if (r0_r3) {
            memcpy(r, r0_r3, sizeof r);
        }
        const float s[3] = {float_at(addr + 24), float_at(addr + 28), float_at(addr + 32)};
        record_call(fn, r, s, 1, 1, 1);
        return fake_guest_fn ? fake_guest_fn(fn, r, s, fake_guest_user).r0 : 0;
    }
    unknown_stub = 1;
    return 0;
}

static int in_stubs(uint32_t addr) {
    return addr >= FAKE_HEAP_AT && addr < FAKE_HEAP_AT + FAKE_STUB_SIZE;
}

static uint32_t host_call(MH4UCall *call, uint32_t addr, uint32_t a0, uint32_t a1, uint32_t a2) {
    (void)call;
    if (!addr) {
        return 0;
    }
    if (in_stubs(addr)) {
        const uint32_t args[4] = {a0, a1, a2, 0};
        const float s[4] = {fake_s[0], fake_s[1], fake_s[2], fake_s[3]};
        return run_stub(addr, args, s);
    }
    const uint32_t r[4] = {a0, a1, a2, 0};
    const float s[3] = {0.0f, 0.0f, 0.0f};
    record_call(addr, r, s, 0, 0, 0);
    return fake_guest_fn ? fake_guest_fn(addr, r, s, fake_guest_user).r0 : 0;
}

static uint32_t host_call2(MH4UCall *call, uint32_t addr, const uint32_t *r0_r3,
                           const float *s0_s1, float *s0_out) {
    (void)call;
    if (!addr) {
        return 0;
    }
    if (in_stubs(addr)) {
        float s[4] = {fake_s[0], fake_s[1], fake_s[2], fake_s[3]};
        s[0] = s0_s1 ? s0_s1[0] : 0.0f;
        s[1] = s0_s1 ? s0_s1[1] : 0.0f;
        return run_stub(addr, r0_r3, s);
    }
    uint32_t r[4] = {0, 0, 0, 0};
    float s[3] = {0.0f, 0.0f, 0.0f};
    if (r0_r3) {
        memcpy(r, r0_r3, sizeof r);
    }
    if (s0_s1) {
        s[0] = s0_s1[0];
        s[1] = s0_s1[1];
    }
    record_call(addr, r, s, s0_s1 != NULL, s0_s1 != NULL, 0);
    FakeResult result = fake_guest_fn ? fake_guest_fn(addr, r, s, fake_guest_user)
                                      : (FakeResult){0, 0.0f};
    if (s0_out) {
        *s0_out = result.s0;
    }
    return result.r0;
}

static MH4UPluginHost the_host = {
    .abi = MH4U_PLUGIN_ABI,
    .size = sizeof(MH4UPluginHost),
    .mod_name = "UC runtime",
    .mod_dir = ".",
    .program_id = 0x0004000000126300u,
    .hook = host_hook,
    .call_original = host_call_original,
    .skip_original = host_skip_original,
    .reg = host_reg,
    .set_reg = host_set_reg,
    .read32 = host_read32,
    .read16 = host_read16,
    .read8 = host_read8,
    .write32 = host_write32,
    .write16 = host_write16,
    .write8 = host_write8,
    .guest_pointer = host_guest_pointer,
    .log = host_log,
    .config = host_config,
    .on_frame = host_on_frame,
    .alloc = host_alloc,
    .free = host_free,
    .call = host_call,
    .call2 = host_call2,
};

MH4UPluginHost *fake_host(void) {
    return &the_host;
}

int fake_init(void) {
    memset(fake_regs, 0, sizeof fake_regs);
    memset(fake_s, 0, sizeof fake_s);
    return mh4u_plugin_init(&the_host, MH4U_PLUGIN_ABI);
}

void fake_set_config(const char *key, const char *value) {
    if (setting_count >= (int)(sizeof settings / sizeof settings[0])) {
        return;
    }
    Setting *setting = &settings[setting_count++];
    snprintf(setting->key, sizeof setting->key, "%s", key);
    snprintf(setting->value, sizeof setting->value, "%s", value);
}

FakeHook *fake_find_hook(const char *name) {
    for (int i = 0; i < fake_hook_count; i++) {
        if (strcmp(fake_hooks[i].name, name) == 0) {
            return &fake_hooks[i];
        }
    }
    return NULL;
}

FakeHook *fake_find_hook_last(const char *name) {
    FakeHook *found = NULL;
    for (int i = 0; i < fake_hook_count; i++) {
        if (strcmp(fake_hooks[i].name, name) == 0) {
            found = &fake_hooks[i];
        }
    }
    return found;
}

void fake_frame(void) {
    if (frame_fn) {
        frame_fn(NULL, frame_user);
    }
}

void fake_reset_calls(void) {
    memset(fake_calls, 0, sizeof fake_calls);
    fake_call_count = 0;
    fake_original_count = 0;
    fake_skip_count = 0;
    fake_created_enemy = 0;
    fake_factory_stand_in = 0;
    fake_probe_address = 0;
    fake_probe_value = 0;
    unknown_stub = 0;
}

int fake_unknown_stub(void) {
    return unknown_stub;
}

void fake_clear_log(void) {
    fake_log_used = 0;
    fake_log[0] = '\0';
}

int fake_log_contains(const char *needle) {
    return strstr(fake_log, needle) != NULL;
}
