# Ported monsters' action ids

The plugin that runs the MH4U action whose handler has the same body as a source game action
MH4U's monster class lacks. A ported monster runs MH4U's own handler for every action id the
two games share ([decision 0002](../../docs/decisions.md#0002-monsters-are-ported-onto-mh4us-engine)).
16 of the 17 3U Rathian ids MH4U's `uEm001` lacks reach the same handler function as a shared
action ([reference/README.md](../../reference/README.md#the-17-ids-mh4u-has-no-action-for)), so
the port does not carry them as new C: the plugin wraps MH4U's action setter
(`uEnemy::setAction`, `0x0090ef74`) and, when a ported monster asks for one of these ids,
replaces the requested pair with the mapped MH4U pair from a generated table. The game's
setter then initializes the shared action, and MH4U's own handler runs.

## The table

`src/actions.h` is generated, never edited: `reference/monster_handlers.py table` writes it from
the per-id table `reference/monster_handlers.py targets -o` produces, one table per ported
monster id in [data/ids/registry.csv](../../data/ids/registry.csv). It holds source and target
action numbers only. Each entry says: when the source game's AI asks for this action (its
category and index bytes), MH4U runs this action instead.

The 3U Rathian (id 125) has 16 translations. Where several shared actions reach the same source
handler, the generator takes the lowest one whose MH4U action reaches a handler (an inline MH4U
action has none), so the handler MH4U runs is the one the body match names; the page lists the
alternatives. Action 4 has no shared action and is left out: it needs new C (#136). The GU
Rathian (id 124) has no entries, because MH4U and MHXX share every action id her port keeps
and each runs MH4U's own handler as it is (check R2).

`tools/check_action_map.py` checks the header: one table per registered monster, sorted and
unique entries, action numbers in range, the 16 ids of #115 and no action 4, and that it agrees
with the map recorded in reference/README.md. Given the per-id table, it also requires the
header to be exactly what the generator writes:

```bash
python3 reference/monster_handlers.py table --targets build/3u-targets.tsv
python3 tools/check_action_map.py
```

## What it hooks

| Function | Address | What it does |
|---|---|---|
| `uEnemy::setAction` | `0x0090ef74` | MH4U's action setter: (this, category, index, mode); the AI calls it when it changes a monster's action, and it initializes the action's state |

The plugin reads the monster's id byte at `work + 0x1c0` and its current action at `work + 0x1ca`
and `+0x1cb`, where `work` is the pointer at `this + 0xe28` (the same work block
`mods/force_action` and `mods/monster_ids` read). A source action the table does not name passes
through untouched: MH4U's own ids, the ids the two games share, action 4, and every move still
to be translated. While the mapped action is the current one, the setter call is skipped, so
the game's repeated calls do not restart the move.

`mod.json` names the one hook point, so a code library built with this mod carries it. Two mods
hook `uEnemy::setAction` without a conflict: the hooks chain. For the in-game check, enable
`force_action` **after** this mod (the last mod in the order runs first), so it writes the
forced pair before this plugin translates it.

Logging, one line per case and at most 64 translations:

- `ready: translating 16 source action id(s) for 2 ported monster id(s); MH4U's own ids pass through`
- `monster 125: action 7/87 -> 7/92` (the first time that translation runs)

## What it does not do yet

- **Action 4.** It has no shared handler, so the table leaves it out and the plugin passes it
  through; the port needs new C for it (#136).
- **The pick among a set.** 7/64 can be served by any of 7/35 to 7/65 and 13/9 by 0/3, 3/10 or
  13/7; the table runs the lowest one whose MH4U action has a handler. R2p's in-game check
  (#116) says whether the move plays; if it does not, moving the entry to another action the
  page lists is the fix.
- **The source's variant arguments.** The target's case block supplies its own arguments, so a
  source id whose variant the target does not pass (11/5's `r2 = 1`) may play the target's
  variant. The in-game check is what settles it.

## Build

```bash
make        # monster_actions.so next to mod.json
```

It builds against the engine fork's `include/mh4u_plugin.h`; `make FORK=/path/to/fork` uses
another checkout. `src/actions.h` is generated, not edited (above). Licence: GPL-3.0-or-later,
like the rest of the mod.

## Install

```bash
python3 <fork>/tools/mods.py add mods/monster_actions
python3 <fork>/tools/mods.py enable "Ported monsters' action ids"
python3 <fork>/tools/build_game.py --dump "MH4U v1.3.0 update.cia" --install <Azahar user directory>
```

The build lists the mod's one hook point; a library built without it logs that it needs
rebuilding and the plugin turns itself off for the run.

## The check

The in-game steps and the rows they fill are in
[checks.md](../../docs/checks.md#the-ported-moves-check-r2p). The headless part is the ready
line above when the code library boots with the mod; the in-game part waits for #49 and #105.
