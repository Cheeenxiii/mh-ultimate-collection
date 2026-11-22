# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after the first session with game files.

## Where we are

Phase: **format checks done; next is engine work with the game files** (port build, ID tables, the MH3U reference recompile). Sessions now start from this file: the workspace hook prints it, `/next` and `/handoff` keep it current. All five specs are checked against MH4U, MH3U and MHXX; `mhuc survey` reruns those checks. MH3U's and MHXX's class registries are in the fork.

Findings that steer the next steps (report: `docs/reports/2026-11-23-first-game-files-session.md`):
- MH3U's 3DS models are the same format as MH4U's (MOD 0xE6): no container conversion needed.
- MH3U's monsters carry their own per-monster state, unlike MH4U's and MHXX's: expect 3U code, not data alone.
- MH4U has no GMD text; its text format is still to describe.

## Branches

| Repository | Branch | State |
|---|---|---|
| mh-ultimate-collection | `claude/game-files-checks` | 5 commits, not pushed; to merge into `claude/nice-knuth-5gd62h` (the default branch) |
| MH4UltimateDC-fork | `uc/reference-classes` | 1 commit on `uc/main`, not pushed; PR into `uc/main` |
| MH4UltimateDC-fork | `uc/main` | the plugin API is merged (PR #1) |

## Next tasks, in order

1. **Push both branches** and open PRs. Done when both are on GitHub.
2. **Build the port with the plugin layer** (`uc/main`, inside Azahar's tree) and run the sample plugin procedure in `docs/design/plugin-api.md`. Done when the procedure's result is written there.
3. **Find MH4U's monster ID table and factory** (`docs/design/id-tables.md`, steps 1-2) in the v1.3.0 code. Done when the addresses and the procedure are in id-tables.md and the fork's `config/`.
4. **MH3U function table** (`docs/design/reference-recompiles.md`, step 2): Ghidra export, `build_function_table.py`, `find_missing_functions.py`. Done when `config/games/mh3u/functions.tsv` exists.
5. **MOD M2:** compare Rathalos (`em001`) across the three games with a model tool. Done when `specs/mod.md` names what each header slot holds.

## Waiting on the maintainer

- A clean dump of the official MHXX v1.4 update (the one here is a fan-translation package).
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
