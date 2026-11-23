# MHGURecomp: what it offers this project

[morerokk/MHGURecomp](https://github.com/morerokk/MHGURecomp) (MIT) is a native PC port of **MHGU on Switch (v1.4.0)**. The game's 32-bit ARM code is statically recompiled to C at build time from the user's own files. Switch system services and the NVN graphics API are reimplemented, with Vulkan for rendering, and there is no emulator core. Read on 2026-11-23 (README and `docs/` at the default branch; release 0.19.1).

## Facts

- **Platforms:** Windows, Linux (glibc 2.39 or newer), Android (experimental). It needs Vulkan 1.2 and AVX2.
- **Status:** "fully playable, singleplayer and multiplayer" (README). The project is very active, with several releases a week in November 2026.
- **Multiplayer:** the game's Local Wireless mode over its own server, which can also be self-hosted, plus direct connect, session codes and a friends list. Crossplay with emulators is experimental.
- **Mods:**
  - romfs overlay, merging `.arc` entries across mods with a load order;
  - `.ips` and `.pchtxt` patches, a patched function running in an interpreter;
  - code modules (`exefs/subsdk1`, as [MHGU Definitive Edition](mhgu-definitive-edition.md) uses);
  - Forge `.nro` plugins and cheats;
  - "engine modules" (native code that extends the port, not the game: `docs/ENGINE-MODULES.md`).
- **Not documented:** a way for mods to grow the game's tables. The README doesn't say whether that is possible.

## How it relates to us

- **Fidelity.** Our MHGU source is the Switch v1.4.0 release, for English text only (CLAUDE.md, rule 2). MHGURecomp is that same release, so nothing it reveals about GU's text changes our sources. Its runtime and assets don't enter the mod.
- **As a base game:** considered and set aside on 2026-11-23 ([open-decisions.md](../design/open-decisions.md), "Base game"). GU's systems would replace 4U's, which is the opposite of this project's aim.
- **As a reference for the engine fork:** it shows a 3DS-era MT Framework game (GU descends from 4U's engine) running natively with its whole system layer reimplemented. That is the end state of the fork's `native` branch. Its notes on frame pacing, Local Wireless rooms and mod layering are worth reading before work there (the "Runtime" decision).
- **Licence.** MIT, compatible with GPL-3.0-or-later. Its own code could be reused with its notice kept. The recompiled game code a build produces is not covered by its licence or ours.

## Next steps it suggests

None for the mod now. For the fork's runtime work: read its `docs/STATUS.md` (runtime, services) and `docs/SWITCH_COMPARE.md` before designing the native layer.
