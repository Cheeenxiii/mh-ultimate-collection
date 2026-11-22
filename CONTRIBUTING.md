# Contributing

Read [LEGAL.md](LEGAL.md) first. The short version: nothing from the games, or derived from them, goes in the repository.

- **Commits:** small and focused, one-sentence subject saying what changed. Docs change in the same commit as the code they describe.
- **Tests:** every tool change comes with a pytest test whose fixtures the test generates itself. `python3 -m pytest` and `ruff check .` pass before you push.
- **Specs:** each field is `verified` (checked against a real file, with the procedure written down) or `unverified` (with the public source it comes from). Credit the source.
- **Catalog:** one fact per cell, a source URL per row, no game text beyond names.
- **Authored content:** only where no source game has the thing. Add a row to [the authored register](docs/sources/authored-register.md) in the same commit.
- **Engine changes** go to [Cheeenxiii/MH4UltimateDC-fork](https://github.com/Cheeenxiii/MH4UltimateDC-fork), on a branch from `uc/main`, in upstream's style so they stay mergeable.
