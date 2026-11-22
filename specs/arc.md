---
class: rArchive
extension: arc
games: MH4U, MHX, MHXX, MH3U (3DS)
status: verified
---

# ARC: MT Framework archive

Every RomFS asset of the 3DS MT Framework Mobile games sits in `.arc` archives: a header, a table of entries, then one zlib stream per file. `mhuc.arc` reads and writes it; [arc.ksy](arc.ksy) describes it.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `ARC\0` | verified | mhff arc.py, Kuriimu2 MtArc; check C2 |
| 0x04 | u16 | version: 0x13 MH4U, 0x11 MHXX, 0x10 MH3U | verified | mhff arc.py (0x13, 0x11); check C2 (all three, and MH3U's 0x10) |
| 0x06 | u16 | entry count | verified | mhff arc.py; check C2 |
| 0x08 | u32 | unknown; present unless version is 7 or 8; 0 in every archive of the three games | verified | Kuriimu2 MtArc.LoadLittleEndian, mhff arc.py; check C2 |

## Entry (0x50 bytes, `count` of them from 0x0C)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[64] | path, `\`-separated, no extension, NUL padded | verified | mhff arc.py; check C2 |
| 0x40 | u32 | class id of the file's resource type, `~crc32(name) & 0x7FFFFFFF` | verified | mhff arc.py; check C1 |
| 0x44 | u32 | compressed size | verified | mhff arc.py; check C2 |
| 0x48 | u32 | decompressed size in the low bits, flags above (table below) | verified | mhff arc.py; checks C2, C3 |
| 0x4C | u32 | offset of the zlib stream from the start of the file | verified | mhff arc.py; check C2 |

## Data

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| after the table | zero bytes | padding up to the first stream: a 32-byte boundary (MH4U, MHXX), 0x8000 (MH3U) | verified | ours; check C2 |
| first stream on | zlib[count] | the streams, back to back in entry order, no padding between them or after the last | verified | ours; check C2 |

## Size word flags

The games' own archives carry one flag value per game in the top three bits; mhff's 0x40000000 is MH3U's and MHXX's, not MH4U's.

| Game | Flags seen | Note |
|---|---|---|
| MH4U | 0x20000000; 0xA0000000 on some models | the 0x80000000 bit is on 1,198 of 1,425 sampled `rModel` entries and nothing else |
| MH3U | 0x40000000 | every entry |
| MHXX | 0x40000000 | every entry of the Japanese release |

What the bits mean (quality or load priority in other MT titles) is still unknown on 3DS. `mhuc.arc` writes each game's usual value in new archives and keeps the original flags of existing entries.

## Open questions

- The flag bits' meaning, and whether the game checks them.
- Whether the game needs the 32-byte (0x8000) alignment of the first stream. Fan patches for MHXX rebuild archives without it and the game is said to load them; not checked here.
- No 3DS archive in the three games is encrypted (check C2 read them all as plain zlib).

## Checks

Run on 2026-11-23 with `mhuc survey <romfs.bin>` on the maintainer's dumps: MH4U USA (cartridge) and the v1.3.0 update, MH4U EUR, MH3U USA, MHXX JPN (cartridge) and its v4.8.0 update, and a fan-translated MHXX. Results in words and counts only.

- **C1 (done): class ids.** `mhuc.classid.class_id` was run over every class name in MH4UltimateDC's `config/mt_classes.tsv`, whose ids were recovered from MH4U's own class registry: 989 of 990 match. The one mismatch, `uShell052`, is a registry row to look at, not a hash question.
- **C2 (done): round trip.** For every `.arc` in the RomFS: `arc.read` succeeds, and `arc.write(arc.read(data)) == data`.
  - MH4U USA: 10,592 archives, all version 0x13, all round trip. EUR: the same 10,592. Update v1.3.0: 20, all round trip.
  - MH3U USA: 4,386 archives, all version 0x10, all round trip; the first stream is always at 0x8000.
  - MHXX JPN: 12,255 archives, all version 0x11, all round trip.
  - The fan-translated MHXX and the v4.8.0 update as dumped hold 652 archives rebuilt by the translation's tools (first stream unaligned, MH4U-style 0x20000000 flags). They round trip too, but they are not a reference for the layout; use the Japanese cartridge.
  - No zlib stream failed to inflate in any game, and every decompressed length matched its size word.
- **C3 (done): size mask.** The largest entry in any game is under 0x00600000 (MH3U), so no entry uses bit 24 or above for its size, and nothing tells 0x00FFFFFF, 0x0FFFFFFF and 0x1FFFFFFF apart. The top three bits are the flags above; mhuc's masks stay as they are.
