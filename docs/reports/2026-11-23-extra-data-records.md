# Extra Data records, a quest writer and a converter (2026-11-23)

A web session with no RomFS or code dumps, run mostly without the maintainer from 17:40 to 20:30 (Paris). When asked to "aim wide", it went on past the Extra Data work. The only game files were the maintainer's own uploads: MH4U Extra Data and save `system` (the same files as the previous session), and MH3U 3DS Extra Data and save `system`. mhef (GPL-3.0) was cloned into the scratchpad for its save-data key. That key, the decrypted files, the fetched wiki pages, the id tables inferred from them and the test files all stayed in the scratchpad, outside both repositories. Nothing from them was committed: only counts, sizes, offsets, field meanings and procedures. Both repositories have an open PR: Cheeenxiii/mh-ultimate-collection#5 and Cheeenxiii/MH4UltimateDC-fork#5.

## Done

| Task | Result | Where |
|---|---|---|
| The 28 bytes after a stored quest (Q16) | solved: they are the rest of the server file, decrypted up to its stated size, as in MH3U. The `.mib`'s SHA-1 with bytes 0 and 1 zeroed, 4 padding bytes (the server file's ciphertext, matched against the goshawk mirror's still-encrypted files), then the size + 20 as a u32 BE. All 120 quests match | specs/quest.md |
| DLC Palicos in `otomo1` (E2, E6) | 9 slots of 0x90 bytes: the `.otb` record, zeros, the file name, then SHA-1 byte 15. The game writes each 0x98-byte decrypted server file at a 0x90 stride, so only the last slot keeps the hash tail. The `.otb` string padding rule rebuilds all 9 records byte for byte | specs/extdata.md |
| Cards, guild quests, MH3U saves (E1, E3) | sizes. The mhff card layout's first two rows are 8 bytes off. Guild quests store one-byte monster ids (id-tables.md) | specs/extdata.md |
| Re-encryption (E5) | `mhuc encrypt` with the file's own seed gives back `otomo1`, `quest1` and `card1` byte for byte | specs/extdata.md |
| `.mib` writer (Q18) | `mibwrite`: an editable model (raw bytes kept for everything unexplained) and a builder that lays the blocks out on 0x20 boundaries and recomputes every offset. The block order, terminators and the small-monster header's three equal offsets come from the 120 quests. Parse and model round-trip on all 120. `mhuc mib export/import` turns a quest into editable JSON and back | `tools/mhuc/mibwrite.py`, specs/quest.md |
| Quest fields against the wiki (Q20, Q21) | the public wiki's quest pages, 116 MH4U and 36 MH3U. MH4U: time 115/116, reward 115, sub-reward 116, fee 104 (12 differ). Stars are one 1–10 scale (1–3 Low, 4–7 High, 8–10 G). Map ids for 19 locales. Objective types: 0x1 hunt, 0x81 capture, 0x101 slay, 0x2 delivery, 0x204 special. Bits of 0xA0. Carve table and gathering rank by rank (both mark exactly the 24 arena quests). MH3U: fee, reward and time 36/36, stars 1–8, map ids for 12 locales | specs/quest.md |
| Monster ids to names (Q22) | `mhuc idnames` intersects quest ids with the wiki's monster categories. MH4U: 77 ids, 68 with one name; MH3U: 38 ids, 27. Derived from the game's files, so the tool refuses to write inside the repository | `tools/mhuc/idnames.py` |
| Converter | `mhuc convert quest --from mhxx` turns an MHXX quest into the MH4U model. Ids go through data/idmap/ (shipped empty, with a README). It refuses unmapped ids, listing them all, and lists every placeholder taken from an MH4U template (stars included, since the scales differ) | `tools/mhuc/convert.py`, data/idmap/, quest-conversion.md |
| Catalog overlap | `mhuc catalog overlap`: 15 of 3U's large monsters and 46 of GU's are in MH4U (matched by wiki page). GU shares 4 locales (Ancestral Steppe, Frozen Seaway, Primal Forest, the wiki's Dunes = Old Desert). So the cheapest first converted quest is a GU quest on one of those | data/catalog/overlap.md, quest-conversion.md |
| In-game test kit | `mhuc extdata testkit`: from the encrypted Extra Data folder, the files for Q17 (a copied quest, id 60999, "UC test" in place), Q19 (a rebuilt quest, id 61000, longer title) and E4 (a renamed Palico), encrypted, with a TESTKIT.txt | `tools/mhuc/extdata.py` |
| Tools, smaller | `mhuc extdata dump\|check\|rename`, `mhuc questslot check\|get\|put`, `mhuc encrypt mh4u-save` | README |
| Designs | Extra Data as a way into the game (quests, Palicos, guild quests); a local DLC responder: the protocol as goshawk serves it, and a key the server chooses, so no Capcom key is needed (unverified, check D1) | docs/design/extra-data.md, dlc-responder.md |
| Fork | `tools/extdata_path.py`: the extdata id from the exheader (3dbrew: storage info at 0x230), and Azahar's folder for it. Research note with the open check. Branch from `uc/main`; fork tests 1,026 passed | fork `tools/extdata_path.py`, `docs/research/extdata.md` |

Tests: 139 in this repository (all synthetic), ruff, `check_specs` and `check_no_game_data` clean.

### After the PRs: research on other projects

| Task | Result | Where |
|---|---|---|
| Related projects | a survey of 15 projects with licence and what each gives. The big find is Scrimas's MHGU Definitive Edition (GPL-3.0-or-later), which ports MH4U monsters into MHGU with readers for MH4U's `.emd`/`.etd`, models, animations, collision, AI bytecode, stages and quests. Others: MHGURecomp (MHGU Switch recompiled, MIT), the MHGU-Modding wiki, mh4edit, MHX data manager, an MHGU decomp, Tri's recompilation and tools | docs/sources/related-projects.md |
| `.emd`/`.etd` spec | STATUS's first RomFS task, written from MHGU-DE's readers: header words, body records (bone, shape, hitzone row, part, radius, offsets), visibility rows, the `.etd` part table, hitzone table, sensors, ailments, attack volumes and records, base HP. Its class ids match our registry. All unverified until check E1 on the RomFS | specs/emd.md, id-tables.md |
| Cross-checks | MHGU-DE agrees with our quest stat rows (and names the stat table), the reward box word, icon 98 = none, and the save key's place in the game's code. Its 0xAC "sub reward" disagrees with Q20 (0xB0), so the spec keeps 0xB0. `mod.md`'s unknown 0x1C-byte entries are skin palettes per MHGU-DE/RevilLib. SBC (collision) and EMC (AI) layouts went into their placeholders | specs/quest.md, extdata.md, mod.md, placeholders/ |

## What it changes for the plan

- **A mod quest can be written end to end without the RomFS.** The pipeline: export or convert to the JSON model, build the `.mib`, put it in a slot, encrypt. Every step reproduces the game's own form where the game's form is known. What's missing is the game's verdict: Q17, Q19 and E4, which the test kit prepares.
- **The first converted quest has a shape.** It is a GU quest on a shared locale with shared monsters, converted by `mhuc convert`. Its id tables would be filled from `mhuc idnames` and the maintainer's decisions. Stars, objectives and the other placeholders need decisions or more checks.
- **Many `.mib` header fields are now verified**, through the wiki's quest pages, a secondary source checked field by field with exceptions listed.

## Not done

- Decrypting the goshawk mirror's server files (`.otb`, the `DLC_*.txt` lists). The session's permission guard refused it twice, even after the maintainer allowed it in chat, and it wasn't bypassed. To allow it, add a `permissions.allow` rule for `Bash(python3 -m tools.mhuc.cli decrypt:*)` to `.claude/settings.json`, or run the command on the maintainer's machine. The DLC list format (D2) waits on it.
- Commit author: the first seven commits carry `Claude` instead of the repository identity (the force-push to fix them was refused). A squash merge fixes it.
- Id tables: left empty on purpose. Their rows are derived from the game's files and from decisions; `mhuc idnames` gives candidates.
- Nothing ran in the game or in the port.
- STATUS.md's RomFS tasks (`.emd`/`.etd`, Q6, Q13, table growth, gametests).

## Checklist for the next session

0. Maintainer: run the test kit (Q17, Q19, E4) on a console or in the port (fork's extdata check first). Its results decide routes 2 and 3.
1. With the RomFS: Q6 and Q13, then the `.emd`/`.etd` specs.
2. With the MHXX DLC decrypted (the maintainer's machine): choose a GU quest on a shared locale, run `mhuc idnames`-style matching for MHXX, fill data/idmap/ row by row, and convert it.
3. Re-running E1 to E6 and Q16 to Q22 needs mhef's save key in a file outside the repositories: `mhuc decrypt mh4u-save` each file, then `mhuc questslot check`, `mhuc extdata check otomo`, `mhuc idnames`.
