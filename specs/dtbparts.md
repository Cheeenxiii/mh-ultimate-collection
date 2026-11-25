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
| +13·c1 | 13-byte records | joint records (object +0x64): s32 joint, u8 kind, u32 index, u32 limit. MH4U `.emd` word 35's records of kind 1 and 4 (and one of kind 255), packed; MH4U keeps each in 24 bytes and adds `a` 255 and `b` 0. MHXX's kind-3 record has no MH4U counterpart. 31 files have the block (103 records): kinds 1 (75), 3 (1), 4 (21), 255 (6, all in one file) | verified | ours, loader; check E5 |
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

## Sever and detach records: not in these files

MH4U's `.emd` word 35 keeps, after a (255, kind, 0, −1) marker in most files, one sever/detach record per bone a
part detaches or severs at: kind 0, 3 or 5, for cut type 1, 2 or 3 (checks E11, E12; [emd](emd.md)). Neither MHXX
file has one, and MHXX does not keep them as data: the joint is a constant in the monster class's own code, and the
cut part is a model beside the body model in the monster's archive.

**The search.** Three places could hold such a record, and none does:

| Searched | Result |
|---|---|
| `dtbparts` joint records, every file | 31 of the 140 entries have the block, 103 records: kinds 1 (75), 3 (1), 4 (21) and 255 (6, all six in one file, joints 200 to 205). Not one kind 0, and no (255, 0, 0, −1) marker (E11) |
| `dtbase`, the three pairs | no block matches the `.emd` word 35 records (E5) |
| every entry of `em001_00.arc` (546) | no u32 143 outside one texture's pixels: no data block spells out a joint (E11) |

**The cut part is a model.** Each of the three paired monsters' MHXX archive holds a `_tail.mod` beside its body
model (`enemy/em001/em001_00/mod/em001_00_tail.mod`, likewise em024_00 and em027_00), and MH4U and MH3U ship the
same pair (`em001_tail.mod` and so on): the cut piece travels as a model in all three games. MHXX's and MH4U's are
rigid (0 bones); MH3U's is skinned with three bones, 143 to 145 ([emstatus](emstatus.md#severing)).

**The joint is in the class's code.** MHXX v1.4 keeps each monster's class in its own `.cro` module, and each of
the three paired monsters' modules calls one static function with the joint:

| Monster | MHXX module | Call site | Joint in r3 |
|---|---|---|---|
| em001_00 Rathian | roEm001.cro | 0x0201c718 | 143 |
| em024_00 Kushala Daora | roEm024.cro | 0x0200e120 | 143 |
| em027_00 Teostra | roEm027.cro | 0x0200afa8 | 143 |

The callee is 0x008de84c in the v1.4 code. The call passes 0 in r1 and r2, the joint in r3, and a fifth argument on
the stack. Rathian's sits in its action-114 case (a compare against 0x72) after the handler has checked that the
severed part is 7, the tail. 29 of the 87 `roEm*.cro` modules call the same function, 35 calls in all; the value they
put in r3 is 143 in 15 of them and 3, 4, 138, 142, 144 or 145 in the rest (a single-digit bone is a part one monster
severs elsewhere than its tail).

The function's name is MHGU Definitive Edition's: their GU code calls `spawnCutPart` (0xc2330) as
`spawnCutPart(this, 0, 0, joint, 0)` from Kushala's action (10, 114), the same argument shape and the same action
id (their `monsters/gogmazios/notes/port-checklist.md`). What our check adds is the same call in MHXX's own module
and the joint it passes; the name stays theirs.

**What a port authors.** The sever records themselves, laid out as MH4U's are: the (255, kind, 0, −1) marker where
MH4U has one, then one record per bone, then the −1 terminator. The joints are the one the source class passes and
the bones that hang off it in the source model's chain: MH4U's own are 143, 144 and 145 on Rathian and 143 and 144
on Kushala Daora and Teostra, and both games' Rathian body models carry the same 43 bone ids with the same parents
([mod](mod.md), check M2). The record that spawns the cut object has `index` 1 and the cut object's kind: 0 for a
tail, and 0, 3 or 5 for cut types 1, 2 and 3 (0xc2d314 reads the byte at +4 and the word at +8). The records for the
other bones in the chain carry `index` 2 or 0, which 0xc2d314 skips. `a` is 0. `b` is 0 or an offset to a 24-byte
block of six offsets, which the `.emd` loader relocates; all 58 nonzero ones point at in-file blocks with three
nonzero words, and no MH4U reader uses the block, so what it drives is unknown. `limit` is the joint on 81 of the 95
records and one or two less on the rest; no MH4U reader reads it on a sever record. A port copies MH4U's shape; the
values of `limit`, `a` and `b` are not known to matter ([emd](emd.md), checks E11, E12).

