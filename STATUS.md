# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after the session that built the port and found the monster id table.

## Where we are

Phase: **engine work with the game files.** The port builds and runs the game with a native plugin; MH4U's monster ids, factory and their bounds are found; MH3U has a function table; MOD headers are named. Report: [docs/reports/2026-11-23-port-ids-and-tables.md](docs/reports/2026-11-23-port-ids-and-tables.md).

Findings that steer the next steps:
- Monster ids run 0..123; three 124-entry bounds move when ids grow (id-tables.md). Every MH4U monster class is the same size.
- MH4U's and MHXX's Rathalos share one skeleton by bone id; MH3U's differs (specs/mod.md).
- The clean MHXX v1.4 dump has the same code as the fan-repackaged one; it's the MHXX reference now (`mhxx_upd`).
- Growing tables from plugins needs guest allocation: the game's heap functions are the next thing to find.

## Branches

| Repo | Branch | State |
|---|---|---|
| content | `claude/port-ids-and-tables` | committed; pushed and PR'd only if the maintainer says so |
| fork | `uc/monster-ids-mh3u-functions` | committed; the same |

## Next tasks, in order

1. **MH3U recompile and gametest** (reference-recompiles.md step 3): `recompile.py --game mh3u` (MH4U's output byte-identical without it), then gametest. Done when the pass rate and unresolved jump tables are in reference-recompiles.md.
2. **MHXX v1.4 function table and classes** with the same Ghidra pipeline. Done when `config/games/mhxx/functions.tsv` exists and game.json names the v1.4 code.
3. **Heap functions and plugin `alloc`/`free`**: find the game's allocator, add the ABI members with tests, rerun plugin step 6. Done when plugin-api.md records step 6 passing.
4. **The rest of the monster tables** (names, sizes, parts, rewards). Done when each has an address and bound in id-tables.md.

## Waiting on the maintainer

- Push and PR the two branches above (asked at the end of the session).
- A check of the port's pad features with the plugin in the app or Azahar's Qt build (plugin-api.md step 5), on a machine with a display.
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
