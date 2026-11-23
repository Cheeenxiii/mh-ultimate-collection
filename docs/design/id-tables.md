# ID tables

**Point:** adding monsters, maps and quests to MH4U means growing the game's fixed-size tables, which are indexed by numeric ids. This doc lists the tables that will have to grow and how to find each one once the game files are at hand. The monster id table and the monster factory are found (USA v1.3.0, below, verified 2026-11-23 against the maintainer's dump); the other rows are still unverified.

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

## Found (USA v1.3.0)

Names and addresses are in the fork's `config/symbols.txt` (section "Monster ids"). Status: **verified** by static reading of the v1.3.0 code (procedure below); not yet checked in a running game.

**Monster ids run 0..123 (124 values).** Id 0 is a placeholder; id N is the monster whose files are `emNNN`. 110 of the 123 ids have files of their own; the others reuse a neighbour's.

| What | Address | Shape | Bound |
|---|---|---|---|
| `enemyDataPaths` | `0x00efbef8` | 110 rows of 8 bytes: two pointers to the same `enemy\emNNN\data\emNNN` string | ends at `0x00efc268` |
| `enemyDataPathIndex` | `0x00efc268` | 124 pointers, by id, into `enemyDataPaths`; id 0 is null | followed by the otomo model paths at `0x00efc458` |
| `loadEnemyData` | `0x00689490` | `(this, id, slot)`: indexes `enemyDataPathIndex[id]`, loads the `rEnemyData` resource, appends it to the array at `this+0x13a4`, stores it in `(*0x00f3a020)[id][slot]` | none: the id isn't range-checked here |
| `createEnemy` (the factory) | `0x006901f4` | `(owner, id, a2, a3)`: takes the first free of 32 slots at `owner+0x18`, then `cmp id, #0x7c` and a 124-word jump table at `0x00690278`; each case calls its class's own `operator new` (`0x8d90` bytes, align `0x10`) and its init | `0x7c`; out of range creates nothing |

Callers: `createEnemy` from `0x0068a9b8`, `0x0068da84`, `0x006aa29c`, `0x006bbc78`; `loadEnemyData` from `0x0065bcd0` and `0x0065cbb8`. `0x00f3a020` holds a pointer to `enemyDataById` (`0x00f3a024`): a static array of 124 pointers, by id, each to a 2-word record in `.data` from `0x00f39c90` (several ids share a record); `loadEnemyData` stores the loaded resource into word `slot`, and `0x0068df70` (`releaseEnemyData`, which loops over ids while `< 0x7c`) clears them.

**Id to class.** The rule is id N → `uEmN`. These ids reuse another monster's class (variants, subspecies and ids with no files):

| Class | Extra ids | Class | Extra ids |
|---|---|---|---|
| uEm001 | 2-6 | uEm048 | 49, 114 |
| uEm007 | 8 | uEm052 | 53, 54, 55 |
| uEm009 | 10 | uEm058 | 59, 60 |
| uEm011 | 12, 80, 121 | uEm065 | 66 |
| uEm016 | 13, 14 | uEm068 | 69-71 |
| uEm017 | 18 | uEm073 | 74-76 |
| uEm019 | 45, 112 | uEm077 | 78, 79, 117 |
| uEm020 | 90 | uEm081 | 84-87, 104, 123 |
| uEm022 | 21, 91, 92 | uEm083 | 111 |
| uEm023 | 93, 120 | uEm088 | 122 |
| uEm024 | 110 | uEm099 | 100, 119 |
| uEm025-027 | 94-96 | uEm101 | 102 |
| uEm028 | 29, 97 | uEm105 | 106 |
| uEm031 | 82 | uEm107 | 108, 109 |
| uEm034 | 35 | uEm038 | 39-41, 115 |
| uEm036 | 37 | uEm042 | 43, 113 |
| uEm044 | 98 | | |

Id 0 creates `uEmXXX` (size `0x8d88`). Every other class is `0x8d90` bytes, so one slot size fits all monsters, as `mt_classes.tsv` suggested.

**Bounds to move when ids grow:** the `0x7c` compare and jump table in `createEnemy`; `enemyDataPathIndex`'s 124 entries; `enemyDataById` (124 entries) and its records at `0x00f39c90`. 54 functions compare a register with `0x7c`; `0x0065bcd0`, `0x0065cbb8` and `0x0068df70` are among them and are monster code, while the others are unchecked (`0x7c` is a common constant).

### Procedure (repeatable from the dump; record results, never bytes)

1. Decompress `code.bin` (`tools/blz.py`) and lay out `.text`, `.rodata` and `.data` at the exheader's addresses.
2. In `.rodata`, find the `enemy\emNNN\data\emNNN` strings. In `.data`, find the run of pointers to them (stride 8: the path table), and the pointer array right after it whose entries point into that run (the index).
3. Find the code literal that points at index − 4, and therefore at entry 0: one function, `loadEnemyData`. Its `ldr rX, [base, id, lsl #2]` shows that the index is by id, 0-based, and its use of the `rEnemyData` DTI shows what it loads.
4. Count the `.text` literals equal to `0x8d90` (the `uEnemy` size from `config/mt_classes.tsv`). Apart from the 0x50-byte per-class DTI functions at `0x00d00df8`..., one large function (`0x1058` bytes) holds one: that's `createEnemy`. Its `cmp id, #0x7c; ldrlo pc, [pc, id, lsl #2]` gives the count and the jump table.
5. For each `uEm` class, read the vtable its DTI's create function stores. For each jump-table case, follow the init call to the vtable it stores, which gives the class. A case that only allocates and then branches into another case's tail takes that case's class (its `operator new` is that class's too).
6. Check that the two tables agree: for each id, the path the index gives and the class the factory makes should be the same `emNNN`, or the same neighbour for an id with no files of its own.

The scripts used live in the maintainer's workspace (`game_files/work/idt/`), since they read the dump; this procedure is enough to rewrite them.

## How to find the rest

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

Both need guest memory allocation from plugins: the plugin API's `alloc`/`free` (ABI 2) take it from the game's default heap ([plugin-api.md](plugin-api.md), "Guest memory").
