# RomFS surveys: report (2026-11-23)

A workspace session with the maintainer's dumps, after the Extra Data web session was merged (PRs #5 in both repositories). It took the survey task: one `mhuc survey` per reference RomFS (MH4U USA, MH3U USA, MHXX JPN), each under the 6 GB cgroup cap with 4 workers. Outputs and probe scripts stayed in `game_files/work/survey/`. Nothing from the files went into the repository, only counts, versions and names. The engine fork is unchanged.

## Done

| Task | Result | Where |
|---|---|---|
| Q6 | all 508 MH4U `.mib` read; stars 1..10 and time 1..50 in all; carve tables 0–3; the builder's round trip gives an equal parse and model for all 508, none byte-identical (the game's own layout differs from the builder's) | specs/quest.md |
| Q13 | 730 MH3U `QTDS` records read, each ending at its file's end: 365 quests stored twice, byte for byte, loose in `/quest/us/` and in the quest archive | specs/quest.md |
| G3 | 27,138 MHXX v2 label hashes match `gmd.label_hashes`, 0 differ: the hash functions are verified | specs/gmd.md |
| M3 | every model readable and consistent: MH4U 10,472, MH3U 6,237, MHXX 17,661. The first run flagged a "group index over the count" in 10,690 models; in all of them, and all others, the value is one of the group entries' ids. The field is a group id, and the check now tests that. Mesh fields promoted | specs/mod.md, `tools/mhuc/mod.py`, `tests/test_mod.py` |
| E1 | 110 `.emd`/`.etd` pairs: magics, header offsets, body and visibility lists, attack volumes all hold. The hitzone table is 80 bytes in every `.etd`: 8 rows of 10 bytes (the only size fitting all 110). Its columns came from matching em001 with Kiranico's MH4U Rathian damage chart, exact in all eight; **em001 is Rathian**, not Rathalos as mod.md had it. The 24 attack-record blocks without an end word run into an unpointed tail; the check now says so | specs/emd.md, specs/mod.md, `tools/mhuc/emd.py`, `tests/test_emd.py` |
| L1 | MH4U 1,466 and MHXX 988 motion lists, all version 67, all readable (732,404 and 677,909 tracks). MH3U's 387 are all version 66, not laid out | specs/lmt.md |
| A1 | EMC: MH4U 124 and MHXX 139 at 0x20120804, MH3U 91 at 0x20110601; every table inside its file | specs/placeholders/rEnemyCmd.md |
| S1 | SBC: MH4U 626 and MH3U 344 with inner class 0x77CF8DF8; MHXX 1,052 with 0x781ACA20 | specs/placeholders/rCollision.md |
| Docs | the check index, underwater.md and monster-port.md updated with the versions | docs/checks/README.md, docs/design/ |

## What it changes for the plan

- **GU assets are closest to MH4U's.** MHXX shares MH4U's model, motion (LMT 67) and AI (EMC) versions, so a GU monster's motions and AI read as they are. Only its stage collision is another class.
- **MH3U's motions are the blocker for underwater.** LMT 66 isn't laid out; that is now a next task. Its stage collision, on the other hand, is MH4U's class.
- **Monster data can be compared with public tables.** The hitzone columns are known, so a converter's output can be checked against Kiranico row by row.
- em001 (Rathian) is the shared monster to use for step 1 of the monster port.

## Not done

- The `.etd` part table, sensors and ailments, the `.emd` scalars, and the hitzone row's last two bytes (stun presumably, then one unknown): no count reaches them.
- Which layout the game's own `.mib` files use (the builder's differs); Q19 still decides whether the game minds.
- Whether em001 is Rathian in MH3U and MHXX too (not checked).
- The in-game checks Q17, Q19, E4 and the fork's extdata check: they need the maintainer.

## Checklist for the next session with game files

1. Start from STATUS.md: in-game checks if the maintainer has results, otherwise the monster port's step 1 or LMT 66.
2. Re-run a survey with `systemd-run --user --scope -p MemoryMax=6G -p MemorySwapMax=0 game_files/work/venv/bin/python -m tools.mhuc.cli survey --workers 4 <romfs.bin>` from the content repo; each one takes seconds.
3. For LMT 66: compare one MH3U and one MH4U motion list of em001 header by header, with Cha-Cha's notes.
