---
class: rMotionList
extension: lmt
games: MH4U and MHXX (version 67, check L1); MH3U uses version 66, not laid out
status: unknown
---

# LMT: motion list (animations)

A list of animations for one skeleton: per animation, tracks (one per bone and channel) pointing at keyframe buffers, optional bounds, and an event block. MH3U's underwater motions and every converted monster's moves are LMT files, so this format sits under both the underwater work (docs/architecture.md#underwater) and monster conversion.

**Source.** Scrimas's MHGU Definitive Edition (GPL-3.0-or-later), `tools/lmt.py`, which copies animations between MH4U and MHGU LMT files and states the layout as read off MH4U's em022 and em092 and MHGU's em067_00 (version 67 in both). Offsets are relative to the file (the game relocates them at load). Check L1 read every MH4U and MHXX motion list with this layout; the rows it reaches are marked verified. MH3U's are version 66 and don't follow it. The keyframe buffer encodings (by buffer type) aren't described there; PredatorCZ's RevilLib is the usual reference for them. Reader: `src/mhuc/lmt.py`.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `LMT\0` | verified | MHGU-DE `lmt.py`; check L1 |
| 0x04 | u16 | version (67 in MH4U, MHXX and MHGU; 66 in MH3U) | verified | MHGU-DE `lmt.py`; check L1 |
| 0x06 | u16 | animation count | verified | MHGU-DE `lmt.py`; check L1 |
| 0x08 | u32 × count | animation offsets (0 = empty slot) | verified | MHGU-DE `lmt.py`; check L1 |

## Animation (0x40 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | track table offset | verified | MHGU-DE `lmt.py`; check L1 |
| +0x04 | u32 | track count | verified | MHGU-DE `lmt.py`; check L1 |
| +0x08 | s32 | frame count | unverified | MHGU-DE `lmt.py` |
| +0x0C | s32 | loop frame | unverified | MHGU-DE `lmt.py` |
| +0x10 | 0x24 bytes | unknown | unknown | MHGU-DE `lmt.py` |
| +0x34 | u32 | event block offset (0 none) | verified | MHGU-DE `lmt.py`; check L1 |
| +0x38 | 8 bytes | unknown | unknown | MHGU-DE `lmt.py` |

## Track (0x24 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u8 | buffer type | unverified | MHGU-DE `lmt.py` |
| +0x01 | u8 | usage: 0 on a bone's rotation track, 1 on its translation track; 3 and 4 only on the 255 track, in every list read | unverified | MHGU-DE `lmt.py`; check L2 |
| +0x02 | u8 | joint type: 0 in every track read | unverified | MHGU-DE `lmt.py`; check L2 |
| +0x03 | u8 | bone id: the id in the model's bone table, not its index | verified | MHGU-DE `lmt.py`; check L2 |
| +0x04 | f32 | weight | unverified | MHGU-DE `lmt.py` |
| +0x08 | u32 | buffer size | verified | MHGU-DE `lmt.py`; check L1 |
| +0x0C | u32 | buffer offset | verified | MHGU-DE `lmt.py`; check L1 |
| +0x10 | f32 ×4 | reference frame | unverified | MHGU-DE `lmt.py` |
| +0x20 | u32 | bounds offset (0x20 bytes; 0 none) | verified | MHGU-DE `lmt.py`; check L1 |

## Event block (4 groups × 0x48 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 ×32 | remap | unverified | MHGU-DE `lmt.py` |
| +0x40 | u32 | event count | verified | MHGU-DE `lmt.py`; check L1 |
| +0x44 | u32 | offset of count × {u32 bits, u32 frames} | verified | MHGU-DE `lmt.py`; check L1 |

## Checks

- **L1 (done):** `mhuc survey` on each RomFS (section `lmt`).
  - MH4U: 1,466 motion lists, all version 67, all readable (every animation, track table, keyframe buffer, bounds block and event block inside its file): 23,412 animations, 25,633 empty slots, 732,404 tracks, buffer types 1–7 and 11–13. Every animation has an event block.
  - MHXX JPN: 988, all version 67, all readable: 21,154 animations, 57,010 empty slots, 677,909 tracks, the same buffer types (type 3 three times). So MHXX motions are MH4U's format: a GU monster's LMT can be read, and probably loaded, as it is.
  - MH3U USA: 387, all **version 66**; `mhuc.lmt` lays out only 67, so none were read. MH3U's motions, the underwater ones among them, need their own layout (Cha-Cha's Wii U reading is the lead, docs/sources.md) or a conversion to 67.
  - Not reached: the meaning of the fields marked unverified (frame counts, weights, reference frames) and the keyframe encodings.
- **L2 (done, version 67):** a track's bone field is a bone id, not an index. MH4U's em001 model has 43 bones whose ids run to 202 with gaps, and its five motion lists carry ids from 60 to 145, which no 43-entry list could index. The player lists say the same: the common and per-weapon lists carry exactly the hunter body's ids (0 to 12 and 14 to 19) and never 13. MH3U's 50 player lists, read with version 67's track-table layout, carry rotation tracks on ids 1 to 21 (one list also gives id 0 a rotation track with no keyframes) and a translation track on 0, with 20 and 21 never keyframed; that part reads the tracks only, because MH3U's keyframe buffers are version 66 and aren't decoded. Procedure: `MHUC_DUMPS=… python -m pytest tests/test_with_game_files.py -k address_bones_by_id` for MH4U; the MH3U counts are a one-off read of the 50 player motion lists with the same track table.
