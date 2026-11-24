# Porting a 3U or GU monster into MH4U: the pipeline

**Point:** a monster port is the mod's biggest unit of work: model, animations, AI, data, behaviour code, quests and content, each from the monster's own game (rule 2). This doc lays the pipeline out step by step, with what we have for each step and what's missing. It follows MHGU Definitive Edition's porting guide (`notes/porting-guide.md`, GPL-3.0-or-later), which has finished ten MH4U-to-MHGU ports, turned the other way. Which monsters, which versions and in what order belong to the open decisions (rule 6).

## Why the 3DS sources make it shorter than MHGU-DE's path

MHGU-DE converts 3DS assets to Switch ones: models from MOD 0xE6 to 0xD4, textures from ETC1 to BC, materials from MRL 0x20 to 0x22. Our sources are 3DS games like MH4U. Check M1 found the same MOD version (0xE6) and header shape in MH4U, MH3U and MHXX, and specs/tex.md describes one TEX container for all three (its format checks T1 to T3 ran on MH4U only). By MHGU-DE's notes, LMT version 67 and EMC are unchanged even between 4U and Switch GU, so 3DS-to-3DS is likely closer still (checks L1 and A1 say for sure). The conversion work concentrates on data (monster tables), behaviour code and content.

## The pipeline

| Step | What | MHGU-DE's way (4U to GU) | Ours (3U/XX to 4U) | Status here |
|---|---|---|---|---|
| 0. Identify | the source monster's number and files; a close MH4U "donor" (skeleton, behaviour) for templates and fallbacks; its arena | reads the 4U quests' boss ids; donor Kushala for Gogmazios | source ids from the source quests (`mhuc idnames`, Q22); donor among MH4U's monsters (catalog overlap.md) | tools ready; choices open |
| 1. Study the source class | DTI, vtable, action dispatch, AI tables, engine calls | 4U class read statically; engine calls mapped 4U to GU through a monster both games have | the MH3U and MHXX reference recompiles (every function, docs/design/reference-recompiles.md); Cha-Cha's names for MH3U; engine calls mapped to MH4U's through a shared monster (Rathalos/Rathian are in all three); MHXX's monster code is in CRO modules, outside the recompile | Rathian's engine calls grouped by class (step 1 results below): 130 of its 197 MH4U callees are `uEnemy`'s; 63 placed in MHXX (51 confirmed by its import table), 39 in MH3U; `roEm001`'s 330 imports grouped by MHXX class, 262 with no MH4U counterpart; MH3U runs Rathian on `uEm002`; all 109 MHXX modules recompiled and tested against the original (fork `tools/recompile_module.py`, `recomp.modtest`) |
| 2. Assets | models, textures, materials, animations, effects, sounds, cameras | ~10 converters (`mod4u2gu`, `tex`, `mrl_build`, `efl4u2gu`, `snd4u2gu`, `lcm4u2gu`); LMT and EMC copied as they are | MOD and TEX likely as they are (M1; T1 to T3 on MH4U, to repeat on the others); LMT and EMC: MHXX's are MH4U's versions (LMT 67, EMC 0x20120804; L1, A1), MH3U's older (LMT 66, EMC 0x20110601); collision: MH3U shares MH4U's SBC class, MHXX has another (S1); MRL, effects, sounds and cameras unexamined | specs: arc, tex, mod (partial), lmt, emd; MRL/EFL/sound none |
| 3. Monster data | hurt and attack volumes, hitzones, parts, breaks, stats, AI sensors | 4U `.emd`/`.etd` to GU `bodydata`/`hitsize`/`attackdata`/`dtbase`/`dttune` per header word (`emdata4u.py`, `dt_convert.py`), checked by rebuilding GU's own files | the reverse mapping: MHXX's GU-style files (if MHXX 3DS uses them; to check) or MH3U's own format to MH4U `.emd`/`.etd`; check by rebuilding a shared monster's MH4U pair from its source files | MH4U side: specs/emd.md (E1 open); source sides unknown |
| 4. Register | a new monster id, its tables, its file ids | an id allocation file and a C module that grows GU's registry tables and patches their bounds | id-tables.md's "Bounds to move" (the factory, the path index, crowns, drops, list order, icons, names) grown by a plugin; the save's 82-entry monster log is fixed-size (id-tables.md) | bounds listed; the first table-growing plugin is STATUS task 5 |
| 5. Behaviour | one handler per source action, translated in the source's call order, with its frame values | C reimplementation of each 4U handler on GU's framework, with a test aid that forces the AI's next action | C handlers in the fork's plugin layer on MH4U's `uEnemy` (settled 2026-11-24: ported, not run on the source engine), translated from the source recompile's functions; for GU, the module recompile gives them as C checked against the original | plugin layer exists (plugin-api.md); no monster yet |
| 6. Quests, arena, UI | the monster's quests, its arena, its name and icon | quest builder from 4U quests; arenas as stage aliases | `mhuc convert quest` (MHXX); Extra Data or quest archives as routes (extra-data.md); a 3U arena is a stage port | quest pipeline built; stages not started |
| 7. Content | materials, carves, rewards, gear, skills, Hunter's Notes | a data file per monster that the module patches into the loaded tables; added ids only; its own save file for added data | the same pattern fits: added records, never replaced; a separate mod save beside MH4U's (MHGU-DE keeps `mhgu_de_<slot>.bin`) | design only |
| 8. Test loop | build, play, read the log | rebuild from the dumps, the maintainer plays, a log reader reports | the port's headless runner and Azahar; docs/checks/ procedures per step | runner exists (plugin-api.md, in-game check) |

