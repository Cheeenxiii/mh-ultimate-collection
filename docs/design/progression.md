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
| **E. Merged key quests** | one story through MH4U's hubs. At each rank, the key quests are a share of each game's own key quests (for example a third from 3U, a third from 4U, a third from GU). The urgent quest to rank up is chosen among the games' urgent quests for that rank | medium: like C, plus a choice of key quests per rank and an urgent-quest choice | medium: every quest is its source game's own, but the selection is authored (register it) | the selection and its balance are design work for every rank; the games don't have the same key and urgent quests per rank |
| **D. Era hubs later** | start with B or C; add A's hubs as a later wave | staged | grows over time | two systems to keep working |

## Constraints on every option

- **Length.** A full story per game makes the whole very long; GU alone has more quests than MH4U. Options C and E keep the total down, while A and D add it up.
- **Difficulty curves differ.** 4U's and GU's ranks roughly line up. 3U's don't: a single 3U rank spans a wide range of difficulty, and its gear progression expects the rank's early monsters to be farmed before its late ones. Re-ranking 3U quests is authored balance work, listed in the register. The quests' own values stay their source game's (quest-conversion.md).
- **Unlocks tied to rank.** Some MH4U features unlock at given Hunter Ranks (the Wyporium, the Wyceum). If one rank-up counts for every era, those unlocks must fire at the same point; if each era has its own ranks, they must stay reachable. See open-decisions.md, "Versions of shared systems".
- **Points and economies.** 3U's resource points, 4U's expedition points and GU's Wycademy points pay for different things (open-decisions.md).

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
