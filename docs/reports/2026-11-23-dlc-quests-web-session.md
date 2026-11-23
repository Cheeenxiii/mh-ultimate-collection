# DLC quests from Extra Data: report (2026-11-23)

A web session with no RomFS or code dumps. The only game files were the maintainer's own MH4U (USA) Extra Data and save `system` file, which they uploaded as an archive. Because STATUS.md's next tasks all need the RomFS, the session took the step that file allows: the quest spec. The maintainer allowed it to download mhef's cipher code, keys included. That code and the decrypted files stayed in the session's scratchpad, outside both repositories. Nothing from them was committed, neither code nor key nor bytes: only counts, sizes, offsets and names. The engine fork is unchanged.

## Done

| Task | Result | Where |
|---|---|---|
| `mhuc entropy` | size, 8-byte alignment, entropy and a verdict (dense or plain) for files or folders. The bar for dense is lowered for short files, which measure under 8 bits per byte even when random. 4 tests on generated data | `tools/mhuc/entropy.py`, `tests/test_entropy.py`, README |
| Extra Data crypto (Q3, Q4) | all 11 files are dense. mhef's `SavedataCipher` (MH4G) decrypts every one with a matching checksum: `quest*` in quest mode, `card*` in card mode, the rest in normal mode | specs/quest.md |
| Quest slots (Q5) | a `quest*` file holds 40 slots of 0x2010 bytes plus a 120-byte zero tail. A slot is empty or holds one bare `.mib`, with no ARC around it. 120 quests in all, 80 slots empty. The last 16 bytes of a used slot are not a hash (Q8 found what they are) | specs/quest.md |
| `.mib` header | the whole layout from the mhff wiki's "MH4U rQuestData Format" page, field by field, credited. Verified on the 120 quests: the magic, the flags offset, the supply, reward, large-monster, intruder and text offsets; the supply, reward-item, monster and intruder list strides and end markers; the 5×7 text pointers to UTF-16. Value ranges recorded for the time, stars, carve table, quest id and size percentage, with those fields left unverified | specs/quest.md |
| Second pass (Q7, Q8) | large monsters come in waves (a 0-terminated list of definition lists); small monsters are a 0-terminated list of areas; all 7 strings of all 5 languages decode; supply items verified; value spreads recorded for the objectives, flags and unknown bytes. Objective types seen: 0x1, 0x81, 0x101, 0x204 (target always a monster of the quest), 0x2 (never one: an item, presumably), 0x2004. The slot trailer is the quest's file name, `m` + the five-digit quest id + `.mib` | specs/quest.md |
| Server quest files (Q9) | Capcom's server is gone (NXDOMAIN), so the maintainer approved the GrenderG/goshawk preservation mirror. Its 120 USA and 120 EUR quest files (identical) decrypt with mhef's `DLCCipher`, SHA-1 checked. Each is a bare `.mib` (no ARC, against mhff's convert_quest.py) and is byte-identical to the start of the matching Extra Data slot. The game adds 28 bytes after it (unknown: not a hash of the file or name) | specs/quest.md |
| MH3U DLC quests (Q10) | 38 USA quests in the goshawk mirror, identical in EUR and on Wii U; 47 for Japan's MH3G. Container understood: ECB with an 8-byte block cipher, then the plaintext size as a big-endian u32. The key isn't known: goshawk's MH3G login key and mhef's keys give no plaintext. The `QTDS` layout is still unspecified | specs/quest.md |
| MHXX DLC quests (Q11) | 188 files of MHXX JPN's mirror folder decrypt (mhef's `DLCXCipher` logic with goshawk's key; MHXX ends with one 0x100 signature, not two). 173 quest ARCs, each ending with a 249-byte `.mib`; mhff's MHXX header checked on all 173 (id = archive name, message reference = `rGUIMessage` + the GMD stem); the boss blocks don't fully fit mhff's 13 bytes | specs/quest.md |
| MH3U quests (Q12) | the maintainer's MH3U 3DS Extra Data turned out to be plain. Its 38 stored quests are the mirror's 38 USA quests, decrypted. quest-studio's `QTDS` layout (MIT) parses all 38 to the last byte of the arena block: header, five-language texts, monsters, rewards, money, objectives, the 442-byte tail. A slot is the server file decrypted, byte for byte in length. The server cipher, unknown at that point, was then found in Cha-Cha (Q14) | specs/quest.md |
| MH3U DLC cipher (Q14) | Cha-Cha (GPL-3.0, an MH3U Wii U recompilation) documents it: MT Framework's own Blowfish variant, MtCipher (little-endian words, a quirk in the S-box schedule). With goshawk's MH3G key, all 38 USA and 47 Japanese MH3G quests decrypt, SHA-1 checked. A stored quest is the server file decrypted, except that the SHA-1's first two bytes are zeroed and the padding is left as ciphertext | specs/quest.md |
| Credits | mhff wiki pages and mhef (GPL-3.0) | specs/README.md |

## What it changes for the plan

- **3U and GU quests have a target format.** The converter can write MH4U `.mib` files: the header, the monster lists and the text block are now understood well enough to build one, though most value meanings still need in-game checks.
- **DLC quests are plain `.mib` files once out of Extra Data.** A mod quest could also go in through Extra Data slots, as downloaded quests do, without touching `quest00.arc`/`quest01.arc` or the quest-id tables. Whether the game lists such a quest after the slot is re-encrypted is an in-game question. A slot is the server's file, 28 unexplained bytes, zeros and the file name. The 28 bytes, a signature perhaps, are the open part: whether the game checks them decides if a mod quest can go in this way.
- **The `.emd`/`.etd` task has no public source.** Nothing turned up for MH4U's `rEnemyData` or `rEnemyTuneData` (mhff, Silvris, searches), so that spec has to come from the files and the code, in a session with the RomFS.

## Not done

- The quest downloader. The maintainer overrode ground rule 5 for this session, but the environment's proxy refuses `goshawk.capcom.co.jp` (403, host not allowed), and mhef's downloader uses plain HTTP, which the proxy doesn't carry at all. The maintainer then ran it on their own machine: the host doesn't resolve, and public DNS gives NXDOMAIN. Capcom's MH4U DLC server is gone. The server's files were taken from the goshawk mirror instead (Q9).
- STATUS.md's next tasks 1 to 4: each needs the RomFS or code dumps, which this session didn't have.
- Q6: the same checks on the game's own 508 `.mib`.
- `card*`, `cardbox`, `otomo1` and `system` decrypt, but their contents weren't examined. mhff's wiki has "MH4U card1 Format" and "MH4U DLC Palico Format" pages for them.
- The workspace's `/next` and `/handoff` skills aren't installed in web sessions. This session followed them by hand from `tools/workspace/skills/`.

## Checklist for the next session

0. MH3U quests: Q13, the `QTDS` checks on the RomFS's 365 `.quest` files. The DLC cipher and the stored form are known (Q14), so new DLC-style MH3U quests can be built; whether the game checks the zeroed hash bytes is an in-game question.
1. With the RomFS: Q6 (the Q5 checks on `quest00.arc`/`quest01.arc`) promotes the header rows from DLC-only to the game's own quests.
2. `.emd`/`.etd` specs from the files, with no public layout to start from.
3. Re-running Q3 to Q5 needs mhef's `SavedataCipher` (the key is in mhef's `mhef/n3ds.py`, not in this repository): decrypt into a folder outside the repositories, then split each `quest*` file at 0x2010.
