# Ids

The registry of every id a ported content takes in MH4U. One file, `registry.csv`, read by
`tools/check_ids.py`; the plugin `mods/monster_ids` gets its ids from the header the tool
generates. Decision [0003](../docs/decisions.md#0003-id-allocation-and-mod-saves) settles the
rule: one registry, ids only ever grow, and the run time reads them from here.

| Column | Meaning |
|---|---|
| `kind` | what kind of id: `monster` today; another kind needs its range and rules in `tools/check_ids.py` first |
| `id` | the id in MH4U. Monsters start at 124 (MH4U uses 0 to 123); 124 to 223 are permanent and 224 to 255 are the pool lent per quest ([0003](../docs/decisions.md#0003-id-allocation-and-mod-saves)), so a permanent monster row stops at 223; `tools/check_ids.py` still allows 255 until [#101](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/101) |
| `key` | the content's name in the registry, lowercase words joined by hyphens, unique |
| `source_game` | which game the content comes from: `mh4u`, `mh3u`, `mhxx` or `mhgu` |
| `source_key` | the content's name in that game: a monster's `emNNN` |
| `name` | the content's name, for review |
| `stand_in` | the MH4U monster id whose table rows answer for this id until the port ships the content's own rows |
| `files` | the kinds of file the port ships, comma-separated: `model`, `motions`, `camera`, `tail`, `mef`, `sound`, `cmd`, `efl` (the resource record's path kinds, below). `motions` takes the number of motion-list slots shipped from slot 0, as `motions=3`; the slots above keep the stand-in's paths |
| `notes` | where the content comes from, and anything the next reader needs |

The rows a registered id answers with are the game's own, read by the plugin's hooks: the
ported monster's id is answered with that MH4U monster's rows. One exception: MH4U loads a
monster's own files from the paths in the record `enemyResourceIndex[id]` (0x00efbd08) points
to, and the plugin builds a record for each registered id on its first frame, from the
stand-in's. For a kind in the row's `files` the path is rewritten to the ported id
(`enemy\em001\...` -> `enemy\em124\...`); for a kind it does not ship the stand-in's path is
kept, so MH4U's own file loads. The data path (`enemyDataPathIndex`) still answers with the
stand-in's: the ports ship no MH4U-format `.emd`/`.etd` yet, and their monster data is the
stand-in's. Changing a `stand_in` is not moving an id.

The resource record is a `0x2c`-byte record of eleven pointers: the model, six motion lists,
the camera, a second motion list, the tail model, the motion effects, an unused field, the
sound, four extra paths (the command/EMC is the fourth), the effect lists and a second effect
list. The plugin's [README](../mods/monster_ids/README.md#the-resource-record) has the
offsets, and check P1 in [checks.md](../docs/checks.md#ported-monster-ids) shows the built
record's paths. A port packages its files under those paths
(`enemy\em124\mod\em124`, `enemy\em124\mot\em124_0`, ...).

## The kinds a port ships

MH4U does not tolerate a resource record that names a file it does not have: a 3U session
hung at "Now Loading" on the record built for 125, which named 13 paths while `em125.arc`
ships 6 ([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)). So a port
ships only some kinds and the record keeps the stand-in's path for the rest. A kind is one
group of paths in the record:

| Kind | The record's paths | 124 ships | 125 ships |
|---|---|---|---|
| `model` | the model | yes | yes |
| `motions` | the six motion lists and the second motion list; `motions=N` is the first N slots from slot 0 | `motions=5` (0-4) | `motions=3` (0-2) |
| `camera` | the camera | no | no |
| `tail` | the tail model | yes | yes |
| `mef` | the motion effects | no | no |
| `sound` | the sound | no | no |
| `cmd` | the command/EMC | yes | yes |
| `efl` | the effect lists | no | no |

124's `em124.arc` holds the model, five motion lists, the tail and the command; 125's holds
the model, three motion lists, the tail and the command. Until a port's own camera, motion
effects, sound and effect lists are converted, its monster loads MH4U's own from the stand-in's
paths (`enemy\em001\...`); 125's record also keeps MH4U's `enemy\em001\mot\em001_3` and `_4`
for the two motion slots it does not ship, so its motion-number translation only targets slots
0 to 2. The motion-effect and effect-list formats the `mef` and `efl` kinds carry are laid out
and checked on the three games' monster archives ([mef](../../specs/mef.md),
[efl](../../specs/efl.md), checks FX1, FX2, EF1 and EF2); their records and blocks are not
understood yet, so a port still ships neither kind.

A new kind is added to `tools/check_ids.py`'s `FILE_KINDS` and to the plugin's path map
together; the generated header's `MHUC_FILES_*` bits and each row's `motions` count are what
the plugin's record builder reads.

125's command is her own AI script: MH3U's EMC is an older format, so her port converts it at
build time (version, 23 group rows and the 15 opcodes whose argument count differs) rather than
running MH4U Rathian's, [specs/emc.md](../specs/emc.md#what-a-converter-must-do). The ported
id's record names it, and [#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49)
ships it with the rest of her files.

## Rules the tool checks

- every id is inside its kind's range and no two rows share one;
- monster ids are consecutive from 124, with no gap: every id up to the highest one used needs
  a row in each table indexed by id;
- a key, a source game and a source key are valid, and every row has a name and a stand-in;
- `files` is not empty, every kind in it appears once, and `motions` gives a count in 1..6;
- `mods/monster_ids/src/ids.h` is exactly what this file generates, including each row's
  `files` bits and `motions` count.

After editing the registry, write the header and check both:

```bash
python3 tools/check_ids.py --write
python3 tools/check_ids.py
```

`ids.h` is checked in so the plugin builds from the registry without the tool having run; the
check fails when it is stale. An id that has shipped never moves: a new content takes the next
free id, and a mistake is corrected by a migration, not by renumbering
([0003](../docs/decisions.md#0003-id-allocation-and-mod-saves)).

## Why these bounds

- **124** is MH4U's first id after its own 0 to 123 ([reference](../reference/README.md#mh4u-monster-tables)).
- **255** is the most one byte holds: the engine keeps a monster's id in one byte (`+0x1c0` of its data
  block, read with `ldrb`), and so does a guild quest card ([specs/extdata.md](../specs/extdata.md)).
  0003's amendment keeps 124 to 223 permanent and lends 224 to 255 per quest to monsters registered
  from 256 up; the tool and the plugin implement the pool in
  [#101](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/101);
  the character save's monster log has 82 fixed entries and whether it is indexed by id is
  unverified, so an id above 81 is already beyond what that structure can hold if it is.
- The name and notes texts are messages named by the id (`emName`, `emExp`): a ported id needs
  a message of its own in the mod's text, which is content work, not an id range.

| Id | Key | Content | Stand-in | Ships |
|---|---|---|---|---|
| 124 | `rathian-gu` | Rathian, ported from MHXX (GU) | MH4U Rathian (1) | model, motions=5, tail, cmd |
| 125 | `rathian-3u` | Rathian, ported from MH3U | MH4U Rathian (1) | model, motions=3, tail, cmd |

The two ports are [#47](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/47)'s
subject; their files come from [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48)
and [#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49).
