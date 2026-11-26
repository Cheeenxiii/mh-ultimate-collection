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
below are our own reading, checked on real files (FX1, FX2, FX3, FX5, FX6), with MH4U's loaders
read for what the file has to satisfy: `rMhMotionEffect`'s load at `0x398f94` (vtable slot 11) and
`cMhMotionEffect`'s serializer at `0x390ccc`, and MH3U's ESQ loader at `0x3b30cc`. The MEF record
fields are ours and are **not understood** beyond the key the loader itself uses, and the ESQ
event's effect parameters and the PSL body are not either: a converter must not map them until a
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
Its 0x24-byte header holds **seven** section offsets at +0x08, not a header-size field and six
offsets: the loader relocates all seven into pointers (`0x3b30cc`), so the first is the start of
the first section and is `0x24` in every file.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `ESQ\0` | verified | ours; FX2 (44 entries) |
| 0x04 | u32 | version `0x20110217` in every file | verified | ours; FX2 |
| 0x08 | u32[7] | seven section offsets: the first is `0x24`, all are inside the file and non-decreasing, an empty section repeats its neighbour's offset | verified | ours, loader `0x3b30cc` relocates +0x08 to +0x20; FX2 |
| 0x24 | bytes | the seven sections, below | unverified | ours; FX2 |

### Sections

Section *i* runs from offset *i* to offset *i+1*; the seventh runs from the last offset to the end.
The sizes say which sections share an entry size (all 44 files):

| Section | Entry size | Contents |
|---|---|---|
| 0, 1, 2, 4 | 0x3C | the motion-effect events, below; 8,092 in the 44 files |
| 3 | 0x0C | unplaced |
| 5 | 0x10 | unplaced |
| 6 | — | a fixed 0x258 bytes, mostly `0xFF`; unplaced |

What separates the four event sections is unverified: they may be the four event groups MH4U's
motion lists carry. The sizes are FX2's; the event contents are FX5's.

### Event (0x3C bytes)

The motion and the frame are placed and checked; the rest of the entry is the effect's parameters
and is not.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | motion index: `file * 100 + slot`, MH3U's numbering (`reference/monster_motions.py`), the file being the monster's motion list 0, 1, 2… | verified | ours; FX5 |
| +0x04 | f32 | frame in that animation; inside it for 7,976 of the 7,983 events whose animation the archive has, with 7 outside (FX5) | verified | ours; FX5 |
| +0x08 | bytes[0x34] | the effect's parameters: eight u16 at +0x08, four 4-byte values at +0x18, four at +0x28 and a u32 at +0x38; **no field is placed** | unverified | ours; FX2 tallies the ranges, FX5 reads them |

An all-zero event is padding at the end of its section (49 across the 44 files). An event whose
motion slot the monster's own archive leaves empty is not padding: 60 of the 8,043 nonzero events
name one, which the archive may share from another monster's; 7 more name an animation whose frame
count the frame is past (FX5).

## MHXX PSL

One per motion list. A file with no effects is 8 bytes: magic, version and a slot count of 0
(seventeen do). Otherwise the header holds one u32 per animation slot, then one 0x10-byte descriptor
for each slot that has effects, in slot order. The descriptors are at
`align(0x08 + 4*n*, 0x10) + 0x10*k*`.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `PSL\0` | verified | ours; FX2 (507 entries) |
| 0x04 | u16 | version, 2 in every file | verified | ours; FX2 |
| 0x06 | u16 | slot count *n* | verified | ours; FX2 |
| 0x08 | u32[*n*] | one offset per slot; slot 0's is 0 in every file, a slot with no effects is 0, and the *k*-th nonzero offset is `align(0x08 + 4*n*, 0x10) + 0x10*k*` (18,831 slots, 8,129 descriptors) | verified | ours; FX2 |
| descriptor +0x00 | u32 | the frame count of the animation in the slot the descriptor sits at | verified | ours; FX6 |
| descriptor +0x04 | u32 | `0x00200000` or `0x01200000`; unplaced | unverified | ours; FX2 |
| descriptor +0x08 | u32 | the slot's effect list, a value that grows within the file; the list's layout is not placed | unverified | ours; FX2 |
| descriptor +0x0C | u32 | 0 in most descriptors, a small value in others; unplaced | unverified | ours; FX2 |
| end | bytes | the per-slot effect lists the third value points at; not laid out | unverified | ours; FX2 |

One hundred and ten descriptors are in four PSLs whose motion list isn't in the same archive, so
their frame count has no local animation to compare with; of the 8,019 that do, 7,980 name an
animation in their slot and its frame count is that animation's, and 39 name a slot the archive
leaves empty (FX6).

## What a converter does

The converters are `src/mhuc/formats/mef.py` and, for the effect-id map, `src/mhuc/effectmap.py`
(whose tables ship empty, [data/effectmap](../data/effectmap/README.md)).

