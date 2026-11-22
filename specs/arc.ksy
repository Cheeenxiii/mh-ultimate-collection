meta:
  id: mt_arc
  title: MT Framework Mobile archive (3DS)
  file-extension: arc
  license: GPL-3.0-or-later
  endian: le
doc: |
  Status per field in arc.md. Sources: mhff (svanheulen), Kuriimu2 plugin_mt_framework.
seq:
  - id: magic
    contents: ["ARC", 0]
  - id: version
    type: u2
  - id: num_entries
    type: u2
  - id: unknown
    type: u4
    if: version != 7 and version != 8
  - id: entries
    type: entry
    repeat: expr
    repeat-expr: num_entries
types:
  entry:
    seq:
      - id: path
        type: strz
        size: 64
        encoding: ASCII
      - id: class_id
        type: u4
      - id: compressed_size
        type: u4
      - id: size_and_flags
        type: u4
      - id: offset
        type: u4
    instances:
      size:
        value: '_root.version == 0x13 ? (size_and_flags & 0x0fffffff) : (size_and_flags & 0x1fffffff)'
      body:
        io: _root._io
        pos: offset
        size: compressed_size
        process: zlib
