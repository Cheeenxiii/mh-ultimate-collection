# Ids

The registry of every id a ported content takes in MH4U. `registry.csv` is read by
`tools/check_ids.py`, and the plugin `mods/monster_ids` gets its ids from the header the tool
generates. Its companion `notes.csv` records where each ported id's Hunter's Notes text comes
from; `tools/check_text.py` checks it and `mhuc text build` turns it and the registry into the
mod's text table. Decision [0003](../docs/decisions.md#0003-id-allocation-and-mod-saves)
settles the rule: one registry, ids only ever grow, and the run time reads them from here.

| Column | Meaning |
|---|---|
| `kind` | what kind of id: `monster` today; another kind needs its range and rules in `tools/check_ids.py` first |
| `id` | the id in MH4U. Monsters start at 124 (MH4U uses 0 to 123); 124 to 223 are permanent and 224 to 255 are the pool lent per quest ([0003](../docs/decisions.md#0003-id-allocation-and-mod-saves)). A permanent row stops at 223; a monster ported after that range is full takes a row from 256 up, and 224 to 255 are never registry ids |
| `key` | the content's name in the registry, lowercase words joined by hyphens, unique |
| `source_game` | which game the content comes from: `mh4u`, `mh3u`, `mhxx` or `mhgu` |
| `source_key` | the content's name in that game: a monster's `emNNN` |
| `name` | the content's name, for review |
| `stand_in` | the MH4U monster id whose table rows answer for this id until the port ships the content's own rows |
| `files` | the kinds of file the port ships, comma-separated: `model`, `motions`, `camera`, `tail`, `mef`, `sound`, `cmd`, `efl` (the resource record's path kinds, below). `motions` takes the motion-list slots shipped, as a range or a list: `motions=0-4` or `motions=0,2,3,4`; a slot it does not name keeps the stand-in's path |
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

## The pool

Ids 224 to 255 are not registry ids: they are the bytes `mods/monster_ids` lends to a quest's
pooled monsters. A pooled row takes an id from 256 up, which is what the quest's u32 monster
list and the mod's data in the save record. When a quest loads, the plugin finds its loaded
`.mib` among the quest holder's quest-file resources and rewrites each pooled id in the
large-monster waves to a free pool byte; the reader hooks answer that byte with the pooled
monster's rows, exactly as they answer a permanent id, and the byte is freed when the quest
ends. A quest names a few large monsters, so 32 bytes are enough. A pooled monster can't be on
a guild quest card (its id field is one byte) and its hunt records go through the mod's data in
the save, not MH4U's byte-indexed structures ([0003](../docs/decisions.md#0003-id-allocation-and-mod-saves)).
No pooled monster ships yet, so this file has no row from 256 up and the header's pooled array
is empty; `tests/fixtures/registry-pooled.csv` is a fixture the checker and check P1 use.

## The kinds a port ships

MH4U does not tolerate a resource record that names a file it does not have: a 3U session
hung at "Now Loading" on the record built for 125, which named 13 paths while `em125.arc`
ships 6 ([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)). So a port
ships only some kinds and the record keeps the stand-in's path for the rest. A kind is one
group of paths in the record:

| Kind | The record's paths | 124 ships | 125 ships | 126 ships | 127 ships |
|---|---|---|---|---|---|
| `model` | the model | yes | yes | yes | yes |
| `motions` | the six motion lists and the second motion list; `motions` names the slots the port ships | `motions=0-4` | `motions=0-2` | `motions=0,2,3,4` | `motions=0-2` |
| `camera` | the camera | no | no | no | no |
| `tail` | the tail model | yes | yes | no | no |
| `mef` | the motion effects | no | no | no | no |
| `sound` | the sound: the call (`sound\call\em\emNNN`) and the waves, bank and request it names | no | yes | no | no |
| `cmd` | the command/EMC | yes | no, until the EMC converter (a follow-up after #49) ships | no | no |
| `efl` | the effect lists | no | no | no | no |

124's `em124.arc` holds the model, five motion lists, the tail and the command; 125's holds
the model, three motion lists, the tail and its converted sound set, but no command yet: the
EMC converter that would give her MH3U's own script is a follow-up after #49
([specs/emc.md](../../specs/emc.md#what-a-converter-must-do)), so her record keeps MH4U
Rathian's script path; 126's holds
the model and four motion lists, borrowed from MHXX's em014 (Velocidrome) and shipped at the
same slots 0, 2, 3 and 4 the source groups them in, so its record keeps the stand-in's paths
for slots 1 and 5; 127's holds the model and three motion lists, its own MH3U lists at slots
0, 1 and 2, and no tail, because MH3U's `em045.arc` has none (its tail is part of the body
model). Until a port's
own camera, motion effects and effect lists are converted, its monster loads MH4U's own from
the stand-in's paths (`enemy\em001\...` for 124 and 125, `enemy\em015\...` for 126 and
127); 125's record also keeps MH4U's `enemy\em001\mot\em001_3` and `_4`
for the two motion slots it does not ship, so its motion-number translation only targets slots
0 to 2. The motion-effect and effect-list formats the `mef` and `efl` kinds carry are laid out
and checked on the three games' monster archives ([mef](../../specs/mef.md),
[efl](../../specs/efl.md), checks FX1, FX2, EF1 and EF2); their records and blocks are not
understood yet, so a port still ships neither kind.

A new kind is added to `tools/check_ids.py`'s `FILE_KINDS` and to the plugin's path map
together; the generated header's `MHUC_FILES_*` bits and each row's `motion_mask` are what
the plugin's record builder reads.

The `sound` kind is one path, `sound\call\em\emNNN`, but the file it names (the sound call)
names its requests, banks and waves by their own paths; those are looked up in the same loaded
archive, so the port's `data/emNNN.arc` must carry all four kinds. `mhuc convert monster` writes
them there from the source game's own archives and moves every path into the ported id's
namespace (`sound\se\em\emNNN\...`), so a port never shadows MH4U's own monster or another
port. [specs/sound.md](../../specs/sound.md) has the formats and the conversion, and check A1
in [checks.md](../docs/checks.md#a-ported-monsters-own-voice-a1) the in-game listen.

125's command would be her own AI script: MH3U's EMC is an older format, so a converter would
rewrite it at build time (version, 23 group rows and the 15 opcodes whose argument count
differs), [specs/emc.md](../specs/emc.md#what-a-converter-must-do). #159 recorded the method,
but the 15 opcodes' added argument's meaning is unverified, so the converter is a follow-up
after [#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49); until it ships her
row lists no `cmd` and MH4U's own script drives her.

## Rules the tool checks

- every id is inside its kind's range and no two rows share one;
- **permanent** monster ids are consecutive from 124, with no gap: every permanent id up to the
  highest one used needs a row in each table indexed by id;
- a pooled id starts at 256 and needs no gap: the pool lends it a byte, so it is not a table
  index, and 224 to 255 are refused as registry ids;
- a key, a source game and a source key are valid, and every row has a name and a stand-in;
- `files` is not empty, every kind in it appears once, and `motions` names slots in 0..5 once
  each;
- `mods/monster_ids/src/ids.h` is exactly what this file generates: the permanent ids in one
  array, the pooled ids in another, and each row's `files` bits and `motion_mask`.

After editing the registry, write the header and check both:

```bash
python3 tools/check_ids.py --write
python3 tools/check_ids.py
```

`ids.h` is checked in so the plugin builds from the registry without the tool having run; the
check fails when it is stale. An id that has shipped never moves: a new content takes the next
free id, and a mistake is corrected by a migration, not by renumbering
([0003](../docs/decisions.md#0003-id-allocation-and-mod-saves)).

## The notes source

The notes text is not in the registry: it is the source game's own, recorded per ported id in
`notes.csv` (the name is the registry's `name`). Columns:

| Column | Meaning |
|---|---|
| `id` | the ported monster's registry id |
| `source_game` | the game the notes come from, which must be the registry row's `source_game` |
| `source_file` | the table's path in that game's RomFS, without its leading `/` |
| `source_entry` | the GMD's path inside that `source_file` when it is an ARC, empty when the file is the GMD |
| `source_index` | the string's index in that GMD; MH3U's Hunter's Notes and MHXX's monster list are ordered tables, not id-indexed ones, so the index is the fact the port's session established |

`tools/check_text.py` checks every ported id has exactly one row, the game is its registry's,
the path is a RomFS path and the index is a non-negative number. `mhuc text build` reads the
player's own dumps (MH3U's `arc/ID/ID_gallery_eng.arc`, MHXX's
`table/HN_MonsterListMsg_jpn.gmd`), takes the name from `registry.csv` and writes
`text/monster_text.bin` into the mod's folder; `tools/check_text.py --mod` checks that built
file holds exactly the registered ids with the registry's names. The text's language is the
source game's: MH3U USA is English, MHXX JPN is Japanese until MHGU's English text is read.
No text is kept here, only the source's address and index; the plugin's README
([the name and notes text](../mods/monster_ids/README.md#the-name-and-notes-text)) says how
the game reads it.

## Why these bounds

- **124** is MH4U's first id after its own 0 to 123 ([reference](../reference/README.md#mh4u-monster-tables)).
- **255** is the most one byte holds: the engine keeps a monster's id in one byte (`+0x1c0` of its data
  block, read with `ldrb`), and so does a guild quest card ([specs/extdata.md](../specs/extdata.md)).
  0003's amendment keeps 124 to 223 permanent and lends 224 to 255 per quest to monsters registered
  from 256 up; the tool and the plugin implement that pool. **256** is the first registry id the
  pool lends for; a quest's monster list ends at `0xffffffff` ([specs/quest.md](../specs/quest.md)),
  so a registry id stops at `0xfffffffe`. The character save's monster log has 82 fixed entries
  and whether it is indexed by id is unverified, so an id above 81 is already beyond what that
  structure can hold if it is.
- The name and notes texts are messages named by the id (`emName`, `emExp`): a ported id needs
  a message of its own in the mod's text. The plugin answers the three message getters with the
  mod's table ([the notes source](#the-notes-source)); the Hunter's Notes list row is not
  answered yet, so the text exists for an id the UI already shows but a ported monster is not
  added to the list itself.

| Id | Key | Content | Stand-in | Ships |
|---|---|---|---|---|
| 124 | `rathian-gu` | Rathian, ported from MHXX (GU) | MH4U Rathian (1) | model, motions=0-4, tail, cmd |
| 125 | `rathian-3u` | Rathian, ported from MH3U | MH4U Rathian (1) | model, motions=0-2, tail, cmd, sound |
| 126 | `giadrome-gu` | Giadrome, ported from MHXX (GU) | MH4U Great Jaggi (15) | model, motions=0,2,3,4 |
| 127 | `great-wroggi-3u` | Great Wroggi, ported from MH3U | MH4U Great Jaggi (15) | model, motions=0-2 |

No pooled row ships yet; the first would be 256, with a `stand_in` like any other.

124 and 125 are [#47](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/47)'s subject;
their files come from [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48) and
[#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49). 126 is
[#161](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/161)'s, and its AI is the
stand-in's until [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48) converts
an MHXX EMC ([specs/emc.md](../specs/emc.md#what-a-converter-must-do)). 127 is
[#166](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/166)'s.
