# Force a monster action

The mod's first native plugin. It makes a chosen action play on a monster, so a ported move
can be watched without waiting for the AI to pick it: the plugin's check R1p in
[checks.md](../../docs/checks.md).

## What it does

A monster's current action lives in two bytes of its work block, a category and an index,
and the AI changes it by calling `uEnemy`'s action setter (`0x0090ef74`, `this, category,
index, mode`). The setter also initializes the action's state, which is why writing the bytes
later, at the dispatcher (vtable slot 44, `0x006e9cac`), is not enough: the AI's next setter
call resets the state and the handler stays on its first frame, holding a pose.

The plugin wraps the setter through the fork's plugin API. For the chosen monster it replaces
the category and index arguments with the forced pair, so the AI's change becomes the forced
action and the game's own setter initializes it. The dispatcher hook is kept only as a
fallback for a code library built before the setter hook existed; it logs a warning, and that
library needs rebuilding.

`mod.json` gives the setter the name `uEnemy::setAction` and the dispatcher
`uEnemy::dispatchAction`, with their USA v1.3.0 addresses;
[`tools/build_game.py`](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/tools/build_game.py)
adds both hook points to the code library it builds.

## Build

```bash
make        # force_action.so next to mod.json
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. Licence: GPL-3.0-or-later, like the rest of the mod.

## Install

Add the folder to the port's mod library and turn it on, then build the code library so the
game has the plugin's hook points:

```bash
python3 <fork>/tools/mods.py add mods/force_action
python3 <fork>/tools/mods.py enable "Force a monster action"
python3 <fork>/tools/build_game.py --dump "Monster Hunter 4 Ultimate Update v1.1 (USA) Decrypted.cia" \
    --install <Azahar user directory>
```

The build prints the mod's hooks and lists the plugin beside the code library. A run then
logs `plugin Force a monster action: ... ready: forcing action 3/17 on monster 1 via the
action setter`, one `first force:` line, and one line each time the AI's action changes. If
the log says the action setter isn't a hook point, the code library was built before that
hook: rebuild it with the command above.

## Settings

`mod.json` holds the defaults; a `config.ini` in the installed mod's folder overrides them
(`key = value` lines).

| Key | Default | Means |
|---|---|---|
| `action` | `3/17` | the action to force, as `category/index` (decimal or `0x`), each 0–255 |
| `monster` | `1` | the monster id to force it on (the work block's byte at `+0x1c0`), or `any`; Rathian is id 1 |
| `hold` | `1` | `1`: replace the AI's action with the forced pair on every setter call; `0`: force the first setter call once, then leave the AI alone |

Setting no `action` (an empty value) keeps `3/17`; an `action` that isn't a category and an
index separated by `/` (or `:`) makes the plugin refuse to start, and the port logs why and
runs without it. The same goes for a `monster` that isn't an id or `any`, and for a `hold`
that isn't `0` or `1`.

The in-game check that uses the plugin is R1p in
[checks.md](../../docs/checks.md#the-plugins-check-r1p); R1 is the code check that compares
the motion each action starts. The plugin's hook points are part of the code library, so a
rebuild is needed whenever `mod.json`'s `hooks` change.
