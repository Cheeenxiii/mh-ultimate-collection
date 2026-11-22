meta:
  id: mt_gmd_v1
  title: MT Framework GMD text table, version 1
  file-extension: gmd
  license: GPL-3.0-or-later
  endian: le
  encoding: UTF-8
doc: |
  Status per field in gmd.md. Source: Kuriimu2 plugin_mt_framework Gmdv1. All unverified.
seq:
  - id: magic
    contents: ["GMD", 0]
  - id: version
    type: u4
  - id: language
    type: u4
  - id: unknown
    type: u8
  - id: num_labels
    type: u4
  - id: num_sections
    type: u4
  - id: label_bytes
    type: u4
  - id: section_bytes
    type: u4
  - id: name_length
    type: u4
  - id: name
    type: strz
  - id: label_entries
    type: label_entry
    repeat: expr
    repeat-expr: num_labels
  - id: labels
    size: label_bytes
  - id: strings
    type: strz
    repeat: expr
    repeat-expr: num_sections
types:
  label_entry:
    seq:
      - id: section
        type: s4
      - id: offset
        type: u4
