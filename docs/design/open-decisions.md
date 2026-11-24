# Decisions: settled and open

All of the project's decisions in one place. Sessions don't settle an open decision (CLAUDE.md, rule 6): they add options, costs and facts here or in the doc each row points to, and the maintainer decides. A settled row records who settled it, when, and the alternatives that were weighed.

## Settled

### Base game: MH4U

Settled by the maintainer on 2026-11-23.

The mod brings content into MH4U, on the MH4UltimateDC engine. Two other recompiled bases were weighed:

| Base | What it would have given | Why not |
|---|---|---|
| GU, on [MHGURecomp](../sources/mhgurecomp.md) | GU's content and systems as they are; working online play; mods at several levels; proof that 4U monsters can be added to GU ([MHGU Definitive Edition](../sources/mhgu-definitive-edition.md)) | MH4U's own systems (expeditions and relics, Guild Quests, Frenzy and Apex, the post-G-rank urgent quests, walking around Dundorma while in a room) are code. Moving them into GU is the hardest kind of port. Content (monsters, maps, quests, gear) is mostly data, so it is cheaper to carry content to the game whose systems we want |
| 3U, on [Cha-Cha](../sources/cha-cha.md) (Wii U) | underwater play as it is | 4U and GU would both have to be carried in; no multiplayer upstream; a Wii U PowerPC build, while our 3U source is the 3DS one |

What this leaves out: GU-only systems (Hunter Styles, Hunter Arts, GU's Kinsect system) are not part of the base. Whether they come in is the "Combat base" decision below.

## Open

### Combat base

Whether GU's combat systems come into MH4U: Hunter Styles, Hunter Arts, GU's Kinsect system (nectar stats, evolution forms, elements), the Sword and Shield oils, Palico customisation. Options:
- MH4U's combat only;
- some GU systems as switches (per player, per quest);
- GU's combat on GU content only.

These are code, not data, so they are the costliest content of the mod. Underwater, Styles and Arts would also need movesets no game ever had (see [underwater.md](underwater.md), "Authored parts").

### Monster versions

A monster that appears in more than one game is listed once per game in [data/catalog/monsters.md](../../data/catalog/monsters.md). Which version the mod uses (data, moves, AI, model) is open.

Facts for GU monsters (2026-11-24, [monster-port.md](monster-port.md), "Step 1 continued"): a GU monster's code lives in its CRO module and depends on MHXX's enemy layer. Rathian's module imports 330 engine functions, 262 of them with no MH4U counterpart, mostly in classes MH4U lacks (`uFestaEnemy`, `uFestaChar`, `uEnemyBase`, GU's projectile classes). How a GU monster runs is open:
- its module recompiled together with that part of MHXX's engine, beside MH4U's;
- its handlers reimplemented on MH4U's `uEnemy` (MHGU-DE's way, turned around).

### Runtime

The engine runs the game's code natively, but on Azahar's 3DS core for system services, graphics, audio and multiplayer. The fork's `native` branch works towards a build with no Azahar.

Facts as of 2026-11-23:
- Upstream MH4UltimateDC's maintainer hasn't answered an issue since 2026-11-01 (upstream issues read on 2026-11-23).
- Network rooms (the base of 4U's multiplayer in the port) work on the Azahar core today.
- The mod reaches the engine only through the plugin API (fork `include/mh4u_plugin.h`, ABI 2).

Options:
- stay on the Azahar core;
- carry the native branch forward in the fork;
- wait for upstream.

Whichever is chosen, keeping the plugin ABI as the only contract lets the mod move with the engine without being rewritten. [MHGURecomp](../sources/mhgurecomp.md) is a reference for a native system layer.

### Progression

How players reach 3U and GU content inside MH4U, and how the three games' rank structures fit together: [progression.md](progression.md).

### Versions of shared systems

Systems that all three games have but run differently. Each needs a choice: 4U's everywhere, each content's own game, or a per-system pick.

- **Skills:** different point totals, different numbers of levels, and different effects for the same skill name. For example, Critical Eye's top level gives a different affinity bonus in 4U than in GU.
- **Meals:** 3U and 4U combine ingredients and a cooking method; GU unlocks set meals and adds a sauce.
- **Kinsect:** 4U's nectar system or GU's (also under "Combat base").
- **Palicos:** 4U's pair combination skills, GU's class and skill customisation.
- **Points:** 3U's resource points (Moga Woods, the Argosy), 4U's expedition points, GU's Wycademy points. These can be kept apart, merged, or merged in part.
- **Unlocks tied to Hunter Rank:** MH4U features gated by rank (the Wyporium and the Wyceum, for example) must stay reachable whatever progression option is chosen, and the Wyporium trades in parts of monsters that neither 3U nor GU has.

Facts for each choice go in `data/catalog/` (a source URL on every row) before options are costed.

### Map versions and lighting

Some locales exist in more than one game, in different versions. The catalog lists Deserted Island in MH3U (12 areas) and MHGU (10 areas), and Misty Peaks in both ([data/catalog/maps.csv](../../data/catalog/maps.csv)). Our GU-era source for maps is MHXX (CLAUDE.md, rule 2).
- **Which version:** the 3U version keeps the underwater areas and the routes through them. The GU version changes the layout (camp, ledges, connections) and drops the water.
- **Lighting:** each game lights the same locale differently, and the difference touches everything in the scene, not only the textures. Options: each map keeps its own game's lighting; or 4U's lighting style is applied to imported maps.

### Music and sound versions

Many themes and monster sounds exist in several games, sometimes rearranged or remixed (GU revisits older games' themes). Options for each one: its first game's version, the version of the game the content is taken from, or MH4U's where MH4U has it. Where a monster has no theme in one game but has one in another, the question is whether it gets one. The conventions differ between games: some give most large monsters a theme, others play the area's music. [audio.md](audio.md) has the formats and the work; this is only the choice.

### GU Switch assets

MHGU on Switch has HD textures and a single-screen interface. Rule 2 takes only English text from it, and GU-era models and textures from MHXX 3DS. Options:
- keep the rule as it is;
- offer Switch textures, interface and audio (48 kHz Opus) as a separate, optional pack built from the player's own Switch dump, with the base mod unchanged;
- change the rule.

Changing it is a change to CLAUDE.md's rule 2 and to [docs/sources/README.md](../sources/README.md).
