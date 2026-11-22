---
class: rQuestData, rSetEmMain, rEmSetList, rRem, rGUIMessage
extension: mib, sem, esl, rem, gmd
games: MH4U (mib), MHX/MHXX (sem, esl, rem, mib), MH3U (to find)
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
| `.gmd` | rGUIMessage | all | quest name, client, description (see [gmd](gmd.md)) |

Class names and extensions come from mhff's table. MH4U's registry (MH4UltimateDC `config/mt_classes.tsv`) has `rQuestData` and `rQuestInfoTbl` but no `rSetEmMain`, `rEmSetList` or `rRem`: in MH4U the monster sets and rewards live inside `.mib`.

## rQuestData (MH4U .mib)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | arc | a quest is one ARC whose last entry is the `.mib` | unverified | mhff convert_quest.py |
| whole | bytes | DLC quests are encrypted (Blowfish, per mhef) | unverified | svanheulen/mhef |
| 0x00 | ? | layout unknown here | unknown | — |

## rSetEmMain, rEmSetList, rRem

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | layout unknown here | unknown | mhff (names and extensions only) |

## Open questions

- MH4U's `.mib` layout: community quest editors exist for MH4U event quests; their field lists are the next public source to read (credit them here).
- MH3U's quest format, and where its quest ARCs are in the RomFS.
- How MHXX's `.sem`/`.esl`/`.rem` map onto `.mib` sections.

## Checks

- **Q1 (with game files):** list MH4U's quest ARCs and confirm that the last entry is always `.mib`.
- **Q2 (with game files):** for MHXX, list which of `.mib`, `.sem`, `.esl`, `.rem` each quest ARC holds.
