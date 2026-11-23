# MH3U recompile, MHXX table, guest heap, monster tables: report (2026-11-23)

The third session with the maintainer's dumps. It ran STATUS.md's four next tasks at the same time, each in its own session, git worktree and branch, then merged them into `main` here and `uc/main` in the engine fork. Nothing from the files went into either repository: only counts, versions, hashes, addresses and names.

## Done

| # | Item | Result | Where |
|---|---|---|---|
| 1 | MH3U recompile and gametest | `recompile.py --game mh3u` (new) recompiles **33,275 functions with 0 unresolved jump tables** (2,543 resolved); no new analysis pattern needed. MH4U's generated code without `--game` is byte-identical to `uc/main`'s (all 209 files). Gametest of 2,000 sampled functions: 1,994 agree (858 pass, 1,136 fault the same way), **0 differ**, 4 call a target missing from the table, 2 run out of budget | reference-recompiles.md step 3; fork `tools/recompile.py`, `config/games/README.md` |
| 2 | MHXX v1.4 function table and classes | **38,931 functions** (two Ghidra passes, 256 candidates left; 1,833 Thumb), **3,110 classes**; `game.json` names the v1.4 code, v1.0's registry moved to `mhxx/v1.0/`. `build_function_table.py` gains `--text-only`, and reference tables are built with `--symbols ""` (MH4U's symbol names had landed on 2 unrelated MH3U functions; the MH3U table is rebuilt) | fork `config/games/mhxx/`, `docs/research/mt-classes.md` |
| 3 | Guest heap and plugin `alloc`/`free` | MT Framework's allocator table `g_mtAllocators` (`0x010bdc88`), entry 0 the default heap; **plugin ABI 2** appends `alloc`/`free`, which call the game's own allocator. **Plugin step 6 passes in the real game** (a heap block counts frames) | plugin-api.md; fork `include/mh4u_plugin.h`, `port/src/plugin_host.h`, `config/symbols.txt` |
| 4 | The rest of the MH4U monster tables | Names (`emName`/`emExp`, 123 messages: id 123 has none), `crownSizeTable` and `getCrown`, hunter's-notes order and icons, resource paths, item drops (`itemListTable` and three id-indexed index tables), and eight id-indexed tables of unknown purpose, each with address, row size and bound; a list of every bound to move | id-tables.md |

## What it changes for the plan

- **MH3U code is ready to recompile** with MH4U's patterns as they are. That makes running 3U swimming code natively a realistic option for the runtime decision (not settled here).
- **Growing tables from a plugin is possible now**: plugins get memory from the game's own heap. Adding a monster id means moving every bound in id-tables.md's "Bounds to move" list together. Some tables hold 123 entries instead of 124, so reading them for id 123 already reads into the next table.
- **Memory on this machine:** `ulimit -v 3000000` doesn't fit two of the jobs. The harness reserves a 4 GB guest address window (address space, not memory), and a full recompile peaks at about 2.5 GB with a larger virtual size, so MH4U's full run hits `MemoryError` under it. A cgroup cap (`systemd-run --user --scope -p MemoryMax=3G -p MemorySwapMax=0`) limits real memory instead. The workspace rule now says so.

## Not done

- MHXX recompile and gametest (step 3 for MHXX): waited on its table, which now exists.
- MH3U: two indirect-call targets missing from its table (`0x0010853c`, `0x00260914`), a full gametest of every function, and the init-table scan, which finds no static constructors in MH3U.
- Monster tables: carves not traced; part data (probably in `.emd`/`.etd`, 110 of each) unverified; what the drop index tables and the eight unknown tables mean.
- Plugin step 5's pad features (needs a display).
- The full MH4U recompile under a memory cap (only `--no-data-pointers` was compared). MH3U's recompile ran after the MH3U table was rebuilt without MH4U's symbols, which changed 2 rows: rerun it before quoting the counts again.

## Checklist for the next session with game files

1. MHXX v1.4: `recompile.py --game mhxx`, gametest `--sample 2000`; record the results in reference-recompiles.md.
2. MH3U: check the two missing targets, add them to `config/games/mh3u/extra_entries.txt`, rerun the recompile, then gametest every function.
3. Specs for `.emd`/`.etd` (`rEnemyData`, `rEnemyTuneData`): find parts, hitzones and breaks, and trace carves.
4. A first plugin that grows one id-indexed table with `alloc` and repoints its readers, tested in the game.

The workspace keeps the worktrees under `worktrees/` (the branches are merged; they can be removed with `git worktree remove`), the MHXX Ghidra project in `game_files/work/`, and the build outputs.
