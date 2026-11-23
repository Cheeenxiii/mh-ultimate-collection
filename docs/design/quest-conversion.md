# Quest conversion: MH3U and MHXX quests into MH4U

**Point:** every 3U and GU quest the mod carries is the source game's own quest, rewritten as an MH4U `.mib` (CLAUDE.md, rule 2: nothing invented where a source exists). This doc maps each source field onto MH4U's, says what each mapping needs, and lists the routes by which a converted quest could reach the game. The choices it raises (which quests, which monster versions, how progression unlocks them) belong to the open decisions (rule 6) and are written as options only.

The three layouts are in [specs/quest.md](../../specs/quest.md): MH4U `.mib` (header and sub-structures verified on 120 DLC quests), MHXX `.mib` and its parts (173 DLC quests), MH3U `QTDS` (38 DLC quests). `mhuc quest dump` reads all three into JSON, which is the converter's input.

## What a converted quest needs

Each source field falls into one of four kinds:

- **direct**: same meaning, copied (perhaps resized);
- **id table**: same meaning, but the value is an id in the source game's numbering (monster, item, map, objective type, icon) and needs a table from the source id to MH4U's, which may mean a new MH4U id ([id-tables](id-tables.md));
- **value table**: an index into a table of the source game's code (monster HP and attack rows, scale tables) whose rows differ between games; converting means reading both games' tables, not copying the index;
- **none**: no counterpart in MH4U's `.mib`, dropped or handled by a plugin, and recorded.

### Header

| MH4U `.mib` | From MH3U `QTDS` | From MHXX `.mib` | Kind |
|---|---|---|---|
| quest id (0xC0, u16) | number (u16) | quest id (0x0C, u32, 7 digits) | id table: a new MH4U id range for each source game; MH4U's DLC quests use 6xxxx, its own quests other ranges |
| stars (0xC2) | stars (u8) | stars (0x12) | direct, though star meanings differ by rank system (3U: Moga and Tanzia, low/high/G; XX: village and hub, with G rank at rank 5) |
| map (0xC4) | map (u8) | map (0x14, +100 at night) | id table: 3U and GU maps get new MH4U stage ids; night is a separate flag in XX |
| time limit (0xB4, minutes) | time (u16, minutes) | time (0x16, minutes) | direct |
| fee, reward, faint penalty (0xA4..0xAC) | fee, reward, faint penalty (i32) | fee, main reward (0x31, 0x39) | direct (economy balance is a separate question) |
| sub-quest reward (0xB0) | — (sub-quest in the objectives) | sub reward (0x3D) | direct where present |
| HR points (0x74..0x7C) | main HRP, failure HRP | HR points (0x4D, 0x51) | direct (meaning differs: MH4U's HR vs XX's HR) |
| carve table (0x8A: arena, low, high, G) | from the rank | carve and drop level (0x2E) | id table: the source rank to MH4U's four |
| gathering rank (0x89) | gathering level in the settings block | mining and fishing levels (0x2F, 0x30) | id table |
| AI level (0x8B) | enemy level (settings block) | — | value table |
| spawn area (0x8C), arena fence (0x8D) | start parameter | start area (0x15) | id table (area numbering is per map) |
| objectives ×3 (0xCC..0xE3: u32 type, u16 target, u16 count) | clear pattern, 2 objectives (u32 param with type in the low u16) and the sub objective in text | 2 main and 1 sub (u8 type, u16 target, u16 count) | id table: type codes (below) and targets (monster or item ids) |
| requirements to post or join (0xC5, 0xC6) | special flag and conditions | requirements 1 and 2 (0x1A, 0x1B) | id table, partly none |
| flags (0xA0..0xA3) | category bits (u64) | type (0x10), clear type (0x1D) | id table |
| icons (0xE8..0xF0) | — (from the monsters) | quest icons (0xD6..0xDA) | id table: icons are per monster |
| intruder chance (0xB8) | intruder block (6 bytes) | intruder chances (0xCC..0xD4) | direct for the chance; the intruder itself is a monster (below) |

Objective types share one bit-coded family between MH4U and MH3U: 0x1 hunt, 0x81 capture, 0x101 slay, 0x2 deliver (target an item) appear in both, 0x8101 (slay small) and the siege codes (0x2515, 0x4014, 0x2000) only in 3U so far, 0x204 and 0x2004 only in MH4U's DLC. MHXX uses small numbers instead (1..9 in its DLC), which need a table. Which MH4U code each 3U siege code becomes is open: MH4U's siege quests (Gogmazios, Dalamadur) are the place to look.

### Monsters

