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

Whatever the runtime, the plugin ABI stays the only contract between mod and engine, so the mod moves with the engine without a rewrite.
