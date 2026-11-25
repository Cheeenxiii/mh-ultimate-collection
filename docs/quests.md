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

## Where Great Wroggi can fight

Great Wroggi is MH3U's, and none of the maps it fights on is MH4U's. From the 365 `QTDS` records of the MH3U RomFS's `/quest/us/` (check Q23), seven field it:

| MH3U quest | Rank | Map | Great Wroggi | Other large monsters | Main small monsters |
|---|---|---|---|---|---|
| Toxic Troublemaker (1307) | ★3 | Flooded Forest | 1 | — | Wroggi, Ludroth |
| Toxic Troublemaker (1616) | ★6 | Flooded Forest | 1 | — | Wroggi, Fish |
| [Canteen] The Endless Hunt (1811) | ★8 | Flooded Forest | 1 | Gobul, Lagiacrus | Wroggi, Fish |
| Supply Constraints (11317) | ★3 | Flooded Forest | 2 | — | Wroggi, Fish |
| Supply Constraints (11608) | ★6 | Flooded Forest | 2 | — | Wroggi, Epioth |
| [Advanced] Forest Fracas (11657) | ★6 | Flooded Forest | 1 | Gobul, Plesioth | Slagtoth, Altaroth |
| Best of Enemies (11820) | ★8 | Land Arena | 1 | Volvidon, Purple Ludroth, Steel Uragaan | — |

The six Flooded Forest quests share the ten-area locale ([maps.csv](../data/catalog/maps.csv)); the Land Arena is a special locale. Five quests field one Great Wroggi and two field two, and five pair it with the Wroggi. The 38 quests the player downloaded (Extra Data, check Q12) add none. A `QTDS` record holds the quest's map but no area or position for a monster, so the dump gives the map only.

**The first quest.** Great Wroggi's first quest is a test on a shared map, as "What blocks a first converted quest" allows: it is MH3U's Toxic Troublemaker (1307), built with **MH4U quest 10110 "Field Trip"** as its template — a Hall ★1 hunt on Ancestral Steppe. The template hunts one Great Jaggi (id 15) in **area 6**, with Jaggi (id 56) in areas 3, 4, 6 and 8 and Jaggia (id 57) in areas 4 and 9, and a sub-objective (type 0x204) whose target is the Great Jaggi. Building Great Wroggi's quest from it changes the large-monster definition's monster id from 15 to Great Wroggi's own id from [data/ids/registry.csv](../data/ids/README.md) — the next free one after 124 and 125, with Great Jaggi as its stand-in (#166) — and the sub-objective's target from 15 to the same id. So the first quest uses **Ancestral Steppe, area 6 for Great Wroggi and areas 3, 4, 6, 8 and 9 for the pack**, and the template's positions: an MH3U `QTDS` record has none.

Ancestral Steppe is chosen because it is the shared map whose Hall quest fields Great Jaggi, the MH4U monster of Great Wroggi's family and the port's stand-in, so the first quest's areas and pack are the game's own. Primal Forest has the closer habitat (forests, swamps, like the Flooded Forest) but no MH4U quest there fields Great Jaggi, so its pack's areas would be authored; the six MH3U quests wait for the Flooded Forest's own conversion.

**The Wroggi.** Five of the seven MH3U quests pair Great Wroggi with the Wroggi, but the Wroggi has no MH4U id yet, so MH4U's Jaggi (56) and Jaggia (57) stand in for it in the template's five areas. The Ludroth that 1307 also fields has no MH4U counterpart either, so the first quest keeps the template's one pack. When the Wroggi is ported, its id replaces 56 and 57 in those definitions and the sub-quest's text becomes its own. That is left undone.

## Where a ported monster fights: Giadrome

A ported monster's first quest goes where its own game already puts it, on a locale MH4U has. GU's Giadrome is MHXX's `em034`. The locale names are in [maps.csv](../data/catalog/maps.csv), and which of them MH4U has in [overlap.md](../data/catalog/overlap.md).

### The MHXX quests that field it

The game's own 1,331 quest archives (MHXX JPN v1.0's RomFS; the v4.8.0 update patches none of them) hold 1,331 `.mib`, 3,474 `.sem` and 2,426 `.esl`, all read with the layouts of checks Q2, Q11 and Q15 without a failure. **21 of them carry Giadrome in the boss set**, and the `.sem` entries and the `.mib`'s five boss blocks give the same 21. Six hunt it; 15 field it as an extra large monster. MHXX's DLC quests are not in this dump and are not counted. The titles below are the dump's Japanese; the English ones wait for MHGU's text (rule 2).

