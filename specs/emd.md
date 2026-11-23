---
class: rEnemyData (.emd), rEnemyTuneData (.etd)
extension: emd, etd (in data/em_data.arc, one pair per monster: enemy\emNNN\data\emNNN)
games: MH4U (from the European game v1.1's files, as MHGU Definitive Edition read them; USA v1.3.0 not checked)
status: unknown
---

# rEnemyData and rEnemyTuneData: a monster's body, hitzones, parts and attacks

Every MH4U monster with files has one `.emd` and one `.etd` in `data/em_data.arc` (110 pairs, id-tables.md). They hold what the quest and the stage don't: hurt volumes and the hitzone and part each one belongs to, the hitzone ("meat") rows, part HP and breaks, attack volumes and attack records, ailment buildups, stamina, the sensor (eye) records, and the base HP. That is what a new 3U or GU monster has to bring (id-tables.md, "Monster parts, breaks, rewards").

**Source.** Everything here comes from Scrimas's MHGU Definitive Edition (GPL-3.0-or-later, `tools/emdata4u.py`, `tools/dt_convert.py`, `notes/data.md`, `notes/porting-guide.md`, read at commit bd3785d of 2026-11-22). That project ports MH4U monsters into MHGU. It reads these two files from the European MH4U v1.1, converts them into MHGU's `bodydata`, `cambodydata`, `hitsize`, `attackdata`, `dtbase` and `dttune`, and checks the conversion by rebuilding MHGU's own files for monsters both games have (Rathian, Kushala Daora, Teostra, Diablos: 95 to 99.7 % equal bytes, by its notes). Nothing here has been checked on our USA v1.3.0 files yet. Every field is unverified until check E1 below runs, and offsets in code (theirs are EUR v1.1 and MHGU) don't apply to our build. The ids and counts quoted are theirs. Credited in specs/README.md.

The class ids MHGU-DE uses for the two ARC entries, 0x0A0E48D4 (`.emd`) and 0x3D8BBBAC (`.etd`), are the ones our own MH4U class registry gives `rEnemyData` and `rEnemyTuneData` (specs/placeholders/, from the fork's `config/mt_classes.tsv`), which ties their files to ours.

Both files start with a header of u32 words, most of them offsets of blocks inside the file (0 when absent). "Word n" is the u32 at 4·n.

## .emd header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x0C, 0x10, 0x14 | u32 or f32 | scalars copied into MHGU's `dtbase` object (+0x64, +0x68, +0xA0); 0x14 also into `dttune` +0xEC | unverified | MHGU-DE `dt_convert.py` |
| word 8 (0x20) | offset | body data: the hurt (and push) volumes, 44-byte records until a record whose first u16 is 0xFFFF (table "Body record") | unverified | MHGU-DE `emdata4u.bodydata` |
| word 9 (0x24) | offset | camera body data: the same records, for the camera | unverified | MHGU-DE `emdata4u.bodydata` |
| word 13 (0x34) | offset | a 32-byte block (into `dtbase` +0x70; 39 of 40 shared monsters equal to MHGU's) | unverified | MHGU-DE `dt_convert.py` |
| 0x30 | u32 | a scalar (into `dtbase` +0x6C) | unverified | MHGU-DE `dt_convert.py` |
| word 16 (0x40) | offset | arena point table (the game uses another on stage 13) | unverified | MHGU-DE porting-guide.md |
| word 20 (0x50) | offset | map-hit sphere: 4 offsets and a radius, 52 bytes (`dtbase` +0x84) | unverified | MHGU-DE `dt_convert.py`, porting-guide.md |
| word 21, 22 | offset | 52-byte and 4-byte blocks (`dtbase` +0x88, +0x8C) | unverified | MHGU-DE `dt_convert.py` |
| 0x6C, 0x70, 0x78, 0x7C | u32 or f32 | scalars (`dtbase` +0x98, +0x9C, +0xA4, +0xA8) | unverified | MHGU-DE `dt_convert.py` |
| word 33 (0x84) | offset | break list (part groups that change when a part breaks) | unverified | MHGU-DE notes/data.md |
| word 34 (0x88) | offset | part visibility rows, 16 bytes each until a group of −1 (table "Visibility row") | unverified | MHGU-DE `emdata4u.part_rows` |
| word 35 (0x8C) | offset | sever and detach records (bones of the tail, for instance) | unverified | MHGU-DE notes/data.md |
| word 38 (0x98) | offset | a 64-byte block (`dtbase` +0x74; MHGU retunes it) | unverified | MHGU-DE `dt_convert.py` |
| word 40 (0xA0) | offset | slope fit: records, a u8 shift, 3 floats, then 44-byte joint records | unverified | MHGU-DE `dt_convert.py` |
| word 43 (0xAC) | offset | joint points, 56 bytes | unverified | MHGU-DE `dt_convert.py` |

### Body record (44 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 | bone A (0xFFFF ends the list) | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x02 | u16 | bone B (the far end of a two-bone capsule) | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x04 | u16 | shape: 0 sphere, 1 capsule from off1 to off2 on bone A, 2 capsule from A+off1 to B+off2 | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x06 | u16 | hitzone row (an index into the `.etd`'s hitzone table) | unverified | MHGU-DE notes/data.md |
| +0x08 | u16 | part index (0..7; the part's HP and breaks are in the `.etd` part table) | unverified | MHGU-DE notes/data.md |
| +0x0A | u16 ×3 | flags | unknown | MHGU-DE `emdata4u.bodydata` |
| +0x10 | f32 | radius | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x14 | f32 ×3 | off1 | unverified | MHGU-DE `emdata4u.bodydata` |
| +0x20 | f32 ×3 | off2 | unverified | MHGU-DE `emdata4u.bodydata` |

### Visibility row (16 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | s32 | model part group (−1 ends the list) | unverified | MHGU-DE `emdata4u.part_rows` |
| +0x04 | u16 | condition: 7 a state-word bit (param is the mask), 6 a break record broken (param), 1 a sever done (param), 11 unknown | unverified | MHGU-DE `emdata4u.row_visible` |
| +0x06 | u16 | mode: 0 hidden while the condition holds, 1 hidden while it doesn't | unverified | MHGU-DE `emdata4u.part_rows` |
| +0x08 | u32 | param | unverified | MHGU-DE `emdata4u.part_rows` |
| +0x0C | u32 | threshold | unverified | MHGU-DE `emdata4u.part_rows` |

## .etd header

40 words; the blocks start at 0xA0. Words 5 to 34 are each 0 or an offset into the file (in all 107 `.etd` the European game has, by MHGU-DE's count). Words 35 to 39 are scalars.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| word 4 (0x10) | u32 | base HP (Kushala Daora 4200, Gogmazios 17500; a quest scales it by its own table) | unverified | MHGU-DE notes/data.md |
| word 5 (0x14) | offset | part table: 8 × 10 bytes, one per part: u16 part HP, u8 break levels, u8 ×3, u16 second-level HP (0xFFFF none), u16 kind | unverified | MHGU-DE `dt_convert.py` |
| word 7 (0x1C) | offset | hitzone table, 80 bytes in the files compared (`dttune` +0x70); the body record's +0x06 picks a row. Find the row by this word rather than at a fixed offset (rows didn't start at the same byte in two of MHGU's files) | unverified | MHGU-DE `dt_convert.py`, porting-guide.md |
| word 8 (0x20) | offset | an 80-byte table beside it (`dttune` +0x74) | unknown | MHGU-DE `dt_convert.py` |
| word 9 (0x24) | offset | sensor (eye) records, 28 bytes each, ending at an s32 0xFFFF: joint, range, near radius, angles | unverified | MHGU-DE `dt_convert.py` |
| words 10, 11 | offset | ranges, every row with its count | unknown | MHGU-DE `dt_convert.py` |
| word 13 | offset | a block whose first bytes MHGU's loader reads as a loop count | unknown | MHGU-DE `dt_convert.py` |
| word 16 | offset | stamina | unverified | MHGU-DE `dt_convert.py` |
| words 17..21, 23, 24, 26 | offset | ailment buildups (12 or 16 bytes each where present) | unverified | MHGU-DE `dt_convert.py` |
| word 25 | offset | a block of at least 14 bytes | unknown | MHGU-DE `dt_convert.py` |
| word 27 (0x6C) | offset | attack volumes ("hitsize"): one offset per group up to word 28; a group is 40-byte records (capsules: off2 at +28) closed by a record whose first u16 is 0xFFFF | unverified | MHGU-DE `emdata4u.hitsize` |
| word 28 (0x70) | offset | attack records, 40 bytes each, up to word 29 (or to the next block when word 29 is 0); byte 18 holds knockback bits | unverified | MHGU-DE `emdata4u.attackdata` |
| word 29 (0x74) | offset | a 24-byte part table (`dttune` +0xC8) | unverified | MHGU-DE `dt_convert.py` |
| word 30 | offset | a block read with the ailments (`dttune` +0xCC) | unknown | MHGU-DE `dt_convert.py` |
| 0x8C, 0x90, 0x94, 0x9C | u32 or f32 | scalars (`dttune` +0xE0, +0xE4, +0xE8, +0xF0) | unverified | MHGU-DE `dt_convert.py` |

## What this means for the mod

- **A monster's hitzones, parts and breaks travel with its own `.emd`/`.etd`.** A new monster brings its pair, loaded by id through `enemyDataPathIndex` (id-tables.md), with no shared table to grow. MHGU's equivalents (`dtbase`, `dttune`, `dtbparts`, `bodydata`, `hitsize`, `attackdata`) map onto MH4U's per word, and MHGU-DE converts them in the GU direction. The GU-to-4U direction this mod needs is the same mapping run backwards: the reverse of `emdata4u.py` and `dt_convert.py`.
- **MH3U's monster data is another layout**, unknown here. Cha-Cha (docs/sources/cha-cha.md) is the lead on that side.
- **Bone ids are the model's.** MHGU-DE keeps 4U's bone ids and remap table when converting models, so the data needs no remap, except where a bone is missing from the target skeleton.

## Checks

- **E1 (open, needs the MH4U USA v1.3.0 RomFS):** for every `.emd`/`.etd` pair in `data/em_data.arc`, check the magic, that words 5 to 34 of the `.etd` and the `.emd` words named above are 0 or offsets inside the file, that the body-record lists end at a 0xFFFF bone, that the visibility rows end at a group of −1, and that the body records' hitzone rows and part indexes stay within the `.etd`'s tables. Record counts only. Then compare one monster's hitzone rows with the wiki's hitzone table for it, as Q20 did for quests.
