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

That is 1,994 of 2,000 (99.7%) agreeing, and no function returns a different state, the same picture as MH4U's runs (the fork's docs/RECOMPILER.md). The two missing targets and the full run are below.

## Step 3 results, MH3U full gametest (2026-11-23)

Every MH3U function, gametested after two fixes in the engine fork (branch `uc/mh3u-full-gametest`). `config/games/mh3u/` still has no `extra_entries.txt`: the recompiler now finds every target the gametest reported by itself.

**The two missing targets of the sample run:**
- **0x0010853c** reads one byte from a stream (`ldr r1, [r0, #0x10]`, post-increment, `ldrb`), a scanf-style callback. 0x00108550 installs it with `ldr r1, =-0x34; add r1, pc, r1`: MHXX's PC-built callback pattern, in its ARM form. The sample run predates that pattern; rerun under it, the recompiler finds this callback and 4 others (0x001085a0, 0x00110464, 0x00110540, 0x00110580).
- **0x00260914** is a real function: it zeroes five words, an array element's constructor. 0x002608a8 passes it from a literal to the runtime's array-construct helper (0x00107720). The note above was wrong: 0x002608a8 is not in the function table (Ghidra started that function at 0x002608b8, after the setup), so the recompiler finds it only through a data pointer. It collected literal constants from the table's functions only, so this literal was never a candidate.

**Fix 1, in the recompiler: follow the literals of functions found through data pointers.** The data-pointer scan now runs again over the literals of the functions it found, until nothing new turns up (`data_pointer_closure` in `tools/recompile.py`, with a synthetic test). The first full gametest had found two more cases of the same shape, 0x005ae498 (an empty constructor) and 0x005aebb0 (a constructor that itself builds an array, so the chain nests), and a measurement with the closure gave exactly those three for MH3U, 4 for MHXX (0x001242b4, 0x001242ec, 0x00293fc4, 0x0040cc98, none of which its 2,000 sample had reached) and none for MH4U. MH4U's full recompile (with data pointers) gives byte-identical generated code: 40,577 functions.

**Fix 2, in the runtime: an indirect call to address 1.** The first full gametest had 5 `fail-fault` functions (0x003212ec, 0x00324da8, 0x00324dec, 0x00324e24, 0x00a0e538), about 1 case in 1,000, Unicorn faulting at 0x0 and native code at an address that changed from run to run. Reproduced and traced on 0x00324da8: it calls 0x0013fe28, which runs into 0x0013fe68 and makes a virtual call through a vtable read from random memory; the slot held 1 (Thumb address 0). The other four pass or agree after the same fix. The per-call-site inline cache (`RC_ICALL` in `recomp.h`, upstream code) used target 1 as its "empty" mark with no function behind it, so native code called a null host pointer. The empty cache now holds a stub that sends target 1 to `rc_call` like any miss; a synthetic test fails without it. In the port, the same garbage call would have crashed the host instead of reaching the host's fallback.

**Recompile** (`recompile.py --game mh3u`, 6 GB cgroup): 33,283 functions (8,094 through data pointers), 0 unresolved jump tables, 0 problems, 3 trap instructions, 31 s analysis + 16 s emit.

**Gametest of every function** (harness library at `-O0 -D RC_CHECK_RETURNS`, `--cases 3 --seed 1`, 4 shards in one cgroup, 144 s):

| Verdict | Functions | First full run (before the fixes, 33,281 functions) |
|---|---|---|
| pass | 14,044 | 14,058 |
| agree-fault-only | 19,228 | 19,203 |
| inconclusive | 9 (instruction budget) | 9 |
| protocol | 2 (RVCT helpers that read a descriptor after their call site, tested through their callers) | 2 |
| native-nofunc | **0** | 4 (targets 0x005ae498, 0x005aebb0) |
| fail-fault | **0** | 5 (the address-1 call) |
| differ | **0** | 0 |

That is 33,272 of 33,283 functions (99.97%) agreeing on all 99,849 cases, the 11 others being the budget and protocol cases. No function returns a different state.

