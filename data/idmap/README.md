# Id tables

One folder per conversion (`mhxx-mh4u/`: MHXX to MH4U), one CSV per kind of id, read by `mhuc convert` (src/mhuc/quests/convert.py, docs/architecture.md#quests). They ship **empty**: their rows come from the maintainer's dumps and from decisions, and are added as they are settled. A converter refuses a quest whose ids aren't all here.

| Column | Meaning |
|---|---|
| `source` | the id in the source game, as text (see each table) |
| `target` | the MH4U id, an integer (decimal or `0x` hex) |
| `source_name`, `target_name` | names, for review (from the games' text or the catalog) |
| `how` | how the row was established (`mhuc idnames`, check Q22 in specs/quest.md, gives candidate names for ids from your own quests): a catalog match, an in-game check (docs/checks.md), or a decision; a new MH4U id says where it was allocated (reference/README.md#mh4u-monster-tables) |

| Table | `source` key | `target` |
|---|---|---|
| `monster.csv` | `emNNN` for a large monster (from its `.sem` file name), `small:N` for an `.esl` entry's monster byte | MH4U monster id (`.mib` definitions; id-tables.md) |
| `map.csv` | MHXX map number (`.mib` 0x14) | MH4U map (`.mib` 0xC4) |
| `area.csv` | `map:area` for a boss's `.sem` area, `map:eslN` for the Nth `.esl` area | MH4U area number on the target map |
| `item.csv` | MHXX item id | MH4U item id |
| `objective.csv` | MHXX objective type | MH4U objective type (not used yet: objectives come from the template) |

Which monster *version* a row points at (an MH4U monster or a new id for the GU version) is the open "monster versions" decision: a row records one when it is taken, never before.
