# In-game checks

Behaviour that only the running game can confirm. Checks against files alone live in each spec's *Checks* section and mostly run through `mhuc survey`.

Record a result as pass, fail or numbers, never as bytes from the game.

## Build and launch (end to end)

Needs the MH4U USA v1.3.0 update, the fork on `uc/main` and a C compiler.

1. Build the fork's sample plugin: `cc -shared -fPIC -Iinclude tools/plugin_sample/sample_plugin.c -o sample_plugin.so`.
2. Make a mod folder with that library and a `mod.json` that hooks `sMhPad::update`, then add it with the fork's `tools/mods.py add`.
3. `tools/build_game.py --dump <update> --install`. The build reports the mod's hooks and one native plugin.
4. Start the game. The log shows the plugin loaded, and the game reaches the save-data screen.
5. Remove the mod and build again. The plugin list is gone and the log has no plugin lines.

Last result: pass on 2026-11-23, Linux, headless runner. The port's own pad features were not covered, because the runner lacks them.

## Extra Data records

`mhuc extdata testkit <Extra Data folder> --key K --out kit/` builds the files for the three checks below, encrypted, with a `TESTKIT.txt` listing what to look for. Back up the Extra Data first and copy the files in with a save manager.

| Check | What | Pass |
|---|---|---|
| Q17 | a stored quest copied into an empty slot under a new id and title | the quest is listed and plays |
| Q19 | the same with a longer title, so the `.mib` builder lays it out again | the quest is listed with the new title and plays like the original |
| E4 | a DLC Palico renamed in `otomo1` | the Palico is shown with its new name |

Full steps: [specs/quest.md](../specs/quest.md) (Q17, Q19) and [specs/extdata.md](../specs/extdata.md) (E4). Status: open.

## Extra Data in the port

The checks above can run in the port instead of on a console, once this one passes.

1. Run the fork's `tools/extdata_path.py` on the USA v1.3.0 exheader. It prints the game's Extra Data id and where Azahar keeps the folder.
2. Start the game once with a fresh user folder and open the DLC menu. Pass: the folder exists and holds `quest1` to `quest5`, `otomo1`, `card1` to `card3` and `cardbox`.
3. Copy a console's Extra Data files there and restart. Pass: the downloaded quests are listed, as on the console.

Status: open.

## Local DLC server

| Check | What | Pass |
|---|---|---|
| D1 | point the DLC screen at a local server that answers the login with its own key and serves one quest encrypted with it | the game downloads and lists the quest, and its Extra Data slot reads back in the stored form |
| D2 | decrypt the server's `DLC_EventQuestInfo_eng.txt` list with the login key | its layout is written into specs/quest.md |

Status: open. goshawk documents the protocol but is AGPL-3.0, so a server here would be written from the protocol, not from its code.

## Monster actions

| Check | What | Pass |
|---|---|---|
| R1 | for every action id Rathian has in two or more of MH4U, MHXX and MH3U, compare the motion (animation) index each game's handler starts | the counts per pair and the ids that differ are recorded below |

