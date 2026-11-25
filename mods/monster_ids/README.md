# Ported monster ids

The plugin that gives a ported monster its own id. MH4U looks a monster up by id in tables
that have 124 rows (0 to 123, [reference/README.md](../../reference/README.md#mh4u-monster-tables)).
A ported monster's id starts at 124 and comes from the mod's registry,
[data/ids/registry.csv](../../data/ids/README.md), which `tools/check_ids.py` turns into
`src/ids.h`. The plugin wraps the readers of those tables and answers a registered id with
the MH4U monster's rows the registry names as its stand-in, except its resource record, which
it builds for the ported id so the game loads the port's files from their own paths; ids 0 to
123 go to the game's function unchanged, so MH4U's own monsters are untouched.

## What it hooks

| Table | Address | Reader hooked | Id where |
|---|---|---|---|
| factory (`createEnemy`) | `0x006901f4` | the factory itself | r1 |
| data path (`enemyDataPathIndex`) | `0x00efc268` | `loadEnemyData`, `0x00689490` | r1 |
| enemy data (`enemyDataById`) | `0x00f3a024` | `0x0068882c` | r1 |
| crowns (`crownSizeTable`) | `0x00f32008` | `getCrown`, `0x0068877c` | r0 |
| list order (`monsterListOrder`) | `0x00df35b0` | `0x0061dc58` (find a monster's position) | r0 |
| icon (`monsterIconIndex`) | `0x00e06698` | `0x00c0e800`, `0x00c0e164` | r1, r2 |
| resource index (`enemyResourceIndex`) | `0x00efbd08` | `0x0068d8c8`, `0x00682ca0` | r1, r2 |
| drops (`dropRecordIndex`) | `0x01003bec` | `0x00684b40`, `0x0092600c` | r1; the monster's own id |
| drops (`dropBaseA`, `dropBaseB`) | `0x01003ddc`, `0x01003ed4` | `0x00911f20`, `0x009357b4` | the monster's own id |

Most readers take the id in a register; the plugin rewrites that register and calls the game's
function. Four read the id from the monster's data block (`this+0xe28`, byte `+0x1c0`); the
plugin swaps that byte for the stand-in, calls the game's function, and puts the real id back,
because the block is the game's own and must not keep the stand-in.

`mod.json` names each hook point with its USA v1.3.0 address; the fork's
[`tools/build_game.py`](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/tools/build_game.py)
adds them to the code library it builds. A library built without them logs which readers are
missing and the rest still answer.

## The resource record

MH4U loads a monster's own files from the `0x2c`-byte record `enemyResourceIndex[id]`
(0x00efbd08) points to: eleven pointers, each to an array of path slots, where a slot holds 0
or a pointer to a path string. The readers are `enemyResource::get` (0x0068d8c8, which
returns the record's field at +0x14), `enemyResource::load` (0x00682ca0, which loads the
paths of the fields at +0x00 to +0x28) and the effect allocator at 0x00c0b830 (which reads
the effect lists at +0x24 and +0x28).

| Offset | What | Slots |
|---|---|---|
| `+0x00` | model | 1 |
| `+0x04` | motion lists | 6 |
| `+0x08` | camera | 1 |
| `+0x0c` | a second motion list, ending at its first empty slot | up to 6 |
| `+0x10` | tail model | 2 |
| `+0x14` | motion effects | 2 |
| `+0x18` | unused (null in MH4U's own records) | 1 |
| `+0x1c` | sound | 1 |
| `+0x20` | four extra paths; slot 3 is the command (EMC) | 4 |
| `+0x24` | effect lists | 1 |
| `+0x28` | a second effect list | 1 |

The stand-in's record names `enemy\em001\...` paths. On its first frame the plugin builds,
for each registered id, a record of its own from the stand-in's: the same fields and slots,
each path copied to the game's heap and its monster-id token rewritten to the ported id
(`em001` -> `em124`, and the camera's `e001` -> `e124`; an effect list's trailing `_000` is
not an id and stays). The record, its slots and its strings are one block from the game's own
heap (`alloc`, ABI 2), and it is kept for the run.

`enemyResource::get` is answered with the built record's +0x14 field. `enemyResource::load`
reads the record from the table itself, and ids 124 and up have no row there (the table ends
where `enemyDataPaths` begins), so the hook points the stand-in's row at the built record for
the call, runs the loader as the stand-in, and puts the row back. The data path
(`enemyDataPathIndex`, 0x00efc268) still answers with the stand-in's: the ports ship no
MH4U-format `.emd`/`.etd` yet, so their monster data loads from the stand-in's.

## What it does not do yet

- **Name and notes text.** The monster's name and description are messages named by the id
  (`emName`, `emExp`); a ported id needs a message of its own in the mod's text. Its reader is
  the message layer, not one per-monster getter, so this plugin doesn't hook it.
- **The Hunter's Notes list** that walks all 124 rows (`0x0061df4c`) and the notes list's sort.
  Only the position lookup (`0x0061dc58`) is answered.
- **The effect allocator** at `0x00c0b830`, the third reader of `enemyResourceIndex`, is not
  hooked: it is called with the spawned monster's own id after `enemyResource::load`, so a
  ported id reads past the table there. It needs a hook point and a build.
- **The data path** stays the stand-in's until the ports ship MH4U-format `.emd`/`.etd`.
- **The monster is the stand-in.** Except for its resource record, the tables answer with the
  stand-in, and the monster's data block still holds the stand-in's own id byte, so a spawned
  monster is MH4U's monster. The port's own rows replace the stand-in when
  [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48) and
  [#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49)'s converted files are
  installed.

## Build

```bash
make        # monster_ids.so next to mod.json
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. `src/ids.h` is generated, not edited: run `python3 tools/check_ids.py
--write` after changing the registry. Licence: GPL-3.0-or-later, like the rest of the mod.

## Install

```bash
python3 <fork>/tools/mods.py add mods/monster_ids
python3 <fork>/tools/mods.py enable "Ported monster ids"
python3 <fork>/tools/build_game.py --dump "MH4U v1.3.0 update.cia" --install <Azahar user directory>
```

A run logs `ready: answering MH4U's monster tables for 2 ported id(s), 124 and up, ...`, then
one line per reader the first time it answers a registered id and one the first time it passes
an MH4U id through, for example `factory: id 124 -> stand-in 1`; the resource readers log
`resource index: id 124 -> its own record` and `resource load: id 124 -> its own record`.

## Settings

`mod.json` holds the defaults; a `config.ini` in the installed mod's folder overrides them
(`key = value` lines).

| Key | Default | Means |
|---|---|---|
| `selftest` | `0` | `1`: on the first frame, log what every reader answers for each registered id, the paths of the resource record built for it, the path the stand-in's data comes from, and that ids 0 to 123 pass through. The check in [checks.md](../../docs/checks.md#ported-monster-ids) uses it. |

## The check

The headless check and what it must show are in
[checks.md](../../docs/checks.md#ported-monster-ids).
