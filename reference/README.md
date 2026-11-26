# Reference recompiles

MH3U, MHXX and MHGU recompiled with the fork's tools, as references to read and test against. They are never played and never shipped: a monster is ported by translating its source code onto MH4U's engine, and these recompiles are where that source code comes from.

## Running the tools

The scripts reuse the fork's recompiler. They find it in a sibling checkout named `MH4UltimateDC-fork`, or wherever `MH4U_FORK` points. They also need the fork's Python requirements (`unicorn`, `capstone`).

| Script | Does |
|---|---|
| `recompile_game.py <game>` | recompiles a reference game from its tables in `games/` |
| `recompile_module.py` | recompiles MHXX's CRO modules with its static code into one library |
| `modtest.py` | tests every recompiled module function against the original, in Unicorn |
| `cro.py` | reads a CRO module: segments, relocations, imports; `calls` lists a module's calls into the static code with the nearest constant in r0..r3, to find where a class passes a value the engine uses |
| `mt_vtables.py` | recovers every MT class's vtable, modules included |
| `fnmap.py` | maps functions between two games |
| `monster_actions.py` | lists a monster's actions from its dispatcher, and pairs handlers across games by action id |
| `extract_nsp.py` | extracts a Switch NSP's program code with your own keys |
| `loader_trace.py` | runs MHXX's `dttune`, `dtbase` or `dtbparts` loader, or MH3U's `em_status` walk, on every such file and checks `mhuc`'s readers against it ([specs/dttune.md](../specs/dttune.md), [specs/dtbase.md](../specs/dtbase.md), [specs/dtbparts.md](../specs/dtbparts.md), [specs/emstatus.md](../specs/emstatus.md)) |
| `trace_calls.py` | logs who calls chosen functions while the game runs in Azahar, through its GDB stub (standard library only; procedure in [docs/checks.md](../docs/checks.md#tracing-engine-calls-in-mhxx)) |
| `force_action.py` | forces the next action of the monster at the dispatcher in MHXX or MH3U through the same GDB stub; a debugging tool for a move, not check R1 |
| `monster_motions.py` | lists the motion each of a monster's action handlers starts, and compares two games' action ids by it (check R1 in [docs/checks.md](../docs/checks.md#monster-actions); [3U Rathian's moves](#a-3u-rathians-moves)) |
| `action_map.py` | joins two games' action and motion inventories: the MH4U handler each shared action id reaches, the ids only one game has, and the ids where the two sides' start motions differ (check R2 in [docs/checks.md](../docs/checks.md#the-shared-action-map-r2)) |
| `monster_handlers.py` | the 3U Rathian's 17 ids MH4U has no action for: each handler's engine calls and MH4U counterpart (`worklist`), and the shared MH4U action with the same handler for each missing id, with the proof (`targets`; [The 17 ids MH4U has no action for](#the-17-ids-mh4u-has-no-action-for)) |
| `monster_fields.py` | the fields two games' paired action handlers read: pairs the handlers by shared action, aligns their field reads/stores and calls, and prints each offset correspondence with its pair count (`map`); `check` re-derives the 3U field map's rows and fails where a count disagrees (procedure in [Extending the 3U field map](#extending-the-3u-field-map)) |
| `monster_attack_records.py` | the in-image action-start record a 3U move passes (44 bytes) and the value curves, their MH4U counterparts rebuilt from MH3U's, and the comparison with MH4U's own records ([specs/actiondata.md](../specs/actiondata.md), checks N1 to N4) |
| `spawn_tables.py` | MH4U's effect spawn tables: their shape and counts, every MEF record resolved through them, and a Unicorn run of the spawn's own code on one record or after the two `.data` writes that make an unused type name a ported effect ([specs/mef.md](../specs/mef.md#mh4us-spawn-tables), checks FX10 and FX11) |
| `monster_emc.py` | the native actions a monster's AI script starts (`00 cat num` in its rEnemyCmd), to tell an action the AI picks from one nothing reaches ([specs/emc.md](../specs/emc.md)) |
| `monster_emc.py` | the native actions a monster's AI script starts (`00 cat num` in its rEnemyCmd), to tell an action the AI picks from one nothing reaches, and the script cut with a game's own instruction-length table (`--lens ... --check`, [specs/emc.md](../specs/emc.md), check A2) |
| `monster_versions.py` | the player-visible comparison of every 3U and GU version MH4U shares, per axis, and the writer of [data/catalog/versions.csv](../data/catalog/versions.csv) ([how it is made](../data/catalog/versions.md)) |

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
| MH3U (3DS, USA) | `code.bin` | every function | gametest: 33,275 of 33,283 agree, the other 8 are test limits (6 run over the instruction budget, 2 read an inline descriptor); none returns a different state |
| MHXX (3DS, v1.4) | `code.bin` plus 109 CRO modules (every monster, weapon type, village…) | everything, modules at fixed bases in one library | module test: all 109 modules loaded, 36,665 functions in 108 of them (`roPlayerQuest05` has none), one test limit; no difference in state, memory or exit |
| MHGU (Switch, v1.4.0) | `main`, 32-bit ARM, monsters linked statically | not recompiled | used for matching functions only |

## Class registries

| Game | Classes | Monster classes | Base enemy |
|---|---|---|---|
| MH4U | 992 | 55 `uEm*`, all 0x8d90 bytes | `uEnemy` < `uMHchar` |
| MH3U | 1,218 | 41 `uEm*`, 0x1e70 to 0x2368 bytes | `uEnemy` (0x1e70) < `uCharacter` |
| MHXX | 3,109 with its modules | in the modules | `uFestaEnemy` < `uEnemy` < `uEnemyBase` |
| MHGU | 3,205 | in `main` | as MHXX; 2,949 class names shared with it |

MH3U's base enemy is a quarter of MH4U's size, and each monster adds its own state. MHXX's `uEnemy` has three times MH4U's virtual methods.

The only class either registry names for water is `uOcean` (`0x7e124a29`), which both games have with the same parent, size and vtable. The only other water-related name is MH3U's `uIDCockpitAir`, which MH4U lacks; it is registered but draws nothing of its own — the air gauge is a display of the player's oxygen timer, drawn by `uIDCockpitMain` ([underwater.md](../docs/underwater.md#what-mh4u-kept)).

## Cross-game function maps

| Map | Functions paired | Check |
|---|---|---|
| MH4U ↔ MHXX | 7,542 | held-out pairs recovered, 100 % correct |
| MH4U ↔ MH3U | 6,866 | held-out pairs recovered, 100 % correct |
| MHXX ↔ MHGU | 26,406 | 161 of 165 held-out functions right, none wrong |

Monster code itself doesn't pair function by function: MHXX rewrote Rathian into more, smaller functions. Pairing works through shared action ids instead.

### MHGU Definitive Edition's pairs

[MHGU Definitive Edition](https://github.com/Scrimas/MHGU-Definitive-Edition) pairs MH4U's functions with MHGU's, the other way round from us. Its `tools/match4u.py build` reads its own analysis of the two games and writes `dump/match4u/pairs.tsv`, with a rating per pair: C (a class seed whose name and parent match), S, W. Run in its own clone on our dumps it writes 7,108 pairs: 1,366 C, 1,404 S and 4,338 W. Its own `check`, against its API map, its slot pairs and its `game.h` brackets, calls 129 of the 132 slot pairs it can test right, 17 of 17 API C pairs, 22 of 22 `game.h` pairs and 20 of 21 API S pairs.

For the pairs alone, its `tools/setup.py` needs the steps `4u_exefs`, `4u_asm`, `gu_code`, `gu_reloc`, `gu_plt` and `gu_pcrefs`; its RomFS extraction and monster builds are not needed.

Its 4U side is the **EUR v1.1** build, ours the **USA v1.3.0** build. They are the same code with small layout shifts (0 to 0x54 bytes across `.text`) and some functions changed between the versions. A local byte shift, confirmed by the same instruction tokens at the shifted address, carries 6,620 of its 7,108 4U addresses into our build; 488 (7 %) cannot be anchored that way and are left out.

Of the 6,620, our maps pair 2,922 4U functions:

| Its rating | Its pairs | On a function we pair | Same GU function | Different GU function |
|---|---|---|---|---|
| C | 1,366 | 1,058 | 1,046 | 12 |
| S | 1,404 | 377 | 332 | 45 |
| W | 4,338 | 1,487 | 1,357 | 130 |
| **all** | **7,108** | **2,922** | **2,735** | **187** |

The other 3,698 are on 4U functions our maps don't pair. From our side, the composed MH4U → MHXX → MHGU map (3,192 pairs) has 2,026 on functions it pairs too (1,894 same, 132 different) and 1,099 on functions it never pairs; the direct MH4U ↔ MHGU map (4,057 pairs) has 2,701 (2,550 same, 151 different) and 1,276.

The 187 disagreements are mostly neighbours: 24 point within 0x100 bytes of each other, 36 more within 0x1000, 41 more within 0x10000, and 86 at unrelated code. Its 12 C-rated disagreements pair the same class slot in both games; where our own vtable recovery has that class and slot, it points at a different GU function, usually a thunk a few bytes away. They are places to read, not a verdict against either pair set.

Rathian's unmatched engine calls, seen through its pairs, are in the "Through MHGU" table below; the full account is on [#14](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/14).

## Rathian, the first port

| | MH4U | MH3U | MHXX |
|---|---|---|---|
| class | `uEm001` | `uEm002` (Rathalos's class) | `uEm001_00`, in `roEm001.cro` |
| action dispatcher | vtable slot 44, 0x006e9cac | slot 50, 0x00687d30 | slot 122, 0x02009704 (module at 0x02000000) |
| actions | 342 | 191 | 301 |
| distinct handlers | 97 | 66 | 83 |

- 273 of MHXX's action ids exist in MH4U. Of the shared actions that pass constants, 194 of 197 pass the same ones.
- Each of the 80 MH4U handlers reached by a shared action meets exactly one MHXX handler.
- For every shared id whose handler starts a constant motion in both games the index is the same (R2: 167 of 167), so a GU handler's constant is already MH4U's once the port's motion lists are MHXX's. 19 ids start a constant motion only in MH4U, 2 only in MHXX, and 18 are inline on one side; the 28 ids MH4U lacks reach 8 handler units, 15 of them projectile spawns ([#112](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/112)).
- Two of the 28 are not missing: MH4U's category-8 and category-12 cases test the index with `cmp #0; bne default`, which the action inventory misses. 12/0's MHXX handler 0x0201177c is the role pair of MH4U's 0x006d524c, which its category-12 case runs. 8/0 is the same action on both sides: MH4U runs 0x006e9770, whose frame values and tail (9/1 or 2/6) match MHXX's 0x0201b460, but the bodies differ, so the port translates MHXX's; its leaf 0x008c4184 is MH4U's 0x0092f6e8, whose table is not carried. The runtime's GU Rathian module (`mods/uc_runtime/src/monsters/rathian-gu.c`) runs the translated 3/98, 12/1-3, 4/27-32, 8/0 and category 17 and leaves 12/0; under decision 0002's 2026-11-26 amendment the port runs her own handler for every id, 12/0's included, which is still owed ([#213](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/213), [#215](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/215)). Its engine-call mapping and float stubs are in [the runtime's README](../mods/uc_runtime/README.md#gu-rathians-translated-actions) and [checks.md](../docs/checks.md#the-translated-actions-check-t1).
- `roEm001` imports 330 engine functions. 61 of those it calls have no MH4U counterpart. Through MHGU, 2 more resolve to MH4U and 28 are placed in GU only, mostly projectile code.

### Enemy class hierarchies

| Enemy hierarchy, slots per vtable | | | | |
|---|---|---|---|---|
| MH4U | `uMHchar` 38 | `uEnemy` 95 | `uEm001` 95 | |
| MH3U | `uCharacter` 42 | `uEnemy` 82 | `uEm002` 82 | |
| MHXX | `uEnemyCharacter` 79 | `uEnemyBase` 118 | `uEnemy` 283 | `uFestaEnemy` 287, `uEm001_00` 293 (in `roEm001`) |

MHXX's `uEnemy` has three times MH4U's virtual methods, and two classes MH4U lacks sit on either side of it (`uEnemyBase` below, `uFestaEnemy` above).

### Rathian's engine calls

**Rathian's MH4U engine calls by class.** Each callee is labelled with the class whose vtable first introduces it, or for a non-virtual function, the nearest common ancestor of its callers' classes (a heuristic):

| MH4U class | Callees | Calls | Placed in MHXX | in MH3U |
|---|---|---|---|---|
| `uEnemy` | 130 | 983 | 40 | 27 |
| `uCoord` (position, transforms) | 13 | 101 | 5 | 2 |
| `uEm001` (its own slots, also called from outside) | 18 | 70 | 2 | 1 |
| other monsters' classes (`uEm032`, `uEm103`, `uEm068`, `uEm089`...; code they share with Rathian) | 19 | 129 | 9 | 3 |
| `uMHchar` | 6 | 37 | 1 | 1 |
| `cUnit` | 2 | 19 | 2 | 1 |
| `MtObject` and the rest | 9 | 11 | 4 | 4 |
| **All** | **197** | **1,350** | **63** (550 calls; 51 land on `roEm001` imports) | **39** (302 calls) |

**What a GU Rathian needs from MHXX's engine.** `roEm001` imports 330 static functions. By MHXX class, with how many have an MH4U counterpart in the map:

| MHXX class | Imports | With MH4U counterpart | Without | Class in MH4U? |
|---|---|---|---|---|
| `uEnemy` | 93 | 9 | 84 | yes, much smaller |
| `uFestaEnemy` | 26 | 0 | 26 | no |
| `uFestaChar` | 24 | 3 | 21 | no |
| `uEmXXX` (the template enemy) | 19 | 17 | 2 | yes |
| `uShell` and `uShellEnemy`, `uShellEmBase*`, `uShellPlayer` (projectiles) | 50 | 2 | 48 | `uShell` only |
| `uEnemyBase`, `uEnemyCharacter`, `uEnemyActCustom`, `uEnemyOption` | 23 | 2 | 21 | no |
| `cUnit`, `MtObject` | 24 | 17 | 7 | yes |
| others (`uMonsterUnitConductor`, `sHitcheck`, `sHitPush`, `uPlayerQuest`, `uPlayerLobby`) | 9 | 1 | 8 | partly |
| no class (library and free functions) | 62 | 17 | 45 | |
| **All** | **330** | **68** | **262** | |

**What the handlers need from MHXX's engine.** | MH4U counterpart | Called by `roEm001`'s code | Not called (vtable slots, other data) |
|---|---|---|
| by code (map) | 86 | 12 |
| at the same call site of a mapped pair (role, not body) | 33 | 2 |
| none | **61** | 136 |
| **All** | 180 | 150 |

Step 1 had 68 with a counterpart; merging the module gives 91, the seeds 98, and call sites add 35. The 136 that are neither matched nor called are mostly `uEm001_00`'s inherited vtable slots (96), and pointers in the module's other data (39, the projectile classes' vtables among them). A port onto MH4U's `uEnemy` doesn't translate them: MH4U's base class provides its own. **The translation worklist is the 61 called functions with no counterpart:** 11 `uEnemy`, 17 projectile classes (`uShell` 9, `uShellEnemy` 3, `uShellEmBase*` 3, `uShellPlayer` 2), 19 with no class, 5 `uFestaEnemy`/`uFestaChar`, and 9 others (`uEnemyActCustom` 2, `uPlayerQuest` 2, `uEnemyBase`, `uEmXXX`, `sHitcheck`, `sHitPush`, `uPlayerLobby`). 9 of the 61 sit under an action that has an MH4U pair, so the MH4U handler shows how MH4U does the same. The other 52 are called outside the action handlers (update, setup and per-frame code). The 33 call-site matches are candidates to confirm one by one.

Through MHGU, with Definitive Edition's pairs:

| Set | Through GU to MH4U | GU counterpart only | No GU counterpart |
|---|---|---|---|
| 62 called imports with no MH4U counterpart (the "61" plus one with use `unknown`) | 2 (its full pair set: a `uFestaChar` material-dirty flag, rated S, and a `uEnemy` rank-table getter, rated W) | 28 | 32 |
| 33 call-site matches | 9 confirmed by its pairs, 7 differ, 3 with no pair of its own, 14 not checkable (no 4U address or no GU partner) | | |

The 28 placed in GU and not in MH4U are mostly projectile code (`uShell`, `uShellEnemy`, `uShellEmBase*`, 17) and GU-era framework slots: candidates for "MH4U lacks it". The 32 with no GU counterpart are mostly `uEnemy` and `uEnemyActCustom` functions without strings, where the next lever is Rathian's own code: pairing `roEm001` with GU's `uEm001_00` by the shared action ids, then reading the imports off aligned call sites.

### The 62 imports, one by one

Each of the 62 called imports with no counterpart in the map, read in MHXX's code (addresses in MHXX v1.4's `code.bin` and MH4U v1.3.0's). Two things make the list shorter than it looks:

- **"Festa" is MHXX's framework name, not a feature.** `sFestaMain` is the game's main object, `uFestaChar` the base of its characters (MH4U's `uMHchar`) and `uFestaEnemy` the layer between `uEnemy` and each monster, which MH4U doesn't have.
- **MH4U has no shell framework like MHXX's.** MHXX builds Rathian's projectiles on `uShellEnemy` and `uShellEmBase*` classes driven by an `rShell` resource of parameters per shell type. MH4U has none of these classes: its projectiles are numbered classes (`uShell000` to `uShell059`) made by one factory, 0x660e60, which takes a type number and a setup block; uEm001's handlers reach it through 0x661bc4 (type 1) and 0x661cf0 (type 5). A ported Rathian's projectiles become MH4U shell types, so the MHXX shell functions below have no one-to-one counterpart.

| MHXX | Class | What it does | MH4U |
|---|---|---|---|
| 0x001d7c7c | `uFestaChar` | releases up to three material references and clears them | 0x001a64c0 (through GU, Definitive Edition's pair) |
| 0x00add36c | `uEnemy` | reads one byte from a table of 12-byte entries in the monster's work block | 0x009473e4 (through GU, Definitive Edition's pair) |
| 0x0089f01c | `uFestaEnemy` | constructor: calls `uEnemy`'s, sets the vtable, clears the layer's fields | 0x00955eac, `uEnemy`'s constructor, which uEm001's own chains to directly |
| 0x008f2a20 | | `uEm001_00`'s operator delete: frees through its class's allocator | 0x006ec8dc, uEm001's operator delete |
| 0x008b7978 | | whether target point *n* lies on the monster's left: angle from the monster to the point, minus its heading, under 0x8000 | 0x0091e0f8, the same steps on MH4U's layout |
| 0x008c50a4 | | angle from the monster to target point *n* relative to its heading, optionally folded to one side | 0x009307f8, the same steps on MH4U's layout |
| 0x0089f018 | `uFestaEnemy` | vtable slot 2, forwards to `uEnemy`'s slot 2 | MH4U lacks it: slot 2 is empty in MH4U's `uEnemy` and uEm001 |
| 0x008ea160 | `uFestaEnemy` | vtable slot 6, empty | MH4U lacks it: nothing to port |
| 0x008eb0b4 | `uEnemy` | vtable slot 240, empty | MH4U lacks it: nothing to port |
| 0x008eb3d8 | `uEnemy` | vtable slot 239, empty | MH4U lacks it: nothing to port |
| 0x0046dfb0 | | operator new of `uShellEmBase00::cSetupParamEmBase00`, the setup block each fireball spawn builds (51 actions) | MH4U lacks it: MH4U fills a setup block on the stack for its factory |
| 0x0046f070 | | operator new of `uShellEmBase01::cSetupParamEmBase01` (40 actions) | MH4U lacks it, as above |
| 0x0046ebac | | `uShellEmBase00`'s constructor | MH4U lacks it: no `uShellEmBase*` classes |
| 0x0046ecdc | `uShellEmBase00` | `uShellEmBase00`'s destructor | MH4U lacks it |
| 0x0046fe80 | | `uShellEmBase01`'s constructor | MH4U lacks it |
| 0x0046ffa8 | `uShellEmBase01` | `uShellEmBase01`'s destructor | MH4U lacks it |
| 0x00476130 | | `uShellEmBase11`'s constructor | MH4U lacks it |
| 0x005a6920 | | operator delete of `uShellEm001_sp_00`, one of Rathian's three projectile classes | MH4U lacks it: Rathian's projectiles are factory shell types |
| 0x005a6950 | | operator delete of `uShellEm001_sp_01` | MH4U lacks it, as above |
| 0x005a6980 | | operator delete of `uShellEm001_sp_11` | MH4U lacks it, as above |
| 0x008cdfbc | | wrapper: calls the large `uEnemy` function 0x008a736c (a per-mode speed or distance computation) with its flag set | 0x00939034, the same wrapper around MH4U's 0x00b06b4c (the flag-clear wrappers 0x008a7360 and 0x0091aae4 are aligned in paired handlers) |
| 0x00265a9c | `uShellEnemy` | plays a sound at the shell when its owner is the local player | MH4U lacks it: each `uShellNNN` plays its own sounds |
| 0x00265bf8 | `uShellEnemy` | sets the shell's scale and scales its two hit spheres by it and an `rShell` factor | MH4U lacks it |
| 0x009285b0 | `uFestaChar` | registers a shell with its owner (up to 144) and checks its type against the shell-type table (58 actions) | MH4U lacks it: no shell registry or `rShell` |
| 0x00928e70 | `uPlayerQuest` | puts a shell in its owner's slots for that type (16 per type) and loads the type's `rShell` resource the first time | MH4U lacks it |
| 0x009649a4 | `uShellPlayer` | the shell's `rShell` hit parameters, or none | MH4U lacks it |
| 0x009651a4 | `uShell` | whether the shell's `rShell` entry has hit data | MH4U lacks it |
| 0x00aed660 | `sHitcheck` | the shell's type id from its setup block | MH4U lacks it |
| 0x00aed6d4 | `uShell` | the shell's owner index from its setup block | MH4U lacks it |
| 0x00aed6e8 | `uShell` | the shell's owner, if it is a character | MH4U lacks it |
| 0x00aedc40 | `uShell` | whether the shell's owner is still active | MH4U lacks it |
| 0x00aed824 | `uShell` | queries the attack parameters of the owner's `rShell` entry | MH4U lacks it |
| 0x00aed8a8 | `uShell` | queries a second parameter set of the same entry | MH4U lacks it |
| 0x00aed928 | `uShell` | reads a float from the entry's effect parameters | MH4U lacks it |
| 0x00aed9b8 | `uShellPlayer` | queries the entry's effect parameters | MH4U lacks it |
| 0x00aedac4 | `uShell` | reads a float from the resource's own effect parameters | MH4U lacks it |
| 0x00aedb64 | `uShell` | another query of the entry's effect parameters | MH4U lacks it |
| 0x008d0d7c | `uEnemyActCustom` | turns the monster towards target point *n* by a step scaled from its speed, and says when it faces it | MH4U lacks it: `uEnemyActCustom`, GU's turning layer, isn't in MH4U; its monsters turn in their own handlers (uEm001's 0x006d56cc passes the angle to the target to 0x00918e48) |
| 0x008d4928 | `uEnemyActCustom` | sets up a turn: stores its parameters and picks left or right from the angle to the target | MH4U lacks it, as above |
| 0x008db468 | `uEnemy` | the attack target's position: from the lock-on object if there is one, else the monster's own target point | 0x0093685c, called at the same place in the paired handlers of actions 3/6 and 3/7 |
| 0x008cc434 | | among the loaded monsters, claims the first active one of a given species outside the given area and flags it | 0x009179f4, the same steps, plus a branch for one MH4U state |
| 0x008d0ec8 | | among the loaded monsters, sends a message to each active one of a species in an area, optionally within a radius | 0x0093c160, the same loop over MH4U's 32 monster slots |
| 0x008e3628 | | checks a linked monster in the same area and its distance (500 units); under action 13/1 only | MH4U lacks it: the paired MH4U handler (0x006db540) has no call at that point |
| 0x008ae1c8 | | plays a sound at a joint (or the monster's root) for the local player; at run time, called in fights from code under `uEnemy`'s vtable slot 10 | 0x304c10, MH4U's copy of the same wrapper for a monster owner (it takes the joint's position with 0xb0545c and requests the sound with the owner through 0x3120dc, type 8); MH4U has three more copies for other owners (0x3052a0 type 7, 0x307554 type 9, 0x3038ac type 10) where MHXX has one. During a Rathian fight a shell's update (`uShell001` slot 22) called it for its owner |
| 0x008a1fc8 | `uEnemy` | forwards a request with a position to a manager's method 0x002cf3b0 | 0x002b9c38, the manager method, which MH4U calls directly (as with the confirmed pair 0x008a200c and 0x002b9cb4) |
| 0x008a1ed8 | `sQuest` | the quest manager's grade getter: it looks the quest id at `sQuest`+0xd8 up in the quest table (a signed byte); with no entry it returns 0 for id 0xf9074 and 16 for the other ids in 0xf906f..0xf907e. The caller uses the result as an index into a 17-entry multiplier table; Rathian tests it (at least 9) in one state | MH4U lacks it: MH4U has no `sQuest` class (no `sQuest::SupplyBox`, `sQuest::ShareBox` or `sQuest::BossLoader`; only `sQuestNpc`), so this quest-grade getter has no counterpart. The class was identified at run time: the singleton at 0xd3d24c has vtable 0xcf8004, which is `sQuest`'s |
| 0x008a1934 | `sHitPush` | asks the hit-push manager about a player (GU's label: player absent) | 0x006832a0, called at the same place in Rathian's paired vtable slot (MHXX 0x0201ccd4, MH4U 0x006ebfd8) |
| 0x008a7844 | `uEnemyBase` | applies a model part group: sets each part's visibility bit in the monster's mask | 0x009428a8, the same bit updates; MH4U takes its one part list from the monster's data instead of a group argument |
| 0x008d8768 | `uEnemy` | saves or clears the monster's status flag sets, by mode | MH4U lacks it: the paired MH4U handler (0x006d5e98) has no call at that point |
| 0x008ddad8 | | selects an entry by index from a table of 36-byte entries in the monster's data (one of two tables, by the quest's state) and keeps its last field | 0x00947400, the same table at +0x74 of the same data block; MH4U copies the whole entry |
| 0x008f1c1c | | reacts to a hit from one shell type: by the shell's kind, one of three reactions with strength 200 | 0x0086ff20 does the reaction part, with the same three reactions (0x00923ba4, 0x00917b60, 0x0091dc8c) in the same order; in MH4U the shell code calls it, not the monster |
| 0x0089e698 | `uFestaEnemy` | vtable slot 76: builds a capability mask in a `uFestaEnemy` field from two of the monster's states | MH4U lacks it: the field belongs to the `uFestaEnemy` layer, and no MH4U function builds that mask |
| 0x0089eb70 | | a rate for a part condition, from two part entries or a default, all `uFestaEnemy` fields (+0xb730 to +0xb76c) | MH4U lacks it: those fields are the `uFestaEnemy` layer's, which MH4U doesn't have |
| 0x008bb4c0 | `uEnemy` | raises a request flag with an id in the work block | 0x00922104, the same two stores (0x00933fe4 clears them) |
| 0x008c86d4 | `uEnemy` | clears one byte at this+0x6b00 when called with 0 (the setter 0x8bf728 sets it); at run time, called in fights from code under `uEnemy`'s vtable slot 9 | MH4U lacks it: no MH4U code reads or writes a byte at this+0x6b00, nor at the 0x280-lower +0x6880 the work-block translation would give. The whole code was searched; MHXX's four accesses are all in the set and clear helpers |
| 0x00adb338 | `uEnemy` | one of two entries of the monster's data table, chosen by the work block's state 0x67 | 0x0091dee8 (the monster's data entry), called at the same place in action 3/78's paired handler |
| 0x00adcd4c | `uEnemy` | a mask from the work block's state flags and kind | 0x00911cfc, the same masks |
| 0x00adcf38 | `uEnemy` | a second mask of the same kind | 0x0091df88, the same masks |
| 0x008eb1c0 | | updates one part's damage state (states 1 to 3) and raises flags in the work block | 0x0094e364, the same switch on the state byte with the same bits (1, 2, 8) in a 16-bit flag field and the same state bytes; the callee pair agrees (MHXX 0x8b7660 = MH4U 0x91dbd4). MH4U goes on to the hit's position and effect; MHXX tail-calls 0x8da948 |
| 0x00a56ee0 | `MtObject` | calls a virtual method with the 16-bit id at +0x24c; at run time, called every frame by the player's and its weapon's code (`uPlayerBase`, `uPlWeapon`) | MH4U lacks it: no function forwards a u16 field to a vtable slot, and `uPlayer`'s slot 45, which MHXX uses for this (0xa5d818, a packed-id converter), is empty (0x0) |
| 0x008ad638 | `uPlayerQuest` | a player's 16-bit field at +0x24c, at +4 of the block at +0x248 whose two floats at +0x40/+0x44 the speed setter 0x001e3950 recomputes; at run time, read in quests by Rathian's module and by `uEnemyActCustom` code | MH4U reads the same field inline at +0x244 (0x937d44, the twin of MHXX's caller 0x8cc708, does `ldrh r3,[r1,#4]` on `this+0x240`); it is also vtable slot 33, 0xb05154 (`uEnemy`) and 0xb08c0c (`uPlayer`, `uPlChar`, `uWeapon`) |
| 0x001e3950 | `uPlayerLobby` | sets a speed and recomputes two ratios from it; at run time, called in menus by `uPlayerPreview`, the hunter preview, so likely a model's motion-speed setter rather than player code | 0x00b065d4, the same float math on MH4U's layout (speed +0x29c, base +0x284, rates at +0x240+0x40/+0x44) |

Of the 62: 23 have an MH4U function, 39 are things MH4U lacks (26 of them the shell framework), none is left open. The joint sound was settled by tracing a Rathian fight in MH4U (the procedure in [docs/checks.md](../docs/checks.md#tracing-engine-calls-in-mhxx), the same tracer on MH4U's addresses); the quest manager by reading the singleton's vtable at run time; the flag by searching both games' whole code for the field.

Three ways found the matches. Translating field offsets: MHXX's work block at +0x10a8 is MH4U's at +0xe28; within it MHXX's +0x40 (position) and +0x54 (heading) are MH4U's +0x198 and +0x1ac, +0x1d0 (target points) is +0x218, +0x1a8 and +0x1ba are +0x1b4 and +0x1c8, and the +0x5900 area is about 0x2160 further on in MH4U. Aligning call sequences: the handlers of a shared action call the same engine functions in the same order, so an import sits where its MH4U counterpart, or nothing, does. The alignment also confirms two of the call-site matches above (0x008a200c with 0x002b9cb4, 0x008a2298 with 0x002bab8c). Comparing the functions' instruction tokens ([fnmap.py](fnmap.py)'s NGRAM index) over the whole code catches the pairs the map's seeds don't reach (0x001e3950 with 0x00b065d4 at 0.82 both ways, 0x008eb1c0 with 0x0094e364); confirming such a pair means reading it, or its twin caller: 0x937d44, MH4U's counterpart of MHXX's 0x008cc708, reads the same u16 inline that 0x008ad638 returns.

### What a 3U Rathian needs from MH3U's engine

Her own code is the block at 0x00686000 to 0x0069b000, which holds `uEm002`'s action dispatcher (vtable slot 50, 0x00687d30), its 66 handlers and the class's other methods. The 66 handlers call **101 engine functions 1,207 times**; the calls counted here are the ones that leave that block. (Her class's non-action methods, update and setup, call further engine functions, not counted here.)

Every engine function falls into one of these:

| How the counterpart was established | Functions | What it means |
|---|---|---|
| In the function map, same body | 18 | the map pairs the two functions; their instruction tokens match |
| Found by reading, same steps | 14 | the same computation at shifted field offsets or with translated constants |
| The same effect or shell class, from a factory | 4 | MH4U's factory builds the same class, or the paired handler calls it at the same place |
| The same call in a paired handler (role, not body) | 37 | the two handlers of a shared action call at the same point; these are candidates to confirm one by one, as in GU's table |
| **With a counterpart** | **73** | |
| MH4U lacks it | 9 | the class or helper has no MH4U equivalent |
| Needs an in-game trace | 19 | no MH4U function with these steps was found: the whole-code token index's candidates are too short to be evidence, and the paired handlers have no call left for it; a trace of an MH4U Rathian fight ([docs/checks.md](../docs/checks.md#tracing-engine-calls-in-mhxx), on MH4U's addresses) says which MH4U code runs where it does the same job |
| **Without** | **28** | |

**By MH3U class.** Each callee is labelled with the class whose vtable first introduces it, or its callers' nearest common ancestor (a heuristic, as in the table above):

| MH3U class | Engine functions | Calls | With an MH4U counterpart | Without |
|---|---|---|---|---|
| `uEnemy` | 62 | 990 | 41 | 21 |
| `uEm004` | 14 | 82 | 14 | 0 |
| `cUnit` | 8 | 39 | 8 | 0 |
| `(no class)` | 2 | 2 | 1 | 1 |
| `uCharacter` | 2 | 8 | 1 | 1 |
| `uEm024` | 2 | 26 | 0 | 2 |
| `uEm066` | 2 | 12 | 0 | 2 |
| `MtObject` | 1 | 2 | 1 | 0 |
| `uEm007` | 1 | 2 | 1 | 0 |
| `uEm015` | 1 | 7 | 1 | 0 |
| `uEm019` | 1 | 2 | 1 | 0 |
| `uEm022` | 1 | 13 | 1 | 0 |
| `uEm025` | 1 | 1 | 1 | 0 |
| `uEm040` | 1 | 15 | 1 | 0 |
| `uEm056` | 1 | 4 | 0 | 1 |
| `uShell` | 1 | 2 | 1 | 0 |
| **All** | **101** | **1,207** | **73** | **28** |

### The 73 with an MH4U counterpart

Addresses are MH3U's `code.bin` and MH4U v1.3.0's. "Map" means `fnmap.py` pairs the two bodies; "call site" means the same call in the paired handler of a shared action, which is a role match and a candidate to confirm.

| MH3U | MH4U | How |
|---|---|---|
| 0x0015f410 | 0x00c0760c | effect factory, type 8 |
| 0x00164f08 | 0x00c0760c | effect factory, type 8 |
| 0x0016669c | 0x00c0760c | effect factory, type 9 |
| 0x0031be10 | 0x0091b0f8 | call site of a paired handler |
| 0x00584760 | 0x00be1d90 | same steps |
| 0x0058493c | 0x00aac8dc | map, same body |
| 0x00584cd8 | 0x00568c64 | call site of a paired handler |
| 0x005852b4 | 0x00aacc0c | map, same body |
| 0x00585384 | 0x00568c64 | call site of a paired handler |
| 0x005858f4 | 0x00aacd50 | map, same body |
| 0x00585f30 | 0x00aacd84 | identical |
| 0x005aef18 | 0x0067c974 | same wrapper (0.88); its worker 0x5864c4 is 0x67c9c0 |
| 0x005bde78 | 0x00948548 | call site of a paired handler |
| 0x0063e4ac | 0x00661bc4 | shell factory, type 1 |
| 0x00828828 | 0x0094e318 | call site of a paired handler |
| 0x0082a06c | 0x0094ef64 | call site of a paired handler |
| 0x0082a878 | 0x0094f408 | call site of a paired handler |
| 0x0082b268 | 0x00955440 | call site of a paired handler |
| 0x0082b8f0 | 0x00955a5c | call site of a paired handler |
| 0x0082c1c4 | 0x0090f8fc | call site of a paired handler |
| 0x0082cee4 | 0x00912288 | map, same body |
| 0x0082d278 | 0x00911c0c | call site of a paired handler |
| 0x0082d430 | 0x0092f6e8 | call site of a paired handler |
| 0x0082fc8c | 0x00916228 | call site of a paired handler |
| 0x0082fe88 | 0x009167b4 | map, same body |
| 0x0082ffbc | 0x00935f8c | call site of a paired handler |
| 0x008310f0 | 0x0093d870 | call site of a paired handler |
| 0x00832670 | 0x00914de0 | same steps |
| 0x00832690 | 0x00918ef0 | call site of a paired handler |
| 0x008326dc | 0x00919788 | call site of a paired handler |
| 0x0083336c | 0x0091aae4 | call site of a paired handler |
| 0x0083369c | 0x00942220 | call site of a paired handler |
| 0x00833b2c | 0x00915d44 | call site of a paired handler |
| 0x00833d88 | 0x00916108 | call site of a paired handler |
| 0x00834098 | 0x00911090 | map, same body |
| 0x008345f8 | 0x0091b7b0 | same steps (0.89) |
| 0x008357b0 | 0x0091db4c | call site of a paired handler |
| 0x00836c04 | 0x00918e48 | map, same body |
| 0x00837594 | 0x00918f38 | call site of a paired handler |
| 0x00838c28 | 0x0091a84c | call site of a paired handler |
| 0x008392d8 | 0x0091aaf0 | call site of a paired handler |
| 0x00839514 | 0x0091b430 | same wrapper |
| 0x00839968 | 0x0096e164 | map, same body |
| 0x00839ea0 | 0x0091b430 | call site of a paired handler |
| 0x0083c6e0 | 0x00922250 | map, same body |
| 0x0083c79c | 0x0093ba88 | call site of a paired handler |
| 0x0083cbf4 | 0x00b05da4 | call site of a paired handler |
| 0x0083cbfc | 0x00922c40 | call site of a paired handler |
| 0x0083d18c | 0x00922ca0 | call site of a paired handler |
| 0x0083d1a4 | 0x0092e4f8 | map, same body |
| 0x0083db3c | 0x00923f90 | map, same body |
| 0x0084134c | 0x0092b140 | call site of a paired handler |
| 0x008437f4 | 0x0092dc50 | call site of a paired handler |
| 0x008438e8 | 0x0092dccc | call site of a paired handler |
| 0x00844004 | 0x0092e408 | map, same body |
| 0x008440a4 | 0x0093c938 | same steps (0.71) |
| 0x00844100 | 0x0092e960 | same steps (0.88), offset translated |
| 0x00844124 | 0x0092e99c | map, same body |
| 0x00844a38 | 0x00914dc4 | call site of a paired handler |
| 0x00844a40 | 0x0093310c | call site of a paired handler |
| 0x0084704c | 0x00938748 | map, same body |
| 0x00847134 | 0x00938834 | same steps (0.58) |
| 0x0084c1ac | 0x00939988 | identical |
| 0x0084d790 | 0x0096e164 | same steps (0.91) |
| 0x0084d7e4 | 0x00938f6c | map, same body |
| 0x0084dc84 | 0x00935a90 | same steps (0.70) |
| 0x0084e74c | 0x00935fb8 | call site of a paired handler |
| 0x00850860 | 0x00917570 | map, same body |
| 0x008509a0 | 0x0093cd70 | call site of a paired handler |
| 0x00850a50 | 0x0093ce60 | map, same body |
| 0x00852324 | 0x0093d870 | map, same body |
| 0x008565d8 | 0x00947d0c | same loop |
| 0x00a37714 | 0x00b0545c | the thunk target 0xa07d48 is 0xb0545c (0.83), same steps at translated offsets |

### The 28 with no MH4U counterpart

Read in MH3U's code; the last column says what MH4U does instead, or that a trace in the running game is needed to find the MH4U function.

| MH3U | Class | What it does | MH4U |
|---|---|---|---|
| 0x0016052c | `uEnemy` | spawns a `uEffect039` (0xe0 bytes: allocated through 0x1d9844, constructed by 0x1d97b8, registered with 0x5a16fc) | MH4U lacks it: it has no `uEffect039` class (its effect classes stop at `uEffect021` and `uEffect022`), and its effect factory 0x00c0760c has no type for one |
| 0x00161798 | `uEnemy` | forwards the object at +0x3f0 to 0x25e264 when it is set | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x905384, 0.53; the paired handlers 0x006dc274 and 0x006deabc have no spare call (best 0xb0704c, 0.0). |
| 0x00257628 | `uEnemy` | sets a byte at +0x1c8 of the object at +0x14, from r1 (-1, 0 or 1) | Needs an in-game trace: no MH4U function with these steps was found. No token candidate; the paired handlers 0x006e9770, 0x006ea05c and 0x006dcfcc have no spare call (best 0.0). |
| 0x005bf66c | `uEnemy` | sets the byte at +0xd61 of the block passed in r1 | MH4U lacks it: the paired handlers (0x006dbffc for action 13/8, 0x006dc274) call none of these aim helpers; MH4U's same actions spawn a factory shell (0x00661bc4), which takes the point in its setup block |
| 0x005bf77c | `uEnemy` | stores a 3-float point at (r1+0xc00)+0x198 and copies a point from +0xd60+0x38 to +0xda8 | MH4U lacks it: the paired handler (0x006dc274) calls none of these aim helpers; MH4U's same action spawns a factory shell (0x00661bc4) |
| 0x005bf7bc | `uEnemy` | turns three floats into values through 0x5c4080 and stores them at +0xde0, +0xde4 and +0xde8 | MH4U lacks it: as above, no such call in the paired handler |
| 0x005c0614 | `uEnemy` | clears +0xd61, then copies a 2-float point into +0xd60+0x38 and a scale into +0xd64+0xc | MH4U lacks it: as above, no such call in the paired handler |
| 0x005c34c0 | `uEnemy` | calls 0x886ef8 with a global: copies the point at global+0x18 to r0 | MH4U lacks it: no such call in the paired handler (0x006dc274) |
| 0x005c3f88 | `uEm024` | builds a point from a speed, a table entry and two positions, then stores it at +0xc00+0x198 | MH4U lacks it: no such call in the paired handlers (0x006dbffc, 0x006dc274) |
| 0x005c6938 | `uEnemy` | compares a point's coordinate (copied by 0x886ef8) with r1 scaled by a constant | MH4U lacks it: no such call in the paired handler (0x006dc274) |
| 0x005c7270 | `uEm024` | a trajectory setup: switches on a type (1 to 7) and builds points through 0x584e18 | MH4U lacks it: no such call in the paired handler (0x006dc274) |
| 0x0064325c | `uEnemy` | maps the byte at +0xed through a 0xff table and returns an address in the block | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x7b9dd4, 0.39; the paired handler 0x006d6be0 has no spare call (best 0.0). |
| 0x00829620 | `uEnemy` | a per-frame helper: reads a signed byte at +0x940 and walks the action table | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x911f20, 0.48, itself the best spare call of 0x006dbd8c; the paired handlers 0x006ea05c and 0x006dcfcc have none. |
| 0x00833234 | `uEnemy` | walks the monster list at the global manager and resets an entry per index | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x910480, 0.45; the paired handler 0x006d5e98's spare calls top out at 0x945584, 0.35. |
| 0x00835f10 | `uEm066` | a large helper (130 tokens) around the positions at +0x1800+0x248, not read to the end | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x852d3c, 0.51; the paired handlers 0x006d5e98, 0x006db948 and 0x006dbbe4 have no spare call above 0.48. |
| 0x0083771c | `uEnemy` | tests bit 2 of +0x8c and sets up a position and a timer | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x9008bc, 0.42; the paired handler 0x006dc274 has no spare call (best 0.0). |
| 0x00839598 | `uEnemy` | returns the signed byte at +0xef of the monster's data block | Needs an in-game trace: no MH4U function with these steps was found. No token candidate over 5 tokens; its 9 paired handlers have no spare call (best 0x911c7c, 0.40). |
| 0x0083c6cc | `uEm066` | returns the float at this+0x284 times a constant | Needs an in-game trace: no MH4U function with these steps was found. No token candidate over 4 tokens; its 4 paired handlers have no spare call (best 0.0). |
| 0x0083db24 | `uEnemy` | sets the byte at +0x259 to 1 | Needs an in-game trace: no MH4U function with these steps was found. Closest token matches 0x970674, 1.0 over 6 tokens, and 0x8618c0, 0.86; the paired handler 0x006d5e98's best spare call is 0x93c690, 0.6. |
| 0x0083dc14 |  | walks the monster list and tests entries by their state at +0xd5c | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0xc1efa0, 0.46; the paired handler 0x006d5e98's spare calls top out at 0x916b94, 0.24. |
| 0x0084161c | `uEm056` | calls 0xa07d48 and copies a point from +0x30, then stores it | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x90b640, 0.45; the paired handlers 0x006e148c and 0x006e0794 have no spare call (best 0.0). |
| 0x00842a7c | `uEnemy` | a large function (710 tokens): a hit reaction or attack resolution, not read to the end | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x93aae8, 0.53 over 710 tokens; its 11 paired handlers have no spare call (best 0.0). |
| 0x00843c20 | `uEnemy` | sets a scale at +0x894 and the byte at +0x923 to 1 | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x9a8b34, 0.86; the paired handlers 0x006db3dc, 0x006db540 and 0x006db948 have no spare call (best 0.0). |
| 0x0084512c | `uEnemy` | walks the monster list, reads +0xd5c and picks an entry by a state byte | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0xc1aa40, 0.43; the paired handlers 0x006e9770, 0x006dcb10 and 0x006dcd7c have no spare call above 0x92b2b0, 0.35. |
| 0x00847798 | `uEnemy` | forwards to 0x59070c when r2 is 0, with a global | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0xa8e1dc, 0.71; the paired handlers 0x006dbec0, 0x006dec6c and 0x006ded84 have no spare call (best 0.0). |
| 0x0085162c | `uEnemy` | sets the float at +0x97c to 1.0 | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0x9a9238, 0.92; the paired handler 0x006dbd8c has no spare call (best 0.0). |
| 0x00853c70 | `uEnemy` | sets the halfword at +0x89c to 2 | Needs an in-game trace: no MH4U function with these steps was found. Closest token match 0xb1c0cc, 0.92; the paired handlers 0x006e9770, 0x006dcb10 and 0x006dcd7c have no spare call (best 0.0). |
| 0x00a347bc | `uCharacter` | maps r1 (0 to 0x1c) through a 0xff table and returns the entry | Needs an in-game trace: no MH4U function with these steps was found. No token candidate; the paired handlers 0x006db3dc, 0x006db540 and 0x006db948 have no spare call (best 0.0). |

**What was searched for the 19.** `fnmap.py`'s instruction-token index (NGRAM) over both games' whole code gives each of them its closest MH4U bodies, scoring 0.39 to 1.0, the highest only over 4 to 10 tokens where a score says little; some have no candidate at all. Aligning her handlers with their MH4U counterparts (the call-site method above) shows no unmatched call left where one should be: the nearest spare call in each paired handler scores 0.0 to 0.6, and none is the function in question. An in-game trace is what settled the joint sound and the quest manager for MHXX (same tracer, MH4U's addresses); these 19 need it too. They are tracked in issue #55.

### The base-class helpers behind category 0 and 0x0082d054

The 101 functions above are the ones the 66 handlers call outside her block. The
dispatcher also reaches `uEnemy`'s own action code: category 0's 0/2, 0/3 and 0/6
(0x0082d1cc, 0x00858b6c and 0x0082b7dc) and 3/2's and 12's 0x0082d054. Decision 0002's second
2026-11-26 amendment makes those handlers port code too, so what still needs MH4U's
counterpart is each engine function they call, not the handlers themselves.

| MH3U handler | Actions | What it does | MH4U's own handler |
|---|---|---|---|
| 0x00699ad4 | 0/0, 0/4 | a two-step delay: sets mode 0 and starts the follow-up through 0x0082a878 (0xa), then subtracts a float from another and, once the result is below zero, falls into the 0/2 handler 0x0082d1cc | — (her own handler; its calls are in the 73) |
| 0x0082d1cc | 0/2 | sets mode 0, picks one of three sub-states from the monster's state byte and action category, applies 0x008412cc, starts the next action with 0x00827d54(0, 0, 1 or 2, 2), sets work+0xf2 | 0x00911b48, the base method MH4U's own 0/2 case block calls through `[vtable+0x164]`: same steps read (0x009167b4 with 0, the state test, 0x0090ef74 with (0, 0/1/2, 2), the run flag), 0.57 by token |
| 0x00858b6c | 0/3 | adds the data record's +0x70 value, scaled by the block's +0x90 and +0x94 factors, to work+0x3c when the mode is 0 or 3, sets mode 1, then unless the action category is 0xb applies 0x008412cc and starts 0x00827d54(0, 3, 2), sets work+0xf2 | 0x0094dc84, MH4U's own 0/3 handler: same steps read, 0.81 by token |
| 0x0082b7dc | 0/6 | sets mode 3, then unless the action category is 0xb applies 0x008412cc and starts 0x00827d54(0, 6, 2), sets work+0xf2 | 0x00955970, MH4U's own 0/6 handler: the same calls in the same order with the same arguments |
| 0x0082d054 | 3/2, 12 | a five-step state machine on work+5: 0x00852324, 0x00844124 and 0x00828828 then 0x008509a0; 0x00850a50, 0x00852324 and 0x0083369c, mode 3 and 0x00828828(0x1d); 0x0083cbf4 then 0x00828828(0x2e); 0x0083cbf4, mode 0 and 0x00828828(0x41); 0x0083cbf4 then 0x0082d1cc | not read |

**The helpers those handlers call**, with MH4U's counterpart or its absence:

| MH3U | Class | What it does | MH4U | Evidence |
|---|---|---|---|---|
| 0x0082fe88 | `uEnemy` | the mode/state setter: stores the mode byte at the work block's +0xdc after per-mode side effects (mode 0 and 4 refill work+0x3c from +0x120, mode 2 does when +0x25e is set, mode 3 copies the data record's +0x70 to work+0x280), and returns early when the byte already holds the argument | 0x009167b4 | map, same body (in the 73); called at the same point with 0, 1 and 3 by the 0/2 (0x0082d1cc/0x00911b48), 0/3 (0x00858b6c/0x0094dc84) and 0/6 (0x0082b7dc/0x00955970) handler pairs |
| 0x00827d54 | `uEnemy` | starts the next action: writes the new category at work+0xdf and index at work+0xe0, a u16 at work+0xe6, resets the action's state bytes and flags (work+5/6/7, +0x956..+0x95a, +0xf6, +0xc27), and notifies the manager through 0x002dc3e8 | 0x0090ef74 | the same call at the same point in the 0/2, 0/3 and 0/6 handler pairs, with the same (category, index, kind) plus one stack argument MH4U adds; 0.62 by token over 507 against 511 tokens, and read: same prologue, state writes, two-entry slot loop and manager call at translated offsets |
| 0x00a33b50 | `uEnemy` | returns the monster's data record from the manager's table at its +0xdc, indexed by the block's +3 (a kind) and +0xa (an index); only kind 0x20 uses the seven-entry index, every other kind reads entry 0 | 0x0068882c | called at the same point in the 0/3 handler pair, and in the pairs 0x00852324/0x0093d870 and 0x0083db3c/0x00923f90, which read the record's +0x70 and +8 against MH4U's +0x64 and +4; MH4U looks the record up by the monster id at +0x1c0 |
| 0x008412cc | `uEnemy` | looks the current action up in a list of 4-byte `{category, index, s16 value}` entries at `[0x0084d3d0(this)+0x3c]+8`, then tail-calls 0x0085033c with the value and work+0x942; 0x0085033c moves a u16 at work+0x944, capped by work+0x942 from the +0x7f8/+0x7fc ratio and the monster's state, and may call 0x008518a4 | MH4U lacks it | none of MH4U's 0/2 (0x00911b48), 0/3 (0x0094dc84) or 0/6 (0x00955970) handlers has a call at that point; the 0/3 and 0/6 ones call 0x009167b4, 0x0090ef74 and 0x0068882c there, and the 0/2 one 0x009167b4, a state predicate 0x0092e960 and 0x0090ef74. The token index's best is 0x0092e1e0 at 0.53 over 31 against 52 tokens, which is a predicate over a 3-byte-entry list at `[record+0x38]` returning a flag, not an applier; 0x0085033c's own best is 0.38 over 157 tokens |

Everything else these handlers call is already in the 73 table: 0x0082a878
(0x00699ad4 and the inline 0/1 case), 0x0083cbf4 (the category 0 case blocks), and
0x00852324, 0x00844124, 0x00828828, 0x008509a0, 0x00850a50 and 0x0083369c (0x0082d054).
So 0x0082d054's eight callees are all covered; only its handler, and the three `uEnemy`
handlers, are new port code. The 73's rows are the evidence for those, not repeated here.

The 0/3 and 0/6 pairs, and the 0/2 pair through the `[vtable+0x164]` call, are what
settled the three matches: each pair calls its helper at the same point with the same
arguments, and the 73 already maps 0x0082fe88 there. 0x008412cc is the one helper of the
set MH4U does not have as its own function; whether MH3U's step is folded into MH4U's
0x0090ef74 (which takes one more argument than 0x00827d54) is what an in-game trace of an
MH4U Rathian at 0/2, 0/3 or 0/6 would settle (#55). [#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)
translates category 0 without its own 0x008412cc call: the module passes MH4U's own per-action
value to 0x0090ef74's stack argument and logs the open item. 0x00833b2c halves its argument and
MH4U's 0x00915d44 does not, so the module passes -5.0 halved.

### The 3U work block on MH4U's layout

The 3U module ([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)) and the family slices translate MH3U's handlers, and those handlers read their state from the block at `*(this+0x1a48)`; MH4U's handlers read the same roles from `*(this+0xe28)`. This is the field map the port's C is written against: the fields category 0 touches first, then those the ground (category 3) and flight (category 7) handlers read, and the object fields outside the block. The other categories extend it per slice; [what is not mapped](#what-is-not-mapped) says where it stops.

**How an offset was established.** Three sources, named per row:

- **A handler pair.** `monster_actions.py pairs` gives **57 pairs** from the 174 action ids both dispatchers handle (MH3U 0x00687d30, 191 ids on 66 handlers; MH4U 0x006e9cac, 342 ids on 97 handlers). The two handlers' loads, stores and calls were read in program order and the sequences aligned: for a shared action the two call the same engine functions in the same order, so a field on one side sits at the point its counterpart sits on the other. The number is how many of the 57 pairs read or wrote the field at that offset; a role that one pair alone reports is marked *(1)*.
- **A twin caller.** The engine functions in [The 73 with an MH4U counterpart](#the-73-with-an-mh4u-counterpart) were read the same way. Where a function reads field X at the point its MH4U counterpart reads Y, X and Y have the same role; where the pair is "same body" the reading is as strong as a handler pair's.
- **A field translation.** Where a structure keeps its layout (a point's x, y, z; a pair of rates), one confirmed component carries the others, as [the GU port's tables](../mods/rathian_actions/README.md#427-32-one-handler-three-states) do for MHXX.

A field only one source reports is **unverified** until a slice reads it; the rows say which. The 57 pairs by category: 7: 24, 3: 11, 13: 8, 1: 5, 2: 3, 9: 3, 8: 1, 0: 1, 11: 1. They cover 81 of the 94 category-7 ids and 28 of the 29 category-3 ids. Fifty-seven of the 66 3U handlers meet exactly one MH4U handler this way. Three serve ids MH4U splits across handlers (0x00858b6c for 0/3, 3/10 and 13/7; 0x00694180 for the 7/2 family; 0x006971c0 for the 7/35 family), so `pairs` leaves them out; six meet none (0x00699ad4 for 0/0, 0x0082d1cc for 0/2, 0x0082ef88 for category 10, 0x0083cc24 for 4/0, and the wrappers 0x00687e88 and 0x006956e8), mostly because MH4U's case is inline.

#### The block pointer, the action pair and the handler's state

| MH3U | MH4U | role | how |
|---|---|---|---|
| `*(this+0x1a48)` | `*(this+0xe28)` | the enemy's work block | both dispatchers load it this way (0x00687d30 holds 0x1a48 in a literal and does `ldr r1,[r1,r0]`; 0x006e9cac does `ldr r1,[r0,#0xe28]`), and every handler pair that reads the block at all loads it the same way in its first instructions |
| work+0xdf | work+0x1ca | current category | both dispatchers read it and switch on ≤ 0xe; 4 twin callers read it where MH4U reads +0x1ca |
| work+0xe0 | work+0x1cb | current index | the category-0 functions 0x0069166c / 0x006dc400 switch on it (≤ 7), read side by side |
| work+0xe3 | work+0x1cf | "a pending action is waiting" | 0x0082a06c / 0x0094ef64, the request-next-action helper (same steps) |
| work+0xe4 | work+0x1d0 | pending category | the same helper |
| work+0xe5 | work+0x1d1 | pending index | the same helper |
| work+0xee | work+0x1d8 | "the action was set immediately" | the same helper |
| work+0xef | work+0x1d9 | the set-immediately mode byte | the same helper |
| work+0xe1 | work+0x7993 | the tail flag: the next move | 2 pairs (8/0 and 9/0) |
| work+0x5 | work+0x144 | the handler's state byte | read or written in 49 of the 57 pairs; every category-0 case block (0x006916b4 vs 0x006dc4c4, 0x00691710 vs 0x006dc520, …) |
| work+0x6 | work+0x145 | its sub-state | 16 pairs |
| work+0x7 | work+0x146 | a third sub-state (category 3) | 1 pair |
| work+0xdc | work+0x1c8 | the monster's mode byte | 0/3's two handlers (0x00858b6c / 0x0094dc84, whose bodies `fnmap` pairs at 0.81) and the mode setters 0x0082fe88 / 0x009167b4 (same body) both compare it and store the new mode there |
| work+0xf2 | work+0x1dc | "the action was set" flag | the 0/2 base-handler pair (0x0082d1cc / 0x00911b48) and the 0/6 pair |
| work+0x381 | work+0x34c | the "other state" byte | the 0/2 base-handler pair, read side by side: 3U compares it to 1 where 0x00911b48 reads +0x34c |
| work+0x941 | work+0x51c | the monster's state, 2 or 3 | the 0/2 base-handler pair, read side by side: 3U tests it inline, MH4U calls 0x0092e960, which tests +0x51c (the wrapper pair 0x00844100 / 0x0092e960) |
| work+0x942 | work+0x51e | the byte after it | 1 twin (0x008345f8 / 0x0091b7b0); its role is unverified |
| work+0x8c | work+0x1b4 | the action-active flag word, bit 0x40 | the 0/2 base-handler pair, read side by side (3U does `tst r1,#0x40` on it, MH4U on +0x1b4) |
| work+0x3 | work+0x1c0 | the enemy-data key: MH4U's id byte | 3 pairs; the twins 0x0083db3c / 0x00923f90 and 0x00852324 / 0x0093d870 read it in r1 of the data lookup |
| work+0xa | work+0x797e | the second key byte of the same lookup | the same twins, in r2 (MH4U addresses it as `0x797e + work`) |
| work+0xdb | work+0x14c | a selector byte for a per-monster rate lookup | 3 pairs (3/6, 7/0, 7/13), but the two helpers it feeds (0x0064325c and 0x006c2854) are not each other's counterpart |

#### The base handlers category 0 falls back to

| 3U action | MH3U handler | MH4U counterpart | what the pair fixes |
|---|---|---|---|
| 0/2 | 0x0082d1cc | 0x00911b48, `uEnemy`'s base action update (vtable slot 89) | work+0x941/+0x51c, +0x8c/+0x1b4, +0xdf/+0x1ca, +0x381/+0x34c and +0xf2/+0x1dc; both call the mode setter (0x0082fe88 / 0x009167b4) with 0 and the action setter (0x00827d54 / 0x0090ef74) with r3 = 2 |
| 0/3 | 0x00858b6c | 0x0094dc84, MH4U's idle | work+0x3/+0x1c0 and +0xa/+0x797e (the data lookup), +0xdc/+0x1c8, the rate pair +0x90/+0x1b8, position y +0x3c/+0x19c and +0xf2/+0x1dc |
| 0/6 | 0x0082b7dc | 0x00955970 | work+0xdf/+0x1ca and +0xf2/+0x1dc; both set mode 3 and call the action setter with r3 = 2 |

The first two counterparts are not `pairs` output: 0x00911b48 was found by reading the two side by side (same steps, same calls in the same order) and 0x0094dc84 by `fnmap`'s body match at 0.81 for the 0/3 handlers; 0x00955970 is 0/6's action pair. All three 3U handlers are the same code as their counterpart step for step; 0x0082d1cc is
the one [decision 0002](../docs/decisions.md#0002-monsters-are-ported-onto-mh4us-engine)'s
amendment covers as base-class code the port still reimplements.

#### Ground: the fields category 3's handlers read

The 11 pairs cover 3/0, 3/1, 3/2, 3/4, 3/5, 3/6, 3/7, 3/8, 3/11, 3/12 and 3/27, and through them
their shared handlers reach 3/9, 3/13, 3/14, 3/16–3/25 and 3/29. The state and block-pointer
rows above apply to every one of them.

| MH3U | MH4U | role | how |
|---|---|---|---|
| work+0x38 / +0x3c / +0x40 | work+0x198 / +0x19c / +0x1a0 | position x, y, z (floats) | the twins 0x0082b268 / 0x00955440 and 0x0082cee4 / 0x00912288 (both add a speed vector to it), 5 readings each; x and z also in 0x0084704c / 0x00938748 |
| work+0x84 | work+0x1ac | heading (float) | 2 pairs; 13 twin readings (0x008357b0 / 0x0091db4c and others) |
| work+0x80 | work+0x1a8 | the turn slot before the heading | 3 twins; the 3U turn wrappers are handed its address and do not read it, while 0x0091b430's turn reads +4 of the address (the heading), so the slot's role is read side by side |
| work+0x260 / +0x264 / +0x268 | work+0x160 / +0x164 / +0x168 | the aim point A (x, y, z) | 11 pairs on A.z and 4 on A.y; the twins 0x0082fc8c / 0x00916228, 0x0082b268 / 0x00955440 (advance position by A) and 0x0084704c / 0x00938748 |
| work+0x270 / +0x274 / +0x278 | work+0x170 / +0x174 / +0x178 | the aim vector B (x, y, z) | 6 pairs on B.z; the twins 0x00834098 / 0x00916594 (advances A by B times the frame delta) and 0x0084704c / 0x00938748 |
| work+0x288 / +0x28c / +0x290 | work+0x218 / +0x21c / +0x220 | the target point (x, y, z) | the twin 0x00847134 / 0x00938834 (the distance and angle to it), the 8/0 pair's aim call, and the layout |
| work+0x68 | work+0x180 | the speed, accumulated from the frame delta | 5 pairs; the twins 0x00833b2c / 0x00915d44 and 0x00833d88 / 0x00916108 (`speed += rate × this+0x14`) |
| work+0xd9 | work+0x1c7 | "the speed was set this frame" | the same two twins |
| work+0x28 / +0x2c | work+0x1d4 | the frame timer and the value it was saved from | 2 and 6 pairs; MH4U counts it down with the helper 0x00b0704c (8/0) |
| work+0x30 | — | the pointer to the frame delta the timer adds | unmapped: MH4U's helper takes the delta in s0 |
| work+0x120 | work+0x624 | the vertical limit position y is clamped to | 1 pair; the wrappers 0x00839514 / 0x0091b430 both tail into a function that reads it (0x00839540 / 0x00922b34) |
| work+0x3d0 | work+0x394 | a 0–1 rate advanced by the frame delta | 1 pair; the twins 0x00836c04 / 0x00918e48 (same body) and 0x0084e74c / 0x00935fb8 |
| work+0x7c9 | work+0x3c4 | the "flying" byte 0x008310f0 sets | 3/8's handler pair (0x0082b37c / 0x006d7378): both set it at the same two state entries, MH4U's handler inline; #220's port writes the field |
| this+0x14 | this+0x14 | the frame delta (seconds) | 12 twins: every advance and every rate above multiplies by it |
| this+0x278 | this+0x290 | a speed (float) | 3 pairs, and the twin 0x0083c6e0 / 0x00922250 |
| this+0x284 | this+0x29c | a second speed | the twin 0x0083c6e0 / 0x00922250 (the same body reads both speeds) |
| this+0x27c | this+0x294 | | 1 pair |

#### The category 3, part 2 units (#220)

#220 translates sixteen of her ground ids on five handler units, reusing cat0.c's base
handlers: 3/6, 3/13 and 3/16 fall into 0/3's `0x00858b6c` (the blocked height branch aside),
and 3/27's last state into 0/2's `0x0082d1cc`.

| 3U ids | Handler | Arguments | What the handler does |
|---|---|---|---|
| 3/6, 3/13, 3/16 | `0x0068e448` | r1, r2 = (0, 0), (1, 0), (0, 1) | state 0: the data float, the fall, motion `0x1a` at 6.0, aim point A cleared; state 1: the value curve at the speed into aim A y, the position advance (the source's 0.5, which `0x00955440` lacks), the flag counts two and clears the aim, then 0x84d7e4's turn; the height test takes 3U's blocked `0x0064325c` for r1 = 0 and target z + 1300 for r1 = 1, then 0/3's base handler |
| 3/7, 3/17, 3/18, 3/19, 3/24, 3/28 | `0x0068e5e8` | r1 = 0 to 5 | state 0: the data float, the fall, motion `0x1a` at 6.0; state 1: the turn at 3U's 0x200 (halved for `0x0091db4c`, which has no 0.5), then r1 2 to 5 ask the next action 3/0x14, 3/0x15, 3/0x19 and 3/0x1d; r1 0 and 1 fall into 0/3's base handler |
| 3/12, 3/20, 3/21, 3/25, 3/29 | `0x0068e6e4` | r1 = 0 to 4 | state 0: the data float, the fall, motion `0x3d` at 6.0; state 1: the 70.0 distance test, aim A z 5.0 and aim B z 3.0, then the turn with aim A z clamped at 90.0; on the flag r1 1 to 4 ask 3/0x16, 3/0x17, 3/0x1a and 3/0x1e, and r1 0 starts 3/11 (`0x0084dc84`, `0x00935a90`) and writes the set byte |
| 3/27 | `0x0068e8c8` | — | state 0: the data float, the fall, motion `0x1a` at 6.0, then `0x8509a0`; state 1: `0x850a50`, the data float, `0x83369c`'s height test, mode 3 and motion `0x1d`; state 2: the flag, mode 0, and the record's kind picks motion `0xcf` (MH4U `0x0207`) for 0x3e/0x3f/1 or `0xe1` (MH4U `0x0219`) for 2/0x40/0x41, then the shell `0x844a38` and `0x83d18c`; state 3: the flag, then 0/2's base handler |
| 3/8 | `0x0082b37c` (base class) | — | five states: the data float and motion `0x2d`; the flag, motion `0x3d` and the rate at target z + 500.0; the two-joint turn at 0x100 (halved to `0x0092fc84`'s 0x80), the 30.0 distance test, aim A z 5.0 and aim B z 3.0, the turn point at -300.0, then motion `0x3e`; the joint turn at 0x80 (halved to `0x0092dccc`'s 0x40), motion `0x2d`, aim A y -10.0 and aim B z -3.2; the 30.0 test and aim B z -6.8, then mode 3 and motion `0x1d` or the blocked `0x00839598` and 0/3's base handler; state 5: mode 3 and 0/3's base handler |

The two calls #55 still blocks are named and logged once per action:

- **`0x0064325c`** (3/6, 3/13 and 3/16's r1 = 0 branch, i.e. 3/6 and 3/16) maps work+0xdb through
  a table and returns a per-monster height from the monster's data block; no MH4U function with
  those steps was found. The port leaves the call out and takes its result as 0.0, so the
  target is the vertical limit + 2000.0 (the branch the source takes for a value below the
  limit) until #55 settles it. 3/13 takes the other branch (target z + 1300.0) and never calls
  it. The selector's field, work+0xdb, does map to MH4U's work+0x14c.
- **`0x00839598`** (3/8's fourth state) returns the signed byte at 3U work+0xef; it is one of
  #55's 28 with no MH4U counterpart, and work+0xef has no mapped offset. The port takes the
  source's nonzero path and ends the action in 0/3's base handler, so the move cannot stall.

Three argument translations the engine calls need: `0x83d884`'s two rates 0x100 and
`0x8357b0`'s 0x200 and `0x8438e8`'s 0x80 are halved (3U's `0x8392d8` halves its rate,
MH4U's `0x0091aaf0` does not), and `0x82b268`'s s0 = 1.0 becomes 0.5 (`0x00955440` has no
0.5 factor). `0x8310f0` sets 3U's work+0x7c9 and has no function in MH4U: the port writes
work+0x3c4, the offset MH4U's own 3/8 handler stores it at inline. The 3/6/3/13/3/16 value
curve is MH4U's own 3/6 curve `0x00fd18a0`, whose keys were compared key by key with 3U's
`0x00c4eca8` and are equal, so MH4U's evaluator `0x00922250` reads the converted curve and no
3U data is carried.

#### Flight: the fields category 7's handlers read

The 24 pairs cover 7/0, 7/1, 7/4–7/9, 7/12, 7/16–7/25, 7/31, 7/33, 7/34, 7/36, 7/38–7/45,
7/58, 7/61, 7/66–7/71, 7/74–7/80, 7/84, 7/86–7/87, 7/90–7/91, 7/94–7/95 and 7/77, and through
their shared handlers more of the 94. The flight handlers use the state, block-pointer,
position, heading, point and speed rows above; what they add:

| MH3U | MH4U | role | how |
|---|---|---|---|
| work+0x68 | work+0x180 | the speed accumulator | 5 pairs |
| work+0x28 / +0x2c | work+0x1d4 | the frame timer | 2 / 6 pairs; 7/1 counts it down before the flight blend |
| work+0x2b6 | work+0x278 or +0x27c | the part byte the hit check takes | 3 pairs each way: 3U passes one byte to 0x0084512c, MH4U passes two (+0x278, +0x27c) to 0x0092b2b0, so which one replies to it is not settled |
| work+0x80 / +0x84 | work+0x1a8 / +0x1ac | the turn slot and the heading | 1 and 2 pairs |
| work+0x2b4 | — | read 10 times by the category, no pair | unverified |
| work+0x260 / +0x264 / +0x268 | work+0x160 / +0x164 / +0x168 | the aim point A | 11 pairs on A.z; 8 twin readings |
| work+0x270 / +0x278 | work+0x170 / +0x178 | the aim vector B | 6 pairs on B.z |
| work+0x288 / +0x28c / +0x290 | work+0x218 / +0x21c / +0x220 | the target point | 1 twin and the 8/0 pair |
| work+0x88 | work+0x1b0 | a u32 read as a size or radius | twin only (5 readings); the role is unverified |
| work+0x2a8 | work+0x238 | the float 7/16 clamps at 1000.0 | MH4U's own 7/6 handler (0x006e01e0) clamps `+0x238` at 1000.0 where the source's 7/16 clamps `+0x2a8` at 1000.0: the same clamp at the same point, read by this slice |
| work+0xb81 | work+0xca5 | the second gate byte 0x006944b8 reads beside work+0x6 | MH4U's own 7/4 handler (0x006dfd54) reads `+0xca5` where the source reads `+0xb81`, both before the same conditional `0x0093310c` step, read by this slice |
| this+0x1e70 | `*(this+0x8d88)` | the target-line struct's first float | 2 pairs (13/2 and 7/31). The layouts differ: 3U embeds the struct at this+0x1e70, MH4U reaches it through the pointer at this+0x8d88 |
| this+0x1ed0 | `*(this+0x8d88)+0x60` | a float inside that struct, advanced by the frame delta | unverified: 3U reads it as this+0x1e70+0x60 (9 readings in 7/68), MH4U's struct is not read there by a pair |
| this+0x27c | this+0x294 | | 1 pair |

#### What is not mapped

- **work+0x2b4** (10 readings, category 7): no pair reads a role at one MH4U offset, and no twin. (`work+0xb81` was on this list; category 7's first slice found it at MH4U's `+0xca5`, above.)
- **work+0x2b6**: the pairs divide between MH4U's +0x278 and +0x27c; the two MH4U bytes are the hit check's part pair, so a slice has to say which one the port passes where.
- **work+0x11c** (category 3, "the fall or hold step is enabled"): MH4U's counterpart function tests two flags instead (+0x620 and +0x628); which of them replies to +0x11c is unsettled.
- **work+0xf4** and **work+0x944** (a byte and a halfword, category 3), **work+0x1c, +0xda, +0xaea** (category 13) and **work+0x1** (one pair, category 11, proposes +0x1c8): no confirmed MH4U offset. (`work+0x2a8` was on this list; category 7's first slice found it at MH4U's `+0x238`, above.) +0xda indexes a `uCharacter` table through 0x00a347bc, which has no MH4U counterpart (see [The 28 with no MH4U counterpart](#the-28-with-no-mh4u-counterpart)).
- **this+0x1a64** (a float the category-11 handler reads, 0x1c bytes past the block pointer), and **this+0x1ed0** as a field of its own rather than the target-line struct's +0x60: unverified.
- **The categories without pairs:** category 4 (1 id) and category 10 (8 ids). Category 0 (1 of 5 ids), 11 (2 of 5), 1 (11 of 12), 2 (10 of 11) and 13 (8 of 10) are partly covered.
- **A handler with no pair** is not evidence of a difference: an inline MH4U case (0/0, 0/1, 0/3) or a different unit leaves nothing to align, and the field still has to be read in the slice.

The map extends per slice: a category's slice adds its rows here with the same three sources and its pair count.

### A 3U Rathian's moves

The 3U port keeps the source's own animations and runs her own handler for every action id,
shared with MH4U or not ([decision 0002](../docs/decisions.md#0002-monsters-are-ported-onto-mh4us-engine)'s
2026-11-26 amendment). MH3U's dispatcher reaches 191 action ids on 66 handler units; 174 of
those ids also exist in MH4U's `uEm001`, which has 342 ids on 97 handlers. R1
([checks.md](../docs/checks.md#monster-actions)) compares the animation each action's handler
starts: 117 of the 174 start a constant animation in both games, and 115 of those start a
different index.

| The 117 compared ids | ids |
|---|---|
| the same index in both games | 2 (1/11 and 1/12) |
| the same animation at another index | 93 (86 identical, 2 with the skeleton's extra MH4U track, 5 whose target slot is empty in MH4U's own lists but whose animation is found at another index there) |
| a different animation | 3 (13/5, 13/6 and 13/8) |
| not resolved | 19 (all category 7, whose shared code can start more than one motion, so the first constant is not enough) |

The other 57 ids are not compared: one handler or both starts no constant animation (it
computes the index, starts none, or does its work inline).

**The 17 ids MH4U has no action for** are 0/4, 4, 7/64, 7/87, 7/93, 10/0 to 10/6, 11/5,
11/15, 11/26, 11/28 and 13/9, on 8 of the 66 handlers. 16 of them reach a handler unit a
shared MH4U action also reaches, so that shared action's MH4U handler is the counterpart to
read for their engine calls; action 4 reaches shared engine code no MH4U action covers, so
its calls are matched from the code alone. Each id's shared MH4U action with the same handler,
and each call's MH4U counterpart or #55 blocker, are in [The 17 ids MH4U has no action
for](#the-17-ids-mh4u-has-no-action-for) below. `monster_actions.py pairs` finds 63 body
pairs between the two classes; 58 of the 66 3U handlers have one, 8 have none.

#### Category 7, part 1 (#221): the seven units and what is blocked

Category 7's first slice reimplements seven handler units on 21 ids. The class (`uEm002`)
shares them with Rathalos and the colour variants (MH3U ids 1, 2 and 62 to 65), and branch on
the work block's +3 (MH4U's +0x1c0) for the variants' attacks. The ported monster is em001
(id 1), so the port carries the id-1 path and not the ids 62-65 branches; the action variant
the case block passes (0, 1, 2 …) is kept and selects a motion, speed, timer or tail in five
of the units. Each unit was read against MH4U's own handler for the same action (the "MH4U
action with the same handler" column is the pair read by hand), and its engine calls are the
MH4U counterpart at the same point.

| 3U ids | MH3U unit | MH4U's own handler | what the port runs |
|---|---|---|---|
| 7/0, 7/77 | 0x00693468 | 0x006df128 | mode 0, motion 0x2f at 4.0 and the tail steps 0,1 and 1,9; the flag then 0/2's base. The ids 0x3e/0x3f branches (extra timers and 0x00842a7c) are not carried |
| 7/1, 7/20, 7/42 | 0x00693be8 | 0x006df510 | mode 3, the order step -14, motion 0xd1 at 6.0; the -6.6666665 vertical step, the -200.0 speed floor, the 0x100 turn and the 50.0 check; state 2's -200.0, aim advance, 110.0 clamp and landing step, then motion 0xd2 (variant 0), mode 0 + motion 0xdd + speed 0 (1) or motion 0x35 at 10.0 (2); state 3's 20.0 drive into 0/6, or motion 0xda and 30.0 into 0/2, or the 10.0/5.0 drive and motion 0x3c into 0/2 |
| 7/2, 7/10, 7/11, 7/15 | 0x00694180 | 0x006dfb30 | mode 0, motion 0x33 at 6.0; the 2.0, 12.0, 36.0 and 78.0 checks, the first three spawning effects 3, 1 and 1; 7/15 adds the source curve's rate step |
| 7/4, 7/12 | 0x006944b8 | 0x006dfd54 | mode 0, motion 0x32/0x31 at 4.0 and three tail steps; the ±0x8000 turn over 0..120; the work+0x6/work+0xb81 gate; the flag into 0/2 |
| 7/5, 7/61 | 0x00694694 | 0x006dffb0 | mode 3, motion 0xce at 10.0 and the 0,0x1b tail; the 200.0 check and the (A-200)/(B-200)·-150 speed; motion 0xcf then 0/2, or 0/6 |
| 7/6, 7/7, 7/16, 7/19, 7/32, 7/85 | 0x00694840 | 0x006e01e0 | mode 0, motion 0x8 at 4.0 and the 0,5,3 tail; the variant's blend and timer (work+0x2a8's 1000.0 clamp for 7/16); the landing step with 0x80/0x40; motion 0x9/0x40/0x30, or 7/32's 4/7; the 36.0/120.0 check and the 0,0xd tail into 0/2 |
| 7/8, 7/34 | 0x00694bf4 | 0x006e0794 | mode 0, motion 0xd0 at 4.0; the 2.0, 12.0 and 36.0 effects; the 78.0, 120.0 and 164.0 structure builds; 7/34 adds the source curve's rate step |

**The calls still blocked or not carried.** They are named in the module's log and recorded
in its README's category-7 section:

- **0x0084161c (#55)**, 7/2's and 7/8's effect target check: named and skipped, and the effect
  structure behind it with it.
- **0x00688a20 and 0x00829950**, the attack-structure builder and its spawn: the structure
  is the source's data and the spawn calls 0x0063cabc and 0x008890f0, which have no MH4U
  counterpart read here, so neither is carried.
- **0x00842a7c (#55)** is only the colour variants' branch of 0x00693468, which the ported id
  (1) never takes; so are that branch's 0x0063e4ac shell spawns and the source's +0xdb
  selector.
- **0x0083c6cc (#55)** is not called by this slice's units; it is other category-7 ids'
  helper.
- **The source's value curves 0x00b0b1c0 and 0x00b0b1e8** (7/15, 7/34) are the source's
  data, which the port does not carry, so the timing value they supply is skipped.

The two field-map rows this slice adds (work+0xb81 → work+0xca5 and work+0x2a8 → work+0x238)
are in [Flight](#flight-the-fields-category-7s-handlers-read). The ledger
([#214](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/214)) marks the 21 ids
translated; their per-move rows are in [checks.md](../docs/checks.md#the-ported-moves-check-r2p).

#### Category 13, part 1 (#227): the five units and what is blocked

Category 13's first slice reimplements five units on five ids. The category entry
`0x00699b78` switches on the index and tail-calls each unit; the units ignore the case
block's registers. The port reads MH4U's own handler for the same action for the field
offsets and the call sites; under decision 0002's amendment it still runs the source's
handler.

| 3U ids | MH3U unit | MH4U's own handler | What the port runs |
|---|---|---|---|
| 13/0 | `0x0068eabc` | `0x006db3dc` | the data float and the fall, motion 0x1a at 10.0, the 300.0 timer, then the 3500/2000 height branches and the 0x180 turn into 13/1 |
| 13/1 | `0x0068eca4` | `0x006db540` | four states: motion 0x3d at 6.0; the aim step, the heading and pitch turns, motion 0x3e at 6.0 and the -2500.0 blend; the landing step and motion 0x2d at 6.0 or the 130.0 aim clamp; the 30.0 query and the flag into 0/3's base handler or 13/2 |
| 13/2 | `0x0068f0fc` | `0x006db948` | mode 3, motion 0xc8 at 20.0, the (0, 0xb) tail, the distance/450 target-line factor and `0x00948548`; the two value curves, the halved vertical step and the -50.0 speed floor, motion 0xdc; the target loop into 13/3 or 1/3 |
| 13/3 | `0x0068f424` | `0x006dbbe4` | mode 0 and the 300.0/38.0 aim into `0x00948674`; the 12.0/50.0 query, the 38 - (speed - 12) aim range and the 0.5 position advance, motion 0xca at 4.0; the target loop into 13/4 or 2/6 |
| 13/4 | `0x0068f66c` | `0x006dbd8c` | mode 0, motion 0xcb at 4.0, the 4.0 timer, then the timer crossing test and the 1000/200 order step into 13/2 |

**The calls still blocked or not carried.** They are named in the module's log and recorded
in its README's category-13 section:

- **`0x00a347bc` and `0x00843c20` (#55)** are 13/0's, 13/1's and 13/2's entry gate: the
  uCharacter table lookup of 3U work+0xda, which has no MH4U offset, and the scale/one-shot
  pair behind its 0xc result. The port takes the source's non-0xc path; 13/0's second lookup
  and its `+0xaea` selector go with it.
- **`0x00839598` and `0x00835f10` (#55)** are 13/2's and 13/3's state-2 target loop: the
  signed work+0xef byte and the uEm066 position helper. The port takes the byte's nonzero
  path and the helper's result as 0, so the source's failure request runs.
- **`0x0085162c` and `0x00829620` (#55)** are 13/4's entry and per-frame helper; both are
  skipped.
- **13/3's action-start record `0x00b0b0e8`** is the source's data, not carried, so its
  setup `0x0082d278` and leaf `0x0082d430` are not called.
- **`0x0084512c`** is not reached by these five units (it is 8/0's `0x006870f4`); the issue's
  list groups it with 13/1, whose source does not call it.

The two field-map rows the units read are earlier slices': `+0xdb` -> `+0x14c` and `+0x7c9`
-> `+0x3c4`. 3U's `+0x1c`, `+0xda` and `+0xaea` stay unmapped ([What is not mapped](#what-is-not-mapped)).
13/2's two value curves 0x00c4edb8 and 0x00c4ee00 were compared key by key with MH4U's own
0x00fd19b0 and 0x00fd19f8 and are equal, so MH4U's evaluator reads MH4U's tables. The
ledger ([#214](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/214)) marks the
five ids translated; their per-move rows are in
[checks.md](../docs/checks.md#the-ported-moves-check-r2p).

### The 17 ids MH4U has no action for

16 of the 17 reach the same handler function as a shared MH4U action, so that shared action's
MH4U handler is the counterpart to read for their engine calls; action 4 has no MH4U action
with the same handler. Every one of the 17 is reimplemented from MH3U's handler like the rest
(0002's 2026-11-26 amendment), in the 3U module
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)), family by family,
and the ledger ([#214](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/214)) marks
each translated. 0/4 is done: it shares 0/0's handler, translated with category 0 in #216 along
with the three base-class handlers 0/2, 0/3 and 0/6 reach. The other 16 are still owed.

The page records, per id, the shared MH4U action with the same handler and every other one
with the same source handler. Where the source's case block picks a variant, the evidence
names it; what a move plays is her own handler, and R2p's in-game check settles how it looks.

| 3U id | MH4U action with the same handler | other MH4U actions with the same body | evidence |
|---|---|---|---|
| 0/4 | 0/0 | — | body match: 0/0 and 0/4 are the same handler; R1 cannot compare (neither starts a constant motion); 0/0's case block is inline. Translated with category 0 in [#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216) |
| 7/64 | 7/35 | 7/46, 7/47, 7/48, 7/62, 7/63, 7/65 | body match: 7/35 to 7/65 are one handler; R1 starts the same constant motion on all seven |
| 7/87 | 7/92 | 7/96, 7/37, 7/84, 7/86 | body match: same handler through 0x00686bcc; R1 records no constant motion to compare; 7/37, 7/84 and 7/86 are inline in MH4U |
| 7/93 | 7/92 | 7/96, 7/37, 7/84, 7/86 | as 7/87: 7/93 reaches 0x00686bcc through the same code |
| 10/0 | 10/7 | — | body match: 10/7 runs the same handler; R1 cannot compare; 10/7's case block is inline |
| 10/1 | 10/7 | — | as 10/0 |
| 10/2 | 10/7 | — | as 10/0 |
| 10/3 | 10/7 | — | as 10/0 |
| 10/4 | 10/7 | — | as 10/0 |
| 10/5 | 10/7 | — | as 10/0 |
| 10/6 | 10/7 | — | as 10/0 |
| 11/5 | 11/0 | — | body match; its case block passes r2 = 1, which is MH4U 11/1's mode, and 11/0 is the shared action with the same handler |
| 11/15 | 11/0 | — | tail match: the wrapper calls 11/0's handler 0x0084d864; its r3 is the action index |
| 11/26 | 11/0 | — | as 11/15: the same wrapper, r3 = 0x1a |
| 11/28 | 11/0 | — | as 11/15: the same wrapper, r3 = 0x1c |
| 13/9 | 0/3 | 3/10, 13/7 | body match; 13/9's case block calls 0x0083cbf4 like 0/3's |

"Body match" is the source game reaching the same handler function for the missing id and the
shared one; "tail match" is a short wrapper ending on the shared handler. R1 confirms the
animation only where the handler starts a constant motion; the 10, 11 and 13 families start
theirs inside an engine helper, so their counterpart rests on the body match alone.

**Action 4 has no MH4U action with the same handler.** Its handler 0x0083cc24 is shared engine
code (0x3cc bytes) that dispatches on the order state. It makes 25 calls with an MH4U
counterpart and calls 7 of the class's own sub-handlers (0x00691930, 0x00691b38, 0x00691c74,
0x00691de0, 0x00691fac, 0x006921b4, 0x00692290), which have to be translated with it. What it
still needs:

- **#55:** 0x00161798 and 0x0016052c, both reached through 0x00691fac. These are two of the
  19 calls whose MH4U counterpart is unknown, so action 4 waits on #55.
- **The plugin API's arguments:** ABI 3's `call` sets r0-r2 only. r3 can be set before the call
  with `set_reg`, but the guest's VFP registers cannot, so a call that passes a float in s0 or
  s1 (0x00833b2c, 0x008437f4 and 0x00839514 here) cannot be made as MH3U makes it. ABI 4's
  `call2` adds r3 and the floats s0/s1 ([#134](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/134), check P4); the s2/s3 arguments are still not carried.
- **MH3U's data:** 0x0084704c and 0x00847134 take 0x00b0b194, a 44-byte action-start record
  in MH3U's image ([specs/actiondata.md](../specs/actiondata.md)). Its MH4U counterpart is
  built from the dumps by `reference/monster_attack_records.py`, checked against the shared
  3/5 record both games have (checks N1 and N2). Action 4's sub-handlers also pass three value
  curves (0x00c4ed68, 0x00c4eef0 and 0x00c4ef28); MH4U's evaluator has the same body, so the
  port carries them (N4). So the data half of this blocker is done; what remains for action 4
  is the C and the calls above.
- **One shared branch:** the handler falls back to 0x00858b6c, the shared 0/3 handler, which
  the 3U module translates for 0/3 in
  [#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216).

The arguments are answered: ABI 4's `call2` sets r0-r3 and s0/s1 and returns s0, so the calls
that pass those floats can be made as MH3U makes them ([#134](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/134),
check P4). A call that needs s2 is not covered yet: the sub-handler at 0x00692078 calls
0x0083336c with s2 = 80, which
[#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136) records.

`reference/monster_handlers.py` builds both results from the two inventories and the motion
list. `targets` prints the per-id candidates; `worklist`
prints each missing id's handler, its calls in order with the constants left in r0-r3 and the
floats in s0-s3, and each call's MH4U counterpart (#55, a body match, or unmapped). Both
per-call TSVs hold addresses and constants only but are derived from game code, so they stay
outside the repository:

```bash
python3 reference/monster_handlers.py targets --game mh3u --exheader <MH3U exheader> \
    --code <MH3U code.bin> --range 0x686000 0x69b000 --dispatcher 0x00687d30 \
    --functions reference/games/mh3u/functions.tsv \
    --actions 0/4,4,7/64,7/87,7/93,10/0,10/1,10/2,10/3,10/4,10/5,10/6,11/5,11/15,11/26,11/28,13/9 \
    --target build/mh4u-actions.tsv --motions build/mh3u-motions.tsv -o build/3u-targets.tsv
python3 reference/monster_handlers.py worklist --game mh3u --exheader <MH3U exheader> \
    --code <MH3U code.bin> --range 0x686000 0x69b000 --dispatcher 0x00687d30 \
    --functions reference/games/mh3u/functions.tsv \
    --actions 0/4,4,7/64,7/87,7/93,10/0,10/1,10/2,10/3,10/4,10/5,10/6,11/5,11/15,11/26,11/28,13/9 \
    -o build/3u-worklist.tsv
```

The inventories and the motion list come from `monster_actions.py list` and
`monster_motions.py list` (their commands are above and in R1).

### The tables the missing ids pass

Each source id's handler passes in-image tables to the engine; for each call, either
MH4U's own data serves it or an MH4U counterpart is built. The three tables' formats are in
[specs/actiondata.md](../specs/actiondata.md).

| Ids | MH3U's call and table | MH4U's counterpart |
|---|---|---|
| 4 | 0x0084704c and 0x00847134 take 0x00b0b194, the second of the two 44-byte action-start records at 0x00b0b168 | built from MH3U's by `reference/monster_attack_records.py`; the shared 3/5 pair rebuilds on all 12 fields (N1/N2) |
| 4's sub-handlers | 0x00691cd8, 0x00691e68, 0x00691e80, 0x00692318 and 0x00692330 pass the value curves 0x00c4ed68, 0x00c4eef0 and 0x00c4ef28 to 0x0083c6e0 | carried, not converted: MH3U's evaluator 0x0058493c and MH4U's 0x00aac8dc are a map pair ("same body"), so MH4U reads the same keys (N4) |
| 10/0 to 10/6 | each case block passes a command list to the shared handler 0x008326e0: 0x00c4d520 (10/0), 0x00c4d5a0 (10/1, 10/2), 0x00c4d550 (10/3), 0x00c4d578 (10/4), 0x00c4d530 (10/5), 0x00c4d540 (10/6) | MH4U's 10/7 runs the same handler's MH4U counterpart 0x00919788 with MH4U's own lists at 0x00fd1db8, 0x00fd1dc8, 0x00fd1dd8, 0x00fd1e10, 0x00fd1e38, 0x00fd1f38, 0x00fd1f48, 0x00fd1f70 and 0x00fd1f80, chosen by 0x009385e8's result |
| 11/5 | its case block passes 0x00c4d818 to 0x008326dc, the shared handler's other entry | MH4U's 11/0 runs 0x00919788 with MH4U's own list 0x00fd2360 |
| 11/15, 11/26, 11/28 | their case blocks pass 0x00c4d850, 0x00c4d868 and 0x00c4d880 through the wrapper 0x00687e88, ending on 0x0084d864 | as 11/5: MH4U's 11/0 and its own list 0x00fd2360 |

The 3/5 record the check compares is not one of the missing ids: both games have 3/5, so its
record is what proves the conversion before it is used for action 4's.

**Where the port's animations go.** The converted animation files keep the source game's
grouping. Her own handler runs for every action id (0002's 2026-11-26 amendment), so the
handler the port reimplements passes MH4U's motion-start wrapper (0x0094e318) the MH4U form
of the animation it starts — MH3U's `file * 100 + slot` written as MH4U's `file << 8 | slot`
for her converted motion lists — where MH3U's handler passes the source form, converted when
the handler is written. Nothing translates a motion number at run time, so each action gets
its own animation and no placement conflict exists: 13/5 and 13/6 keep the animations their
own handlers start, and 13/8 keeps its own. The 19 category-7 ids whose computed index R1
cannot resolve are read from their handlers' code
([#217](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/217) to
[#229](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/229)).

### Lessons from MHGU Definitive Edition's ports

- **Keep the source's bone ids and remap table.** Then the monster data needs no bone remap, except where a bone is missing from the target skeleton.
- **A handler that never ends its action freezes the AI.** Translate the source handlers literally, timers and all.
- **Ids only ever grow.** Never move an installed monster's ids: saves and quests keep them.
- **Add, never replace.** No shipped file should be a copy of a game file another mod might also ship; patch the loaded resource instead.
- **Check a converted file by rebuilding the target game's own file** for a monster both games have, then count equal bytes. MHGU-DE reaches 95 to 99.7 % on the volume tables this way; the remainder points at real format differences.

## MH4U monster tables

Monster ids run 0 to 123. Id N's files are `emNNN`. Every table below has to grow when ids do.

| Table | Address | Shape | Reader |
|---|---|---|---|
| `createEnemy` (factory) | 0x006901f4 | `cmp id, #0x7c`, then a 124-word jump table at 0x00690278 | the factory itself, id in r1 |
| `enemyDataPathIndex` | 0x00efc268 | 124 pointers by id into `enemyDataPaths` (0x00efbef8, 110 rows) | `loadEnemyData` 0x00689490, id in r1 |
| `enemyDataById` | 0x00f3a024 | 124 pointers by id to records from 0x00f39c90 | 0x0068882c, id in r1; written by `loadEnemyData`, cleared by `releaseEnemyData` (0x0068df70) |
| `crownSizeTable` | 0x00f32008 | 124 rows of 4 floats | `getCrown` 0x0068877c, id in r0 |
| `monsterListOrder` | 0x00df35b0 | 124 rows of 8 bytes, by list position | 0x0061dc58, id in r0 (a monster's position); the notes list walks all 124 rows at 0x0061df4c |
| `monsterIconIndex` | 0x00e06698 | 124 bytes, 0x7f = no icon | 0x00c0e800, id in r1; 0x00c0e164, id in r2 |
| `enemyResourceIndex` | 0x00efbd08 | 124 pointers to 0x2c-byte path records | 0x0068d8c8, id in r1; 0x00682ca0, id in r2; 0x00c0b830, the spawned monster's own id |
| effect-list counts | 0x00fb7a70 | 124 rows of two u16: the number of path slots 0x00c0b830 reads from the record's +0x24, then +0x28 | 0x00c0b830, the spawned monster's own id |
| `dropRecordIndex`, `dropBaseA`, `dropBaseB` | 0x01003bec, 0x01003ddc, 0x01003ed4 | 124 entries each, into `itemListTable` (0x01002a5c) | `dropRecordIndex`: 0x00684b40, id in r1, and 0x0092600c, the monster's own id; `dropBaseA`: 0x00911f20; `dropBaseB`: 0x009357b4, both the monster's own id |
| names and notes text | `emName`, `emExp` in `core_common.arc` | message N names id N; 123 messages | the message layer: the 71-file list at 0x00f006c4 holds `emName` at 6 and `emExp` at 7, loaded into 0x0109a080; the per-id getters are `0x00cdfb30` (the 16-byte format entry), `0x00cdfa18` (the string record from a format entry) and `0x00cdfa30` (the record by id) |

- The current monster's id is the byte at +0x1c0 of the block that `this+0xe28` points to.
- A resource record's eleven pointers are, at +0x00 the model, +0x04 six motion lists, +0x08 the camera, +0x0c a second motion list (it ends at its first empty slot, up to six), +0x10 two tail-model paths, +0x14 two motion-effect paths, +0x18 unused (null in all 123 records), +0x1c the sound, +0x20 four extra paths (the fourth is the command/EMC), +0x24 the effect lists and +0x28 a second effect list. `enemyResource::get` returns +0x14; `enemyResource::load` loads the paths of +0x00 to +0x28, skipping a null field; 0x00c0b830 reads +0x24 and +0x28. The 124 records run 0xefa7b4..0xefbd08, so the table itself begins where they end.
- The effect-list fields are not null-terminated. 0x00c0b830 reads exactly the two u16 at 0x00fb7a70 + id*4 (the count for +0x24, then +0x28) from each field's slot array, so a record that gives either field fewer slots makes the reader walk past the array: in a plugin-built record the words after it are the record's own path strings, and their first bytes are passed as path pointers.
- Ids map to class `uEmN`, or to a sibling's class for variants and subspecies.
- Several tables hold 123 entries, not 124: reading them for id 123 reads the next table.
- 54 functions compare a register with 0x7c. Only some are monster code.
- Save-side limits: a guild quest stores monster ids in one byte, and the character save's monster log has 82 fixed entries.

The readers are what `mods/uc_runtime` hooks for a ported id
([its README](../mods/uc_runtime/README.md#what-it-hooks)): each takes the id either in a
register or from the monster's data block, so the plugin rewrites that one value and calls the
game's function, which leaves MH4U's 0 to 123 untouched. The resource record is the exception:
a port ships only some of its path kinds and motion slots, so the plugin builds the id a
record of its own with its own paths for the kinds and motion slots its registry `files`
lists and the stand-in's for the rest, and answers the three table readers with it. The name
and notes text is answered through the three message getters, and the notes list's page init
(0x006191f8), page builder (0x0061df4c) and detail (0x006234b4) are hooked so a ported id gets
a page of its own after MH4U's own pages; the walk still reads all 124 order rows, so the
runtime adds its ids' pages rather than a row. [The plugin's check](../docs/checks.md#uc-runtime)
is the headless one.

The game's heap allocator, which plugins use, is named in the fork's `config/symbols.txt`, section "Heap".

### Ids and classes

**Id to class.** The rule is id N → `uEmN`. These ids reuse another monster's class (variants, subspecies and ids with no files):

| Class | Extra ids | Class | Extra ids |
|---|---|---|---|
| uEm001 | 2-6 | uEm048 | 49, 114 |
| uEm007 | 8 | uEm052 | 53, 54, 55 |
| uEm009 | 10 | uEm058 | 59, 60 |
| uEm011 | 12, 80, 121 | uEm065 | 66 |
| uEm016 | 13, 14 | uEm068 | 69-71 |
| uEm017 | 18 | uEm073 | 74-76 |
| uEm019 | 45, 112 | uEm077 | 78, 79, 117 |
| uEm020 | 90 | uEm081 | 84-87, 104, 123 |
| uEm022 | 21, 91, 92 | uEm083 | 111 |
| uEm023 | 93, 120 | uEm088 | 122 |
| uEm024 | 110 | uEm099 | 100, 119 |
| uEm025-027 | 94-96 | uEm101 | 102 |
| uEm028 | 29, 97 | uEm105 | 106 |
| uEm031 | 82 | uEm107 | 108, 109 |
| uEm034 | 35 | uEm038 | 39-41, 115 |
| uEm036 | 37 | uEm042 | 43, 113 |
| uEm044 | 98 | | |

Id 0 creates `uEmXXX` (size `0x8d88`). Every other class is `0x8d90` bytes, so one slot size fits all monsters, as `mt_classes.tsv` suggested.

### Item drops

Reward items are lists in `.data`, reached through one master pointer array and three id-indexed index tables. The rank offset comes from `0x006bc528`, which returns 0..3 from the current quest. Each index table gives a base index into the master array, and the code adds `4 × slot + rank` to it.

| What | Address | Shape | Bound | Status |
|---|---|---|---|---|
| `itemListTable` | `0x01002a5c` .. `0x01003bec` | 1124 pointers (281 groups of 4, one per rank), 853 non-null, each to an item list: 4-byte entries (u8, u8, u16 item id) ended by `0xffff` | none in code; set by the largest index the tables below produce (`0x460 + 3`) | address and bound verified; the entry fields are unverified (the u16 ranges over item ids, below `itemName`'s 1937) |
| `dropRecordIndex` | `0x01003bec` | 124 pointers by id (114 non-null) to records at `0x01003fcc`.. of 16-byte entries; an entry's u16 at `+0` is a base index into `itemListTable` and its byte at `+0xb` another index (`0xff` none) | 124 | verified for the shape and the indexing; what the entries describe (the floats suggest parts or drop points) is unverified |
| `dropBaseA` | `0x01003ddc` | 124 u16 by id, `0xffff` = none (81 used) | 124 | verified |
| `dropBaseB` | `0x01003ed4` | 124 u16 by id, `0xffff` = none (12 used) | 124, followed by the records at `0x01003fcc` | verified |

Readers: `0x00684b40` `(_, id)` and `0x0092600c` use `dropRecordIndex`; `0x00911f20` uses `dropBaseA` (after a percentage roll and a per-monster counter at data-block offset `0x7a64`, so probably shiny drops: unverified); `0x009357b4` uses `dropBaseB`. All four create an item-pop object through the manager at `*0x00fb8a1c` (`0x005b90d4`) and store the item list in it at `+0x28`. **Which of these are carves, captures, breaks and shiny drops is unverified**; carving was not traced.

### Other tables indexed by id

Each is read with the monster id from the data block (`ldrb [x, #0x1c0]`) as its index. Bounds are the gap to the next referenced address and are verified; meanings are not.

| Address | Shape | Reader |
|---|---|---|
| `0x00deef04` | 124 bytes | `0x00b9b340` |
| `0x00e067f4` | 124 u16 | `0x00696878` |
| `0x00e070a4`, `0x00e07120` | 124 bytes each | `0x006b8290`, `0x006b40dc` |
| `0x00fc96dc` | 124 bytes | `0x006a69e4` |
| `0x00fcd71c` | 123 rows × 8 bytes (two floats) | `0x0030f4cc` (`cmp #0x7c`) |
| `0x00ffeaa4` | 124 pointers to small records at `0x00ffea88`.. | `0x0093f350` |
| `0x00ffecb8` .. `0x00fff55e` | **nine tables of 123 i16** (stride `0xf6`), one picked by quest type; the result goes to data-block offset `0x7af4` | `0x0094813c`, `0x0094829c`, `0x0094c840`, `0x0094c948` |
| `0x00f384d0` | 124 words, `-1` = none | `0x0068efc8` |

The 123-entry tables (the nine i16 tables, `0x00fcd71c`, `emName`, `emExp`) stop one short of id 123: reading them for id 123 reads the next table's first entry.

### Not monster tables

`0x00f029e4` (20-byte rows; byte 6 counts up) is the item table: it is indexed by item id, and its `cmp #0x7c`/`#0x7d` are item ids. The 124-entry tables at `0x01017980`..`0x0101b214` are read by `0x00c4c4fc` with an index from `this+0xfd` that isn't a monster id. `0x00ecf1d8` and its neighbours are gathering lists chosen by stage.

### How tables grow

Two ways, to choose per table:

- **Relocate:** a plugin allocates a larger table at boot, copies the original rows, appends the new ones, and patches the code's references (hook points on the readers, or tunables for the bounds). Works for tables in `.data`.
- **Overlay:** hooks on the table's readers return the new rows for new ids and fall through to the original for old ids. Less patching, more hooks.

Both need guest memory allocation from plugins: the plugin API's `alloc`/`free` (ABI 2) take it from the game's default heap (the fork's docs/PLUGINS.md).

**Allocating ids, an option:** MHGU Definitive Edition, which adds MH4U monsters to MHGU, keeps every game-wide id a ported monster takes in one file (`allocations.toml`: registry index, monster number, file ids, save slots), each from a pool whose bounds were checked in the game, checked by a script and read by both its C module and its converters. Its rule: ids only ever grow, and an installed monster's ids never move, because saves and quests keep them. The same constraints apply here: a hunter's save keeps per-monster records (mhff's "MH4U user1 Format" lists a monster log of 82 entries of 10 bytes, whose indexing by id is unverified), and quests name monsters by id.

## MH3U's ids to MH4U's

MH3U and MH4U number their monsters differently: MH3U's em006 is MH4U's em099, MH3U's em071 is MH4U's em043, and MH4U's em043 is a Deviljho where MH3U's em043 is a Lagombi. A conversion of a 3U monster needs the pair for every file, so all 85 MH3U ids (`/arc/enemy/emNNN.arc`) are recorded here: 32 have an MH4U monster, 44 are monsters MH4U does not have, and nine are props or placeholders.

**Where the names come from.** Both games carry their own id-indexed monster-name table. MH3U's is `GUI/font/Monster_eng`, a GMD in `/arc/ID/ID_gallery_eng.arc`, whose string N is the name of id N; MH3U's factory groups the same ids by class ([MH3U's factory](#mh3us-factory): 1, 2 and 62-65 on `uEm002`; 7 and 71 on `uEm007`; 25 and 85 on `uEm025`), which agrees with the name table's indexing. MH4U's is `eng/msg/emName_eng` in `/eng/data/core_common.arc`, an rLayoutMessage of 123 UTF-16 messages, whose message N is the name of id N. A shared name is the candidate and the data checks it: every pair below is compared on the 80-byte hitzone table, the base HP, MH3U's part HP and second-level HP against MH4U's part record ([specs/emstatus.md](../specs/emstatus.md), "Part record mapping"), and the attack-volume group count, which `mhuc monsterdata` prints as counts; for MH3U em012 against MH4U em015 (Great Jaggi) it gives `hitzone table: 6 of 8 rows equal`, `part HP: 6 of 8 equal` and `attack volumes: 7 of 8 groups`. The data does not separate every pair: close relatives share most of their tables (MH3U's Rathalos agrees with MH4U's Rathian on 69 of 80 hitzone bytes and with em002 on 61) and small monsters repeat each other's, so the name tables order those; where MH4U gives several ids one name, the data says which is which (below).

In the table's Evidence column, hitzones are bytes of the 80-byte table, part HP and second-level HP are parts of the eight-part record, and the attack-volume groups are MH3U's own count against MH4U's. Each row's MH3U name is MH3U's table's name for that id, and its MH4U name is MH4U's.

| MH3U | Monster | MH4U | Evidence |
|---|---|---|---|
| em001 | Rathian | em001 | hitzones 78/80 bytes, part HP 5/8, second HP 7/8, base HP equal, attack-volume groups 18 against 22 |
| em002 | Rathalos | em002 | hitzones 61/80 bytes, part HP 4/8, second HP 7/8, base HP differs, attack-volume groups 18 against 22 |
| em006 | Diablos | em099 | hitzones 80/80 bytes, part HP 3/8, second HP 8/8, base HP differs, attack-volume groups 20 against 32 |
| em007 | Deviljho | em042 | hitzones 79/80 bytes, part HP 8/8, second HP 8/8, base HP equal, attack-volume groups 17 against 22 |
| em010 | Jaggi | em056 | hitzones 77/80 bytes, part HP 1/8, second HP 8/8, base HP equal, attack-volume groups 3 against 3 |
| em011 | Jaggia | em057 | hitzones 77/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 3 against 3 |
| em012 | Great Jaggi | em015 | hitzones 74/80 bytes, part HP 6/8, second HP 8/8, base HP differs, attack-volume groups 7 against 8 |
| em022 | Delex | em062 | hitzones 77/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 4 against 4 |
| em027 | Aptonoth | em052 | hitzones 74/80 bytes, part HP 1/8, second HP 8/8, base HP differs, attack-volume groups 4 against 5 |
| em028 | Popo | em053 | hitzones 74/80 bytes, part HP 1/8, second HP 8/8, base HP differs, attack-volume groups 4 against 5 |
| em029 | Rhenoplos | em051 | hitzones 76/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 3 against 3 |
| em030 | Felyne | em065 | hitzones 77/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 2 against 3 |
| em031 | Melynx | em066 | name only: MH4U's em066 has no `.etd`/`.emd` (its arc loads em065's command) |
| em033 | Altaroth | em067 | hitzones 76/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 1 against 1 |
| em034 | Kelbi | em064 | hitzones 77/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 2 against 1 |
| em036 | Bnahabra | em068 | hitzones 76/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 2 against 2; MH4U's four Bnahabra ids differ only in model and texture, and em068's is the only `.etd`/`.emd` |
| em037 | Bnahabra | em069 | MH4U's em069-em071 have no `.etd`/`.emd` either (they load em068's command); the four MH3U status files are identical, so em036's check covers them |
| em038 | Bnahabra | em070 | MH4U's em069-em071 have no `.etd`/`.emd` either (they load em068's command); the four MH3U status files are identical, so em036's check covers them |
| em039 | Bnahabra | em071 | MH4U's em069-em071 have no `.etd`/`.emd` either (they load em068's command); the four MH3U status files are identical, so em036's check covers them |
| em041 | Zinogre | em048 | hitzones 54/80 bytes, part HP 1/8, second HP 7/8, base HP differs, attack-volume groups 29 against 32 |
| em043 | Lagombi | em047 | hitzones 77/80 bytes, part HP 3/8, second HP 8/8, base HP differs, attack-volume groups 19 against 24 |
| em049 | Slagtoth | em054 | hitzones 74/80 bytes, part HP 1/8, second HP 8/8, base HP differs, attack-volume groups 4 against 5; model 1815 vertices and 4096 indices against em054's 1817 and 4106 (em078's are em055's exactly) |
| em050 | Gargwa | em050 | hitzones 74/80 bytes, part HP 8/8, second HP 8/8, base HP differs, attack-volume groups 2 against 2 |
| em058 | Black Diablos | em100 | hitzones 80/80 bytes, part HP 3/8, second HP 8/8, base HP differs, attack-volume groups 20 against 32 |
| em062 | Pink Rathian | em003 | hitzones 60/80 bytes, part HP 4/8, second HP 7/8, base HP differs, attack-volume groups 18 against 22 |
| em063 | Gold Rathian | em005 | hitzones 68/80 bytes, part HP 3/8, second HP 8/8, base HP differs, attack-volume groups 18 against 22 |
| em064 | Azure Rathalos | em004 | hitzones 60/80 bytes, part HP 1/8, second HP 8/8, base HP differs, attack-volume groups 18 against 22 |
| em065 | Silver Rathalos | em006 | hitzones 64/80 bytes, part HP 2/8, second HP 7/8, base HP differs, attack-volume groups 18 against 22 |
| em071 | Deviljho | em043 | hitzones 62/80 bytes, part HP 8/8, second HP 7/8, base HP equal, attack-volume groups 17 against 22 |
| em072 | Stygian Zinogre | em049 | hitzones 60/80 bytes, part HP 1/8, second HP 7/8, base HP differs, attack-volume groups 29 against 32 |
| em074 | Brachydios | em044 | hitzones 72/80 bytes, part HP 2/8, second HP 7/8, base HP differs, attack-volume groups 11 against 11 |
| em078 | Slagtoth | em055 | hitzones 74/80 bytes, part HP 1/8, second HP 8/8, base HP equal, attack-volume groups 4 against 5; model 1814 vertices and 4074 indices, em055's exactly |

**Repeated names.** MH4U's table gives one name to several ids, and the files say which is which:

- **Deviljho (em042, em043, em113).** em042 owns `uEm042`; em113 is a second id on the same class whose `.etd` differs from em042's in three words; MH3U's em007 agrees with both on 79 of 80 hitzone bytes and with em043 on 37. em043 is another data set: MH3U's em071 agrees with it on 62 of 80, and with em042 and em113 on 19. Both games have a Deviljho and a Savage Deviljho ([data/catalog/monsters.csv](../data/catalog/monsters.csv)), so em007→em042 is the Deviljho and em071→em043 the second one; em113 has no MH3U distinction.
- **Diablos (em099, em119) and Black Diablos (em100).** em099 owns `uEm099` and em100 and em119 reuse it. MH3U's em006 agrees with em099 and em119 on all 80 hitzone bytes; em119's base HP is the one MH3U's file has, em099's differs. MH3U's em058 agrees with em100 on all 80.
- **Zinogre (em048, em114) and Stygian Zinogre (em049).** em048 owns `uEm048`, em049 and em114 reuse it; em114's `.etd` differs from em048's in three words. MH3U's em041 agrees with both on 54 of 80 hitzone bytes, and em072 with em049 on 60.
- **Bnahabra (em068-em071).** The four MH4U ids differ in model and texture only; only em068 has an `.etd`/`.emd`, and em069-em071 load em068's command. MH3U's four `em_status` files (em036-em039) are byte-identical and match em068's data, so the ids pair in order and the data cannot tell the four variants apart.
- **Slagtoth (em054, em055).** MH3U's em049 and em078 have byte-identical `em_status` files, so the status data cannot tell them apart; the body model does. em078's vertex and index counts (1814 and 4074) are em055's exactly, while em049's (1815 and 4096) are closest to em054's (1817 and 4106). em055's base HP is MH3U's, em054's differs.
- **Melynx (em066).** MH4U has no `.etd`/`.emd` for it (its arc loads em065's command), so the pair rests on the name alone.

em113, em114 and em119 are second ids for the base monster; em043, em049 and em100 are the second monster of their family and reuse the base monster's class ([Ids and classes](#ids-and-classes)).


**MH3U monsters with no MH4U id.** These 44 ids have a name in MH3U's table that MH4U's 123-message table does not have, so MH4U has no monster of that name. The third column is the most any MH4U file's hitzone table agrees with the MH3U file: the nearest is a different monster in every row, and where it comes close it is a lookalike whose hitzones repeat (MH3U's Baggi and MH4U's Jaggi share 77 of 80 bytes).

| MH3U | Monster | Best MH4U hitzones |
|---|---|---|
| em003 | Qurupeco | 33/80 |
| em004 | Gigginox | 38/80 |
| em005 | Barioth | 37/80 |
| em008 | Barroth | 43/80 |
| em009 | Uragaan | 36/80 |
| em013 | Baggi | 77/80 |
| em014 | Great Baggi | 68/80 |
| em015 | Lagiacrus | 45/80 |
| em016 | Royal Ludroth | 35/80 |
| em017 | Ludroth | 67/80 |
| em018 | Gobul | 37/80 |
| em019 | Agnaktor | 36/80 |
| em020 | Ceadeus | 33/80 |
| em021 | Uroktor | 67/80 |
| em023 | Epioth | 72/80 |
| em024 | Alatreon | 46/80 |
| em025 | Jhen Mohran | 40/80 |
| em026 | Giggi | 74/80 |
| em042 | Arzuros | 46/80 |
| em044 | Volvidon | 38/80 |
| em045 | Great Wroggi | 66/80 |
| em046 | Duramboros | 30/80 |
| em047 | Nibelsnarf | 41/80 |
| em048 | Wroggi | 73/80 |
| em051 | Crimson Qurupeco | 36/80 |
| em052 | Baleful Gigginox | 33/80 |
| em053 | Sand Barioth | 41/80 |
| em054 | Jade Barroth | 40/80 |
| em055 | Steel Uragaan | 36/80 |
| em056 | Purple Ludroth | 40/80 |
| em057 | Glacial Agnaktor | 35/80 |
| em059 | Nargacuga | 34/80 |
| em060 | Green Nargacuga | 32/80 |
| em061 | Lucent Nargacuga | 40/80 |
| em066 | Plesioth | 35/80 |
| em067 | Green Plesioth | 35/80 |
| em068 | Ivory Lagiacrus | 38/80 |
| em069 | Abyssal Lagiacrus | 41/80 |
| em070 | Goldbeard Ceadeus | 32/80 |
| em073 | Rust Duramboros | 31/80 |
| em075 | Dire Miralis | 36/80 |
| em076 | Bullfango | 73/80 |
| em077 | Anteka | 74/80 |
| em085 | Hallowed Jhen Mohran | 34/80 |

- **The four files with the second-level HP block (0x6C)** are em025 Jhen Mohran, em046 Duramboros, em073 Rust Duramboros and em085 Hallowed Jhen Mohran. MH4U has none of them: its closest file to Jhen Mohran is Dah'ren Mohran (em046), a different monster that agrees on 40 of 80 hitzone bytes and has a different base HP, and the closest for the other three agree on at most 34. The block's place in MH4U's part record therefore has no MH4U file to check it ([specs/emstatus.md](../specs/emstatus.md), "Part record mapping").
- **Props and placeholders (nine ids):** em032 is named Fish, em035 Giggi Sac, and em040 and em079-em084 Rock. They hold data but are not monsters. The seven Rock ids' data matches MH4U's em081 `rock` on 79 of 80 hitzone bytes and the same base HP, so MH4U has the same prop; it has no Fish or Giggi Sac.

## MH3U's factory

0x005bbc5c: `cmp r1, #0x56`, then an 86-word jump table. Rathian (id 1) runs on `uEm002` with Rathalos and the colour variants (ids 2, 62 to 65). MH4U does the reverse, with ids 1 to 6 on `uEm001`.

**Id to class** follows MH4U's rule: id N runs `uEmN`, or another monster's class when there's no `uEmN`. The shared classes:

| Class | Ids | Class | Ids |
|---|---|---|---|
| uEm002 | 1, 2, 62-65 | uEm025 | 25, 85 |
| uEm003 | 3, 51 | uEm027 | 27, 28, 49, 78 |
| uEm004 | 4, 52 | uEm030 | 30, 31 |
| uEm005 | 5, 53 | uEnemy (the base class itself) | 32, 50 |
| uEm006 | 6, 58 | uEm034 | 34, 77 |
| uEm007 | 7, 71 | uEm036 | 36-39 |
| uEm008 | 8, 54 | uEm040 | 40, 79-84 |
| uEm009 | 9, 55 | uEm041 | 41, 72 |
| uEm010 | 10, 13 | uEm042 | 42-44 |
| uEm011 | 11, 48 | uEm046 | 46, 73 |
| uEm012 | 12, 14, 45 | uEm059 | 59-61 |
| uEm015 | 15, 68, 69 | uEm066 | 66, 67 |
| uEm017 | 16, 17, 21 | | |
| uEm019 | 19, 57 | | |
| uEm020 | 20, 70 | | |

The others (18, 22-24, 26, 29, 33, 35, 47, 56, 74-76) have a class of their own. **Rathian (id 1) runs on `uEm002`**, Rathalos's class, with ids 62-65 (the colour variants). `uEm002`'s vtable slot 14 (`0x006918a4`) names their files by id: 1 → em001, 2 → em002, 62-65 → em062-em065. MH4U does it the other way round: ids 1-6 all run `uEm001`.

## Procedures

Repeatable from the dump. Record results, never bytes.

### Finding the id table and the factory

1. Decompress `code.bin` (`tools/blz.py`) and lay out `.text`, `.rodata` and `.data` at the exheader's addresses.
2. In `.rodata`, find the `enemy\emNNN\data\emNNN` strings. In `.data`, find the run of pointers to them (stride 8: the path table), and the pointer array right after it whose entries point into that run (the index).
3. Find the code literal that points at index − 4, and therefore at entry 0: one function, `loadEnemyData`. Its `ldr rX, [base, id, lsl #2]` shows that the index is by id, 0-based, and its use of the `rEnemyData` DTI shows what it loads.
4. Count the `.text` literals equal to `0x8d90` (the `uEnemy` size from `config/mt_classes.tsv`). Apart from the 0x50-byte per-class DTI functions at `0x00d00df8`..., one large function (`0x1058` bytes) holds one: that's `createEnemy`. Its `cmp id, #0x7c; ldrlo pc, [pc, id, lsl #2]` gives the count and the jump table.
5. For each `uEm` class, read the vtable its DTI's create function stores. For each jump-table case, follow the init call to the vtable it stores, which gives the class. A case that only allocates and then branches into another case's tail takes that case's class (its `operator new` is that class's too).
6. Check that the two tables agree: for each id, the path the index gives and the class the factory makes should be the same `emNNN`, or the same neighbour for an id with no files of its own.

The procedure is enough to rewrite the scripts, which stay outside the repository because they read the dump.

### Finding the other per-monster tables

1. Lay out the code as for the id table. List the code's literals that point into `.rodata`/`.data`. For each, take the distance to the next referenced address; keep the ones that are 123, 124 or 125 times a small row size.
2. Find the functions that read the id (`ldrb [x, #0x1c0]` after `ldr [this, #0xe28]`) or compare a register with `#0x7c`. Keep the literal tables they index with that register; the shift or multiply gives the row size.
3. Names: find `msg\emName_jpn` in `.rodata`, the pointer list that holds it (`0x00f006c4`), and its loader (one function with a `cmp #0x47` loop storing `rLayoutMessage` pointers). The functions that read the stored pointer at `+0x18` are the getters. Count the messages from the `.lmd` file's header in `core_common.arc`.
4. Crowns: the function that indexes a 16-byte-row table by an id it compares with `#0x7c` and compares floats.
5. Drops: scan `.data` for runs of pointers whose targets are lists of 4-byte entries ending in `0xffff`. The long run is `itemListTable`; the functions that read it show the index tables and the `0x006bc528` rank offset.
6. For each table, check its count against the id tables (each id in range, the list order a permutation of 0..123).

### Finding the tables still unknown

1. **Start from a known monster.** Pick one MH4U monster whose files are known by name in the RomFS (its ARC folder, `em/emXXX/`-style). Its id is in the folder name. Search `.data` and `.rodata` for that id next to its path string: the record that holds the path is a row of the monster table; its neighbours are the other rows, and the table's start and end bound the count.
2. **From the class registry.** `config/mt_classes.tsv` gives each `uEm` class's DTI address. In Ghidra, the code that references many `uEm*` DTIs in one function is the factory: its switch or table maps ids to classes, and its bound is the monster count.
3. **From resource loaders.** For each resource class in the placeholders (specs/placeholders/), its loader's callers index by id: their array bounds and the constants compared against are the table sizes.
4. **From GMD tables.** The monster-name GMD's string count is an upper bound for monster ids that have names.
5. **Heaps.** The resource and unit managers are created early in start-up (MH4UltimateDC's docs/research/system-services.md covers the main systems); their sizes are constants passed to their constructors. Record which heap a monster's resources come from.
6. **Record each table** as: name, address (USA v1.3.0), row size, row count, what indexes it, the functions that read it. Addresses and sizes are fine to commit (LEGAL.md); contents are not.

### Finding the MH3U-to-MH4U id pairs

1. Read each game's own id-indexed monster-name table. MH3U's is `GUI/font/Monster_eng` in `/arc/ID/ID_gallery_eng.arc`: a GMD whose string N names id N (`mhuc gmd dump` reads an extracted `Monster_eng`). MH4U's is `eng/msg/emName_eng` in `/eng/data/core_common.arc`: an rLayoutMessage whose 123 messages are NUL-terminated UTF-16-LE strings in id order, the first being `No enemy`.
2. For every name both tables hold, the pair with that name is a candidate; a name MH4U's table lacks has no pair. Read the tables' names and counts, never their bytes.
3. Check each candidate with `mhuc monsterdata --mh4u data/em_data.arc --id <MH4U id> --mh3u arc/enemy/em<NNN>.arc`; its hitzone, part-table and attack-volume counts are the evidence in [MH3U's ids to MH4U's](#mh3us-ids-to-mh4us).
4. Where a name repeats, compare every id that holds it. The base HP, the hitzone table and, between byte-identical `em_status` files, the body model's vertex and index counts say which id is which.

### Extending the 3U field map

The field map ([The 3U work block on MH4U's layout](#the-3u-work-block-on-mh4us-layout)) starts
from category 0 and covers what the ground and flight slices read. A new slice extends it with
the same three sources, and `monster_fields.py` re-derives the rows so a hand edit cannot drift
from the code.

1. Build both inventories outside the repository: `python3 reference/monster_actions.py list
   --game mh3u --exheader <work>/exheader.bin --code <work>/code.bin --dispatcher 0x00687d30
   --range 0x686000 0x69b000 -o <work>/mh3u-actions.tsv`, and the same for MH4U's `uEm001`
   (dispatcher `0x006e9cac`, range `0x6d4f80 0x6ec8e0`). Keep the TSVs out of the repository.
2. `python3 reference/monster_fields.py map --a-inv <work>/mh3u-actions.tsv --b-inv
   <work>/mh4u-actions.tsv --a-exheader ... --a-code ... --a-range 0x686000 0x69b000
   --b-exheader ... --b-code ... --b-range 0x6d4f80 0x6ec8e0` prints every offset the 57
   handler pairs and the 73's engine twins put together, with the number of pairs behind each,
   and the offsets the handlers read that nothing pairs. A row with one pair and no twin is a
   candidate, not a fact: read the two handlers at that point before recording it.
3. For an offset the alignment cannot settle (the two handlers differ by a call, so their
   field sequences shift: the base handlers of category 0 are the case), read the two
   functions side by side and record the row with "read side by side" in its evidence.
   `check` skips those rows and the ones marked "unverified" or whose structure differs.
4. Add the row to the map with its role, its evidence kind and the pair count from step 2.
5. `python3 reference/monster_fields.py check --page reference/README.md` with the same game
   arguments re-derives every row and fails on a count that no longer matches; a row it cannot
   derive is reported as skipped, so nothing is silently dropped. CI has no dumps, so this is
   a local step, run before the slice's pull request.

The tool reads the page's "73 with an MH4U counterpart" table for the twin functions, so that
table is the only engine counterpart it trusts; a pair whose fields contradict the rest of the
map is reported as misaligned and left out of the counts.

### Recompiling and testing a reference game

The checks reported in [The reference games](#the-reference-games) are run like this. A recompiled function is not trusted: it runs against the original code in Unicorn from the same random states, and the two must agree on registers, flags, VFP state, writable memory and exit.

1. Extract the dump (`tools/extract_ncch.py`) and compare it with the game's `game.json` (`tools/verify_dump.py`); `recompile_game.py` and `recompile_module.py` also refuse code whose sha1 is not the one `game.json` names.
2. Static code: `python3 reference/recompile_game.py <game> --exheader <work>/exheader.bin --code <work>/code.bin -o <build>`. It prints the function count, the instructions analysed, the entry points found through data pointers, and any problems.
3. Library: from the fork's `tools/`, `python3 -m recomp.build <build> --harness --opt O0 -j 4 -o game.so`.
4. Test: `python3 -m recomp.gametest --lib <build>/game.so --exheader <work>/exheader.bin --code <work>/code.bin --cases 4 --shard <i>/4`, for i 0 to 3; the shards' verdicts add up. A verdict is a test limit when it is `inconclusive` (over the instruction budget), `protocol` (an inline descriptor, tested through its callers), or `native-nofunc` for an indirect call the random state aims outside the function table; every other verdict is a difference.
5. MHXX's modules: `python3 reference/recompile_module.py --game mhxx --exheader <work>/exheader.bin --code <work>/code.bin --crs <romfs>/modules_MasterRelease/static.crs -o <build> <romfs>/modules_MasterRelease/*.cro` recompiles them with the static code, then build the library as above and test it with `python3 reference/modtest.py --build <build> --exheader <work>/exheader.bin --code <work>/code.bin --crs <romfs>/modules_MasterRelease/static.crs <romfs>/modules_MasterRelease/*.cro --cases 4`.
6. MHXX's `reference/games/mhxx/extra_entries.txt` lists the 4,256 static functions the modules branch to; `recompile_module.py --static-entries <out>` regenerates it, and it must stay identical. The static recompile reads it.

MH3U gives 33,283 functions: 33,275 agree, 6 run over the budget and 2 read a descriptor, and none differs in state, memory or exit. MHXX gives 109 modules, 36,665 functions in 108 of them (`roPlayerQuest05` has none): 20,718 pass, 15,768 fault the same way in both, 178 run over the budget, one is the `native-nofunc` limit below, and none differs in state, memory or exit.

**The `roEm060` limit.** Its function at `0x024a0634` is an import stub: `ldr pc, [pc, #-4]` with the import's address word, `0x002e4409`, the Thumb pointer to the static function at `0x002e4408`. That function calls its second argument: `r6 = r1`, then `blx r6` once per count in `r3`, with `r0` stepping by `r2`. In one of the stub's four cases the random state draws `r1 = 0x028b1678`, inside `roEms027`'s text but not a function entry: it is 0x10 bytes into the body that follows the `push {r4, r5, r6, lr}` at `0x028b1668`, so no further Ghidra pass can add it to the table. The original run from the same state arrives at `0x028b1678` with the same general registers, flags and VFP state as the recompiled code at the call, then executes the middle of that body and faults at `0xb3`; the recompiled code agrees up to the call, and what runs at the target is not a function of the program, so the test cannot compare it. The target is the test's random data, a function pointer no game data gives, so the verdict is a test limit and not a difference.

**The `roEms027` entry the table misses.** `0x028b1668` is a function the module's table should have. It opens with `push {r4, r5, r6, lr}` and `vpush {d8}`, has its epilogue at `0x028b176c` (`pop {r4, r5, r6, pc}`), and begins right after its predecessor's literal pool (`0x028b1648` to `0x028b1664`). The only direct branch to it in any of the 109 modules is the tail call `b 0x028b1668` at `0x028b332c`, one arm of the dispatcher at `0x028b3294` (`f_028b3294`, another table entry): that function reads a state byte (`ldrb r1, [r1, r0]`) and its arms each `pop {r3, r4, r5, lr}` and tail-call a handler — `0x028b1044`, `0x028b138c`, `0x028b1668`, `0x028b1800`, `0x028b1a44`, `0x028b1cf4` and `0x028b1fcc`, with `0x028b28b8` from its jump-table arms. So the code at `0x028b3294` is a neighbour that calls into `0x028b1668`, not the same routine. Nothing else reaches it: no `.rodata`/`.data` word in the module equals it, no relocation names it, it is not an export (the module has no indexed exports and one named one at `0x028b52cc`), no module imports it, and the static executable imports only `0x028b0820` and `0x028b4cdc` from the module.

**Why the table misses it.** `module_entries` seeds the analysis with the module's `.rodata`/`.data` code pointers and its imports (180 seeds; analysis then discovers 89 call targets), and `Analyzer._classify` gives a `b` to an in-text address that is not already an entry the `goto` class, a local label. A `b` adds a new entry only when `Analyzer._link_return` can read the LR the caller set (`mov lr, pc`, `add lr, …`), so a tail call to a function no seed reaches is decoded into the caller's body. The branch itself says it is a tail call: the `pop {r3, r4, r5, lr}` immediately before it restores the caller's link register, so the branch cannot return into the caller. The rule to add upstream: a `b` after LR is loaded from the stack is a tail call, and its target, when it decodes, is a function entry. It is not one address: the dispatcher alone folds eight prologue-headed handlers (the seven arms and `0x028b28b8`), and `roEms027` folds five more in other functions (`0x028b255c`, `0x028b2624`, `0x028b27ac`, `0x028b349c` and `0x028b3dc0`), so its 269-function table is at least 13 short. The fix belongs in upstream's `tools/recomp/analysis.py`; the fork keeps that file unedited.

**What splitting it out changes.** `roEms027`'s table would have 270 functions instead of 269, the module test 36,666 instead of 36,665 (36,678 with all 13), each with four cases. The emitted code for the address does not change: the 95 instruction translations for the new function are identical to the block the current build already carries at `L_028b1668` inside `f_028b3294`. No existing verdict changes for the same entry states: in #87's run all four of `f_028b3294`'s cases fault at the `ldrb r1, [r1, r0]` (which reads `0x6bf1 + r0` for a random `r0`) before any arm, so no folded handler is executed and the verdict stays `agree-fault-only`. The test draws its random states in table order from one seed, so a rebuilt table reruns every later function from different states and its aggregate verdict counts are not directly comparable. A test of `roEms027` alone cannot judge the new entry: two of its four random cases reach the static function at `0x8b1700`, which only the full library resolves; in a full rebuild they are compared like any call.
