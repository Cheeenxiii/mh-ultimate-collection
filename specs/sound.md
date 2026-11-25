---
class: rLtSoundSourceADPCM, rLtSoundBank, rLtSoundRequest, rLtSoundStreamRequest, rMHSoundEmitter, rMHSoundSequence (MH4U, MH3U); rSoundSourceADPCM, rSoundBank, rSoundRequest, rSoundStreamRequest, rFestaSoundEmitter, rFestaSoundSequence, rSoundReverb, rSoundEQ (MHXX)
extension: mca (waves and music streams), and sound entries inside ARCs (banks, requests, emitters)
games: MH4U (from MHGU Definitive Edition's tools, EUR v1.1); MH3U and MHXX by class registry; every file's magic and version checked (SN1)
status: unverified
---

# Sound: waves, banks, requests, emitters

MT Framework Mobile plays sound through four resource kinds:
- a **wave** (mono or stereo Nintendo DSP-ADPCM);
- a **bank**, which groups waves under keys;
- a **request**, which is what game code asks for, by id;
- an **emitter** file, which places sound sources and reverb or EQ zones in a stage area.

Music is a long stereo wave played through a stream request (`.stq`).

Sources:
- The MH4U layouts below come from MHGU Definitive Edition (Scrimas, GPL-3.0-or-later): `tools/snd4u2gu.py` (waves, banks, requests), `tools/snd_bgm.py` (music streams) and `tools/snd_area.py` (emitters). It read them from MH4U EUR v1.1's RomFS and checked them against the MHGU files Capcom converted from the same 4U monsters.
- The class names and ids come from the engines' class registries: MH4UltimateDC `config/mt_classes.tsv` for MH4U, and this repository's `reference/games/mh3u/mt_classes.tsv` and `reference/games/mhxx/mt_classes.tsv` for the other two.

## Which class, which game

| Kind | MH4U | MH3U (3DS) | MHXX (3DS) | Source |
|---|---|---|---|---|
| wave | `rLtSoundSourceADPCM` 0x67195a2e, magic `MADP` | same class and id, magic `MADP` | `rSoundSourceADPCM` 0x79c47b59, magic `MADP` | registries; magics seen in every file (SN1) |
| bank | `rLtSoundBank` 0x14b5c8e6, magic `SNDB` | same | `rSoundBank` 0x15d782fb, magic `SBKR` | registries; magics seen in every file (SN1) |
| request | `rLtSoundRequest` 0x2618de3f, magic `SREQ` | same | `rSoundRequest` 0x1bcc4966, magic `SRQR` | registries; magics seen in every file (SN1) |
| stream request (music) | `rLtSoundStreamRequest` 0x3a6a5a4d, magic `STRQ` | same, magic `STRQ` | `rSoundStreamRequest` 0x167dbbff, magic `STQR` | registries; magics seen in every file (SN1) |
| area emitters | `rMHSoundEmitter` 0x68cd2933, magic `SES\0` | same class and id, but no file | `rFestaSoundEmitter` 0x2543b93e, magic `SES\0` | registries; magics seen in every file (SN1) |
| sequence | `rMHSoundSequence` 0x6e171a6e, magic `MSS\0` | same | `rFestaSoundSequence` 0x10ebe843, magic `MSS\0` | registries; magics seen in every file (SN1) |
| reverb, EQ | `rLtSoundReverb` 0x4a4b677c, magic `REV\0` (no EQ class) | same, magic `REV\0` | `rSoundReverb` 0x232e228c (`REVR`), `rSoundEQ` 0x2b40ae8f (`EQUR`) | registries; magics seen in every file (SN1) |
| category filter | `rLtSoundCategoryFilter` 0x7bea3086, magic `CFL\0` | same | none in its registry or RomFS | registries; SN1 |
| sound attribute se | `rSoundAttributeSe` 0x07437cce, an `XFS\0` container | same | none in its registry or RomFS | registries; SN1 |

MH3U's classes are MH4U's, with slightly smaller instance sizes, but the file versions are older (SN1). MHXX's ids are the same as MHGU Switch's in Definitive Edition's notes (`SBKR` 0x15d782fb, `SRQR` 0x1bcc4966, wave 0x79c47b59). That suggests Definitive Edition's 4U → GU rules, run in reverse, describe MHXX → MH4U; check S3 decides it.

## Versions and counts in the three games (SN1)

Every resource above starts with its magic, then a u32 version at 0x04; the survey prints a version below 0x100 in decimal, so MH4U's stream requests show as 34 (0x22). `mhuc survey` counted them in all three RomFS (check SN1), loose files and ARC entries together:

| Kind | MH4U | MH3U | MHXX |
|---|---|---|---|
| wave | 27,146 (`MADP` v5) | 10,132 (`MADP` v4) | 52,204 (`MADP` v5) |
| bank | 3,582 (`SNDB` v11) | 1,225 (`SNDB` v10) | 3,010 (`SBKR` v4) |
| request | 2,828 (`SREQ` v8) | 1,004 (`SREQ` v6) | 2,845 (`SRQR` v5) |
| stream request | 214 (`STRQ` 0x22) | 106 (`STRQ` 0x20) | 88 (`STQR` v4) |
| area emitter | 132 (`SES\0` 0x20120623) | 0 | 248 (`SES\0` 0x20160706) |
| sequence | 451 (`MSS\0` 0x20120123) | 240 (`MSS\0` 0x20110404) | 236 (`MSS\0` 0x20131015) |
| reverb | 82 (`REV\0`) | 26 (`REV\0`) | 119 (`REVR`) |
| category filter | 46 (`CFL\0`) | 9 (`CFL\0`) | 0 |
| EQ | 0 | 0 | 62 (`EQUR`) |
| sound attribute se | 8 (`XFS\0`) | 26 (`XFS\0`) | 0 |

Loose files, the rest being ARC entries: MH4U 571 waves, 13 banks, 16 requests and 50 stream requests; MH3U 289 waves, 106 stream requests and 94 sequences; MHXX 511 waves and 44 stream requests. Every ARC entry's class id was the one its magic's class has in that game's registry, so the class table above holds for every file counted.

What the versions say about conversion:

- **MH3U** has MH4U's classes but each file version is one older: wave 4 against 5, bank 10 against 11, request 6 against 8, stream request 0x20 against 0x22. 3U's sound needs readers for those versions or a conversion for all four kinds, not just new request ids; its RomFS holds no area emitter file at all.
- **MHXX**'s waves are `MADP` version 5, the version MH4U reads, but its banks and requests are the next generation's (`SBKR` 4, `SRQR` 5, the magics and versions of MHGU's in Definitive Edition's notes) and its stream requests are `STQR` version 4. Its waves may therefore convert as-is, while its banks and requests follow GU's layouts if S3 confirms them. Its area emitters are a different class on both sides (`rFestaSoundEmitter`, version 0x20160706, against `rMHSoundEmitter`, 0x20120623), and it has an EQ class where MH4U has none.

## Wave (`MADP`, version 5): header 0x60 bytes, then data

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MADP` | unverified | Definitive Edition snd4u2gu.py |
| 0x04 | u32 | version 5 | unverified | Definitive Edition snd4u2gu.py |
| 0x08 | u8[4] | 01 00 00 01 (channels and flags, meaning not traced) | unverified | Definitive Edition snd4u2gu.py |
| 0x0C | u32 | sample count | unverified | Definitive Edition snd4u2gu.py, snd_bgm.py |
| 0x10 | u32 | sample rate (sound effects 8000 to 22000 Hz; music 32728 Hz) | unverified | Definitive Edition snd4u2gu.py, snd_bgm.py |
| 0x14 | u32 | loop flag (effects); loop start (music) | unverified | Definitive Edition snd4u2gu.py, snd_bgm.py |
| 0x18 | u32 | loop start (effects); loop end (music) | unverified | Definitive Edition snd4u2gu.py, snd_bgm.py |
| 0x20 | u32 | data size, padded to 0x100 | unverified | Definitive Edition snd4u2gu.py, snd_bgm.py |
| 0x24 | f32 | length in seconds | unverified | Definitive Edition snd4u2gu.py, snd_bgm.py |
| 0x30 | s16[16] | DSP-ADPCM coefficients (mono waves) | unverified | Definitive Edition snd4u2gu.py |
| 0x50 | u16 ×4 | gain, predictor/scale, history 1, history 2 | unverified | Definitive Edition snd4u2gu.py |
| 0x60 | bytes | DSP-ADPCM frames (8 bytes each), mono effects | unverified | Definitive Edition snd4u2gu.py |

Music streams (stereo) differ: a seek table at 0x28 (entry count) and 0x2C (data offset), 20-byte entries from 0x30. After it come 0x30 bytes of coefficients and state per channel, and the data interleaves channels every 0x100 bytes (Definitive Edition snd_bgm.py, unverified).

## Wave (`MADP`, version 4)

MH3U's wave is one version older. Its header is 0x5C for a mono effect and 0x8C for a stereo music stream: a u32 at 0x28, then one 0x30-byte decoder block per channel, then the data. The decoder block is version 5's moved down by 4 bytes: the 16 coefficients at +0 and the four u16 at +0x20 that version 5 keeps at 0x50. Version 5's second u32 at 0x2C is gone; 0x28 packs a 0x3348 marker in its high half and the seek table's entry count in its low half. Unlike version 5, the seek table follows the data, 20 bytes per entry.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MADP` | verified | every MH3U wave (SN6) |
| 0x04 | u32 | version 4 | verified | every MH3U wave (SN6) |
| 0x08 | u8[4] | channels (1 mono effect, 2 stereo music), then 00 00 01 | verified | SN6: 697 mono and 289 stereo; the 290 music streams' channel counts equal their stream record's |
| 0x0C | u32 | sample count | verified | SN6: the length in seconds is samples / rate in every wave; a stream record repeats the count for the 290 music streams |
| 0x10 | u32 | sample rate | verified | SN6: the same check |
| 0x14 | u32 | loop flag (effects); loop start (music) | verified | SN6: 0 on every mono effect, and a stream record repeats the loop start for the 290 music streams |
| 0x18 | u32 | loop start (effects); loop end (music) | verified | SN6: the same check |
| 0x1C | u32 | data offset: 0x2C + 0x30 × channels | verified | every MH3U wave (SN6) |
| 0x20 | u32 | data size, a multiple of 0x100 | verified | every MH3U wave (SN6) |
| 0x24 | f32 | length in seconds | verified | SN6: equals samples / rate |
| 0x28 | u32 | high half 0x3348, low half seek table entry count | verified | SN6: the bytes after the data are 20 × the low half in every wave; 0 in 959 of the 986 waves sampled |
| 0x2C + 0x30 × i, +0x00 | s16[16] | channel i's DSP-ADPCM coefficients | verified | SN6: byte-identical to version 5's at 0x30 in the 31 waves whose audio both games ship |
| 0x2C + 0x30 × i, +0x20 | u16 ×4 | channel i's gain, predictor/scale, history 1, history 2 | verified | SN6: the same 31 pairs (version 5's at 0x50) |
| 0x2C + 0x30 × i, +0x28 | u8 ×8 | not traced; version 5's same bytes are junk | unverified | SN6 (histogram) |
| 0x2C + 0x30 × channels | bytes | DSP-ADPCM frames, then the seek table | verified | SN6: data offset + size + 20 × count = the file's length in every wave |

