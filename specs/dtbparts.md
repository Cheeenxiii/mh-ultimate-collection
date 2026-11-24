---
class: rEnemyDtBaseParts
extension: dtbparts (in each monster's arc/enemy/emNNN_SS.arc: enemy\dt_base\emNNN_SS_dtbparts)
games: MHXX (JPN v1.0 RomFS, v1.4 code)
status: unknown
---

# rEnemyDtBaseParts: an MHXX monster's break and joint records

MHXX's counterpart of the part-break and joint/sever records MH4U keeps in its `.emd` (specs/emd.md, words 32, 33 and
35). One per monster variant (140 entries, 138 distinct files in MHXX, class id 0x1BBC291E, a `cResource` of 0xD0 bytes
in MHXX's registry). MH4U's registry has no class of this name.

**Layout.** A 0x4D-byte header (magic, version, 16 count bytes, a run of scalars and one more count), then blocks read
one after another with no offsets; a count byte of 0 means its block is absent. The order and sizes are MHXX's own
loader's (`rEnemyDtBaseParts` vtable slot 11, 0x0058e424 in the v1.4 code): it reads the header, copies the 16 count
bytes to object +0x88, then reads each block into memory it allocates. Check E7 runs our reader
(`mhuc.formats.dtbparts`) on every file and `reference/loader_trace.py` runs the loader itself on every file: the
layout below ends exactly at the file's end in all 138, and its blocks are the loader's reads.

**Meaning.** Two blocks are named after the MH4U `.emd` bytes they hold, checked by rebuilding MH4U's values from MHXX's
files (`mhuc monsterdata`, check E5) on the three monsters MHGU Definitive Edition pairs across the games: Rathian
(MH4U em001, MHXX em001_00), Kushala Daora (em031, em024_00) and Teostra (em032, em027_00). The other blocks are named
only where MHGU Definitive Edition's own `dtbparts` work says what they are, and are unknown otherwise.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `DTP\0` | verified | ours, loader 0x0058e424; check E7 |
| 0x04 | u32 | version 0x01339ECB (the loader rejects any other) | verified | ours, loader; check E7 |
| 0x08 | u8 ×16 | c0..c15, copied to object +0x88..+0x97: c0..c8 size the blocks below; c9..c15 are stored and not read by this loader | verified | ours, loader; check E7 |
| 0x18 | u32 | scalar (object +0x98) | verified | ours, loader; check E7 |
| 0x1C | u32 | scalar (object +0x9C) | verified | ours, loader; check E7 |
| 0x20 | u16 ×14 | scalars (object +0xA0..+0xBA) | verified | ours, loader; check E7 |
| 0x3C | u32 ×4 | scalars (object +0xBC..+0xC8); MHGU Definitive Edition reads the first three as floats | verified | ours, loader; check E7 |
| 0x4C | u8 | c16, copied to object +0xCC: the count of the last block | verified | ours, loader; check E7 |

"Verified" on a scalar covers its place and size only; what it means is not known.

## Blocks

In loader order; "Object" is where the loader puts the block. c_i is the byte at 0x08 + i; c16 is the byte at 0x4C.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +4·c0 | 4-byte records | break records (object +0x60): u8 part, u8 LR count, u8 HR count, s8 group. MH4U's part break table (`.emd` word 32) and break list (word 33); not byte-equal: MHXX splits the count into ranks and stores one record per part | verified | ours, loader; MHGU-DE `dala_break.c`; check E5 |
| +13·c1 | 13-byte records | joint records (object +0x64): s32 joint, u8 kind, u32 index, u32 limit. MH4U `.emd` word 35's records whose kind isn't 0, packed (MH4U keeps each in 24 bytes). 31 files have the block (103 records): kinds 1 (75), 3 (1), 4 (21), 255 (6, all in one file) | verified | ours, loader; check E5 |
| +12·c2 | 12-byte records | part break HP records (object +0x68): u8 part, u8, u16, f32 HP, u8 ×4 | unverified | ours, loader; MHGU-DE notes/data.md names it (part break HP) |
| +16·c3 | 16-byte records | block (object +0x6C): u32, u32, u8, u8, u16, u8, u8, u16; no counterpart found | unknown | ours, loader |
| +15·c4 | 15-byte records | block (object +0x70): u16 ×5, u8 ×5; no counterpart found | unknown | ours, loader |
| +24·c5 | 24-byte records | block (object +0x74): 16 bytes, u32, u32; no counterpart found | unknown | ours, loader |
| +4·c6 | 4-byte records | block (object +0x78): u8 ×4; no counterpart found | unknown | ours, loader |
| +5·c7 | 5-byte records | visibility state records (object +0x7C): u8 ×5; MHGU Definitive Edition reads 5-byte state records here (Kushala's 12 are its 12 visibility states) | unverified | ours, loader; MHGU-DE notes/data.md |
| +4·c8 | 4-byte records | block (object +0x80): u16, u8, u8; no counterpart found | unknown | ours, loader |
| +4·c16 | 4-byte records | block (object +0x84): one u32 or f32 per record; no counterpart found | unknown | ours, loader |

The joint record's fields after the 13 bytes are not in the file: MH4U's record is 24 bytes, and MHXX packs the joint,
the kind and two of the four following words into 13.

## What this means for the mod

- **A GU monster's break records and joint records come from `dtbparts`.** `mhuc monsterdata` rebuilds the break parts
  and the joint records into MH4U's layout and compares them: the break parts are equal on the three monster pairs, and
  the joint records are 6 of 6 on Rathian and absent on both sides for Kushala Daora and Teostra.
- **MH4U's sever records have no counterpart in `dtbparts` or `dtbase`.** MH4U's `.emd` word 35 stores, after a
  (255, 0, 0, −1) marker, the kind-0 records that sever or detach a bone (3 on Rathian, 2 each on Kushala Daora and
  Teostra). No block of either file holds a kind-0 record: the joint-record block never has one, and the pairs' sever
  joints are not stored as records. Where MHXX keeps them is open.
- The part break HP records and the visibility state records are named from MHGU Definitive Edition's `dtbparts`
  work and stay unverified here; the blocks with no counterpart are the mod's to author or to leave alone.

## Checks

- **E7 (done, MHXX JPN v1.0 RomFS):** `mhuc survey <romfs.bin>` counts `E7 dtbparts layout ends at the file's end`.
  Result: 140 entries (138 distinct files) end exactly at their last byte.
- **Loader trace (done, MHXX v1.4 code, same RomFS):** `python3 reference/loader_trace.py mhxx-dtbparts --exheader
  <exheader.bin> --code <code.bin> --romfs <romfs.bin>` runs the game's loader in Unicorn on each file and logs every
  stream read. Result: it reads the whole file in all 138, and our reader's blocks split the same bytes (every block
  starts where a read starts, and every read starts inside a block).
- **E5 (done, the three monster pairs above):** `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mhxx
  arc/enemy/em001_00.arc` (likewise em031/em024_00, em032/em027_00) prints, per field, whether MHXX's value rebuilt into
  MH4U's layout equals MH4U's. Results: the break parts equal on all three pairs; the joint records 6 of 6 on Rathian,
  none on either side for the other two; MH4U's 3, 2 and 2 sever records absent from MHXX's files.
