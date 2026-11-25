# Quests

Every 3U and GU quest in the mod is the source game's own quest, rewritten as an MH4U `.mib` (rule 2). This page maps each source field onto MH4U's, describes the three routes into the game, and says what a first converted quest needs.

Progression is one story whose key quests come from all three games ([decisions.md](decisions.md#0007-progression)); which quests each rank takes is authored work.

## What exists

- **Readers:** `mhuc quest dump` reads all three formats into JSON. Layouts: [specs/quest.md](../specs/quest.md).
- **Writer:** `mibwrite.mib4_build` lays out an MH4U `.mib` from a model. It round-trips all 120 DLC quests (check Q18). Whether the game accepts its output is check Q19 ([checks.md](checks.md)).
- **Converter:** `mhuc convert quest --from mhxx` exists. MH3U waits for stage data, because `QTDS` doesn't hold monster positions.
- **Id tables:** [data/idmap/](../data/idmap/README.md) ships empty, so nothing converts yet without the maintainer's tables.

## Four kinds of field

| Kind | Meaning |
|---|---|
| direct | same meaning, copied, maybe resized |
| id table | same meaning, but the value is an id in the source game's numbering |
| value table | an index into a game table whose rows differ between games |
| none | no MH4U counterpart: dropped or handled by a plugin, and recorded |

An id table may need a new MH4U id ([reference/README.md](../reference/README.md#mh4u-monster-tables)). A value table means reading both games' tables, not copying the index.

## Field map

Offsets are MH4U `.mib` offsets unless stated.

### Header

| MH4U field | From MH3U | From MHXX | Kind |
|---|---|---|---|
| quest id (0xC0) | number | quest id (0x0C) | id table (1) |
| stars (0xC2) | stars | stars (0x12) | value table (2) |
| map (0xC4) | map | map (0x14) | id table (3) |
| time limit (0xB4) | time | time (0x16) | direct |
| fee, reward, faint penalty | same three | fee, main reward | direct |
| sub-quest reward (0xB0) | none | sub reward (0x3D) | direct |
| HR points | main and failure HRP | HR points (0x4D, 0x51) | direct (4) |
| carve table (0x8A) | from the rank | carve level (0x2E) | id table |
| gathering rank (0x89) | gathering level | mining and fishing levels | id table |
| AI level (0x8B) | enemy level | none | value table |
| spawn area, arena fence | start parameter | start area (0x15) | id table |
| 3 objectives | 2 objectives and a text sub-objective | 2 main and 1 sub | id table (5) |
| post and join requirements | special flag and conditions | requirements 1 and 2 | id table, partly none |
| flags (0xA0) | category bits | type, clear type | id table |
| icons (0xE8) | none | quest icons (0xD6) | id table, per monster |
| intruder chance (0xB8) | intruder block | intruder chances | direct |

1. Each source game gets its own MH4U id range. MH4U's DLC quests use 6xxxx.
2. MH4U's stars run 1–3 Low, 4–7 High, 8–10 G (check Q20). 3U's run 1–8 across all ranks (Q21). MHXX has village and hub stars, with G rank at rank 5. Which source star becomes which MH4U star is a decision.
3. 3U and GU maps need new MH4U stage ids. MHXX adds 100 for night. MH4U keeps night as a separate flag.
4. The meaning differs: MH4U's HR is not MHXX's HR.
5. MH4U and MH3U share bit-coded objective types: 0x1 hunt, 0x81 capture, 0x101 slay, 0x2 deliver. Only 3U has 0x8101 (slay small) and the siege codes 0x2515, 0x4014 and 0x2000. Only MH4U's DLC has 0x204 and 0x2004. MHXX numbers its types 1 to 9 and needs a table. Which MH4U code each 3U siege code becomes is open: MH4U's siege quests (Gogmazios, Dalamadur) are where to look.

### Monsters

| MH4U field | From MH3U | From MHXX | Kind |
|---|---|---|---|
| large monster waves | 5 monster slots | `.sem` files and 5 boss blocks | id table |
| positions | none (set by type) | `.sem` x/y/z | direct from MHXX |
| stats: size, health, attack, defense, stamina | HP, attack and other rows, size, stamina | vital, attack, other tables, scale, stamina | value table |
| small monsters by area | 2 main ones and a settings block | `.esl` entries | id table |
| intruders | intruder block | intruder chances, boss conditions | id table |
| frenzy | none | aura type | id table (6) |

6. Frenzy and GU's auras are different systems.

**Stat tables.** MH4U's table is `em_nando_tbl`: 32-byte rows of floats (HP, attack, defense and five statuses), picked by the quest's stat bytes at 0x34. Source: MHGU Definitive Edition, which found it at 0xF3A330 in the European v1.1 code. The USA v1.3.0 address is still to find. MHGU's table of the same name holds most of MH4U's rows under the same numbers, but not all.

### Rewards and supplies

| MH4U field | From MH3U | From MHXX | Kind |
|---|---|---|---|
| supply boxes | a supply set number | supply list (40 slots) | id table (7) |
| reward boxes | reward tables A and B | `.rem` files | id table; chances direct |

7. 3U's supplies are a set number pointing into a table. That table's contents still need finding.

### Text

| MH4U field | From MH3U | From MHXX | Kind |
|---|---|---|---|
| 5 languages × 7 strings, UTF-16 | 5 languages × 6 strings, UTF-8 | Japanese GMD; English from MHGU Switch | direct after re-encoding |

- MH4U's "summary" and "main monsters" strings are built from the source's description and monsters.
- Language order differs. MH4U: English, French, Spanish, German, Italian. 3U: English, French, German, Italian, Spanish.

### Arena gear (3U)

3U's arena and challenge quests carry five gear sets of 86 u16 each. MH4U's `.mib` has an equipment-presets block at 0xE4: eight 28-byte entries and an item. Weapons and armour are id tables, and new 3U gear needs MH4U ids first.

## Routes into the game

| Route | Fits | Needs |
|---|---|---|
| 1. The game's quest archives | quests woven into progression | growing the quest lists and id bounds (plugin layer) |
| 2. An Extra Data slot, as a download | event-style quests | check Q17; at most 200 quests (5 files × 40 slots) |
| 3. A local DLC responder | event-style quests | the port answering the game's HTTP requests |

The routes can coexist.

- **Route 1** adds `.mib` files to `quest00.arc` or `quest01.arc`, or a new archive, and grows `rQuestInfoTbl` ([reference/README.md](../reference/README.md#mh4u-monster-tables)).
- **Route 2** stores the quest as the game stores a download: the `.mib`, its SHA-1 with two bytes zeroed, padding, the size, and the name `mNNNNN.mib` (check Q16). `mhuc questslot put` writes the slot, and `mhuc encrypt` re-encrypts the file byte-exactly. Details below, in "Extra Data records".
- **Route 3** serves quests to the game's own DLC screen, as Cha-Cha does for MH3U on Wii U. MH4U's server format is known (standard Blowfish, check Q9). Details below, in "A local DLC server".

## What blocks a first converted quest

In order:

1. **Monster ids.** Start with a quest whose monsters MH4U already has.
2. **The map.** A 3U quest needs its own map, so it waits for the first converted stage. A test may use an MH4U map as a recorded placeholder, never shipped. Four GU locales are MH4U's own: Ancestral Steppe, Frozen Seaway, Primal Forest and the Dunes (MH4U's Old Desert). See [overlap.md](../data/catalog/overlap.md).
3. **Item ids** for rewards and supplies, matched by name from the GMD texts.
4. **The stat tables**, read from both games' code. MH4U's defaults can stand in for a first test, recorded as a placeholder.
5. **A route**, checked in game with a procedure in [docs/checks/](checks.md).

**The cheapest first quest** is an MHXX quest on a shared locale whose large monsters are among the 46 that MH4U also has. It needs no new monster and no new map: only the id tables for monsters, the map, items and objectives.

## The MHXX converter

`mhuc convert quest --from mhxx` (`src/mhuc/quests/convert.py`) takes three inputs:

- the quest, as `mhuc quest dump mhxx` prints it;
- an MH4U template quest, from `mhuc mib export`;
- the five languages' texts.

It writes the MH4U model JSON that `mhuc mib import` builds into a `.mib`.

| Field | What the converter does |
|---|---|
| time, fee, rewards | copies them |
| stars | leaves them to the template, since the scales differ |
| map, monsters, areas, items | maps them through `data/idmap/` |
| positions | copies them, which is right only on a shared stage |
| anything unmapped | refuses the quest and lists every missing id |

Objectives, faint penalty, HR points, carve table, flags, presets, intruders and unknown bytes all come from the template. The result lists them under `placeholders`. Each one must go in the [authored register](sources.md#authored-register) before anything ships.

## Extra Data records

MH4U loads whole records from its Extra Data, the save area where downloaded content lands. All three kinds below can be read, written in the exact form the game stores them, and re-encrypted byte for byte (check E5), so whatever the game rejects will be the content, not the container. None has been tried in the game yet (checks Q17, Q19, E4).

| Kind | Where | Capacity | Stored form | Tool |
|---|---|---|---|---|
| quest (`.mib`) | `quest1` to `quest5`, 0x2010-byte slots | 40 per file, 200 in all | the `.mib`, its SHA-1 with bytes 0 and 1 zeroed, padding, size; the name at 0x2000 (Q16) | `mhuc questslot` |
| DLC Palico (`.otb`) | `otomo1`, 0x90-byte slots | 9 | the record padded to 0x80, then a hash byte at 0x8F; the full tail only after the last slot (E6) | `mhuc extdata ... otomo` |
| guild quest | `card1` to `card3`, 304-byte records | 150 | mhff's layout, unverified: no record in the maintainer's data | `mhuc extdata dump card` |

What each could carry:

- **Quests:** converted quests whose monsters and maps MH4U has. Extra Data quests appear as event quests, so this suits event content, not quests woven into progression.
- **Palicos:** a record names skills, looks and colours by id. A GU-era Palico needs MH4U ids for them. Nine slots cap it.
- **Guild quests:** they name monsters by a one-byte id and maps by id, with a level that scales the monsters. If the game accepts an edited one, it is a cheap way to put a monster on a map at a chosen level.

The maintainer's Palico files are the `_ger` ones: that Extra Data may come from a European game or a German-language system, while the base is MH4U USA v1.3.0. Quests are identical in both regions (Q9).

In the port, Extra Data is the runtime's SD extdata folder. The fork's `tools/extdata_path.py` prints where Azahar keeps it ([checks.md](checks.md), "Extra Data in the port").

## A local DLC server

MH4U still has its DLC screen. If the port answered the requests that screen makes, the game would download mod quests itself and store them in Extra Data in its own form. The protocol below comes from goshawk (a replacement DLC server, AGPL-3.0), mhff's notes and mhef's cipher. None of it is checked against MH4U's code yet (check D1).

| Step | Request | Reply | Status |
|---|---|---|---|
| login | `POST https://<server>/SSL/3ds/mh4g_us/login.cgi` (Europe: `mh4g_eu`) | raw bytes: u16 BE key length, the Blowfish key in Shift-JIS with a NUL, u16 BE URL length, the base URL of the files | unverified |
| lists | `GET <base>/DLC_*.txt`, per kind and language (`DLC_EventQuestInfo_eng.txt`…) | Shift-JIS text, encrypted like the quests presumably; plain format undocumented (check D2) | unknown |
| files | `GET <base>/m60001.mib`, `ot001_eng.otb`… | the file encrypted with the login key: Blowfish over the plaintext and its SHA-1, then the size | cipher verified (Q9), route unverified |

- **The key is the server's to choose.** The game takes whatever key the login reply carries, so a local server could use its own key, and no Capcom key would be needed or shipped. This holds only if MH4U doesn't check the key against its own (D1).
- **A downloaded quest is stored as Q16 describes,** so it ends up identical to one written by `mhuc questslot put`. This route only replaces the copying step.

A server needs to catch the game's HTTPS requests (inside the port's HTTP service, or through a local server the runtime's DNS points at, with the certificate check passed or skipped), serve the list files, and use quest ids no official DLC uses: event quests use 60000 to 69999 (Q5), and 60999 and 61000 are the test kit's. goshawk's code can't be copied into this GPL-3.0 project, so a server would be written from the protocol.
