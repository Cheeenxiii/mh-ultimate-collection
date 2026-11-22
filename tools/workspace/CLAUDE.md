# MH Ultimate Collection workspace

<!-- Installed from mh-ultimate-collection/tools/workspace/CLAUDE.md by `tools/doctor.py --install`. Edit the source, not this copy. -->

A content mod that brings MH3U's and MHGU/MHXX's maps, monsters and systems into MH4U on top of MH4UltimateDC. This folder is the maintainer's workspace; start Claude sessions here, not inside a repository, so the hook and skills below load.

## Layout

| Folder | What | In git |
|---|---|---|
| `mh-ultimate-collection/` | content repo: specs, `mhuc` tools, design docs, reports, **`STATUS.md`** | yes (`Cheeenxiii/mh-ultimate-collection`) |
| `MH4UltimateDC-fork/` | engine fork: recompiler, port, plugin API, `config/games/` | yes (`Cheeenxiii/MH4UltimateDC-fork`) |
| `game_files/` | the maintainer's dumps and keys | **never** |
| `game_files/work/<dump>/` | extractions: `exheader.bin`, `code.bin`, `romfs.bin`, `info.txt` | never |
| `game_files/work/venv/` | Python venv with both repos' tools (pytest, ruff, unicorn, capstone) | never |

`mh-ultimate-collection/tools/workspace/dumps.json` maps each work folder to its dump and says which ones are references.

## Every session

- **Start:** the SessionStart hook prints the doctor's report and `STATUS.md`. Begin from STATUS.md's next tasks; `/next` does the orientation explicitly. The repos' own `CLAUDE.md` files hold the ground rules: read `mh-ultimate-collection/CLAUDE.md` before changing anything.
- **End:** `/handoff` updates STATUS.md, writes the report, runs the checks, commits and asks before pushing.
- **Doctor:** `python3 mh-ultimate-collection/tools/doctor.py` (`--fix` re-extracts dumps and rebuilds the venv, `--install` refreshes these workspace files, `--tests` runs both suites, `--fetch` updates remote state).

## Rules for this machine

- Keep everything inside this folder. Scratch output, extractions and venvs go in `game_files/work/`; `/tmp` and the session scratchpad don't survive a reboot.
- Run Python with `game_files/work/venv/bin/python` (by that path: resolving the symlink loses the venv).
- Big jobs over a whole RomFS: at most 4 worker processes and a memory cap (`ulimit -v 3000000`). The machine has 14 GB and crashed once at 16 workers.
- Both repos commit as Cheeenxiii (GitHub noreply address), set in each repo's own git config; never the machine's global identity. The doctor FAILs if a repo lacks it; `doctor.py --fix` sets it.
- Nothing from `game_files/` goes into either repository: counts, versions, hashes, addresses and names only. Both repos have a game-data check; run it before committing.
- Never look for or fetch keys or dumps elsewhere on the PC or online. `game_files/aes_keys.txt` is the maintainer's own; use it only when asked.
