# versions.csv

One row for every large monster MH4U shares with MH3U or MHGU (61 rows: 15 MH3U, 46 MHGU), with
a verdict on whether a player would notice the source game's version differ from MH4U's
([decision 0004](../../docs/decisions.md#0004-monster-versions), amended: only versions a player
would notice get an id). Names, action ids and counts only; nothing here is read from a game
file by the reader of this page.

| Column | Meaning |
|---|---|
| `source_game` | MH3U or MHGU, the wiki's game ([monsters.csv](monsters.csv)) |
| `monster` | English name, the wiki's spelling |
| `mh4u_id` | MH4U's file id (`emNNN`) |
| `source_file` | the source game's file id: MH3U `arc/enemy/emNNN.arc`; MHGU uses MHXX (3DS), `arc/enemy/emNNN_VV.arc` per the fidelity rule |
| `data` | `same`, `differs` or `not compared` |
| `data_detail` | HP, weakness and breakable-part evidence behind `data` |
| `moves` | `same`, `differs` or `not compared`: the games' code and the wiki's attack lists together |
| `moves_detail` | the code's action ids and animations, then the wiki's list |
| `wiki` | `same`, `differs` or `not compared`, the wiki's attack lists alone, so the two can be read apart |
| `wiki_detail` | the attack names the two lists add or lack |
| `model` | `same`, `differs` or `not compared` |
| `model_detail` | rig, mesh and texture evidence behind `model` |
| `verdict` | `differs`, `doesn't differ` or `not decided` |
| `source_url` | the wiki monster page the row's name comes from |
| `attack_source_url` | the source game's per-monster page the attack list came from |
| `attack_mh4u_url` | the MH4U per-monster page the attack list was compared with |

The wiki's attack lists are in [attacks.csv](attacks.csv), one row per game, monster and name,
with the page it came from (read on 2026-11-25).

## The rule

Decision 0004's amendment gives a version an id only when **a player would easily notice the
difference**. An axis is `differs` when any of these holds, `same` when none does and the axis
was compared, and `not compared` when the files or the wiki could not answer it:

- **`data`** — base HP differs by 10 % or more; a weakness (one of the eight damage types in a
  hitzone row) differs by 10 points or more on a hitzone row both games' body records use; or the
  set of parts with a break record differs. A different value below those thresholds, a
  different number of attack records or attack-volume groups, and a retuned part HP are not
  differences: MH4U's version already has those fields.
- **`moves`** — a shared action id starts a different animation (same frame count and loop frame
  at another index is the same animation; the track count is recorded but doesn't decide); a
  source-only action starts an animation MH4U's motion lists do not hold and the source game's
  AI script names it; or the wiki's attack lists differ after dropping the translation marker
  and a trailing qualifier from each name. An action the AI script does not name is not met in
  a normal fight; one whose animation MH4U already plays is not a new move.
- **`model`** — the main body model's bound box differs by more than 2 % on a side where the two
  games share a bind space (MHXX against MH4U). MH3U's bind space differs in every row, so its
  box is not comparable. Bone numbering and an emptied root never decide; a mesh or texture
  re-exported into another atlas does not either.

`verdict` is `differs` when any axis differs, `doesn't differ` when every axis is `same`, and
`not decided` when no axis differs but one could not be compared. `moves` is decided by the
code; a wiki list that differs adds a difference, and a source page without an attack list does
not withhold the verdict the code reached (the wiki's own result still says `not compared`).
Every per-axis count and action id is kept in the detail columns so a threshold can be tightened
without a re-run.

## How the axes are made

**Which monster pairs with which file.** MH3U's ids are paired with MH4U's in
[reference/README.md](../../reference/README.md#mh3u-ids-to-mh4us). MHXX numbers its monsters
differently from MH4U, so the MHGU rows use MHXX's own monster registry: the order of its
monster-name table (`GUI\06_msg\monsterName_jpn` in `arc/resident.arc`) and the registry's
file-id table give the file id, and MHGU's English name table names it (MHGU supplies English
text only, CLAUDE.md rule 2). The data counts cross-check every pair: a wrong pair does not
agree on the hitzone table and the part table.

**Data.** `mhuc monsterdata` rebuilds MH4U's HP, hitzone table and part table from MHXX's
`dttune`, `dtbase` and `dtbparts` or MH3U's `em_status`, and the tool compares them
([specs/emd.md](../../specs/emd.md), [emstatus.md](../../specs/emstatus.md)). Only the hitzone
rows both games' body records use are compared, so a row MH4U fills and the source leaves empty
does not count; `break parts` is the set of parts whose part record has a break level or a
second-level HP.

**Moves.** The inventory is the action dispatcher walk of
[monster_motions.py](../../reference/monster_motions.py) (check R1): the action ids a monster
class handles and the first constant motion each handler starts. Two games' inventories are
compared by action id; a different index is decoded to its LMT file and slot and the two
animations are compared by frame count and loop frame. The pairs come from
[reference/monster_versions.py](../../reference/monster_versions.py). The AI evidence is
[monster_emc.py](../../reference/monster_emc.py): the `00 cat num` native-action opcodes the
monster's rEnemyCmd script names (`specs/emc.md`). Its bytecode reading is MHGU Definitive
Edition's heuristic, so it proves which actions a script names, not a complete decode; MH4U and
MHXX share version 0x20120804 and MH3U's is older. Category 7's shared code can start more than
one motion, so its first constant is not enough and a differing signature there is not resolved.

**Model.** `mhuc`'s MOD reader gives the main body model's bone records, bound box, material
names and counts ([specs/mod.md](../../specs/mod.md)). The rig is compared after contracting
bones that sit at their parent's position: MH3U adds one such root (id 14 for most monsters) and
reparents three chains to it, which is the same rig. MHXX's meshes have MH4U's bound box in
every row. `mhuc`'s TEX reader records each texture's size and format; MH4U splits the same skin
into different texture files, so a re-atlas is not a difference.

## Rathian first

The milestone's two ports depend on the answer, so both rows were read action by action:

- **MHGU Rathian** — `data` same (HP equal, hitzones and breakable parts equal). `moves` same:
  of 273 shared ids, 167 start an animation and all are the same; 8 of her 9 GU-only motion
  actions are named by the AI script (`3/98`, `4/27`-`4/32`, `12/0`; it does not name `8/0`).
  `3/98` and `12/0` start MH4U's motion 1/1 and `8/0` MH4U's 4/3, which MH4U's Rathian already
  plays; `4/27`-`4/32` start motion 9/11, which neither game's own lists decode, so it is not
  resolved rather than a new animation. The wiki lists the same 10 attacks in MHGU and MH4U.
  `model` same (same rig, same bound box, same material parts; the 43/43 bone ids and parents
  agree, the meshes differ by 13 vertices of 6,890). Verdict: **doesn't differ**.
- **MH3U Rathian** — `data` same (HP equal, every used hitzone within 1 point, breakable parts
  equal). `moves` differs: the same 174 action ids are compared and 13/5, 13/6 and 13/8 start a
  different animation (frames 347/489, 347/133 and 243/133), while 93 of the 115 different
  indices are the same animation at another index; of her 17 source-only ids, none is named by
  the 3U AI script and only 4/None (category 4's single action) and 7/64 start a motion. The
  wiki's MH3U pages carry no attack list, so `wiki` is not compared. `model` same (the one extra
  bone is an empty root at the origin). Verdict: **differs**.

## Rerun

The comparison needs the MH4U, MH3U and MHXX dumps and the class vtables that
[reference/mt_vtables.py](../../reference/mt_vtables.py) recovers (kept outside the repository,
because their slot lists are read from game code):

```bash
python3 reference/mt_vtables.py --exheader mh4u/exheader.bin --code mh4u/code.bin \
    --classes reference/games/mh4u/mt_classes.tsv -o build/mh4u.vt.tsv
python3 reference/mt_vtables.py --exheader mh3u/exheader.bin --code mh3u/code.bin \
    --classes reference/games/mh3u/mt_classes.tsv -o build/mh3u.vt.tsv
python3 reference/mt_vtables.py --exheader mhxx/exheader.bin --code mhxx/code.bin \
    --crs mhxx/romfs/modules_MasterRelease/static.crs -o build/mhxx.vt.tsv \
    mhxx/romfs/modules_MasterRelease/roEm*.cro
```

Then rewrite the verdicts and their evidence from the row file:

```bash
python3 reference/monster_versions.py --rows data/catalog/versions.csv \
    --attacks data/catalog/attacks.csv \
    --mh4u-romfs mh4u/romfs.bin --mh3u-romfs mh3u/romfs.bin \
    --mhxx-romfs mhxx/romfs.bin --mhxx-update-romfs mhxx_update/romfs.bin \
    --mh4u-exheader mh4u/exheader.bin --mh4u-code mh4u/code.bin \
    --mh3u-exheader mh3u/exheader.bin --mh3u-code mh3u/code.bin \
    --mh4u-vt build/mh4u.vt.tsv --mh3u-vt build/mh3u.vt.tsv --mhxx-vt build/mhxx.vt.tsv \
    -o data/catalog/versions.csv
```

`--rows` only supplies the pairing (`source_game`, `monster`, `mh4u_id`, `source_file`,
`source_url`); every verdict and its evidence are rewritten. MH4U's code is v1.3.0, the update's
`code.bin`. A source file with no MHXX module of its own is compared on the class MH4U's version
shares with it (Rathalos and Silver Rathalos on Rathian's, Gravios on Basarios's, Shagaru Magala
on Gore Magala's, Gendrome and Iodrome on Velocidrome's); its `moves_detail` says `shared family
class`. The `not decided` rows are where no axis differs and an axis could not be compared; the
detail says which and why.
