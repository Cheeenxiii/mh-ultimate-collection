# Plugin API

**Decision:** mods hook game functions by name through `mod.json`; `build_game.py` merges those hooks into the build's hook points and lists each mod's native library next to the code library; the port loads the libraries and runs every hook on a function as a chain: the last mod first, then the port's own hook, then the game's function. Implemented on the engine fork (`Cheeenxiii/MH4UltimateDC-fork`, branch `uc/plugin-api`, on `uc/main`), tested on recompiled test code. The in-game check is written down at the end for the first session with game files.

## What the fork had

Read before designing: `port/src/hooks.cpp`, `port/src/hook_address.h`, `tools/recomp/runtime/recomp.h`, `tools/build_game.py`, `tools/recompile.py`, `tools/mods.py`, `docs/MODS.md`.

| Piece | How it works | What it meant for plugins |
|---|---|---|
| Hook points | `config/hooks.txt` lists functions (USA address + name); the recompiler wraps each in `RC_HOOK_POINT`, which calls `rc_hooks[i]` if set | a function needs to be a hook point **at build time**; mods must add theirs before recompiling |
| `RHookFn(RCtx*, RFunc original)` | one slot per point, no user pointer | several hooks on one function need a dispatcher that knows which chain it runs |
| `RCodeInfo.set_hook`, `hook_names` | the library names its hook points; `FindHookPoint` finds them by name in any version | hooks by name work for USA v1.3.0 and EUR v1.1.0 alike |
| Version shifts | `build_game.translate_tables` moves USA addresses to EUR's | a mod's address-given hook moves the same way |
| Mods | `tools/mods.py`: a library of mods, `mod.json` with text fields; code patches applied before recompiling; one code mod at a time | the natural home for `hooks`, `plugin`, `config`; build time already reads the mods |

## The pieces

```
mod.json (hooks, plugin, config)
   │  tools/mods.py read_manifest keeps them; plugin-only mods are valid
   ▼
tools/mod_hooks.py ── names → USA addresses (hooks.txt, symbols.txt, functions.tsv)
   │  merge with config/hooks.txt, conflicts stop the build
   ▼
tools/build_game.py ── recompiles with the merged hook points (shifted for EUR)
   │  writes recomp/<program id>.plugins.tsv next to the library
   ▼
port: ARM_Recomp::LoadCode
   ├─ Plugins::Begin(info) → RCodeInfo whose set_hook records the port's hooks
   ├─ Hooks::Install(...)   (the port's own hooks, unchanged)
   └─ Plugins::Load(path)   reads the .tsv, opens each library, calls mh4u_plugin_init
          plugin_host.h: chains per hook point, 256 fixed dispatchers Slot<K>
```

### `mod.json`

```json
{
  "hooks": ["sMhPad::update", {"name": "uMyFind::run", "address": "0x00123456"}],
  "plugin": {"windows": "bin/m.dll", "linux": "bin/m.so", "macos": "bin/m.dylib", "android": "bin/m.so"},
  "config": {"speed": 2}
}
```

- Hooks are names, never bare addresses. A name the project hasn't got needs the USA v1.3.0 address next to it; the build moves it to EUR's with the version shifts, like the project's own.
- Conflicts reported (all at once, each naming both sides): one name at two addresses; two names for one address; a name the project doesn't know without an address. Two mods hooking one function is not a conflict; the build log says they chain.
- `config` gives defaults; the player's `config.ini` in the mod's library folder overrides them. Both end up in the plugin list.

### `include/mh4u_plugin.h`

`int mh4u_plugin_init(const MH4UPluginHost *host, uint32_t abi)`; nonzero means started. Each plugin gets its own host table and passes it back as `self`.

