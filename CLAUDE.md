# Notes for AI-assisted sessions

Project: a content mod for MH4UltimateDC (the static-recompilation PC port of Monster Hunter 4 Ultimate) that brings MH3U's and MHGU/MHXX's maps, monsters and systems, underwater combat included, into MH4U. The engine side lives in `Cheeenxiii/MH4UltimateDC-fork` (branch `uc/main`); this repository holds everything about content.

## Start and end of a session

- **Start:** read [README.md](README.md) and [docs/architecture.md](docs/architecture.md). They describe the project as it is today; `git log` tells what changed and why. `/next` picks the task.
- **Tasks** are GitHub issues in this repository, grouped by milestone, each with a "Done when". One session works on one issue; `/plan` adds issues and milestones.
- **End:** `/done` runs the checks, commits, and opens a pull request that closes the issue. Write no session report, status file or task list anywhere in either repository.

## Ground rules (every session starts from these)

1. **No game data in any repository, ever.** That includes anything derived from it: traces, captures, disassembly listings, screenshots, extracted tables and converted assets. Addresses and names in config files and specs are fine. Work only from the maintainer's own dumps, outside the repository.
2. **Fidelity.** Each thing comes from its own source game:
   - MH4U USA v1.3.0: the base game and engine.
   - MH3U 3DS: 3U maps, monsters, swimming code and underwater motions.
   - MHXX 3DS: GU-era models, textures, code and data.
   - MHGU Switch v1.4.0: English text only.

   Author something only where no source exists, and record it in the [authored register](docs/sources.md#authored-register).
3. **Never wait on upstream MH4UltimateDC**, and keep the fork rebasable on it (see "The fork" below).
4. **Licence.** GPL-3.0-or-later. Check a tool's licence before reusing its code, and credit whatever informs a format spec (mhff, Silvris's templates, Kuriimu2).
5. **Web sessions have no game files.** Don't try to get them from anywhere.
6. **Don't settle open decisions.** They are listed in [docs/decisions.md](docs/decisions.md). Add facts and options there, then stop. Only the maintainer settles one.

## Conventions

- Python 3.10+, standard library only for `src/mhuc`. `reference/` may use the fork's requirements.
- Specs (`specs/`) mark every field `verified` or `unverified`, with its source. A field becomes verified only after a check against a real file, recorded as a procedure, never as the file's bytes.
- Catalog rows (`data/catalog/`) carry a source URL each. Facts only.
- Anything that can only be checked in the game gets a procedure in [docs/checks.md](docs/checks.md).
- Commits do one thing. The subject says what, in the imperative; the body says why.

## Where information goes

| Information | Goes in |
|---|---|
| what the project is and does now | README.md, docs/architecture.md, specs/, reference/README.md, updated in the same commit as the change |
| why a change was made | the commit message |
| a structural decision, settled or open | docs/decisions.md |
| a task, its progress, next steps | a GitHub issue |
| results of a session, dated "results (YYYY-MM-DD)" sections | nowhere in the repository |
| a command's options | its `--help`, not the docs |

The 2026-11-24 cleanup removed 14 session reports, a STATUS.md rewritten by every session, and design docs whose dated results had grown to 170 lines. Don't recreate them under another name.

## Tests

- One command: `python3 -m pytest` here, `tests/uc/run` in the fork. Lint with `ruff check .` before committing.
- Write a test only for a real risk or a bug that was fixed. Its name says the behaviour it protects.
- Prove it: break that behaviour in the code, see the test fail with a readable message, revert. A test that stays green is rewritten or deleted.
- A round trip through our own reader and writer proves nothing about the format. Compare against something independent: published test vectors, values computed by hand, or the player's own files (tests marked `game_files`, run with `MHUC_DUMPS`).
- Mock only what is out of reach (the game, the hardware), never the code under test.
- Test code in its own language with its own tooling: the fork's C++ plugin host is tested with CTest (`port/tests/plugins`), never through Python.

## The fork

- Its diff with upstream stays minimal: `git diff --stat upstream/main` lists only additions and the few hooks into upstream's files they need. Don't edit, reformat or "fix" upstream's code, docs or tests.
- The fork's own docs are `.github/README.md` and `docs/PLUGINS.md`; its own tests are `tests/uc/` and `port/tests/plugins/`.
- Logic specific to this mod doesn't go in the fork. The reference recompile tools once added 80,000 lines there; they live in `reference/` now.

## Before adding something

Check that it serves the pitch in README.md and that it belongs in this repository (content, formats, research) or the fork (an engine capability upstream could take). If it doesn't, say so instead of implementing it.
