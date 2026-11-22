# In-game and with-game-files checks

Procedures for things that can only be checked with the game files or in the game. Each records its result in words (pass, fail, counts, versions seen), never as bytes from the files.

| Check | Where written | Needs |
|---|---|---|
| ARC round trip, size mask (C2, C3) | specs/arc.md | MH4U, MH3U, MHXX RomFS |
| TEX header reading, formats, flip (T1-T3) | specs/tex.md | MH4U RomFS |
| GMD versions, round trip (G1, G2) | specs/gmd.md | MH4U, MHXX RomFS |
| MOD versions (M1, M2) | specs/mod.md | MH4U, MH3U, MHXX RomFS |
| Quest ARC contents (Q1, Q2) | specs/quest.md | MH4U, MHXX RomFS |
| Native plugin in the game | docs/design/plugin-api.md | MH4U dump, the port |
| Class registries of MH3U and MHXX | docs/design/reference-recompiles.md | MH3U, MHXX code.bin |
