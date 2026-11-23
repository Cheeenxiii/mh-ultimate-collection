# ID tables

**Point:** adding monsters, maps and quests to MH4U means growing the game's fixed-size tables, which are indexed by numeric ids. This doc lists the tables that will have to grow and how to find each one once the game files are at hand. The monster id table and the monster factory are found (USA v1.3.0, below, verified 2026-11-23 against the maintainer's dump), and so are the per-monster tables for names, sizes and crowns, icons, resource paths and item drops ("Other per-monster tables", below); the other rows are still unverified.

## Tables that have to grow

| Table | Indexed by | Why it grows | Likely form |
|---|---|---|---|
| Monster (enemy) id table | monster id | every new 3U or GU monster needs an id | an array of per-monster records in `.data` (model/ARC paths, class, sizes), or a resource (`rEnemyData`, `.emd`) per monster plus a master list |
| Monster class factory | monster id → class | MH4U has 55 classes `uEm001`…`uEm118` (config/mt_classes.tsv); new monsters need a class to run as | a switch or table mapping ids to `MtDTI*`; the uniform size 0x8d90 suggests one class can host different monsters' data |
| Monster names and texts | monster id → text id | names in the hunter's notes, quest texts | found: `emName`/`emExp` `rLayoutMessage` resources, message N = id N (below) |
| Monster size and crown tables | monster id | size scaling, crowns | found: `crownSizeTable`, an array in `.data` (below) |
| Monster parts, breaks, rewards | monster id, part id | carves, breaks, quest rewards | drops found: id-indexed index tables into an item-list array in `.data` (below); parts, hitzones and breaks in the per-monster `.emd`/`.etd` ([specs/emd.md](../../specs/emd.md), from MHGU Definitive Edition, unverified until its check E1); quest rewards in quest data |
| Item and material ids | item id | new monsters bring new materials | item data resource (`rItemData`-like) plus GMD names and icons |
| Equipment tables | weapon/armor id per class | new monsters' weapons and armour | per-class weapon data (`w00d`… in mhff's table), armour series data |
| Stage (map) table | stage id | new 3U maps | `rStageInfoSet`, `rStageAreaInfo`, `rStageCameraData` per stage plus a master list of stage ids → folders |
| Area tables | stage id, area id | per-area files, transitions | resources per stage |
| Quest ids | quest id | 3U and GU quests | `rQuestData` (`.mib`) per quest, and quest lists (rQuestInfoTbl) |
| BGM, effects, sounds per monster | monster id | themes, roars | sound request tables (srq, stq); see audio.md |
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

## Other per-monster tables (USA v1.3.0)

Found 2026-11-23 by static reading of the v1.3.0 code and RomFS (procedure below). Addresses, sizes and counts only. In the Status column, **verified** means read from the code: the address, the row size, the bound and what indexes the table. A row's *meaning* (what its fields are for) is **unverified** unless the column says otherwise, because nothing here has been checked in a running game yet.

**Where the monster id lives.** The uEnemy constructor (`0x00955fbc`) stores the id as a byte at offset `0x1c0` of the data block that `this+0xe28` points to. Code reads the current monster's id with `ldr rX, [this, #0xe28]; ldrb rY, [rX, #0x1c0]`.

### Names (text)

| What | Where | Shape | Bound | Status |
|---|---|---|---|---|
| `msg\emName_<lang>` | `eng/msg/emName_eng.lmd` (`rLayoutMessage`) in `data/core_common.arc`, in both the base RomFS and the update's | one message per monster id: message N names id N | **123 messages**, so ids 0..122; id 123 has no name entry | address and indexing verified; the count is read from the LMD header word at `+0x08`, which matches `itemName_eng.lmd`'s item count, but the LMD format has no spec yet, so the count is unverified |
| `msg\emExp_<lang>` | `eng/msg/emExp_eng.lmd`, same archive | hunter's-notes text by id | 123 messages | as above |
| Message file list | `0x00f006c4` | 71 pointers to `msg\…_jpn` paths (the language suffix is replaced at load); emName is entry 6, emExp entry 7 | `cmp #0x47` in the loader `0x005aa2f0` | verified |
| Loaded messages | `0x0109a080` (`.bss`) | 71 `rLayoutMessage*`; emName at `0x0109a098`, emExp at `0x0109a09c` | 71 | verified |
| Name getters | `0x005a9000` `(id, outLen)` returns the string; `0x005a9184` `(buf, id)` formats it | read `0x0109a098` and index by id | none: the id isn't range-checked | verified; that the argument is the monster id is shown by `0x006b8290`, which passes ids it compares with `0x23`, `0x52` and `0x67` |

