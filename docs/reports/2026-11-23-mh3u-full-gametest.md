# MH3U full gametest: report (2026-11-23)

The fifth session with the maintainer's dumps. It took STATUS.md's first next task: MH3U's two missing targets and a gametest of every function. It worked on `uc/mh3u-full-gametest` in the engine fork and `mh3u-full-gametest` here. Nothing from the files went into either repository: only counts, addresses and names.

## Done

| Task | Result | Where |
|---|---|---|
| MH3U's two missing targets | 0x0010853c: a byte-reading stream callback built with ARM `ldr r1, =off; add r1, pc, r1`, which last session's PC-built pattern already covers (the old run predates it). 0x00260914: an array element's constructor, loaded from a literal by a function the table lacks | reference-recompiles.md, "Step 3 results, MH3U full gametest" |
| Recompiler: follow literals of data-pointer functions | `data_pointer_closure` repeats the data-pointer scan over the literals of the functions it found, until nothing new turns up. It finds 3 functions in MH3U, 4 in MHXX, 0 in MH4U. MH4U's full recompile gives byte-identical generated code (40,577 functions) | fork `tools/recompile.py`, `tests/test_recomp.py`, `docs/RECOMPILER.md` |
| Runtime: indirect call to address 1 | `RC_ICALL`'s empty inline cache used target 1 as its mark with a null function, so a garbage call to 1 called a null host pointer. That accounts for the first full run's 5 `fail-fault` functions, about 1 case in 1,000. The empty cache now holds a stub that goes to `rc_call`. The synthetic test fails without the fix | fork `tools/recomp/runtime/recomp.h`, `tests/test_recomp.py`, `docs/RECOMPILER.md` |
| MH3U full gametest | 33,283 functions, `--cases 3 --seed 1`, 4 shards, 144 s: 14,044 pass, 19,228 agree-fault-only, 9 inconclusive, 2 protocol, **0 differ, 0 fail-fault, 0 missing targets** | reference-recompiles.md |
| MHXX under both fixes | 63,087 functions (+4). The 4 give 3 pass and 1 agree-fault-only. A new 2,000 sample has 0 differ and 0 missing targets | same |

`config/games/mh3u/` still needs no `extra_entries.txt`: every target the gametest reported is now found by the recompiler.

## What it changes for the plan

- **MH3U is a complete, verified reference recompile**: every function agrees with Unicorn on random states, apart from 11 budget and protocol cases. Targeted studies (step 4: swim state, oxygen, underwater camera) can start from it.
- **Gametest notes can be wrong about the cause.** The earlier guess that 0x00260914 "sits inside the function that jumps to it" was off: Ghidra had started that function 0x10 bytes late. Trace before acting, as with MHXX.
- **A rare `fail-fault` is worth chasing.** This one was a real runtime bug in upstream code that also affects the port (a garbage call to 1 would crash the host instead of reaching its fallback). The runtime fix is a candidate to offer upstream.
- Reproducing a rare case: replay gametest's own loop (same seed, same function order) and keep the RNG state of the failing case. A state that fails in the loop also fails when replayed alone.
- The memory and worker caps held: recompiles peak under 6 GB, and 4 gametest shards fit in one 6 GB cgroup.

## Not done

- MHXX's full gametest (every function): only the 2,000 sample was rerun.
- The fork's `uc/reference-classes` branch is merged but still exists, locally and on the remote.
- The fork's pre-existing ruff findings in `tools/recompile.py` and `tests/test_recomp.py` are left alone. This session added none.

## Checklist for the next session with game files

1. `.emd`/`.etd` specs (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves.
2. A first plugin that grows one id-indexed table with `alloc` and repoints its readers, checked in game.
3. MHXX full gametest: 4 shards in one 6 GB cgroup, as for MH3U (about 5 minutes).
4. MH3U targeted studies (reference-recompiles.md step 4), now that the recompile is fully verified.
