# What each game supplies

The fidelity rule: everything new is extracted from the game it comes from, its assets and its behaviour both. Nothing is recreated.

| Source | Version | Supplies | Not used for |
|---|---|---|---|
| MH4U | USA v1.3.0 (update 0004000E00126300) | the base game and engine; everything the port runs | — |
| MH3U | 3DS (USA) | 3U maps, monsters, swimming code, underwater motions, underwater monster behaviour | text (except where no other source has it) |
| MHXX | 3DS | GU-era models, textures, code and data | text |
| MHGU | Switch v1.4.0 | English text only (GU-era names, descriptions, quest texts) | assets, code |

Each player supplies their own dumps (LEGAL.md). The tools read them outside the repository and write the converted mod to the player's machine.

Anything not supplied by one of these games is authored and listed in the [authored register](authored-register.md).

## Reference projects

Other projects on the same games. Their facts and formats inform our specs, credited where used. None of them is a source of game content.

| Project | Game and platform | Licence | Assessment |
|---|---|---|---|
| [Cha-Cha](https://github.com/BoyClinton/Cha-Cha) | MH3U, Wii U (recompile) | GPL-3.0 | [cha-cha.md](cha-cha.md) |
| [MHGU Definitive Edition](https://github.com/Scrimas/MH4U-port-to-MHGU) | MH4U monsters into MHGU, Switch (mod) | GPL-3.0-or-later | [mhgu-definitive-edition.md](mhgu-definitive-edition.md) |
| [MHGURecomp](https://github.com/morerokk/MHGURecomp) | MHGU, Switch (recompile) | MIT | [mhgurecomp.md](mhgurecomp.md) |

More projects that bear on this one, and what each could give, are listed in [related-projects.md](related-projects.md).
