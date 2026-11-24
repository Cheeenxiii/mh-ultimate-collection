# Architecture

How the mod is built, what exists today, and where each part of the work stands.

## Two repositories

| Repository | Holds |
|---|---|
| this one | content: the `mhuc` toolkit, format specs, the reference recompiles, and later the mod's own files |
| [MH4UltimateDC-fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork), branch `uc/main` | the engine: upstream's port, plus native plugins and hooks by name |

The mod reaches the engine only through the fork's plugin API. Its reference is the fork's [docs/PLUGINS.md](https://github.com/Cheeenxiii/MH4UltimateDC-fork/blob/uc/main/docs/PLUGINS.md). In short:

- a mod folder holds a `mod.json`, RomFS files and a native library;
- `mod.json` names the game functions the library hooks;
- the fork's `tools/build_game.py` builds those hooks into the recompiled game;
- at start-up the port loads the library, which can read and write game memory and allocate from the game's heap.

The mod has no `mod.json` and no plugin yet.

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
| 2. Assets | models, textures, motions, AI scripts, collision, sounds | MOD is the same version in all three games; MHXX's LMT and EMC match MH4U's, MH3U's are older |
| 3. Monster data | hitzones, parts, breaks, attacks, stats | known in all three games ([emd](../specs/emd.md), [dttune](../specs/dttune.md), [dtbase](../specs/dtbase.md), [dtbparts](../specs/dtbparts.md), [emstatus](../specs/emstatus.md), [hitdata](../specs/hitdata.md)); `mhuc monsterdata` rebuilds MH4U Rathian's HP, parts, hitzones, break parts and joint records from MHXX, and her HP, most hitzone rows and her attack records' shared fields from MH3U; MH4U's sever records have no MHXX counterpart found |
| 4. Register | a new monster id and the tables it indexes | MH4U's tables are found ([reference/](../reference/README.md#mh4u-monster-tables)) |
| 5. Behaviour | each action handler, translated onto `uEnemy` | not started |
| 6. Quests, arena | the monster's quests and map | quest conversion exists for MHXX |

What makes this tractable:

- **The three games share one action scheme.** A monster's current action is a category byte and an index byte. 273 of MHXX Rathian's 301 action ids also exist in MH4U.
- **A GU monster's code assumes MHXX's enemy layer.** Rathian's MHXX module calls 330 engine functions, and MH4U lacks 262 of them. That is why handlers are rewritten instead of linked.
- **MHXX keeps its monsters in 109 CRO modules,** not in `code.bin`. All of them recompile and test against the original ([reference/](../reference/README.md)).
- **MHGU on Switch is nearly MHXX.** It shares 2,949 classes with MHXX and links its monsters statically, which helps match functions across games.

Before porting a monster, MH4U's id-indexed tables have to grow. Two ways are open: relocate a table into plugin memory and patch its readers, or hook the readers and answer new ids. Ids only ever grow, because saves and quests keep them. How ids are handed out, and where the mod keeps what MH4U's save doesn't hold, is open ([decisions.md](decisions.md#id-allocation-and-mod-saves)).

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

- MH3U's 387 motion lists are LMT version 66. The layout we have reads version 67, so underwater motions need a version-66 layout or a converter.
- MH3U's stage collision uses MH4U's format ([specs/sbc.md](../specs/sbc.md)).
- Cha-Cha (MH3U on Wii U) marks the swim state, the underwater camera and underwater carving. Its offsets must be re-found on 3DS.

The first target is the Water Arena: enter water, swim, surface, oxygen, with Sword and Shield motions, then Lagiacrus. Charge Blade and Insect Glaive never had underwater movesets, so theirs would be authored. What comes from MH3U, the leads and the unknowns: [underwater.md](underwater.md).

## Audio

Sounds and music come from each piece of content's own game and play through MH4U's sound engine by request id. The port needs no audio change.

- MH3U uses MH4U's sound classes, with the same class ids.
- MHXX uses the next generation of classes, shared with MHGU on Switch.
- MH4U's layouts come from MHGU Definitive Edition and are unverified ([specs/sound.md](../specs/sound.md)).

What the mod needs, what is known and the unknowns: [audio.md](audio.md).

## Progression

How players reach 3U and GU content is an open decision ([decisions.md](decisions.md#open)). The options range from separate hubs per game to new quest categories on MH4U's existing boards.