**MHXX under the same fixes:** 63,087 functions (+4, the ones listed above); the 4 give 3 pass and 1 agree-fault-only (20 cases each); a new `--sample 2000 --cases 3 --seed 1` gives 860 pass, 1,087 agree-fault-only, 53 inconclusive, 0 differ, 0 missing targets.

## Step 3 results, MHXX v1.4 (2026-11-23)

`tools/recompile.py --game mhxx` (engine fork, branch `uc/mhxx-recompile`) recompiles MHXX JPN v1.4 (update v4.8.0) from `config/games/mhxx/`. The first run gave 0 unresolved jump tables, but its gametest found two indirect targets missing. They led to three analysis patterns MH4U's tuning hadn't needed. Each is added with a synthetic test in the fork's `tests/test_recomp.py`:

1. **RVCT's Thumb switch helper** (`__ARM_common_switch8`, at 0x002e4328 in MHXX). A Thumb `bl` to it is followed by a byte table: the case count, then one entry per case and a default. The helper jumps to `lr + 2 * entry` and never returns to `lr`. The analyser decoded the table as code and never reached the cases. It now treats the call as a multi-return call, like the floating-point descriptor helpers. MHXX has 37 call sites; MH4U and MH3U don't have the helper. This one was invisible in the "unresolved jump tables" count: the 9 trap instructions of the first run drop to 3.
2. **Callbacks built position-independently.** MHXX's stream readers (0x002e3fc8 reads a byte, 0x002e6710 a halfword) are installed with `ldr r1, =off; add r1, pc`. No word in the data or literal pools holds their address, so the data-pointer scan missed them. Literal-plus-PC sums now go through the same checks as other candidates.
3. **ARM thunks into Thumb.** `add ip, pc, #1; bx ip` (0x00127204 → 0x00127214 in MHXX, a this-adjusting thunk). The constant-target rule took only ARM targets; an odd target after `bx` is now Thumb.

