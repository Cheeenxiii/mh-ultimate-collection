# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-24, after opening MHGU Switch as a code bridge (monster port, towards step 5).

## Where we are

Phase: **engine work with the game files.** Both reference games recompile, every MHXX module recompiles and tests against the original, and monsters are ported onto MH4U's `uEnemy` (settled). Every open decision is in [open-decisions.md](docs/design/open-decisions.md).

This session ([report](docs/reports/2026-11-24-gu-switch-bridge.md), results in [monster-port.md](docs/design/monster-port.md), "MHGU Switch as a bridge"):
- **MHGU Switch is 32-bit ARM** (clang, monsters linked statically). Fork `tools/extract_nsp.py` extracts its code with the maintainer's keys.
- **MHXX and GU are nearly the same game:** 2,949 shared classes; 26,406 MHXX functions mapped to GU, held out 161 of 165 right and none wrong; 95.3% triangle agreement with the MH4U↔MHXX map.
- **Definitive Edition's dumps are byte-identical to ours**: its 85 MH4U↔GU pairs carry to USA v1.3.0.
- **Rathian's worklist through GU:** of the 62, 2 resolved to MH4U, 28 placed in GU only (mostly projectile and GU-era code), 32 not placed; of the 33 call-site matches, 7 confirmed, 1 differs.

## Branches

- No session branch is in flight. This session's PRs merged on 2026-11-24 at the maintainer's request: fork #9 (`uc/nsp-extract`, the extractor), content #11 (`claude/gu-switch-map`).
- Scratch work to carry on from: `game_files/work/gusw/` (matcher, GU analysis) and `game_files/work/mport/actions/roEm001_imports_gu.tsv` (the worklist through GU); the report's checklist has the commands.

## Next tasks, in order

1. **The 62 GU engine functions Rathian calls:** pair `roEm001` with GU's `uEm001_00` by the shared action ids (a GU dispatcher reader for clang's switch forms), read the unplaced imports off aligned call sites, then write each one's entry (what it does, MH4U's way or "MH4U lacks it"). Done when all 62 have an entry and the 25 unchecked call-site matches are confirmed or dropped.
2. **Definitive Edition's `match4u.py` on our dumps** (numpy is now in the venv, at the maintainer's yes): its 4U↔GU pairs and ratings, read in its own folder `game_files/work/de/src/` with its `dump/` paths pointed at our identical files (read its `tools/setup.py` first). Done when its pairs are checked against our MH4U↔GU map and the worklist rerun with them.
3. **The matcher into the fork:** the GU-side analysis (functions, classes by `getDTI`) and `xmap` as tools with synthetic tests. Done when `game_files/work/gusw/` results reproduce from fork commands.
4. **Rathian's monster data** (step 3), MHXX's and MH3U's, then the action-forcing test aid and check R1.
5. **In-game checks Q17, Q19, E4** with `mhuc extdata testkit`. Done when the specs record the results and extra-data.md says which routes work.

## Housekeeping

- **Fork branches:** delete every remote branch except `main`, `native`, `uc/main` and the heads of open PRs (re-check with `git branch -r --merged` first). Fast-forward `native` and `main` to upstream's.
- **Merged session branches:** delete them in both repositories.

## Waiting on the maintainer

- Check R1 (an action id is the same move in both games), once the test aid exists; the in-game checks Q17, Q19, E4, and which region and language the Extra Data's game is.
- Whether to contact MHGU Definitive Edition's maintainers about shared format specs.
- If server files should be decrypted: a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` in `.claude/settings.json`.
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The other open decisions in [open-decisions.md](docs/design/open-decisions.md): not ours to settle.
