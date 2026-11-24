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
| [MHGU Definitive Edition](https://github.com/Scrimas/MHGU-Definitive-Edition) | MH4U monsters ported into MHGU on Switch | GPL-3.0-or-later | readers for MH4U's monster data, AI, collision, motions and sound; its id allocation and mod save are models for ours. Its dumps are byte-identical to ours, so its addresses apply |
| [MHGURecomp](https://github.com/morerokk/MHGURecomp) | MHGU Switch recompiled for PC | MIT | a native system layer for MT Framework, and mod layering with per-entry archive merging |
| [Cha-Cha](https://github.com/BoyClinton/Cha-Cha) | MH3U Wii U recompiled for PC | GPL-3.0 | MH3U's DLC format, XFS, class names, underwater leads |
| [mhff](https://github.com/svanheulen/mhff), [mhef](https://gitlab.com/svanheulen/mhef) | format notes and ciphers for the PSP and 3DS games | GPL-3.0 | quest, card, Palico and equipment layouts; save and DLC ciphers |
| [goshawk](https://github.com/GrenderG/goshawk) | replacement DLC server for the 3DS and Wii U games | AGPL-3.0 | the DLC login protocol, read only: AGPL code can't be copied here |
| [mh4edit](https://github.com/Rokumaehn/mh4edit) | MH4U save editor | MIT | a cross-check of the guild quest record |
| [MHGU-Modding wiki](https://github.com/RTHKKona/MHGU-Modding) | community wiki | MIT | GU id lists by name |
| [Forge](https://github.com/Fexty12573/forge) | runtime hooking for MHGU | MIT | how a hooking layer for an MT game is shaped |
| [MHTrIDA](https://github.com/sepalani/MHTrIDA) | reverse-engineering tools for Monster Hunter Tri | see repository | Tri is 3U's base: a second reference for underwater code |

Format credits are in [specs/README.md](../specs/README.md).