| Member | Purpose |
|---|---|
| `abi`, `size` | `MH4U_PLUGIN_ABI` (1) and the table's size: members are only ever appended |
| `mod_name`, `mod_dir`, `program_id` | who and where, and which game (USA or Europe) |
| `hook(self, name, fn, user)` | wrap a hook point by name (init only); 0 if the library lacks it |
| `call_original(call)`, `skip_original(call)` | run the rest of the chain; or return to the game's caller |
| `reg`, `set_reg` | guest r0-r15 |
| `read32/16/8`, `write32/16/8` | guest memory, through the same accessors as recompiled code (Azahar's page table) |
| `guest_pointer(call, addr, size)` | a host pointer for a span inside one mapped page, else NULL |
| `log(self, level, text)` | the port's log, prefixed with the mod's name |
| `config(self, key)` | the mod's setting, or NULL |
| `on_frame(self, fn, user)` | once per engine frame, at `sMhMain::frame` |

The API never exposes `RCtx` or `RCodeInfo`: `MH4UCall` is opaque, so the recompiler's structures can change without breaking plugins.

### Loading and failure

- Plugins load in mod order. A missing library, a missing `mh4u_plugin_init`, or an init returning 0 turns that mod's plugin off for the run with a log line; any hooks or frame calls its init asked for are taken back. The game still starts.
- The plugin list is rewritten (or removed) by every build, so it always matches the library's hook points. A plugin asking for a hook the library lacks gets 0 and a log line telling the player to build again.
- `Reset` on a new library puts the port's own hooks back on the old points and closes the old plugins.

### Safety

A native plugin is arbitrary code with the player's permissions. Still to do in the launcher (`port/app`): warn before enabling a mod whose `mod.json` has `plugin`, and show a badge for catalog entries with one (a `plugin: true` field in `tools/mods_catalog.json`, which the catalog test would then require to have a `sha256`, as code patches already do).

## Files changed in the fork

| File | Change |
|---|---|
| `include/mh4u_plugin.h` | new: the C ABI |
| `port/src/plugin_host.h` | new: chains, dispatchers, host table, plugin list parser (no Azahar) |
| `port/src/plugins.h`, `port/src/plugins.cpp` | new: Azahar glue (DynamicLibrary, log, list path) |
| `port/src/arm_recomp.cpp` | `LoadCode`: `Hooks::Install(Plugins::Begin(info))`, then `Plugins::Load(path)` |
| `port/CMakeLists.txt` | the three new sources in `mh4u_backend` |
| `tools/mod_hooks.py` | new: resolve, merge, conflicts, plugin list |
| `tools/mods.py` | `read_manifest` keeps `hooks`, `plugin`, `config`; plugin-only mods are valid (`layout` "plugin") |
| `tools/build_game.py` | merges the enabled mods' hooks before recompiling; writes the plugin list next to the library (and the installed copy) |
| `tools/plugin_sample/sample_plugin.c` | new: a complete sample plugin, configurable for tests |
| `tests/test_plugin_host.py` | new: chains, order, skip, Thumb, frames + guest memory, missing hook, failed init, bad library, reset, list round trip, on the `rh_set_hook` harness |
| `tests/test_mod_hooks.py` | new: merge, conflicts, names, manifest fields, library, build integration |
| `docs/MODS.md` | new section "Native plugins" |

Not changed: `config/hooks.txt`, `hooks.cpp`, the recompiler, the code-library ABI (`RC_HOST_VERSION`). Upstream can take the plugin layer as is, or leave it: nothing else depends on it.

## Limits and next steps

- Hooks need a rebuild of the code library; there is no run-time hooking of arbitrary functions. That matches how the port works and keeps unhooked functions at full speed.
- 256 functions can carry plugin chains at once (`PluginHost::SLOTS`); raise it if needed.
- Frame calls run inside the engine's frame function, before the game's own frame. Calls at other points (area load, quest start) are just hooks on those functions.
- Plugins can't add new guest code or allocate guest memory yet. The underwater work will need guest allocations: next ABI step, `alloc`/`free` through the game's own heap functions, once found (see [id-tables.md](id-tables.md)).
- `mods.py status` doesn't yet flag a plugin list older than the enabled mods; the build record should carry the hook list's fingerprint.

## In-game check (first session with game files)

Written for a Windows or Linux PC with the USA v1.3.0 dump and the port installed.

1. Build the sample plugin for the PC: `cc -shared -fPIC -Iinclude tools/plugin_sample/sample_plugin.c -o sample_plugin.so` (`.dll` with llvm-mingw on Windows).
2. Make a mod folder `sample-plugin/` with that library and this `mod.json`: `{"name": "Sample plugin", "hooks": ["sMhPad::update"], "plugin": {"linux": "sample_plugin.so", "windows": "sample_plugin.dll"}, "config": {"hook": "sMhPad::update", "op": "add", "value": "0", "frames_at": "0"}}`. `python3 tools/mods.py add sample-plugin`.
3. `python3 tools/mod_hooks.py`: expect "Sample plugin: hooks sMhPad::update, which config/hooks.txt hooks too".
4. `python3 tools/build_game.py --dump <dump> --install`: expect "mods' hooks:" and "native plugins: 1".
5. Start the game. The log shows `plugins: Sample plugin: plugin loaded` and `sample plugin ready`. The game plays normally (value 0 changes nothing), and the port's own pad features (skip button, mouse camera) still work, which proves the chain runs the port's hook.
6. Set `frames_at` to a free guest address the project knows to be unused, rebuild, and watch it count frames with the runner's memory read. Record pass or fail, not the memory's contents.
7. Remove the mod, build again: the `.plugins.tsv` is gone and the log has no plugin lines.
