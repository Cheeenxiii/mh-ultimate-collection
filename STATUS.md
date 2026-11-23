# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after an unattended web session on the maintainer's MH4U and MH3U Extra Data: the stored-quest trailer solved, DLC Palicos specified, Extra Data writing tools.

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly (MH3U: 33,283 functions, 0 differ; MHXX v1.4: a 2,000-function sample, 0 differ). Quests read and check in all three games ([quest.md](specs/quest.md)), with a conversion design ([quest-conversion.md](docs/design/quest-conversion.md)).

This session ([report](docs/reports/2026-11-23-extra-data-records.md)):
- **Stored MH4U quests are fully understood** (Q16): the 28 bytes after each `.mib` are its SHA-1 (bytes 0 and 1 zeroed), padding and size, the server file decrypted up to its stated size, as in MH3U. `mhuc questslot put` writes a quest in that form; `mhuc encrypt` gives back the game's files byte for byte (E5).
- **DLC Palicos** (`otomo1`, [extdata.md](specs/extdata.md)): 9 slots, same scheme; the slot's last byte is SHA-1 byte 15. `mhuc extdata rename` edits one in the game's form.
- [extra-data.md](docs/design/extra-data.md): quests, Palicos and guild quests as ways into the game without touching the RomFS, as options. Guild quests hold one-byte monster ids.
- The stored Palicos are `_ger` files: this Extra Data may be from a European game or a German-language system (the base is MH4U USA v1.3.0).
- No public layout exists for `.emd`/`.etd`; that spec has to come from the files and the code. Adding a monster id means moving every bound in id-tables.md's "Bounds to move" list.
- Memory: cap big jobs with a cgroup at **6 GB** (one job, 4 workers). Fork recompiler tests need `PATH=/usr/lib/llvm-22/bin:$PATH`.

## Branches

This repo: `claude/confident-gates-g95y9s` has this session's commits on top of `main` (PR #3 is merged). It's pushed, with no PR yet. Its first seven commits carry the author `Claude` instead of the repository identity (see the report). The fork is unchanged. Nothing else is in flight.

## Next tasks, in order

1. **In-game checks Q17 and E4** (a copied quest under a new id, a renamed Palico; specs/quest.md, specs/extdata.md). Needs a save manager on a console or an emulator's save folder. Done when both results are in the specs and extra-data.md says which routes work.
2. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves. Needs the RomFS. Done when specs/ has both and id-tables.md's parts row points at them.
3. **Quest checks Q6 and Q13** (the game's own 508 `.mib` and MH3U's 365 `.quest`). Needs both RomFS; short, so do them alongside task 2.
4. **A first table-growing plugin**: grow one id-indexed table with `alloc` and repoint its readers. Done when a procedure in docs/checks/ passes in game.
5. **MHXX full gametest**, then **MH3U targeted studies** from Cha-Cha's swim and camera marks (underwater.md). Done as in reference-recompiles.md and underwater.md.

## Waiting on the maintainer

- Reviewing the branch and opening or merging its PR (a squash merge also fixes the commit author).
- Running Q17 and E4 in game, and saying which region and language the Extra Data's game is.
- If server files should be decrypted in web sessions: a `permissions.allow` rule in `.claude/settings.json` (the guard refused it this session, even with the maintainer's go-ahead in chat).
- A check of the port's pad features with the plugin, on a machine with a display; whether to offer the inline-cache fix to upstream.
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