| | MHXX JPN v1.4 | first run, before the fixes |
|---|---|---|
| Functions recompiled | 63,083 (38,931 from the table, 684 static constructors, 23,046 through data pointers, 422 discovered) | 63,050 |
| Instructions | 2,763,585 | 2,759,769 |
| Jump tables resolved | 1,681 (+ 37 switch-helper tables) | 1,681 |
| Unresolved jump tables | **0** | 0 |
| Trap instructions | 3: two VFPv3 `d16-d31` save/restore stubs of the runtime library (the 3DS's VFPv2 never calls them) and one ASCII word reached inside a data block | 9 |
| Recompile time | 34 s analysis + 18 s emit, under the 3 GB cgroup cap | 32 s + 19 s |

The init-table scan finds 684 static constructors in MHXX (none in MH3U). Three times as many functions come through data pointers as in MH3U (23,046 against 8,086): MHXX has 2.5 times as many classes (3,110), so more vtables. The gametest samples all 63,083 functions, these included, and finds none that differ.

**Gametest** (harness library at `-O0 -D RC_CHECK_RETURNS`, `--sample 2000 --cases 3 --seed 1`, 5 s):

| Verdict | Functions | First run |
|---|---|---|
| pass | 818 | 879 |
| agree-fault-only | 1,120 | 1,083 |
| inconclusive | 62 (all the instruction budget) | 36 |
| native-nofunc | **0** | 2 (0x0030553b, 0x00305571: switch-helper cases) |
| differ | **0** | 0 |

The two samples are different functions: the sample is drawn from the whole set, which grew by 33. An intermediate run, with only the switch helper fixed, found the three other missing targets (0x002e3fc9, 0x002e6711 and 0x00127215), and the trace that led to patterns 2 and 3.

That is 1,938 of 2,000 (96.9%) agreeing, with no function returning a different state.

**Effect on MH4U.** MH4U doesn't have the switch helper, but it has the other two patterns: 22 ARM→Thumb thunks, and 10 distinct Thumb addresses built with `add rN, pc`.
- Without data pointers, MH4U's generated code changes only by additions: 4 Thumb functions the thunks reach (0x00100482, 0x0010050c, 0x001005a6, 0x00101de0), 601 new lines, nothing else changed. In the gametest, 1 passes and 3 agree-fault-only (20 cases each). A 2,000-function sample of that build finds 0 differing.
- The full recompile (with data pointers), compared with `uc/main`'s under the workspace's 6 GB cap (66 s each): 40,572 → 40,577 functions. The 5 added are the 4 thunk targets and 0x00101990, a Thumb callback that no word holds. 635 lines are added and none changed. Gametest of that build: the 5 new functions show 2 pass and 3 agree-fault-only (20 cases each); `--sample 2000 --cases 3 --seed 1` gives 764 pass, 1,209 agree-fault-only, 27 inconclusive, **0 differ** and 0 missing targets.

Memory on this 14 GB machine: the full MH4U recompile (and MH3U's, close to it) hits `MemoryError` under `ulimit -v 3000000` in `code_cover`, the data-pointer pass's set of every covered halfword. MH3U's run peaked at about 2.5 GB. The harness reserves a 4 GB guest address window at start (`harness.c`, PROT_NONE and MAP_NORESERVE: address space, not memory), so gametest can't start under any `ulimit -v` below about 4.3 GB. It ran in a cgroup instead: `systemd-run --user --scope -p MemoryMax=3G -p MemorySwapMax=0`, with `ulimit -v 6000000`, which caps real memory at 3 GB. Under that 3 GB cap the full MH4U recompile is killed; the workspace cap is 6 GB since 2026-11-23, and the full run fits in it.

## MHXX's code modules (2026-11-23)

The MHXX numbers above are for `code.bin` only. MHXX keeps much of its code in 109 CRO modules in RomFS (`/modules_MasterRelease/`, 6.5 MB of code: every large and small monster, the 16 weapon types, village, quest, title), loaded at run time; the static side calls into them through 699 veneers the loader fills. So the MHXX reference recompile has no monster or weapon behaviour code. The engine fork's `tools/cro.py` (branch `uc/monster-port-step1`) loads all 109 modules with their relocations and static imports, and the analyser reads `roEm001` (Rathian) cleanly. MH4U and MH3U have no modules.

**Module recompiles (2026-11-24).** The fork's `tools/recompile_module.py` recompiles all 109 modules at fixed bases into one library with the static code, and `recomp.modtest` tests every module function against the original in Unicorn (fork `config/games/README.md`, "Recompiling the modules"). Since monsters are ported onto MH4U's engine (open-decisions.md, "Monster ports"), this C is the checked reference a port translates, not code the mod runs. All 109 modules (36,662 functions) gametest with no differences in state, memory or exit: 20,746 pass and 15,697 fault the same way in both; 40 functions are left on missing entry points and veneer edge cases, with fixes in and a full rerun to do. The modules also showed the static recompile 956 functions only modules call, now in the fork's `config/games/mhxx/extra_entries.txt`.

## Steps, in order (first session with game files)

1. **Class registries (no recompile). Done, results above.** `mt_dti.py --exheader <mh3u exheader> --code <mh3u code.bin> -o config/games/mh3u/mt_classes.tsv`, the same for MHXX. Compare their `uEm*` classes, sizes and parents with MH4U's: the size-0x8d90 pattern of MH4U's monsters says much of a monster may be data; whether MH3U's and MHXX's monsters share one size per game is the first test of that.
2. **Function tables.** Ghidra export of each game (the fork's `tools/ghidra/` scripts), then `build_function_table.py` and `find_missing_functions.py`.
3. **Recompile and gametest. Done for MH3U (every function) and MHXX (2,000 sample), results above.** `recompile.py --game mhxx`, then `python3 -m recomp.gametest --lib ... --sample 2000`. Record pass rates and unresolved jump tables; add analysis patterns where needed (with tests, as for MH4U's video decoder).
4. **Targeted studies.** Run single functions (MH3U's swim state machine, oxygen, underwater camera) in the harness from captured states, with hooks for tracing; feed what's learned into [underwater.md](underwater.md).

## Optional refactor done now?

Not done in this session. The plan above changes defaults only, and the brief allows it only with MH4U's output unchanged. Without game files the "unchanged" can't be shown on the real tables, only on the synthetic tests. It is better done in the first session with game files, where step 1 can check it at once.
