---
class: rEnemyDtTune
extension: dttune (in each monster's arc/enemy/emNNN_SS.arc: enemy\dt_tune\emNNN_SS_dttune)
games: MHXX (JPN v1.0 RomFS, v1.4 code; MHGU on Switch has the same class)
status: unknown
---

# rEnemyDtTune: an MHXX monster's HP, parts, hitzones and tuning

MHXX's counterpart of MH4U's `.etd` (specs/emd.md). One per monster variant (138 files in MHXX, class id 0x48E8AC29, a `cResource` of 0x128 bytes in MHXX's registry). MH4U's registry has a class of the same name and id, but MH4U ships no file of it.

**Layout.** A 0x38-byte header, then blocks read one after another with no offsets: what is present depends on ten count bytes and 35 flag bytes in the header. The order and sizes are MHXX's own loader's (`rEnemyDtTune` vtable slot 11, 0x002b7f80 in the v1.4 code): it reads the header into a buffer, copies the counts to object +0xF4 and the flags to +0xFE, then reads each block with the stream read 0x0028140c into memory it allocates and stores at a fixed object field. Check E2 runs our reader (`mhuc.formats.dttune`) on every file and `reference/loader_trace.py` runs the loader itself on every file: the layout below ends exactly at the file's end in all 138, and its blocks are the loader's reads.

**Meaning.** Each block is named after the MH4U `.etd` block it equals, checked by rebuilding MH4U's values from MHXX's files (`mhuc monsterdata`, check E5) for the three monsters MHGU Definitive Edition pairs across the games: Rathian (MH4U em001, MHXX em001_00), Kushala Daora (em031, em024_00) and Teostra (em032, em027_00). A block that equals MH4U's on those monsters has MH4U's layout, and its fields keep the status specs/emd.md gives them; a block that differs where GU retuned a monster keeps its layout but not a value. Blocks without an MH4U counterpart are unknown.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `DTT\0` | verified | ours, loader 0x002b7f80; check E2 |
| 0x04 | u32 | version 0x0133A06C (the loader rejects any other) | verified | ours, loader; check E2 |
| 0x08 | u8 ×10 | counts c0..c9, copied to object +0xF4 (table "Blocks" says what each counts) | verified | ours, loader; check E2 |
| 0x12 | u8 ×35 | flags f0..f34, copied to object +0xFE: **0 = the block is present** | verified | ours, loader; check E2 |
| 0x35 | u8 ×3 | not read | verified | ours, loader |

## Blocks

In file order. "Object" is where the loader puts the block (a pointer to it, except for base HP and the scalars). Sizes are in bytes.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x38 | u32 | base HP (object +0x60): MH4U `.etd` word 4, equal on all three monsters | verified | ours, loader; checks E2, E5 |
| +0x50 | 8 × 10 bytes | part table (+0x64): MH4U `.etd` word 5's 80 bytes; equal for Rathian and Teostra, all 8 part HPs equal for Kushala (one second-level HP differs) | verified | ours, loader; checks E2, E5 |
| +c0 | u8 × c0 | part break bytes (+0x68); no counterpart found | unknown | ours, loader |
| +0x50 | 8 × 10 bytes | hitzone table (+0x6C): MH4U `.etd` word 7, the same 8 rows of 10 bytes (specs/emd.md, "Hitzone row"); equal for Rathian and Teostra, 7 of 8 rows for Kushala | verified | ours, loader; checks E2, E5 |
| f0: +0x50 | 80 bytes | a second table of the hitzone table's size (+0x70); MH4U `.etd` word 8 is 80 bytes too; absent on the three monsters | unverified | ours, loader; MHGU-DE `dt_convert.py` |
| +32·c1 | 32-byte records | sensor (eye) records (+0x74): MH4U `.etd` word 9's 28-byte records with 4 bytes after the s32 joint, and no closing record (c1 counts them). The joint and the three words after the inserted bytes are equal on Rathian; the radius right after the joint differs on all three (GU retuned it, as MHGU-DE notes) | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| +16·c2 | 4 × f32 rows | distance ranges (+0x78): MH4U `.etd` word 10 without its closing row of −1; equal on all three | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| +12·c3 | 3 × f32 | range offsets (+0x7C), one per range row: MH4U `.etd` word 11; equal on all three | verified | ours, loader; checks E2, E5 |
| f1 (f2: +0x10, f3: +0x1C) | bytes | two blocks under one pointer (+0x80 → two pointers) | unknown | ours, loader |
| f4 (f5: f6 +0x10, f7 +0x20, f8 +0x28; f9: f10 +0x10, f11 +0x20, f12 +0x20; f13: f14 +0x10, f15 +0x20) | bytes | three groups of blocks (+0x84 → three pointers, each to up to three blocks) | unknown | ours, loader |
| f16: +0x7C | bytes | rage (+0x88): its first 56 bytes are MH4U `.etd` word 14, equal on all three; the other 68 have no MH4U counterpart | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| f17: +4 | bytes | a 4-byte block (+0x8C) | unknown | ours, loader |
| c4 ≠ 0: see "Block 0x90" | | a table of u16 lists (+0x90) | unknown | ours, loader |
| f18: +0x10 | bytes | ailment buildup (+0x94): MH4U `.etd` word 17, equal on all three | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| f19..f25: +0x0C each | bytes | seven more ailment buildups (+0x98..+0xB0): MH4U `.etd` words 18 to 24 in order. 18, 19, 20 and 22 equal on all three; 21 differs on two (absent on Teostra); 23 and 24 differ on all three, with the same shape (retuned) | unverified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| f26: +0x0E | bytes | MH4U `.etd` word 25's first 14 bytes (+0xB4); equal on Rathian and Teostra | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| f27 (f28..f31: +6 each) | bytes | four 6-byte blocks (+0xB8 → four pointers) | unknown | ours, loader |
| +24·c7 | 24-byte records | second part table (+0xC4): MH4U `.etd` word 29, same record count; 8 of 12 records equal on Rathian, all on Kushala and Teostra | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |
| f32: +0x90 | bytes | a block (+0xC8) whose start lines up with MH4U `.etd` word 30 (72 bytes); the rest is filled with 0xCD in Rathian's | unverified | ours, loader; check E5 |
| f33: +0x0C | bytes | a block (+0xCC) | unknown | ours, loader |
| +36·c8 | 36-byte records | focus points (+0xD0): MH4U `.etd` word 33's records (joint A + offset, joint B + offset, radius) | unverified | ours, loader; MHGU-DE `dt_convert.py` |
| +36·c9 | 36-byte records | a second focus list (+0xD4) | unverified | ours, loader; MHGU-DE `dt_convert.py` |
| f34: +0x80 | bytes | a block (+0xD8) | unknown | ours, loader |
| +4 ×5 | u32 or f32 | five scalars (+0xDC..+0xEC): MH4U `.etd` words 35 to 39, in order; 4 of 5 equal on Rathian and Teostra, 3 on Kushala | verified | ours, loader; MHGU-DE `dt_convert.py`; checks E2, E5 |

### Block 0x90

Read only when c4 ≠ 0. The loader allocates a 12-byte object at +0x90, then:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0 | u16 | head (object +0) | verified | ours, loader 0x002b8668; check E2 |
| then, c5 times | u32 n, u16 key, u16 × n | a list: its length n (kept in a separate array at object +0xF0), a key (+4 of an 8-byte entry), its n values (pointer at +0 of the entry) | verified | ours, loader; check E2 |
| then | u32 × c6 | words (object +8) | verified | ours, loader; check E2 |

What the lists mean is unknown: MH4U's stamina block (`.etd` word 16) is not this.

## What this means for the mod

- **A GU monster's HP, part HP and hitzones come straight from its `dttune`.** They are byte for byte MH4U's layout: `mhuc monsterdata` rebuilds MH4U's base HP, part table and hitzone table, and the ranges, rage and most ailment blocks.
- **A GU monster also needs what MH4U's `.etd` has and GU's file lacks** (the break records of `.emd` word 33, the stamina of `.etd` word 16) and drops what GU added (the rest of rage, the blocks marked unknown). Where GU retuned MH4U's monsters, the GU values are the source game's and stay (fidelity rule).
- MHXX's other monster files: hurt volumes, attack volumes and attack records are in specs/hitdata.md. `dtbase` (rEnemyDtBase, loader 0x002b6f88) and `dtbparts` (rEnemyDtBaseParts, loader 0x0058e424) are not specced here.

## Checks

- **E2 (done, MHXX JPN v1.0 RomFS):** `mhuc survey` counts `E2 dttune layout ends at the file's end`. Result: the layout above ends exactly at the end of all 140 `dttune` entries (138 distinct files; two archives carry a copy).
- **Loader trace (done, MHXX v1.4 code, same RomFS):** `python3 reference/loader_trace.py mhxx --exheader … --code … --romfs …` runs the game's loader in Unicorn on each file and logs every stream read. Result: it reads the whole file in all 138, and our reader's blocks cover the same bytes, each starting where a read starts. The game reads the lists of block 0x90 two bytes at a time; the reader takes each list whole.
- **E5 (done, the three monster pairs above):** `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mhxx arc/enemy/em001_00.arc` (likewise em031/em024_00, em032/em027_00) prints, per field, whether MHXX's value rebuilt into MH4U's layout equals MH4U's. Results are in the tables above, as counts.
