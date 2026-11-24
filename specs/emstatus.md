---
class: rEnemyStatus
extension: em_status00 (in each monster's arc/enemy/emNNN.arc: enemy\emNNN\em_status00)
games: MH3U (USA)
status: unknown
---

# rEnemyStatus: an MH3U monster's HP, parts, hitzones and tuning

MH3U's counterpart of MH4U's `.etd` (specs/emd.md) and MHXX's `dttune` (specs/dttune.md). One per monster (91 files in MH3U USA, class id 0x4DEE8265, an `rAppResource` of 0x150 bytes in MH3U's registry).

**Layout.** The game loads the whole file, checks the magic and the version, and walks it with a cursor (`rEnemyStatus` vtable slot 11, 0x0029c578, then 0x0029c744). Each step stores the cursor at an object field, advances it by the block's size and rounds it up to 16 bytes (0x00298918). An optional block is announced by a signed **presence byte, non-zero = present** (0x00298970), which takes a 16-byte slot of its own whether or not the block follows. A few blocks are sized by a count read inline. Check E3 runs our reader (`mhuc.formats.emstatus`) on every file and `reference/loader_trace.py` runs the walk itself on every file: the walk below ends exactly at the file's end in all 91, and its blocks are the game's.

**Meaning.** Each block is named after the MH4U `.etd` block it equals or lines up with, checked by rebuilding MH4U Rathian's values from MH3U's files (`mhuc monsterdata`, check E5): MH3U em001 is Rathian, as in MH4U. Rathian is the only pair checked, so a meaning backed by her alone stays unverified unless the values are equal. The break blocks are named from the code that reads them (0x84c56c, 0x835ebc, 0x837a60, 0x8525a8, below); their fields' meanings stay unverified.

## Walk

