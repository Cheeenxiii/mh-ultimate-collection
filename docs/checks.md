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

## System save fields

The `system` save's options, guild-card list and DLC/quest registration are the candidates in
[specs/save.md](../specs/save.md#system-save) (checks S9, S10). Back up `system`, `user1` to `user3` and
the Extra Data with a save manager first; `mhuc save dump` reads the decrypted file, or takes the key with
`--key`.

1. Keep the current file as the baseline. Change one option in the game's Options menu, save and quit,
   then decrypt `system` again and compare. Pass: the option moved a byte or a bit that no other option
   moved; write the offset and the value's encoding into the table. Repeat for every option. Ignore 0x04,
   the four words at 0x08 and 0x64 while comparing: they may move on every save.
2. Create a new character, then select each character in turn, saving after each. Pass: 0x3C holds the
   selected slot and 0x40 the highest slot in use. If they move with something else, give them their own
   rows instead.
3. Receive a guild card (StreetPass or a Gathering Hall), save and compare. Pass: one of the four u32 at
   0x08, or a bit in the block at 0x18, changes for the card and for no other action; the card list's
   count and entry shape go in the spec.
4. Download a DLC quest, then remove its Extra Data file, saving after each. Pass: the block at 0x18
   changes at that quest's bit and no other field changes, the time fields aside; that bit is the
   registration that #77's converter has to clear.
5. Put the original files back.

Status: open. The steps need the game (or the port); files alone cannot say which bit is which.

## Save converter (S11)

`mhuc save clean` gives back a clean MH4U save ([specs/save.md](../specs/save.md#converting-a-modded-save-back)).
Check S11 is its file-side half, run by `tests/test_save.py` and `tests/test_with_game_files.py`: on a save
that never met the mod it changes no byte and re-encrypts to the same file. This is the in-game half: the
cleaned save loads and shows none of the mod's data.

Back up `system`, `user1` to `user3` and the Extra Data with a save manager first, and keep the backups until
the check passes.

1. Make a modded copy of one character save. With a save editor, put an item id above MH4U's item list (1,937
   or higher) in an empty item-box slot, and a monster id from the registry (124 or higher) in one monster
   record of a guild-quest slot. Note the slots. If a save the mod wrote exists, use that copy instead.
2. Clean it: `mhuc save clean user1 --key save.key --out user1.clean`. Pass: it reports one item slot and one
   guild quest removed. On a save that never met the mod it must report none and write the same bytes.
3. `mhuc save check user1.clean --key save.key`. Pass: it prints `character save ok`.
4. Compare the cleaned and original files (`mhuc save dump` both): the only differences are the cleared item
   slots and the cleared guild-quest slot; the profile, both boxes, the worn gear, the Palicos, the monster
   log, the item flags and the unknown blocks are unchanged.
5. Put `user1.clean`, the untouched `system` and the other character files back and boot MH4U. Pass: the
   save-data screen lists the character, it loads in the hub, the item box has no slot the converter counted,
   the guild quest is gone, and every other item, piece of gear, Palico and quest is the one in the backup;
   the game saves again without an error and the character is there after a restart.
6. Put the backups back.

Status: open. Needs the game. "Indistinguishable from a save that never met the mod" holds for the mapped
structures only: the unknown blocks and the `system` save are left as they are until decision 0003 settles
where the mod's data goes and check S10 maps the system save's registration.

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
`no-handler`; the run prints the reason counts. The port's own handler for each 3U id passes
MH4U's form of her own animation to MH4U's motion-start wrapper, written as `file << 8 | slot`
when the handler is written
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)); nothing translates a
motion number at run time. 13/5, 13/6 and 13/8 each keep their own animation.

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
  calls and layout (the runtime's GU Rathian module); its leaf `0x008c4184` is MH4U's
  `0x0092f6e8`, whose table is not carried yet. Both 8/0 and 12/0 are missing from the
  inventory because their cases are `cmp #0; bne`, not switches.

`reference/monster_actions.py`'s `find_switch` needs that `cmp #0; bne` case before R2's counts
can include the two ids; the counts above were made without it.

What this means for the port: under decision 0002's 2026-11-26 amendment a ported id runs her
own handler, so R2's counts are evidence for the constant each handler passes, not for whose
handler runs. GU's index is already MH4U's on every comparable id; a 3U handler's MH3U index is
converted when the handler is written
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)). The ids above where
only one side starts a motion are what R2p looks at first.

### The ported moves' check (R2p)

| Check | What | Pass |
|---|---|---|
| R2p | force each action id the port ships on the ported Rathian and compare the move with its source game | every shipped id has a row below, and the ids that do not play like the source game are named with what differs |

For each id in R2's map (the GU port, id 124), set it in `mods/force_action`'s `config.ini`
(`action = <cat>/<idx>`, `monster = 124`, `hold = 1`), take a quest that names id 124, and watch
the move. R2 says what to expect: her own handler starts the animation at the index R2 records,
and the ids R2 lists as one-sided may start no motion or another one. Record pass or fail per id and
what differs: no motion, another motion, a different timing, a missing effect or projectile.
The translated ids on the GU port are 3/98, 12/1, 12/2, 12/3 and 8/0; 8/0 should play motion
0x403 at 4.0 and then ask for 9/1 (or 2/6), and its leaf effect is the one part not carried.

