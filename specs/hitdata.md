---
class: rBodyData, rHitSize, rHitDataEnemy (MHXX), rHitData (MH3U)
extension: bodydata, cambodydata, hitsize, attackdata (MHXX enemy\body_data, cam_body_data, hit_data); em_body00, em_cambody00, em_hitsize00, em_hitdata00 (MH3U enemy\emNNN)
games: MH3U (USA), MHXX (JPN v1.0 RomFS, v1.4 code)
status: unknown
---

# Hurt volumes, attack volumes and attack records in MH3U and MHXX

What MH4U keeps inside its `.emd` (body records, words 8 and 9) and `.etd` (attack volumes, word 27; attack records, word 28) the source games keep in files of their own, one set per monster. The `rBodyData` and `rHitSize` classes are shared with other owners (players, shells); this spec covers the monsters' files in `arc/enemy/`.

**Layout.** Each file is a 16-byte header and records:

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic: `BDD\0`, `HTS\0`, `HDE\0` (MHXX), `HTD\0` (MH3U) | verified | ours, loaders (MHXX `rBodyData` slot 11 0x009f60f4, `rHitDataEnemy` 0x003d2650); check E4 |
| 0x04 | u32 | version: BDD 0x20110219 in both games; HTS 0x20110212 (MH3U), 0x20131015 (MHXX); HDE 0x20160121; HTD 0x20110209 | verified | ours, loaders; check E4 |
| 0x08 | u32 | count: records (BDD without its closing record, HDE, HTD) or groups (HTS) | verified | check E4 |
| 0x0C | u32 | 0 | verified | check E4 |

The loaders copy the file whole and check the magic and the version; the game reads records through accessors, not the loader, so the record sizes below are the ones that tile every file exactly (check E4).

## BDD: hurt volumes (`bodydata`, `cambodydata`)

`count` + 1 records of 44 bytes from 0x10: the last one is the end, its first u16 0xFFFF. The record is MH4U's body record (specs/emd.md, "Body record").

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | u16 | bone A (0xFFFF ends the list) | verified | specs/emd.md; check E4 (every file ends so), E5 |
| +0x02 | u16 | bone B. MHXX writes 0xFFFF where MH4U writes 0 when the shape isn't 2 (2,599 of MHXX's 3,401 such records); MH3U never writes 0xFFFF | verified | check E5 (equal to MH4U's once 0xFFFF is read as 0, on the three monster pairs of specs/dttune.md) |
| +0x04 | u16 | shape: 0, 1, 2 (and 6 in 3 MHXX records) | verified | specs/emd.md; check E4 (histogram), E5 |
| +0x06 | u16 | hitzone row: an index into the hitzone table of `dttune` / `em_status00`; below 8 in every MH3U record and in all but 8 of MHXX's 4,653 | verified | specs/emd.md; check E5 (equal on the three pairs) |
| +0x08 | u16 | part index; below 8 in every MH3U record and in all but 23 of MHXX's | verified | specs/emd.md; check E5 (equal on the three pairs) |
| +0x0A | u16 ×3 | flags | unverified | specs/emd.md; check E5 (equal in 123 of 124 records on the three pairs) |
| +0x10 | f32 | radius | verified | specs/emd.md; check E5 (equal in every record on the three pairs) |
| +0x14 | f32 ×3 | off1 | verified | specs/emd.md; check E5 (equal in 121 of 124) |
| +0x20 | f32 ×3 | off2; MHXX zeroes it on spheres where MH4U keeps a value | verified | specs/emd.md; check E5 (equal in 119 of 124) |

On the three pairs, MHXX's hurt volumes rebuild MH4U's 116 of 124 records exactly. MH3U's are on MH3U's skeleton: none of Rathian's 28 equals one of MH4U's 32 (MH4U remade the model).

## HTS: attack volumes (`hitsize`)

After the header, `count` pairs (u32 records, u32 offset), then the groups' records in order; each group starts where the previous one ends and the last ends at the file's end.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| table | u32, u32 | records in the group, offset of its first record | verified | check E4 |
| MH3U record, 40 bytes | | MH4U's attack volume record (specs/emd.md, `.etd` word 27), except bytes 8..11, which are non-zero in every MH3U record and 0 in MH4U's | unverified | check E5 (22 of Rathian's 31 records in her first 18 groups equal MH4U's without bytes 8..11) |
| MH3U count | | includes the group's closing record (first u16 0xFFFF), as MH4U's lists end; every non-empty group ends with one | verified | check E4 |
| MHXX record, 48 bytes | | MH4U's 40-byte record with 4 bytes inserted at +28 (the capsule's far end moves from +28 to +32) and 4 bytes at the end; both inserted words are 0 in every MHXX record | verified | MHGU-DE `emdata4u.hitsize`; checks E4, E5 (35 of 38 records equal on Rathian, 60 of 60 on Kushala, 83 of 83 on Teostra) |
| MHXX count | | no closing record; MHXX adds one empty group after MH4U's | verified | check E5 |

