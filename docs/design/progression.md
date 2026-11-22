# Progression: options

How a player reaches 3U and GU content inside MH4U is an **open decision** (ground rule 6). This doc lays out the options and what each costs. It doesn't choose.

## The question

MH4U has its own hubs (Val Habar, Cheeko Sands, Dundorma and the rest), its own village and guild quest lines, and High and G Rank gates. 3U brings Moga and Port Tanzia; GU brings Bherna and the other villages (data/catalog/maps.csv lists the settlements). New monsters and maps must be reachable somehow.

## Options

| Option | How it plays | Work | Fidelity | Risks |
|---|---|---|---|---|
| **A. Separate hubs per era** | 3U content lives in a Moga or Port Tanzia hub, GU content in Bherna; MH4U's hubs stay as they are. A gate (a menu, a boat, a cart) switches era | high: each hub is a set of stage, NPC, shop and quest-board files to convert, plus the switching | high: each era keeps its own hub, quests and order | hub code in MH4U may assume its own hubs (ids, NPC tables); saves must keep per-era progress |
| **B. One shared hub** | everything from MH4U's existing hubs: new quests on the existing quest boards, new monsters in MH4U's rank structure | lowest: quest tables and lists grow (id-tables.md); no hub conversion | lower: 3U's and GU's quests are re-homed; their villages don't appear | MH4U's rank and unlock flags must make room; quest counts per board may be fixed |
| **C. Shared hub, era quest lines** | MH4U's hubs, but a separate quest category per era (a "3U" and a "GU" tab on the board, like MH4U's event quests), each with its own star order | medium: quest categories and unlock flags | medium: era order kept, villages not | needs a free quest category or a way to add one |
| **D. Era hubs later** | start with B or C; add A's hubs as a later wave | staged | grows over time | two systems to keep working |

## What each needs from the engine

- Quest list and unlock flags: found and growable for B, C, D (id-tables.md, quest ids).
- Hub stages and NPC tables: only A and D.
- Save data: B and C fit MH4U's save if quest-clear flags can be extended; A needs per-era progress, likely a side file kept by a plugin.
- Online: whichever option, quests must stay identical between players in a session (the port's network rooms): content is the same mod version on both sides.

## Inputs before deciding

1. How MH4U stores quest lists and clear flags (first session with game files).
2. Whether quest categories are a fixed set.
3. How hub stages load NPCs and shops.
4. The maintainer's preference on how 3U's story is felt (villages vs quests only).
