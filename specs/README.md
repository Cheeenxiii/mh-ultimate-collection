# Format specs

One spec per file type: a Markdown note (`<type>.md`) and, once the layout is known well enough, a Kaitai Struct description (`<type>.ksy`). `tools/check_specs.py` (run in CI) checks the rules below.

## Rules

- Every field table has the columns **Offset**, **Type**, **Name**, **Status** and **Source**.
- **Status** is one of:
  - `verified`: checked against real files with a written procedure (in the spec's *Checks* section). The check's result is described in words, never pasted as bytes.
  - `unverified`: taken from a public source and not checked yet.
  - `unknown`: a placeholder; nothing is known beyond the class.
- **Source** names where the field comes from: a community tool or template (credited below), the engine's class registry (MH4UltimateDC `config/mt_classes.tsv`), or `ours` (our own reading of the engine's code, with the function named).
- Every spec has a front-matter block with `class`, `extension`, `games` and `status` (the lowest status of its fields).
- No bytes from game files, ever (LEGAL.md). Example values are synthetic.

## Credits

| Source | Licence | Used for |
|---|---|---|
| [svanheulen/mhff](https://github.com/svanheulen/mhff) | GPL-3.0 | ARC, TEX, MOD header, quest ARCs; its wiki's "MH4U rQuestData Format" and "MH4U DLC Encryption" pages for the `.mib` layout |
| [GrenderG/goshawk](https://github.com/GrenderG/goshawk) | AGPL-3.0 (the DLC files in it are Capcom's) | a preservation mirror of Capcom's DLC server; its MH4U quest files were read outside the repositories for check Q9 of quest.md, nothing copied |
| [svanheulen/mhef](https://gitlab.com/svanheulen/mhef) | GPL-3.0 | MH4U save, Extra Data and DLC encryption (`SavedataCipher`, `DLCCipher`); used outside the repositories, no code or key copied |
| [BoyClinton/Cha-Cha](https://github.com/BoyClinton/Cha-Cha) | GPL-3.0 | MH3U's DLC wire format and MtCipher's Blowfish variant (`runtime/os/dlc_server.cpp`); no code copied |
| [Matt-Wood-23/mh3u-quest-studio](https://github.com/Matt-Wood-23/mh3u-quest-studio) | MIT | the MH3U `QTDS` record and event-pack slots (`questlib/quest_format.py`, `dlc_pack.py`) |
| [ArmoredRaven17/mh3u-quest-randomizer](https://github.com/ArmoredRaven17/mh3u-quest-randomizer) | MIT | MH3U `QTDS` tail offsets (`scripts/build_data.py`) |
| [Silvris/MH-Tools-and-Scripts](https://github.com/Silvris/MH-Tools-and-Scripts) | see repository | MOD (MH3U, MHGU), TEX (mobile), GMD |
| [Kuriimu2](https://github.com/FanTranslatorsInternational/Kuriimu2) (`plugin_mt_framework`) | GPL-3.0 | ARC header variants, GMD v1/v2 |
| [3dbrew: GPU/Textures](https://www.3dbrew.org/wiki/GPU/Textures) | wiki | PICA200 texture formats and tiling |
| MH4UltimateDC `config/mt_classes.tsv`, `docs/research/mt-classes.md` | GPL-3.0 | class names, ids, sizes |
| MH4UltimateDC-fork `config/games/` (MH3U, MHXX registries) | GPL-3.0 | class names, ids, sizes of the source games |

## Index

| Spec | Class | Status |
|---|---|---|
| [arc](arc.md) | rArchive | verified (MH4U, MH3U, MHXX) |
| [tex](tex.md) | rTexture | header and 11 formats verified; formats 6, 15, 16 open |
| [gmd](gmd.md) | rGUIMessage | layouts verified (MH3U v1-short, MHXX v2 and v2-32); v2 hashes open |
| [mod](mod.md) | rModel | version and header shape verified, the same in all three games; fields partial |
| [quest](quest.md) | rQuestData, rSetEmMain, rEmSetList, rRem | where each game keeps quests verified; layouts unknown |
| [placeholders/](placeholders/) | enemy, stage and quest classes | unknown |
