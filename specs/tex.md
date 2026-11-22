---
class: rTexture
extension: tex
games: MH4U, MHX, MHXX, MH3U (3DS)
status: unverified
---

# TEX: MT Framework Mobile texture

A 16-byte header of bit fields, mip offsets, then pixel data in the PICA200's tiled layout. `mhuc.tex` reads and writes plain textures; `mhuc.pica` holds the codecs; [tex.ksy](tex.ksy) describes the header.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `TEX\0` | verified | mhff tex.py; check T1 |
| 0x04 | u32 bits 0-11 | version: 0xA5 MH4U and MH3U, 0xA6 MHXX | verified | mhff tex.py; check T1 |
| 0x04 | u32 bits 12-23 | unknown | unverified | mhff tex.py |
| 0x04 | u32 bits 24-27 | size shift, always 0 | unverified | mhff tex.py |
| 0x04 | u32 bits 28-31 | kind: 2 plain, 6 cube map | verified | mhff tex.py; check T1 |
| 0x08 | u32 bits 0-5 | mip count | verified | mhff tex.py; check T1 |
| 0x08 | u32 bits 6-18 | width | verified | mhff tex.py, Silvris MobileMTF_Tex.bt; check T1 |
| 0x08 | u32 bits 19-31 | height | verified | mhff tex.py, Silvris MobileMTF_Tex.bt; check T1 |
| 0x0C | u32 bits 0-7 | texture count (6 for cube maps) | verified | mhff tex.py; check T1 |
| 0x0C | u32 bits 8-15 | format (table below) | verified | mhff tex.py; checks T1, T2 |
| 0x0C | u32 bits 16-28 | unknown, always 1 | unverified | mhff tex.py |
| 0x10 | u8[0x6C] | cube maps only: unknown (spherical harmonics in other MT titles); the size is verified | verified | mhff tex.py; check T1 |
| 0x10 or 0x7C | u32[mips × textures] | offsets from the start of the pixel data | verified | mhff tex.py; checks T1, T3 |

Silvris's MobileMTF_Tex.bt reads the second word differently (16-bit version, 8-bit unknown, 8-bit format) and puts the mip count in a different word. Check T1 settles it for the 3DS games: mhff's reading fits every texture of MH4U, MH3U and MHXX; Silvris's is likely another MT Mobile revision.

## Formats

| MT format | PICA format | Status | Source |
|---|---|---|---|
| 1 | RGBA4 | verified | mhff tex.py; check T2 |
| 2 | RGBA5551 | verified | mhff tex.py; check T2 |
| 3 | RGBA8 | verified | mhff tex.py; check T2 |
| 4 | RGB565 | verified | mhff tex.py; check T2 |
| 5 | A8 (a soft alpha mask decodes as one) | verified | mhff tex.py; check T2 |
| 6 | 8 bits per pixel, meaning unknown (MH3U 1 texture, MHXX 157, MH4U none) | unknown | ours; check T1 |
| 7 | LA8 | verified | mhff tex.py; check T2 |
| 11 | ETC1 | verified | mhff tex.py; check T2 |
| 12 | ETC1A4 | verified | mhff tex.py; check T2 |
| 14 | A4 (a glyph sheet decodes as one) | verified | mhff tex.py; check T2 |
| 15 | L4 (the sample was too plain to tell) | unverified | mhff tex.py; check T2 |
| 16 | L8 (plausible, not conclusive) | unverified | mhff tex.py; check T2 |
| 17 | RGB8 | verified | mhff tex.py; check T2 |

## PICA200 layout (all formats)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| per tile | 8×8 pixels | tiles in row-major order, pixels of a tile in Morton (Z) order | verified | 3dbrew GPU/Textures, mhff deblock; check T2 |
| per pixel | little endian | RGBA8 stored A,B,G,R; RGB8 B,G,R; 16-bit formats with red in the top bits; LA8 A then L; 4-bit formats low nibble first | verified | 3dbrew GPU/Textures; check T2 |
| per ETC1 tile | 4 blocks | top left, top right, bottom left, bottom right; each a little-endian u64, pixels numbered x×4+y | verified | mhff decode_etc1, Khronos ETC1; check T2 |
| per ETC1A4 block | u64 + u64 | 4-bit alpha per pixel (same numbering), then the colour block | verified | mhff decode_etc1; check T2 |
| image | rows | top row first as mhuc decodes them: text reads upright without `--flip-y` | verified | 3dbrew; check T2 |

## Checks

Run on 2026-11-23 with `mhuc survey` on the maintainer's dumps (see [arc](arc.md#checks) for the list), and by eye for T2.

- **T1 (done): sizes.** For every texture (entries of type `rTexture` in every ARC), the length mhff's header reading implies (header, the cube-map block, offsets, then each mip of each face at the format's bits per pixel, minimum 8×8) equals the entry's length.
  - MH4U: 38,320 textures (147 cube maps), all match. EUR the same.
  - MH3U: 16,594 (172 cube maps); all match except one in format 6, which mhuc can't size.
  - MHXX JPN: 43,909 (118 cube maps); all match except 157 in format 6. Those are 8 bits per pixel by their length.
- **T2 (done): looks.** One texture of each format from MH4U was decoded with `mhuc.tex.to_rgba` and composited over a checkerboard, then looked at; the images stayed in the work folder, outside git. Portraits, icons, a map with digits, the game's logo, a glyph sheet with words, lava, monster skin and a sky all looked right, with alpha where expected and text upright and unmirrored, so `--flip-y` is not needed. Formats 15 and 16 gave plain grey images, which are plausible but tell nothing.
- **T3 (done): round trip.** `tex.write(tex.read(data)) == data` for every plain single texture: MH4U 38,173 of 38,173, MH3U 16,421 of 16,421 readable, MHXX 43,634 of 43,634 readable (format 6 skipped).
