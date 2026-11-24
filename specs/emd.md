---
class: rEnemyData (.emd), rEnemyTuneData (.etd)
extension: emd, etd (in data/em_data.arc, one pair per monster: enemy\emNNN\data\emNNN)
games: MH4U (USA v1.3.0 checked, E1; MHGU Definitive Edition read the European v1.1)
status: unknown
---

# rEnemyData and rEnemyTuneData: a monster's body, hitzones, parts and attacks

Every MH4U monster with files has one `.emd` and one `.etd` in `data/em_data.arc` (110 pairs, id-tables.md). They hold what the quest and the stage don't: hurt volumes and the hitzone and part each one belongs to, the hitzone ("meat") rows, part HP and breaks, attack volumes and attack records, ailment buildups, stamina, the sensor (eye) records, and the base HP. That is what a new 3U or GU monster has to bring (id-tables.md, "Monster parts, breaks, rewards").

**Source.** Everything here comes from Scrimas's MHGU Definitive Edition (GPL-3.0-or-later, `tools/emdata4u.py`, `tools/dt_convert.py`, `notes/data.md`, `notes/porting-guide.md`, read at commit bd3785d of 2026-11-22). That project ports MH4U monsters into MHGU. It reads these two files from the European MH4U v1.1, converts them into MHGU's `bodydata`, `cambodydata`, `hitsize`, `attackdata`, `dtbase` and `dttune`, and checks the conversion by rebuilding MHGU's own files for monsters both games have (Rathian, Kushala Daora, Teostra, Diablos: 95 to 99.7 % equal bytes, by its notes). Check E1 (below) ran on our USA v1.3.0 files: the structure holds on all 110 pairs, and the hitzone table is laid out from it and from the public hitzone tables. Fields E1 doesn't reach stay unverified, and offsets in code (theirs are EUR v1.1 and MHGU) don't apply to our build. The ids and counts quoted are theirs. Credited in specs/README.md.

