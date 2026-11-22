# ID tables

**Point:** adding monsters, maps and quests to MH4U means growing the game's fixed-size tables, which are indexed by numeric ids. This doc lists the tables that will have to grow and how to find each one once the game files are at hand. None has been found yet; nothing below is verified.

## Tables that have to grow

| Table | Indexed by | Why it grows | Likely form |
|---|---|---|---|
| Monster (enemy) id table | monster id | every new 3U or GU monster needs an id | an array of per-monster records in `.data` (model/ARC paths, class, sizes), or a resource (`rEnemyData`, `.emd`) per monster plus a master list |
| Monster class factory | monster id → class | MH4U has 55 classes `uEm001`…`uEm118` (config/mt_classes.tsv); new monsters need a class to run as | a switch or table mapping ids to `MtDTI*`; the uniform size 0x8d90 suggests one class can host different monsters' data |
| Monster names and texts | monster id → text id | names in the hunter's notes, quest texts | GMD tables (rGUIMessage) indexed by id |
| Monster size and crown tables | monster id | size scaling, crowns | `rEmSizeCalcTblElement`-like resource, or arrays |
| Monster parts, breaks, rewards | monster id, part id | carves, breaks, quest rewards | resources per monster; reward tables inside quest data |
| Item and material ids | item id | new monsters bring new materials | item data resource (`rItemData`-like) plus GMD names and icons |
| Equipment tables | weapon/armor id per class | new monsters' weapons and armour | per-class weapon data (`w00d`… in mhff's table), armour series data |
| Stage (map) table | stage id | new 3U maps | `rStageInfoSet`, `rStageAreaInfo`, `rStageCameraData` per stage plus a master list of stage ids → folders |
| Area tables | stage id, area id | per-area files, transitions | resources per stage |
| Quest ids | quest id | 3U and GU quests | `rQuestData` (`.mib`) per quest, and quest lists (rQuestInfoTbl) |
| BGM, effects, sounds per monster | monster id | themes, roars | sound request tables (srq, stq) |
| Unit and resource heaps | — | more monsters loaded or larger ARCs | heap sizes set at start-up (the engine's unit and resource managers) |

## How to find them (first session with game files)

1. **Start from a known monster.** Pick one MH4U monster whose files are known by name in the RomFS (its ARC folder, `em/emXXX/`-style). Its id is in the folder name. Search `.data` and `.rodata` for that id next to its path string: the record that holds the path is a row of the monster table; its neighbours are the other rows, and the table's start and end bound the count.
2. **From the class registry.** `config/mt_classes.tsv` gives each `uEm` class's DTI address. In Ghidra, the code that references many `uEm*` DTIs in one function is the factory: its switch or table maps ids to classes, and its bound is the monster count.
3. **From resource loaders.** For each resource class in the placeholders (specs/placeholders/), its loader's callers index by id: their array bounds and the constants compared against are the table sizes.
4. **From GMD tables.** The monster-name GMD's string count is an upper bound for monster ids that have names.
5. **Heaps.** The resource and unit managers are created early in start-up (MH4UltimateDC's docs/research/system-services.md covers the main systems); their sizes are constants passed to their constructors. Record which heap a monster's resources come from.
6. **Record each table** as: name, address (USA v1.3.0), row size, row count, what indexes it, the functions that read it. Addresses and sizes are fine to commit (LEGAL.md); contents are not.

## How they grow

Two ways, to choose per table once found (the choice isn't made here):

- **Relocate:** a plugin allocates a larger table at boot, copies the original rows, appends the new ones, and patches the code's references (hook points on the readers, or tunables for the bounds). Works for tables in `.data`.
- **Overlay:** hooks on the table's readers return the new rows for new ids and fall through to the original for old ids. Less patching, more hooks.

Both need guest memory allocation from plugins, which the plugin API doesn't offer yet (plugin-api.md, "Limits").
