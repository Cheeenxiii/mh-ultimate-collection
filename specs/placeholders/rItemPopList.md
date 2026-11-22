---
class: rItemPopList
extension: ipl
games: MH4U (registry); MH3U and MHXX to find
status: unknown
---

# rItemPopList (stage)

Placeholder: only the class is known. MH4U's class registry (MH4UltimateDC `config/mt_classes.tsv`) lists it under `cResource`, class id `0x25fd693f`, resource object size 0x88 bytes (the loaded object, not the file).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | file layout unknown | unknown | MH4UltimateDC config/mt_classes.tsv (class only) |

## To find out

- Its file extension and where its files are in the RomFS (an ARC listing with `mhuc arc list` shows the class id).
- Its loader: the class's `load` virtual, found from the registry's DTI address in Ghidra; the fields it reads give the layout.
- Whether MH3U and MHXX have the same class (their reference recompiles' registries, docs/design/reference-recompiles.md).
