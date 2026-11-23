# A local DLC responder (quest route 3)

**Point:** MH4U still has its DLC screen. If the port answered the requests that screen makes, the game would download mod quests itself and store them in Extra Data in its own form (specs/quest.md, Q16). This note gathers what is known about the protocol, what a responder would need, and what stays open. Whether the mod uses this route, Extra Data files (route 2) or the quest archives (route 1) is an open decision (quest-conversion.md, "Routes into the game"; rule 6).

Sources: GrenderG/goshawk (`app.py`, AGPL-3.0), a replacement DLC server for the 3DS and Wii U Monster Hunter games; mhff's wiki page "MHX DLC Key Negotiation" (GPL-3.0); mhef's `DLCCipher` (GPL-3.0). Nothing here was checked against the game's code: all of it is unverified for MH4U until check D1 below.

## The exchange, as goshawk serves it

| Step | Request | Reply | Status | Source |
|---|---|---|---|---|
| login | `POST https://<server>/SSL/3ds/mh4g_us/login.cgi` (Europe: `mh4g_eu`) | raw bytes, no Content-Type: u16 BE key length, the Blowfish key in Shift-JIS with a NUL, u16 BE URL length, the base URL for the files (no NUL) | unverified | goshawk `make_login_v1_response` |
| lists | `GET <base>/DLC_*.txt`: info lists per kind and language (`DLC_EventQuestInfo_eng.txt`, `DLC_OtomoInfo_eng.txt`, `DLC_Info_List_eng.txt`, …), served as Shift-JIS text | the mirror's files (encrypted like the quests, presumably; their plain format isn't documented) | unknown | goshawk; the mirror's file names |
| files | `GET <base>/m60001.mib`, `ot001_eng.otb`, … | the files encrypted with the login key: Blowfish over the plaintext and its SHA-1, then the size (mhef `DLCCipher`) | verified for the cipher (quest.md Q9), unverified for the route | mhef; goshawk |

Two consequences:

- **The key is the server's to choose.** The game takes whatever key the login reply carries (goshawk hands each game its key this way). A responder could use a key of its own and encrypt mod quests with it: no Capcom key would be needed or shipped. This holds only if MH4U doesn't check the key against one of its own (check D1).
- **The game stores what it downloads as Q16 describes.** So a quest served this way and one written into Extra Data by `mhuc questslot put` end up identical. Route 3 only replaces the copying step with the game's own download.

## What a responder needs

1. **Catching the requests.** The game talks HTTPS to Capcom's host through the 3DS HTTP service. In the port, that service is Azahar's. A responder can sit behind it (answering in-process, no network) or be a local server the runtime's DNS points at. Either needs the certificate check passed or skipped (goshawk relies on Pretendo or an SSL patch on a console).
2. **The list files.** The DLC menu builds its list from the `DLC_*.txt` files, whose plain format isn't documented. Decrypting the mirror's copies (with the login key, as Q9 did for quests) would show it. That decryption needs the maintainer's go-ahead and a permission rule (see the 2026-11-23 report).
3. **Quest ids.** Event quests use ids 60000 to 69999 (quest.md Q5). Mod quests would need a range that no official DLC uses (60999 and 61000 are the test kit's).
4. **Licence.** goshawk is AGPL-3.0. Its code can't be copied into this GPL-3.0 project without making the combined work AGPL. It informs this note only. A responder would be written from the protocol.

## Checks

- **D1 (open):** in the port, point the DLC screen at a local responder that answers the login with a key of its own and serves one quest encrypted with that key (`dlccrypt`). Pass: the game downloads and lists the quest, and its Extra Data slot reads back as Q16 says.
- **D2 (open):** decrypt the mirror's `DLC_EventQuestInfo_eng.txt` with the login key and write its layout into specs/quest.md.
