# Audio

Every sound and piece of music the mod adds comes from its source game's files, converted to MH4U's formats and played by MH4U's own sound engine through request ids. The port needs no audio change: Azahar plays whatever the game asks for. Formats: [specs/sound.md](../specs/sound.md).

## What the mod needs

| Kind | For | Played through | Comes from |
|---|---|---|---|
| monster sounds (roars, voices, steps, attacks) | each new monster | the monster's bank and requests, by id from its code and motions | the monster's own game |
| monster themes | monsters with a theme | stream requests (`bgm_bat.stq` holds one id per theme, with a volume) | the monster's own game |
| map music | each new locale | the stage's stream requests | the locale's own game (the map version chosen) |
| area ambience | each area: emitters, reverb and EQ zones | `rMHSoundEmitter` files in the area archives | the locale's own game |
| weapon sounds | gear from 3U or GU monsters | per-weapon banks | the gear's game, or MH4U's class sounds where only the model is new |
| underwater | the muffled mix, bubbles, underwater ambience and music | to find in MH3U: a category filter or the reverb | MH3U |
| jingles and UI | only for a new hub or screen | system requests | the hub's own game |

## What is known

- **MH3U uses MH4U's sound classes,** with the same class ids, but its file versions are one older (SN1): waves `MADP` version 4 against 5, banks `SNDB` 10 against 11, requests `SREQ` 6 against 8, stream requests 0x20 against 0x22. 3U's sound therefore needs version-aware readers or a conversion; new request ids alone don't make it play. Its RomFS ships no area emitter file at all.
- **MHXX uses the next generation of classes,** shared with MHGU on Switch: its banks (`SBKR` version 4) and requests (`SRQR` version 5) carry GU's magics and versions, while its waves are `MADP` version 5 like MH4U's. Its stream requests are `STQR` 4 and its area emitters are `rFestaSoundEmitter` (version 0x20160706) against MH4U's `rMHSoundEmitter` (0x20120623). MHGU Definitive Edition converts MH4U sound to GU's formats with rules taken from Capcom's own conversions, and its waves convert bit for bit (both are DSP-ADPCM). If MHXX's banks and requests match GU's layouts, the same rules run backwards.
- **MH4U's layouts** come from MHGU Definitive Edition and are unverified.
- **Code asks for request ids.** A monster's code and its motions' sound events name request ids, resolved through its own request file, so ids only clash within one loaded set. Area and stage ids are per stage.
- **Music is per stream request id:** Gogmazios's two phases are ids 32 and 33 of `bgm_bat.stq`. A new theme needs a free id there, or a stream request of its own.

## Memory

MH4U reserves no heap of its own for sound. MT Framework Mobile creates its allocators at start-up from a hardcoded table at 0x00f2bb44, read by 0x0010612c: nine heaps, carved in 4 KiB pages out of the application memory at 0x08000000. The three that concern sound:

| Index | Name | Size | What it holds |
|---|---|---|---|
| 11 | Resource | 47 MiB (49,283,072 B) | non-drawing resources: models, motions, sound and the rest |
| 15 | Sound | no heap | the gameplay sound classes, which fall back to the default "Heap" allocator |
| 21 | SoundBuffer | aliased to 11 | sound-buffer allocations, on the same Resource heap |

- The sound system object itself, `sLtSound` (0x9d90 bytes), is a `cSystem` (index 12, System 3,316 KiB), but its own size is negligible next to the loaded resources.
- The class-to-index table built at 0x00104904 gives `cResource` index 11, and `cMHSoundEmitter`, `cMHSoundSequence` and `nMHSoundSequence` index 15. The sound resource classes (`rLtSoundBank`, `rLtSoundRequest`, `rLtSoundSourceADPCM`, `rLtSoundStreamRequest`, `rMHSoundEmitter`, `rMHSoundSequence`) have no row of their own; their class-registry parent is `cResource`, index 11.
- The alias table at 0x00f2bc1c sends seven derived indices onto the nine heaps: SoundBuffer (21) to Resource (11), Area (14) to Unit (13), Network (17) to System (12), Effect (19), AI (18) and GUI (20) to Unit, and String (2) to Array (3). Nothing creates a heap for Sound (15) and the alias table does not redirect it, so a SOUND-indexed allocation lands on the default heap, the one index 0 uses.
- The shipped `/memory.ini` says the same for the CTR build: its `[Allocators: CTR]` section makes Resource 47MB, defines `SOUND_BUF = RESOURCE`, and defines no SOUND allocator. Its comment on the PC sections calls SOUND_BUF the sound waveform.
- The nine heaps total about 61 MiB of application memory: Resource 47 MiB, Unit/Area 7 MiB, System 3,316 KiB, Collision 1,792 KiB, CommandCache 768 KiB, Global 768 KiB, Temp 552 KiB, Array 72 KiB, Develop 100 KiB. A physical allocator of 640 KiB is added at index 5 (0x0010489c).

So loaded banks, requests and waves share the 47 MiB Resource heap with everything else that is not drawing. There is no fixed sound reservation for a larger MH3U or MHXX bank to exceed: it spends the shared heap on demand. [Check SN5](../specs/sound.md#checks-with-game-files) records the addresses and the procedure.

## How much MH4U's monster banks use

The 123 monster ARCs (`/data/emNNN.arc`) carry each monster's sound. The sizes are the decompressed, loaded sizes of the entries:

- 232 `SNDB` banks in all, 4,083,511 B together.
- Largest single bank: 73,066 B (`em017`).
- Largest complete sound set: 1,583,089 B (`em110` and `em111`): bank 10,693 B, request 14,860 B, waves 1,557,536 B. That is 3.2 % of the 47 MiB Resource heap, and 0.15 % for the largest bank alone.
- All 232 monster banks together are 8.3 % of it.

A quest loading two of the largest monsters puts at most about 3.2 MB of monster sound in the shared heap, under 7 % of it. The banks themselves are small; the waves are what take the room.

## Unknowns

1. Whether MHXX's bank and request layouts match GU's (check S3).
2. How MH4U picks a monster's theme: a per-monster table, the quest, or the stage.
3. The `.stq` layout, and with it how much of a music stream stays in memory while it plays.
4. How MH3U muffles the mix and swaps the ambience when the hunter dives.

## In-game checks, once it runs

- A converted monster's roar and theme play on cue, at a volume matching MH4U's monsters, compared by ear with the source game.
- A converted locale's ambience follows the hunter from area to area, with no silent area and no doubled emitter.
