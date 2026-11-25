---
class: rSuppItem, rPopData, rQuestList, rTexLayout, rStageData, rStageCamera, rSoundAttributeSe, rDemoFade, rDemoListeningPoint, rAinpc
extension: supp, pop, list, and XFS entries inside ARCs
games: MH3U and MH4U (little-endian, check X1); MH3U on Wii U is big-endian (Cha-Cha); MHXX not checked
status: unknown
---

# XFS: MT Framework's serialised objects

XFS writes an object the way the class's `createProperty()` describes it, schema first: one definition per class (its DTI id and property list), then the root object. A reader needs no per-class code. In MH3U, `.supp` (`rSuppItem`, quest supply boxes), `.pop` (`rPopData`), `.list` (`rQuestList`) and several ARC classes use it, among them the quest cockpit layouts (`rTexLayout`). MH4U's only XFS files are eight `rSoundAttributeSe`; its HUD layouts are `rLayout` (`.lyt`) entries, a different format ([lyt.md](lyt.md)).

**Byte order comes from the magic.** The bytes `XFS\0` in file order are a little-endian file, `\0SFX` a big-endian one: the 3DS games (MH3U and MH4U) write little-endian, Cha-Cha's Wii U build big-endian. Three words are laid out differently, each given per byte order below; everything else is the same. Reader: `mhuc xfs dump FILE` (`src/mhuc/formats/xfs.py`), which takes the byte order from the magic.

**Sources.** The big-endian layout is BoyClinton's Cha-Cha (`docs/formats/xfs.md`, GPL-3.0), written for MH3U on Wii U and checked there on 848 of 848 files. The little-endian layout is checked against every XFS file of MH3U's and MH4U's RomFS: 853 files, all read, every object using exactly its size and every root object ending exactly at its file's end (check X1).

## Header (0x18 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | magic: bytes `XFS\0` in a little-endian file, `\0SFX` in a big-endian one | verified | Cha-Cha xfs.md; check X1 (one magic per file, 853 files) |
| 0x04 | u16 | version: 15 | verified | Cha-Cha xfs.md; check X1 |
| 0x06 | u16 | sub-version: 1, 2 or 3 | verified | Cha-Cha xfs.md (1, 2); check X1 (1, 2, 3) |
| 0x08 | u32 | unknown: 6 in Cha-Cha's sample, 1 to 682 in ours | unknown | Cha-Cha xfs.md; our files |
| 0x0C | u32 | unknown: 0 in every file checked | unknown | Cha-Cha xfs.md; our files |
| 0x10 | u32 | number of class definitions n | verified | Cha-Cha xfs.md; check X1 |
| 0x14 | u32 | size of the definition block, counted from 0x18 | verified | Cha-Cha xfs.md; check X1 |
| 0x18 | u32 × n | offsets of the class definitions, from 0x18 | verified | Cha-Cha xfs.md; check X1 |

## Class definition

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | DTI id (`~crc32(name) & 0x7FFFFFFF`, as `mhuc classid`) | verified | Cha-Cha xfs.md; check X1 (all 14 ids of the 853 files are in the class registries) |
| +0x04 | u32 | property count, little-endian files | verified | check X1 |
| +0x04 | u16, u16 | property count × 2, then 0, big-endian files | unverified | Cha-Cha xfs.md |
| +0x08 | 0x28 bytes × count | one property record each, below | verified | Cha-Cha xfs.md; check X1 |

A property record:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | name offset from 0x18; the name is NUL-terminated ASCII | verified | Cha-Cha xfs.md; check X1 (every name resolves) |
| +0x04 | u8 | type, from the table below | verified | Cha-Cha xfs.md; check X1 |
| +0x05 | u8 | attr: bit 0x20 marks an array; 0x01, 0x80 and 0x91 also occur, their meanings unknown | verified | Cha-Cha xfs.md; check X1 (every property holding more than one value has 0x20; 149 arrays hold one) |
| +0x06 | u16 | size, little-endian files: the value's runtime size in bytes (1 for a bool or u8, 2 for a u16, 4 for a u32, f32, color, string or class reference, 8 for a size or vector2, 16 for a vector3, vector4 or rect) | verified | check X1 |
| +0x06 | u16 | size, big-endian files (Cha-Cha: the value's bytes × 2) | unverified | Cha-Cha xfs.md |
| +0x08 | 0x20 bytes | zero: the runtime getter/setter slots | verified | Cha-Cha xfs.md; check X1 |

The size is the property's slot in the class's runtime object, not the length its values take in the
file: a string's is 4 (a pointer), and its NUL-terminated text follows in the object.

## Objects (from 0x18 + the definition block's size)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 | class word, little-endian files: the class index shifted left one, with bit 0 set on every object and bits 1 to 15 the 0-based class index | verified | check X1 |
| +0x00 | u16 | class word, big-endian files: 0x8000 OR'd with the class index, the flag in bit 15 and bits 0 to 14 the index | unverified | Cha-Cha xfs.md |
| +0x02 | u16 | instance id: the object's place in file order, 0 for the root and one higher for each object after it (0 to n-1 in every file) | verified | Cha-Cha xfs.md; check X1 |
| +0x04 | u32 | size, counting itself: bytes from this field to the object's end | verified | Cha-Cha xfs.md; check X1 (every object's body ends where its size says) |
| +0x08 | per property | u32 count, then that many values (attr bit 0x20 = array; a scalar has count 1) | verified | Cha-Cha xfs.md; check X1 |

