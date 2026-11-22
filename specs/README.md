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
| [svanheulen/mhff](https://github.com/svanheulen/mhff) | GPL-3.0 | ARC, TEX, MOD header, quest ARCs |
| [Silvris/MH-Tools-and-Scripts](https://github.com/Silvris/MH-Tools-and-Scripts) | see repository | MOD (MH3U, MHGU), TEX (mobile), GMD |
| [Kuriimu2](https://github.com/FanTranslatorsInternational/Kuriimu2) (`plugin_mt_framework`) | GPL-3.0 | ARC header variants, GMD v1/v2 |
| [3dbrew: GPU/Textures](https://www.3dbrew.org/wiki/GPU/Textures) | wiki | PICA200 texture formats and tiling |
| MH4UltimateDC `config/mt_classes.tsv`, `docs/research/mt-classes.md` | GPL-3.0 | class names, ids, sizes |

## Index

| Spec | Class | Status |
|---|---|---|
| [arc](arc.md) | rArchive | unverified (class-id hash verified) |
| [tex](tex.md) | rTexture | unverified |
| [gmd](gmd.md) | rGUIMessage | unverified |
| [mod](mod.md) | rModel | unverified, partial |
| [quest](quest.md) | rQuestData, rSetEmMain, rEmSetList, rRem | unverified, partial |
| [placeholders/](placeholders/) | enemy, stage and quest classes | unknown |
