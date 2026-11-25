---
class: rMaterial
extension: mrl
games: MH4U, MHXX, MH3U (3DS)
status: unknown
---

# MRL: MT Framework Mobile material (header and name hashes)

A monster's model names its materials in its 128-byte material name strings ([mod](mod.md)); the
material file the model loads holds one record per material whose first word hashes the name. The
three 3DS games share one layout at version 0x20, but not the value at 0x10: each game's files
carry that game's own signature, and MH4U's rMaterial load refuses any other. A ported material
therefore keeps the source's file and body and has only the signature rewritten, which is what
`mhuc.formats.mrl.for_mh4u` does for a converted MH3U or MHXX monster.

## Header (0x1c bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MRL\0` | verified | check MR1 |
| 0x04 | u32 | version: 0x20 in MH4U, MH3U and MHXX | verified | check MR1 |
| 0x08 | u32 | material record count (0x3c-byte records at +0x18 + 4) | verified | ours, MH4U rMaterial::findMaterial `0x00be6e88`; check MR1 |
| 0x0c | u32 | reference count (0x4c-byte entries at +0x14) | verified | ours, MH4U rMaterial load `0x00be7000`; check MR1 |
| 0x10 | u32 | signature: MH4U 0xcec1aa61, MH3U 0x3810b2e2, MHXX 0xeaca0cbd | verified | ours, the load's check; check MR1 |
| 0x14 | u32 | reference array offset, 0x1c | verified | ours, the load; check MR1 |
| 0x18 | u32 | material record array offset, 0x14 + 0x4c × reference count | verified | ours, the load; check MR1 |

MH4U's rMaterial load (`0x00be7000`) reads the header in place: it checks the magic, the version
0x20 and the signature at 0x10, the last against the engine's own value at
`*(*(0x010572d0)+0x202c)`; a file that fails any of the three is refused and the resource it
belongs to never reaches done. It then turns the two offsets into pointers and loads the
references (checks [`mod`](mod.md)'s M2 for the model side).

## Reference (0x4c bytes each, at +0x14)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | class id: 0x241f5deb (rTexture) for a texture reference, 0 for an inline block | verified | ours, the load; check MR1 |
| 0x04, 0x08 | u32 × 2 | unknown, 0 in the files checked | unverified | ours |
| 0x0c | char[64] | texture path when +0x00 is rTexture's class id; inline data when it is 0 | verified | ours, the load; check MR1 |

The load calls the resource manager with the class id and the path for a texture reference, and
parses the inline block at +0x0c when the class id is 0. What an inline block holds is not
decoded.

## Material record (0x3c bytes each, after a 4-byte block word at +0x18)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | name hash: `(~crc32(name)) & 0xffffffff` of one of the model's material names | verified | ours, rMaterial::findMaterial `0x00be6e88`; check MR2 |
| 0x04 | u32 × 14 | the material's shader and parameter data | unknown | not decoded |

The model's material table gives names, not hashes: `rModel::createMaterials` (`0x00681650`) asks
the material for each name, and the lookup hashes the name and scans these records in file order.
The record order need not match the model's name order. A converted material keeps the source's
records and hashes, so a port's model keeps binding the source's material names unchanged.

## Conversion

MH3U's and MHXX's material files have MH4U's version and layout but their own signature; MH4U's
loader refuses them, and the archive they came in stalls (an MH3U monster archive with one MH3U
material never completes its load). `mhuc convert monster` rewrites the signature to MH4U's and
moves the texture paths to the port's folder (the paths are absolute and the two file names are
the same length). Every other byte, the material records and their hashes included, stays the
source's.

## Checks

- **MR1 (done, 2026-11-25, static):** `mhuc survey <RomFS>` reads every `rMaterial` entry of the
  three RomFS images. MH3U: 6,193 readable, all signature 0x3810b2e2, references at 0x1c and the
  records right after them; 16,508 texture references, all with a printable path; 8,238 inline
  references; 31 empty files. MH4U: 13,341 readable, all 0xcec1aa61; 44,083 texture references
  and 27,952 inline; 6 empty. MHXX: 17,678 readable, all 0xeaca0cbd; 47,579 texture references
  and 38,115 inline. Every reference's class id is rTexture's or 0. (Two MH3U files and one MHXX
  file repeat a material name hash inside one file; the count reports it, the loader takes the
  first match.)
- **MR2 (done, 2026-11-25, static):** on MH4U, MH3U and MHXX `em001`, every material name the
  model lists hashes to one of its material file's records. Procedure:
  `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k three_games_material`.
- **MR3 (done, 2026-11-25, game):** a converted material loads in MH4U. In the headless 125
  quest the archive resource's +0x50 reaches done (`0x00928a01`) and `HW.Memory UnmappedAccess`
  is 0 through the load, where the source signature stalled it. The ported model still does not
  draw, which is the model's binding to the material, not the material's load. Procedure in
  [checks.md](../docs/checks.md#a-converted-material-loads-m3).
- **MR4 (done, 2026-11-25, static):** every model/material pair of every monster archive of MH4U
  (`/data/emNNN.arc`, 123 archives) and MH3U (`/arc/enemy/emNNN.arc`, 85 archives). For every
  `rModel` with an `rMaterial` at the same path (270 and 409 pairs), every name in the model's
  material table hashes to one of the material file's record keys; no name was unbound. The 5 and
  1 files that hold more records than their model's names still bind every name. Procedure:
  `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k every_material_a_monster`.
