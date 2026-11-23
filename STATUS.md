# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after the session that recompiled and gametested MHXX v1.4 and taught the recompiler three patterns.

## Where we are

Phase: **engine work with the game files.** Both reference games now recompile cleanly:
- MH3U: 0 unresolved jump tables, 0 differing in a 2,000-function gametest.
- MHXX v1.4: 63,083 functions, 0 unresolved jump tables, and a 2,000-function gametest with 0 differing and 0 missing targets.

Plugins can allocate from the game's heap, and the per-monster tables are mapped. Report: [docs/reports/2026-11-23-mhxx-recompile.md](docs/reports/2026-11-23-mhxx-recompile.md).

Findings that steer the next steps:
- "0 unresolved jump tables" can hide tables the analyser doesn't recognise (MHXX's Thumb switch helper). Chase every missing target the gametest reports by tracing the reference with Unicorn hooks.
- The three new patterns add 5 functions to MH4U's own recompile (additive, gametested). MH3U's run predates them.
- Adding a monster id means moving every bound in id-tables.md's "Bounds to move" list.
- Part data is probably in the per-monster `.emd`/`.etd` files.
- Memory: cap big jobs with a cgroup at **6 GB** (`MemoryMax=6G`, one job at a time, 4 workers); the full MH4U recompile needs more than 3 GB. Fork recompiler tests need `PATH=/usr/lib/llvm-22/bin:$PATH`.

## Branches

Nothing in flight: this session's work is on `main` here and `uc/main` in the fork, both pushed if the maintainer approved at handoff. The fork's `uc/reference-classes` is merged (PR #2) and can be deleted locally and on the remote.

## Next tasks, in order

1. **MH3U's missing targets and full gametest**: check `0x0010853c` and `0x00260914` (trace them as MHXX's were), add real entries to `extra_entries.txt`, rerun the recompile with the new patterns, gametest every function. Done when reference-recompiles.md has the full-run results.
2. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves. Done when specs/ has both with verified/unverified fields and id-tables.md's parts row points at them.
3. **A first table-growing plugin**: grow one id-indexed table with `alloc` and repoint its readers, checked in game. Done when a procedure in docs/checks/ passes.
4. **MHXX full gametest** (every function, not a sample). Done when reference-recompiles.md has its verdict counts.

## Waiting on the maintainer

- A check of the port's pad features with the plugin in the app or Azahar's Qt build (plugin-api.md step 5), on a machine with a display.
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