## Bank (`SNDB`, version 11)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SNDB` | unverified | Definitive Edition snd4u2gu.py |
| 0x04 | u32 | version 11 | unverified | Definitive Edition snd4u2gu.py |
| 0x08 | u32 | group record count | unverified | Definitive Edition snd4u2gu.py |
| 0x0C | u32 | entry count | unverified | Definitive Edition snd4u2gu.py |
| 0x10 | u32 | tail record count x; the tail is 8 × x bytes after the entries | unverified | Definitive Edition snd4u2gu.py; the MH4U banks read in SN6 close with it |
| 0x14 + 12 × i | u16, u16, u32, u32 | group i: id; flags (0x8000, plus category shifted left by 11, plus 2 × count); first entry; x | unverified | Definitive Edition snd4u2gu.py |
| +0x00 (entry) | char[], u32, 76 bytes | wave path (NUL-terminated); wave type id; parameters, a 4-byte key at +12 | unverified | Definitive Edition snd4u2gu.py |
| +0x00 (tail) | f32, u32 | one {value, index} record; the index's low byte is 0..x-1 | unverified | Definitive Edition snd4u2gu.py |

## Bank (`SNDB`, version 10)

MH3U's bank has the same container as version 11: a 0x14-byte header, 12-byte group records, one entry per wave (a NUL-terminated path, a u32 type id and 76 parameter bytes), then 8-byte tail records. In every MH3U bank read the counts and the sizes tile the file exactly (SN6).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SNDB` | verified | every MH3U bank (SN6) |
| 0x04 | u32 | version 10 | verified | every MH3U bank (SN6) |
| 0x08 | u32 | group record count | verified | SN6: the group records end where the entries begin |
| 0x0C | u32 | entry count | verified | SN6: the entries close on the tail |
| 0x10 | u32 | tail record count x; the tail is 8 × x bytes after the entries | verified | SN6: the tail ends the file |
| 0x14 + 12 × i, +0x00 | u16 | group i's id | unverified | SN6 (histogram) |
| 0x14 + 12 × i, +0x02 | u16 | group i's flags: 0x8000, a category in bits 11 to 14 and a count in the low bits; the low 15 bits are twice the group's 47 and 35 entries in Rathian's bank | unverified | SN6 (histogram) |
| 0x14 + 12 × i, +0x04 | u32 | group i's first entry | verified | SN6: 0 ≤ first ≤ the entry count in every group |
| 0x14 + 12 × i, +0x08 | u32 | not traced; 0 in every group read | unverified | SN6 (histogram) |
| entry +0x00 | char[] | wave path, NUL-terminated | verified | SN6: the entries tile the file between the groups and the tail |
| entry +len+1 | u32 | wave type id, `0x67195a2e` (`rLtSoundSourceADPCM`) | verified | SN6: every entry of every MH3U bank read |
| entry +len+5 | u8[76] | parameters; byte 2 is 8 and the 4-byte key at +12 is {lo, hi, root, 0} with lo = hi = root | unverified | SN6 (histogram); the same 76 bytes carry the same values as version 11 for the 33 waves both games ship |
| tail +0x00 | f32, u32 | one {value, index} record, 8 bytes; the index's low byte is 0..x-1 | verified | SN6: x records close every bank read |