The action dispatchers are the ones the inventory walks: MH4U `uEm001` vtable slot 44,
`0x006e9cac`; MHXX `roEm001` module offset `0x9704`; MH3U `uEm002` vtable slot 50,
`0x00687d30`. A handler starts an animation by calling its game's motion-start wrapper with
the motion index in r1: MH4U `0x0094e318` (`mov r2,#0; b 0x0091908c`), MHXX `0x008eb108`
(the same into `0x008b393c`), MH3U `0x00828828` (it tail-calls `0x0083771c`, which sets the
model's motion). The wrappers are engine functions of the base enemy class, so one address
serves every monster of a game.

How it was found: each wrapper is the routine the handler calls or tail-calls with a small
constant, and MH4U's and MHXX's are the same two instructions into their setters. For the
actions checked by hand (3/0, 3/17 and 7/5) the MH4U and MHXX handlers reach the same call in
the same place and pass the same index, while MH3U's handlers pass a different one;
`reference/monster_motions.py` then runs it over every action.

[reference/monster_motions.py](../reference/monster_motions.py) reuses
[monster_actions.py](../reference/monster_actions.py)'s inventory. For each action it scans
the handler, stepping over the inline jump tables and literal pools that stop a linear
disassembly, and takes the **first constant in r1** passed to the wrapper: the action's entry
motion. A handler that calls the wrapper only with a computed value is `computed`; one that
never calls it is `none`; an action whose work is inline is `no-handler`. Those three are not
compared. The run covers MH4U USA v1.3.0, MHXX v1.4 `roEm001` and MH3U USA.

| Game | Actions | Constant | Computed | None | No handler |
|---|---|---|---|---|---|
| MH4U | 342 | 240 | 0 | 67 | 35 |
| MHXX | 301 | 178 | 0 | 96 | 27 |
| MH3U | 191 | 132 | 0 | 50 | 9 |

| Pair | Common ids | Compared | Same index | Different index | Not compared |
|---|---|---|---|---|---|
| MH4U / MHXX | 273 | 167 | 167 | 0 | 106 |
| MH4U / MH3U | 174 | 117 | 2 | 115 | 57 |
| MHXX / MH3U | 145 | 84 | 0 | 84 | 61 |

The index says little about the motion: MH4U and MHXX pack a motion index as LMT file << 8 |
slot, MH3U as file * 100 + slot, and the LMT files group the animations differently.
Comparing the animation each handler starts (its frame count, loop frame and track count; the
MH3U version-66 files use the same animation header and track table as version 67 for this
comparison, while their keyframe encodings are still unlaid-out, specs/lmt.md) splits the
differing ids:

| Pair | Differing ids | Same motion, another index | Different motion | Not resolved |
|---|---|---|---|---|
| MH4U / MH3U | 115 | 93 | 3 | 19 |
| MHXX / MH3U | 84 | 67 | 3 | 14 |

The same-motion class is 86 exact signatures in MH4U/MH3U (64 in MHXX/MH3U), 2 with one extra
MH4U track (the skeleton, specs/mod.md), and 5 (3) whose handler's index decodes to an empty
MH4U/MHXX slot but whose animation is found at another index by its signature. The 3 different
are 13/5, 13/6 and 13/8 in both pairs: their frame or loop frame counts differ. The not-resolved
ids decode to an empty slot with no unique signature match; their handlers are category 7,
whose code is shared and can start more than one motion, so the first constant is not enough.

Different motion (both pairs, 3):

```
13/5 13/6 13/8
```

Not resolved, MH4U / MH3U (19):

```
7/36 7/38 7/39 7/40 7/49 7/50 7/51 7/52 7/59 7/60
7/62 7/66 7/67 7/68 7/69 7/70 7/74 7/90 7/91
```

Not resolved, MHXX / MH3U (14):

```
7/36 7/38 7/39 7/40 7/49 7/50 7/51 7/52 7/59 7/60
7/62 7/66 7/67 7/68
```

The other differing ids (93 and 67) are the same motion at another index. The per-id mapping
(action id, the two motion indices and the class) is written by `compare --mapping`; the motion
indices stay outside the repository.

Last result (2026-11-24): MH4U and MHXX start the same index for every one of their 167
comparable ids. The two ids whose index also agrees with MH3U are 1/11 and 1/12; the content
comparison above shows that the rest are mostly the same motion at another index, not different
moves. The not-compared ids are those where one side (or both) is `computed`, `none` or
`no-handler`; the run prints the reason counts. The port must map MH3U's motion indices (its
packing and LMT grouping), not reuse them; 13/5, 13/6 and 13/8 are the entries whose motion
itself differs.

To rerun, write the TSVs outside the repository (for example under `build/`):

```bash
python3 reference/monster_motions.py list --game mh4u --exheader <v1.3.0 exheader> \
    --code <v1.3.0 code.bin> --range 0x6d4f80 0x6ec8e0 --dispatcher 0x006e9cac -o build/mh4u.tsv
python3 reference/monster_motions.py list --game mhxx --module roEm001.cro --crs static.crs \
    --dispatcher 0x02009704 -o build/mhxx.tsv
python3 reference/monster_motions.py list --game mh3u --exheader <MH3U exheader> \
    --code <MH3U code.bin> --range 0x686000 0x69b000 --dispatcher 0x00687d30 -o build/mh3u.tsv
python3 reference/monster_motions.py compare build/mh4u.tsv build/mhxx.tsv
```