## Step 1 results: Rathian (2026-11-23)

Tools in the engine fork, branch `uc/monster-port-step1`: `tools/cro.py` (CRO modules) and `tools/fnmap.py` (function maps between games). Its `config/games/README.md` has the commands. Everything below is addresses and counts.

**Where Rathian's code is.**

| | MH4U v1.3.0 | MHXX v1.4 | MH3U |
|---|---|---|---|
| Class | `uEm001` < `uEnemy` | `uEm001_00` < `uFestaEnemy` < `uEnemy` < `uEnemyBase` | no `uEm001`; `uEm002` (0x1f68) holds an `Em001JointCallback` |
| Code | in `code.bin`: 122 functions, 21,713 instructions, one block at 0x6d4f80–0x6ec8dc | in `roEm001.cro`, not `code.bin`: 265 functions, 32,700 instructions | not isolated yet |
| Engine it calls | 197 functions (1,350 calls and references) | 392 imports from static: 330 functions, 22 data; its code calls 220 static addresses through veneers | |

- **MHXX keeps its monsters in modules.** 109 CRO modules in RomFS (each large and small monster, the 16 weapon types, village, quest, title...), 6.5 MB of code in all. The MHXX reference recompile covers `code.bin` only, so it has **no monster behaviour code**. All 109 load with `tools/cro.py`, and the analyser reads `roEm001` with no problems. Recompiling and linking modules is the missing piece for step 5 of any GU monster.
- **MH4U's own code for Rathian** is what only Rathian refers to: the closure from its vtable's 25 overridden slots (of 97), minus anything a function outside the set also calls (a workspace script for now, not yet in the tools). Its DTI's `newInstance` is slot 2 of the DTI vtable, which gives the instance vtable.
- **MH3U's Rathian class** is open: the registry has `uEm002` but no `uEm001`, while RomFS has both `em001.arc` and `em002.arc`. The enemy factory will say which class em001 gets.

**The two Rathians don't pair function by function.** With register-free instruction tokens, 16 of MH4U's 122 functions find an MHXX function at ratio ≥ 0.6. By shared constants (floats, motion and frame values), 13 of 110 do. MHXX's Rathian code was largely rewritten, split into more and smaller functions. So "map engine calls through a shared monster", as MHGU-DE did it, works here only at the boundary: map the engines directly, then use the monster's own call list (and MHXX's import table) to pick and check what matters.

**The engine map.** Anchors are functions whose normalised body is unique and identical in both games. Calls at aligned positions in mapped pairs then place their callees.

| MH4U against | Anchors | After propagation | Held-out anchors recovered | of those correct |
|---|---|---|---|---|
| MHXX v1.4 static | 1,805 | 3,433 | 151 of 516 | 100% |
| MH3U | 2,582 | 3,930 | 112 of 361 | 99.1% |

Anchors and propagation cover core and library code well, and the enemy layer badly: only 8 of Rathian's 197 callees. MHXX restructured that layer (`uEnemyBase`, `uEnemyCharacter`), and MH3U's `uEnemy` is a quarter of MH4U's size. Similarity fills part of the gap: the best candidate by alignment ratio, taken only when clear (≥ 0.7 and 0.1 ahead of the next), agrees with propagation in 94% of cases for MHXX (151/160) and 99% for MH3U (132/133). Unclear best matches are right about half the time and aren't used.

**Rathian's engine calls, mapped** (`fnmap.py map` with `--similar` on Rathian's 197 callees; whole maps of 3,540 pairs with MHXX and 3,967 with MH3U):

| | MH4U callees placed | Calls and references covered | Check |
|---|---|---|---|
| in MHXX | 60 of 197 (35 by similarity, 21 by propagation, 4 identical) | 540 of 1,350 (40%) | 48 of the 60 land on functions `roEm001` imports |
| in MH3U | 37 of 197 (29 by similarity, 4 by propagation, 4 identical) | 261 of 1,350 (19%) | none independent yet |
| MHXX → MH4U | 54 of `roEm001`'s 330 imported functions have an MH4U counterpart in the map | | |