The class ids MHGU-DE uses for the two ARC entries, 0x0A0E48D4 (`.emd`) and 0x3D8BBBAC (`.etd`), are the ones our own MH4U class registry gives `rEnemyData` and `rEnemyTuneData` (the fork's `config/mt_classes.tsv`), which ties their files to ours.

Both files start with a header of u32 words, most of them offsets of blocks inside the file (0 when absent). "Word n" is the u32 at 4·n.

## .emd header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x0C, 0x10, 0x14 | u32 or f32 | scalars: 0x0C and 0x10 into MHXX's `dtbase` object +0x60 and +0x64, 0x14 into `dttune` +0xEC (and MHGU's `dtbase` +0xA0); equal to MHXX's on the three pairs | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| word 8 (0x20) | offset | body data: the hurt (and push) volumes, 44-byte records until a record whose first u16 is 0xFFFF (table "Body record"); set in all 110, every list ends | verified | MHGU-DE `emdata4u.bodydata`; check E1 |
| word 9 (0x24) | offset | camera body data: the same records, for the camera (0 in 3 of 110) | verified | MHGU-DE `emdata4u.bodydata`; check E1 |
| word 13 (0x34) | offset | a 32-byte block: MHXX's `dtbase` block +0x6C, 16 u16; equal on the three pairs | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| 0x30 | u32 | a scalar: MHXX's `dtbase` object +0x68; equal on the three pairs | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| word 16 (0x40) | offset | arena point table (the game uses another on stage 13) | unverified | MHGU-DE porting-guide.md |
| word 20 (0x50) | offset | map-hit sphere: 52 bytes, four offsets then a radius; MHXX's `dtbase` map-hit sphere record, equal on Kushala Daora and Teostra and 51 of 52 bytes on Rathian | verified | MHGU-DE `dt_convert.py`, porting-guide.md; specs/dtbase.md; check E5 |
| word 21 (0x54) | offset | a second 52-byte block: MHXX's `dtbase` +0x84; equal on Kushala Daora and Teostra, 51 of 52 bytes on Rathian | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| word 22 (0x58) | offset | a 4-byte block: MHXX's `dtbase` +0x88; equal on all three pairs | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| 0x6C, 0x70, 0x78, 0x7C | u32 or f32 | scalars, in this order with 0x14: MHXX's `dtbase` block +0x94; equal on the three pairs | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| word 32 (0x80) | offset | part break table: 32-byte records (u8 part, u8 break count, u8, u8, u8 group, u32 joint at +8, f32 at +0xC, u8 0xFF, RGB at +0x1D) until a part of 0xFF; its breakable parts equal MHXX's `dtbparts` break records on the three pairs | unverified | MHGU-DE `dala_break.c`; specs/dtbparts.md; check E5 |
| word 33 (0x84) | offset | break list: (s32 group, u32 param) pairs until group −1; no counterpart found in MHXX's `dtbase` or `dtbparts` | unverified | MHGU-DE notes/data.md; specs/dtbparts.md; check E5 |
| word 34 (0x88) | offset | part visibility rows, 16 bytes each until a group of −1 (table "Visibility row"); 0 in 6 of 110, every list ends | verified | MHGU-DE `emdata4u.part_rows`; check E1 |
| word 35 (0x8C) | offset | joint and sever records: 24-byte records (s32 joint, u32 kind, u32 index, u32 limit, u32 255, u32 0) until a joint of −1. The records whose kind isn't 0 are MHXX's `dtbparts` joint records (6 of 6 on Rathian); the kind-0 records after a (255, 0, 0, −1) marker are the sever/detach records, which no `dtbase` or `dtbparts` block holds | verified | MHGU-DE notes/data.md; ours, `mhuc monsterdata`; specs/dtbparts.md; check E5 |
| word 38 (0x98) | offset | a 64-byte block: MHXX's `dtbase` +0x70; equal on Rathian, 54 and 55 of 64 bytes on Kushala Daora and Teostra (MHGU retunes it) | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| word 39 (0x9C) | offset | a 12-byte block: MHXX's `dtbase` +0x74; equal on Rathian, absent on both sides for Kushala Daora and Teostra | verified | specs/dtbase.md; check E5 |
| word 40 (0xA0) | offset | slope fit: records, a u8 shift, 3 floats, then 44-byte joint records | unverified | MHGU-DE `dt_convert.py` |
| word 43 (0xAC) | offset | joint points: 56 bytes = two 28-byte records, MHXX's `dtbase` +0xA8; equal on all three pairs | verified | MHGU-DE `dt_convert.py`; specs/dtbase.md; check E5 |
| word 44 (0xB0) | offset | 32-byte records closed by one whose first u32 is 0xFF: MHXX's `dtbase` +0xAC, equal on Rathian and absent on both sides for Kushala Daora and Teostra | verified | specs/dtbase.md; check E5 |

### Body record (44 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 | bone A (0xFFFF ends the list) | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x02 | u16 | bone B (the far end of a two-bone capsule) | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x04 | u16 | shape: 0 sphere, 1 capsule from off1 to off2 on bone A, 2 capsule from A+off1 to B+off2 (only 0, 1, 2 in 4,521 records; the meanings not checked) | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x06 | u16 | hitzone row (an index into the `.etd`'s hitzone table: below 8 in all 110; Rathian's rows 0–6 are her parts) | verified | MHGU-DE notes/data.md; check E1 |
| +0x08 | u16 | part index (0..7 in all 4,521 records; the part's HP and breaks are in the `.etd` part table) | verified | MHGU-DE notes/data.md; check E1 (range) |
| +0x0A | u16 ×3 | flags | unknown | MHGU-DE `emdata4u.bodydata` |
| +0x10 | f32 | radius | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x14 | f32 ×3 | off1 | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x20 | f32 ×3 | off2 | unverified | MHGU-DE `emdata4u.bodydata` |

### Visibility row (16 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | s32 | model part group (−1 ends the list) | unverified | MHGU-DE `emdata4u.part_rows` |
| +0x04 | u16 | condition: 7 a state-word bit (param is the mask), 6 a break record broken (param), 1 a sever done (param), 11 unknown; values seen in 1,568 rows: 0, 1, 5, 6, 7, 8, 10, 11 | unverified | MHGU-DE `emdata4u.row_visible` |
| +0x06 | u16 | mode: 0 hidden while the condition holds, 1 hidden while it doesn't (only 0 and 1 seen) | unverified | MHGU-DE `emdata4u.part_rows` |
| +0x08 | u32 | param | unverified | MHGU-DE `emdata4u.part_rows` |
| +0x0C | u32 | threshold | unverified | MHGU-DE `emdata4u.part_rows` |

## .etd header

40 words; the blocks start at 0xA0. Words 5 to 34 are each 0 or an offset into the file (in all 107 `.etd` the European game has, by MHGU-DE's count; in all 110 of USA v1.3.0, check E1). Words 35 to 39 are scalars.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| word 4 (0x10) | u32 | base HP (Kushala Daora 4200, Gogmazios 17500; a quest scales it by its own table); 1..100,000 in all 110 | unverified | MHGU-DE notes/data.md |
| word 5 (0x14) | offset | part table: 8 × 10 bytes, one per part: u16 part HP, u8 break levels, u8 ×3, u16 second-level HP (0xFFFF none), u16 kind | unverified | MHGU-DE `dt_convert.py` |
| word 7 (0x1C) | offset | hitzone table: 80 bytes in all 110, **8 rows of 10 bytes** (table "Hitzone row"); the body record's +0x06 picks a row (`dttune` +0x70 in MHGU). Find it by this word rather than at a fixed offset | verified | MHGU-DE `dt_convert.py`, porting-guide.md; check E1 |
| word 8 (0x20) | offset | an 80-byte table beside it (`dttune` +0x74) | unknown | MHGU-DE `dt_convert.py` |
| word 9 (0x24) | offset | sensor (eye) records, 28 bytes each, ending at an s32 0xFFFF: joint, range, near radius, angles | unverified | MHGU-DE `dt_convert.py` |
| words 10, 11 | offset | ranges, every row with its count | unknown | MHGU-DE `dt_convert.py` |
| word 13 | offset | a block whose first bytes MHGU's loader reads as a loop count | unknown | MHGU-DE `dt_convert.py` |
| word 16 | offset | stamina | unverified | MHGU-DE `dt_convert.py` |
| words 17..21, 23, 24, 26 | offset | ailment buildups (12 or 16 bytes each where present) | unverified | MHGU-DE `dt_convert.py` |
| word 25 | offset | a block of at least 14 bytes | unknown | MHGU-DE `dt_convert.py` |
| word 27 (0x6C) | offset | attack volumes ("hitsize"): one offset per group up to word 28; a group is 40-byte records (capsules: off2 at +28) closed by a record whose first u16 is 0xFFFF; 2,184 groups, 5,463 volumes, every group ends | verified | MHGU-DE `emdata4u.hitsize`; check E1 |
| word 28 (0x70) | offset | attack records, 40 bytes each, up to word 29 (whole records in all 86 files where word 29 is set). Where word 29 is 0 (24 files) no header word marks the end and the block runs into an unpointed tail of 4 to 16 bytes over whole records (the stride is what E1 verifies); byte 18 holds knockback bits | verified | MHGU-DE `emdata4u.attackdata`; check E1 |
| word 29 (0x74) | offset | a 24-byte part table (`dttune` +0xC8) | unverified | MHGU-DE `dt_convert.py` |
| word 30 | offset | a block read with the ailments (`dttune` +0xCC) | unknown | MHGU-DE `dt_convert.py` |
| 0x8C, 0x90, 0x94, 0x9C | u32 or f32 | scalars (`dttune` +0xE0, +0xE4, +0xE8, +0xF0) | unverified | MHGU-DE `dt_convert.py` |

### Hitzone row (10 bytes, 8 rows)

Laid out by check E1: the column order is Kiranico's damage chart order, matched on Rathian (em001), whose rows 0 to 6 equal the chart's seven regions (head, neck, back, belly, tail, wing, legs) in all eight columns.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0 .. +7 | u8 ×8 | cut, impact, shot, fire, water, ice, thunder, dragon (percent) | verified | ours; check E1 against kiranico.com/en/mh4u/monster/rathian |
| +8 | u8 | 100 on Rathian's head row, 0 elsewhere: the stun (KO) zone, presumably (the chart's "Dizzy" column is empty) | unverified | ours; check E1 |
| +9 | u8 | 100 in every row of Rathian: exhaust, perhaps | unknown | ours; check E1 |

Rathian's row 7 is 100 in all ten bytes and no body record uses it.

## What this means for the mod

- **A monster's hitzones, parts and breaks travel with its own `.emd`/`.etd`.** A new monster brings its pair, loaded by id through `enemyDataPathIndex` (id-tables.md), with no shared table to grow. MHGU's equivalents (`dtbase`, `dttune`, `dtbparts`, `bodydata`, `hitsize`, `attackdata`) map onto MH4U's per word, and MHGU-DE converts them in the GU direction. The GU-to-4U direction this mod needs is the same mapping run backwards: the reverse of `emdata4u.py` and `dt_convert.py`.
- **The source games split the same data over several files.** MHXX's `dttune` holds the `.etd`'s HP, part table, hitzones, ranges, rage and ailments in a stream (specs/dttune.md); its `dtbase` holds the `.emd` blocks named above and its `dtbparts` the break and joint records (specs/dtbase.md, specs/dtbparts.md); the break records and joint records are not byte-equal to MH4U's, and MH4U's sever records have no counterpart found (specs/dtbparts.md). MH3U's `em_status00` holds HP, part HP and hitzones in an aligned walk, and its part HP, second-level HP and per-part break records (specs/emstatus.md); both keep hurt volumes, attack volumes and attack records in files of their own (specs/hitdata.md). MH3U has no `.emd`: its part model-group changes are code, and a severed part is a separate `emNNN_tail.mod` the class swaps in. `mhuc monsterdata` rebuilds MH4U's values from them and compares.
- **Bone ids are the model's.** MHGU-DE keeps 4U's bone ids and remap table when converting models, so the data needs no remap, except where a bone is missing from the target skeleton.

## Checks

- **E1 (done, MH4U USA v1.3.0 RomFS):** `mhuc survey` (or `mhuc emd check <data/em_data.arc>`). Results, all 110 pairs: both magics; every `.emd` word listed and every `.etd` word 5 to 34 is 0 or inside its file; every body-record list (2,917 body, 1,604 camera records) ends at a 0xFFFF bone, with shapes 0, 1, 2 only and parts below 8; every visibility list (1,568 rows) ends at −1, modes 0 and 1 only; base HP 1..100,000; 2,184 attack-volume groups, all ending; attack records whole wherever word 29 marks their end. The hitzone table is 80 bytes in every `.etd` and the body records' rows stay below 8: the first run's histogram of "table bytes / rows used" (10, 16, 20, 40, 80, and 31 not whole) only meant that most monsters leave rows unused; 10 bytes is the only row size that fits all 110. Comparing em001's rows with Kiranico's Rathian damage chart then fixed the columns (table "Hitzone row") and showed em001 is Rathian. Still open: the `.etd` part table, sensors, ailments, and the `.emd` scalars, which no count reaches.