## Request (`SREQ`, version 8)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SREQ` | unverified | Definitive Edition snd4u2gu.py |
| 0x04 | u32 | version 8 | unverified | Definitive Edition snd4u2gu.py |
| entries | 92 bytes each | one per request id: which bank key plays, with volume and parameters (field list in snd4u2gu.py) | unverified | Definitive Edition snd4u2gu.py |

## Area emitters (`SES\0`, version 0x20120623)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SES\0` | unverified | Definitive Edition snd_area.py |
| 0x04 | u32 | version 0x20120623 | unverified | Definitive Edition snd_area.py |
| 0x08 | u32 | record count n | unverified | Definitive Edition snd_area.py |
| 0x10 | {u32, u32} ×n | index and offset of each record | unverified | Definitive Edition snd_area.py |
| +0x00 (record) | u32 | low 16 bits index, high 16 bits request id | unverified | Definitive Edition snd_area.py |
| +0x04 (record) | u8 ×4 | shape (1 points, 2 polyline), point count, type (1 emitter, 3 reverb zone, 4 EQ zone), flag | unverified | Definitive Edition snd_area.py |
| +0x08 (record) | f32, u16, u16 | radius, near, far | unverified | Definitive Edition snd_area.py |
| +0x18 (record) | char[64] | path: the area bank (type 1) or the stage reverb or EQ file (types 3, 4) | unverified | Definitive Edition snd_area.py |
| then | vec4 ×points | positions | unverified | Definitive Edition snd_area.py |

