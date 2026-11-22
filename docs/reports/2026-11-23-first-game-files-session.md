# First session with game files: report (2026-11-23)

The first session with the maintainer's dumps, following the checklist at the end of [the web session's report](2026-11-22-first-web-session.md). The format checks are all run; the in-game and recompile items aren't started. Branches: `claude/game-files-checks` here, `uc/reference-classes` in the engine fork. Nothing from the files went into either repository: only counts, versions, hashes, addresses and names.

## Dumps

| Dump | State | Used as |
|---|---|---|
| MH4U USA cartridge | its game partition was already decrypted, but the NoCrypto flag wasn't set, so tools refused it; the flag is now set and the manual and update-data partitions decrypted. `tools/verify_ncch.py` passes every hash | the MH4U reference, with the v1.3.0 update |
| MH4U EUR cartridge | the same fix; its e-manual partition doesn't decrypt to anything valid (damaged in the dump, not used by the game) | checks only |
| MH4U v1.3.0 (USA) and v1.1.0 (EUR) updates | decrypted | the code the port targets |
| MH3U USA cartridge | decrypted | MH3U reference |
| MHXX JPN cartridge, v1.0 | decrypted | MHXX reference |
| MHXX v4.8.0 update ("GU Patch v2" and "English Full Patch" are the same file) | a fan-translation package: 652 of its archives were rebuilt by the translation's tools | not a reference; text and layout only with care |
| MHXX English (fan-patched cartridge) | the same 652 rebuilt archives | not a reference |

Extraction and all work files live in the maintainer's `game_files/work/`, outside both repositories.

## Done

| # | Item | Result | Where |
|---|---|---|---|
| 1 | Review and merge `uc/plugin-api` | already merged into `uc/main` (PR #1) before this session | fork |
| 2 | ARC C2, C3; MH3U's version | all 27,233 archives of the three games round trip once mhuc keeps the first stream's alignment (32 bytes, 0x8000 in MH3U) and each game's flags (0x20000000 MH4U, 0x40000000 MH3U and MHXX). **MH3U's ARC version is 0x10.** No size needs bit 24 or above | specs/arc.md |
| 3 | TEX T1-T3 | mhff's header reading fits every texture in all three games (98,823 checked); 11 formats decode correctly by eye; rows are top-down (`--flip-y` not needed); format 6 is 8 bits per pixel, meaning unknown | specs/tex.md |
| 4 | GMD G1, G2 | MH4U has no GMDs. MH3U uses v1 with a 0x20-byte header; MHXX uses v2 in two layouts (0x20- and 0x14-byte label entries). All 6,366 tables read and round trip | specs/gmd.md |
| 5 | MOD M1 | **version 0xE6 and the same header shape in MH4U, MH3U and MHXX**: the 3DS MH3U's models aren't the older format the plan assumed | specs/mod.md |
| 6 | Quests Q1, Q2 | MH4U: all quests in two archives (207 + 301 `.mib`). MH3U: loose `QTDS`, `QTDB` and `XFS` files, no quest archives. MHXX: one archive per quest with `.mib`, `.sem`, `.esl`, `.rem` | specs/quest.md |
| 7 | Class registries | MH3U 1,218 classes, MHXX 3,110, MH4U's regenerated identical to upstream. MH4U's and MHXX's monsters are near-uniform classes; **MH3U's each carry their own state** (up to 0x4f8 bytes over the base) | docs/design/reference-recompiles.md; fork `config/games/` |

New in `mhuc`: `romfs` (reads a RomFS image in place), `survey` (the checks above as one command, counts only), ARC version 0x10, alignment and flag handling, GMD `v1-short` and `v2-32`. 74 tests, all on synthetic data.

## What it changes for the plan

- **Models:** moving 3U models into MH4U needs no container conversion. The converter's work is skeletons, materials and what the models reference (M2).
- **Monsters:** 3U monsters can't be expected to be data on MH4U's monster base, as 4U's and XX's mostly are. Their behaviour is in 3U code, which points at the reference recompile of MH3U (step 3 of reference-recompiles.md) and code plugins rather than data conversion. This is a finding for the open decisions, not a decision.
- **Text:** MH3U's and MHXX's GMDs are readable and writable now; MH4U keeps its text elsewhere, so a text path into MH4U still needs describing.
- **MHXX source:** the official v1.4 update hasn't been dumped clean. GU-era content after v1.0 needs that dump.

## Not done

- **Port build and the sample plugin in the game** (checklist 8): not started. It builds inside Azahar's tree.
- **Monster id table and factory** (checklist 9, id-tables.md steps 1-2): not started.
- **MH3U reference recompile** (checklist 10): not started; step 1 (registries) is done.
- MOD M2 (field meanings), TEX formats 6, 15 and 16, the GMD v2 hash functions.

## Checklist for the next session with game files

1. Get a clean dump of the official MHXX v1.4 update (title version 4224) and add it to `config/games/mhxx/` if its code differs from v1.0's in ways that matter.
2. Build the port with the plugin layer (`uc/main`) and run the sample plugin procedure in docs/design/plugin-api.md.
3. id-tables.md steps 1-2: find MH4U's monster id table and factory in the v1.3.0 code.
4. reference-recompiles.md step 2: Ghidra export and function table for MH3U, then step 3 (recompile, gametest).
5. MOD M2: read one monster shared by all three games (Rathalos, `em001`) with a model tool, compare skeletons.
6. Describe MH4U's text resources (`rLayoutMessage` and friends) and MH3U's `QTDS` quest files.
