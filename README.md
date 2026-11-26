# MH Ultimate Collection

MH Ultimate Collection brings Monster Hunter 3 Ultimate's and Generations Ultimate's monsters, maps and underwater combat into the PC port of Monster Hunter 4 Ultimate, built from your own game dumps.

It is a content mod for [MH4UltimateDC](https://github.com/CompaLarios18/MH4UltimateDC), on top of [our fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork) of it. MH4U stays the base game: its systems, hubs and online rooms are kept, and content from the other two games is added to them.

## Status

Nothing is playable yet. The repository has:

- `mhuc`, a toolkit that reads, writes and converts the three games' files: archives, textures, text and MH4U's message tables, camera lists, quests, a monster's files and sounds, and save data;
- specs of those file formats;
- the reference recompiles of MH3U and MHXX, used to study the code that monsters are ported from;
- the mod's native code: `mods/uc_runtime`, the one runtime for the mod's native code, which gives the ported monsters their own ids, answers MH4U's monster-id-indexed tables and name/notes message getters for them, lends a quest a free byte of the last 32 ids to a monster ported past the permanent range ([data/ids](data/ids/README.md)) and runs one C module per ported monster's actions ([decision 0013](docs/decisions.md#0013-one-runtime-for-the-mods-native-code)); its first module is GU Rathian's translated actions (the MHXX-only 3/98, 12/1-3, 4/27-32, 8/0 and category 17, and the shared categories 1 and 2 with 9/3 and 9/4, checks T1, [data/actions](data/actions/README.md)). `mods/force_action` is a debug tool that makes a monster perform a chosen action so a ported move can be watched (the plugin's check, R1p).

How it all fits together: [docs/architecture.md](docs/architecture.md).

What comes next is planned in the open: [milestones](https://github.com/Cheeenxiii/mh-ultimate-collection/milestones) for the goals, [issues](https://github.com/Cheeenxiii/mh-ultimate-collection/issues) for the tasks, and the [project board](https://github.com/users/Cheeenxiii/projects/1) for where each one stands.

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
