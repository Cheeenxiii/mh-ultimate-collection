# Status

The one place that says where the project stands. Overwritten at the end of every session (`/handoff`); history is in `docs/reports/`. Keep it under a screen.

**Updated:** 2026-11-23, after a web session that decrypted the maintainer's MH4U Extra Data and checked the `.mib` quest layout on 120 DLC quests.

## Where we are

Phase: **engine work with the game files.** Both reference games recompile cleanly:
- MH3U: 33,283 functions, every one gametested: 0 differ, 0 fail-fault, 0 missing targets.
- MHXX v1.4: 63,087 functions; a 2,000-function sample with 0 differing and 0 missing targets.

The MH4U quest format (`.mib`) is now specified from mhff's wiki and partly verified on the 120 DLC quests in the maintainer's Extra Data. Report: [docs/reports/2026-11-23-dlc-quests-web-session.md](docs/reports/2026-11-23-dlc-quests-web-session.md).

Findings that steer the next steps:
- Downloaded quests sit in Extra Data as bare `.mib` files, 40 slots of 0x2010 bytes per `quest*` file, each ending with its file name (`mNNNNN.mib`), under mhef's `SavedataCipher`. That's a possible way in for mod quests without growing quest tables. Monsters come in waves; objective types are mapped by value, though their meanings aren't confirmed.
- Capcom's MH4U DLC server is gone (NXDOMAIN). Its files live on in the GrenderG/goshawk preservation mirror (AGPL-3.0, files Capcom's): server quests are bare `.mib`, identical to what the game stores, plus 28 bytes the game adds (unknown; they decide whether mod quests can go in through Extra Data). MHXX's DLC (173 quests) decrypts and fits mhff's MHXX `.mib` layout. MH3U's `QTDS` layout (from mh3u-quest-studio) is verified on the 38 USA DLC quests stored in clear in the maintainer's 3DS Extra Data; the server cipher stays unknown and isn't needed.
- No public layout exists for `.emd`/`.etd`; that spec has to come from the files and the code.
- Chase every missing target and every rare `fail-fault` the gametest reports by tracing the reference. The inline-cache runtime fix is a candidate to offer upstream.
- Adding a monster id means moving every bound in id-tables.md's "Bounds to move" list.
- Memory: cap big jobs with a cgroup at **6 GB** (one job at a time, 4 workers). Fork recompiler tests need `PATH=/usr/lib/llvm-22/bin:$PATH`.

## Branches

This repo: `claude/zealous-wozniak-eip1pk` has this session's commits on top of `main`. It's pushed, with no PR open. The fork is unchanged. Nothing else is in flight.

## Next tasks, in order

1. **`.emd`/`.etd` specs** (`rEnemyData`, `rEnemyTuneData`): parts, hitzones, breaks; trace carves. Needs the RomFS. Done when specs/ has both with verified/unverified fields and id-tables.md's parts row points at them.
2. **A first table-growing plugin**: grow one id-indexed table with `alloc` and repoint its readers. Done when a procedure in docs/checks/ passes in game.
3. **Quest check Q6**: run the Q5 checks on the game's 508 `.mib` (specs/quest.md). Needs the RomFS; it's short, so do it alongside task 1.
4. **MH3U quest check Q13**: run the `QTDS` parse on the RomFS's 365 `.quest` files (specs/quest.md). Needs the MH3U RomFS; short, so pair it with Q6.
5. **MHXX full gametest** (every function, 4 shards, about 5 minutes). Done when reference-recompiles.md has its verdict counts and every non-agreeing function is explained.
6. **MH3U targeted studies** (swim state, oxygen, underwater camera in the harness). Done when underwater.md cites what the harness showed.

## Waiting on the maintainer

- Merging `claude/zealous-wozniak-eip1pk` into `main`.
- A check of the port's pad features with the plugin in the app or Azahar's Qt build (plugin-api.md step 5), on a machine with a display.
- Whether to offer the inline-cache fix (fork `recomp.h`) to upstream MH4UltimateDC.
- The open decisions (combat base, monster versions, runtime, progression): unchanged, not ours to settle.
