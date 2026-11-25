# GU Rathian's MHXX-only actions

The plugin that runs the actions GU Rathian has and MH4U does not. MH4U's action dispatcher
(`uEnemy` vtable slot 44, USA v1.3.0 `0x006e9cac`) runs nothing for the 13 action ids MHXX's
Rathian has and MH4U's lacks ([#112](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/112)).
This plugin wraps the dispatcher and, for the ported monster, runs a translated handler for
the ids this slice carries; every other id, and every other monster, goes to the game's own
dispatcher unchanged.

The 13 ids split into four slices (the issues are in the same milestone):

| Slice | Ids | State |
|---|---|---|
| 3/98 and the 12/1-3 chain | 3/98, 12/1, 12/2, 12/3 | this plugin |
| 4/27 to 4/32 | six ids on one handler | pending |
| 8/0 | one handler, with its combo tail | pending |
| category 17 | a gate plus a base-class routine | pending |

12/0 needs no code. MH4U's category-12 case checks index 0 and runs its own handler
`0x006d524c`, the handler MH4U's shared 3/2, 3/83 etc. use and the role pair of MHXX's 12/0
(`0x0201177c`). R2's map misses it because the case is a `cmp`/`bne`, not a switch; the note
is in [checks.md](../../docs/checks.md#the-shared-action-map-r2).

## What it translates

| Action | MHXX | What the port runs |
|---|---|---|
| 3/98 | block `0x020089a8`, handler `0x020062d4`, 3 states, motions `0x101` and `0x104` | a C state machine in `src/rathian_actions.c`: data float, fall advance, motion, fall snap; then the rate, speed `2.0`, motion; then the finish flag and `0x0094dc84` (idle) |
| 12/1 | block `0x0201c1d0` | fixed target points, then the 3/98 handler |
| 12/2 | block `0x0201c228` | target points from the caller's `s0`-`s3`, then MH4U's shared 3/12 handler `0x006d791c` |
| 12/3 | block `0x0201c27c` | target points from the caller's `s0`-`s3`, then MH4U's shared 3/9 handler `0x006d5e98` (r1=1, r2=0) |

Each engine call maps to the MH4U function of the same steps, from the reference's call
mapping (the MHXX address in brackets): motion start `0x0094e318` [`0x008eb108`], data float
`0x0093d870` [`0x008d21ac`], fall advance `0x0092e99c` [`0x008b1698`], fall snap `0x0094a45c`
[`0x008e192c`], rate `0x0093ce60` [`0x008d1a0c`], speed `0x00941d84` [`0x008d73e8`], finish
flag `0x00b05da4` [`0x00aed11c`], idle `0x0094dc84` [`0x008eb050`]. The work block is
MH4U's `*(this+0xe28)`; MHXX's `+0x44` and `+0x1d0` are MH4U's `+0x19c` and `+0x218`.

**What it does not translate yet.** The 12/1 and 12/2 blocks end through MHXX's
request-next-action helper `0x008ebab0` (also 13/4's tail). MH4U has neither the helper's
work-block bytes nor its pending-action queue, so the chain stops after the move and returns
to idle instead of following on to 12/2 or 12/3. The plugin logs that once per action. 3/98's
second motion gets `s1 = 0.0`; the source leaves `s1` from the previous state, which is
`0.0` while the move is current. Both are recorded in the slice's issue and R2p.

## Floats: the guest stubs

The host's ABI 3 `call` runs a game function with `r0`-`r2` and returns its `r0`. MH4U's
engine functions take motion speeds and points in VFP registers (`s0`, `s1`), which `call`
does not set, and a source case block receives target points in `s0`-`s3`, which a hook
cannot read. So the plugin builds tiny ARM stubs in a 256-byte block from the game's own heap
(`alloc`, ABI 2):

- `vldr s0/s1` from a literal, then branch to the engine function;
- for a function that hands a float back, set `lr` to a continuation that moves `s0` to `r0`;
- `vmov r0, sN; bx lr` to read the caller's `s0`-`s3`.

The port runs code that is not recompiled in Azahar's interpreter (`port/src/arm_recomp.cpp`,
`Interpret`), which reads the bytes each time, so a block from `alloc` is executable and a
stub's literals can be rewritten per call. P3 proves the guest call; T0 in
[checks.md](../../docs/checks.md#floats-through-a-guest-stub-t0) proves the stub in a headless
run. If the engine ever refuses executable heap memory, the stubs are the one part to redo.
The fork's issue [#134](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/134) adds
float and `r3` arguments to the plugin ABI; when it lands, the stubs are replaced by the new
`call` and the handlers keep their code otherwise.

## Build

```bash
make        # rathian_actions.so next to mod.json
make test   # the translated actions' call sequences, with a fake host and no game
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. Licence: GPL-3.0-or-later, like the rest of the mod.

## Install

```bash
python3 <fork>/tools/mods.py add mods/rathian_actions
python3 <fork>/tools/mods.py enable "GU Rathian's MHXX-only actions"
python3 <fork>/tools/build_game.py --dump "MH4U v1.3.0 update.cia" --install <Azahar user directory>
```

A run logs the ready line, then `running the translated action 3/98` (or 12/1, 12/2, 12/3)
the first time one runs. The dispatcher must be a hook point, so the code library needs the
mod's hooks (the build above).

## Settings

`mod.json` holds the defaults; a `config.ini` in the installed mod's folder overrides them
(`key = value` lines).

| Key | Default | Means |
|---|---|---|
| `monster` | `124` | the id to translate the actions for (the registry's GU Rathian), `any` for every monster, or an MH4U id such as `1` for MH4U's own Rathian |
| `selftest` | `0` | `1`: on the first frame, log what this build translates, what is pending, and where the float stubs are; check T1 uses it |

## The checks

The static check (`tools/check_actions.py`) verifies the ledger in
[data/actions](../../data/actions/rathian-gu.csv) against MHXX's module; `make test` runs the
state machines with a fake host; T1 and T0 are in
[checks.md](../../docs/checks.md#the-translated-actions-check-t1). The per-move in-game check
is R2p and waits for [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48) and
[#105](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/105).
