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
MH4U's resource record names two MEF files per monster; MH3U ships one ESQ per monster (44 of its
85 monster archives have one); MHXX ships one PSL per motion list. MH4U's is what a port must
produce, the other two are what it must read.

**Source.** No public tool lays these out. The class names, ids and sizes come from the engines'
own class registries: MH4U's `config/mt_classes.tsv` (`rMhMotionEffect` `0x148b6f89`, size `0x88`;
its data class `cMhMotionEffectData` `0x61aeb049`, size `0x58`), MH3U's and MHXX's
`reference/games/*/mt_classes.tsv` (`rEffectSequence` `0x525bbf16`, `0x68`;
`rProofEffectMotSequenceList` `0x254309c9`, `0x68`). The paths are the games' own resource paths:
the MH4U records' data, MH3U's `code.bin` format strings and the MHXX archives. The containers
below are our own reading, checked on real files (FX1, FX2, FX3), with MH4U's loaders read for
what the file has to satisfy: `rMhMotionEffect`'s load at `0x398f94` (vtable slot 11) and
`cMhMotionEffect`'s serializer at `0x390ccc`. The record fields are ours and are **not
understood** beyond the key the loader itself uses: a converter must not map the rest until a
check pins their meaning.

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
| +0x00 | u8 | 0 to 31; (an animation slot) is the guess | unverified | ours; FX1 |
| +0x01 | u8 | 0 to 2 | unverified | ours; FX1 |
| +0x02 | u8 | 0 or 1 | unverified | ours; FX1 |
| +0x03 | u8 | 0, 1 or 5 | unverified | ours; FX1 |
| +0x04 | u16 | record key: unique within its file, 0 to 4505; the loader indexes the records by it (`0x398f94`). What the game looks it up by is unverified | verified | ours, MH4U loader `0x398f94`; FX3 |
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

## How MH4U reads it

`rMhMotionEffect`'s load (`0x398f94`, vtable slot 11) checks the magic and the version byte 9,
reads the count and copies each 0x48-byte file record unchanged to `+0x08` of a
`cMhMotionEffectData` object. It then builds a table at the resource's `+0x80`: one u16 entry per
value from 0 to the largest record key, holding the record's index, with `0xFFFF` for a key no
record has; `+0x84` holds that length. The table is why the keys must be unique within a file; a
duplicate would leave one record unreachable. What the game passes as the lookup key, and what
every other record field means, is not read yet.

## MH3U ESQ

One per monster, read in place inside its archive (`effect\esq\em\emNNN`, class id `0x525bbf16`).
The header is 0x24 bytes and holds six offsets into the rest of the file.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `ESQ\0` | verified | ours; FX2 (44 entries) |
| 0x04 | u32 | version `0x20110217` in every file | verified | ours; FX2 |
| 0x08 | u32 | header size, `0x24` in every file | verified | ours; FX2 |
| 0x0C | u32[6] | six section offsets, each `0x24` ≤ offset ≤ file size and non-decreasing; an empty section repeats its neighbour's offset | verified | ours; FX2 |
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

## What a converter does

The converters are `src/mhuc/formats/mef.py` and, for the effect-id map, `src/mhuc/effectmap.py`
(whose tables ship empty, [data/effectmap](../data/effectmap/README.md)).

| Conversion | Carried | Skipped or refused |
|---|---|---|
| MEF (MH4U) -> MEF: `read_mef(...).to_bytes()`, `to_mh4u(data, "mh4u")` | every byte: the header from its fields, the records unchanged | nothing |
| ESQ (MH3U) -> its own form: `read_esq(...).to_bytes()` | the header, six section offsets and body unchanged | nothing (round trip only) |
| PSL (MHXX) -> its own form: `read_psl(...).to_bytes()` | the header, slot table and body unchanged | nothing (round trip only) |
| ESQ or PSL -> MEF: `to_mh4u(data, "mh3u"\|"mhxx")` | the source's container is read and checked | **refused**: every record field is unmapped, and the record key at `+0x04` is not known to be an action, a motion or an event id, so a record written today would never be looked up and its effect would never play |

The refusal is deliberate: a MEF whose keys don't match the game's lookup cannot play effects, so
writing one would carry guesses into a port. What has to be read to lift it:

