---
class: rModel
extension: mod
games: MH4U, MHXX, MH3U (3DS)
status: unverified
---

# MOD: model (partial)

Meshes, bones, groups and materials. Only the header is described here; the mesh and vertex layouts are still to describe. **Check M1 found the same version, 0xE6, and the same header shape in all three 3DS games, MH3U included.** The 3DS MH3U is a port onto MH4U's MT Mobile engine generation, and its models are not the older format Silvris's template reads (that template's versions under 190 are the Wii/Wii U files'). Moving a 3U model into MH4U is therefore not a format conversion at the container level; what differs is skeletons, materials and the data the models point to (M2).

## Header (MH4U, version 0xE6, per mhff; 64 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MOD\0` | verified | mhff io_import_scene_mod.py; check M1 |
| 0x04 | u16 | version: 0xE6 in MH4U, MH3U and MHXX | verified | mhff io_import_scene_mod.py; check M1 |
| 0x06 | u16 | bone count | unverified | Silvris MH3U MOD.bt (field order) |
| 0x08 | u16 | mesh count | unverified | mhff io_import_scene_mod.py |
| 0x0A | u16 | material count | unverified | Silvris MH3U MOD.bt |
| 0x0C | u32 × 13 | counts and offsets; mhff uses the 12th as the mesh table offset, the 13th as the vertex buffer, the 14th as the index buffer. The words at 0x18 and 0x2C to 0x3C are file offsets in every model sampled, 0x28 in most; the first data usually starts at 0x80. The same in all three games | unverified | mhff io_import_scene_mod.py; check M1 (shape only) |

## Header (Wii/Wii U MH3U and versions under 190, per Silvris; not used by the 3DS games)

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

- **M1 (done, 2026-11-23):** `mhuc survey` counted every `rModel` entry: MH4U 10,472, MH3U 6,237, MHXX JPN 17,661, all with magic `MOD\0` and version 0xE6. On 1,500 models per game, the u32 words that are valid offsets fall in the same slots in all three games (0x18, 0x2C to 0x3C always, 0x28 in about three quarters), and the smallest offset is 0x80 in most. What each slot holds is left to M2.
- **M2 (with game files):** import one monster's model from each game with the community Blender/Noesis tools and with a future `mhuc` reader; compare vertex and face counts.
