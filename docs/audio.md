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

## Unknowns

1. Whether MHXX's bank and request layouts match GU's (check S3).
2. How MH4U picks a monster's theme: a per-monster table, the quest, or the stage.
3. The `.stq` layout.
4. The sound memory budget: whether the game reserves a fixed amount for loaded banks and streams, which larger 3U or XX banks could exceed. Where the sound system allocates its heap, in the recompile, says.
5. How MH3U muffles the mix and swaps the ambience when the hunter dives.

## In-game checks, once it runs

- A converted monster's roar and theme play on cue, at a volume matching MH4U's monsters, compared by ear with the source game.
- A converted locale's ambience follows the hunter from area to area, with no silent area and no doubled emitter.
