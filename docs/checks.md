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
Comparing the animation each handler starts (its frame count and loop frame; a different
track count is recorded but doesn't decide, because MH4U's animations carry more tracks for
the same motion — every compared Zinogre id is 46 against MH3U's 37. The MH3U version-66
files use the same animation header and track table as version 67 for this comparison, while
their keyframe encodings are still unlaid-out, specs/lmt.md) splits the differing ids:

| Pair | Differing ids | Same motion, another index | Different motion | Not resolved |
|---|---|---|---|---|
| MH4U / MH3U | 115 | 93 | 3 | 19 |
| MHXX / MH3U | 84 | 67 | 3 | 14 |

The same-motion class is 86 exact signatures in MH4U/MH3U (64 in MHXX/MH3U), 2 with the same
frames and loop but a different track count, and 5 (3) whose handler's index decodes to an
empty MH4U/MHXX slot but whose animation is found at another index by its signature. The 3 different
are 13/5, 13/6 and 13/8 in both pairs: their frame or loop frame counts differ. The not-resolved
ids decode to an empty slot with no unique signature match, or match a different signature;
their handlers are category 7, whose code is shared and can start more than one motion, so the
first constant is not enough.

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
`no-handler`; the run prints the reason counts. The port translates MH3U's motion indices at
run time from a generated table ([#125](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/125));
13/5, 13/6 and 13/8 each keep their own animation.

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

### The shared action map (R2)

| Check | What | Pass |
|---|---|---|
| R2 | for every action id MHXX Rathian and MH4U's Rathian both have, record MH4U's handler, each side's start motion, and whether the constant indices agree; list the ids where only one side starts a constant motion or where the case blocks pass different arguments | the counts and ids are recorded below |

`reference/action_map.py` joins the inventories and motion lists R1 already writes. It prints
counts and ids only; the per-id map, which holds the motion indices, is written with `--out`
and stays outside the repository:

```bash
python3 reference/action_map.py map build/mhxx-actions.tsv build/mh4u-actions.tsv \
    build/mhxx-motions.tsv build/mh4u-motions.tsv --out build/action-map.tsv
```

Last result (2026-11-25, MHXX v1.4 `roEm001`, MH4U USA v1.3.0): of MHXX's 301 action ids, 273
exist in MH4U. 167 start the same constant index and none starts a different one. The other 106
are not compared by index: 50 start no motion on either side, 17 are inline on both sides, 16
MH4U starts one and MHXX none, 12 MH4U is inline and MHXX starts none, 6 MH4U starts none and
MHXX is inline, 3 MH4U starts one and MHXX is inline, 2 MH4U is inline and MHXX starts one.

Only MH4U starts a constant motion (19):

```
1/11 2/14 2/15 2/16 2/17 2/20 2/21 2/22 3/1 7/3 7/41 7/43 7/44 7/53 7/54 7/55 7/56 7/58 13/4
```

Only MHXX starts one (2): `9/3 9/4`. One side is inline and the other starts none (18):

```
0/3 0/6 3/14 3/22 3/23 3/26 3/30 3/39 3/40 3/44 3/58 3/76 3/77 3/97 4/2 4/12 4/13 4/23
```

20 ids pass different case-block arguments. The 12 category-3 ones (3/14, 3/22, 3/23, 3/26,
3/30, 3/39, 3/40, 3/44, 3/58, 3/76, 3/77, 3/97) take a mode in `r1` in MHXX and run inline in
MH4U, so they are the first to watch in R2p.

The 28 ids MH4U lacks reach 8 handler units: 15 are projectile spawns that tail-call MHXX's
`0x008b4228` (category 10's 14 ids and 11/7), and the other 13 use six units, listed in
[#112](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/112).

Two of those 28 are not missing. MH4U's category-8 and category-12 cases test the index with
`cmp #0; bne default` rather than a switch, so the inventory and R2's map lose them:

- **12/0 is MH4U's own action.** Its category-12 case runs `0x006d524c`, the handler MH4U's
  shared 3/2, 3/83 etc. use and the role pair of MHXX's 12/0 (`0x0201177c`). The port needs no
  code for it, and forcing it on the ported monster plays MH4U's handler.
- **8/0 is a shared id with the same action.** MH4U's category-8 case runs `0x006e9770`
  for index 0, which uses the same frame values as MHXX's `0x0201b460` (300.0/38.0,
  12.0/50.0, the 180.0 timer, motion 0x403 at 4.0, 300.0/0.0/150.0) and the same tail
  (9/1 or 2/6). The two bodies differ, so the port translates MHXX's handler onto MH4U's
  calls and layout (`mods/rathian_actions`); its leaf `0x008c4184` is MH4U's
  `0x0092f6e8`, whose table is not carried yet. Both 8/0 and 12/0 are missing from the
  inventory because their cases are `cmp #0; bne`, not switches.

`reference/monster_actions.py`'s `find_switch` needs that `cmp #0; bne` case before R2's counts
can include the two ids; the counts above were made without it.

What this means for the port: a shared id runs MH4U's own handler, and because #48 ships
MHXX's motion lists under the ported monster's name and the index is the same, that handler
starts MHXX's animation. A GU shared id needs no index remap, unlike a 3U one. The ids above
where only one side starts a motion are what R2p looks at first.

### The ported moves' check (R2p)

| Check | What | Pass |
|---|---|---|
| R2p | force each action id the port ships on the ported Rathian and compare the move with its source game | every shipped id has a row below, and the ids that do not play like the source game are named with what differs |

For each id in R2's map (the GU port, id 124), set it in `mods/force_action`'s `config.ini`
(`action = <cat>/<idx>`, `monster = 124`, `hold = 1`), take a quest that names id 124, and watch
the move. R2's map says what to expect: a shared id starts MHXX's motion at the same index, and
the ids R2 lists as one-sided may start no motion or another one. Record pass or fail per id and
what differs: no motion, another motion, a different timing, a missing effect or projectile.
The translated ids on the GU port are 3/98, 12/1, 12/2, 12/3 and 8/0; 8/0 should play motion
0x403 at 4.0 and then ask for 9/1 (or 2/6), and its leaf effect is the one part not carried.

Category 17 has no motion to watch. MHXX's case jumps to the gate `0x008d5bd4`, which returns
for indexes 0 to 2 and otherwise tail-calls the base update `0x008ae50c`; the port maps that
routine to MH4U's `0x00911b48` (the step mapping is in the plugin's
[README](../mods/rathian_actions/README.md#category-17-the-gate-and-the-base-update)). Force
each row:

| Forced | What MHXX does | What to watch |
|---|---|---|
| 17/0, 17/1, 17/2 | the gate returns | no move and no action change; the log has `17/N: nothing (the gate returns for 0 to 2)` |
| 17/3 and up | the base update returns the monster to an idle action | the log has `17/N: running MH4U's base action update 0x00911b48`, and the action pair goes back to category 0 |

Status: not done. The category-17 rows wait with the rest of R2p for #48 and #105.

The 3U port (id 125) has the rows below (#116's). They are the 16 ids MH4U's `uEm001` lacks that
reach a handler a shared action also reaches, so `mods/monster_actions` sends each to the MH4U
action the map names and MH4U's own handler runs
([reference](../reference/README.md#the-17-ids-mh4u-has-no-action-for)). For each row, enable
both plugins, put `force_action` after `monster_actions` in the mod order (the last mod's hook
runs first, so `force_action` writes the forced pair and the map translates it), set
`action = <3U id>`, `monster = 125` and `hold = 1`, take a quest that names id 125, and watch
the move. The plugin's log shows its ready line and one `monster 125: action <source> -> <target>`
line per id. Record pass or fail and what differs; if the move is another variant, the actions
in the page's "other MH4U actions with the same body" column are what to try next.

| 3U id | the map runs | status |
|---|---|---|
| 0/4 | 0/0 | not done |
| 7/64 | 7/35 | not done |
| 7/87 | 7/92 | not done |
| 7/93 | 7/92 | not done |
| 10/0 | 10/7 | not done |
| 10/1 | 10/7 | not done |
| 10/2 | 10/7 | not done |
| 10/3 | 10/7 | not done |
| 10/4 | 10/7 | not done |
| 10/5 | 10/7 | not done |
| 10/6 | 10/7 | not done |
| 11/5 | 11/0 | not done |
| 11/15 | 11/0 | not done |
| 11/26 | 11/0 | not done |
| 11/28 | 11/0 | not done |
| 13/9 | 0/3 | not done |

Action 4 needs new C (#136) and is not on the map; it joins this table when it plays.

Status: not done. The GU rows wait for #48 (the ported files) and #105 (the ported monster's own
resource paths); the 3U rows wait for #49, #105 and #125 (the motion table).

The port's plugin for the MHXX-only ids is `mods/rathian_actions`: it runs the translated
handlers for 3/98, 12/1-3, 4/27-32, 8/0 and category 17, and leaves shared ids and
12/0 alone (T1). It logs one line the first time each translated action runs, one line per
category-17 index and, for 8/0, one line naming its uncovered calls.

Status: not done. It waits for #48 (the ported files) and #143 (the ported monster's own
resource paths); the ids themselves are in R2.

### The ported AI's check (R3)

| Check | What | Pass |
|---|---|---|
| R3 | play the ported 3U Rathian (id 125) without forcing, and read the actions her AI asks for | she asks for an action only MH3U's script picks, so `mods/monster_actions` logs `monster 125: action 7/64 -> 7/35`; MH4U's own script never asks for 7/64, so the line is only there if her converted EMC drives her |

The 3U Rathian's EMC is converted at build time (version, 23 group rows, the 15 opcodes whose
argument count differs; [specs/emc.md](../specs/emc.md#what-a-converter-must-do)). Cut by the
game's tables, it names 143 native actions; six of them, 3/0, 7/22, 7/63, 7/64, 7/69 and 7/85,
are not in MH4U's own script. 7/64 is also one of the 17 ids MH4U's `uEm001` lacks, so
`mods/monster_actions` translates it to 7/35 and logs one line the first time it runs.

1. Build 125's files with #49, including the converted EMC at `enemy\em125\data\em125_cmd`.
   The registry names `cmd` for her, so the resource record loads it
   ([data/ids](../data/ids/README.md)).
2. Check the converted EMC first: 23 group rows, every script cuts cleanly with MH4U's table
   (A2):

   ```bash
   game_files/work/venv/bin/python reference/monster_emc.py <cmd> \
       --lens <the MH4U ELF or flat code image> 0x00ffe9f4 146 --check
   ```

3. Enable `mods/monster_ids` and `mods/monster_actions`, build the code library with them
   (the fork's `tools/build_game.py`), and take a quest that names 125.
4. Fight her normally: let her fly, run, bite and tail-swipe. Pass: the log has
   `monster 125: action 7/64 -> 7/35`. The control is a build whose 125 row has no `cmd`, so
   her record keeps the stand-in's script; that run never logs the line.
5. Category-4 lines are expected too: action 4 has no MH4U handler and is not on the map
   ([#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136)), so the AI's
   category-4 picks are recorded but are not this check's pass.

Status: not done. It waits for #49's converted EMC and a quest that names 125.

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
registry names as its stand-in, except its resource record, which the plugin builds for the
ported id with its own paths for the kinds of file the port ships and the stand-in's for the
rest; 0 to 123 fall through. The headless check needs no converted monster files, so it runs
before #48 and #49.

| Check | What | Pass |
|---|---|---|
| P1 | the plugin's first-frame self-test, headless | the log shows the ready line, each reader answering the registered ids, the resource record each registered id built with its own id's paths for the kinds the port ships and the stand-in's for the rest, the path the stand-in's data comes from, and ids 0 to 123 passing through |
| P2 | a quest whose monster is a ported id, played | the reader lines appear when the monster spawns and 0 to 123 still pass through; the quest plays, and a quest with MH4U's own monster plays as before |

P1, headless:

1. Build the plugin (`make` in `mods/monster_ids`) and add it to a user folder's mod library
   (`tools/mods.py add mods/monster_ids`). Set `selftest = 1` in the installed mod's
   `config.ini`. Build the code library with the mod on:
   `tools/build_game.py --dump <MH4U USA v1.3.0 update .cia> --install <user folder>`. The
   build lists the mod's 14 hook points.
2. Run the game headless:
   `mh4u_runner <MH4U USA .3ds> --code <user folder>/recomp/0004000000126300.so --user <user folder> --ms 20000 --log "*:Info"`.
3. Pass: the log has `ready: answering MH4U's monster tables for 2 ported id(s), 124 and up,
   with the files each port ships and the stand-in's for the rest`; one `self-test: id 124
   resource record at <address>, built from stand-in 1, names: ...` line per registered id,
   listing the paths read back from the record built in guest memory; one `self-test: id 124
   ships model, motions 0-4, tail, cmd; keeps stand-in 1's paths for motions above 4, camera,
   mef, sound, efl` line and one for 125 (`ships model, motions 0-2, tail, cmd; keeps stand-in
   1's paths for motions above 2, camera, mef, sound, efl`); and, for each reader,
   `self-test: <reader> answers ...; ids 0..123 pass through`. In the 124 record the model,
   motion, tail and command paths name `em124`, and the camera, motion-effect, sound and
   effect-list paths still name `em001`. The 125 record names `em125` for the model, motion
   slots 0 to 2, the tail and the command, and keeps the stand-in's `em001` for motion slots 3
   and 4, the camera, motion effects, sound and effect lists. No path may name a file the
   port's arc does not ship: `enemy\em125\mot\em125_3`/`_4`, `e125_cam`,
   `effect\mef\em\em125_*`, `sound\call\em\em125` and `effect\efl\em\em125\em125_000` are the
   ones that hung the load. The 125 command path is the port's converted EMC, which #49 ships;
   a P1 run before that file exists still builds the record (the self-test does not load
   files), but a quest with 125 would hang as in #143. The factory's and data path's lines
   name the path the stand-in's files are read from (`enemy\em001\data\em001`), which the
   record does not change. MH4U's own monsters were not loaded, so only the self-test's
   mapping shows here; a real spawn's reader lines are P2's.

P2, in game: needs the ported files (#48, #49) and a quest that names id 124
([quests.md](quests.md)). Not done.

Status: P1 run on 2026-11-25, USA v1.3.0 update, the code library built with the mod, headless
runner. Result: the plugin loaded, and the log showed the ready line, a line per registered
id naming the paths of the record it built in the game's heap and the kinds and motion slots
each port ships and keeps the stand-in's for, a self-test line for each reader with `ids
0..123 pass through` (including the effect lists reader, the third reader of the record), and
the stand-in's data path `enemy\em001\data\em001`. The records kept `enemy\em001\...` for the
kinds and motion slots a port does not ship and named no missing `em124`/`em125` path: MH4U
does not tolerate a missing entry ([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)).
P2 is not done, so a real spawn's load is unverified. After this run, 125's registry row
gained `cmd` ([#159](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/159)), so the
next P1 run's 125 record also names `enemy\em125\data\em125_cmd`, the converted EMC #49 ships;
that run is not done yet.

## A ported camera's cut-in (C2)

MH4U's camera list ([specs/camera.md](../specs/camera.md)) holds the cameras an action posts by
number; a ported monster brings its source game's list, converted to MH4U's version 4, in its
arc at `enemy\emNNN\mot\eNNN_cam` (the `camera` kind in [data/ids](../data/ids/README.md)).
This check needs the converted camera in the port's arc, the `camera` kind on the id, the
plugin's record built with it (P1), and a quest that spawns the id (#144).

1. Convert the source camera with `mhuc convert monster --from mhxx --id 124 --arc <MHXX
   arc/enemy/em001_00.arc> --out <mod folder>`; the port's arc holds
   `enemy\em124\mot\e124_cam`. Check that 124's `files` in `data/ids/registry.csv` lists
   `camera`, regenerate `mods/monster_ids/src/ids.h` and rebuild the code library (P1 step 1).
2. Force an action whose handler posts a camera event: MH4U's camera event is `0x00934544`
   (USA v1.3.0), and a handler's call to it names the event id it posts. `mods/force_action`
   (R1p) plays the chosen action; the converted list keeps the source's event ids, and Rathian's
   shared ids include 0, 1, 2, 4, 5 and 8, so an event MH4U's own Rathian posts is in it.
3. Pass: the view cuts to the source game's framing of the monster (MHXX's cut-in camera), not
   MH4U Rathian's, and the P1 log's line for 124 names `e124_cam` among the record's own paths.
   Fail: the framing is MH4U Rathian's (the record kept the stand-in's `e001_cam`), or the load
   stops at the camera path.

Status: open; waits for #48's port files and #144's quest-load proof.

## Calling the engine from a plugin (P3)

The plugin API's ABI 3 `call` runs a game function by address with r0-r2 as its arguments and
returns its r0 (`call(call, addr, a0, a1, a2)`, the fork's [docs/PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md)). This check calls a
getter that only reads a table, so it needs no monster and no quest: MH4U's crown getter,
`getCrown` (USA v1.3.0 `0x0068877c`, id in r0, a scale in r1, and a pointer to its 8-byte
result in r2).

| Check | What | Pass |
|---|---|---|
| P3 | a plugin calls `getCrown` through ABI 3 `call` in a headless run | the log shows the host's ABI 3 and `call getCrown(id=1, scale=1.0f, out=<guest address>) -> r0=0x1, class=1`; the runner exits 0 |

1. Build both port binaries after the ABI 3 change, each in its existing CMake tree:
   `cmake --build <build> --target mh4u_runner` for the headless runner and
   `cmake --build <build-qt> --target azahar` for the Qt frontend. Both compile
   `port/src/plugin_host.h`, so both carry `call`.
2. Build a throwaway plugin (not in either repository) against the fork's
   `include/mh4u_plugin.h`: in `mh4u_plugin_init` it checks `host->abi >= 3` and that
   `host->size` covers `call`, then asks for `on_frame`. In a frame call after start-up it
   takes 8 bytes from `alloc`, calls
   `host->call(call, 0x0068877c, 1, 0x3f800000, out)` (id 1, scale 1.0f, out) and logs the
   returned r0 and the byte at `out`. r1 carries the scale as an unsigned integer: the
getter does `vmov s0, r1; vcvt.f32.u32` at `0x006887a8`, so P3 proves r0-r2 and the r0
return, not float arguments (T0 covers those).
3. Put the plugin's line in the code library's `<program id>.plugins.tsv`
   (`plugin`, name, library path and mod folder, tab-separated) in a copy of a user folder. No
   code library rebuild is needed: `sMhMain::frame` is a hook point of every library the
   fork's `tools/build_game.py` builds.
4. Run
   `mh4u_runner <MH4U USA .3ds> --code <user folder>/recomp/0004000000126300.so --user <user folder> --ms 12000 --speed 0 --log "*:Info"`.

Result (2026-11-25, MH4U USA v1.3.0, headless runner rebuilt with ABI 3): pass. The log had
`plugin <name>: ready: host ABI 3, size 0xb0, call present` when the plugin loaded, then
`plugin <name>: frame 30: call getCrown(id=1, scale=1.0f, out=0x08e44670) -> r0=0x00000001, class=1`,
and the runner exited 0. r0=1 is the getter's crown class for id 1 (0 to 3), and the same
class byte was written into the out buffer: the call reached the game function and returned
its r0, and the run continued to its end, so the guest's registers were put back. The
motion-start wrapper `0x0094e318` reads the enemy at `this+0xe28`, so it needs a live `uEnemy`
and is called from a quest, not from this boot-only check: P3 proves the call mechanism, and
the translated handlers ([#112](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/112),
[#115](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/115)) call it on a monster.
A longer run (130 s of emulated time, menu input through the opening movie) loaded a save and
reached the character and the village, where no monster spawns; the probe also hooks
`uEnemy::dispatchAction` to capture a live `this`, and it captured nothing. Calling the wrapper
on a spawned monster still waits for a quest run.

## The translated actions' check (T1)

The port's translated handlers for MHXX-only actions have no in-game run yet (R2p), so they
are checked without a monster: the source facts against MHXX's module, the state machines
against a fake host, and the plugin's self-test in a headless run.

| Check | What | Pass |
|---|---|---|
| T1a | `tools/check_actions.py` reads [data/actions/rathian-gu.csv](../data/actions/rathian-gu.csv) and MHXX v1.4's `roEm001.cro` | every row's case block, handler unit and first motion constant match the module's dispatcher; counts and ids only |
| T1b | `make -C mods/rathian_actions test` | the plugin's call sequences and frame values match the source's order, and a changed value fails it |
| T1c | a headless run of the code library built with the plugin | the log has the plugin's ready and self-test lines and the float stubs' address; the runner exits 0 |
| T1d | the in-game per-move check | R2p |

T1a: MHXX v1.4's `roEm001.cro` and its `static.crs` come from the player's own dump.

```bash
MH4U_FORK=<fork> python3 tools/check_actions.py --module <roEm001.cro> --crs <static.crs>
```

Last result (2026-11-25): pass. 13 actions; blocks 13/13, handlers 12/13 (category 17 has
none), first motions 9/13; translated 12 (3/98, 12/1-3, 4/27-32, 8/0 and category
17), MH4U's own 1 (12/0), pending 0. Changing a ledger motion makes it exit 1 and name the
id.

T1b, last result (2026-11-25): pass, the call sequences checked across 3/98's three frames,
the 12/1-3 blocks, 4/27-32's states, 8/0's three states and category 17's no-op and
base-update paths. Changing 3/98's `6.0` to `5.0` fails it with the motion line; making
17/3 a no-op (`index > 3`) fails it with 17/3's line; giving 4/27 the fast turn step fails
it with the turn line; changing 8/0's motion speed `4.0` to `5.0` fails it with 8/0's line.

T1c, last result (2026-11-25, MH4U USA v1.3.0, the #139 code library built with the mod's
`uEnemy::dispatchAction` hook, headless runner): pass, when only the 3/98 and 12/1-3 slices
were in the build. The log had the plugin's ready line,
`ready: translating 5 of GU Rathian's 13 MHXX-only actions on monster 124`, then
`selftest: 5 of the 13 actions: 3/98 <- 0x020062d4 (3 states, motions 0x101 and 0x104), ...`,
the line naming 12/0 as MH4U's own `0x006d524c` and the pending slices, and
`selftest: float stubs at 0x08e44670 (256 bytes, the game's heap)`; the runner exited 0. No
monster spawned, so no translated action ran: the in-game side is R2p.

The 4/27-32 and 8/0 slices change that line to `selftest: 12 of the 13 actions: ... 4/27-32
<- 0x0200e3b4 (3 states, motions 0x417/0x418, 0x909/0x90a, 0x90b/0x90d, r1/r2 per id), 8/0
<- 0x0201b460 (3 states, motion 0x403 at 4.0, ...), 17 <- the gate 0x008d5bd4 + MH4U's base
update 0x00911b48`, and the last line names 8/0's leaf and no pending slice. No headless run
has shown that line yet: it needs a code library rebuilt with the plugin, and the build
machine's one heavy job is the quest-load proof
([#144](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/144)).

## Floats through a guest stub (T0)

ABI 3 `call` sets `r0`-`r2` and returns `r0`, but MH4U's motion start reads its speed in `s0`,
and a source case block takes target points in `s0`-`s3`. A plugin can write a small ARM stub
into a block from `alloc` (ABI 2) that loads `s0`/`s1` and branches to the engine function, and
hand a float back by moving `s0` to `r0` after the call. The port interprets code that is not
recompiled (`port/src/arm_recomp.cpp`, `Interpret`), so a block from `alloc` is executable and
a stub's literals can be rewritten per call.

| Check | What | Pass |
|---|---|---|
| T0 | a throwaway plugin allocates a block, writes a stub that sets `s0` to 6.0 and branches to a second stub doing `vmov r0, s0; bx lr`, and calls it | `call` returns `0x40c00000` (6.0f) and the runner exits 0 |

Result (2026-11-25, MH4U USA v1.3.0, headless runner with an ABI 3 code library): pass. The log
had the stub and target addresses, `call -> r0=0x40c00000`, and exit 0. A first attempt with a
wrong literal offset jumped into the literal and the runner died with an illegal instruction,
which is what a bad stub looks like; the layout is in
[the plugin's README](../mods/rathian_actions/README.md#floats-the-guest-stubs). The fork's
[#134](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/134) adds float and `r3`
arguments to the plugin ABI; when it lands, the stubs give way to that `call`.

## Tracing engine calls in MHXX

Shows which code calls an engine function at run time, and with which arguments, when reading the code doesn't settle it (the open entries of [reference/README.md](../reference/README.md#the-62-imports-one-by-one)). The maintainer plays; the tracer and the recording run beside the game.

1. Build Azahar's Qt frontend with the GDB stub (`-DENABLE_QT=ON -DENABLE_GDBSTUB=ON`; Debian needs `qt6-base-dev`, `qt6-multimedia-dev` and `qt6-base-private-dev`).
2. In a separate Azahar user folder, install the MHXX v4.8.0 update and turn the stub on (`[Debugging] use_gdbstub=true` in `config/qt-config.ini`). The update must be a decrypted CIA whose `code.bin` equals the official one, or the addresses won't match.
3. MHXX's game save is ExtData 0x1971: `sdmc/Nintendo 3DS/<id>/<id>/extdata/00000000/00001971/user/system` and `system_backup`. Put it there before the first boot, or the game creates a blank one.
4. Start the game, then `reference/trace_calls.py ADDR=label ...`. A function called every frame slows the game until `--max` retires it.
5. Play to the situation that should call the functions. A row's caller (LR) names the code using the function; matching the caller to a class through the vtables says who it is.

Last result (2026-11-24, a low-rank and a Hyper Rathian fight, Verdant Hills and Primal Forest): 5 of the 7 open functions ran, with their callers recorded in reference/README.md; `0x008a1ed8` and `0x008eb1c0` never ran.

The same tracer runs on MH4U's addresses. Its user folder holds the installed update (title `0004000e/00126300`) and the save in SavedData `title/00040000/00126300/data/00000001/` (`system` and `user1` to `user3`); the Qt frontend uses the `user` folder next to its binary, and it needs `/dev/dri` and `/dev/input`, so start it outside a file sandbox. Break on one or two addresses only: a getter called every frame freezes the game until `--max` retires it, so leave those out and keep `--max` low. Last result (2026-11-24, a Rathian quest): `0xb05154`, `0xb08c0c`, `0xb0545c`, `0x3120dc` and `0x304c10` ran; `0x94e364` did not. `0x304c10` was called once, by a shell's update (`uShell001` slot 22) for its owner, which settles the joint sound `0x008ae1c8`.
