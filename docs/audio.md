# Audio

Every sound and piece of music the mod adds comes from its source game's files, converted to MH4U's formats and played by MH4U's own sound engine through request ids. The port needs no audio change: Azahar plays whatever the game asks for. Formats: [specs/sound.md](../specs/sound.md).

## What the mod needs

| Kind | For | Played through | Comes from |
|---|---|---|---|
| monster sounds (roars, voices, steps, attacks) | each new monster | the monster's bank and requests, by id from its code and motions | the monster's own game |
| monster themes | monsters with a theme | stream requests: `bgm_bat.stq` for the monster's own theme, the stage's `bgm_st_NN.stq` for a stage's theme (below) | the monster's own game |
| map music | each new locale | the stage's stream requests | the locale's own game (the map version chosen) |
| area ambience | each area: emitters, reverb and EQ zones | `rMHSoundEmitter` files in the area archives | the locale's own game |
| weapon sounds | gear from 3U or GU monsters | per-weapon banks | the gear's game, or MH4U's class sounds where only the model is new |
| underwater | the muffled mix, bubbles, underwater ambience and music | to find in MH3U: a category filter or the reverb | MH3U |
| jingles and UI | only for a new hub or screen | system requests | the hub's own game |

## What is known

- **MH3U uses MH4U's sound classes,** with the same class ids, but its file versions are one older (SN1): waves `MADP` version 4 against 5, banks `SNDB` 10 against 11, requests `SREQ` 6 against 8, stream requests 0x20 against 0x22. `mhuc` now reads all four older kinds and checks them against the whole MH3U RomFS: 10,132 waves, 1,225 banks, 1,004 requests and 106 stream requests, each closing on its last byte ([specs/sound.md](../specs/sound.md#checks-with-game-files), check SN6). Converting 3U's files to MH4U's versions, and making the game play the new request ids, is still undone. Its RomFS ships no area emitter file at all.
- **MHXX uses the next generation of classes,** shared with MHGU on Switch: its banks (`SBKR` version 4) and requests (`SRQR` version 5) carry GU's magics and versions, while its waves are `MADP` version 5 like MH4U's. Its stream requests are `STQR` 4 and its area emitters are `rFestaSoundEmitter` (version 0x20160706) against MH4U's `rMHSoundEmitter` (0x20120623). MHGU Definitive Edition converts MH4U sound to GU's formats with rules taken from Capcom's own conversions, and its waves convert bit for bit (both are DSP-ADPCM). If MHXX's banks and requests match GU's layouts, the same rules run backwards.
- **MH4U's layouts** come from MHGU Definitive Edition and are unverified, except the stream request (`.stq`): its tables are checked against all 50 files and `mhuc` reads every stream request in MH4U (214, 50 loose and 164 inside ARCs), matching every loose stream record to the wave header it names ([specs/sound.md](../specs/sound.md#stream-request-strq-a-stream-table-and-a-sequence-table), check S4). The 100-byte sequence record is read in the game's own code too ([specs/sound.md](../specs/sound.md#stream-request-strq-a-stream-table-and-a-sequence-table), check S7): the loader builds the id-to-row index, and the sequence driver reads the cue's type, selectors, priority, levels and durations.
- **Code asks for request ids.** A monster's code and its motions' sound events name request ids, resolved through its own request file, so ids only clash within one loaded set. Area and stage ids are per stage.
- **Music is per stream request id:** Gogmazios's two phases are ids 32 and 33 of `bgm_bat.stq`, each naming its wave, level and loop through the stream request. A new theme needs a free id there, or a stream request of its own: the sequence record carries the id, the dB level and the stream index, the stream record the wave's path, length, samples, channels, rate and loop. The 100-byte sequence record carries more than those three: the type at +0x08, four track selectors at +0x10 to +0x16, a priority at +0x18, the level (+0x24) and a fade's start level (+0x28) in dB, two durations (+0x44, +0x48) and the stream slot the loader resolves (+0x60). The game reads each of those (S7), so a new theme copies them from an existing row of its own type; only the words listed as having no reader in the spec may be left at an existing row's values.
- **A monster's theme is chosen in code, not in a data table.** A hardcoded switch over the monster id returns one sequence id and one of three sources; see below.

## How MH4U picks a monster's theme

### The selector

`0x30e148`..`0x30e514` (0x3cc bytes, MH4U USA v1.3.0 `code.bin`) is the selector. Its first argument is `sSoundControl`, the game's sound manager (`sSoundControl`, class id `0x10163337`, DTI `0x010b5560`, size 0x1840; its singleton pointer is the literal at `0x00fccd6c`). Its signature is `(sSoundControl *sound, u32 emId, u8 *kind, u32 *theme)`: it writes a kind byte and a sequence id.

The kind byte says where the theme comes from:

| Kind | Theme source |
|---|---|
| 1 | the stage's stream request, `sound/bgm/stage/bgm_st_NN.stq` |
| 2 | the battle stream request, `sound/bgm/battle/bgm_bat.stq` |
| 255 | none: the monster has no theme |

It reads five inputs:

- **the monster id:** the caller passes `byte[data+0x1c0]` of the monster's data block at `monster+0xe28`, the same field the rest of MH4U's id-indexed tables use ([reference/README.md](../reference/README.md#mh4u-monster-tables));
- **the stage number:** `byte[*(0x00fb6b7c)+0xc8c]` (`sGameControl`+0xc8c), used to override themes on stages 7, 11 and 12;
- **Gogmazios's phase:** `byte[sound+0x1838]`, set to 1 at `0x308fc4`..`0x308fe8` when the monster's work block `+0xca` is 1 (the phase-2 roar);
- **the Speartip Crag arena check** for ids 24 and 110: `0x6c3b60(*(0x00fcf45c), 1, 1)`, true once the arena's first breakable is broken (Definitive Edition reads it as kobj 1, area 1, state `+0xb1` of the stage's k00), which picks id 12 over 11;
- **a check for id 82:** `0x6b9160(*(0x00fbeffc))`, which picks its own theme 39 over 13.

Who calls it:

- `0x311ab8` (0x2b0 bytes) is called from the quest/stage update `0x659c84` (which also reads the stage global). It resolves each of the four battle slots through `0x683438`, reads the monster's id and calls the selector.
- `0x305698` (0x1278 bytes), the `sSoundControl` state machine (its state byte is at `sound+0x177b`), calls it twice (at `0x305bd4` and `0x306370`) on the transitions that start and change a fight's music.
- `0x308720` (0xffc bytes) calls it once (at `0x3093fc`).

The result is cached per monster in one of the four 16-byte battle slots at `sound+0x1700`: `+0` active, `+2` the monster's u16 key, `+4` the selector's kind, `+8` the theme id. `0x30daf0(sound, key, kind, theme)` writes a slot, or takes a free one. The state machine turns a slot into a request. A request is a 20-byte record at `sound+0x169c+20*i`: `+0` active, `+2` state, `+4` which stream request the id is looked up in, `+8` the theme id, `+0x10` the monster key. `0x306d48(sound, byte)` returns the loaded stream request for that byte: 1 the stage's `.stq`, 2 `bgm_bat`, 5 the area streams, and 0, 3, 4, 6, 7, 8 the common, event, lobby, system and download requests. `0xcebb8c(request, id)` finds the sequence record by id.

The request's creator `0x309d38` passes the kind straight to `0x306d48`, so the selector's kind is the stream request's kind: 1 the stage's `.stq`, 2 `bgm_bat`.

### The answers

The switch covers ids 0 to 123. Every id not listed in the table returns kind 1, theme 11, which plays the stage's own battle theme. Ids 83 and 111 (Dalamadur's two tails) return 255, no theme. The rest:

| Kind, theme | Monster ids | Sequence and stream |
|---|---|---|
| 1, 11 | every id not listed here or below | the stage `.stq`'s id 11, `bgm_stage_NN` (stage 19 has no id 11, so its lookup finds no sequence) |
| 2, 11 | 11, 12, 80, 121 | `bgm_em011` |
| 2, 13 | 31; 82 while its check is false | `bgm_em031` |
| 2, 14 | 33 | `bgm_em033` |
| 2, 15 | 19, 45, 112 | `bgm_em019` |
| 2, 16 | 30 | `bgm_em030` |
| 2, 17 | 32 | `bgm_em032` |
| 2, 18 | 77, 78 | `bgm_em077` |
| 2, 19 | 79 | `bgm_em079` |
| 2, 20 | 42, 43, 113 | `bgm_em042` |
| 2, 21 | 48, 49, 114 | `bgm_em048` |
| 2, 22 | 44, 98 | `bgm_em044` |
| 2, 23 | 13, 14, 15, 16, 25, 47, 94 | `bgm_mid01` |
| 2, 26 | 28 | `bgm_em028` |
| 2, 27 | 29 | `bgm_em029` |
| 2, 28 | 34, 35 | `bgm_em034` |
| 2, 29 | 89 at phase state 2 | `bgm_Eiyu` |
| 2, 30 | 65, 66 | `bgm_em065` |
| 2, 31 | 88, 122 | `bgm_em088` |
| 2, 32 | 89 at any other phase state | `bgm_em089` |
| 2, 33 | 89 at phase state 1 | `bgm_em089_2` |
| 2, 34 | 97 | `bgm_em097` |
| 2, 35 | 117 | `bgm_em117` |
| 2, 36 | 116 | `bgm_em116` |
| 2, 37 | 103 | `bgm_em103` |
| 2, 39 | 82 while its check is true | `bgm_em082` |
| 1, 12 | 24, 110 while the arena check is true | the stage `.stq`'s id 12; on stage 8, `bgm_em024_2` |
| 1, 11 | 24, 110 while the arena check is false | the stage `.stq`'s id 11; on stage 8, `bgm_em024` |
| 255, 0 | 83, 111 | none |

**Stages 7, 11 and 12 override the theme of 23 ids** to kind 1, theme 11 (the stage's own battle theme): 11, 12, 13, 14, 15, 16, 25, 28, 29, 30, 34, 35, 44, 47, 48, 49, 80, 88, 94, 97, 114, 121, 122. Every other id keeps its answer on those stages.

43 of the 124 ids have a theme of their own (kind 2); 79 fall back to their stage's theme; 2 have none.

### The two stream requests

Both are `rLtSoundStreamRequest` resources, and both hold the sequence in a 36-byte stream table and a 100-byte sequence table ([specs/sound.md](../specs/sound.md#stream-request-strq-a-stream-table-and-a-sequence-table)).

- **`sound/bgm/battle/bgm_bat.stq`**: 26 streams, 40 sequences. The sequence ids 11 to 39 are the themes; 13 to 39 are the monsters' own, one stream each; id 11 is `bgm_em011`, the theme the four ids in the table above use; ids 12, 24 and 25 are empty (no stream) and ids 0 to 10 are control rows. A stream record names its `.mca` (`sound/bgm/battle/wav/bgm_emNNN.mca`), its byte size, sample count, channels, rate, loop start and loop end; a sequence record holds its id, its volume in dB and its stream index. `bgm_em089` and `bgm_em089_2` are the ids 32 and 33 already named above.
- **`sound/bgm/stage/bgm_st_NN.stq`**: one per stage that has battle music (15 files: stages 1 to 8, 10, 11, 13, 15, 17, 18 and 19; stage 12 uses `bgm_st_11`; 9, 14 and 16 have none). Each has id 10 as the camp jingle (`bgm_map_NN`) and id 11 as the stage's battle theme (`bgm_stage_NN`). Some stages replace id 11 with a monster's theme: stage 6 has `bgm_em046` and `bgm_em046_2` at 11 and 12 and `bgm_Eiyu` at 13, stage 8 has `bgm_em024` and `bgm_em024_2` at 11 and 12, and stage 10 has `bgm_em077` at 11. Stage 19 has only the jingle; there a kind 1 lookup finds no sequence, and only a kind 2 theme (Gogmazios's) plays from the battle `.stq`.
- **Which file is loaded:** `sSoundControl` keeps the loaded requests at `sound+0x1674` (common), `+0x1678` (stage), `+0x167c` (`bgm_bat`), `+0x1680`/`+0x1684` (event), `+0x1688` (area streams), `+0x168c` (lobby), `+0x1690` (system) and `+0x1694` (download). Its loader `0x3099c8` takes a kind 0 to 8; kind 2 loads `bgm_bat` from the path at `0x00f006a4`, kind 1 loads the stage's `.stq` from the path table at `0x00f00624` indexed by stage, and kind 5 loads the area's stream request from the table at `0x00f005b0`. The paths are the game's own strings the resource manager resolves.

So a monster theme is **not** in the quest, in the stage's data or in a per-monster file: the quest only supplies the monster id, and the selector maps that id to (kind, sequence id). The stage matters twice: it filters 23 ids on stages 7, 11 and 12, and, for kind 1, it chooses which stage's `.stq` holds the sequence.

### What a new monster must add

1. **Its id, in the usual places.** The quest's monster list and the id-indexed tables ([reference/README.md](../reference/README.md#mh4u-monster-tables), [decisions.md](decisions.md#0003-id-allocation-and-mod-saves)). The theme follows the id; no sound data goes in the quest.
2. **A selector answer for the id.** The switch has no row for a new id, so it returns kind 1, theme 11. A plugin hooks `0x30e148` and answers for the new id instead. Kind 2 for a theme of its own; kind 1 if it should share its stage's battle theme; 255 for none. A phase, like Gogmazios's, is a second answer for the same id, keyed on `sound+0x1838` or on the monster's own state.
3. **A stream and a sequence in the stream request the kind selects.** For kind 2, add the theme to `bgm_bat.stq`: a stream record for the `.mca` and a sequence record with an unused id (12, 24 and 25 carry no stream, or append an id past 39 and raise the count), its volume and its stream index. Copy the other words the game reads ([specs/sound.md](../specs/sound.md#stream-request-strq-a-stream-table-and-a-sequence-table), S7) from an existing row whose type at +0x08 fits; the type is what picks the track setup. For kind 1, add it to that stage's `bgm_st_NN.stq` at id 11 or 12, as the boss stages do. Nothing else in the game names the theme.
4. **The wave.** The `MADP` `.mca` in `sound/bgm/battle/wav/` (kind 2) or `sound/bgm/stage/wav/` (kind 1), at the path the stream record gives, with the size, samples, channels, rate and loop the record repeats.
5. **Its own sound bank and requests**, as for any ported monster; the theme is separate from those.

A monster that reuses its stage's battle theme needs only steps 1, 2 (kind 1) and 5. A monster that reuses another monster's theme needs only a selector answer naming that theme's id: the ids only clash within one loaded set, and the theme is a stream request, not a bank.

### How this was checked

- **The selector:** read in MH4U USA v1.3.0's `code.bin`. Its answer for every id 0 to 123 was produced by running the function under Unicorn with a stand-in `sSoundControl`, stage 1 and stage 7, and phase states 0, 1 and 2, with the two conditional helpers forced both ways. The addresses above are the entry points; the table is the emulator's output, cross-checked against the stream names in `bgm_bat.stq` and the stage `.stq` files.
- **The `.stq` tables:** every `.stq` in MH4U USA v1.3.0's RomFS was parsed with the layout in [specs/sound.md](../specs/sound.md#stream-request-strq-a-stream-table-and-a-sequence-table) and each stream record's file size, sample count, channels, rate, loop start and loop end was compared with the `MADP` header of the `.mca` it names: all 497 loose streams agree. Only counts and names are recorded, never bytes.
- **The sequence record and the index:** check S7 reads the loader (0x004044b0), its index builder (0x00404310), the lookup (0xcebb8c), `sSoundControl`'s loader (0x003099c8) and the sequence driver (0xbd0ea8), counts every field over all 214 files, and records which words have a reader and which don't.
- **Still open:** the meaning of `0x6b9160`'s check for id 82, and which of stages 7, 11 and 12 are which locales (the stage's path table shows 12 uses `bgm_st_11`).


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
2. The meaning of the `.stq` sequence words the spec leaves unverified, and how much of a music stream stays in memory while it plays.
3. How MH3U muffles the mix and swaps the ambience when the hunter dives.

## In-game checks, once it runs

- A converted monster's roar and theme play on cue, at a volume matching MH4U's monsters, compared by ear with the source game.
- A converted locale's ambience follows the hunter from area to area, with no silent area and no doubled emitter.
