# Architecture

How the mod is built, what exists today, and where each part of the work stands.

## Two repositories

| Repository | Holds |
|---|---|
| this one | content: the `mhuc` toolkit, format specs, the reference recompiles, and the mod's own files |
| [MH4UltimateDC-fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork), branch `uc/main` | the engine: upstream's port, plus native plugins and hooks by name |

The mod reaches the engine only through the fork's plugin API. Its reference is the fork's [docs/PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md). In short:

- a mod folder holds a `mod.json`, RomFS files and a native library;
- `mod.json` names the game functions the library hooks;
- the fork's `tools/build_game.py` builds those hooks into the recompiled game;
- at start-up the port loads the library, which can read and write game memory, allocate from the game's heap, and call a game function by address, with r0-r3 and the floats s0 and s1 as its arguments, and its r0 and float return back (ABI 4, `call` and `call2`; the headless checks [P3](checks.md#calling-the-engine-from-a-plugin-p3) and [P4](checks.md#calling-the-engine-with-r3-and-floats-from-a-plugin-p4)).

A hook can also run instead of the game's function, so the mod may replace any part of MH4U with its own C code, written from the decompiled original, while the fork stays a minimal diff on upstream ([decision 0012](decisions.md#0012-how-much-of-mh4u-the-mod-may-replace)).

The mod's native code is one runtime, a module per ported monster ([decision 0013](decisions.md#0013-one-runtime-for-the-mods-native-code)): one fixed hook list, the id layer and every ported monster's action code compiled into the same library, so a new monster rebuilds the mod's library and not the game's code library. `mods/uc_runtime` is that plugin. Its `mod.json` names the fixed hook list: the id layer's 21 hook points and `uEnemy::dispatchAction`; `src/runtime.c` is the plugin entry point and the one hook table, `src/ids.c` is the id layer, `src/module.c` is the machinery every module shares (the factory association, the action dispatcher, the per-monster state slots and the ABI 4 guest call), and `src/modules.h` is the module table, generated from `data/ids/registry.csv` and one `src/monsters/<key>.c` per ported monster ([#215](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/215)). The runtime's [README](../mods/uc_runtime/README.md) records the interface and how a module is added.

The id layer gives the ported monsters their own ids and answers MH4U's monster-id-indexed tables for them: the readers of the factory, data path, enemy data, crowns, list order, icon, resource index and drop tables are hooked, and a registered id is answered with the MH4U monster the registry names as its stand-in — except its resource record, which the runtime builds for the ported id with its own paths for the kinds of file and motion slots the port ships and the stand-in's for the rest — while ids 0 to 123 fall through to the game's functions. At quest start it also reads the quest's large-monster waves and marks their stand-ins present in the quest task's 124-byte enemy-data array, so the game's own preload loads the stand-in's data; a ported id is past that array ([#182](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/182)). Ids 124 to 223 are permanent. A monster ported after that range is full takes a registry id from 256 up, which a quest's u32 monster list records; at quest start the runtime finds the loaded `.mib` and lends each pooled monster it names a free byte of 224 to 255, answers that byte with the monster's rows, and frees it when the quest ends ([the pool](../data/ids/README.md#the-pool)). No pooled monster ships yet. Which reader each table is, and what is not answered yet, are in [reference/](../reference/README.md#mh4u-monster-tables) and the [runtime's README](../mods/uc_runtime/README.md).

One plugin stays outside the runtime. `mods/force_action` is a debug tool: its `mod.json` names the action setter (USA v1.3.0 address `0x0090ef74`), and its C library replaces the category and index the AI asks for with the forced pair, so the game's own setter initializes the chosen action and it plays (the plugin's check, R1p). The dispatcher (`0x006e9cac`) is a fallback hook only. Its library is built into the code library by the fork's `tools/build_game.py`, like any other plugin.