In walk order; every block starts on a 16-byte boundary. "Flag" marks a block behind a presence byte. "Object" is the field the game stores the block's address in.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `EMS\0` | verified | ours, loader 0x0029c578; check E3 |
| 0x04 | u32 | version 0x20110824 (the loader rejects any other) | verified | ours, loader; check E3 |
| 0x08 | u8 ×8 | not read by the walk | verified | ours, walk 0x0029c744 |
| 0x10 | 0x24 bytes | header (object +0xD0); its u32 at +0 is the base HP: MH4U `.etd` word 4, equal on Rathian | verified | ours, walk; checks E3, E5 |
| 0x40, 0x60 | 0x18 bytes each | two blocks (+0xF8, +0xFC) | unknown | ours, walk |
| flag | 8 × u16 | part HP (+0x68): 5 of Rathian's 8 equal MH4U's part HP by index, and the block feeds MH4U's part record +0 (see [Part record mapping](#part-record-mapping)); MH4U's part table also has break levels, which 3U keeps in the break records below | verified | ours, walk; code 0x8525a8; check E5 |
| flag | 0x10 bytes | second part HP (+0x6C): 8 × s16, a second HP for each part; see [Break and sever records](#break-and-sever-records) and [Part record mapping](#part-record-mapping) | verified | ours, walk; code 0x8525a8; check E3 |
| flag | 3 bytes | break ids (+0x70): up to three ids, 0xFF for an unused one; 0x84c480 returns the position of a value among them | unverified | ours, walk; code 0x84c480; check E9 |
| flag | 0x30 bytes | break records (+0x74): 8 × 6 bytes, one per part; see [Break and sever records](#break-and-sever-records) | verified | ours, walk; code 0x84c56c; check E3 |
| always | 8 × 10 bytes | hitzone table (+0x78): MH4U `.etd` word 7, the same rows of 10 bytes (specs/emd.md); 6 of Rathian's 8 rows equal, and the other two differ in one column each (MH4U retuned them) | verified | ours, walk; checks E3, E5 |
| flag | 0x50 bytes | a second table of the hitzone table's size (+0x7C), as MH4U `.etd` word 8 and MHXX's | unverified | ours, walk |
| always | s32 n, then 24·n bytes | a counted table (+0x80); the count sits in its own 16-byte slot | verified | ours, walk 0x0029c9c0; check E3 |
| flag | 0x18 bytes | a block (+0x84) | unknown | ours, walk |
| always | 0x20 bytes | a block (+0x88); its first 16 bytes equal Rathian's first MH4U distance range row | unverified | ours, walk; check E5 |
| always | 0x10 bytes | distance range row (+0x100): MH4U `.etd` word 10, row 0, equal on Rathian | unverified | ours, walk; check E5 |
| flag | 0x1C bytes | a block (+0x104) | unknown | ours, walk |
| flag | 0x10, 0x1C, 0x1C bytes | a group of three blocks (+0x114, +0x118, +0x11C) | unknown | ours, walk |
| flag | 0x10, 0x1C, 8 bytes | a group of three blocks (+0x120, +0x124, +0x128) | unknown | ours, walk |
| flag | 0x10, 0x1C bytes | a group of two blocks (+0x12C, +0x130) | unknown | ours, walk |
| flag | 0x38 bytes | rage (+0x94): 45 of MH4U `.etd` word 14's 56 bytes appear in it, 11 bytes later | unverified | ours, walk; check E5 |
| flag | 0x34 bytes | a block (+0x98) | unknown | ours, walk |
| flag | 4 bytes | a block (+0x9C) | unknown | ours, walk |
| flag | s16, s16 k, 10·k bytes, s16 m, 4·m bytes | a block in three parts (+0x138, +0x13C, +0x140), each count in its own 16-byte slot | verified | ours, walk 0x0029ce10; check E3 |
| flag | 0x10 bytes | ailment buildup (+0xA4), MH4U `.etd` word 17's shape | unverified | ours, walk; check E5 |
| flag ×4 | 0x0C bytes each | four ailment buildups (+0xA8..+0xB4), the shape of MH4U `.etd` words 18 to 21; values differ from MH4U's on Rathian | unverified | ours, walk; check E5 |
| flag | 8 bytes | a buildup (+0xB8) equal to the first 8 bytes of MH4U `.etd` word 24 on Rathian | unverified | ours, walk; check E5 |
| flag | 0x38 bytes, then per part i < 8: 32·b[0x0E + i] bytes | a block (+0xBC) and, for each of 8 parts, the number of 32-byte records its byte at +0x0E + i gives | verified | ours, walk 0x0029d164; check E3 |
| flag (then 3 × flag, 6 bytes) | 6 bytes ×3 | three blocks (+0x144, +0x148, +0x14C); each takes its 6 bytes even when its own presence byte is 0 | verified | ours, walk 0x0029d1c0; check E3 |

"Verified" on a block of unknown meaning covers its place and size only.

## Break and sever records

MH4U keeps a part's break data in its `.etd` part table (word 5: part HP, break levels, second-level HP, kind, specs/emd.md) and its model-group changes in `.emd` words 33 to 35. MH3U has neither file: `em_status00` carries the numbers in three blocks and the class code does the model side.

| Block (walk name) | Bytes | What the game does with it |
|---|---|---|
| part table (+0x68) | 8 × u16 | a part's first-level HP; 0x8525a8 scales it into the monster's per-part record, and 0x84cb10 calls it for every part |
| block 0x6C | 8 × s16 | a second-level HP per part; 0x8525a8 scales it into the same per-part record, and the update 0x837a60 uses it as a part's active HP when the class says the part has a second level (vtable slot 0x120) |
| block 0x70 | 3 | up to three break ids; 0x84c480(monster, value) returns the position of `value` among them (0 to 2) or −1, and the update uses that position to pick an effect row for the part |
| block 0x74 | 8 × 6 | one break record per part; 0x84c56c(monster, part) returns it, or one shared default record (0xc727a8) when the block is absent |

**How the game breaks a part.** The update 0x837a60 runs the per-part state machine: when a part's HP runs out it sets the part's break bit, advances the part's counter, reloads the part's HP at the first or second level, and calls the break-event handler 0x84e1d4. The test 0x835ebc(monster, part, kind) then answers whether the part's next break of that kind is due: it returns true when the record's +0 field is above the part's own counter and its +2 field equals `kind`. The update also reads the record's +2 and +3 fields as break ids, matched against block 0x70, to pick the part's effect row.

### Break record (6 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 | break counter: the test 0x835ebc returns true while the part's counter is below it; 0 on the shared default | unverified | ours, 0x835ebc, 0x837a60; check E9 |
| +0x02 | u8 | break kind: 0x835ebc compares it with the damage call's kind, and 0x837a60 matches it against block 0x70 | unverified | ours, 0x835ebc, 0x837a60, 0x84c480 |
| +0x03 | u8 | a second break id matched against block 0x70 (0xFF when unused) | unverified | ours, 0x837a60, 0x84c480 |
| +0x04 | u16 | a value the part initializer 0x84cb10 scales and stores beside the part's HP; on Rathian's one break part it is higher than MH4U's second-level HP | unverified | ours, 0x84cb10; check E9 |

The block's place and size are the walk's (check E3); each field's meaning is our reading of that code and has not been checked in the game, so all four stay unverified. A file without block 0x74 (45 of 91) gives every part the shared default record at 0xc727a8: its counter, kind and second break id are 0 and its +4 field is 0xFFFF, so no part has a break of its own or a second-level HP.

### Second-level HP (8 × s16)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00, +0x02, … +0x0E | s16 ×8 | one second-level HP per part; the update uses it as a part's active HP when the class says the part has a second level (vtable slot 0x120), and the initializer 0x84cb10 scales it into the part's state record | unverified | ours, 0x8525a8, 0x837a60; check E9 |

### Part record mapping

MH4U keeps a part's HP and breaks in one 10-byte record in its `.etd` part table (specs/emd.md, word 5). MH3U keeps the same values in the three blocks above: the part HP table (+0x68), the second-level HP block (+0x6C) and the 6-byte break record (+0x74). `mhuc monsterdata --mh4u … --id em001 --mh3u …` rebuilds MH4U's eight records from them and prints, for each field, how many of the eight equal MH4U's own record (check E5).

| MH4U offset | Type | MH4U field | MH3U source | Status | Check |
|---|---|---|---|---|---|
| +0x00 | u16 | part HP | part HP table (+0x68), same part index | verified | E5: 5 of 8 equal on Rathian; MH4U retuned parts 0, 6 and 7 |
| +0x02 | u8 | break levels | break record +0x00, low byte | verified | E5: 8 of 8 equal |
| +0x03 | u8 | first of three bytes after the break levels | break record +0x00, high byte | verified | E5: 8 of 8 equal (0 on all eight parts of Rathian) |
| +0x04 | u8 | second of the three bytes | break record +0x02 (the break kind) | verified | E5: 8 of 8 equal |
| +0x05 | u8 | third of the three bytes | break record +0x03 (the second break id) | verified | E5: 8 of 8 equal |
| +0x06 | u16 | second-level HP (0xFFFF none), from the break record | break record +0x04, when block 0x6C has no positive value for the part | verified | E5: 7 of 8 equal on Rathian, all seven 0xFFFF on both sides; the eighth retuned |
| +0x06 | u16 | second-level HP, from block 0x6C | second-level HP block (+0x6C), when the part's value is above 0 | unverified | no MH4U pair identified for the four files with block 0x6C |
| +0x08 | u16 | kind | none | unverified | no MH3U field; E5: no source |

The record's first four bytes go into MH4U's bytes +2 to +5 as they are, and its last two bytes (+4) into MH4U's second-level HP. On Rathian the eight records' bytes +0 to +3 equal MH4U's bytes +2 to +5 on all eight parts, and the record's +4 equals MH4U's second-level HP on the seven parts that have none in both games; on the eighth, the tail, both games have a value and MH4U's is the lower of the two. That the 0xFFFF of the record's +4 is the same 0xFFFF as MH4U's +6, and that the field takes the same place in the record, is the evidence for the mapping; what the 3U field itself means stays unverified, and the initializer 0x84cb10 scales it into the part's state record.

**What the 3U fields mean is still our reading of the code.** The mapping above is the placement of the fields, checked against MH4U's file on Rathian; the 3U break record's four fields and the second-level HP block stay unverified in their own tables.

**Where 3U has no value for an MH4U field:**

- **MH4U's kind (+8)** has no 3U field at all. The converter writes 0 and the comparison prints `kind no 3U field`; the field stays unverified, and a port that needs it has to find where MH4U reads it, or author a value.
- **MH4U's second-level HP (+6)** is written as 0xFFFF (none) when neither block 0x6C nor the break record's +4 supplies a value; both games use 0xFFFF for "no second-level HP".
- **MH4U's part HP (+0)** is written as 0 when a file lacks the part HP block (the walk makes it optional).
- **Block 0x6C's place in MH4U** is unverified: it is 3U's own second-level HP and the converter prefers it over the record's +4 when it is above 0, but no MH4U monster has been identified for the four 3U files that have it, so that preference has no check behind it.

### Severing

MH3U has no sever record in the status file. A monster whose tail severs carries a second model in its own archive, `enemy/emNNN/mod/emNNN_tail.mod`, and its class swaps it in for the intact tail. `uEm002`, Rathian's and Rathalos's class, does it in vtable slot 45 (0x68c804): it builds `enemy\em001\mod\em001_tail` or `enemy\em002\mod\em002_tail` for its id and attaches the model. On Rathian that tail model's three bones are 143, 144 and 145 — the same bone ids MH4U's `.emd` word 35 sever records name for its own em001 — and its model group 8 is the group MH4U's visibility rows switch on a sever (condition 1). The break record at part 7 is the tail's.

What calls slot 45, and at which break level, is unverified: no function calls 0x68c804 directly and the part-break code (0x837a60, 0x84e1d4) reaches the class only through engine calls. The sever data a port needs is therefore the separate model plus the class handler, not a per-part threshold.

### Rathian: 3U against MH4U

`mhuc monsterdata --mh4u data/em_data.arc --id em001 --mh3u arc/enemy/em001.arc` (check E5) prints the part-record comparison field by field:

| Part-record field | MH3U source | Equal on Rathian |
|---|---|---|
| part HP (+0) | part HP table | 5 of 8 |
| break levels (+2) | break record +0, low byte | 8 of 8 |
| byte +3 | break record +0, high byte | 8 of 8 |
| byte +4 | break record +2 | 8 of 8 |
| byte +5 | break record +3 | 8 of 8 |
| second-level HP (+6) | break record +4 (block 0x6C absent) | 7 of 8 |
| kind (+8) | none | no 3U field |

| | MH3U | MH4U |
|---|---|---|
| parts | 8 | 8 |
| parts with a break record / break levels | 1: part 7 | 1: part 7 |
| second-level HP block | absent | present, part 7 only |

- Both games single out exactly part 7, and it is the tail in both (the sever data above). MH4U's only non-zero break-level byte and only second-level HP are part 7's, and 3U's only non-default break record is part 7's.
- The 3U record's first four bytes equal MH4U's part-record bytes +2 to +5 on all eight parts (the seven unused records are zero on both sides). The record's +4 equals MH4U's second-level HP on the seven parts that have none in both games; on part 7 both games have a value, MH4U's lower, so MH4U retuned it. 3U has no second-level HP block for Rathian, so the record's +4 is the only 3U field that can hold that value.
- MH4U's kind has no 3U field: the comparison prints `kind no 3U field`, and the field stays unverified.

## What this means for the mod

- **A 3U monster's base HP and hitzones come from its `em_status00`**, in MH4U's hitzone layout. MH4U retuned some of the monsters it inherited from 3U; a 3U monster that MH4U lacks keeps 3U's values (fidelity rule).
- **MH3U's break data is also in `em_status00`**: the part HP table, the second-level HP block and one 6-byte break record per part. A port takes all three; [Part record mapping](#part-record-mapping) says which 3U field feeds which MH4U field, checked against MH4U's own file on Rathian (check E5). MH4U's kind field has no 3U source, so a port has to find or author it. Severing is not a file record: it is the separate `emNNN_tail.mod` plus the class handler that swaps it in.
- MH3U's hurt volumes, attack volumes and attack records are in specs/hitdata.md. They are on MH3U's own skeleton: none of Rathian's hurt volumes equals MH4U's.

## Checks

- **E3 (done, MH3U USA RomFS):** `mhuc survey` counts `E3 em_status walk ends at the file's end`. Result: the walk ends exactly at the end of all 91 files.
- **Loader trace (done, MH3U USA code, same RomFS):** `python3 reference/loader_trace.py mh3u --exheader … --code … --romfs …` runs the game's walk in Unicorn on each file and logs every cursor step. Result: our reader's blocks are the game's steps, in order, in all 91.
- **E5 (done, Rathian):** `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mh3u arc/enemy/em001.arc` prints, per field, whether MH3U's value rebuilt into MH4U's layout equals MH4U's. The `part table` line gives one count per field: on Rathian, `part table: 5 of 8 part HP, 8 of 8 break levels, 8 of 8 +3, 8 of 8 +4, 8 of 8 +5, 7 of 8 second HP, kind no 3U field`. `second part HP` compares block 0x6C with MH4U's second-level HP: on Rathian, `absent in the source`. Results are in the tables above, as counts.
- **E9 (done, MH3U USA RomFS):** `mhuc survey <romfs.bin>` counts, per `em_status` file, the break blocks and their contents (`E9 …`). Result: 46 of the 91 files have block 0x74 as 8 × 6 bytes and block 0x70 with it; their records name 50 parts with a non-default record. 4 files have block 0x6C as 8 s16 and 20 of their parts have a non-zero second HP. The other 45 files have no block 0x74 and use the shared default record. Block sizes are the walk's, which E3 checks in all 91.
