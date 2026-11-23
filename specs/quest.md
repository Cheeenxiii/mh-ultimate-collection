---
class: rQuestData, rSetEmMain, rEmSetList, rRem, rGUIMessage
extension: mib, sem, esl, rem, gmd
games: MH4U (mib), MHX/MHXX (sem, esl, rem, mib), MH3U (quest, quest_btl, supp)
status: unknown
---

# Quest files (partial)

How a quest is put together differs between the games, and the mod needs to translate 3U and GU quests into MH4U's form. This spec records what is known and what isn't.

| File | Class | Game | What it holds |
|---|---|---|---|
| `.mib` | rQuestData | MH4U, MHX/MHXX (rGuestQuestData) | the quest: map, monsters, objectives, rewards, text ids |
| `.sem` | rSetEmMain | MHX/MHXX | monster placement for a quest (large monsters) |
| `.esl` | rEmSetList | MHX/MHXX | small-monster sets per area |
| `.rem` | rRem | MHX/MHXX (rGuestRemData) | reward tables |
| `.gmd` | rGUIMessage | MH3U, MHXX | quest name, client, description (see [gmd](gmd.md)); MH4U has no GMDs |
| `.quest` | ? | MH3U | loose files under `/quest/us/` (365), magic `QTDS` |
| `.quest_btl` | rQuestBattleData | MH3U | loose files under `/quest/btl/` (353), magic `QTDB` |
| `.supp` | rSuppItem | MH3U | loose files under `/quest/support/` (196), magic `XFS\0`: [XFS](xfs.md), MT's self-describing serialised objects |

Class names and extensions come from mhff's table. MH4U's registry (MH4UltimateDC `config/mt_classes.tsv`) has `rQuestData` and `rQuestInfoTbl` but no `rSetEmMain`, `rEmSetList` or `rRem`: in MH4U the monster sets and rewards live inside `.mib`.

## rQuestData (MH4U .mib)

### Where quests live

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | arc | the game's own quests: all `.mib` in two archives, `/loc/data/quest00.arc` (207) and `quest01.arc` (301), nothing else in them | verified | ours; check Q1 |
| file | mib | a DLC quest as served by Capcom's server (MH4U USA and EUR) is one bare `.mib` named `mNNNNN.mib` after its quest id, with no ARC around it (mhff's convert_quest.py describes an ARC: not so for these) | verified | ours; check Q9 |
| file | mib | the EUR server's 120 quest files are byte-identical to the USA server's | verified | ours; check Q9 |
| whole | bytes | the server's DLC files: Blowfish on byte-swapped 32-bit words over the plaintext plus its SHA-1, zero-padded to 8 bytes, then the plaintext-plus-hash size as a u32 (mhef `DLCCipher`, the NA/EU key) | verified | svanheulen/mhef; mhff wiki "MH4U DLC Encryption"; check Q9 |
| file | extdata | downloaded quests are kept in Extra Data, in five files `quest1`..`quest5` of 328,704 bytes each, beside `card1`..`card3`, `cardbox` and `otomo1` (specs/extdata.md) | verified | ours; check Q3 |
| whole | bytes | every Extra Data file, and the save's `system`, is encrypted: mhef's `SavedataCipher` (MH4G) decrypts all of them with a matching checksum, in mode "quest" for `quest*`, "card" for `card*` and "normal" for the rest | verified | svanheulen/mhef; ours, check Q4 |
| quest file | slots | a decrypted `quest*` file is 40 slots of 0x2010 bytes, then 120 zero bytes; a slot is all zero (empty) or holds one bare `.mib` from its offset 0 (no ARC around it): the server's decrypted file, byte for byte | verified | ours; checks Q5, Q9 |
| slot, after the `.mib` | 28 bytes | the rest of the server file, decrypted up to its stated size, as MH3U stores its quests: the `.mib`'s SHA-1 with bytes 0 and 1 set to zero (20 bytes), the padding to 8 (4 bytes in all 120, since every `.mib` is a multiple of 8) left as the server file's ciphertext, then the `.mib` size + 20 as a u32 BE; then zeros up to 0x2000. `mhuc questslot check` checks it; `mhuc questslot put` writes it | verified | ours; check Q16 |
| slot 0x2000 | char[16] | the quest's file name, `m` + the quest id in five decimal digits + `.mib`, NUL-padded (`m6NNNN.mib` for every DLC quest); the `.mib` body before it ends well short of 0x2000 and is zero-padded | verified | ours; check Q8 |

### Header

