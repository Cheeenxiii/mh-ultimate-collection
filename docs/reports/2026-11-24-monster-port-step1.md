# Monster port, step 1 for Rathian: report (2026-11-24)

A workspace session with the maintainer's dumps, after PR #6 (the RomFS surveys) was merged. It took STATUS task 2: step 1 of [monster-port.md](../design/monster-port.md), mapping the engine calls of MH3U's and MHXX's monster code to MH4U's through a monster all three games have (em001, Rathian). Heavy jobs ran one at a time under the 6 GB cgroup cap. Scratch scripts and every output (decompressed images, analyses, maps) stayed in `game_files/work/mport/`. Only counts, addresses and names went into the repositories.

## Done

| Task | Result | Where |
|---|---|---|
| Rathian's classes | MH4U `uEm001` (instance vtable found through the DTI's `newInstance`, slot 2 of the DTI vtable; 97 slots, 25 overridden). MHXX `uEm001_00` < `uFestaEnemy`. MH3U has no `uEm001`: `uEm002` holds an `Em001JointCallback` | monster-port.md |
| MH4U's own code for Rathian | 122 functions, 21,713 instructions, one block at 0x6d4f80–0x6ec8dc: the closure from the overridden slots, minus anything code outside the set also refers to. It calls 197 engine functions (1,350 calls and references) | monster-port.md |
| MHXX's code modules | MHXX keeps much of its code in 109 CRO modules (`/modules_MasterRelease/`, 6.5 MB of code: every monster, 16 weapon types, village, quest, title). The reference recompile of `code.bin` has none of it; 699 static veneers wait for the loader. New `tools/cro.py` loads all 109 (135,931 patches, all ABS32; 31,734 static imports); the analyser reads `roEm001` (265 functions, 32,700 instructions) with no problems | fork: `tools/cro.py`, `tests/test_cro.py`, `config/games/README.md`; reference-recompiles.md |
| Pairing the two Rathians | fails: 16 of MH4U's 122 functions find an MHXX one at ratio ≥ 0.6 (register-free tokens), 13 of 110 by shared constants. MHXX's Rathian was largely rewritten | monster-port.md |
| Engine maps | new `tools/fnmap.py`: anchors (unique identical bodies), propagation through aligned calls, clear similarity on request. MH4U↔MHXX 1,805 anchors → 3,540 pairs; MH4U↔MH3U 2,582 → 3,967. Held-out anchors: 100% / 99.1% of those recovered are correct; clear similarity agrees with propagation 94% / 99% | fork: `tools/fnmap.py`, `tests/test_fnmap.py` |
| Rathian's engine calls | MHXX: 60 of 197 callees placed (40% of calls), 48 of them on functions `roEm001` really imports. MH3U: 37 of 197 (19%). 54 of `roEm001`'s 330 imported functions have an MH4U counterpart | monster-port.md |
| Tool fixes found by the real run | sides saved as plain data (the CLI's pickles named `__main__` classes); a module's calls into static were dropped when the veneer wasn't an analysed function | fork: `tools/fnmap.py` |

## What it changes for the plan

- **A GU monster port needs module recompiles.** The monster's behaviour code is in its `.cro`, so step 5 for any MHXX monster waits on recompiling modules and linking them to the static library at run time. That is fork work no one had planned.
- **"Through a shared monster" works only at the engine boundary.** Rathian's code was rewritten between MH4U and MHXX, so the map goes engine to engine, and the monster's call list and import table pick and check what matters.
- **The enemy layer is where the map is thin.** Anchors cover core and library code; MHXX restructured `uEnemy` (`uEnemyBase`, `uEnemyCharacter`) and MH3U's is a quarter of MH4U's. Vtables of classes both games name are the next anchor source.
- The 276 MHXX imports with no MH4U counterpart are the engine behaviour a GU Rathian relies on: the list to study for step 5.

## Not done

- MH3U's Rathian class (needs the enemy factory) and the isolation of its code.
- Vtable anchors from shared class names; grouping the unplaced imports by class.
- Isolating a monster's own code is a workspace script, not yet a tool.
- Recompiling CRO modules and linking them at run time.

## Checklist for the next session with game files

1. Rebuild the sides when needed: `tools/fnmap.py side --game mh4u|mhxx|mh3u --exheader ... --code ... -o <work>/x.side` (each 2–4 min under the 6 GB cap), `side --module roEm001.cro --crs static.crs`. The modules come out of RomFS with `mhuc romfs` (`tools.mhuc.romfs.open_image`).
2. `fnmap.py map A.side B.side --similar callees.txt -o map.tsv`; the Rathian callee list and the own-code script are in `game_files/work/mport/` (`mpcore.py`, `em001_engine.py`).
3. For vtables: a class's instance vtable is the literal its DTI `newInstance` (slot 2 of the DTI vtable) stores into the new object; MH4U's monster vtables are 0x184 bytes apart.
