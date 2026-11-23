# Reference recompiles of MH3U and MHXX

**Finding:** the recompiler itself is game-neutral; what ties it to MH4U is its inputs (`config/`'s tables of USA v1.3.0) and the gates around it (version checks, program ids, the port's hook addresses). A reference recompile of MH3U or MHXX needs a per-game config folder and a function list made from that game's own code. Neither needs a refactor of the recompiler. The class registry, the first thing we want from each game, needs no recompile at all: `tools/mt_dti.py` finds the DTI constructor by itself and runs on any code.bin.

"Reference recompile" means: MH3U's or MHXX's code recompiled with the same tools, run under the test harness or Unicorn to study its behaviour (the swim state, underwater AI, GU-era systems) and compare it with MH4U's. It doesn't mean playing those games on the port.

## MH4U-specific assumptions in the fork

Read: `tools/recompile.py`, `tools/recomp/` (analysis, arm, thumb, emit, build, gametest, harness, runtime), `tools/mt_dti.py`, `tools/build_function_table.py`, `tools/find_missing_functions.py`, `tools/build_game.py`, `tools/version_map.py`, `port/src/frontend.cpp`, `config/`.

| Where | Assumption | Kind | What a reference recompile needs |
|---|---|---|---|
| `config/functions.tsv` (31,411 rows) | MH4U USA v1.3.0's function entries, from its Ghidra export plus `find_missing_functions.py` | data, per game | a new table per game, made by the same pipeline (Ghidra export → `build_function_table.py` → `find_missing_functions.py`) |
| `config/extra_entries.txt` (600) | MH4U's vtable-only and indirect-target entries, found by gametest runs | data, per game | per game; starts empty and fills from that game's gametest runs |
| `config/symbols.txt` (177) | names at MH4U addresses | data, per game | per game; optional |
| `config/hooks.txt`, `config/tunables.txt` | MH4U addresses of the port's hook points and tunables | data, per game | empty for a reference recompile (no port hooks); research hooks of our own later |
| `config/versions.json` | known code hashes; `target: true` on USA v1.3.0; EUR's `shifts` | data + gate | an entry per reference game, `target` for its own table, no shifts |
| `config/mt_classes.tsv` | MH4U's class registry | data, per game | regenerated per game with `mt_dti.py` |
| `tools/recompile.py` `main` | defaults to `baserom/update_v130/`; refuses code with `shifts` (EUR) | gate | a `--game` option choosing the config folder; the refusal stays for EUR |
| `tools/build_game.py` `check_version`, `buildable` | only USA v1.3.0 and EUR v1.1.0 build, unless `--any-version` | gate | not used for reference recompiles: they don't install a library |
| `tools/build_function_table.py` `--dti-ctor` | its usage example is MH4U's constructor address (0x005bfa94) | argument | `mt_dti.py` finds each game's constructor; pass that |
| `tools/mt_dti.py` | constructor shape `MtDTI(this, name, parent, size, arg4, flags, id)`, three stack arguments, id at DTI + 0x1C | engine version | holds for MT Framework Mobile; MH3U (an older MT Mobile) must be checked: if the class count comes out near zero, the shape differs |
| `tools/recomp/analysis.py` | jump-table and pointer patterns tuned on MH4U's code (the video decoder needed its own) | heuristics | expect a few new patterns per game; the analysis reports unresolved tables |
| `tools/recomp/gametest.py` | memory layout from the exheader; random states | none | works as is, given the game's exheader and code |
| `tools/recomp/runtime/recomp.h`, `rc_dll.c` | `rc_title_id`, `RC_HOST_VERSION`; nothing game-specific | none | works as is |
| `port/src/frontend.cpp` `IsMh4u`, `hooks.cpp` constants | MH4U's program ids and USA addresses | port | not used: reference recompiles run in the harness, not in the port |
| `tools/mods.py` `REGIONS` | MH4U's two program ids | mod manager | not used |

The DTI constructor address is not an assumption of `mt_dti.py`: it finds the most-called target right after a class-name string's address is taken. Only `build_function_table.py`'s `dti-init` category takes it as an argument.

## Per-game config plan

