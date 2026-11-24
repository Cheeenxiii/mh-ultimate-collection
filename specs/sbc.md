---
class: rCollision
extension: sbc
games: MH4U and MH3U (inner class 0x77CF8DF8); MHXX (0x781ACA20, not laid out)
status: unverified
---

# SBC: stage collision

A stage's collision mesh, split into parts with a uniform grid each and a bounding-volume hierarchy over them. Stage conversion needs it.

**Source.** MHGU Definitive Edition, `tools/sbc.py` (GPL-3.0-or-later), which converts MH4U's stage collision to MHGU's. Class id `0x51fc779f` (MH4U registry).

## Header (0x48 bytes in MH4U)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SBC\xFF` | verified | MHGU-DE `sbc.py`; check S1 |
| 0x04 | u32 | inner class hash | verified | check S1 |
| 0x08 | ? | counts of parts, attribute groups, polygons, triangles and vertices, then a bounding box (exact offsets in `sbc.py`, not yet transcribed) | unverified | MHGU-DE `sbc.py` |

After the header, with no alignment between blocks: one 0x48-byte record per part (a grid, indices local to the part), 28-byte polygon boxes, a `BVHC` block of 112-byte four-wide nodes, then the grids, triangles and vertices.

## Checks

- **S1 (done):** `mhuc survey` reads every `rCollision`. All have magic `SBC\xFF`. MH4U: 626 files, inner class 0x77CF8DF8. MH3U: 344 files, the **same** class, so 3U stage collision is MH4U's format. MHXX: 1,052 files, class **0x781ACA20**, so GU collision needs its own layout or a conversion.
