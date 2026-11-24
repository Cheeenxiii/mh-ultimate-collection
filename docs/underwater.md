# Underwater

Underwater play comes from MH3U, which has it in full. Each part is read from MH3U's files or its recompiled code, and carried into MH4U as data plus plugin hooks. Only what no game ever had is authored.

Nothing here is verified yet: "where it likely lives" is a hypothesis to confirm in the reference recompile.

## What comes from MH3U

| Part | What it does | Where it likely lives in MH3U | How it reaches MH4U |
|---|---|---|---|
| Swim state | 3D movement, surfacing, diving, entering and leaving water | a state of the player's action state machine, and the player command tables | hooks on MH4U's player update running a swim state machine translated from MH3U's |
| Oxygen | the gauge, drain, refill on surfacing, damage at zero, items and skills | player status code, item and skill data | gauge logic in the plugin, values from MH3U's tables |
| Camera | the free 3D camera underwater | MH3U's camera classes | a hook on MH4U's camera (`sMhCamera`, which the port already hooks) |
| Water volumes | where the water is, its surface, which areas are underwater | stage collision and area info, per area | converted stage data; the area loader told which areas are water |
| Underwater motions | idle, swim, attacks, reactions, per weapon class | motion lists (`.lmt`) for the player, per weapon | converted motion lists, with a 3U-to-4U skeleton mapping |
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

## Unknowns

1. Whether MH4U kept any of MH3U's water code: no water-related class name has turned up in MH4U's class registry so far.
2. How MH3U's player state machine is organised (one class per state, or one big switch). This decides whether the swim state can be ported function by function.
3. Whether the 3U and 4U hunter skeletons match: bone counts and names.

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
