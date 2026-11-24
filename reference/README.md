# Reference recompiles

MH3U, MHXX and MHGU recompiled with the fork's tools, as references to read and test against. They are never played and never shipped: a monster is ported by translating its source code onto MH4U's engine, and these recompiles are where that source code comes from.

## Running the tools

The scripts reuse the fork's recompiler. They find it in a sibling checkout named `MH4UltimateDC-fork`, or wherever `MH4U_FORK` points. They also need the fork's Python requirements (`unicorn`, `capstone`).

| Script | Does |
|---|---|
| `recompile_game.py <game>` | recompiles a reference game from its tables in `games/` |
| `recompile_module.py` | recompiles MHXX's CRO modules with its static code into one library |
| `modtest.py` | tests every recompiled module function against the original, in Unicorn |
| `cro.py` | reads a CRO module: segments, relocations, imports |
| `mt_vtables.py` | recovers every MT class's vtable, modules included |
| `fnmap.py` | maps functions between two games |
| `monster_actions.py` | lists a monster's actions from its dispatcher, and pairs handlers across games by action id |
| `extract_nsp.py` | extracts a Switch NSP's program code with your own keys |

Typical MHXX run, with `<work>` holding your own extraction:

```bash
python3 reference/recompile_game.py mhxx --exheader <work>/exheader.bin --code <work>/code.bin -o build/recomp-mhxx
(cd ../MH4UltimateDC-fork/tools && python3 -m recomp.build ../../mh-ultimate-collection/build/recomp-mhxx --harness --opt O0 -o game.so)
```

A new game's tables come from the fork's own tools, run from its checkout:

1. `tools/extract_ncch.py` on your dump, then `tools/mt_dti.py` for the class registry.
2. A Ghidra export with the fork's `tools/ghidra/` scripts, then `tools/find_missing_functions.py` and a second export.
3. `tools/build_function_table.py ... --symbols "" --text-only`. The empty `--symbols` matters: the default file names MH4U's addresses.

`games/<name>/` holds each game's `game.json` (the hash and layout of the dump the tables fit), its function table, its extra entry points and its class registry. They are addresses and names only.

This page also records what has been established about the engines. Addresses are USA v1.3.0 for MH4U unless stated. Nothing here is game data: only addresses, sizes, counts and names.

## The reference games

| Game | Code | Recompile | Check against the original |
|---|---|---|---|
| MH3U (3DS, USA) | `code.bin` | every function | gametest: 33,272 of 33,283 agree, the rest are test limits; none returns a different state |
| MHXX (3DS, v1.4) | `code.bin` plus 109 CRO modules (every monster, weapon type, village…) | everything, modules at fixed bases in one library | module test: all 109 modules, no difference in state, memory or exit |
| MHGU (Switch, v1.4.0) | `main`, 32-bit ARM, monsters linked statically | not recompiled | used for matching functions only |

## Class registries

| Game | Classes | Monster classes | Base enemy |
|---|---|---|---|
| MH4U | 992 | 55 `uEm*`, all 0x8d90 bytes | `uEnemy` < `uMHchar` |
| MH3U | 1,218 | 41 `uEm*`, 0x1e70 to 0x2368 bytes | `uEnemy` (0x1e70) < `uCharacter` |
| MHXX | 3,109 with its modules | in the modules | `uFestaEnemy` < `uEnemy` < `uEnemyBase` |
| MHGU | 3,205 | in `main` | as MHXX; 2,949 class names shared with it |

MH3U's base enemy is a quarter of MH4U's size, and each monster adds its own state. MHXX's `uEnemy` has three times MH4U's virtual methods.

## Cross-game function maps

| Map | Functions paired | Check |
|---|---|---|
| MH4U ↔ MHXX | 7,542 | held-out pairs recovered, 100 % correct |
| MH4U ↔ MH3U | 6,866 | held-out pairs recovered, 100 % correct |
| MHXX ↔ MHGU | 26,406 | 161 of 165 held-out functions right, none wrong |

Monster code itself doesn't pair function by function: MHXX rewrote Rathian into more, smaller functions. Pairing works through shared action ids instead.

## Rathian, the first port

| | MH4U | MH3U | MHXX |
|---|---|---|---|
| class | `uEm001` | `uEm002` (Rathalos's class) | `uEm001_00`, in `roEm001.cro` |
| action dispatcher | vtable slot 44, 0x006e9cac | slot 47, 0x00687d30 | 0x02009704 (module at 0x02000000) |
| actions | 342 | 191 | 301 |
| distinct handlers | 97 | 66 | 83 |

- 273 of MHXX's action ids exist in MH4U. Of the shared actions that pass constants, 194 of 197 pass the same ones.
- Each of the 80 MH4U handlers reached by a shared action meets exactly one MHXX handler.
- `roEm001` imports 330 engine functions. 61 of those it calls have no MH4U counterpart. Through MHGU, 2 more resolve to MH4U and 28 are placed in GU only, mostly projectile code.

## MH4U monster tables

Monster ids run 0 to 123. Id N's files are `emNNN`. Every table below has to grow when ids do.

| Table | Address | Shape |
|---|---|---|
| `createEnemy` (factory) | 0x006901f4 | `cmp id, #0x7c`, then a 124-word jump table at 0x00690278 |
| `enemyDataPathIndex` | 0x00efc268 | 124 pointers by id into `enemyDataPaths` (0x00efbef8, 110 rows) |
| `enemyDataById` | 0x00f3a024 | 124 pointers by id to records from 0x00f39c90 |
| `crownSizeTable` | 0x00f32008 | 124 rows of 4 floats, read by `getCrown` (0x0068877c) |
| `monsterListOrder` | 0x00df35b0 | 124 rows of 8 bytes, by list position |
| `monsterIconIndex` | 0x00e06698 | 124 bytes, 0x7f = no icon |
| `enemyResourceIndex` | 0x00efbd08 | 124 pointers to 0x2c-byte path records |
| `dropRecordIndex`, `dropBaseA`, `dropBaseB` | 0x01003bec, 0x01003ddc, 0x01003ed4 | 124 entries each, into `itemListTable` (0x01002a5c) |
| names and notes text | `emName`, `emExp` in `core_common.arc` | message N names id N; 123 messages |

- The current monster's id is the byte at +0x1c0 of the block that `this+0xe28` points to.
- Ids map to class `uEmN`, or to a sibling's class for variants and subspecies.
- Several tables hold 123 entries, not 124: reading them for id 123 reads the next table.
- 54 functions compare a register with 0x7c. Only some are monster code.
- Save-side limits: a guild quest stores monster ids in one byte, and the character save's monster log has 82 fixed entries.

The game's heap allocator, which plugins use, is named in the fork's `config/symbols.txt`, section "Heap".

## MH3U's factory

0x005bbc5c: `cmp r1, #0x56`, then an 86-word jump table. Rathian (id 1) runs on `uEm002` with Rathalos and the colour variants (ids 2, 62 to 65). MH4U does the reverse, with ids 1 to 6 on `uEm001`.
