---
class: rEnemyCmd
extension: emc
games: MH4U and MHXX (version 0x20120804); MH3U (version 0x20110601, not laid out)
status: unverified
---

# EMC: enemy AI scripts

A monster's AI: top-level selectors and action scripts in a bytecode. A converted monster brings its own.

**Source.** MHGU Definitive Edition, `tools/emc.py` (GPL-3.0-or-later). Its bytecode reading is partial and inferred. Class id `0x3aabba02` (MH4U registry).

## Header

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `EMC\0` | verified | MHGU-DE `emc.py`; check A1 |
| 0x04 | u32 | version | verified | check A1 |
| 0x08 | u32 | group count | unverified | MHGU-DE `emc.py` |
| 0x0C | u32 | zero | unverified | MHGU-DE `emc.py` |
| 0x10 | {u32 count, u32 offset, u32, u32} × groups | group table | unverified | MHGU-DE `emc.py` |

Each group points at script entries `{u32 length, u32 offset, 0, 0}`. Scripts are byte strings padded to 16. Group 0 holds the top-level selectors, group 1 the action scripts.

Opcodes as MHGU-DE reads them: `00 cat num` starts a native action of the monster class, `14 nn` runs action script `nn`, `02 …` is a weighted random choice. The others open condition blocks.

## Checks

- **A1 (done):** `mhuc survey` reads every `rEnemyCmd`. All have magic `EMC\0` and their tables inside the file. MH4U: 124 files, version 0x20120804, 13,501 scripts. MHXX: 139 files, the same version, 19,424 scripts. MH3U: 91 files, version **0x20110601**, 6,864 scripts, same header shape. GU monsters' AI shares MH4U's version; MH3U's is older.
