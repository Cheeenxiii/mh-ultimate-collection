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
| word 35 (0x8C) | offset | joint and sever records: 24-byte records (table "Joint and sever record") until a joint of −1; set in 56 of the 110 files. A record of kind 0, 3 or 5 is a sever/detach record for cut type 1, 2 or 3 (MH4U's cut-object code 0xc2d314; kinds 0 and 5 occur, 95 records), and of kind 1 or 4 is one of MHXX's `dtbparts` joint records (`a` 255, `b` 0; 130 records including the one of kind 255). A (255, kind, 0, −1) marker in 34 files (35 records) separates the two groups. No `dtbase` or `dtbparts` block holds a sever record: MHXX keeps the joint in the monster class's code ([dtbparts](dtbparts.md#sever-and-detach-records-not-in-these-files)) | verified | MHGU-DE notes/data.md; ours, loader 0x1618a4 and 0xc2d314; checks E11, E12 |
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

### Joint and sever record (24 bytes)

Word 35's records. MH4U reads them three ways:

- **At load.** The `rEnemyData` loader (0x1618a4; the word-35 walk is 0x163824–0x163a5c) walks the list to the joint −1 terminator and, for every record whose `b` isn't 0, adds the loaded file's base address to `b` and then to each of the six u32 at the block `b` points at. `joint` and `b` are the only fields it reads.
- **Through a getter.** 0x94c558 returns word 35's relocated pointer, read at `[header + 0x84]` of the loaded `.emd` (header = data + 8, at `getEnemyData` 0x68882c).
- **By its consumers.** Five functions call that getter: 0xc2d314 (the cut-object sever spawner, which reads `kind`, `index` and `joint`), 0x934280, 0x93be24, 0x919144 and 0x910480 (which read kind-1 records only).

The kind is a byte (the u32's low byte). 0xc2d314 maps the cut object's type byte (this+0xe2e) to a pair of detached bit and kind: type 1 → 1/0, type 2 → 2/3, type 3 → 8/5, and then takes the first record whose kind matches and whose `index` is 1. The records' kinds are 1 (109), 4 (20), 0 (128: 94 severs and 34 markers), 5 (2: 1 sever and em089's marker) and 255 (1); no file holds kind 3.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | s32 | joint: the bone the record names; −1 ends the list. A 255 joint with `limit` −1 is a marker that precedes a sever group (35 records: 34 of kind 0, 1 of kind 5, the second one in em089); no reader tests it | verified | ours, loader (terminator check), 0xc2d314; check E11 |
| +0x04 | u8 | kind: 0, 3 or 5 a sever/detach record for cut type 1, 2 or 3 (0 and 5 in the files); 1 or 4 one of MHXX's `dtbparts` joint records; 255 once. The three bytes after it are 0 | verified | ours, 0xc2d314 (type → kind, reads the byte); MHGU-DE `dala_break.c` for kinds 1 and 4; checks E11, E12 |
| +0x08 | u32 | index: of a sever group, the record whose index is 1 is the one 0xc2d314 acts on (the other records are skipped: 49 with 2, 2 with 0). On a kind-1 record 0x919144 uses it as an index below 6 | verified | ours, 0xc2d314, 0x919144; check E12 |
| +0x0C | u32 | limit: on a kind-1 record 0x934280 adds it into a 16-bit value; no reader reads it on a sever record (kind 0/3/5), where it is the joint on 81 of 95, the joint −1 on 5 and the joint −2 on 9 | unknown | ours, 0x934280; check E12 |
| +0x10 | u32 | a: 0 in all 95 sever records, 255 in all 130 others; no reader reads it | unknown | ours, loader and the five word-35 consumers; check E12 |
| +0x14 | u32 | b: an offset into the `.emd`, 0 on 37 sever records and inside the file on 58. The loader relocates it and the six u32 at the block it points at; all 58 blocks are inside the file and have exactly three nonzero words. No consumer of the list reads `b`, so what the block drives is unknown | verified | ours, loader 0x163824–0x163a5c; check E12 |

## .etd header

40 words; the blocks start at 0xA0. Words 5 to 34 are each 0 or an offset into the file (in all 107 `.etd` the European game has, by MHGU-DE's count; in all 110 of USA v1.3.0, check E1). Words 35 to 39 are scalars.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| word 4 (0x10) | u32 | base HP (Kushala Daora 4200, Gogmazios 17500; a quest scales it by its own table); 1..100,000 in all 110 | unverified | MHGU-DE notes/data.md |
| word 5 (0x14) | offset | part table: 8 × 10 bytes, one per part: u16 part HP, u8 break levels, u8 ×3, u16 second-level HP (0xFFFF none), u16 kind. MH3U rebuilds the same ten bytes from its part HP, second-level HP and break record, field by field ([emstatus.md](emstatus.md#part-record-mapping)); on Rathian every break-record byte and the second-level HP's "none" agree, and the kind has no 3U source. The kind is the part's Insect Glaive extract kind: 0 none, 1 red, 2 orange, 3 white, 4 green (below, "Part extract kind") | verified | ours, 0x936904; MHGU-DE `dt_convert.py`; specs/emstatus.md; checks E5, E13 |
| word 7 (0x1C) | offset | hitzone table: 80 bytes in all 110, **8 rows of 10 bytes** (table "Hitzone row"); the body record's +0x06 picks a row (`dttune` +0x70 in MHGU). Find it by this word rather than at a fixed offset | verified | MHGU-DE `dt_convert.py`, porting-guide.md; check E1 |
| word 8 (0x20) | offset | an 80-byte table beside it (`dttune` +0x74) | unknown | MHGU-DE `dt_convert.py` |
| word 9 (0x24) | offset | sensor (eye) records, 28 bytes each, ending at an s32 0xFFFF: joint, range, near radius, angles | unverified | MHGU-DE `dt_convert.py` |
| words 10, 11 | offset | ranges, every row with its count | unknown | MHGU-DE `dt_convert.py` |
| word 13 | offset | a block whose first bytes MHGU's loader reads as a loop count | unknown | MHGU-DE `dt_convert.py` |
| word 16 | offset | stamina | unverified | MHGU-DE `dt_convert.py` |
| words 17..21, 23, 24, 26 | offset | ailment buildups (12 or 16 bytes each where present) | unverified | MHGU-DE `dt_convert.py` |
| word 25 | offset | a block of at least 14 bytes | unknown | MHGU-DE `dt_convert.py` |
| word 27 (0x6C) | offset | attack volumes ("hitsize"): one offset per group up to word 28; a group is 40-byte records (capsules: off2 at +28) closed by a record whose first u16 is 0xFFFF; 2,184 groups, 5,463 volumes, every group ends | verified | MHGU-DE `emdata4u.hitsize`; check E1 |
| word 28 (0x70) | offset | attack records, 40 bytes each (table "Attack record"): an all-zero record (index 0), the attacks, then one whose first u16 is 0xFFFF and whose other 38 bytes are 0, ending the list. Word 29, when set (81 of the 110), is one record past that terminator; when it is 0 (29) the terminator still ends the list and the data after it belongs to no header word. E1 counts the stride to word 29 or the next referenced offset; E10 counts the records to the terminator | verified | ours, 0xb700a8 and 0xb6d09c; MHGU-DE `emdata4u.attackdata`; checks E1, E10 |
| word 29 (0x74) | offset | a 24-byte part table (`dttune` +0xC8) | unverified | MHGU-DE `dt_convert.py` |
| word 30 | offset | a block read with the ailments (`dttune` +0xCC) | unknown | MHGU-DE `dt_convert.py` |
| 0x8C, 0x90, 0x94, 0x9C | u32 or f32 | scalars (`dttune` +0xE0, +0xE4, +0xE8, +0xF0) | unverified | MHGU-DE `dt_convert.py` |

### Part extract kind (word 5, +8 of each record)

MH4U reads the kind at +8 of a part record as the part's **Insect Glaive extract kind**. Its own 0x936904 `(monster, part)` returns the byte at `part_table + 10·part + 8` (the part table is `[0x938604(monster)+4]`; the break record that 0x936a28 returns is the same table's `+2 + 10·part`, an MH3U-style 6-byte record, [emstatus.md](emstatus.md#part-record-mapping)). Its three call sites are in the Insect Glaive's kinsect code: 0x33dfbc and 0x33e05c in the kinsect's target update 0x33dd80, which treats 0 as "this part yields no extract" and indexes the kind's table 0x0109f098, and 0xbea7ec, which hands the value to the extract state 0xb379ac (0 returns there, and 4 is handled apart from the other values). The reader takes the low byte; the high byte is 0 in every record (check E13).

The value names the extract the kinsect harvests from that part: 1 red, 2 orange, 3 white, 4 green, 0 none. MH4U's and MHXX's Rathian and Rathalos put the same values on the same part regions, and those regions' extracts in the public charts are these: Rathian's head, neck and tail red, torso orange, legs white, wings green; Rathalos's head, neck and legs red, wings white, torso and tail orange. The extract's colours and effects are in MH4U's manual: red, white and orange are buffs, green heals ([page 91](http://game.capcom.com/manual/MH4U/en/page-91.html)). Check E13 counts the values and records the comparison.

### Attack record (40 bytes)

MH4U's own setup reads the table at word 28 in two functions. 0xb6d09c takes the monster, the attack state, word 28 as the record base, an index, the word-27 group table and a flags word; it makes the record `base + index × 40`, reads the group index at +0x19, resolves it in the word-27 table and calls 0xb700a8 with the resolved pointer. 0xb700a8 copies the record into the attack state and converts as the table says. The list starts with an all-zero record (index 0) and ends with the 0xFFFF terminator; neither is an attack.

**What the source games carry.** MH3U's `em_hitdata00` (specs/hitdata.md, HTD) has the same values in MH4U's bytes 0x00-0x11, and its group (+0x15), count (+0x16) and signed byte (+0x18) correspond to MH4U's +0x19, +0x1a and +0x1d; check E8 counts them. MHXX's `attackdata` (HDE) has MH4U's bytes 0x00-0x1B, with byte 0x12 split into its +0x12 (bits 0-1) and +0x1F (bits 2-7), and byte 0x1D; check E5 counts them. So MHXX carries nothing of MH4U's +0x1C and +0x1E..+0x27 (its +0x1C and +0x1E are its own fields), and MH3U carries nothing of MH4U's +0x12..+0x18, +0x1b..+0x1c and +0x1e..+0x27. A field is `verified` when MH4U's reader places it and a source game carries its value, `unverified` when only MH4U's reader places it, and `unknown` when no reader reads it.

The eight bytes at +0x10 are moved together by one f32 load/store pair (`vldmia`/`vstmia` to the attack state's +0x40): the compiler copies them as two 32-bit words, not as two float fields. In all 4,806 records they are a u16 and two bytes, then a byte and three zero bytes (E10), so the table splits them.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | s16 | time A: the attack's start; converted to a float at the attack state's +0x54 | verified | ours, 0xb700a8; MH3U 0x844a40 (the name); checks E5, E8 |
| +0x02 | s16 | time B: the window's length; converted to a float at the state's +0x58 | verified | ours, 0xb700a8; MH3U 0x844a40 (the name); checks E5, E8 |
| +0x04 | u16 | to the state's +0x38; MH3U reads a signed 16 here and converts it to a float at its state's +0x44 | verified | ours, 0xb700a8; checks E5, E8 |
| +0x06 | u8 | attack kind (MH3U's name), to the state's +0x3a | verified | ours, 0xb700a8; MH3U 0x987d50 (the name); checks E5, E8 |
| +0x08 | u16 | flags (MH3U's name), to the state's +0x36 | verified | ours, 0xb700a8; MH3U 0x987d50 (the name); checks E5, E8 |
| +0x0a | u8 | to the state's +0x3b | verified | ours, 0xb700a8; checks E5, E8 |
| +0x0b | u8 | to the state's +0x64 | verified | ours, 0xb700a8; checks E5, E8 |
| +0x0c | u32 | to the state's +0x3c; MH3U's +0x0c is a u16 and its high u16 is 0 | verified | ours, 0xb700a8; checks E5, E8 |
| +0x10 | u16 | the first two bytes of the four copied to the state's +0x40; 0, 1, 2, 4, 0x0400, 0x0800 or 0x8000 in every record | verified | ours, 0xb700a8; MHXX carries bytes 0x10-0x11 (E5); check E10 |
| +0x12 | u8 | the first four-byte group's third byte; MHXX splits it: bits 0-1 at its +0x12 and bits 2-7 at its +0x1F (MHGU-DE calls the high six the knockback bits; not checked in game) | verified | MHGU-DE `emdata4u.attackdata`; ours, 0xb700a8; checks E5, E10 |
| +0x13 | u8 | the first four-byte group's high byte: 0, 0x08 or 0x40 in every record | verified | ours, 0xb700a8; MHXX carries it (E5); check E10 |
| +0x14 | u8 | the low byte of the four copied to the state's +0x44: 0, 2 or 4 in every record | verified | ours, 0xb700a8; MHXX carries it (E5); check E10 |
| +0x15..+0x17 | u8 ×3 | the upper three bytes of the second four; 0 in every record; no reader reads them | unknown | ours, 0xb700a8 (copied); check E10 |
| +0x18 | u8 | to the state's +0x48, widened to a u16 | verified | ours, 0xb700a8; MHXX carries it (E5) |
| +0x19 | u8 | attack-volume group: an index into word 27's group table; the caller hands its pointer to the state at +0x80 | verified | ours, 0xb6d09c; MH3U +0x15 (E8); check E10 |
| +0x1a | u16 | to the state's +0x4a; MH3U's +0x16 plus one | verified | ours, 0xb700a8; checks E5, E8 |
| +0x1c | u8 | to the state's +0x4d; 0 in 4,668 of 4,806 records; MHXX uses this byte (28) as its own kind, so it carries nothing of MH4U's | unverified | ours, 0xb700a8; MHGU-DE `emdata4u.attackdata`; check E10 |
| +0x1d | s8 | to the state's +0x4e, clamped at 0; MH3U's +0x18 | verified | ours, 0xb700a8; checks E5, E8 |
| +0x1e | u8 | 0xff means the default, else a float at the state's +0x5c; 0 in every record | unverified | ours, 0xb700a8; check E10 |
| +0x1f | u8 | 0xff means the default, else a float at the state's +0x60; 0 in all but 2 of 4,806 records (10 there) | unverified | ours, 0xb700a8; check E10 |
| +0x20 | u8 | to the state's +0x65, with 1 stored as 0; 0, 1, 5 or 6 in every record | unverified | ours, 0xb700a8; check E10 |
| +0x21 | u8 | to the state's +0x4f; 0 in every record | unverified | ours, 0xb700a8; check E10 |
| +0x22 | u8 | to the state's +0x50; 0 in 4,776 of 4,806 records (60 in the other 30) | unverified | ours, 0xb700a8; check E10 |
| +0x23 | u8 | to the state's +0x51; 0 in every record | unverified | ours, 0xb700a8; check E10 |
| +0x24..+0x27 | 4 bytes | 0 in every record; no reader reads them | unknown | ours, 0xb700a8 (the record is 40 bytes); check E10 |

Byte 18 (the spec's earlier name for +0x12) is not a separate field: it is the third byte of the u32 at +0x10, and MHXX is the only source game that keeps it as a byte of its own.

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
- **The source games split the same data over several files.** MHXX's `dttune` holds the `.etd`'s HP, part table, hitzones, ranges, rage and ailments in a stream (specs/dttune.md); its `dtbase` holds the `.emd` blocks named above and its `dtbparts` the break and joint records (specs/dtbase.md, specs/dtbparts.md); the break records and joint records are not byte-equal to MH4U's, and MH4U's sever records have no counterpart in either file: MHXX's class code passes the joint to the engine and ships the cut part as a `_tail.mod` (specs/dtbparts.md). MH3U's `em_status00` holds HP, part HP and hitzones in an aligned walk, and its part HP, second-level HP and per-part break records (specs/emstatus.md); both keep hurt volumes, attack volumes and attack records in files of their own (specs/hitdata.md). MH3U has no `.emd`: its part model-group changes are code, and a severed part is a separate `emNNN_tail.mod` the class swaps in. `mhuc monsterdata` rebuilds MH4U's values from them and compares.
- **Bone ids are the model's.** MHGU-DE keeps 4U's bone ids and remap table when converting models, so the data needs no remap, except where a bone is missing from the target skeleton.

## Checks

- **E1 (done, MH4U USA v1.3.0 RomFS):** `mhuc survey` (or `mhuc emd check <data/em_data.arc>`). Results, all 110 pairs: both magics; every `.emd` word listed and every `.etd` word 5 to 34 is 0 or inside its file; every body-record list (2,917 body, 1,604 camera records) ends at a 0xFFFF bone, with shapes 0, 1, 2 only and parts below 8; every visibility list (1,568 rows) ends at −1, modes 0 and 1 only; base HP 1..100,000; 2,184 attack-volume groups, all ending; the attack-record stride is whole from word 28 to word 29 in 86 files and stops on 4 to 16 extra bytes in the other 24 (E10 bounds the records themselves). The hitzone table is 80 bytes in every `.etd` and the body records' rows stay below 8: the first run's histogram of "table bytes / rows used" (10, 16, 20, 40, 80, and 31 not whole) only meant that most monsters leave rows unused; 10 bytes is the only row size that fits all 110. Comparing em001's rows with Kiranico's Rathian damage chart then fixed the columns (table "Hitzone row") and showed em001 is Rathian. Still open: the `.etd` sensors and ailments, and the `.emd` scalars, which no count reaches.

- **E10 (done, MH4U USA v1.3.0 RomFS):** `mhuc emd check data/em_data.arc` bounds every `.etd`'s attack records at their 0xFFFF terminator and counts them. Results: 110 lists, 4,806 records before the terminator; the all-zero record 0 in 110 lists and the terminator in 110; +0x15..+0x17, +0x1e, +0x21, +0x23 and +0x24..+0x27 are zero in all 4,806; +0x13 is 0, 0x08 or 0x40, +0x14 is 0, 2 or 4, +0x1f is 0 or 10, and +0x20 is 0, 1, 5 or 6 in every record; the +0x19 group is below the word-27 group count in 4,793 of 4,806 (the 13 outside are em026's records 56 to 68, indices 25 to 30 against its 25 groups). E1's stride count is 5,204: for the 29 files whose word 29 is 0 it walks from word 28 to the next referenced offset, which includes the data after the terminator.
- **E11 (done, MH4U USA v1.3.0 `data/em_data.arc`):** `mhuc emd check <data/em_data.arc>` counts word 35's records
  (the same walk the survey runs). Result, all 110 pairs: word 35 is set in 56 files and 0 in 54; its records are of
  kind 1 (109), 4 (20), 0 (128, the 34 markers included), 5 (2, the em089 marker included) and 255 (1), and none of
  kind 3. The sever/detach records (kind 0, 3 or 5 and a joint that isn't 255 or −1) are 95 over 43 files: 94 of
  kind 0, whose joints are 141 (6), 142 (11), 143 (34), 144 (25), 145 (16) and 157 (2), and 1 of kind 5 (em089,
  joint 200). The (255, kind, 0, −1) marker is in 34 files (35 records: 34 of kind 0, 1 of kind 5); every list ends
  at a −1 joint. MHXX's side of the check is in [dtbparts](dtbparts.md#checks).
- **E12 (done, MH4U USA v1.3.0 `data/em_data.arc`):** `mhuc emd check <data/em_data.arc>` counts the word-35
  records' fields (the same walk). Result, the 95 sever records: `index` is 1 on 44, 2 on 49 and 0 on 2; `limit` is
  the joint on 81, the joint −1 on 5 and the joint −2 on 9; `a` is 0 on all 95; `b` is 0 on 37 and inside the file
  on 58, and each of those 58 blocks is inside the file and has exactly three nonzero words. The 130 other records
  all have `a` 255 and `b` 0. The code that reads them is the loader and the five getter callers named under
  "Joint and sever record"; the loader's `b` relocation is what E12's block counts follow.
- **E13 (done, MH4U USA v1.3.0 `data/em_data.arc`):** `mhuc emd check <data/em_data.arc>` counts the kind at +8 of word 5's eight 10-byte part records. Result, all 110 pairs: 880 records; kind 0 on 236, 1 on 189, 2 on 141, 3 on 256 and 4 on 58; no record above 4 and no high byte set; em081 is the only file whose eight kinds are all 0. The reader is 0x936904 `(monster, part)`, above. The extract names are checked part by part against two public charts: mh4info's [MHXX Rathian](https://x.mh4info.com/m/d/3) (head, neck and tail red; torso orange; legs white; wings green) and the [MH4 Insect Glaive wiki's list](https://w.atwiki.jp/mushimh4/pages/36.html) (Rathalos: head, neck and legs red; wings white; torso and tail orange). `tests/test_with_game_files.py::test_mh4u_part_kinds_count_what_the_insect_glaive_reader_returns` checks the counts and `tests/test_formats.py` the +8 placement.