## What this means for the mod

- **A GU monster's break records and joint records come from `dtbparts`.** `mhuc monsterdata` rebuilds the break parts
  and the joint records into MH4U's layout and compares them: the break parts are equal on the three monster pairs, and
  the joint records are 6 of 6 on Rathian and absent on both sides for Kushala Daora and Teostra.
- **MH4U's sever records have no counterpart in `dtbparts` or `dtbase`; they are code on MHXX's side.** MH4U's
  `.emd` word 35 stores, after a (255, kind, 0, −1) marker, the sever/detach records that name a bone (3 on Rathian,
  2 each on Kushala Daora and Teostra). Their kind is 0, 3 or 5, for a cut type 1, 2 or 3; MH4U's cut-object
  spawner 0xc2d314 reads the kind, the `index` (1 on the record it acts on) and the joint, and no reader reads
  `limit`, `a` or `b` on a sever record ([emd](emd.md#joint-and-sever-record-24-bytes)). No block of either file
  holds a sever record, and the pairs' sever joints are not stored as records: the monster class passes the joint to
  the engine's cut-part spawner, and the cut part is a separate `_tail.mod`. A port therefore authors the records
  ("Sever and detach records").
- The part break HP records and the visibility state records are named from MHGU Definitive Edition's `dtbparts`
  work and stay unverified here; the blocks with no counterpart are the mod's to author or to leave alone.

## Checks

- **E7 (done, MHXX JPN v1.0 RomFS):** `mhuc survey <romfs.bin>` counts `E7 dtbparts layout ends at the file's end`.
  Result: 140 entries (138 distinct files) end exactly at their last byte.
- **E11 (done, MHXX JPN v1.0 RomFS and v1.4 code):** three parts.
  `mhuc survey <romfs.bin> --workers 2` counts `E11 dtbparts joint records` and `E11 dtbparts [no] joint record of
  kind 0`. Result: 103 joint records over 31 of the 140 entries, kinds 1 (75), 3 (1), 4 (21) and 255 (6), and those 31
  entries report no kind-0 record.
  `python3 reference/cro.py calls <module> --game mhxx` loads a monster module at recompile_module.py's base with the
  static segment bases in `reference/games/mhxx/game.json` and prints its calls into the static code with the nearest
  constant in r0..r3; `--arg r3=0x8f` keeps only the calls that pass 143. Result: one call each in roEm001
  (0x0201c718 -> 0x008de84c), roEm024 (0x0200e120 -> 0x008de84c) and roEm027 (0x0200afa8 -> 0x008de84c), every one
  with 143 in r3; without the filter, 29 of the 87 `roEm*.cro` modules call 0x008de84c (35 calls).
  A scan of the 546 entries of `em001_00.arc` for a u32 of 143 finds one, in a texture's pixels.
- **Loader trace (done, MHXX v1.4 code, same RomFS):** `python3 reference/loader_trace.py mhxx-dtbparts --exheader
  <exheader.bin> --code <code.bin> --romfs <romfs.bin>` runs the game's loader in Unicorn on each file and logs every
  stream read. Result: it reads the whole file in all 138, and our reader's blocks split the same bytes (every block
  starts where a read starts, and every read starts inside a block).
- **E5 (done, the three monster pairs above):** `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mhxx
  arc/enemy/em001_00.arc` (likewise em031/em024_00, em032/em027_00) prints, per field, whether MHXX's value rebuilt into
  MH4U's layout equals MH4U's. Results: the break parts equal on all three pairs; the joint records 6 of 6 on Rathian,
  none on either side for the other two; MH4U's 3, 2 and 2 sever records absent from MHXX's files.
