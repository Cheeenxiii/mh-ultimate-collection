# MHGU Definitive Edition: what it offers this project

[Scrimas/MH4U-port-to-MHGU](https://github.com/Scrimas/MH4U-port-to-MHGU), now titled *MHGU Definitive Edition* (GPL-3.0-or-later), adds MH4U monsters to **MHGU on Switch (v1.4)**, each with its arena, music, quests, armour, weapons, skills and Hunter's Notes entry. Nothing in GU is replaced. It runs on Ryujinx, yuzu/Eden, Atmosphère, and on [MHGURecomp](mhgurecomp.md), which loads its code module in its interpreter. Read on 2026-11-23 at release v3.1.0 (shallow clone of the default branch, `ARCHITECTURE.md`, `tools/`).

## How it relates to us

It is the same idea in the opposite direction. It keeps GU's systems and brings in 4U's content. We keep 4U's systems (expeditions, Guild Quests, Apex, Dundorma) and bring in 3U's and GU's content. The two projects read the same 4U files, so the format knowledge is shared, but the content doesn't overlap.

- **Its 4U source is MH4U EUR v1.1** (`dump/update/`). Our base is USA v1.3.0, and the fork also runs EUR v1.1. Per the fork's `config/shifts/eur_v110.txt`, data addresses agree between the two builds and `.text` addresses are shifted by region. Addresses in its tools (`KEY_4U = 0xe05e04`, carve table pointers) are EUR v1.1. Map each one through the shift table and check it on USA v1.3.0 before using it.
- **Licence.** GPL-3.0-or-later, like ours. Its contributors also agree that their work may be relicensed under a future merged project's licence, which doesn't affect reuse under the GPL. Take facts and formats first. If code is reused, keep its notice and credit it (CLAUDE.md, rule 4).
- **Ground rule 1 holds there too.** No game data is in git; every table is rebuilt from the user's dumps.

## What it gives us

| Area | What it has (file) | Use for us |
|---|---|---|
| Monster data | `tools/emdata4u.py`: 4U `em_data.arc` → `emd` (0x0a0e48d4) and `etd` (0x3d8bbbac) records (body and camera volumes, attack data, hit sizes), with a selftest that rebuilds GU Rathian and Kushala from their 4U data and diffs them | the starting layout for STATUS task 1 (`.emd`/`.etd` specs); every field still needs our own check on USA v1.3.0 |
| Enemy AI | `tools/emc.py`: `EMC\0` (rEnemyCmd) v0x20120804, the same in 4U and GU; groups, scripts, partly inferred opcodes | AI of GU monsters coming into 4U (same format), and a check on MHXX's |
| Carves | `tools/hagi4u.py`: 4U carve tables (pointer tables per monster and rank, shiny drops) | id-tables.md carve rows; MHXX → 4U carve conversion |
| Quests | `tools/quest4u.py` (4U quest arcs, `v005` records), `tools/extdata4u.py` (DLC quests in Extra Data, mhef's SavedataCipher) | cross-check of specs/quest.md and `mhuc quest` |
| Items | `tools/items4u.py`: 4U item records; how it appends items past GU's 2991 (`notes/items-append.md`) | the item-table row of id-tables.md |
| Other formats | `arc`, `tex`, `lmt` (animation), `mod` (model), `mrl` (materials), `sbc` (collision), `xfs`, `sdl` | compare with specs/ before writing ours |
| Growing tables | `allocations.toml` (every game-wide id the port takes: registry slot, em number, file ids, save slots, text, quest ids; ids only grow), `module/port.c` (relocated monster registry), GU's quest list raised from 864 to 1024 and 99 to 255 per star board | the design pattern for STATUS task 2 (first table-growing plugin) and for id-tables.md |
| Saves | `notes/mod-save-format.md`, `module/modsave.c`: the mod's own save files beside the game's, split and merged per character slot | an option for progression.md's per-era progress |
| Code mapping | `tools/apimap*.py`, `slotmap.py`: matches 4U functions and vtable slots to GU's | the same need when carrying MHXX code into 4U |
| Repository | `ARCHITECTURE.md` (what runs, what is tracked, what stays local, every dump path), `CONTRIBUTING.md`, `notes/porting-guide.md`, per-monster folders with their own `build.py` | a model for our own layout and docs |

## What it doesn't cover

- MH3U: two 3U monsters are on its wish list (Jhen Mohran, Dire Miralis), none ported.
- Underwater: not mentioned.
- 4U's systems (expeditions, Guild Quests, Apex): out of its scope, since GU is its base.

## Next steps it suggests

1. Before writing `specs/emd.md` and `specs/etd.md`, read `emdata4u.py` and record each field as `unverified` with it as the source, then verify on USA v1.3.0.
2. Read `allocations.toml` and `notes/registry.md` before designing the first table-growing plugin.
3. Consider talking to its maintainers: specs of the shared formats are useful to both projects.
