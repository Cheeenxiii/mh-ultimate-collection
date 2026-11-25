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
| `notes` | where the content comes from, and anything the next reader needs |

The table it stands in for is the game's own, read by the plugin's hooks: the ported monster's
id is answered with that MH4U monster's rows, so the id loads the base game's files today and
the port's own files when they are installed. Changing a `stand_in` is not moving an id.

## Rules the tool checks

- every id is inside its kind's range and no two rows share one;
- monster ids are consecutive from 124, with no gap: every id up to the highest one used needs
  a row in each table indexed by id;
- a key, a source game and a source key are valid, and every row has a name and a stand-in;
- `mods/monster_ids/src/ids.h` is exactly what this file generates.

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

| Id | Key | Content | Stand-in |
|---|---|---|---|
| 124 | `rathian-gu` | Rathian, ported from MHXX (GU) | MH4U Rathian (1) |
| 125 | `rathian-3u` | Rathian, ported from MH3U | MH4U Rathian (1) |

The two ports are [#47](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/47)'s
subject; their files come from [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48)
and [#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49).
