# Format specs

One spec per file type: a Markdown note (`<type>.md`) and, once the layout is known well enough, a Kaitai Struct description (`<type>.ksy`). `tools/check_specs.py` (run in CI) checks the rules below.

## Rules

- Every field table has the columns **Offset**, **Type**, **Name**, **Status** and **Source**.
- **Status** is one of:
  - `verified`: checked against real files with a written procedure (in the spec's *Checks* section). The check's result is described in words, never pasted as bytes.
  - `unverified`: taken from a public source and not checked yet.
  - `unknown`: nothing is known yet.
- **Source** names where the field comes from: a community tool or template (credited below), the engine's class registry (MH4UltimateDC `config/mt_classes.tsv`), or `ours` (our own reading of the engine's code, with the function named).
- Every spec has a front-matter block with `class`, `extension`, `games` and `status` (the lowest status of its fields).
- No bytes from game files, ever (LEGAL.md). Example values are synthetic.

## Credits

| Source | Licence | Used for |
|---|---|---|
| [svanheulen/mhff](https://github.com/svanheulen/mhff) | GPL-3.0 | ARC, TEX, MOD header, quest ARCs; its wiki's "MH4U rQuestData Format" and "MH4U DLC Encryption" pages for the `.mib` layout; "MH4U card1 Format", "MH4U Guild Quest Structure", "MH4U Equipment Structure" and "MH4U DLC Palico Format" for specs/extdata.md |
| [GrenderG/goshawk](https://github.com/GrenderG/goshawk) | AGPL-3.0 (the DLC files in it are Capcom's) | a preservation mirror of Capcom's DLC server; its MH4U quest files were read outside the repositories for check Q9 of quest.md, nothing copied |
| [svanheulen/mhef](https://gitlab.com/svanheulen/mhef) | GPL-3.0 | MH4U save, Extra Data and DLC encryption (`SavedataCipher`, `DLCCipher`); used outside the repositories, no code or key copied |
| [BoyClinton/Cha-Cha](https://github.com/BoyClinton/Cha-Cha) | GPL-3.0 | MH3U's DLC wire format and MtCipher's Blowfish variant (`runtime/os/dlc_server.cpp`); the XFS format (`docs/formats/xfs.md`); class ids and loaders (`config/dti.csv`, `symbols.txt`); no code copied |
| [Scrimas/MH4U-port-to-MHGU](https://github.com/Scrimas/MH4U-port-to-MHGU) (MHGU Definitive Edition) | GPL-3.0-or-later | MH4U sound layouts: waves, banks, requests, area emitters (`tools/snd4u2gu.py`, `snd_bgm.py`, `snd_area.py`); no code copied |
| [Matt-Wood-23/mh3u-quest-studio](https://github.com/Matt-Wood-23/mh3u-quest-studio) | MIT | the MH3U `QTDS` record and event-pack slots (`questlib/quest_format.py`, `dlc_pack.py`) |
| [ArmoredRaven17/mh3u-quest-randomizer](https://github.com/ArmoredRaven17/mh3u-quest-randomizer) | MIT | MH3U `QTDS` tail offsets (`scripts/build_data.py`) |
| [Silvris/MH-Tools-and-Scripts](https://github.com/Silvris/MH-Tools-and-Scripts) | see repository | MOD (MH3U, MHGU), TEX (mobile), GMD |
| [beeequeue/gmd](https://github.com/beeequeue/gmd) | MIT | the GMD v2 label hash functions (`src/encode.ts`); no code copied |
| [Scrimas/MHGU-Definitive-Edition](https://github.com/Scrimas/MHGU-Definitive-Edition) | GPL-3.0-or-later | MH4U `.emd`/`.etd` layouts (`tools/emdata4u.py`, `tools/dt_convert.py`, `notes/data.md`), read from its MH4U-to-MHGU monster ports; the 4U-to-GU mappings of hitsize, attackdata, sensor and rage blocks, of the `.emd` blocks `dtbase` holds, and the break records (`monsters/dalamadur/module/dala_break.c`); the three monster pairs used by specs/dttune.md; no code copied |
| [Kuriimu2](https://github.com/FanTranslatorsInternational/Kuriimu2) (`plugin_mt_framework`) | GPL-3.0 | ARC header variants, GMD v1/v2 |
| [3dbrew: GPU/Textures](https://www.3dbrew.org/wiki/GPU/Textures) | wiki | PICA200 texture formats and tiling |
| MH4UltimateDC `config/mt_classes.tsv`, `docs/research/mt-classes.md` | GPL-3.0 | class names, ids, sizes |
| `reference/` (MH3U, MHXX registries) | GPL-3.0 | class names, ids, sizes of the source games |

## Index

| Spec | Class | Status |
|---|---|---|
| [arc](arc.md) | rArchive | verified (MH4U, MH3U, MHXX) |
| [tex](tex.md) | rTexture | header and 11 formats verified; formats 6, 15, 16 open |
| [gmd](gmd.md) | rGUIMessage | layouts verified (MH3U v1-short, MHXX v2 and v2-32); v2 hashes open |
| [mod](mod.md) | rModel | version and header shape verified, the same in all three games; fields partial |
| [quest](quest.md) | rQuestData, rSetEmMain, rEmSetList, rRem, rQuestBattleData, rSuppItem | MH4U, MHXX `.mib` and MH3U `QTDS` headers verified on DLC quests; DLC crypto of all three; `.quest_btl` unknown |
| [lmt](lmt.md) | rMotionList | animations: MHGU Definitive Edition's version-67 layout, read on every MH4U and MHXX file (L1); MH3U is version 66 |
| [emd](emd.md) | rEnemyData, rEnemyTuneData | MH4U body volumes, hitzones, parts, attacks: from MHGU Definitive Edition, structure checked on all 110 pairs and hitzone columns laid out (E1); the 40-byte attack record placed from MH4U's own reader and checked against MHXX's and MH3U's records (E10) |
| [sound](sound.md) | rLtSoundSourceADPCM, rLtSoundBank, rLtSoundRequest, rMHSoundEmitter, … | MH4U layouts from MHGU Definitive Edition, unverified; class ids from the registries; every file's magic and version counted in all three games (SN1): MH3U one version older, MHXX's banks and requests GU's |
| [dttune](dttune.md) | rEnemyDtTune | MHXX HP, parts, hitzones, tuning: layout from MHXX's loader, checked on all 138 files (E2); blocks matched to MH4U's `.etd` on three monsters (E5) |
| [dtbase](dtbase.md) | rEnemyDtBase | MHXX map-hit spheres, joint points, part groups and the `.emd` scalars: layout from MHXX's loader, checked on all 138 files (E7); matched to MH4U's `.emd` on three monsters (E5) |
| [dtbparts](dtbparts.md) | rEnemyDtBaseParts | MHXX break and joint records: layout from MHXX's loader, checked on all 138 files (E7); break parts and joint records matched to MH4U's `.emd` on three monsters (E5); MH4U's sever records absent |
| [emstatus](emstatus.md) | rEnemyStatus | MH3U HP, parts, hitzones, break records, tuning: layout from MH3U's walk, checked on all 91 files (E3); HP and hitzones matched on Rathian (E5); break and second-level HP blocks counted on all 91 (E9) |
| [hitdata](hitdata.md) | rBodyData, rHitSize, rHitDataEnemy, rHitData | MH3U and MHXX hurt volumes, attack volumes, attack records: record sizes tile every file (E4); MHXX's match MH4U's (E5) and MH3U's attack records are placed and match on the fields MH4U kept (E8); MH4U's own record is laid out in specs/emd.md (E10) |
| [emc](emc.md) | rEnemyCmd | header verified in all three games (A1); bytecode from MHGU Definitive Edition |
| [sbc](sbc.md) | rCollision | magic and inner class verified (S1); layout from MHGU Definitive Edition |
| [xfs](xfs.md) | rSuppItem, rQuestList, rPopData, … | from Cha-Cha (Wii U); 3DS magic verified, the rest open (X1) |
