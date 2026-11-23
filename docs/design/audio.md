# Audio

**Plan:** every sound and every piece of music the mod adds comes from its source game's own files: 3U's from MH3U 3DS, GU-era from MHXX 3DS (CLAUDE.md, rule 2). Each is converted to MH4U's formats and played by MH4U's own sound engine through its request ids, the way MH4U's content is. The port needs no audio change: Azahar's DSP plays whatever the game asks for. Formats: [specs/sound.md](../../specs/sound.md).

## What the mod needs

| Kind | For | Played through | Comes from |
|---|---|---|---|
| Monster sounds (roars, voices, steps, attacks) | each new monster | the monster's bank and request, by request id from its code and motions | the monster's own game |
| Monster themes | monsters with a theme of their own | stream requests (`bgm_bat.stq` holds one id per theme, with a volume) | the monster's own game |
| Map music | each new locale: stage theme and per-area streams | the stage's stream requests | the locale's own game (MH3U or MHXX, depending on the map version chosen) |
| Area ambience | each area of a new locale: emitters (wind, water, creatures), reverb and EQ zones | `rMHSoundEmitter` files in the area archives | the locale's own game |
| Weapon sounds | gear from 3U or GU-era monsters | per-weapon banks (Definitive Edition found GU's are class templates) | the gear's own game, or 4U's class sounds where the model is new but the class isn't |
| Underwater | swimming, the muffled mix, bubbles, underwater ambience and music | to be found in MH3U: a category filter (`rLtSoundCategoryFilter` is in both MH3U's and MH4U's registries) or the reverb | MH3U |
| Quest and hub jingles, UI | only if a new hub or a new screen needs them (progression.md) | system requests | the hub's own game |

## What we know

- **MH3U uses MH4U's sound classes.** Both registries have `rLtSoundSourceADPCM`, `rLtSoundBank`, `rLtSoundRequest`, `rLtSoundStreamRequest` and `rMHSoundEmitter`, with the same ids. 3U's sound may need little more than renaming and new request ids, unless the file versions differ (check S1).
- **MHXX uses the next generation**, `rSoundSourceADPCM`, `rSoundBank`, `rSoundRequest`, with the same ids as MHGU Switch. MHGU Definitive Edition converts MH4U sound into GU's formats with rules derived from Capcom's own 4U → GU conversions (43 monster pairs, 579 weapon pairs). Its waves convert bit for bit, since both are DSP-ADPCM. If MHXX's files match those GU layouts (check S3), the same rules run backwards give XX → 4U.
- **MH4U's own layouts** come from Definitive Edition, credited and still unverified ([specs/sound.md](../../specs/sound.md)).
- **Request ids are what code asks for.** A monster's code and its motions' sound events name request ids, which resolve through its request file to bank keys and waves. New monsters bring their own request files, so ids clash only within one loaded set, not across the game. Area and stage ids are per stage.
- **Music is per stream request id**: Gogmazios's two phases are ids 32 and 33 of `bgm_bat.stq`. A new theme needs a free id in that file, or a stream request of its own. That is an id table for [id-tables.md](id-tables.md) ("BGM, effects, sounds per monster").

## Unknowns to settle first

1. The file versions of each sound kind in MH3U and MHXX against MH4U (SN1).
2. MHXX's layouts against GU's (S3).
3. How MH4U picks a monster's theme: a per-monster table, the quest, or the stage. Its readers set the bound to move (id-tables.md).
4. The `.stq` layout (S4).
5. Sound memory: whether the game keeps a fixed budget for loaded banks and streams. 3U's or XX's banks are larger, or more of them load in one quest, could exceed it. This can be checked in the recompile, by finding where the sound system allocates its heap.
6. Underwater: how MH3U muffles the mix and swaps the ambience when the hunter dives (underwater.md, "What to lift").

## Order of work

1. SN1 survey, alongside the next RomFS session (it's counts only, so pair it with quest checks Q6 and Q13).
2. Verify the MH4U layouts on MH4U's own files (SN2), then `mhuc sound` to list and decode waves to WAV for checking by ear, on the maintainer's machine only. No output is committed.
3. The first monster port's sounds, as part of that monster: bank, request, waves, and its theme if it has one.
4. The first locale's music and ambience, with its map.
5. Underwater audio, with the swim state (underwater.md, step 3).

## Decisions it touches

- **Music versions** (open-decisions.md, "Music and sound versions"): when a theme exists in several games, which one plays.
- **Map versions:** a locale's music and ambience follow the map version chosen (open-decisions.md, "Map versions and lighting").
- **GU Switch assets:** GU's Switch audio (48 kHz Opus) is outside rule 2 like its textures. It would only ever come in through the optional-pack route.

## In-game checks (later)

- A converted monster's roar and its theme play on cue, at a volume matching MH4U's monsters. The check is by ear against the source game, with timings noted in a check note.
- A converted locale's ambience follows the hunter from area to area, with no silent area and no doubled emitter.
