# Actions

The action ids a port has to translate, and the facts each translation is checked against.
One file per ported monster, read by `tools/check_actions.py`:

| Column | Meaning |
|---|---|
| `action` | the action id, `category/index` (or a category alone, when the dispatcher ignores the index) |
| `block` | the case block in the source game's dispatcher |
| `handler` | the handler unit the case block tail-calls, empty when the work is inline or a jump |
| `first_motion` | the first constant motion index the handler starts, empty when it computes it or starts none |
| `status` | `translated`: the port's plugin runs it; `mh4u`: MH4U's own handler already serves it; `pending`: still owed |

Addresses, action ids and motion numbers only; nothing read from a file is stored here. The
checker walks the source game's dispatcher and compares, and prints counts and ids only.
