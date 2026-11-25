# Ported monster ids

The plugin that gives a ported monster its own id. MH4U looks a monster up by id in tables
that have 124 rows (0 to 123, [reference/README.md](../../reference/README.md#mh4u-monster-tables)).
A ported monster's id starts at 124 and comes from the mod's registry,
[data/ids/registry.csv](../../data/ids/README.md), which `tools/check_ids.py` turns into
`src/ids.h`. Ids 124 to 223 are permanent; a monster ported after that range is full takes a
registry id from 256 up, and the plugin lends it a free byte of 224 to 255 for each quest that
names it (the [id pool](#the-id-pool) below). The plugin wraps the readers of those tables and
answers a registered id with the MH4U monster's rows the registry names as its stand-in, except
its resource record, which it builds for the ported id from the kinds of file the port ships;
ids 0 to 123 go to the game's function unchanged, so MH4U's own monsters are untouched.

## What it hooks

| Table | Address | Reader hooked | Id where |
|---|---|---|---|
| factory (`createEnemy`) | `0x006901f4` | the factory itself | r1 |
| data path (`enemyDataPathIndex`) | `0x00efc268` | `loadEnemyData`, `0x00689490` | r1 |
| enemy data (`enemyDataById`) | `0x00f3a024` | `0x0068882c` | r1 |
| crowns (`crownSizeTable`) | `0x00f32008` | `getCrown`, `0x0068877c` | r0 |
| list order (`monsterListOrder`) | `0x00df35b0` | `0x0061dc58` (find a monster's position) | r0 |
| icon (`monsterIconIndex`) | `0x00e06698` | `0x00c0e800`, `0x00c0e164` | r1, r2 |
| resource index (`enemyResourceIndex`) | `0x00efbd08` | `0x0068d8c8`, `0x00682ca0`, `0x00c0b830` | r1, r2, r2 |
| drops (`dropRecordIndex`) | `0x01003bec` | `0x00684b40`, `0x0092600c` | r1; the monster's own id |
| drops (`dropBaseA`, `dropBaseB`) | `0x01003ddc`, `0x01003ed4` | `0x00911f20`, `0x009357b4` | the monster's own id |
| name/notes text (`emName`, `emExp`) | `0x0109a080` slots 6, 7 | `0x00cdfb30` (`message::getFormat`) | r0 the table, r1 the id |
| name/notes text | — | `0x00cdfa18` (`message::getRecord`) | r0 the table, r1 the format entry |
| name/notes text | — | `0x00cdfa30` (`message::getRecordById`) | r0 the table, r1 the id |

Most readers take the id in a register; the plugin rewrites that register and calls the game's
function. Four read the id from the monster's data block (`this+0xe28`, byte `+0x1c0`); the
plugin swaps that byte for the stand-in, calls the game's function, and puts the real id back,
because the block is the game's own and must not keep the stand-in.

`mod.json` names each hook point with its USA v1.3.0 address; the fork's
[`tools/build_game.py`](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/tools/build_game.py)
adds them to the code library it builds. A library built without them logs which readers are
missing and the rest still answer.

## The id pool

MH4U's one-byte id leaves 124 to 223 permanent and 224 to 255 free
([0003](../../docs/decisions.md#0003-id-allocation-and-mod-saves)). A monster ported after the
permanent range is full takes a registry id from 256 up, which a quest's u32 monster list
records; 224 to 255 are the bytes the plugin lends it for each quest. No pooled monster ships
yet, so the shipped header's pooled array is empty. The checker's rules for the two ranges are
in [data/ids/README.md](../../data/ids/README.md#rules-the-tool-checks).

| Hook | Address | When |
|---|---|---|
| `QuestFlow::startQuest` | `0x00b7c010` | a quest starts: find its loaded `.mib` and rewrite the pooled ids it names |
| `aQuest::endSequence` | `0x0065a378` | the quest's return: free the bytes once the holder's status is 4 |

At quest start the plugin reads the quest id and the loaded quest-file resources from the
engine's quest holder (the same objects the port's quest-start workaround reads; the fork's
`port/src/hooks.cpp`, `QuestFlow::startQuest`). It finds the resource whose `.mib` quest id
matches, then walks the `.mib`'s large-monster waves ([specs/quest.md](../../specs/quest.md)):
each pooled id (256 and up) is rewritten in place to a free byte of 224 to 255, in the quest's
own wave order, so the same quest lends the same bytes on every player's console. The reader
hooks answer that byte with the pooled monster's rows, and build its resource record from its
stand-in exactly as for a permanent id. A retried quest start (the port rebuilds the list when
a file is late) keeps the bytes it already lent. When `aQuest::endSequence` has set the
holder's status to 4, the quest is over and the bytes are free; the next quest lends them
again. A quest that never reaches its end sequence keeps them until the next start.

The codes a lent byte needs are the same as a permanent id's: the stand-in's rows, the
resource record built for the pooled id, and the mod's own text; the pool only changes which
one-byte id those rows are addressed by. A pooled monster can't be on a guild quest card and
its hunt records go through the mod's data in the save, not MH4U's byte-indexed structures
([0003](../../docs/decisions.md#0003-id-allocation-and-mod-saves)).

The self-test (settings below) builds a synthetic `.mib` in guest memory that names the first
pooled id, lends it a byte, logs the answer, frees it again and logs that. With the shipped
registry (no pooled row) it logs that the pool is unused instead; check P1 in
[checks.md](../../docs/checks.md#ported-monster-ids) builds the plugin from
`tests/fixtures/registry-pooled.csv` to see the pooled lines.

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

The stand-in's record names paths under the stand-in's own id (`enemy\em001\...` for 124
and 125, `enemy\em015\...` for 126 and 127). On its first frame the plugin builds,
for each registered id, a record of its own from the stand-in's: the same fields and slots,
each path copied to the game's heap. A port ships only some of the record's path kinds (its
arc holds the model, motions, tail and command for 124 and 125, 125's command is her converted
MH3U AI script, 126's holds the model and its four borrowed motion lists, and 127's the model
and its three motion lists ([specs/emc.md](../../specs/emc.md)); MH4U stops the load on a path
that is not there, which is what hung a 3U session at "Now Loading" when the 125 record named
13 paths and `em125.arc` ships 6
([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)). So the registry's
`files` column, generated into `src/ids.h` as `MHUC_FILES_*` bits, names the kinds a port
ships, and the builder rewrites the monster-id token only in those kinds' paths
(`em001` -> `em124`, and the camera's `e001` -> `e124`; an effect list's trailing `_000` is
not an id and stays). The motion slots are named, `motions=0-4` or `motions=0,2,3,4`: only
those slots are rewritten and the other slots keep the stand-in's paths, because the port's
motion-number translation only targets the source slots it ships (125 keeps MH4U's
`enemy\em001\mot\em001_3` and `_4`; 126 ships MHXX's slots 0, 2, 3 and 4 and keeps the
stand-in's 1 and 5; 127 ships slots 0, 1 and 2 and keeps 3, 4 and 5). For a kind it does not
ship, the stand-in's path is
copied unchanged, so the monster loads MH4U's own camera, motion effects and effect lists
until its game's are converted; 125 ships her own sound (`mhuc convert monster`, issue
#158). The record, its slots and its strings are one block from the game's own heap (`alloc`,
ABI 2), and it is kept for the run.

| Kind in `files` | The record's paths |
|---|---|
| `model` | +0x00, the model |
| `motions=0,2` | +0x04, the six motion lists, and +0x0c, the second motion list; each named slot is the port's and the others keep the stand-in's path |
| `camera` | +0x08, the camera |
| `tail` | +0x10, the tail model |
| `mef` | +0x14, the motion effects |
| `sound` | +0x1c, the sound |
| `cmd` | +0x20 slot 3, the command/EMC |
| `efl` | +0x24 and +0x28, the effect lists |

The `+0x20` slots 0 to 2 are empty in MH4U's own records and have no kind, so they can only
keep the stand-in's path. A new kind is added to `data/ids/registry.csv`'s checker
(`tools/check_ids.py`) and to the plugin's path map together; the `motions` slot mask is
emitted into the header beside the bits (`MHUC_MOTION_SLOT`).

`enemyResource::get` is answered with the built record's +0x14 field. `enemyResource::load`
and `enemyResource::effectLists` (0x00c0b830, called with the spawned monster's own id after
the loader) read the record from the table itself, and ids 124 and up have no row there (the
table ends where `enemyDataPaths` begins), so the hook points the stand-in's row at the built
record for the call, runs the reader as the stand-in, and puts the row back. The data path
(`enemyDataPathIndex`, 0x00efc268) still answers with the stand-in's: the ports ship no
MH4U-format `.emd`/`.etd` yet, so their monster data loads from the stand-in's.

## The name and notes text

MH4U answers a monster's name and its Hunter's Notes text by the id: the message tables
`emName` and `emExp` are loaded from `core_common.arc` and their message N names monster N
(specs/lmd.md). The game loads 71 message tables into the pointer array at `0x0109a080`, with
`emName` at slot 6 and `emExp` at slot 7, and the per-id getters are `0x00cdfb30` (the 16-byte
format entry), `0x00cdfa18` (the 12-byte string record from a format entry) and `0x00cdfa30`
(the record by id). The plugin wraps the three: a registered id is answered with its own
format entry (a copy of the stand-in id's, so the message object's layout words stay), its own
string record and a UTF-16 string in the game's heap. Every other id and every other message
table goes to the game's getters unchanged.

The text comes from the mod's `text/monster_text.bin`: one entry per registered id, its name
from [the registry](../../data/ids/README.md) and its notes from the source game's own table,
recorded per id in [data/ids/notes.csv](../../data/ids/README.md#the-notes-source). The file
holds no MH4U text. Build it where the mod's folder can see it (outside the repository):

```bash
MHUC_DUMPS=<dumps> mhuc text build --dumps <dumps> \
    --out <mod library>/<the mod's folder>/text/monster_text.bin
tools/check_text.py --mod <that file>
```

Until the file exists, the plugin logs a warning and the ported ids keep no text (the game's
getters return nothing for them). The notes' language is the source game's: MH3U USA gives
English, MHXX JPN gives Japanese until the port reads MHGU's English text. A GU monster's
English notes are therefore still content work, not this plugin's.

## What it does not do yet

- **The Hunter's Notes list** that walks all 124 rows (`0x0061df4c`) and the notes list's sort.
  Only the position lookup (`0x0061dc58`) is answered, so the textual getters above answer an
  id the UI already shows, but a ported monster is not added to the Notes list itself.
- **The data path** stays the stand-in's until the ports ship MH4U-format `.emd`/`.etd`.
- **The pool's real path.** No pooled monster ships and no quest names one yet, so the quest
  start and end hooks have only run against the synthetic `.mib` of check P1; a real quest with
  a pooled monster is check P2 and is not done, and whether the post-quest screens still read
  the tables after the end sequence is unverified. A quest that never reaches its end sequence
  keeps its bytes until the next quest starts.
- **The port's camera, motion effects and effect lists.** A port ships its model, motions,
  tail and command, and 125 her sound (126 and 127 ship only their models and motions); the
  record keeps
  the stand-in's paths for the camera, motion effects and effect lists, and their files are
  MH4U's until the port's game has them converted.
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
MHUC_DUMPS=<dumps> mhuc text build --dumps <dumps> \
    --out <user directory>/mods/<the mod's folder>/text/monster_text.bin
python3 <fork>/tools/build_game.py --dump "MH4U v1.3.0 update.cia" --install <Azahar user directory>
```

A run logs `ready: answering MH4U's monster tables and name/notes message getters for 4
permanent and 0 pooled id(s), 124 and up, lending 224..255 per quest, with the files each port
ships and the stand-in's for the rest`, then `text: 2 of 2 entry(ies) from
text/monster_text.bin; every registered id has a name and notes`, then one line per reader the first time it answers a registered id and one the first
time it passes an MH4U id through, for example `factory: id 124 -> stand-in 1`; the resource
readers log `resource index: id 124 -> its own record`, `resource load: id 124 -> its own
record` and `effect lists: id 124 -> its own record`. A quest that names a pooled monster logs
`quest 60012: pooled id 256 -> lent 224`, and its end logs `quest 60012 ends: freed the pool
byte(s) 224`.

## Settings

`mod.json` holds the defaults; a `config.ini` in the installed mod's folder overrides them
(`key = value` lines).

| Key | Default | Means |
|---|---|---|
| `selftest` | `0` | `1`: on the first frame, log what every reader answers for each registered id, the paths of the resource record built for it and which kinds and motion slots it ships and keeps the stand-in's for, the path the stand-in's data comes from, the name and notes text and the three message getters' answers, that ids 0 to 123 pass through, and a pooled id lent, answered and freed by a synthetic quest. The check in [checks.md](../../docs/checks.md#ported-monster-ids) uses it. |

## The check

The headless check and what it must show are in
[checks.md](../../docs/checks.md#ported-monster-ids).
