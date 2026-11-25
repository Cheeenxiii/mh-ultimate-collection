# Underwater

Underwater play comes from MH3U, which has it in full. Each part is read from MH3U's files or its recompiled code, and carried into MH4U as data plus plugin hooks. Only what no game ever had is authored.

Where a part is not marked as checked, "where it likely lives" is a hypothesis to confirm in the reference recompile. The hunter skeleton comparison below is checked against both games' files.

## What comes from MH3U

| Part | What it does | Where it likely lives in MH3U | How it reaches MH4U |
|---|---|---|---|
| Swim state | 3D movement, surfacing, diving, entering and leaving water | a state of the player's action state machine, and the player command tables | hooks on MH4U's player update running a swim state machine translated from MH3U's |
| Oxygen | the gauge, drain, refill on surfacing, damage at zero, items and skills | player status code, item and skill data | gauge logic in the plugin, values from MH3U's tables |
| Camera | the free 3D camera underwater | MH3U's camera classes | a hook on MH4U's camera (`sMhCamera`, which the port already hooks) |
| Water volumes | where the water is, its surface, which areas are underwater | stage collision and area info, per area | converted stage data; the area loader told which areas are water |
| Underwater motions | idle, swim, attacks, reactions, per weapon class | motion lists (`.lmt`) for the player, per weapon | converted motion lists, with the 3U bone ids rewritten to 4U's |
| Monster behaviour | swimming movement and attacks | monster AI scripts (`.emc`) and monster code | monsters bring their own data; water-aware movement translated from MH3U |
| Effects and sound | bubbles, splashes, muffled audio, water fog | effect lists, sound requests, filters | converted assets; MH4U's own screen filters where they match |
| HUD | oxygen gauge, depth cues | layout files | converted layout, or drawn by the plugin |

## What is known

