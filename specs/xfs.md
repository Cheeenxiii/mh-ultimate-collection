---
class: rSuppItem, rPopData, rQuestList, rStageData, rTexLayout and others (any class serialised with XFS)
extension: supp, pop, list, and XFS entries inside ARCs
games: MH3U (Wii U documented; 3DS by the same magic); MH4U and MHXX not checked
status: unknown
---

# XFS: MT Framework's serialised objects

XFS writes an object the way the class's `createProperty()` describes it, schema first: one definition per class (its DTI id and property list), then the root object. A reader needs no per-class code. In MH3U, `.supp` (`rSuppItem`, quest supply boxes), `.pop`, `.list` (`rQuestList`) and several ARC classes use it.

Source: BoyClinton's Cha-Cha (`docs/formats/xfs.md`, GPL-3.0), written for MH3U on Wii U and checked there on 848 of 848 files. That build is big-endian. The 3DS RomFS's `.supp` files start with the bytes `XFS\0` (quest.md check Q1): the same magic value read as a little-endian u32, so the 3DS files are presumably the same format in little-endian. Reader: `mhuc xfs dump FILE` (`src/mhuc/xfs.py`); it takes the byte order from the magic.

## Header (0x18 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | magic 0x00534658: bytes `XFS\0` on 3DS, `\0SFX` on Wii U | verified | Cha-Cha xfs.md; quest.md check Q1 (3DS bytes) |
| 0x04 | u16, u16 | version 15, sub-version 1 or 2 | unverified | Cha-Cha xfs.md |
| 0x08 | u32 | unknown (6 in Cha-Cha's sample) | unknown | Cha-Cha xfs.md |
| 0x0C | u32 | unknown (0) | unknown | Cha-Cha xfs.md |
| 0x10 | u32 | number of class definitions n | unverified | Cha-Cha xfs.md |
| 0x14 | u32 | size of the definition block, counted from 0x18 | unverified | Cha-Cha xfs.md |
| 0x18 | u32 ×n | offsets of the class definitions, from 0x18 | unverified | Cha-Cha xfs.md |

## Class definition

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | DTI id (`~crc32(name) & 0x7FFFFFFF`, as `mhuc classid`) | unverified | Cha-Cha xfs.md |
| +0x04 | u16, u16 | property count × 2, then 0 | unverified | Cha-Cha xfs.md |
| +0x08 | 0x28 bytes ×count | properties: u32 name offset (from 0x18, NUL-terminated ASCII); a packed word of u8 type, u8 attr, u16 size (value bytes × 2); 0x20 zero bytes (runtime slots). On a little-endian file the packed word is read as one u32 (an assumption: check X1) | unverified | Cha-Cha xfs.md |

## Objects (from 0x18 + the definition block's size)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u32 | 0x8000 ORed with the class index in the high half, instance id in the low half (read as one u32: check X1) | unverified | Cha-Cha xfs.md |
| +0x04 | u32 | size, counting itself: bytes from this field to the object's end | unverified | Cha-Cha xfs.md |
| +0x08 | per property | u32 count, then that many values (attr bit 0x20 = array; a scalar has count 1) | unverified | Cha-Cha xfs.md |
| value | by type | 0x01/0x02 nested object; 0x03 bool, 0x04 u8, 0x05 u16, 0x06 u32, 0x09 s16, 0x0A s32, 0x0C f32 at their sizes; 0x0E string (NUL-terminated); 0x0F color 4 bytes; 0x11 size 2×u32; 0x12 rect 4×u32; 0x14/0x15 vector3/vector4 4×f32; 0x40 8 bytes; 0x80 resource: u8 kind, kind 2 = class name and path, NUL-terminated | unverified | Cha-Cha xfs.md |

## Open questions

- Attr bits other than 0x20 (0x80, 0x01, 0x91 seen on Wii U).
- Not every registered property is written (Cha-Cha: `rPopData` registers a type-0x19 `DataList` the files lack).
- Whether MH4U and MHXX use XFS anywhere. MHXX's quest supply lists (`supp_N`, class 0x54539AEE) are not XFS: they start with a float 1.0, the layout mhff's wiki gives for MHX's `rSupplyList`.

## Checks

- **X1 (open):** run `mhuc xfs dump` over the MH3U 3DS RomFS's 196 `.supp`, 105 `.pop` and 4 `.list` (and the XFS entries in ARCs). Pass: every file parses with every object using exactly its size and nothing left over; then the packed-word readings above are verified for little-endian files. If they fail, try reading the packed words as separate fields in file order. Needs the MH3U RomFS.
