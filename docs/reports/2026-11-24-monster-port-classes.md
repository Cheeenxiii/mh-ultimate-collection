# Monster port, step 1 continued: classes and vtables (2026-11-24)

An unattended workspace session, the first under the one-area rule (PR #8). It took STATUS task 1: the rest of step 1 of [monster-port.md](../design/monster-port.md). That meant vtable anchors, `roEm001`'s unplaced imports grouped by class, and MH3U's Rathian class. Every job ran under the 6 GB cap and took seconds. Scratch scripts and outputs are in `game_files/work/mport/` (`s2/` for this session). The repositories got counts, names and addresses only.

## Done

| Task | Result | Where |
|---|---|---|
| Every class's vtable | new `tools/mt_vtables.py`: emulates each DTI's `newInstance` with a fake allocator and records the vtables the constructors store (own and bases'). Abstract classes take theirs from their subclasses' chains. CRO modules load beside `code.bin` with the static veneers resolved. Found: MH4U 982/991, MHXX 3,103/3,109 (109 modules), MH3U 1,208/1,218. `mt_dti.emulate` got an `after` hook | fork: `tools/mt_vtables.py`, `tests/test_mt_vtables.py`, `config/games/README.md` |
| Vtable anchors | `fnmap.py map --vtables`: slots of same-named classes aligned in order (ratio ≥ 0.6), then bracketed slots by position (ratio ≥ 0.3); `--class-pair` for differently named ones. Maps 3,540 → 7,542 (MHXX), 3,967 → 6,866 (MH3U). Held-out anchors (30%): 281/541 and 515/774 recovered (172 and 273 without), all correct. Position alone is right for 97.9% / 99.5% of mapped slots | fork: `tools/fnmap.py`, `tests/test_fnmap.py` |
| Rathian's MH4U engine calls by class | 130 of 197 callees (983 of 1,350 calls) are `uEnemy`'s; 63 placed in MHXX (51 on `roEm001` imports), 39 in MH3U. Vtables added only 3 and 2: Rathian calls `uEnemy`'s non-virtual helpers, which were rewritten | monster-port.md |
| `roEm001`'s imports by class | 330 imports, 68 with an MH4U counterpart. Without one: 84 `uEnemy`, 26 `uFestaEnemy`, 21 `uFestaChar`, 48 projectile classes (`uShell*`), 21 `uEnemyBase` and kin, 45 no class. Most of these classes don't exist in MH4U | monster-port.md |
| The enemy hierarchies | MH4U `uMHchar` 38 → `uEnemy` 95 slots; MH3U `uCharacter` 42 → `uEnemy` 82; MHXX `uEnemyCharacter` 79 → `uEnemyBase` 118 → `uEnemy` 283 → `uFestaEnemy` 287 → `uEm001_00` 293 | monster-port.md |
| MH3U's factory and Rathian | factory `0x005bbc5c`, 86 ids, whole id-to-class table; same search re-finds MH4U's `createEnemy`. Ids 1, 2, 62-65 run `uEm002` (slot 14 names their files by id). `uEm002` owns 35 functions (5,545 instructions) against MH4U `uEm001`'s 137 (22,729); 71 engine callees, 13 with an MH4U counterpart | id-tables.md, monster-port.md |

## What it changes for the plan

- **A GU monster brings MHXX's enemy layer with it, or gets rewritten on MH4U's.** `roEm001` depends on about 260 static functions with no MH4U counterpart, most in classes MH4U lacks (`uFestaEnemy`, `uFestaChar`, `uEnemyBase`, the GU projectile classes). Step 5 either recompiles those with each module or reimplements every handler on MH4U's `uEnemy`. That choice is open (open-decisions.md, "Monster versions"). The counts are in monster-port.md to inform it.
- **The three Rathians are three codebases.** Slot alignment maps 3 of MH4U Rathian's own functions to MH3U's `uEm002` and 13 to MHXX's `uEm001_00`. A port translates the source's handlers. It can't diff against MH4U's.
- **The function maps are now good enough to lean on** for the engine's virtual layer (the enemy classes' slots line up one for one). The rewritten non-virtual helpers are what stays unmapped.

## Not done

- MHXX module recompiles (STATUS task 2): the next area, fork recompiler work.
- The class labels for non-virtual functions (nearest common ancestor of the callers' classes) are a heuristic with no independent check. Label with care.
- One- and two-instruction slot stubs are mapped by alignment, and held-out anchors (12 tokens and up) don't test them.
- Isolating a class's own code and the per-class grouping are still workspace scripts (`s2/own.py`, `s2/rathian.py`), not tools.
- `mt_vtables.py` loads modules in the order given. `roEm001` lands at `0x02000000` only because it sorts first, which is the same base `fnmap.py side --module` uses. Pass `--module` lists with that in mind.

## Checklist for the next session

1. Module recompiles (STATUS task 2): `tools/cro.py` already loads every module and resolves both directions of imports. `mt_vtables.load` shows how to patch the static veneers.
2. If step 5 goes the "bring the layer" way, the list to recompile alongside `roEm001` is in `game_files/work/mport/s2/roEm001_imports_by_class.tsv` (scratch, addresses only).
