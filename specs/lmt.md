---
class: rMotionList
extension: lmt
games: MH4U, MHXX and MHGU (version 67, check L1); MH3U (version 66, the same layout, check L3)
status: unknown
---

# LMT: motion list (animations)

A list of animations for one skeleton: per animation, tracks (one per bone and channel) pointing at keyframe buffers, optional bounds, and an event block. MH3U's underwater motions and every converted monster's moves are LMT files, so this format sits under both the underwater work (docs/architecture.md#underwater) and monster conversion.

**Source.** Scrimas's MHGU Definitive Edition (GPL-3.0-or-later), `tools/lmt.py`, which copies animations between MH4U and MHGU LMT files and states the layout as read off MH4U's em022 and em092 and MHGU's em067_00 (version 67 in both). Offsets are relative to the file (the game relocates them at load). PredatorCZ's [RevilLib](https://github.com/PredatorCZ/RevilLib) (GPL-3.0) states the layout of each version in `src/mtf_lmt/*.inl`: its animation layout covers LMT 66 to 68, its bone track 56 to 67, its event block 56 to 68, and its events and float tracks 22 to 95, so **version 66 and 67 share every structure**; check L3 read all 387 MH3U lists that way. The [Float-track block](#float-track-block-0x38) is RevilLib's `float_track.inl` and `float_track.hpp`. Each game's loader is read from its `code.bin` ([Versions](#versions)). RevilLib also names the fields MHGU-DE leaves unknown (the animation's flags, scene position and rotation, and float-track block, the track's reference data and bounds, the track type and buffer-type enums) and gives the keyframe encodings in `codecs.hpp` and the per-version buffer-type registry in `bone_track.cpp`, which the [Keyframe buffers](#keyframe-buffers) section below lays out. Check L1 read every MH4U and MHXX motion list; check L4 then decoded every keyframe buffer of the three games. The rows those checks reach are marked verified. Reader: `src/mhuc/lmt.py`.

## Versions

| Version | Games | Layout |
|---|---|---|
| 66 | MH3U | the layout below; read on all 387 MH3U lists (check L3) |
| 67 | MH4U, MHXX, MHGU | the layout below; read on every MH4U and MHXX list (check L1) |

Every field's offset, size and meaning is the same in RevilLib's per-version layouts, and one reader covers both versions. What differs between the builds is the keyframe encoding of buffer types 11 to 13 (signed in 66, unsigned behind a bounds block in 67; [Keyframe buffers](#keyframe-buffers)) and where each build keeps those types' bounds.

**What the number selects in the engine.** Nothing in the data's shape: each build has one motion-list loader, and the version is a check, not a switch.

- MH4U USA v1.3.0: `rMotionList`'s loader at `0x0023e508` (the fork's function table) reads the magic through the build's `LMT\0` constant at `0x0023e724` and requires `version == 67` (`ldrh r1,[r0,#4]` then `cmp r1,#0x43`, `0x0023e588`).
- MH3U USA: the same function at `0x00256304`, constant `0x00256510`, requires `version == 66` (`cmp r1,#0x42`, `0x00256388`).
- MHXX v1.4: the same function at `0x0024dadc`, constant `0x0024dcf0`, requires `version == 67` (`cmp r1,#0x43`, `0x0024db5c`).

Any other version, or another magic, makes the loader return 0 without relocating anything; neither function branches on the version. Both loaders relocate the same pointers: each animation offset (header +0x08), and per animation the track table (+0x00), each track's keyframe buffer (+0x0C), the bounds pointer (+0x20) where the build keeps one, the event block (+0x34) and its four groups' event lists (+0x44, +0x8c, +0xd4 and +0x11c). Two animation flags tell it not to: bit 0x1000000 skips the track block and 0x2000000 the event lists. The first is the shared-motion case: every MHXX motion with the bit set (702) shares its track table with a motion that lacks it, so the buffers and bounds were relocated once already, and no two motions without the bit share one (check L5); 0x2000000 is set on none. Neither loader reads the animation's +0x38 or the four bytes at +0x3C.

The bounds rule is not selected by the version either: MH4U's loader relocates +0x20 only for buffer types 4, 5, 7 and 11 to 13 (its switch over the buffer type; no track of type 1, 2, 3 or 6 has a bounds block there, check L4), while MH3U's relocates it for every type except 11 to 13 and, for those three, writes the address of the track's own reference data (+0x10) instead of a file offset (no MH3U type 11 to 13 track has a bounds block, check L4). The build's motion code, not the header, decides how a version's files are handled; the number says which build's motion code the file was written for.

**Consequence for a converter.** Writing version 67 is necessary and sufficient for MH4U's loader to take an MH3U-format file; it is not sufficient for the motion to play as MH3U's, because types 11 to 13's keys must be re-encoded into version 67's form ([Keyframe buffers](#keyframe-buffers)). The rebuild is [Converting a version 66 list to version 67](#converting-a-version-66-list-to-version-67). A type 6 track with a bounds block (2,991 in MH3U, none in MH4U) would load with its +0x20 left as a file offset; what MH4U does with it is unverified.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `LMT\0` | verified | MHGU-DE `lmt.py`; RevilLib `serialize.cpp`; check L1, L3 |
| 0x04 | u16 | version (66 in MH3U; 67 in MH4U, MHXX and MHGU) | verified | MHGU-DE `lmt.py`; RevilLib `lmt.inl`; check L1, L3 |
| 0x06 | u16 | animation count | verified | MHGU-DE `lmt.py`; RevilLib `serialize.cpp`; check L1, L3 |
| 0x08 | u32 × count | animation offsets (0 = empty slot) | verified | MHGU-DE `lmt.py`; RevilLib `serialize.cpp`; check L1, L3 |

## Animation (0x3C bytes of fields, 16-byte aligned to 0x40)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | track table offset | verified | MHGU-DE `lmt.py`; RevilLib `animation.inl`; check L1, L3 |
| +0x04 | u32 | track count | verified | MHGU-DE `lmt.py`; RevilLib `animation.inl`; check L1, L3 |
| +0x08 | s32 | frame count (RevilLib's `numFrames`) | unverified | MHGU-DE `lmt.py`; RevilLib `animation.inl` |
| +0x0C | s32 | loop frame (RevilLib's `loopFrame`): -1, 0 or a frame | unverified | MHGU-DE `lmt.py`; RevilLib `animation.inl` |
| +0x10 | f32 ×4 | end-of-animation scene position (RevilLib's `endFrameAdditiveScenePosition`) | unverified | RevilLib `animation.inl` |
| +0x20 | f32 ×4 | end-of-animation scene rotation, a quaternion (RevilLib's `endFrameAdditiveSceneRotation`) | unverified | RevilLib `animation.inl` |
| +0x30 | u32 | flags: 0x800000 is set exactly when +0x34 is non-zero (every animation read in all three games) and 0x40000 is set on none (RevilLib names it float tracks). 0x1000000, which RevilLib leaves unnamed, marks a motion that shares its track table with an earlier one that lacks the bit: 702 MHXX animations, and the loader then skips relocating the shared buffers and bounds; 0x2000000 makes the loader skip the event lists and is set on none. 0x1 (RevilLib's `Unk01`) occurs on 685 MHXX motions, meaning unknown. MH4U's and MH3U's animations all carry 0x00800000 | verified | RevilLib `animation.cpp`; the loaders ([Versions](#versions)); check L1, L3, L5 |
| +0x34 | u32 | event block offset (0 none) | verified | MHGU-DE `lmt.py`; RevilLib `animation.cpp`; check L1, L3 |
| +0x38 | u32 | float-track block offset (0 none); 0 in every animation (check L5), so the [block](#float-track-block-0x38) it names is RevilLib's alone | unverified | RevilLib `float_track.inl`; check L5 |
| +0x3C | — | not a field: the animation's fields end at +0x38, these four bytes are 0 in every animation whose header is not its list's highest, and when one is non-zero it belongs to the list's highest-offset header, where the next block starts (check L5) | verified | check L5; RevilLib `animation.inl` gives the 32-bit class 0x40 bytes with no member there |

## Track (0x24 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | buffer type (the keyframe encoding): 3 to 7 and 11 to 13 on every track that carries a buffer; 1 and 2 occur too, but only on tracks without one. RevilLib's registry for versions 56 and up names them; the [Keyframe buffers](#keyframe-buffers) section lays each out | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.cpp`; check L1, L3, L4 |
| +0x01 | u8 | usage (track type): 0 and 3 on rotation-buffer tracks, 1, 2, 4 and 5 on vector3-buffer tracks. RevilLib names 0 local rotation, 1 local position, 2 local scale, 3 absolute rotation and 4 absolute position, and has no 5 | verified | RevilLib `bone_track.cpp` (`TrackType_er`); check L2, L3 |
| +0x02 | u8 | joint type (RevilLib's `BoneType`): 0 in every track read | unverified | MHGU-DE `lmt.py`; RevilLib `bone_track.hpp`; check L1, L3 |
| +0x03 | u8 | bone id: the id in the model's bone table, not its index; 255 on the root track | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.cpp`; check L2 |
| +0x04 | f32 | weight: 1.0 in every track read | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.inl`; check L1, L3 |
| +0x08 | u32 | buffer size: 0 when the track has no keyframes, else a whole number of keys at its type's stride (RevilLib `codecs.hpp`) | verified | MHGU-DE `lmt.py`; RevilLib `codecs.hpp`; check L1, L3 |
| +0x0C | u32 | buffer offset | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.inl`; check L1, L3 |
| +0x10 | f32 ×4 | reference data (RevilLib's `referenceData`) | unverified | RevilLib `bone_track.hpp` |
| +0x20 | u32 | bounds offset (0x20 bytes; 0 none) | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.inl`; check L1, L3 |

The bounds block is two `f32 ×4` (RevilLib's `TrackMinMax`), which RevilLib applies to a key as offset + scale × value: the second vector offsets and the first scales, so the pair isn't a min and a max and the first vector is often the larger one. Check L4 confirms that order on the rotation types whose keys must be unit quaternions after it (type 7, and types 11 to 13 in version 67). Whether the engine applies it to type 6 as well is unverified: 2,991 MH3U tracks carry one.

## Keyframe buffers

A track with a non-zero buffer size points at its keys, and every buffer type here packs one key in a fixed number of bytes, so the buffer size is a whole number of keys; the reader refuses a buffer it can't split. Keys are read in order and their frames accumulate: the first key is at frame 0, and each next key's frame is the previous key's frame plus that key's frame gap. Types 1 and 2 carry no gap field, so their keys are one frame apart. In every animation read, the last key is at frame count − 1 (the animation's +0x08), and a key at or past the frame count is an error (check L4).

The components a key decodes to are its buffer's own values, four of them (x, y, z, w): a rotation type's are the quaternion, and a position type's are (x, y, z, 1). Where the track has a bounds block the engine applies it on top ([Track](#track-0x24-bytes) above), and for the compressed types that block is what turns the normalized components into the real values.

Offsets are from the start of a key.

### Type 3: `LinearVector3`, 16 bytes

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | f32 × 3 | x, y, z | verified | RevilLib `codecs.hpp` (`Buf_LinearVector3`); check L4 |
| 0x0C | u32 | frame gap to the next key | verified | RevilLib `codecs.hpp`; check L4 |

### Type 4: `BiLinearVector3_16bit`, 8 bytes

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u16 × 3 | x, y, z, each divided by 0xFFFF | verified | RevilLib `codecs.hpp` (`Buf_BiLinearVector3_16bit`); check L4 |
| 0x06 | u16 | frame gap | verified | RevilLib `codecs.hpp`; check L4 |

### Type 5: `BiLinearVector3_8bit`, 4 bytes

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u8 × 3 | x, y, z, each divided by 0xFF | verified | RevilLib `codecs.hpp` (`Buf_BiLinearVector3_8bit`); check L4 |
| 0x03 | u8 | frame gap | verified | RevilLib `codecs.hpp`; check L4 |

### Type 6: `LinearRotationQuat4_14bit`, 8 bytes

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u64 | bits 0–13 w, 14–27 z, 28–41 y, 42–55 x; each field's upper half is negative (a value above 8191.5 means the field minus 16383), and the scale is 0x3FFF / 4 = 4095.75, so a component spans −2 to 2 | verified | RevilLib `codecs.hpp` (`Buf_LinearRotationQuat4_14bit`); check L4 |
| 0x07 | u8 | frame gap (bits 56–63) | verified | RevilLib `codecs.hpp`; check L4 |

The game's components stay within −1 to 1: every key is a unit quaternion to within 0.00048 before any bounds ([check L4](#checks)).

### Type 7: `BiLinearRotationQuat4_7bit`, 4 bytes

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | bits 0–6 w, 7–13 z, 14–20 y, 21–27 x; each divided by 0x7F | verified | RevilLib `codecs.hpp` (`Buf_BiLinearRotationQuat4_7bit`); check L4 |
| 0x03 | u8 | frame gap (bits 28–31) | verified | RevilLib `codecs.hpp`; check L4 |

The components are unsigned magnitudes and every type 7 track carries a bounds block, which supplies their signs and scales. After it a key is a quaternion within 0.13 of unit (mean 0.003 to 0.006; about 2% of keys are more than 0.02 off, the 7-bit field being coarse, and a quaternion defines the same rotation at any length).

### Types 11 to 13: `BiLinearRotationQuat{X,Y,Z}W_14bit`, 4 bytes

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | bits 0–13 the named axis component (x for 11, y for 12, z for 13), 14–27 w | verified | RevilLib `codecs.hpp` (`Buf_BiLinearRotationQuatXW_14bit` and its YW and ZW variants); check L4 |
| 0x03 | u8 | frame gap (bits 28–31) | verified | RevilLib `codecs.hpp`; check L4 |

The two components are encoded differently in the two versions:

- **Version 67 (MH4U, MHXX):** unsigned, each divided by 0x3FFF. Every track carries a bounds block, which supplies the sign and scale; after it a key is a unit quaternion to within 0.00851 (check L4).
- **Version 66 (MH3U):** as type 6 does it, the upper half of each 14-bit field negative and the scale 4095.75. No type 11 to 13 track in MH3U carries a bounds block, and the value is already a quaternion: 2,369,015 of 2,373,039 keys are unit to within 0.01 (check L4).

What the version change was for is unknown. RevilLib's registry gives all versions from 56 up the same codecs, so its reading is version 67's; MH3U's files only decode under the signed reading.

### Converting a version 66 list to version 67

Nothing else differs, so `mhuc.formats.lmt.convert` copies every block and re-encodes the keyframe buffers of types 11 to 13 only: a component v in −1 to 1 becomes the unsigned field round((v + 1) × 0x3FFF / 2) in 0 to 0x3FFF (a value outside −1 to 1 clamps), and the track gains a bounds block with scale 2 and offset −1 on the two components it stores, the other two left 0. The version-67 reading, offset + scale × value, gives v back within 6.11e-5, half the unsigned field's step, so a converted list decodes to the source's keys. The frame gaps, the animation headers and event blocks, and every other track's bytes stay the source's.

### Types 1 and 2: `SingleVector3` and `StepRotationQuat3` (no keys in any file)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | f32 × 3 | type 1: x, y, z. Type 2: x, y, z with w = sqrt(1 − x² − y² − z²), and 0 when that isn't positive | unverified | RevilLib `codecs.hpp` (`Buf_SingleVector3`, `Buf_StepRotationQuat3`) |
| none | — | frame: one apart, no gap field | unverified | RevilLib `codecs.hpp` |

No type 1 or type 2 track in the three games carries a keyframe buffer: all 128,784 of MH4U's, 108,611 of MHXX's and 39,278 of MH3U's type 1 and type 2 tracks have buffer size 0 (check L4). The layout above is RevilLib's alone, and `mhuc` decodes it, but no real key of either type exists to check it against.

Types 8, 9 and 10 have no codec in RevilLib's registry for version 56 and up, and types 14 (`BiLinearRotationQuat4_11bit`, 6 bytes) and 15 (`BiLinearRotationQuat4_9bit`, 5 bytes) occur in none of the three games; `mhuc` doesn't decode them and raises instead.

## Event block (4 groups × 0x48 bytes)

Four groups per animation in versions 56 and up (RevilLib's `AnimationEvent` layout).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 ×32 | remap | unverified | MHGU-DE `lmt.py`; RevilLib `event.inl` |
| +0x40 | u32 | event count | verified | MHGU-DE `lmt.py`; RevilLib `event.inl`; check L1, L3 |
| +0x44 | u32 | offset of count × {u32 bits, u32 frames} | verified | MHGU-DE `lmt.py`; RevilLib `event.hpp`; check L1, L3 |

## Float-track block (+0x38)

RevilLib's float tracks: the animation's +0x38 offsets four groups (RevilLib's `FloatTracks`), each naming its own keyframe array. No motion list in any of the three games has one: the field is 0 in all 52,902 animations (check L5), and neither MH4U's nor MH3U's loader relocates it (it stops at the event block, [Versions](#versions)). So the block's offsets are read relative to the file as RevilLib does, `mhuc` reads it ([`read_float_tracks`](../src/mhuc/formats/lmt.py)), and every field below is RevilLib's alone.

### Float-track groups (0x30 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00, +0x0C, +0x18, +0x24 | `FloatTrack` ×4 | the animation's four groups, 0x0C bytes each (below) | unverified | RevilLib `float_track.inl` (`FloatTracks`) |

### FloatTrack (0x0C bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 ×4 | component remap, one per value component (RevilLib's `FloatTrackComponentRemap`: 0 none, 1 x, 2 y, 3 z) | unverified | RevilLib `float_track.inl`, `float_track.hpp` |
| +0x04 | u32 | key count (RevilLib's `numFloats`) | unverified | RevilLib `float_track.inl` |
| +0x08 | u32 | keyframe array offset (0 none), relative to the file | unverified | RevilLib `float_track.cpp` (`FramesPtr().Fixup`) |

### Float key (0x10 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | bits 0–7 the number of components the key sets, 8–23 the frame, 24–31 RevilLib's pad `0xCD` | unverified | RevilLib `float_track.hpp` (`FloatFrame`) |
| +0x04 | f32 ×3 | the three floats | unverified | RevilLib `float_track.hpp` |

RevilLib reads the key count from a group and then that many 0x10-byte keys from its array offset (`FloatTracksMidInterface::GetFrames`), fixing both the +0x38 offset and each group's array offset up as file-relative pointers. The animation's flag bit 0x40000, RevilLib's `FLoatTracks`, is clear in every animation of the three games (check L5), as is +0x38, so no flag or field in these games would ask for the block.

## Checks

- **L1 (done):** `mhuc survey` on each RomFS (section `lmt`).
  - MH4U: 1,466 motion lists, all version 67, all readable (every animation, track table, keyframe buffer, bounds block and event block inside its file): 23,412 animations, 25,633 empty slots, 732,404 tracks, buffer types 1–7 and 11–13. Every animation has an event block.
  - MHXX JPN: 988, all version 67, all readable: 21,154 animations, 57,010 empty slots, 677,909 tracks, the same buffer types (type 3 three times). So MHXX motions are MH4U's format: a GU monster's LMT can be read, and probably loaded, as it is.
  - MH3U USA: 387, all **version 66**. The reader now takes them, because RevilLib puts 66 and 67 in one layout; check L3 is their read.
  - Not reached: the meaning of the fields marked unverified (frame counts, loop frames, reference data, the scene position and rotation, the bounds block's two vectors). The keyframe buffers are check L4; +0x38 and +0x3C are check L5.
- **L2 (done):** a track's bone field is a bone id, not an index.
  - MH4U's em001 model has 43 bones whose ids run to 202 with gaps, and its five motion lists carry ids from 60 to 145, which no 43-entry list could index. The player lists say the same: the common and per-weapon lists carry exactly the hunter body's ids (0 to 12 and 14 to 19) and never 13.
  - MH3U's 50 player motion lists, read as version 66, carry ids 0 to 21 and the root's 255: rotation tracks on 1 to 21 (one list also gives id 0 a rotation track with no keyframes) and a translation track on 0, with 20 and 21 never keyframed. That part reads the tracks; the keyframe buffers are check L4.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k address_bones_by_id`, for MH4U and MH3U.
- **L3 (done, version 66):** every MH3U motion list reads as version 66.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k mh3u_motion_lists_read` (the read, the counts and the tracks' fields); `mhuc survey <ROMFS> --workers 1` (section `lmt`) for the version count.
  - Result: 387 motion lists, all version 66, all readable (every animation, track table, keyframe buffer, bounds block and event block inside its file): 15,594 slots, 8,336 animations, 7,258 empty slots, 270,420 tracks, buffer types 1–7 and 11–13, with 1 and 2 only on keyless tracks (check L4). Every track weighs 1.0; 231,142 tracks have a keyframe buffer, whose size is a whole number of keys at its type's stride, and 51,794 have a bounds block. Every animation has flags 0x00800000 and a non-zero event block offset. The track types (usage) come out 237,990 of 0, 75 of 3, and 13,286, 10,696, 8,300 and 73 of 1, 2, 4 and 5.
  - Not reached: why version 66 encodes buffer types 11 to 13 differently (check L4), and why MH3U's loader points those tracks' bounds at their reference data ([Versions](#versions)). The number itself is a loader gate, not a layout switch ([Versions](#versions)). The float-track block and +0x3C are check L5.

- **L4 (done):** every keyframe buffer of the three games decodes.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k motion_keyframe`.
  - Read all 2,841 motion lists (1,466 MH4U, 988 MHXX, 387 MH3U), 52,902 animations and 1,680,733 tracks. 1,404,060 tracks carry a keyframe buffer, holding 90,536,863 keys (40,672,238 MH4U, 33,075,719 MHXX, 16,788,906 MH3U). Every buffer is a whole number of keys of its type; every animation's keys start at frame 0 and end at its frame count − 1, with every frame gap positive; every value is finite.
  - Tracks with a buffer, by buffer type:

    | Game | 3 | 4 | 5 | 6 | 7 | 11 | 12 | 13 |
    |---|---|---|---|---|---|---|---|---|
    | MH4U | 641 | 24,613 | 12,999 | 362,290 | 110,522 | 66,482 | 19,469 | 6,604 |
    | MHXX | 3 | 21,593 | 13,735 | 321,115 | 113,725 | 71,569 | 20,887 | 6,671 |
    | MH3U | 214 | 10,000 | 6,470 | 143,814 | 32,333 | 26,368 | 11,310 | 633 |

  - No type 1 or type 2 track carries a buffer: 128,784 such tracks in MH4U, 108,611 in MHXX and 39,278 in MH3U. Every track of types 3 to 7 and 11 to 13 has one.
  - Bounds blocks: every type 4, 5, 7, 11, 12 and 13 track has one in MH4U and MHXX, and so does every type 4, 5 and 7 track in MH3U; MH3U's types 11 to 13 have none, type 3 never has one, and type 6 has one on 2,991 MH3U tracks and none elsewhere.
  - The quaternion types: type 6's keys are unit to within 0.00048 before any bounds; type 7's, after its bounds block, within 0.13 (mean 0.003 to 0.006, the field being 7-bit); version 67's types 11 to 13, after their bounds block, within 0.00851 (mean 0.00009); version 66's types 11 to 13, under the signed-magnitude reading and with no bounds, are unit to within 0.01 for 2,369,015 of their 2,373,039 keys (type 11: 1,628,374; type 12: 718,846; type 13: 21,795).
  - Not reached: why version 66 and 67 encode types 11 to 13 differently; why the type 7 keys more than 0.02 from unit are so (the field is 7-bit), and why about 4,000 version 66 type 11 to 13 keys are more than 0.01 from unit; whether the engine applies a bounds block to type 6; types 1 and 2 (no real key exists), 14 and 15 (no file).

- **L5 (done):** the float-track block is unused in the three games, and the animation's fields end at +0x38.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k float_track` (reads every motion list of the three games); `mhuc survey <ROMFS> --workers 1` reports the same facts as the counters `L5 float-track blocks`, `L5 animations with the float-track flag` and `L5 padding at +0x3C non-zero`.
  - Result: in all 2,841 motion lists and 52,902 animations (23,412 MH4U, 21,154 MHXX, 8,336 MH3U), no animation has a float-track block (+0x38 is 0 in every one) and none sets flag 0x40000.
  - The word at +0x3C is non-zero in 1,466 MH4U animations (one in each of its 1,466 lists), 972 MHXX and 383 MH3U, and each is its list's highest-offset animation; in each, offset + 0x3C is the start of a block the list names (a track table, keyframe buffer, bounds block, event block or event list), so the word is that block's first four bytes. Every other animation has 0 there.
  - The flags the loaders read: 0x40000 and 0x2000000 are set on no animation. Bit 0x1000000 is set on 702 MHXX animations only; each shares its track table with an earlier animation without the bit, and no track table is shared by two animations without it (525 MHXX tables are shared, none in MH4U or MH3U). The animations' flag words are 0x00800000 in MH4U (23,412) and MH3U (8,336), and 0x00800000 (19,767), 0x00800001 (685) or 0x01800000 (702) in MHXX; the meaning of bit 0x1 is unverified.
  - Not reached: the meaning of the float-track block's fields, since no file exercises them (all unverified, [above](#float-track-block-0x38)); what bit 0x1 means.

- **L6 (done):** every MH3U motion list converts to version 67 and decodes to the same keys.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k motion_list_converts`.
  - Result: all 387 lists (384 in ARCs, 3 loose files) rebuilt as version 67. The 8,336 animations and 270,420 tracks keep their frame and loop counts, flags and events, their type, usage, joint type, bone and key frames, and every key its components within 6.11e-5. 38,311 tracks of types 11 to 13 were re-encoded (26,368 type 11, 11,309 type 12 and 633 type 13 in the ARCs, and one more in a loose list), each gaining a 0x20-byte bounds block: the 384 archive lists grow 0.87%, from 135,366,776 to 136,543,444 bytes.
  - Not reached: whether the game plays a re-encoded track exactly as the source game played the version-66 one; it reads the version-67 form, and the in-game check is [A1](../docs/checks.md#a-ported-monsters-files).
