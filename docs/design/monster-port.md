# Porting a 3U or GU monster into MH4U: the pipeline

**Point:** a monster port is the mod's biggest unit of work: model, animations, AI, data, behaviour code, quests and content, each from the monster's own game (rule 2). This doc lays the pipeline out step by step, with what we have for each step and what's missing. It follows MHGU Definitive Edition's porting guide (`notes/porting-guide.md`, GPL-3.0-or-later), which has finished ten MH4U-to-MHGU ports, turned the other way. Which monsters, which versions and in what order belong to the open decisions (rule 6).

## Why the 3DS sources make it shorter than MHGU-DE's path

MHGU-DE converts 3DS assets to Switch ones: models from MOD 0xE6 to 0xD4, textures from ETC1 to BC, materials from MRL 0x20 to 0x22. Our sources are 3DS games like MH4U. Check M1 found the same MOD version (0xE6) and header shape in MH4U, MH3U and MHXX, and specs/tex.md describes one TEX container for all three (its format checks T1 to T3 ran on MH4U only). By MHGU-DE's notes, LMT version 67 and EMC are unchanged even between 4U and Switch GU, so 3DS-to-3DS is likely closer still (checks L1 and A1 say for sure). The conversion work concentrates on data (monster tables), behaviour code and content.

## The pipeline

| Step | What | MHGU-DE's way (4U to GU) | Ours (3U/XX to 4U) | Status here |
|---|---|---|---|---|
| 0. Identify | the source monster's number and files; a close MH4U "donor" (skeleton, behaviour) for templates and fallbacks; its arena | reads the 4U quests' boss ids; donor Kushala for Gogmazios | source ids from the source quests (`mhuc idnames`, Q22); donor among MH4U's monsters (catalog overlap.md) | tools ready; choices open |
| 1. Study the source class | DTI, vtable, action dispatch, AI tables, engine calls | 4U class read statically; engine calls mapped 4U to GU through a monster both games have | the MH3U and MHXX reference recompiles (every function, docs/design/reference-recompiles.md); Cha-Cha's names for MH3U; engine calls mapped to MH4U's through a shared monster (Rathalos/Rathian are in all three) | recompiles done; mapping not started |
| 2. Assets | models, textures, materials, animations, effects, sounds, cameras | ~10 converters (`mod4u2gu`, `tex`, `mrl_build`, `efl4u2gu`, `snd4u2gu`, `lcm4u2gu`); LMT and EMC copied as they are | MOD and TEX likely as they are (M1; T1 to T3 on MH4U, to repeat on the others); LMT and EMC to confirm (L1, A1); MRL, effects, sounds and cameras unexamined | specs: arc, tex, mod (partial), lmt, emd; MRL/EFL/sound none |
| 3. Monster data | hurt and attack volumes, hitzones, parts, breaks, stats, AI sensors | 4U `.emd`/`.etd` to GU `bodydata`/`hitsize`/`attackdata`/`dtbase`/`dttune` per header word (`emdata4u.py`, `dt_convert.py`), checked by rebuilding GU's own files | the reverse mapping: MHXX's GU-style files (if MHXX 3DS uses them; to check) or MH3U's own format to MH4U `.emd`/`.etd`; check by rebuilding a shared monster's MH4U pair from its source files | MH4U side: specs/emd.md (E1 open); source sides unknown |
| 4. Register | a new monster id, its tables, its file ids | an id allocation file and a C module that grows GU's registry tables and patches their bounds | id-tables.md's "Bounds to move" (the factory, the path index, crowns, drops, list order, icons, names) grown by a plugin; the save's 82-entry monster log is fixed-size (id-tables.md) | bounds listed; the first table-growing plugin is STATUS task 5 |
| 5. Behaviour | one handler per source action, translated in the source's call order, with its frame values | C reimplementation of each 4U handler on GU's framework, with a test aid that forces the AI's next action | C handlers in the fork's plugin layer on MH4U's `uEnemy`, from the source recompile's functions (which the recompile already provides as C) | plugin layer exists (plugin-api.md); no monster yet |
| 6. Quests, arena, UI | the monster's quests, its arena, its name and icon | quest builder from 4U quests; arenas as stage aliases | `mhuc convert quest` (MHXX); Extra Data or quest archives as routes (extra-data.md); a 3U arena is a stage port | quest pipeline built; stages not started |
| 7. Content | materials, carves, rewards, gear, skills, Hunter's Notes | a data file per monster that the module patches into the loaded tables; added ids only; its own save file for added data | the same pattern fits: added records, never replaced; a separate mod save beside MH4U's (MHGU-DE keeps `mhgu_de_<slot>.bin`) | design only |
| 8. Test loop | build, play, read the log | rebuild from the dumps, the maintainer plays, a log reader reports | the port's headless runner and Azahar; docs/checks/ procedures per step | runner exists (plugin-api.md, in-game check) |

## Lessons worth carrying over (from MHGU-DE's notes, 2026-11)

- **Keep the source's bone ids and remap table.** Then the monster data needs no bone remap, except where a bone is missing from the target skeleton.
- **A handler that never ends its action freezes the AI.** Translate the source handlers literally, timers and all.
- **Ids only ever grow.** Never move an installed monster's ids: saves and quests keep them (id-tables.md).
- **Add, never replace.** No shipped file should be a copy of a game file another mod might also ship; patch the loaded resource instead.
- **Check a converted file by rebuilding the target game's own file** for a monster both games have, then count equal bytes. MHGU-DE reaches 95 to 99.7 % on the volume tables this way; the remainder points at real format differences.
