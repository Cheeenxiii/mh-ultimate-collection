---
class: rLayout
extension: lyt
games: MH4U (all five languages of the USA RomFS checked); MH3U and MHXX not checked
status: unverified
---

# LYT: MH4U's layouts

MH4U's HUD and menu screens are MT Framework layouts: `rLayout` resources, extension `.lyt`. A layout is a header, a table of texture paths, a chain of node records in depth-first order and a table of root pointers. The game creates one runtime object per type-2 root, then builds the panes' transforms and sprites from the nodes' records.

These are the files a HUD port has to read or write. MH3U's cockpit (including the oxygen gauge) is an XFS `rTexLayout`; MH4U has no XFS layout at all ([xfs.md](xfs.md), check X1), so its own HUD is this format. Reader: `mhuc lyt dump FILE` (`src/mhuc/formats/lyt.py`).

**Sources.** Our reading of MH4U USA v1.3.0's code: the loader `0x00aed0a0` (magic, version, the three offsets, the texture list and the node chain), `sMhLayout::registerLayout` `0x00c0f424` (the root count and how roots become runtime objects) and the node converter `0x00b039dc` (record sizes and the per-type fields). The file checks are in [Checks](#checks). The per-type field names beyond position come from the converter and are marked unverified; the names in the fork's [second-screen research](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/research/second-screen.md) agree with it.

## Where the layouts are, and how the game picks one

