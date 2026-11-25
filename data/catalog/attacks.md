# attacks.csv

The attack list each game's per-monster page gives, for every monster in
[versions.csv](versions.md): one row per game, monster and attack name, read from the public
[Monster Hunter Wiki](https://monsterhunterwiki.org) on 2026-11-25. Every row carries the page
it came from. Nothing here comes from the games' files.

| Column | Meaning |
|---|---|
| `game` | MH4U, MH3U or MHGU, the wiki's game |
| `monster` | English name, the wiki's spelling ([monsters.csv](monsters.csv)) |
| `attack` | the attack's name as the page gives it, without the "(Unreviewed Translation)" marker |
| `source_url` | the per-monster page the row came from |

The lists are what [versions.csv](versions.md)'s `moves` axis compares: after a trailing
qualifier is dropped, the source game's names against MH4U's. The MH3U pages carry no attack
table, so MH3U rows have no entries; a page that lists no attacks contributes none.