- **the key's namespace.** The keys are the ids the motion lists' event blocks remap to: in
  `em001_0.lmt` 10 of the 11 nonzero remap ids of its four event groups are keys of
  `em001_0.mef`, and in `em015_0.lmt` 24 of 25 are keys of `em015_0.mef`. The MEF also has keys
  no shipped motion list names, so code can trigger a record too. **MH3U's and MHXX's motion
  lists carry no such ids** (every MH3U v66 event is one zero-bits event per group and MHXX's
  remaps are zero), so a port that keeps the source's animations has to write the event entries
  itself, with ids of its own, and key the MEF to them. That makes the converter a writer of
  both the MEF and the ported LMT's event blocks, not of the MEF alone. The samples above are
  not a full check; FX4 would be.
- **the source fields.** MH3U's ESQ six sections and 0x3C-byte entries and MHXX's PSL descriptors
  and lists need the same treatment: the loaders (`0x3b30cc` MH3U, `0x6eb318` MHXX v1.4) only
  relocate their offsets, and the fields they point at are not placed.
- **the source fields' readers.** A linear code pass found where the source resources are loaded but
  not where their fields are read. MH3U loads the ESQ with `0x8475fc` (15 per-class setup callers
  between `0x69a930` and `0x821d88`), stores it at the monster's `+0x1a68`, and `0x8fca78` puts it
  in the class resource array at `+0x24d8`; the factory is `0xa1a544`. MHXX's PSL loader is
  `0x6eb318`, its factory `0xabf6b4`, and the per-monster setups `0x2ddcf8`, `0x2ddfc0`,
  `0x3248d0`, `0x4037ac` and `0x8aa090` load it beside `cMhEffectSequence` (`0xd740e0`). No
  instruction reads `[x+0x1a68]` or a `0x24d8` displacement directly, and the PSL factory has no
  direct caller. A pointer-table pass then placed the class methods: MH3U's `rEffectSequence`
  vtable is `0xb6e9a8`, the factory `0xa1a544` sits at slot `0xb6f3e0` and the loader `0x3b30cc` at
  slot `0xb58044`, and the factory's objects use vtable `0xb575e8`. MHXX's resource vtable is
  `0xd0d5e8` (the factory `0xabf6b4` in its slot 2, `0xd0d5f0`) and the objects it makes use vtable
  `0xcf64c0`, whose slot 11 is the loader `0x6eb318` (`0xcf64ec`). All of those methods are
  lifecycle, serializer and helper code; none reads the slot table, the descriptors or the
  0x3C-byte ESQ entries. The field readers are therefore not class methods: the next targets are
  the manager the path loader calls (MH3U global `0xca8980`, MHXX `0xd3b0d0`) and the class
  resource-array setup `0x8fca78` on MH3U's side, then whatever reads those array entries - the
  array base is computed, so that needs a data-flow pass or an in-game trace.
- **the effect-id map.** Each record's effect id is a game's own id space. `data/effectmap` holds
  the source-to-MH4U rows (empty until the maintainer's dumps and a check fill them), and
  `mhuc.effectmap.EffectMap.check` refuses a conversion that meets an id they don't name. The
  effect assets an id names (the monster's `effect/base/...`) must be converted with it.
- **the two files.** MH4U's record names two MEF paths; which records go in which is unverified.

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
  version `0x20110217`, every set of six offsets inside the file and non-decreasing, with five files repeating one offset; 507 PSL
  entries with 18,831 slots and 8,129 descriptors, every version 2, slot 0's offset 0 in every file, every nonzero slot offset where
  the slot order puts it, seventeen 8-byte files with no slots. The section contents and descriptor
  contents were not decoded.
- **FX3 (done, 2026-11-25).** Every MEF file's record keys are unique, which the loader's
  key-to-record table needs, and the largest is 4505 (a u16's range is what the table holds).
  Procedure: read all 96 distinct MEF resource paths of MH4U's monster archives
  (`MHUC_DUMPS=… python3 -m pytest -q -m game_files -k effects_round_trip` plus the unit tests)
  and take the u16 at `+0x04` of every record; no file repeats a key, and the keys span 0 to 4505.
  The loader's use of the key is read from `0x398f94`, not checked in game; what it is looked up
  by stays unverified.
- **FX4 (open).** The motion lists' event remap ids are the MEF keys: every nonzero remap id of a
  motion list's four event groups should have a record in that list's MEF. Sample so far:
  `em001_0` 10 of 11, `em015_0` 24 of 25. A full pass reads every MH4U monster arc's motion lists
  and MEFs; it needs the same whole-archive pass as FX1 and has not run yet.
