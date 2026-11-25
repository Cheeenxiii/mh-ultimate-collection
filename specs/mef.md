---
class: rMhMotionEffect, rEffectSequence, rProofEffectMotSequenceList
extension: mef, esq, psl
games: MH4U, MH3U, MHXX
status: unverified
---

# Motion effects: MH4U's MEF, MH3U's ESQ and MHXX's PSL

A monster's visual effects are played at frames of its animations. Each game keeps that timing in a
resource of its own: MH4U in `rMhMotionEffect` (magic `MEF\0`, extension `mef`), MH3U in
`rEffectSequence` (`ESQ\0`, `esq`) and MHXX in `rProofEffectMotSequenceList` (`PSL\0`, `psl`).
MH4U's resource record names two MEF files per monster; MH3U ships one ESQ per monster; MHXX ships
one PSL per motion list. MH4U's is what a port must produce, the other two are what it must read.

**Source.** No public tool lays these out. The class names, ids and sizes come from the engines'
own class registries: MH4U's `config/mt_classes.tsv` (`rMhMotionEffect` `0x148b6f89`, size `0x88`;
its data class `cMhMotionEffectData` `0x61aeb049`, size `0x58`), MH3U's and MHXX's
`reference/games/*/mt_classes.tsv` (`rEffectSequence` `0x525bbf16`, `0x68`;
`rProofEffectMotSequenceList` `0x254309c9`, `0x68`). The paths are the games' own resource paths:
the MH4U records' data, MH3U's `code.bin` format strings and the MHXX archives. The containers
below are our own reading, checked on real files (FX1, FX2). The record fields are ours and are
**not understood**: a converter must not map them until a check pins their meaning.

## How a record names them

| Game | Resource | Path | What names it |
|---|---|---|---|
| MH4U | `rMhMotionEffect` | `effect\mef\em\emNNN_0` and `_1` | the monster resource record's `+0x14`: two path pointers ([reference/README.md](../reference/README.md#mh4u-monster-tables)). MH4U's data holds both strings for each of its ids |
| MH3U | `rEffectSequence` | `effect\esq\em\emNNN` | one per monster; the loader's format string `effect\esq\em\em%03d` is in MH3U's `code.bin`. Which record field selects it is unverified |
| MHXX | `rProofEffectMotSequenceList` | `effect\psl\enemy\emNNN\emNNN_RR\mot\emNNN_RR_K` | one per motion list `K` of rank `RR`; the paths are in the monster's rank archive. No path string was found in MHXX's `code.bin` or its CRO modules, so which record field selects it is unverified |

## MH4U MEF

