# First web session: report (2026-11-22)

All nine tasks of the brief's "First web session" have work committed. Two items are partial: the fork's `main`/`uc/main` branches wait on permission, and the catalog lacks the columns the wiki doesn't hold. Branch in both repositories: `claude/nice-knuth-5gd62h`.

## Done

| # | Task | Result | Where |
|---|---|---|---|
| 1 | Sync the fork | the session branch is fast-forwarded to upstream 6825147 (0.1.7); 84 commits, a clean fast-forward. **`main` and `uc/main` not pushed**: the session may push only its own branch | fork |
| 2 | Scaffold the content repo | LICENSE (GPL-3.0), LEGAL.md, CLAUDE.md with the ground rules, CONTRIBUTING.md, CI (pytest, ruff, spec checks, game-data guard) | this repo |
| 3 | Plugin API design | docs/design/plugin-api.md, naming each fork file changed | this repo |
| 4 | Plugin API implementation | `include/mh4u_plugin.h`, `port/src/plugin_host.h`, `port/src/plugins.{h,cpp}`, LoadCode wiring, `tools/mod_hooks.py`, `mods.py` and `build_game.py` changes, sample plugin, docs/MODS.md section; 27 new tests; fork suite 990 passed, 81 skipped | fork |
| 5 | Format specs | ARC, TEX, GMD (with .ksy), MOD, quest files; 24 placeholders (enemy, stage, quest classes); every field marked with status and source; `tools/check_specs.py` in CI | specs/ |
| 6 | mhuc toolkit | ARC read/write, class-id hash, 14 PICA texture codecs incl. ETC1/ETC1A4, TEX, GMD v1/v2, CLI (`arc`, `classid`, `gmd`, `tex`, stubs for `ingest`/`convert`/`build`); round-trip tests | tools/mhuc |
| 7 | Reference recompiles study | docs/design/reference-recompiles.md: every MH4U-specific assumption, a per-game config plan. No refactor (reason in the doc) | this repo |
| 8 | Content catalog | monsters (300 rows), maps (71), weapons (40) from monsterhunterwiki.org, a source URL per row, a README per table | data/catalog |
| 9 | Design docs | underwater.md, id-tables.md, progression.md (options only) | docs/design |

Verified on the way: the class-id hash `~crc32(name) & 0x7FFFFFFF` matches 989 of 990 ids in the fork's MH4U class registry (only `uShell052` differs).

## Couldn't be checked or done

- **Fork branches:** `main` (fast-forward to 6825147) and `uc/main` need an explicit go-ahead to push.
- **Plugin API in the game:** the port wasn't built here (it builds inside Azahar's tree). The host is tested on recompiled test code; `plugins.cpp` and the `arm_recomp.cpp` change are compiled only by the port's CI. The in-game procedure is in plugin-api.md.
- **Every spec field** except the class-id hash is unverified: no game files here.
- **Catalog gaps:** habitats per game, skeleton family, tier, underwater areas and underwater movesets aren't structured facts on the wiki. The catalog README says where each will come from.
- **Launcher warning and catalog badge** for native plugins: designed, not built (port/app).
- **Network:** the wiki was blocked at first; a personal environment "MH Ultimate Collection" (package registries plus monsterhunterwiki.org) was created and approved during the session.

## Checklist for the first session with game files

1. Push the fork's `main` and create `uc/main` if not done; rebase the plugin work onto `uc/plugin-api`.
2. ARC: run checks C2, C3 on MH4U, MH3U and MHXX; record MH3U's ARC version.
3. TEX: checks T1-T3; settle the header reading and the `--flip-y` question.
4. GMD: checks G1, G2; record versions per game.
5. MOD: check M1 (versions per game, 3U vs 4U skeletons).
6. Quests: checks Q1, Q2.
7. Class registries: `mt_dti.py` on MH3U's and MHXX's code; compare `uEm*` sizes with MH4U's 0x8d90.
8. Build the port with the plugin layer; run the sample plugin procedure (plugin-api.md).
9. Find the monster id table and the factory (id-tables.md, steps 1-2).
10. Start the MH3U reference recompile (reference-recompiles.md, steps 2-3).