New names go into `emName`/`emExp` (and every language's copy); these two resources hold one message fewer than there are ids.

### Size and crowns

| What | Address | Shape | Bound | Status |
|---|---|---|---|---|
| `crownSizeTable` | `0x00f32008` .. `0x00f327c8` | 124 rows × 16 bytes (4 floats), by id | `cmp id, #0x7c` in `getCrown` | verified; 86 rows have a non-zero first float |
| `getCrown` | `0x0068877c` | `(id, sizePercent, out)`: scales the row's float 0 by the percentage, compares the result with floats 1, 2 and 3, and writes a crown code to `out` (`0xff` none, `0`, `1`, `2`, `3`) | `0x7c` | verified. Field meaning: float 0 is the base size; floats 1, 3 and 2 are the mini, gold and silver thresholds: **unverified** (read from which comparison writes which code) |

Callers of `getCrown`: `0x00622d24`, `0x00a318c8`, `0x00a54430`, `0x00ab01bc`, `0x00acc36c`, `0x00acc5b4`, `0x00c20a70`.

### Hunter's-notes list and icons

| What | Address | Shape | Bound | Status |
|---|---|---|---|---|
| `monsterListOrder` | `0x00df35b0` | 124 rows × 8 bytes, **by list position, not by id**: byte 0 is the monster id (the 124 rows hold each id 0..123 once); byte 1 a category; u16 at `+4` a save-flag number (non-zero in 91 rows) that `0x00c1bea8` tests | loops `while < 0x7c` in `0x006191f8`, `0x0061dc58`, `0x0061df4c` | verified for the shape, the id and the bound; the category and flag meanings are unverified |
| `monsterIconIndex` | `0x00e06698` (`.rodata`) | 124 bytes by id; `0x7f` = no icon (7 ids) | `cmp id, #0x7c` in `0x00c0e164` and `0x00c0e800`, which copy the 124 bytes to the stack | verified |
| Icon cell to UV | `0x00c0e8ac` | icon index → cell in a 7-column sheet; indexes `0x00..0x61` use one sheet and `0x63..0x7b` another | `cmp #0x62`, then `sub #0x63; cmp #0x19` | verified |

The icon sheets themselves have room for `0x7b` indexes at most; a new monster needs a new cell or a reused one.

### Resource paths

| What | Address | Shape | Bound | Status |
|---|---|---|---|---|
| `enemyResourceIndex` | `0x00efbd08` | 124 pointers by id (id 0 null), each to a record in `enemyResourceRecords` | followed by `enemyDataPaths` at `0x00efbef8` | verified |
| `enemyResourceRecords` | `0x00efa7e0` .. `0x00efbd04` | 123 records × `0x2c` bytes: 11 pointers to null-terminated lists of path strings (model, motions, camera list, extra models, motion effects, command file, sound sequence, effect lists) | 123 | verified (pointer targets are `enemy\emNNN\…`, `effect\…` and `sound\…` paths) |

Readers: `0x00682ca0`, `0x0068d8c8` (returns the record's word at `+0x14`), `0x00c0b830`.

### Item drops (rewards)

Reward items are lists in `.data`, reached through one master pointer array and three id-indexed index tables. The rank offset comes from `0x006bc528`, which returns 0..3 from the current quest. Each index table gives a base index into the master array, and the code adds `4 × slot + rank` to it.

| What | Address | Shape | Bound | Status |
|---|---|---|---|---|
| `itemListTable` | `0x01002a5c` .. `0x01003bec` | 1124 pointers (281 groups of 4, one per rank), 853 non-null, each to an item list: 4-byte entries (u8, u8, u16 item id) ended by `0xffff` | none in code; set by the largest index the tables below produce (`0x460 + 3`) | address and bound verified; the entry fields are unverified (the u16 ranges over item ids, below `itemName`'s 1937) |
| `dropRecordIndex` | `0x01003bec` | 124 pointers by id (114 non-null) to records at `0x01003fcc`.. of 16-byte entries; an entry's u16 at `+0` is a base index into `itemListTable` and its byte at `+0xb` another index (`0xff` none) | 124 | verified for the shape and the indexing; what the entries describe (the floats suggest parts or drop points) is unverified |
| `dropBaseA` | `0x01003ddc` | 124 u16 by id, `0xffff` = none (81 used) | 124 | verified |
| `dropBaseB` | `0x01003ed4` | 124 u16 by id, `0xffff` = none (12 used) | 124, followed by the records at `0x01003fcc` | verified |

Readers: `0x00684b40` `(_, id)` and `0x0092600c` use `dropRecordIndex`; `0x00911f20` uses `dropBaseA` (after a percentage roll and a per-monster counter at data-block offset `0x7a64`, so probably shiny drops: unverified); `0x009357b4` uses `dropBaseB`. All four create an item-pop object through the manager at `*0x00fb8a1c` (`0x005b90d4`) and store the item list in it at `+0x28`. **Which of these are carves, captures, breaks and shiny drops is unverified**; carving was not traced.

### Parts

No part table indexed by id was found in `.data`. The per-monster resources are the likely place: `data/em_data.arc` holds 110 `rEnemyData` (`.emd`) and 110 `rEnemyTuneData` (`.etd`) files, one pair per monster with files (the same 110 as `enemyDataPaths`). Both are section-offset files (`.emd` magic `emd\0`, `.etd` magic `etd\0`), laid out in [specs/emd.md](../../specs/emd.md) from MHGU Definitive Edition's readers. **Unverified on our files:** that hitzones, part HP and breaks live there (check E1 in that spec). A new monster brings its own pair, loaded through `enemyDataPathIndex`, so these files don't grow a table.

### Other tables indexed by id, purpose unknown

Each is read with the monster id from the data block (`ldrb [x, #0x1c0]`) as its index. Bounds are the gap to the next referenced address and are verified; meanings are not.

| Address | Shape | Reader |
|---|---|---|
| `0x00deef04` | 124 bytes | `0x00b9b340` |
| `0x00e067f4` | 124 u16 | `0x00696878` |
| `0x00e070a4`, `0x00e07120` | 124 bytes each | `0x006b8290`, `0x006b40dc` |
| `0x00fc96dc` | 124 bytes | `0x006a69e4` |
| `0x00fcd71c` | 123 rows × 8 bytes (two floats) | `0x0030f4cc` (`cmp #0x7c`) |
| `0x00ffeaa4` | 124 pointers to small records at `0x00ffea88`.. | `0x0093f350` |
| `0x00ffecb8` .. `0x00fff55e` | **nine tables of 123 i16** (stride `0xf6`), one picked by quest type; the result goes to data-block offset `0x7af4` | `0x0094813c`, `0x0094829c`, `0x0094c840`, `0x0094c948` |
| `0x00f384d0` | 124 words, `-1` = none | `0x0068efc8` |

The 123-entry tables (the nine i16 tables, `0x00fcd71c`, `emName`, `emExp`) stop one short of id 123: reading them for id 123 reads the next table's first entry.

### Not monster tables

`0x00f029e4` (20-byte rows; byte 6 counts up) is the item table: it is indexed by item id, and its `cmp #0x7c`/`#0x7d` are item ids. The 124-entry tables at `0x01017980`..`0x0101b214` are read by `0x00c4c4fc` with an index from `this+0xfd` that isn't a monster id. `0x00ecf1d8` and its neighbours are gathering lists chosen by stage.

### Bounds to move, all together

When ids grow past 123: the factory compare and jump table, `enemyDataPathIndex`, `enemyDataById` (above); `crownSizeTable`, `monsterListOrder` (and the three loops over it), `monsterIconIndex` (and the two 124-byte stack copies), `enemyResourceIndex` and its records, `dropRecordIndex`, `dropBaseA`, `dropBaseB` and `itemListTable` (for new lists); the unknown-purpose tables above; and every language's `emName`/`emExp`.

**Save-side limits (not tables to move):** a guild quest (specs/extdata.md) stores each monster id in one byte, so ids above 255 can't appear in one; ids up to 255 fit as they are. The character save (`user1`..`user3`) has a monster log of 82 fixed 10-byte entries (mhff "MH4U user1 Format", unverified): a fixed-size block in the save, so new monsters' hunt records need room outside it (a separate mod save, as MHGU Definitive Edition keeps; its notes/mod-save-format.md) or a save layout change.

**How another project allocates ids (an option, not a decision).** MHGU Definitive Edition, which adds MH4U monsters to MHGU, keeps every game-wide id a ported monster takes in one file (`allocations.toml`: registry index, monster number, file ids, save slots), each from a pool whose bounds were checked in the game, checked by a script and read by both its C module and its converters. Its rule: ids only ever grow, and an installed monster's ids never move, because saves and quests keep them. The same constraints apply here: a hunter's save keeps per-monster records (mhff's "MH4U user1 Format" lists a monster log of 82 entries of 10 bytes, whose indexing by id is unverified), and quests name monsters by id.

### Procedure (repeatable from the dump; record results, never bytes)

1. Lay out the code as in step 1 above. List the code's literals that point into `.rodata`/`.data`. For each, take the distance to the next referenced address; keep the ones that are 123, 124 or 125 times a small row size.
2. Find the functions that read the id (`ldrb [x, #0x1c0]` after `ldr [this, #0xe28]`) or compare a register with `#0x7c`. Keep the literal tables they index with that register; the shift or multiply gives the row size.
3. Names: find `msg\emName_jpn` in `.rodata`, the pointer list that holds it (`0x00f006c4`), and its loader (one function with a `cmp #0x47` loop storing `rLayoutMessage` pointers). The functions that read the stored pointer at `+0x18` are the getters. Count the messages from the `.lmd` file's header in `core_common.arc`.
4. Crowns: the function that indexes a 16-byte-row table by an id it compares with `#0x7c` and compares floats.
5. Drops: scan `.data` for runs of pointers whose targets are lists of 4-byte entries ending in `0xffff`. The long run is `itemListTable`; the functions that read it show the index tables and the `0x006bc528` rank offset.
6. For each table, check its count against the id tables (each id in range, the list order a permutation of 0..123).

The scripts live in the maintainer's workspace (`game_files/work/mt/`).

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