Field names and the layout come from the mhff wiki's "MH4U rQuestData Format" page (Seth VanHeulen, GPL-3.0). "Verified" here means checked on the 120 DLC quests of check Q5; the game's own `.mib` files in `quest00.arc`/`quest01.arc` are not checked yet (check Q6).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | offset to the flags (always 0xA0) | verified | mhff wiki; check Q5 |
| 0x04 | char[4] | magic `v005` | verified | mhff wiki; check Q5 |
| 0x08 | u32 | offset to the supply boxes | verified | mhff wiki; check Q5 |
| 0x0C | u32 | supply-box related; as bytes it is 0,0,0,0 (67 of 120), 3,3,0,0 (51) or 1,1,0,0 (2) | unverified | mhff wiki; check Q7 |
| 0x10..0x18 | u32 ×3 | unknown (0x10 always 0; 0x14 as bytes 0,0,0,0 in 104, 1,1,0,0 in 15; 0x18 is 0 or 2) | unknown | mhff wiki; check Q7 |
| 0x1C | u32 | offset to the main reward box | verified | mhff wiki; check Q5 |
| 0x20 | u32 | offset to a second reward box (0 in 24) | unverified | mhff wiki |
| 0x24 | u32 | offset to the sub-quest reward box (0 in 69) | unverified | mhff wiki |
| 0x28 | u32 | offset to the large monsters | verified | mhff wiki; check Q5 |
| 0x2C | u32 | offset to the small monsters | verified | mhff wiki; check Q7 |
| 0x30 | u32 | offset to the intruder monsters | verified | mhff wiki; check Q5 |
| 0x34..0x5B | stats ×5 | large monster stats, 8 bytes each: u16 size percentage (0 or 50..200 in 596 of 600), then size variation, health, attack, defense, stamina, unknown. Over the 120 quests the bytes reach at most 40, 90, 119, 140, 4 and 2: table indices, not percentages | unverified | mhff wiki; check Q5, Q7 |
| 0x5C | stats | small monster stats | unverified | mhff wiki |
| 0x64..0x70 | u32 ×4 | unknown: 0x64 and 0x6C always 0, 0x68 and 0x70 never 0 | unknown | mhff wiki; check Q7 |
| 0x74 | u32 | main hunter rank points | unverified | mhff wiki |
| 0x78 | u32 | hunter rank penalty | unverified | mhff wiki |
| 0x7C | u32 | sub-quest hunter rank points | unverified | mhff wiki |
| 0x88 | u8 | unknown (0 in 111 of 120; else 1, 2, 5 or 7) | unknown | mhff wiki; check Q7 |
| 0x89 | u8 | gathering rank (1..4) | unverified | mhff wiki; check Q7 |
| 0x8A | u8 | carve table: 0 arena, 1 low, 2 high, 3 G rank (0..3 in all 120) | unverified | mhff wiki; check Q5 |
| 0x8B | u8 | AI level (1, 3, 5 or 6) | unverified | mhff wiki; check Q7 |
| 0x8C | u8 | spawn area: 0 camp, 1 random, 2 elder dragon fight | unverified | mhff wiki |
| 0x8D | u8 | arena fence: 0 off, 1 on | unverified | mhff wiki |
| 0x8F | u8 | unknown (0 in 112; else 40 to 210, multiples of 10) | unknown | mhff wiki; check Q7 |
| 0xA0..0xA3 | u8 ×4 | flags: quest type, repel, sub-quest, ship integrity (0x08). Each is a bit set: 0xA0 is one of 0x01, 0x02, 0x03, 0x04, 0x08, 0x10; 0xA1 0, 0x01, 0x02 or 0x04; 0xA2 0, 0x04, 0x40 or 0x84; 0xA3 0, 0x04, 0x08 or 0x0C | unverified | mhff wiki; check Q7 |
| 0xA4 | u32 | posting fee | unverified | mhff wiki |
| 0xA8 | u32 | main reward (zenny) | unverified | mhff wiki |
| 0xAC | u32 | reward lost per faint | unverified | mhff wiki |
| 0xB0 | u32 | sub-quest reward | unverified | mhff wiki |
| 0xB4 | u32 | time limit in minutes (1..50 in all 120) | unverified | mhff wiki; check Q5 |
| 0xB8 | u32 | intruder probability | unverified | mhff wiki |
| 0xBC | u32 | offset to the text languages | verified | mhff wiki; check Q5 |
| 0xC0 | u16 | quest id (60000..69999 for all 120 DLC quests) | unverified | mhff wiki; check Q5 |
| 0xC2 | u16 | star rank (1..10 in all 120) | unverified | mhff wiki; check Q5 |
| 0xC4 | u8 | map (19 different values, 1..17 among them) | unverified | mhff wiki; check Q7 |
| 0xC5, 0xC6 | u8 ×2 | requirements to post or join | unverified | mhff wiki |
| 0xCC | u32, u16, u16 | main objective 1: type, target id, count. Types seen: 0x1, 0x81, 0x101, 0x204 (target always a monster of the quest's waves), 0x2 (never one: an item, presumably), 0x2004 (sub only); 0x101 also targets ids outside the waves with counts of 10 to 50, small monsters presumably | unverified | mhff wiki; check Q7 |
| 0xD4 | u32, u16, u16 | main objective 2 (type 0 = none, in 91 of 120) | unverified | mhff wiki; check Q7 |
| 0xDC | u32, u16, u16 | sub objective (type 0 = none, in 68; 0x204 in 37) | unverified | mhff wiki; check Q7 |
| 0xE4 | u32 | offset to equipment and item presets (0 in 96) | unverified | mhff wiki |
| 0xE8..0xF0 | u16 ×5 | objective icon ids | unverified | mhff wiki |

### Sub-structures

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| supply box | 8 bytes | u8 box id, u8 slot count, u16 ?, u32 offset to items; the list ends at box id 0xFF | verified | mhff wiki; check Q5 (the end marker) |
| supply item | 4 bytes | u16 item id, u16 count; the box's slot count gives the number of items | verified | mhff wiki; check Q7 (every count of a non-zero item is 1..99) |
| reward box | 8 bytes | u8, u8, u16 unknown, u32 offset to items | verified | mhff wiki; check Q5 (the item offset) |
| reward item | 6 bytes | u16 probability (0xFFFF ends the list), u16 item id, u16 count | verified | mhff wiki; check Q5 (stride and end marker) |
| large monsters | u32 ×n | offsets to waves, ending at 0; each wave is a list of definitions. 109 quests have one wave, 3 two, 7 three, 1 four; a wave can be empty (9 quests have only an empty one, and the last wave of a multi-wave quest often is) | verified | mhff wiki (one list); ours, check Q7 (the waves) |
| monster definition | 0x28 bytes | u32 monster id (0xFFFFFFFF ends the list), u32 spawn count, u8 condition, u8 area, sizes, u8 frenzy, f32 x/y/z | verified | mhff wiki; check Q5 (stride, end marker, ids all < 124) |
| small monsters | u32 ×3 | offset to a list of area offsets, then two equal words; the area list ends at 0 and each area is a list of definitions (1 to 11 areas, 3 in 80 quests) | verified | mhff wiki; check Q7 |
| intruder | 0x2C bytes | u32 probability (a u16 0xFFFF ends the list), then a monster definition | verified | mhff wiki; check Q5 (stride and end marker) |
| text languages | u32 ×5 | offsets to English (or Japanese, Korean), French, Spanish, German, Italian | verified | mhff wiki; check Q7 (all five) |
| text | u32 ×7 | offsets to NUL-terminated UTF-16LE strings: title, success, failure, summary, main monsters, client, sub-quest | verified | mhff wiki; check Q7 (all 7 strings of all 5 languages decode in all 120) |
| equipment preset | 0x104 bytes | eight 28-byte equipment entries, then an item | unverified | mhff wiki |

## rQuestData (MHXX .mib) and the DLC quest archive

Field names and offsets come from the mhff wiki's "MHXX rQuestData Format" page (GPL-3.0). "Verified" means checked on the 173 DLC quests of MHXX JPN, decrypted from the goshawk mirror (check Q11); the RomFS's 1,334 quest archives (check Q2) are not checked field by field yet.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | arc | the server's DLC quests are `arc/quest/qNNNNNNN.arc` (173 for JPN), each an ARC version 0x11 of 12 to 16 entries: 1 to 5 `rSetEmMain` (`.sem`, 32 bytes each), 1 or 2 `rEmSetList` (`.esl`), 4 or 5 `rRem` (`.rem`, 184 bytes each), three entries of classes outside mhuc's table (`supp_N`, `questPlus_N`, `questLink_N`, ids 0x54539AEE, 0x26BEC21C, 0x00E0BB1C), the `_jpn` GMD, and last the `.mib` | verified | ours; check Q11 |
| file | sem count | the number of `rSetEmMain` entries is the number of boss monsters plus one in 168 of 173 | unverified | ours; check Q11 |
| whole | bytes | server files: Blowfish in CTR mode (32-bit nonce, little-endian counter) on byte-swapped words over the plaintext plus its SHA-1, then the byte-swapped nonce, then one 0x100-byte RSA signature (mhef's `DLCXCipher` has two, as for MHX); the key is the one the login reply carries | verified | svanheulen/mhef; GrenderG/goshawk; check Q11 |
| .mib size | 249 bytes | every `.mib` is 249 bytes, the end of mhff's table (0xF5 + 4) | verified | mhff wiki; check Q11 |
| 0x00 | char[4] | magic (the same 4 bytes in all 173) | verified | mhff wiki; check Q11 |
| 0x04, 0x08 | u32 ×2 | count (1), index (0) | verified | mhff wiki; check Q11 |
| 0x0C | u32 | quest id: the archive's number in all 173; decimal digits A (1 = DLC, all 173), B (1 = Palico quest, 34), C (type: 1 or 2 here), then 4 digits. mhff's reading of those as star and number doesn't match the star byte | verified | mhff wiki; check Q11 (id and digit A) |
| 0x10 | u8 | type: 0 hunt, 1 slay, 2 capture, 3 deliver, 4 hunt-a-thon, 5 marathon (0..5 seen) | unverified | mhff wiki; check Q11 |
| 0x11 | u8 | village (9 or 10 here) | unverified | mhff wiki |
| 0x12 | u8 | star (2..14 here) | unverified | mhff wiki |
| 0x13 | u8 | rank (1, 3 or 5 here; mhff lists 0, 1, 3, from MHX) | unverified | mhff wiki; check Q11 |
| 0x14 | u8 | map, +100 at night (10 of 173 at night) | unverified | mhff wiki |
| 0x15..0x17 | u8 ×3 | start area, time (50 in 172), faints allowed (3 or 9) | unverified | mhff wiki |
| 0x1A..0x1E | u8 ×5 | requirements 1 and 2, entry type, clear type (0, 1, 2), repel HP percent | unverified | mhff wiki |
| 0x1F | u8, u16, u16 | main objective 1: type, target id, count (unaligned) | unverified | mhff wiki |
| 0x24 | u8, u16, u16 | main objective 2 (type 0 in 160) | unverified | mhff wiki |
| 0x29 | u8, u16, u16 | sub objective (type 0 in 111) | unverified | mhff wiki |
| 0x2E..0x30 | u8 ×3 | carve and drop, mining, fishing levels | unverified | mhff wiki |
| 0x31..0x51 | u32 ×9 | fee, village points, main and sub rewards, academy points (×3), HR points (×2); all unaligned | unverified | mhff wiki; check Q11 (fee and reward in range) |
| 0x55..0x63 | mixed | reward lot settings; supply deliveries 1 and 2: label, type (0 none, 1 timed, 2 hunt, 3 deliver, 4 sub-quest), target id, count | unverified | mhff wiki |
| 0x64 | 13 bytes ×5 | boss monsters 1..5: u16 monster type first (below 0x200 in 825 of 865 blocks: the 13-byte block or its fields don't fit all), sub type, aura, restore count, vital/attack/other tables, difficulty, scale, scale and stamina tables | unverified | mhff wiki; check Q11 |
| 0xA5..0xA7 | u8 ×3 | small monster HP, attack, other | unverified | mhff wiki |
| 0xA8..0xCB | mixed | enemy-set 2 and 3 conditions; boss 1..5 appearance conditions (type, target, count) | unverified | mhff wiki |
| 0xCC..0xD5 | u8 ×10 | intruder chances and extra-time settings | unverified | mhff wiki |
| 0xD6..0xDA | u8 ×5 | quest icons | unverified | mhff wiki |
| 0xDB | u32 | "prog number" | unverified | mhff wiki |
| 0xDF | u32 | message reference: the class id of `rGUIMessage` in all 173 | verified | mhff wiki; check Q11 |
| 0xE3 | char[] | then the quest id and `_jpn` (11 characters, NUL-terminated): the stem of the archive's own GMD | verified | mhff wiki; check Q11 |
| 0xF1, 0xF5 | u32 ×2 | `mVillagePointG?`, `mFlag?` | unverified | mhff wiki |

## MH3U quests (.quest, QTDS)

The cipher comes from BoyClinton's Cha-Cha (`runtime/os/dlc_server.cpp`, GPL-3.0), an MH3U Wii U recompilation that serves the game its DLC locally. The `QTDS` layout comes from Matt-Wood-23's mh3u-quest-studio (`questlib/quest_format.py`, MIT), written for the Wii U version; ArmoredRaven17's mh3u-quest-randomizer (`scripts/build_data.py`, MIT) gives the same tail offsets. "Verified" means checked on the 38 USA DLC quests in the maintainer's own MH3U 3DS Extra Data, which the game stores in the clear (checks Q10, Q12). The RomFS's 365 `.quest` files are not checked yet (Q13).

### Where quests live

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | quest | the server's DLC quests are `q_NNNNN.quest`: 38 in the USA folder (`mh3gu_us`), the same 38 byte for byte in EUR (`mh3gu_eu`) and on Wii U (`mh3ghd_us`); 47 for Japan's MH3G (`mh3g`) | verified | GrenderG/goshawk; check Q10 |
| whole | bytes | server files: MT Framework's own Blowfish variant (MtCipher) in ECB mode over the record plus its SHA-1, zero-padded to 8, then the record-plus-hash size as a u32 BE. MtCipher differs from standard Blowfish in two ways: each 8-byte block is two little-endian words, and its S-box schedule advances one entry per encryption while writing two, so every entry ends up as the left half of successive encryptions. P and S start from the standard digits of pi | verified | Cha-Cha `runtime/os/dlc_server.cpp`; ours, check Q14 |
| key | — | the key is the one the login reply carries: goshawk's MH3G key (`BLOWFISH_KEY_TYPE_1`, not copied here) decrypts all 38 USA and all 47 Japanese MH3G files, every SHA-1 matching. Standard Blowfish under the same key fails (check Q12), because of MtCipher's quirks | verified | GrenderG/goshawk; Cha-Cha; check Q14 |
| file | extdata | the 3DS Extra Data holds `quest1`..`quest4` of 0x29000 bytes: a u32 (44 in all four), then 20 slots of 0x2010 bytes, then zeros; `card1`..`card3` and `cardbox` were empty here | verified | ours; check Q12 |
| whole | bytes | the 3DS Extra Data is not encrypted (MH4U's is) | verified | ours; check Q12 |
| slot | bytes | a slot is empty, or holds a downloaded quest as the server sent it, the same length: the `QTDS` record (byte-identical to the server's), its SHA-1 with the first two bytes zeroed, the padding bytes still as ciphertext (the game decrypts only up to the stated size), the size as a u32 BE; zeros up to 0x2000; the file name (`q_NNNNN.quest`) at 0x2000 | verified | mh3u-quest-studio `dlc_pack.py` (slot, name); ours, checks Q12, Q14 |
| slot | 20 bytes | after the record: the record's SHA-1 with bytes 0 and 1 set to zero, in all 38 | verified | ours; check Q14 |
| file | extdata | on Wii U the pack header is 0x28 bytes, then the same 20 slots | unverified | mh3u-quest-studio `dlc_pack.py` |

### Record

All integers little-endian. A "text" is five strings, English, French, German, Italian, Spanish, each a u32 byte length and UTF-8 without a terminator.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `QTDS` | verified | mh3u-quest-studio; check Q12 |
| 0x04 | u32 | language count, 5 | verified | mh3u-quest-studio; check Q12 |
| 0x08 | text | name | verified | mh3u-quest-studio; check Q12 |
| next | u16 | quest number: the file's `q_NNNNN` in all 38 (20xxx and 6xxxx here) | verified | mh3u-quest-studio; check Q12 |
| next | text | main objective | verified | mh3u-quest-studio; check Q12 |
| next | u8, u8 | stars (1..8 here), map | verified | mh3u-quest-studio; check Q12 (layout) |
| next | text | sub objective | verified | mh3u-quest-studio; check Q12 |
| next | u16 | time limit in minutes (30 or 50 here) | verified | mh3u-quest-studio; check Q12 |
| next | text | failure conditions | verified | mh3u-quest-studio; check Q12 |
| next | u16 ×3 | special flag and two conditions | unverified | mh3u-quest-studio |
| next | text ×2 | client, description | verified | mh3u-quest-studio; check Q12 |
| tail +0x00 | u8 ×2 | main small monsters 1 and 2 | unverified | mh3u-quest-studio |
| tail +0x02 | u64 | category bits (0x10 and 0x100000: monster HP ×0.55, per quest-studio) | unverified | mh3u-quest-studio |
| tail +0x0A | 11 bytes ×5 | large monsters: type, set type, start type, number, HP, attack and other table rows (0..127, rows of a table in the code), a fourth row, size, size parameter, stamina; type 0 = empty slot | verified | mh3u-quest-studio; check Q12 (stride; table rows all ≤ 127) |
| tail +0x41 | u8 ×6 | intruder settings | unverified | mh3u-quest-studio |
| tail +0x47 | 4 bytes ×64 | rewards: u16 item, u8 count, u8 chance; even slots are table A, odd slots table B, each ending at item 0 | verified | mh3u-quest-studio; check Q12 (both tables end; chances ≤ 100) |
| tail +0x147 | i32 ×5 | fee, reward, reward lost per faint, main HRP, failure HRP | verified | mh3u-quest-studio; randomizer; check Q12 (first three in range) |
| tail +0x15B | mixed | u8 ×4, u16 ×8, u32 ×4, u16 ×6, u32 ×2: gathering, progress, enemy level, supply and small-monster settings | unverified | mh3u-quest-studio |
| tail +0x193 | u16 | clear pattern: 0 one objective, 1 both, 2 either | verified | mh3u-quest-studio; randomizer; check Q12 (0..2) |
| tail +0x195 | (u32, u16, i16) ×2 | objectives: type in the low u16 (0x1 hunt, 0x2 deliver, item id as target, 0x81 capture, 0x101 slay, 0x8101 slay small, 0x404 repel, 0x2515 and 0x4014 siege repel, 0x2000 siege damage), target, count | verified | mh3u-quest-studio; check Q12 (every type seen is in that list) |
| tail +0x1A5 | u16 ×2, u64 ×2, u8 | arena times, unlock flags required and counted, clears required | unverified | mh3u-quest-studio; randomizer |
| tail +0x1BA | — | end of the fixed tail (442 bytes in all 38) | verified | randomizer; check Q12 |
| next | u32, 45 bytes ×n | arena monster sets (quests 201xx..203xx and 6xxxx; all 38 here) | verified | mh3u-quest-studio; check Q12 |
| next | u32, 172 bytes ×n | arena gear sets (5 in all 38): 86 u16, equipment, talismans, pouch, ammo | verified | mh3u-quest-studio; check Q12 (count and stride) |

### .quest_btl and .supp

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| class | rQuestBattleData | `.quest_btl`: id 0x7FD4466F, 0x88 bytes in memory, a `cResource`, in both MH3U 3DS (DTI at 0x00CB9E90) and Wii U; loader `rQuestBattleData::load` (Wii U 0x02074174) | verified | MH4UltimateDC-fork `config/games/mh3u/mt_classes.tsv`; Cha-Cha `config/dti.csv`, `symbols.txt` |
| file | ? | `.quest_btl` layout, magic `QTDB` (Wii U `BDTQ`): not documented anywhere public; the next step is the loader in MH3U's code, or the 353 files | unknown | — |
| class | rSuppItem | `.supp`: id 0x4EC7B399, 0x1A0 bytes in memory, a `cResource` (3DS DTI at 0x00CB9FF0) | verified | MH4UltimateDC-fork `mt_classes.tsv`; Cha-Cha `config/dti.csv` |
| file | xfs | `.supp` is an XFS file, so its field names come with it (check X1 in [xfs](xfs.md)); the game's quest supply box keeps 40 cells of 4 bytes (Wii U, Cha-Cha `src/game/menu_mouse.cpp`), which suggests what a supply set holds | unverified | Cha-Cha `docs/formats/xfs.md`, `menu_mouse.cpp` |

## rSetEmMain, rEmSetList, rRem, supply list (MHXX)

Layouts from the mhff wiki's MHX pages ("MHX rSetEmMain/rEmSetList/rRem/rSupplyList Format", GPL-3.0), checked on the parts of MHXX JPN's 173 DLC quest archives (check Q15). MHXX's `.esl` doesn't follow the MHX page; the layout below is ours. All little-endian.

### rSetEmMain (.sem): a boss monster's placement

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | 32 bytes | every `.sem` is 0x20 bytes (430 files); named `b_mMMemEEE_NN.sem` (map, monster, variant) | verified | ours; check Q15 |
| 0x00 | f32 | magic 1.0 | verified | mhff wiki; check Q15 |
| 0x04 | u32 | count (1 in all) | verified | mhff wiki; check Q15 |
| 0x08 | u32 | round number? (0 in 426, 1 in 4) | unverified | mhff wiki; check Q15 |
| 0x0C | u32 | area | unverified | mhff wiki; check Q15 (all small) |
| 0x10 | f32 | angle | unverified | mhff wiki |
| 0x14 | f32 ×3 | x, y, z position | unverified | mhff wiki; check Q15 (all finite, within ±1e5) |

### rEmSetList (.esl): small monsters per area

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `esl\0` | verified | mhff wiki (a magic); check Q15 (the value) |
| 0x04 | u32 | 2 in all (a version, presumably; the MHX page says unknown) | verified | ours; check Q15 |
| 0x08 | u32 ×14 | area offsets from the file start, 0 = unused, used ones first; the first area at 0x40 (the MHX page has 20 slots, from 0x08 to 0x54: not so in MHXX) | verified | ours; check Q15 |
| file | 0x40 bytes | every quest carries one empty `.esl` (no area; 173 of 249) | verified | ours; check Q15 |
| area +0x00 | char[4] | magic `ESD\0` | verified | ours; check Q15 |
| area +0x04 | u32 | 20151214 in all 631 areas (a date: a version, presumably) | verified | ours; check Q15 |
| area +0x08 | u16 | entry count; areas follow one another with nothing between, the last ending at the file end (the MHX page has a u32 count at +0x08 and 40-byte entries: not so in MHXX) | verified | ours; check Q15 |
| area +0x0A | 36 bytes ×count | entries: u8 small-monster id (38 values, at most 101), u8 0x10, then 8 bytes of settings; 0xCDCD at +0x0A (uninitialised fill); f32 x, y, z at +0x0C; zeros at +0x18; a u16 at +0x1C; zeros to the end | unverified | ours; check Q15 (stride, zeros, floats finite) |

### rRem (.rem): a reward table

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | 184 bytes | every `.rem` is 0xB8 bytes (786 files), named `rem_NNNNNN.rem` | verified | ours; check Q15 |
| 0x00 | f32 | magic 1.0 | verified | mhff wiki; check Q15 |
| 0x04 | u32 | count (1 in all) | verified | mhff wiki; check Q15 |
| 0x08 | (u8, u8) ×8 | flags: id, item count; the counts add up to the number of non-empty slots in all 786 | verified | mhff wiki; check Q15 |
| 0x18 | (u16, u8, u8) ×40 | slots: item id, count, chance; in 738 of 786 the non-empty slots come first and each flag's group of chances sums to 100; the other 48 have gaps (unexplained) | unverified | mhff wiki; check Q15 |

### Supply list (`supp_N`, class 0x54539AEE)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | 168 bytes | every supply list is 0xA8 bytes (173 files) | verified | mhff wiki (rSupplyList); check Q15 |
| 0x00 | f32 | magic 1.0 | verified | mhff wiki; check Q15 |
| 0x04 | u32 | count (1 in all) | verified | mhff wiki; check Q15 |
| 0x08 | (u16, u8, u8) ×40 | slots: item id, count (1..99 whenever the item is non-zero), label (0..4 seen) | verified | mhff wiki; check Q15 (stride, counts) |

## Open questions

- MH4U's `.mib`: the header's remaining unverified fields (Q6 against the game's own quests; in-game checks for meanings).
- Whether the game checks a stored quest's hash or its padding bytes when it lists or loads the quest (check Q17, in game). The 28 bytes themselves are understood (Q16), so a mod quest can be stored in the same form either way.
- MH3U's quest format: the `QTDS` record is now laid out (above); Q13 checks it on the RomFS's own quests. `.quest_btl` (`QTDB`) and `.supp` (`XFS`) are still unknown. Why the game zeroes the first two bytes of a stored quest's SHA-1 is open (a "checked" mark, perhaps).
- How MHXX's `.sem`/`.esl`/`.rem` map onto `.mib` sections.

## Checks

Run on 2026-11-23 with `mhuc survey` and `mhuc romfs list` on the maintainer's dumps (see [arc](arc.md#checks)).

Re-running Q3 to Q15 needs no scratch script: `mhuc decrypt` (with a key file you make from mhef's `mhef/n3ds.py` or goshawk's `utils/constants.py`, kept outside the repositories) and `mhuc quest check|dump` read every file these checks covered. For example: `mhuc decrypt mh4u-save quest1 q1.bin --key mh4u_save.key --mode quest`, then `mhuc quest check mh4u q1.bin`; `mhuc decrypt mh3u-dlc q_20102.quest out.quest --key mh3g.key`; `mhuc quest check mhxx q*.arc`. On 2026-11-23 they read all 120 MH4U, 173 MHXX (with every part) and 38 MH3U quests without a failure.

- **Q1 (done):** MH4U keeps its quests in two archives that hold only `rQuestData`: 207 and 301 entries (the same in EUR). The four language folders' `core_quest.arc` hold the quest screens (effects, layouts, textures), no quest data. MH3U has no quest archives: 365 `.quest`, 353 `.quest_btl` and 196 `.supp` files lie loose in the RomFS, plus quest screens in archives.
- **Q2 (done):** MHXX JPN has 1,335 archives with quest classes. 1,331 hold all four of `rQuestData`, `rSetEmMain`, `rEmSetList` and `rRem`; 3 hold only `rQuestData`; 1 holds only `rRem`. In 1,334 the last entry is the `rQuestData`. A quest is one archive in MHXX, as mhff describes for MH4U's DLC.

Q3 to Q5 were run on 2026-11-23 in a web session on the maintainer's own MH4U (USA) Extra Data and save `system` file, uploaded by them as an archive and kept outside the repositories. The decryption used mhef's `SavedataCipher` logic (svanheulen/mhef, GPL-3.0; its key is in mhef's `mhef/n3ds.py` and is not copied here), in a throwaway script outside the repositories.

- **Q3 (done):** `mhuc entropy <Extra Data folder>` lists eleven files (`card1`..`card3` 494,592 bytes, `cardbox` 270,336, `otomo1` 8,704, `quest1`..`quest5` 328,704, and the save's `system` 512), all multiples of 8 and all dense (7.98 to 8.00 bits per byte; `system` 7.54, dense for its 512 bytes). The three `card*` files start with the same two bytes, which mhef's card mode explains: it leaves a 24-byte header in the clear, whose first word is `seed << 16 | 0x10`.
- **Q4 (done):** decrypt each file with mhef's `SavedataCipher(MH4G_NA)` in all three modes. Pass: exactly the modes in the table above give a matching checksum, for all eleven files (`cardbox`, `otomo1` and `system` also pass in quest mode, whose only difference is dropping the last 0x100 bytes).
- **Q5 (done):** in each decrypted `quest*` file, split at 0x2010 and look at every slot. Pass: 200 slots, 120 holding a quest and 80 all zero; every quest starts at its slot's offset 0 with 0xA0 and `v005`. On all 120 quests: every header offset listed as verified lands inside the slot; the supply-box list ends with 0xFF; the main reward items end with 0xFFFF at a 6-byte stride; the large monster list ends with 0xFFFFFFFF at a 0x28 stride with every id below 124 (the id table's size, [id-tables](../docs/design/id-tables.md)); the intruder list ends at a 0x2C stride; the English title decodes as printable UTF-16. The value ranges quoted in the header table are from the same 120.
- **Q7 (done):** a second pass over the same 120 quests, for the sub-structures and the spread of enum-like values. Pass: the large-monster offset leads to a 0-terminated list of wave offsets, each a terminated definition list, and every objective target of types 0x1, 0x81 and 0x204 is a monster of those waves; the small-monster offset leads to a 0-terminated list of areas, each a terminated definition list with ids below 0x200; every supply item with a non-zero id has a count of 1 to 99; the five language offsets are distinct and all seven strings of each decode as UTF-16. The value spreads in the header table come from this pass.
- **Q8 (done):** compare each used slot's last 16 bytes with the quest id at 0xC0. Pass: in all 120 they are exactly `m%05d.mib` of that id, NUL-padded. (Q5 had ruled out the common hashes; the low entropy, 10 printable ASCII characters and digits matching the quest id gave it away.)
- **Q9 (done):** take the server's quest files from the GrenderG/goshawk preservation mirror (Capcom's server is gone: `goshawk.capcom.co.jp` gives NXDOMAIN as of 2026-11-23): 120 `m*.mib` in `files/3ds/mh4g_us_/` and 120 in `mh4g_eu_/`, outside the repositories. Decrypt with mhef's `DLCCipher` (MH4G NA). Pass: all 240 check against their SHA-1, every encrypted size is the plaintext plus 20, padded to 8, plus 4; every plaintext starts with 0xA0 and `v005`, none is an ARC, all are under 0x2000 bytes; EUR and USA are identical; the 120 names are exactly the 120 quests of the maintainer's Extra Data, and each slot starts with its server file byte for byte, followed by 28 bytes, then zeros.
- **Q10 (done):** take MH3U's DLC quests from the goshawk mirror (`files/3ds/mh3gu_us`, `mh3gu_eu`, `mh3g`, `files/wiiu/mh3ghd_us`), outside the repositories. Pass: the USA, EUR and Wii U folders hold the same 38 files byte for byte; every file is 8n+4 bytes; in every file the last 4 bytes, big-endian, are 0 to 7 less than the length before them; the aligned 8-byte blocks repeat (a third of them one block) and the first is common to all 85. Fail, so far: Blowfish with goshawk's MH3G key (and mhef's MH4U keys, with simple variants and byte orders) gives no plaintext; the repeated block doesn't decrypt to a constant under any of them.
- **Q11 (done):** take MHXX JPN's DLC from the goshawk mirror (`files/3ds/mhxx_jp`), outside the repositories, and decrypt with mhef's `DLCXCipher` logic and goshawk's MHXX JPN key. The layout that works ends with one 0x100 signature, not two. Pass: all 188 files check against their SHA-1 (173 quest ARCs, the two quest lists, the GMDs, the Palico and update files); every quest is an ARC 0x11 whose last entry is a 249-byte `.mib`, as in the RomFS (Q2); over the 173 `.mib`, the header rows marked verified hold, and the spreads quoted come from the same files.
- **Q12 (done):** the maintainer's MH3U 3DS Extra Data (USA), uploaded by them, outside the repositories. Pass: no file is encrypted (`mhuc entropy`: all plain); each `quest*` file starts with a u32, then `QTDS` at 4 + 0x2010·k; 38 quests in 80 slots, all 38 on the goshawk mirror. Parsing each with quest-studio's layout reads to the end of the arena gear sets without error; the fixed tail is 442 bytes in all; the record ends 20 bytes before the mirror file's plaintext size, and the slot then holds the padding and the size exactly as the mirror file's last bytes, the same length as the file. Pairing slot and mirror blocks gives a consistent codebook (10,095 of 10,098), which shows ECB with one key; Blowfish, DES, CAST and RC2 under the known keys don't reproduce it.
- **Q13 (open):** parse the 365 RomFS `.quest` files of MH3U USA with the same layout (no arena block outside 201xx..203xx and 6xxxx). Needs the MH3U RomFS.
- **Q14 (done):** decrypt the goshawk mirror's MH3U files with MtCipher as Cha-Cha describes it (standard pi tables computed, not copied; little-endian words; the S-box quirk) under goshawk's MH3G key. Pass: all 38 USA (`mh3gu_us`) and all 47 Japanese MH3G (`mh3g`) files decrypt to `QTDS` with a matching SHA-1. Against the maintainer's 38 stored quests: every record is byte-identical to its server file; the 20 bytes after it are the SHA-1 with bytes 0 and 1 zeroed; the padding bytes equal the server file's ciphertext; the size trailer is the same.
- **Q15 (done):** over the 173 decrypted MHXX JPN quest archives (Q11), read every `rSetEmMain`, `rEmSetList`, `rRem` and supply-list entry with the tables above. Pass: sizes, magics and counts as stated for 430 `.sem`, 249 `.esl` (631 areas, 1,815 entries), 786 `.rem` and 173 supply lists; every `.esl` area is `ESD\0` + version + u16 count + 36-byte entries, back to back, to the file end.
- **Q16 (done, 2026-11-23, a second web session on the same Extra Data):** for each of the 120 used slots, read the last non-zero 4 bytes before 0x2000 as a u32 BE size. Pass, in all 120: the slot's non-zero bytes end exactly at the size padded to 8, plus 4; the first size − 20 bytes are the `.mib`; the 20 bytes after it equal the `.mib`'s SHA-1 except bytes 0 and 1, which are zero; the 4 padding bytes equal the bytes at the same offset in the goshawk mirror's still-encrypted server file of the same name (compared as stored, nothing decrypted), and that file has the slot's length. So a slot is the server file decrypted up to its stated size, exactly as in MH3U (Q14). Q5 had ruled out the hashes because it hashed the whole file and compared all 20 bytes. Re-run: `mhuc questslot check quest1.bin ... quest5.bin` prints "120 used slots, 120 with a matching hash and size".
- **Q17 (open, in game):** back up the Extra Data, decrypt `quest1` (`mhuc decrypt mh4u-save quest1 q.bin --key K --mode quest`), copy one stored quest into an empty slot under a new id and name (change the id at 0xC0 of the `.mib`, then `mhuc questslot put q.bin --slot N --mib new.mib --out q2.bin`), encrypt again (`mhuc encrypt mh4u-save q2.bin quest1 --key K --mode quest`; specs/extdata.md check E5 shows the round trip is exact) and put it back with a save manager. Pass: the game lists both quests and the new one starts. Then repeat with the hash bytes changed: if the quest vanishes or the game reports corrupt data, the hash is checked (and `questslot put` already writes it correctly).
- **Q6 (open):** run the Q5 checks over the 508 `.mib` in `quest00.arc` and `quest01.arc` (MH4U USA v1.3.0 RomFS). Needs the RomFS.
