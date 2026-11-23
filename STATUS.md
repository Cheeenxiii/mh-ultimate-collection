# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after a long web session on the maintainer's Extra Data: the stored-quest trailer solved, DLC Palicos, a `.mib` writer, quest fields checked against the wiki, an MHXX quest converter, an in-game test kit.

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly (MH3U: 33,283 functions, 0 differ; MHXX v1.4: a 2,000-function sample, 0 differ).

This session ([report](docs/reports/2026-11-23-extra-data-records.md)):
- **A mod quest can be built end to end without the RomFS**: `mhuc convert` (MHXX) or `mhuc mib export`, then `mhuc mib import` (the builder recomputes every offset; Q18 round-trips 120 quests), then `mhuc questslot put` (the stored form, Q16 solved), then `mhuc encrypt` (byte-exact, E5). The game's verdict is the open part: **Q17, Q19, E4**, prepared by `mhuc extdata testkit`.
- DLC Palicos (`otomo1`) use the same scheme ([extdata.md](specs/extdata.md)). Routes into the game are written up in [extra-data.md](docs/design/extra-data.md) and [dlc-responder.md](docs/design/dlc-responder.md), as options.
- `.mib` and `QTDS` fields checked against the wiki's quest pages (Q20, Q21): stars are one 1–10 scale in MH4U, map ids, objective types, fees, rewards, time. `mhuc idnames` infers monster ids to names (kept outside the repository).
- The cheapest first converted quest: a GU quest on a locale MH4U shares, with shared monsters ([overlap.md](data/catalog/overlap.md)). The id tables in data/idmap/ ship empty.
- The stored Palicos are `_ger` files: this Extra Data may be from a European game or a German-language system (the base is MH4U USA v1.3.0).
- Memory: cap big jobs with a cgroup at **6 GB** (one job, 4 workers). Fork recompiler tests need `PATH=/usr/lib/llvm-22/bin:$PATH`.

## Branches

- This repo: `claude/confident-gates-g95y9s`, pushed, PR [Cheeenxiii/mh-ultimate-collection#5](https://github.com/Cheeenxiii/mh-ultimate-collection/pull/5) open (its first seven commits carry the author `Claude`; a squash merge fixes it).
- Fork: `claude/confident-gates-g95y9s` from `uc/main` (`tools/extdata_path.py`), pushed, PR [Cheeenxiii/MH4UltimateDC-fork#5](https://github.com/Cheeenxiii/MH4UltimateDC-fork/pull/5) open.

## Next tasks, in order

1. **In-game checks Q17, Q19, E4** with `mhuc extdata testkit`, on a console or in the port after the fork's extdata check (`docs/research/extdata.md`). Done when the specs record the results and extra-data.md says which routes work.
2. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`). Needs the RomFS. Done when specs/ has both and id-tables.md's parts row points at them.
3. **Quest checks Q6 and Q13** (the game's own 508 `.mib` and MH3U's 365 `.quest`). Needs both RomFS; do them alongside task 2.
4. **A first converted GU quest**: decrypt the MHXX DLC (maintainer's machine), pick a quest on a shared locale, fill data/idmap/ row by row, run `mhuc convert`, then Q17's procedure. Done when it is listed in game.
5. **A first table-growing plugin**, then the **MHXX full gametest** and **MH3U targeted studies** (reference-recompiles.md, underwater.md).

## Waiting on the maintainer

- Reviewing and merging the two PRs.
- Running the test kit in game, and saying which region and language the Extra Data's game is.
- If server files should be decrypted in web sessions: a `permissions.allow` rule in `.claude/settings.json` (the guard refused it this session, even with the go-ahead in chat).
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The open decisions (combat base, monster versions, runtime, progression), now also which star scale and which quest ids converted quests get: not ours to settle.
