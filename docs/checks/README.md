# In-game and with-game-files checks

Procedures for things that can only be checked with the game files or in the game. Each records its result in words (pass, fail, counts, versions seen), never as bytes from the files.

Most checks run as `mhuc survey <romfs.bin>`, which reads a whole RomFS in place and prints only counts. Since 2026-11-23 it also runs the open checks Q6, Q13, Q18 (on the game's quests), E1, L1, M3, A1 and S1, so one run per game covers them all. Run it from your own extraction (`tools/extract_ncch.py --romfs` in the engine fork), outside this repository.

| Check | Where written | Needs | Status |
|---|---|---|---|
| ARC round trip, size mask (C2, C3) | specs/arc.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| TEX header reading, formats, flip (T1-T3) | specs/tex.md | MH4U RomFS | done 2026-11-23 |
| GMD versions, round trip (G1, G2) | specs/gmd.md | MH3U, MHXX RomFS | done 2026-11-23 |
| MOD versions (M1) | specs/mod.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| MOD field meanings (M2) | specs/mod.md | all three, a model tool | open |
| MOD mesh records against the header and buffers (M3) | specs/mod.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| Quest files (Q1, Q2) | specs/quest.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| Extra Data crypto and quest slots, `.mib` header on 120 DLC quests (Q3-Q5) | specs/quest.md | MH4U Extra Data | done 2026-11-23 |
| Extra Data cards, DLC Palicos, MH3U saves, re-encryption (E1-E3, E5, E6) | specs/extdata.md | MH4U, MH3U Extra Data | done 2026-11-23 |
| A changed DLC Palico through `otomo1` (E4) | specs/extdata.md | MH4U save, a save manager, the game | open |
| Stored-quest trailer: hash, padding, size (Q16) | specs/quest.md | MH4U Extra Data | done 2026-11-23 |
| `.mib` model and builder on 120 quests (Q18) | specs/quest.md | MH4U Extra Data | done 2026-11-23 |
| `.mib` and `QTDS` fields against the wiki: fee, rewards, time, stars, maps, objective types (Q20, Q21) | specs/quest.md | MH4U, MH3U Extra Data | done 2026-11-23 |
| A rebuilt quest in game (Q19) | specs/quest.md | MH4U save, a save manager, the game | open |
| A mod quest through an Extra Data slot (Q17) | specs/quest.md | MH4U save, a save manager, the game | open |
| A local DLC responder with its own key (D1), the DLC list files (D2) | docs/design/dlc-responder.md | the port; the goshawk mirror | open |
| AI (EMC) and collision (SBC) versions in the three games (A1, S1) | specs/placeholders/rEnemyCmd.md, rCollision.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 |
| GMD v2 label hashes against MHXX's tables (G3) | specs/gmd.md | MHXX RomFS | done 2026-11-23 |
| LMT versions and layout in the three games (L1) | specs/lmt.md | MH4U, MH3U, MHXX RomFS | done 2026-11-23 (MH3U: version 66, not laid out) |
| `.emd`/`.etd` layout on the 110 pairs (E1) | specs/emd.md | MH4U RomFS | done 2026-11-23 |
| Sound entries per type and version in the three games (SN1); MH4U sound layouts (SN2) | specs/sound.md | MH4U, MH3U, MHXX RomFS | open |
| `.mib` header on the game's own 508 quests (Q6) | specs/quest.md | MH4U RomFS | done 2026-11-23 |
| MH3U `QTDS` on the game's own 365 quests (Q13) | specs/quest.md | MH3U RomFS | done 2026-11-23 |
| Native plugin in the game | docs/design/plugin-api.md | MH4U dump, the port | open |
| Class registries of MH3U and MHXX | docs/design/reference-recompiles.md | MH3U, MHXX code.bin | done 2026-11-23 |