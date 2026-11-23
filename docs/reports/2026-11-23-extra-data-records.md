# Extra Data records: quests, DLC Palicos and cards (2026-11-23)

A web session with no RomFS or code dumps, run without the maintainer from 17:40 to 20:30 (Paris). The only game files were the maintainer's own uploads: MH4U Extra Data and save `system` (the same files as the previous session), and MH3U 3DS Extra Data and save `system`. mhef (GPL-3.0) was cloned into the scratchpad for its save-data key; that key, the decrypted files and every test file built from them stayed in the scratchpad, outside both repositories. Nothing from them was committed: only counts, sizes, offsets, names and procedures. The engine fork is unchanged.

## Done

| Task | Result | Where |
|---|---|---|
| The 28 bytes after a stored quest (Q16) | solved: they are the rest of the server file, decrypted up to its stated size, as in MH3U. The `.mib`'s SHA-1 with bytes 0 and 1 zeroed, 4 padding bytes (the server file's ciphertext), the size + 20 as a u32 BE. All 120 quests match; the padding bytes match the goshawk mirror's still-encrypted files (compared as stored, nothing decrypted). Q5 had missed it by hashing the whole file and comparing all 20 bytes | specs/quest.md |
| DLC Palicos in `otomo1` (E2, E6) | 9 slots of 0x90 bytes: the `.otb` record, zeros, the file name (`ot001_ger.otb`..`ot009_ger.otb`), then byte 15 of the record's SHA-1. The game writes each 0x98-byte decrypted server file at a 0x90 stride, then the name over the hash, so only the last slot keeps the hash tail, padding and size (the 12 bytes at 0x510). The `.otb` strings' padding rule rebuilds all 9 records byte for byte | specs/extdata.md |
| Card files (E1) | `card1`..`card3` and `cardbox` decrypt but are empty here. The mhff wiki's card layout tiles the file only with a 16-byte header: its first two rows are 8 bytes off (it counted the encrypted header) | specs/extdata.md |
| Guild quests | mhff's 304-byte layout written up, all unverified (no record in the data). Its monster id is one byte: recorded in id-tables.md as a save-side limit (ids up to 255) | specs/extdata.md, docs/design/id-tables.md |
| MH3U saves (E3) | `card*` and `cardbox` all zero, `system` plain with 37 non-zero bytes. Sizes only | specs/extdata.md |
| Re-encryption (E5) | `mhuc encrypt mh4u-save` with the file's own seed gives back `otomo1`, `quest1` and `card1` byte for byte | specs/extdata.md, `tools/mhuc/cli.py` |
| Tools | `mhuc extdata dump\|check\|rename` (cards, guild quests, Palicos; renaming recomputes the hash byte and tail), `mhuc questslot check\|put` (hash check; put a `.mib` or a copy of a stored quest with a new id and title, in the stored form, refusing used slots without `--replace`), `mhuc encrypt mh4u-save`. 124 tests, all on synthetic data | `tools/mhuc/extdata.py`, `quest.py`, `tests/test_extdata.py`, `test_quest_tools.py`, README |
| Design | Extra Data as a way into the game: quests (200 slots), Palicos (9), guild quests (150), what each could carry, as options | docs/design/extra-data.md, quest-conversion.md |
| In-game procedures | Q17 (a copied quest under a new id and title) and E4 (a renamed Palico), each with a second step that shows whether the hash is checked | specs/quest.md, specs/extdata.md, docs/checks/README.md |

## What it changes for the plan

- **The Extra Data route for quests is open on paper.** Nothing about a stored quest is unexplained any more, and `mhuc` writes one in the game's exact form and encrypts it back byte for byte. What's left is in the game: Q17.
- **Palicos are a second route**, with the same storage scheme. GU-era Palicos would need skill and look id tables, like quests.
- **One test file each for Q17 and E4 was built** from the maintainer's own files and left in this session's scratchpad (`q17/quest2`: quest2 with slot 0 copied to slot 38 as id 60999 "UC test"; `e4/otomo1`: the first Palico renamed "UC Test"). The scratchpad doesn't outlive the session. The procedures rebuild both in three commands.
- The stored Palicos are the `_ger` files, which suggests a European game or a German-language system. The base is MH4U USA v1.3.0; quests are the same in both regions, but region-specific data needs checking first.

## Not done

- Decrypting the goshawk mirror's server `.otb` files, which would confirm that each Palico record is stored as sent (the size trailers and padding bytes already point that way). The session's permission guard refused the decryption twice, even after the maintainer allowed it in chat. The guard isn't the project's to bypass, so it stayed undone. To allow it next time, add a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` to the repository's `.claude/settings.json`, or run the command on the maintainer's machine.
- Commits: this session's first seven commits carry the session's default author (`Claude`), not the repository-local identity the doctor expects. The doctor's `--fix` was run before the last commits; rewriting the pushed ones needed a force-push, which the guard refused. Re-authoring them before merging is the maintainer's call (a squash merge does it).
- A general `.mib` writer. Text layouts differ between quests (strings 0x20-aligned in some, packed in others), so `mib4_patch` edits in place only: the id, and titles no longer than the old ones.
- STATUS.md's next tasks 1 to 7: each needs the RomFS, code dumps or a display.

## Checklist for the next session

0. With a console or emulator save folder: run Q17 and E4. Their results decide whether Extra Data can carry mod quests and Palicos.
1. With the RomFS: Q6 and Q13 (quest checks on the game's own quests), then the `.emd`/`.etd` specs.
2. Re-running E1 to E6 and Q16 needs mhef's save key in a file outside the repositories (`mhef/mhef/n3ds.py`, class `SavedataCipher`). Then: `mhuc decrypt mh4u-save` each file (modes as in specs/extdata.md), `mhuc questslot check quest*.bin`, `mhuc extdata check otomo otomo1.bin`.
