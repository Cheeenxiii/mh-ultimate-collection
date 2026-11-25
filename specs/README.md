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
| [Scrimas/MHGU-Definitive-Edition](https://github.com/Scrimas/MHGU-Definitive-Edition) | GPL-3.0-or-later | MH4U `.emd`/`.etd` layouts (`tools/emdata4u.py`, `tools/dt_convert.py`, `notes/data.md`), read from its MH4U-to-MHGU monster ports; the 4U-to-GU mappings of hitsize, attackdata, sensor and rage blocks, of the `.emd` blocks `dtbase` holds, and the break records (`monsters/dalamadur/module/dala_break.c`); the three monster pairs used by specs/dttune.md; the camera list's version 4 to 5 record prefix and the offset fields that move with it (`tools/lcm4u2gu.py`); no code copied |
| [PredatorCZ/RevilLib](https://github.com/PredatorCZ/RevilLib) | GPL-3.0 | MT Framework LMT layouts per version (`src/mtf_lmt/*.inl`): the version groups that put 66 and 67 in one layout, the animation's flags, scene position and rotation and float-track block, the track's reference data and bounds, the track type and buffer type enums, and the keyframe buffer codecs (`codecs.hpp`, `bone_track.cpp`) that [lmt.md](lmt.md#keyframe-buffers) lays out, and the same track and codecs in [camera.md](camera.md)'s camera list; no code copied |
| [Kuriimu2](https://github.com/FanTranslatorsInternational/Kuriimu2) (`plugin_mt_framework`) | GPL-3.0 | ARC header variants, GMD v1/v2 |
| [Rokumaehn/mh4edit](https://github.com/Rokumaehn/mh4edit) | MIT | MH4U character save layout: profile, item and equipment boxes, equipped slots, guild quests and Palicos; no code copied |
| the MH4G save-editor wiki ([saveeditor_mh4g](https://w.atwiki.jp/saveeditor_mh4g/)) | not stated | MH4U pouches, guild-card quest counts and weapon usage; facts only, no text copied |
| [jvrs-0/mh4u-toolbox](https://github.com/jvrs-0/mh4u-toolbox) | MIT, from mh4edit | the Palico equipment box's offset; no code copied |
| GameFAQs MH4U save-editing threads ([1](https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/72464388), [2](https://gamefaqs.gamespot.com/boards/762804-monster-hunter-4-ultimate/77653912)) | forum posts | the monster log's offset and fields, the arena block; facts only |
| [3dbrew: GPU/Textures](https://www.3dbrew.org/wiki/GPU/Textures) | wiki | PICA200 texture formats and tiling |
| MH4UltimateDC `config/mt_classes.tsv`, `docs/research/mt-classes.md` | GPL-3.0 | class names, ids, sizes |
| `reference/` (MH3U, MHXX registries) | GPL-3.0 | class names, ids, sizes of the source games |

## Index

| Spec | Class | Status |
|---|---|---|
| [arc](arc.md) | rArchive | verified (MH4U, MH3U, MHXX) |
| [tex](tex.md) | rTexture | header and 11 formats verified; formats 6, 15, 16 open |
| [lmd](lmd.md) | rLayoutMessage | MH4U's message tables read on all 1,455 of the base and update RomFS (LM1): the header, the id-indexed `emName`/`emExp` tables (123 messages, message N names id N), the formatting and string records; the label hash and the file's trailer are open |
| [gmd](gmd.md) | rGUIMessage | layouts verified (MH3U v1-short, MHXX v2 and v2-32); v2 hashes open |
| [mod](mod.md) | rModel | version and header shape verified, the same in all three games; fields partial |
| [quest](quest.md) | rQuestData, rSetEmMain, rEmSetList, rRem, rQuestBattleData, rSuppItem | MH4U, MHXX `.mib` and MH3U `QTDS` headers verified on DLC quests; DLC crypto of all three; `.quest_btl` unknown |
| [lmt](lmt.md) | rMotionList | animations: MHGU Definitive Edition's layout and RevilLib's version groups, read on every MH4U and MHXX file (L1) and on all 387 MH3U files, which are version 66 (L3); every keyframe buffer of the three games decoded (L4), versions 66 and 67 differing in types 11 to 13, the version word a loader gate and the +0x38 float-track block read but unused (L5) |
| [mef](mef.md) | rMhMotionEffect, rEffectSequence, rProofEffectMotSequenceList | MH4U's MEF header and 0x48-byte records read on all 150 monster-archive entries (FX1); MH3U's ESQ and MHXX's PSL headers and slot tables on all 44 and 507 entries (FX2); the record key read from MH4U's loader and checked unique per file (FX3); the containers round-trip, and an ESQ/PSL to MEF conversion is refused until the record fields are placed, with the effect-id tables shipping empty |
| [efl](efl.md) | rEffectList, rProofEffectList | the EFL header shared by the three games read on all 7,475 monster-archive entries (EF1); MHXX's PEL magic and version on 280 entries (EF2); every list round-trips and the three versions convert between each other by the version word with the block carried (EF3); the block and the PEL body are not decoded |
| [emd](emd.md) | rEnemyData, rEnemyTuneData | MH4U body volumes, hitzones, parts, attacks: from MHGU Definitive Edition, structure checked on all 110 pairs and hitzone columns laid out (E1); the 40-byte attack record placed from MH4U's own reader and checked against MHXX's and MH3U's records (E10); the part record's kind placed from MH4U's own reader as the Insect Glaive extract kind, counted on all 110 pairs and matched to two public charts (E13); the joint and sever records' kinds and fields from MH4U's loader and cut-object code (E11, E12) |
| [sound](sound.md) | rLtSoundSourceADPCM, rLtSoundBank, rLtSoundRequest, rLtSoundStreamRequest, rMHSoundEmitter, … | MH4U stream requests (`.stq`) read on all 214 files (S4), the sequence record's readers and the loader's id index named from the code (S7); the wave, bank, request and emitter layouts from MHGU Definitive Edition are unverified; every file's magic and version counted in all three games (SN1): MH3U one version older, MHXX's banks and requests GU's; every sound file's size and each monster's set counted in all three (SN7) |
| [dttune](dttune.md) | rEnemyDtTune | MHXX HP, parts, hitzones, tuning: layout from MHXX's loader, checked on all 138 files (E2); blocks matched to MH4U's `.etd` on three monsters (E5) |
| [dtbase](dtbase.md) | rEnemyDtBase | MHXX map-hit spheres, joint points, part groups and the `.emd` scalars: layout from MHXX's loader, checked on all 138 files (E7); matched to MH4U's `.emd` on three monsters (E5) |
| [dtbparts](dtbparts.md) | rEnemyDtBaseParts | MHXX break and joint records: layout from MHXX's loader, checked on all 138 files (E7); break parts and joint records matched to MH4U's `.emd` on three monsters (E5); MH4U's sever records are in no block of either file, the monster class passing the joint to the engine's cut-part spawner and shipping a `_tail.mod` (E11) |
| [emstatus](emstatus.md) | rEnemyStatus | MH3U HP, parts, hitzones, break records, tuning: layout from MH3U's walk, checked on all 91 files (E3); HP and hitzones matched on Rathian (E5); break and second-level HP blocks counted on all 91 (E9) |
| [hitdata](hitdata.md) | rBodyData, rHitSize, rHitDataEnemy, rHitData | MH3U and MHXX hurt volumes, attack volumes, attack records: record sizes tile every file (E4); MHXX's match MH4U's (E5) and MH3U's attack records are placed and match on the fields MH4U kept (E8); MH4U's own record is laid out in specs/emd.md (E10) |
| [actiondata](actiondata.md) | none (in-image action data) | the 44-byte action-start record the two paired readers start animations from, the 8-byte command list the category-10/11 handler interprets, and the value curve an action's sub-handlers evaluate: every field placed from the readers, the interpreter and the evaluator, the shared 3/5 record rebuilt from MH3U's and compared with MH4U's own (N1), the four motions matched by their LMT signature (N2), the command lists left to MH4U's own handler (N3) and the curves carried (N4) |
| [emc](emc.md) | rEnemyCmd | header verified in all three games (A1); bytecode from MHGU Definitive Edition |
| [emc](emc.md) | rEnemyCmd | header, group and script tables verified in all three games (A1, A2); the instruction tables whose opcode arities differ (A3) and the loaders' version and group-row rules (A4); bytecode meaning from MHGU Definitive Edition, and what a converter must do for MH3U |
| [camera](camera.md) | rCameraList | MH4U and MHXX layouts, tracks and keyframe buffers verified (C1); MH3U ships no file of the class |
| [sbc](sbc.md) | rCollision | magic and inner class verified (S1); layout from MHGU Definitive Edition |
| [xfs](xfs.md) | rSuppItem, rQuestList, rPopData, rTexLayout, rSoundAttributeSe, … | from Cha-Cha (Wii U); the little-endian layout read on all 853 XFS files of MH3U's and MH4U's RomFS (X1): 845 in MH3U, 8 in MH4U, which ships no rTexLayout |
| [lyt](lyt.md) | rLayout | MH4U's HUD and menu layouts: header, texture slots, node chain and the common node header read on all 825 entries of the five languages (LY1); the per-type fields beyond position and the text string unverified |
| [save](save.md) | none (save-side files) | character save (profile, item and equipment boxes, pouches, guild quests, Palicos, monster log, guild card) and the system save's cipher and checksum, checked on the maintainer's saves (S1-S7); the character save's quest lists and the system save's fields open |
