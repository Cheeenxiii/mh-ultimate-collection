---
class: rMotionList
extension: lmt
games: MH4U, MHXX and MHGU (version 67, check L1); MH3U (version 66, the same layout, check L3)
status: unknown
---

# LMT: motion list (animations)

A list of animations for one skeleton: per animation, tracks (one per bone and channel) pointing at keyframe buffers, optional bounds, and an event block. MH3U's underwater motions and every converted monster's moves are LMT files, so this format sits under both the underwater work (docs/architecture.md#underwater) and monster conversion.

**Source.** Scrimas's MHGU Definitive Edition (GPL-3.0-or-later), `tools/lmt.py`, which copies animations between MH4U and MHGU LMT files and states the layout as read off MH4U's em022 and em092 and MHGU's em067_00 (version 67 in both). Offsets are relative to the file (the game relocates them at load). PredatorCZ's [RevilLib](https://github.com/PredatorCZ/RevilLib) (GPL-3.0) states the layout of each version in `src/mtf_lmt/*.inl`: its animation layout covers LMT 66 to 68, its bone track 56 to 67, its event block 56 to 68, and its events and float tracks 22 to 95, so **version 66 and 67 share every structure**; check L3 read all 387 MH3U lists that way. RevilLib also names the fields MHGU-DE leaves unknown (the animation's flags, scene position and rotation, and float-track block, the track's reference data and bounds, the track type and buffer-type enums) and gives the keyframe encodings in `codecs.hpp`, which this spec doesn't lay out. Check L1 read every MH4U and MHXX motion list; the rows it reaches are marked verified. Reader: `src/mhuc/lmt.py`.

## Versions

| Version | Games | Layout |
|---|---|---|
| 66 | MH3U | the layout below; read on all 387 MH3U lists (check L3) |
| 67 | MH4U, MHXX, MHGU | the layout below; read on every MH4U and MHXX list (check L1) |

The version number is the only thing that differs between 66 and 67 as far as these structures go: every field's offset, size and meaning is the same in RevilLib's per-version layouts, and one reader covers them all. What may differ is a keyframe buffer's encoding, which goes by buffer type and isn't decoded here.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `LMT\0` | verified | MHGU-DE `lmt.py`; RevilLib `serialize.cpp`; check L1, L3 |
| 0x04 | u16 | version (66 in MH3U; 67 in MH4U, MHXX and MHGU) | verified | MHGU-DE `lmt.py`; RevilLib `lmt.inl`; check L1, L3 |
| 0x06 | u16 | animation count | verified | MHGU-DE `lmt.py`; RevilLib `serialize.cpp`; check L1, L3 |
| 0x08 | u32 × count | animation offsets (0 = empty slot) | verified | MHGU-DE `lmt.py`; RevilLib `serialize.cpp`; check L1, L3 |

## Animation (0x40 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | track table offset | verified | MHGU-DE `lmt.py`; RevilLib `animation.inl`; check L1, L3 |
| +0x04 | u32 | track count | verified | MHGU-DE `lmt.py`; RevilLib `animation.inl`; check L1, L3 |
| +0x08 | s32 | frame count (RevilLib's `numFrames`) | unverified | MHGU-DE `lmt.py`; RevilLib `animation.inl` |
| +0x0C | s32 | loop frame (RevilLib's `loopFrame`): -1, 0 or a frame | unverified | MHGU-DE `lmt.py`; RevilLib `animation.inl` |
| +0x10 | f32 ×4 | end-of-animation scene position (RevilLib's `endFrameAdditiveScenePosition`) | unverified | RevilLib `animation.inl` |
| +0x20 | f32 ×4 | end-of-animation scene rotation, a quaternion (RevilLib's `endFrameAdditiveSceneRotation`) | unverified | RevilLib `animation.inl` |
| +0x30 | u32 | flags: bit 0x800000 is set exactly when +0x34 is non-zero (every animation read in all three games); RevilLib names 0x40000 float tracks, and 0x1000000 and 0x1 not at all | verified | RevilLib `animation.cpp`; check L1, L3 |
| +0x34 | u32 | event block offset (0 none) | verified | MHGU-DE `lmt.py`; RevilLib `animation.cpp`; check L1, L3 |
| +0x38 | u32 | float-track block offset (0 none) | unverified | RevilLib `float_track.inl` |
| +0x3C | u32 | unknown; RevilLib's layout has no field there | unknown | ours |

## Track (0x24 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | buffer type (the keyframe encoding): 1 to 7 and 11 to 13 in MH3U; 1 to 7 and 11 to 13 in MH4U and MHXX. RevilLib's enum for versions 56 and up names them | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.cpp`; check L1, L3 |
| +0x01 | u8 | usage (track type): 0 and 3 on rotation-buffer tracks, 1, 2, 4 and 5 on vector3-buffer tracks. RevilLib names 0 local rotation, 1 local position, 2 local scale, 3 absolute rotation and 4 absolute position, and has no 5 | verified | RevilLib `bone_track.cpp` (`TrackType_er`); check L2, L3 |
| +0x02 | u8 | joint type (RevilLib's `BoneType`): 0 in every track read | unverified | MHGU-DE `lmt.py`; RevilLib `bone_track.hpp`; check L1, L3 |
| +0x03 | u8 | bone id: the id in the model's bone table, not its index; 255 on the root track | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.cpp`; check L2 |
| +0x04 | f32 | weight: 1.0 in every track read | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.inl`; check L1, L3 |
| +0x08 | u32 | buffer size: 0 when the track has no keyframes, else a whole number of keys at its type's stride (RevilLib `codecs.hpp`) | verified | MHGU-DE `lmt.py`; RevilLib `codecs.hpp`; check L1, L3 |
| +0x0C | u32 | buffer offset | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.inl`; check L1, L3 |
| +0x10 | f32 ×4 | reference data (RevilLib's `referenceData`) | unverified | RevilLib `bone_track.hpp` |
| +0x20 | u32 | bounds offset (0x20 bytes; 0 none) | verified | MHGU-DE `lmt.py`; RevilLib `bone_track.inl`; check L1, L3 |

The bounds block is two `f32 ×4` (RevilLib's `TrackMinMax`), which RevilLib applies as offset + scale × value: the pair isn't a min and a max, so the first vector is often the larger one. The meaning of either is unverified.

## Event block (4 groups × 0x48 bytes)

Four groups per animation in versions 56 and up (RevilLib's `AnimationEvent` layout).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 ×32 | remap | unverified | MHGU-DE `lmt.py`; RevilLib `event.inl` |
| +0x40 | u32 | event count | verified | MHGU-DE `lmt.py`; RevilLib `event.inl`; check L1, L3 |
| +0x44 | u32 | offset of count × {u32 bits, u32 frames} | verified | MHGU-DE `lmt.py`; RevilLib `event.hpp`; check L1, L3 |

## Checks

- **L1 (done):** `mhuc survey` on each RomFS (section `lmt`).
  - MH4U: 1,466 motion lists, all version 67, all readable (every animation, track table, keyframe buffer, bounds block and event block inside its file): 23,412 animations, 25,633 empty slots, 732,404 tracks, buffer types 1–7 and 11–13. Every animation has an event block.
  - MHXX JPN: 988, all version 67, all readable: 21,154 animations, 57,010 empty slots, 677,909 tracks, the same buffer types (type 3 three times). So MHXX motions are MH4U's format: a GU monster's LMT can be read, and probably loaded, as it is.
  - MH3U USA: 387, all **version 66**. The reader now takes them, because RevilLib puts 66 and 67 in one layout; check L3 is their read.
  - Not reached: the meaning of the fields marked unverified (frame counts, loop frames, reference data, the scene position and rotation, the tail at +0x3C, the bounds block's two vectors) and the keyframe encodings.
- **L2 (done):** a track's bone field is a bone id, not an index.
  - MH4U's em001 model has 43 bones whose ids run to 202 with gaps, and its five motion lists carry ids from 60 to 145, which no 43-entry list could index. The player lists say the same: the common and per-weapon lists carry exactly the hunter body's ids (0 to 12 and 14 to 19) and never 13.
  - MH3U's 50 player motion lists, read as version 66, carry ids 0 to 21 and the root's 255: rotation tracks on 1 to 21 (one list also gives id 0 a rotation track with no keyframes) and a translation track on 0, with 20 and 21 never keyframed. That part reads the tracks only: the keyframe buffers aren't decoded.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k address_bones_by_id`, for MH4U and MH3U.
- **L3 (done, version 66):** every MH3U motion list reads as version 66.
  - Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k mh3u_motion_lists_read` (the read, the counts and the tracks' fields); `mhuc survey <ROMFS> --workers 1` (section `lmt`) for the version count.
  - Result: 387 motion lists, all version 66, all readable (every animation, track table, keyframe buffer, bounds block and event block inside its file): 15,594 slots, 8,336 animations, 7,258 empty slots, 270,420 tracks, buffer types 1–7 and 11–13. Every track weighs 1.0; 231,142 tracks have a keyframe buffer, whose size is a whole number of keys at its type's stride, and 51,794 have a bounds block. Every animation has flags 0x00800000 and a non-zero event block offset. The track types (usage) come out 237,990 of 0, 75 of 3, and 13,286, 10,696, 8,300 and 73 of 1, 2, 4 and 5.
  - Not reached: why the version number rose from 66 to 67 when the structures are the same; the values at +0x3C and at +0x38.