## Values

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| value | 0x01, 0x02 | nested object (class, class reference), a whole object header and body | verified | Cha-Cha xfs.md; check X1 |
| value | 0x03, 0x04 | bool, u8: 1 byte | verified | Cha-Cha xfs.md; check X1 |
| value | 0x05 | u16: 2 bytes | verified | Cha-Cha xfs.md; check X1 |
| value | 0x06 | u32: 4 bytes | verified | Cha-Cha xfs.md; check X1 |
| value | 0x07 | u64: 8 bytes | unverified | reader only; no file has one |
| value | 0x08 | s8: 1 byte | unverified | reader only; no file has one |
| value | 0x09 | s16: 2 bytes | unverified | Cha-Cha xfs.md; no file has one |
| value | 0x0A | s32: 4 bytes | verified | Cha-Cha xfs.md; check X1 |
| value | 0x0B | s64: 8 bytes | unverified | reader only; no file has one |
| value | 0x0C | f32: 4 bytes | verified | Cha-Cha xfs.md; check X1 |
| value | 0x0D | f64: 8 bytes | unverified | reader only; no file has one |
| value | 0x0E | string: NUL-terminated, inline | verified | Cha-Cha xfs.md; check X1 |
| value | 0x0F | color: 4 bytes | verified | Cha-Cha xfs.md; check X1 |
| value | 0x10 | point: 2 × i32 | unverified | reader only; no file has one |
| value | 0x11 | size: 2 × u32 | verified | Cha-Cha xfs.md; check X1 |
| value | 0x12 | rect: 4 × u32 | verified | Cha-Cha xfs.md; check X1 |
| value | 0x13 | matrix: 16 × f32 | unverified | reader only; no file has one |
| value | 0x14 | vector3: 4 × f32 (padded) | verified | Cha-Cha xfs.md; check X1 |
| value | 0x15 | vector4: 4 × f32 | verified | Cha-Cha xfs.md; check X1 |
| value | 0x16 | quaternion: 4 × f32 | unverified | reader only; no file has one |
| value | 0x20 | cstring? | unverified | reader only; no file has one |
| value | 0x40 | vector2: 2 × f32 | verified | Cha-Cha xfs.md (8 bytes); check X1 |
| value | 0x80 | resource: u8 kind; kind 2 = class name and path, NUL-terminated | verified | Cha-Cha xfs.md; check X1 |

The types a file uses, across the 853 files: 0x06 3,011, 0x03 2,035, 0x0F 1,375, 0x0E 1,040,
0x15 805, 0x05 740, 0x01 738, 0x0C 725, 0x11 520, 0x04 461, 0x02 425, 0x12 285, 0x40 285,
0x80 285, 0x14 88 and 0x0A 34. Types 0x07, 0x08, 0x09, 0x0B, 0x0D, 0x10, 0x13, 0x16 and 0x20
never occur, so their encodings are the reader's assumptions.

## Open questions

- The header's 0x08 and 0x0C words.
- The attr bits other than 0x20: 0x80, 0x01 and 0x91 seen.
- Not every registered property is written (Cha-Cha: `rPopData` registers a type-0x19 `DataList` the files lack).
- Whether MHXX uses XFS. MH3U's and MH4U's RomFS are checked (X1).
- MH4U's only XFS files are its sound attribute sets; its HUD layouts are `rLayout` (`.lyt`), laid out in [lyt.md](lyt.md).

## Checks

- **X1 (done, 2026-11-25):** read every XFS file of MH3U USA's and MH4U USA's RomFS. Procedure:
  `mhuc survey <romfs.bin> --workers 1` (section `xfs`) counts the files read, by version, endianness,
  class id in an ARC and loose file; `MHUC_DUMPS=… pytest -m game_files -k xfs`
  (`test_every_mh3u_xfs_file_reads`, `test_mh4u_ships_no_texlayout_and_its_xfs_files_read`) parses the
  known XFS classes and the loose files again and checks the counts. Pass: every file parses, every object
  using exactly its size and the root ending the file, and the counts are:
  - MH3U: 845 files, all little-endian, all read. 543 in ARCs: 285 `rTexLayout` (the quest cockpit
    layouts), 169 `rStageData`, 27 `rStageCamera`, 26 `rSoundAttributeSe`, 17 `rDemoFade`,
    17 `rDemoListeningPoint`, 1 `rQuestList` and 1 `rAinpc`. 302 loose: 196 `.supp`, 105 `.pop` and
    1 `.list`. Versions 15.1 (545 files), 15.2 (274) and 15.3 (26).
  - MH4U: 8 files, all `rSoundAttributeSe`, version 15.3, all read. No `.supp`, `.pop`, `.list` and no
    `rTexLayout`: the test's scan of every ARC entry finds none, and its HUD layouts are
    `rLayout` (`.lyt`, such as `eng\lyt\quest\ui200`), laid out in [lyt.md](lyt.md).
  The three little-endian differences the check settled: a class definition's property count is the count
  itself, a property's size is a u16 in the file's byte order, and an object's class word is
  `class index << 1 | 1`.
