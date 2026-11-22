---
class: rTexture
extension: tex
games: MH4U, MHX, MHXX (3DS); MH3U to check
status: unverified
---

# TEX: MT Framework Mobile texture

A 16-byte header of bit fields, mip offsets, then pixel data in the PICA200's tiled layout. `mhuc.tex` reads and writes plain textures; `mhuc.pica` holds the codecs; [tex.ksy](tex.ksy) describes the header.

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `TEX\0` | unverified | mhff tex.py |
| 0x04 | u32 bits 0-11 | version: 0xA5 (MH4U), 0xA6 also seen | unverified | mhff tex.py |
| 0x04 | u32 bits 12-23 | unknown | unverified | mhff tex.py |
| 0x04 | u32 bits 24-27 | size shift, always 0 | unverified | mhff tex.py |
| 0x04 | u32 bits 28-31 | kind: 2 plain, 6 cube map | unverified | mhff tex.py |
| 0x08 | u32 bits 0-5 | mip count | unverified | mhff tex.py |
| 0x08 | u32 bits 6-18 | width | unverified | mhff tex.py, Silvris MobileMTF_Tex.bt |
| 0x08 | u32 bits 19-31 | height | unverified | mhff tex.py, Silvris MobileMTF_Tex.bt |
| 0x0C | u32 bits 0-7 | texture count (6 for cube maps) | unverified | mhff tex.py |
| 0x0C | u32 bits 8-15 | format (table below) | unverified | mhff tex.py |
| 0x0C | u32 bits 16-28 | unknown, always 1 | unverified | mhff tex.py |
| 0x10 | u8[0x6C] | cube maps only: unknown (spherical harmonics in other MT titles) | unverified | mhff tex.py |
| 0x10 or 0x7C | u32[mips × textures] | offsets from the start of the pixel data | unverified | mhff tex.py |

Silvris's MobileMTF_Tex.bt reads the second word differently (16-bit version, 8-bit unknown, 8-bit format) and puts the mip count in a different word: likely a different MT Mobile revision. To settle with check T1.

## Formats

| MT format | PICA format | Status | Source |
|---|---|---|---|
| 1 | RGBA4 | unverified | mhff tex.py |
| 2 | RGBA5551 | unverified | mhff tex.py |
| 3 | RGBA8 | unverified | mhff tex.py |
| 4 | RGB565 | unverified | mhff tex.py |
| 5 | A8 or L8 (mhff: "may not be correct") | unverified | mhff tex.py |
| 7 | LA8 | unverified | mhff tex.py |
| 11 | ETC1 | unverified | mhff tex.py |
| 12 | ETC1A4 | unverified | mhff tex.py |
| 14 | A4 or L4 (guess) | unverified | mhff tex.py |
| 15 | L4 or A4 (guess) | unverified | mhff tex.py |
| 16 | L8 (guess) | unverified | mhff tex.py |
| 17 | RGB8 | unverified | mhff tex.py |

## PICA200 layout (all formats)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| per tile | 8×8 pixels | tiles in row-major order, pixels of a tile in Morton (Z) order | unverified | 3dbrew GPU/Textures, mhff deblock |
| per pixel | little endian | RGBA8 stored A,B,G,R; RGB8 B,G,R; 16-bit formats with red in the top bits; LA8 A then L; 4-bit formats low nibble first | unverified | 3dbrew GPU/Textures |
| per ETC1 tile | 4 blocks | top left, top right, bottom left, bottom right; each a little-endian u64, pixels numbered x×4+y | unverified | mhff decode_etc1, Khronos ETC1 |
| per ETC1A4 block | u64 + u64 | 4-bit alpha per pixel (same numbering), then the colour block | unverified | mhff decode_etc1 |
| image | rows | whether rows are stored bottom-up (the GPU's origin) | unverified | 3dbrew; `mhuc tex --flip-y` |

## Checks

- **T1 (with game files):** for every `.tex` in MH4U's RomFS, `mhuc tex info` gives a size that matches the data length from the offsets and format. Record which header reading (mhff's or Silvris's) fits, per game.
- **T2 (with game files):** decode a few textures of each format and look at them. Note the format numbers whose colours or alpha look wrong, and whether `--flip-y` is needed.
- **T3 (with game files):** `tex.write(tex.read(data)) == data` for plain single textures.
