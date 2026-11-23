# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-24, after a workspace session on the monster port's step 1 (Rathian's engine calls across the three games).

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly (MH3U fully, MHXX v1.4 on a sample), and the RomFS surveys are merged (PR #6).

This session ([report](docs/reports/2026-11-24-monster-port-step1.md), results in [monster-port.md](docs/design/monster-port.md)):
- **MHXX keeps its monsters in CRO modules**: 109 `.cro` files (every monster, weapons, village, quest, title; 6.5 MB of code), outside `code.bin`. So the MHXX recompile has no monster behaviour code. The fork's new `tools/cro.py` loads all 109.
- **MHXX's Rathian was rewritten**: its functions don't pair with MH4U's. So the map goes engine to engine (`tools/fnmap.py`): 3,540 pairs with MHXX and 3,967 with MH3U, accurate to 99–100% on held-out tests.
- **Rathian's engine calls:** 60 of its 197 MH4U callees are placed in MHXX (48 confirmed by `roEm001`'s import table) and 37 in MH3U. The enemy layer is where the map is thin.
- MH3U has no `uEm001` class (`uEm002` holds an `Em001JointCallback`). Which class em001 gets is open.
- Scratch outputs are in `game_files/work/mport/`, outside the repos.

## Branches

- This repo: `monster-port-step1` from `main` (report, STATUS, monster-port.md and reference-recompiles.md), pushed, PR [Cheeenxiii/mh-ultimate-collection#7](https://github.com/Cheeenxiii/mh-ultimate-collection/pull/7) open.
- Fork: `uc/monster-port-step1` from `uc/main` (`tools/cro.py`, `tools/fnmap.py`, tests, `config/games/README.md`), pushed, PR [Cheeenxiii/MH4UltimateDC-fork#6](https://github.com/Cheeenxiii/MH4UltimateDC-fork/pull/6) open.

## Next tasks, in order

1. **Monster port, step 1 continued:** vtables of classes both games name (654 MH4U/MHXX, 593 MH4U/MH3U) as anchors; group the 276 unplaced `roEm001` imports by class; find MH3U's em001 class through the enemy factory. Done when monster-port.md lists Rathian's engine calls per class, with which ones MH4U lacks.
2. **MHXX module recompiles** (fork): recompile each `.cro` at a fixed base with the static library's addresses resolved, then link at run time in the harness. Done when `roEm001` gametests like the static code (0 differ).
3. **In-game checks Q17, Q19, E4** with `mhuc extdata testkit`. Done when the specs record the results and extra-data.md says which routes work.
4. **LMT version 66** (MH3U): a layout from the files and Cha-Cha, then L1 again. Unblocks the underwater motions ([underwater.md](docs/design/underwater.md)).
5. **A first converted GU quest**, then the first table-growing plugin (see the previous STATUS in git for their details).

## Waiting on the maintainer

- Reviewing and merging PRs #7 (this repo) and #6 (fork).
- Running the test kit in game, and saying which region and language the Extra Data's game is.
- If server files should be decrypted: a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` in `.claude/settings.json`.
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The open decisions (combat base, monster versions, runtime, progression, star scale and quest ids for converted quests): not ours to settle.
