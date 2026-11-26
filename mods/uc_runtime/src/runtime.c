/*
 * runtime.c: the mod's one native plugin.
 *
 * Decision 0013 puts the mod's native code in one library, the runtime, with a module per
 * ported monster: one fixed hook list, so adding or fixing a monster rebuilds the runtime's
 * library and redeploys the mod, while the game's code library stays as it is. This file is
 * the plugin entry point and the one list: it registers the id layer's hooks (src/ids.c) and
 * its frame call, then the module side's two hooks (src/module.c: the factory association
 * and the action dispatcher) and its first-frame self-test. Every ported monster's code is
 * reached through that same dispatcher, adding no hook of its own. src/modules.h is the
 * module table, generated from data/ids/registry.csv; a row's `ops` is the module whose C
 * file is in src/monsters/, or 0 for a data-only port.
 *
 * The hook list mod.json names is the union of the id layer's names and the module side's.
 * build_game.py puts mod.json's hooks in the code library, and the plugin asks for each of
 * them by name at load; a library built without them logs which are missing and the rest
 * still answer, as before.
 *
 * The module hooks are registered after the id layer's on purpose: the host puts a later hook
 * first in a function's chain, so the factory association sees the ported id before the id
 * layer's reader rewrites it to the stand-in.
 *
 * Build: make, in the runtime's folder (this file with src/ids.c, src/module.c and the
 * monsters' files in src/monsters/).
 * Licence: GPL-3.0-or-later.
 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "ids.h"
#include "modules.h"
#include "runtime.h"

static const MH4UPluginHost *host;

static void say(int level, const char *text) {
    host->log(host, level, text);
}

/* Registers one list of hooks. Returns how many the code library lacks. */
static int register_hooks(const MhucHook *hooks, size_t count) {
    int missing = 0;
    for (size_t i = 0; i < count; i++) {
        if (!host->hook(host, hooks[i].name, hooks[i].fn, hooks[i].user)) {
            char line[200];
            snprintf(line, sizeof line, "%s (0x%s) isn't a hook point: the code library needs "
                     "building with this mod", hooks[i].name, hooks[i].address);
            say(MH4U_LOG_ERROR, line);
            missing++;
        }
    }
    return missing;
}

/* The runtime's frame: the id layer's work first (the resource records and the text), then
 * each module's one-shot self-test. */
static void runtime_frame(MH4UCall *call, void *user) {
    (void)user;
    mhuc_ids_frame(call, NULL);
    mhuc_modules_frame(call, NULL);
}

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 4 || plugin_host->size < offsetof(MH4UPluginHost, call2) + sizeof plugin_host->call2) {
        plugin_host->log(plugin_host, MH4U_LOG_ERROR,
                         "the runtime needs the code library's ABI 4 plugin API (call2)");
        return 0;
    }
    host = plugin_host;
#if MHUC_MONSTER_COUNT + MHUC_POOLED_MONSTER_COUNT < 1
#error "the registry has no ported monster id: nothing to answer"
#endif
#if MHUC_MODULE_COUNT != MHUC_MONSTER_COUNT + MHUC_POOLED_MONSTER_COUNT
#error "src/modules.h doesn't have one entry per registered monster id: run tools/check_ids.py --write"
#endif
    mhuc_ids_start(host);
    size_t count = 0;
    const MhucHook *ids_hooks = mhuc_ids_hooks(&count);
    int missing = register_hooks(ids_hooks, count);
    if (missing == (int)count) {
        return 0;
    }
    if (!mhuc_modules_start(host)) {
        return 0;
    }
    size_t module_count = 0;
    const MhucHook *module_hooks = mhuc_modules_hooks(&module_count);
    const int module_missing = register_hooks(module_hooks, module_count);
    missing += module_missing;
    if (missing == (int)(count + module_count)) {
        return 0;
    }
    if (missing) {
        say(MH4U_LOG_WARNING, "some readers aren't hook points: the code library needs rebuilding "
                              "with this mod; the rest answer");
    }
    if (!host->on_frame(host, runtime_frame, NULL)) {
        say(MH4U_LOG_WARNING, "no frame call point: the self-test can't run");
    }
    char line[256];
    snprintf(line, sizeof line, "ready: answering MH4U's monster tables and name/notes message "
             "getters for %d permanent and %d pooled id(s), %u and up, lending %u..%u per quest, "
             "with the files each port ships and the stand-in's for the rest",
             MHUC_MONSTER_COUNT, MHUC_POOLED_MONSTER_COUNT, (unsigned)MHUC_MONSTER_FIRST,
             (unsigned)MHUC_MONSTER_POOL_FIRST, (unsigned)MHUC_MONSTER_POOL_LAST);
    say(MH4U_LOG_INFO, line);
    return 1;
}
