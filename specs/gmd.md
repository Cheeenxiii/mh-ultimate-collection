---
class: rGUIMessage
extension: gmd
games: MH4U, MHX, MHXX (3DS); MHGU (Switch) for English text
status: unverified
---

# GMD: text table

Labelled UTF-8 strings. `mhuc.gmd` reads versions 1 and 2 and writes them; [gmd.ksy](gmd.ksy) describes version 1. The Switch's MHGU v1.4.0 supplies English text only (README's source table); its GMDs are version 2 in the PC/Switch layout, which mhuc doesn't read yet.

## Header (0x28 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `GMD\0` (`\0DMG` big endian) | unverified | Kuriimu2 GmdSupport |
| 0x04 | u32 | version: 0x00010201 v1, 0x00010302 v2 | unverified | Kuriimu2 GmdSupport |
| 0x08 | u32 | language: 0 Japanese, 1 English, 2 French, 3 Spanish, 4 German, 5 Italian | unverified | Kuriimu2 GmdSupport |
| 0x0C | u64 | unknown | unverified | Kuriimu2 GmdHeader |
| 0x14 | u32 | label count | unverified | Kuriimu2 GmdHeader |
| 0x18 | u32 | section (string) count | unverified | Kuriimu2 GmdHeader |
| 0x1C | u32 | label bytes | unverified | Kuriimu2 GmdHeader |
| 0x20 | u32 | section bytes | unverified | Kuriimu2 GmdHeader |
| 0x24 | u32 | name length (without its NUL) | unverified | Kuriimu2 GmdHeader |
| 0x28 | char[n+1] | table name, NUL-terminated | unverified | Kuriimu2 Gmdv1 |

## Label entries

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| v1 +0x00 | s32 | section index | unverified | Kuriimu2 Gmdv1LabelEntry |
| v1 +0x04 | u32 | label offset; offsets count from the first entry's value | unverified | Kuriimu2 Gmdv1.ReadLabels |
| v2 mobile +0x00 | s32 | section index | unverified | Kuriimu2 Gmdv2MobileLabelEntry |
| v2 mobile +0x04 | u32, u32 | two hashes (functions unknown) | unverified | Kuriimu2 Gmdv2MobileLabelEntry |
| v2 mobile +0x0C | u32 | zero | unverified | Kuriimu2 Gmdv2MobileLabelEntry |
| v2 mobile +0x10 | u64 | label offset | unverified | Kuriimu2 Gmdv2MobileLabelEntry |
| v2 mobile +0x18 | u64 | list link | unverified | Kuriimu2 Gmdv2MobileLabelEntry |
| after v2 entries | u8[0x800] | hash buckets, when there are labels | unverified | Kuriimu2 Gmdv2.ReadMobile |

Then the labels, NUL-terminated, then the strings, NUL-terminated, in section order. A table can have fewer labels than strings.

## Open questions

- Which version each game uses. MH3U's GMDs seem to have yet another header (Silvris's GMDPy reads one with a group name).
- The v2 hash functions, needed before mhuc can write a v2 table the game accepts.
- Kuriimu2 detects an XOR obfuscation of the strings in some MT titles. None is assumed on 3DS; check G1 tells.
- The game's control codes inside strings (colours, icons, line breaks).

## Checks

- **G1 (with game files):** `mhuc gmd dump` on every GMD in MH4U's and MHXX's RomFS; record the versions seen and any table whose strings don't decode as UTF-8.
- **G2 (with game files):** `gmd.write(gmd.read(data)) == data` for v1 tables.
