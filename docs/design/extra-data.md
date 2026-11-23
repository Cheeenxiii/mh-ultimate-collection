# Extra Data: what can reach MH4U without touching the RomFS

**Point:** MH4U loads whole records from its Extra Data, the save area where downloaded content lands: quests (`quest1`..`quest5`) and DLC Palicos (`otomo1`). Guild quests in the card files (`card1`..`card3`) are a third kind of record. All three can now be read, written in the exact form the game stores and encrypted back byte for byte. That makes Extra Data the quickest way to show content in game while the plugin layer (table growth, new archives) isn't ready. It doesn't settle any open decision (rule 6): which content goes this way, and whether players should get it through Extra Data at all, stay open.

Layouts: [specs/quest.md](../../specs/quest.md) (quest slots, checks Q16 and Q17) and [specs/extdata.md](../../specs/extdata.md) (cards, guild quests, Palicos, checks E1 to E6).

## The three record kinds

| Kind | Where | Capacity | Form the game stores | Tool | What's left |
|---|---|---|---|---|---|
| Quest (`.mib`) | `quest1`..`quest5`, 0x2010-byte slots | 40 per file, 200 in all; a `.mib` up to 0x2000 − 28 bytes | the server file decrypted up to its stated size: `.mib`, SHA-1 with bytes 0 and 1 zeroed, padding, size BE; the name at 0x2000 (Q16) | `mhuc questslot check\|put`, `mibwrite` | Q17 and Q19 in game: is a new or rebuilt quest listed and playable, and is the hash checked |
| DLC Palico (`.otb`) | `otomo1`, 0x90-byte slots | 9 slots in the file | the server file decrypted (record padded to 0x80, SHA-1, padding, size) at a 0x90 stride, the name over the hash: byte 15 of the hash at 0x8F, the full tail only after the last slot (E6) | `mhuc extdata dump\|check\|rename otomo` | E4 in game: is a renamed Palico shown, and is the hash byte checked |
| Guild quest | `card1`..`card3`, 50 records of 304 bytes each | 150 | mhff's layout, unverified: no record in the maintainer's data | `mhuc extdata dump card` | a card file holding a guild quest, then the in-game checks |

Every file round-trips through `mhuc decrypt mh4u-save` and `mhuc encrypt mh4u-save` byte for byte when given the file's own seed (E5), so whatever the game rejects will be the content, not the container.

## What each kind could carry, as options

- **Quests.** Converted 3U and GU quests whose monsters and maps MH4U already has (quest-conversion.md, route 2) can go in first. Once a new monster has an id, a quest naming it is the smallest test of that monster in game. Extra Data quests are event quests in MH4U's lists, so this suits event-style content, not quests woven into village or hub progression (progression.md).
- **Palicos.** The `.otb` record names skills, looks and colours by id. A GU-era Palico would need MH4U ids for its skills and looks, an id table like the quests' (quest-conversion.md, "What a converted quest needs"). Nine slots cap it.
- **Guild quests.** A guild quest names its monsters by a one-byte id (ids up to 255; id-tables.md) and its maps by id, with a level that scales the monsters. If the game accepts an edited guild quest, it is a cheap way to put a monster on a map at a chosen level without building a whole `.mib`.

## Limits and unknowns

- None of this has run in the game yet: Q17, Q19 and E4 are the first in-game checks to run, and they need a save manager (Checkpoint, JKSM) on a console or an emulator's save folder. `mhuc extdata testkit` builds all three files at once.
- The maintainer's Palicos are the `_ger` files. This Extra Data may come from a European game or a German-language system, while the base is MH4U USA v1.3.0 (rule 2). Quests are identical in both regions (quest.md Q9), but it's worth checking before relying on region-specific data.
- In the port, Extra Data is the runtime's SD extdata folder. The fork's `tools/extdata_path.py` reads the game's extdata id from its exheader and prints where Azahar keeps the folder (fork `docs/research/extdata.md`, Cheeenxiii/MH4UltimateDC-fork#5); the check there, that the game reads files put in it, lets Q17, Q19 and E4 run in the port instead of on a console.
