---
class: rArchive
extension: arc
games: MH4U, MHX, MHXX, MH3U (3DS)
status: unverified
---

# ARC: MT Framework archive

Every RomFS asset of the 3DS MT Framework Mobile games sits in `.arc` archives: a header, a table of entries, then one zlib stream per file. `mhuc.arc` reads and writes it; [arc.ksy](arc.ksy) describes it.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `ARC\0` | unverified | mhff arc.py, Kuriimu2 MtArc |
| 0x04 | u16 | version: 0x13 MH4U, 0x11 MHX/MHXX | unverified | mhff arc.py |
| 0x06 | u16 | entry count | unverified | mhff arc.py |
| 0x08 | u32 | unknown; present unless version is 7 or 8; tools write 0 | unverified | Kuriimu2 MtArc.LoadLittleEndian, mhff arc.py |

## Entry (0x50 bytes, `count` of them from 0x0C)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[64] | path, `\`-separated, no extension, NUL padded | unverified | mhff arc.py |
| 0x40 | u32 | class id of the file's resource type, `~crc32(name) & 0x7FFFFFFF` | verified | mhff arc.py; check C1 |
| 0x44 | u32 | compressed size | unverified | mhff arc.py |
| 0x48 | u32 | decompressed size in the low bits, flags above: mask 0x0FFFFFFF (v0x13), 0x1FFFFFFF (v0x11) | unverified | mhff arc.py (Kuriimu2 masks 0x00FFFFFF for little-endian ARCs: to settle) |
| 0x4C | u32 | offset of the zlib stream from the start of the file | unverified | mhff arc.py |

Flags: mhff writes 0x40000000 in new archives. Their meaning (quality or load priority in other MT titles) is unknown on 3DS.

## Open questions

- MH3U's ARC version. The brief lists it as still to find; Kuriimu2 handles versions 7 and 8 without the extra header word, which may be MH3U's.
- The flag bits' meaning, and whether the game cares about stream order or alignment.
- Whether any 3DS archive is encrypted (Kuriimu2 has a Blowfish path for some PC titles).

## Checks

- **C1 (done): class ids.** `mhuc.classid.class_id` was run over every class name in MH4UltimateDC's `config/mt_classes.tsv`, whose ids were recovered from MH4U's own class registry: 989 of 990 match. The one mismatch, `uShell052`, is a registry row to look at, not a hash question.
- **C2 (with game files): round trip.** For every `.arc` in MH4U's, MHXX's and MH3U's RomFS: `mhuc arc list` succeeds, and `arc.write(arc.read(data)) == data`. Record the count of archives and versions seen, not their contents.
- **C3 (with game files): size mask.** Look for an entry whose decompressed size exceeds 0x00FFFFFF; if one exists, Kuriimu2's mask is wrong for 3DS.