Category 17 has no motion to watch. MHXX's case jumps to the gate `0x008d5bd4`, which returns
for indexes 0 to 2 and otherwise tail-calls the base update `0x008ae50c`; the port maps that
routine to MH4U's `0x00911b48` (the step mapping is in the runtime's
[README](../mods/uc_runtime/README.md#category-17-the-gate-and-the-base-update)). Force
each row:

| Forced | What MHXX does | What to watch |
|---|---|---|
| 17/0, 17/1, 17/2 | the gate returns | no move and no action change; the log has `17/N: nothing (the gate returns for 0 to 2)` |
| 17/3 and up | the base update returns the monster to an idle action | the log has `17/N: running MH4U's base action update 0x00911b48`, and the action pair goes back to category 0 |

Status: not done. The category-17 rows wait with the rest of R2p for #48 and #105.

The 3U port (id 125) has the rows below (#116's). They are the 17 ids MH4U's `uEm001` has no
action for; #116 will hold a row for every id the ledger marks translated. Under decision
0002's 2026-11-26 amendment she runs her own handler for each, so the 3U module
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)) runs the source's
handler and the row checks the move against MH3U's own
([reference](../reference/README.md#the-17-ids-mh4u-has-no-action-for)). For each, set
`action = <3U id>`, `monster = 125` and `hold = 1` in `mods/force_action`'s `config.ini`, take
a quest that names id 125, and watch the move. The module logs the handler it ran, and an id
the ledger ([#214](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/214)) still
marks pending goes to MH4U's dispatcher once and is logged. Record pass or fail and what
differs.

| 3U id | status |
|---|---|
| 0/4 | not done |
| 4 | not done |
| 7/64 | not done |
| 7/87 | not done |
| 7/93 | not done |
| 10/0 | not done |
| 10/1 | not done |
| 10/2 | not done |
| 10/3 | not done |
| 10/4 | not done |
| 10/5 | not done |
| 10/6 | not done |
| 11/5 | not done |
| 11/15 | not done |
| 11/26 | not done |
| 11/28 | not done |
| 13/9 | not done |

Action 4 has no shared MH4U action to compare with; [#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136)
translates it, and the other sixteen's counterparts are in the reference page.

Status: not done. The GU rows wait for #48 (the ported files) and #105 (the ported monster's own
resource paths); the 3U rows wait for #49, #105 and the quest load
([#144](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/144)), with her module
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)) and its slices
[#217](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/217) to
[#229](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/229) and
[#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136).

The shared ids the slices translate get a row too, since #116 holds one for every id the ledger
marks translated. Category 3's part 2 ([#220](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/220))
runs her own handlers for sixteen of them; force each and compare it with MH3U's own move. The
runtime's [README](../mods/uc_runtime/README.md) and the
[reference](../reference/README.md#the-category-3-part-2-units-220) name each unit's calls and
the two #55 calls it leaves out.

| 3U id | Handler unit | What to watch |
|---|---|---|
| 3/6 | 0x0068e448 | motion 0x1a at 6.0, the curve on aim A y and the position advance, then the height test: with 3U's 0x0064325c blocked the fall starts at the vertical limit + 2000 |
| 3/7 | 0x0068e5e8 | motion 0x1a at 6.0; on the flag the turn at 0x200 and the fall into 0/3's base handler |
| 3/8 | 0x0082b37c | motions 0x2d, 0x3d, 0x3e, 0x2d and 0x1d, the 30.0/70.0 aims and the two-joint turns; the end of state 4 takes 3U's blocked 0x00839598 as nonzero |
| 3/12 | 0x0068e6e4 | motion 0x3d at 6.0, the 70.0 distance test, aim A z 5.0 then 90.0 and aim B z 3.0, then 3/11 through 0x0084dc84 |
| 3/13 | 0x0068e448 | motion 0x1a, the curve and the advance, then target z + 1300 as the height (it never calls 0x0064325c) |
| 3/16 | 0x0068e448 | the flying byte first, then the 3/6 sequence |
| 3/17 | 0x0068e5e8 | the flying byte, then the 3/7 sequence asking 3/0x14 |
| 3/18 | 0x0068e5e8 | the 3/7 sequence asking 3/0x15 |
| 3/19 | 0x0068e5e8 | the 3/7 sequence asking 3/0x19 |
| 3/20 | 0x0068e6e4 | the 3/12 sequence asking 3/0x16 |
| 3/21 | 0x0068e6e4 | the 3/12 sequence asking 3/0x17 |
| 3/24 | 0x0068e5e8 | the 3/7 sequence asking 3/0x19 |
| 3/25 | 0x0068e6e4 | the 3/12 sequence asking 3/0x1a |
| 3/27 | 0x0068e8c8 | motions 0x1a, 0x1d and 0xcf/0xe1 by the record's kind, mode 3 then mode 0, then 0/2's base handler |
| 3/28 | 0x0068e5e8 | the 3/7 sequence asking 3/0x1d |
| 3/29 | 0x0068e6e4 | the 3/12 sequence asking 3/0x1e |

Status: not done. These rows wait for #49, #105 and the quest load (#144), like the 17 above.
The port's module for the MHXX-only ids is the runtime's GU Rathian module
(`mods/uc_runtime/src/monsters/rathian-gu.c`): it runs the translated handlers for 3/98,
12/1-3, 4/27-32, 8/0 and category 17 and leaves 12/0 (T1). Her own handler for every id,
shared ids included, is still owed under decision 0002's 2026-11-26 amendment. The module logs
one line the first time each translated action runs, one line per category-17 index and, for
8/0, one line naming its uncovered calls.

Status: not done. It waits for #48 (the ported files) and #143 (the ported monster's own
resource paths); the ids themselves are in R2.

### The ported AI's check (R3)

| Check | What | Pass |
|---|---|---|
| R3a | run the 125 quest headless and read the resource record the id layer builds and the archive the game loads | the log has the record line for id 125 naming `enemy\em125\data\em125_cmd`, `data resource: id 125 -> its own archive`, `resource load: id 125 -> its own record`, and LayeredFS's replacement line for `/data/em125.arc`; no missing-resource line |
| R3 | play the ported 3U Rathian (id 125) without forcing, and read the actions her AI asks for | she asks for an action only MH3U's script picks, so her module logs that it ran 7/64; MH4U's own script never asks for 7/64, so the line is only there if her converted EMC drives her |

The 3U Rathian's EMC is converted at build time (version `0x20120804`, 23 group rows, the 15
opcodes whose argument count differs; [specs/emc.md](../specs/emc.md#what-a-converter-must-do)
and [the added argument](../specs/emc.md#the-added-argument), check A5). Cut by the game's
tables, it names 143 native actions; six of them, 3/0, 7/22, 7/63, 7/64, 7/69 and 7/85, are not
in MH4U's own script. 7/64 is also one of the 17 ids MH4U's `uEm001` lacks, so the port runs her
own 7/64 handler, translated in a category-7 slice
([#221](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/221) to
[#224](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/224)), and the module's log
names it the first time it runs.

1. Build 125's files, with the two games' decompressed code images for the EMC tables:

   ```bash
   game_files/work/venv/bin/python -m mhuc convert monster --id 125 \
       --romfs <MH3U RomFS> --mh4u-romfs <MH4U RomFS> \
       --mh3u-code <MH3U decompressed code.bin> --mh4u-code <MH4U v1.3.0 decompressed code.bin> \
       --out <mod folder>
   ```

   Pass here already: `Rathian (id 125, from MH3U em001): 10 files`, and the archive holds one
   `rEnemyCmd` at `enemy\em125\data\em125_cmd`, version `0x20120804` with 23 group rows.
2. Check the converted EMC on its own: 23 group rows, every script cuts cleanly with MH4U's
   table (A2), and the action pairs and script calls are the source's (A5):

   ```bash
   game_files/work/venv/bin/python reference/monster_emc.py <cmd> \
       --lens <the MH4U flat code image> 0x00ffe9f4 146 --check
   ```
3. Deploy the mod into a copy of an Azahar profile with the fork's `tools/mods.py`
   (`--user-dir <copy>`, after putting the mod in `<copy>/mh4u-mods`), and take a quest whose
   monster list names 125. Build the profile's code library from the USA v1.3.0 update with the
   fork's `tools/build_game.py --mods <copy> --install <copy>`, with only the repository's
   current mods enabled: for this check `Ported monster ids` (and the data-only quest mod, which
   carries no hooks). A library left over from an older profile can bring in retired plugins
   such as the `Ported monsters' motion numbers` bridge, whose action log is not evidence about
   this converter.
4. Run it headless with the port's runner; the id layer's `selftest` config makes it print each
   ported id's record:

   ```bash
   game_files/work/azahar/build/bin/Release/mh4u_runner \
       "Monster Hunter 4 Ultimate (USA) Decrypted.3ds" \
       --code <copy>/recomp/0004000000126300.so --user <copy> --ms 150000 --speed 0 \
       --log "*:Info" --input <the input script> --draw-window 1
   ```

   Pass: `self-test: id 125 resource record at ..., built from stand-in 1, names: ...` with the
   command path in the list; `data resource: id 125 -> its own archive`; `resource load: id 125 ->
   its own record`; and LayeredFS's `replacement file in use for /data/em125.arc`, with no
   missing-resource or failed-to-load line. This shows the record and the archive load, not
   which actions the AI picks: nothing in the repository today logs those, so that is R3's
   question.
5. Build the runtime with her module
   ([#213](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/213),
   [#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)) and the id layer
   (`mods/monster_ids` until [#213](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/213)
   moves it), build the code library with them (the fork's `tools/build_game.py`), and take a
   quest that names 125.
6. Fight her normally: let her fly, run, bite and tail-swipe. Pass: the module's log names
   7/64 as the action it ran. A run with the stand-in's script is the control: the line must
   not appear without the converted EMC.
7. Category-4 lines are expected too: action 4 gets its own translated handler in
   [#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136), so the AI's
   category-4 picks are recorded but are not this check's pass.

Status: R3a passes (2026-11-26, quest 10212, a clean profile with only `Ported monster ids`,
its library built from the USA v1.3.0 update by `build_game.py`): the record names
`enemy\em125\data\em125_cmd`, the id layer answers id 125's own archive and record, and
LayeredFS loads `/data/em125.arc`. The run does not show which actions the AI picks, so the
converted script's 3U-only actions are R3's, with a human playing the quest; R3 waits for #216's
module.

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

## UC runtime

The runtime answers MH4U's monster-id-indexed tables for the ids in
[data/ids](../data/ids/README.md): a registered id is answered with the MH4U monster the
registry names as its stand-in, except its resource record, which the runtime builds for the
ported id with its own paths for the kinds of file the port ships and the stand-in's for the
rest; 0 to 123 fall through. The headless check needs no converted monster files, so it runs
before #48 and #49.

Ids 124 to 223 are permanent. A monster ported after that range is full takes a registry id
from 256 up, and the runtime lends it a free byte of 224 to 255 for each quest that names it: at
quest start it rewrites the pooled ids in the loaded `.mib`'s large-monster waves, the reader
hooks answer the lent byte with the pooled monster's rows, and the bytes are freed when the
quest ends. The bytes, the quest data it reads and the fixture are in the runtime's
[README](../mods/uc_runtime/README.md#the-id-pool). No pooled monster ships, so the shipped
registry has no row from 256 up and the pool is exercised through a registry fixture.

| Check | What | Pass |
|---|---|---|
| P1 | the runtime's first-frame self-test, headless | the log shows the ready line, each reader answering the registered ids, the resource record each registered id built with its own id's paths for the kinds and motion slots the port ships and the stand-in's for the rest, its name and notes text from `text/monster_text.bin` and the three message getters answering it, the Hunter's Notes list's own page for the registered ids after MH4U's pages, the path the stand-in's data comes from, ids 0 to 123 passing through, and (with the pooled fixture) a pooled id lent, answered and freed |
| P2 | a quest whose monster is a ported id, played | the reader lines appear when the monster spawns and 0 to 123 still pass through; the Hunter's Notes list shows each ported id's row with its name and its own notes page, and MH4U's own rows and pages are as before; the quest plays, and a quest with MH4U's own monster plays as before |

P1, headless:

1. Build the runtime (`make` in `mods/uc_runtime`) and add it to a user folder's mod library
   (`tools/mods.py add mods/uc_runtime`). Set `selftest = 1` in the installed mod's
   `config.ini`. Build the mod's text table from the player's own dumps into the installed
   mod's folder, and check it:
   `MHUC_DUMPS=<dumps> mhuc text build --dumps <dumps> --out "<user folder>/mh4u-mods/UC
   runtime/text/monster_text.bin"` and `tools/check_text.py --mod "<that file>"`. Build the
   code library with the mod on:
   `tools/build_game.py --dump <MH4U USA v1.3.0 update .cia> --install <user folder>`. The
   build reports 56 hook points: the base 32 and the runtime's 24 new names,
   `QuestFlow::startQuest` being in both.
2. For the pool's lines, use the registry fixture instead of the shipped registry: copy the
   mod, write the copy's headers from `tests/fixtures/registry-pooled.csv`
   (`python3 tools/check_ids.py --registry tests/fixtures/registry-pooled.csv --header
   <copy>/src/ids.h --modules-header <copy>/src/modules.h --write`), `make` in the copy, and
   install that library. It is a registry fixture, not a shipped monster.
3. Run the game headless:
   `mh4u_runner <MH4U USA .3ds> --code <user folder>/recomp/0004000000126300.so --user <user folder> --ms 20000 --log "*:Info"`.
4. Pass: the log has `ready: answering MH4U's monster tables and name/notes message getters
   for 4 permanent and 0 pooled id(s), 124 and up, lending 224..255 per quest, with the files
   each port ships and the stand-in's for the rest`; `text: 4 of 4 entry(ies) from
   text/monster_text.bin; every registered id has a name and notes`; a `self-test: message name
   id 124 -> "Rathian", N UTF-16 unit(s)` line and a notes line per registered id, one
   `self-test: id 124's getters answer its own record; ids 0..123 pass through` per id (the
   getters are called through the game's own entry points), one `self-test: message tables:
   id 1 answers the game's own format; ids 0..123 pass through`; one `self-test: the notes
   list: MH4U's own pages pass through; the runtime's page adds id 124, id 125, id 126,
   id 127 with their own name and notes`; one `self-test: id 124 resource record at <address>, built from
   stand-in 1, names: ...` line per registered id, listing the paths read back from the
   record built in guest memory; one `self-test: id 124 ships model, motions 0,1,2,3,4, camera,
   tail; keeps stand-in 1's paths for motions 5, mef, sound, cmd, efl` line; one for 125
   (`ships model, motions 0,1,2, tail, sound, cmd; keeps stand-in 1's paths for motions 3,4,
   camera, mef, efl`); one for 126 (`ships model, motions 0,2,3,4; keeps stand-in 15's paths
   for motions 1,5, camera, tail, mef, sound, cmd, efl`); one for 127 (`ships model, motions
   0,1,2; keeps stand-in 15's paths for motions 3,4,5, camera, tail, mef, sound, cmd, efl`);
   and, for each reader, `self-test: <reader> answers ...; ids 0..123 pass through`. In the
   124 record the model, motion, camera and tail paths name `em124`, and the motion-effect,
   sound, effect-list and command paths and motion slot 5 still name `em001`. The 125
   record names `em125` for the model, motion slots 0 to 2, the tail, the sound and the
   command, and keeps the stand-in's `em001` for motion slots 3 and 4, the camera, motion
   effects and effect lists. The 126 record names `em126` for the model and motion slots 0, 2,
   3 and 4, and keeps stand-in 15's `em015` for motion slots 1 and 5, the tail, the camera,
   motion effects, the sound, the command and the effect lists. The 127 record names `em127`
   for the model and motion slots 0, 1 and 2, and keeps stand-in 15's `em015` for motion slots
   3, 4 and 5, the tail, the camera, the motion effects, the sound, the command and the effect
   lists; no path may name a file the port's arc does not ship ([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)).
   The 125 sound path is the converted call `mhuc convert monster` writes (#158), and her
   command path is her converted 3U EMC ([specs/emc.md](../specs/emc.md), check A5).
   The factory's and data path's lines name the path the stand-in's files are read from
   (`enemy\em001\data\em001` for stand-in 1, `enemy\em015\data\em015` for the Great
   Jaggi), which the record does not change. With the fixture the ready
   line is `1 permanent and 1 pooled`, its record is `enemy\em256\...` for the one kind the
   fixture's `files` names and the stand-in's for the rest, and the log also has `quest 60001:
   pooled id 256 -> lent 224`, `self-test: quest 60001 names pooled id 256; lent 224; the
   readers answer 224 -> pooled id 256, stand-in 1, its own record`, `quest 60001 ends: freed
   the pool byte(s) 224` and `self-test: the quest ended, so byte 224 is free again`; with the
   shipped registry the pool's line is `self-test: the pool 224..255 is unused: no pooled
   monster id is registered`. MH4U's own monsters were not loaded, so only the self-test's
   mapping shows here; a real spawn's reader lines are P2's.

P2, in game: needs the ported files (#48, #49) and a quest that names id 124
([quests.md](quests.md)), for the pool a pooled monster's row, files and a quest that names
its registry id (256), and its headless prerequisite is P4. It also opens the Hunter's Notes:
each ported id's row appears after MH4U's own pages with its name, its own notes page and its
own getters' text, and MH4U's own rows and pages are as before. Not done.

Status: P1 run on 2026-11-25, USA v1.3.0 update, the code library built with the mod's 16 hook
points (the two quest hooks among them), headless runner. The runs:

- **Shipped registry (2 permanent, 0 pooled):** pass. The log had `ready: answering MH4U's
  monster tables for 2 permanent and 0 pooled id(s), 124 and up, lending 224..255 per quest,
  with the files each port ships and the stand-in's for the rest`; the 124 and 125 records
  named `em124`/`em125` for the model, their motion slots, the tail and the command and kept
  `em001` for the camera, motion effects, sound and effect lists; the ships/keeps lines; every
  reader line with `ids 0..123 pass through`; and `self-test: the pool 224..255 is unused: no
  pooled monster id is registered`. No path named a missing `em124`/`em125` file
  ([#143](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/143)).
- **Pooled fixture (1 permanent, 1 pooled):** pass. The log had the fixture's ready line; its
  124 and 256 records named only `enemy\em124\mod\em124` and `enemy\em256\mod\em256`
  (the fixture's `files` is `model`) and kept the stand-in's `em001` elsewhere; `quest 60001:
  pooled id 256 -> lent 224`; `self-test: quest 60001 names pooled id 256; lent 224; the
  readers answer 224 -> pooled id 256, stand-in 1, its own record`; `quest 60001 ends: freed
  the pool byte(s) 224`; and `self-test: the quest ended, so byte 224 is free again`.
- **Four registered ids, Giadrome and Great Wroggi in (4 permanent, 0 pooled):** pass for the
  records. The log had `ready: answering MH4U's monster tables and name/notes message getters
  for 4 permanent and 0 pooled id(s), 124 and up, lending 224..255 per quest, with the files
  each port ships and the stand-in's for the rest`; the 126 record named
  `enemy\em126\mod\em126` and motion slots 0, 2, 3 and 4, after the builder started naming
  a port's motion slot the stand-in's record leaves empty (Great Jaggi has no slot 4); the 127
  record named `em127` for slots 0 to 2; each record's ships/keeps line and the reader lines
  with `ids 0..123 pass through` were as above; and `self-test: the pool 224..255 is unused:
  no pooled monster id is registered`. The name/notes hooks were not in this run's code
  library, so its text lines were not exercised.
- **Four registered ids with the name/notes hooks (4 permanent, 0 pooled):** pass. The code
  library was built from the three plugins (54 hook points), with the mod's text table in its
  folder. The log had the ready line `ready: answering MH4U's monster tables and name/notes
  message getters for 4 permanent and 0 pooled id(s), 124 and up, lending 224..255 per quest,
  with the files each port ships and the stand-in's for the rest`; the 124 to 127 records
  named `em124`/`em125`/`em126`/`em127` for the kinds and slots their registry rows list and
  kept the stand-in's paths for the rest (the 125 record named `sound\call\em\em125`; the 126
  and 127 records kept `em015` elsewhere); the ships/keeps lines reported the registry's
  masks; every reader line had `ids 0..123 pass through`; `text: 4 of 4 entry(ies) from
  text/monster_text.bin; every registered id has a name and notes`; a `self-test: message name
  id 124 -> "Rathian", 7 UTF-16 unit(s)` line and a notes line per id (118, 223, 75 and 238
  units for 124 to 127); one `self-test: id 124's getters answer its own record; ids 0..123
  pass through` per id; `self-test: message tables: id 1 answers the game's own format; ids
  0..123 pass through`; and `self-test: the pool 224..255 is unused: no pooled monster id is
  registered`. The self-test logged at 3.22 s, when MH4U's message tables were up; the plugin
  now waits for `load_text`'s result before running it.
- **Four registered ids with the notes-list hooks (4 permanent, 0 pooled):** pass. The code
  library was built with the runtime's 25 hook names (56 hook points, the base 32 and the
  runtime's 24 new names), with the mod's text table in its folder. The log had the ready
  line, the 124 to 127 records and reader lines as in the run above; `text: 4 of 4
  entry(ies) from text/monster_text.bin; every registered id has a name and notes`; and
  `self-test: the notes list: MH4U's own pages pass through; the runtime's page adds id 124,
  id 125, id 126, id 127 with their own name and notes`. No `isn't a hook point` line
  appeared. The notes screen was not opened, so its page count, the runtime page's widgets
  and its detail page are P2's.

The name/notes message getters and the text table were in the run above: the code library
has the mod's 19 hook names (50 hook points with the mod alone, 54 with the three plugins) and
`text/monster_text.bin` was built from the dumps (4 entries) and passed `tools/check_text.py
--mod`. The notes-list run then rebuilt the library with the mod's 25 hook names (56 hook
points) and the same text table. The Python side is checked without the game: the message
tables by LM1 (specs/lmd.md).

No `isn't a hook point` line appeared in any run. P2 is not done; until it is, whether the
files a port does not ship are tolerated as missing is unverified.

After that run, 125's registry row gained `cmd`
([#159](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/159)) and `sound`
([#158](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/158)), and 126 and 127
were registered for Giadrome ([#161](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/161))
and Great Wroggi ([#166](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/166)), so
the next P1 run's 125 record also names `sound\call\em\em125`, the converted sound call
#158's `mhuc convert monster` writes, and its 126 and 127 records name `em126`/`em127` for the
model and the motion slots their rows list while keeping the stand-in's `em015` elsewhere;
#159 added `cmd` on the plan to convert 125's EMC; that converter now ships ([specs/emc.md](../specs/emc.md), check A5), so her row lists it and a current P1 run's 125 record names her own script. That run is the four-id run above: its records, masks, text and readers pass.

After that run, 124's registry row gained `camera`
([#157](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/157)), so the next P1 run's
124 record names `enemy\em124\mot\e124_cam` (the converted list `mhuc convert monster` writes)
and its ships/keeps line lists the camera among the kinds it ships; that part of P1 has not
been re-run. After P4's 2026-11-26 run, 124's row lost `cmd`: the converter ships MHXX's EMC as
is, and with it the quest reached the factory line and then froze on the splash, while the same
archive with the stand-in's `em001_cmd` in the command slot loads the map (P4's Result). So
124's record now keeps the stand-in's script, and the ships/keeps line step 4 lists is the one a
P1 run reports.

### The quest's load, fixed (P2, headless)

The P4 harness (#144) starts quest 10212; the map/area init builds the engine's enemy resource
path `data\emNNN` from the quest's wave monster id (0x00bc3284, the format at 0x00e062a4) and
asks the engine's own archive loader for it. With a ported id the path is `data\em125`: the
engine never asks the readers the plugin answers, and the init waits in state 1. Two parts fix
that, both outside the engine:

1. The quest file is written in place: `mib4_set_wave_monster` keeps MH4U's own quest bytes and
   changes only the large-monster wave's id. The builder's layout shifts the texts and the
   map/area init reads a stale zone index (99); the in-place path is covered by
   `tests/test_with_game_files.py` (an unchanged patch returns the file exactly).
2. `mods/uc_runtime` hooks the `data\em%03d` builder (0x00b7300c) and answers a registered id
   with the stand-in's `data\em001`; ids 0..123 pass through. The error reporter and the engine
   mutex are not touched.

Result (2026-11-25, USA v1.3.0 update, headless runner, the #144 route): the 125 quest starts and
the map loads; the reader lines, the map and the timing are P4's result below. The load is slow
(about 76 s from the departure) but it completes, and the base quest with the original file is
the control (map at about 60 s). 124 (GU) uses the same two parts; P4 has its route and result.

### The enemy data the monster spawns with (P2, headless)

The map, the archive and the resource record load, but the monster still does not appear: the
quest task's presence array gates the enemy data. The task (`0x0065bcd0`) fills a 124-byte
array at `task + 0xd4`, one byte per MH4U id, from the quest's monster set, and in state 0
(`0x0065bd7c`) calls `loadEnemyData` (`0x00689490`) for every id whose byte is set, 0 to 0x7b.
A quest that fields a ported id sets a byte past the array, which the loop never visits: the
stand-in's data is never loaded, `enemyData::get(stand_in)` returns null, and the first caller
dereferences it (`ldr r0,[r0,#0x18]` at `0x00922160`; 553,321 `UnmappedAccess` reads in the
next 100 s without this part).

`mods/uc_runtime` finds the starting quest's loaded `.mib` with the lookup the id pool
already uses (`QuestFlow::startQuest`, `0x00b7c010`), reads the registered ids its large-monster
waves name, and sets their stand-ins' bytes in the presence array before the state 0 preload.
The game's own loop then loads the stand-in's data, with its own `loadEnemyData` call, exactly
as for an MH4U quest that fields the stand-in. A quest that names no registered id is
untouched.

Procedure:

1. Deploy the port's own archive at `data/em125.arc` (the #203 conversion: the port's files
   plus the stand-in's kept entries, with MH4U's material signature) and the quest whose large
   monster is 125.
2. Build the code library with the runtime's hooks, now including `uc_questTask` (`0x0065bcd0`).
3. Run the P4 route (#144) headless for 150 s, count `HW.Memory UnmappedAccess`, and take
   screenshots after the factory.

Result (2026-11-25, USA v1.3.0 update, headless runner, the #144 route): **pass.** The run
logged `quest 10212: id 125 -> stand-in 1 marked present so the state 0 preload loads its enemy
data` at 43.87 s, `quest task: marked stand-in 1 present before the preload` at 43.96 s, then
the preload's first `data path: id 1 is MH4U's own; passed through` at 46.27 s: the marked row
made the stand-in the first id the loop loaded. The resource load and the factory followed at
47.57 s (`resource load: id 125 -> its own record`, `factory: id 125 -> stand-in 1`), and
`HW.Memory UnmappedAccess` was **0** for the whole 150 s (553,321 without the marking, the
first at `0x00922160`). P2's headless half passes; a player's run and the base quest's in-game
control remain. The monster is created and placed at the wave's spawn in area 3 (`enemy + 0xf80`
holds the wave's position), but nothing is drawn there yet: that is
[#203](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/203)'s render check.

## A converted material loads (M3)

MH4U's rMaterial load (`0x00be7000`) accepts only its own MRL signature at +0x10: it compares it
with the value the engine holds and refuses the file otherwise ([specs/mrl.md](../specs/mrl.md)).
MH3U's material files carry `0x3810b2e2` where MH4U's own carry `0xcec1aa61`, so the archive that
shipped the source material as-is never completed its load (the area init stayed in state 1 with
the resource's `+0x50` at `0x200`/`0x210`; #182). `mhuc convert monster` now writes MH4U's
signature and keeps every other byte of the material.

| Check | What | Pass |
|---|---|---|
| M3 | a converted MH3U material loads in MH4U's archive loader | the archive resource's `+0x50` reaches the done bit, the resource load and the factory run for 125, and `HW.Memory UnmappedAccess` is 0 through the load |

Procedure:

1. Convert MH3U Rathian for id 125 with the self-sufficient archive of #182 (`--mh4u-romfs`,
   the stand-in's kept entries appended). The material's two files in it are byte for byte what
   this branch's converter writes: the run above was made on the #182 working tree, which carries
   the material change only on top of it. Deploy the archive as the port's `data/em125.arc` in
   the P4 profile.
2. Run the P4 route headless for 150 s with the mgr probe on the manager's load request
   (`0x00c16370`) and on the area init (`0x00bc31d4`), and count `HW.Memory UnmappedAccess`.
3. Read the probe's status: `0x200` while the archive loads, bit 0 set when it is done.

Result (2026-11-25, USA v1.3.0 update, headless runner, the P4 route): **the material side
passes.** The manager is asked for `data\em125` at 51.54 s and returns the archive object; the
area init polls its `+0x50` at `0x00000200` in state 1, then reads `0x00928a01` at 52.64 s with
the init back in state 0. `resource load: id 125 -> its own record` and `factory: id 125 ->
stand-in 1` follow at 52.97 s, and `HW.Memory UnmappedAccess` is 0 up to that point. The same
archive with the source signature stalls exactly as #182 recorded.

The map itself loads: the screenshot at 148 s shows the player and the two Palicoes in the
Ancestral Steppe. **The Rathian is still not drawn**: from the factory line the model-missing
read storm starts (519,678 unmapped reads by 150 s, at the same PCs as #182: `0x0092076c`,
`0x00936a34`, `0x00944e60`, `0x00920578`, `0x0091518c`). The material loads; the model binding to
it is the remaining cause, and it is #203's model-side half. (That storm was the stand-in's
missing enemy data, fixed by #182's preload; with it the run has 0 unmapped reads.)

### The material's shader ids (X4, game)

A converted material that loads still names its shader objects by MH3U's slots unless its ids
are moved to MH4U's package ([specs/mfx.md](../specs/mfx.md)): with the signature alone
rewritten, MH4U read 3U Rathian's blend state as the sampler `SSLinear`. `mhuc convert monster
--mh4u-romfs` now moves every id; its 3U Rathian material's state ids are MH4U Rathian's own
(mfx check X2).

Procedure:

1. Convert 3U Rathian (`mhuc convert monster --id 125 --romfs <MH3U RomFS> --mh4u-romfs <MH4U
   RomFS> --out <mod folder>`, then the sound mode), add the mod and the quest of #182, and run
   `tools/mods.py deploy`: the runner and the frontend read the deployed copies under
   `load/mods/<program id>/romfs/`, not the mod library. Turn "Force a monster action" off.
2. Play the 125 quest to the wave's area (area 3) and look at the Rathian; compare with the
   stock quest's MH4U Rathian at the same spot.

Result (2026-11-26, USA v1.3.0 update, the Qt frontend, the maintainer's walk): **pass.** In
area 3 of the Ancestral Steppe, 3U Rathian stands at the wave's spawn, drawn with her own model
and textures, and the minimap marks her in that area. Before the ids were moved, the same walk
found no Rathian. She plays her limp animation in a loop: MH4U's AI was driving her while
MH4U's handler ran, so the motion number it asked for picked another motion in her MH3U
lists — not a material fault. Under decision 0002's 2026-11-26 amendment her own handlers ask
for her own animations
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216) and its slices).
Headlessly the 125 quest loads with the converted archive (0 unmapped reads),
but the harness's route never puts a large monster on screen: with the wave moved to area 1,
MH4U's own Rathian (id 1) was not in view either. So this check is a player's walk, not a
headless run.

## A ported camera's cut-in (C2)

MH4U's camera list ([specs/camera.md](../specs/camera.md)) holds the cameras an action posts by
number; a ported monster brings its source game's list, converted to MH4U's version 4, in its
arc at `enemy\emNNN\mot\eNNN_cam` (the `camera` kind in [data/ids](../data/ids/README.md)).
124's row lists `camera`, and `mhuc convert monster --id 124` writes MHXX em001's own list
there. The code side needs that arc and the runtime's record built with the camera bit (P1);
the in-game half would need a quest that spawns the id (#144), and is waived below.

1. Run `mhuc convert monster --id 124 --romfs <MHXX RomFS> --mh4u-romfs <MH4U RomFS> --out
   <mod folder>` on the player's dumps: its `data/em124.arc` holds `enemy\em124\mot\e124_cam`,
   the LCM 4 conversion of `enemy\em001\em001_00\mot\em001_00_cam` (the game_files test
   `test_convert_monster_ships_the_gu_rathians_mhxx_camera` checks the entry against MHXX's
   list). Regenerate `mods/uc_runtime/src/ids.h` and rebuild the code library (P1 step 1).
2. The visual half — force an action whose handler posts a camera id (MH4U's event is
   `0x00934544`, and the handler's call names the id), and see whether the view cuts to MHXX's
   framing of the monster rather than MH4U Rathian's — is **waived by the maintainer
   (2026-11-26)**. No in-game camera check is planned; this paragraph records what the waiver
   covers, not a step to run.

**A 3U id is outside C2.** Decision [0014](decisions.md#0014-a-3u-monster-ships-no-camera)
keeps the stand-in's camera path for a ported 3U id and no 3U row of `data/ids/registry.csv`
lists `camera`; the camera code check for a 3U monster is C4 in
[specs/camera.md](../specs/camera.md#mh3u-at-mh4us-camera-moments-checks-c3-and-c4), and no
in-game run is planned for it either.

Code side: pass (2026-11-26). 124's registry row lists `camera`, `mhuc convert monster --id 124`
writes the converted list at the record's path, `tests/test_with_game_files.py` checks the
entry against MHXX's own list, and the archive no longer carries the stand-in's `e001_cam`.
Status: closed (2026-11-26). Code side pass; the visual check is waived by the maintainer, so
no in-game run is planned and #144's quest-load proof is no longer needed for it.

## A ported effect at the source frame (E1)

A ported monster's motion effects time its visual effects to its own animations. MH4U plays an
effect when one of a motion's event-block entries fires: the event's remap id selects a record in
the MEF, and the record names the effect and where it appears ([specs/mef.md](../specs/mef.md)).
The port has to write both: the source's events into its own motion lists (the source's motion
lists carry no such ids) and the MEF records keyed to them, from the source game's ESQ (MH3U) or
PSL (MHXX). This check confirms the timing, which is the part a file check can miss: the source
event's motion and frame are read and checked against the source's motion list (FX5, FX6), while
the source's effect parameters and the MEF record's fields are not placed yet, so
`mhuc convert monster` still refuses an `mef` kind and the row's `files` does not list
`mef`/`efl` yet.

1. Take MH3U's effect sequence for the monster out of its archive (`effect\esq\em\emNNN`) and its
   effect lists (`effect\efl\em\emNNN\...`); for MHXX, the motion list's PSL
   (`effect\psl\enemy\...`) and its lists. The converter will write the source's events into
   the ported motion lists and a MEF as MH4U reads it, and the effect lists as MH4U's version. Check
   that the id's row in `data/ids/registry.csv` lists `mef,efl`, regenerate
   `mods/uc_runtime/src/ids.h` and rebuild the code library (P1 step 1).
2. Play an action whose source effect is visible and timed: a fireball or a breath is easiest to
   time. `mods/force_action` (R1p) plays a chosen action without the AI; the action's handler
   starts the same animation in both games, so the effect's frame is the frame of that animation.
   Record the source game's move and the port's move frame by frame (the emulator's frame advance
   and screen capture, outside the repository), or compare two recordings at the same frame rate.
3. Pass: the effect first appears on the source game's frame of the same animation — the frame
   FX5 reads in the source ESQ/PSL, not MH4U's own Rathian's timing — on the same bone and at the
   same offset and scale, and the P1 log's line for the id names the port's own `mef` paths.
   Fail: MH4U Rathian's fire, dust or wind (the record kept the stand-in's effect paths and the
   port ships no `mef`), no effect at all (the ported motion list's event ids don't reach the
   MEF's keys), or the effect at another frame (the event frame or the source motion's frame
   count is wrong).

**What is done headless (FX10, FX11 in [specs/mef.md](../specs/mef.md#checks)).** The spawn tables
are laid out and every one of MH4U's 6,216 MEF records resolves through them on the real files, the
game's own code agreeing on a 696-sample cross-check; and the addition path runs on that code: two
`.data` writes make an unused type's chain name the port's own `effect\efl\em\em125\em125_000`.
The converter part still needed for this check is [specs/mef.md](../specs/mef.md#a-3u-effects-assets):
rewrite the source effect list's block paths, carry its model, materials, textures and effect
animation, and write the MEF record with the port's type, time and bone. The one link no file check
covers is the effect manager resolving the port's path to its own arc.

Status: open; the visual half is the maintainer's, and it waits for the asset conversion (the effect
list's paths, its model, materials, textures and effect animation) and #144's quest-load proof.

## A ported monster's own voice (A1)

A ported monster's resource record names its sounds by one path, `sound\call\em\emNNN`: the
sound call, which names the requests, banks and waves the monster's code and motions play
([specs/sound.md](../specs/sound.md), check SN7). `mhuc convert monster` writes the set from the
source game's archives into the port's own arc. This check hears it; it needs the port's other
files so the monster spawns (#48, #49), the `sound` kind on the id, the plugin's record built
with it (P1), and a quest that spawns the id (#144). It is the in-game half of SN9.

1. Convert the sound set: `mhuc convert monster --id 125 --arc <MH3U
   arc/enemy/em001.arc> --sound-arc <MH3U arc/sound/se/em/em001/snd_em001.arc> --out <mod
   folder>` (MHXX: `--from mhxx --id 124 --arc <MHXX arc/enemy/em001_00.arc>`). The port's
   `data/em125.arc` gains the sound call, 48 waves, the bank and the request, every path under
   `sound\se\em\em125\...` or `sound\call\em\em125`. Check that 125's `files` in
   `data/ids/registry.csv` lists `sound`, regenerate `mods/uc_runtime/src/ids.h` and rebuild the
   code library (P1 step 1).
2. Spawn the ported monster in a quest (#144) and let it roar, bite, fly and take a hit; a roar
   is an action, so `mods/force_action` (R1p) can play one without waiting for the AI.
3. Pass: the sounds are the source game's — MH3U Rathian's roar, not MH4U Rathian's — at about
   the volume MH4U's own monster sounds play at, and the footsteps and attack sounds match the
   source game's on the same moves. The P1 log's line for 125 names `sound\call\em\em125`
   among the record's own paths.
   Fail: MH4U Rathian's voice (the record kept the stand-in's `sound\call\em\em001`), silence
   (a path or an id the request doesn't answer), or a sound at the wrong pitch or volume, which
   would point at the request words the converter keeps from MH3U
   ([specs/sound.md](../specs/sound.md#the-request-records-words)).

Status: not done; waits for #48, #49 and #144.

### The quest's headless load (P4)

| Check | What | Pass |
|---|---|---|
| P4 | a headless run starts quest 10212 with a ported id (125 in the 3U profile, 124 in the GU one) and the quest loads past "Now Loading" | the run draws the quest's "Royal Assassination" splash, then the quest's map with the player (and the two Palicoes) in it, no hang, and the log has the ported id's preload, resource and factory lines; the model's render is not part of this check (X4 runs it in game) |

**What "loaded" means.** The departure is accepted and the quest's "Royal Assassination" splash is
drawn; then the quest's map is drawn with the player in it (on these saves, the two Palicoes and
the quest HUD as well), and nothing hangs. At that point the log has, for the ported id, the
preload's lines — `quest 10212: id NNN -> stand-in N marked present so the state 0 preload loads
its enemy data`, `quest task: marked stand-in N present before the preload` and the stand-in's
`data path: id N is MH4U's own; passed through` — then `data resource: id NNN -> its own
archive`, `resource load: id NNN -> its own record`, `effect lists: id NNN -> its own record` and
`factory: id NNN -> stand-in N`, the game opening the port's own `data/emNNN.arc` and creating the
monster's entity from the record the runtime answers. The whole run logs no `HW.Memory
UnmappedAccess`: the preload's enemy data (#182) and the archive's converted material (#203) leave
nothing the game reads as a pointer. Loaded is **not** visible: the harness's route stops at the
camp, so no large monster is on screen; the screenshots show the map, the hunter and the two
Palicoes, and the model's render is X4's in-game check.

The per-move checks (#113, #116) need this load. This check starts one without a window: the
runner's `--input` script plays from the title to the Gathering Hall's Low-rank quest counter,
posts quest 10212, and leaves the quest to load.

1. Profiles: two user folders, each a copy of the maintainer's save. Restore `system` and
   `user1` to `user3` before each run: the game writes the save when a quest starts, and the
   input script's menu and counter presses no longer land on a profile that already started one.
   The 3U one has the wave of the deployed `loc/data/quest01.arc` naming monster 125 and
   `data/em125.arc`; the GU one names 124 and deploys `data/em124.arc`. Both have the code
   library built with `mods/uc_runtime` on (`selftest = 1`), and the quest written in place from
   MH4U's own `.mib` (P2): only the wave's monster id changes; the layout and the texts stay.
   Build the library with `tools/build_game.py --dump <MH4U USA v1.3.0 update .cia> --install
   <user folder>`; the session's shared build (the runtime and `force_action`, 54 hook points)
   can be copied into `<user folder>/recomp/` instead, with the plugin list written for the
   profile's enabled mods. Put the enabled mods in the profile's `load/mods/<program id>/` with
   the fork's `tools/mods.py deploy` (the runner reads the deployed copies, not a mod library).
   The port's archive is what `mhuc convert monster --id NNN --romfs <source RomFS>
   --mh4u-romfs <MH4U RomFS> --out <mod folder>` writes, the sound mode too for 125. 124's row
   ships no `cmd`: MHXX's EMC is not converted yet, and the as-is one froze the quest after the
   factory line (the Result below); 125 ships her converted 3U EMC.
2. The 3U profile's route (125) is the maintainer's recorded `.ctm`: 7-15 s, A through the Circle
   Pad Pro and break screens, the title, the save and the character select; 26-32 s, R held with
   the circle pad up, running through Val Habar; 33-52 s, A through the World Map, the Gathering
   Hall fast travel, the Hall's Low-rank quest counter, the 2★ list and "Royal Assassination";
   the departure A is at 52.3 s. The run draws the "Royal Assassination" splash and the map at
   about 128 s, so it needs at least 150 s emulated (the stock quest draws its map at about 60 s).
3. The GU profile's route (124) keeps the recorded menu phase but re-anchors it after its own
   boot; its steps are below. It departs at 54.3 s, draws the splash at about 62 s and the map at
   about 70 s, so a 140 s run covers the screenshot series with room to spare.
4. The input script stays outside the repository. It can be written from the route or converted
   from an Azahar `.ctm` recording of the same run: the movie holds the controller states in the
   order the HID service consumes them, and a pad record is one HID update, 234 per emulated
   second, so a record's time is about (index + 1) * 1000 / 234 ms. The screenshot schedule
   matters: a drawn frame pauses the emulated clock before each screenshot, so a route timed
   under one schedule drifts under another; keep the schedule the route was proved under.
5. Run it under the session's headless-run gate, from the workspace root:
   ```
   game_files/work/locks.sh headless -- mh4u_runner "<MH4U USA .3ds>" \
       --code <user>/recomp/0004000000126300.so --user <user> --ms 150000 --speed 0 \
       --input "<script>" --shots <dir> --shot-every 4000 --shots-from 56000 \
       --draw-window 150 --log "*:Info"
   ```
   Screenshots show the route; `--draw-window` without `--shots` draws nothing and is much
   faster.
6. Pass: the map with the player in it and the factory line for the ported id, as defined above.
   A stock quest (MH4U's own id 1) started with the same script is the control.

Result (2026-11-26, USA v1.3.0 update, headless runner, fresh save copies, the code library and
mods of this branch):

| Profile | id | Route | Departure | Splash | Map | From the title |
|---|---|---|---|---|---|---|
| 3U | 125 | recorded `.ctm` | 52.3 s | "Royal Assassination" | 128 s, player and two Palicoes, HUD | 128 s; give 150 s |
| GU | 124 | the route below | 54.3 s | 62 s | ~70 s, player and two Palicoes, HUD | ~70 s; the 140 s run covers the series |
| 3U | 1 (control) | recorded `.ctm` | 52.3 s | "Royal Assassination" | 62 s, player in the Ancestral Steppe, HUD | 62 s |

- **125: pass.** The log has `quest 10212: id 125 -> stand-in 1 marked present so the state 0
  preload loads its enemy data`, `quest task: marked stand-in 1 present before the preload`, `data
  path: id 1 is MH4U's own; passed through`, `data resource: id 125 -> its own archive`,
  `resource load: id 125 -> its own record`, `effect lists: id 125 -> its own record` and
  `factory: id 125 -> stand-in 1`; the run exited 0 with no `HW.Memory UnmappedAccess`.
- **124: pass.** The same lines for 124 (`data resource: id 124 -> its own archive`, `resource
  load`, `effect lists`, `factory: id 124 -> stand-in 1`), exit 0 and no `HW.Memory
  UnmappedAccess`; the screenshot series shows the map and the hunter at 70 s. That run's row
  was `model,motions=0-4,tail`; 124's converted `camera` ([#157](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/157))
  joined the row afterwards, and the load has not been re-run with it.
- **Stock control: pass.** The same script with MH4U's own id 1 puts the player in the Ancestral
  Steppe at about 62 s, quest HUD up, no hang, no unmapped reads; its log has no runtime lines,
  since the stock profile enables no plugin.
- **The 125 wait is a load, not a hang.** The map comes about 76 s after the departure, the
  runtime's lines each fire once and the wait is not a round timeout: the game is loading and
  processing the ported monster (its model and motions), which the stock quest does in about 8 s.
- **124's converted MHXX EMC hung the load.** With the row shipping `cmd`, the run reached the
  factory line for 124 and then froze on the splash for the rest of two 180 s runs (the frames
  from 65 to 180 s are identical), while the same archive with the stand-in's `em001_cmd` in the
  port's command slot instead loads the map at about 70 s. MHXX's EMC is copied as is; its group
  rows and opcode table are not MH4U's ([emc](../specs/emc.md)), so shipping it is unverified to
  load and hung the load. 124's row now keeps the stand-in's script until an MHXX EMC
  converter ships; 3U's converts (check A5), so 125 ships her own.
- **Loaded is not visible.** The harness's route stops at the camp: the map shows the hunter and
  the Palicoes but no monster, and no unmapped reads are logged. The model's render is X4's
  in-game check; the headless run proves the map and the monster's factory line only.

The harness is not specific to these two: any registered id can be written into the same quest in
place and takes the same route. Giadrome (126) and Great Wroggi (127) have their records and
stand-in 15; their load proof is #189's and has not been run.

#### The GU profile's route

The recorded `.ctm`'s boot phase is timed on the 3U and stock saves. On the GU profile's save (the
maintainer's three-hunter save) the same presses do not land: the character select is not up at
7.1 s, the recorded walk and counter presses (25.7 to 52.3 s) all fire before the hunter is in Val
Habar, and the quest never starts (the log has no quest line).

The GU route keeps the recorded route's menu phase but drives the boot itself and re-anchors that
phase after the character is in town:

1. From 5 to 24.5 s: A every 1.5 s, 14 presses. The first dismisses the Circle Pad Pro screen; the
   character select is up at about 13.5 s and the save's first hunter is in Val Habar at about
   27 s.
2. From 27.7 s: the recorded route's events from its 25.7 s, every time 2000 ms later. R held with
   the circle pad up for 6.3 s runs up Val Habar's street; the A presses then enter the Gathering
   Hall (it loads from about 35 s), answer the Low Questatrix's high-rank speech, open the 2★ list
   and pick "Royal Assassination". The departure A is at 54.3 s and the splash is drawn at about
   62 s.
3. The script stays outside the repository, like P4's. It is the converted `.ctm` with those 14
   presses prepended and the events at 25.692 s and later shifted by 2000 ms.
4. Run it with the code library built with `mods/uc_runtime` (P1) and the GU profile's deployed
   `data/em124.arc`, and with the screenshot schedule below. The schedule matters: a drawn frame
   pauses the emulated clock before each screenshot, and the counter's speech and the rank menu
   are timing-sensitive, so a route timed under one schedule drifts under another.
   ```
   game_files/work/locks.sh headless -- mh4u_runner "<MH4U USA .3ds>" \
       --code <user>/recomp/0004000000126300.so --user <user> --ms 140000 --speed 0 \
       --input "<script>" --shots <dir> --shot-every 2500 --shots-from 15000 \
       --draw-window 150 --log "*:Info"
   ```
5. Pass: the log shows the quest's map loading with the player in it and no hang, and the ported
   id's factory and resource reader lines.

Result: pass, P4's table above has the route's timings and the log lines. The profile's save is
restored before the run (P4's step 1): a profile that already started a quest boots into a state
the recorded route no longer matches, and the counter presses then land before the hunter is
there. The 124 archive's command slot carries the stand-in's `em001_cmd` (the row ships no
`cmd`); with the converted MHXX EMC the load freezes after the factory line (P4's Result). The
script and the screenshots stay outside the repository.

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
3. Put the runtime's line in the code library's `<program id>.plugins.tsv`
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
are checked without a monster: the source facts against MHXX's module and MH3U's code, the
state machines against a fake host, and the module's self-test in a headless run.

| Check | What | Pass |
|---|---|---|
| T1a | `tools/check_actions.py` reads [data/actions/rathian-gu.csv](../data/actions/rathian-gu.csv) against MHXX v1.4's `roEm001.cro`, and [data/actions/rathian-3u.csv](../data/actions/rathian-3u.csv) against MH3U USA's `code.bin` | every row's case block, handler unit and first motion constant match the source dispatcher; counts and ids only |
| T1b | `make -C mods/uc_runtime test` | the module's routing and its call sequences and frame values match the source's order, and a changed value fails it |
| T1c | a headless run of the code library built with the runtime | the log has the runtime's ready line, the GU module's ready and self-test lines and the float stubs' address; the runner exits 0 |
| T1d | the in-game per-move check | R2p |

T1a: MHXX v1.4's `roEm001.cro` and its `static.crs` come from the player's own dump.

```bash
MH4U_FORK=<fork> python3 tools/check_actions.py --module <roEm001.cro> --crs <static.crs>
```

Last result (2026-11-25): pass. 13 actions; blocks 13/13, handlers 12/13 (category 17 has
none), first motions 9/13; translated 12 (3/98, 12/1-3, 4/27-32, 8/0 and category
17), MH4U's own 1 (12/0), pending 0. Changing a ledger motion makes it exit 1 and name the
id.

T1a also checks the 3U ledger against MH3U USA's `code.bin` and its `exheader.bin`:

```bash
MH4U_FORK=<fork> python3 tools/check_actions.py --game mh3u --exheader <exheader.bin> \
    --code <code.bin> --dispatcher 0x00687d30 --range 0x686000 0x69b000
```

Last result (2026-11-26, issues #216 and #220): pass. 191 actions; blocks 191/191, handlers
182/191 (the other 9 are inline), first motions 132/191; translated 22 (0/0, 0/1, 0/2, 0/3,
0/4 and 0/6, and category 3's part 2's sixteen ids), pending 169. Changing a ledger motion
makes it exit 1 and name the id.

T1b, last result (2026-11-26): pass, the call sequences checked across 3/98's three frames,
the 12/1-3 blocks, 4/27-32's states, 8/0's three states and category 17's no-op and
base-update paths, and the routing (the module's id runs it; an MH4U id and a registered id
without a module fall through). Deleting the factory association fails the routing check with
`the module's monster didn't run 3/98 (0 calls, 1 original, 0 skipped)`. Changing 3/98's `6.0`
to `5.0` fails it with the motion line; making 17/3 a no-op (`index > 3`) fails it with 17/3's
line; giving 4/27 the fast turn step fails it with the turn line; changing 8/0's motion speed
`4.0` to `5.0` fails it with 8/0's line (the checks in `tests/test_module.c`). Proofs of the
last four were run when the plugin was translated (#139-#142); this session proved the routing
and re-ran the suite.

The 3U module's tests are `tests/test_rathian_3u.c` (the shell: the factory association for
125, the routing, the ready line and the self-test) and one program per action family under
`tests/rathian-3u/` (category 0's is `cat0.c`, for #216; category 3's part 2 is `cat3b.c`, for
#220); `make test` discovers the family tests from the directory (issue #268). Last result
(2026-11-26): pass. The shell test
checks that 125 runs the module, that an MH4U id and a registered id without a module fall
through, that an id the slice does not carry (`1/0`) is logged once and left to MH4U's
dispatcher, and the ready and self-test lines. The family tests check the six ids' call
sequences — 0/0 and 0/4's 150.0 delay and countdown, 0/1's inline delay, 0/2's mode and
three-way state test, 0/3's data record and fall rate, 0/6's vertical step and -75.0 clamp,
and the three base handlers' `0x009167b4`, `0x0094f408`, `0x00b05da4`, `0x0093d870`,
`0x0092e99c`, `0x0068882c` and `0x0090ef74` calls, with the setter's fifth stack argument.
Breaking the 0/2 base handler's sub-state choice (`index = 2` to `0`) fails `tests/family-cat0`
with `0/0 state 1 doesn't start the sub-state 2 action`, plus the 0/1 and 0/2 fall-through
lines; reverting makes it pass. Category 3's part 2's test checks the sixteen ids' call
sequences — the curve, the position advance at 0.5, the height branches, the turn rates halved
to MH4U's helpers, the motions `0x1a`/`0x2d`/`0x3d`/`0x3e`/`0x207`/`0x219`, 3/11's start, the
next actions and the two base handlers — and the two blocked calls' log lines. Changing the
motion speed `6.0` fails it with `3/6 doesn't request motion 0x1a at 6.0`; changing the
two-joint turn's 0x40 fails it with `3/8 doesn't halve 0x8438e8's rate`.

The family list's discovery is `tests/test_family_discovery.c`, for issue #265: it puts a probe
family the module does not ship in a directory of its own, has `tools/gen_families.py` write
its list (the build's step), and calls the entry the list found; it fails with `the generated
list doesn't name the probe family` when the generator leaves the file out.

The family tests' discovery is `make test`'s `test-family-discovery`, for issue #268: it puts a
probe family test in a directory of its own and has the wildcard's list build and run it; when
the wildcard leaves the file out, `test-family-tests` fails with `no family tests in
tests/probe-tests`. Last result (2026-11-26): pass.

T1c: a headless run of the code library built with the runtime, with `selftest = 1`. The log
must have the runtime's ready line, each module's ready and self-test lines and the guest
stubs' address; the runner must exit 0. The GU module's ready line is
`ready: translating 12 of GU Rathian's 13 MHXX-only actions on monster 124`; the 3U module's
is `ready: translating 22 of 3U Rathian's 191 actions on monster 125` (after #216 and #220),
with cat0's `selftest: 6 of the 191 actions`, cat3b's `selftest: 16 of the 191 actions` and
both `field map anchors`/`selftest: open:` lines.
The 3U module's run is the 125 quest's route (the P4/session125 input). The build has to add the runtime's
`uEnemy::dispatchAction` hook point, so it is rebuilt from `--install <user dir>` after the
runtime's `mod.json` changed. The runner must carry ABI 4: the one in the build tree predated
ABI 4's merge into the fork and refused the runtime, so rebuild its `mh4u_runner` target from
the current fork before the run.

Last result (2026-11-26, MH4U USA v1.3.0, the runtime built into the game's code library, the
runner rebuilt from the fork's `uc/main`, headless runner): pass. The build reported 53 hook
points (the 52 before it plus `uEnemy::dispatchAction`) and one native plugin. The log had the
runtime's ready line, then `ready: translating 12 of GU Rathian's 13 MHXX-only actions on
monster 124`, then `selftest: 12 of the 13 actions: ... 17 <- the gate 0x008d5bd4 + MH4U's
base update 0x00911b48 (slot 89, MHXX's slot 244)`, the line naming 12/0 as MH4U's own
`0x006d524c` and 8/0's leaf, and `selftest: float stubs at 0x08e45550 (384 bytes, the game's
heap)`; the runner exited 0. No monster spawned, so no translated action ran: the in-game
side is R2p.

That "no pending slice" covers only the 13 MHXX-only ids; under decision 0002's 2026-11-26
amendment her own handler runs for every action id, shared ids included, so 12/0 is not MH4U's
to keep and the set the self-test counts stays open until the GU module's shared-id work.

The 3U module's run (2026-11-26, USA v1.3.0, the runtime on the session's shared code library,
the 125 quest's route, `--ms 150000`): pass, exit 0. The log has `ready: translating 6 of 3U
Rathian's 191 actions on monster 125` and cat0's self-test lines (the run predates #220),
then quest 10212's `id 125 -> stand-in 1
marked present` and `data resource: id 125 -> its own archive`; the runtime's own self-test
and the GU module's lines are in it too.

The 3U module's run after #220 (2026-11-26, USA v1.3.0, the session's shared code library, the
ABI 4 `mh4u_runner` rebuilt from the fork, `--ms 5000`): pass, exit 0. The log has the runtime's
ready line, `ready: translating 12 of GU Rathian's 13 MHXX-only actions on monster 124`, then
`ready: translating 22 of 3U Rathian's 191 actions on monster 125`, cat0's `selftest: 6 of the
191 actions` and cat3b's `selftest: 16 of the 191 actions: 3/6, 3/13 and 3/16 <- 0x0068e448 ...`,
its `selftest: field map anchors: +0x5/6/7 -> +0x144/145/146 ...` line and its
`selftest: open: 3U's 0x0064325c (#55) is left out of 3/6/3/16, and 0x00839598 (#55) of 3/8 ...`
line, and the float stubs' address. The 125 quest route was left to #216's run above: the
module's handlers are T1b's and the self-test runs on the first frame, so a boot run exercises
the new lines.

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
[the runtime's README](../mods/uc_runtime/README.md#floats-the-guest-stubs). The fork's
[#134](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/134) adds float and `r3`
arguments to the plugin ABI; when it lands, the stubs give way to that `call`.

## Calling the engine with r3 and floats from a plugin (P4)

ABI 3's `call` sets r0-r2 and returns r0. ABI 4 adds
`call2(call, addr, r0_r3, s0_s1, s0_out)`, which sets r0-r3 and the float arguments s0 and
s1, returns r0 and, through `s0_out`, the function's s0 (a float return). This check calls a
game function that stores the arguments it receives, so the log shows they arrived: MH4U USA
v1.3.0 `0x0022e43c` stores r3 at `+0` and r2 at `+2` of the block in r0, s0 at `+8`, and the
remainder of s1 divided by a count from r1 at `+0xc`; with r1 = 0 the count is 1, so s0 comes
back as 10.0f and the remainder is 0. It reads and writes only that block, so it needs no
monster and no quest.

| Check | What | Pass |
|---|---|---|
| P4 | a plugin calls `0x0022e43c` through ABI 4 `call2` in a headless run | the log shows the host's ABI 4 and `call2 ... -> r0=<block>, out=10; block +0: r3=0xbeef r2=7, +8: s0=1.5, +0xc: remainder=0`; the runner exits 0 |

1. Build the headless runner after the ABI 4 change, in its existing CMake tree:
   `cmake --build <build> --target mh4u_runner`. The Qt frontend compiles the same header and
   needs the same rebuild before it carries `call2`.
2. Build a throwaway plugin (not in either repository) against the fork's
   `include/mh4u_plugin.h`: in `mh4u_plugin_init` it checks `host->abi >= 4` and that
   `host->size` covers `call2`, then asks for `on_frame`. In a frame call after start-up it
   takes 0x20 bytes from `alloc`, calls
   `host->call2(call, 0x0022e43c, args, floats, &out)` with `args = {block, 0, 7, 0xbeef}`
   and `floats = {1.5f, 10.0f}`, and logs r0, the out float and the words at `block + 0`,
   `+8` and `+0xc`.
3. Put the runtime's line in the code library's `<program id>.plugins.tsv` (`plugin`, name,
   library path and mod folder, tab-separated) in a copy of a user folder. No code library
   rebuild is needed: `sMhMain::frame` is a hook point of every library the fork's
   `tools/build_game.py` builds.
4. Run
   `mh4u_runner <MH4U USA .3ds> --code <user folder>/recomp/0004000000126300.so --user <user folder> --ms 12000 --speed 0 --log "*:Info"`.

Result (2026-11-25, MH4U USA v1.3.0, headless runner rebuilt with ABI 4): pass. The log had
`plugin <name>: ready: host ABI 4, size 0xb8, call2 present` when the plugin loaded, then
`plugin <name>: frame 30: call2 0x0022e43c(block=0x08e44668, r1=0, r2=7, r3=0xbeef, s0=1.5f, s1=10.0f) -> r0=0x08e44668, out=10; block +0: r3=0xbeef r2=7, +8: s0=1.5, +0xc: remainder=0`,
and the runner exited 0. The block holds r3 and r2 exactly as the call set them, and its `+8`
is s0 as 1.5f, so the function received the r3 and the VFP arguments. `out=10` is the
function's own s0 (s1 divided by its count of 1), so the float return came back through
`s0_out`. The run continued to its end, so the guest's registers, VFP registers and flags were
put back. The function only reads and writes the block the plugin allocates, so this proves
the call mechanism at boot; the translated 3U handler ([#115](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/115))
calls the engine's motion and effect functions the same way on a live monster.

## Tracing engine calls in MHXX

Shows which code calls an engine function at run time, and with which arguments, when reading the code doesn't settle it (the open entries of [reference/README.md](../reference/README.md#the-62-imports-one-by-one)). The maintainer plays; the tracer and the recording run beside the game.

1. Build Azahar's Qt frontend with the GDB stub (`-DENABLE_QT=ON -DENABLE_GDBSTUB=ON`; Debian needs `qt6-base-dev`, `qt6-multimedia-dev` and `qt6-base-private-dev`).
2. In a separate Azahar user folder, install the MHXX v4.8.0 update and turn the stub on (`[Debugging] use_gdbstub=true` in `config/qt-config.ini`). The update must be a decrypted CIA whose `code.bin` equals the official one, or the addresses won't match.
3. MHXX's game save is ExtData 0x1971: `sdmc/Nintendo 3DS/<id>/<id>/extdata/00000000/00001971/user/system` and `system_backup`. Put it there before the first boot, or the game creates a blank one.
4. Start the game, then `reference/trace_calls.py ADDR=label ...`. A function called every frame slows the game until `--max` retires it.
5. Play to the situation that should call the functions. A row's caller (LR) names the code using the function; matching the caller to a class through the vtables says who it is.

Last result (2026-11-24, a low-rank and a Hyper Rathian fight, Verdant Hills and Primal Forest): 5 of the 7 open functions ran, with their callers recorded in reference/README.md; `0x008a1ed8` and `0x008eb1c0` never ran.

The same tracer runs on MH4U's addresses. Its user folder holds the installed update (title `0004000e/00126300`) and the save in SavedData `title/00040000/00126300/data/00000001/` (`system` and `user1` to `user3`); the Qt frontend uses the `user` folder next to its binary, and it needs `/dev/dri` and `/dev/input`, so start it outside a file sandbox. Break on one or two addresses only: a getter called every frame freezes the game until `--max` retires it, so leave those out and keep `--max` low. Last result (2026-11-24, a Rathian quest): `0xb05154`, `0xb08c0c`, `0xb0545c`, `0x3120dc` and `0x304c10` ran; `0x94e364` did not. `0x304c10` was called once, by a shell's update (`uShell001` slot 22) for its owner, which settles the joint sound `0x008ae1c8`.
