/*
 * runtime.h: what the runtime's entry point and its parts share.
 *
 * The mod's native code is one plugin, the runtime, with a module per ported monster
 * (docs/decisions.md#0013). src/runtime.c owns the plugin entry point and registers the one
 * fixed hook list; src/ids.c answers the monster-id-indexed tables, the resource records and
 * the name and notes text; src/modules.h is the generated module table.
 *
 * Licence: GPL-3.0-or-later.
 */
#ifndef MHUC_RUNTIME_H
#define MHUC_RUNTIME_H

#include <stddef.h>

#include "mh4u_plugin.h"

/* One hook the runtime asks the code library for. mod.json names the same list: build_game.py
 * puts those names in the code library and the plugin asks for each of them by name. */
typedef struct MhucHook {
    const char *name;    /* the hook point's name */
    const char *address; /* its USA v1.3.0 address, for the log when the library lacks it */
    MH4UHookFn fn;
    void *user;
} MhucHook;

/* The id layer's hooks, in the order src/ids.c registers them. mod.json names the same
 * set; build_game.py needs the names, not their order. */
const MhucHook *mhuc_ids_hooks(size_t *count);

/* Takes the host and reads the id layer's settings; called once at init. */
void mhuc_ids_start(const MH4UPluginHost *host);

/* The id layer's per-frame work, registered by the runtime (src/ids.c). */
void mhuc_ids_frame(MH4UCall *call, void *user);

/* The registry id a factory id names: the id itself for a permanent registered id, or the
 * pooled registry id a lent byte answers for; 0 for MH4U's own ids and free pool bytes. The
 * module dispatcher needs it at uEnemyFactory::create, where a quest's lent byte is what the
 * game passes. */
uint32_t mhuc_ids_registry_id(uint32_t id);

/* The module side (src/module.c, src/monsters/<key>.c): its two hooks (the factory
 * association and the action dispatcher), its start and its first-frame self-test. The
 * runtime registers the module hooks after the id layer's, so the factory association runs
 * first and sees the ported id before the id layer rewrites it. */
const MhucHook *mhuc_modules_hooks(size_t *count);
int mhuc_modules_start(const MH4UPluginHost *host);
void mhuc_modules_frame(MH4UCall *call, void *user);

#endif
