# Sources

Where the mod's content and knowledge come from.

## Source games

| Game | Version | Supplies | Not used for |
|---|---|---|---|
| MH4U | USA v1.3.0 | the base game and engine | |
| MH3U | 3DS (USA) | 3U maps and monsters, swimming code, underwater motions and behaviour | text |
| MHXX | 3DS | GU-era models, textures, code and data | text |
| MHGU | Switch v1.4.0 | English text | assets, code |

Each player supplies their own dumps. The tools read them outside the repository.

## Authored register

Things no source game has, which the mod therefore makes. Add a row in the same commit as the work starts.

| Item | Why no source exists | Status |
|---|---|---|
| Charge Blade underwater moveset | Charge Blade first appears in MH4, after underwater combat was dropped | planned |
| Insect Glaive underwater moveset, and the Kinsect underwater | Insect Glaive first appears in MH4 | planned |

## Related projects

They inform our specs and designs, credited where used. None is a source of game content.

| Project | What it is | Licence | What it gives us |
|---|---|---|---|
| [MHGU Definitive Edition](https://github.com/Scrimas/MHGU-Definitive-Edition) | MH4U monsters ported into MHGU on Switch | GPL-3.0-or-later | readers for MH4U's monster data, AI, collision, motions and sound; its id allocation and mod save are models for ours. Its tools read MH4U **EUR v1.1**; ours read **USA v1.3.0**, the same code with small layout shifts and some functions changed between versions, so its addresses translate, they do not carry over ([the pairs](reference/README.md#mhgu-definitive-editions-pairs)) |
| [MHGURecomp](https://github.com/morerokk/MHGURecomp) | MHGU Switch recompiled for PC | MIT | a native system layer for MT Framework, and mod layering with per-entry archive merging |
| [Cha-Cha](https://github.com/BoyClinton/Cha-Cha) | MH3U Wii U recompiled for PC | GPL-3.0 | MH3U's DLC format, XFS, class names, underwater leads |
| [mhff](https://github.com/svanheulen/mhff), [mhef](https://gitlab.com/svanheulen/mhef) | format notes and ciphers for the PSP and 3DS games | GPL-3.0 | quest, card, Palico and equipment layouts; save and DLC ciphers |
| [goshawk](https://github.com/GrenderG/goshawk) | replacement DLC server for the 3DS and Wii U games | AGPL-3.0 | the DLC login protocol, read only: AGPL code can't be copied here |
| [mh4edit](https://github.com/Rokumaehn/mh4edit) | MH4U save editor | MIT | a cross-check of the guild quest record |
| [MHGU-Modding wiki](https://github.com/RTHKKona/MHGU-Modding) | community wiki | MIT | GU id lists by name |
| [Forge](https://github.com/Fexty12573/forge) | runtime hooking for MHGU | MIT | how a hooking layer for an MT game is shaped |
| [MHTrIDA](https://github.com/sepalani/MHTrIDA) | reverse-engineering tools for Monster Hunter Tri | see repository | Tri is 3U's base: a second reference for underwater code |
| [beeequeue/gmd](https://github.com/beeequeue/gmd) | a GMD reader and writer for MHGU (TypeScript) | MIT | a second implementation to test our GMD reader against |
| [mhx_data_manager](https://github.com/svanheulen/mhx_data_manager), [mhxqe](https://svanheulen.github.io/mhxqe) | MHX's DLC and quest import into Extra Data; a quest-text editor | see repository | how MHX stores imported quests: a lead for MHXX's Extra Data |
| [mhgu-decomp](https://github.com/mamotromico/mhgu-decomp) | an MHGU decompilation in its planning stage | GPL-3.0 | its function ledger uses the same addresses as our GU v1.4.0 code; it names only SDK functions so far, no game function |
| [Yakumo](https://github.com/TeamGDB/Yakumo) | a static recompilation of Monster Hunter Portable 3rd | see repository | another MT-era recompilation to compare approaches with |
| [umvc3-tools](https://github.com/tge-was-taken/umvc3-tools), [Gibbed.MT](https://github.com/gibbed/Gibbed.MT) | MT Framework tools for other Capcom games | see repositories | desktop MT Framework formats, close to but not the 3DS ones |

## What these projects make possible

Beyond the facts already in our specs:

- **Names for the MH3U recompile.** Cha-Cha's `config/symbols.txt` and `virtuals.csv` name about 36,000 functions by class and virtual slot on the Wii U build. A class's slot *n* is the same method on 3DS, so names carry over through our own class and vtable recovery, checkable by counting how many slots line up.
- **The `.quest_btl` format.** Cha-Cha names its loader (`rQuestBattleData::load`); its 3DS counterpart, found through the shared vtable slot, gives the layout.
- **Definitive Edition's readers as a second implementation.** Its MH4U readers for models, motions, collision and AI scripts can run beside `mhuc` on the same files before those specs are written. Its licence allows reuse with credit; whether to vendor its code is the maintainer's call.
- **Definitive Edition's id allocation and mod save** (`allocations.toml`, `notes/registry.md`, `notes/mod-save-format.md`): read them before the first plugin that grows a table. Written up with the alternatives in [decisions.md](decisions.md#0003-id-allocation-and-mod-saves).
- **MHGURecomp's runtime notes** (`docs/STATUS.md`, `docs/SWITCH_COMPARE.md`): read them before any work on a native runtime.
- **GU behaviour, observed.** Watching a GU monster run natively in MHGURecomp can complement the MHXX reference recompile. Switch code is a reference for behaviour only, never a source of assets.
- **Talking to Definitive Edition's maintainers:** specs of the formats both projects read would help both. The maintainer's call.

Format credits are in [specs/README.md](../specs/README.md).
