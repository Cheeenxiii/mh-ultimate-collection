/*
 * runtime.c: the mod's one native plugin.
 *
 * Decision 0013 puts the mod's native code in one library, the runtime, with a module per
 * ported monster: one fixed hook list, so adding or fixing a monster rebuilds the runtime's
 * library and redeploys the mod, while the game's code library stays as it is. This file is
 * the plugin entry point and the one list: it registers the id layer's hooks (src/ids.c) and
 * its frame call, and every ported monster's module will be reached through that same
 * dispatcher, adding no hook of its own. src/modules.h is the module table, generated from
 * data/ids/registry.csv; issue #215 fills it with the first monster's code.
 *
 * The hook list mod.json names is the one mhuc_ids_hooks returns. The two must agree:
 * build_game.py puts mod.json's hooks in the code library, and the plugin asks for each of
 * them by name at load; a library built without them logs which are missing and the rest
 * still answer, as before.
 *
 * Build: make, in the runtime's folder (this file with src/ids.c).
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

MH4U_PLUGIN_EXPORT int mh4u_plugin_init(const MH4UPluginHost *plugin_host, uint32_t abi) {
    if (abi < 1 || plugin_host->size < offsetof(MH4UPluginHost, alloc)) {
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
    const MhucHook *hooks = mhuc_ids_hooks(&count);
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
    if (missing == (int)count) {
        return 0;
    }
    if (missing) {
        say(MH4U_LOG_WARNING, "some readers aren't hook points: the code library needs rebuilding "
                              "with this mod; the rest answer");
    }
    if (!host->on_frame(host, mhuc_ids_frame, NULL)) {
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
