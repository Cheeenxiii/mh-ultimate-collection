# Decisions

Structural choices that shape the project. Only the maintainer settles an open decision; anyone may add facts or options to it.

## Settled

### 0001. MH4U is the base game

Settled by the maintainer on 2026-11-23.

MH4U's own systems are code: expeditions and relics, Guild Quests, Frenzy and Apex, walking around Dundorma in a room. Content (monsters, maps, quests, gear) is mostly data. Carrying data to the game whose systems we want is cheaper than carrying systems to another game.

| Alternative | Why not |
|---|---|
| GU, on MHGURecomp | MH4U's systems would have to be ported as code |
| 3U, on Cha-Cha | both 4U and GU carried in, no multiplayer upstream, and a Wii U build while our 3U source is the 3DS one |

GU-only systems (Hunter Styles, Hunter Arts, GU's Kinsect) are therefore not part of the base.

### 0002. Monsters are ported onto MH4U's engine

Settled by the maintainer on 2026-11-24.

A GU monster's code depends on MHXX's enemy layer, most of which MH4U lacks. Linking that layer beside MH4U's would put two enemy engines in one game, and MH4U's status, parts, AI sensors and multiplayer sync would not see the monster. So each handler is reimplemented on MH4U's `uEnemy`, from the source's recompiled code, keeping its frame values and call order. MHGU Definitive Edition does the same in the other direction.

## Open

| Decision | The question | Options |
|---|---|---|
| Combat base | which GU combat systems come in | MH4U's only; some as switches; GU's on GU content only |
| Monster versions | which version of a monster that several games have | MH4U's where it exists; the newest; a pick per monster |
| Runtime | stay on Azahar's core or go native | Azahar core; the fork's `native` branch; wait for upstream |
| Progression | how players reach 3U and GU content | hubs per game; one shared hub; quest categories per game; merged key quests; hubs later |
| Shared systems | skills, meals, Kinsect, Palicos, points, rank unlocks | 4U's everywhere; each content's own; a pick per system |
| Map versions | 3U's or GU's version of a shared locale, and whose lighting | 3U's (keeps water); GU's; both as separate maps |
| Music versions | which game's arrangement of a shared theme | first game's; the content's own game's; MH4U's |
| GU Switch assets | whether HD Switch assets may come in | no; an optional pack from the player's Switch dump; change the source rule |

Each one in detail below. Facts and options only: none of them is chosen.

### Combat base

GU's combat systems are code, not data, so they are the costliest content in the mod: Hunter Styles, Hunter Arts, GU's Kinsect (nectar stats, evolution forms, elements), the Sword and Shield oils, Palico customisation.

| Option | Gives | Costs |
|---|---|---|
| MH4U's combat only | one consistent combat system, the least work | GU players lose Styles and Arts |
| Some GU systems as switches, per player or per quest | choice | each system ported as code and tested against the others |
| GU's combat on GU content only | GU content plays as in GU | two combat systems side by side |

Underwater, Styles and Arts would also need movesets no game ever had (see [underwater.md](underwater.md)).

### Monster versions

Some monsters appear in more than one game ([data/catalog/monsters.md](../data/catalog/monsters.md) lists each once per game). The versions differ in data, moves, AI and model. How a 3U or GU monster runs is settled (0002); which version of a shared monster the mod uses is not.

| Option | Gives | Costs |
|---|---|---|
| MH4U's version wherever MH4U has the monster | no porting for those | 3U and GU versions are lost |
| The newest game's version | the latest design | ports replace MH4U monsters |
| A pick per monster | the best of each | a choice to justify per monster |

### Runtime

The engine runs the game's code natively, but system services, graphics, audio and multiplayer come from Azahar's 3DS core. The fork's `native` branch mirrors upstream's work towards a build without Azahar. Network rooms, the base of the port's multiplayer, work on the Azahar core today. Upstream's maintainer had not answered an issue between 2026-11-01 and 2026-11-23.

| Option | Gives | Costs |
|---|---|---|
| Stay on the Azahar core | works today, multiplayer included | depends on an emulator core |
| Carry the native branch forward in the fork | a real PC port | a large amount of engine work |
| Wait for upstream | no work on our side | no date |

Whatever the runtime, the plugin ABI stays the only contract between mod and engine, so the mod moves with the engine without a rewrite. [MHGURecomp](https://github.com/morerokk/MHGURecomp) is a reference for a native system layer.

### Progression

MH4U has its own hubs (Val Habar, Cheeko Sands, Dundorma), village and guild quest lines, and High and G Rank gates. 3U brings Moga and Port Tanzia; GU brings Bherna and its other villages. New monsters and maps must be reachable somehow.

| Option | How it plays | Work | Fidelity | Risks |
|---|---|---|---|---|
| A. A hub per game | 3U content in a Moga or Tanzia hub, GU content in Bherna, MH4U's hubs as they are; a gate switches between them | high: each hub's stage, NPCs, shops and quest board converted | high | MH4U's hub code may assume its own hubs; saves keep per-game progress |
| B. One shared hub | new quests on MH4U's boards, new monsters in MH4U's ranks | lowest: quest lists grow | lower: 3U's and GU's villages don't appear | rank and unlock flags must make room; quest counts per board may be fixed |
| C. Shared hub, a quest line per game | a "3U" and a "GU" category on the board, each in its own star order | medium | medium | needs a free quest category or a way to add one |
| D. Hubs later | B or C first, A's hubs as a later wave | staged | grows over time | two systems to keep working |
| E. Merged key quests | one story through MH4U's hubs; each rank's key quests drawn from all three games, the urgent quest picked among theirs | medium | medium: every quest is its own game's, the selection is authored | balancing every rank; the games' key quests don't line up |

Constraints whatever the option:

- **Length.** A full story per game makes the whole very long; GU alone has more quests than MH4U. C and E keep the total down, A and D add it up.
- **Difficulty curves.** 4U's and GU's ranks roughly line up. 3U's don't: one 3U rank spans a wide range, and its gear expects the rank's early monsters to be farmed first. Re-ranking 3U quests is authored balance work, recorded in the authored register.
- **Unlocks tied to Hunter Rank.** The Wyporium and the Wyceum unlock at given ranks. If one rank-up counts for every game, they fire at the same point; if each game has its own ranks, they must stay reachable.
- **Saves.** B and C fit MH4U's save if quest-clear flags can be extended. A needs per-game progress, likely a side file kept by a plugin (MHGU Definitive Edition keeps such a mod save).
- **Online.** Quests must be identical for every player in a room: the same mod version on both sides.

Inputs before deciding: how MH4U stores quest lists and clear flags, whether quest categories are a fixed set, how hub stages load NPCs and shops.

### Shared systems

All three games have these systems but run them differently. Each needs its own choice: 4U's everywhere, each content's own game's, or a pick per system.

- **Skills:** different point totals, numbers of levels and effects for the same name. Critical Eye's top level gives a different affinity bonus in 4U and GU.
- **Meals:** 3U and 4U combine ingredients and a cooking method; GU unlocks set meals and adds a sauce.
- **Kinsect:** 4U's nectar system or GU's (also under "Combat base").
- **Palicos:** 4U's pair combination skills, or GU's class and skill customisation.
- **Points:** 3U's resource points (Moga Woods, the Argosy), 4U's expedition points, GU's Wycademy points. They can be kept apart, merged, or merged in part.
- **Rank unlocks:** the Wyporium and the Wyceum must stay reachable whatever progression is chosen, and the Wyporium trades parts of monsters that neither 3U nor GU has.

Facts for each choice go in `data/catalog/`, with a source URL per row, before options are costed.

### Map versions and lighting

Some locales exist in several games, in different versions: Deserted Island in MH3U (12 areas) and MHGU (10 areas), Misty Peaks in both ([data/catalog/maps.csv](../data/catalog/maps.csv)). Our GU-era source for maps is MHXX.

| Option | Gives | Costs |
|---|---|---|
| 3U's version | the underwater areas and the routes through them | GU's layout is lost |
| GU's version | GU's layout (camp, ledges, connections) | no water |
| Both, as separate maps | both | two maps to port and fit into progression |

Lighting: each game lights a locale differently, and lighting affects the whole scene. Either each map keeps its own game's lighting, or MH4U's lighting style is applied to imported maps (authored work, recorded in the register).

### Music and sound versions

Many themes and monster sounds exist in several games, sometimes rearranged (GU revisits older games' themes). Some monsters have a theme in one game and none in another, and the conventions differ: some games give most large monsters a theme, others play the area's music.

| Option, per theme or sound | Gives | Costs |
|---|---|---|
| Its first game's version | the original | may clash with the content's own game |
| The version of the game the content comes from | consistent with the content | |
| MH4U's, where MH4U has it | consistent with the base game | 3U and GU arrangements are lost |

A second question: whether a monster with no theme in its own game gets one from another. Formats and the work are in [audio.md](audio.md).

### GU Switch assets

MHGU on Switch has HD textures and a single-screen interface. The source rule takes only English text from it; GU-era models and textures come from MHXX 3DS.

| Option | Gives | Costs |
|---|---|---|
| Keep the rule | one consistent 3DS look | no HD |
| An optional pack built from the player's own Switch dump: textures, interface, 48 kHz Opus audio | HD for those who want it, base mod unchanged | a second asset pipeline |
| Change the rule | HD everywhere | the mod depends on a Switch dump |

Changing the rule means changing CLAUDE.md's rule 2 and [sources.md](sources.md).
