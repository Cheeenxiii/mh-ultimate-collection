---
class: rGUIMessage
extension: gmd
games: MH4U, MHX, MHXX (3DS); MHGU (Switch) for English text
status: unverified
---

# GMD: text table

Labelled UTF-8 strings. `mhuc.gmd` reads and writes every layout below; [gmd.ksy](gmd.ksy) describes the 0x28-byte header with v1 entries. MH4U has no GMD tables at all (check G1): its text lives in other resource types (`rLayoutMessage` and others, to describe). The tables that matter are MH3U's (v1, short header) and MHXX's (v2). The Switch's MHGU v1.4.0 supplies English text only (README's source table); its GMDs are version 2 in the PC/Switch layout, which mhuc doesn't read yet.

## Header (0x28 bytes; MHXX)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `GMD\0` | verified | Kuriimu2 GmdSupport; check G1 |
| 0x04 | u32 | version: 0x00010302 (v2) in MHXX; 0x00010201 (v1) in MH3U, with the short header below | verified | Kuriimu2 GmdSupport; check G1 |
| 0x08 | u32 | language: 0 Japanese, 1 English, 2 French, 3 Spanish, 4 German, 5 Italian | verified | Kuriimu2 GmdSupport; check G1 |
| 0x0C | u64 | unknown | verified | Kuriimu2 GmdHeader; check G1 (present in every MHXX table) |
| 0x14 | u32 | label count | verified | Kuriimu2 GmdHeader; check G1 |
| 0x18 | u32 | section (string) count | verified | Kuriimu2 GmdHeader; check G1 |
| 0x1C | u32 | label bytes | verified | Kuriimu2 GmdHeader; check G1 |
| 0x20 | u32 | section bytes | verified | Kuriimu2 GmdHeader; check G1 |
| 0x24 | u32 | name length (without its NUL) | verified | Kuriimu2 GmdHeader; check G1 |
| 0x28 | char[n+1] | table name, NUL-terminated | verified | Kuriimu2 Gmdv1; check G1 |

## Header (0x20 bytes; MH3U, layout "v1-short")

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `GMD\0` | verified | ours; check G1 |
| 0x04 | u32 | version 0x00010201 | verified | ours; check G1 |
| 0x08 | u32 | language (MH3U USA ships 1 to 5, one table per language) | verified | ours; check G1 |
| 0x0C | u32 | label count | verified | ours; check G1 |
| 0x10 | u32 | section (string) count | verified | ours; check G1 |
| 0x14 | u32 | label bytes | verified | ours; check G1 |
| 0x18 | u32 | section bytes | verified | ours; check G1 |
| 0x1C | u32 | name length | verified | ours; check G1 |
| 0x20 | char[n+1] | table name, NUL-terminated | verified | ours; check G1 |

The same fields as the long header without the u64. Silvris's GMDPy reads an MH3U header with a group name, which may be the same thing seen differently.

## Label entries

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| v1 +0x00 | s32 | section index | verified | Kuriimu2 Gmdv1LabelEntry; check G1 (MH3U) |
| v1 +0x04 | u32 | label offset; offsets count from the first entry's value | verified | Kuriimu2 Gmdv1.ReadLabels; check G1 (MH3U) |
| v2 +0x00 | s32 | section index | verified | Kuriimu2 Gmdv2MobileLabelEntry; check G1 |
| v2 +0x04 | u32, u32 | two hashes: the inverted CRC-32 of the label repeated twice, then three times, as beeequeue/gmd writes them for MHGU; equal to `gmd.label_hashes` for all 27,138 MHXX labels | verified | Kuriimu2 Gmdv2MobileLabelEntry; beeequeue/gmd `encode.ts`; check G3 |
| v2 +0x0C | u32 | zero | verified | Kuriimu2 Gmdv2MobileLabelEntry; check G1 |
| v2 +0x10 | u64 | label offset | verified | Kuriimu2 Gmdv2MobileLabelEntry; check G1 |
| v2 +0x18 | u64 | list link | unverified | Kuriimu2 Gmdv2MobileLabelEntry |
| after v2 entries | u8[0x800] | hash buckets, when there are labels | verified | Kuriimu2 Gmdv2.ReadMobile; check G1 (the size) |
| v2-32 +0x00 | s32 | section index | verified | ours; check G1 |
| v2-32 +0x04 | u32, u32 | two hashes, as in v2 (G3 counts both layouts together) | verified | ours; check G3 |
| v2-32 +0x0C | u32 | label offset | verified | ours; check G1 |
| v2-32 +0x10 | u32 | list link | unverified | ours |
| after v2-32 entries | u8[0x400] | hash buckets, when there are labels | verified | ours; check G1 (the size) |

MHXX uses both v2 layouts: 0x20-byte entries in most tables, 0x14-byte entries (a 32-bit build of the same structure) in 146 tables of its Japanese release, quest text among them. They have the same version word and are told apart by the file size; `mhuc.gmd.layout_of` does that.

Then the labels, NUL-terminated, then the strings, NUL-terminated, in section order. A table can have fewer labels than strings.

## Open questions

- The v2 hash functions are confirmed (G3). The buckets' fill rule is still unknown (beeequeue/gmd copies them from the file it read), and is needed too before mhuc can write a v2 table with new labels that the game accepts. Tables read from the game keep their index byte for byte while their labels are unchanged, so changing strings alone is safe.
- The game's control codes inside strings (colours, icons, line breaks).
- Where MH4U keeps the text MH3U and MHXX keep in GMDs (`rLayoutMessage` and others).

## Checks

Run on 2026-11-23 with `mhuc survey` on the maintainer's dumps (see [arc](arc.md#checks)), counting every GMD inside ARCs and loose in the RomFS.

- **G1 (done): versions and decoding.**
  - MH4U: no GMD tables in the RomFS.
  - MH3U USA: 3,115 tables, all version 0x00010201 with the 0x20-byte header; every size adds up, every string is UTF-8, and each table comes in languages 1 to 5.
  - MHXX JPN: 3,251 tables, all version 0x00010302, all language 0; 3,105 in layout v2 and 146 in layout v2-32 (82 in archives, 64 loose). All decode as UTF-8. No obfuscation in any game.
  - The fan-translated MHXX keeps language 0 in its English tables, and a few of its rebuilt tables fit neither layout: the translation's tools, not the game.
- **G2 (done): round trip.** `gmd.write(gmd.read(data)) == data` for all 3,115 MH3U tables. All 3,251 MHXX tables too, both layouts, with their label index kept.
- **G3 (done, 2026-11-23):** `mhuc survey` on the MHXX JPN RomFS compares each v2 label entry's two stored hashes with `gmd.label_hashes` of its label. Result: 27,138 labels match, 0 differ, over all 3,251 tables (both layouts). The hash functions are verified for MHXX.