The runtime's first module, `mods/uc_runtime/src/monsters/rathian-gu.c`, is GU Rathian's translated MHXX-only actions, moved from the plugin that held them. The runtime records the enemy that `uEnemyFactory::create` spawned against the ported id, before the id layer rewrites the factory's id to the stand-in, and for that monster it wraps `uEnemy`'s action dispatcher (USA v1.3.0 address `0x006e9cac`): the module runs the translated handlers for her MHXX-only actions (3/98, 12/1-3, 4/27-32, 8/0 and category 17, whose gate runs MH4U's base action update), and every other id, and every other monster, goes to the game's own dispatcher unchanged. Its engine calls go through ABI 4's `call2` (r0-r3, s0/s1, the s0 return), with the runtime's guest stubs for the caller's s0-s3, the three-float hit check and a fifth stack argument ABI 4 cannot pass (checks T0, T1). Its ledger is [data/actions](../data/actions/README.md). The runtime's second module, `mods/uc_runtime/src/monsters/rathian-3u.c`, is 3U Rathian's own handlers, reimplemented on `uEnemy` under decision 0002's amendments ([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)): its first slice is category 0 (0/0, 0/1, 0/2, 0/3, 0/4 and 0/6) and the three base-class handlers they reach (`0x0082d1cc`, `0x00858b6c`, `0x0082b7dc`), which later slices reuse; an id the module does not carry yet goes to MH4U's dispatcher and is logged once. Its handlers are one file per action family under `src/monsters/rathian-3u/`, so the ten family slices add a file and no shared edit: the build discovers the files with `tools/gen_families.py` and writes the family list the module's dispatch loops over ([#265](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/265)), and each family's fake-host test lives under `tests/rathian-3u/`, which `make test` discovers the same way ([#268](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/268)). Its field map is in the [runtime's README](../mods/uc_runtime/README.md#3u-rathians-module-category-0).

The action-id map onto shared MH4U actions is gone: decision [0002](decisions.md#0002-monsters-are-ported-onto-mh4us-engine)'s 2026-11-26 amendment runs the source's own handler for every action, shared ids included, so no run-time table sends a ported action to an MH4U one.

## From dumps to a mod

1. The player dumps MH4U, MH3U, MHXX and MHGU themselves.
2. `mhuc` reads those dumps and converts what the mod needs into MH4U's formats.
3. The result is a mod folder that the fork's mod manager installs.

Steps 1 and 2 work for single files, and step 2 for a ported monster's whole asset archive
(`mhuc convert monster`). The commands that would run the whole pipeline don't exist yet.

## The toolkit

`src/mhuc/`, standard library only.

| Module | Does |
|---|---|
| `formats/` | MT Framework archives (ARC), 3DS textures (TEX), text (GMD) and MH4U's message tables (LMD), motions (LMT), camera lists (LCM), models (MOD), monster data (MH4U EMD, MHXX `dttune`, `dtbase` and `dtbparts`, MH3U `em_status`, hurt and attack volumes), motion effects and effect lists (MEF/ESQ/PSL, EFL/PEL), serialised objects (XFS), MH4U layouts (LYT), RomFS images, class ids |
| `crypto/` | Blowfish and the save, Extra Data and DLC ciphers of the three games |
| `quests/` | quest readers for the three games, the MH4U `.mib` writer, conversion from MHXX, monster ids by name |
| `extdata.py` | MH4U Extra Data records: guild quest cards, DLC Palicos, the in-game test kit |
| `save.py` | MH4U's character saves (`user1` to `user3`) and `system`: profile, item and equipment boxes, pouches, guild quests, Palicos, monster log and guild card ([save](../specs/save.md)) |
| `survey.py` | runs the specs' checks over a whole RomFS and prints counts only |
| `catalog.py` | what MH4U already has of 3U's and GU's monsters and maps, from `data/catalog/` |
| `monsterdata.py` | rebuilds an MH4U monster's `.etd`/`.emd` values from MHXX's or MH3U's files and compares, counts only |
| `monsters.py` | a ported monster's files: an MHXX monster archive sorted into the kinds the registry's `files` column ships, converted where needed and packed as a mod folder |
| `monstertext.py` | a ported monster's name and Hunter's Notes text: the registry's name and the source game's notes table, built into the mod's `text/monster_text.bin` (`mhuc text build`) |
| `monsterassets.py` | builds a ported monster's mod folder from its source game's archive: the models and textures as they are, the materials with MH4U's MRL signature, the motion lists converted to version 67 ([3U Rathian's files](#3u-rathians-files)) |
| `monstersound.py` | a ported monster's own sounds: its source game's waves, bank, request and sound call converted to MH4U's and written into the port's arc ([specs/sound.md](../specs/sound.md#what-a-converter-must-produce)) |
| `save.py` | MH4U's character and `system` saves: profile, boxes, equipment, guild quests, Palicos, the monster log, the guild card and the mapped `system` fields |

Each format follows its spec in [specs/](../specs/README.md). A field is marked verified only once it has been checked against real files, with the procedure written down.

## Saves

MH4U's character saves are read by `mhuc save dump` (specs/save.md): the profile, item and equipment boxes, the seven worn pieces and their box indices, the item and gunner pouches, ten guild quests, 56 Palicos, the 82 fixed monster-log entries and the guild card's quest counts, weapon usage and brigade points. Checks S1 to S7 fix those offsets against the maintainer's saves.

`mhuc save clean` is the converter decision [0003](decisions.md#0003-id-allocation-and-mod-saves) asks for: it empties the item-box and pouch slots whose id is above MH4U's item list and the guild-quest slots that name a monster above id 123, and leaves the unknown blocks and the `system` save untouched, so a save that never met the mod comes back byte for byte (check S11; the in-game check is [checks.md](checks.md#save-converter-s11)). Ported weapons and armour, and the region the mod's own data goes in, wait on decision 0003's open part; the character save's quest clear lists ([#153](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/153)) and the `system` save's fields ([#154](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/154)) stay open too. The monster log is not indexed by monster id: its order is the guild card's, so a ported id does not fit it, which decision [0003](decisions.md#0003-id-allocation-and-mod-saves) asked.

## Monsters

A 3U or GU monster is ported onto MH4U's own enemy class, `uEnemy`. Its source game's code is the reference to translate, handler by handler, and never runs in the mod ([decision 0002](decisions.md#0002-monsters-are-ported-onto-mh4us-engine)). Every handler is the source's, shared action ids included, and a handler the base enemy class owns is reimplemented too (0002's 2026-11-26 amendments); the runtime's GU Rathian module's translated MHXX handlers are the kind of code every action gets, and the ported monsters' action code goes into the runtime ([decision 0013](decisions.md#0013-one-runtime-for-the-mods-native-code), [#213](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/213)). Before a version gets an id, [data/catalog/versions.csv](../data/catalog/versions.csv) records whether a player would notice it differ from MH4U's version ([decision 0004](decisions.md#0004-monster-versions)'s amendment): every large monster MH4U shares with MH3U or MHXX has a verdict, per axis (monster data, moves, model), with the evidence — the source's AI script and the wiki's attack lists for moves, the thresholds and counts for data ([how it is made](../data/catalog/versions.md)).

| Step | What | State |
|---|---|---|
| 1. Study the source | class, vtable, action dispatcher, engine calls | done for Rathian in all three games |
| 2. Assets | models, textures, motions, AI scripts, collision, sounds | MOD is the same version in all three games, and a 3U model's material names bind to a 3U material's records by inverted CRC-32 ([mrl](../specs/mrl.md), checks MR2 and MR4); MHXX's LMT matches MH4U's, MH3U's LMT is version 66, which reads with MH4U's layout ([lmt](../specs/lmt.md), check L3) and whose keyframe buffers decode too, except types 11 to 13, which version 66 encodes differently (check L4) and `mhuc convert monster` re-encodes as version 67 (check L6); the AI scripts share their file shape but not their bytecode: MH3U's EMC is version `0x20110601` with 13 group rows and 113 opcodes, MH4U's `0x20120804` with 23 rows and 146, and MHXX's has MH4U's version word but 21 rows and MHGU's 167 opcodes ([emc](../specs/emc.md), checks A1 to A4), so a 3U script is converted to MH4U's version and a MHXX one needs the same for the ports that use it. The motion-effect and effect-list containers are laid out and read on the three games' monster archives ([mef](../specs/mef.md), [efl](../specs/efl.md), checks FX1 to FX9, EF1, EF2, EF3); an ESQ event's motion, frame and parameters, a PSL descriptor's frame count, flags and list offset, and MH4U's record fields are placed, the effect lists convert between the three games' versions and every container round-trips, but MH4U derives an effect from the record's type, time and bone rather than an id: the spawn tables are laid out and every record resolved through them on the real files (FX10), an unused type's chain can name the port's own effect path with two `.data` writes (FX11), and the effectmap doesn't carry the port's (type, time, bone) yet, the source effect lists' block paths, effect animation and arc placement are not converted, and the PSL lists are not laid out, so an ESQ/PSL to MEF conversion is refused and no port ships its own effects yet; MHXX's camera list is version 5 against MH4U's 4, the only difference being a 16-byte record prefix ([camera](../specs/camera.md), check C1), MH3U ships none, and `mhuc convert camera` writes the version 4 list; `mhuc convert monster` turns a GU monster's MHXX archive into the port's files for the kinds its registry row ships, kind by kind below | 3U Rathian's mod folder is built, each file kind accounted for: [her files](#3u-rathians-files) |
| 3. Monster data | hitzones, parts, breaks, severing, attacks, stats | known in all three games ([emd](../specs/emd.md), [dttune](../specs/dttune.md), [dtbase](../specs/dtbase.md), [dtbparts](../specs/dtbparts.md), [emstatus](../specs/emstatus.md), [hitdata](../specs/hitdata.md)); `mhuc monsterdata` rebuilds MH4U Rathian's HP, parts, hitzones, break parts and joint records from MHXX, and her HP, most hitzone rows, her attack records' shared fields and her part records from MH3U, whose fields are mapped one by one ([part record mapping](../specs/emstatus.md#part-record-mapping)) and whose break blocks' meanings stay unverified; her part kind is MH4U's Insect Glaive extract kind, which 3U never had and MH4U's own Rathian supplies by part index ([specs/emd.md](../specs/emd.md), check E13); MH4U's own 40-byte attack record is placed from its reader, its two flag words' consumers in the hit check and the slot update are named, and its values are checked against both games' records ([specs/emd.md](../specs/emd.md), check E10); MH4U's sever records have no counterpart in MHXX's or MH3U's data: both sever a part by swapping in a `_tail.mod`, the joint coming from the monster class's code, and MH4U's sever records' kind, index and b are read by its own loader and cut-object spawner while limit and a have no reader ([emd](../specs/emd.md#joint-and-sever-record-24-bytes), checks E11, E12) |
| 4. Register | a new monster id and the tables it indexes | MH4U's tables are found ([reference/](../reference/README.md#mh4u-monster-tables)), and MH3U's ids are paired with MH4U's: 32 of the 85 have an MH4U monster, 44 are monsters MH4U does not have, and 9 are props ([reference/](../reference/README.md#mh3us-ids-to-mh4us)); ids 124 to 127 are in `data/ids/registry.csv` (Rathian from MHXX and MH3U, Giadrome from MHXX, Great Wroggi from MH3U), checked by `tools/check_ids.py` and generated into `mods/uc_runtime/src/ids.h`; the runtime answers the readers of the factory, data path, enemy data, crowns, list order, icon, resource index and drop tables, with a resource record built for the ported id that keeps its own paths for the kinds of file and motion slots it ships and the stand-in's for the rest, and the stand-in's rows elsewhere; MH4U's 0 to 123 fall through. Once the permanent range (124 to 223) is full, a ported monster takes a registry id from 256 up and is lent a byte of 224 to 255 per quest; no pooled row ships yet. The engine opens a model port's own `data/emNNN.arc`, which the converter made self-sufficient; the enemy data reader still answers with the stand-in's until the ports ship `.emd`/`.etd`, and the quest task's enemy-data preload is supplied for the stand-in (#182); the name and notes text are answered by the three message getters, and the Hunter's Notes list's page init, page builder and detail hooks give a ported id a page of its own after MH4U's own pages, with ids 0 to 123 keeping the game's rows and pages |
| 5. Behaviour | each action handler, the source's reimplemented on `uEnemy` | every action id runs her source game's handler, shared or not, and a handler the base class owns is reimplemented too (0002's 2026-11-26 amendments), so nothing maps ids or motion numbers at run time. The 3U port's handlers are written family by family against the ledger `data/actions/rathian-3u.csv` ([#214](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/214)) in her module of the runtime ([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)), the slices being [#217](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/217) to [#229](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/229) and action 4's [#136](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/136). The facts to write them from: MH3U's 191 ids on 66 handler units, 174 shared with MH4U's `uEm001` (342 ids, 97 units) and 17 MH4U lacks, each handler passing MH4U's motion wrapper the MH4U index of its own animation ([R1](checks.md#monster-actions), [reference](../reference/README.md#a-3u-rathians-moves)); each engine call goes to MH4U's counterpart through ABI 4's `call2` with r0-r3 and s0/s1 ([#110](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/110), [#134](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/134), checks P3 and P4), and the calls #55 still blocks are named. Action 4's action-start record is converted from MH3U's and checked against the 3/5 pair both games have ([actiondata](../specs/actiondata.md), checks N1/N2), and its value curves are carried because both games' evaluators are the same body (N4). The GU port's translated MHXX handlers (3/98, 12/1-3, 4/27-32, 8/0 and category 17) are the runtime's first module (checks T0/T1, `mods/uc_runtime/src/monsters/rathian-gu.c`); the interface it uses is in the runtime's [README](../mods/uc_runtime/README.md#adding-a-module). The per-move in-game checks wait for #48/#49 and #143 ([#113](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/113), [#116](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/116)) |
| 6. Quests, arena | the monster's quests and map | quest conversion exists for MHXX |


### A ported monster's files

`mhuc convert monster --id 124 --romfs <MHXX RomFS> --mh4u-romfs <MH4U RomFS> --out <mod
folder>` reads the id's registry row ([data/ids](../data/ids/README.md)), takes the row's
`source_key` and variant to find the monster's MHXX archive (`arc/enemy/em001_00.arc`), and
writes the kinds the row's `files` column ships into MH4U's `/data/em124.arc` plus a `mod.json`
the fork's mod manager installs. The same column is what the runtime reads: it rewrites
the resource record's path for each kind the port ships to the port's own names and keeps the
stand-in's path for the rest, so the converter and the plugin agree on what is in the archive.
The converter also reads the stand-in's own `/data/emNNN.arc` from MH4U's RomFS and copies
every entry the record keeps into the port's archive under its original path, so the one
archive the game opens holds both the port's files and the stand-in's kept ones. For Rathian
the row is `model,motions=0-4,camera,tail`; Giadrome's is `model,motions=0,2,3,4`.

The port's files take MH4U's names with the port's id: `enemy\em124\mod\em124` and
`..._tail`, `enemy\em124\mot\em124_0` to `_4`, `enemy\em124\mot\e124_cam`. Its command path
stays the stand-in's until MHXX's EMC converts (P4). MH4U builds the archive's own name from
the id (`data\em%03d`),
so a ported id's own archive is what the game opens. The stand-in's kept paths (its camera for
125 to 127, unshipped motion slots, motion effects, sound, effect lists and command) are copied
into the same archive under the stand-in's paths. The enemy data reader still answers with the
stand-in's: MH4U reads the monster's `.etd`/`.emd` from `data/em_data.arc` and the port ships no
data yet (step 3).

| File kind | MHXX | MH4U | What the converter does |
|---|---|---|---|
| model and tail model (rModel) | MOD 0xE6 | MOD 0xE6 | taken as is, when the row ships `model` and `tail` |
| material (rMaterial) | MRL 0x20 | MRL 0x20 | taken as is except its shader ids, moved to MH4U's slots for the same object names, and the signature at 0x10, MH4U's shader package hash (a material names its shader objects by slot in its own game's package, and MH4U's loader refuses another package's hash: [mfx](../specs/mfx.md), [mrl](../specs/mrl.md)); the texture paths it names are MHXX's and kept |
| motion lists (rMotionList) | LMT 67 | LMT 67 | taken as is, at the slots the row's `motions=` names. MHXX may store them under another monster's folder (a family shares them: Giadrome's are em014's, at slots 0, 2, 3 and 4), so the converter takes a list from any `enemy/emNNN/.../mot/` and renames it to the port's id at its own slot |
| camera list (rCameraList) | LCM 5 | LCM 4 | converted with `camera.from_mhxx` when the row ships `camera` ([camera](../specs/camera.md)); 124 ships MHXX's list at `e124_cam`, while 125 to 127 have no source camera and keep the stand-in's |
| AI script (rEnemyCmd) | EMC 0x20120804, 21 group rows, MHGU's 167 opcodes | EMC 0x20120804, 23 rows, 146 opcodes | MH3U's EMC converts (check A5), so 125 ships her own script; MHXX's rows and opcode table are not MH4U's ([emc](../specs/emc.md), checks A1 to A4), so 124 keeps the stand-in's until an MHXX EMC converter ships (P4: the as-is MHXX EMC hung the load) |
| textures (rTexture) | TEX 0xA6 | TEX 0xA5 | converted: the version field 0xA6 → 0xA5, the one byte that differs, the PICA200 layout is the same ([tex](../specs/tex.md)); on Rathian's two textures the converted file differs from MHXX's in that byte alone. They stay at MHXX's paths (below) |
| archive | ARC 0x11 | ARC 0x13 | converted: the kept entries are re-packed in MH4U's ARC version |
| the stand-in's kept paths (the camera for 125 to 127, unshipped motion slots, motion effects, sound, effect lists, command) | — (the record names the stand-in's paths) | the same MH4U files, at those paths | copied as is from MH4U's own `data/emNNN.arc`, at their original paths, so the port's archive holds every path its resource record names (mef and efl have no converter yet) |
| sound | MHXX's SBKR banks and SRQR requests | MH4U's SNDB banks and SREQ requests | not this mode: the same command's sound mode (`--arc`, `--sound-arc`) converts the set for a row that ships `sound` ([specs/sound.md](../specs/sound.md)) |
| effects (EFL, EAN, PEL, PSL) | versions 0x30120306 and 0x20120224 | 0x30111104 and 0x20100924 | left out: the versions differ and effects are not ported yet |
| motion effects | PSL and PEL | MEF | left out: MHXX has no MEF |
| shells, projectiles | `shell/em/...` | MH4U's own classes | left out: MH4U's projectile code is its own ([reference](../reference/README.md#rathian-the-first-port)) |
| monster data, collision, AI auxiliaries | `dttune`, `dtbase`, `dtbparts`, body, hit and area data | MH4U's `.etd`/`.emd` and systems | left out: MH4U reads its own rows, and the registry's stand-in answers until the port ships its data (step 3) |

The converter fails rather than ship a short archive: a kind in `files` with no entry in the
source, or a kind this mode cannot produce (sound, mef, efl), is an error naming it. The
materials keep MHXX's texture paths (`enemy\em001\em001_00\mod\em001_00_BM`), because they
are bytes of the material file whose string data isn't documented beyond the resources it
names; the textures are therefore kept at those paths, which MH4U has no file of. The one field
the converter does rewrite are the material's shader ids and signature: MHXX's ids are slots of
MHXX's shader package and its signature `0xeaca0cbd` is that package's hash, where MH4U's loader
wants its own `0xcec1aa61` and uses the slots as stored ([mfx](../specs/mfx.md),
[mrl](../specs/mrl.md)). The converter reads both packages from the two RomFS images.
Nothing is authored: every file comes from MHXX, taken or converted as the table says.

### 3U Rathian's files

`mhuc convert monster --id 125 --romfs <MH3U RomFS> --mh4u-romfs <MH4U RomFS> --mh3u-code <MH3U code> --mh4u-code <MH4U code> --out <mod folder>` is the MH3U side of [the converter
above](#a-ported-monsters-files): the id comes from [data/ids](../data/ids/README.md), the row's `source_key`
finds `arc/enemy/em001.arc`, and the mod holds one RomFS file, `/data/em125.arc`, whose every path names that id
(`enemy\em125\...`), so it never touches the MH4U monster whose tables stand in for it. The `cmd` her row ships
needs the two games' decompressed code images, where their instruction-length tables are
([emc.md](../specs/emc.md), check A5). 3U Rathian is the worked case: MH3U's 78-entry archive becomes 10 entries
of her own (2.9 MiB) plus the 31 stand-in entries the record keeps, a 3.5 MiB archive, and the sound mode of the
same command adds her sound set (`--arc --sound-arc`).

| File kind | MH3U entries | In the mod | Why |
|---|---|---|---|
| models (`MOD`, 0xE6) | 2 | as they are, under MH4U's model flag | the same version in MH3U and MH4U ([mod.md](../specs/mod.md), checks M1 to M3); her body's 44 bones (MH4U's Rathian has 43) and her tail's 3 are kept whole, because her motions are hers too; her meshes use vertex format `0xf606f017` at stride 36, which MH4U's own Rathian models use as well, and the archive's entry flag is MH4U's `0xA0000000` on models ([arc.md](../specs/arc.md#size-word-flags)) |
| materials (`MRL`, 0x20) | 2 | as they are, with their shader ids moved to MH4U's slots, the signature at 0x10 rewritten to MH4U's package hash and their texture paths rewritten | the same version and layout in both games, but a material names its shader objects by slot in its own game's shader package and carries that package's hash: MH3U's `0x3810b2e2` stalled the archive load where MH4U's loader checks for `0xcec1aa61` ([mrl.md](../specs/mrl.md), check MR3), and with only the signature rewritten MH4U reads MH3U's slots as its own, so her blend state is a sampler ([mfx.md](../specs/mfx.md)); the paths are absolute and are moved in place from `enemy\em001\mod\em001*` to `enemy\em125\mod\em125*`, the two names being the same length. The material records and their name hashes are kept, so the model still finds its materials, and MH4U's archive loader completes with the converted material (#203, [check M3](../docs/checks.md#a-converted-material-loads-m3)); and with the ids moved the model draws in game ([X4](../docs/checks.md#the-materials-shader-ids-x4-game)) |
| model textures (`TEX`, 0xA5) | 2 | as they are | the same version in both games ([tex.md](../specs/tex.md), check T1) |
| motion lists (`LMT`, 66) | 3 | converted to version 67 | the layouts are the same, but version 66 stores keyframe types 11 to 13 signed and version 67 unsigned behind a bounds block ([lmt.md](../specs/lmt.md#keyframe-buffers)): each key is re-encoded, within 6.11e-5 of the source's component (check L6) |
| monster data (`EMS`, `BDD`, `HTS`, `HTD`) | 5 | left out of the archive | they become MH4U's `.emd`/`.etd` rows through `mhuc monsterdata`, on her own skeleton ([hitdata.md](../specs/hitdata.md)); those rows live in `/data/em_data.arc`, not in her archive |
| AI script (`EMC`, 0x20110601) | 1 | converted to MH4U's version `0x20120804`, 23 group rows, at `enemy\em125\data\em125_cmd` | the file shape is shared but the bytecode is not: 15 opcodes' argument counts differ, and MH4U's evaluator reads the argument each of the 14 gains as a target-point or state-table index ([emc.md](../specs/emc.md), check A5). The converter writes 0 there, the entry MH3U's evaluator uses, keeps every `00 cat num` and `14 nn`, and refuses a file that uses `0x70` (whose value MH3U computes) or a `0x67` whose dropped argument is not 0; hers converts, so her registry row ships `cmd` and the record names this path |
| movement and spawn data (`EMM`, `EMG`, `EML`, `EMT`, `EAR`) | 5 | left out | MH4U's `uEnemy` doesn't read these files; they are the source for the behaviour port |
| sound (`MSS`, 0x20110404) | 1 | converted by the command's sound mode | MH4U's is 0x20120123; `--arc --sound-arc` converts her 48 waves, bank, request and call into the same archive ([sound.md](../specs/sound.md), check SN9) |
| effects (`EFL` 0x30110616, `EAN`, `ESQ`, the effect model, material and textures) | 57 | left out | MH4U's effect lists are 0x30111104; effects are their own work, and MH4U's own effects play for now |

**Motion numbers.** MH4U starts an animation by the index `file << 8 | slot` and MH3U by `file * 100 + slot`, and
her converted motion lists keep MH3U's grouping. A ported monster runs her own handler for every action id
(0002's 2026-11-26 amendment), so the handler the port reimplements asks MH4U's motion-start wrapper
(`0x0094e318`, R1's) for MH4U's form of the animation it starts: MH3U's `file * 100 + slot` written as MH4U's
`file << 8 | slot` for her converted lists, as the constant MH3U's handler passes, converted when the handler
is written. No table translates a motion number at run time. R1 finds the same animation at another index for
93 of the 115 compared 3U ids; 13/5, 13/6 and 13/8 are the ids whose motion itself differs and each keeps
theirs, and the 19 category-7 ids whose computed index R1 cannot resolve are read from their handlers
([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216) and its slices).

Nothing is authored. A conversion adds no value, name or path the source game doesn't have; the only thing it
fixes is the mod's own layout, `enemy\em<id>\mod\em<id>` and `enemy\em<id>\mot\em<id>_<n>`, which the
resource-path answers for a ported id read ([issue #105](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/105)).
The in-game load and move checks are [#144](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/144) and [#113](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/113).

What makes this tractable:

- **The three games share one action scheme.** A monster's current action is a category byte and an index byte. 273 of MHXX Rathian's 301 action ids also exist in MH4U. The motion index a handler starts is numbered differently, though: MH4U and MHXX pack it as LMT file << 8 | slot and MH3U as file * 100 + slot, with the LMT files grouping the animations differently. R1's content check finds the same animation at another index for most 3U ids, so a 3U handler passes MH4U's form of the index it starts; 13/5, 13/6 and 13/8 are the ids whose motion itself differs. For GU the index agrees on every comparable id (R2) and #48 ships MHXX's motion lists, so a GU handler's index is already MH4U's. The converted animation files keep the source game's grouping and every action runs its source's handler (0002's 2026-11-26 amendment), so each action keeps its own animation: 13/5, 13/6 and 13/8 each play theirs, and the 17 3U ids MH4U lacks are reimplemented like the 174 it has, base-class handlers included, in her module ([#216](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/216)).
- **The AI script's action ids and group order survive a conversion.** An EMC names native actions by the same category/index pair the handlers use, and `14 nn` indexes group 1, so a 3U script keeps both: no action id and no motion number is remapped in the script. Only the version, the group rows and 15 opcodes' arguments change ([emc](../specs/emc.md#the-added-argument)): the 14 that gain one get the entry MH3U's evaluator used (0) and `0x67` loses a 0, both read in the games' evaluators (check A5), and the ported monster's `cmd` path loads the result (`files` in [data/ids](../data/ids/README.md)).
- **A GU monster's code assumes MHXX's enemy layer.** Rathian's MHXX module calls 330 engine functions, and MH4U lacks 262 of them. That is why handlers are rewritten instead of linked.
- **MHXX keeps its monsters in 109 CRO modules,** not in `code.bin`. All of them recompile and test against the original ([reference/](../reference/README.md)).
- **MHGU on Switch is nearly MHXX.** It shares 2,949 classes with MHXX and links its monsters statically, which helps match functions across games.

Before porting a monster, MH4U's id-indexed tables have to grow. They grow by hooks on their readers, which answer the new ids; a table is relocated only where a case needs it. Ids come from one registry file, `data/ids/registry.csv`, start at 124 and only ever grow, because saves and quests keep them; its first four rows are 124 to 127: the two ported Rathians, Giadrome and Great Wroggi, each with the MH4U monster whose rows stand in until the port ships its own ([data/ids](../data/ids/README.md)). `tools/check_ids.py` checks the ranges and uniqueness, keeps the permanent ids consecutive, and generates the runtime's headers with the permanent array, the pooled one and the module table: 124 to 223 are permanent, and once that range is full a ported monster takes a row from 256 up and is lent a byte of 224 to 255 per quest ([the pool](../data/ids/README.md#the-pool)). The mod's data may go in MH4U's save, which a converter will clean back to MH4U's own ([decisions.md](decisions.md#0003-id-allocation-and-mod-saves)).

## Quests

Every 3U and GU quest is the source game's own quest, rewritten as an MH4U `.mib`.

- **Readers:** `mhuc quest dump` reads MH4U `.mib`, MHXX quest archives and MH3U `QTDS` into JSON.
- **Writer:** the `.mib` builder lays a quest out with every offset recomputed. Rebuilding any of the 120 MH4U DLC quests gives back every field it had.
- **Converter:** `mhuc convert quest --from mhxx` maps ids through `data/idmap/`, which ships empty. It refuses any quest with an unmapped id.
- **Routes into the game:** the quest archives, an Extra Data slot as a download, or a local DLC server answering the game's DLC screen.

The field-by-field mapping, the three routes, the Extra Data records and the DLC protocol are in [quests.md](quests.md).

## Underwater

Underwater play comes from MH3U, which has it in full: the swim state, oxygen, the camera, water volumes, motions per weapon and monsters' underwater behaviour. Each part is to be read from MH3U's files or its recompiled code, and carried in as data plus plugin hooks.

Known so far:

- MH3U's 387 motion lists are LMT version 66. Version 66 and 67 share one layout, so `mhuc` reads all 387 ([lmt](../specs/lmt.md), check L3), and their keyframe buffers decode too ([lmt](../specs/lmt.md#keyframe-buffers), check L4): the one version difference is types 11 to 13, which version 66 stores signed and version 67 unsigned behind a bounds block, so a converter has to re-encode those tracks' keys. The version word itself is a loader gate: MH4U's loader refuses any version but 67 ([lmt](../specs/lmt.md#versions)).
- MH3U's and MH4U's hunter skeletons are the same rig with MH3U's empty root dropped and the pelvis renumbered 13 to 0, so 3U underwater motions need their bone ids rewritten, not a positional retarget ([underwater.md](underwater.md#hunter-skeletons)). The Sword and Shield weapon rigs are the same in both games with nothing renumbered, and MH3U ships no weapon-rig motion list, so a 3U weapon model plays MH4U's own weapon motion unchanged ([underwater.md](underwater.md#weapon-rigs), [specs/mod.md](../specs/mod.md), check M5).
- MH3U's stage collision uses MH4U's format ([specs/sbc.md](../specs/sbc.md)).
- MH3U's player has no class per state: one action machine holds a category byte (+0x3e) and an index (+0x40) in the status block at `[uPlayer+0xd5c]`, set by `0x8e128c` and dispatched by `0x8aaa48`; the swim actions are category 1, indices 0x12 to 0x17, and the water position is a separate byte, +0x3d (3 underwater) ([underwater.md](underwater.md#mh3us-player-state-machine), check U2).
- Cha-Cha (MH3U on Wii U) marks the swim state, the underwater camera and underwater carving. All three are re-found on 3DS: the carve is category 0, index 0x33 on land (gather kind 4) and index 0x61 under water (kind 6), both calling the same gather action ([underwater.md](underwater.md#cha-chas-marks-on-3ds)).
- MH4U kept the water-surface class `uOcean` whole (same class id, parent, size and vtable, its functions paired in the MH4U↔MH3U map) and none of the underwater systems: MH3U's air-gauge class (which draws nothing of its own), its in-game camera classes and its guest player are gone, and its player class survives only as a name on a rewritten layer. The air gauge is a display of the player's oxygen timer, drawn by MH3U's quest cockpit, not a system of its own. No MH4U stage file or code path creates `uOcean`, so a converted 3U stage must bring its own water surface ([underwater.md](underwater.md#what-mh4u-kept)).

The first target is the Water Arena: enter water, swim, surface, oxygen, with Sword and Shield motions, then Lagiacrus. Charge Blade and Insect Glaive never had underwater movesets, so theirs would be authored. What comes from MH3U, the leads and the unknowns: [underwater.md](underwater.md).

## Audio

Sounds and music come from each piece of content's own game and play through MH4U's sound engine by request id. The port needs no audio change.

- MH3U uses MH4U's sound classes, with the same class ids, but each file version is one older (SN1); `mhuc` reads the older wave, bank, request and stream request layouts against the whole MH3U RomFS (SN6). A 3U monster's whole call set converts to MH4U's versions (`mhuc convert monster`, [specs/sound.md](../specs/sound.md), checks SN7 to SN9), and the 3U Rathian's registry row ships `sound`.
- MHXX uses the next generation of classes, shared with MHGU on Switch: its banks are GU's (`SBKR` 4), but its requests are 100-byte records, not GU Switch's 132 (S3), and its waves are `MADP` 5 in a header MH4U doesn't read.
- MH4U's wave, bank and emitter layouts come from MHGU Definitive Edition and are unverified; the `.stq` tables are checked against all 50 MH4U `.stq` files and every stream request in the image (214, loose and inside ARCs) is read (check S4), and the 100-byte sequence record's readers and the loader's id-to-row index are named from the game's code (check S7).
- A monster's theme is a sequence id in a stream request, chosen by a hardcoded switch over its id, not by a table ([audio.md](audio.md#how-mh4u-picks-a-monsters-theme)).
- **A monster's set is one path in its resource record.** The record's +0x1c names the sound call (`sound\call\em\emNNN`), and the call, request and bank name the rest by path; MH4U ships all four kinds in the monster's own `data/emNNN.arc` ([specs/sound.md](../specs/sound.md#a-monsters-sound-set-and-how-the-record-points-to-it-sn7)). A port ships its own set under its own id (`mhuc convert monster`), so a monster MH4U never had brings its own voice.
- **There is no separate sound heap.** MH4U loads banks, requests and waves from the 47 MiB Resource heap it shares with every other non-drawing resource; the SoundBuffer allocator is an alias of Resource ([audio.md](audio.md#memory)).

What the mod needs, what is known and the unknowns: [audio.md](audio.md).

## Progression

Players reach 3U and GU content through one story in MH4U's hubs, whose key quests are drawn from all three games ([decisions.md](decisions.md#0007-progression)).

