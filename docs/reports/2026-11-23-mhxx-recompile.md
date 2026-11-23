# MHXX recompile and gametest: report (2026-11-23)

The fourth session with the maintainer's dumps. It took STATUS.md's first next task, the MHXX v1.4 recompile and gametest. It worked on a branch in each repo and fast-forwarded them into `main` here and `uc/main` in the engine fork. Nothing from the files went into either repository: only counts, versions, addresses and names.

## Done

| Task | Result | Where |
|---|---|---|
| MHXX v1.4 recompile | `recompile.py --game mhxx`: **63,083 functions, 0 unresolved jump tables** (1,681 resolved, plus 37 switch-helper tables), 3 trap instructions (all expected), 52 s | reference-recompiles.md, "Step 3 results, MHXX v1.4" |
| MHXX gametest | `--sample 2000 --cases 3 --seed 1`: 818 pass, 1,120 agree-fault-only, 62 inconclusive (budget), **0 differ, 0 missing targets** | same |
| Three analyser patterns MHXX needed | RVCT's Thumb switch helper (`__ARM_common_switch8`, 37 call sites) as a multi-return call; callbacks built with `ldr rN, =off; add rN, pc` as data-pointer candidates; ARM `add ip, pc, #1; bx ip` thunks reaching Thumb code. Each has a synthetic test that fails without it | fork `tools/recomp/analysis.py`, `emit.py`, `tools/recompile.py`, `tests/test_recomp.py`, `docs/RECOMPILER.md` |
| MH4U unchanged except additions | Full recompile against `uc/main`'s: 40,572 → 40,577 functions (the 4 thunk targets and one PC-built callback), 635 lines added, none changed. Gametest: the 5 show no differences; a 2,000-function sample has 0 differing and 0 missing targets | reference-recompiles.md; fork RECOMPILER.md's numbers |
| Workspace memory cap | Raised from 3 GB to **6 GB per job** (the maintainer's choice), one capped job at a time, still 4 workers; Ghidra heap 4 GB | `tools/workspace/CLAUDE.md`, installed |

## What it changes for the plan

- **"0 unresolved jump tables" isn't the whole story.** The switch helper's tables never showed up as unresolved; the gametest's missing-target list found them. The gametest's missing targets are worth chasing every time, as here, by tracing the reference with Unicorn hooks (who jumps to the target, who writes its address).
- **MHXX code is a realistic recompile target**, like MH3U's: three small patterns and it runs clean on the sample. MHXX has many more Thumb functions (1,833) than MH4U, so it leans on Thumb-specific idioms.
- **The port gains 5 functions** it was missing: Thumb code reached only through a thunk or a PC-built pointer. The port used to dispatch to them at run time without a recompiled function.
- **The full MH4U recompile needs more than 3 GB** (it was killed there, before and after the change). It fits in 6 GB.
- The fork's recompiler tests need the LLVM tools on PATH: `PATH=/usr/lib/llvm-22/bin:$PATH`, or the recompiler's end-to-end tests skip.

## Not done

- MH3U's two missing targets and full gametest (next task).
- A full MHXX gametest of every function (only the 2,000 sample).
- The fork has ruff findings in the files this session touched. They were there before this session, and the fork's rules only ask for pytest.
- The fork branch `uc/reference-classes` is merged (PR #2) but still exists, locally and on the remote.

## Checklist for the next session with game files

1. MH3U: check `0x0010853c` and `0x00260914` (the first may be another switch-helper-style or PC-built target: trace it as here), add real entries to `config/games/mh3u/extra_entries.txt`, rerun the recompile under the new patterns, then gametest every function.
2. Specs for `.emd`/`.etd` (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves.
3. A first plugin that grows one id-indexed table with `alloc` and repoints its readers, checked in game.
4. Optionally: MHXX's full gametest (every function), now that it runs in seconds per 2,000.