```
config/                     MH4U USA v1.3.0, as today (the port's tables)
config/games/mh3u/          MH3U (3DS), reference only
    game.json               program id, update id, code hash, segments, "reference": true
    functions.tsv  extra_entries.txt  symbols.txt  mt_classes.tsv
config/games/mhxx/          MHXX (3DS), reference only
    (same files)
```

- `game.json` takes the place of a `versions.json` entry for that game, so `config/versions.json` stays MH4U's alone and upstream's checks don't change.
- `tools/recompile.py --game mh3u` reads `config/games/mh3u/` for every default (`--functions`, `--extra`, `--hooks` none, `--tunables` none, `--versions` from `game.json`) and checks the code hash against it. Without `--game`, nothing changes: MH4U's output is byte-identical.
- `tools/mt_dti.py` and `tools/build_function_table.py` take `--game` the same way, for their defaults only.
- The tables are addresses and names only, like MH4U's (allowed by LEGAL.md). Ghidra exports stay in `build/`.
- This lives in the engine fork, on a branch from `uc/main`, in new files plus one argument per tool: easy for upstream to take or ignore.

## Step 1 results (2026-11-23)

`mt_dti.py` ran unchanged on all three games: the MT Mobile constructor shape holds for MH3U too. The tables are in the engine fork, branch `uc/reference-classes`, under `config/games/`. Regenerating MH4U's from its v1.3.0 code gives upstream's `config/mt_classes.tsv` exactly.

| Game (code) | Constructor | Classes | Monster classes | Their sizes | Base class |
|---|---|---|---|---|---|
| MH4U USA v1.3.0 | 0x005bfa94 | 992 | 55 `uEmNNN` | 0x8d90 (54), 0x8de8 (1) | `uEnemy` 0x8d88 < `uMHchar` |
| MH3U USA | 0x0054c8b8 | 1,218 | 41 `uEmNNN` | 0x1e70 to 0x2368, many different sizes | `uEnemy` 0x1e70 < `uCharacter` |
| MHXX JPN v1.0 | 0x0083fd00 | 3,110 | 61 `uEmNNN_NN` | 0xb778 to 0xb790 for most | `uFestaEnemy` 0xb770 < `uEnemy` 0xb730 < `uEnemyBase` |

- **MH4U and MHXX** each give their monsters near-uniform classes that add 8 to 0x20 bytes to the base. That supports the brief's reading: a monster there is mostly data and shared code.
- **MH3U** is different: its base enemy is a quarter of MH4U's size, and each monster adds its own state, up to 0x4f8 bytes. 3U monsters carry more per-monster code, so lifting them will mean recompiled 3U code (or a reimplementation on MH4U's base, which the fidelity rule rules out) rather than data alone. This is the main input for the converter and plugin plans.
- Resource classes share names and ids across the games (`rQuestData`, `rEnemyCmd`, `rGUIMessage`, `rModel`, `rTexture`), with different sizes. MHXX has `rSetEmMain`, `rEmSetList` and `rRem`; MH4U and MH3U don't. MH3U has no `rEnemyData` or `rStageAreaInfo`.
- No class in MH3U's registry is named for swimming, water or oxygen: the swim state lives inside `uPlayer` (0x26a8) and friends, not in classes of its own. Step 4 has to find it in code, not by name.
- 593 class names are shared between MH4U and MH3U, and 654 between MH4U and MHXX.

## Step 2 results (2026-11-23)

MH3U's function table is in the engine fork, `config/games/mh3u/functions.tsv`: 24,869 functions (800 DTI initialisers, 493 SDK), made with Ghidra 12.1.4 headless in two passes (20,281 from the first, then `find_missing_functions.py`'s 4,510 candidates added; 347 candidates are left for a third pass). The commands are in the fork's `config/games/README.md`. Ghidra 12.2 needs JDK 25; 12.1.4, the version `ExportForAgents.java` was verified on, runs on JDK 21. MHXX's table is not made yet; the official v1.4 (v4.8.0) update now has a clean dump, whose code is the same as the fan-repackaged copy's.

## Step 3 results, MH3U (2026-11-23)