## Stream request (`STRQ`): a stream table and a sequence table

The resource `rLtSoundStreamRequest` loads. A stream request names the waves one music context can play and maps a request id to one of them with a level. MH4U has 214: 50 loose `.stq` under `/sound/bgm` (`bgm_bat` for monster battle themes, `bgm_st_NN` for a stage, `str_mNN` for a locale's area streams, plus the common, download, event, lobby and system files) and 164 inside ARCs under `/data`, `/loc/data` and the other language data folders. Check S4 reads every one and checks the tables against all 50 loose files.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `STRQ` | verified | all 50 files (S4) |
| 0x04 | u32 | version 0x22 (34) | verified | all 50 files (S4); ours, the loader compares it at 0x00404530 |
| 0x08 | u32 | stream count | verified | all 50 files (S4); ours, the loader reads it at 0x00404564 |
| 0x0C | u32 | sequence count | verified | all 50 files (S4); ours, the loader reads it at 0x0040456C |
| 0x10 | u32 | stream table offset (0x18 in all 50) | verified | all 50 files (S4); ours, the loader reads it at 0x004045F0 |
| 0x14 | u32 | sequence table offset (0x18 + 36 n) | verified | all 50 files (S4); ours, the loader reads it at 0x00404574 |
| +0x00 (stream) | u32 | name offset from the file start; a NUL-terminated ASCII path, `sound\bgm\...`, without the `.mca` extension | verified | all 497 stream records (S4); ours, the loader uses it at 0x00404610 |
| +0x04 | u32 | the `.mca`'s file size in bytes | verified | 497 of 497 (S4) |
| +0x08 | u32 | sample count | verified | 497 of 497 (S4) |
| +0x0C | u32 | channels (2 for every music stream) | verified | 497 of 497 (S4) |
| +0x10 | u32 | sample rate (32728 Hz for every music stream) | verified | 497 of 497 (S4) |
| +0x14 | u32 | loop start in samples | verified | 497 of 497 (S4) |
| +0x18 | u32 | loop end in samples | verified | 497 of 497 (S4); 0 with a 0 loop start on the 268 loose streams that don't loop |
| +0x1C | u32 | source class id `0x67195a2e` (`rLtSoundSourceADPCM`) | verified | all 50 files (S4); ours, the loader copies it to runtime +0x28 at 0x00404738 |
| +0x20 | u32 | 2, meaning not traced | unverified | all 50 files (S4); ours, the loader copies it to runtime +0x2C at 0x00404730 |
| +0x00 (sequence) | u32 | request id | verified | all 1,154 loose sequence records (S4); Definitive Edition snd_bgm.py (ids 32 and 33 of `bgm_bat.stq`) |
| +0x04 | u32 | not traced; 0, 1, 2 or 4 in the loose files | unverified | S4 (histogram) |
| +0x08 | u32 | not traced; 0, 1, 5, 6, 9, 10 or 11 in the loose files | unverified | S4 (histogram) |
| +0x0C | u32 | not traced; 1 in every loose sequence | unverified | S4 (histogram) |
| +0x10 | u16 ×2 | not traced; the low half 0 or 1, the high half 0, 1, 2 or 3 | unverified | S4 (histogram) |
| +0x14 | u16 ×2 | not traced; the low half 0, 1 or 2, the high half 0, 1 or 2 | unverified | S4 (histogram) |
| +0x18 | u16 ×2 | not traced; the low half is 0x0114 or 0x0100 in most loose sequences, 0x0014, 0x011E, 0x0048, 0x0032 or 0x0132 in others; the high half 0xFFFF in most, 0x0003 or 0 | unverified | S4 (histogram) |
| +0x1C | u32 | not traced; 0 or 1 | unverified | S4 (histogram) |
| +0x20 | u32 | not traced; 0xFFFFFFFF in every loose sequence | unverified | S4 (histogram) |
| +0x24 (with a stream) | f32 | volume in dB: id 32 is 0.0 dB and id 33 is -0.9 dB in `bgm_bat.stq`; -16.0 to +1.5 dB across the 5,410 sequences with a stream | verified | Definitive Edition snd_bgm.py; S4 (range over every stream request) |
| +0x24 (without a stream) | f32 | the same word on a sequence without a stream: 0 in most, 20, 50, 55, 70 or 100 on 196 of the 7,839; the unit of those positive values isn't established | unverified | S4 (histogram) |
| +0x28 | f32 | not traced; -96.0 in every loose sequence | unverified | S4 (histogram) |
| +0x2C | u32 | not traced; 0 in all but two loose sequences (400 and -200) | unverified | S4 (histogram) |
| +0x30, 0x34 | u32 ×2 | not traced; 0 in every loose sequence | unverified | S4 (histogram) |
| +0x38, 0x3C, 0x40 | u32 ×3 | not traced; 0xFFFFFFFF in every loose sequence | unverified | S4 (histogram) |
| +0x44 | u32 | not traced; 0 in most loose sequences, 1,000 to 4,000 in 39 | unverified | S4 (histogram) |
| +0x48 | u32 | not traced; 0, 100, 500, 1,000 or 1,500 | unverified | S4 (histogram) |
| +0x4C | u32 | not traced; 0, 16 or 0x01000010 | unverified | S4 (histogram) |
| +0x50, 0x54, 0x58 | u32 ×3 | not traced; 0 in every loose sequence | unverified | S4 (histogram) |
| +0x5C | u32 | stream index into the stream table, `0xFFFFFFFF` for no stream | verified | all 1,154 loose sequence records (S4); Definitive Edition snd_bgm.py (ids 32 and 33 name streams 18 and 19); ours, the loader resolves it at 0x00404818 |
| +0x60 | u32 | stream pointer slot: 0 exactly when +0x5C is 0xFFFFFFFF, otherwise a build-time pointer (0x127F0144 to 0x1281964C) that the loader overwrites with the runtime stream object | verified | ours, the loader writes it at 0x00404830; S4 (zero on the 7,839 sequences without a stream, non-zero on the 5,410 with one) |

Stream records are 36 bytes and sequence records 100. The lookup compares the id at +0; the request ids are unique and ascending in every MH4U stream request, but sparse (the event files reach 773). The music streams are stereo DSP-ADPCM at 32728 Hz, so a stream record's +0x04 size equals the `.mca` file size and +0x08, +0x0C, +0x10, +0x14 and +0x18 equal its header's sample count, channels, rate, loop start and loop end: that is the check. What the ids select, and what a new monster theme has to add, is in [docs/audio.md](../docs/audio.md#how-mh4u-picks-a-monsters-theme).

## Checks (with game files)

- **SN1 (done, 2026-11-25):** `mhuc survey <romfs.bin>` on MH4U USA (cartridge), MH3U USA and MHXX JPN v1.0 counts every sound resource in its report's `sound` section, by kind, magic and version, and by class id inside ARCs. Result: the versions and counts table above. Every sound file in every game matched one magic and one version of its kind, and every ARC entry's class id was that game's registry class for the kind. MH3U's versions are not MH4U's: each is one older (wave 4 against 5, bank 10 against 11, request 6 against 8, stream 0x20 against 0x22), so 3U's files need version-aware readers or a conversion. MHXX keeps MH4U's wave version (5) but has GU's banks and requests (`SBKR` 4, `SRQR` 5), so only its waves may convert unchanged; S3 checks whether the GU layouts really fit. MH3U ships no area emitter file; MHXX's emitters are `rFestaSoundEmitter`, version 0x20160706.
- **SN2:** parse every MH4U `MADP`, `SNDB`, `SREQ` and `SES` with this layout. Count files whose sizes and offsets close exactly, and record the counts, never bytes. A field becomes verified when every file agrees.
- **S3:** MHXX's bank and request against Definitive Edition's GU layouts (`SBKR` v4, `SRQR` v5). SN1 already matches their magics and versions; if the layouts agree, the XX → 4U conversion is the 4U → GU rule run backwards. MHXX's wave is `MADP` version 5, MH4U's version and not GU's 2, so it needs no GU layout.
- **S4 (done, 2026-11-25):** parse every `.stq` of MH4U USA v1.3.0's RomFS, loose and inside ARCs. `mhuc stq <file>` reads one stream request; `mhuc survey <romfs.bin> --workers 1` reports S4 read 214 files (50 loose, 164 in ARCs), 5,120 streams and 13,249 sequences, 5,410 of them with a stream and 7,839 without. Every file closed exactly: magic `STRQ`, version 0x22, stream table at 0x18, sequence table at 0x18 + 36 n, names in stream order from the end of the sequence table to the file's end, and every stream index in range (the reader refuses anything else). Each stream record's size, sample count, channels, rate and loop start and end equal the `MADP` header of the `.mca` it names, 497 of 497 in the loose files. The with-game-files test reads every loose `.stq` and checks that the request ids are unique and ascending and that every stream is used. Still open: the sequence record's words marked unverified above, the lookup's index at `+0x94`/`+0x98` of the loaded resource, and `sSoundControl`'s loader `0x3099c8` at run time.
- **SN5 (done, 2026-11-25):** read the allocator setup in the MH4U USA v1.3.0 image instead of the files, to say where sound memory comes from. The heap table is at 0x00f2bb44: nine 0x18-byte records {name pointer, allocator index, type, size, flags, 0}, read by 0x0010612c; the alias table is at 0x00f2bc1c and holds seven {index, target index} pairs. The class-to-index table is built by the function at 0x00104904. Result: Resource (index 11) is 0x2F00000 = 47 MiB and receives every `cResource` subclass; SoundBuffer (21) is aliased to Resource; no heap is made for Sound (15), the index of `cMHSoundEmitter`, `cMHSoundSequence` and `nMHSoundSequence`, which therefore allocate from the default heap. The sound resource classes have no entry of their own and their parent is `cResource`. The shipped `/memory.ini` `[Allocators: CTR]` agrees: Resource 47MB, `SOUND_BUF = RESOURCE`, no SOUND. Unverified: that the index lookup follows a class's parent (the table has 128 rows for 992 classes); the sound resource classes are assumed to take `cResource`'s index, and nothing was run to watch an allocation. Sizes and the largest monster sets: [audio.md](../docs/audio.md#memory).
- **SN6 (in progress, 2026-11-25):** read every MH3U wave, bank, request and stream request with `mhuc` and check each layout against the files; the procedure and the full RomFS counts are below once all four readers exist. Wave evidence: `sound.read_wave` accepted 986 MH3U waves (289 loose, 697 in six ARCs); in every one the data offset was 0x2C + 0x30 × channels, the data size a multiple of 0x100, the length in seconds samples / rate, and the bytes after the data 20 × the seek count. 31 waves of Rathian's MH3U arc are also in MH4U (same wave name, DSP data byte-identical to MH4U's): every one had the same 0x08..0x24 fields, and its coefficients and state at 0x2C..0x53 were byte-identical to MH4U's at 0x30..0x57.
