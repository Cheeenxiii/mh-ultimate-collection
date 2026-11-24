---
class: rEnemyStatus
extension: em_status00 (in each monster's arc/enemy/emNNN.arc: enemy\emNNN\em_status00)
games: MH3U (USA)
status: unknown
---

# rEnemyStatus: an MH3U monster's HP, parts, hitzones and tuning

MH3U's counterpart of MH4U's `.etd` (specs/emd.md) and MHXX's `dttune` (specs/dttune.md). One per monster (91 files in MH3U USA, class id 0x4DEE8265, an `rAppResource` of 0x150 bytes in MH3U's registry).

**Layout.** The game loads the whole file, checks the magic and the version, and walks it with a cursor (`rEnemyStatus` vtable slot 11, 0x0029c578, then 0x0029c744). Each step stores the cursor at an object field, advances it by the block's size and rounds it up to 16 bytes (0x00298918). An optional block is announced by a signed **presence byte, non-zero = present** (0x00298970), which takes a 16-byte slot of its own whether or not the block follows. A few blocks are sized by a count read inline. Check E3 runs our reader (`mhuc.formats.emstatus`) on every file and `reference/loader_trace.py` runs the walk itself on every file: the walk below ends exactly at the file's end in all 91, and its blocks are the game's.

**Meaning.** Each block is named after the MH4U `.etd` block it equals or lines up with, checked by rebuilding MH4U Rathian's values from MH3U's files (`mhuc monsterdata`, check E5): MH3U em001 is Rathian, as in MH4U. Rathian is the only pair checked, so a meaning backed by her alone stays unverified unless the values are equal.

## Walk

In walk order; every block starts on a 16-byte boundary. "Flag" marks a block behind a presence byte. "Object" is the field the game stores the block's address in.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `EMS\0` | verified | ours, loader 0x0029c578; check E3 |
| 0x04 | u32 | version 0x20110824 (the loader rejects any other) | verified | ours, loader; check E3 |
| 0x08 | u8 ×8 | not read by the walk | verified | ours, walk 0x0029c744 |
| 0x10 | 0x24 bytes | header (object +0xD0); its u32 at +0 is the base HP: MH4U `.etd` word 4, equal on Rathian | verified | ours, walk; checks E3, E5 |
| 0x40, 0x60 | 0x18 bytes each | two blocks (+0xF8, +0xFC) | unknown | ours, walk |
| flag | 8 × u16 | part HP (+0x68): 5 of Rathian's 8 equal MH4U's part HP by index; MH4U's part table also has break levels, which this block lacks | unverified | ours, walk; check E5 |
| flag | 0x10 bytes | a block (+0x6C) | unknown | ours, walk |
| flag | 3 bytes | a block (+0x70) | unknown | ours, walk |
| flag | 0x30 bytes | a block (+0x74) | unknown | ours, walk |
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

## What this means for the mod

- **A 3U monster's base HP and hitzones come from its `em_status00`**, in MH4U's hitzone layout. MH4U retuned some of the monsters it inherited from 3U; a 3U monster that MH4U lacks keeps 3U's values (fidelity rule).
- **MH3U's part block has HP only.** Break levels, the second part table and most tuning blocks have no 3U counterpart found yet; MH3U's ailment blocks have MH4U's shapes but fewer of them.
- MH3U's hurt volumes, attack volumes and attack records are in specs/hitdata.md. They are on MH3U's own skeleton: none of Rathian's hurt volumes equals MH4U's.

## Checks

- **E3 (done, MH3U USA RomFS):** `mhuc survey` counts `E3 em_status walk ends at the file's end`. Result: the walk ends exactly at the end of all 91 files.
- **Loader trace (done, MH3U USA code, same RomFS):** `python3 reference/loader_trace.py mh3u --exheader … --code … --romfs …` runs the game's walk in Unicorn on each file and logs every cursor step. Result: our reader's blocks are the game's steps, in order, in all 91.
- **E5 (done, Rathian):** `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mh3u arc/enemy/em001.arc` prints, per field, whether MH3U's value equals MH4U's. Results are in the table above, as counts.