| MH4U | From MH3U | From MHXX | Kind |
|---|---|---|---|
| large monsters: waves of definitions (id, count, condition, area, size, frenzy, x/y/z) | 5 monster slots (type, set type, start type, number, rows, size, stamina) | 1..5 `.sem` (area, angle, x/y/z) and 5 boss blocks in the `.mib` (type, sub type, aura, tables, scale) | id table for the monster; positions: none in 3U's quest (set by type), direct from XX's `.sem` |
| monster stats ×5 (size %, size variation, health, attack, defense, stamina) | HP, attack, other rows (0..127) and a fourth row, size, size parameter, stamina | vital, attack, other table numbers, scale, scale table, stamina table | value table: each game's rows mean different multipliers |
| small monsters: areas of definitions | 2 main small monsters and the small-monster block in settings | `.esl`: areas of 36-byte entries (id, x/y/z) | id table; positions direct from XX |
| intruders (probability + definition) | intruder block | intruder chances, boss conditions | id table |
| frenzy status | — | aura type (boss block) | id table (frenzy and GU's auras are different systems) |

### Rewards and supplies

| MH4U | From MH3U | From MHXX | Kind |
|---|---|---|---|
| supply boxes (id, items: u16 item, u16 count) | supply set number (settings block: points into a supply table) | supply list (40 slots: item, count, label) | id table for items; 3U's supplies are a set number: the set's contents need finding |
| reward boxes (u16 chance, item, count) | reward tables A and B (item, count, chance) | `.rem` ×4..5 (8 flags with counts, 40 slots: item, count, chance) | id table for items; chances direct |

### Text

| MH4U | From MH3U | From MHXX | Kind |
|---|---|---|---|
| 5 languages × 7 strings (title, success, failure, summary, main monsters, client, sub-quest), UTF-16 | 5 languages × 6 strings (name, objective, sub objective, failure, client, description), UTF-8 | Japanese GMD per quest; English comes from MHGU Switch v1.4.0 (rule 2) | direct after re-encoding; MH4U's "summary" and "main monsters" are built from the source's description and monsters. MH4U's language order is English, French, Spanish, German, Italian; 3U's is English, French, German, Italian, Spanish |

### Arena and gear (3U)

3U's arena and challenge quests carry their monster sets and five gear sets (86 u16 each). MH4U's `.mib` has an equipment-presets block (offset 0xE4: eight 28-byte entries and an item). Weapons and armour are id tables, and new 3U gear needs MH4U ids first (id-tables.md, "Equipment tables").

## Routes into the game

Options, for the open decisions to settle:

1. **The game's own quest archives.** Add converted `.mib` files to `quest00.arc`/`quest01.arc` (or a new archive) and grow the quest lists (`rQuestInfoTbl`) and any quest-id bounds (id-tables.md, "Quest ids"). This fits the mod's progression (village or hub lists), but needs the table growth the plugin layer is meant for.
2. **Downloaded quests.** Write the quest into an Extra Data slot as the game stores a download: the `.mib`, its SHA-1 with two bytes zeroed, padding and the size (the 28 bytes, understood since quest.md check Q16), the name `mNNNNN.mib`. `mhuc questslot put` writes a slot in that form, and `mhuc encrypt` re-encrypts the file byte-exactly. No tables grow; what's left is the in-game check Q17, and the event-quest list may limit how many quests show (40 slots per file, 5 files: 200 at most). [extra-data](extra-data.md) sets this route beside the Palico and guild-quest ones.
3. **A local DLC responder.** Serve converted quests to the game's own DLC screen, as Cha-Cha does for MH3U on Wii U ([cha-cha](../sources/cha-cha.md)). MH4U's server format is now known (standard Blowfish, quest.md Q9), so the game stores them itself. It needs the port to answer the game's HTTP requests, through the plugin layer or the runtime: [dlc-responder](dlc-responder.md) gathers the protocol and what's open.

Routes 2 and 3 suit event-style quests; route 1 suits quests woven into progression. They can coexist.

## What blocks a first converted quest

In order of dependence:

1. Monster ids for the quest's monsters in MH4U (an existing MH4U monster first: a 3U quest whose monsters MH4U already has, so no new monster is needed).
2. The map: a 3U quest needs its own map in MH4U, so a faithful 3U quest waits for the first converted stage. A test may run it on an MH4U map meanwhile, recorded as a placeholder, never shipped. GU is different: four of its locales are MH4U's own (Ancestral Steppe, Frozen Seaway, Primal Forest, and the wiki's "Dunes", MH4U's Old Desert), with the special locales Castle Schrade, Ingle Isle, Polar Field, Sanctuary and Slayground ([overlap.md](../../data/catalog/overlap.md)).
3. Item ids for rewards and supplies (MH4U's own items where the item exists in both games, by name from the GMD texts).
4. The value tables for monster HP and attack (read from both games' code in the reference recompiles), or MH4U's defaults for a first test, recorded as a placeholder.
5. One route above, checked in game with a procedure in docs/checks/.

**The cheapest first quest** is therefore a GU (MHXX) quest set on one of those shared locales whose large monsters are among the 46 MH4U also has (overlap.md lists them): no new monster and no new map, only the id tables for monsters, the map, items and objectives. Which quest, and whether the GU or MH4U version of a shared monster is used, belongs to the open decisions.

The writer side exists: `mibwrite.mib4_build` lays out a `.mib` from a model (header, texts, raw list entries) and recomputes every offset; it round-trips all 120 DLC quests (quest.md Q18). A converter fills that model, or its JSON form (`mhuc mib export`/`import`), which is also how a quest can be edited by hand. Whether the game takes the builder's layout is check Q19.

**The converter exists for MHXX** (`mhuc convert quest --from mhxx`, tools/mhuc/convert.py): it takes a quest as `mhuc quest dump mhxx` prints it, an MH4U template quest (`mhuc mib export`) and the five languages' texts, and writes the MH4U model JSON that `mhuc mib import` builds. It copies stars, time, fee and rewards; maps the map, monsters (by the `.sem` file names and `.esl` bytes), areas and items through the id tables in [data/idmap/](../../data/idmap/README.md), which ship empty; takes positions as they are (an assumption that holds only on a shared stage); and refuses any quest with an unmapped id, listing them all. Everything it can't convert yet (objectives, faint penalty, HR points, carve table, flags, presets, intruders, the unknown bytes of each definition) comes from the template and is listed in the result's `placeholders`, to be recorded in docs/sources/authored-register.md before anything ships. 3U quests need their stage data first (monster placement isn't in `QTDS`), so `--from mh3u` waits for that.
