# monsters.csv

One row per monster per game, in the order of each game's list page (large, then small).

| Column | Meaning | Source |
|---|---|---|
| game | MH3U, MH4U or MHGU | the list page |
| monster | English name, the wiki's spelling | the list page |
| size | large or small (the list's section) | the list page |
| new_in_game | yes when the list marks the name in bold (its first appearance) | the list page |
| class | the monster page's infobox `Class` (Leviathan, Flying Wyvern, ...) | `page_source` |
| original_game | the infobox `Original Game` | `page_source` |
| source_game | the dump this version would come from (fidelity rule), not a wiki fact | README.md |
| list_source, page_source | the two pages read | — |

Monsters in more than one game are listed once per game: the mod ports each version as a monster of its own ([decision 0004](../../docs/decisions.md#0004-monster-versions)).
