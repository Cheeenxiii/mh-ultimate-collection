# In-game checks

Behaviour that only the running game can confirm. Checks against files alone live in each spec's *Checks* section and mostly run through `mhuc survey`.

Record a result as pass, fail or numbers, never as bytes from the game.

## Build and launch (end to end)

Needs the MH4U USA v1.3.0 update, the fork on `uc/main` and a C compiler.

1. Build the fork's sample plugin: `cc -shared -fPIC -Iinclude tools/plugin_sample/sample_plugin.c -o sample_plugin.so`.
2. Make a mod folder with that library and a `mod.json` that hooks `sMhPad::update`, then add it with the fork's `tools/mods.py add`.
3. `tools/build_game.py --dump <update> --install`. The build reports the mod's hooks and one native plugin.
4. Start the game. The log shows the plugin loaded, and the game reaches the save-data screen.
5. Remove the mod and build again. The plugin list is gone and the log has no plugin lines.

Last result: pass on 2026-11-23, Linux, headless runner. The port's own pad features were not covered, because the runner lacks them.

## Extra Data records

`mhuc extdata testkit <Extra Data folder> --key K --out kit/` builds the files for the three checks below, encrypted, with a `TESTKIT.txt` listing what to look for. Back up the Extra Data first and copy the files in with a save manager.

| Check | What | Pass |
|---|---|---|
| Q17 | a stored quest copied into an empty slot under a new id and title | the quest is listed and plays |
| Q19 | the same with a longer title, so the `.mib` builder lays it out again | the quest is listed with the new title and plays like the original |
| E4 | a DLC Palico renamed in `otomo1` | the Palico is shown with its new name |

Full steps: [specs/quest.md](../specs/quest.md) (Q17, Q19) and [specs/extdata.md](../specs/extdata.md) (E4). Status: open.

## Extra Data in the port

The checks above can run in the port instead of on a console, once this one passes.

1. Run the fork's `tools/extdata_path.py` on the USA v1.3.0 exheader. It prints the game's Extra Data id and where Azahar keeps the folder.
2. Start the game once with a fresh user folder and open the DLC menu. Pass: the folder exists and holds `quest1` to `quest5`, `otomo1`, `card1` to `card3` and `cardbox`.
3. Copy a console's Extra Data files there and restart. Pass: the downloaded quests are listed, as on the console.

Status: open.

## Local DLC server

| Check | What | Pass |
|---|---|---|
| D1 | point the DLC screen at a local server that answers the login with its own key and serves one quest encrypted with it | the game downloads and lists the quest, and its Extra Data slot reads back in the stored form |
| D2 | decrypt the server's `DLC_EventQuestInfo_eng.txt` list with the login key | its layout is written into specs/quest.md |

Status: open. goshawk documents the protocol but is AGPL-3.0, so a server here would be written from the protocol, not from its code.

## Monster actions

| Check | What | Pass |
|---|---|---|
| R1 | force the same action id on a Rathian in MH4U and in MHXX, for a sample of ids in categories 3 and 7 | each forced id plays the same move in both games |

Needs a plugin that writes the two action bytes (MH4U: bytes 0x1ca and 0x1cb of the block at `this+0xe28`; MHXX: `this+0x6bf0` and `+0x6bf1`). Status: open, the plugin doesn't exist yet.
