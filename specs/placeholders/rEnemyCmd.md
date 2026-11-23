---
class: rEnemyCmd
extension: emc
games: MH4U (registry); MH3U and MHXX to find
status: unknown
---

# rEnemyCmd (enemy)

**A layout exists** in MHGU Definitive Edition's `tools/emc.py` (GPL-3.0-or-later): `EMC\0`, version 0x20120804, the same in MH4U and MHGU; a 16-byte header (magic, version, group count, 0), then per group {u32 count, u32 offset, 0, 0}, each pointing at script entries {u32 length, u32 offset, 0, 0}; scripts are byte strings padded to 16. Group 0 holds the top-level AI selectors, group 1 the action scripts. Its bytecode reading is partial and inferred (`00 cat num` starts a native action of the monster class, `14 nn` runs action script nn, `02 …` a weighted random choice, other opcodes condition blocks). Unverified on our files. This is the monster AI a converted monster brings along, so its MH3U and MHXX counterparts matter.

Placeholder: only the class is known. MH4U's class registry (MH4UltimateDC `config/mt_classes.tsv`) lists it under `cResource`, class id `0x3aabba02`, resource object size 0xc8 bytes (the loaded object, not the file).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | file layout unknown | unknown | MH4UltimateDC config/mt_classes.tsv (class only) |

## To find out

- Its file extension and where its files are in the RomFS (an ARC listing with `mhuc arc list` shows the class id).
- Its loader: the class's `load` virtual, found from the registry's DTI address in Ghidra; the fields it reads give the layout.
- Whether MH3U and MHXX have the same class (their reference recompiles' registries, docs/design/reference-recompiles.md).
