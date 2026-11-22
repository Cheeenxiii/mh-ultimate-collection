---
class: rQuestData, rSetEmMain, rEmSetList, rRem, rGUIMessage
extension: mib, sem, esl, rem, gmd
games: MH4U (mib), MHX/MHXX (sem, esl, rem, mib), MH3U (quest, quest_btl, supp)
status: unknown
---

# Quest files (partial)

How a quest is put together differs between the games, and the mod needs to translate 3U and GU quests into MH4U's form. This spec records what is known and what isn't.

| File | Class | Game | What it holds |
|---|---|---|---|
| `.mib` | rQuestData | MH4U, MHX/MHXX (rGuestQuestData) | the quest: map, monsters, objectives, rewards, text ids |
| `.sem` | rSetEmMain | MHX/MHXX | monster placement for a quest (large monsters) |
| `.esl` | rEmSetList | MHX/MHXX | small-monster sets per area |
| `.rem` | rRem | MHX/MHXX (rGuestRemData) | reward tables |
| `.gmd` | rGUIMessage | MH3U, MHXX | quest name, client, description (see [gmd](gmd.md)); MH4U has no GMDs |
| `.quest` | ? | MH3U | loose files under `/quest/us/` (365), magic `QTDS` |
| `.quest_btl` | ? | MH3U | loose files under `/quest/btl/` (353), magic `QTDB` |
| `.supp` | ? | MH3U | loose files under `/quest/support/` (196), magic `XFS\0` (MT's serialised-object format) |

Class names and extensions come from mhff's table. MH4U's registry (MH4UltimateDC `config/mt_classes.tsv`) has `rQuestData` and `rQuestInfoTbl` but no `rSetEmMain`, `rEmSetList` or `rRem`: in MH4U the monster sets and rewards live inside `.mib`.

## rQuestData (MH4U .mib)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | arc | the game's own quests: all `.mib` in two archives, `/loc/data/quest00.arc` (207) and `quest01.arc` (301), nothing else in them | verified | ours; check Q1 |
| file | arc | a DLC quest is one ARC whose last entry is the `.mib` | unverified | mhff convert_quest.py |
| whole | bytes | DLC quests are encrypted (Blowfish, per mhef) | unverified | svanheulen/mhef |
| 0x00 | ? | layout unknown here | unknown | — |

## rSetEmMain, rEmSetList, rRem

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | layout unknown here | unknown | mhff (names and extensions only) |

## Open questions

- MH4U's `.mib` layout: community quest editors exist for MH4U event quests; their field lists are the next public source to read (credit them here).
- MH3U's quest format: loose `QTDS`/`QTDB` files and `XFS` support files, not ARCs (check Q1). Their layouts are unknown; `XFS` is MT's generic serialisation, which may make `.supp` readable from the class registry.
- How MHXX's `.sem`/`.esl`/`.rem` map onto `.mib` sections.

## Checks

Run on 2026-11-23 with `mhuc survey` and `mhuc romfs list` on the maintainer's dumps (see [arc](arc.md#checks)).

- **Q1 (done):** MH4U keeps its quests in two archives that hold only `rQuestData`: 207 and 301 entries (the same in EUR). The four language folders' `core_quest.arc` hold the quest screens (effects, layouts, textures), no quest data. MH3U has no quest archives: 365 `.quest`, 353 `.quest_btl` and 196 `.supp` files lie loose in the RomFS, plus quest screens in archives.
- **Q2 (done):** MHXX JPN has 1,335 archives with quest classes. 1,331 hold all four of `rQuestData`, `rSetEmMain`, `rEmSetList` and `rRem`; 3 hold only `rQuestData`; 1 holds only `rRem`. In 1,334 the last entry is the `rQuestData`. A quest is one archive in MHXX, as mhff describes for MH4U's DLC.
