---
class: rModel
extension: mod
games: MH4U, MHXX, MH3U (3DS)
status: unverified
---

# MOD: model (partial)

Meshes, bones, groups and materials. Only the header is described here; the mesh and vertex layouts differ by version and are left to the first session with game files. The header changes with the version byte, so MH3U's models (an older version) and MH4U's need separate readings: that difference is what the model converter will be built on.

## Header (MH4U, version 0xE6, per mhff; 64 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MOD\0` | unverified | mhff io_import_scene_mod.py |
| 0x04 | u16 | version: 0xE6 for MH4U | unverified | mhff io_import_scene_mod.py |
| 0x06 | u16 | bone count | unverified | Silvris MH3U MOD.bt (field order) |
| 0x08 | u16 | mesh count | unverified | mhff io_import_scene_mod.py |
| 0x0A | u16 | material count | unverified | Silvris MH3U MOD.bt |
| 0x0C | u32 × 13 | counts and offsets; mhff uses the 12th as the mesh table offset, the 13th as the vertex buffer, the 14th as the index buffer | unverified | mhff io_import_scene_mod.py |

## Header (MH3U and versions under 190, per Silvris)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | magic | unverified | Silvris MH3U MOD.bt |
| 0x04 | u8, u8 | version (second byte is the main one) | unverified | Silvris MH3U MOD.bt |
| 0x06 | s16 × 3 | bone, mesh, material counts | unverified | Silvris MH3U MOD.bt |
| 0x0C | s32 × 5 | vertex count, vertex ids, face count, vertex buffer size, second buffer size | unverified | Silvris MH3U MOD.bt |
| then | s32 | unknown count (versions under 190) | unverified | Silvris MH3U MOD.bt |
| then | s32 | group count; bone-map count (versions under 190 or over 220) | unverified | Silvris MH3U MOD.bt |
| then | s32 × 8 | bone, group, material-name, mesh, vertex, vertex2, face, unknown offsets | unverified | Silvris MH3U MOD.bt |
| then | floats | bounding sphere and box (versions under 190) | unverified | Silvris MH3U MOD.bt |

## Mesh entry (MH4U, 48 bytes, per mhff)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u16 | unknown | unverified | mhff io_import_scene_mod.py |
| 0x02 | u16 | vertex count | unverified | mhff io_import_scene_mod.py |
| 0x04 | u32 | unknown | unverified | mhff io_import_scene_mod.py |
| 0x08 | u16 | unknown | unverified | mhff io_import_scene_mod.py |
| 0x0A | u8 | vertex stride | unverified | mhff io_import_scene_mod.py |
| 0x0B | u8 | unknown | unverified | mhff io_import_scene_mod.py |
| 0x0C | u32 × 9 | vertex start, vertex offset, index start, index count, … | unverified | mhff io_import_scene_mod.py |

## Checks

- **M1 (with game files):** for every `.mod` in MH4U, MH3U and MHXX, record the version values seen and whether the header sizes above add up to the first offset.
- **M2 (with game files):** import one monster's model from each game with the community Blender/Noesis tools and with a future `mhuc` reader; compare vertex and face counts.
