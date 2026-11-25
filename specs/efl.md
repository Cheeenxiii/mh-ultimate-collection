---
class: rEffectList, rProofEffectList
extension: efl, pel
games: MH4U, MH3U, MHXX
status: unverified
---

# Effect lists: EFL and PEL

An effect list names the effects a monster can play. MH4U, MH3U and MHXX all ship them as
`rEffectList` (magic `EFL\0`, extension `efl`); MHXX also ships `rProofEffectList` (`PEL\0`,
`pel`). MH4U's resource record names one or two EFL files per monster, so a port has to write them;
MHXX's PEL is what the newer engine calls an effect list, and whether a port needs it is part of
what its record names.

**Source.** No public tool lays these out. The class names and ids come from the engines' class
registries: `rEffectList` is `0x6d5ae854` in all three games (size `0x98` in MH4U and MH3U, `0x90`
in MHXX), and `rProofEffectList` is MHXX's `0x5a525c16` (size `0xa8`). The paths are the games' own:
the MH4U records' data, MH3U's `code.bin` format string and the MHXX archives. The EFL header is
our own reading, checked on real files (EF1, EF2). The block it points at and the PEL body are not
decoded.

## How a record names them

| Game | Resource | Path | What names it |
|---|---|---|---|
| MH4U | `rEffectList` | `effect\efl\em\emNNN\emNNN_NNN` | the monster resource record's `+0x24` (effect lists) and `+0x28` (a second effect list) ([reference/README.md](../reference/README.md#mh4u-monster-tables)); MH4U's data holds the strings |
| MH3U | `rEffectList` | `effect\efl\em\emNNN\emNNN_%03x` | the loader's format string is in MH3U's `code.bin`; which record field selects a file is unverified |
| MHXX | `rEffectList` | `effect\em\emNNN\emNNN_RR_NNN` | one per rank `RR`; the paths are in the monster's rank archive. Which record field selects them is unverified |
| MHXX | `rProofEffectList` | `effect\pel\em\emNNN_RRc` and `..._RRu` | as above; `c` and `u` are the file's two variants |

## EFL

All three games use one header, 0x30 bytes, followed by a block whose size the header gives. The
version word picks the game; the rest of the header is not understood.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `EFL\0` | verified | ours; EF1 (7,475 entries) |
| 0x04 | u32 | version: `0x30111104` MH4U, `0x30110616` MH3U, `0x30120306` MHXX | verified | ours; EF1 (1,937 / 1,496 / 4,042) |
| 0x08 | u32 | block size; the file is exactly `0x30 + this` bytes | verified | ours; EF1 (every file) |
| 0x0C | f32 | 60.0 in every file but one MH3U file (30.0) | unverified | ours; EF1 |
| 0x10 | u16, u16 | two counts: the first 0 to 108, the second 0 to 44 across the three games | unverified | ours; EF1 |
| 0x14 | u32 | `0x100` in every MH4U and 4,041 of 4,042 MHXX entries; in MH3U `0x100` 1,476 times, `0x102` 13, `0x101` 4, `0x122` once, 0 twice | unverified | ours; EF1 |
| 0x18 | u32 | always 0 | verified | ours; EF1 |
| 0x1C | u32 | always 0 | verified | ours; EF1 |
| 0x20 | u32 | 0 in every MH4U and MHXX entry; 0 in 1,478 of 1,496 MH3U entries | unverified | ours; EF1 |
| 0x24 | u32 | as `0x20` | unverified | ours; EF1 |
| 0x28 | u32 | as `0x20` | unverified | ours; EF1 |
| 0x2C | u32 | 0 or a value tied to the block's size; non-zero in 625 MH4U, 1,301 MH3U and 2,368 MHXX entries | unverified | ours; EF1 |
| 0x30 | u8[block size] | the block; its size is a multiple of 16 in every file, its contents are not placed | unverified | ours; EF1 |

## PEL (MHXX)

`rProofEffectList` files are in MHXX's monster archives. Only the first eight bytes are checked; the
rest is handed back by the reader but not laid out.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `PEL\0` | verified | ours; EF2 (280 entries) |
| 0x04 | u32 | version, 15 in every file | verified | ours; EF2 |
| 0x08 | bytes | the body; many files start with length-prefixed `effect\...` path strings after a few header words, but neither the boundary nor the fields is verified | unverified | ours; EF2 |

## What a converter must produce

For a port of a monster MH4U does not have, the converter must write an **EFL** with the game's
version word (`0x30111104`), the `0x30 + block size` header, the fixed zeros at `+0x18` and `+0x1C`
and a block that is a multiple of 16 bytes; and it must fill that block from the source game's EFL
so the effects the port's motion effects name are the effects the monster actually has. Three things
block that today:

- the block's layout is unverified, so no source block field can be paired with an MH4U one;
- MHXX's PEL body is unverified, so whether a GU monster needs PEL *and* EFL (and which one its
  record names) is unknown;
- the effect ids and resources a list names are each game's own: converting them needs the
  source→MH4U effect-id map and the effect assets, exactly as `specs/mef.md` says.

MH4U's record has two effect-list slots (`+0x24`, `+0x28`); what the second one holds is
unverified, so a converter that writes an EFL must say which slot it goes in. Until then a port keeps its stand-in's EFL paths ([data/ids/README.md](../data/ids/README.md)).

## Checks

- **EF1 (done, 2026-11-25).** Read every `rEffectList` entry of the three games' monster archives:
  `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k effect_list_header`, with the synthetic
  reader tests in `tests/test_effects.py`. Result: 7,475 entries (MH4U 1,937, MH3U 1,496, MHXX
  4,042), all read; every file is `0x30 + block size` bytes; every block size is a multiple of 16;
  every MH4U entry's version is `0x30111104`, MH3U's `0x30110616`, MHXX's `0x30120306`; `+0x0C` is
  60.0 in all but one MH3U file; `+0x18` and `+0x1C` are 0 in every file; `+0x20` to `+0x28` are 0
  in every MH4U and MHXX file and in 1,478 of 1,496 MH3U files. The value tallies in the table are
  EF1's.
- **EF2 (done, 2026-11-25).** Read every `rProofEffectList` entry of MHXX's monster archives:
  `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k mhxx_motion_effect`. Result: 280 entries, all
  magic `PEL\0` and version 15. The body was not decoded.
