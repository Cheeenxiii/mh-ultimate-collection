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
builder, the pool, the text tables, the notes list and the self-test moved here from the plugin
that held them before.

## Layout

| Path | Holds |
|---|---|
| `src/runtime.c` | the plugin entry point and the one hook table: it registers the id layer's hooks and frame call, then the module side's |
| `src/runtime.h` | what the entry point and the parts share: the hook type, the id layer's calls, the registry-id lookup and the module side's calls |
| `src/ids.c` | the id layer: the readers, the resource-record builder, the id pool, the name and notes text, the notes list and the self-test |
| `src/ids.h` | generated from `data/ids/registry.csv` by `tools/check_ids.py --write`; do not edit |
| `src/module.c` | the machinery every module shares: the factory association, the action dispatcher, the state slots, the guest call and the guest stubs |
| `src/module.h` | the module interface: `MhucModuleOps`, `MhucState`, the guest call, the accessors, the motion encoder and the log |
| `src/modules.h` | generated from the registry and the module files: one row per registered id, with the monster's `ops` or 0 for a data-only port; do not edit |
| `src/monsters/rathian-gu.c` | GU Rathian's module: the shared entry (the factory association's dispatch, the action log, the ready line and the self-test) and the loop over the generated family list |
| `src/monsters/rathian-gu/family.h` | GU Rathian's family interface: `MhucFamily` (a name, the ids it carries, a dispatch entry, a self-test), the bit helpers the handlers share, 3/98's handler `mhuc_gu_run_3_98` and the shell's state/log helper `mhuc_gu_state` |
| `src/monsters/rathian-gu/cat17.c` | category 17's family: the gate's 0-2 no-op and MH4U's base action update for the rest |
| `src/monsters/rathian-gu/act3_98.c` | action 3/98's family: three states, motions `0x101` and `0x104`; its handler is exported for 12/1 |
| `src/monsters/rathian-gu/act12_1_3.c` | the 12/1 to 12/3 family: the target-point blocks, 3/98's handler and MH4U's shared 3/12 and 3/9 handlers |
| `src/monsters/rathian-gu/act4_27_32.c` | the 4/27 to 4/32 family: one handler, three states, r1/r2 per id |
| `src/monsters/rathian-gu/act8_0.c` | action 8/0's family: three states and the 9/1 or 2/6 combo tail |
| `src/monsters/rathian-gu/families.h` | generated at build time from the `.c` files in that directory by `tools/gen_families.py`; do not edit or commit |
| `src/monsters/rathian-3u.c` | 3U Rathian's module: the shared entry (the factory association's dispatch, the pending log, the ready line and the self-test) and the loop over the generated family list |
| `src/monsters/rathian-3u/family.h` | the family interface: `MhucFamily` (a name, the ids it carries, a dispatch entry, a self-test) and the three base handlers `cat0.c` exports for the slices that reuse them |
| `src/monsters/rathian-3u/cat0.c` | category 0's family: `0/0`, `0/1`, `0/2`, `0/3`, `0/4`, `0/6` and the three base handlers they reach, the first slice of her 191 ids |
| `src/monsters/rathian-3u/cat1.c` | category 1's family: `1/0` to `1/14`, its five handler units and four inline blocks; it reuses `cat0.c`'s `mhuc_3u_base_0_2` for 1/10 |
| `src/monsters/rathian-3u/cat3b.c` | category 3's part 2's family: `3/6`, `3/7`, `3/8`, `3/12`, `3/13`, `3/16` to `3/21`, `3/24`, `3/25`, `3/27` to `3/29`, and 3/8's base-class handler (#220) |
| `src/monsters/rathian-3u/cat7a.c` | category 7's first family (#221): `7/0`, `7/1`, `7/2`, `7/4`, `7/5`, `7/6`, `7/7`, `7/8`, `7/10`, `7/11`, `7/12`, `7/15`, `7/16`, `7/19`, `7/20`, `7/32`, `7/34`, `7/42`, `7/61`, `7/77`, `7/85`, and the calls still blocked |
| `src/monsters/rathian-3u/cat7b.c` | category 7 part 2's family (#222): `7/3`, `7/9`, `7/13`, `7/14`, `7/17`, `7/18`, `7/21`, `7/30`, `7/41`, `7/43`, `7/44`, `7/53`, `7/54`, `7/55`, `7/56`, `7/72`, `7/73`, `7/78`, `7/80`, `7/83`, `7/88`, `7/89`, on the units 0x00694474, 0x00694f4c, 0x006956e8, 0x00695e68 and 0x00696408 |
| `src/monsters/rathian-3u/cat13a.c` | category 13's first family (#227): `13/0` to `13/4`, the five units and the calls still blocked |
| `src/monsters/rathian-3u/cat8.c` | category 8's family: id `8` and the three class helpers its handler reaches (#225) |
| `src/monsters/rathian-3u/cat11.c` | category 11's family: `11/0`, `11/5`, `11/15`, `11/26`, `11/28`, the shared wrapper `0x00687e88` and the base-class handler `0x0084d864` (#225) |
| `src/monsters/rathian-3u/families.h` | generated at build time from the `.c` files in that directory by `tools/gen_families.py`; do not edit or commit |
| `tests/test_rathian_3u.c` | the 3U module's shell on the fake host: the factory association, the routing, the ready line and the self-test (`make test`) |
| `tests/rathian-3u/host.h` | what the 3U module's fake-host tests share: the constants the expectations are written against, and the spawn/frame helpers |
| `tests/rathian-3u/cat0.c` | category 0's fake-host test: its six ids' and three base handlers' call sequences; `make test` discovers it and builds `tests/family-cat0` |
| `tests/rathian-3u/cat1.c` | category 1's fake-host test: its fifteen ids' states, call sequences and frame values; `make test` discovers it and builds `tests/family-cat1` |
| `tests/rathian-3u/cat3b.c` | category 3's part 2's fake-host test: the sixteen ids' frames and call order and the two blocked calls' log lines; `make test` builds `tests/family-cat3b` |
| `tests/rathian-3u/cat7a.c` | category 7 part 1's fake-host test: every id's and variant's call sequence; `make test` discovers it and builds `tests/family-cat7a` |
| `tests/rathian-3u/cat7b.c` | category 7 part 2's fake-host test: every id's and variant's call sequence and frame values; `make test` discovers it and builds `tests/family-cat7b` |
| `tests/rathian-3u/cat13a.c` | category 13 part 1's fake-host test: the five ids' frame values and call order, and the blocked calls' log lines; `make test` discovers it and builds `tests/family-cat13a` |
| `tests/rathian-3u/cat8.c` | category 8's fake-host test: id 8's three states, the 300.0/38.0 aim, the 12.0/50.0 test, the 90.0 timer and motion `0xca`, and the four blocked calls' log lines; `make test` builds `tests/family-cat8` |
| `tests/rathian-3u/cat11.c` | category 11's fake-host test: the five ids' shared-handler calls, 11/28's 45.0/0.5 step and its three open items' log lines; `make test` builds `tests/family-cat11` |
| `tests/rathian-gu/host.h` | what the GU module's fake-host tests share: the constants the expectations are written against, and the spawn/frame helpers |
| `tests/rathian-gu/cat17.c` | category 17's fake-host test: the 0-2 no-op and the base update; `make test` discovers it and builds `tests/family-gu-cat17` |
| `tests/rathian-gu/act3_98.c` | action 3/98's fake-host test: its three states and the motions `0x101`/`0x104`; `make test` builds `tests/family-gu-act3_98` |
| `tests/rathian-gu/act12_1_3.c` | the 12/1 to 12/3 family's fake-host test: the target points and the shared handlers; `make test` builds `tests/family-gu-act12_1_3` |
| `tests/rathian-gu/act4_27_32.c` | the 4/27 to 4/32 family's fake-host test: the six ids' states and the fast-step path; `make test` builds `tests/family-gu-act4_27_32` |
| `tests/rathian-gu/act8_0.c` | action 8/0's fake-host test: its three states and the 9/1 or 2/6 tail; `make test` builds `tests/family-gu-act8_0` |
| `tests/fixtures/rathian-3u/probe_test.c` | the probe family test the test-list discovery builds and runs |
| `tests/test_family_discovery.c` | a family file added to a directory, discovered and routed with no other edit (`make test`) |
| `tests/fake_host.c`, `tests/fake_host.h` | the fake host every test runs on: guest memory, the heap, `call`/`call2` and the guest stubs, the hooks, the registers and the log |
| `tests/test_runtime.c` | the id layer on the fake host (`make test`) |
| `tests/test_module.c` | GU Rathian's module shell on the fake host: the factory association, the routing, the ready line and the self-test (`make test`) |

