# Port, monster ids and function tables: report (2026-11-23)

The second session with the maintainer's dumps, starting from STATUS.md's four next tasks; it ran them side by side while the builds ran. Branches: `claude/port-ids-and-tables` here, `uc/monster-ids-mh3u-functions` in the engine fork. Nothing from the files went into either repository: only counts, versions, hashes, addresses and names.

## Done

| # | Item | Result | Where |
|---|---|---|---|
| 1 | Build the port, run the sample plugin procedure | Azahar at the pinned commit with the patch; `mh4u_runner` built with clang (1,504 steps, 4 jobs). The code library from the USA v1.3.0 update, `-O1`, 209 objects in 17 min. Steps 1-5 and 7 pass: the plugin loads, its init runs, the game boots on recompiled code (no `interpreting` lines) to the save-data screen with the chain on `sMhPad::update`; without the mod the plugin list and the log lines are gone | docs/design/plugin-api.md |
| 2 | MH4U's monster id table and factory | **Ids 0..123**; id N runs `uEmN`, ids without files of their own reuse a neighbour's files and class. Factory `createEnemy` `0x006901f4` (switch on id < `0x7c`, 124-word jump table, 32 slots); `enemyDataPaths` (110 rows), `enemyDataPathIndex` (124), `loadEnemyData`, `enemyDataById` (124), `releaseEnemyData`. Every class is `0x8d90` bytes but id 0's | docs/design/id-tables.md; fork `config/symbols.txt` |
| 3 | MH3U function table | 24,869 functions with Ghidra 12.1.4 headless in two passes (20,281, then 4,510 candidates from `find_missing_functions.py`); 347 candidates left | fork `config/games/mh3u/functions.tsv`, `config/games/README.md` |
| 4 | MOD M2 (static) | Every header slot named and checked on all 39 models of one Rathalos archive per game (counts, offsets, entry sizes 0x20 groups, 0x80 materials, 0x30 meshes, bone block size formula); the word at 0x14 and two record kinds still unknown. **MH4U's and MHXX's Rathalos share one skeleton** (43 ids, same parents, other order); **MH3U's has 44 and 3 different parents** | specs/mod.md |
| 5 | MHXX v1.4 update | The maintainer's new dump (official, title version 4224) decrypted with their keys (CIA layer, then NCCH with key slot 0x25); every NCCH hash matches. **Its exheader and code are the same as the fan-repackaged copy's**; only RomFS differs | tools/workspace/dumps.json (`mhxx_upd`); fork `config/games/README.md` |

## What it changes for the plan

- **Adding monsters** means moving three 124-entry bounds (the factory's `0x7c` and jump table, `enemyDataPathIndex`, `enemyDataById`) and finding the rest (names, sizes, rewards). The uniform `0x8d90` class size means a new MH4U-style monster needs no new slot size; 3U monsters are another matter (their state differs, last report).
- **Motions:** MHXX's Rathalos skeleton matches MH4U's by bone id, so GU motions may fit 4U's models once it's shown motions address bones by id; MH3U's need a remap.
- **MHXX code:** the fan package's code was Nintendo's all along, so earlier code work on it holds; the clean dump is the reference from now on.
- **Plugins:** the plugin layer works in the real game. Guest memory allocation (for growing tables) is the next ABI step, and needs the game's heap functions.

## Not done

- Plugin procedure step 5's pad features (skip button, mouse camera): only in the app and the Qt build, not built here. Step 6: no guest address known to be free.
- MH3U's recompile and gametest (reference-recompiles.md step 3): `recompile.py --game` isn't written yet.
- MHXX's function table; a third Ghidra pass for MH3U.
- MOD: the community Blender/Noesis import for a count comparison; the mesh entry's fields.
- MH4U's text resources and MH3U's `QTDS` quest files (last report's checklist 6).

## Checklist for the next session with game files

1. reference-recompiles.md step 3 for MH3U: add `--game` to `recompile.py` (defaults from `config/games/<game>/`, MH4U's output byte-identical without it), recompile, gametest; record pass rates and unresolved jump tables.
2. The same Ghidra pipeline for MHXX's v1.4 code (`game_files/work/mhxx_upd`): `config/games/mhxx/functions.tsv`, and its class registry next to v1.0's.
3. Find the game's heap allocate and free functions, for the plugin ABI's `alloc`/`free`, and a free guest address for plugin step 6.
4. id-tables.md, the rest of the monster tables: names, sizes and crowns, parts and rewards, each with its bound.
5. Describe MH4U's text resources.

The workspace keeps what this session built: `game_files/work/azahar/` (runner), `ghidra/` (12.1.4), `azahar-user/` (code library installed), `mh3u_ghidra/` (project and exports), and the scripts in `idt/`, `m2/` and `xxdec/`.
