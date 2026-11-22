meta:
  id: mt_tex_3ds
  title: MT Framework Mobile texture (3DS)
  file-extension: tex
  license: GPL-3.0-or-later
  endian: le
doc: |
  Header only; pixel data is PICA200-tiled (tex.md). Source: mhff tex.py. All unverified.
seq:
  - id: magic
    contents: ["TEX", 0]
  - id: word1
    type: u4
  - id: word2
    type: u4
  - id: word3
    type: u4
  - id: cube_data
    size: 0x6c
    if: kind == 6
  - id: offsets
    type: u4
    repeat: expr
    repeat-expr: mip_count * texture_count
instances:
  version:
    value: word1 & 0xfff
  kind:
    value: (word1 >> 28) & 0xf
  mip_count:
    value: word2 & 0x3f
  width:
    value: (word2 >> 6) & 0x1fff
  height:
    value: (word2 >> 19) & 0x1fff
  texture_count:
    value: word3 & 0xff
  format:
    value: (word3 >> 8) & 0xff