The whole file is a 0x0C-byte header and a flat array of records; there is no header-size field.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MEF\0` | verified | ours; FX1 (150 entries, 96 distinct resource paths) |
| 0x04 | u32 | version, 9 in every file | verified | ours; FX1 |
| 0x08 | u32 | record count *n* | verified | ours; FX1 |
| 0x0C | 0x48 × *n* | *n* records, below; nothing follows them | verified | ours; FX1 (6,216 records, every file's size `0x0C + 0x48 * n`) |

### Record (0x48 bytes)

The field meanings are unverified. The Name column says only what the value range allows, and every
range is the one FX1 found across all 6,216 records; a name in parentheses is a guess, not a fact.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | 0 to 31; repeats with the motion-list file, so (animation slot) is the guess | unverified | ours; FX1 |
| +0x01 | u8 | 0 to 2 | unverified | ours; FX1 |
| +0x02 | u8 | 0 or 1 | unverified | ours; FX1 |
| +0x03 | u8 | 0, 1 or 5 | unverified | ours; FX1 |
| +0x04 | u16 | 0 to 4505 | unverified | ours; FX1 |
| +0x06 | u16 | 0 to 122, (a frame) is the guess | unverified | ours; FX1 |
| +0x08 | u16 | 0 to 210, (a bone) is the guess | unverified | ours; FX1 |
| +0x0A | u16 | `0xFFFF` or a small number | unverified | ours; FX1 |
| +0x0C | u16 | 0 to 4641, 0 in 5 records; (an effect id) is the guess | unverified | ours; FX1 |
| +0x0E | u16 | 0, 32 or 64 | unverified | ours; FX1 |
| +0x10 | u32 | `0xFFFFFFFF` or 0 to 4; (a link or index) is the guess | unverified | ours; FX1 |
| +0x14 | f32 | finite; a value in a 4-value group with +0x18, +0x1C and +0x20 | unverified | ours; FX1 |
| +0x18 | f32 | finite, as +0x14 | unverified | ours; FX1 |
| +0x1C | f32 | finite, as +0x14 | unverified | ours; FX1 |
| +0x20 | f32 | finite, as +0x14 | unverified | ours; FX1 |
| +0x24 | u32 | always 0 | verified | ours; FX1 |
| +0x28 | f32 | finite; a value in a 3-value group with +0x2C and +0x30 | unverified | ours; FX1 |
| +0x2C | f32 | finite, as +0x28 | unverified | ours; FX1 |
| +0x30 | f32 | finite, as +0x28 | unverified | ours; FX1 |
| +0x34 | u32 | always 0 | verified | ours; FX1 |
| +0x38 | f32 | finite; the first of three equal-typed values at +0x38, +0x3C and +0x40 | unverified | ours; FX1 |
| +0x3C | f32 | finite, as +0x38 | unverified | ours; FX1 |
| +0x40 | f32 | finite, as +0x38 | unverified | ours; FX1 |
| +0x44 | u32 | always 0 | verified | ours; FX1 |

## MH3U ESQ

One per monster, read in place inside its archive (`effect\esq\em\emNNN`, class id `0x525bbf16`).
The header is 0x24 bytes and holds six offsets into the rest of the file.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `ESQ\0` | verified | ours; FX2 (44 entries) |
| 0x04 | u32 | version `0x20110217` in every file | verified | ours; FX2 |
| 0x08 | u32 | header size, `0x24` in every file | verified | ours; FX2 |
| 0x0C | u32[6] | six section offsets, each `0x24` ≤ offset ≤ file size and non-decreasing; an empty section repeats its neighbour's offset (five files do) | verified | ours; FX2 |
| 0x24 | bytes | the six sections; the first two look like fixed 0x3C-byte entries, but no field is placed | unverified | ours; FX2 |

## MHXX PSL

One per motion list. A file with no effects is 8 bytes: magic, version and a slot count of 0
(seventeen do). Otherwise the header holds one u32 per animation slot, then one 0x10-byte descriptor
for each slot that has effects, in slot order.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `PSL\0` | verified | ours; FX2 (507 entries) |
| 0x04 | u16 | version, 2 in every file | verified | ours; FX2 |
| 0x06 | u16 | slot count *n* | verified | ours; FX2 |
| 0x08 | u32[*n*] | one offset per slot; slot 0's is 0 in every file, a slot with no effects is 0, and the *k*-th nonzero offset is `align(0x08 + 4*n*, 0x10) + 0x10*k*` (18,831 slots, 8,129 descriptors) | verified | ours; FX2 |
| 0x08 + 4*n* | 0x10 × descriptors | the slot descriptors, in slot order: three u32 values (the first 5 to 1767, the second `0x00200000` or `0x01200000`, the third larger), then a fourth u32 that is 0 in most but not all | unverified | ours; FX2 |
| end | bytes | the per-slot effect lists the descriptor points at | unverified | ours; FX2 |

## What a converter must produce

MH4U loads the two MEF files its record names and, at run time, spawns the effects a record asks
for. A port's converter must therefore write **MEF version 9** with the record count, record size
and fixed zeros above; it must also decide what each of the two files holds and fill the fields
from the source game's ESQ or PSL. That mapping is not possible from this spec yet:

- the MEF record's slot, frame, effect-id and placement fields are unverified;
- MH3U's ESQ sections and MHXX's PSL descriptors are unverified, so their source fields can't be
  paired with MH4U's;
- an effect id is a game's own id space: a source→MH4U effect-id map has to be built (the same
  shape as quests' `data/idmap/`, which ships empty), and the effect assets an id names (the
  monster's `effect/base/...` models, textures, materials and animations) have to be converted
  with it. MH4U's record also names an effect-list file (`specs/efl.md`), so the two formats go
  together.

A check that pins the record's meaning is what unblocks the converter: play a known record in
game and see which effect appears at which frame, or read the MH4U function that walks the array.
Until then, a port keeps its stand-in's MEF paths ([data/ids/README.md](../data/ids/README.md)).

## Checks

- **FX1 (done, 2026-11-25).** Read every `rMhMotionEffect` entry of MH4U's monster archives and
  check the header and each record: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k
  mh4u_motion_effect`, with the synthetic reader tests in `tests/test_effects.py`. Result: 150
  entries, 96 distinct resource paths and 6,216 records, all read; every file's size is
  `0x0C + 0x48 * n`; `+0x24`, `+0x34` and `+0x44` are 0 in every record; the bytes at `+0x07`,
  `+0x09` and `+0x0F` are 0 in every record; the three floats at `+0x38` are finite in every
  record. The value ranges in the record table are FX1's tally.
- **FX2 (done, 2026-11-25).** Read every `rEffectSequence` and `rProofEffectMotSequenceList` entry
  of MH3U's and MHXX's monster archives: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k
  "effect_sequence or mhxx_motion_effect"`. Result: 44 ESQ entries, every header size `0x24`, every
  version `0x20110217`, every set of six offsets inside the file and non-decreasing; 507 PSL
  entries with 18,831 slots and 8,129 descriptors, every version 2, every nonzero slot offset where
  the slot order puts it, seventeen 8-byte files with no slots. The section contents and descriptor
  contents were not decoded.
