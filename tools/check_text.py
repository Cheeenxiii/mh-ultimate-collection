#!/usr/bin/env python3
"""Check data/ids/notes.csv against the ported monster ids, and a built mod table against both.

Each ported monster id answers MH4U's name and notes text with its own message. The name comes
from `data/ids/registry.csv`; the notes come from the source game's own table, recorded per id
in `data/ids/notes.csv`:

    id,source_game,source_file,source_entry,source_index

`source_file` is a path in that game's RomFS, `source_entry` the GMD's path inside an ARC
(empty for a loose GMD), and `source_index` the string's index in that table. The rows are
addresses/counts, not text: the builder (`mhuc text build`) reads the player's own dumps.

Rules checked: every ported monster has exactly one notes row, every row names a ported id,
the source game is the registry's, the path is a RomFS path, and the index is a non-negative
number. With `--mod`, the built table (`text/monster_text.bin`) must hold exactly those ids
with the registry's names.

Usage: check_text.py [--registry PATH] [--notes PATH] [--mod PATH]
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from mhuc import monstertext  # noqa: E402


def check_mod(path: str, registry: list[dict[str, str]], notes: list[dict[str, str]]) -> list[str]:
    """The built table must hold exactly the registry's ids and names."""
    problems: list[str] = []
    try:
        with open(path, "rb") as f:
            entries = monstertext.read_mod_text(f.read())
    except (OSError, monstertext.TextError) as e:
        return [f"{path}: {e}"]
    by_id = {int(r["id"], 0): r["name"] for r in registry}
    wanted = set(notes_ids(notes))
    got = {e.id for e in entries}
    for ident in sorted(wanted - got):
        problems.append(f"{path}: no entry for id {ident}")
    for ident in sorted(got - wanted):
        problems.append(f"{path}: entry for id {ident}, which has no notes row")
    for e in entries:
        if e.id in by_id and e.name != by_id[e.id]:
            problems.append(f"{path}: id {e.id} is named {e.name!r}, the registry says "
                            f"{by_id[e.id]!r}")
        if not e.notes:
            problems.append(f"{path}: id {e.id} has no notes")
    return problems


def notes_ids(notes: list[dict[str, str]]) -> list[int]:
    out = []
    for row in notes:
        try:
            out.append(int(row["id"], 0))
        except ValueError:
            pass
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=monstertext.REGISTRY)
    ap.add_argument("--notes", default=monstertext.NOTES)
    ap.add_argument("--mod", help="the installed mod folder's text/monster_text.bin")
    args = ap.parse_args(argv)

    registry = monstertext.registry_rows(args.registry)
    try:
        notes = monstertext.read_notes(args.notes)
    except (OSError, monstertext.TextError) as e:
        print(e)
        return 1
    problems = monstertext.check(registry, notes)
    if args.mod:
        problems += check_mod(args.mod, registry, notes)
    if problems:
        for p in problems:
            print(p)
        print("a ported monster's text must come from its source game (data/ids/notes.csv)",
              file=sys.stderr)
        return 1
    print(f"text ok ({os.path.relpath(args.notes, ROOT)}: {len(notes)} notes source(s) for "
          f"{len(registry)} ported monster(s)" + (f"; {args.mod} matches" if args.mod else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
