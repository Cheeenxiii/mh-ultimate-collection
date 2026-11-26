# Actions

The action ids a port has to translate, and the facts each translation is checked against.
One file per ported monster and source game, read by `tools/check_actions.py`:

| File | Source game's code | `status` values |
|---|---|---|
| [rathian-gu.csv](rathian-gu.csv) | MHXX v1.4's `roEm001.cro` and its `static.crs` | `translated`, `mh4u`, `pending` |
| [rathian-3u.csv](rathian-3u.csv) | MH3U USA's `code.bin` and `exheader.bin` | `translated`, `pending` |

| Column | Meaning |
|---|---|
| `action` | the action id, `category/index` (or a category alone, when the dispatcher ignores the index) |
| `block` | the case block in the source game's dispatcher |
| `handler` | the handler unit the case block tail-calls, empty when the work is inline or a jump |
| `first_motion` | the first constant motion index the handler starts, empty when it computes it or starts none |
| `status` | `translated`: the runtime's monster module runs it; `mh4u`: MH4U's own handler already serves it; `pending`: still owed |

`rathian-3u.csv` holds all 191 ids MH3U's dispatcher handles. A 3U row is `translated` or
`pending` only: MH3U reaches every id on one of its own handlers, so no 3U id is left to an
MH4U handler.

Addresses, action ids and motion numbers only; nothing read from a file is stored here. The
checker walks the source game's dispatcher and first motion, compares, and prints counts and
ids only.
