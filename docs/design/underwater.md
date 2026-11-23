# Underwater combat

**Plan:** underwater play comes from MH3U, which has it in full: the swim state, oxygen, the camera, water volumes, underwater motions per weapon class, and monsters' underwater behaviour. Each part is extracted from MH3U's files or its code (through the reference recompile), and carried into MH4U as data plus native plugin hooks. Only what no game ever had is authored: Charge Blade and Insect Glaive underwater movesets, and anything MH4U-era that touches water, listed in the [authored register](../sources/authored-register.md).

Nothing here is verified yet. Every "where it lives" below is a hypothesis for the first session with game files to confirm or correct.

## What to lift from MH3U

| Part | What it does | Where it likely lives in MH3U | How it reaches MH4U |
|---|---|---|---|
| Swim state | the player's mode when in water: 3D movement, surfacing, diving, entering and leaving | player code (a state in the player's action state machine) and player command tables | ported behaviour: hooks on MH4U's player update that run a swim state machine, written by reading MH3U's (reference recompile), not invented |
| Oxygen | the gauge, drain rate, refill on surfacing, damage at zero, items (Oxygen Supply) and skills | player status code and item/skill data | gauge logic in the plugin; values from MH3U's data tables |
| Camera | the free 3D camera underwater, depth framing | camera classes (MH3U's camera code) | hook on MH4U's camera (`sMhCamera`, already hooked by the port for the mouse camera) |
| Water volumes | where the water is, its surface height, which areas are underwater | stage files: collision and area info (rStageAreaInfo-like types) per area | converted stage data; the area loader told which areas are water |
| Underwater motions | per weapon class: idle, swim, attacks, reactions | motion lists (rMotionList, `.lmt`) for the player, per weapon | converted motion lists; needs the skeleton mapping (3U player skeleton to 4U's) |
| Monster underwater AI | Leviathans' and others' swimming movement and attacks | monster command data (rEnemyCmd-like, `.emc`) and monster code | monsters arrive with their own data; the engine side needs water-aware movement, from MH3U's code |
| Effects and sound | bubbles, splashes, muffled audio, water fog | effect lists (rEffectList), sound requests, filters | converted assets; filters through MH4U's own screen filters where they match |
| HUD | oxygen gauge, depth cues | layout files (rLayout) | converted layout, or drawn by the plugin if layouts don't convert |

## Leads from Cha-Cha (MH3U Wii U)

Cha-Cha, a recompilation of the Wii U build of MH3U, marks some of this already ([docs/sources/cha-cha.md](../sources/cha-cha.md)). Wii U offsets, to re-find on 3DS before use:

- Swim state: the player's pad block (player + 0xE30 there) holds 3 at +0x3D under water (`src/game/modern_camera.cpp`, `camera_speed.cpp`).
- Camera: a mark at +0x12D of the camera block is 1 under water; under water the game handles camera pitch itself (`cameraPitchInput?`), and its turn ramp is longer (10 frames instead of 5).
- Carving: a carve spot is kind 6 under water, 4 on land (`src/game/carving.cpp`).

## Unknowns to settle first

1. Whether MH4U's engine kept any of MH3U's water code (dead code, unused states, class names). Check: MH4U's class registry (`config/mt_classes.tsv`) for water-related names; none found by name so far would mean nothing kept.
2. MH3U's ARC version and model version (specs/arc.md, specs/mod.md): the converters depend on them.
3. How MH3U's player state machine is organised: one class per state, or a big switch. Determines whether the swim state can be ported function by function.
4. Skeleton compatibility of the 3U and 4U hunters: bone counts and names (check M1 in specs/mod.md).

## Order of work

1. Reference recompile of MH3U, class registry first (reference-recompiles.md steps 1-3).
2. Find the swim state's entry: the code that switches the player into it when entering water, through the area's water flag.
3. Port the minimum: enter water, float, swim, surface, oxygen. One arena (Water Arena) as the test map, since it has no land transitions to get right.
4. Motions for one weapon class (Sword and Shield: simplest moveset), then the others.
5. One underwater monster (Lagiacrus) with its own data and AI, against the swim state.
6. Then the open-water locales (Deserted Island, Flooded Forest), with land-water transitions.

## Authored parts

Things no game has, so they are made rather than extracted (each gets a row in the register when started):

- Charge Blade and Insect Glaive underwater movesets (and the Kinsect underwater).
- MH4U-era player actions that would happen underwater: mounting from a ledge, the jumping attacks (likely disabled underwater instead: an option, not a decision).
- MH4U and GU-only monsters entering water, if any are placed in water maps.

## In-game checks (later)

- Swim in, surface, and drown on the Water Arena with the plugin, and compare timings with MH3U on the same arena (oxygen drain per second, swim speed), measured on both, recorded as numbers in a check note.
- Lagiacrus's underwater attack set matches its MH3U set (watch a hunt in both).
