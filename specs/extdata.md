---
class: none (save-side files); the Palico record is the DLC `.otb`
extension: Extra Data files card1..card3, cardbox, otomo1; `.otb`
games: MH4U (USA layout, checked on the maintainer's own Extra Data); MH3U sizes only
status: unknown
---

# MH4U Extra Data besides quests

Downloaded quests (`quest1`..`quest5`) are in specs/quest.md. This page covers the other Extra Data files: the guild-card files `card1`..`card3`, `cardbox` and the DLC Palicos' `otomo1`. All are encrypted with mhef's `SavedataCipher` (quest.md check Q4): mode `card` for `card*`, `normal` for the rest. Offsets below are in the **decrypted** file, as `mhuc decrypt mh4u-save` writes it: the cipher's seed word and checksum are gone, so a `card*` file's 24-byte clear header becomes 16 bytes.

The Blowfish key `SavedataCipher` uses is a NUL-terminated string in the game's own code: MHGU Definitive Edition reads it from the European v1.1 code at 0xE05E04 (`tools/extdata4u.py`), so a player can take it from their own dump rather than from mhef. USA v1.3.0 keeps it at the same address, 0xE05E04, the only copy in its code; taken there, it decrypts the maintainer's `system`, character saves and every Extra Data file (`card*` in mode `card`, `quest*` in mode `quest`, `cardbox` and `otomo1` in mode `normal`), each checksum matching.

Sources: the mhff wiki (svanheulen/mhff, GPL-3.0) pages "MH4U card1 Format", "MH4U Guild Quest Structure", "MH4U Equipment Structure" and "MH4U DLC Palico Format", credited in specs/README.md. Reader: `mhuc extdata dump|check card|otomo FILE` (`src/mhuc/extdata.py`).

Why it matters to the mod: `otomo1` is a second place, after the quest slots, where the game takes whole DLC records from Extra Data. A mod Palico (a GU-era Palico, say) could go in this way without touching the RomFS. A guild quest is a 304-byte record that names its monsters and maps by id, so it may be a cheap way to put a new monster on a known map once ids grow.

## Files

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| file | 494,592 bytes (494,584 decrypted) | `card1`..`card3`: guild cards and the rest of the table below | verified | ours; quest.md checks Q3, Q4; check E1 |
| file | 270,336 bytes (270,328 decrypted) | `cardbox`: empty in the maintainer's data, so no layout | unknown | ours; check E1 |
| file | 8,704 bytes (8,696 decrypted) | `otomo1`: DLC Palicos, table "otomo1" below | verified | ours; check E2 |
| file | 512 bytes (504 decrypted) | the save's `system`: small, mostly zero; its mapped fields are in [save.md](save.md#system-save) | unknown | ours; checks E1, S9 |
| file | 360,448, 196,608 and 12,288 bytes | MH3U 3DS: `card1`..`card3` and `cardbox` (all zero here), the save's `system` (plain, 37 non-zero bytes in the first 0x78) | verified | ours; check E3 |

## card1..card3 (decrypted)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00000 | 16 bytes | header (the clear part of the encrypted file's 24 bytes, after the seed and checksum words) | unverified | mhef `SavedataCipher`; mhff wiki |
| 0x00010 | 4,608 bytes ×100 | guild cards | unverified | mhff wiki |
| 0x70810 | 64 bytes ×100 | unknown, one per guild card | unknown | mhff wiki |
| 0x72110 | 304 bytes ×50 | unregistered guild quests (table below) | unverified | mhff wiki |
| 0x75C70 | 86 bytes ×40 | equipment sets | unverified | mhff wiki |
| 0x769E0 | 156 bytes ×24 | item sets | unverified | mhff wiki |
| 0x77880 | 36 bytes ×24 | unknown sets | unknown | mhff wiki |
| 0x77BE0 | 64 bytes ×18 | shoutouts | unverified | mhff wiki |
| 0x78060 | 64 bytes ×6 | automatic shoutouts: mount, pinned, bomb, slept, stunned, faint | unverified | mhff wiki |
| 0x781E0 | 2,584 bytes | unknown, to the end of the file (0x78BF8) | unknown | mhff wiki; check E1 |

The wiki lists the guild cards at 0x18 and the next table at 0x70810. Those two disagree by 8 bytes; every later offset, and the file's end, only fit a 16-byte header, as above (check E1). The wiki counted the encrypted file's header.

## Guild quest (304 bytes)

No guild quest was in the maintainer's data, so every row is unverified.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x000 | 24 bytes | original owner's name (UTF-16 presumably) | unverified | mhff wiki |
| 0x018 | 8 bytes | unique id | unverified | mhff wiki |
| 0x020 | u16 | unknown | unknown | mhff wiki |
| 0x022 | u8 ×3 | Poogie or Felyne, Poogie type, its area | unverified | mhff wiki |
| 0x025 | u8 ×3 | biases: weapon type, armour series, armour piece | unverified | mhff wiki |
| 0x028 | 40 bytes ×5 | large monsters: **u8 monster id** at +0, u8 spawn area at +9, the rest unknown | unverified | mhff wiki |
| 0x0F0 | 7 bytes ×5 | per monster: other area, sleep area, 5 spawn subareas | unverified | mhff wiki |
| 0x113 | u8 | unknown | unknown | mhff wiki |
| 0x114 | 4 bytes ×5 | areas: map id at +1, entrance at +2, exit at +3 | unverified | mhff wiki |
| 0x128 | u8 ×3 | initial level, current level, treasure area | unverified | mhff wiki |
| 0x12B | u8 ×5 | per monster: frenzy bits (bit 0 normal start, bit 1 frenzy, bit 4 apex) | unverified | mhff wiki |

The monster id is one byte here, so a guild quest can name ids up to 255 (reference/README.md#mh4u-monster-tables).

## otomo1 (decrypted)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x000 | 0x90 bytes ×9 | Palico slots, in download order; a slot is used when its name field is | verified | ours; check E2 |
| after the last used slot | 12 bytes | the tail of that slot's server file: its SHA-1 bytes 16..19, the 4 padding bytes as the server file's ciphertext, the plaintext size 0x94 (0x80 + 20) as a u32 BE (at 0x510 here, after the ninth slot) | verified | ours; check E6 |
| 0x51C | to 0x21F8 | zeros | verified | ours; check E2 |

## Palico slot (0x90 bytes)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | variable | the `.otb` record (table below), 112 to 124 bytes here | verified | ours; check E2 |
| record end | to 0x80 | zeros | verified | ours; check E2 |
| 0x80 | 15 bytes | the record's file name, `otNNN_<lang>.otb`, NUL-padded (as a quest slot ends with `mNNNNN.mib`) | verified | ours; check E2 |

How the slots come about (check E6): the game decrypts each server file up to its stated size, as it does for quests (specs/quest.md Q16): the record padded to 0x80, its SHA-1, 4 padding bytes, the size, 0x98 bytes in all. It writes that at a stride of 0x90, so the next slot overwrites the last 8 bytes, and puts the 15-byte name at 0x80, over SHA-1 bytes 0..14. Byte 15 of the hash is what's left at 0x8F, and only the last slot keeps its full tail. `mhuc extdata rename` and `extdata.put_otomo_slot` write a slot that way.
| 0x8F | u8 | byte 15 of the SHA-1 of the record zero-padded to 0x80 bytes | verified | ours; check E6 |

## `.otb` record

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 ×2 | unknown (0 in all 9) | unknown | mhff wiki; check E2 |
| 0x08 | u8 | level (5 in all 9) | unverified | mhff wiki; check E2 |
| 0x09 | u8 ×2 | unknown (0 and 1 in all 9) | unknown | mhff wiki; check E2 |
| 0x0B | u8 | forte (1 to 7) | unverified | mhff wiki; check E2 |
| 0x0C | u8 ×3 | quest skills (each slot keeps its own value range; 0x0E is 50 in all 9) | unverified | mhff wiki; check E2 |
| 0x0F | u8 | signature skill (9 different values, 73 to 81) | unverified | mhff wiki; check E2 |
| 0x10 | u8 ×3 | Meownster Hunter, casting and team-attack skills | unverified | mhff wiki; check E2 |
| 0x13 | u8 ×6 | coat, clothing, voice, eyes, ears, tail | unverified | mhff wiki; check E2 |
| 0x19 | u8 | Palico id (0 to 4 here) | unverified | mhff wiki; check E2 |
| 0x1A | u8 ×2 | unknown (12 or 24; then small values) | unknown | mhff wiki; check E2 |
| 0x1C | u8 ×4 | coat RGB, then 0xFF | verified | mhff wiki; check E2 (terminator) |
| 0x20 | u8 ×4 | clothing RGB, then 0xFF | verified | mhff wiki; check E2 (terminator) |
| 0x24 | u32 | offset of the text table | verified | mhff wiki; check E2 |
| 0x28 | UTF-16 | strings, NUL-terminated, in the order owner, name, greeting; each next string starts at the first multiple of 8 past the previous one's end + 1, and the text table at the first multiple of 4 past the greeting's end + 1 | verified | ours; check E2 (all 9 records rebuild byte for byte) |
| text table | u32 ×3 | offsets of the owner, name and greeting strings | verified | mhff wiki; check E2 |

## Open

- Whether the game checks the hash byte at 0x8F, or the tail, when it lists the Palicos (check E4). Both are understood (E6), so a mod Palico can be written in the game's form either way. Decrypting the server's `.otb` files (goshawk mirror) would confirm that each record is stored as sent; their size trailers (148 = 0x80 + 20) and the matching padding bytes already point that way.
- The stored Palicos are the `_ger` files. Check that this Extra Data comes from the same game as the base (MH4U USA v1.3.0): a European game, or a system in German, would explain it.
- Guild cards (4,608 bytes) have no MH4U layout; mhff's "MHGen Guild Card Structure" is a later game's.

## Checks

Run on 2026-11-23 in a web session, on the maintainer's own MH4U Extra Data and MH3U 3DS Extra Data and saves, uploaded by them and kept outside the repositories. Decrypted with `mhuc decrypt mh4u-save` and mhef's key (in mhef's `mhef/n3ds.py`, not in this repository).

- **E1 (done):** decrypt `card1`..`card3` in mode `card`, `cardbox` and `system` in mode `normal`. Pass: the sizes above; `extdata.card_layout_problems()` is empty, so the sections tile the 494,584 bytes with a 16-byte header; `mhuc extdata check card` reports 0 used records in every section of all three files (the maintainer's cards are empty); `cardbox` is all zero.
- **E2 (done):** decrypt `otomo1` in mode `normal`, then `mhuc extdata dump otomo`. Pass: 9 slots of 0x90 bytes read without error; each record's colour terminators are 0xFF, its text table points at three NUL-terminated UTF-16 strings in the record, the bytes after the record are zero up to 0x80, and the name field reads `ot001_ger.otb` to `ot009_ger.otb` in slot order. The value spreads in the `.otb` table come from those 9 records. `extdata.set_otb_texts` with each record's own strings rebuilds all 9 byte for byte, which confirms the padding rule.
- **E3 (done):** `mhuc entropy` on the MH3U 3DS Extra Data and save `system`. Pass: all plain; `card*` and `cardbox` all zero.
- **E4 (open, in game):** back up the Extra Data, then `mhuc decrypt mh4u-save otomo1 o.bin --key K`, `mhuc extdata rename otomo o.bin --slot 0 --name Testname --out o2.bin`, `mhuc encrypt mh4u-save o2.bin otomo1 --key K` and put `otomo1` back with a save manager (Checkpoint, JKSM). Open the DLC Palico list in game. Pass: the first Palico shows as Testname. `rename` recomputes the hash byte at 0x8F (and the tail, for the last slot). Then repeat with `--last-byte` set to any other value: if that Palico disappears or the game reports corrupt data, the game checks the byte; if it loads, it doesn't.
- **E6 (done):** for each of the 9 slots, hash the first 0x80 bytes with SHA-1; compare the 12 bytes after the ninth slot with the goshawk mirror's still-encrypted `ot009_ger.otb` (compared as stored, nothing decrypted). Pass: every slot's byte 0x8F is byte 15 of its hash (other bytes of the hash, sums, XORs, CRC-32 and Adler-32 of the record, slot or name had failed); the tail is that hash's bytes 16..19, then the server file's bytes 148..151 (its padding), then 0x94 as a u32 BE; the mirror's 45 `.otb` files are all 156 bytes with the size trailer 148. `extdata.otomo_problems` is empty on the maintainer's `otomo1`, and stays empty after `rename` on the first or the last slot.
- **E5 (done):** decrypt `otomo1` (normal), `quest1` (quest) and `card1` (card), then encrypt each again with `mhuc encrypt` and the seed read from the file's first word. Pass: all three come out byte-identical to the originals, so a file `mhuc` writes is in the exact form the game wrote (the quest file's last 0x100 bytes are zero in the original too). `tests/test_with_game_files.py::test_extra_data_files_reencrypt_byte_for_byte` runs it over a folder of `quest*`, `card*` and `otomo1`, and skips when `MHUC_DUMPS` holds none.