| Conversion | Carried | Skipped or refused |
|---|---|---|
| MEF (MH4U) -> MEF: `read_mef(...).to_bytes()`, `to_mh4u(data, "mh4u")` | every byte: the header from its fields, the records unchanged | nothing |
| ESQ (MH3U) -> its own form: `read_esq(...).to_bytes()`, `read_esq(...).events()` | the header, seven section offsets and body unchanged; each event's motion and frame read | nothing (round trip only; what an event does is not placed) |
| PSL (MHXX) -> its own form: `read_psl(...).to_bytes()` | the header, slot table, descriptors and body unchanged; each descriptor's frame count read | nothing (round trip only; what a list holds is not placed) |
| ESQ or PSL -> MEF: `to_mh4u(data, "mh3u"\|"mhxx")` | the source's container is read and checked, and the motion and frame of each event are placed | **refused**: no MEF record field beyond the key is placed, and the source's effect id, bone, placement and flags are not, so a record written today would carry guesses |

The refusal is deliberate: a MEF whose keys don't match the game's lookup cannot play effects, and
a record whose other fields guess would play the wrong effect at the wrong place, so writing one
would carry guesses into a port. What has to be read to lift it:

- **the key's namespace.** The keys are the ids the motion lists' event blocks remap to: in
  `em001_0.lmt` 10 of the 11 nonzero remap ids of its four event groups are keys of
  `em001_0.mef`, and in `em015_0.lmt` 24 of 25 are keys of `em015_0.mef`. The MEF also has keys
  no shipped motion list names, so code can trigger a record too. **MH3U's and MHXX's motion
  lists carry no such ids** (every MH3U v66 event is one zero-bits event per group and MHXX's
  remaps are zero), so a port that keeps the source's animations has to write the event entries
  itself, with ids of its own, and key the MEF to them. That makes the converter a writer of
  both the MEF and the ported LMT's event blocks, not of the MEF alone. The samples above are
  not a full check; FX4 would be.
- **the source's effect parameters.** The ESQ event's motion and frame are placed (FX5), and a PSL
  descriptor's frame count (FX6), but neither file's effect id, bone, placement, scale or flags is:
  0x34 bytes of the 0x3C-byte ESQ event and the whole body of a PSL file remain unplaced. The
  loaders (`0x3b30cc` MH3U, `0x6eb318` MHXX v1.4) only relocate the offsets.
- **MH4U's record fields.** Only `+0x04` is placed (the key, [above](#how-mh4u-reads-it)); what
  `+0x00` to `+0x03`, `+0x06`, `+0x08`, `+0x0A`, `+0x0C`, `+0x0E`, `+0x10` and the three float
  groups mean is unverified, so the effect id, the bone, the frame and the placement have no
  target field.
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
- **FX2 (done, 2026-11-25, re-run 2026-11-26).** Read every `rEffectSequence` and
  `rProofEffectMotSequenceList` entry of MH3U's and MHXX's monster archives: `MHUC_DUMPS=… python3
  -m pytest -q -m game_files -k "effect_sequence or mhxx_motion_effect"`. Result: 44 ESQ entries,
  every version `0x20110217`, every section 0 at `0x24`, every set of seven offsets inside the
  file and non-decreasing with five files repeating one offset, every section a whole number of
  its entry size, every seventh section `0x258` bytes; 507 PSL entries with 18,831 slots and
  8,129 descriptors, every version 2, slot 0's offset 0 in every file, every nonzero slot offset
  where the slot order puts it, seventeen 8-byte files with no slots. The section contents are
  FX5's; the descriptors are FX6's.
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
- **FX5 (done, 2026-11-26).** An ESQ event's motion and frame decode against the monster's own
  motion lists: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k
  effect_sequence_event`, with the unit tests in `tests/test_effects.py`. Procedure: read every
  ESQ entry of MH3U's monster archives, take the 0x3C-byte events of sections 0, 1, 2 and 4, read
  `+0x00` as MH3U's motion index `file * 100 + slot` and `+0x04` as a frame, and compare the frame
  with the animation's frame count from the same archive. Result: 8,092 events, 49 all-zero
  padding entries, 7,976 whose animation is in the archive and whose frame is inside it, 60 that
  name a slot the archive leaves empty (a motion list it shares with another monster's archive),
  and 7 whose frame is outside: em066's and em067's motion 85 at frame 193 (its animation has 139
  frames) and em072's motion 34 at frame 53 (43 frames). The 7 are open: they may be a shared
  motion, or an entry of a kind that isn't an effect event in the same section.
- **FX6 (done, 2026-11-26).** A PSL descriptor's first word is the frame count of the animation in
  its slot: `MHUC_DUMPS=… python3 -m pytest -q -m game_files -k psl_descriptor`. Procedure: read
  every PSL entry of MHXX's monster archives, find the motion list of the same name in the same
  archive, and compare each descriptor's first word with the frame count of the animation at the
  descriptor's slot. Result: 507 PSLs, 18,831 slots, 8,129 descriptors. 110 descriptors are in
  four PSLs whose motion list is not in the same archive; of the other 8,019, 7,980 equal their
  animation's frame count and 39 sit at a slot the archive leaves empty. No descriptor's frame
  count differs from the animation in its slot.
