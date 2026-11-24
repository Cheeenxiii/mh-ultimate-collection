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

- MH3U's 387 motion lists are LMT version 66. The layout in [specs/lmt.md](../specs/lmt.md) reads version 67 (MH4U, MHXX), so underwater motions need a version-66 layout or a converter. Cha-Cha's Wii U files are the lead.
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
- **Motions name bones by id.** MH4U's player motion lists, common and per weapon, rotate every hunter id (0 to 12 and 14 to 19) and translate id 0; none carries id 13 (check L2). MH3U's 50 player motion lists, read with version 67's 0x24-byte track table, rotate ids 1 to 21 and translate id 0, with ids 20 and 21 never given a keyframe; both games keep track 255 for root motion. The version-66 buffers aren't decoded, so for MH3U this reads the tracks only.

**The mapping.** Rewrite each MH3U track's bone id: 1 to 12 and 14 to 19 stay; 13 becomes 0; 0 stays 0; 20 and 21 are dropped; 255 stays. MH3U's translation track on id 0 and its rotation track on id 13 become MH4U's two tracks on id 0, so no keyframe has to be composed. Converting the version-66 keyframe buffers is still open (first known bullet above); this mapping only says where each track goes.

Procedure: `MHUC_DUMPS=<dumps> python3 -m pytest tests/test_with_game_files.py -k "hunter_skeleton or address_bones_by_id"` ([specs/mod.md](../specs/mod.md), check M4; [specs/lmt.md](../specs/lmt.md), check L2).

## What MH4U kept

At the class level, MH4U kept `uOcean`, the only water-named class in either game. Of the generic classes the underwater systems live in, it kept the camera base; the rest are gone or survive as names only (unknown 1).

**Neither game names a class for the water behaviour.** MH3U's class registry names 1,218 classes and MH4U's 992; in both, exactly one class carries a water word, `uOcean`. MH3U has one more water-related name, `uIDCockpitAir`, one of 19 `uIDCockpit*` HUD classes; MH4U has no `uIDCockpit` class at all, its HUD classes being layouts (`uLayout`, `sLayout`). The Wii U build's own 1,251-class registry (Cha-Cha) has no other water name either. The swim state, oxygen, the underwater camera and the water volumes were never classes of their own, so the classes that carry them are the generic ones.

**The water-surface class survives whole.** `uOcean` (class id `0x7e124a29`) is a `cUnit`, `0x108` bytes and 18 vtable slots in MH3U; MH4U keeps the class id, parent, size and slot count. All 15 of MH3U's slot functions have an MH4U counterpart in the MH4U↔MH3U function map, 14 at a ratio of 0.96 or better and the last at 0.83; 14 of MH4U's 15 map back. It is the one piece of MH3U's water code this class-level search found in MH4U. What it draws is unverified: its name and its being a `cUnit` are all that say it is the ocean.

**The classes the underwater systems live in**, looked up by class id:

| MH3U class (class id) | Carries | MH3U | MH4U |
|---|---|---|---|
| `uIDCockpitAir` (`0x3db8d448`) | the oxygen gauge | `uIDCockpit` subclass, `0x238`, 65 vtable slots | **lacks** it: no class with this id or name, and no `uIDCockpit` class at all |
| `uPlayer` (`0x72b401fd`) | the swim state, dive and surface | `uCharacter` subclass, `0x26a8`, 46 slots | **name only**: same id, now a `uPlChar` subclass, `0xace0`, 89 slots, and 25 of its 82 code slots pair with MH3U's |
| `uPlayerGuest` (`0x47916456`) | the guest player's copy of the same state | `uPlayer` subclass, `0x26b8`, 48 slots | **lacks** it |
| `sCamera` (`0x3261a0a7`) | the camera; Cha-Cha's underwater-camera mark is in a camera block | `cSystem` subclass, `0xd90`, 11 slots | **kept**: `0xe10`, 11 slots, 6 paired; MH4U adds `sMhCamera` (`0x576b8b6f`), the quest camera the port hooks |
| `uGameCamera` (`0x3361a524`) | MH3U's in-game camera | `uAppCameraBase` subclass, `0x8f0`, 20 slots | **lacks** it; `uAppCameraBase` (`0x75744321`) too |
| `uStage` (`0x504d895e`) | the stage object; the water volumes' data comes with the stage | `uCharacter` subclass, `0xef8`, 42 slots | **name only**: same id, a `uModel` subclass, `0xc78`, 29 slots; `uStageAnimation` (`0x28ac1e52`) lacks |

The monster behaviour and the effects of the first table are not here: each monster carries its own water behaviour in its code, and effects and sound are data and requests, not classes.

**What MH4U's own water names are not.** MH4U's code still names the water element and a water area colour: `DMATTR_WATER` with `pw->mRegupTimer[DMATTR_WATER]` and `pw->mWaterDmTimer` (the element's damage and blight timers), `d_water`, and `area_color_water` (a stage tint). Those are water-element and rendering names, not swimming, and none of them is MH3U's water code.

**Answer.** MH4U kept `uOcean` and the camera base, and none of the underwater systems' own code: the oxygen-gauge class, the guest player and MH3U's in-game camera classes are absent, and `uPlayer` and `uStage` survive only as names on rewritten layers. So no MH3U swim, oxygen or underwater-camera code can be hooked into as it stands; they go on MH4U's own `uPlayer` and `sMhCamera` as the "How it reaches MH4U" column above says, and only the water surface is reused as it is (the converted stage can create `uOcean`, or a plugin hooks it).

**How this was checked.** Nothing here is bytes from a dump; the results are class ids, sizes, slot counts and pair counts.

1. Decompress each game's `code.bin` with the fork's `tools/blz.py`; the result's SHA-1 matches the dump's entry (`reference/games/mh3u/game.json`, and the fork's `config/versions.json` for MH4U USA v1.3.0).
2. Recover each game's class registry with `reference/mt_dti.py` (`reference/games/mh3u/mt_classes.tsv` and the fork's `config/mt_classes.tsv`) and each class's instance vtable with `reference/mt_vtables.py`.
3. Pair the functions with `reference/fnmap.py`; the MH4U↔MH3U map used here holds 6,866 pairs ([reference/README.md](../reference/README.md#cross-game-function-maps)).
4. Look each class up by name and class id in the other game's registry. For a class both games have, read its parent, size and vtable, and count how many of its vtable's functions the map pairs.
5. Search both name lists for water, swim, dive, oxygen, breath, ocean, sea, aqua, submerge, drown, buoy, tide, wave, bubble, splash and air, each followed by a capital letter or the end of the name, so that `Search` does not count.
6. Read the identifiers in the paragraph above with `strings` over the decompressed images.

The oxygen gauge's role is inferred from its name and its cockpit siblings, not read in code or seen in game. Whether MH4U's stages instantiate `uOcean` is likewise unverified; the class and its code are present, but the data side is not checked.

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
- GU's Styles and Arts underwater, if GU's combat comes in ([decisions.md](decisions.md#combat-base)).

An option, not a decision: until a weapon class has underwater motions, keep it out of underwater quests (the quest board or the equipment check refuses it). That lets 3U's water quests ship before the new movesets exist.

## In-game checks, once it runs

- Swimming, surfacing and drowning on the Water Arena time the same as in MH3U (oxygen drain per second, swim speed), measured in both games.
- Lagiacrus's underwater attacks match its MH3U set.
