---
class: rMotionList
extension: lmt
games: MH4U (version 67, per MHGU Definitive Edition); MH3U and MHXX to check (L1)
status: unknown
---

# LMT: motion list (animations)

A list of animations for one skeleton: per animation, tracks (one per bone and channel) pointing at keyframe buffers, optional bounds, and an event block. MH3U's underwater motions and every converted monster's moves are LMT files, so this format sits under both the underwater work (docs/design/underwater.md) and monster conversion.

**Source.** Scrimas's MHGU Definitive Edition (GPL-3.0-or-later), `tools/lmt.py`, which copies animations between MH4U and MHGU LMT files and states the layout as read off MH4U's em022 and em092 and MHGU's em067_00 (version 67 in both). Offsets are relative to the file (the game relocates them at load). Nothing here has been checked on our files: check L1. The keyframe buffer encodings (by buffer type) aren't described there; PredatorCZ's RevilLib is the usual reference for them. Reader: `tools/mhuc/lmt.py`.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `LMT\0` | unverified | MHGU-DE `lmt.py` |
| 0x04 | u16 | version (67 in MH4U and MHGU) | unverified | MHGU-DE `lmt.py` |
| 0x06 | u16 | animation count | unverified | MHGU-DE `lmt.py` |
| 0x08 | u32 × count | animation offsets (0 = empty slot) | unverified | MHGU-DE `lmt.py` |

## Animation (0x40 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | track table offset | unverified | MHGU-DE `lmt.py` |
| +0x04 | u32 | track count | unverified | MHGU-DE `lmt.py` |
| +0x08 | s32 | frame count | unverified | MHGU-DE `lmt.py` |
| +0x0C | s32 | loop frame | unverified | MHGU-DE `lmt.py` |
| +0x10 | 0x24 bytes | unknown | unknown | MHGU-DE `lmt.py` |
| +0x34 | u32 | event block offset (0 none) | unverified | MHGU-DE `lmt.py` |
| +0x38 | 8 bytes | unknown | unknown | MHGU-DE `lmt.py` |

## Track (0x24 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 ×4 | buffer type, usage, joint type, bone id | unverified | MHGU-DE `lmt.py` |
| +0x04 | f32 | weight | unverified | MHGU-DE `lmt.py` |
| +0x08 | u32 | buffer size | unverified | MHGU-DE `lmt.py` |
| +0x0C | u32 | buffer offset | unverified | MHGU-DE `lmt.py` |
| +0x10 | f32 ×4 | reference frame | unverified | MHGU-DE `lmt.py` |
| +0x20 | u32 | bounds offset (0x20 bytes; 0 none) | unverified | MHGU-DE `lmt.py` |

## Event block (4 groups × 0x48 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 ×32 | remap | unverified | MHGU-DE `lmt.py` |
| +0x40 | u32 | event count | unverified | MHGU-DE `lmt.py` |
| +0x44 | u32 | offset of count × {u32 bits, u32 frames} | unverified | MHGU-DE `lmt.py` |

## Checks

- **L1 (open, needs the RomFS of each game):** `mhuc survey` counts every `rMotionList`: its version, whether `mhuc.lmt.read` reads it (every offset inside the file), and its animations, tracks, buffer types and event blocks. Pass for MH4U: version 67 throughout and every file readable. For MH3U and MHXX, the versions they use say whether this layout applies (MH3U is older and may differ: underwater motions come from it).
