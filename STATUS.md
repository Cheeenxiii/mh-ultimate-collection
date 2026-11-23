# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after the session that recompiled MH3U, built MHXX's table, added plugin `alloc`/`free` and mapped the monster tables.

## Where we are

Phase: **engine work with the game files.** MH3U recompiles with 0 unresolved jump tables and passes a 2,000-function gametest with none differing; MHXX v1.4 has its function table (38,931) and classes; plugins can allocate from the game's own heap (ABI 2, step 6 passes in game); every per-monster table found has an address and bound. Report: [docs/reports/2026-11-23-parallel-engine-tasks.md](docs/reports/2026-11-23-parallel-engine-tasks.md).

Findings that steer the next steps:
- MH4U's jump-table patterns cover MH3U unchanged, so 3U code is a realistic native-runtime candidate (the decision stays open).
- Adding an id means moving every bound in id-tables.md's "Bounds to move" list; some tables hold 123 entries, not 124.
- Part data isn't in a code table: probably in the per-monster `.emd`/`.etd` files.
- Memory: the harness reserves 4 GB of address space, so cap jobs with a cgroup (`MemoryMax=3G`), not `ulimit -v`.

## Branches

Nothing in flight: this session's branches are merged into `main` here and `uc/main` in the fork. Both are ahead of their remotes until pushed. The merged branches (`mh3u-recompile`, `heap-alloc`, `monster-tables`; fork `uc/mh3u-recompile`, `uc/heap-alloc`, `uc/mhxx-functions`) and their worktrees under `worktrees/` can be deleted.

## Next tasks, in order

1. **MHXX recompile and gametest**: `recompile.py --game mhxx`, gametest `--sample 2000`. Done when its pass rate and unresolved jump tables are in reference-recompiles.md.
2. **MH3U's missing targets and full gametest**: check `0x0010853c` and `0x00260914`, add them to `extra_entries.txt`, rerun, gametest every function. Done when reference-recompiles.md has the full-run results.
3. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves. Done when specs/ has both with verified/unverified fields and id-tables.md's parts row points at them.
4. **A first table-growing plugin**: grow one id-indexed table with `alloc` and repoint its readers, checked in game. Done when a procedure in docs/checks/ passes.

## Waiting on the maintainer

- A check of the port's pad features with the plugin in the app or Azahar's Qt build (plugin-api.md step 5), on a machine with a display.
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