The 48 are the strongest result: MHXX's import table comes from the loader, so it confirms those matches without relying on similarity. The 276 imported functions with no MH4U counterpart are the MHXX engine behaviour a GU Rathian depends on and MH4U may lack. They're the list to study for step 5: shim, port, or find by other means.

**Next for step 1** (all done on 2026-11-24, below):
1. ~~Vtables of the classes both games name, slot by slot, as anchors.~~
2. ~~Group the 276 unplaced MHXX imports by class and vtable slot.~~
3. ~~MH3U: find em001's class through the enemy factory, then isolate its code.~~
4. ~~Module recompiles for MHXX.~~ Done: see "Module recompiles" below.

## Step 1 continued: classes and vtables (2026-11-24)

Tools in the engine fork, branch `uc/monster-port-classes`: `tools/mt_vtables.py` (every class's instance vtable) and `fnmap.py map --vtables` (slot alignment). The fork's `config/games/README.md` has the commands and the accuracy checks. Everything below is names, counts and addresses.

**Every class's vtable.** Each DTI's `newInstance`, emulated with a fake allocator, runs the class's constructors, and each stores its vtable in the new object. That gives the class's own vtable and its bases' in order. Abstract classes take theirs from their subclasses' chains. CRO modules load beside `code.bin`, so MHXX's monster classes resolve too. Found: 982 of 991 classes in MH4U, 3,103 of 3,109 in MHXX (with its 109 modules), 1,208 of 1,218 in MH3U.

| Enemy hierarchy, slots per vtable | | | | |
|---|---|---|---|---|
| MH4U | `uMHchar` 38 | `uEnemy` 95 | `uEm001` 95 | |
| MH3U | `uCharacter` 42 | `uEnemy` 82 | `uEm002` 82 | |
| MHXX | `uEnemyCharacter` 79 | `uEnemyBase` 118 | `uEnemy` 283 | `uFestaEnemy` 287, `uEm001_00` 293 (in `roEm001`) |

MHXX's `uEnemy` has three times MH4U's virtual methods, and two classes MH4U lacks sit on either side of it (`uEnemyBase` below, `uFestaEnemy` above).

**Vtables as anchors.** For each class both games name (625 MH4U/MHXX, 584 MH4U/MH3U), the slots are aligned in order and pairs that look alike are mapped. Then a slot between two mapped slots at equal distances in both games is mapped by position. The whole maps double:

| MH4U against | Pairs before | Pairs now | Held-out anchors recovered (30%, seed 1) | correct |
|---|---|---|---|---|
| MHXX v1.4 static | 3,540 | 7,542 | 281 of 541 (172 without vtables) | 100% |
| MH3U | 3,967 | 6,866 | 515 of 774 (273 without) | 100% |

Position alone is right for 97.9% (MHXX) and 99.5% (MH3U) of mapped slots, left out one at a time. `uEnemy`'s own slots 30 to 88 line up one for one with MHXX's slots 65 to 243. Its big functions (the per-frame update, 2,313 instructions in MH4U) don't match anything, by likeness or by position.

**Rathian's MH4U engine calls by class.** Each callee is labelled with the class whose vtable first introduces it, or for a non-virtual function, the nearest common ancestor of its callers' classes (a heuristic):

| MH4U class | Callees | Calls | Placed in MHXX | in MH3U |
|---|---|---|---|---|
| `uEnemy` | 130 | 983 | 40 | 27 |
| `uCoord` (position, transforms) | 13 | 101 | 5 | 2 |
| `uEm001` (its own slots, also called from outside) | 18 | 70 | 2 | 1 |
| other monsters' classes (`uEm032`, `uEm103`, `uEm068`, `uEm089`...; code they share with Rathian) | 19 | 129 | 9 | 3 |
| `uMHchar` | 6 | 37 | 1 | 1 |
| `cUnit` | 2 | 19 | 2 | 1 |
| `MtObject` and the rest | 9 | 11 | 4 | 4 |
| **All** | **197** | **1,350** | **63** (550 calls; 51 land on `roEm001` imports) | **39** (302 calls) |

The vtables added three callees for MHXX (60 → 63) and two for MH3U (37 → 39): Rathian calls `uEnemy`'s non-virtual helpers, not its slots, and those were rewritten. The slot map does place the enemy layer's virtual methods, which step 5 dispatches through.

**What a GU Rathian needs from MHXX's engine.** `roEm001` imports 330 static functions. By MHXX class, with how many have an MH4U counterpart in the map:

| MHXX class | Imports | With MH4U counterpart | Without | Class in MH4U? |
|---|---|---|---|---|
| `uEnemy` | 93 | 9 | 84 | yes, much smaller |
| `uFestaEnemy` | 26 | 0 | 26 | no |
| `uFestaChar` | 24 | 3 | 21 | no |
| `uEmXXX` (the template enemy) | 19 | 17 | 2 | yes |
| `uShell` and `uShellEnemy`, `uShellEmBase*`, `uShellPlayer` (projectiles) | 50 | 2 | 48 | `uShell` only |
| `uEnemyBase`, `uEnemyCharacter`, `uEnemyActCustom`, `uEnemyOption` | 23 | 2 | 21 | no |
| `cUnit`, `MtObject` | 24 | 17 | 7 | yes |
| others (`uMonsterUnitConductor`, `sHitcheck`, `sHitPush`, `uPlayerQuest`, `uPlayerLobby`) | 9 | 1 | 8 | partly |
| no class (library and free functions) | 62 | 17 | 45 | |
| **All** | **330** | **68** | **262** | |

So a GU monster ported as its own code needs, besides MH4U's `uEnemy`, most of MHXX's enemy layer: `uFestaEnemy`, `uFestaChar` and `uEnemyBase` are classes MH4U doesn't have, and GU's projectiles are a class family of their own. That decides step 5's shape. The maintainer settled it on 2026-11-24 (open-decisions.md, "Monster ports"): each GU handler is reimplemented on MH4U's `uEnemy`, as MHGU-DE does the other way. MHXX's enemy layer doesn't come along. The 262 imports are the GU engine calls each translated handler must express with MH4U's engine.

**MH3U's Rathian is `uEm002`.** MH3U's enemy factory (`0x005bbc5c`, 86 ids; id-tables.md has the whole id-to-class table) builds ids 1, 2 and 62-65 (Rathian, Rathalos and the colour variants) with `uEm002`. `uEm002`'s slot 14 names their files by id. MH4U does the reverse, with all six on `uEm001`. `uEm002`'s own code is small: it overrides 26 slots and owns 35 functions (5,545 instructions), against MH4U `uEm001`'s 24 slots and 137 functions (22,729 instructions). Its engine calls go to 71 functions (312 calls), 50 of them `uEnemy`'s (253 calls). Only 13 of the 71 have an MH4U counterpart, and 11 of those are functions MH4U's Rathian calls too. Aligning `uEm001`'s slots with `uEm002`'s maps 3 of Rathian's own functions; aligning them with MHXX's `uEm001_00` in `roEm001` maps 13. The three Rathians are three codebases, as the token comparison already said.

## Module recompiles (2026-11-24)

Monsters are ported onto MH4U's engine (open-decisions.md, "Monster ports"), so a GU monster's module is the reference a port translates, handler by handler. The fork now recompiles all 109 MHXX modules at fixed bases into one library with the static code (`tools/recompile_module.py`) and tests every module function against the original in Unicorn (`recomp.modtest`). All 109 modules (36,662 functions) gametest with no differences in state, memory or exit: 20,746 pass and 15,697 fault the same way in both; 40 functions are left on missing entry points and veneer edge cases, with fixes in and a full rerun to do. Rathian's module alone: 454 functions (veneers counted), 289 pass and 160 fault the same way in both, with no differences.

Two things came out of it for the static side. 956 static functions are called only from modules, so a recompile of `code.bin` alone never had them; they're now extra entry points. And the analyser gave different C from run to run (a set iterated in hash order); it now queues functions in address order.

**Next, towards step 5** (preparing Rathian's port as the first one):
1. Rathian's action inventory in each source: MH4U's `uEm001` dispatches through a 98-case `switch` (84 distinct targets) in a function reached from 0x6e9cac; MHXX's and MH3U's dispatch are still to find. Done when each source's actions are listed with their handler functions.
2. For each GU engine call Rathian's handlers make (the 262 with no MH4U counterpart, by class above), the MH4U way to do the same. Done when every one is mapped, or listed as something MH4U lacks.
3. The source's monster data (step 3) for Rathian, MHXX's and MH3U's.

## Lessons worth carrying over (from MHGU-DE's notes, 2026-11)

- **Keep the source's bone ids and remap table.** Then the monster data needs no bone remap, except where a bone is missing from the target skeleton.
- **A handler that never ends its action freezes the AI.** Translate the source handlers literally, timers and all.
- **Ids only ever grow.** Never move an installed monster's ids: saves and quests keep them (id-tables.md).
- **Add, never replace.** No shipped file should be a copy of a game file another mod might also ship; patch the loaded resource instead.
- **Check a converted file by rebuilding the target game's own file** for a monster both games have, then count equal bytes. MHGU-DE reaches 95 to 99.7 % on the volume tables this way; the remainder points at real format differences.
