# Contributing

Read [LEGAL.md](LEGAL.md) first: nothing from the games, or derived from them, goes in the repository.

- **Commits** are small and do one thing. The subject says what changed, in the imperative. The body says why, when that isn't obvious.
- **Tests** protect a real risk or a bug that was fixed, and fail when that behaviour breaks. `python3 -m pytest` passes before you push.
- **Specs** mark each field `verified` (checked on real files, with the procedure written in the spec) or `unverified` (with its public source).
- **Catalog** rows carry a source URL each.
- **Authored content** is allowed only where no source game has the thing, and gets a row in the [authored register](docs/sources.md#authored-register).
- **Engine changes** go to [the fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork), on a branch from `uc/main`.
- **Docs** describe the project as it is. History belongs in commit messages.