Every language folder has ten `core_*.arc` archives under `<lang>\data\` that hold the UI: `core_arena` (2 layouts), `core_common` (33), `core_dlc` (4), `core_end` (1), `core_end2` (45), `core_event` (1), `core_lobby` (46), `core_quest` (20), `core_result` (2) and `core_title` (11). That is 165 entries per language; the same 162 paths repeat in each language, because `lobby\ui441` is stored in three archives. Check LY1 counts them.

The file stores no path. The code names a layout by path in its loader, e.g. `lyt\quest\ui202`, and a loader holds a table of those path pointers with a byte beside each saying which screen the layout belongs on (0 top, 1 bottom). It loads each path from the archive, then calls `sMhLayout::registerLayout` (`0x00c0f424`) with the root count at header +0x08. That function creates one runtime object per type-2 root, hides them, and writes the screen's view number into each object's flags. The quest HUD loader (`0x00c1012c`) takes `lyt\quest\ui200` to `ui212` and `ui220` to `ui222` (top screen) and `ui601` to `ui604`, `ui610` and `ui250` (bottom); the health and stamina bars are `ui202`, and `ui204` is its gauge layout. All of them are in `core_quest.arc`.

The layouts' own root and pane names make the HUD readable: `ui202`'s roots are named for what they draw (`ui202_time`, `ui202_tairyoku`, `ui202_stamina`, `ui202_mushi` and so on). MH4U has no oxygen gauge to reuse; a port adds the gauge's nodes to a quest layout or draws it from a plugin ([underwater.md](../docs/underwater.md)).

## Header (0x30 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `lyt\0` | verified | loader `0x00aed150`; LY1 (all 825 files) |
| 0x04 | u32 | version: 0x70C | verified | loader `0x00aed168`; LY1 |
| 0x08 | u32 | number of roots (type-2 nodes) | verified | `registerLayout` `0x00c0f424` reads it as the root loop's count; LY1 (equals the chain's type-2 count on all 825) |
| 0x0C | u32 | number of texture slots | verified | loader's texture loop `0x00aed1e0`; LY1 |
| 0x10 | u32 | type-1 (group) + type-3 (text) node count | verified | LY1 (equals that sum on all 825) |
| 0x14 | u32 | type-0 (picture) node count | verified | LY1 |
| 0x18 | u32 | unknown: 0 in every file | unverified | LY1 (0 in all 825); no reader found |
| 0x1C | u32 | type-3 (text) node count | verified | LY1 |
| 0x20 | u32 | type-4 (boundary) node count | verified | LY1 |
| 0x24 | u32 | offset of the texture slots, from the file start | verified | loader rebases it `0x00aed1a0`; LY1 |
| 0x28 | u32 | offset of the first node record | verified | loader walks from it `0x00aed254`; LY1 |
| 0x2C | u32 | offset of the root-pointer table, 4 bytes per root; zero in the file and filled by the loader with the type-2 nodes' addresses | verified | loader rebases and fills it `0x00aed1cc`, `0x00aed2a4`; LY1 (the file ends at the table, all zero) |

## Texture slot (8 bytes each, from header +0x24)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | texture object pointer: 0 in the file, filled by the loader | verified | loader `0x00aed214`, `0x00aed234`; LY1 |
| +0x04 | u32 | offset of the texture's NUL-terminated ASCII path, 0 for an empty slot | verified | loader rebases it `0x00aed1fc`; LY1 (all 636 paths per language resolve, 13 slots are empty) |

## Node record: the common header (0x14 bytes)

The records are back to back in file order, then a u32 `0xFF` terminator, 0x10 zero bytes and the names. A root owns every record after it until the next type-2 record or the terminator; the depth word only says how deep in the transform stack the pane sits.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | type, from the table below | verified | loader's jump table `0x00aed280`; LY1 |
| +0x04 | u32 | depth: 0 for every type-2 root and for the first record; a record is at most one deeper than the one before it | verified | LY1 |
| +0x08 | u32 | name hash: `~crc32(name)`, 0 when the record has no name | verified | LY1 (27,774 named records and 1,871 unnamed per language) |
| +0x0C | u32 | offset of the NUL-terminated ASCII name, 0 when the record has no name | verified | loader rebases it `0x00aed264`; LY1 |
| +0x10 | u32 | size-like word: the record size for picture (0x6C), text (0x7C) and boundary (0x30); usually the record plus its picture and boundary descendants for groups and roots, but 0 for 715 groups and 0x28 for 325 roots per language. No reader found | unverified | ours; LY1 |

## Node types

| Value | Type | Record size | Status | Source |
|---|---|---|---|---|
| 0 | picture | 0x6C | verified | loader `0x00aed2c8`; LY1 (18,616 per language) |
| 1 | group | 0x38 | verified | loader `0x00aed2c0`; LY1 (4,825) |
| 2 | root | 0x28 | verified | loader `0x00aed2a4`; LY1 (1,246) |
| 3 | text | 0x7C | verified | loader `0x00aed2d0`; LY1 (4,256) |
| 4 | boundary | 0x30 | verified | loader `0x00aed2ec`; LY1 (702) |
| 5 | a sixth kind | 0x88 | unverified | loader `0x00aed2f4`; occurs in no MH4U layout, its converter (`0x00b045b0`) only partly read |

### Picture (type 0, 0x6C)

The converter `0x00b02fe0` copies these into a runtime sprite. The first two are the pane's position (f32, layout units = pixels); the rest are read but their names are inferred.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x14 | f32 | x position | unverified | converter `0x00b02fe0`; second-screen.md calls it position |
| +0x18 | f32 | y position | unverified | as above |
| +0x1C | f32 | z | unverified | converter |
| +0x20 | f32 | width | unverified | converter; values run 4 to 700 |
| +0x24 | f32 | height | unverified | converter; values run 1 to 700 |
| +0x28 | f32 | scale x | unverified | converter |
| +0x2C | f32 | scale y | unverified | converter |
| +0x30 | f32 | rotation | unverified | converter |
| +0x34 | f32 | u0 | unverified | converter |
| +0x38 | f32 | v0 | unverified | converter |
| +0x3C | f32 | u1 or v1 | unverified | converter; values are 0 to 1, as a texture coordinate |
| +0x40 | 4 × u32 | four RGBA8 colours | unverified | converter reads `+0x50`/`+0x54` into the runtime colour block; these four words are not read by it |
| +0x50 | f32 | ? | unverified | converter |
| +0x54 | f32 | ? (1.0 in every record) | unverified | converter |
| +0x58 | u8 | flags: low 4 bits go into the runtime flags | unverified | converter |
| +0x59 | u8 | flags: bits 4 to 6 go into the runtime flags | unverified | converter |
| +0x5A | char[2] | zero | unverified | LY1 (0 in all 18,616 pictures per language) |
| +0x5C | 12 bytes | three words copied to the runtime sprite's first 12 bytes; 16 distinct values across all pictures | unverified | converter `0x00b03020`, `0x00ae8ce4` |
| +0x68 | u32 | 0 or 1 | unverified | LY1 |

### Group (type 1, 0x38)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x14 | f32 | x position | unverified | converter `0xb03a4c`; second-screen.md calls it position |
| +0x18 | f32 | y position | unverified | as above |
| +0x1C | 7 × u32 | seven words copied to the runtime transform | unverified | converter `0xb03a4c` |

### Root (type 2, 0x28)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x14 | f32 | x position | unverified | converter `0xb04a10`; second-screen.md calls it position |
| +0x18 | f32 | y position | unverified | as above |
| +0x1C | u32 | ? | unverified | converter |
| +0x20 | f32 | a float the converter scales into a byte | unverified | converter |
| +0x24 | u32 | flags: low byte, bit 8 (visible) and bit 9 | unverified | converter |

### Text (type 3, 0x7C)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x14 | u32 | offset of the NUL-terminated UTF-16LE string | verified | loader rebases it `0x00aed2d0`; LY1 (4,256 strings per language, all inside the file and terminated) |
| +0x18 | 2 × u32 | ? | unverified | converter `0xb03f40` |
| +0x20 | 22 × u32 | copied to the runtime text object | unverified | converter |
| +0x78 | u32 | five nibble/bit fields copied to the runtime flags | unverified | converter |

### Boundary (type 4, 0x30)

A touch area. The converter `0x00b03c00` copies x, y, w, h and the two words; the fork's second-screen research reads the rectangle as the hit area of a touch group.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x14 | f32 | x (top-left, layout units) | unverified | converter `0x00b03c00`; second-screen.md |
| +0x18 | f32 | y (top-left) | unverified | as above |
| +0x1C | f32 | width | unverified | as above; positive in all 702 records |
| +0x20 | f32 | height | unverified | as above; positive in all 702 records |
| +0x24 | 2 × u32 | two scale words | unverified | converter |
| +0x2C | u8 | flag byte | unverified | converter |

## Checks

- **LY1 (done):** read every `rLayout` entry of MH4U USA v1.3.0's RomFS. Procedure: `MHUC_DUMPS=… python3 -m pytest -m game_files -k layout` reads the ten `core_*.arc` archives of every language and parses each entry; `mhuc survey <romfs.bin> --workers 1` (section `lyt`) counts the same over the whole image. Pass: every entry parses, every header count equals the chain, every name hash is `~crc32`, every text pointer and string resolves, every name sits in the tail region, the file ends at a zero root table, and the terminator is followed by 0x10 zero bytes.
  Result (the game-files test, 2026-11-25): 825 layouts, all read (165 in each of eng, fre, ger, ita and spa). Per language: 29,645 nodes (1,246 roots, 18,616 pictures, 4,825 groups, 4,256 text and 702 boundary records), 27,774 named and 1,871 unnamed records, 636 texture paths and 13 empty texture slots, and one root with no child. The 165 entries hold 162 distinct paths, because `lobby\ui441` is stored in three archives. The five languages have identical counts, because only the text strings differ.
  This check is what established the +0x10 word's exceptions and the field semantics marked unverified; it records numbers only.

## Open questions

- The node header's +0x10 word: no reader was found, and its value is not always the subtree size the fork's second-screen research reports (text records are excluded, 206 groups say 0, 51 roots say 0x28). It may be the editing tool's block size.
- The header's +0x18 word: 0 in every file; no reader found.
- The picture, group, root and boundary fields' meanings beyond position, and type 5's record: the renderer (`uLayout::draw` `0x00b04774`, the sprite upload `0x00ae65a4`) is the next place to read.
- Whether MH3U or MHXX ship `.lyt` layouts at all; only MH4U was checked.
