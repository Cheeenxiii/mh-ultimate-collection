---
class: rCameraList
extension: lcm
games: MH4U (version 4) and MHXX (version 5); MH3U registers the class but ships no file
status: unverified
---

# LCM: camera list

A monster's own cameras: the cut-ins, mounts, pins and kill cameras its actions post by id. A
camera list holds up to 256 cameras, each a record with a frame count and up to four animation
tracks. A track is the same 0x24-byte structure an LMT motion list uses ([lmt](lmt.md#track-0x24-bytes)),
pointing at a key buffer and at a bounds block; the fourth track's block is shorter (0x14 bytes).

The camera list is the file MH4U's resource record names at `+0x08` for an id
(`enemy\emNNN\mot\eNNN_cam`, [reference](../reference/README.md#mh4u-monster-tables)); #143
answers a ported id's record with the stand-in's path until the port ships its own.

**Source.** MH4U's own loader `0x0023b808` (USA v1.3.0) for the header, the 256-entry table and
the seven words it relocates; MH4U's camera manager `0x00c0376c` for the record's frame count
and for what the fourth block is passed to; PredatorCZ's [RevilLib](https://github.com/PredatorCZ/RevilLib)
(GPL-3.0, `src/mtf_lmt/bone_track.cpp`, `codecs.hpp`, `codecs.cpp`) for the track and keyframe
layouts it shares with LMT; Scrimas's MHGU Definitive Edition (GPL-3.0-or-later,
`tools/lcm4u2gu.py`) for the version 4 to 5 record prefix and the offsets that move with it.
Both are read through [lmt.md](lmt.md), which lays the same track and codecs out. Reader:
`src/mhuc/formats/camera.py`.

## Versions

| Version | Games | Record | Layout |
|---|---|---|---|
| 4 | MH4U | 0x9c | the record below |
| 5 | MHXX (and MHGU) | 0xac | the same record behind 16 zero bytes: a field at MH4U's `+x` is at `+x+16` |

The loader checks the magic and the u16 version, and reads the u16 at `+0x06` as the number of
table entries (256 in every file read). MH4U's loader requires version 4 (`cmp r1, #4` at
`0x0023b878`); version 5 is the same file with every offset field moved by 16 per record.

MH3U registers `rCameraList` (class id `0x39c52040`, `reference/games/mh3u/mt_classes.tsv`) but
its 3DS RomFS holds no file of that class: a scan of all 6,141 files and all 85 monster arcs
finds none (check C1). Its cut-in cameras are `rDemoCamera` resources (`camera/dcm*`, 81 in the
RomFS), which belong to cutscenes, not to a monster. **A 3U port has no source camera to
convert.**

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `LCM\0` | verified | MH4U loader `0x0023b864`; check C1 |
| 0x04 | u16 | version (4 MH4U, 5 MHXX) | verified | MH4U loader `0x0023b874`; check C1 |
| 0x06 | u16 | table entry count: 256 in every file read | verified | MH4U loader `0x0023b884`, which loops over it; check C1 |
| 0x08 | u32 × count | record offset, relative to the start of the file; 0 = this id has no camera. MH4U's loader adds the file's own address to each non-zero word | verified | MH4U loader `0x0023b8a4` to `0x0023b90c`; check C1 |

The records follow the table at `0x408`, one after another in table order, then the data area the
records' offsets point into. Every file read has its records contiguous (`record i` at
`0x408 + i × record size`) and its table count 256.

## Record (0x9c; MHXX adds a 16-byte zero prefix)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 ×4 | zero in every record; meaning unknown | unverified | check C1 |
| +0x10 | u32 | frame count: the camera manager stores `count - 1` as the camera's last frame | verified | MH4U camera manager `0x00c038d8`; check C1 |
| +0x14 | u32 | 0 or 1; a flag, meaning unknown | unverified | check C1 |
| +0x18 | f32 | aspect ratio: 1.77778 (16:9) or 1.66667 (5:3) | unverified | check C1 |
| +0x1c | track | track 0 | verified | [track](#track-0x24) below; MH4U loader `0x0023b8e4`; check C1 |
| +0x40 | track | track 1 | verified | as track 0; check C1 |
| +0x64 | track | track 2 | verified | as track 0; check C1 |
| +0x88 | u32 | fourth block count: 2, 4 or 5 | unverified | check C1 |
| +0x8c | u32 | fourth block key data size, 0 when it has none | unverified | check C1 |
| +0x90 | f32 | unknown; between 18 and 55 in every record read | unverified | check C1 |
| +0x94 | f32 | unknown; 0, 18 or 42 in every record read | unverified | check C1 |
| +0x98 | u32 | fourth block key data offset, relative to the file | verified | MH4U loader `0x0023b988`; check C1 |

The camera manager (`0x00c0376c`, reached from the camera event `0x00934544` with type 4 and the
event's id) takes the record the table's id points at and passes the three tracks to
`0x00ae988c` and the fourth block to `0x00aea8e0`. A table entry of 0, or an id past the count,
does nothing.

## Track (0x24 bytes, at +0x1c, +0x40 and +0x64)

The same structure as an LMT track; the loader relocates the two words marked so.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | buffer type: the keyframe encoding, 1 to 7 and 11 to 15 in the files read | verified | RevilLib `TrackV2BufferTypes`; check C1 |
| +0x01 | u8 | usage (RevilLib's `TrackType_er`): 1 local position on the two position tracks, 0 or 1 elsewhere | verified | RevilLib `bone_track.cpp`; check C1 |
| +0x02 | u8 | joint type; 0 in every track read | verified | RevilLib `bone_track.cpp`; check C1 |
| +0x03 | u8 | bone id; 0 in every track read | verified | RevilLib `bone_track.cpp`; check C1 |
| +0x04 | f32 | weight; 0.0 in every track read | verified | RevilLib `bone_track.cpp`; check C1 |
| +0x08 | u32 | key buffer size: a whole number of keys at the type's stride | verified | RevilLib `codecs.hpp`; check C1 |
| +0x0c | u32 | key buffer offset, relative to the file; **relocated** | verified | MH4U loader `0x0023b948`; check C1 |
| +0x10 | f32 ×4 | reference value; it matches the first key in some tracks and not others, so its use is unknown | unverified | RevilLib `bone_track.hpp`; check C1 |
| +0x20 | u32 | bounds block offset, 0 when there is none; **relocated** | verified | MH4U loader `0x0023b964`; check C1 |

## Bounds block (0x20 bytes)

Two `f32 ×4`, the same block LMT calls `TrackMinMax` and applies the same way: a key's four
components become `offset + scale × value` with the second vector offsetting and the first
scaling.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | f32 ×4 | scale for the key's four components | verified | RevilLib `codecs.cpp` (`additiveLerp`); check C1 |
| +0x10 | f32 ×4 | offset added after scaling | verified | RevilLib `codecs.cpp`; check C1 |

A position track (types 4 and 5) needs its bounds block to turn the normalized keys into
coordinates. A rotation track (types 2 and 6 to 15) is a unit quaternion after the block; the
16-bit bounds keep it so. Check C1 decodes every rotation key of every file and every one is
within 0.03 of unit length.

## Fourth block (0x14 bytes, at +0x88)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | count: 2, 4 or 5 | unverified | check C1 |
| +0x04 | u32 | key data size | unverified | check C1 |
| +0x08 | f32 | unknown | unverified | check C1 |
| +0x0c | f32 | unknown | unverified | check C1 |
| +0x10 | u32 | key data offset, relative to the file; **relocated** | verified | MH4U loader `0x0023b988`; check C1 |

It is passed to a different setter than the three tracks (`0x00aea8e0` against `0x00ae988c`), and
the values at +0x08 and +0x0c look like field-of-view degrees (18, 28, 42, 46, 55), but nothing
read names its fields. The converter copies it and moves only its offset.

## Keyframe buffers

A track's key buffer is a whole number of keys. The frame gap each key stores advances the
frame, the first key is at frame 0, and in every camera track read the gaps sum to the record's
frame count − 1. Types 1 and 2 have no gap field and advance one frame per key.

| Type | Name | Key | Frame gap | Status | Source |
|---|---|---|---|---|---|
| 1 | `SingleVector3` | 12: 3 f32 | none, one frame per key | verified | RevilLib `codecs.cpp`; check C1 |
| 2 | `StepRotationQuat3` | 12: x, y, z f32; w = √(1 − x² − y² − z²) | none, one frame per key | verified | RevilLib `codecs.cpp`; check C1 |
| 3 | `LinearVector3` | 16: 3 f32 | u32 at +0x0c | verified | RevilLib `codecs.cpp`; check C1 |
| 4 | `BiLinearVector3_16bit` | 8: 3 u16, each / 0xFFFF | u16 at +0x06 | verified | RevilLib `codecs.cpp`; check C1 |
| 5 | `BiLinearVector3_8bit` | 4: 3 u8, each / 0xFF | u8 at +0x03 | verified | RevilLib `codecs.cpp`; check C1 |
| 6 | `LinearRotationQuat4_14bit` | 8: u64, 14-bit w, z, y, x at bits 0, 14, 28, 42; a field above 8191.5 is negative, scale 0x3FFF/4 | u8 at +0x07 | verified | RevilLib `codecs.cpp`; [lmt](lmt.md#type-6-linearrotationquat4_14bit-8-bytes); check C1 |
| 7 | `BiLinearRotationQuat4_7bit` | 4: u32, 7-bit w, z, y, x at bits 0, 7, 14, 21, each / 0x7F | 4 bits at +0x03 | verified | RevilLib `codecs.cpp`; [lmt](lmt.md#type-7-bilinearrotationquat4_7bit-4-bytes); check C1 |
| 11 | `BiLinearRotationQuatXW_14bit` | 4: u32, x at bits 0–13, w at 14–27, each / 0x3FFF; y and z come from the bounds block | 4 bits at +0x03 | verified | RevilLib `codecs.cpp`; check C1 |
| 12 | `BiLinearRotationQuatYW_14bit` | as type 11 with y in x's place | 4 bits at +0x03 | verified | RevilLib `codecs.cpp`; check C1 |
| 13 | `BiLinearRotationQuatZW_14bit` | as type 11 with z in x's place | 4 bits at +0x03 | verified | RevilLib `codecs.cpp`; check C1 |
| 14 | `BiLinearRotationQuat4_11bit` | 6: 4 × 11-bit fields at bits 0, 11, 22, 33, stored bit-rotated; each / 0x7FF | 4 bits at +0x05 | verified | RevilLib `codecs.cpp`; check C1 |
| 15 | `BiLinearRotationQuat4_9bit` | 5: 4 × 9-bit fields at bits 0, 9, 18, 27, stored bit-rotated; each / 0x1FF | 4 bits at +0x04 | verified | RevilLib `codecs.cpp`; check C1 |

Types 8 to 10 (`BiLinearRotationQuat*_7bit` variants) are legal LMT types and occur in no camera
list read; the reader refuses them rather than guessing. The bit rotations in types 14 and 15 are
RevilLib's own arithmetic (`Evaluate`), not a simple little-endian split.

## How the record points to it

- **MH4U.** `enemyResourceIndex[id]` is a 0x2c-byte record of eleven path pointers; `+0x08` is
  the camera, one path (`enemy\emNNN\mot\eNNN_cam`), class `rCameraList` ([reference](../reference/README.md#mh4u-monster-tables),
  [mods/monster_ids](../mods/monster_ids/README.md#the-resource-record)). The id in the file's
  table is the **camera event's id**, not the monster id: an action posts camera event N and
  the manager takes record N. The port's `files` kind `camera` makes #143's record builder
  rewrite the path's id token to the ported id.
- **MHXX.** The monster's own archive holds the list under
  `enemy\emNNN\emNNN_VV\mot\emNNN_VV_cam`, class `0x39c52040`; a monster that shares a family's
  motions (MHXX's `em002_00.arc` is one) also carries that family's camera list under the
  family's path, so a converter finds the entry by its class id, not by the path. MHGU
  Definitive Edition's registry names the monster's file manifest's field 11 as the camera
  (`notes/registry.md`), which is MHGU's layout; MHXX's own manifest was not read here.
- **MH3U.** Nothing to point at: the 3U monster archive holds one ARC of the monster's files and
  no `rCameraList` entry (check C1). Its cutscene cameras are `rDemoCamera` files shared by
  quests.

## What a converter must produce

`mhuc convert camera SOURCE.lcm --from mhxx -o OUT.lcm` takes the source monster's camera list
and writes version 4 for MH4U:

1. version 4; keep the u16 count (256) and the source's camera ids and records;
2. drop each record's 16-byte zero prefix, so every record is 0x9c bytes;
3. re-lay the records contiguously from 0x408, in the order their table offsets had;
4. subtract 16 × the record count from each of the seven fields MH4U's loader relocates
   (`+0x28`, `+0x3c`, `+0x4c`, `+0x60`, `+0x70`, `+0x84`, `+0x98`), skipping a 0;
5. copy the data area after the records unchanged: the key buffers and bounds blocks are
   already what MH4U's codecs read, and only their offsets moved.

`camera.to_mhxx` is the exact inverse (the check round-trips every MHXX file through it). The
source's camera ids stay: a ported monster's handlers post the source's event ids, so the ids
must not be renumbered. The port's own converter (`mhuc convert monster`, #48's) calls
`camera.from_mhxx` on the camera entry in the MHXX monster archive and places the result at
`enemy\emNNN\mot\eNNN_cam`, for a row whose `files` lists `camera`; 124 is the first (issue
#157).

The two Rathians' lists show what staying by id means: they share ids 0, 1, 2, 4, 5 and 8,
MH4U's own has 9, 10 and 12 to 20 as well, and MHXX's has 40 to 44 and 50 to 53. A port that runs
MH4U's shared handlers posts MH4U's event ids, so an id the port's list lacks does nothing
(check C1; the wiring is #48's). A 3U port cannot convert a camera at all, because the source
has none; it keeps MH4U's stand-in camera (its record's path is the stand-in's) or would need
one authored, which is content work and not a conversion.

## Checks

- **C1 (done, MH4U USA v1.3.0 and MHXX JPN v1.0 RomFS, and MH3U USA RomFS):** `mhuc survey`
  reads every `rCameraList` resource in a RomFS and runs `camera.check` on it. MH4U: all 295
  resources read (179 distinct files); 123 of the `data/emNNN.arc` monster arcs hold 86 of them
  (id 0 has no arc), 32 distinct lists with 441 cameras and 1,323 tracks. MHXX: all 125 resources read (80
  distinct); 93 of the 137 `arc/enemy/*.arc` hold one, 57 distinct lists with 591 cameras and
  1,773 tracks. MH3U: 0 resources in the whole RomFS (6,141 files, 85 monster arcs). In every
  file: the count is 256, the records are contiguous from 0x408, MHXX's 16-byte prefixes are
  zero, every key buffer is a whole number of keys at its type's stride, every gapped track's
  gaps sum to frame count − 1, and every rotation key is a unit quaternion within 0.03 after its
  bounds block. `camera.to_mhxx(camera.from_mhxx(file)) == file` for every MHXX file; running
  the version 5 to 4 conversion and reading it back holds the same invariants.
- **C2 (open, in game):** the ported Rathian's cut-in camera plays. `mhuc convert monster`
  writes a ported id's own camera into its arc for a row that lists `camera` (124 does, and
  the game_files test checks the entry against MHXX's own list). Spawn the id in a quest and
  force an action whose handler posts a camera event (the handler's `bl 0x00934544` names the
  id): the view frames the monster with the source game's camera, not MH4U Rathian's.
  Procedure in [docs/checks.md](../docs/checks.md#a-ported-cameras-cut-in-c2); needs #144's
  quest-load proof and a run in the game.
