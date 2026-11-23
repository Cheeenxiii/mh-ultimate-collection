---
class: rCollision
extension: sbc
games: MH4U (registry); MH3U and MHXX to find
status: unknown
---

# rCollision (stage)

**A layout exists** in MHGU Definitive Edition's `tools/sbc.py` (GPL-3.0-or-later), which reads MH4U's stage collision and converts it to MHGU's; its class id for the MH4U file, 0x51FC779F, is this class's. Summary, unverified on our files: magic `SBC\xff`, an inner class hash (0x77CF8DF8 in MH4U), counts of parts, attribute groups, polygons, triangles and vertices, a bounding box (header 0x48 bytes in MH4U); then one 0x48-byte record per part (a uniform grid each; indices local to the part), 28-byte polygon boxes, a `BVHC` block of 112-byte four-wide nodes over the parts, the grids, triangles and vertices, with no alignment between blocks. Stage conversion (3U and GU maps into MH4U) will need this; MH3U's and MHXX's own collision formats are still to find.

Placeholder: only the class is known. MH4U's class registry (MH4UltimateDC `config/mt_classes.tsv`) lists it under `cResource`, class id `0x51fc779f`, resource object size 0xd8 bytes (the loaded object, not the file).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | file layout unknown | unknown | MH4UltimateDC config/mt_classes.tsv (class only) |

## To find out

- Its file extension and where its files are in the RomFS (an ARC listing with `mhuc arc list` shows the class id).
- Its loader: the class's `load` virtual, found from the registry's DTI address in Ghidra; the fields it reads give the layout.
- Whether MH3U and MHXX have the same class (their reference recompiles' registries, docs/design/reference-recompiles.md).

## Checks

- **S1 (done, 2026-11-23):** every `rCollision` has magic `SBC\xFF`. MH4U: 626 files, all inner class 0x77CF8DF8 (as MHGU Definitive Edition says), 469 with one part, 157 with several. MH3U USA: 344, all **0x77CF8DF8** too (340 one part, 4 several): 3U stage collision is MH4U's class. MHXX JPN: 1,052, all **0x781ACA20**, another class (852 one part, 200 several), so GU collision needs its own layout or a conversion.
- *As first written:* `mhuc survey` counts every `rCollision`: its magic, inner class hash (0x77CF8DF8 in MH4U per MHGU Definitive Edition) and whether it has one part or several. MH3U's and MHXX's values say whether their stages' collision shares MH4U's layout.
