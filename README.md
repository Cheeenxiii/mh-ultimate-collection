# MH Ultimate Collection

MH Ultimate Collection brings Monster Hunter 3 Ultimate's and Generations Ultimate's monsters, maps and underwater combat into the PC port of Monster Hunter 4 Ultimate, built from your own game dumps.

It is a content mod for [MH4UltimateDC](https://github.com/CompaLarios18/MH4UltimateDC), on top of [our fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork) of it. MH4U stays the base game: its systems, hubs and online rooms are kept, and content from the other two games is added to them.

## Status

Nothing is playable yet. The repository has:

- `mhuc`, a toolkit that reads, writes and converts the three games' files: archives, textures, text, quests and save data;
- specs of those file formats;
- the reference recompiles of MH3U and MHXX, used to study the code that monsters are ported from;
- the mod's native plugins: `mods/force_action`, which makes a monster perform a chosen action so a ported move can be watched (the plugin's check, R1p), `mods/monster_ids`, which gives the ported monsters their own ids and answers MH4U's monster-id-indexed tables for them ([data/ids](data/ids/README.md)), and `mods/monster_motions`, which translates the motion number a ported monster's MH4U handler asks into the source game's animation (check [M1](docs/checks.md#the-motion-translation-m1)).

How it all fits together: [docs/architecture.md](docs/architecture.md).

## No game data

This repository contains no game data and nothing derived from it. Every tool works from dumps you made of games you own, on your machine. See [LEGAL.md](LEGAL.md).

Each piece of content comes from the game it belongs to:

| Game | Supplies |
|---|---|
| MH4U USA v1.3.0 | the base game and engine |
| MH3U (3DS) | 3U maps and monsters, swimming code, underwater motions |
| MHXX (3DS) | GU-era models, textures, code and data |
| MHGU (Switch) v1.4.0 | English text |

## Getting started

Python 3.10 or newer, no other dependency.

```bash
python3 -m pip install -e .
mhuc --help
```

Run the tests with `python3 -m pytest`. The tests against real game files run only when `MHUC_DUMPS` points at your dumps (layout in [tests/conftest.py](tests/conftest.py)).

## Licence

GPL-3.0-or-later. See [LICENSE](LICENSE). Credits for format knowledge are in [specs/README.md](specs/README.md).
