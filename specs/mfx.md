---
class: none (loaded by the engine at boot)
extension: lfx
games: MH4U, MHXX, MH3U (3DS)
status: unknown
---

# MFX: MT Framework Mobile shader package (object names and slots)

Each game ships one shader package: MH4U and MHXX at `/system/ltshader/LtShaderPackage.lfx`, MH3U
at `/LtUserShader/LtUserShaderPackage.lfx`. It holds every shader object the game's materials
and models can name: input layouts (`IAObj4wtT`, the vertex format of a skinned mesh), blend,
depth-stencil, rasterizer and sampler states (`BSSolid`, `DSZTestWrite`, `RSMesh`,
`SSAlbedoSampler`), constant buffers (`CBMaterialStd`) and texture slots (`tAlbedoMap`).

A material or model never stores an object's name. It stores an **object id**:

    id = (crc32_string(~0, name) & 0xfffff) << 12 | slot

The high 20 bits are the low 20 bits of the name's CRC-32 with no final inversion (the hash the
engine uses for material names, [mrl](mrl.md)). The low 12 bits are the object's slot in the
package. The three games number their objects in different orders: MH4U keeps `BSSolid` in slot
0x9e, MH3U in 0x91, where MH4U keeps the sampler `SSLinear`. A material is therefore only right
in the game whose package it was made against. That package's hash is the signature the material
carries at 0x10, and MH4U's rMaterial load refuses any other ([mrl](mrl.md)). Past that check the
slots are used as stored, so a material converted by rewriting the signature alone points at
other objects (check X4 is the game check of the converted model).

Reading the package: the names and slots below are what the converter needs. The objects'
bodies (shader code, state values, buffer layouts) are not decoded.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MFX\0` | verified | check X1 |
| 0x04 | u16 | version, 0x34 in the three games | verified | check X1 |
| 0x06 | u16 | the game's revision: MH3U 0x63, MH4U 0x64, MHXX 0x69 | unverified | ours, the three files |
| 0x08 | u32 | the package's hash, which is the signature its game's materials carry at MRL 0x10 | verified | check X1 |
| 0x0c | u32 | object slot count (MH4U 0x31c, MH3U 0x2f0, MHXX 0x32c) | verified | check X1 |
| 0x10 to 0x1c | u32 × 4 | counts and offsets of the other sections, not decoded | unknown | ours |
| 0x20 | u32 | string table offset | verified | check X1 |
| 0x24 | u32 | offset of a further section, not decoded | unknown | ours |
| 0x28 | u32 × count | one offset per slot, from the file's start; 0 for an empty slot (slot 0) | verified | check X1 |

## Object entry (at its slot's offset)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | name offset in the string table | verified | check X1 |
| 0x04, 0x08 | u32 × 2 | kind and other fields, not decoded | unknown | ours |
| 0x0c | u16 | unknown | unknown | ours |
| 0x0e | u16 | the entry's own slot number | unverified | ours, the three files |

## Where the ids are

- **Material records** ([mrl](mrl.md)): the blend, depth-stencil and rasterizer state ids at
  record +0x08, +0x0c and +0x10.
- **Material command blocks**, after the records: constant-buffer, texture and sampler ids among
  other words. The blocks aren't decoded, so the converter takes every aligned word past the
  header and outside the texture paths that is an id of the source package. A word counts as an
  id only if its slot holds an object whose name hashes to its high 20 bits.
- **Model meshes** ([mod](mod.md)): the vertex format at mesh +0x14 is an input-layout id.

## Conversion

`mhuc convert monster` reads both games' packages from their RomFS images (`mhuc.formats.mfx`).
In each converted material it rewrites every id of the source package to MH4U's id for the same
name, and the signature to MH4U's package hash (`mrl.for_mh4u`). It does the same for each mesh's
vertex format (`mod.for_mh4u`), which keeps the same slot for MH3U's and MHXX's monster layouts in
practice. An object MH4U's package lacks is refused; none of MH3U's or MHXX's monster files names
one (check X3).

## Checks

- **X1 (done, static):** the three packages read: magic, version 0x34, every slot's name in the
  string table, and the 20-bit name hashes unique within each package. Each package's hash at
  0x08 equals the signature its game's materials carry (MH4U 0xcec1aa61, MH3U 0x3810b2e2, MHXX
  0xeaca0cbd; [mrl](mrl.md) MR1). The same object sits in different slots: `BSSolid` 0x9e in
  MH4U, 0x91 in MH3U. Procedure:
  `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k shader_package_hash`.
- **X2 (done, static):** the id formula against MH4U's own files. MH4U's Rathian material
  (`/data/em001.arc`) stores 0x62b2d09e, 0xb81390d2 and 0x108cf0de in its records' state words,
  which are `BSSolid`, `DSZTestWrite` and `RSMesh` at MH4U slots 0x9e, 0xd2 and 0xde by the
  formula. MH3U's Rathian stores the same names at MH3U slots 0x91, 0xc4 and 0xd0. Before
  conversion none of MH3U Rathian's state triples is one of MH4U Rathian's; after it, every one
  is. Procedure:
  `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k converted_states`.
- **X3 (done, static):** every `rMaterial` and `rModel` of every MH3U (`/arc/enemy/emNNN.arc`) and
  MHXX (`/arc/enemy/emNNN_VV.arc`) monster archive converts: each id names an object MH4U's package
  has. A survey of the monster materials found 7,423 ids in 409 MH3U files and 102,695 in 3,843
  MHXX files. Only one aligned word in the MH3U files carries a known name hash with the wrong
  slot (a coincidence, left alone). Procedure:
  `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k shader_package`.
- **X4 (game, open):** the converted model drawn in MH4U; procedure and status in
  [checks.md](../docs/checks.md#the-materials-shader-ids-x4-game-open).
