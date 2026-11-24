# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-24, after the module rerun and Rathian's action inventory (monster port, towards step 5).

## Where we are

Phase: **engine work with the game files.** Both reference games recompile, every MHXX module recompiles and tests against the original, and monsters are ported onto MH4U's `uEnemy` (settled). Every open decision is in [open-decisions.md](docs/design/open-decisions.md).

This session ([report](docs/reports/2026-11-24-rathian-actions.md), results in [monster-port.md](docs/design/monster-port.md), "Rathian's actions"):
- **Module recompiles are done:** 36,669 functions, none differ; the 40 leftovers are down to 3, all explained (one random-state artifact, two false entries now dropped).
- **One action scheme in all three games** (category and index bytes, a dispatcher slot). Rathian: MH4U 342 actions, MH3U 191, MHXX 301 (fork `tools/monster_actions.py`). **The ids are shared**: 80 MH4U↔MHXX handler pairs. A map built without them agrees on all 42 it holds.
- **The GU engine gap is 61 functions:** of `roEm001`'s 330 imports, 98 match MH4U code, 35 match by call site, and 136 of the rest are inherited vtable slots or data the code never calls.

## Branches

- All four of the last sessions' PRs merged on 2026-11-24 at the maintainer's request (content #9, #10; fork #7, #8). No session branch is in flight.
- Fork: `claude/practical-johnson-jobxzw` (PR #4, the fork README) is still open.

## Next tasks, in order

1. **The 61 GU engine functions Rathian calls** (monster-port.md, "Next, towards step 5"): for each, what it does and the MH4U way to do it, or "MH4U lacks it"; confirm or drop the 33 call-site matches. Done when all 61 have an entry.
2. **Rathian's monster data** (step 3), MHXX's and MH3U's, then the action-forcing test aid and check R1.
3. **In-game checks Q17, Q19, E4** with `mhuc extdata testkit`. Done when the specs record the results and extra-data.md says which routes work.
4. **LMT version 66** (MH3U): a layout from the files and Cha-Cha, then L1 again. Unblocks the underwater motions ([underwater.md](docs/design/underwater.md)).
5. **Sound survey SN1** (specs/sound.md): sound entries per type and version in the three RomFS, counts only.

## Housekeeping

- **Fork branches:** delete every remote branch except `main`, `native`, `uc/main` and the heads of open PRs (re-check with `git branch -r --merged` first). Fast-forward `native` and `main` to upstream's.
- **Merged session branches:** delete them in both repositories.

## Waiting on the maintainer

- PR #4 in the fork, and whether `uc/main` becomes the fork's default branch.
- Check R1 (an action id is the same move in both games), once the test aid exists; the in-game checks Q17, Q19, E4, and which region and language the Extra Data's game is.
- Whether to contact MHGU Definitive Edition's maintainers about shared format specs.
- If server files should be decrypted: a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` in `.claude/settings.json`.
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The other open decisions in [open-decisions.md](docs/design/open-decisions.md): not ours to settle.
