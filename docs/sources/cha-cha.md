# Cha-Cha: what it offers this project

[BoyClinton/Cha-Cha](https://github.com/BoyClinton/Cha-Cha) (GPL-3.0) is a static recompilation of **MH3U for Wii U** (US, update v32) to native C++ for Windows, Linux and Android, on its own reimplementation of the Wii U system libraries, with Vulkan graphics and SDL3 input and audio. It ships no game data. Read on 2026-11-23 at the commit then on its default branch.

## How it relates to our sources

- **Fidelity.** Our MH3U source is the **3DS** release (CLAUDE.md, rule 2). Cha-Cha is the Wii U build of the same game. Content matches where checked: the DLC quest files are byte-identical on 3DS and Wii U (specs/quest.md, Q10), and the class registries agree on names and ids, with sizes that differ slightly (`rQuestData` 0x930 on 3DS, 0x938 on Wii U). So Cha-Cha's **documentation** (formats, class names, behaviour, field meanings) is a strong lead for the 3DS. Its **addresses and offsets** are PowerPC and Wii U-specific: each one has to be re-found in the 3DS code before we rely on it. Nothing of the Wii U build's own assets is a source for the mod.
- **Byte order.** Wii U files are big-endian, 3DS files little-endian: the same magics appear reversed (`SDTQ` and `QTDS`, `\0SFX` and `XFS\0`).
- **Licence.** GPL-3.0 like both our repositories. So far we have taken facts and formats only, credited in specs/README.md, and no code.

## What it gives us

| Area | What Cha-Cha has | Use for us | Taken so far |
|---|---|---|---|
| DLC | the wire format and MtCipher, MT's Blowfish variant (`runtime/os/dlc_server.cpp`); a local DLC responder that feeds the game's own DLC screen | MH3U DLC decryption, done (quest.md Q14). The responder is a pattern the MH4U port could follow to serve mod quests through MH4U's own DLC screen: its DLC crypto (standard Blowfish, known key), its quest form and its Extra Data slots are all now specified. That is a design option for the plugin layer, not a decision | Q14 |
| Formats | `docs/formats/`: ARC (Wii U v16), TEX (Wii U 0xA5), XFS, shaders, an inventory of every file type with its class | XFS, done (specs/xfs.md, `mhuc xfs`). The inventory names the classes behind loose files (`.quest_btl` is `rQuestBattleData`, `.supp` is `rSuppItem`, `.list` is `rQuestList`) | specs/xfs.md, quest.md |
| Class registry | `config/dti.csv`: 1,251 classes with DTI, parent, size, id, vtable | cross-checks our 3DS registry (fork `config/games/mh3u/mt_classes.tsv`); same ids | quest.md |
| Function names | `config/symbols.txt` (about 36,000 symbols, almost all generated from the DTI: per-class virtual slots such as `rQuestBattleData::load`), `virtuals.csv` (26,237 rows), `functions.csv` | names for our MH3U 3DS reference recompile: a class's virtual slot *n* is the same method on both builds, so names can be carried across by class and slot through our own DTI and vtable recovery, with no address matching | — |
| Underwater | the swim state in the player's pad block (Wii U: +0x3D = 3 under water), the camera's underwater mark and its separate pitch input, carving under water (a carve spot of kind 6, 4 on land) | starting points for underwater.md's "Swim state" and "Camera" rows and for reference-recompiles step 4 | — |
| Gameplay | quest supply box layout (40 cells of 4 bytes), carving and gathering spots, quest unlock checks ("key quest markers"), delivery handling | field meanings for quest and item data when we convert 3U quests | — |
| Engine notes | `docs/engine.md`: MT Framework Lite on Wii U: DTI, virtual slots, static constructors, resource loading, allocators | comparison with MT Framework Mobile on 3DS (MH4U, MHXX) and with our recompiler's notes | — |
| Runtime | PowerPC recompiler, Vulkan renderer, SDL3 input and audio, overlay file system, texture packs, Android | for the engine fork's maintainers to compare with MH4UltimateDC's ARM recompiler and runtime; no direct reuse planned | — |
| Mods | item sets (GU style), quest HP scaling, a free camera, auto carving, instant gathering, quest markers; planned: a quest maker and online lobby | ideas only: the combat base and runtime choices are the maintainer's open decisions (CLAUDE.md, rule 6) | — |

## Next steps it suggests

1. **Names for the MH3U recompile** (fork): carry Cha-Cha's class-and-slot names onto our 3DS vtables. It's a script over two CSV files plus our DTI tables, checkable by counting how many slots line up. Credit Cha-Cha in the fork's config.
2. **Underwater studies** (STATUS task 6): start from Cha-Cha's swim mark and camera code paths, find the 3DS equivalents in the MH3U recompile, and cite both.
3. **`.quest_btl`**: `rQuestBattleData::load` (Wii U 0x02074174) and its 3DS counterpart, found through the shared vtable slot, give the file layout.