- MH3U's 387 motion lists are LMT version 66. Version 66 and 67 share one layout, so `mhuc` reads all 387 ([specs/lmt.md](../specs/lmt.md), check L3), underwater motions among them; their keyframe buffers decode too ([specs/lmt.md](../specs/lmt.md#keyframe-buffers), check L4), except that version 66 stores buffer types 11 to 13 signed where version 67 stores them unsigned behind a bounds block, so a converter has to re-encode those tracks' keys. MH4U's loader takes only version 67 and MH3U's only 66, so converting a 3U motion list means writing the number as well as re-encoding those keys ([specs/lmt.md](../specs/lmt.md#versions)).
- MH3U's stage collision is MH4U's format ([specs/sbc.md](../specs/sbc.md)).
- Cha-Cha (MH3U on Wii U) marks some of this. Its Wii U offsets must be re-found on 3DS:
  - swim state: the player's pad block (player + 0xE30 there) holds 3 at +0x3D under water;
  - camera: a mark at +0x12D of the camera block is 1 under water, the game handles pitch itself there, and the turn ramp is 10 frames instead of 5;
  - carving: a carve spot is kind 6 under water, 4 on land.
- Monster Hunter Tri, 3U's Wii base, has a static recompilation and reverse-engineering tools (MHTrIDA). They are a reference for behaviour, never a source.

## Hunter skeletons

The two hunters are the same rig with one bone dropped and one renumbered.

- **Bones.** MH3U's hunter body has 20 bones, ids 0 to 19; MH4U's has 19, ids 0 to 12 and 14 to 19. In every armour set checked, each MH4U bone has the same parent as its MH3U counterpart, and in the base set (armour id 1) the same rest position and parent distance too. MH4U id 0 is MH3U id 13, the pelvis (it carries the body's mesh); every other id is itself. MH3U id 0 is an empty root whose record is all zeroes; MH4U dropped it, and the torso (id 1) and the two leg chains (ids 14 and 17) hang off the pelvis.
- **Parts.** Arm (9 bones), face (1) and hair (3) are identical. Leg (7) and waist (6) have the same ids and tree with the root renumbered 13 → 0. Helm is ids 2 to 4, and some sets add ids 20 and 21; those two are outside the motion rig.
- **No names.** No hunter model stores bone names: the bone block is exactly bone count × 0x98 + 0x100 + skin count × 0x1C bytes and the file ends at the index buffer. The id is the only identity a model and a motion share.
- **Motions name bones by id.** MH4U's player motion lists, common and per weapon, rotate every hunter id (0 to 12 and 14 to 19) and translate id 0; none carries id 13 (check L2). MH3U's 50 player motion lists, read with version 67's 0x24-byte track table, rotate ids 1 to 21 and translate id 0, with ids 20 and 21 never given a keyframe; both games keep track 255 for root motion. The keyframe buffers are decoded too (check L4), so the tracks' keys can be carried across once their type is re-encoded where it differs.

**The mapping.** Rewrite each MH3U track's bone id: 1 to 12 and 14 to 19 stay; 13 becomes 0; 0 stays 0; 20 and 21 are dropped; 255 stays. MH3U's translation track on id 0 and its rotation track on id 13 become MH4U's two tracks on id 0, so no keyframe has to be composed. The keyframe buffers decode (first known bullet above), so this mapping says where each track goes; only version 66's types 11 to 13 need their keys re-encoded into version 67's form, and nothing composes a key.

Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k "hunter_skeleton or address_bones_by_id"` ([specs/mod.md](../specs/mod.md), check M4; [specs/lmt.md](../specs/lmt.md), check L2).

## What MH4U kept

At the class level, MH4U kept `uOcean`, the only water-named class in either game. Of the generic classes the underwater systems live in, it kept the camera base; the rest are gone or survive as names only (unknown 1).

**Neither game names a class for the water behaviour.** MH3U's class registry names 1,218 classes and MH4U's 992; in both, exactly one class carries a water word, `uOcean`. MH3U has one more water-related name, `uIDCockpitAir`, one of 19 `uIDCockpit*` HUD classes; MH4U has no `uIDCockpit` class at all, its HUD classes being layouts (`uLayout`, `sLayout`). The Wii U build's own 1,251-class registry (Cha-Cha) has no other water name either. The swim state, oxygen, the underwater camera and the water volumes were never classes of their own, so the classes that carry them are the generic ones.

**The water-surface class survives whole.** `uOcean` (class id `0x7e124a29`) is a `cUnit`, `0x108` bytes and 18 vtable slots in MH3U; MH4U keeps the class id, parent, size and slot count. All 15 of MH3U's slot functions have an MH4U counterpart in the MH4U↔MH3U function map, 14 at a ratio of 0.96 or better and the last at 0.83; 14 of MH4U's 15 map back. It is the one piece of MH3U's water code this class-level search found in MH4U. What it draws is unverified: its name and its being a `cUnit` are all that say it is the ocean. No MH4U stage file creates it, and no code calls it directly (below).

**The classes the underwater systems live in**, looked up by class id:

| MH3U class (class id) | Carries | MH3U | MH4U |
|---|---|---|---|
| `uIDCockpitAir` (`0x3db8d448`) | nothing of its own: a registered cockpit class with no gauge code (the gauge is drawn by `uIDCockpitMain`, below) | `uIDCockpit` subclass, `0x238`, 65 vtable slots | **lacks** it: no class with this id or name, and no `uIDCockpit` class at all |
| `uPlayer` (`0x72b401fd`) | the swim state, dive and surface | `uCharacter` subclass, `0x26a8`, 46 slots | **name only**: same id, now a `uPlChar` subclass, `0xace0`, 89 slots, and 25 of its 82 code slots pair with MH3U's |
| `uPlayerGuest` (`0x47916456`) | the guest player's copy of the same state | `uPlayer` subclass, `0x26b8`, 48 slots | **lacks** it |
| `sCamera` (`0x3261a0a7`) | the camera; Cha-Cha's underwater-camera mark is in a camera block | `cSystem` subclass, `0xd90`, 11 slots | **kept**: `0xe10`, 11 slots, 6 paired; MH4U adds `sMhCamera` (`0x576b8b6f`), the quest camera the port hooks |
| `uGameCamera` (`0x3361a524`) | MH3U's in-game camera | `uAppCameraBase` subclass, `0x8f0`, 20 slots | **lacks** it; `uAppCameraBase` (`0x75744321`) too |
| `uStage` (`0x504d895e`) | the stage object; the water volumes' data comes with the stage | `uCharacter` subclass, `0xef8`, 42 slots | **name only**: same id, a `uModel` subclass, `0xc78`, 29 slots; `uStageAnimation` (`0x28ac1e52`) lacks |

The monster behaviour and the effects of the first table are not here: each monster carries its own water behaviour in its code, and effects and sound are data and requests, not classes.

**What MH4U's own water names are not.** MH4U's code still names the water element and a water area colour: `DMATTR_WATER` with `pw->mRegupTimer[DMATTR_WATER]` and `pw->mWaterDmTimer` (the element's damage and blight timers), `d_water`, and `area_color_water` (a stage tint). Those are water-element and rendering names, not swimming, and none of them is MH3U's water code.

**Answer.** MH4U kept `uOcean` and the camera base, and none of the underwater systems' own code: the class MH3U registers as its air gauge (`uIDCockpitAir`, which draws nothing of its own), the guest player and MH3U's in-game camera classes are absent, and `uPlayer` and `uStage` survive only as names on rewritten layers. So no MH3U swim, oxygen or underwater-camera code can be hooked into as it stands; they go on MH4U's own `uPlayer` and `sMhCamera` as the "How it reaches MH4U" column above says, and only the water surface's code is reused as it is. MH4U does not create the ocean object from any stage file, so a converted 3U stage must bring its own surface, or the mod must create the object (below).

**Nothing in MH4U creates it.** The class and its code survive, but no stage file and no direct call asks for an object of it:

- **No stage file names it.** Every ARC entry stored under a `stage\` or `snake\stage\` path — 22,851 across the maps, event stages and demos — was decompressed and searched for the class id's four bytes and for the name `uOcean`: no entry carries either, and none is typed `uOcean` (check U1). The positive control sits in the same count: 12 stage entries name or are named a `suimen` (water-surface) texture or material, so the check does see water names.
- **There is no block to put it in.** 3U's stage layout is one XFS `rStageData` resource per area: each of its 169 area stage-data files has one, and 55 of them list a water-surface model (`...-suimen`) in its stage-resource path list. MH4U has no `rStageData` class and no entry of that type at all; its stage resources are `rStageInfoSet` (127 entries), `rStageAreaInfo` (5), `rStageCameraData` (61), `rCollision` (626) and `rScheduler` (1,291), and none of their bytes names `uOcean`. The stage-data archives hold only two files that start with XFS at all, and both are sound material lists (`snd_pl_fs`), not stage object lists.
- **MH4U's own water surfaces are stage geometry.** The two event stages with a water-surface texture, `v01a00` and `v03a01`, name it from their stage materials (`v01a00_suimen00_BM`, `v03a01_suimen00_BM`); no stage names a water object.
- **No code calls it.** In USA v1.3.0, the constructor `0x96bfcc` is branched to from one place only, inside its own `newInstance` `0xd02ecc`; `newInstance` is word-referenced from one place only, its class-registry vtable slot `0xe7da70`; and the class's vtable and registry words are referenced only by its own constructor, destructor, `newInstance` and registry blob. The engine could still create the object if a resource named the class, and no MH4U resource does.

**What a converted 3U stage must add.** It cannot rely on the game creating the ocean for it: MH4U's stage data has no object list, and its own stages that have a water surface draw it as geometry. A converted 3U area therefore brings the surface itself, as 3U does — the area's `-suimen` model, its material and its textures, converted to MH4U's MOD/MRL/TEX and placed in the converted area. If the water should instead use `uOcean`'s own surface (its constructor sets two size fields to 50 and calls a builder that lays out an (x+2)×(y+2) grid), the mod has to create the object from a plugin: no stage file can. Which of the two the mod does is a choice for the swim work; this check settles only that the game will not make the object.

**How this was checked.** Nothing here is bytes from a dump; the results are class ids, sizes, slot counts and pair counts.

1. Decompress each game's `code.bin` with the fork's `tools/blz.py`; the result's SHA-1 matches the dump's entry (`reference/games/mh3u/game.json`, and the fork's `config/versions.json` for MH4U USA v1.3.0).
2. Recover each game's class registry with `reference/mt_dti.py` (`reference/games/mh3u/mt_classes.tsv` and the fork's `config/mt_classes.tsv`) and each class's instance vtable with `reference/mt_vtables.py`.
3. Pair the functions with `reference/fnmap.py`; the MH4U↔MH3U map used here holds 6,866 pairs ([reference/README.md](../reference/README.md#cross-game-function-maps)).
4. Look each class up by name and class id in the other game's registry. For a class both games have, read its parent, size and vtable, and count how many of its vtable's functions the map pairs.
5. Search both name lists for water, swim, dive, oxygen, breath, ocean, sea, aqua, submerge, drown, buoy, tide, wave, bubble, splash and air, each followed by a capital letter or the end of the name, so that `Search` does not count.
6. Read the identifiers in the paragraph above with `strings` over the decompressed images.
7. Check U1 (`mhuc survey <MH4U romfs.bin>`, the `stage:` block) decompresses every entry whose stored path starts `stage\` or `snake\stage\` and compares its type id with `uOcean`'s class id (`0x7e124a29`), and its bytes with that id and with the names `uOcean` and `suimen`. MH4U: 22,851 stage-path entries, 0 typed `uOcean`, 0 carrying its class id, 0 naming it, 12 naming a `suimen` surface. A byte search of the 169 MH3U area `rStageData` files finds `-suimen` in 55 and `uOcean` in none — 3U's water surface is a model resource, not this class.
8. For the code side, take the class's `newInstance` from the recovered vtable (step 2) and scan the decompressed image for that word and for ARM/Thumb branches to it and to the constructor: the only word is its registry vtable slot and the only branch is the one inside `newInstance` itself.

Both answers are negative: MH4U's stage files do not reference `uOcean` (step 7), and no code calls it (step 8).

**The oxygen gauge is a display, not the oxygen system.** `uIDCockpitAir` has no gauge code of its own. Its instance vtable (`0xb53c48`, 65 slots) differs from `uIDCockpit`'s (`0xb4f038`) in five slots only: slot 1 is its destructor (`0x2f9288`), slot 4 branches to the base's no-op (`0x2f927c`, to `0x535b04`), slot 5 returns its DTI (`0xa12b04`), and slots 58 and 59 are `bx lr` (`0x2f9280`, `0x2f9278`) where `uIDCockpit` runs `0x1f2d94` and `0x1f26c4`. Apart from that destructor, its constructor and its DTI getter, the class has no code. Registering a class does not create it, and nothing in MH3U's code or RomFS names it outside its own registration, constructor, destructor and getters: an instance of it, were one made, has no gauge code to run.

The gauge is drawn by `uIDCockpitMain` (`0x3f4318b3`, DTI `0xd461f8`), the quest cockpit. Its per-frame update (vtable `0xb55930`, slot 59 = `0x33ff2c`) calls `0x341a58`, which calls `0x33f3fc(self, status)`; `status` is the player status at `[uPlayer+0xd5c]`. That function reads `status+0x3d` (3 = underwater), shows nodes 8 to 10 (`ariA1` to `ariA3`) underwater and 11 to 13 (`ariB1` to `ariB3`) on land, shows node 14 (`ariber`) only underwater, and sets the bar's length: 64 px at full, filled by 64 px × current / 150, eased, where the current is the signed 16-bit at `status+0x654` and the capacity the signed 16-bit at `status+0x656`, capped at `0x96` (150).

The timer itself is player code. `0xa39c20(player, delta)` adds `delta` to the current air and clamps it to `[0, capacity]`; `0xa3a478(player, delta)` raises the capacity (cap 150) and sets the current to it. The player's update (`0x8d60c0`) calls `0xa39c20(player, -1)` at `0x8d6fe4` while `status+0x3d == 3` (underwater) and `0xa39c20(player, +150)` at `0x8d6ad8` otherwise; `0x8eccb8` calls `0xa3a478` at `0x8ecd70`.

So the gauge is a display of the player's oxygen timer, not the oxygen system's HUD half. The drain, capacity and refill are player code, and the gauge is a few sprites in the quest cockpit layout `GUI\texlayout\quest\coc_main_eng` (in `/arc/ID/ID_cock_eng.arc`), whose 52 nodes include `ariA1` to `ari_eff` at indices 8 to 15. A port carries the timer with the swim state and redraws the gauge as a layout; there is no `uIDCockpitAir` behaviour to rebuild. MH4U's own HUD layouts are `rLayout` (`.lyt`) entries, not XFS: it ships no XFS texlayout at all ([specs/xfs.md](../specs/xfs.md#checks), check X1).

**How the air gauge was read.** Addresses and names only.

1. Decompress MH3U's `code.bin`; its SHA-1 matches `reference/games/mh3u/game.json`.
2. Recover the class registry and instance vtables with `reference/mt_dti.py` and `reference/mt_vtables.py`, then compare `uIDCockpitAir`'s vtable with `uIDCockpit`'s slot by slot; the five differing slots are read with capstone.
3. Follow `uIDCockpitMain`'s slot 59 (`0x33ff2c`) to `0x341a58` and then `0x33f3fc`, and read the status offsets and layout node indices there.
4. Extract `/arc/ID/ID_cock_eng.arc` from the RomFS (one file, 47 entries) and read `GUI\texlayout\quest\coc_main_eng` (14,960 bytes) with `mhuc`'s RomFS, ARC and XFS readers; its 52 nodes' names and indices come from that XFS read (check X1).
5. Read the player update `0x8d60c0` at its two calls to `0xa39c20`, `0x8eccb8` at its call to `0xa3a478`, and both functions' clamps.
6. Search the decompressed image and the RomFS for the class id, DTI, vtable and name.

The texlayout is a little-endian XFS file; `mhuc`'s XFS reader reads it as the other 3DS XFS files (its object-header flag, property count and property sizes are laid out per byte order, [specs/xfs.md](../specs/xfs.md), check X1), so step 4 reads its objects rather than walking the bytes.

## Unknowns

1. Whether MH4U kept any of MH3U's water code: answered for the class level in [What MH4U kept](#what-mh4u-kept) — the water surface survives, the underwater systems do not. The function-level question stays with unknown 2.
2. How MH3U's player state machine is organised (one class per state, or one big switch). This decides whether the swim state can be ported function by function.

## Approach

The smallest complete target is the Water Arena, which has no land transitions: enter water, float, swim, surface, oxygen, with Sword and Shield motions (the simplest moveset). Then one underwater monster (Lagiacrus), then the open-water locales with land-water transitions (Deserted Island, Flooded Forest).

## Authored parts

No game has these, so they are made, each with a row in the [authored register](sources.md#authored-register) when work starts:

- Charge Blade and Insect Glaive underwater movesets, and the Kinsect underwater;
- MH4U-era actions underwater (ledge mounts, jumping attacks), or their being disabled there;
- MH4U-only and GU-only monsters entering water, if any are placed in water maps;
- GU's Styles and Arts underwater, which don't come in ([decisions.md](decisions.md#0005-combat-base)).

An option, not a decision: until a weapon class has underwater motions, keep it out of underwater quests (the quest board or the equipment check refuses it). That lets 3U's water quests ship before the new movesets exist.

## In-game checks, once it runs

- Swimming, surfacing and drowning on the Water Arena time the same as in MH3U (oxygen drain per second, swim speed), measured in both games.
- Lagiacrus's underwater attacks match its MH3U set.
