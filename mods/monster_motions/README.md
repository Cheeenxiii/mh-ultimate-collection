# Ported monsters' motion numbers

The plugin that translates the motion number a ported monster's MH4U handler asks into the
source game's animation. A ported monster runs MH4U's own handler for every action id the two
games share ([decision 0002](../../docs/decisions.md#0002-monsters-are-ported-onto-mh4us-engine)),
so the handler asks for an MH4U motion index (LMT file << 8 | slot). The converted motion lists
keep the source game's grouping, so that index names another animation or an empty slot. The
plugin wraps MH4U's motion-start wrapper (`0x0094e318`, check R1's) and, when the monster is a
ported one, replaces the number in `r1` with the source game's animation from a generated table.

## The table

`src/motions.h` is generated, never edited: `reference/monster_motions.py table` writes it from
R1's comparison ([checks.md](../../docs/checks.md#monster-actions)), one table per ported
monster id in [data/ids/registry.csv](../../data/ids/registry.csv). It holds action and motion
numbers only. Each entry says: for this current action (its category and index bytes), MH4U's
handler asks this motion number, and the source game's animation sits at this index in the
converted lists. A source index is in MH4U's packing whatever the source game's was: MH3U's
`file * 100 + slot` becomes `file << 8 | slot`, while MHXX's already is. A category-only action
(the category has one action, the index byte unused) is keyed by category with index `0x100`.

The 3U Rathian (id 125) has 96 translations: the 2 ids whose two indices agree (1/11 and 1/12)
need none. The 19 action ids R1 cannot resolve — category 7's computed index — are listed in
the header and left out; their numbers pass through. The 57 ids R1 does not compare pass
through too. The GU Rathian (id 124) has no translations: MH4U and MHXX start the same index on
all 167 of their comparable ids (check R2), so her port needs none for them.

`tools/check_motion_tables.py` checks the header: one table per registered monster, sorted and
unique entries, numbers in range, the left-out ids in category 7, the counts adding up, and
R1's counts. Given the same inputs as the generator, it also requires the file to be exactly
what the generator writes. Run it after regenerating:

```bash
python3 reference/monster_motions.py table --mh4u build/mh4u.tsv \
    --source mh3u build/mh3u.tsv build/mh4u-mh3u-map.tsv \
    --source mhxx build/mhxx.tsv build/mh4u-mhxx-map.tsv \
    -o mods/monster_motions/src/motions.h
python3 tools/check_motion_tables.py
```

## The fallback

`src/fallback.h` is generated too: `reference/monster_motions.py fallback` writes it from the two
games' motion lists in the player's RomFS images, one table per ported monster. When the action
table has no entry for (current action, number), the plugin looks the number alone up there: the
source animation whose signature (frames, loop frame, track count, one more track on MH4U's side
allowed) matches MH4U's animation at that number, and among several the one whose decoded keys
equal MH4U's on strictly more tracks. It answers what the action table can't: category 7's
computed index, a handler's second motion, the ids R1 doesn't compare. The 3U Rathian has 89
numbers; the GU Rathian none (MHXX starts the same indices). A number neither table answers
passes through. `tools/check_motion_tables.py` checks its shape, and with the RomFS images that
it is exactly what the generator writes:

```bash
python3 reference/monster_motions.py fallback --mh4u-romfs <MH4U RomFS> \
    --source-romfs mh3u <MH3U RomFS> --source-romfs mhxx <MHXX RomFS> \
    -o mods/monster_motions/src/fallback.h
python3 tools/check_motion_tables.py --mh4u-romfs <MH4U RomFS> \
    --source-romfs mh3u <MH3U RomFS> --source-romfs mhxx <MHXX RomFS>
```

## What it hooks

| Function | Address | What it does |
|---|---|---|
| `uEnemy::startMotion` | `0x0094e318` | MH4U's motion-start wrapper (`mov r2,#0; b 0x0091908c`); r0 is the enemy, r1 the motion number |
| `uEnemyFactory::create` | `0x006901f4` | creates an enemy by id; r1 is the id the quest asked for, r0 the enemy on return |

The plugin reads the monster's current action at `work + 0x1ca` and `+0x1cb`, where `work` is
the pointer at `this + 0xe28` (the same work block `mods/force_action` and `mods/monster_ids`
read). A ported monster is created as its stand-in (`mods/monster_ids` rewrites the factory's
id), so its id byte at `work + 0x1c0` holds the stand-in's id. The plugin therefore also wraps
the factory (`uEnemyFactory::create`, `0x006901f4`) and remembers each enemy made for a ported
id. This mod comes after `mods/monster_ids` in the mod order, so its factory hook runs first and
sees the id the quest asked for. Every other enemy is MH4U's own and is left alone. Both hook
points are in `mod.json`; `mods/monster_ids` builds the factory one into the library too.

Logging, one line per distinct case and at most 64 of each:

- `ready: translating motion numbers for 2 ported monster id(s), 96 entries; MH4U's own ids pass through`
- `monster 125: action 13/5 asks motion 0x002 -> source 0x013` (the first time that translation runs)
- `monster 125: action 2/7 asks motion 0x005 -> source 0x006 (by its animation's signature)` (the fallback, once)
- `monster 125: no entry for action 7/36 motion 0x4ff; passing it through` (a number neither table answers, once)

## What it does not do yet

- **Category 7's computed index.** R1's first-constant scan cannot tell which of several
  motions a category-7 handler starts, so the 19 action ids are left out of the action table
  (listed in the header and [checks.md](../../docs/checks.md#monster-actions)); the fallback
  answers their numbers where MH4U's animation has a counterpart. 21 numbers of MH4U's files 3
  and 4 have none in MH3U's lists and still play MH4U's animation.
- **GU's one-sided ids.** 19 action ids start a constant motion only in MH4U and 2 only in
  MHXX (R2); neither side is compared, so both pass through. The GU table is otherwise empty
  because every compared id shares its index.
- **Motions after the entry motion.** The action table is built from each handler's first
  constant motion; a later motion goes to the fallback.

## Build

```bash
make        # monster_motions.so next to mod.json
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. `src/motions.h` is generated, not edited (above). Licence: GPL-3.0-or-later,
like the rest of the mod.

## Install

```bash
python3 <fork>/tools/mods.py add mods/monster_motions
python3 <fork>/tools/mods.py enable "Ported monsters' motion numbers"
python3 <fork>/tools/build_game.py --dump "MH4U v1.3.0 update.cia" --install <Azahar user directory>
```

The build lists the mod's one hook point; a library built without it logs that it needs
rebuilding and the plugin turns itself off for the run.

## The check

The headless and in-game steps and what they must show are in
[checks.md](../../docs/checks.md#the-motion-translation-m1).
