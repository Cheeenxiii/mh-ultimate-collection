---
class: rModel
extension: mod
games: MH4U, MHXX, MH3U (3DS)
status: unverified
---

# MOD: model (partial)

Meshes, bones, groups and materials. Only the header is described here; the mesh and vertex layouts are still to describe. **Check M1 found the same version, 0xE6, and the same header shape in all three 3DS games, MH3U included.** The 3DS MH3U is a port onto MH4U's MT Mobile engine generation, and its models are not the older format Silvris's template reads (that template's versions under 190 are the Wii/Wii U files'). Moving a 3U model into MH4U is therefore not a format conversion at the container level; what differs is skeletons, materials and the data the models point to (M2).

## Header (MH4U, MH3U and MHXX, version 0xE6; 64 bytes)

The same layout in all three games. "M2" fields were checked on every `rModel` in one Rathalos archive per game (39 models: monster body, tail, effects), and each relation held for every one (procedure under Checks).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MOD\0` | verified | mhff io_import_scene_mod.py; check M1 |
| 0x04 | u16 | version: 0xE6 in MH4U, MH3U and MHXX | verified | mhff io_import_scene_mod.py; check M1 |
| 0x06 | u16 | bone count (0 for unskinned models) | verified | Silvris MH3U MOD.bt (field order); check M2 |
| 0x08 | u16 | mesh count | verified | mhff io_import_scene_mod.py; check M2 |
| 0x0A | u16 | material count | verified | Silvris MH3U MOD.bt; check M2 |
| 0x0C | u32 | vertex count: the sum of the meshes' vertex counts | verified | check M2 |
| 0x10 | u32 | index count: the index buffer holds this many u16 minus one and ends at the end of the file (the minus one is observed, not explained) | verified | mhff io_import_scene_mod.py; check M2 |
| 0x14 | u32 | edge count per RevilLib (via MHGU Definitive Edition's `mod.py`); less than the vertex count here | unverified | check M2; MHGU-DE `mod.py` |
| 0x18 | u32 | vertex buffer size in bytes (0x34 + this = 0x3C) | verified | check M2 |
| 0x1C | u32 | always 0 | verified | check M2 |
| 0x20 | u32 | group count (0x20-byte entries at 0x2C) | verified | check M2 |
| 0x24 | u32 | count of 0x1C-byte entries inside the bone block (0 without bones). MHGU Definitive Edition's `mod.py` reads them as skin palettes, MH4U only: {u32 count, u8 bones[24]}, which a mesh's skin-bone index picks (the size is checked here, the meaning is theirs) | unverified | check M2; MHGU-DE `mod.py` |
| 0x28 | u32 | bone block offset, 0x80; 0 without bones | verified | check M2 |
| 0x2C | u32 | group table offset (0x80 when there are no bones) | verified | check M2 |
| 0x30 | u32 | material table offset: material count × 0x80 bytes | verified | check M2 |
| 0x34 | u32 | mesh table offset: mesh count × 0x30, then a u32 n and n × 0x90 bytes (n is 0 in skinned models; in unskinned effect models it equals the mesh count) | verified | mhff io_import_scene_mod.py; check M2 |
| 0x38 | u32 | vertex buffer offset | verified | mhff io_import_scene_mod.py; check M2 |
| 0x3C | u32 | index buffer offset | verified | mhff io_import_scene_mod.py; check M2 |

MHGU Definitive Edition's `mod.py` (GPL-3.0-or-later, after PredatorCZ's RevilLib) also lays out what follows the header for MH4U: a bounding sphere and box, then metadata (middle and low LOD distances, light group, boundary joint); bones as 24-byte records {u8 index, parent, mirror, pad, f32 furthest vertex, f32 parent distance, f32 pos[3]}, then the local and inverse-bind matrices and a 256-byte remap (bone id to index); materials as 128-byte names whose CRC-32 (inverted) is the MRL material hash; meshes as 48-byte records (draw mode, vertex count, group/material/LOD bit fields, visibility/weights/stride/primitive bit fields, vertex start and stream offset, vertex format hash, index start, count and value offset, skin-bone start, envelopes). Unverified here; check M2 can take each field in turn.

## Bone block (at 0x28, size 0x2C − 0x28)

Size = bone count × 0x98 + 0x100 + (u32 at 0x24) × 0x1C in every skinned model checked, which matches 0x18 bytes of bone info, two 4×4 float matrices per bone (local and inverse bind, per mhff) and a 256-byte bone remap table. The order of the parts after the info entries isn't checked.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u8 | bone id: a stable id for the bone, not its index (ids from 0 and from 100 up seen) | verified | check M2 |
| 0x01 | u8 | parent: index of the parent's entry, 0xFF for the root | verified | check M2 |
| 0x02 | 0x16 bytes | unknown (lengths, offsets) | unverified | mhff io_import_scene_mod.py |

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
- **M2 (done, 2026-11-23, static):** Rathalos, MH4U `data/em001.arc`, MH3U `arc/enemy/em001.arc`, MHXX JPN `arc/enemy/em001_00.arc`. For every `rModel` entry (3, 3 and 33), checked: offsets 0x28..0x3C ascending; groups, materials and meshes fill the gaps between them at 0x20, 0x80 and 0x30 bytes each (with the u32 n and n × 0x90 after the meshes); vertex buffer offset + size = index buffer offset; index buffer offset + 2 × index count = file size + 2; the meshes' vertex counts (mesh +0x02) add up to the header's; the bone block's size by the formula above. Every relation held for all 39 models.
  - **Skeletons:** MH4U's and MHXX's Rathalos have the same 43 bone ids with the same parents, stored in a different order. MH3U's has 44: one more id (14), and 3 of the shared ids have a different parent. So MHXX motions that address bones by id should fit MH4U's Rathalos; MH3U's need a remap. Not yet checked: whether motions address bones by id or by index.
  - **Still open:** importing with the community Blender/Noesis tools and comparing their vertex and face counts with these; the mesh entry's fields; the word at 0x14; the 0x1C-byte entries; the 0x90-byte records.
