# maps.csv

One row per locale per game, in the order of the wiki's locale list template for that game.

| Column | Meaning | Source |
|---|---|---|
| game | MH3U, MH4U or MHGU | `list_source` |
| locale | the wiki's name | `list_source` |
| kind | locale, special (arenas, one-area fights) or settlement | the template's section |
| areas_in_game | the infobox `Areas` value marked for this game (or the only value); empty when the page gives none | `page_source` |
| habitat | the infobox `Habitat` types | `page_source` |
| page_source, list_source | the two pages read | — |

Underwater areas aren't listed (README.md). Their counts must come from the stage files.
