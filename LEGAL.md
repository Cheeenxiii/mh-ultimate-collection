# Legal

Monster Hunter 3 Ultimate, Monster Hunter 4 Ultimate, Monster Hunter Generations Ultimate and Monster Hunter XX are © CAPCOM. Nintendo 3DS and Nintendo Switch are © Nintendo. This project is not affiliated with, endorsed by, or sponsored by either company.

## Ground rules

1. **No game data in the repository, ever.** No ROM images, `code.bin`, exheaders, RomFS or ExeFS files, `.arc` archives, models, textures, audio, text, saves or keys, not even small excerpts.
2. **Nothing derived from game data either.** No traces, captures, disassembly listings, screenshots, extracted tables, converted assets or hex dumps. Addresses, class names and field offsets in specs and config files are fine, as upstream MH4UltimateDC does.
3. **Bring your own dumps.** Each player dumps the games they own on their own hardware. We don't link to, host or help find copies. Issues asking for game files are closed.
4. **Clean-room contributions.** No code from leaked SDKs or proprietary sources. Use public documentation, credited community research and your own reverse engineering.
5. **Tests use generated data.** Fixtures are built by the tests themselves from synthetic values.

The CI's guard (`tools/check_no_game_data.py`) refuses the obvious cases. It is a backstop, not permission: when unsure, ask in an issue before committing.

*This is not legal advice.*