## HDE: MHXX attack records (`attackdata`)

`count` records of 32 bytes from 0x10.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | 28 bytes | MH4U's attack record bytes 0..27 (specs/emd.md, `.etd` word 28), except byte 18 | verified | MHGU-DE `emdata4u.attackdata`; check E5 |
| +0x12 | u8 | bits 0-1 of MH4U's byte 18, its third byte at +0x12 (the higher bits, the knockback bits, are at +0x1F; specs/emd.md, "Attack record") | verified | MHGU-DE `emdata4u.attackdata`; check E5 |
| +0x1C | u8 | a kind: 6 to 10, or 0xFE on an empty record (0xFF in 39 records); MH4U's byte 28 is mostly 0 | unknown | MHGU-DE `emdata4u.attackdata`; check E4 (histogram) |
| +0x1D | u8 | MH4U's byte 29 | verified | check E5 |
| +0x1E | u8 | not in MH4U's record (non-zero in 654 of 4,805) | unknown | check E4 |
| +0x1F | u8 | MH4U's byte 18 shifted right by 2 | verified | MHGU-DE `emdata4u.attackdata`; check E5 |

Rebuilt into MH4U's layout (`mhuc monsterdata`), MHXX's records equal MH4U's on bytes 0..27 and 29 in 48 of Rathian's 55, 25 of Kushala's 37 and 38 of Teostra's 46. MH4U's bytes 30..39 have no MHXX counterpart: Teostra sets byte 32 in 40 records, so whole records match in 4 of 46 only. MHXX adds records after MH4U's (Rathian 64 against 55).

## HTD: MH3U attack records (`em_hitdata00`)

`count` records of 32 bytes from 0x10. The game fetches one by attack id: `rHitData`'s loader (slot 11, 0x951d8c) checks the magic and puts the records at the object's +0x64, and the monster's attack setup (0x844a40) reads record `base + attack id × 32` and copies it into a 124-byte attack state. The setup reads the volume group and the two times itself and calls 0x987d50 for the rest; 0x987d50 is shared by the monster, player and shell setups.

**Placement.** The offsets below are the game's own readers'. E4 checks the 32-byte stride on every file (125 HTD files) and E8 checks the values MH4U shares. A field E8 does not reach is unverified even though a reader places it; a byte no reader touches is unknown.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| +0x00 | s16 | time A: 0x844a40 compares it with the monster's animation time and starts the attack's time window at the attack state's +0x3c | verified | ours, 0x844a40; check E8 (bytes 0x00-0x11) |
| +0x02 | s16 | time B: the window's length, to the attack state's +0x40 as a float | verified | ours, 0x844a40; check E8 |
| +0x04 | s16 | read as a signed value, converted to a float, to the attack state's +0x44 | verified | ours, 0x987d50; check E8 |
| +0x06 | u8 | attack kind, to the attack state's +0x48 | verified | ours, 0x987d50; check E8 |
| +0x08 | u16 | flags, to the attack state's +0x4a | verified | ours, 0x987d50; check E8 |
| +0x0a | u8 | to the attack state's +0x4c | verified | ours, 0x987d50; check E8 |
| +0x0b | u8 | to the attack state's +0x4d | verified | ours, 0x987d50; check E8 |
| +0x0c | u16 | to the attack state's +0x4e; MH4U widens it to a u32 at +0x0c | verified | ours, 0x987d50; check E8 |
| +0x0e | u16 | 0 in every Rathian record; no reader reads it | unknown | ours, 0x987d50 |
| +0x10 | u32 | to the attack state's +0x50; MH4U carries bytes 0x10-0x11 only | unverified | ours, 0x987d50; check E8 |
| +0x14 | u8 | converted to a float, to the attack state's +0x54 | unverified | ours, 0x987d50; check E8 |
| +0x15 | u8 | attack-volume group: index into `rHitSize`'s group pointer table at the object's +0x64, whose count is the HTS header's count (loader 0x951f64) | verified | ours, 0x844a40; check E8 (below the group count and equal to MH4U's +0x19) |
| +0x16 | u8 | to the attack state's +0x5a as a u16; MH4U's +0x1a is one more in 42 of Rathian's 45 records | verified | ours, 0x987d50; check E8 |
| +0x17 | u8 | to the attack state's +0x5c | unverified | ours, 0x987d50 |
| +0x18 | s8 | to the attack state's +0x5d, clamped at 0; MH4U's +0x1d carries it | verified | ours, 0x987d50; check E8 |
| +0x19 | u8 | 0xff means the default, else converted to a float at the attack state's +0x60 | unverified | ours, 0x987d50 |
| +0x1a | u8 | 0xff means the default, else converted to a float at the attack state's +0x64 | unverified | ours, 0x987d50 |
| +0x1b | u8 | to the attack state's +0x68 | unverified | ours, 0x987d50 |
| +0x1c | u8 | to the attack state's +0x69 | unverified | ours, 0x987d50 |
| +0x1d | u8 | to the attack state's +0x6a | unverified | ours, 0x987d50 |
| +0x1e | u8 | to the attack state's +0x6c | unverified | ours, 0x987d50 |
| +0x1f | u8 | 0 in every Rathian record; no reader reads it | unknown | ours, 0x987d50 |

