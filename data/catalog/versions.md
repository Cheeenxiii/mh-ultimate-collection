# versions.csv

One row for every large monster MH4U shares with MH3U or MHGU (61 rows: 15 MH3U, 46 MHGU),
with a verdict on whether the source game's version differs from MH4U's ([decision
0004](../../docs/decisions.md#0004-monster-versions), amended: only versions that differ get an
id). Names and counts only; nothing here is read from a game file by the reader of this page.

| Column | Meaning |
|---|---|
| `source_game` | MH3U or MHGU, the wiki's game ([monsters.csv](monsters.csv)) |
| `monster` | English name, the wiki's spelling |
| `mh4u_id` | MH4U's file id (`emNNN`) |
| `source_file` | the source game's file id: MH3U `arc/enemy/emNNN.arc`; MHGU uses MHXX (3DS), `arc/enemy/emNNN_VV.arc` per the fidelity rule |
| `data` | `same`, `differs` or `not compared` |
| `data_detail` | the counts behind `data` |
| `moves` | `same`, `differs` or `not compared` |
| `moves_detail` | the action ids and motion counts behind `moves` |
| `model` | `same rig`, `differs` or `not compared` |
| `model_detail` | bone and mesh counts behind `model` |
| `verdict` | `differs`, `doesn't differ` or `not decided` |
| `source_url` | the wiki page the row's name comes from |

## How the verdict is made

**Which monster pairs with which file.** MH3U's ids are paired with MH4U's in
[reference/README.md](../../reference/README.md#mh3u-ids-to-mh4us). MHXX numbers its monsters
differently from MH4U, so the MHGU rows use MHXX's own monster registry: the order of its
monster-name table (`GUI\06_msg\monsterName_jpn` in `arc/resident.arc`) and the registry's
file-id table give the file id, and MHGU's English name table names it (MHGU supplies English
text only, CLAUDE.md rule 2). The data counts below cross-check every pair: a wrong pair does
not agree on the hitzone table and the part table.

**What each axis compares.** The comparisons are the repository's tools:

| Axis | Tool | What it compares | Counts shown |
|---|---|---|---|
| data | `mhuc monsterdata` (reference/README.md, specs/emd.md, dttune.md, dtbase.md, dtbparts.md, emstatus.md, hitdata.md) | base HP, the 8-row hitzone table, the 8-record part table, attack-volume groups, attack records | equal bytes/rows/records, and whether either side has more records/groups/parts |
| moves | [reference/monster_motions.py](../../reference/monster_motions.py) (docs/checks.md, R1) | every action id both games have, the motion index its handler starts, then the animation's signature (frames, loop frame, track count) when the two indices differ | common actions, compared, same index, different index, source-only ids, and the content split (same animation at another index / different / not resolved) |
| model | `mhuc`'s MOD reader (specs/mod.md, M2/M3) | the main body model's rig: bone count and each bone's id and parent | bones, whether the skeleton (ids and parents) is equal, and the mesh/vertex/index counts for reference |

**The verdict rule**, following the amendment's reading agreed for this issue:

- `data` **differs** when the source version has a block, field or part MH4U's version does not
  have (a field `absent in MH4U`, or a breakable part MH4U does not list). A different value in
  a field both games have (HP, a hitzone byte, a record's value), or a different number of
  records or attack-volume groups in a block both games have, is **not** a difference: it is a
  same-field retune, and MH4U's version already has that field. Those counts are still in
  `data_detail`, so a stricter threshold can be read off them.
- `moves` **differs** when the source has an action id MH4U lacks whose handler starts a
  motion, or a shared action id starts a different animation (frames/loop/track count). The
  same animation at another index is not a difference (the two games pack and group indices
  differently, R1).
- `model` **differs** when the rig differs: bone count, or any bone's id or parent. Vertex,
  index, mesh and material counts are recorded but do not decide it (artwork alone does not
  make a version).
- `verdict` is `differs` when any axis differs, `doesn't differ` when all three are `same`, and
  `not decided` when no axis differs but one could not be compared.

The per-axis counts are in the table so the threshold can be tightened without re-running
anything but the comparison.

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

Then rewrite the counts and verdicts from the row file:

```bash
python3 reference/monster_versions.py --rows data/catalog/versions.csv \
    --mh4u-romfs mh4u/romfs.bin --mh3u-romfs mh3u/romfs.bin \
    --mhxx-romfs mhxx/romfs.bin --mhxx-update-romfs mhxx_update/romfs.bin \
    --mh4u-exheader mh4u/exheader.bin --mh4u-code mh4u/code.bin \
    --mh3u-exheader mh3u/exheader.bin --mh3u-code mh3u/code.bin \
    --mh4u-vt build/mh4u.vt.tsv --mh3u-vt build/mh3u.vt.tsv --mhxx-vt build/mhxx.vt.tsv \
    -o data/catalog/versions.csv
```

`--rows` only supplies the pairing (`source_game`, `monster`, `mh4u_id`, `source_file`,
`source_url`); every count and verdict is rewritten. A source file with no MHXX module of its
own is compared on the class MH4U's version shares with it (Rathalos and Silver Rathalos on
Rathian's, Gravios on Basarios's, Shagaru Magala on Gore Magala's, Gendrome and Iodrome on
Velocidrome's); its `moves_detail` says `shared family class`. The `not decided` rows are where
no axis differs and an axis could not be compared; the detail says which and why.
