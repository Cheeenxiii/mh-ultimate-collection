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
| `trace_calls.py` | logs who calls chosen functions while the game runs in Azahar, through its GDB stub (standard library only; procedure in [docs/checks.md](../docs/checks.md#tracing-engine-calls-in-mhxx)) |

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
| 62 called imports with no MH4U counterpart (the "61" plus one with use `unknown`) | 2 (DE C pairs: a `uFestaChar` material-dirty flag, a `uEnemy` rank-table getter) | 28 | 32 |
| 33 call-site matches | confirmed 7 (5 by DE pairs, 2 by our MH4U↔GU map), 1 differs, 25 unchecked | | |

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
| 0x008a1ed8 | `uEmXXX` | calls a manager with no arguments; Rathian tests its result (at least 9) only in one state of hers | not found yet; never called while tracing a low-rank and a Hyper Rathian fight |
| 0x008a1934 | `sHitPush` | asks the hit-push manager about a player (GU's label: player absent) | 0x006832a0, called at the same place in Rathian's paired vtable slot (MHXX 0x0201ccd4, MH4U 0x006ebfd8) |
| 0x008a7844 | `uEnemyBase` | applies a model part group: sets each part's visibility bit in the monster's mask | 0x009428a8, the same bit updates; MH4U takes its one part list from the monster's data instead of a group argument |
| 0x008d8768 | `uEnemy` | saves or clears the monster's status flag sets, by mode | MH4U lacks it: the paired MH4U handler (0x006d5e98) has no call at that point |
| 0x008ddad8 | | selects an entry by index from a table of 36-byte entries in the monster's data (one of two tables, by the quest's state) and keeps its last field | 0x00947400, the same table at +0x74 of the same data block; MH4U copies the whole entry |
| 0x008f1c1c | | reacts to a hit from one shell type: by the shell's kind, one of three reactions with strength 200 | 0x0086ff20 does the reaction part, with the same three reactions (0x00923ba4, 0x00917b60, 0x0091dc8c) in the same order; in MH4U the shell code calls it, not the monster |
| 0x0089e698 | `uFestaEnemy` | vtable slot 76: builds a capability mask in a `uFestaEnemy` field from two of the monster's states | MH4U lacks it: the field belongs to the `uFestaEnemy` layer, and no MH4U function builds that mask |
| 0x0089eb70 | | a rate for a part condition, from two part entries or a default, all `uFestaEnemy` fields (+0xb730 to +0xb76c) | MH4U lacks it: those fields are the `uFestaEnemy` layer's, which MH4U doesn't have |
| 0x008bb4c0 | `uEnemy` | raises a request flag with an id in the work block | 0x00922104, the same two stores (0x00933fe4 clears them) |
| 0x008c86d4 | `uEnemy` | clears one flag when called with 0; at run time, called in fights from code under `uEnemy`'s vtable slot 9 | not found yet |
| 0x00adb338 | `uEnemy` | one of two entries of the monster's data table, chosen by the work block's state 0x67 | 0x0091dee8 (the monster's data entry), called at the same place in action 3/78's paired handler |
| 0x00adcd4c | `uEnemy` | a mask from the work block's state flags and kind | 0x00911cfc, the same masks |
| 0x00adcf38 | `uEnemy` | a second mask of the same kind | 0x0091df88, the same masks |
| 0x008eb1c0 | | updates one part's damage state (states 1 to 3) and raises flags in the work block | 0x0094e364, the same switch on the state byte with the same bits (1, 2, 8) in a 16-bit flag field and the same state bytes; the callee pair agrees (MHXX 0x8b7660 = MH4U 0x91dbd4). MH4U goes on to the hit's position and effect; MHXX tail-calls 0x8da948 |
| 0x00a56ee0 | `MtObject` | calls a virtual method with the 16-bit id at +0x24c; at run time, called every frame by the player's and its weapon's code (`uPlayerBase`, `uPlWeapon`) | MH4U lacks it: no function forwards a u16 field to a vtable slot, and `uPlayer`'s slot 45, which MHXX uses for this (0xa5d818, a packed-id converter), is empty (0x0) |
| 0x008ad638 | `uPlayerQuest` | a player's 16-bit field at +0x24c, at +4 of the block at +0x248 whose two floats at +0x40/+0x44 the speed setter 0x001e3950 recomputes; at run time, read in quests by Rathian's module and by `uEnemyActCustom` code | MH4U reads the same field inline at +0x244 (0x937d44, the twin of MHXX's caller 0x8cc708, does `ldrh r3,[r1,#4]` on `this+0x240`); it is also vtable slot 33, 0xb05154 (`uEnemy`) and 0xb08c0c (`uPlayer`, `uPlChar`, `uWeapon`) |
| 0x001e3950 | `uPlayerLobby` | sets a speed and recomputes two ratios from it; at run time, called in menus by `uPlayerPreview`, the hunter preview, so likely a model's motion-speed setter rather than player code | 0x00b065d4, the same float math on MH4U's layout (speed +0x29c, base +0x284, rates at +0x240+0x40/+0x44) |

Of the 62: 23 have an MH4U function, 37 are things MH4U lacks (26 of them the shell framework), 2 are not found yet: the manager getter 0x008a1ed8 and the work-block flag 0x008c86d4. Both go through MHXX managers or fields with no structural twin in MH4U; the offset translation, the caller pairing and the token similarity all reach no MH4U function for them. The joint sound 0x008ae1c8 was settled by tracing a Rathian fight in MH4U (the procedure in [docs/checks.md](../docs/checks.md#tracing-engine-calls-in-mhxx), the same tracer on MH4U's addresses).

Three ways found the matches. Translating field offsets: MHXX's work block at +0x10a8 is MH4U's at +0xe28; within it MHXX's +0x40 (position) and +0x54 (heading) are MH4U's +0x198 and +0x1ac, +0x1d0 (target points) is +0x218, +0x1a8 and +0x1ba are +0x1b4 and +0x1c8, and the +0x5900 area is about 0x2160 further on in MH4U. Aligning call sequences: the handlers of a shared action call the same engine functions in the same order, so an import sits where its MH4U counterpart, or nothing, does. The alignment also confirms two of the call-site matches above (0x008a200c with 0x002b9cb4, 0x008a2298 with 0x002bab8c). Comparing the functions' instruction tokens ([fnmap.py](fnmap.py)'s NGRAM index) over the whole code catches the pairs the map's seeds don't reach (0x001e3950 with 0x00b065d4 at 0.82 both ways, 0x008eb1c0 with 0x0094e364); confirming such a pair means reading it, or its twin caller: 0x937d44, MH4U's counterpart of MHXX's 0x008cc708, reads the same u16 inline that 0x008ad638 returns.

### Lessons from MHGU Definitive Edition's ports

- **Keep the source's bone ids and remap table.** Then the monster data needs no bone remap, except where a bone is missing from the target skeleton.
- **A handler that never ends its action freezes the AI.** Translate the source handlers literally, timers and all.
- **Ids only ever grow.** Never move an installed monster's ids: saves and quests keep them.
- **Add, never replace.** No shipped file should be a copy of a game file another mod might also ship; patch the loaded resource instead.
- **Check a converted file by rebuilding the target game's own file** for a monster both games have, then count equal bytes. MHGU-DE reaches 95 to 99.7 % on the volume tables this way; the remainder points at real format differences.

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
