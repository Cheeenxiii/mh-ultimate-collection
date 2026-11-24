# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-24, after an unattended session that finished the monster port's step 1 (classes and vtables).

## Where we are

Phase: **engine work with the game files.** Both reference games recompile, and the RomFS surveys and step 1's first maps are merged (PRs #6, #7). Every open decision is in [open-decisions.md](docs/design/open-decisions.md).

This session ([report](docs/reports/2026-11-24-monster-port-classes.md), results in [monster-port.md](docs/design/monster-port.md), "Step 1 continued"):
- **Every class's vtable**, in all three games (99%), with MHXX's monster classes found through their CRO modules (fork `tools/mt_vtables.py`). Used as anchors, they double the function maps: 7,542 pairs with MHXX, 6,866 with MH3U, all held-out checks correct.
- **A GU monster needs MHXX's enemy layer.** `roEm001` imports 330 engine functions. 262 have no MH4U counterpart, mostly in classes MH4U lacks (`uFestaEnemy`, `uFestaChar`, `uEnemyBase`, GU's projectile classes). Whether GU monsters run with that layer or get rewritten on MH4U's `uEnemy` is now an open decision ("Monster versions").
- **MH3U runs Rathian on `uEm002`** (ids 1, 2, 62-65), found through MH3U's enemy factory (id-tables.md has its id-to-class table). The three Rathians are three codebases.

## Branches

- This repo: `monster-port-classes` (monster-port.md, id-tables.md, open-decisions.md, this report and STATUS), pushed, PR open.
- Fork: `uc/monster-port-classes` (`tools/mt_vtables.py`, `fnmap.py --vtables`, tests, `config/games/README.md`), pushed, PR open.

## Next tasks, in order

1. **MHXX module recompiles** (fork): recompile each `.cro` at a fixed base with the static library's addresses resolved, then link at run time in the harness. Done when `roEm001` gametests like the static code (0 differ). The report's checklist has the starting points.
2. **In-game checks Q17, Q19, E4** with `mhuc extdata testkit`. Done when the specs record the results and extra-data.md says which routes work.
3. **LMT version 66** (MH3U): a layout from the files and Cha-Cha, then L1 again. Unblocks the underwater motions ([underwater.md](docs/design/underwater.md)).
4. **Sound survey SN1** (specs/sound.md): sound entries per type and version in the three RomFS, counts only. Then a first converted GU quest and the first table-growing plugin (Definitive Edition's `allocations.toml` and `notes/registry.md` first).

## Housekeeping

- **Fork branches:** delete every remote branch except `main`, `native`, `uc/main` and the heads of open PRs (re-check with `git branch -r --merged` first). Fast-forward `native` and `main` to upstream's.
- **Fork default branch:** `uc/main`, if the maintainer agrees (Cheeenxiii/MH4UltimateDC-fork#4).
- **Merged session branches:** delete them in both repositories (`claude/practical-johnson-jobxzw`, `romfs-surveys`, `monster-port-step1`, `long-sessions` here; `uc/monster-port-step1` in the fork).

## Waiting on the maintainer

- Reviewing and merging this session's two PRs.
- The new open question in "Monster versions": GU monsters with MHXX's enemy layer, or rewritten on MH4U's `uEnemy`.
- Whether to contact MHGU Definitive Edition's maintainers about shared format specs.
- Running the test kit in game, and saying which region and language the Extra Data's game is.
- If server files should be decrypted: a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` in `.claude/settings.json`.
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The other open decisions in [open-decisions.md](docs/design/open-decisions.md): not ours to settle.
