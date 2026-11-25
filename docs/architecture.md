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
- at start-up the port loads the library, which can read and write game memory and allocate from the game's heap.

The first plugin is `mods/force_action`. Its `mod.json` names `uEnemy`'s action setter (USA
v1.3.0 address `0x0090ef74`); the C library replaces the category and index the AI asks for
with the forced pair, so the game's own setter initializes the chosen action and it plays (the
plugin's check, R1p). The dispatcher (`0x006e9cac`) is a fallback hook only. The library is
built into the code library by the fork's `tools/build_game.py`, like any other plugin.

The second plugin is `mods/monster_ids`. It gives the ported monsters their own ids and
answers MH4U's monster-id-indexed tables for them: the readers of the factory, data path,
enemy data, crowns, list order, icon, resource index and drop tables are hooked, and a
registered id is answered with the MH4U monster the registry names as its stand-in, while ids
0 to 123 fall through to the game's functions. Which reader each table is, and what is not
answered yet, are in [reference/](../reference/README.md#mh4u-monster-tables) and the
plugin's [README](../mods/monster_ids/README.md).

## From dumps to a mod

1. The player dumps MH4U, MH3U, MHXX and MHGU themselves.
2. `mhuc` reads those dumps and converts what the mod needs into MH4U's formats.
3. The result is a mod folder that the fork's mod manager installs.

Steps 1 and 2 work for single files today. The commands that would run the whole pipeline don't exist yet.

## The toolkit

`src/mhuc/`, standard library only.

| Module | Does |
|---|---|
| `formats/` | MT Framework archives (ARC), 3DS textures (TEX), text (GMD), motions (LMT), models (MOD), monster data (MH4U EMD, MHXX `dttune`, `dtbase` and `dtbparts`, MH3U `em_status`, hurt and attack volumes), serialised objects (XFS), RomFS images, class ids |
| `crypto/` | Blowfish and the save, Extra Data and DLC ciphers of the three games |
| `quests/` | quest readers for the three games, the MH4U `.mib` writer, conversion from MHXX, monster ids by name |
| `extdata.py` | MH4U Extra Data records: guild quest cards, DLC Palicos, the in-game test kit |
| `survey.py` | runs the specs' checks over a whole RomFS and prints counts only |
| `catalog.py` | what MH4U already has of 3U's and GU's monsters and maps, from `data/catalog/` |
| `monsterdata.py` | rebuilds an MH4U monster's `.etd`/`.emd` values from MHXX's or MH3U's files and compares, counts only |

Each format follows its spec in [specs/](../specs/README.md). A field is marked verified only once it has been checked against real files, with the procedure written down.

## Monsters

A 3U or GU monster is ported onto MH4U's own enemy class, `uEnemy`. Its source game's code is the reference to translate, handler by handler, and never runs in the mod ([decision 0002](decisions.md#0002-monsters-are-ported-onto-mh4us-engine)).

| Step | What | State |
|---|---|---|
| 1. Study the source | class, vtable, action dispatcher, engine calls | done for Rathian in all three games |
| 2. Assets | models, textures, motions, AI scripts, collision, sounds | MOD is the same version in all three games; MHXX's LMT and EMC match MH4U's, MH3U's LMT is version 66, which reads with MH4U's layout ([lmt](../specs/lmt.md), check L3) and whose keyframe buffers decode too, except types 11 to 13, which version 66 encodes differently (check L4), and its EMC is older |
| 3. Monster data | hitzones, parts, breaks, severing, attacks, stats | known in all three games ([emd](../specs/emd.md), [dttune](../specs/dttune.md), [dtbase](../specs/dtbase.md), [dtbparts](../specs/dtbparts.md), [emstatus](../specs/emstatus.md), [hitdata](../specs/hitdata.md)); `mhuc monsterdata` rebuilds MH4U Rathian's HP, parts, hitzones, break parts and joint records from MHXX, and her HP, most hitzone rows, her attack records' shared fields and her part records from MH3U, whose fields are mapped one by one ([part record mapping](../specs/emstatus.md#part-record-mapping)) and whose break blocks' meanings stay unverified; her part kind is MH4U's Insect Glaive extract kind, which 3U never had and MH4U's own Rathian supplies by part index ([specs/emd.md](../specs/emd.md), check E13); MH4U's own 40-byte attack record is placed from its reader and checked against both games' records ([specs/emd.md](../specs/emd.md), check E10); MH4U's sever records have no counterpart in MHXX's or MH3U's data: both sever a part by swapping in a `_tail.mod`, the joint coming from the monster class's code, and MH4U's sever records' kind, index and b are read by its own loader and cut-object spawner while limit and a have no reader ([emd](../specs/emd.md#joint-and-sever-record-24-bytes), checks E11, E12) |
| 4. Register | a new monster id and the tables it indexes | MH4U's tables are found ([reference/](../reference/README.md#mh4u-monster-tables)), and MH3U's ids are paired with MH4U's: 32 of the 85 have an MH4U monster, 44 are monsters MH4U does not have, and 9 are props ([reference/](../reference/README.md#mh3u-ids-to-mh4us)); ids 124 and 125 are in `data/ids/registry.csv`, checked by `tools/check_ids.py` and generated into `mods/monster_ids/src/ids.h`; `mods/monster_ids` answers the readers of the factory, data path, enemy data, crowns, list order, icon, resource index and drop tables, and MH4U's 0 to 123 fall through. The name and notes text and the notes-list walk are not answered yet |
| 5. Behaviour | each action handler, translated onto `uEnemy` | not started |
| 6. Quests, arena | the monster's quests and map | quest conversion exists for MHXX |

What makes this tractable:

- **The three games share one action scheme.** A monster's current action is a category byte and an index byte. 273 of MHXX Rathian's 301 action ids also exist in MH4U. The motion index a handler starts is numbered differently, though: MH4U and MHXX pack it as LMT file << 8 | slot and MH3U as file * 100 + slot, with the LMT files grouping the animations differently. R1's content check finds the same animation at another index for most ids, so a port maps the indices instead of reusing them; 13/5, 13/6 and 13/8 are the ids whose motion itself differs.
- **A GU monster's code assumes MHXX's enemy layer.** Rathian's MHXX module calls 330 engine functions, and MH4U lacks 262 of them. That is why handlers are rewritten instead of linked.
- **MHXX keeps its monsters in 109 CRO modules,** not in `code.bin`. All of them recompile and test against the original ([reference/](../reference/README.md)).
- **MHGU on Switch is nearly MHXX.** It shares 2,949 classes with MHXX and links its monsters statically, which helps match functions across games.

Before porting a monster, MH4U's id-indexed tables have to grow. They grow by hooks on their readers, which answer the new ids; a table is relocated only where a case needs it. Ids come from one registry file, `data/ids/registry.csv`, start at 124 and only ever grow, because saves and quests keep them; its first two rows are 124 and 125, the two ported Rathians, each with the MH4U monster whose rows stand in until the port ships its own ([data/ids](../data/ids/README.md)). `tools/check_ids.py` checks the ranges, uniqueness and consecutive ids, and generates the plugin's header. The mod's data may go in MH4U's save, which a converter will clean back to MH4U's own ([decisions.md](decisions.md#0003-id-allocation-and-mod-saves)).

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

- MH3U's 387 motion lists are LMT version 66. Version 66 and 67 share one layout, so `mhuc` reads all 387 ([lmt](../specs/lmt.md), check L3), and their keyframe buffers decode too ([lmt](../specs/lmt.md#keyframe-buffers), check L4): the one version difference is types 11 to 13, which version 66 stores signed and version 67 unsigned behind a bounds block, so a converter has to re-encode those tracks' keys.
- MH3U's and MH4U's hunter skeletons are the same rig with MH3U's empty root dropped and the pelvis renumbered 13 to 0, so 3U underwater motions need their bone ids rewritten, not a positional retarget ([underwater.md](underwater.md#hunter-skeletons)).
- MH3U's stage collision uses MH4U's format ([specs/sbc.md](../specs/sbc.md)).
- Cha-Cha (MH3U on Wii U) marks the swim state, the underwater camera and underwater carving. Its offsets must be re-found on 3DS.
- MH4U kept the water-surface class `uOcean` whole (same class id, parent, size and vtable, its functions paired in the MH4U↔MH3U map) and none of the underwater systems: MH3U's air-gauge class (which draws nothing of its own), its in-game camera classes and its guest player are gone, and its player class survives only as a name on a rewritten layer. The air gauge is a display of the player's oxygen timer, drawn by MH3U's quest cockpit, not a system of its own ([underwater.md](underwater.md#what-mh4u-kept)).

The first target is the Water Arena: enter water, swim, surface, oxygen, with Sword and Shield motions, then Lagiacrus. Charge Blade and Insect Glaive never had underwater movesets, so theirs would be authored. What comes from MH3U, the leads and the unknowns: [underwater.md](underwater.md).

## Audio

Sounds and music come from each piece of content's own game and play through MH4U's sound engine by request id. The port needs no audio change.

- MH3U uses MH4U's sound classes, with the same class ids, but each file version is one older (SN1); `mhuc` now reads the older wave, bank, request and stream request layouts against the whole MH3U RomFS (SN6), so a 3U monster's sound can be read. Converting it to MH4U's versions is still undone.
- MHXX uses the next generation of classes, shared with MHGU on Switch: its waves are MH4U's version, its banks and requests are GU's.
- MH4U's wave, bank and emitter layouts come from MHGU Definitive Edition and are unverified; the `.stq` tables are checked against all 50 MH4U `.stq` files and every stream request in the image (214, loose and inside ARCs) is read ([specs/sound.md](../specs/sound.md#stream-request-strq-a-stream-table-and-a-sequence-table), check S4).
- A monster's theme is a sequence id in a stream request, chosen by a hardcoded switch over its id, not by a table ([audio.md](audio.md#how-mh4u-picks-a-monsters-theme)).
- **There is no separate sound heap.** MH4U loads banks, requests and waves from the 47 MiB Resource heap it shares with every other non-drawing resource; the SoundBuffer allocator is an alias of Resource ([audio.md](audio.md#memory)).

What the mod needs, what is known and the unknowns: [audio.md](audio.md).

## Progression

Players reach 3U and GU content through one story in MH4U's hubs, whose key quests are drawn from all three games ([decisions.md](decisions.md#0007-progression)).