| Map | Quest | Rank | Giadrome in | Hunt |
|---|---|---|---|---|
| Arctic Ridge | q0000705 商売ガタキのドスギアノス | High | area 7, with Giaprey | yes |
| Arctic Ridge | q0000934 ベリオロスを捕獲せよ！ | High | area 7 | extra |
| Arctic Ridge | q0010434 強敵、ドスギアノス現る！ | High | area 7, with Giaprey | yes |
| Arctic Ridge | q0011105 ドスの威信を賭けた戦い | G | area 7, with Giaprey | yes |
| Arctic Ridge | q0011122 雪山の採集ツアー | G | area 7, with Giaprey | extra |
| Arctic Ridge | q0011213 ……欲するならば資格を示して | G | area 7 | extra |
| Arctic Ridge, night | q0000708 氷雪に舞う白うさぎ | High | area 7 | extra |
| Arctic Ridge, night | q0000726 雪山の採集ツアー | High | area 7 | extra |
| Arctic Ridge, night | q0000805 フルフルのまごころ診療所 | High | area 7 | extra |
| Arctic Ridge, night | q0000810 ホワイトアウト | High | area 7 | extra |
| Arctic Ridge, night | q0011108 氷雪に舞う白うさぎ | G | area 7 | extra |
| Arctic Ridge, night | q0011208 身体の芯までビッリビッリ | G | area 7 | extra |
| Arctic Ridge, night | q0100802 冷血なるドスギアノス！ | High | areas 7 and 6, with Giaprey | yes, 2 |
| Frozen Seaway | q0000831 狩人のための舞台～氷海～ | High | area 2 | extra |
| Frozen Seaway | q0000928 ガムートの強さは世界一 | High | area 2 | extra |
| Frozen Seaway | q0011207 閃きへの１ピースを求めて | G | area 2 | extra |
| Frozen Seaway | q0011304 氷牙竜・ベリオロス！ | G | area 2 | extra |
| Frozen Seaway | q0101004 スノーフェスティバル | High | area 2, with Giaprey | yes |
| Frozen Seaway | q0111402 雪に紛れしドスギアノス | G | areas 2 and 5, with Giaprey | yes, 2 |
| Arena | q0011241 子分の自覚が足りないっチャ！ | G | area 1 | extra |
| Arena | q0101005 怒濤のドスラッシュ！ | High | area 1 | extra |

The six hunts are q0000705, q0010434 and q0011105 (Arctic Ridge), q0100802 (night), and q0101004 and q0111402 (Frozen Seaway). Giaprey are MHXX's small monster id 15, which a slay quest names as `0x100F`; they stand in Giadrome's area in seven of the 21, and in all six hunts.

### The MH4U map and areas

Of the locales [overlap.md](../data/catalog/overlap.md) lists as MH4U's, the Frozen Seaway is the one MHXX fields Giadrome on: map 14 there (氷海, the name the quests' titles use), MH4U's map 4. Giadrome stands in area 2 in every MHXX Frozen Seaway quest, and in area 5 in the one with two of them.

So the first quest uses the Frozen Seaway: **area 2**, one Giadrome; the two-Giadrome MHXX quest uses areas 2 and 5. The Arctic Ridge (map 3; 103 at night), where 13 of the 21 quests are, is one MH4U does not have ([overlap.md](../data/catalog/overlap.md): to add), so those quests wait for its port. The two Arena quests are arena quests (map 9, one area), not field quests, and the Polar Field has no MHXX Giadrome quest.

### The MH4U quest it is built from

**10210, "Snow with Occasional Lagombi"** (Hall, Low Rank ★2, `quest01.arc`): the Frozen Seaway (map 4), one Lagombi (id 47) in area 2, a hunt objective targeting 47, and two Felyne groups (id 65) in area 2's small-monster list. It is the same Hall Low Rank ★2 list as 10212, the quest [#144](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/144)'s headless proof starts, and it is the same map the converted Giadrome quests will use.

To make it the first Giadrome quest, the large-monster definition's id 47 and the first objective's target 47 become Giadrome's id, the next free one in `data/ids/registry.csv` from 124 up that [#161](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/161) gives it (126 while Great Wroggi's row is not in). `mhuc mib export` and `mhuc mib import` make that one-field edit on the `.mib`, and the patched quest is what the headless proof runs. 10212's Rathian is changed to id 125 the same way.

For a converted MHXX quest the id changes on the source side: Giadrome's `em034` row in [monster.csv](../data/idmap/mhxx-mh4u/monster.csv) points at the registry id, with [map.csv](../data/idmap/mhxx-mh4u/map.csv) `14`→`4` and [area.csv](../data/idmap/mhxx-mh4u/area.csv) `14:2`→`4:2` (and `14:5`→`4:5`). The two-Giadrome q0111402 then needs no new map or stage.

### The pack, and what stands in

Giaprey are a small monster MH4U does not have ([overlap.md](../data/catalog/overlap.md): "Small monsters to add"), and this milestone ports the large monster only. So **MH4U's Jaggi (id 56) stand in for the pack**: the two area-2 Felyne groups become Jaggi groups. Porting Giaprey is left to a task of its own.

While Giadrome's own files are incomplete, its registry row's stand-in does the work: **MH4U's Great Jaggi (id 15)**, as [#161](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/161) records. Every kind of file the port does not ship yet — sound, effects, camera, `.emd`/`.etd` data and the motion slots it keeps — comes from Great Jaggi, and each kind it ships from its own folder ([monster_ids](../mods/monster_ids/README.md)). The first quest's rank, stat rows and texts stay 10210's as placeholders; it is not shipped, and the first shipped quest is a converted MHXX one.


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