`tools/recompile.py --game mh3u` (engine fork, branch `uc/mh3u-recompile`) recompiles MH3U from `config/games/mh3u/`: its function table and extra entries (none yet), no hooks or tunables, and only code whose hash matches its `game.json`. Without `--game`, MH4U's generated code is byte-identical to `uc/main`'s: all 209 generated source files are identical, and only report.txt's timings differ. That comparison ran with `--no-data-pointers` on both sides, because the full MH4U run needs more than the 3 GB memory cap (below). The change only touches how arguments are resolved, which that flag doesn't bypass.

| | MH3U USA | MH4U USA v1.3.0 (for scale, `--no-data-pointers`) |
|---|---|---|
| Functions recompiled | 33,275 (24,869 from the table, 8,086 through data pointers, 320 discovered) | 32,439 |
| Instructions | 2,498,365 | 3,179,179 |
| Jump tables resolved | 2,543 | 3,397 |
| Unresolved jump tables | **0** | 0 (2 other problems) |
| Trap instructions | 3 | 1 |
| Static constructors from the init table | 0 found | 256 |
| Recompile time | 38 s analysis + 23 s emit | 34 s + 23 s |

No new analysis pattern was needed: every MH3U jump table matches the patterns tuned on MH4U. The init-table scan finds nothing in MH3U: either its RVCT init table has another shape, or its 800 DTI initialisers are already in the table. Worth a look before relying on static constructors.

**Gametest** (harness library at `-O0 -D RC_CHECK_RETURNS`, `--sample 2000 --cases 3 --seed 1`, 13 s):

| Verdict | Functions | |
|---|---|---|
| pass | 858 | same registers, flags, VFP and writable memory |
| agree-fault-only | 1,136 | both sides fault at the same address (random states) |
| native-nofunc | 4 | an indirect call to a target missing from the table: 0x0010853c (3 callers), 0x00260914 (1) |
| inconclusive | 2 | instruction budget |
| differ | **0** | |

That is 1,994 of 2,000 (99.7%) agreeing, and no function returns a different state, the same picture as MH4U's runs (the fork's docs/RECOMPILER.md). Next for MH3U: add the two missing targets to `config/games/mh3u/extra_entries.txt` (0x00260914 sits inside the function that jumps to it, so check it's a real entry first), then a full run of every function.

Memory on this 14 GB machine: the full MH4U recompile (and MH3U's, close to it) hits `MemoryError` under `ulimit -v 3000000` in `code_cover`, the data-pointer pass's set of every covered halfword. MH3U's run peaked at about 2.5 GB. The harness reserves a 4 GB guest address window at start (`harness.c`, PROT_NONE and MAP_NORESERVE: address space, not memory), so gametest can't start under any `ulimit -v` below about 4.3 GB. It ran in a cgroup instead: `systemd-run --user --scope -p MemoryMax=3G -p MemorySwapMax=0`, with `ulimit -v 6000000`, which caps real memory at 3 GB.

## Steps, in order (first session with game files)

1. **Class registries (no recompile). Done, results above.** `mt_dti.py --exheader <mh3u exheader> --code <mh3u code.bin> -o config/games/mh3u/mt_classes.tsv`, the same for MHXX. Compare their `uEm*` classes, sizes and parents with MH4U's: the size-0x8d90 pattern of MH4U's monsters says much of a monster may be data; whether MH3U's and MHXX's monsters share one size per game is the first test of that.
2. **Function tables.** Ghidra export of each game (the fork's `tools/ghidra/` scripts), then `build_function_table.py` and `find_missing_functions.py`.
3. **Recompile and gametest. Done for MH3U, results above; MHXX waits for its function table.** `recompile.py --game mhxx`, then `python3 -m recomp.gametest --lib ... --sample 2000`. Record pass rates and unresolved jump tables; add analysis patterns where needed (with tests, as for MH4U's video decoder).
4. **Targeted studies.** Run single functions (MH3U's swim state machine, oxygen, underwater camera) in the harness from captured states, with hooks for tracing; feed what's learned into [underwater.md](underwater.md).

## Optional refactor done now?

Not done in this session. The plan above changes defaults only, and the brief allows it only with MH4U's output unchanged. Without game files the "unchanged" can't be shown on the real tables, only on the synthetic tests. It is better done in the first session with game files, where step 1 can check it at once.
