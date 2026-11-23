# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after a web session that assessed three related projects and recorded the base-game decision (MH4U, settled by the maintainer).

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly:
- MH3U: 33,283 functions, every one gametested: 0 differ, 0 fail-fault, 0 missing targets.
- MHXX v1.4: 63,087 functions; a 2,000-function sample with 0 differing and 0 missing targets.

The MH4U quest format (`.mib`) is specified from mhff's wiki and partly verified on 120 DLC quests ([report](docs/reports/2026-11-23-dlc-quests-web-session.md)). The base game is settled: MH4U, with GU on MHGURecomp and 3U on Cha-Cha weighed and set aside. All decisions now live in [docs/design/open-decisions.md](docs/design/open-decisions.md) ([report](docs/reports/2026-11-23-reference-projects.md)).

Findings that steer the next steps:
- Downloaded quests sit in Extra Data as bare `.mib` files, 40 slots of 0x2010 bytes per `quest*` file, each ending with its file name (`mNNNNN.mib`), under mhef's `SavedataCipher`. That's a possible way in for mod quests without growing quest tables. Monsters come in waves; objective types are mapped by value, though their meanings aren't confirmed.
- Capcom's MH4U DLC server is gone (NXDOMAIN). Its files live on in the GrenderG/goshawk preservation mirror (AGPL-3.0, files Capcom's): server quests are bare `.mib`, identical to what the game stores, plus 28 bytes the game adds (unknown; they decide whether mod quests can go in through Extra Data). MHXX's DLC (173 quests) decrypts and fits mhff's MHXX `.mib` layout. MH3U's `QTDS` layout (from mh3u-quest-studio) is verified on the 38 USA DLC quests stored in clear in the maintainer's 3DS Extra Data; its DLC cipher is MT Framework's Blowfish variant (MtCipher, as Cha-Cha documents it): all 38 USA and 47 Japanese MH3G server quests decrypt. Its S-box quirk isn't in MH4U's or MHXX's DLC crypto, which standard Blowfish decrypts.
- Cha-Cha (MH3U Wii U recompile, GPL-3.0) is a strong lead for MH3U: DLC, formats, ~36,000 class-and-slot function names, and underwater state marks. Its addresses are Wii U PowerPC and must be re-found on 3DS. Assessment: [docs/sources/cha-cha.md](docs/sources/cha-cha.md).
- Quests are now fully readable and checkable in three games: `mhuc decrypt` and `mhuc quest` reproduce every check, and [docs/design/quest-conversion.md](docs/design/quest-conversion.md) maps 3U and GU fields onto MH4U's `.mib`, with three routes into the game (quest archives, Extra Data slots, a local DLC responder) left as options.
- `.emd`/`.etd` now have a public lead: MHGU Definitive Edition's `tools/emdata4u.py` reads 4U's `emd`/`etd` (from EUR v1.1), checked by rebuilding GU monsters. Its `allocations.toml` and monster registry are the pattern for growing tables. Assessment: [docs/sources/mhgu-definitive-edition.md](docs/sources/mhgu-definitive-edition.md). Its addresses are EUR v1.1: map `.text` ones through the fork's `config/shifts/eur_v110.txt` and check on USA v1.3.0.
- Chase every missing target and every rare `fail-fault` the gametest reports by tracing the reference. The inline-cache runtime fix is a candidate to offer upstream.
- Audio was never planned; now it is ([docs/design/audio.md](docs/design/audio.md), [specs/sound.md](specs/sound.md)). MH3U uses MH4U's sound classes (same ids). MHXX uses GU's, whose 4U → GU conversion Definitive Edition derived from Capcom's own pairs, so the reverse may give XX → 4U.
- Adding a monster id means moving every bound in id-tables.md's "Bounds to move" list.
- Memory: cap big jobs with a cgroup at **6 GB** (one job at a time, 4 workers). Fork recompiler tests need `PATH=/usr/lib/llvm-22/bin:$PATH`.

## Branches

This repo: `claude/practical-johnson-jobxzw` has this session's docs commits on top of `main` (PR #3 is merged). It's pushed, no PR yet. The fork is unchanged. Nothing else is in flight.

## Next tasks, in order

1. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves. Start from Definitive Edition's `emdata4u.py` and `hagi4u.py` (fields `unverified`, credited), then verify on USA v1.3.0. Needs the RomFS. Done when specs/ has both with verified/unverified fields and id-tables.md's parts row points at them.
2. **A first table-growing plugin**: grow one id-indexed table with `alloc` and repoint its readers. Read Definitive Edition's `allocations.toml` and `notes/registry.md` first. Done when a procedure in docs/checks/ passes in game.
3. **Quest check Q6 and sound check S1**: run the Q5 checks on the game's 508 `.mib` (specs/quest.md), and survey the sound entries of the three RomFS by type and version (specs/sound.md). Needs the RomFS; both are short, so do them alongside task 1.
4. **MH3U quest check Q13**: run the `QTDS` parse on the RomFS's 365 `.quest` files (specs/quest.md). Needs the MH3U RomFS; short, so pair it with Q6.
5. **MHXX full gametest** (every function, 4 shards, about 5 minutes). Done when reference-recompiles.md has its verdict counts and every non-agreeing function is explained.
6. **MH3U targeted studies** (swim state, oxygen, underwater camera in the harness), starting from Cha-Cha's swim and camera marks (underwater.md, "Leads from Cha-Cha"). Done when underwater.md cites what the harness showed.
7. **Cha-Cha names on the MH3U recompile** (fork): carry its class-and-slot names onto our 3DS vtables. Done when the fork's MH3U config has the names and a count of slots that matched.

## Housekeeping (first session on the maintainer's machine)

Cloud sessions can push only their own branch, so these wait for a local session:
- **Fork branches:** delete every remote branch except `main`, `native`, `uc/main` and the heads of open PRs. On 2026-11-23 that was 32 branches. 26 were upstream's (`batch/*`, `wp/*`, `fix/*`, `docs/*`, and five `claude/*`). The other 6 were ours and already merged: three in upstream's `native` (CompaLarios18/MH4UltimateDC#64, #65 and #66), two in `main`, one in `uc/main`. Re-check with `git branch -r --merged` before deleting.
- **Fork mirrors:** fast-forward `native` to upstream's (it was behind on 2026-11-23); check `main` too.
- **Fork default branch:** set to `uc/main` if the maintainer agrees, so the fork's page shows `.github/README.md` (Cheeenxiii/MH4UltimateDC-fork#4).
- **Merged session branches:** delete them in both repositories once their PRs are merged.

## Waiting on the maintainer

- Reviewing this session's branch (`claude/practical-johnson-jobxzw`): docs only.
- Whether to contact MHGU Definitive Edition's maintainers about shared format specs.
- A check of the port's pad features with the plugin in the app or Azahar's Qt build (plugin-api.md step 5), on a machine with a display.
- Whether to offer the inline-cache fix (fork `recomp.h`) to upstream MH4UltimateDC.
- The open decisions in [docs/design/open-decisions.md](docs/design/open-decisions.md): four were added this session (versions of shared systems, map versions and lighting, music and sound versions, GU Switch assets), and progression gained option E. None settled.
