# Notes for AI-assisted sessions

Project: a content mod for MH4UltimateDC (the static-recompilation PC port of Monster Hunter 4 Ultimate) that brings MH3U's and MHGU/MHXX's maps, monsters and systems, underwater combat included, into MH4U. The engine side lives in `Cheeenxiii/MH4UltimateDC-fork` (branch `uc/main`); this repository holds everything about content.

## Ground rules (every session starts from these)

1. **No game data in any repository, ever.** That includes anything derived from it: traces, captures, disassembly listings, screenshots, extracted tables and converted assets. Addresses and names in config files and specs are fine. Work only from the maintainer's own dumps, outside the repository.
2. **Fidelity.** Each thing comes from its own source game:
   - MH4U USA v1.3.0: the base game and engine.
   - MH3U 3DS: 3U maps, monsters, swimming code and underwater motions.
   - MHXX 3DS: GU-era models, textures, code and data.
   - MHGU Switch v1.4.0: English text only.

   Author something only where no source exists, and record it in `docs/sources/authored-register.md`.
3. **Stay mergeable with upstream MH4UltimateDC, but never wait on it.** Small focused commits with one-sentence subjects. Update docs in the same commit as the code. Add pytest tests. In the fork, add new files rather than rewriting upstream's, and keep the plugin layer additive.
4. **Licence.** GPL-3.0-or-later. Check a tool's licence before reusing its code, and credit whatever informs a format spec (mhff, Silvris's templates, Kuriimu2).
5. **Web sessions have no game files.** Don't try to get them from anywhere.
6. **Don't settle the open decisions** (combat base, monster versions, runtime, progression). Write up the options and stop there.

## Conventions

- Python 3.10+, standard library only for `tools/mhuc`. Every tool change needs a test in `tests/` built on synthetic data.
- Run `python3 -m pytest` and `ruff check .` before committing.
- Specs (`specs/`) mark every field `verified` or `unverified`, with its source. A field becomes verified only after a check against a real file, recorded as a procedure, never as the file's bytes.
- Catalog rows (`data/catalog/`) carry a source URL each. Facts only.
- Anything that can only be checked in the game gets a written test procedure in `docs/checks/`.
