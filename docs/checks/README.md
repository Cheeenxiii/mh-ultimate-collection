# In-game and with-game-files checks

Procedures for things that can only be checked with the game files or in the game. Each records its result in words (pass, fail, counts, versions seen), never as bytes from the files.

Most checks run as `mhuc survey <romfs.bin>`, which reads a whole RomFS in place and prints only counts. Run it from your own extraction (`tools/extract_ncch.py --romfs` in the engine fork), outside this repository.

| Check | Where written | Needs | Status |
|---|---|---|---|
| ARC round trip, size mask (C2, C3) | specs/arc.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| TEX header reading, formats, flip (T1-T3) | specs/tex.md | MH4U RomFS | done 2026-11-23 |
| GMD versions, round trip (G1, G2) | specs/gmd.md | MH3U, MHXX RomFS | done 2026-11-23 |
| MOD versions (M1) | specs/mod.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| MOD field meanings (M2) | specs/mod.md | all three, a model tool | open |
| Quest files (Q1, Q2) | specs/quest.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| Extra Data crypto and quest slots, `.mib` header on 120 DLC quests (Q3-Q5) | specs/quest.md | MH4U Extra Data | done 2026-11-23 |
| Extra Data cards, DLC Palicos, MH3U saves, re-encryption (E1-E3, E5) | specs/extdata.md | MH4U, MH3U Extra Data | done 2026-11-23 |
| A changed DLC Palico through `otomo1` (E4) | specs/extdata.md | MH4U save, a save manager, the game | open |
| `.mib` header on the game's own 508 quests (Q6) | specs/quest.md | MH4U RomFS | open |
| Native plugin in the game | docs/design/plugin-api.md | MH4U dump, the port | open |
| Class registries of MH3U and MHXX | docs/design/reference-recompiles.md | MH3U, MHXX code.bin | done 2026-11-23 |
