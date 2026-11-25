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

### 0003. Id allocation and mod saves

Settled by the maintainer on 2026-11-25.

- **Ids: one registry file.** Every id a ported content takes is recorded in one file in this repository, checked by a tool, and the run time gets its ids from it (a generated header or table). Monsters first; the format leaves room for the other game-wide ids. New monster ids start at 124, after MH4U's 0 to 123, and a shipped id never moves.
- **Tables grow by hooks on their readers** (the overlay below): a hook answers the new ids and falls through to the game's function for the old ones. A table is relocated only where a case needs it. Besides the costs below, the game is statically recompiled, so a table's address may be folded into the native code, and relocating would then take a patch at recompile time (unverified).
- **MH4U's save may hold the mod's data.** The base save need not stay vanilla, on one condition: a converter, still to be written, removes everything that isn't MH4U's (other games' weapons, armour, monsters and records) and gives back a clean MH4U save. A player runs it before removing the mod, because an unmodded game that meets a ported id may crash.

Still open: where in MH4U's save the mod's data goes and in what format (MH4U's save layout is unmapped, see the open questions below); when the registry takes ids other than monsters; the rule for a shipped id that has to move, and who applies the migration.

| Alternative | Why not |
|---|---|
| An id range per mod | ownership still has to be recorded, so a registry comes back; two relocations of one table cannot both win |
| An id from a hash of the name | collisions, and sparse ids in tables indexed by id |
| The first free id at boot | ids change with the mods installed and their order, which breaks saves |
| Stand-ins only | the base game records the stand-in, and the ported monster still needs its tables |
| Relocating every table | one patch per reference, possibly impossible at run time on a recompiled game |
| A save file of the mod's own, MH4U's save kept vanilla (Definitive Edition) | hooks on the save's write, read and parse and a format to maintain; the converter gives the same way back to a clean save |

**Amended by the maintainer on 2026-11-25: fitting in one byte.** The engine keeps a monster's id in one byte (`+0x1c0` of its data block, read with `ldrb` by the table readers, [reference](../reference/README.md#mh4u-monster-tables)), and a guild quest card's id is one byte too, so 255 is a hard limit; widening it would mean finding and hooking every read of that byte. With every 3U and GU version side by side ([0004](#0004-monster-versions)), the catalog's 51 3U and 93 GU large monsters alone are more than the 132 ids from 124 to 255. So:

- **Ids 124 to 223 are permanent**, given to monsters in the order they are ported, as now.
- **Ids 224 to 255 are a pool lent per quest.** A monster ported after the permanent range is full takes a registry id from 256 up, which quests (whose monster id is a u32, [specs/quest.md](../specs/quest.md)) and the mod's data in the save record; when a quest loads, the plugin lends it a free byte from the pool, and the hooked readers answer that byte with the monster's rows. A quest names a few large monsters, so 32 bytes are enough ([#101](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/101)). A pooled monster can't be on a guild quest card, and its hunt records go through the mod's data in the save, not MH4U's byte-indexed structures.
- Fewer ids are needed in the first place: [0004](#0004-monster-versions)'s amendment ports a version only when it differs, and shared small monsters use MH4U's.

The facts and options it was chosen from, as the open entry held them:

A ported monster or item is a row MH4U never shipped with: an id, a row in every table indexed by that id, and a place in the save for what the base game's structures don't hold. The two halves are one question, because the id is what a save and a quest both record. The entry complemented [Monster versions](#0004-monster-versions), which chooses which version of a monster runs; this one chooses what number it takes and where the mod's own data lives. [Progression](#0007-progression) names a side file as likely for per-game progress, which is this entry's save half.

**What is known**

- **Ids only ever grow.** An installed content's ids never move, because saves and quests keep them ([reference/README.md](../reference/README.md#lessons-from-mhgu-definitive-editions-ports), [How tables grow](../reference/README.md#how-tables-grow)).
- **MH4U's ids are dense.** Monster ids run 0 to 123 and each has a class in the factory; the ids with no files of their own run another monster's class. A new id is 124 or more, and every id up to the highest one used needs a row in each table below.
- **Reusing a base-game id replaces base content**, which the project's lessons forbid ("Add, never replace", [the lessons](../reference/README.md#lessons-from-mhgu-definitive-editions-ports)). Whether the base game actually uses every id in 0 to 123 is unverified.

Every table indexed by the monster id has to grow ([reference/README.md](../reference/README.md#mh4u-monster-tables)):

| Table | Address | Shape |
|---|---|---|
| `createEnemy` (factory) | 0x006901f4 | `cmp id, #0x7c`, then a 124-word jump table at 0x00690278 |
| `enemyDataPathIndex` | 0x00efc268 | 124 pointers by id into `enemyDataPaths` (0x00efbef8, 110 rows) |
| `enemyDataById` | 0x00f3a024 | 124 pointers by id to records from 0x00f39c90 |
| `crownSizeTable` | 0x00f32008 | 124 rows of 4 floats, read by `getCrown` (0x0068877c) |
| `monsterListOrder` | 0x00df35b0 | 124 rows of 8 bytes, by list position |
| `monsterIconIndex` | 0x00e06698 | 124 bytes, 0x7f = no icon |
| `enemyResourceIndex` | 0x00efbd08 | 124 pointers to 0x2c-byte path records |
| `dropRecordIndex`, `dropBaseA`, `dropBaseB` | 0x01003bec, 0x01003ddc, 0x01003ed4 | 124 entries each into `itemListTable` (0x01002a5c) |
| names and notes text | `emName`, `emExp` in `core_common.arc` | message N names id N; 123 messages |

Eight more rows (addresses, shapes, readers) are under [Other tables indexed by id](../reference/README.md#other-tables-indexed-by-id); several of them have no bound check, and a table of 123 rows already reads into the next table for id 123. Growth is therefore never just an append. Item ids grow the item table at 0x00f029e4 (20-byte rows) and the item text the same way ([Not monster tables](../reference/README.md#not-monster-tables)); the monster tables are the worked case here because the milestone ports a monster.

**Two ways to grow a table**, already named in [architecture.md](architecture.md#monsters) and [reference/README.md](../reference/README.md#how-tables-grow):

| Way | Gives | Costs |
|---|---|---|
| Relocate: at boot a plugin allocates a larger table from the game's heap, copies the rows, appends the new ones, and makes the code read the copy | the readers run unchanged; the new rows are ordinary rows; one copy serves every reader | one patch per reference to the table (a literal word, or the single word when the table is reached through one), plus the bounds the code compares; a table read by many literals is many patches |
| Overlay: hooks on the readers answer the new ids and fall through for the old | no copies, no table patches, less memory | a hook per reader, each translated, and several readers are not named yet; a reader left unhooked still stops at its old count; adding a hook needs its name or address in `mod.json`, and changing a hook list rebuilds the game |

Both take guest memory through the plugin host's `alloc`/`free` (ABI 2, the game's own heap), and `read8/16/32`/`write8/16/32` reach the rows ([PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md)).

**The structures the id also has to fit**

| Structure | Holds | Limit |
|---|---|---|
| a quest's monster definition (`.mib`) | a u32 monster id ([specs/quest.md](../specs/quest.md)) | the file allows large ids; whether the game takes one it has no table row for is unverified |
| a guild quest card | a u8 monster id ([specs/extdata.md](../specs/extdata.md), from mhff, unverified) | 255 at most |
| the character save's monster log | 82 fixed entries of 10 bytes (mhff, [reference/README.md](../reference/README.md#mh4u-monster-tables)) | whether it is indexed by id, and what it does with a new one, is unverified |

**Definitive Edition's ids: one registry file.** MHGU Definitive Edition ports MH4U monsters into MHGU the other way round, and keeps every game-wide id a port takes in one file, `allocations.toml` (GPL-3.0-or-later; commit dd5c666 of 2026-11-24, core 3.1.0): registry index, monster number, file ids, save slot, name, icon and Hunter's Notes entries, quest ids, items, decorations, BGM ids, stage folder, and the records a port appends to the game's tables.

- Each value comes from a `[pools]` range whose bounds were checked in the game, and the file records where: registry indexes from 137 because GU uses 0 to 136; monster numbers 89 to 255 because GU's large monsters are 1 to 88; file ids from 0x10700 because GU's file-id table ends at 0x106d0; the seven unused save slots 105 to 111, all taken, so a later monster takes `save = "lease"` and borrows a slot per quest instead.
- `tools/alloc.py` checks the rules (each value inside its pool, no two entries sharing a value, registry and Notes order consecutive, appended records in order); `module/build.py` emits `module/out/alloc.h` for the C side; the converters read the same file. `migrations.toml` is empty because shipped ids never move, and a release check refuses a moved shipped id without a migration step.
- It does not avoid growing tables: `notes/registry.md` is the patch set for GU's registry (copies of the id-to-index pair table and six tables indexed by the index, with a sentinel after the new entry; fourteen literal patches, two bound patches and one data word for the file-id table), plus hooks on the file-id table and on two unbounded save readers.

| Gives | Costs |
|---|---|
| one place to see and check every id; no double-booking; the checked bound of each pool written down; code, converters and build agree; one home for migrations; a pull request shows an id at a glance | each pool's bound has to be found in the game first (Definitive Edition records one check per pool); every port edits one shared file; a wrong range is permanent because ids never move; MH4U's tables are indexed by the id itself, unlike GU's index-to-id pair table, so this would be a ledger of ids, and the run time still needs it turned into a header or a table (Definitive Edition emits `alloc.h`; a plugin cannot read the TOML as it stands) |

**Definitive Edition's saves: first inside the game's save, then a file of its own.** Two steps, both in the tree:

- **A store in the base game's save** (`notes/save-store.md`, 2026-11-04). GU's character save has a 0xd74-byte reserved block that the game copies as it is, and a scan of every function that loads the save found no reader of it (Definitive Edition marks that scan strong, not confirmed). The mod put its own store in it ("MH4S", version 2, 232 records of hunts, captures and smallest/largest sizes), and because all seven save slots were taken, a ported monster leased one slot per quest and its numbers went to the store.
- **A file of the mod's own** (`notes/mod-save-format.md`, core 3.0.0). `mhgu_de_<slot>.bin` (slots 1 to 3) beside GU's `system` and `system_backup`, 32 KiB created once and never grown: header "MHDE" with format version, bytes used, a checksum and a link id, then records. On save the mod splits the character: everything it added moves into the file and GU's slot gets placeholders (an emptied box stack, the vanilla item instead of an added one, a cleared bit), with a 16-byte link record left in the reserved block. On load the file is merged back before GU parses the slot, and the slot's bytes are restored afterwards. A file that is damaged or of a newer format is never overwritten. A Python reference, the C module and the Rust installer implement the same format and are compared on the same saves.

| Step | Gives | Costs |
|---|---|---|
| Store inside GU's save | no second file; the game saves and loads it itself; it survives removing the mod, because GU copies the block as it is | the game's save is no longer vanilla; a region that is copied but never read has to exist and be proved so; a fixed byte budget; a save editor that zeroes the block loses the data |
| The mod's own file | GU's files keep vanilla data only, so removing the mod, an older core or a save editor can never meet an added id; the mod's data is one bounded file that can be backed up, checked and migrated; Definitive Edition calls it "the definitive fix" | hooks on the save image, its write, its read and parse, and the save thread; a merge rule per record kind; a byte budget that can cut records; the link record still sits in the base game's save; the format is maintained in three implementations; every platform's save path to test; 32 KiB is the ceiling |

**Other options for the ids**

| Option | Gives | Costs |
|---|---|---|
| An id range per mod, declared in its own manifest | no shared file; a mod ships on its own | two mods choose the same ids unless something records who owns what, so the registry returns; a block per mod wastes ids when it adds one monster; the tables still have to grow, and two relocations of one table cannot both win |
| An id from a hash of the content's name | no ledger to maintain; stable while the name and the scheme don't change | collisions; MH4U indexes arrays by id, so a sparse hash means a huge table or a lookup on every read, which is a ledger with extra steps; a renamed content moves its id, which the save rule forbids |
| The first free id, allocated at boot | no file to write or keep | ids depend on load order and on the mods installed, so removing, adding or reordering a mod renumbers content and breaks saves; a guest with a different set gets different ids |
| A stand-in the plugin swaps at spawn | a quest file names a monster the base game has, so no new id enters that quest or a guild card; Definitive Edition does this in the quests it ships, alongside its registry | the base game records the stand-in (hunt tallies, Notes, rewards, quest clear) unless every reader is hooked, and unmodded players see the stand-in; it does not avoid the tables or the save for the ported monster itself |

**Other options for the saves**

| Option | Gives | Costs |
|---|---|---|
| A store in an unused region of MH4U's save (Definitive Edition's first step) | no second file; the game saves it | MH4U's save layout is not mapped in this repository, so the region is unknown (open question); a fixed budget; a save editor that clears it loses the data; the base save is no longer vanilla |
| Grow MH4U's save: new sections, or a larger file | all data in the game's own save, with no split and merge | needs the layout, the size rule and the checksum; whether the game takes a bigger file or an unknown section is unverified; an old save manager may drop it; the hardest to undo |
| An Extra Data record | the game already reads whole records from Extra Data, the port's extdata folder is known (the fork's `tools/extdata_path.py`), and `mhuc` writes the game's form byte for byte (check E5) | capacity is per kind (40 × 5 quests, 9 Palicos, 50 × 3 guild quest files); whether the game takes a file or a spare slot it did not download is unverified; Extra Data lives on the SD card, so a save manager, a wipe or another card loses it; it is not per character |
| No mod save: keep everything in MH4U's own fields | nothing new to write, nothing to keep compatible | the fixed structures (the 82-entry monster log, one-byte guild quest ids, the quest lists) cannot record a new id past their size, so the mod's monsters lose part of their record; exactly which parts is unverified |
| The content routes from [quests.md](quests.md#routes-into-the-game) | deliver quests in the game's own form | they store no progress: the game writes a download into Extra Data, and the fork's mod manager installs a mod folder, not a save |

**Constraints whatever the option**

- **Base-game compatibility.** Base quests, saves and hunts must keep working. An option that writes a new id where the base game reads it must either keep the base game from reading it (a file of its own, Extra Data) or make it read cleanly (grown tables, stand-ins); an id that overwrites a base id breaks base content.
- **Online.** Each player's save is their own, but a quest must be identical for every player in a room, so every player needs the mod and the same content ids. What a guest without the mod shows for a quest that names a new id is unverified.
- **Update survival.** The project targets one version of MH4U, USA v1.3.0 ([sources.md](sources.md)), so the addresses and bounds the tools record are fixed for it; what changes is the port and the mod's own versions. Hooks by name work on every version the port runs; a function without a name needs its USA v1.3.0 address, which the build moves for Europe's v1.1.0 ([PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md)). "Ids never move" is what lets a save survive a mod update; Definitive Edition keeps migrations for the exception, applied by its installer.
- **Crash risk.** A reader that indexes past its table is the crash. Definitive Edition's experience: GU's quest-end tally wrote 8 bytes past a 137-entry array for a new index (`notes/registry.md`), and the item box's sort wrote past its array and crashed the game (`notes/items-append.md`). MH4U's unbounded readers are the same risk; they are listed in [reference/README.md](../reference/README.md#other-tables-indexed-by-id).
- **Maintenance.** One ledger and one save format have one place to be right; per-mod ranges and per-mod files scatter that. Definitive Edition maintains its save format in three implementations and compares them on the same saves.
- **The content routes.** [quests.md](quests.md#routes-into-the-game) delivers quests three ways (the game's archives, an Extra Data slot, a local DLC server). None stores player progress, so none answers the save half, and each still puts a quest into the game's form, which names its monsters by id.

**The questions as they stood** (0003 answers 1, 2 and 4; 3 in part, since the mod's data goes in MH4U's save; 5 stays open)

1. Which id rule: one registry file as Definitive Edition has, a range per mod, a hash, or stand-ins only. If a registry: which file (the allocation record #47 then holds the ids), whether it covers monsters only or every game-wide id (maps, quests, items, gear, Palicos, icons, BGM), and how the run time gets the ids (a header generated from it, as Definitive Edition does, or a table the content ships).
2. How tables grow: relocate, hook, or a mix per table, and whether a plugin may write the code and data that hold the references. This fixes the shape of [#47](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/47).
3. Whether the mod has a save of its own; if so, which option, where the file lives, its format, version and budget, and who migrates it (the fork's mod manager or an installer step).
4. Whether the base game's save must stay vanilla, as Definitive Edition decided.
5. The rule for a shipped id that has to move, and who applies the migration.

**Open questions**, where a fact is missing to cost an option honestly:

- MH4U's save layout: whether the 82-entry monster log is indexed by id (then an id above 81 could not be recorded), whether the save has a region the game copies and never reads, and its fixed size and checksum. The repository has a spec for Extra Data ([specs/extdata.md](../specs/extdata.md)) but none for the save.
- Whether any loader validates a quest's or a guild card's monster ids, and what the game does with an id past 123 in a `.mib` and past 255 in a card.
- What a guest without the mod sees for a new id in a quest or a room.
- Whether the plugin host may write the code segment (the references and the bound instructions) or only hook: `PLUGINS.md` gives named hooks and read/write of guest memory, and says nothing about patching code.
- Whether a plugin can write an Extra Data record at run time, and whether the game reads a record it did not download.
- Whether any id in 0 to 123 is unused by the base game, which the "reuse a base-game id" option needs to be costed.
- How a second mod's table growth composes with the first's: two plugins hooking the same reader chain ([PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md) allows 256 chained functions), but two relocations of one table cannot both win.

**Sources for Definitive Edition's side:** its `allocations.toml`, `migrations.toml`, `tools/alloc.py`, `notes/registry.md`, `notes/save-store.md`, `notes/mod-save-format.md` and `notes/items-append.md`, read at commit dd5c666 (2026-11-24, core 3.1.0). The project is credited in [sources.md](sources.md); no code is copied.

### 0004. Monster versions

Settled by the maintainer on 2026-11-25.

**Every version comes in, side by side.** MH4U's own version of a monster stays as it is; the 3U and GU versions of a monster MH4U has are ported as monsters of their own, each with its own id ([0003](#0003-id-allocation-and-mod-saves)). The Rathian milestone therefore adds two Rathians beside MH4U's.

| Alternative | Why not |
|---|---|
| MH4U's version wherever MH4U has the monster | the 3U and GU versions are lost |
| The newest game's version | ports replace MH4U monsters, which "Add, never replace" forbids |
| A pick per monster | a choice to justify per monster, and the others are still lost |

**Amended by the maintainer on 2026-11-25: only versions that differ.** Ids are scarce ([0003](#0003-id-allocation-and-mod-saves)'s amendment), and MHXX carried many MH4U monsters over almost unchanged. So:

- A 3U or GU version of a monster MH4U has gets an id of its own only when it differs from MH4U's: its moves (action handlers and the motions they start), its model, or its monster data beyond values MH4U's version already has. The comparison is made per monster with the repository's tools (`mhuc monsterdata`, `reference/monster_motions.py`) and recorded in the catalog ([#102](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/102)); a version that doesn't differ is not ported, and MH4U's plays its quests.
- A small monster MH4U has is never ported again: 3U and GU quests use MH4U's. Only small monsters MH4U lacks take ids.
- The two Rathians keep 124 and 125: the milestone ports both on purpose, and they are the first monsters the comparison is run on.

The facts and options it was chosen from, as the open entry held them:

Some monsters appear in more than one game ([data/catalog/monsters.md](../data/catalog/monsters.md) lists each once per game). The versions differ in data, moves, AI and model. How a 3U or GU monster runs is settled (0002); which version of a shared monster the mod uses is not.

| Option | Gives | Costs |
|---|---|---|
| MH4U's version wherever MH4U has the monster | no porting for those | 3U and GU versions are lost |
| The newest game's version | the latest design | ports replace MH4U monsters |
| A pick per monster | the best of each | a choice to justify per monster |

### 0005. Combat base

Settled by the maintainer on 2026-11-25.

**MH4U's combat only.** GU's Hunter Styles, Hunter Arts, GU's Kinsect, the Sword and Shield oils and Palico customisation don't come in; GU's and 3U's weapons are played with MH4U's movesets. The question can be reopened later as optional switches, which this choice doesn't rule out.

| Alternative | Why not |
|---|---|
| Some GU systems as switches | each system ported as code and tested against the others, before any content |
| GU's combat on GU content only | two combat systems side by side |

The facts and options it was chosen from, as the open entry held them:

GU's combat systems are code, not data, so they are the costliest content in the mod: Hunter Styles, Hunter Arts, GU's Kinsect (nectar stats, evolution forms, elements), the Sword and Shield oils, Palico customisation.

| Option | Gives | Costs |
|---|---|---|
| MH4U's combat only | one consistent combat system, the least work | GU players lose Styles and Arts |
| Some GU systems as switches, per player or per quest | choice | each system ported as code and tested against the others |
| GU's combat on GU content only | GU content plays as in GU | two combat systems side by side |

Underwater, Styles and Arts would also need movesets no game ever had (see [underwater.md](underwater.md)).

### 0006. Runtime

Settled by the maintainer on 2026-11-25.

**Azahar's core now, native later.** Content work targets the port on Azahar's core, which runs today with multiplayer; the fork's `native` branch carries on beside it without blocking content. The plugin ABI stays the only contract between mod and engine, so the mod moves with the engine.

| Alternative | Why not |
|---|---|
| Carry the native branch forward first | a large amount of engine work before any content |
| Wait for upstream | no date |

The facts and options it was chosen from, as the open entry held them:

The engine runs the game's code natively, but system services, graphics, audio and multiplayer come from Azahar's 3DS core. The fork's `native` branch mirrors upstream's work towards a build without Azahar. Network rooms, the base of the port's multiplayer, work on the Azahar core today. Upstream's maintainer had not answered an issue between 2026-11-01 and 2026-11-23.

| Option | Gives | Costs |
|---|---|---|
| Stay on the Azahar core | works today, multiplayer included | depends on an emulator core |
| Carry the native branch forward in the fork | a real PC port | a large amount of engine work |
| Wait for upstream | no work on our side | no date |

Whatever the runtime, the plugin ABI stays the only contract between mod and engine, so the mod moves with the engine without a rewrite. [MHGURecomp](https://github.com/morerokk/MHGURecomp) is a reference for a native system layer.

### 0007. Progression

Settled by the maintainer on 2026-11-25.

**Merged key quests (option E below).** One story through MH4U's hubs. Each rank's key quests are drawn from all three games, and the urgent quest is picked among theirs. Every quest stays its own game's; which ones are chosen, and the re-ranking of 3U's quests, are authored balance work recorded in the authored register. There is one Hunter Rank, so the Wyporium and the Wyceum unlock as in MH4U.

Still open, as work rather than a decision: which quests each rank takes, and how the quest lists and clear flags make room for them (the inputs listed below).

| Alternative | Why not |
|---|---|
| A. A hub per game | each hub's stage, NPCs, shops and board converted; per-game progress in the save |
| B. One shared hub, quests in MH4U's ranks | the lowest work, but no authored route through the content |
| C. A quest line per game on MH4U's boards | three stories end to end make the whole very long |
| D. Hubs later | two systems to keep working |

The facts and options it was chosen from, as the open entry held them:

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
- **Saves.** B and C fit MH4U's save if quest-clear flags can be extended. A needs per-game progress, likely a side file kept by a plugin (MHGU Definitive Edition keeps such a mod save; the save half is [Id allocation and mod saves](#0003-id-allocation-and-mod-saves)).
- **Online.** Quests must be identical for every player in a room: the same mod version on both sides.

Inputs before deciding: how MH4U stores quest lists and clear flags, whether quest categories are a fixed set, how hub stages load NPCs and shops.

### 0008. Shared systems

Settled by the maintainer on 2026-11-25.

**A pick per system, and each pick is MH4U's:**

- **Skills:** MH4U's. 3U and GU armour carries MH4U skill points; a skill MH4U lacks gets an authored conversion, recorded in the authored register.
- **Meals:** MH4U's canteen.
- **Kinsect:** MH4U's (follows [0005](#0005-combat-base)).
- **Palicos:** MH4U's two Palicos and their skills; 3U's and GU's Palico systems don't come in.
- **Points:** one pot, MH4U's. Every quest pays MH4U's points, and the 3U and GU trades worth keeping move into MH4U's shops.
- **Rank unlocks:** as in MH4U, reached through the one story ([0007](#0007-progression)).

| Alternative | Why not |
|---|---|
| Each content's own game's systems | several parallel systems to make coexist in code and in the save |

The facts and options it was chosen from, as the open entry held them:

All three games have these systems but run them differently. Each needs its own choice: 4U's everywhere, each content's own game's, or a pick per system.

- **Skills:** different point totals, numbers of levels and effects for the same name. Critical Eye's top level gives a different affinity bonus in 4U and GU.
- **Meals:** 3U and 4U combine ingredients and a cooking method; GU unlocks set meals and adds a sauce.
- **Kinsect:** 4U's nectar system or GU's (also under "Combat base").
- **Palicos:** 4U's pair combination skills, or GU's class and skill customisation.
- **Points:** 3U's resource points (Moga Woods, the Argosy), 4U's expedition points, GU's Wycademy points. They can be kept apart, merged, or merged in part.
- **Rank unlocks:** the Wyporium and the Wyceum must stay reachable whatever progression is chosen, and the Wyporium trades parts of monsters that neither 3U nor GU has.

Facts for each choice go in `data/catalog/`, with a source URL per row, before options are costed.

### 0009. Map versions and lighting

Settled by the maintainer on 2026-11-25.

**Both versions, as separate maps.** A locale in 3U and GU (Deserted Island, Misty Peaks) comes in twice: 3U's version keeps its water, GU's its layout. Each map keeps its own game's lighting.

| Alternative | Why not |
|---|---|
| 3U's version only | GU's layout is lost |
| GU's version only | the underwater areas are lost |

The facts and options it was chosen from, as the open entry held them:

Some locales exist in several games, in different versions: Deserted Island in MH3U (12 areas) and MHGU (10 areas), Misty Peaks in both ([data/catalog/maps.csv](../data/catalog/maps.csv)). Our GU-era source for maps is MHXX.

| Option | Gives | Costs |
|---|---|---|
| 3U's version | the underwater areas and the routes through them | GU's layout is lost |
| GU's version | GU's layout (camp, ledges, connections) | no water |
| Both, as separate maps | both | two maps to port and fit into progression |

Lighting: each game lights a locale differently, and lighting affects the whole scene. Either each map keeps its own game's lighting, or MH4U's lighting style is applied to imported maps (authored work, recorded in the register).

### 0010. Music and sound versions

Settled by the maintainer on 2026-11-25.

**The version of the game the content comes from.** 3U Rathian has 3U's theme and sounds, GU Rathian GU's; MH4U's content keeps MH4U's.

Still open: whether a monster with no theme in its own game gets one from another.

| Alternative | Why not |
|---|---|
| Its first game's version | may clash with the content's own game |
| MH4U's, where MH4U has it | 3U and GU arrangements are lost |

The facts and options it was chosen from, as the open entry held them:

Many themes and monster sounds exist in several games, sometimes rearranged (GU revisits older games' themes). Some monsters have a theme in one game and none in another, and the conventions differ: some games give most large monsters a theme, others play the area's music.

| Option, per theme or sound | Gives | Costs |
|---|---|---|
| Its first game's version | the original | may clash with the content's own game |
| The version of the game the content comes from | consistent with the content | |
| MH4U's, where MH4U has it | consistent with the base game | 3U and GU arrangements are lost |

A second question: whether a monster with no theme in its own game gets one from another. Formats and the work are in [audio.md](audio.md).

The mechanism takes no side: in MH4U a theme is a sequence id in a stream request (`bgm_bat.stq`, or a stage's `bgm_st_NN.stq` for a stage theme), and a hardcoded per-monster switch in `sSoundControl` picks it ([audio.md](audio.md#how-mh4u-picks-a-monsters-theme)). Every option above is therefore a choice of sequence and audio, and none of them changes how the game asks for it; a ported monster reusing another's theme only needs the switch to answer with that theme's id.

### 0011. GU Switch assets

Settled by the maintainer on 2026-11-25.

**The base mod stays 3DS; an optional HD pack may come later.** The source rule (CLAUDE.md rule 2, [sources.md](sources.md)) is unchanged for the mod itself. A separate, optional pack built from the player's own Switch dump (textures, interface, audio) may come later as a second pipeline; nothing from it is needed to play the mod.

| Alternative | Why not |
|---|---|
| No HD ever | closes a door for no gain |
| Change the rule | the mod would depend on a Switch dump |

The facts and options it was chosen from, as the open entry held them:

MHGU on Switch has HD textures and a single-screen interface. The source rule takes only English text from it; GU-era models and textures come from MHXX 3DS.

| Option | Gives | Costs |
|---|---|---|
| Keep the rule | one consistent 3DS look | no HD |
| An optional pack built from the player's own Switch dump: textures, interface, 48 kHz Opus audio | HD for those who want it, base mod unchanged | a second asset pipeline |
| Change the rule | HD everywhere | the mod depends on a Switch dump |

Changing the rule means changing CLAUDE.md's rule 2 and [sources.md](sources.md).

### 0012. How much of MH4U the mod may replace

Settled by the maintainer on 2026-11-25.

**As much as it needs.** A plugin hook can run instead of a game function (`skip_original`, [PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md)), so the mod may replace a single function, a whole system (AI, saves, id handling) or, over time, as much of MH4U as it wants, with its own C code written from the decompiled original. The working rule: when working around one of the game's limits would take more hooks than rewriting the functions behind it, rewrite them, and check the result in game.

The engine side does not move with it: the fork keeps its diff with upstream MH4UltimateDC minimal (additions and the hooks they need, [CLAUDE.md](../CLAUDE.md#the-fork)), in the hope that upstream's maintainer returns, and the plugin ABI stays the contract between mod and engine ([0006](#0006-runtime)). Replacing MH4U's code happens in the mod, never in the fork. Whatever the mod replaces, it ships only its own code: it still needs the player's dumps, and no Capcom code or asset is distributed (CLAUDE.md rule 1).

| Alternative | Why not |
|---|---|
| Hooks only around the game's code, never instead of it | every limit of MH4U's structures (one-byte ids, fixed tables, hard-coded motion indices) has to be worked around, monster by monster |
| Replace MH4U's code in the fork | the fork would drift from upstream, which it must stay rebasable on |

## Open

None. A new structural question goes here, with its facts and options, until the maintainer settles it.
