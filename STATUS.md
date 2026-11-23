# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after a workspace session that ran `mhuc survey` on the MH4U, MH3U and MHXX RomFS. Every open with-RomFS check is now closed.

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly (MH3U: 33,283 functions, 0 differ; MHXX v1.4: a 2,000-function sample, 0 differ). The Extra Data web session (Q16, E6, the mod-quest chain, the MHXX converter: [report](docs/reports/2026-11-23-extra-data-records.md)) is merged.

This session, one survey per game ([report](docs/reports/2026-11-23-romfs-surveys.md)):
- **Passes:** Q6 (all 508 MH4U quests read, builder round trip equal, none byte-identical), Q13 (365 MH3U quests, each stored twice), G3 (27,138 MHXX label hashes match), M3 (34,370 models), E1 (110 `.emd`/`.etd` pairs).
- **Corrections:** a mesh's "group" is a group **id**, not an index (mod.md). The `.etd` hitzone table is **8 rows of 10 bytes**, its columns matched to Kiranico's chart. That match also shows **em001 is Rathian**, not Rathalos (emd.md, mod.md). Both checks were fixed in `mhuc` and tested.
- **What the versions mean for porting:** MHXX shares MH4U's LMT (67) and EMC (0x20120804), so GU motions and AI read as they are. MH3U's are older (**LMT 66**, which isn't laid out, and EMC 0x20110601), and that blocks reading the underwater motions. Collision is the other way round: MH3U shares MH4U's SBC class, MHXX has another (0x781ACA20).
- Survey outputs and probe scripts are in `game_files/work/survey/`, outside the repos.

## Branches

- This repo: `romfs-surveys` from `main` (the check fixes, the specs, the report), committed and not pushed; it goes up only on the maintainer's yes, then a PR.
- Fork: nothing in flight (`uc/main`; PR #5 squash-merged).

## Next tasks, in order

1. **In-game checks Q17, Q19, E4** with `mhuc extdata testkit`, on a console or in the port after the fork's extdata check (`docs/research/extdata.md`). Done when the specs record the results and extra-data.md says which routes work.
2. **The monster-port pipeline** ([monster-port.md](docs/design/monster-port.md)): step 1 (map MH3U/MHXX engine calls to MH4U's through a shared monster, em001 Rathian being one) can start with the reference recompiles.
3. **LMT version 66** (MH3U): a layout from the files and Cha-Cha, then L1 again. That unblocks the underwater motions ([underwater.md](docs/design/underwater.md)).
4. **A first converted GU quest**: decrypt the MHXX DLC (maintainer's machine), pick a quest on a shared locale, fill data/idmap/ row by row, run `mhuc convert`, then Q17's procedure. Done when it is listed in game.
5. **A first table-growing plugin**, then the **MHXX full gametest** and **MH3U targeted studies** (reference-recompiles.md, underwater.md). Smaller ones: MHXX's SBC class; the `.etd` part, sensor and ailment blocks.

## Waiting on the maintainer

- Running the test kit in game, and saying which region and language the Extra Data's game is.
- If server files should be decrypted: a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` in `.claude/settings.json`.
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The open decisions (combat base, monster versions, runtime, progression), now also which star scale and which quest ids converted quests get: not ours to settle.