For the motion content, pass each game's LMT files in file order (MH4U/MHXX `_0` to `_4`,
MH3U `mot_em001_000`, `_100`, `_200`; extracted from the monster's archive):

```bash
python3 reference/monster_motions.py compare build/mh4u.tsv build/mh3u.tsv \
    --game-a mh4u --lmt-a build/lmt/em001_{0,1,2,3,4} \
    --game-b mh3u --lmt-b build/lmt/mot_em001_{000,100,200} \
    --mapping build/mh4u-mh3u-map.tsv
```

For another monster, change `--range` to its code (or `--module`/`--crs` to its MHXX
module); `--motion` overrides the wrapper if its class uses another one, and `--functions`
another function table.

### The plugin's check (R1p)

| Check | What | Pass |
|---|---|---|
| R1p | force action 3/17 on Rathian with `mods/force_action` | the log shows the plugin loaded and `forcing action 3/17 on monster 1`, and the forced move plays |

1. Build the code library with the mod enabled and add the mod to the port's library; the
   commands are in [the mod's README](../mods/force_action/README.md#install). The current
   `mod.json` adds the `uEnemy::setAction` hook (`0x0090ef74`), which is what makes the move
   play: a library built before that hook falls back to the dispatcher, logs a warning, and
   cannot beat the AI's per-frame reset.
2. In the installed mod's folder, set `action = 3/17`, `monster = 1` and `hold = 1` in
   `config.ini` (monster 1 is Rathian; the plugin reads the id at `work+0x1c0`).
3. Take quest 10212 from the Hall (Low Rank 2★) and go to area 3, where the Rathian is.
4. Start the quest. The log shows `plugin Force a monster action: ... ready: forcing action
   3/17 on monster 1 via the action setter`, then one `first force: monster 1 3/17 over ...`
   line, then one `setter` line per distinct call (current action, requested action, mode,
   caller) saying what the plugin did with it. If it says the action setter isn't a
   hook point, the code library needs rebuilding. A headless boot with the same library
   (`mh4u_runner` with `--code`, the update installed) already logs that `ready` line at
   start-up, which shows the hook is in the library; with no monster loaded there is no
   `first force` line.
5. Watch the Rathian: note the move and whether it plays to the end. The first session covers
   only the first row below; the others are not done, and are not recorded as passed.

| Row | What to watch | Status |
|---|---|---|
| 3/17, `hold = 1` | the move plays, not a frozen pose | passed (2026-11-25): one move, played over and over |
| 3/0, `hold = 1` | the move plays | not done |
| 7/5, `hold = 1` | the move plays | not done |
| 3/17, `hold = 0` | forced once, then the AI resumes | not done |
| 3/0, `hold = 0` | forced once | not done |
| 7/5, `hold = 0` | forced once | not done |

Result (2026-11-25, the maintainer, quest 10212, area 3): 3/17 with `hold = 1` passed on the
fourth try; the Rathian plays one move over and over. The three tries before it fixed the
plugin, and their logs are what the plugin's handling of the setter rests on:

- Forcing every setter call restarted the move each time: the game calls the setter about
  twice a frame (the monster's return to idle, then the AI's pick), so the move stayed on its
  first frame, sinking into the ground with only its start effect (sand) playing.
- Not restarting a running move was enough until the Rathian saw the hunter. With a target,
  the idle routine `0x0094dc84` runs every frame even while the forced move is current and
  returns the monster to idle (`0/3`, mode 2, called from `0x0094dd38`); the AI's next pick
  (mode 0, through `0x0094de74`) was then forced again, and the move restarted each frame.
- Skipping that idle return let the move run, but letting the AI's own picks through mixed
  its moves into the forced one.

The plugin now starts the forced pair only from another action and, while it runs, skips
every setter call for at most 300 calls in a row, after which one change goes through and the
next is forced again. Why the idle routine runs during a forced move is not traced.

 The source games can still be forced
with [reference/force_action.py](../reference/force_action.py) through Azahar's GDB stub; it
is a debugging tool for later move investigations, not part of this check.

## Ported monster ids

`mods/monster_ids` answers MH4U's monster-id-indexed tables for the ids in
[data/ids](../data/ids/README.md): a registered id is answered with the MH4U monster the
registry names as its stand-in, and 0 to 123 fall through. The headless check needs no
converted monster files, so it runs before #48 and #49.

| Check | What | Pass |
|---|---|---|
| P1 | the plugin's first-frame self-test, headless | the log shows the ready line, each reader answering the registered ids, the path the stand-in's data comes from, and ids 0 to 123 passing through |
| P2 | a quest whose monster is a ported id, played | the reader lines appear when the monster spawns and 0 to 123 still pass through; the quest plays, and a quest with MH4U's own monster plays as before |

P1, headless:

1. Build the plugin (`make` in `mods/monster_ids`) and add it to a user folder's mod library
   (`tools/mods.py add mods/monster_ids`). Set `selftest = 1` in the installed mod's
   `config.ini`. Build the code library with the mod on:
   `tools/build_game.py --dump <MH4U USA v1.3.0 update .cia> --install <user folder>`. The
   build lists the mod's 13 hook points.
2. Run the game headless:
   `mh4u_runner <MH4U USA .3ds> --code <user folder>/recomp/0004000000126300.so --user <user folder> --ms 20000 --log "*:Info"`.
3. Pass: the log has `ready: answering MH4U's monster tables for 2 ported id(s), 124 and up`
   and, for each reader, `self-test: <reader> answers id 124 -> 1, id 125 -> 1; ids 0..123
   pass through`; the factory's and data path's lines name the path the stand-in's files are
   read from (`enemy\em001\data\em001`). MH4U's own monsters were not loaded, so only the
   self-test's mapping shows here; a real spawn's reader lines are P2's.

P2, in game: needs the ported files (#48, #49) and a quest that names id 124
([quests.md](quests.md)). Not done.

Status: P1 run on 2026-11-25, USA v1.3.0 update, the code library built with the mod, headless
runner. Result: the plugin loaded, and the log showed the ready line and a self-test line
for each reader it logs, with `id 124 -> 1` and `id 125 -> 1` and `ids 0..123 pass through`, and the
stand-in's path `enemy\em001\data\em001`. P2 is not done.

## Tracing engine calls in MHXX

Shows which code calls an engine function at run time, and with which arguments, when reading the code doesn't settle it (the open entries of [reference/README.md](../reference/README.md#the-62-imports-one-by-one)). The maintainer plays; the tracer and the recording run beside the game.

1. Build Azahar's Qt frontend with the GDB stub (`-DENABLE_QT=ON -DENABLE_GDBSTUB=ON`; Debian needs `qt6-base-dev`, `qt6-multimedia-dev` and `qt6-base-private-dev`).
2. In a separate Azahar user folder, install the MHXX v4.8.0 update and turn the stub on (`[Debugging] use_gdbstub=true` in `config/qt-config.ini`). The update must be a decrypted CIA whose `code.bin` equals the official one, or the addresses won't match.
3. MHXX's game save is ExtData 0x1971: `sdmc/Nintendo 3DS/<id>/<id>/extdata/00000000/00001971/user/system` and `system_backup`. Put it there before the first boot, or the game creates a blank one.
4. Start the game, then `reference/trace_calls.py ADDR=label ...`. A function called every frame slows the game until `--max` retires it.
5. Play to the situation that should call the functions. A row's caller (LR) names the code using the function; matching the caller to a class through the vtables says who it is.

Last result (2026-11-24, a low-rank and a Hyper Rathian fight, Verdant Hills and Primal Forest): 5 of the 7 open functions ran, with their callers recorded in reference/README.md; `0x008a1ed8` and `0x008eb1c0` never ran.

The same tracer runs on MH4U's addresses. Its user folder holds the installed update (title `0004000e/00126300`) and the save in SavedData `title/00040000/00126300/data/00000001/` (`system` and `user1` to `user3`); the Qt frontend uses the `user` folder next to its binary, and it needs `/dev/dri` and `/dev/input`, so start it outside a file sandbox. Break on one or two addresses only: a getter called every frame freezes the game until `--max` retires it, so leave those out and keep `--max` low. Last result (2026-11-24, a Rathian quest): `0xb05154`, `0xb08c0c`, `0xb0545c`, `0x3120dc` and `0x304c10` ran; `0x94e364` did not. `0x304c10` was called once, by a shell's update (`uShell001` slot 22) for its owner, which settles the joint sound `0x008ae1c8`.
