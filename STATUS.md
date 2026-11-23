# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after the session that gametested every MH3U function and fixed two recompiler gaps it found.

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly:
- MH3U: 33,283 functions, **every one gametested**: 0 differ, 0 fail-fault, 0 missing targets (11 budget/protocol cases).
- MHXX v1.4: 63,087 functions, 0 unresolved jump tables, and a 2,000-function sample with 0 differing and 0 missing targets.

Plugins can allocate from the game's heap, and the per-monster tables are mapped. Report: [docs/reports/2026-11-23-mh3u-full-gametest.md](docs/reports/2026-11-23-mh3u-full-gametest.md).

Findings that steer the next steps:
- Chase every missing target and every rare `fail-fault` the gametest reports by tracing the reference (Unicorn hooks, or a replay of gametest's own loop). This session's were a recompiler gap (literals of functions found through data pointers) and a runtime bug in upstream's inline cache that the port shares.
- MH4U's generated code is unchanged by this session's fixes (byte-identical, 40,577 functions). The runtime fix is a candidate to offer upstream.
- Adding a monster id means moving every bound in id-tables.md's "Bounds to move" list.
- Part data is probably in the per-monster `.emd`/`.etd` files.
- Memory: cap big jobs with a cgroup at **6 GB** (`MemoryMax=6G`, one job at a time, 4 workers; 4 gametest shards fit in one cgroup). Fork recompiler tests need `PATH=/usr/lib/llvm-22/bin:$PATH`.

## Branches

This session's work is on `mh3u-full-gametest` here and `uc/mh3u-full-gametest` in the fork, to be fast-forwarded into `main` / `uc/main` and pushed if the maintainer approves at handoff. The fork's `uc/reference-classes` is merged (PR #2) and can be deleted locally and on the remote.

## Next tasks, in order

1. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves. Done when specs/ has both with verified/unverified fields and id-tables.md's parts row points at them.
2. **A first table-growing plugin**: grow one id-indexed table with `alloc` and repoint its readers, checked in game. Done when a procedure in docs/checks/ passes.
3. **MHXX full gametest** (every function, 4 shards, about 5 minutes). Done when reference-recompiles.md has its verdict counts and every non-agreeing function is explained.
4. **MH3U targeted studies** (reference-recompiles.md step 4: swim state, oxygen, underwater camera in the harness). Done when underwater.md cites what the harness showed.

## Waiting on the maintainer

- A check of the port's pad features with the plugin in the app or Azahar's Qt build (plugin-api.md step 5), on a machine with a display.
- Whether to offer the inline-cache fix (fork `recomp.h`) to upstream MH4UltimateDC.
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
