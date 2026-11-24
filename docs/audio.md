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

- **MH3U uses MH4U's sound classes,** with the same class ids. 3U's sound may need little more than new request ids, unless the file versions differ.
- **MHXX uses the next generation of classes,** shared with MHGU on Switch. MHGU Definitive Edition converts MH4U sound to GU's formats with rules taken from Capcom's own conversions, and its waves convert bit for bit (both are DSP-ADPCM). If MHXX's files match GU's layouts, the same rules run backwards.
- **MH4U's layouts** come from MHGU Definitive Edition and are unverified.
- **Code asks for request ids.** A monster's code and its motions' sound events name request ids, resolved through its own request file, so ids only clash within one loaded set. Area and stage ids are per stage.
- **Music is per stream request id:** Gogmazios's two phases are ids 32 and 33 of `bgm_bat.stq`. A new theme needs a free id there, or a stream request of its own.

## Unknowns

1. The file versions of each sound kind in MH3U and MHXX against MH4U (check SN1).
2. Whether MHXX's layouts are GU's.
3. How MH4U picks a monster's theme: a per-monster table, the quest, or the stage.
4. The `.stq` layout.
5. The sound memory budget: whether the game reserves a fixed amount for loaded banks and streams, which larger 3U or XX banks could exceed. Where the sound system allocates its heap, in the recompile, says.
6. How MH3U muffles the mix and swaps the ambience when the hunter dives.

## In-game checks, once it runs

- A converted monster's roar and theme play on cue, at a volume matching MH4U's monsters, compared by ear with the source game.
- A converted locale's ambience follows the hunter from area to area, with no silent area and no doubled emitter.
