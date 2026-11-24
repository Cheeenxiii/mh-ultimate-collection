# Force a monster action

The mod's first native plugin. It makes a chosen action play on a monster, so a ported move
can be watched without waiting for the AI to pick it: check R1 in
[checks.md](../../docs/checks.md).

## What it does

The game runs a monster's current action from two bytes of its work block, a category and an
index. `uEnemy`'s action dispatcher (vtable slot 44, `0x006e9cac`) loads the work block from
`this+0xe28` and branches on the category byte at `+0x1ca`; the case it reaches switches on the
index byte at `+0x1cb`. The plugin wraps the dispatcher through the fork's plugin API and
writes those two bytes before the game reads them. It logs each forced action to the port's
log, so the run shows what was forced over what the AI had chosen.

`mod.json` gives the dispatcher the name `uEnemy::dispatchAction` and its USA v1.3.0 address;
[`tools/build_game.py`](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/tools/build_game.py)
adds that hook point to the code library it builds.

## Build

```bash
make        # force_action.so next to mod.json
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. Licence: GPL-3.0-or-later, like the rest of the mod.

## Install

Add the folder to the port's mod library and turn it on, then build the code library so the
game has the plugin's hook point:

```bash
python3 <fork>/tools/mods.py add mods/force_action
python3 <fork>/tools/mods.py enable "Force a monster action"
python3 <fork>/tools/build_game.py --dump "Monster Hunter 4 Ultimate Update v1.1 (USA) Decrypted.cia" \
    --install <Azahar user directory>
```

The build prints the mod's hooks and lists the plugin beside the code library; a run then
logs `plugin Force a monster action: ready: forcing action 3/17 on monster 1`.

## Settings

`mod.json` holds the defaults; a `config.ini` in the installed mod's folder overrides them
(`key = value` lines).

| Key | Default | Means |
|---|---|---|
| `action` | `3/17` | the action to force, as `category/index` (decimal or `0x`), each 0–255 |
| `monster` | `1` | the monster id to force it on (the work block's byte at `+0x1c0`), or `any`; Rathian is id 1 |
| `hold` | `1` | `1`: force the action again each time the AI changes it, so it replays; `0`: force it once |

Setting no `action` (an empty value) keeps `3/17`; an `action` that isn't a category and an
index separated by `/` (or `:`) makes the plugin refuse to start, and the port logs why and
runs without it. The same goes for a `monster` that isn't an id or `any`, and for a `hold`
that isn't `0` or `1`.

The check that uses the plugin, with its sample ids and the matching procedure for MHXX and
MH3U, is R1 in [checks.md](../../docs/checks.md#monster-actions). Building the code library
with the mod enabled is a separate step: a recompile.
