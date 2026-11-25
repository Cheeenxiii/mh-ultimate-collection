# Effect-id tables

One folder per source game (`mh3u-mh4u/`, `mhxx-mh4u/`), one CSV per kind of id, read by the
effect converters (`src/mhuc/effectmap.py`). They ship **empty**, like [idmap](../idmap/README.md):
their rows come from the maintainer's dumps and an in-game check, and are added as they are
settled. A converter refuses an effect id the table doesn't name, naming every missing id.

An effect id is the number a motion effect (`effect\mef\em\emNNN_*`) or an effect list
(`effect\efl\em\emNNN\...`) names, not a file path. MH3U's and MHXX's ids are their own spaces;
MH4U's is the one a port must write.

| Column | Meaning |
|---|---|
| `source` | the effect id in the source game, decimal or `0x` hex |
| `target` | the MH4U effect id, decimal or `0x` hex |
| `source_name`, `target_name` | names, for review (from the games' effect data or a catalogue) |
| `how` | how the row was established: the source's effect model matched to MH4U's by its name or shape, or an in-game check ([docs/checks.md](../../docs/checks.md)) |

| Table | `source` key | `target` |
|---|---|---|
| `effect.csv` | MH3U's or MHXX's effect id | the MH4U effect id that plays the same effect |

The format specs are [mef](../specs/mef.md) and [efl](../specs/efl.md); the check that lists which
ids a source file names is theirs.
