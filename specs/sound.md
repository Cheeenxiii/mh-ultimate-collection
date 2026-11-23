---
class: rLtSoundSourceADPCM, rLtSoundBank, rLtSoundRequest, rLtSoundStreamRequest, rMHSoundEmitter (MH4U, MH3U); rSoundSourceADPCM, rSoundBank, rSoundRequest, rSoundStreamRequest (MHXX)
extension: mca (waves and music streams), and sound entries inside ARCs (banks, requests, emitters)
games: MH4U (from MHGU Definitive Edition's tools, EUR v1.1); MH3U and MHXX by class registry only
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
- The class names and ids come from the engines' class registries: MH4UltimateDC `config/mt_classes.tsv` for MH4U, and the fork's `config/games/mh3u/` and `config/games/mhxx/`.

## Which class, which game

| Kind | MH4U | MH3U (3DS) | MHXX (3DS) | Source |
|---|---|---|---|---|
| wave | `rLtSoundSourceADPCM` 0x67195a2e, magic `MADP` | same class and id | `rSoundSourceADPCM` 0x79c47b59 | registries |
| bank | `rLtSoundBank` 0x14b5c8e6, magic `SNDB` | same | `rSoundBank` 0x15d782fb | registries; magics from Definitive Edition |
| request | `rLtSoundRequest` 0x2618de3f, magic `SREQ` | same | `rSoundRequest` 0x1bcc4966 | registries; magics from Definitive Edition |
| stream request (music) | `rLtSoundStreamRequest` 0x3a6a5a4d | same | `rSoundStreamRequest` 0x167dbbff | registries |
| area emitters | `rMHSoundEmitter` 0x68cd2933, magic `SES\0` | same | not in the registry under that name | registries |
| reverb, EQ | `rLtSoundReverb` (no EQ class) | `rLtSoundReverb` | `rSoundReverb`, `rSoundEQ` | registries |

MH3U's classes are MH4U's, with slightly smaller instance sizes, so their file versions may differ. MHXX's ids are the same as MHGU Switch's in Definitive Edition's notes (`SBKR` 0x15d782fb, `SRQR` 0x1bcc4966, wave 0x79c47b59). That suggests Definitive Edition's 4U → GU rules, run in reverse, describe MHXX → MH4U; check S3 decides it.

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

## Bank (`SNDB`, version 11)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | char[4] | magic `SNDB` | unverified | Definitive Edition snd4u2gu.py |
| 0x04 | u32 | version 11 | unverified | Definitive Edition snd4u2gu.py |
| 0x08 | u32 | group record count | unverified | Definitive Edition snd4u2gu.py |
| 0x0C | u32 | entry count | unverified | Definitive Edition snd4u2gu.py |
| 0x10 | u32 | 3 or 4 | unverified | Definitive Edition snd4u2gu.py |
| +0 (record) | u16, u16, u32, u32 | id; flags (0x8000, plus category shifted left by 11, plus 2 × count); first entry; x | unverified | Definitive Edition snd4u2gu.py |
| +0 (entry) | char[], u32, 76 bytes | wave path (NUL-terminated); wave type id; parameters, a 4-byte key at +12 | unverified | Definitive Edition snd4u2gu.py |

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

## Stream request (`.stq`)

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | ? | layout not documented for MH4U. Definitive Edition names sequence ids in `bgm_bat.stq` (Gogmazios's two phases are ids 32 and 33, with a volume in dB) | unknown | Definitive Edition snd_bgm.py |

## Checks (with game files)

- **SN1:** survey the sound entries of the three RomFS (`mhuc survey`): the count per type id and per version for each kind above, MH4U against MH3U against MHXX. That tells whether MH3U's versions are MH4U's.
- **SN2:** parse every MH4U `MADP`, `SNDB`, `SREQ` and `SES` with this layout. Count files whose sizes and offsets close exactly, and record the counts, never bytes. A field becomes verified when every file agrees.
- **S3:** MHXX's wave, bank and request against Definitive Edition's GU layouts (`SBKR` v4, `SRQR` v5, wave v2). If they agree, the XX → 4U conversion is the 4U → GU rule run backwards.
- **S4:** the `.stq` layout, from `rLtSoundStreamRequest`'s loader in the MH4U recompile.