**What MH4U carries.** MH4U's 40-byte record (specs/emd.md, `.etd` word 28) is a later layout, read by MH4U's own setup (0xb6d09c and 0xb700a8). Only part of the HTD record comes back:

| MH3U | MH4U | Rathian (of 45) | other shared monsters |
|---|---|---|---|
| bytes 0x00-0x11 | bytes 0x00-0x11 | 19 | Diablos 41/46, Deviljho 48/67, Great Jaggi 8/8, Lagombi 12/30 |
| +0x0c u16 (+0x0e u16 high) | +0x0c u32 | 45 | the high u16 is 0 in the same files |
| +0x15 group | +0x19 group | 38 | Diablos 46/46, Deviljho 67/67, Great Jaggi 8/8, Lagombi 30/30 |
| +0x16 u8 | +0x1a u16, one more | 42 | Diablos 46/46, Deviljho 66/67, Great Jaggi 8/8, Lagombi 30/30 |
| +0x18 s8 | +0x1d s8 | 37 | Diablos 46/46, Deviljho 67/67, Great Jaggi 8/8, Lagombi 30/30 |

The rest of MH3U's tail (+0x10's high u16, +0x14, +0x17, +0x19..+0x1e) has no MH4U counterpart at those offsets, and MH4U's bytes +0x10..+0x17 (a u16, two bytes and a byte; specs/emd.md, "Attack record"), +0x18, +0x1c and +0x20..+0x27 are not in MH3U's record: MH4U retuned or remade that part. The pairs are the same monster by name, not the same id: MH3U em001/MH4U em001 (Rathian), em012/em015 (Great Jaggi), em006/em100 (Diablos), em007/em042 (Deviljho) and em043/em047 (Lagombi). The games' monster-name tables give the ids, and the files' hitzones agree for all five.

`mhuc monsterdata` rebuilds MH4U's record from MH3U's where the table says it can: bytes 0x00-0x11 as they are, the group at +0x19, the +0x16 value one more at +0x1a, and the signed byte at +0x1d; the bytes with no counterpart stay 0. On Rathian 12 of the 55 MH4U records come back whole, and 19 on the shared bytes.

## Checks

- **E4 (done, MHXX JPN v1.0 and MH3U USA RomFS):** `mhuc survey` counts, per kind and version, the files whose records tile the file exactly (`E4 … tiles the file`) and those that don't. Results: every file tiles: MHXX 314 BDD entries (309 distinct files), 542 HTS, 151 HDE; MH3U 182 BDD, 125 HTS, 125 HTD; every BDD list and every MH3U attack volume group ends with its 0xFFFF record. The histograms quoted above come from the same files, read with `mhuc.formats.hitdata`.
- **E5 (done):** `mhuc monsterdata` (specs/dttune.md, specs/emstatus.md) rebuilds MH4U's body records, attack volumes and attack records from these files and counts the equal records. Results are in the tables above.
- **E8 (done, MH3U USA RomFS and the shared monsters):** two runs. `mhuc survey` counts `E8 htd volume group below the HTS group count` for every MH3U archive that holds both a hitdata and a hitsize file: 119 archives (85 monsters and 34 shells), 2,656 records, every group index below its file's HTS group count and none outside, which places the +0x15 group index against that table. `mhuc monsterdata --mh4u data/em_data.arc --id em001 --mh3u arc/enemy/em001.arc` prints, per field, how many of MH3U's records rebuild MH4U's: on Rathian bytes 0x00-0x11 19 of 45, the group 38 of 45, the +0x16 value one more at +0x1a 42 of 45 and the signed byte at +0x1d 37 of 45. The same command with `--id em015`/`arc/enemy/em012.arc` (Great Jaggi), `--id em100`/`arc/enemy/em006.arc` (Diablos), `--id em042`/`arc/enemy/em007.arc` (Deviljho) and `--id em047`/`arc/enemy/em043.arc` (Lagombi) gives the counts in the table above.
