# Content catalog

Facts from the public [Monster Hunter Wiki](https://monsterhunterwiki.org) (monsterhunterwiki.org), read on 2026-11-22; the attack lists on 2026-11-25. Every row carries the URL of the page it came from. Nothing here comes from the games' files.

| Table | Rows | What |
|---|---|---|
| [monsters.csv](monsters.md) | 300 | every monster each game's list page shows, large and small, with class and first game |
| [maps.csv](maps.md) | 71 | every locale, special locale and settlement each game's locale list shows, with area counts |
| [weapons.csv](weapons.md) | 40 | the weapon classes of each game |
| [overlap.md](overlap.md) | — | generated: which 3U and GU monsters and locales MH4U already has (same wiki page), by `mhuc catalog overlap` |
| [versions.csv](versions.md) | 61 | which 3U and GU large monsters MH4U shares a player would notice differ from MH4U's, per axis, with the code and wiki evidence (decision 0004's amendment) |
| [attacks.csv](attacks.md) | 1,051 | the attack list each game's per-monster page gives, with its URL |

`game` is the wiki's game: MH3U, MH4U, MHGU. `source_game` (monsters) is the dump the mod takes that version from, per the fidelity rule: MH3U (3DS) for 3U, MH4U USA v1.3.0 for 4U, MHXX (3DS) for GU-era assets.

## What the brief asked for and isn't here yet

| Column | Why not | Where it will come from |
|---|---|---|
| habitats per monster per game | the wiki has them only in prose and per-game quest pages, not as structured fields | the games' stage and quest files (rEmSetList, rSetEmMain, .mib), once read |
| likely skeleton family | not a wiki fact; it's our inference | the reference recompiles and model comparisons (reference/README.md) |
| tier (rank, star level) | not a structured fact per monster | the games' quest data |
| underwater areas per map | the wiki has no structured field; a text match was too unreliable to keep | the stage files (rStageAreaInfo), once read |
| underwater movesets per weapon | the wiki has no page on underwater combat | MH3U's player command data (docs/architecture.md#underwater) |

The tables were made by a one-off script over the wiki's API (wikitext of the list pages, then each monster's and locale's infobox `Class`, `Original Game`, `Areas`, `Habitat`). `tests/test_catalog.py` checks their shape and sources.