## The module interface

A ported monster's action code is one C file, `src/monsters/<key>.c`, where `<key>` is its
registry key, compiled into the runtime. A monster with many action ids puts its families in a
directory `src/monsters/<key>/`, one file per family, and the build discovers them (see
[Adding a family](#adding-a-family-an-action-slice)); the module file keeps what every family
shares. The module exports one `const MhucModuleOps` ([src/module.h](src/module.h)):

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

### Adding a family (an action slice)

A monster whose ids are ported in slices keeps one C file per family under
`src/monsters/<key>/` and one fake-host test per family under `tests/<key>/`. The 3U Rathian
has ten action families (#217 to #229, and action 4's #136); the GU Rathian's twelve
translated ids are split the same way, one family per slice below. A slice adds **its family
file and its test file, and nothing shared**:

1. Write `src/monsters/<key>/<family>.c` with the slice's handlers. It includes `family.h` and
   exports one `const MhucFamily` whose name is the file's stem with every non-alphanumeric
   byte replaced by `_`, under the module's tag: `mhuc_3u_family_cat0` for the 3U module,
   `mhuc_gu_family_cat17` for GU. The tag is the Makefile's `FAMILY_TAG_<key>`, which the build
   passes to `tools/gen_families.py --tag`; it names the symbols and the generated
   `families.h`:
   ```c
   static int dispatch_cat0(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                            int index);
   static void self_test_cat0(MH4UCall *call);
   const MhucFamily mhuc_3u_family_cat0 = { "cat0", 6, dispatch_cat0, self_test_cat0 };
   ```
   `dispatch` gets the MH4U work block and the action pair and returns 1 when it ran the pair,
   0 so the module tries the next family. `translated` is the number of ids the family carries,
   which the ready line sums. `self_test` logs the family's self-test lines (NULL for none).
   A handler another family's source falls into is exported from its file and declared in the
   key's `family.h`: the 3U module's three base handlers from `cat0.c` (1/10 and 2/13 run
   0/2's; 3/10, 13/7 and 13/9 run 0/3's) and GU's 3/98 handler from `act3_98.c` (12/1 runs
   it). A GU family asks for its state through the shell's `mhuc_gu_state`, which also writes
   the action log, instead of calling `mhuc_state` directly; the 3U families keep their state
   in the work block.
2. Write `tests/<key>/<family>.c`, the family's fake-host test, with its own `main` and
   `guest_fn` (what the engine answers its calls). It includes `tests/<key>/host.h` for the
   constants and the spawn/frame helpers, and checks the call sequences like `cat0.c` does.
   The shell's test is `tests/test_rathian_3u.c` for 3U and `tests/test_module.c` for GU; a
   family test never edits it. `make test` discovers every `.c` file under `tests/<key>/`,
   builds each as `tests/family-<family>` for 3U and `tests/family-gu-<family>` for GU (the
   prefix keeps the two modules' family names apart), and runs it; `test-family-discovery`
   puts a probe family test in a directory of its own and runs the entry the wildcard found,
   so a new test file needs no other edit.
3. Mark the slice's ids in [data/actions/rathian-3u.csv](../../data/actions/README.md) or
   [data/actions/rathian-gu.csv](../../data/actions/README.md).
4. `make`. The Makefile runs `tools/gen_families.py` over the source directory once per
   `FAMILY_KEYS` entry and writes that module's generated `families.h`; the module's dispatch
   tries the families in it. Nothing else is edited: no list, no dispatch, no other family.
5. `make test` and the headless check T1c. `tests/test_family_discovery.c` builds a directory
   with a probe family the module does not ship, generates its list, and calls the entry the
   list found; it is the same step a slice takes for the module's family list.

### A worked example: GU Rathian's module

`src/monsters/rathian-gu.c` is the shell every GU family shares, and
`src/monsters/rathian-3u.c` has the same shape for 3U. The shell's `dispatch` reads the pair
once and tries the generated family list:

```c
static int dispatch(MH4UCall *call, uint32_t enemy) {
    const uint32_t work = mhuc_work(call, enemy);
    if (!work) {
        return 0;
    }
    const int category = mhuc_category(call, work);
    const int index = mhuc_index(call, work);
    for (unsigned i = 0; i < MHUC_GU_FAMILY_COUNT; i++) {
        const MhucFamily *family = mhuc_gu_families[i];
        if (family && family->dispatch &&
            family->dispatch(call, enemy, work, category, index)) {
            return 1;
        }
    }
    return 0;
}
```

A family file claims its own pair and runs it, asking the shell for the state and the action
log (`act3_98.c`):

```c
static int dispatch_act3_98(MH4UCall *call, uint32_t enemy, uint32_t work, int category,
                            int index) {
    if (category != 3 || index != 98) {
        return 0;
    }
    MhucState *st = mhuc_gu_state(call, enemy, category, index);
    if (!st) {
        return 0;
    }
    mhuc_gu_run_3_98(call, enemy, work, st);
    return 1;
}

const MhucFamily mhuc_gu_family_act3_98 = { "act3_98", 1, dispatch_act3_98, 0 };
```

The shell's `start` sums the families' `translated` counts into the ready line, and its
`self_test` logs what the module carries, the families the build discovered and where the guest
stubs are. `tests/test_module.c` drives the shell: the factory association, the routing (its id
runs the module, an MH4U id and a registered id without a module fall through) and the ready
and self-test lines; each family's call sequences are its own program under
`tests/rathian-gu/`.

### GU Rathian's translated actions

The fourteen ids split into four slices (the issues are in the same milestone), and the
module's five family files: `cat17.c` for category 17, `act3_98.c` for 3/98, `act12_1_3.c` for
the 12/1 to 12/3 chain, `act4_27_32.c` for 4/27 to 4/32 and `act8_0.c` for 8/0. 3/98 and the
12/1-3 chain are one slice but two files, because 12/1 runs 3/98's handler.

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

### 3U Rathian's module: category 0, category 1 and category 3

MH3U's Rathian (USA, class `uEm002`) has 191 action ids, every one on her own code: the
dispatcher (vtable slot 50, `0x00687d30`) switches on the category byte and each category on
the index byte. `src/monsters/rathian-3u.c` is her module, the second in the runtime: the
shared entry (the factory association's dispatch, the pending log, the ready line and the
self-test) and the loop over the family list the build generates from
`src/monsters/rathian-3u/`. Category 0's family is `cat0.c`, the first slice (issue
[#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)); the ten family
slices (#217 to #229, and action 4's #136) add one file each. Category 0's family runs:

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

Category 1's fifteen ids are `cat1.c`, the second slice (issue
[#217](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/217)). Its five handler units
and four inline blocks run:

| Id | Source | What the module runs |
|---|---|---|
| 1/0, 1/9 | handler `0x00692834` | state 0: state byte 1, mode 0, the motion 5 at 10.0, the `(0, 0x13)` call and the elapsed-time accumulator cleared; state 1: the 110.0 query twice, the `(1, 8, 5)` call and the `0x00161798` forward on the first, the accumulator on the 112.0/214.0 query, then the finish flag and 0/2's base handler |
| 1/1 | its inline block (`0x00686384`) | state 0: state byte 1, mode 0, the motion `0x12` at 10.0; state 1: the finish flag, then 0/2's base handler |
| 1/2 | its inline block (`0x006863e0`) | state 0: state byte 1, mode 0, the source's motion `0x7c` (file 1, slot 24) at 2.0; state 1: the finish flag, then 0/2's base handler |
| 1/3 | its inline block (`0x0068643c`) | state 0: state byte 1, mode 0, the motion 2 at 50.0; state 1: the 52.0 query at mode 1, then 0/2's base handler |
| 1/4, 1/13 | handler `0x00692a1c`, r1 = 0 | the `0x0083d18c` byte, state 0: state byte 1, mode 0, the motion `0x13` at 6.0 and the 3.0 timer; state 1: the 176.0 query counts the timer down; while it runs, return; once spent, a request for 1/5 (index 4) or 1/0x0e |
| 1/7 | handler `0x00692a1c`, r1 = 1 | the same, plus the twelve animation queries and their effect spawns; a spent timer requests 1/8 |
| 1/5, 1/14 | handler `0x00692f14`, r1 = 0 | state 0: state byte 1, mode 0, the motion `0x14` at 6.0; state 1: the finish flag and 0/2's base handler |
| 1/8 | handler `0x00692f14`, r1 = 1 | the same, with the six animation queries and their effect spawns before the flag |
| 1/6 | handler `0x0069322c` | state 0: state byte 1, mode 0, the motion `0x17` at 6.0; state 1: the finish flag, then state 2, the motion `0x18` at 0.0, the 1800.0 timer and `0x0031be10`; state 2: the `(1, 0xa, 0.6)` call, the countdown, then state 3, the motion `0x19` at 4.0 and `0x008440a4`; state 3: the finish flag and 0/2's base handler |
| 1/10 | its inline block (`0x006864dc`) | state 0: state byte 1, mode 0, the motion `0x11` at 6.0; state 1: the finish flag, then `cat0.c`'s `mhuc_3u_base_0_2` |
| 1/11 | handler `0x00693388`, r1 = 0 | state 0: state byte 1, mode 0, the 20.0 timer and the motion 1 at 10.0; state 1: the finish flag or the spent timer, then 0/2's base handler |
| 1/12 | handler `0x00693388`, r1 = 1 | the same, with the motion `0x11` at 6.0 |

**#55's open calls.** All eight ids on the three handlers `0x00692834`, `0x00692a1c` and
`0x00692f14` (`1/0`, `1/4`, `1/5`, `1/7`, `1/8`, `1/9`, `1/13` and `1/14`) call the source's
`0x0016052c`, the uEffect039 spawn. MH4U has no uEffect039 class, so the call is #55-blocked;
`0x00161798` (1/0 and 1/9), `0x00847798` (the six ids whose handler runs the r1 = 1 effect
block) and `0x0016669c` (1/7's type-9 effect factory, whose MH4U factory takes a type where the
source passes the monster) are blocked the same way, and `0x005aef18`'s two-float gate has no
MH4U field pair. The module names them once in the log, skips them and plays the moves without
their effects; #55's trace, and the effects' carrying in
[0015](../../docs/decisions.md#0015-carrying-a-source-effect-into-mh4u), fill them in. 1/3's
motion start also passes a fifth stack argument, which MH4U's motion-start wrapper does not
take.

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
| `+0x1d4` | `+0x28` | 0/0's 150.0 delay, category 1's timer (1/4, 1/6, 1/11) and 1/0's elapsed-time accumulator | MH4U's own category-0 handler (`0x006dc454`) stores its delay there and calls `0x00b0704c`, which the source's inline subtraction stands for; category 1's 1/4/1/6/1/11 pairs read the same field as their timer, and 1/0's pair reads it as the elapsed value its effect gate divides |
| `+0x14` (this) | `+0x14` (this) | the frame delta | the same 12 twins as the field map ([#251](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/251)); `0x00b0704c` reads it there, and 3U's timer reaches the same value through the pointer at `work+0x30` |

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
| `0x00b0704c` | `0x008a78ec`'s body | count a float down by the frame delta | MH4U's own 0/0 handler; category 1's 1/4, 1/6 and 1/11 timer |
| `0x0094e318` | `0x00828828` | start a motion (index r1, speed s0, s1) | the same call in a paired handler (the 73); the source's r2 is the speed, which MH4U takes in s0 (1/6's 6.0, 1/11's 10.0 and 6.0) |
| `0x0091aae4` | `0x0083336c` | the flag-clear query, its r0 tested | the same call in a paired handler (the 73); the source's r1 is the mode, and MH4U's r3 = r2, r2 = 0 |
| `0x0094ef64` | `0x0082a06c` | request the next action (r1, r2) | the same call in a paired handler (the 73) |
| `0x0093310c` | `0x00844a40` | 1/0's `(1, 8, 5)` call | the same call in a paired handler (the 73) |
| `0x00914dc4` | `0x00844a38` | 1/0's `(0, 0x13)` call, r3 = 0 | the same call in a paired handler (the 73); `0x00844a38` is `0x00844a40` with r3 = 0, and `0x00914dc4` is `0x0093310c` with r3 = 0 |
| `0x00922ca0` | `0x0083d18c` | 1/4's and 1/13's r1 = 0 byte | the same call in a paired handler (the 73) |
| `0x0093ba88` | `0x0083c79c` | 1/6's state 2 call | the same call in a paired handler (the 73) |
| `0x0091b0f8` | `0x0031be10` | 1/6's state 1 tail | the same call in a paired handler (the 73) |
| `0x0093c938` | `0x008440a4` | 1/6's state 2 tail | the same call in a paired handler (the 73); `0x008440a4` is the source's r1 = 0 form, MH4U's r1/r2 = 0 |

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

The module's ready line sums the families' `translated` counts: `ready: translating 6 of 3U
Rathian's 191 actions on monster 125` after #216, 22 after #220, 37 after #217, 58 after
#221, 63 after #227, 85 after #222, 100 after #219 and 106 after #225. Its self-test logs
families' ids, engine calls and open items. The 125 quest's run is check T1c.

#### Category 3's part 1 (#219)

`cat3.c` translates fifteen ids on eight source units: 3/0 (`0x0068d9ec`), 3/1
(`0x0068db54`), 3/2 and 12 (`0x0082d054`, base-class code reimplemented under 0002's second
amendment), 3/4 (`0x0068dc60`), the seven ids `0x0068dd78` serves (3/5, 3/9, 3/14, 3/22,
3/23, 3/26 and 3/30, told apart by the r1 its case block leaves: 3/5=0, 3/9=1, 3/14=2,
3/22=3, 3/23=4, 3/26=5, 3/30=6), 3/10 (`0x00858b6c`, the 0/3 base handler cat0.c exports),
3/11 (its case block `0x0069987c` and tail `0x0083b424`, the "action was set" byte) and 3/15
(the inline block `0x00699964`). 3/10 and 3/15 share the source's state-0 block `0x006999ac`,
so both start motion `0x2d` at 6.0; 3/15's state 1 turns toward the target by 0x180 first.

| Id | Source | What the module runs |
|---|---|---|
| 3/0 | handler `0x0068d9ec` | state 0: mode 0, motion `0x29` at 6.0; state 1: the flag, the data float, the fall, motion `0x43` at 0.0, A cleared; state 2: the curve (blocked), the data float, the turn at 1.0, the flag, state 3, motion `0x1a` at 6.0; state 3: turn by 0x100, the flag, the immediate 3/2 |
| 3/1 | handler `0x0068db54` | as 3/0's first two states; state 2: the curve (blocked), the data float, the turn, the flag, then 0/3's base handler |
| 3/2 and 12 | base handler `0x0082d054` | state 0: the data float, the fall, motion `0x1a` at 6.0, `0x0093cd70`; state 1: `0x0093ce60`, the data float, the `0x0083369c` test, mode 3, motion `0x1d`; state 2: the flag, motion `0x2e`; state 3: the flag, mode 0, motion `0x41` at 0.0; state 4: the flag, then 0/2's base handler |
| 3/4 | handler `0x0068dc60` | state 0: the data float, the fall, `0x00832690`, motion `0x1f` at 0.0; state 1: the attack (blocked), the angle to the target, the scaled heading difference turned at 0.04, then the part check `0x0084e74c` with parts `0x23`/`0x24`, the speed at `this+0x278` and the rate at `work+0x3d0` |
| 3/5, 3/9, 3/14, 3/22, 3/23, 3/26, 3/30 | handler `0x0068dd78` | entry: `0x0083d18c`, `0x0083db24` for variants 3-6 (blocked), the 0x687efc point; state 0: the records (blocked), `0x008437f4`, the data float and the turn; state 1: variant 1's sub-machine first, then the common tail: `0x008438e8`; when it parts, the second record and the turn, else the variant step (0 and 2: the fall and the immediate 3/11; 1: the next 3/9 or 3/10; 3-6: the tail flag's immediate 3/… or the hit setup and the next 7/…) |
| 3/10 | case block `0x0069983c` | `0x0083d18c`, the shared state 0, then the flag and 0/3's base handler |
| 3/11 | case block `0x0069987c` and tail `0x0083b424` | state 0: the data float, the fall, the request for motion `0x1f` at 4.0, the 60.0 timer; state 1: the countdown, then the data float, the fall, the immediate 3/11 and the set byte |
| 3/15 | inline block `0x00699964` | `0x0083d18c`, the shared state 0, then state 1's turn by 0x180, the flag and 0/3's base handler |

**The 3/5 pair's field map.** The map flags the 3/5 pair as misaligned, so these rows were
read by hand against MH4U's own 3/5 handler (0x006d5e98), where the same role sits at the
aligned step:

| MH4U | 3U | What | How |
|---|---|---|---|
| `+0x1ee` | `+0xf4` | the byte that must be zero before the 3/5 loops | the pair's state-1 variant 1 opens on it (`0x6d616c`) |
| `+0x520` | `+0x944` | the u16 the loops compare with 0x12c | the pair's `0x92e960`/threshold step (`0x6d61cc`) |
| `+0x202` | `+0xaec` | the byte 3/5's variant 1 compares with `work+0xdb` | the pair compares `+0x202` with `+0x14c` (`0x6d6444`) |
| `+0x27c` | `+0x2b6` | the part byte the hit setup reads | the pair tests `+0x27c` against 0xff (`0x6d6560`), settling the map's `+0x278`/`+0x27c` choice for this handler |

**The engine calls this slice adds**, each the MH4U counterpart at the same point:

| MH4U | 3U | What | How |
|---|---|---|---|
| `0x0094e318` | `0x00828828` | start a motion; the source's r2/r3 are s0/s1 | the 73 and MH4U's own 3/0, 3/1 and 3/5 |
| `0x00916228` | `0x0082fc8c` | clear the aim point A | the 73 and MH4U's own 3/0 |
| `0x0091656c` | `0x00839514` | the turn/advance wrapper | MH4U's own 3/0, 3/1 and 3/5 call it at the same point; the 73 also names `0x0091b430` as a body match of the wrapper, but that one carries no r2 mode argument |
| `0x0091db4c` | `0x008357b0` | turn toward the target by a step | the 73 and MH4U's own 3/0 |
| `0x0092b140` | `0x0084134c` | set an action immediately, kind 1 | the 73; MH4U's own 3/5 passes the same 3/… pairs |
| `0x00935a90` | `0x0084dc84` | set an action immediately, kind 2 | the 73; MH4U's own 3/5's 3/11 step |
| `0x0094ef64` | `0x0082a06c` | request the next action | the 73; MH4U's own 3/5 passes the same 7/… and 3/… pairs |
| `0x00922ca0` | `0x0083d18c` | set the work+0x3e3 byte | the 73; the pair's first step |
| `0x0092dccc` | `0x008438e8` | the 3/5 "may advance" predicate | the 73; the pair's step |
| `0x0092dc50` | `0x008437f4` | the 3/5 action-start call (0x19, s0) | the 73; the pair's step |
| `0x00947d0c` | `0x008565d8` | the same loop | the 73 |
| `0x00939988` | `0x0084c1ac` | the same end step | the 73 |
| `0x0093cd70` | `0x008509a0` | 3/2's state-0 end step | the 73; MH4U's own 3/2 |
| `0x0093ce60` | `0x00850a50` | 3/2's state-1 opening step | the 73; MH4U's own 3/2 |
| `0x00942220` | `0x0083369c` | 3/2's hold/fall test; the data float is its s0 | the 73's row; MH4U's own 3/2 calls `0x0093e4b0`, the same test at the same point, and `0x00942220` is its variant that also reads `work+0x628` |
| `0x00918e48` | `0x00836c04` | turn by s0 at s1's rate | the map pair; MH4U's own 3/4 |
| `0x00568c64` | `0x00584cd8` | the angle from dx/dz (s0/s1) | the 73; MH4U's own 3/4 builds the same x/z difference |
| `0x00aacd84` | `0x00585f30` | the squared distance between two points | identical bodies |
| `0x0092e960` | `0x00844100` | the state 2/3 predicate | the map pair |
| `0x00918ef0` | `0x00832690` | advance the aim point A | the 73; MH4U's own 3/4 |
| `0x00935fb8` | `0x0084e74c` | the part check: parts r1/r2, the speed as s0, the rate as s1 | the 73; MH4U's own 3/4 maps the source's r3 (the int speed) to s0 and its s0 (`work+0x3d0`) to s1 (`work+0x394`) |
| `0x0092e4f8` | `0x0083d1a4` | the per-action flag | the 73; MH4U's own 3/5 |
| `0x00916b94` | `0x0082ffbc` | the hit setup, r1-r3 and the fifth argument on the stack | MH4U's own 3/5 calls it with the source's (0, 0, 0), (5, 9, 0) and (0xb, 9, r6) and a zero stack argument; the 73 names `0x00935f8c`, its re-encoding wrapper, which does not take the source's r2/r3 |

**What this slice leaves blocked** (each logged once, the first time it is reached):

- **#55's 0x0083db24, 0x00833234, 0x00835f10, 0x0083dc14 and 0x00a347bc** in the 3/5 family:
  the entry byte, the two monster-list loops, their state test and the point mapping. A
  blocked call answers 0 ("nothing found"), and the point keeps its generic `0x1b`/`0` entries.
- **0x00842a7c**, 3/4's hit resolution, also on #55's 28 list. The angle and the part check
  after it still run.
- **The action-start record readers 0x0084704c and 0x00847134** (#135's rebuilt record).
  They take MH3U's 0x00b0b168, which is source-image data; the module carries no rebuilt copy,
  so the calls are named and skipped and the 3/5 ids still play their remaining calls.
- **The value curve 0x0083c6e0 with MH3U's 0x00c4ed80** in 3/0 and 3/1. The curve is source
  data and no rebuilt curve ships with the module, so the call and the A.y store that reads
  its result are skipped.

The family's fake-host test is `tests/rathian-3u/cat3.c` (`tests/family-cat3`). It drives each
unit's states and checks the frame values, the call order and the arguments, that no blocked
source address is called, and that each blocked one is logged.

#### Category 3's part 2 (#220)

`cat3b.c` translates sixteen of her ground ids on five handler units: `0x0068e448` for 3/6,
3/13 and 3/16; `0x0068e5e8` for 3/7, 3/17 to 3/19, 3/24 and 3/28; `0x0068e6e4` for 3/12,
3/20, 3/21, 3/25 and 3/29; `0x0068e8c8` for 3/27; and 3/8's base-class `0x0082b37c`,
reimplemented under 0002's second amendment. It reuses `cat0.c`'s `mhuc_3u_base_0_3` and
`mhuc_3u_base_0_2`; the reference page's
[category 3 part 2 table](../../reference/README.md#the-category-3-part-2-units-220) lists each
unit's states and ids.

The argument translations the engine calls need: 3U's turn rates 0x200, 0x100 and 0x80 are
halved for MH4U's `0x0091db4c`, `0x0092fc84` and `0x0092dccc` (3U's `0x8392d8` halves a rate,
MH4U's `0x0091aaf0` does not), and `0x82b268`'s s0 = 1.0 becomes 0.5 (`0x00955440` has no 0.5
factor). `0x8310f0` has no MH4U function: the port writes work+0x3c4, the offset MH4U's own
3/8 handler stores it at inline. The 3/6 value curve is MH4U's own 3/6 curve `0x00fd18a0`,
whose keys equal 3U's `0x00c4eca8`.

Two calls #55 still blocks are reached and each is logged once per action:

- **`0x0064325c`** (3/6 and 3/16, the r1 = 0 branch; 3/13 takes target z + 1300): the
  per-monster height through work+0xdb. The port skips it and takes its result as 0.0, so the
  height target is the vertical limit + 2000.0 until #55 settles it.
- **`0x00839598`** (3/8's state 4): the signed byte at 3U work+0xef. The port takes the
  source's nonzero path and ends the action in 0/3's base handler, so the move cannot stall.

The family's fake-host test is `tests/rathian-3u/cat3b.c`.

#### Categories 8 and 11 (#225)

`cat8.c` translates her one category-8 id on its handler `0x00687074`, whose MH4U action pair
is MH4U's own 8/0 handler `0x006e9770`. Under 0002's amendment the port runs the source's
handler with the source's values, all three of MH4U's own 8/0 values replaced where 3U's
differ: the aim at 300.0/38.0, the distance test at 12.0/50.0, a 90.0 timer, motion `0xca` at
90.0, the hit check at 300.0/0.0/150.0, then the request for 9/1 or 2/6.

| State | What the module runs |
|---|---|
| 0 | state byte 1, sub-state 0, mode 0, the action-start data setup (`0x00911c0c` with MH4U's list and the fifth stack argument), the aim (`0x00948674`) at 300.0/38.0, then the blocked `0x00257628` |
| 1 | the 12.0/50.0 distance test (`0x0091aae4`, r1 = 3); when it holds, the position advance by 0.5 (`0x00955440`) and the action-start leaf (`0x0092f6e8`); on the finish flag, state 2, the 90.0 timer at work+0x1d4 and motion `0xca` at 90.0 (`0x0094e318`) |
| 2 | the countdown (`0x00b0704c`) with the timer clamped at 0; the blocked `0x00839598` (taken nonzero); the hit check (`0x009122fc`, 300.0/0.0/150.0) or 2/6 when it fails; the blocked `0x0084512c` (taken nonzero); the tail flag 3, the part step and the request for 9/1 |

3U's motion call also passes r2 = 4, which MH4U's wrapper `0x0094e318` fixes at 0 before its
own player; the port goes through that wrapper, so the source's r2 is left out and the motion
number and speed are the source's.

Three calls into her class's own helpers are translated with the MH4U functions MH4U's own
8/0 and 9/0 handlers call at the same points: `0x0068d070` (the aim) is `0x00948674`;
`0x00687ae0` (the hit check) is `0x009122fc`; and `0x0068d940` (the part/effect step) is the
block `0x0092e960`, then `0x00944c34` at -900.0 or `0x0091b7b0` at 0x32, then `0x0093b9ec`,
whose input is `(int16)(work+0x3ec x 0.015)` (3U work+0x7fc, the same count). `0x0083c7a0`'s
inner guard `0x008532a0` has no confirmed MH4U counterpart; the accumulator runs without it, as
it does in MH4U's own handlers (`0x0093b9ec` is MH4U's own 9/0 call; its 8/0 uses `0x0093ba88`,
the same clamp with its delta step).

`cat11.c` translates her five category-11 ids. Every case block passes a source list, a mode in
r2 and the action index in r3 to the shared handler `0x008326dc` (a veneer to `0x008326e0`),
then falls into the base-class handler `0x0084d864`. MH4U's counterpart of the shared handler
is `0x00919788`, which MH4U's own category-11 case (`0x006e9d9c`) runs with its own list
`0x00fd2360` and the same mode; the source's r3 is ignored by `0x008326e0`. The source's lists
(`0x00c4d800` for 11/0, `0x00c4d818` for 11/5, `0x00c4d850` for 11/15, `0x00c4d868` for
11/26 and `0x00c4d880` for 11/28) are her data and are not carried, so the port passes MH4U's
own list. 11/5 is the one id that passes mode 1; the other four pass mode 0.

| Id | Source | What the module runs |
|---|---|---|
| 11/0 | wrapper `0x00687e6c`, shared handler `0x008326e0` | `0x00919788` with MH4U's list and mode 0, then `0x0084d864`, which returns at its index test |
| 11/5 | wrapper `0x00687e7c`, mode 1 | `0x00919788` with MH4U's list and mode 1, then the same tail |
| 11/15, 11/26 | wrappers `0x00687e98`, `0x00687ea8`, mode 0 | `0x00919788` with mode 0, then the same tail |
| 11/28 | wrapper `0x00687eb8`, mode 0 | `0x00919788` with mode 0, then `0x0084d864`'s own branch: the index 0x1c and mode gates, the blocked `0x00a37b3c` (taken nonzero), the 45.0/0.5 step on this+0x1a64, and the blocked `0x008477bc` above 45.0 |

The base-class handler `0x0084d864` is reimplemented here under 0002's second amendment. Only
11/28 goes past its first test; the other four ids end after the shared handler. Three parts of
11/28's branch have no mapped MH4U field or counterpart and are named in the module's log:
`0x00a37b3c` (bit 4 of the halfword at this+0x22e) is left out and its nonzero path taken;
this+0x1a64 (3U work+0x1c) has no confirmed MH4U offset, so the port keeps it at MH4U's
work+0x1c as a stopgap; `0x008477bc` (the record's +0xa0 effect/attack step) is left out, so
the step above 45.0 does nothing.

The two families' fake-host tests are `tests/rathian-3u/cat8.c` and
`tests/rathian-3u/cat11.c`. Neither family falls into category 0's three base handlers.

### 3U Rathian's module: category 7, part 1

Category 7's first slice is `cat7a.c`, issue [#221](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/221):
seven handler units on 21 ids. The class (`uEm002`) shares them with Rathalos and the
colour variants (MH3U ids 1, 2 and 62 to 65), and some branch on the work block's +3 (MH4U's
+0x1c0). The ported monster is em001, id 1, so the branches only ids 62, 63 and 65 take are
the class's colour-variant attacks and are not carried; the source's own id-1 path is. The
action variant the case block passes (0, 1, 2 …) is kept, and it selects a motion, a speed, a
timer or a tail in five of the seven units.

| Id | Source | What the module runs |
|---|---|---|
| 7/0, 7/77 | handler `0x00693468` | state 0: state byte 1, mode 0, motion 0x2f at 4.0 and the tail steps 0,1 and 1,9; state 1 (id 1): the finish flag, then 0/2's base handler. The colour variants' extra timers and their `0x00842a7c` call are not carried |
| 7/1, 7/20, 7/42 | handler `0x00693be8` | state 0: state byte 1, mode 3, the id-1 order step `0x008345f8(-14)`, motion 0xd1 at 6.0; state 1: the vertical step -6.6666665 (halved), the -200.0 speed floor, a `0x100` turn, the 50.0 check; state 2: -200.0, the aim advance, the 110.0 clamp, the landing step, then variant 0's motion 0xd2 and -3.0 aim, variant 1's mode 0, motion 0xdd and speed 0, or variant 2's motion 0x35 at 10.0; state 3: variant 0's 20.0 timer drive into 0/6, variant 1's motion 0xda then a 30.0 check into 0/2, variant 2's 10.0/5.0 timer and motion 0x3c into 0/2 |
| 7/2, 7/10, 7/11, 7/15 | handler `0x00694180` | state 0: mode 0, the order step except for 7/15, motion 0x33 at 6.0; state 1: the 2.0, 12.0, 36.0 and 78.0 checks, the first three spawning effect types 3, 1 and 1; 7/15 adds the source curve's rate step |
| 7/4, 7/12 | handler `0x006944b8` | state 0: mode 0, motion 0x32 (7/4) or 0x31 (7/12) at 4.0 and the tail steps 0,c1,8 and 1,c2,0x18; states 1 and 2: the turn by ±0x8000 over 0..120, the tail step 1,c3,0x10 once while work+0x6 and work+0xb81 are clear, and the finish flag into 0/2 |
| 7/5, 7/61 | handler `0x00694694` | state 0: mode 3, the order step, motion 0xce at 10.0 and the 0,0x1b tail; state 1: the one-shot reset, the 200.0 check and the (A-200)/(B-200)·-150 speed; when the flag sets, 7/61 goes to 0/6's base while 7/5 starts motion 0xcf and waits a second state for 0/2's |
| 7/6, 7/7, 7/16, 7/19, 7/32, 7/85 | handler `0x00694840` | state 0: mode 0, the order step, motion 0x8 at 4.0 and the tail step 0,5,3, then the variant's blend (-300, -900, -300, -300, -2000 or -600; 7/6 arms a 20.0 timer, 7/16 clamps work+0x2a8 at 1000.0); state 1: the timer countdown, the landing step with 0x80 for 7/6 and 7/85 (0x40 otherwise), then motion 0x9 or 0x40/0x30, or 7/32's apply 4/7; state 2: the 36.0 (7/16: 120.0) check and the 0,0xd tail, then 0/2 |
| 7/8, 7/34 | handler `0x00694bf4` | state 0: mode 0, the order step, motion 0xd0 at 4.0; state 1: the 2.0, 12.0 and 36.0 effects, then the 78.0, 120.0 and 164.0 structure builds whose target check is #55's; 7/34 adds the source curve's rate step |

**The field map rows this slice adds.** The category-0 rows above apply. These are new:

| MH4U | 3U | What | How |
|---|---|---|---|
| `+0xca5` | `+0xb81` | the second gate byte `0x006944b8` reads beside +0x6 | MH4U's own 7/4 handler (`0x006dfd54`) reads `+0xca5` where the source reads `+0xb81` before the same conditional `0x0093310c` step |
| `+0x238` | `+0x2a8` | the float 7/16 clamps at 1000.0 | MH4U's own 7/6 handler (`0x006e01e0`) clamps `+0x238` at 1000.0 where the source's 7/16 clamps `+0x2a8` |

The other rows the family reads are the map's: +0x5/+0x6 → +0x144/+0x145, +0x28 →
+0x1d4 (3U's saved +0x2c is not kept; MH4U's countdown has one field), +0x68 → +0x180,
+0x80/+0x84 → +0x1a8/+0x1ac, +0x268/+0x278 → +0x168/+0x178, and the object speeds
3U this+0x278/+0x27c → MH4U this+0x290/+0x294. The source's timer steps read the frame delta
through 3U's work+0x30 pointer; MH4U has no such pointer, so the module reads its own
this+0x14 (the map's row).

**The engine calls this slice adds**, each the MH4U counterpart at the same point:

| MH4U | 3U | What |
|---|---|---|
| `0x0094e318` | `0x00828828` | start a motion (`r1` the motion, the source's `r2` speed in `s0`) |
| `0x00915d44` | `0x00833b2c` | advance the vertical value (the source's -6.6666665 is passed halved, -3.3333333, as 3U's helper halves it and MH4U's does not) |
| `0x00916108` | `0x00833d88` | set the speed |
| `0x00911090` | `0x00834098` | advance the aim point by the aim vector |
| `0x0091db4c` | `0x008357b0` | turn toward a target point |
| `0x0091aae4` | `0x0083336c` | the per-mode distance check |
| `0x0092dccc` | `0x008438e8` | the landing step |
| `0x0092dc50` | `0x008437f4` | the vertical blend filter |
| `0x0090f8fc` | `0x0082c1c4` | clear an action slot by index |
| `0x0093310c` / `0x00914dc4` | `0x00844a40` / `0x00844a38` | the per-slot tail step, with `r3` 0 in the second |
| `0x0091b7b0` | `0x008345f8` | the order/phase step; the ported id is 1, whose wrapper passes -14 |
| `0x00917570` | `0x00850860` | turn by an angle step (`r1` the step, `s0`/`s1` the 0..120 range) |
| `0x0096e164` | `0x00839968` | clear the aim point and vector |
| `0x0092b140` | `0x0084134c` | apply the next action pair (7/32's 4/7) |
| `0x00c0760c` | `0x0015f410`, `0x00164f08` | the effect factory, with the source's type moved from 3U's `r2` to MH4U's `r1` |
| `0x00922c40` / `0x00922ca0` | `0x0083cbfc` / `0x0083d18c` | store a rate / set the one-shot byte |

**What it does not carry.** The family's blocked or source-data calls are named once in the
log and recorded here:

- **`0x0084161c` (#55)** is 7/2's and 7/8's effect target check. Its call is named and
  skipped, and the effect structure behind it with it.
- **`0x00688a20` and its spawn `0x00829950`** build the attack structure the target check
  reads. The structure is the source's data and `0x00829950` calls `0x0063cabc` and
  `0x008890f0`, which have no MH4U counterpart read here, so the structure is not built and
  the spawn is skipped. The 78.0/120.0/164.0 checks themselves still run.
- **`0x00842a7c` (#55)** is only reached from `0x00693468`'s id 0x3e/0x3f branches, the
  colour variants' attacks. The ported id's byte is 1, so the port makes no call. The same
  goes for the variant branches' `0x0063e4ac` shell spawns and the source's `+0xdb` selector.
- **`0x0083c6cc` (#55)** is not called by this slice's units; it is other category-7 ids'
  helper.
- **The source's value curves `0x00b0b1c0` and `0x00b0b1e8`** (7/15 and 7/34) are the
  source's data, which the port does not carry, so the timing value their evaluation
  supplies and the `0x0083cbfc` call that takes it are skipped.

The module's ready line sums the families' counts — `ready: translating 58 of 3U Rathian's
191 actions on monster 125` with cat0, cat1, cat3b and this slice — and the family's
self-test logs the seven units, the two field-map rows and the blocked calls. The 125 quest's run reuses check T1c; the per-move rows are #116's.

### 3U Rathian's module: category 13, part 1

Category 13's first slice is `cat13a.c`, issue
[#227](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/227): five handler units
on five ids. The category entry `0x00699b78` switches on the index (0 to 9) and tail-calls
each unit; the units ignore the case block's registers, so the family claims them by the
pair. The units branch on the work block's id byte (`+3`, MH4U's `+0x1c0`) in 13/0, 13/2 and
13/4; the ported monster is em001 (id 1), so the port carries the source's id-1 path.

| Id | Source | What the module runs |
|---|---|---|
| 13/0 | handler `0x0068eabc` | state 0: state byte 1, the data float and the fall it advances, motion 0x1a at 10.0, the rate, the 300.0 timer; state 1: the height above the target (position y - target y), the 3500 rate or the +10.0 step at or below 2000, the timer countdown, the 0x180 turn, then the request for 13/1 |
| 13/1 | handler `0x0068eca4` | state 0: state byte 1, the data float and the fall, motion 0x3d at 6.0, the aim reset, aim A z -20.0 and aim B z 0.5; state 1: the aim step, the vector's heading and pitch, the 0x100/0x40 turns, then motion 0x3e at 6.0, aim A y -2.0, aim B z 0.5 and the -2500.0 blend; state 2: the 0x80 landing step, motion 0x2d at 6.0 and aim A y -15.0/aim B z -6.2, or the 130.0 aim clamp; state 3: the 30.0 query, the aim step, the flag and then 0/3's base handler or the request for 13/2 |
| 13/2 | handler `0x0068f0fc` | state 0: state byte 1, mode 3, motion 0xc8 at 20.0, the (0, 0xb) tail, the aim reset, speed 0, the distance/450 target-line factor clamped to [1.0, 3.8] and the target-line step; state 1: the two value curves, the halved vertical step, the -50.0 speed floor, the aim step, the 36.0 query and the 0x100 turn; state 2: the 30.0 query, the signed work+0xef byte and the two-entry target loop, then 13/3 or 1/3 |
| 13/3 | handler `0x0068f424` | state 0: mode 0 and the aim at the target at 300.0/38.0 (the source's action-start record is not carried); state 1: the 12.0/50.0 query, the 38 - (speed - 12) aim range, the 0.5 position advance and the record's leaf, then motion 0xca at 4.0; state 2: the signed work+0xef byte and the target loop, then 13/4 or 2/6 |
| 13/4 | handler `0x0068f66c` | state 0: mode 0, motion 0xcb at 4.0 and the 4.0 timer; state 1: the flag, the timer crossing test (the source's saved `+0x2c` and the frame delta through `+0x30`), the state predicate and the 1000/200 order step, then the request for 13/2 |

**The field-map rows.** The slice adds no confirmed row: it reads the map's state, mode,
timer, position, heading, aim, target and speed rows, the id row `+3` -> `+0x1c0`, the
selector `+0xdb` -> `+0x14c` the earlier slices found, and `+0x7c9` -> `+0x3c4` (13/1's
`0x8310f0`). 3U's `+0x1c`, `+0xda` and `+0xaea` stay in the map's "what is not mapped":
`+0xda` is the index 13/0, 13/1 and 13/2 hand to the blocked `0x00a347bc`, and `+0xaea` is
13/0's second selector, reached only through that blocked lookup. 3U's target-line struct at
`this+0x1e70` is MH4U's `*(this+0x8d88)`.

**The engine calls this slice adds**, each the MH4U counterpart at the same point:

| MH4U | 3U | What |
|---|---|---|
| `0x0093ce60` / `0x0093cd70` | `0x00850a50` / `0x008509a0` | 13/0's height rate and state-0 rate |
| `0x00948548` | `0x005bde78` | 13/2's target-line step; MH4U's own 13/2 calls it at the same point |
| `0x00948674` | `0x0068d070` | the class's aim-at-target-with-lead; MH4U's own 13/3 calls it with aim A at `+0x160` and the target at `+0x218` |
| `0x00568c64` | `0x00585384` | the vector's heading and pitch; MH4U's own 13/1 calls the same helper twice |
| `0x00aacd50` | `0x005858f4` | the distance in x/z; the third float `0x00845004` takes in s2 is why the port reproduces its step with this call |
| `0x0091b430` | `0x00839ea0` / `0x00839514` | the aim step and the vertical clamp |
| `0x0091aaf0` | `0x008392d8` | a turn by an angle step; the source's rates 0x100 and 0x40 are halved |
| `0x0092dc50` | `0x008437f4` | 13/1's blend (`0x12`, -2500.0) |
| `0x0092dccc` | `0x008438e8` | 13/1's landing step (its 0x80 halved to 0x40) |
| `0x00955440` | `0x0082b268` | 13/3's position advance (the source's 1.0 becomes 0.5) |
| `0x00922250` | `0x0083c6e0` | 13/2's two value curves; 3U's 0x00c4edb8 and 0x00c4ee00 were compared key by key with MH4U's own 0x00fd19b0 and 0x00fd19f8 and are equal, so MH4U's evaluator reads MH4U's tables |
| `0x00916228` | `0x0082fc8c` | 13/1's state-2 entry step |
| `0x0092e960` / `0x0091b7b0` | `0x00844100` / `0x008345f8` | 13/4's state predicate and order/phase step |
| `0x00914dc4` / `0x00916108` | `0x00844a38` / `0x00833d88` | 13/2's (0, 0xb) tail and speed 0 |

**What it does not carry.** The calls are named once in the log and recorded here:

- **`0x00a347bc` and `0x00843c20` (#55)** are 13/0's, 13/1's and 13/2's entry gate: the
  uCharacter table lookup of 3U work+0xda (which has no MH4U offset) and the scale/one-shot
  pair behind its 0xc result. The port takes the source's non-0xc path; 13/0's second
  lookup, its `+0xaea` selector and 13/1's special flag are skipped with it.
- **`0x00839598` and `0x00835f10` (#55)** are 13/2's and 13/3's state-2 target loop: the
  signed 3U work+0xef byte and the uEm066 position helper (called twice with the entry byte
  0x1b, 700.0 and 350.0). The port takes the byte's nonzero path and the helper's result as
  0, so the source's failure request runs (1/3 in 13/2, 2/6 in 13/3) and the move cannot
  stall.
- **`0x0085162c` and `0x00829620` (#55)** are 13/4's entry (the float at the monster's
  `+0x97c`) and per-frame action-table helper. Both are skipped.
- **13/3's action-start record `0x00b0b0e8`** is the source's data, not carried; its setup
  `0x0082d278` and leaf `0x0082d430` are not called, so the port's MH4U counterpart
  `0x00911c0c` is not run with the source's table.
- **`0x0084512c`** is not reached by these five units: it is 8/0's unit `0x006870f4`.
  `0x00829620` is reached by 13/4 only. The issue's list groups them with 13/1, but the
  source's 13/1 does not call either.
- **The aim wrappers' two floats.** 3U's `0x00839ea0` and `0x00839514` take the aim step in
  s1 (1.0) and the clamp factor in s0; MH4U's `0x0091b430` takes one float and passes it to
  both workers. The port passes the source's s0 (the clamp factor, the value MH4U's own 13/1
  passes) and the heading slot at r1.
- **13/4's timer.** 3U saves the old value at `+0x2c`; MH4U keeps one value at `+0x1d4`, so
  the crossing test uses a local copy of the old value and MH4U's frame delta at this+0x14.

The family's fake-host test is `tests/rathian-3u/cat13a.c`. The module's ready line sums the
families' counts — `ready: translating 63 of 3U Rathian's 191 actions on monster 125` with
cat0, cat1, cat3b, cat7a and this slice — and the family's self-test logs the five units and
the blocked calls. The 125 quest's run reuses check T1c; the per-move rows are #116's.

### 3U Rathian's module: category 7, part 2

Category 7's second slice is `cat7b.c`, issue [#222](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/222):
five handler units on 22 ids. The class (`uEm002`) shares them with Rathalos and the colour
variants (MH3U ids 1, 2 and 62 to 65); the ported monster is em001 (id 1), so the branches
only the variants take are not carried and the source's own id-1 path is. The action variant
the case block passes (0 to 6) is kept, and it selects a variant, a motion, a speed or a tail
in four of the five units.

| Id | Source | What the module runs |
|---|---|---|
| 7/3, 7/41, 7/43, 7/44, 7/53, 7/54, 7/55, 7/56, 7/72, 7/73 | the veneer `0x00694474` -> `0x00687398` | the six-state flight machine: state 0 mode 0 and motion 0xd6 at 4.0; state 1 the 0x400 turn for selectors 2, 4 and 5, the finish flag, mode 3, speed 50.0, motion 0xd7, the extra step, the (blocked) speed curve and the aim advance; state 2 the 6.0 check and the selector's blocked point/effect spawn, then the flag into the substate, the aim-vector z 0.5 and motion 0x1b, or the blocked curve and the aim advance; state 3 the aim step, the aim-z clamp, and the flag into 0/2's base (r1 = 0) or 0/6's (r1 = 1), or the substate's motion 0x1b/0xd8; state 4 mode 0 and motion 0xd9; state 5 0/2's base |
| 7/9, 7/14, 7/30, 7/80, 7/83, 7/88, 7/89 | `0x00694f4c` | the seven-variant machine: the work-block flag 0x20 every frame; state 0 mode 0, the id-1 run flag -14 and motion 0xcd at 6.0 (variants 3 to 6: motion 0xe1/0xe3 at 0.0); state 1 the flag into motion 0xce, the 0,7 pair, the extra step and the two second speeds (variants 3 to 6: the 398.31 fall step, motion 0xe2/0xe4, the 0,0x26 pair and the unmapped u16 copy); state 2 the (blocked) curve, the turn step, the mode checks and the per-mode step, then variant 0's motion 0xcf, variant 1's motion 0x1b, variant 2's motion 0xd2, variants 3/4's motion 0x1b and set byte, variants 5/6's state advance into 0xcf (variants 3 to 6 also the blocked 0x00842a7c, curve and effects); state 3 variant 0/5/6 into 0/2, variant 2's motion 0xcd at 70.0 (the source's own r3 = 0x46), variants 1/3/4's vertical step into 0/6; state 4 the advance block; state 5 the turn/mode-check/per-mode path into 0xcf; state 6 into 0/2 |
| 7/13 | `0x006956e8` | state 0 mode 0, the run flag -14, motion 8 at 0.0, the 0,5,2 pair and the -300 turn step; state 1 the 0x40 turn condition into motion 0x2f, the 0,1 and 1,9 pairs; state 2 the flag into 0/2. Its colour-variant effect and shell spawns are not carried |
| 7/17, 7/78 | `0x00695e68` | the entry's -5.0 vertical step and -75.0 clamp; state 0 mode 3, the run flag, motion 0x36 at 4.0, the 0,0xc pair, the camera step and the distance/angle speed into the aim z; state 1 the 60.0 check, the 0x40 turn and the aim advance, then the flag into 0/6 |
| 7/18, 7/21 | `0x00696408` | the entry's -5.0 vertical step and clamp; state 0 mode 3, the run flag, motion 0x37 at 4.0, the 0,2 pair, and for 7/21 the extra step with the 20.0/-0.5 aim; state 1 the flag into 0/6 |

**The field map rows this slice reads.** They are the map's: +0x5/+0x6 -> +0x144/+0x145,
+0x3 -> +0x1c0, +0x68 -> +0x180, +0x80/+0x84 -> +0x1a8/+0x1ac (the heading is a u16 angle,
as MH4U's `0x0091db4c` stores it), +0x264/+0x268/+0x278 -> +0x164/+0x168/+0x178, +0x38/+0x288
-> +0x198/+0x218 (the two points), +0xf2 -> +0x1dc, and the object speed 3U this+0x284 ->
MH4U this+0x29c (`0x0083c6cc`'s second speed, read as the map's row pairs it). One field has no
row: **work+0x140**, a u16 `0x00694f4c` copies into the target-line struct's +0x6a on the
7/80-family state 1. MH4U's own 7/80-family handler has no such step and no pair reads the
field, so the copy is left out and logged.

**The engine calls this slice adds**, each the MH4U counterpart at the same point:

| MH4U | 3U | What |
|---|---|---|
| `0x0094e318` | `0x00828828` | start a motion (`r1` the motion, `s0`/`s1` the speed; 3U's wrapper ignores its caller's floats, so the value is MH4U's own handler's at the same step, or the source's r3 where it sets one) |
| `0x009167b4` | `0x0082fe88` | the mode setter |
| `0x00b05da4` | `0x0083cbf4` | the finish flag |
| `0x0091db4c` | `0x008357b0` | turn toward the target (`r2` 0) |
| `0x0091b430` | `0x00839ea0`, `0x00839514` | the turn wrapper (slot, `s0`, `s1`) |
| `0x0091aae4` | `0x0083336c` | the per-mode check |
| `0x00942220` | `0x0083369c` | the per-mode step |
| `0x00911090` | `0x00834098` | advance the aim point by the aim vector |
| `0x00912288` | `0x0082cee4` | advance the position by a speed vector |
| `0x00916108` | `0x00833d88` | the speed 50.0 |
| `0x0093d870` | `0x00852324` | the action data's float |
| `0x0092e99c` | `0x00844124` | advance the fall |
| `0x0096e164` | `0x00839968` | clear the aim point and vector |
| `0x00915d44` | `0x00833b2c` | advance the vertical value (the source's -5.0 is passed halved, -2.5) |
| `0x00922ca0` | `0x0083d18c` | set the one-shot byte |
| `0x0092e960` | `0x00844100` | the state 2/3 predicate |
| `0x00914de0` | `0x00832670` | the work-block flag 0x20 |
| `0x0091b7b0` | `0x008345f8` | the run flag; the ported id is 1, whose wrapper passes -14 (the variants' values are -15, -10 and -7) |
| `0x00916228` | `0x0082fc8c` | the camera step |
| `0x00923f90` | `0x0083db3c` | the target's height |
| `0x00568c64` | `0x00584cd8` | the u16 angle from a point to a point |
| `0x00aacd50` | `0x005858f4` | the distance between two points |
| `0x0092dc50` | `0x008437f4` | the vertical blend filter |
| `0x0092dccc` | `0x008438e8` | the landing step |
| `0x0093310c` / `0x00914dc4` | `0x00844a40` / `0x00844a38` | the motion's parameter pair |

`0x0083c6cc` (3U's `this+0x284` times 2.0) and `0x0083b424` (the set byte at work+0xf2) are
not calls in the port: the first is the mapped field read, the second the mapped work+0x1dc
store. The two base handlers the flight machine ends in are `cat0.c`'s, reused (`0/2`'s for
r1 = 0 and `0/6`'s for r1 = 1).

**What it does not carry.** The family's blocked or source-data calls are named once in the
log and recorded here:

- **`0x00842a7c` (#55)** is `0x00694f4c`'s variant 3 to 6 state 2 and `0x00695e68`'s colour
  variant 0x41 state 1. It is named and skipped. `0x0084161c`, the other #55 call the
  category is known for, is not reached by this slice's units.
- **`0x0083c6e0` -> `0x00922250`.** The MH4U function has the same body, but the call takes
  one of the source's speed-curve tables (`0x00c4ee30`, `0x00c4ee70`, `0x00c4ef98`), which the
  port does not carry, so the call is logged and the aim coordinate keeps its value.
- **`0x00164f08`'s effect spawn**, with `0x00688a20`, `0x00688870` and `0x0063cabc`: the point
  comes from `0x00199d00` and `0x00829950`, which have no MH4U counterpart (the whole-code
  token index's best is 0.35), and the effect ids 0x17/2/4 and the manager are the source's.
  The factory's counterpart is `0x00c0760c` with the type moved from 3U's r2 to MH4U's r1, but
  without the point it is not called. The log keeps the source's point selector (0x1c72 for
  selectors 1 to 4, 0x1555 for 5 and 6) so a run says which path a move took.
- **`0x0063e4ac`'s shell factory** is only in the colour variants' branches (kind 0x3e, 0x3f
  and 0x41), which the ported id 1 never takes; it is not carried.
- **work+0x140 -> the target line's +0x6a** is unmapped, as above.

The module's ready line sums the families' counts — `ready: translating 85 of 3U Rathian's
191 actions on monster 125` — and the family's self-test logs the five units, the field
rows this slice reads and the calls still blocked.

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

## The Hunter's Notes list

MH4U's Hunter's Notes list is built from `monsterListOrder` (`0x00df35b0`): 124 rows of 8
bytes, byte 0 the monster id and +4 the message index of its name. The page builder
(`0x0061df4c`) takes a page in r0 and fills the page object at `0x01090868` (+0x30 the number
of entries on the page, +0x34 eight order positions, -1 for an empty slot); the page init
(`0x006191f8`) sets the page count at +0x1f7 of the notes UI object it gets in r0, and the
detail (`0x006234b4`) takes an order position and shows the id in that row through the message
getters. A row is listed when its name index is set in the bitset of the current message
string table, the same check the position getter makes for one id; rows 91 to 123 have no
name index, so the game's own count is at most 12 pages.

A ported id has no row, so the runtime wraps the page init and the builder: the init gets
`ceil(registered/8)` pages after MH4U's own, and the builder fills those pages from the
registry, setting each name through the game's own text widgets. The page slots are the
registered ids. The detail hook maps such a slot to its stand-in's order position, runs the
game's detail for that position (the page, the widgets and the transition), and then sets the
name and notes objects to the ported id, whose message getters above answer its own text.
Every page before the runtime's is MH4U's own and runs unchanged, so ids 0 to 123 keep their
rows and pages; nothing is written to the game's tables. The runtime's hook names are
`notesList::pages`, `notesList::page` and `notesList::detail` (`mod.json` gives their USA
v1.3.0 addresses, as the project's tables have no names for them).

The row's text is the text table's (above): a GU monster's row shows the registry's name and
the source game's notes, Japanese until MHGU's English text is read.

## What it does not do yet

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
- **The rest of the 3U module's 191 ids.** Only category 0 (six ids), category 1 (fifteen ids),
  category 3's part 2 (sixteen ids), category 7's part 1 (twenty-one ids), category 13's part
  1 (five ids), category 3's part 1 (fifteen ids) and category 0's three base handlers run;
  the other 113 ids are still owed, one family per slice
  ([#217](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/217) to
  [#229](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/229)) and action 4's
  ([#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136)). An id this slice
  does not carry goes to MH4U's dispatcher and is logged once, so a forced id that does
  nothing says so. The source's `0x008412cc` per-action value step is the one item the
  category-0 slice leaves open (#55); category 1's `0x0016052c` uEffect039 spawn and its
  three other effect calls are #55's too, and the moves play without their effects until
  #55 and [0015](../../docs/decisions.md#0015-carrying-a-source-effect-into-mh4u) carry them.
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
tools/check_ids.py --write` after changing the registry. Each monster's family list
(`src/monsters/<key>/families.h`) is generated at build time by `tools/gen_families.py`; the
Makefile's `FAMILY_KEYS` names the monsters whose actions are split, and each key's
`FAMILY_TAG` names its C symbols. It is not committed, and adding a family file is what makes
the next `make` rewrite it. Licence: GPL-3.0-or-later, like the rest of the mod.

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
| `selftest` | `0` | `1`: on the first frame, log what every reader answers for each registered id, the paths of the resource record built for it and which kinds and motion slots it ships and keeps the stand-in's for, the path the stand-in's data comes from, the name and notes text and the three message getters' answers, the notes list's own page for the registered ids, that ids 0 to 123 pass through, and a pooled id lent, answered and freed by a synthetic quest; then each module's self-test. The check in [checks.md](../../docs/checks.md#uc-runtime) uses it. |
| `monster` | `124` | The id a module's ready line names. A module answers the registry id it was built for, so this no longer chooses another monster (the old plugin's `monster = 1` translated her actions onto MH4U's Rathian; a module cannot, see [what it does not do yet](#what-it-does-not-do-yet)); the setting is kept so an old `config.ini` still loads, and the runtime warns when it names no module. |

## The check

The headless check and what it must show are in
[checks.md](../../docs/checks.md#uc-runtime).
