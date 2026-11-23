# Related projects and the base game: report (2026-11-23)

A web session with no game files. It started from questions about playing MH4U on the port, which led to reading upstream MH4UltimateDC's issues. Then it assessed three related projects, to see whether another base would spare the mod work. The maintainer settled the base game (MH4U) after reading the comparison. Docs only: no code, no game data, the engine fork unchanged.

## Done

| Task | Result | Where |
|---|---|---|
| Upstream issues | 26 issues read (12 open), no open PRs. None mention the European game or save compatibility. A Steam Deck crash in Game Mode (#52) and a failing Linux build of the code library (#60) were fixed in 0.1.6. The maintainer hasn't answered an issue since 2026-11-01 | open-decisions.md, "Runtime" |
| MHGU Definitive Edition | MH4U monsters added to MHGU (Switch). Its 4U readers (`emdata4u`, `emc`, `hagi4u`, `quest4u`, `items4u`) work from MH4U EUR v1.1. `allocations.toml` and the monster registry show how it grows GU's tables. GPL-3.0-or-later | docs/sources/mhgu-definitive-edition.md |
| MHGURecomp | native MHGU (Switch) port, no emulator core, MIT, very active; online play; mods at several levels, including code modules (which run Definitive Edition) | docs/sources/mhgurecomp.md |
| Cha-Cha, again | v0.2.1; the Cha-Cha-Plus fork adds a file overlay, a plugin API with fixed hook points, and very experimental online play. Already assessed in cha-cha.md | docs/sources/README.md |
| Base game | weighed MH4U, GU on MHGURecomp and 3U on Cha-Cha. MH4U's own systems are code and GU's or 3U's content is mostly data, so content moves to the game whose systems the mod wants. **Settled by the maintainer: MH4U** | docs/design/open-decisions.md |
| Decisions in one place | open-decisions.md lists every decision. Four were added: versions of shared systems (skills, meals, Kinsect, Palicos, points, rank-gated unlocks); map versions and lighting; music and sound versions; GU Switch assets (an optional HD pack is one option). CLAUDE.md rule 6 now points there | open-decisions.md, CLAUDE.md |
| Progression | option E (merged key quests: a share of each game's key quests per rank, and a choice of urgent quest), and constraints for every option (length, 3U's difficulty curve, rank-gated unlocks, point economies) | progression.md |
| Underwater | the staging option: keep a weapon class out of underwater quests until it has motions; Styles and Arts underwater added to the authored parts | underwater.md |
| Audio | never planned until now. MH4U's sound layouts (waves, banks, requests, area emitters) from Definitive Edition, credited and unverified. The registries show MH3U on MH4U's sound classes and MHXX on GU's. A design doc covers what the mod needs, the unknowns, the order of work and the in-game checks; "Music and sound versions" is a new open decision | docs/design/audio.md, specs/sound.md |
| Indexes | the reference projects in docs/sources/README.md and in the README | README.md |

## What it changes for the plan

- **STATUS task 1 (`.emd`/`.etd`) now has a starting layout.** It is Definitive Edition's, read from 4U EUR v1.1 and checked by rebuilding GU monsters. Each field still needs our own check on USA v1.3.0. Its `.text` addresses are shifted by region (the fork's shift table).
- **STATUS task 2 (growing a table) has a working pattern to read first**: `allocations.toml` (ids only grow) and a relocated registry.
- **The runtime question is sharper.** Upstream has been quiet for three weeks. Keeping the plugin ABI as the mod's only contract with the engine keeps every runtime option open.
- **Audio joins the plan.** Its first step (check S1) is a count-only survey that fits in the next RomFS session.

## Not done

- decompdex.com's summaries were blocked by the session's network; the projects' own repositories were read instead.
- MHGURecomp's `docs/STATUS.md` was read only in part.
- No contact with any of the projects' maintainers.
