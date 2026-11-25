---
class: none (save-side files)
extension: system, user1, user2, user3 (no extension)
games: MH4U USA v1.3.0, checked on the maintainer's own saves; the cipher is the one Extra Data uses too
status: unknown
---

# MH4U saves

MH4U keeps four save files on the SD card: `system` and one file per character slot, `user1` to `user3`.
Every one is encrypted with mhef's `SavedataCipher` (mode `normal`) and decrypted by
`mhuc decrypt mh4u-save FILE --key K`, which also strips the cipher's 8-byte header. **Offsets below are in
the decrypted file** unless a row says "encrypted". A character save is 81,400 bytes decrypted; `system` is
504.

This page maps the character save (the item box and equipment tables, the structures indexed by monster id,
item id and quest id) and records what is known of `system`. The character save's quest clear lists and the
`system` save's fields are their own slices of the same work: [#153](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/153)
and [#154](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/154).

Sources: [Rokumaehn/mh4edit](https://github.com/Rokumaehn/mh4edit) (MIT) for the character profile, item box,
equipment box, guild quests and Palicos; the MH4G save-editor wiki
([saveeditor_mh4g](https://w.atwiki.jp/saveeditor_mh4g/)) for the pouches, quest counts and weapon usage; the
mhff wiki (svanheulen/mhff, GPL-3.0) and a community board post for the monster log's shape; mhef (GPL-3.0)
for the cipher. All are credited in [README.md](README.md). The reader is `mhuc save dump|check`
(`src/mhuc/save.py`); its checks are this page's S1 to S7.

## Files

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | 512 bytes (504 decrypted) | `system`: one per SD card, shared by the three characters | verified | ours; the cipher round trip is check S1 |
| file | 81,408 bytes (81,400 decrypted) | `user1` to `user3`: one character each | verified | ours; check S1 |

The four files' cipher, and its checksum, are in [quest.md](quest.md) check Q4 and [extdata.md](extdata.md):
the key is the NUL-terminated string in the game's own code (specs/extdata.md), never in this repository.

## Cipher and checksum

The cipher's header is inside the encrypted file and is removed by `mhuc decrypt mh4u-save`:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 (encrypted) | u32 | seed word: the 16-bit stream seed in the high half, `0x10` in the low half | verified | mhef `SavedataCipher`; check S1 |
| 0x04 (encrypted) | u32 | checksum: the sum of the decrypted payload's bytes, modulo 2^32 | verified | mhef `SavedataCipher`; check S1 |
| 0x08 (encrypted) | rest | payload: Blowfish on little-endian words, then a 16-bit XOR stream seeded from the seed word | verified | mhef `SavedataCipher`; check S1 |

There is no other checksum: re-encrypting a decrypted file recomputes exactly these two words, and every byte
of the four files comes back identical (check S1). A writer therefore only has to keep the plaintext sum.

## Character save blocks

The blocks tile the 81,400 bytes exactly:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x0000 | 0x40 bytes | profile (table below) | verified | mh4edit; checks S2, S3 |
| 0x0040 | 7 × 28 bytes | the seven worn equipment records, in the order weapon, chest, arms, waist, legs, head, talisman | verified | mh4edit; check S3 |
| 0x0104 | 7 × u16 | the equipment-box slot each worn piece comes from (`0xFFFF` = none) | verified | mh4edit; check S3 |
| 0x0112 | 0x4C bytes | unknown | unknown | ours; non-zero in the maintainer's saves |
| 0x015E | 1,400 × 4 bytes | item box (table below) | verified | mh4edit; checks S3, S6 |
| 0x173E | 1,400 × 28 bytes | equipment box (table below) | verified | mh4edit; check S3 |
| 0xB05E | 0xAE6 bytes | unknown; all zero in the maintainer's saves | unknown | ours |
| 0xBB44 | 0x96C bytes | Palico equipment box: 12 bytes then 100 × 24-byte slots, unread | unknown | mh4u-toolbox; ours |
| 0xC4B0 | 232 bytes | the main Palico (table below) | verified | mh4edit; check S5 |
| 0xC598 | 0x55C bytes | unknown | unknown | ours; non-zero in the maintainer's saves |
| 0xCAF4 | 8 × 4 bytes | gunner pouch (table below) | verified | the MH4G save-editor wiki; check S3 |
| 0xCB14 | 24 × 4 bytes | item pouch: three pages of eight (table below) | verified | the MH4G save-editor wiki; check S3 |
| 0xCB74 | 0x1134 bytes | unknown | unknown | ours; non-zero in the maintainer's saves |
| 0xDCA8 | 10 × 304 bytes | guild-quest slots (table below) | verified | mh4edit; check S4 |
| 0xE888 | 0x998 bytes | unknown; brigade points at 0xE8A0 (table below) | unknown | ours; the wiki's `system`-side offsets don't place it |
| 0xF220 | 280 bytes | 2,240 bits, meaning unknown (see "quest lists" below) | unknown | ours; all set in the completed save, partly set in the mid-game one |
| 0xF338 | 55 × 232 bytes | the other Palicos (table below) | verified | mh4edit; check S5 |
| 0x12510 | 0xF0 bytes | unknown; all zero in the maintainer's saves | unknown | ours |
| 0x12600 | 0xBA4 bytes | the guild-card block (table below) | unknown | ours; offsets from the MH4G save-editor wiki, partly checked |
| 0x131A4 | 0x5D0 bytes | arena leaderboard: quest ids and times, not decoded | unknown | a community board post; ours |
| 0x13774 | 0x27C bytes | unknown; all zero in the maintainer's saves | unknown | ours |
| 0x139F0 | 0x408 bytes | unknown, non-zero in every character save | unknown | ours |

`mhuc save dump` lists each unknown block's offset, size and non-zero byte count, so a later session can
tell which ones move between characters.

### Profile (0x0000)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | 24 bytes | name, UTF-16LE, NUL-padded (at most 12 characters) | verified | mh4edit; check S2 |
| 0x18 | u8 | gender (0 male, 1 female) | verified | mh4edit; check S2 |
| 0x19 | u8 | face | verified | mh4edit; check S2 |
| 0x1A | u8 | hair style | verified | mh4edit; check S2 |
| 0x1B | u8 | inner clothing type | verified | mh4edit; check S2 |
| 0x1C | u8 | voice | verified | mh4edit; check S2 |
| 0x1D | u8 | eye colour | verified | mh4edit; check S2 |
| 0x1E | u8 | makeup type | verified | mh4edit; check S2 |
| 0x1F | u8 ×3 | makeup colour, R G B | verified | mh4edit; check S2 |
| 0x22 | u8 ×3 | hair colour, R G B | verified | mh4edit; check S2 |
| 0x25 | u8 ×3 | inner clothing colour, R G B | verified | mh4edit; check S2 |
| 0x28 | u8 ×3 | skin colour, R G B | verified | mh4edit; check S2 |
| 0x2B | u8 | unknown, zero in the maintainer's saves | unknown | mh4edit |
| 0x2C | u32 | Hunter Rank (the game caps it at 999) | verified | mh4edit; check S2 |
| 0x30 | u32 | Hunter Rank points | verified | mh4edit; check S2 |
| 0x34 | u32 | funds (the game caps them at 99,999,999) | verified | mh4edit; check S2 |
| 0x38 | u32 | play time in MH4G, in seconds | verified | mh4edit; check S2 |
| 0x3C | u32 | play time in MH4, in seconds (0 in the maintainer's saves) | verified | mh4edit; check S2 |

### Equipment record (28 bytes)

Worn in 0x0040, and the equipment box at 0x173E.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u8 | kind: 0 empty, 1 chest, 2 arms, 3 waist, 4 legs, 5 head, 6 talisman, 7 to 20 the fourteen weapon types in the game's order | verified | mh4edit; check S3 |
| 0x01 | u8 | unknown, zero in the maintainer's saves | unknown | mh4edit |
| 0x02 | u16 | equipment id, indexed by kind | verified | mh4edit; check S3 |
| 0x04 | u16 | unknown | unknown | mh4edit |
| 0x06 | u16 | decoration slot 1: the jewel id in bits 0 to 14 | verified | mh4edit; check S3 |
| 0x08 | u16 | decoration slot 2, same shape | verified | mh4edit; check S3 |
| 0x0A | u16 | decoration slot 3, same shape | verified | mh4edit; check S3 |
| 0x0C | 16 bytes | type-specific bytes (weapons: relic fields), not decoded | unknown | mh4edit |

Bit 15 of each slot word is read by mh4edit as "slot fixed"; whether the game uses it is **unverified**, so
`mhuc` prints the whole u16.

### Item box (0x015E) and the pouches

The same four-byte slot everywhere: an item id, then a count.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u16 | item id in bits 0 to 10; bits 11 to 15 are unknown | verified | mh4edit masks 0x7FF; check S3 |
| 0x02 | u16 | count (0 to 99) | verified | mh4edit; check S3 |

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x015E + 4i | 4 bytes | item box slot *i*, 1,400 slots | verified | mh4edit; check S3 |
| 0xCAF4 + 4i | 4 bytes | gunner pouch slot *i*, 8 slots | verified | the MH4G save-editor wiki; check S3 |
| 0xCB14 + 4i | 4 bytes | item pouch slot *i*, 24 slots: three pages of eight | verified | the MH4G save-editor wiki; check S3 |

A used slot has a non-zero id or count; the game accepts an empty slot with a zero id and count.

### Guild-quest slots (0xDCA8)

Ten 304-byte records, the same record as a card's unregistered guild quests in
[extdata.md](extdata.md#guild-quest-304-bytes). A slot is empty when every byte is zero. The fields checked so
far:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x000 | 24 bytes | original owner's name, UTF-16LE | verified | mh4edit; check S4 |
| 0x018 | 8 bytes | the quest's unique id | verified | mh4edit; check S4 |
| 0x025 | u8 ×3 | weapon, armour-series and armour-type bias | unverified | mh4edit; check S4 |
| 0x028 + 40i | u8 | monster *i*'s id (0 to 123), 40-byte monster records ×5 | verified | mh4edit; check S4 |
| 0x114 + 4i | u8 ×4 | area *i*: unknown, map id, entrance, exit | unverified | extdata.md; check S4 |
| 0x128 | u8 ×3 | initial level, current level, treasure area | verified | mh4edit; check S4 |
| 0x12B | u8 ×5 | frenzy flags, one byte per monster | unverified | extdata.md; check S4 |

The rest of the record (spawn areas, subareas, biases' meanings) is in extdata.md and has not been checked
against a save.

### Palicos (0xC4B0 and 0xF338)

Fifty-six 232-byte records: the main Palico at 0xC4B0, then 55 at 0xF338.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | 24 bytes | name, UTF-16LE, NUL-padded | verified | mh4edit; check S5 |
| 0x70 | u64 | experience | verified | mh4edit; check S5 |

The rest of the record (appearance, skills, equipment slots) is not decoded; mh4edit edits some of it, and
the Palico gear box at 0xBB44 is unread.

### Monster log (0x12E5C)

82 fixed ten-byte entries, tiling 0x12E5C to 0x13190.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u16 | kills | verified | the mhff wiki and a community board post; check S6 |
| 0x02 | u16 | captures | verified | same; check S6 |
| 0x04 | u16 | largest size recorded, in the game's size units (0 = none) | verified | same; check S6 |
| 0x06 | u16 | smallest size recorded, same units (0 = none) | verified | same; check S6 |
| 0x08 | u16 | crown flags (bit 0 mini, 1 silver, 2 gold, 3 something else; the values seen are 0 to 13) | unverified | same; check S6 |

**The log is not indexed by monster id.** A community board post names the first entry's monster as Seltas,
and Seltas is MH4U id 25 (`data/catalog/versions.csv`, `mh4u_id` em025), not 0. The order the 82 entries follow
is **unknown**: it is probably the guild card's own monster order, but no table for it has been found. A modded
monster's new id therefore does not fit this log, and the entry a new monster would use is unknown.

### Guild-card block (0x12600)

The character save keeps the data the guild card shows. Some fields are checked; the rest of the block (awards,
quest clear bits and other records) is not.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x12600 | u16 ×3 | unknown header words | unknown | ours; values differ per character |
| 0x12606 | u16 | Hunter Rank, equal to the profile's | verified | ours; check S7 |
| 0x12608 | 24 bytes | character name, UTF-16LE, equal to the profile's | verified | ours; check S7 |
| 0x12620 | 7 × u16 | quest counts (table below) | unverified | the MH4G save-editor wiki; check S7 |
| 0x12796 | 14 × u16 + u16 | weapon usage, village: fourteen weapon types in the game's order, then an unknown u16 and a zero u16 (a 0x20-byte record) | verified | the MH4G save-editor wiki; check S7 |
| 0x127B6 | 14 × u16 + u16 | weapon usage, gathering hall, same shape | verified | same; check S7 |
| 0x127D6 | 14 × u16 + u16 | weapon usage, arena, same shape | verified | same; check S7 |
| 0xE8A0 | u32 | brigade points (the game caps them at 9,999,999) | unverified | the MH4G save-editor wiki; check S7 |
| 0xF220 | 280 bytes | 2,240 bits; meaning unknown, candidate for the quest clear flags | unknown | ours; check S7 |

The wiki gives the three weapon-usage tables at 0x12756, 0x12776 and 0x12796; in the maintainer's USA
v1.3.0 saves the same three tables are 0x40 later, at the offsets above (the values there are the weapon
counts and the three tables are separated by four zero bytes). That regional difference, and the meanings
"village", "gathering hall" and "arena", are unverified; the shape and the offsets are checked.

Quest counts, in field order:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x12620 | u16 | village, low rank | unverified | the MH4G save-editor wiki; check S7 |
| 0x12622 | u16 | gathering hall, low rank | unverified | same |
| 0x12624 | u16 | gathering hall, high rank | unverified | same |
| 0x12626 | u16 | guild quests | unverified | same |
| 0x12628 | u16 | arena | unverified | same |
| 0x1262A | u16 | village, high rank | unverified | same |
| 0x1262C | u16 | gathering hall, G rank | unverified | same |

Quest lists: the character save must also record which quests a character has cleared, but no public layout
was found. The 280-byte field at 0xF220 is the main candidate (2,240 bits: all set in the completed save,
1,257 set in the mid-game one), and the block at 0xE888 is another. Mapping them is
[#153](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/153).

## System save

504 bytes decrypted, shared by all three characters; `mhuc decrypt` and `mhuc save dump` handle it like
a character save. The cipher and checksum are the character saves' (check S1). Three saved states were
compared (check S9): the maintainer's current `system`, a second copy in the DLC Save Data folder,
and the `system` the game writes on a fresh SD card before a character exists. The two copies differ in
exactly six bytes, so they are the same save at two times. That comparison supports the candidate rows
below, but it does not name their fields: no in-game screen has been compared yet and the game's own
reader has not been read. Check S10 is the procedure that settles them.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | version: 0 in the save written before a character exists, 1 in the two saves with characters | unverified | ours; check S9 |
| 0x04 | u32 | candidate: a Unix time that moves; it differs between the two copies | unverified | ours; check S9 |
| 0x08 + 4i | u32 ×4 | four values; identical in both copies | unknown | ours; check S9 |
| 0x18 | 32 bytes | bit flags: the only dense field, and the only other bytes that differ between the copies (at 0x35 to 0x37) | unknown | ours; check S9 |
| 0x38 | u32 | 1 in every observed save, including the one written before a character exists | verified | ours; check S9 |
| 0x3C | u32 | candidate: the selected character slot; 0xFFFFFFFF before a character exists, 0 once one does | unverified | ours; check S9 |
| 0x40 | u32 | unknown; 0 before a character exists, 1 in the other copy, 2 in the current save (three character files) | unknown | ours; check S9 |
| 0x44 | 0x20 bytes | no field found; zero in every observed save | unknown | ours; check S9 |
| 0x64 | u32 | unknown; 1 in the current save, 0 in the other copy and before a character exists | unknown | ours; check S9 |
| 0x68 | 0x190 bytes | no field found; zero in every observed save | unknown | ours; check S9 |

Read little-endian as Unix seconds, the four words at 0x08 fall within 14 seconds of each other and the
word at 0x04 moved by about three hours between the copies. That makes 0x04 a candidate for a time that
moves (a last write) and 0x08 to 0x17 a candidate for four times or ids that stayed put (the last write
of four save files, or four guild cards). Neither is verified.

What is still unmapped: the options, the guild-card list and the DLC/quest registration. The candidates
are the 32-byte flag block at 0x18 — the only dense bit field, and the other copy differs there at 0x35
to 0x37, which a changed option or a few more registered quests would explain — and the four words at
0x08. Mapping them is check S10. [#77](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/77)'s
converter needs the DLC/quest bits: until S10, `mhuc` cannot tell a mod's registration from MH4U's, so
the converter must leave `system` untouched.

## Checks

Run on 2026-11-25 on the maintainer's own saves (`game_files/saves/MH4U`: `system`, `user1` to `user3`)
and, for S9, the copy of `system` that ships in the DLC Save Data folder and one the game wrote on a fresh
SD card, outside the repository, decrypted with `mhuc decrypt mh4u-save` and the key in
`game_files/work/mhuc_dumps/mh4u/save.key`. The procedures print values and counts, never bytes; they are
repeatable on any player's saves.

- **S1 (done):** decrypt each file, then encrypt it again with `mhuc encrypt mh4u-save` and the seed read
  from its own ciphertext (the first word's high half). Pass: all four files come back byte-identical, so the
  seed and checksum words are exactly as this page says and there is no second checksum. `tests/test_with_game_files.py`
  runs the same round trip.
- **S2 (done for the offsets; the appearance comparison is the maintainer's):** `mhuc save dump FILE` prints
  the profile. The name and Hunter Rank it prints equal the guild-card copies at 0x12608 and 0x12606 (S7), the
  ranks and funds sit inside the game's caps (two of the maintainer's characters are at both caps and the
  mid-game one is at HR 173 with lower funds), and the play times agree with the ranks. To finish the check by
  eye, compare the printed name, gender, face, hair, voice, eye colour, makeup, the four colours, Hunter Rank,
  HR points, funds and play time with the character-select and status screens in game; the maintainer's three
  characters are the reference. The appearance fields come from mh4edit and have only this in-game check.
- **S3 (done):** for every used item-box, pouch and equipment slot, resolve the id in mh4edit's item and
  equipment lists; for every worn piece, check that its equipment-box index points at a record with the same
  kind and id. Pass: every id resolves and every count is inside 0 to 99; all 7 worn indices point at
  matching records on all three characters; the equipment kinds are 1 to 20. Item names are not written
  here (game data); the check reads them from the lists outside the repository, or from the game.
- **S4 (done):** read the ten guild-quest records. Pass: every used record's owner name is a decodable UTF-16
  name (the character's or another player's), every monster id is 0 to 123, and every level is 1 to 140; the
  records tile 0xDCA8 to 0xE888. The maintainer's mid-game character has all ten slots used, the other two
  have five.
- **S5 (done):** read the 56 Palico records. Pass: the used slots have decodable names and non-zero
  experience; the main Palico is at 0xC4B0 and the rest are the 55 records at 0xF338; the records tile
  0xC4B0 to 0xC598 and 0xF338 to 0x12510.
- **S6 (done):** read the 82 log entries. Pass: they tile 0x12E5C to 0x13190; every largest is at least its
  smallest (when both are non-zero); crowns are 0 to 13; the completed save's entries are full. A board post
  names the first entry's monster Seltas, whose MH4U id is 25, so the order is not the id order; what the
  order is stays unknown.
- **S7 (done):** read the guild-card block. Pass: the Hunter Rank and name at 0x12606 and 0x12608 equal the
  profile's; the three 14-u16 tables sit at 0x12796, 0x127B6 and 0x127D6, separated by four zero bytes, and
  their sums are in the same order of magnitude as the quest counts; the brigade-points field is at or below
  9,999,999. The mid-game character's arena weapon-usage sum is 2 and its arena quest count is 2. The
  meanings of the tables and counts remain unverified.
- **S8 (open):** the character save's quest clear lists.
  [#153](https://github.com/Cheeenxiii/mh-ultimate-collection/issues/153).
- **S9 (done):** decrypt three saved states of `system`: the maintainer's current one, the other copy in
  the DLC Save Data folder, and one the game wrote on a fresh SD card. Pass: each is 504 bytes; the
  fresh one's non-zero bytes are only 0x38 (1) and 0x3C (0xFFFFFFFF); the two saves with characters differ
  in exactly six bytes, at 0x04, 0x35 to 0x37, 0x40 and 0x64; the four u32 at 0x08 are identical in both.
  The differences are what the candidate rows above rest on; they do not name the fields.
- **S10 (open, in game):** the options, the guild-card list and the DLC/quest registration. The procedure is
  [docs/checks.md](../docs/checks.md#system-save-fields). Pass: each setting, guild card and DLC quest is
  placed in the table above with its own row and status, and `mhuc save dump` prints it.
