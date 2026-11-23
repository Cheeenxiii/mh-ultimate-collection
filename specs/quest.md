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
| `.quest_btl` | ? | MH3U | loose files under `/quest/btl/` (353), magic `QTDB` |
| `.supp` | ? | MH3U | loose files under `/quest/support/` (196), magic `XFS\0` (MT's serialised-object format) |

Class names and extensions come from mhff's table. MH4U's registry (MH4UltimateDC `config/mt_classes.tsv`) has `rQuestData` and `rQuestInfoTbl` but no `rSetEmMain`, `rEmSetList` or `rRem`: in MH4U the monster sets and rewards live inside `.mib`.

## rQuestData (MH4U .mib)

### Where quests live

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | arc | the game's own quests: all `.mib` in two archives, `/loc/data/quest00.arc` (207) and `quest01.arc` (301), nothing else in them | verified | ours; check Q1 |
| file | arc | a DLC quest as served by Capcom's server is one ARC whose last entry is the `.mib` | unverified | mhff convert_quest.py |
| whole | bytes | the server's DLC files: Blowfish on byte-swapped 32-bit words, a SHA-1 of the plaintext and the size at the end (mhef `DLCCipher`) | unverified | svanheulen/mhef; mhff wiki "MH4U DLC Encryption" |
| file | extdata | downloaded quests are kept in Extra Data, in five files `quest1`..`quest5` of 328,704 bytes each, beside `card1`..`card3`, `cardbox` and `otomo1` | verified | ours; check Q3 |
| whole | bytes | every Extra Data file, and the save's `system`, is encrypted: mhef's `SavedataCipher` (MH4G) decrypts all of them with a matching checksum, in mode "quest" for `quest*`, "card" for `card*` and "normal" for the rest | verified | svanheulen/mhef; ours, check Q4 |
| quest file | slots | a decrypted `quest*` file is 40 slots of 0x2010 bytes, then 120 zero bytes; a slot is all zero (empty) or holds one bare `.mib` from its offset 0 (no ARC around it) | verified | ours; check Q5 |
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

## rSetEmMain, rEmSetList, rRem

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | layout unknown here | unknown | mhff (names and extensions only) |

## Open questions

- MH4U's `.mib`: the header's remaining unverified fields (Q6 against the game's own quests; in-game checks for meanings).
- Whether a server DLC file, once through mhef's `DLCCipher`, holds the same `.mib` bytes as its Extra Data slot (needs one file from Capcom's server; this environment can't reach it).
- MH3U's quest format: loose `QTDS`/`QTDB` files and `XFS` support files, not ARCs (check Q1). Their layouts are unknown; `XFS` is MT's generic serialisation, which may make `.supp` readable from the class registry.
- How MHXX's `.sem`/`.esl`/`.rem` map onto `.mib` sections.

## Checks

Run on 2026-11-23 with `mhuc survey` and `mhuc romfs list` on the maintainer's dumps (see [arc](arc.md#checks)).

- **Q1 (done):** MH4U keeps its quests in two archives that hold only `rQuestData`: 207 and 301 entries (the same in EUR). The four language folders' `core_quest.arc` hold the quest screens (effects, layouts, textures), no quest data. MH3U has no quest archives: 365 `.quest`, 353 `.quest_btl` and 196 `.supp` files lie loose in the RomFS, plus quest screens in archives.
- **Q2 (done):** MHXX JPN has 1,335 archives with quest classes. 1,331 hold all four of `rQuestData`, `rSetEmMain`, `rEmSetList` and `rRem`; 3 hold only `rQuestData`; 1 holds only `rRem`. In 1,334 the last entry is the `rQuestData`. A quest is one archive in MHXX, as mhff describes for MH4U's DLC.

Q3 to Q5 were run on 2026-11-23 in a web session on the maintainer's own MH4U (USA) Extra Data and save `system` file, uploaded by them as an archive and kept outside the repositories. The decryption used mhef's `SavedataCipher` logic (svanheulen/mhef, GPL-3.0; its key is in mhef's `mhef/n3ds.py` and is not copied here), in a throwaway script outside the repositories.

- **Q3 (done):** `mhuc entropy <Extra Data folder>` lists eleven files (`card1`..`card3` 494,592 bytes, `cardbox` 270,336, `otomo1` 8,704, `quest1`..`quest5` 328,704, and the save's `system` 512), all multiples of 8 and all dense (7.98 to 8.00 bits per byte; `system` 7.54, dense for its 512 bytes). The three `card*` files start with the same two bytes, which mhef's card mode explains: it leaves a 24-byte header in the clear, whose first word is `seed << 16 | 0x10`.
- **Q4 (done):** decrypt each file with mhef's `SavedataCipher(MH4G_NA)` in all three modes. Pass: exactly the modes in the table above give a matching checksum, for all eleven files (`cardbox`, `otomo1` and `system` also pass in quest mode, whose only difference is dropping the last 0x100 bytes).
- **Q5 (done):** in each decrypted `quest*` file, split at 0x2010 and look at every slot. Pass: 200 slots, 120 holding a quest and 80 all zero; every quest starts at its slot's offset 0 with 0xA0 and `v005`. On all 120 quests: every header offset listed as verified lands inside the slot; the supply-box list ends with 0xFF; the main reward items end with 0xFFFF at a 6-byte stride; the large monster list ends with 0xFFFFFFFF at a 0x28 stride with every id below 124 (the id table's size, [id-tables](../docs/design/id-tables.md)); the intruder list ends at a 0x2C stride; the English title decodes as printable UTF-16. The value ranges quoted in the header table are from the same 120.
- **Q7 (done):** a second pass over the same 120 quests, for the sub-structures and the spread of enum-like values. Pass: the large-monster offset leads to a 0-terminated list of wave offsets, each a terminated definition list, and every objective target of types 0x1, 0x81 and 0x204 is a monster of those waves; the small-monster offset leads to a 0-terminated list of areas, each a terminated definition list with ids below 0x200; every supply item with a non-zero id has a count of 1 to 99; the five language offsets are distinct and all seven strings of each decode as UTF-16. The value spreads in the header table come from this pass.
- **Q8 (done):** compare each used slot's last 16 bytes with the quest id at 0xC0. Pass: in all 120 they are exactly `m%05d.mib` of that id, NUL-padded. (Q5 had ruled out the common hashes; the low entropy, 10 printable ASCII characters and digits matching the quest id gave it away.)
- **Q6 (open):** run the Q5 checks over the 508 `.mib` in `quest00.arc` and `quest01.arc` (MH4U USA v1.3.0 RomFS). Needs the RomFS.
