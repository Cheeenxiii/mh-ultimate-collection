# UC runtime

The mod's one native plugin ([decision 0013](../../docs/decisions.md#0013-one-runtime-for-the-mods-native-code)).
It holds the id layer that gives a ported monster its own id, and one C module per ported
monster for its actions; GU Rathian's module was the first, and 3U Rathian's module its first
slice of her 191 ids. Its `mod.json` names one fixed hook
list, so a new monster rebuilds this library and redeploys the mod, while the game's code
library stays as it is.

The id layer: MH4U looks a monster up by id in tables that have 124 rows (0 to 123,
[reference/README.md](../../reference/README.md#mh4u-monster-tables)). A ported monster's id
starts at 124 and comes from the mod's registry, [data/ids/registry.csv](../../data/ids/README.md),
which `tools/check_ids.py` turns into `src/ids.h` (the id tables and file kinds) and
`src/modules.h` (the module table, one entry per registered id). Ids 124 to 223 are permanent;
a monster ported after that range is full takes a registry id from 256 up, and the runtime
lends it a free byte of 224 to 255 for each quest that names it (the [id pool](#the-id-pool)
below). The runtime wraps the readers of the id-indexed tables and answers a registered id with
the MH4U monster's rows the registry names as its stand-in, except its resource record, which it
builds for the ported id from the kinds of file the port ships; ids 0 to 123 go to the game's
function unchanged, so MH4U's own monsters are untouched. The readers, the resource-record
builder, the pool, the text tables and the self-test moved here unchanged from the plugin that
held them before.

## Layout

| Path | Holds |
|---|---|
| `src/runtime.c` | the plugin entry point and the one hook table: it registers the id layer's hooks and frame call, then the module side's |
| `src/runtime.h` | what the entry point and the parts share: the hook type, the id layer's calls, the registry-id lookup and the module side's calls |
| `src/ids.c` | the id layer: the readers, the resource-record builder, the id pool, the name and notes text and the self-test |
| `src/ids.h` | generated from `data/ids/registry.csv` by `tools/check_ids.py --write`; do not edit |
| `src/module.c` | the machinery every module shares: the factory association, the action dispatcher, the state slots, the guest call and the guest stubs |
| `src/module.h` | the module interface: `MhucModuleOps`, `MhucState`, the guest call, the accessors, the motion encoder and the log |
| `src/modules.h` | generated from the registry and the module files: one row per registered id, with the monster's `ops` or 0 for a data-only port; do not edit |
| `src/monsters/rathian-gu.c` | GU Rathian's module: her translated MHXX-only actions, the first real module |
| `src/monsters/rathian-3u.c` | 3U Rathian's module: category 0 (`0/0`, `0/1`, `0/2`, `0/3`, `0/4`, `0/6`) and the three base handlers they reach, the first slice of her 191 ids |
| `tests/fake_host.c`, `tests/fake_host.h` | the fake host every test runs on: guest memory, the heap, `call`/`call2` and the guest stubs, the hooks, the registers and the log |
| `tests/test_runtime.c` | the id layer on the fake host (`make test`) |
| `tests/test_module.c` | the module's routing and its translated actions' call sequences on the fake host (`make test`) |

## The module interface

A ported monster's action code is one C file, `src/monsters/<key>.c`, where `<key>` is its
registry key, compiled into the runtime. It exports one `const MhucModuleOps`
([src/module.h](src/module.h)):

```c
typedef struct MhucModuleOps {
    uint32_t id;                       /* the registry id the module answers */
    void (*start)(void);               /* once at init: log the module's ready line */
    void (*self_test)(MH4UCall *call); /* once, first frame, when `selftest = 1` */
    int (*dispatch)(MH4UCall *call, uint32_t enemy);  /* 1 when it ran a handler */
} MhucModuleOps;
```

The runtime does the rest once for every module:

- **the factory association.** `uEnemyFactory::create` receives the ported id in r1, and the id
  layer's reader rewrites that register to the stand-in before the game creates the monster.
  The runtime's factory hook is registered after the id layer's, and the host runs a later hook
  first, so it keeps the original id, calls the rest of the chain (the id layer answers the
  stand-in, the game creates the enemy), and records the returned enemy pointer against the
  module its registry id names. An id no module answers, and MH4U's own ids, are not recorded
  and fall through.
- **the dispatch.** `uEnemy::dispatchAction` (USA v1.3.0 `0x006e9cac`) runs the module recorded
  for the monster in r0; the module reads the action pair and returns 1 when it ran a handler,
  which makes the runtime skip the game's dispatcher, or 0 for a pair it leaves to the game. A
  monster with no module recorded goes to the game unchanged.
- **the state slots.** `mhuc_state(call, enemy, category, index, &changed)` returns the
  monster's slot, keyed by the enemy pointer; `state` and `data` are reset when the action pair
  changes, and `changed` says when that happened (the module logs the action then). The runtime
  keeps eight slots.
- **the guest call.** `mhuc_call2` is ABI 4's `call2` (r0-r3, the floats s0/s1, the s0 return);
  `mhuc_call` and `mhuc_call_f` spell the arguments out. Three calls ABI 4 cannot make run on
  guest stubs from the game's heap: `mhuc_call_s2` (a third float, s2), `mhuc_call5` (a fifth
  argument on the stack, which MH4U's action setter takes), and `mhuc_read_s` (the caller's
  s0-s3, which a hook cannot read). `mhuc_stubs` allocates that block, `mhuc_scratch` gives 16
  bytes of guest memory to an engine function that fills a point.
- **the accessors.** `mhuc_work` (the work block at `*(enemy + 0xe28)`), `mhuc_category` and
  `mhuc_index` (its `+0x1ca`/`+0x1cb`), `mhuc_object` (a pointer field of the monster, such as
  the target line at `+0x8d88`), the read/write and float helpers, and `MHUC_MOTION(file, slot)`
  for MH4U's motion number, `file << 8 | slot`.
- **the log and the settings.** `mhuc_log`/`mhuc_logf` write one line through the port, and
  `mhuc_config` reads the mod's settings (init only).

A module adds no hook of its own: the runtime's one dispatcher reaches it, and the id layer's
readers answer its id. That is what keeps the code library's hook list fixed.

## Adding a module

1. Register the monster's id in [data/ids/registry.csv](../../data/ids/README.md), if it isn't
   there yet; a row is what gives it an entry in `src/modules.h`. Run
   `python3 tools/check_ids.py --write`.
2. Write `src/monsters/<key>.c` and export `const struct MhucModuleOps mhuc_module_<key>`
   (hyphens become underscores). The Makefile compiles every `src/monsters/*.c`; run
   `python3 tools/check_ids.py --write` again so the generated table gives the row its `ops`.
   The checker refuses a module file with no registry row, and one that doesn't export its
   symbol, so the C build can't silently lose it.
3. `make`, then redeploy the mod. The runtime's `mod.json` and its hook list do not change, so
   the game's code library is not built again.

### A worked example: GU Rathian's module

`src/monsters/rathian-gu.c` is the first module and the template; `src/monsters/rathian-3u.c`
is the second, and the one whose handlers read the source's state byte. Its `dispatch` is the
shape every module uses:

```c
static int dispatch(MH4UCall *call, uint32_t enemy) {
    const uint32_t work = mhuc_work(call, enemy);
    if (!work) {
        return 0;
    }
    const int category = mhuc_category(call, work);
    const int index = mhuc_index(call, work);
    if (category == 17) {                      /* its own path: the gate plus the base update */
        if (index > 2) {
            mhuc_call(call, FN_BASE_UPDATE, enemy, 0, 0, 0);
        }
        return 1;
    }
    if (!(category == 3 && index == 98)) {     /* only the ids this module carries */
        return 0;
    }
    int changed;
    MhucState *state = mhuc_state(call, enemy, category, index, &changed);
    if (!state) {
        return 0;
    }
    if (changed) {
        mhuc_logf(MH4U_LOG_INFO, "running the translated action %d/%d", category, index);
    }
    /* one state per frame; an engine call is mhuc_call / mhuc_call_f, a motion number
     * MHUC_MOTION(file, slot) */
    return 1;
}

const struct MhucModuleOps mhuc_module_rathian_gu = {
    MHUC_MONSTER_ID_RATHIAN_GU, start, self_test, dispatch,
};
```

The module's `start` logs its ready line, its `self_test` logs what it carries and where the
guest stubs are, and the rest of the file is the translated handlers below. The runtime's
`tests/test_module.c` drives exactly this: the factory association, the routing (its id runs
the module, an MH4U id and a registered id without a module fall through) and every translated
handler's call sequence on the fake host.

### GU Rathian's translated actions

The fourteen ids split into four slices (the issues are in the same milestone):

| Slice | Ids | State |
|---|---|---|
| 3/98 and the 12/1-3 chain | 3/98, 12/1, 12/2, 12/3 | this module |
| 4/27 to 4/32 | six ids on one handler | this module |
| 8/0 | one handler, with its combo tail | this module |
| category 17 | a gate plus a base-class routine | this module |

12/0 needs no code. MH4U's category-12 case checks index 0 and runs its own handler
`0x006d524c`, the handler MH4U's shared 3/2, 3/83 etc. use and the role pair of MHXX's 12/0
(`0x0201177c`). Under decision 0002's 2026-11-26 amendment her own handler is still owed for
12/0 and the shared ids; this move only carries the twelve translated ones.

| Action | MHXX | What the port runs |
|---|---|---|
| 3/98 | block `0x020089a8`, handler `0x020062d4`, 3 states, motions `0x101` and `0x104` | a C state machine: data float, fall advance, motion, fall snap; then the rate, speed `2.0`, motion; then the finish flag and `0x0094dc84` (idle) |
| 12/1 | block `0x0201c1d0` | fixed target points, then the 3/98 handler |
| 12/2 | block `0x0201c228` | target points from the caller's `s0`-`s3`, then MH4U's shared 3/12 handler `0x006d791c` |
| 12/3 | block `0x0201c27c` | target points from the caller's `s0`-`s3`, then MH4U's shared 3/9 handler `0x006d5e98` (r1=1, r2=0) |
| 17 | case `0x020098b8` -> gate `0x008d5bd4`; 0-2 return, others the base update `0x008ae50c` (vtable slot `0x3d0`) | indexes 0-2 nothing; others MH4U's base action update `0x00911b48` (`uEnemy` vtable slot 89) |
| 4/27-32 | handler `0x0200e3b4`, blocks `0x02018af8`, `0x02018b1c`, `0x02018b40`, `0x02018b64`, `0x02018b88`, `0x02018bac`, r1/r2 2/0, 1/0, 2/1, 1/1, 2/0, 1/0 | one C state machine, three states: line setup and motion `0x418`/`0x417` at 6.0; a turn, a line point and a step, motion `0x90a`/`0x909` at 0.0; a turn at +-0x2000, then the finish flag and MH4U's base update `0x00911b48`, or motion `0x90b`/`0x90d` at 2.0 and the source's next-action request |
| 8/0 | block `0x020097a4`, handler `0x0201b460`, 3 states, motion `0x403` | a C state machine: copy the data entry and aim at the target at 300.0/38.0; the per-mode check at 12.0/50.0 and the position advance; the finish flag, motion `0x403` at 4.0 and the 180.0 timer; then the timer, the two hit checks at 300.0/0.0/150.0 and the request for `9/1`, or `2/6` when they fail or the timer is spent |

8/0 is the same action as MH4U's own 8/0: MH4U's category-8 case runs `0x006e9770`, which uses
the same frame values (300.0/38.0, 12.0/50.0, 180.0, 4.0, 300.0/0.0/150.0) and the same tail
(`9/1` or `2/6`). So its calls map onto MH4U functions at the same points, and its work offsets
are MH4U's: the state is kept by the module, the timer is work+0x1d4, the pending-action mode
work+0x1d9, the two hit-check bytes work+0x278/+0x27c and the velocity work+0x160. The entry
stores are MH4U's work+0x7738/+0x7739 cleared and work+0x7a3c set to 2, and the tail flag is
work+0x7993.

Each engine call maps to the MH4U function of the same steps, from the reference's call mapping
(the MHXX address in brackets): motion start `0x0094e318` [`0x008eb108`], data float
`0x0093d870` [`0x008d21ac`], fall advance `0x0092e99c` [`0x008b1698`], fall snap `0x0094a45c`
[`0x008e192c`], rate `0x0093ce60` [`0x008d1a0c`], speed `0x00941d84` [`0x008d73e8`], finish
flag `0x00b05da4` [`0x00aed11c`], idle `0x0094dc84` [`0x008eb050`]. The work block is MH4U's
`*(this+0xe28)`; MHXX's `+0x44` and `+0x1d0` are MH4U's `+0x19c` and `+0x218`.

#### Category 17: the gate and the base update

MH4U's dispatcher has no category 17: its category table compares the category byte with 14
and returns for anything above. MHXX's dispatcher case for 17 (`0x020098b8`) is a veneer to
`0x008d5bd4`, a gate shared by every monster: it reads the index byte (MHXX's `this+0x6bf1`,
the port's `work+0x1cb`), returns for indexes 0 to 2, and otherwise tail-calls `uEnemy`'s
vtable slot `0x3d0` (`0x008ae50c`). That slot is a base-class action update, and MH4U's
`uEnemy` vtable stops at slot 94, so the number does not exist there. MH4U's own `uEnemy`
slot 89 (`0x00911b48`) is the same routine on MH4U's layout, so the port calls it with the
monster in `r0` instead of reimplementing the steps.

`0x008ae50c` and `0x00911b48` do the same work at translated offsets:

| Step | MHXX `0x008ae50c` | MH4U `0x00911b48` |
|---|---|---|
| reset the action from the monster's data entry, mode 0 | `0x8b1700(this, 0)` | `0x9167b4(this, 0)` |
| is the monster in state 2 or 3 | `0xadd004`: `work+0x4dd` is 2 or 3 | `0x92e960`: `work+0x51c` is 2 or 3, and `work+0x7e80` bit 0x20 is clear |
| the action-active flag | `work+0x1a8` bit 0x40 | `work+0x1b4` bit 0x40 |
| the current category | `this+0x6bf0` | `work+0x1ca` |
| category 11 skips the update | `#0xb` | `#0xb` |
| the setter's extra argument | `0x8a1d88(this)`, a signed byte from a table | a signed byte at `*(0x00fb6b7c)+0x2f` |
| the action setter | `0x8ac5a0(this, 0, r2, 2, arg)` | `0x0090ef74(this, 0, r2, 2, arg)` |
| the other state | `work+0x2c0` is 1 | `work+0x34c` is 1 |
| the finish flag | `0x8bf728(this, 0)` sets `this+0x6b00` to 1 | stores 1 at `work+0x1dc` |

`r2` is 2 when the first two conditions hold, otherwise 1 when the other state is 1, otherwise
0. The index the gate tests is MH4U's `work+0x1cb`, the byte its dispatcher reads. The
category-17 path needs no float stubs; the setter's call is the same one `0x00911b48` makes
for MH4U's own actions, so MH4U's handler runs the ported action's data.

#### 4/27-32: one handler, three states

The 4/27-32 handler's calls, and the fields and the target-line struct they use:

| MHXX | MH4U | What |
|---|---|---|
| `0x0201262c` | `0x006e7be8` | the flight's setup, from the monster's height data |
| `0x008b1700` | `0x009167b4` | set the monster's mode |
| `0x008b2210` | `0x00917570` | turn by an angle step, s0/s1 the speed range |
| `0x008a7360` | `0x0091aae4` | the mode call's flag-clear wrapper (r3 = r2, r2 = 0) |
| `0x008c21f8` | `0x0092d09c` | build a target point from an index |
| `0x008b75d8` | `0x0091db4c` | turn toward a target point at a step in r3 |
| `0x020063fc` | `0x006e5608` | a point on the target line at a fraction |
| `0x0201277c` | `0x00aad55c` | rotate a direction by an angle |
| `0x008eb108` | `0x0094e318` | start a motion |
| `0x00aed11c` | `0x00b05da4` | the action's finish flag |
| vtable slot 244, `0x008ae50c` | `0x00911b48` | the finish flag's end-of-action, the same routine as category 17's base update (MH4U's vtable slot 89) |

The work-block fields, MHXX -> MH4U, each read from a paired function (the MHXX and MH4U
functions that step through the same fields): position x,y,z `+0x40/+0x44/+0x48` ->
`+0x198/+0x19c/+0x1a0`, position w `+0x4c` -> `+0x1a4`, heading `+0x54` -> `+0x1ac`, target
point x,z `+0x1d0/+0x1d8` -> `+0x218/+0x220`, heading saved `+0x200` -> `+0x248`. The speed
getter `0x008bb4e4` reads the float at `this+0x298`, which MH4U's same handler reads at
`this+0x290`; the turn step `this+0x1c` is MH4U's `this+0x14`. The target-line struct
`*(this+0xb770)` is MH4U's `*(this+0x8d88)` and keeps its layout: origin x,z at `+0x30`,
direction x,y,z,w at `+0x40` to `+0x4c`.

8/0's calls, each the MH4U function MH4U's own 8/0 handler calls at the same point: data
entry `0x009167b4` [`0x008b1700`], aim at a point `0x00948674` [`0x008df28c`], per-mode
speed/distance `0x0091aae4` [`0x008a7360`], position advance `0x00955440` [`0x008f1f30`],
countdown `0x00b0704c` [`0x008a78ec`'s worker; MHXX's worker multiplies the frame delta by
the call's `s0`, which is 1.0 here, and both clamp at 0], hit check `0x009122fc`
[`0x008ae8ec`], hit check with its mode in r3 `0x0092b2b0` [`0x008c024c`], request next
action `0x0094ef64` [`0x008ebab0`].

**What it does not translate yet.** The 12/1 and 12/2 blocks end through MHXX's
request-next-action helper `0x008ebab0`. Its MH4U counterpart is `0x0094ef64` — the same
steps: refuse category 0x0b, otherwise take the immediate path through the action setter
when work+0x1d9 is 1, else store the pending pair at work+0x1d0/+0x1d1 with the flag at
work+0x1cf. The 8/0 slice uses it, but the 12/1-3 slice still returns to idle instead of
following on to 12/2 or 12/3; wiring those two is a follow-up (the chain is visible in R2p).

8/0 has four gaps, recorded here and in the module's log:

- **The leaf `0x008c4184` is MH4U's `0x0092f6e8`.** Both take `(this, table)` with the mode
  in r2: 0x008c4184 clears r2 and falls into `0x008c418c`, which picks one of the table's
  entries by work+0x331, adds this+0x2a4 times the frame delta to the float at work+0x334,
  and sets flags at work+0x32e. MH4U's own handler calls it with `0x00e094d8` where MHXX
  uses `0x20220ac`. The MHXX table is the port's data and is not carried yet, so the
  handler does not call it; when it does, the table goes with it.
- **`0x008ae5e4` (MH4U `0x00911c0c`) takes its 4th and 5th arguments in r3 and on the
  stack**, which ABI 4 cannot set. It is the data setup for this action and waits on #134.
- **`0x008d0528` has no confirmed MH4U counterpart.** It reads this+0x6dd0, calls
  0x00add004 and then 0x008da42c or 0x008b58c0, and ends in 0x008d057c(this, 0), which
  adjusts a float at work+0x59d4 and the work+0x5800 area. MH4U's own 8/0 handler has no
  call at that point. The port skips it.
- The source's `[this+0xa304] == 2 && [this+0xa305] == 4` branch sets the tail flag to 1
  instead of 3. The MH4U handler has no such branch and the two bytes have no MH4U
  counterpart, so the port takes the source's other path.

Both slices leave one small detail: 3/98's second motion gets `s1 = 0.0` (the source leaves
`s1` from the previous state, which is `0.0` while the move is current), and 8/0's state 1
calls the per-mode check every frame as the source does.

The 4/27-32 slice has two more gaps:

- **The case blocks' call to `0x00adb528`, before the handler.** It forwards `(this, mode)` to
  method `0x4c` of the object `*(this+0x6dc4)` (the mode is 2, 2, 3, 3, 5, 5 per id). MH4U
  has no object at a matching field and no counterpart for the call was found, so it is left
  out and logged once per action. The handler's incoming `s0` (the percent it puts the line
  point at) is the dispatcher caller's; without the call's return the source may have had
  another value, which R2p will show.
- **The state-2 request for 7/246 or 7/247**, through the same `0x008ebab0` helper as 12/1 and
  12/2. It is left out and logged once; the move plays and the action ends without it.

#### Floats: the guest stubs

The host's ABI 4 `call2` runs a game function with `r0`-`r3` and the floats `s0`/`s1`, and
returns its `r0` plus its s0. That covers every engine call the translated handlers make
except two: 8/0's first hit check takes a third float in `s2`, and a source case block
receives its target points in `s0`-`s3`, which a hook cannot read. The runtime writes small
ARM stubs in a 384-byte block from the game's own heap (`alloc`, ABI 2) once for every module:

- `vldr s0/s1/s2` from a literal, then branch to the engine function (8/0's hit check);
- `vmov r0, sN; bx lr` to read the caller's `s0`-`s3`.

The port runs code that is not recompiled in Azahar's interpreter (`port/src/arm_recomp.cpp`,
`Interpret`), which reads the bytes each time, so a block from `alloc` is executable and a
stub's literals can be rewritten per call. T0 in
[checks.md](../../docs/checks.md#floats-through-a-guest-stub-t0) proves the stub in a headless
run, and P4 proves ABI 4's `call2`. When the plugin API grows s2/s3 arguments, the s2 stub is
replaced by the new call; the s0-s3 read still needs the `vmov` stub. `mhuc_call5`'s stub is the
third: it pushes the fifth argument, calls the function with r0-r3 as they came, and returns
its r0.

### 3U Rathian's module: category 0

MH3U's Rathian (USA, class `uEm002`) has 191 action ids, every one on her own code: the
dispatcher (vtable slot 50, `0x00687d30`) switches on the category byte and each category on
the index byte. `src/monsters/rathian-3u.c` is her module, the second in the runtime, and
category 0 is its first slice (issue [#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)):

| Id | Source | What the module runs |
|---|---|---|
| 0/0, 0/4 | handler `0x00699ad4` | state 0: state byte 1, mode 0, the block's 150.0 delay, the request for motion 1 at speed 10.0; state 1: count the delay down and, when spent, fall into 0/2's base handler |
| 0/1 | its inline case block (`0x006916b4`) | state 0: state byte 1, mode 0, the request for motion 2 at 10.0; state 1: the finish flag, then 0/2's base handler |
| 0/2 | base handler `0x0082d1cc` | state 0: state byte 1, mode 0, the request for motion `0x11` at 6.0; state 1: the finish flag, then the base handler: mode 0, the state test, the action start |
| 0/3 | base handler `0x00858b6c` | state 0: state byte 1, the data record's float, the fall it advances (which also sets mode 1), the request for motion `0x1a` at 6.0; state 1: the finish flag, then the base handler: the record's `+0x64`, the rate, mode 1, the action start |
| 0/6 | base handler `0x0082b7dc` | state 0: state byte 1, mode 3, the vertical step and its -75.0 clamp, the request for motion `0x1b` at 6.0; state 1: the vertical step, the finish flag, then the base handler: mode 3 and the action start |

The three base handlers are the port's own code under decision 0002's second 2026-11-26
amendment. Later slices reuse them: `0x0082d1cc` for 1/10 and 2/13, `0x00858b6c` for 3/10,
13/7 and 13/9.

**The field map.** MH3U keeps the work block at `*(this+0x1a48)`, MH4U at `*(this+0xe28)`.
Each row is an offset in MH4U's block and the 3U offset it stands for, with how it was found
(the paired function that reads both, or MH4U's own handler for the same action):

| MH4U | 3U | What | How |
|---|---|---|---|
| `+0x144` | `+0x5` | the action's state byte, shared by category 0's six ids | the field map recorded for [#251](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/251); `0x0090ef74` resets it at the action start |
| `+0x145`, `+0x146` | `+0x6`, `+0x7` | the action's next two state bytes | the field map recorded for [#251](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/251); `0x0090ef74` resets them too |
| `+0x1c8` | `+0xdc` | the mode byte | `0x0082fe88`/`0x009167b4` stores it at both offsets (map pair) |
| `+0x1ca` | `+0xdf` | the current category | the dispatcher reads both at the same place (`0x0082d1cc`/`0x00911b48`, `0x00858b6c`/`0x0094dc84`, `0x0082b7dc`/`0x00955970`) |
| `+0x1cb` | `+0xe0` | the current index | the dispatcher reads both |
| `+0x1dc` | `+0xf2` | "the action was set" | the three handler pairs store 1 there at the same point |
| `+0x51c` | `+0x941` | the state the 0/2 base handler tests | the `0x0082d1cc`/`0x00911b48` pair (MH4U's `0x0092e960` reads `+0x51c`) |
| `+0x1b4` bit `0x40` | `+0x8c` bit `0x40` | the same state's second test | the same pair; MH4U's base handler tests `+0x1b4` |
| `+0x34c` | `+0x381` | the other state byte the 0/2 base handler tests | the same pair |
| `+0x1c0` | `+0x3` | the data record lookup's id | the `0x00a33b50`/`0x0068882c` pair (the 0/3 handler pair reads it) |
| `+0x797e` | `+0xa` | the data record lookup's index | the same pair (`0x00a33b50` takes the block's `+0xa`) |
| `+0x64` (record) | `+0x70` (record) | the action data's float | the `0x00852324`/`0x0093d870` pair and the 0/3 base-handler pair |
| `+0x1b8`, `+0x1bc` | `+0x90`, `+0x94` | the fall rate and its second factor | the `0x00844124`/`0x0092e99c` pair (map, same body, offsets translated) |
| `+0x19c` | `+0x3c` | the fall height the data float advances | the same pair |
| `+0x180` | `+0x68` | the vertical value 0/6 advances | the `0x00833b2c`/`0x00915d44` pair |
| `+0x1c7` | `+0xd9` | `0x00833b2c`'s "applied" byte | the same pair |
| `+0x1d4` | `+0x28` | 0/0's 150.0 delay | MH4U's own category-0 handler (`0x006dc454`) stores its delay there and calls `0x00b0704c`, which the source's inline subtraction stands for |

The #251 map covers the state, mode, category and record-key rows; the record's `+0x64`
and the fall rate come from the [#253 helper map](../../reference/README.md#the-base-class-helpers-behind-category-0-and-0x0082d054); `+0x180` and `+0x1c7` are read off the
`0x00833b2c`/`0x00915d44` pair, and `+0x1d4` off MH4U's own 0/0. 0/0's `+0x28`/`+0x30` (the
delay and the frame delta it subtracts) are not in either table: MH4U's own 0/0 shows the
delay at `+0x1d4` and the countdown worker reads the frame delta at `this+0x14`, so the module
uses those.

**The engine calls.** Each row is the MH4U function the module calls, the 3U function it stands
for, and how the counterpart was established:

| MH4U | 3U | What | How |
|---|---|---|---|
| `0x009167b4` | `0x0082fe88` | the mode/state setter | map, same body (the 73) |
| `0x0094f408` | `0x0082a878` | set the next motion/state (r1, s0, s1) | the same call in the paired handlers (the 73); MH4U's own 0/0 and 0/1 pass the same ids and 10.0 |
| `0x00b05da4` | `0x0083cbf4` | the action's finish flag | the same call in the paired handlers (the 73) |
| `0x00915d44` | `0x00833b2c` | advance the vertical value by s0 * delta | the same call in a paired handler (the 73); `+0x68`/`+0x180` and `+0xd9`/`+0x1c7` agree |
| `0x0093d870` | `0x00852324` | the action data's float | the 73 and the same field |
| `0x0092e99c` | `0x00844124` | advance the fall by s0, set mode 1 | map, same body (the 73), offsets translated |
| `0x0068882c` | `0x00a33b50` | the monster's data record | the same call in the 0/3 handler pair (the [#253 map](../../reference/README.md#the-base-class-helpers-behind-category-0-and-0x0082d054)) |
| `0x0090ef74` | `0x00827d54` | start an action | the same call in the three handler pairs (the [#253 map](../../reference/README.md#the-base-class-helpers-behind-category-0-and-0x0082d054)), with one more stack argument |
| `0x00b0704c` | `0x008a78ec`'s body | count a float down by the frame delta | MH4U's own 0/0 handler |

Three things are not translated yet:

- **The source's `0x008412cc`.** The three base handlers call it before the action start: it
  looks the current action up in a list of `{category, index, s16 value}` entries from the
  source's action table and applies the value. MH4U has no function for it (the [#253 map](../../reference/README.md#the-base-class-helpers-behind-category-0-and-0x0082d054)), and
  the list is the source's data, which the port does not carry. MH4U's own action setter
  `0x0090ef74` takes a per-action value as a fifth, stack argument; the module passes MH4U's
  own value there (the same one MH4U's 0/2, 0/3 and 0/6 handlers pass), and logs the open item
  once. Whether the two are the same step is #55's in-game trace to settle.
- **`0x00833b2c`'s factor.** 3U's helper halves its argument before adding it to the block's
  vertical value; MH4U's `0x00915d44` does not. The module passes the source's -5.0 halved
  (-2.5), so the step applied is the source's. The source's own -5.0 is in the module's
  comment.
- **0/0's second delay field.** The source keeps the old delay at `+0x2c`; MH4U's countdown
  worker keeps one value, so the port keeps `+0x1d4` only.

The module's ready line is `ready: translating 6 of 3U Rathian's 191 actions on monster 125`,
and its self-test logs the six ids, the three base handlers' engine calls and the open item.
The 125 quest's run is check T1c.

## What it hooks

| Table | Address | Reader hooked | Id where |
|---|---|---|---|
| factory (`createEnemy`) | `0x006901f4` | the factory itself (the id layer), and the module association, which runs first and keeps the original id | r1 |
| data path (`enemyDataPathIndex`) | `0x00efc268` | `loadEnemyData`, `0x00689490` | r1 |
| enemy data (`enemyDataById`) | `0x00f3a024` | `0x0068882c` | r1 |
| crowns (`crownSizeTable`) | `0x00f32008` | `getCrown`, `0x0068877c` | r0 |
| list order (`monsterListOrder`) | `0x00df35b0` | `0x0061dc58` (find a monster's position) | r0 |
| icon (`monsterIconIndex`) | `0x00e06698` | `0x00c0e800`, `0x00c0e164` | r1, r2 |
| resource index (`enemyResourceIndex`) | `0x00efbd08` | `0x0068d8c8`, `0x00682ca0`, `0x00c0b830` | r1, r2, r2 |
| drops (`dropRecordIndex`) | `0x01003bec` | `0x00684b40`, `0x0092600c` | r1; the monster's own id |
| drops (`dropBaseA`, `dropBaseB`) | `0x01003ddc`, `0x01003ed4` | `0x00911f20`, `0x009357b4` | the monster's own id |
| name/notes text (`emName`, `emExp`) | `0x0109a080` slots 6, 7 | `0x00cdfb30` (`message::getFormat`) | r0 the table, r1 the id |
| name/notes text | — | `0x00cdfa18` (`message::getRecord`) | r0 the table, r1 the format entry |
| name/notes text | — | `0x00cdfa30` (`message::getRecordById`) | r0 the table, r1 the id |
| the quest task (`uc_questTask`) | `0x0065bcd0` | the state machine itself, before its state 0 preload (`0x0065bd7c`) | the stand-in's byte at `task + 0xd4`, see [the enemy data](#the-enemy-data) |
| the monster archive's name (`uc_dataPath`) | `0x00b7300c` | the `data\em%03d` builder, before the area init asks the archive loader | r2 the quest's wave id, see [the port's archive](#the-ports-archive) |
| the action dispatcher (`uEnemy::dispatchAction`) | `0x006e9cac` | the runtime's module dispatch, which runs the monster's module or the game's dispatcher | r0 the monster |

Most readers take the id in a register; the plugin rewrites that register and calls the game's
function. The factory has two hooks: the runtime's module association runs first and keeps the
original id, the id layer's reader rewrites it to the stand-in. Four read the id from the monster's data block (`this+0xe28`, byte `+0x1c0`); the
plugin swaps that byte for the stand-in, calls the game's function, and puts the real id back,
because the block is the game's own and must not keep the stand-in.

`mod.json` names each hook point with its USA v1.3.0 address; the fork's
[`tools/build_game.py`](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/tools/build_game.py)
adds them to the code library it builds. A library built without them logs which readers are
missing and the rest still answer.

## The id pool

MH4U's one-byte id leaves 124 to 223 permanent and 224 to 255 free
([0003](../../docs/decisions.md#0003-id-allocation-and-mod-saves)). A monster ported after the
permanent range is full takes a registry id from 256 up, which a quest's u32 monster list
records; 224 to 255 are the bytes the plugin lends it for each quest. No pooled monster ships
yet, so the shipped header's pooled array is empty. The checker's rules for the two ranges are
in [data/ids/README.md](../../data/ids/README.md#rules-the-tool-checks).

| Hook | Address | When |
|---|---|---|
| `QuestFlow::startQuest` | `0x00b7c010` | a quest starts: find its loaded `.mib` and rewrite the pooled ids it names |
| `aQuest::endSequence` | `0x0065a378` | the quest's return: free the bytes once the holder's status is 4 |

At quest start the plugin reads the quest id and the loaded quest-file resources from the
engine's quest holder (the same objects the port's quest-start workaround reads; the fork's
`port/src/hooks.cpp`, `QuestFlow::startQuest`). It finds the resource whose `.mib` quest id
matches, then walks the `.mib`'s large-monster waves ([specs/quest.md](../../specs/quest.md)):
each pooled id (256 and up) is rewritten in place to a free byte of 224 to 255, in the quest's
own wave order, so the same quest lends the same bytes on every player's console. The reader
hooks answer that byte with the pooled monster's rows, and build its resource record from its
stand-in exactly as for a permanent id. A retried quest start (the port rebuilds the list when
a file is late) keeps the bytes it already lent. When `aQuest::endSequence` has set the
holder's status to 4, the quest is over and the bytes are free; the next quest lends them
again. A quest that never reaches its end sequence keeps them until the next start.

The codes a lent byte needs are the same as a permanent id's: the stand-in's rows, the
resource record built for the pooled id, and the mod's own text; the pool only changes which
one-byte id those rows are addressed by. A pooled monster can't be on a guild quest card and
its hunt records go through the mod's data in the save, not MH4U's byte-indexed structures
([0003](../../docs/decisions.md#0003-id-allocation-and-mod-saves)).

The self-test (settings below) builds a synthetic `.mib` in guest memory that names the first
pooled id, lends it a byte, logs the answer, frees it again and logs that. With the shipped
registry (no pooled row) it logs that the pool is unused instead; check P1 in
[checks.md](../../docs/checks.md#uc-runtime) builds the plugin from
`tests/fixtures/registry-pooled.csv` to see the pooled lines.

## The resource record

MH4U loads a monster's own files from the `0x2c`-byte record `enemyResourceIndex[id]`
(0x00efbd08) points to: eleven pointers, each to an array of path slots, where a slot holds 0
or a pointer to a path string. The readers are `enemyResource::get` (0x0068d8c8, which
returns the record's field at +0x14), `enemyResource::load` (0x00682ca0, which loads the
paths of the fields at +0x00 to +0x28) and the effect allocator at 0x00c0b830 (which reads
the effect lists at +0x24 and +0x28).

| Offset | What | Slots |
|---|---|---|
| `+0x00` | model | 1 |
| `+0x04` | motion lists | 6 |
| `+0x08` | camera | 1 |
| `+0x0c` | a second motion list, ending at its first empty slot | up to 6 |
| `+0x10` | tail model | 2 |
| `+0x14` | motion effects | 2 |
| `+0x18` | unused (null in MH4U's own records) | 1 |
| `+0x1c` | sound | 1 |
| `+0x20` | four extra paths; slot 3 is the command (EMC) | 4 |
| `+0x24` | effect lists | the count in 0x00fb7a70 + id*4 (low u16; 26 for the stand-in em001) |
| `+0x28` | a second effect list | the high u16 of the same word (0 for em001) |

The two effect-list fields are arrays without a null terminator. `enemyResource::effectLists`
(0x00c0b830) takes their lengths from the per-id table of two u16 at 0x00fb7a70 (the low half
for +0x24, the high half for +0x28) and reads exactly that many slots. The builder gives each
field the stand-in's count, since the reader runs as the stand-in and a port ships no effect
lists yet. A field built with fewer slots makes the reader walk past the array; in the
plugin-built block the words after it are the record's path strings, so their first bytes
(`enem`, `y\em`, `125\`, `mod\`) are passed as path pointers and the load faults (#182).

The stand-in's record names paths under the stand-in's own id (`enemy\em001\...` for 124
and 125, `enemy\em015\...` for 126 and 127). On its first frame the plugin builds,
for each registered id, a record of its own from the stand-in's: the same fields and slots,
each path copied to the game's heap. A port ships only some of the record's path kinds (its
arc holds the model, motions, tail and command for 124 and 125, 125's command is her converted
MH3U AI script, 126's holds the model and its four borrowed motion lists, and 127's the model
and its three motion lists ([specs/emc.md](../../specs/emc.md)); MH4U stops the load on a path
that is not there, which is what hung a 3U session at "Now Loading" when the 125 record named
13 paths and `em125.arc` ships 6
([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)). So the registry's
`files` column, generated into `src/ids.h` as `MHUC_FILES_*` bits, names the kinds a port
ships, and the builder rewrites the monster-id token only in those kinds' paths
(`em001` -> `em124`, and the camera's `e001` -> `e124`; an effect list's trailing `_000` is
not an id and stays). The motion slots are named, `motions=0-4` or `motions=0,2,3,4`: only
those slots are rewritten and the other slots keep the stand-in's paths, because the port's
motion-number translation only targets the source slots it ships (125 keeps MH4U's
`enemy\em001\mot\em001_3` and `_4`; 126 ships MHXX's slots 0, 2, 3 and 4 and keeps the
stand-in's 1 and 5; 127 ships slots 0, 1 and 2 and keeps 3, 4 and 5). A slot the stand-in's
own record leaves empty but the port ships gets the port's own motion-list name,
`enemy\emNNN\mot\emNNN_<slot>`, which is what the converter writes: 126's slot 4 is one,
because Great Jaggi's record has no slot 4. For a kind it does not ship, the stand-in's path is
copied unchanged, so the monster loads MH4U's own motion effects and effect lists until its
game's are converted; 125 to 127 also keep MH4U's camera, since only 124 has a source camera
list to convert (MHXX's; `mhuc convert monster` writes it at `e124_cam`). 125 ships her own
sound (`mhuc convert monster`, issue #158). The record, its slots and its strings are one
block from the game's own heap (`alloc`, ABI 2), and it is kept for the run.

| Kind in `files` | The record's paths |
|---|---|
| `model` | +0x00, the model |
| `motions=0,2` | +0x04, the six motion lists, and +0x0c, the second motion list; each named slot is the port's and the others keep the stand-in's path |
| `camera` | +0x08, the camera |
| `tail` | +0x10, the tail model |
| `mef` | +0x14, the motion effects |
| `sound` | +0x1c, the sound |
| `cmd` | +0x20 slot 3, the command/EMC |
| `efl` | +0x24 and +0x28, the effect lists |

The `+0x20` slots 0 to 2 are empty in MH4U's own records and have no kind, so they can only
keep the stand-in's path. A new kind is added to `data/ids/registry.csv`'s checker
(`tools/check_ids.py`) and to the plugin's path map together; the `motions` slot mask is
emitted into the header beside the bits (`MHUC_MOTION_SLOT`).

`enemyResource::get` is answered with the built record's +0x14 field. `enemyResource::load`
and `enemyResource::effectLists` (0x00c0b830, called with the spawned monster's own id after
the loader) read the record from the table itself, and ids 124 and up have no row there (the
table ends where `enemyDataPaths` begins), so the hook points the stand-in's row at the built
record for the call, runs the reader as the stand-in, and puts the row back. The data path
(`enemyDataPathIndex`, 0x00efc268) still answers with the stand-in's: the ports ship no
MH4U-format `.emd`/`.etd` yet, so their monster data loads from the stand-in's.

## The enemy data

Before the area exists, the quest task's state machine (`uc_questTask`, 0x0065bcd0) fills a
124-byte monster-presence array at `task + 0xd4`, one byte per MH4U id 0 to 123, from the
quest's monster set. In state 0 its preload loop (`0x0065bd7c`) then loads the enemy data of
every id whose byte is set, through `loadEnemyData` (`0x00689490`). The loader answers a
registered id with the stand-in's data row, so the stand-in's `.emd`/`.etd` from
`data/em_data.arc` is what the ported monster's factory reads.

The array has no row for a ported id: a quest that fields id 125 sets a byte past its end,
which the preload loop never visits, so the stand-in's data is never loaded and every later
`enemyData::get(1)` returns null, which the callers dereference. At quest start the plugin
already finds the quest's loaded `.mib` (the pool's hook, below); there it reads the
large-monster waves, and for every registered id they name it records the stand-in's byte.
Before the state 0 preload runs, it sets those bytes in the presence array. The game's own
preload then loads the stand-in's data, at the same point and with the same call as for an
MH4U quest that fields the stand-in. A quest that names no registered id is untouched.

The run logs `quest 10212: id 125 -> stand-in 1 marked present so the state 0 preload loads its
enemy data`, then `quest task: marked stand-in 1 present before the preload`.

## The port's archive

The map/area init builds the monster archive's path from the quest's wave id with the
`data\em%03d` format (`0x00b7300c`) and asks the engine's archive loader for it. A port that
ships a model has its own archive at that path (`data/em125.arc`), and its record's
`enemy\em125\...` paths only resolve if that archive is the one mounted, so a model port's id
passes through the builder unchanged (the log line is `data resource: id 125 -> its own
archive`). A port that ships no model keeps the stand-in's model in its record, so for it the
builder still answers with the stand-in's archive. MH4U's own ids 0 to 123 always pass through.

The material signature was what made the port's archive never load (#203): MH4U's
`rMaterial` loader refuses a file whose signature at +0x10 isn't its own, and
`mhuc convert monster` now writes it ([specs/mrl.md](../../specs/mrl.md)). A model port's
archive must also carry the stand-in's entries the record keeps (the camera for a row without
one, motion effects, command and effect lists), so the one archive the game opens holds every
path the record names: `mhuc convert monster --mh4u-romfs` copies them in from MH4U's own
`data/emNNN.arc`.

## The name and notes text

MH4U answers a monster's name and its Hunter's Notes text by the id: the message tables
`emName` and `emExp` are loaded from `core_common.arc` and their message N names monster N
(specs/lmd.md). The game loads 71 message tables into the pointer array at `0x0109a080`, with
`emName` at slot 6 and `emExp` at slot 7, and the per-id getters are `0x00cdfb30` (the 16-byte
format entry), `0x00cdfa18` (the 12-byte string record from a format entry) and `0x00cdfa30`
(the record by id). The plugin wraps the three: a registered id is answered with its own
format entry (a copy of the stand-in id's, so the message object's layout words stay), its own
string record and a UTF-16 string in the game's heap. Every other id and every other message
table goes to the game's getters unchanged.

The text comes from the mod's `text/monster_text.bin`: one entry per registered id, its name
from [the registry](../../data/ids/README.md) and its notes from the source game's own table,
recorded per id in [data/ids/notes.csv](../../data/ids/README.md#the-notes-source). The file
holds no MH4U text. Build it where the mod's folder can see it (outside the repository):

```bash
MHUC_DUMPS=<dumps> mhuc text build --dumps <dumps> \
    --out <mod library>/<the mod's folder>/text/monster_text.bin
tools/check_text.py --mod <that file>
```

Until the file exists, the plugin logs a warning and the ported ids keep no text (the game's
getters return nothing for them). The notes' language is the source game's: MH3U USA gives
English, MHXX JPN gives Japanese until the port reads MHGU's English text. A GU monster's
English notes are therefore still content work, not this plugin's.

## What it does not do yet

- **The Hunter's Notes list** that walks all 124 rows (`0x0061df4c`) and the notes list's sort.
  Only the position lookup (`0x0061dc58`) is answered, so the textual getters above answer an
  id the UI already shows, but a ported monster is not added to the Notes list itself.
- **The data path** stays the stand-in's until the ports ship MH4U-format `.emd`/`.etd`.
- **The pool's real path.** No pooled monster ships and no quest names one yet, so the quest
  start and end hooks have only run against the synthetic `.mib` of check P1; a real quest with
  a pooled monster is check P2 and is not done, and whether the post-quest screens still read
  the tables after the end sequence is unverified. A quest that never reaches its end sequence
  keeps its bytes until the next quest starts.
- **The port's camera, motion effects and effect lists.** A port ships its model, motions,
  tail and command, 124 her converted MHXX camera, and 125 her sound (126 and 127 ship only
  their models and motions); for the kinds it does not ship — motion effects and effect lists
  for all of them, and the camera for 125 to 127, which have no source list — the record keeps
  MH4U's paths, and their files are MH4U's until the port's game has them converted.
- **The monster is the stand-in.** Except for its resource record, the tables answer with the
  stand-in, and the monster's data block still holds the stand-in's own id byte, so a spawned
  monster is MH4U's monster. The port's own rows replace the stand-in when
  [#48](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/48) and
  [#49](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/49)'s converted files are
  installed. The module's routing does not depend on that byte: it comes from the factory's r1
  before the id layer rewrites it.
- **The GU module's shared ids and 12/0.** Decision 0002's 2026-11-26 amendment owes her own
  handler for every action, shared ids included. This move carries only the twelve translated
  MHXX-only actions; 12/0 and the shared ids still run MH4U's dispatcher.
- **The rest of the 3U module's 191 ids.** Only category 0 (six ids) and its three base
  handlers run; the other 185 ids are still owed, one family per slice
  ([#217](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/217) to
  [#229](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/229)) and action 4's
  ([#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136)). An id this slice
  does not carry goes to MH4U's dispatcher and is logged once, so a forced id that does
  nothing says so. The source's `0x008412cc` per-action value step is the one item the
  category-0 slice leaves open (#55).
- **`monster` no longer chooses another monster.** A module answers its registry id, so the old
  plugin's `monster = 1` (translate GU Rathian's actions onto MH4U's Rathian) is gone. The
  setting is kept for old config files and warns when it names no module; whether a module can
  be switched off by a setting is [0013](../../docs/decisions.md#0013-one-runtime-for-the-mods-native-code)'s
  open question.

## Build

```bash
make        # uc_runtime.so next to mod.json
make test   # the id layer and the modules on a fake host, with no game
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. `src/ids.h` and `src/modules.h` are generated, not edited: run `python3
tools/check_ids.py --write` after changing the registry. Licence: GPL-3.0-or-later, like the
rest of the mod.

## Install

```bash
python3 <fork>/tools/mods.py add mods/uc_runtime
python3 <fork>/tools/mods.py enable "UC runtime"
MHUC_DUMPS=<dumps> mhuc text build --dumps <dumps> \
    --out "<Azahar user directory>/mh4u-mods/UC runtime/text/monster_text.bin"
python3 <fork>/tools/build_game.py --dump "MH4U v1.3.0 update.cia" --install <Azahar user directory>
```

A run logs `ready: answering MH4U's monster tables and name/notes message getters for 4
permanent and 0 pooled id(s), 124 and up, lending 224..255 per quest, with the files each port
ships and the stand-in's for the rest`, then the modules' ready lines, for GU Rathian
`ready: translating 12 of GU Rathian's 13 MHXX-only actions on monster 124`, then
`text: 4 of 4 entry(ies) from
text/monster_text.bin; every registered id has a name and notes`, then one line per reader the first time it answers a registered id and one the first
time it passes an MH4U id through, for example `factory: id 124 -> stand-in 1`; the resource
readers log `resource index: id 124 -> its own record`, `resource load: id 124 -> its own
record` and `effect lists: id 124 -> its own record`. A quest that names a pooled monster logs
`quest 60012: pooled id 256 -> lent 224`, and its end logs `quest 60012 ends: freed the pool
byte(s) 224`. A quest that names a registered monster logs `quest 10212: id 125 -> stand-in 1
marked present so the state 0 preload loads its enemy data`, then `quest task: marked stand-in
1 present before the preload` and `data resource: id 125 -> its own archive`.

## Settings

`mod.json` holds the defaults; a `config.ini` in the installed mod's folder overrides them
(`key = value` lines).

| Key | Default | Means |
|---|---|---|
| `selftest` | `0` | `1`: on the first frame, log what every reader answers for each registered id, the paths of the resource record built for it and which kinds and motion slots it ships and keeps the stand-in's for, the path the stand-in's data comes from, the name and notes text and the three message getters' answers, that ids 0 to 123 pass through, and a pooled id lent, answered and freed by a synthetic quest; then each module's self-test. The check in [checks.md](../../docs/checks.md#uc-runtime) uses it. |
| `monster` | `124` | The id a module's ready line names. A module answers the registry id it was built for, so this no longer chooses another monster (the old plugin's `monster = 1` translated her actions onto MH4U's Rathian; a module cannot, see [what it does not do yet](#what-it-does-not-do-yet)); the setting is kept so an old `config.ini` still loads, and the runtime warns when it names no module. |

## The check

The headless check and what it must show are in
[checks.md](../../docs/checks.md#uc-runtime).
