/*
 * fake_host.h: the runtime's fake plugin host, shared by its tests (the module contract's
 * "fake-host harness", written once).
 *
 * tests/fake_host.c gives the runtime a guest: a flat memory array, the game's heap (alloc),
 * the calls (ABI 3 `call` and ABI 4 `call2`, with the runtime's guest stubs decoded), the
 * hook table and the frame call, the registers, and the log. A test drives the runtime's
 * hooks itself and supplies the result of each guest function through `fake_guest_fn`.
 *
 * Licence: GPL-3.0-or-later.
 */
#ifndef MHUC_FAKE_HOST_H
#define MHUC_FAKE_HOST_H

#include <stddef.h>
#include <stdint.h>

#include "mh4u_plugin.h"

#define FAKE_MEM_SIZE (1u << 21)
#define FAKE_HEAP_AT  0x00080000u
#define FAKE_STUB_SIZE 384u

/* One guest function the runtime called: the guest function, its integer arguments r0-r3 and
 * its floats s0-s2 (the ones the call took). A stub-wrapped call has s2; a direct call2 has
 * s0-s1. */
typedef struct FakeCall {
    uint32_t fn, r0, r1, r2, r3;
    float s0, s1, s2;
    int has_s0, has_s1, has_s2;
} FakeCall;

typedef struct FakeHook {
    char name[64];
    MH4UHookFn fn;
    void *user;
} FakeHook;

/* What a guest function returns: r0 and its s0 (the float return). The test's handler also
 * gets the guest memory, so it can fill a point an engine function would. */
typedef struct FakeResult {
    uint32_t r0;
    float s0;
} FakeResult;

typedef FakeResult (*FakeGuestFn)(uint32_t fn, const uint32_t r0_r3[4], const float s[3],
                                  void *user);

#define FAKE_CALLS 128
#define FAKE_HOOKS 64
#define FAKE_LOG_SIZE 16384

extern FakeCall fake_calls[FAKE_CALLS];
extern int fake_call_count;
extern int fake_original_count;
extern int fake_skip_count;
extern uint32_t fake_regs[16];
extern float fake_s[4];
extern FakeHook fake_hooks[FAKE_HOOKS];
extern int fake_hook_count;
extern char fake_log[FAKE_LOG_SIZE];
extern size_t fake_log_used;
extern FakeGuestFn fake_guest_fn;
extern void *fake_guest_user;
/* The factory's rest-of-chain: when `fake_created_enemy` is set, call_original puts it in r0,
 * as the game's create returns it; when `fake_factory_stand_in` is set, it puts that stand-in
 * id in r1 first, as the id layer's factory reader does. */
extern uint32_t fake_created_enemy;
extern uint32_t fake_factory_stand_in;
/* When set, call_original reads this guest address into fake_probe_value: the id byte the
 * game's own function sees during a work-block reader (the stand-in, not the ported id). */
extern uint32_t fake_probe_address;
extern uint32_t fake_probe_value;

/* Whether a call hit a stub the fake host doesn't know (a broken stub layout). */
int fake_unknown_stub(void);

/* Guest memory, by guest address; out of range reads give 0 and writes are dropped. */
uint8_t *fake_guest(uint32_t addr);
uint32_t fake_mem_read8(uint32_t addr);
uint32_t fake_mem_read16(uint32_t addr);
uint32_t fake_mem_read32(uint32_t addr);
void fake_mem_write8(uint32_t addr, uint32_t value);
void fake_mem_write16(uint32_t addr, uint32_t value);
void fake_mem_write32(uint32_t addr, uint32_t value);

/* The fake host table and the plugin it loaded. fake_init calls mh4u_plugin_init with ABI 4
 * and returns its result. */
MH4UPluginHost *fake_host(void);
int fake_init(void);

/* A setting the module reads through host->config. */
void fake_set_config(const char *key, const char *value);

/* The hook registered under `name`: the first time it was registered, or the last (the one a
 * real chain runs first). */
FakeHook *fake_find_hook(const char *name);
FakeHook *fake_find_hook_last(const char *name);

/* The registered frame call, run as the host runs it. */
void fake_frame(void);

/* Between test sections. */
void fake_reset_calls(void);
void fake_clear_log(void);

/* Whether the log has a line containing `needle`. */
int fake_log_contains(const char *needle);

#endif
