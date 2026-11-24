---
class: rEnemyDtBase
extension: dtbase (in each monster's arc/enemy/emNNN_SS.arc: enemy\dt_base\emNNN_SS_dtbase)
games: MHXX (JPN v1.0 RomFS, v1.4 code)
status: unknown
---

# rEnemyDtBase: an MHXX monster's data that MH4U keeps in its `.emd`

MHXX's counterpart of the blocks of MH4U's `.emd` (specs/emd.md) that are not hitzones: the broken-part groups, the
map-hit sphere, the joint points and the scalars MHGU Definitive Edition's converter calls `dtbase`. One per monster
variant (140 entries, 138 distinct files in MHXX, class id 0x59D9C3DA, a `cResource` of 0xD0 bytes in MHXX's registry).
MH4U's registry has a class of the same name and id (the fork's `config/mt_classes.tsv`), but MH4U ships no such file:
its monster data is the `.emd`/`.etd` pair.

**Layout.** An 8-byte header, 13 count/flag bytes, a run of scalars, then blocks read one after another with no offsets;
a block with a count of 0 is absent, and a flag byte of 0 means present. The order and sizes are MHXX's own loader's
(`rEnemyDtBase` vtable slot 11, 0x002b6f88 in the v1.4 code): it reads the 8-byte header, copies the 13 bytes to object
+0xB8, then reads the scalars and blocks into memory it allocates or into fixed object fields. Check E7 runs our reader
(`mhuc.formats.dtbase`) on every file and `reference/loader_trace.py` runs the loader itself on every file: the layout
below ends exactly at the file's end in all 138, and its blocks are the loader's reads.

**Meaning.** A block is named after the MH4U `.emd` bytes it equals, checked by rebuilding MH4U's values from MHXX's
files (`mhuc monsterdata`, check E5) for the three monsters MHGU Definitive Edition pairs across the games: Rathian
(MH4U em001, MHXX em001_00), Kushala Daora (em031, em024_00) and Teostra (em032, em027_00). A block that equals MH4U's
on those monsters has MH4U's meaning; a block with no counterpart is unknown. MHGU Definitive Edition's `dt_convert.py`
and `notes/data.md` name the same MH4U side, and its object offsets are 4 bytes lower in MHXX (MHGU +0x64 is MHXX
+0x60, and so on).

## Header and scalars

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `DTB\0` | verified | ours, loader 0x002b6f88; check E7 |
| 0x04 | u32 | version 0x15022601 (the loader rejects any other) | verified | ours, loader; check E7 |
| 0x08 | u8 ×13 | c0..c12, copied to object +0xB8..+0xC4: counts where a loop reads that many records, presence flags (0 = present) at c7, c8, c10, c11 and c12 | verified | ours, loader; check E7 |
| 0x15 | f32 | MH4U `.emd` byte 0x0C (object +0x60) | verified | ours, loader; check E5 |
| 0x19 | u8 ×4 | MH4U `.emd` byte 0x10 (object +0x64..+0x67; the four bytes are that u32) | verified | ours, loader; check E5 |
| 0x1D | u32 | MH4U `.emd` byte 0x30 (object +0x68) | verified | ours, loader; check E5 |
| 0x21 | u8 | not identified (object +0xB4) | unknown | ours, loader |
| 0x22 | 5 × 4 bytes | MH4U `.emd` bytes 0x6C, 0x70, 0x14, 0x78, 0x7C, in that order (object +0x94) | verified | ours, loader; check E5 |
| 0x36 | u8 | read only when c12 ≠ 0 (object +0x90); no counterpart found | unknown | ours, loader |

The scalars are matched word for word on the three monster pairs, 4 fields of 4 bytes each; MHGU's `dt_convert.py`
names the same `.emd` offsets.

## Blocks

In loader order; "Object" is where the loader puts the block. Sizes are in bytes, c_i is the header byte at 0x08 + i.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| c12 ≠ 0: +1 | u8 | byte (object +0x90) | unknown | ours, loader |
| +52·c9 | 52-byte records | map-hit spheres (object +0x80): MH4U `.emd` word 20, one record per sphere. c9 is 1 in 136 files and 2 in 2 | verified | ours, loader; MHGU-DE porting-guide.md; check E5 |
| c10 ≠ 0: +52 | 52 bytes | second sphere block (object +0x84): MH4U `.emd` word 21 | verified | ours, loader; check E5 |
| c7 ≠ 0: +64 | 64 bytes | block (object +0x70): MH4U `.emd` word 38 | verified | ours, loader; check E5 |
| c8 ≠ 0: +12 | 12 bytes | block (object +0x74): MH4U `.emd` word 39 | verified | ours, loader; check E5 |
| c11 ≠ 0: +4 | 4 bytes | block (object +0x88): MH4U `.emd` word 22 | verified | ours, loader; check E5 |
| +28·c2 | 28-byte records | block (object +0x7C); no counterpart found | unknown | ours, loader |
| +2·c0 | u16 × c0 | block (object +0x6C): MH4U `.emd` word 13 (32 bytes = 16 u16 in all 138 files) | verified | ours, loader; check E5 |
| +28·c4 | 28-byte records | joint points (object +0xA8): MH4U `.emd` word 43, two records = its 56 bytes. c4 is 0 or 2 in every file | verified | ours, loader; check E5 |
| +32·c5 | 32-byte records | block (object +0xAC): MH4U `.emd` word 44's records, without its closing 0xFF record | verified | ours, loader; check E5 |
| +2·c3 | u16 × c3 | block (object +0x8C); no counterpart found | unknown | ours, loader |
| +2·c6 | u16 × c6 | block (object +0xB0); no counterpart found | unknown | ours, loader |
| c1 × list | u32 count, then 44-byte records, then one u8 and three u32 | list (object +0x78, counts at +0xC8); no counterpart found | unknown | ours, loader |

The map-hit sphere record is 52 bytes: four 12-byte offsets and a radius (MHGU DE, porting-guide.md). The joint points
are 28-byte records; MH4U's word 43 (56 bytes) is two of them.

## What this means for the mod

- **A GU monster's broken-part groups, map-hit sphere, joint points and the `.emd` scalars come from its `dtbase`.**
  `mhuc monsterdata` rebuilds the map-hit sphere, the joint points and the scalars into MH4U's layout and compares them:
  the spheres and joint points are equal on Kushala Daora and Teostra, 51 of 52 bytes on Rathian; the joint points are
  equal on all three; the scalars are equal on all three.
- **The blocks without a counterpart are the mod's to author or to carry from MHXX unread.** They are marked unknown,
  not guessed at.
- What MH4U keeps in `.emd` and MHXX splits into `dtbase` and `dtbparts`: this spec (the `.emd` blocks above) and
  [dtbparts](dtbparts.md) (the break records and joint records). The `.emd` word 35 sever records are in neither: a
  monster class passes its joint to the engine and ships the cut part as a `_tail.mod`
  ([dtbparts](dtbparts.md#sever-and-detach-records-not-in-these-files)). The hitzones, HP and parts are in
  [dttune](dttune.md); hurt and attack volumes in [hitdata](hitdata.md).

## Checks

- **E7 (done, MHXX JPN v1.0 RomFS):** `mhuc survey <romfs.bin>` counts `E7 dtbase layout ends at the file's end`.
  Result: 140 entries (138 distinct files) end exactly at their last byte.
- **Loader trace (done, MHXX v1.4 code, same RomFS):** `python3 reference/loader_trace.py mhxx-dtbase --exheader
  <exheader.bin> --code <code.bin> --romfs <romfs.bin>` runs the game's loader in Unicorn on each file and logs every
  stream read. Result: it reads the whole file in all 138, and our reader's blocks split the same bytes (every block
  starts where a read starts, and every read starts inside a block).
- **E5 (done, the three monster pairs above):** `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mhxx
  arc/enemy/em001_00.arc` (likewise em031/em024_00, em032/em027_00) prints, per field, whether MHXX's value rebuilt into
  MH4U's layout equals MH4U's. Results: the map-hit sphere 51 of 52 bytes on Rathian, equal on the other two; the joint
  points equal on all three; the joint records 6 of 6 on Rathian, absent on both sides for the other two; the `.emd`
  scalars and the `.emd` word 44 block equal on all three.
