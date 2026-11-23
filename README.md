# MH Ultimate Collection

A content mod for [MH4UltimateDC](https://github.com/CompaLarios18/MH4UltimateDC), the static-recompilation PC port of Monster Hunter 4 Ultimate. It brings Monster Hunter 3 Ultimate's and Monster Hunter Generations Ultimate's maps, monsters and systems, underwater combat included, into MH4U as one package.

**This repository contains no game data.** Every asset and every behaviour comes from the player's own dumps of the games, converted on their own machine by the tools here. See [LEGAL.md](LEGAL.md).

## The fidelity rule

Everything new is extracted from the game it comes from, both its assets and its behaviour. Nothing is recreated. The only exceptions are things no game ever had, such as Insect Glaive or Charge Blade underwater. Those are authored and listed in the [authored register](docs/sources/authored-register.md).

| Source | Supplies |
|---|---|
| MH4U USA v1.3.0 | the base game and engine |
| MH3U (3DS) | 3U maps, monsters, swimming code, underwater motions |
| MHXX (3DS) | GU-era models, textures, code and data |
| MHGU (Switch) v1.4.0 | English text only |

## Layout

| Path | What |
|---|---|
| `docs/design/` | design documents: plugin API, underwater, ID tables, reference recompiles, progression |
| `docs/sources/` | what each source game supplies; the authored register |
| `specs/` | one spec per file type (`.ksy` + notes), each field marked verified or unverified |
| `STATUS.md` | where the project stands and what's next; rewritten every session |
| `tools/doctor.py`, `tools/workspace/` | the workspace check, and the Claude files (CLAUDE.md, hook, skills) it installs |
| `tools/mhuc/` | Python toolkit: RomFS, ARC, textures, GMD text, class ids, the specs' checks, CLI |
| `tests/` | tests on generated fixtures only |
| `data/catalog/` | facts from public wikis, a source URL on every row |
| `plugins/` | native plugin sources (C), built against the engine fork's `include/mh4u_plugin.h` |

The engine side (the plugin API and engine changes) lives in [Cheeenxiii/MH4UltimateDC-fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork).

## Toolkit

```bash
python3 -m pip install -e .
mhuc --help
```

`mhuc` needs Python 3.10+ and nothing outside the standard library.

| Command | Does |
|---|---|
| `mhuc arc list FILE` / `mhuc arc extract FILE DIR` / `mhuc arc pack DIR FILE` | MT Framework ARC archives |
| `mhuc classid NAME...` | the engine's class-id hash of a type name |
| `mhuc gmd dump FILE` | a GMD text file as JSON |
| `mhuc tex info FILE` / `mhuc tex decode FILE OUT.ppm` | 3DS textures |
| `mhuc romfs list ROMFS.BIN` | the files of a RomFS image, read in place |
| `mhuc survey ROMFS.BIN [--workers N]` | the specs' with-game-files checks over a whole RomFS; prints counts only |
| `mhuc entropy PATH...` | size, 8-byte alignment and byte entropy of files or folders, to tell encrypted ones (saves, Extra Data) from plain; prints counts only |
| `mhuc xfs dump FILE` | an MT XFS file (`.supp`, `.pop`, `.list`, …) as JSON, its schema included; either byte order |
| `mhuc decrypt KIND IN OUT --key FILE [--mode M]` | DLC and Extra Data crypto: `mh4u-save` (modes normal, card, quest), `mh4u-dlc`, `mhxx-dlc`, `mh3u-dlc` (MtCipher). The key comes from a file you supply; none is in this repository |
| `mhuc quest dump\|check KIND PATH...` | quests as JSON or as counts: `mh4u` (a `.mib` or a decrypted Extra Data `quest*` file), `mhxx` (a quest `.arc`, every part), `mh3u` (a `QTDS` file or a 3DS Extra Data `quest*` file) |
| `mhuc ingest`, `mhuc convert`, `mhuc build` | the pipeline from a dump to a mod (skeletons for now) |

## Tests

```bash
python3 -m pytest
ruff check .
```

## Licence

GPL-3.0-or-later, like the engine. See [LICENSE](LICENSE). Format knowledge credited in each spec under `specs/`.
