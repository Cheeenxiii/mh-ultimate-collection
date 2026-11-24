# Module recompiles finished, Rathian's actions and engine calls (2026-11-24)

This report covers two sessions on STATUS task 1. The first recompiled MHXX's modules and stopped at its usage limit before writing a report. Its work is in fork PR #8 and content PR #10, and monster-port.md's "Module recompiles" section describes it. The second session finished that work and prepared Rathian's port: the action inventory in each game, and the engine calls classified. Big jobs ran under the 6 GB cap: the module build and test took 4 and 13 minutes, the function maps a few minutes each. Scratch scripts and outputs are in `game_files/work/mport/` (`actions/` for this session) and `game_files/work/runs/modrerun/`. The repositories got counts, names and addresses only.

## Done

| Task | Result | Where |
|---|---|---|
| Module recompiles (first session) | all 109 MHXX modules at fixed bases in one library with the static code; `recomp.modtest` tests each module function against the original in Unicorn. 956 static functions only modules call became MHXX extra entries; the analyser's output is now the same from run to run | fork: `tools/recompile_module.py`, `recomp/modtest.py`, `config/games/mhxx/extra_entries.txt` |
| Full module rerun | 36,669 functions: 20,718 pass, 15,770 fault the same way in both, 178 inconclusive, none differ. 40 leftovers → 3: one garbage pointer from a random state (passes in 64 more cases), two data words in `roTitle` pointing into veneers. Fix: a pointer into a veneer is no longer an entry (4 dropped, all in `roTitle`) | fork: `tools/recompile_module.py`, `tests/test_recompile_module.py`, `config/games/README.md` |
| Rathian's action inventory | one scheme in all three games: category and index bytes, a dispatcher slot, a switch per category, tail calls to handlers. Actions and distinct handlers: MH4U 342 and 97, MH3U 191 and 66, MHXX 301 and 83 | fork: new `tools/monster_actions.py`, `tests/test_monster_actions.py`; monster-port.md |
| Shared action ids | 273 ids are shared between MH4U and MHXX; 194 of 197 shared actions that pass constants pass the same ones. The 80 handlers pair one to one. A map built without them holds 42 of the 80 pairs, all agreeing; one pair conflicts. MH3U: 174 shared ids, 63 handler pairs | monster-port.md |
| Seeded map into the imports | `fnmap.py map --seed`, `--module-side`, `side --entries`. `roEm001`'s 330 imports: 98 with an MH4U counterpart by code (68 before), 35 by call site, 197 without. 180 imports are called by the module's code; 61 of those have no counterpart, the translation worklist. 136 of the unmatched ones are never called (inherited vtable slots, other data) | fork: `tools/fnmap.py`, `tests/test_fnmap.py`; monster-port.md |

## What it changes for the plan

- **Actions pair across games by id.** A GU or 3U action's handler has its MH4U counterpart wherever the id exists in MH4U. A port can follow MH4U's handler for structure and the source's handler for behaviour.
- **The GU engine gap is 61 functions, not 262.** Most unmatched imports are base-class behaviour the module's vtables inherit. On MH4U's `uEnemy`, MH4U's own base class covers that. The list to translate is what Rathian's code actually calls.
- **Equal ids are a slot match, not yet a move match.** MHXX's Rathian was largely rewritten, so the same slot might hold a different move. Check R1 in game settles it.

## Not done

- The full module run wasn't repeated after the veneer-pointer fix. It only drops 4 entries, but the numbers above are from before it.
- The 61 functions aren't described yet, and the 33 call-site matches aren't confirmed.
- MH3U's 168 MH4U-only ids, MHXX's 28 MHXX-only ids: not looked at.
- Category 8 in MH4U has a single action and is listed with no index. The tool doesn't descend a one-case guard (`cmp idx, #0; bne`).
- Check R1 needs an action-forcing test aid that doesn't exist yet.
- `tests/test_recompile_module.py` line 182 has a ruff RET501 warning from the first session. The fork's checks don't run ruff.

## Checklist for the next session

1. Monster-port.md's "Next, towards step 5": the 61 functions, one entry each. The list with addresses is in `game_files/work/mport/actions/roEm001_imports_mh4u_use.tsv` (scratch, rows where `status` is `none` or `unclear` and `use` isn't `vtable` or `data`). The recompiled C is in the fork's `build/recomp-mhxx-modules/`.
2. To redo the inventories and maps, the commands are in the fork's `config/games/README.md` ("Monster actions", "Function maps between games"). `roEm001`'s side needs `--entries` with its handler addresses (`game_files/work/mport/tool/roEm001.entries`).
