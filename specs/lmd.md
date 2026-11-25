---
class: rLayoutMessage
extension: lmd
games: MH4U (all five languages of the USA RomFS checked); MH3U and MHXX not checked (they keep text in GMDs)
status: unverified
---

# LMD: MH4U's message tables

MH4U keeps its text in `rLayoutMessage` resources, extension `.lmd`: a header of counts and
offsets, a table of 8-byte label entries, a table of 16-byte formatting entries (two per
message), a table of 12-byte string records and the messages themselves, NUL-terminated
UTF-16LE strings. The file stores no path; the game names each table by the path it is loaded
from, e.g. `eng\msg\emName_eng` in `eng\data\core_common.arc`, whose message N is the name of
monster N, and `emExp`, whose message N is its Hunter's Notes text
([reference](../reference/README.md#mh4u-monster-tables)). Reader: `mhuc lmd FILE` (`src/mhuc/formats/lmd.py`).

**Sources.** Our reading of MH4U USA v1.3.0's code: the message loader `0x005aa2f0` (the
71-path list at `0x00f006c4`, its 71 loaded `rLayoutMessage` pointers stored at `0x0109a080`)
and the getters `0x00cdfb30` (format entry by id), `0x00cdfa30` (string record by id) and
`0x00cdfa18` (string record by format entry). The file checks are in [Checks](#checks). No
community layout was used.

## Header (0x24 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `lmd\0` | verified | loader `0x005aa2f0`; LM1 (all 1,455 tables) |
| 0x04 | u32 | version: 0x0001010B | verified | loader; LM1 |
| 0x08 | u32 | count of 8-byte label entries | verified | the label table's size in every file; LM1 |
| 0x0C | u32 | count of 16-byte formatting entries (two per message) | verified | the formatting table's size; LM1 |
| 0x10 | u32 | count of 12-byte string records | verified | the record table's size; LM1 |
| 0x14 | u32 | offset of the label table, always 0x24 | verified | loader rebases it; LM1 |
| 0x18 | u32 | offset of the formatting table | verified | LM1 (equals 0x24 + 8 × label count) |
| 0x1C | u32 | offset of the string-record table | verified | LM1 (equals the formatting offset + 16 × formatting count) |
| 0x20 | u32 | end of the message strings | verified | LM1 (the last record's string ends at it or two bytes before it) |

The file may carry 5 to 13 bytes after the string area that no message record points into
(the table's name and alignment are the likely content); they are not read. Status: unknown.

## Label entry (8 bytes, from header +0x14)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | label hash | unverified | shape only; every file's label region is label count × 8 bytes (LM1) |
| +0x04 | u32 | entry tag: on the id-indexed tables (one label and one record per message) `0x00400000 + 2 × message index`, the index of the message's formatting entry | verified | the getter `0x00cdfb30` masks the low 22 bits and indexes the 16-byte entries by it; true for `emName` and `emExp` (LM1) |

Other tables (the lobby, dialogue and DLC tables) label only some strings and use other tag
values; their labels are not read. The id-indexed tables are the ones this repository needs:
`emName` and `emExp` have one label and one record per message.

## Formatting entry (16 bytes, from header +0x18)

Two entries per message on the id-indexed tables: entry 2N belongs to message N, entry 2N+1 is
a second formatting record.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | 1 on the message's own entry, 0x16 on the second entry | unverified | counted on every `emName`/`emExp` file (LM1); the getter `0x00cdfb30` indexes by 2N |
| +0x04 | u32 | string-record index (N on message N's entry; 0 on the second entry) | verified | the getter `0x00cdfa18` reads it as the index into the string records; LM1 |
| +0x08 | u32 | zero | unverified | LM1 (0 in all entries) |
| +0x0C | u32 | zero | unverified | LM1 (0 in all entries) |

The other fields are the runtime text object's formatting (font, width and colour words); they
are copied through, not understood.

## String record (12 bytes, from header +0x1C)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | offset of the message string, from the file start | verified | the getter `0x00cdfa30` rebases it into a pointer; every string resolves (LM1) |
| +0x04 | u32 | UTF-16 code units in the message, its NUL not counted | verified | LM1 (every string is NUL-terminated at this length) |
| +0x08 | u32 | width: equal to +0x04 in every file read | verified | LM1; the game reads it as the text's width (`0x00ae3fe0`) |

Then the messages, in record order: NUL-terminated UTF-16LE strings, no separators.
`emName` and `emExp` have 123 records and 123 messages; record N is message N, and message N
names monster id N (message 0 is `No enemy`, message 1 `Rathian`). Other tables may have more
records than strings or extra label-only entries; a record index is a message id only on the
id-indexed tables.

## Checks

- **LM1 (done):** read every `rLayoutMessage` entry of MH4U USA v1.3.0. Procedure:
  `MHUC_DUMPS=… python3 -m pytest -m game_files -k message_table` reads every `core_*.arc` of
  the five languages in the base RomFS, parses every entry and counts; `mhuc survey
  <romfs.bin> --workers 1` (section `lmd`) does the same over the whole image, and was run on
  the update's image too. Pass:
  every entry parses, the header's offsets are in file order, every table's region sizes and
  counts agree, every string record resolves to a terminated UTF-16LE string inside the
  string area, and the two record lengths are equal.
  Result (the game-files test, 2026-11-25): 920 tables in the base RomFS's 50 `core_*.arc`,
  184 per language; the update RomFS's 20 `core_*.arc` hold 535 more, 107 per language; all
  1,455 read. `emName` and `emExp` have 123 messages each in every language. Every message's
  two lengths are equal; message 0 of `emName_eng` is `No enemy` and message 1 `Rathian`.
  This check is what established the fields marked verified; it records numbers only.

## Open questions

- The label hash's function and the tag values of tables that label only some strings.
- The trailer after the string area.
- Whether MH3U and MHXX ship any `.lmd`; neither was found in their RomFS (MH4U's text is the
  only `.lmd` set read).
