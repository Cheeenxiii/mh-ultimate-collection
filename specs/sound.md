---
class: rLtSoundSourceADPCM, rLtSoundBank, rLtSoundRequest, rLtSoundStreamRequest, rMHSoundEmitter, rMHSoundSequence (MH4U, MH3U); rSoundSourceADPCM, rSoundBank, rSoundRequest, rSoundStreamRequest, rFestaSoundEmitter, rFestaSoundSequence, rSoundReverb, rSoundEQ (MHXX)
extension: mca (waves and music streams), and sound entries inside ARCs (banks, requests, emitters)
games: MH4U (from MHGU Definitive Edition's tools, EUR v1.1); MH3U and MHXX by class registry; every file's magic and version checked (SN1); the monster sound set and the conversion checked (SN7, SN9)
status: unknown
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

## Sizes (SN7)

[Check SN7](#checks-with-game-files) sums every sound resource's decompressed size, loose and inside ARCs, in the three images, and each monster's complete set. The counts are SN1's:

| Kind | MH4U | MH3U | MHXX |
|---|---|---|---|
| bank | 3,582 / 9,313,817 B | 1,225 / 3,083,367 B | 3,010 / 8,488,973 B |
| request | 2,828 / 6,332,267 B | 1,004 / 2,588,121 B | 2,845 / 7,048,989 B |
| wave | 27,146 / 1,132,574,464 B | 10,132 / 643,930,632 B | 52,204 / 977,940,320 B |
| stream request | 214 / 1,690,288 B | 106 / 515,826 B | 88 / 202,780 B |
| sequence | 451 / 6,214,815 B | 240 / 6,195,594 B | 236 / 5,539,452 B |
| area emitter | 132 / 80,704 B | 0 | 248 / 160,372 B |
| reverb | 82 / 35,084 B | 26 / 8,760 B | 119 / 69,188 B |
| category filter | 46 / 10,212 B | 9 / 472 B | 0 |
| EQ | 0 | 0 | 62 / 14,520 B |
| sound attribute se | 8 / 17,954 B | 26 / 49,634 B | 0 |

No bank is large: the biggest in any game is 32,862 B (MH4U's `em114`), and the banks do not grow with the game — MH3U's largest is 21,664 B, an NPC bank. Some ARC entries under `sound/` carry a class id that is in neither registry: MH4U has 10 (142,200 B: `sound/initial` and `sound/initial_d` in each language's `core_common.arc`), MH3U none, and MHXX 389 (1,188,350 B, 386 of them under `sound/pts/`). They are not one of the kinds above.

A monster's complete set is its bank, request and waves, the three kinds MH4U's monster ARCs were counted by before: MH4U 123 sets / 232 banks / 4,083,511 B, MH3U 58 / 59 / 460,410 B, MHXX 137 / 260 / 4,295,309 B. The largest set is 1,583,089 B (MH4U), 1,774,774 B (MH3U) and 3,349,540 B (MHXX), 3.2 %, 3.6 % and 6.8 % of the 47 MiB Resource heap. Where a monster's sound sits in each game: [audio.md](../docs/audio.md#what-a-monsters-own-sounds-are); the heap accounting: [audio.md](../docs/audio.md#how-much-the-three-games-monster-banks-use).

What the versions say about conversion:

- **MH3U** has MH4U's classes but each file version is one older: wave 4 against 5, bank 10 against 11, request 6 against 8, stream request 0x20 against 0x22. `mhuc` now reads those four older layouts (SN6) and the tables below lay them out. A 3U monster's whole sound set converts to MH4U's versions (`mhuc convert monster`, SN9); 3U music streams and area sounds are still unconverted. Its RomFS holds no area emitter file at all.
- **MHXX**'s waves are `MADP` version 5, the version MH4U reads, but the header is not MH4U's: the data starts at 0x68, the coefficients at 0x38 and the file ends 24 bytes after the data (check SN7). They need a conversion, not a copy. Its banks are the next generation's (`SBKR` 4) and match MHGU's; its requests are `SRQR` 5 but **do not** use MHGU Switch's 132-byte records: MHXX's are 100 bytes (check S3). Its stream requests are `STQR` version 4. Its area emitters are a different class on both sides (`rFestaSoundEmitter`, version 0x20160706, against `rMHSoundEmitter`, 0x20120623), and it has an EQ class where MH4U has none.

## A monster's sound set, and how the record points to it (SN7)

MH4U's monster resource record has one sound path at +0x1c
([reference](../reference/README.md#mh4u-monster-tables)), `sound\call\em\emNNN`. It names the
**sound call** (`rMHSoundSequence`, `MSS`), and the call names the rest by RomFS path, in a chain:

| Kind | Class | MH4U path | Named by |
|---|---|---|---|
| sound call | `rMHSoundSequence` | `sound\call\em\emNNN` | the monster's resource record +0x1c |
| request | `rLtSoundRequest` | `sound\se\em\emNNN\snd_emNNN` | the sound call |
| bank | `rLtSoundBank` | the request's base path, `...\snd_emNNN` | the request's string table |
| waves | `rLtSoundSourceADPCM` | `sound\se\em\emNNN\wave\*` | the bank's entries |

A bank and a request share one path and differ only in their class id and extension (`sbk`,
`srq`); an arc entry stores the class id, so both fit. The record may name **another monster's**
call: MH4U's em002.arc (Rathalos) holds `sound\call\em\em001` and em110.arc holds
`sound\call\em\em024`, because those monsters share the other's calls. A ported monster that
MH4U never had must name its own.

The paths resolve from the loaded monster archive: the record's call path names an entry of
`/data/emNNN.arc`, and the call, request and bank name the rest by path, which the same loaded
archive answers. That is why MH4U ships all four kinds in `/data/emNNN.arc` (236 waves, 7 banks,
4 requests and 4 calls over the four arcs read), and why a port cannot ship only the call.

The two source games lay the same set out differently:

| Game | Where the set lives | Paths |
|---|---|---|
| MH4U | all four in `/data/emNNN.arc` | `sound\call\em\emNNN`, `sound\se\em\emNNN\wave\...`, the request/bank at `sound\se\em\emNNN\snd_emNNN` |
| MH3U | the call in `arc/enemy/emNNN.arc`; the rest in `arc/sound/se/em/emNNN/snd_emNNN.arc` | `sound\call\em\emNNN`, `sound\se\em\emNNN\wav\...`, `...\snd_emNNN`; no common bank |
| MHXX | all four in `arc/enemy/emNNN_VV.arc` | `sound\call\em\emNNN`, `sound\se\em\emNNN_VV\wav\...`, `...\snd_emNNN_VV`, plus the common bank `sound\se\com\snd_com_qst` and its waves under `sound\se\com\wav\...` |

Check SN7's procedure: `arc.read` on MH4U's em001.arc, em002.arc, em089.arc and em110.arc (the
`data/` ones from the cartridge RomFS) and MHXX's em001_00, em003_00 and em008_00; MH3U's
`arc/enemy/em001.arc` and `arc/sound/se/em/em001/snd_em001.arc`. The counts and the chain's
paths are above; every record path in the MH4U arcs names an arc entry, every bank entry names a
wave entry in the same arc, and every request bank name names a bank. The recording of each
converted wave against its source, and of MH4U's own shared waves, is in the wave sections.

## Wave (`MADP`, version 5, MH4U): header 0x60 bytes, then data

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MADP` | verified | the 236 waves of the four sample monster arcs (SN7) |
| 0x04 | u32 | version 5 | verified | the same 236 (SN7) |
| 0x08 | u8[4] | 01 00 00 01: channels and flags; the first byte is the channel count | verified | the same 236 are mono; SN6 shows 2 on MH3U's stereo music streams |
| 0x0C | u32 | sample count | verified | SN7: the length in seconds and the DSP frame count are samples / rate and ceil(samples / 14) in every wave |
| 0x10 | u32 | sample rate (sound effects 8000 to 22000 Hz; music 32728 Hz) | verified | the same check (SN7) |
| 0x14 | u32 | loop flag (effects); loop start (music) | verified | SN7: 0 on all 236 mono effects |
| 0x18 | u32 | loop start (effects); loop end (music) | verified | SN7: 0 on all 236 mono effects |
| 0x1C | u32 | data offset: 0x60 | verified | every MH4U wave (SN7) |
| 0x20 | u32 | data size, padded to 0x100; the DSP frames then the padding | verified | SN7: data offset + size = the file's length in every wave |
| 0x24 | f32 | length in seconds | verified | SN7: equals samples / rate |
| 0x28 | u32 | 0 | verified | every MH4U wave (SN7) |
| 0x2C | u32 | 0x60 (the data offset again) | verified | every MH4U wave (SN7) |
| 0x30 | s16[16] | DSP-ADPCM coefficients (mono waves) | verified | SN7: the coefficients decode the frames (the conversion of MH3U's 31 shared waves reproduces them) |
| 0x50 | u16 ×4 | gain, predictor/scale, history 1, history 2 | verified | SN7: the same 31 shared waves |
| 0x58 | u8 ×8 | unused; MH4U's own files hold the tail of an earlier path string | unknown | SN7 (histogram): every value occurs; a converter writes zeros |
| 0x60 | bytes | DSP-ADPCM frames (8 bytes each), mono effects | verified | SN7: the 31 shared waves' frames are byte-identical to MH3U's (SN6) |

Music streams (stereo) differ: a seek table at 0x28 (entry count) and 0x2C (data offset), 20-byte entries from 0x30. After it come 0x30 bytes of coefficients and state per channel, and the data interleaves channels every 0x100 bytes (Definitive Edition snd_bgm.py, unverified).

## Wave (`MADP`, version 5, MHXX): the same version, another header

MHXX's mono effect wave is version 5 but not laid out like MH4U's: the data starts at 0x68, the 16
coefficients at 0x38 and the four state words at 0x58, a stamp 0x120907e0 sits at 0x2C, and the
file ends 24 bytes after the data. The extra block at 0x30 (two u32) and the 8 bytes at 0x60 are
not traced. Check SN7 read all 588 waves of three monster arcs and decoded one with both candidate
coefficient offsets: 0x38 gives 0.04 % clipped samples, 0x30 gives 10.8 %, so 0x38 is the block.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MADP` | verified | 588 waves in em001_00, em003_00 and em008_00's arcs (SN7) |
| 0x04 | u32 | version 5 | verified | the same 588 |
| 0x08 | u8[4] | 01 00 00 01 (mono) | verified | the same 588 |
| 0x0C | u32 | sample count | verified | SN7: the DSP frame count is ceil(samples / 14) in every wave |
| 0x10 | u32 | sample rate | verified | the same check |
| 0x14 | u32 | loop flag | verified | 0 on all 588 |
| 0x18 | u32 | loop start | verified | 0 on all 588 |
| 0x1C | u32 | data offset: 0x68 | verified | every MHXX wave (SN7) |
| 0x20 | u32 | data size, a multiple of 0x100 | verified | every MHXX wave (SN7) |
| 0x24 | f32 | length in seconds | verified | SN7: equals samples / rate |
| 0x28 | u32 | 0 | verified | every MHXX wave (SN7) |
| 0x2C | u32 | 0x120907e0, the same in every wave | unknown | SN7 (histogram); a build stamp, meaning untraced |
| 0x30 | u32 ×2 | not traced; three (value, 0x80) pairs over the 588 | unverified | SN7 (histogram) |
| 0x38 | s16[16] | DSP-ADPCM coefficients | verified | SN7: the 0x38 / 0x30 decode comparison |
| 0x58 | u16 ×4 | gain, predictor/scale, history 1, history 2 | verified | SN7: (0, predictor/scale, 0, 0) on 561 of 588, the same shape MH4U's have |
| 0x60 | u8 ×8 | junk: the string `eLite\so` in all 588 | unknown | SN7 (histogram) |
| 0x68 | bytes | DSP-ADPCM frames | verified | SN7: the waves convert to MH4U's header and the audio is copied bit for bit (588 of 588) |
| after the data | 24 bytes | junk, zeros in most, never read | unknown | SN7: exactly 24 bytes in all 588; a converter drops them |

Converting it (check SN7): the 588 waves' samples, rate, loop, seconds, data size, coefficients,
state and frames come out equal at MH4U's offsets, 588 of 588.

## Wave (`MADP`, version 4)

MH3U's wave is one version older. Its header is 0x5C for a mono effect and 0x8C for a stereo music stream: a u32 at 0x28, then one 0x30-byte decoder block per channel, then the data. The decoder block is version 5's moved down by 4 bytes: the 16 coefficients at +0 and the four u16 at +0x20 that version 5 keeps at 0x50. Version 5's second u32 at 0x2C is gone; 0x28 packs a 0x3348 marker in its high half and the seek table's entry count in its low half. Unlike version 5, the seek table follows the data, 20 bytes per entry.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MADP` | verified | every MH3U wave (SN6) |
| 0x04 | u32 | version 4 | verified | every MH3U wave (SN6) |
| 0x08 | u8[4] | channels (1 mono effect, 2 stereo music), then 00 00 01 | verified | SN6: 9,843 mono (01 00 00 01) and 289 stereo (02 00 00 01); the music streams' channel counts equal their stream record's |
| 0x0C | u32 | sample count | verified | SN6: the length in seconds is samples / rate in every wave; a stream record repeats the count for the 290 music streams |
| 0x10 | u32 | sample rate | verified | SN6: the same check |
| 0x14 | u32 | loop flag (effects); loop start (music) | verified | SN6: 0 on all 9,843 mono effects; on a music wave it is the stream record's loop start (290 of 290) |
| 0x18 | u32 | loop start (effects); loop end (music) | verified | SN6: 0 on all 9,843 mono effects; on a music wave it is the stream record's loop end (290 of 290) |
| 0x1C | u32 | data offset: 0x2C + 0x30 × channels | verified | every MH3U wave (SN6) |
| 0x20 | u32 | data size, a multiple of 0x100 (0 on one placeholder) | verified | every MH3U wave (SN6) |
| 0x24 | f32 | length in seconds | verified | SN6: equals samples / rate |
| 0x28 | u32 | high half 0x3348, low half seek table entry count | verified | SN6: the bytes after the data are 20 × the low half in every wave; 0 in 10,105 of the 10,132, 27 carry a seek table |
| 0x2C + 0x30 × i, +0x00 | s16[16] | channel i's DSP-ADPCM coefficients | verified | SN6: channel 0's are byte-identical to version 5's at 0x30 in the 31 waves whose audio both games ship; every channel's block is 0x30 bytes, because the data offset is 0x2C + 0x30 × channels in every file |
| 0x2C + 0x30 × i, +0x20 | u16 ×4 | channel i's gain, predictor/scale, history 1, history 2 | verified | SN6: channel 0's are the same 31 pairs (version 5's at 0x50); the block's size is the same check as the row above |
| 0x2C + 0x30 × i, +0x28 | u8 ×8 | not traced; version 5's same bytes are junk | unverified | SN6 (histogram) |
| 0x2C + 0x30 × channels | bytes | DSP-ADPCM frames, then the seek table | verified | SN6: data offset + size + 20 × count = the file's length in every wave |

## Bank (`SNDB`, version 11)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SNDB` | verified | the 7 banks of the four sample monster arcs (SN7) |
| 0x04 | u32 | version 11 | verified | the same 7 |
| 0x08 | u32 | group record count | verified | SN7: the group records end where the entries begin |
| 0x0C | u32 | entry count | verified | SN7: the entries close on the tail |
| 0x10 | u32 | tail record count x; the tail is 8 × x bytes after the entries | verified | SN7: the tail ends the file |
| 0x14 + 12 × i, +0x00 | u16 | group i's id | unverified | SN7 (histogram) |
| 0x14 + 12 × i, +0x02 | u16 | group i's flags: 0x8000 set, a category in bits 11 to 14, 2 × the group's entry count in the low 11 bits | verified | SN7: 0x8000 is set and (flags & 0x7ff) is twice the next group's first entry minus this one's, in all 91 groups |
| 0x14 + 12 × i, +0x04 | u32 | group i's first entry | verified | SN7: 0 ≤ first ≤ the entry count in every group |
| 0x14 + 12 × i, +0x08 | u32 | not traced; 0 in 71 of the 91 groups, a small value on the common bank's | unverified | SN7 (histogram) |
| entry +0x00 | char[] | wave path, NUL-terminated | verified | SN7: the entries tile the file between the groups and the tail |
| entry +len+1 | u32 | wave type id, `0x67195a2e` (`rLtSoundSourceADPCM`) | verified | SN7: all 1,085 entries of the 7 banks name it |
| entry +len+5 | u8[76] | parameters; byte 2 is 8 and the 4-byte key at +12 is {lo, hi, root, 0} with lo = hi = root | unverified | SN7 (histogram): byte 2 is 8 in every entry and the key's first three bytes equal; the parameters' meaning is untraced |
| tail +0x00 | f32, u32 | one {value, index} record; the index's low byte is the record's position in 37 of the 550, so the index is not a position on MH4U's banks | unverified | SN7 (histogram) |

## Bank (`SBKR`, version 4, MHXX)

MHXX's bank is the same container as MH4U's, with the next generation's magic and a different
packing in the group flags: the group marker is 0x0800, the low 11 bits are again twice the
entry count, the category moved into the group's x high byte, and the entry parameters are
permuted (the 4-byte key MH4U keeps at +12 sits at +71, and byte 2 is 0 instead of 8). Check S3
read the 6 banks of three monster arcs (the monster's own and the common `snd_com_qst`).

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SBKR` | verified | 6 banks in 3 arcs (S3) |
| 0x04 | u32 | version 4 | verified | the same 6 |
| 0x08 | u32 | group record count | verified | S3: the records, entries and tail tile every file |
| 0x0C | u32 | entry count | verified | the same check |
| 0x10 | u32 | tail record count | verified | the same check |
| 0x14 + 12 × i, +0x02 | u16 | group flags: 2 × the group's entry count in the low 11 bits, and 0x0800 set on the monster's own bank's groups but not on the common bank's | verified | S3: (flags & 0x7ff) is twice the group's count in all 6 banks' groups; 0x0800 is set on the 3 own banks' groups and clear on the common one's |
| 0x14 + 12 × i, +0x08 | u32 | high byte: the group's category (0 to 8 over the sample); low 24 bits: not traced | unverified | S3 (histogram); MHGU's rules (Definitive Edition) read it this way |
| entry +len+5 | u8[76] | parameters; byte 2 is 0, the 4-byte key sits at +71 and byte 75 is 0 | unverified | S3 (histogram); MHGU Definitive Edition's rules move MH4U's key to +71 and clear byte 2 |
| entry +len+1 | u32 | wave type id, `0x79c47b59` (`rSoundSourceADPCM`) | verified | S3: every entry of the 6 banks |

The conversion (check S3, run backwards): 4U flags = 0x8000 | (GU flags & 0x7ff) |
(category << 11), x = x & 0xFFFFFF; the entry's byte 2 becomes 8, the key moves from +71 to +12,
byte 75 becomes 0 and the type becomes `0x67195a2e`.

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
| tail +0x00 | f32, u32 | one {value, index} record, 8 bytes; the index's low byte is the record's position in 2,258 of the 2,273 | unverified | SN6: x records close every bank read; 15 records name another position |

## Request (`SREQ`, version 8)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SREQ` | verified | the 4 requests of the sample monster arcs (SN7) |
| 0x04 | u32 | version 8 | verified | the same 4 |
| 0x08 | u32 | record count n | verified | SN7: the string table starts at 0x10 + 92 n in every file |
| 0x0C | u32 | string table offset: 0x10 + 92 n | verified | the same check |
| 0x10 + 92 × i, +0x00 | u16 | the request id: word 0's low half | verified | SN7: the ids are unique and ascending in all 889 records, and MH3U's own 101 ids keep MH4U's records' id, entry index and level |
| 0x10 + 92 × i, +0x02 | u16 | flags: 0x7f00 or 0x7f01 on MH3U's; MH4U's word 0 is 0x7f000000 plus one byte and the id | unverified | SN7 (histogram) |
| 0x10 + 92 × i, +0x08 | u32 | the bank entry index: the entry of the bank word 21 names | verified | SN7: 889 of 889 indices are in range and name a wave entry, and MH3U's records name the same entry for the same id |
| 0x10 + 92 × i, +0x14 | u32 | the per-monster category, in a global table (Definitive Edition); the low u16 is the value | unverified | Definitive Edition snd4u2gu.py; SN7 (histogram) |
| 0x10 + 92 × i, +0x20 | u32 | 0x1ffff on 771 of the 889 records, 0xffffffff on 71, other values on the other 47; meaning untraced | unverified | SN7 (histogram) |
| 0x10 + 92 × i, +0x24 | f32 | level in dB (Definitive Edition); -2.08 on 151 of em001's 219 records, and the level the source game also writes on MH3U's own request | unverified | Definitive Edition snd4u2gu.py; SN7: the same values as MH3U's words 9 for the shared 101 ids |
| 0x10 + 92 × i, +0x28 | f32 | the same level on 870 of the 889 records, 0 on the other 19 | unverified | SN7 (histogram) |
| 0x10 + 92 × i, +0x38 / +0x3C | u32 ×2 | equal on 886 of the 889, a small value; meaning untraced | unverified | SN7 (histogram) |
| 0x10 + 92 × i, +0x54 | u32 | bank index into the string table, 0xFFFFFFFF for none | verified | SN7: every value is a valid index or 0xFFFFFFFF, and the string table tiles the file |
| 0x10 + 92 × i, +0x58 | u32 | a build-time pointer slot: 0x12e57030 on em001's records; the loader overwrites it | unverified | Definitive Edition snd4u2gu.py; SN7 (histogram) |
| 0x10 + 92 × i, other words | u32 | not traced | unverified | SN7 (histograms) |

The 23 words are numbered 0 to 22 from +0x10. The six words above are the ones with a meaning;
a converter copies the others as its source game wrote them (see "The request record's words").

## Request (`SREQ`, version 6)

MH3U's request has the same container as version 8, verified on every MH3U request read (SN6): a
0x10-byte header, one 92-byte record per request, then one u32 offset per bank and the
NUL-terminated bank paths in order, ending the file. The records are 23 u32 at the same offsets,
and the fields version 8 calls the id, the bank entry index, the level and the bank index are in
the same words; the other words are packed differently or hold other values. Check SN6 laid the
container out; check SN7 compares the words with MH4U's own request for the 101 ids the two
games share.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SREQ` | verified | every MH3U request (SN6) |
| 0x04 | u32 | version 6 | verified | every MH3U request (SN6) |
| 0x08 | u32 | record count n | verified | SN6: the string table starts at 0x10 + 92 n |
| 0x0C | u32 | string table offset | verified | SN6: 0x10 + 92 n in every file |
| 0x10 + 92 × i, +0x00 | u16 | the request id | verified | SN6: a small request number, distinct in 1,003 of the 1,004 files and ascending in 999; version 8 documents word 0 as its id too |
| 0x10 + 92 × i, +0x02 | u16 | flags: 0x7f00 or 0x7f01 observed; meaning not traced | unverified | SN6 (histogram) |
| 0x10 + 92 × i, +0x24 | f32 | level in dB: -2.08 on Rathian's requests and -3.0 on a stage's | unverified | SN6 (histogram); version 8's word 9 has that meaning |
| 0x10 + 92 × i, +0x08 | u32 | the bank entry index: the same entry MH4U's own request names for the shared ids | verified | SN7: 101 of 101 shared ids name the same wave entry |
| 0x10 + 92 × i, +0x14 | u32 | the category in the low u16 and a build-time value in the high u16: 0xf4e9011e, 0xf1a1011e and 0x1a51011e on Rathian's records, against MH4U's 0x12d | unverified | SN7 (histogram) |
| 0x10 + 92 × i, +0x54 | u32 | bank index into the string table, 0xFFFFFFFF for none | verified | SN6: every value is a valid index or 0xFFFFFFFF, and the string table tiles the file |
| 0x10 + 92 × i, other words | u32 | not traced; version 8's meanings don't hold (MH3U writes 0xffffffff in word 8 and 0 in word 10, where MH4U writes 0x1ffff and the level) | unverified | SN6 and SN7 (histograms) |

## Request (`SRQR`, version 5, MHXX)

MHXX's request header and string table are MH4U's, but its records are **not** MHGU Switch's
132-byte records: they are 100 bytes, 25 u32, and words 0 to 21 sit where MH4U's 23-word record
has them. Check S3 read three MHXX requests; MHGU's 132-byte layout (Definitive Edition) is the
next generation's, and `mhuc` reads only MHXX's 100-byte records.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SRQR` | verified | 3 files (S3) |
| 0x04 | u32 | version 5 | verified | the same 3 |
| 0x08 | u32 | record count n | verified | S3: the string table starts at 0x10 + 100 n |
| 0x0C | u32 | string table offset: 0x10 + 100 n | verified | the same check |
| 0x10 + 100 × i | 100 bytes | 25 u32; words 0 to 21 as MH4U's, words 22 to 24 zero | verified | S3: every record reads, the ids are unique and ascending, and for the 150 ids MH4U's own request also has the entry index is the same and names the same wave (case aside) |
| after the records | u32 × banks | one u32 offset per bank, then the NUL-terminated names, ending the file | verified | S3 (3 of 3) |

Converting a record is dropping words 22 to 24 and setting word 8's bit 16 (MHGU's rule read
backwards), which gives MH4U's 92-byte record; see "The request record's words".

## Sound call (`MSS`): one layout, three versions (SN8)

A monster's sound call holds, per motion, the sound events an animation fires. All three versions
share one layout: the version word is the only difference between MH4U's and MHXX's files, and
MH3U's older version differs in the table's length. Check SN8 read MH4U's em001, em089 and em024
calls, MH3U's em001 call and MHXX's em001 call: 5 files, 857 records and 5,873 events, every table
and record tiling its file.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `MSS\0` | verified | the 5 files (SN8) |
| 0x04 | u32 | version: 0x20110404 (MH3U), 0x20120123 (MH4U), 0x20131015 (MHXX, MHGU) | verified | SN8; SN1 counts every sequence in the three RomFS by version |
| 0x08 | u16, u16 | 0x0100, then the record count | verified | SN8: the low half is the record count in all 5 (and the pair table's length); the high half is 0x0100 in all 5, meaning untraced |
| 0x0C | u32 | 0 | verified | the 5 files |
| 0x10 | u16[512], u16[2048] on MH3U | the motion table: row i is i for i < the record count, 0xffff after | verified | SN8: every table is the identity followed by 0xffff |
| after the table | {u32, u32} × count | the pair table: each record's key and its offset from the file start | verified | SN8: the keys ascend, the offsets ascend, and the first offset is the table's end |
| +0x00 (record) | u32 | the key: its bank × 1000 + motion (Definitive Edition's reading of the engine); equals the pair table's key | verified | SN8: the value matches the pair table in all 857 records; the key's meaning is unverified |
| +0x04 | u16 | the event count n | verified | SN8: the data offset and the pair list follow it |
| +0x06 | u16 | not traced (0x12c, 0xd4, 0xee on MH4U's records; 0 on MH3U's empty ones) | unknown | SN8 (histogram) |
| +0x08 | u32 | 0xffffffff | verified | the 857 records |
| +0x0C | u32 | the data offset: 0x10 + 8 n | verified | the 857 records |
| +0x10 | {u32 frame, u32 offset} × n | each event's frame and its offset from the record's start | verified | SN8: every offset points at a u16 that equals its frame |
| +data offset | u16, u16 | 0xffff, 0 | verified | the 857 records |
| +data offset + 4 | events | each event starts with its u16 frame (the pair table's); the event body holds command words 0x140, 0x15e, 0x160 and 0x163, all four in MH4U's own files too | unverified | SN8: the frame is verified at every event's offset; the body is not decoded. 0x163 is followed by three u32 (request id, joint, flags) in MHGU Definitive Edition's reading |

A conversion moves the records and the table, not the event bytes: MH3U's 2048-row table becomes
MH4U's 512 (Rathian's 229 records all sit in the first 512 rows), the pair table follows it, each
pair's offset moves with the records, and the version word changes. The records hold only
record-relative offsets, so their bytes are copied unchanged. Check SN9 converts MH3U Rathian's
call and reads the result back: 229 records, the same keys and byte-identical record bodies.

## The request record's words

Both MH3U's and MHXX's requests are 23 or 25 u32 records at MH4U's offsets, but only some words
share a meaning. A converter copies the words it cannot justify instead of inventing them, and the
in-game listen (check A1) is where a wrong word shows.

| Word (from +0x10) | MH4U's meaning | MH3U (23 words) | MHXX (25 words) |
|---|---|---|---|
| 0 | the id in the low u16; the high half packs flags | copied | copied |
| 2 | the bank entry index | copied (MH3U and MH4U name the same entry for the 101 shared ids) | copied |
| 3, 4 | not traced | copied | copied |
| 5 | the category (low u16), per-monster in a global table | MH3U packs a build value in the high u16, so only the low u16 is kept | copied |
| 6, 7 | not traced | copied | copied |
| 8 | 0x1ffff on most MH4U records, 0xffffffff on 71, other values on the rest | copied (0xffffffff is a value MH4U's own files hold) | bit 16 set (MHGU's rule read back: GU clears it) |
| 9 | the level in dB | copied | copied |
| 10 | level or second level: equal to word 9 on 870 of 889 records, 0 on the rest | copied (MH3U writes 0) | copied |
| 11 to 20 | not traced | copied | copied |
| 21 | the bank index into the string table | copied | copied |
| 22 | a build-time pointer slot | 0 (MH3U's value is a 3U address) | 0 (MHXX's words 22 to 24 are 0 and dropped) |
| 23, 24 | none (MH4U has 23 words) | none | dropped |

## What a converter must produce

For a ported monster of id N, one complete set, every path under the ported id's namespace so it
never shadows MH4U's own monster or another port, and all of it in `/data/emNNN.arc` (or a
separate loaded archive) so the record's one path resolves:

| Kind | Port path | From MH3U | From MHXX |
|---|---|---|---|
| sound call | `sound\call\em\emNNN` | version 0x20120123, 512-row table, records moved | version 0x20120123 (same layout) |
| waves | `sound\se\em\emNNN\wave\<source name, emNNN prefix moved to the port>` | version 5 header, audio copied bit for bit | MH4U's version 5 header (data from 0x68, coefficients from 0x38), the 24-byte tail dropped |
| bank | `sound\se\em\emNNN\snd_emNNN` (the common bank as `...\snd_common`) | `SNDB` 11, same container, paths rewritten | `SNDB` 11, MHGU's flags/parameters reversed |
| request | the bank's path, `srq` | `SREQ` 8, words as "The request record's words" | `SREQ` 8, 100-byte records to 92, words as above |

`mhuc convert monster` writes this (`--id 125 --arc <MH3U arc/enemy/em001.arc> --sound-arc <MH3U
arc/sound/se/em/em001/snd_em001.arc> --out <mod folder>`; MHXX: `--from mhxx --arc <MHXX
arc/enemy/em001_00.arc>`), creating or extending `<mod folder>/romfs/data/emNNN.arc`. It refuses
a source it cannot place (a wave outside the known directories, a bank entry naming a wave the
archive doesn't hold, MHGU's 132-byte request records). The 3U Rathian's registry row lists
`sound` and her converted arc holds 48 waves, one bank, one request and one call (SN9).

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

MH3U ships the same layout one version older, 0x20 (check SN6): all 106 of its stream requests close exactly, and each of their 290 stream records repeats the header of the `.mca` it names (file size, sample count, channels, rate and loop start and end). The MH4U addresses in the rows below are MH4U's loader; MH3U's isn't traced.

**The loader (0x004044b0).** MH4U's `rLtSoundStreamRequest` load checks the magic and the version, copies the file into a buffer and keeps on the resource the buffer (+0x64), the stream count (+0x8C), the sequence count (+0x68) and the sequence table's address (+0x6C). It allocates a 64-byte slot per stream at +0x88 (8 bytes plus 64 × the stream count) and fills each slot from the stream record: the name's address at +0x04, sample count +0x08, channels +0x0C, rate +0x10, file size +0x14, loop start +0x18, loop end +0x1C, the matching sequence's +0x0C at +0x20, flags 1 (0x101 when that word is 1) at +0x24, the source class id at +0x28 and the stream record's +0x20 at +0x2C. The stream's sequence is the first record in the sequence table whose +0x5C names it. The loader then writes that slot's address at the sequence's +0x60. When the sequence's +0x0C isn't 1 it also creates the stream's source object and keeps it at the slot's +0x30 and calls its vtable +0x44; every MH4U sequence has 1 there, so the path isn't taken in any shipped file. At the end it calls 0x00404310.

**The index at +0x94/+0x98.** 0x00404310 takes the highest u16 id in the sequence table, stores max + 1 at +0x98 (u16) and allocates that many u16 at +0x94, fills them with 0xFFFF and sets each to its record's row number by the record's id. `0xcebb8c(request, id)` reads the index: when the pointer is set and the id is below the count it takes the u16 there (0xFFFF: no row) and returns sequence table + 100 × the row; without an index it scans the table linearly, comparing the u16 at +0x00. The index is larger than the sequence count in 102 of the 214 files because the ids are sparse; `bgm_bat.stq`'s is 40 entries and the largest, `se_ev_lob.stq`'s, 774 (id 773). Across the 214 files the 13,249 sequence records get 35,257 index entries.

**`sSoundControl`'s loader (0x003099c8).** It takes a kind 0 to 8 and picks the slot `sound + 0x1674 + 4 × kind` (0 common, 1 stage, 2 battle, 3 and 4 event, 5 area, 6 lobby, 7 system, 8 download) and the game's own path for that kind: the stage table at 0x00f00624 indexed by the stage for kind 1, the area table at 0x00f005b0 indexed by the area for kind 5, the pointer tables at 0x00f006a0 or 0x00f006b4 for the others, and the inline `sound\bgm\download\…` string at 0x309b20 for kind 8. It releases the request already in the slot through 0x0030cebc, which calls 0xbe2718 and clears the slot, then loads the new resource with the descriptor at 0x010e7750 and that path.

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `STRQ` | verified | all 50 files (S4) |
| 0x04 | u32 | version 0x22 (34) on MH4U, 0x20 (32) on MH3U | verified | all 50 MH4U files (S4) and all 106 MH3U files (SN6); ours, the loader compares it at 0x00404530 |
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
| +0x00 (sequence) | u32 | request id; the field's u16 at +0x00 is the key: the index builder reads it with `ldrh` and the lookup compares a u16. 0 to 773 across the 214 files, unique and ascending in every file | verified | all 13,249 sequence records in the 214 files (S4, S7); ours, 0x00404310 and 0xcebb8c (0xcebbf8, 0xcebc40) |
| +0x04 | u32 | 0, 1, 2 or 4 in every file (5,494, 7,366, 345 and 44); no reader found | unknown | whole-image search (S7): the loader, the index builder, the lookup's caller functions and the sequence driver's handlers never load it |
| +0x08 | u32 | type: the sequence driver 0xbd0ea8 dispatches on the byte at +0x08 through the table at 0xbd1020 (0 to 11; 0, 1, 5, 6, 9, 10 and 11, in 3,936, 1,548, 275, 120, 196, 3,587 and 3,587 sequences). Type 11 also makes 0x309d38 and 0x3123a0 store id − 1 as the request's theme id | verified | ours, 0xbd1010, 0x309d38 (0x30a0a8), 0x3123a0 (0x312440); S4 (counts), S7 |
| +0x0C | u32 | source type: the loader creates a stream's source object unless this word is 1 (0x404744); 1 in all 13,249 sequences. The track setup copies the low byte to the track's +0x238 | verified | ours, 0x00404744, 0xbcdb10 (0xbce0cc); S4 (count), S7 |
| +0x10 | u8 | track selector 1: 0 (624) or 1 (12,625). The driver passes it to 0xbd242c, which matches it against a loaded track's +0x14 (the tracks are the sound object's 0x3a8-byte array at +0x5b98, count at +0x900c); copied to the track's +0x14. +0x11 is 0 and has no reader | verified | ours, 0xbd242c (0xbd24a8), 0xbcdb10 (0xbcdb90, 0xbce07c); S4 (counts), S7 |
| +0x12 | s16 | track selector 2: 0 (624), 1 (7,282), 2 (5,299) or 3 (44); matched against a track's +0x18 and copied to the track's +0x18 | verified | ours, 0xbd242c (0xbd24b4), 0xbcdb10 (0xbcdba8, 0xbce084); S4 (counts), S7 |
| +0x14 | s16 | track selector 3: 0 (2,187), 1 (2,112) or 2 (8,950); matched against a track's +0x1C and copied to the track's +0x1C | verified | ours, 0xbd242c (0xbd24c8), 0xbcdb10 (0xbcdb98, 0xbce08c); S4 (counts), S7 |
| +0x16 | s16 | track selector 4: 0 (13,183), 1 (55) or 2 (11); matched against a track's +0x20 and copied to the track's +0x20 | verified | ours, 0xbd242c (0xbd24dc), 0xbcdb10 (0xbcdba0, 0xbce094); S4 (counts), S7 |
| +0x18 | u8 | priority: 0x308720 reads it (0x309430) and keeps the theme with the highest value among the battle candidates. 0 (1,693), 5 (8), 10 (30), 20 (9,755), 30 (1,232), 35 (11), 40 (44), 50 (106), 52 (13), 54 (13), 56 (11), 58 (11), 59 (11), 60 (15), 61 (11), 62 (11), 63 (11), 64 (13), 66 (8), 68 (11), 70 (11), 72 (132), 73 (11), 80 (44) and 90 (33) | verified | ours, 0x309428; S4 (counts), S7 |
| +0x19 | u8 | 0 (834) or 1 (12,415); the second fallback for a track selector when the caller passes 0xFF (0xbcdb60); the purpose isn't established | unverified | ours, 0xbcdb60; S7 |
| +0x1A | s16 | −1 (12,907), 0 (47) or 3 (295); no reader found | unknown | whole-image search (S7) |
| +0x1C | u32 | 0 (1,145) or 1 (12,104); 0xbcdb10 compares it with the number of loaded tracks whose fields match the cue's selectors and starts one per match while that number is at least this value, so 0 starts none and 1 starts them (0xbcddc4, 0xbcdea4); copied to the track's +0x2C | unverified | ours, 0xbcdb10; S4 (counts), S7 |
| +0x20 | s16 | next sequence id: the driver reads the s16 at 0xbd14c8 and, when the cue ends, switches to that id unless it is −1 or the id being played; all 13,249 sequences are −1. The same s16 is copied to the track's +0x9C | verified | ours, 0xbd0ea8 (0xbd14c8), 0xbcdb10 (0xbce0b4); S7 |
| +0x22 | s16 | −1 in all 13,249 sequences; copied to the track's +0x74 (0xbce06c); no other reader | unverified | ours, 0xbcdb10; S7 |
| +0x24 (with a stream) | f32 | level in dB: 0.0 at `bgm_bat` id 32 and −0.9 at id 33 (Definitive Edition); −16.0 to +1.5 dB over the 5,410 sequences with a stream. The start path passes it to the queue, which converts it to a linear gain 10^(level/20), with ≤ −96.0 dB as 0 | verified | Definitive Edition snd_bgm.py; ours, 0x309d38 (0x30a058), 0xbcce10; S4 (range), S7 |
| +0x24 (without a stream) | f32 | percentage: 0 on 7,343, 20 on 33, 50 on 30, 55 on 24, 70 on 11 or 100 on 98, and −0.2 to −4.0 dB on the other 300. Read as a percentage of another sequence's level where a cue starts: 0x306408 computes 20·log10(10^(a/20)·v/100) from the cue's level a and this word v, with v = 0 giving 0 dB (no change). Within the sequences without a stream, every positive value is on one of the 196 rows with +0x08 = 9 | verified | ours, 0x306408, 0x302b68 (0x303064), 0x305698 (0x306408); S4 (counts), S7 |
| +0x28 | f32 | the fade's start level in dB, read with +0x24 by the ramp setter 0xbc82d4 (0xbc849c); −96.0 in all 13,249 sequences, which its conversion turns into silence | verified | ours, 0xbc82d4; S4 (count), S7 |
| +0x2C | u32 | 0 in 13,245 sequences, 400 in two and −200 in two; copied to the track's +0x78 (0xbce074); the purpose isn't established | unverified | ours, 0xbcdb10; S4 (counts), S7 |
| +0x30 | u32 | 0 in all 13,249 sequences; no reader found | unknown | whole-image search (S7) |
| +0x34 | u32 | 0 in all 13,249 sequences; copied to the track's +0x98 (0xbce0bc) | unverified | ours, 0xbcdb10; S7 |
| +0x38, +0x3C, +0x40 | u32 ×3 | −1 in all 13,249 sequences; copied to the track's +0x8C, +0x90 and +0x94 (0xbce0e0–0xbce100) | unverified | ours, 0xbcdb10; S4 (counts), S7 |
| +0x44 | u32 | 0 on 12,658 sequences, 1,000 on 460, 1,500 on 6, 1,900 on 48, 2,000 on 11, 3,000 on 33 and 4,000 on 33; a length the ramp setter 0xbc82d4 counts down once per update (it divides the level change by it); also passed as the stop duration at 0x3084ac | unverified | ours, 0xbc82d4, 0x3084ac, 0x302b68 (0x3030cc); S4 (counts), S7 |
| +0x48 | u32 | 0 on 7,149 sequences, 100 on 44, 500 on 4,378, 1,000 on 1,570 and 1,500 on 108; the default stop duration when 0x3069c4 is called with −1, queued as command 7/4 (0xbcabb0); the unit isn't established | unverified | ours, 0x3069c4 (0x306a0c), 0x309d38 (0x30a03c); S4 (counts), S7 |
| +0x4C | u32 | 0 (1,655), 0x10 (2,105) or 0x01000010 (9,489); bits 4-7, when set, queue command 6/0x21 after the cue starts (0xbd2260); bits 0-3 and 8-31 have no reader | unverified | ours, 0x309d38 (0x309e68), 0x3102f0, 0x300254, 0xbd2260; S4 (counts), S7 |
| +0x50, +0x54, +0x58 | u32 ×3 | 0 in all 13,249 sequences; no reader found | unknown | whole-image search (S7) |
| +0x5C | u32 | stream index into the stream table, `0xFFFFFFFF` for no stream | verified | all 13,249 sequence records (S4); Definitive Edition snd_bgm.py (ids 32 and 33 name streams 18 and 19); ours, the loader resolves it at 0x00404818 |
| +0x60 | u32 | stream slot pointer: 0 exactly when +0x5C is 0xFFFFFFFF, otherwise a build-time pointer (0x127F0144 to 0x1281964C) that the loader overwrites with the address of the stream's 64-byte slot; 0xbd2c64 reads it (0xbd2c7c) and follows the slot's +0x30 to the source object | verified | ours, the loader writes it at 0x00404830, 0xbd2c64; S4 (zero on the 7,839 sequences without a stream, non-zero on the 5,410 with one) |

Stream records are 36 bytes and sequence records 100. The lookup compares the id at +0; the request ids are unique and ascending in every MH4U stream request, but sparse (the event files reach 773). The music streams are stereo DSP-ADPCM at 32728 Hz, so a stream record's +0x04 size equals the `.mca` file size and +0x08, +0x0C, +0x10, +0x14 and +0x18 equal its header's sample count, channels, rate, loop start and loop end: that is the check. The sequence records stay in the file buffer; the loader only writes each sequence's +0x60 and the index bytes at +0x94/+0x98, so every word above is the file's own. Which sequence type a cue is (+0x08) decides how the sequence driver 0xbd0ea8 starts it: types 1, 5 and 10 go through 0xbcdb10, 2 through 0xbd1078, 3 through 0xbd1284, 6 to 9 through 0xbcd890 (9 also calls the ramp setter) and 11 through 0xbcf76c, each with the four selectors at +0x10 to +0x16; types 0 and 4 do nothing. What the ids select, and what a new monster theme has to add, is in [docs/audio.md](../docs/audio.md#how-mh4u-picks-a-monsters-theme).

## Checks (with game files)

- **SN1 (done, 2026-11-25):** `mhuc survey <romfs.bin>` on MH4U USA (cartridge), MH3U USA and MHXX JPN v1.0 counts every sound resource in its report's `sound` section, by kind, magic and version, and by class id inside ARCs. Result: the versions and counts table above. Every sound file in every game matched one magic and one version of its kind, and every ARC entry's class id was that game's registry class for the kind. MH3U's versions are not MH4U's: each is one older (wave 4 against 5, bank 10 against 11, request 6 against 8, stream 0x20 against 0x22), so 3U's files need version-aware readers or a conversion. MHXX keeps MH4U's wave version (5) but its header differs, and it has GU's bank (`SBKR` 4) and a `SRQR` 5 request with 100-byte records, not GU's 132; S3 (done) checks the layouts. MH3U ships no area emitter file; MHXX's emitters are `rFestaSoundEmitter`, version 0x20160706.
- **SN2:** parse every MH4U `MADP`, `SNDB`, `SREQ` and `SES` with this layout, over the whole RomFS (SN7 reads the monster arcs only). Count files whose sizes and offsets close exactly, and record the counts, never bytes. A field becomes verified when every file agrees.
- **S3 (done, 2026-11-25):** MHXX's bank and request against MHGU's layouts (`SBKR` v4, `SRQR` v5). Procedure: `mhuc survey` or the game-files test reads the six banks and three requests inside MHXX JPN v1.0's em001_00, em003_00 and em008_00 arcs; `sound.read_bank` and `sound.read_request_gu` read them. Result: the banks are MHGU's container (all 6 read; own banks 9/8/8 groups, 116/72/67 entries, 3 tail records; the common `snd_com_qst` 20 groups, 205 entries, 10 tail; the group flags are 2 × the entry count in the low 11 bits, with 0x0800 on the monster's own bank and the category in x's high byte; the entries' 76 bytes have MHGU's permutation and type `0x79c47b59`). The requests are **not** MHGU Switch's: MHXX's records are 100 bytes (25 u32), where MHGU Definitive Edition reads 132 (33 u32); the header and the string table are MH4U's, the ids and entry indices agree with MH4U's own records (150 of MHXX's 155 ids are MH4U's too, and the same entry index names the same wave, case aside), and words 22 to 24 are zero. So the XX → 4U conversion is MHGU's bank rules run backwards and the request is MH4U's 23-word record plus two dropped words; MHGU's 132-byte rules must not be used. MHXX's wave is `MADP` version 5 but not MH4U's header (SN7).
- **S4 (done, 2026-11-25):** parse every `.stq` of MH4U USA v1.3.0's RomFS, loose and inside ARCs. `mhuc stq <file>` reads one stream request; `mhuc survey <romfs.bin> --workers 1` reports S4 read 214 files (50 loose, 164 in ARCs), 5,120 streams and 13,249 sequences, 5,410 of them with a stream and 7,839 without. Every file closed exactly: magic `STRQ`, version 0x22, stream table at 0x18, sequence table at 0x18 + 36 n, names in stream order from the end of the sequence table to the file's end, and every stream index in range (the reader refuses anything else). Each stream record's size, sample count, channels, rate and loop start and end equal the `MADP` header of the `.mca` it names, 497 of 497 in the loose files. The with-game-files test reads every loose `.stq` and checks that the request ids are unique and ascending and that every stream is used. The sequence record's words, the lookup's index at `+0x94`/`+0x98` and `sSoundControl`'s loader `0x003099c8` are read in S7; still open there are the meanings of the words marked unverified.
- **S7 (done, 2026-11-25):** read the sequence record from the code that reads it and counted every field over all 214 stream requests (13,249 sequences). Procedure: `mhuc survey <romfs.bin> --workers 1` (S4) reports the file, stream and sequence totals; the field counts come from reading every `.stq` — the 50 loose ones and the 164 inside ARCs — with `stq.read` and unpacking each 100-byte record at the sequence-table offset. The code was read in MH4U USA v1.3.0's decompressed `code.bin` (base 0x00100000) with capstone: the loader 0x004044b0 and index builder 0x00404310, the lookup 0xcebb8c, `sSoundControl`'s loader 0x003099c8 and release 0x0030cebc, the sequence driver 0xbd0ea8 and its handlers 0xbcdb10, 0xbcd890 and 0xbcf76c, and the other functions that call the lookup (42 call sites in 24 functions, whole image). Result: +0x00, +0x08, +0x0C, +0x10, +0x12, +0x14, +0x16, +0x18, +0x20, +0x24, +0x28, +0x5C and +0x60 are named above from their readers; +0x19, +0x1C, +0x22, +0x2C, +0x34, +0x38, +0x3C, +0x40, +0x44, +0x48 and +0x4C have a reader but no established meaning; +0x04, +0x11, +0x1A, +0x30, +0x50, +0x54 and +0x58 have no reader in any of those functions, which is the negative record for them: the record's pointer is handed on by the lookup alone, and the functions that receive it are the ones named above. +0x0C is 1 in all 13,249 sequences; the request ids are unique and ascending in all 214 files; +0x20 and +0x22 are −1 in all; +0x28 is −96.0 in all; the 196 sequences without a stream that have a positive +0x24 are exactly the 196 with +0x08 = 9; and the index at +0x98 is max u16 id + 1, 35,257 entries over the 214 files (largest 774, in `se_ev_lob.stq`).
- **SN5 (done, 2026-11-25):** read the allocator setup in the MH4U USA v1.3.0 image instead of the files, to say where sound memory comes from. The heap table is at 0x00f2bb44: nine 0x18-byte records {name pointer, allocator index, type, size, flags, 0}, read by 0x0010612c; the alias table is at 0x00f2bc1c and holds seven {index, target index} pairs. The class-to-index table is built by the function at 0x00104904. Result: Resource (index 11) is 0x2F00000 = 47 MiB and receives every `cResource` subclass; SoundBuffer (21) is aliased to Resource; no heap is made for Sound (15), the index of `cMHSoundEmitter`, `cMHSoundSequence` and `nMHSoundSequence`, which therefore allocate from the default heap. The sound resource classes have no entry of their own and their parent is `cResource`. The shipped `/memory.ini` `[Allocators: CTR]` agrees: Resource 47MB, `SOUND_BUF = RESOURCE`, no SOUND. Unverified: that the index lookup follows a class's parent (the table has 128 rows for 992 classes); the sound resource classes are assumed to take `cResource`'s index, and nothing was run to watch an allocation. Sizes and the largest monster sets: [audio.md](../docs/audio.md#how-much-the-three-games-monster-banks-use).
- **SN6 (done, 2026-11-25):** the MH3U wave, bank, request and stream request layouts above are laid out and checked against the whole MH3U RomFS. Procedure: `mhuc survey <MH3U USA romfs.bin> --workers 1` reads every sound resource of the four kinds with `sound.read_wave`, `sound.read_bank`, `sound.read_request` and `stq.read`, and reports each kind's version (SN1) and how many it read; `MHUC_DUMPS=… pytest -m game_files -k mh3u_sound` (`test_every_mh3u_sound_file_reads_and_its_stream_requests_match_their_waves`) repeats the reads and checks them against each other. Result: all 10,132 waves (`MADP` 4: 9,843 mono, 289 stereo, 27 with a seek table, 1 empty placeholder), all 1,225 banks (`SNDB` 10: 13,695 group records, 24,985 entries, 2,273 tail records), all 1,004 requests (`SREQ` 6: 27,424 records, 1,225 bank names) and all 106 stream requests (`STRQ` 0x20: 290 streams, 4,926 sequences) read; none was refused. Every file closed exactly: a wave's offset, size and seek table end it, a bank's groups, entries and tail tile it, a request's records and bank table tile it, a stream request's tables and names tile it. Cross-checks: every request bank name names a bank resource in the RomFS (1,225 of 1,225); every stream record's file size, sample count, channels, rate and loop start and end are the `.mca`'s own (290 of 290). The wave decoder fields are version 5's moved down by four bytes: in the 31 waves of Rathian's arc that both games ship with byte-identical DSP data, MH3U's 0x08..0x24 fields equal MH4U's and its coefficients and state at 0x2C..0x53 are byte-identical to MH4U's at 0x30..0x57. Still open: MH4U's version 5 stereo music layout (only its mono effects are read), the meanings of version 6's request words beyond the id and the bank index, version 10's group flags and entry parameters, and its tail record's index (15 of 2,273 records don't name their own position).

- **SN7 (done, 2026-11-25):** the monster sound set and MH4U's own wave, bank and request layouts.
  Procedure: `arc.read` the four MH4U cartridge monster arcs under `data/` (em001, em002, em089,
  em110), MHXX JPN v1.0's em001_00, em003_00 and em008_00, and MH3U USA's em001 monster and sound
  arcs; read every sound entry with `sound.read_wave`, `sound.read_bank`, `sound.read_request` and
  `sound.read_sequence`; `MHUC_DUMPS=… pytest -m game_files -k monster_sound` repeats it and checks
  the conversions against the sources. Result: the record's +0x1c path is the sound call in all
  four MH4U arcs; the four arcs hold 4 calls (645 records, 5,279 events), 4 requests (889
  records), 7 banks (91 groups, 1,085 entries, 550 tail records) and 236 mono waves. MH4U's wave
  version 5, bank version 11 and request version 8 tables above are what those files read; the
  group flag formula holds in all 91 groups, and every bank entry names a wave in its archive and
  every request bank name a bank. The wave conversion: MH3U's 48 waves become MH4U's header with
  the audio and decoder fields unchanged (48 of 48), and for the 31 waves MH4U ships with the same
  audio the converted bytes equal MH4U's own at every field except the unused 0x58; MHXX's 588
  waves convert with data, coefficients and state unchanged (588 of 588) and their 24-byte tail
  dropped. The bank and request words a converter copies are in "The request record's words".
- **SN8 (done, 2026-11-25):** the sound call's layout in the three versions. Procedure:
  `sound.read_sequence` on MH4U's em001/em089/em024 calls, MH3U's em001 call and MHXX's em001 call
  (5 files, 857 records, 5,873 events), plus `mhuc survey`'s new `SN8 sequence read` counter on a
  whole RomFS. Result: every file's table is the identity followed by 0xffff, the pair table is
  the records' keys and offsets in order, every record's data offset is 0x10 + 8 × its event
  count, the sentinel is there, and every event's offset points at its frame (0 mismatches). The
  record's key is the pair table's in all 857; `x` at +0x06 and the event bodies' commands are the
  fields still unverified.
- **SN9 (done, 2026-11-25):** a whole 3U monster's set converts. Procedure: `mhuc convert monster
  --id 125 --arc <MH3U arc/enemy/em001.arc> --sound-arc <MH3U
  arc/sound/se/em/em001/snd_em001.arc> --out <mod folder>`, then read every entry of the written
  `data/em125.arc` with MH4U's readers and compare against MH3U's own files. Result: 48 waves, 1
  bank (2 groups, 82 entries), 1 request (101 records, one bank) and 1 call (229 records,
  0x20120123); every wave's audio, coefficients and state equal MH3U's; the bank's entries keep
  their order and all name shipped waves; the request keeps MH3U's ids, entry indices and level,
  with one bank; the call keeps its keys and record bytes. MHXX's em001_00 converts the same way
  for id 124 (198 waves, 2 banks, 1 request with 155 ids, 1 call with 184 records); its request
  words match MHXX's for 0 to 21 and the bank flags/parameters reverse MHGU's rules. The in-game
  listen is check A1 in [checks.md](../docs/checks.md#a-ported-monsters-own-voice-a1).
- **SN10 (done, 2026-11-25):** every sound resource's decompressed size in the three images, not only its number, and each monster's complete set. Procedure: read every file of a RomFS image; for an ARC, read its header and its 0x50-byte table-of-contents entries with the layout in [arc.md](arc.md) — the entry's size word is the decompressed size — and keep the entries whose class id is a sound class (`SOUND_CLASSES` in `src/mhuc/survey.py`); for a loose file, take its length when its first four bytes are a magic in `SOUND_MAGIC`. Nothing is decompressed. Checked instead by decompressing three sample ARCs (MH4U `/data/em017.arc`, 150 sound entries; MH3U `/arc/sound/se/em/em020/snd_em020.arc`, 63; MHXX `/arc/enemy/em001_00.arc`, 202): every sound entry's decompressed length equalled its table-of-contents size. Result: the sizes table above; SN1's counts reproduced exactly (3,582 / 1,225 / 3,010 banks, 2,828 / 1,004 / 2,845 requests, 27,146 / 10,132 / 52,204 waves, 451 / 240 / 236 sequences, 214 / 106 / 88 stream requests, 132 / 0 / 248 area emitters, 82 / 26 / 119 reverbs, 46 / 9 / 0 category filters, 0 / 0 / 62 EQs, 8 / 26 / 0 sound attribute se), and the per-monster sets in [audio.md](../docs/audio.md#how-much-the-three-games-monster-banks-use). A set is the bank, request and wave entries of the ARCs whose paths name a monster (`/data/emNNN.arc` in MH4U, `/arc/sound/se/em/emNNN/snd_emNNN.arc` in MH3U, and `/arc/enemy/emNNN_NN.arc` or `emsNNN_NN.arc` in MHXX); the call sequence `sound\call\em\emNNN` is outside the figure, as MH4U's was before. MHXX's v4.8 update replaces 116 RomFS files, two of which carry sound (`/arc/resident.arc` and `/arc/village/common.arc`); both carry the same sound entry counts and sizes as v1.0's, so the base image's totals hold for the updated game.
