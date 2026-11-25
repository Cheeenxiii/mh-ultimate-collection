#!/usr/bin/env python3
"""Check data/ids/registry.csv and keep the plugin's generated header in step with it.

The registry is the one file that records every id a ported content takes
(docs/decisions.md#0003-id-allocation-and-mod-saves). It is a CSV with one row per id:

    kind,id,key,source_game,source_key,name,stand_in,files,notes

- `kind`      what kind of id it is. Monster ids are checked today; another kind needs its
              range and rules added here first.
- `id`        the id in MH4U. Monsters start at 124 (MH4U uses 0 to 123) and go up to 255,
              the largest id a guild quest card's one-byte field can hold.
- `key`       the content's name in the registry, lowercase with hyphens, unique.
- `source_game`, `source_key`  where the content comes from: mh4u, mh3u, mhxx or mhgu and its
              own name there (a monster's `emNNN`).
- `name`      the content's name, for review.
- `stand_in`  the MH4U monster id whose rows the reader hooks answer with until the port
              ships this content's own rows (0 to 123).
- `files`     the kinds of file the port ships, comma-separated: model, motions, camera,
              tail, mef, sound, cmd, efl (the resource record's path kinds). The record the
              plugin builds rewrites the id token only in these kinds' paths; the rest keep
              the stand-in's path, because the game does not tolerate a missing file. A kind
              covers every path in its group, except motions, which takes the number of
              motion-list slots shipped from slot 0 (`motions=3`): the slots above keep the
              stand-in's paths.
- `notes`     free text.

Rules checked: each id is inside its kind's range and unique, monster ids are consecutive
from 124 (every id up to the highest one used needs a row in each table), each key, source
game and source key is valid, `files` names known kinds once each and gives `motions` a
count in 1..6, and every line of the plugin's header is the one this file generates.

`--write` writes the header. The header is checked in, so a wrong or stale one fails the
check: run `check_ids.py --write` after editing the registry, never edit the header.

Usage: check_ids.py [--registry PATH] [--header PATH] [--write]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "data", "ids", "registry.csv")
HEADER = os.path.join(ROOT, "mods", "monster_ids", "src", "ids.h")

COLUMNS = ("kind", "id", "key", "source_game", "source_key", "name", "stand_in", "files", "notes")
SOURCE_GAMES = ("mh4u", "mh3u", "mhxx", "mhgu")
# The resource record's path kinds, in the record's field order (mods/monster_ids/README.md):
# MH4U loads one path per kind, and a port ships some of them. A kind it does not ship keeps
# the stand-in's path, because a missing file stops the load (#143).
FILE_KINDS = ("model", "motions", "camera", "tail", "mef", "sound", "cmd", "efl")
# The motion-list fields hold this many slots (record +0x04, reference/README.md#mh4u-monster-tables);
# `motions=N` says the first N are the port's, and the slots above keep the stand-in's path.
MOTION_SLOTS = 6
# MH4U's own monster ids are 0 to 123 (reference/README.md#mh4u-monster-tables); 255 is what
# a guild quest card's one-byte monster id can hold (docs/decisions.md#0003).
MONSTER_FIRST = 124
MONSTER_LAST = 255
MH4U_MONSTER_LAST = 123
KEY = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
MONSTER_KEY = re.compile(r"em\d{3}\Z")


def parse_int(text: str) -> int | None:
    try:
        return int(text, 0)
    except ValueError:
        return None


def read_registry(path: str) -> tuple[list[dict[str, str]], list[str]]:
    """The registry's rows, and what is wrong with its shape."""
    problems: list[str] = []
    if not os.path.exists(path):
        return [], [f"{path}: no registry"]
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return [], [f"{path}: the registry is empty"]
    if tuple(rows[0]) != COLUMNS:
        return [], [f"{path}: the header must be {','.join(COLUMNS)}"]
    out = []
    for n, cells in enumerate(rows[1:], start=2):
        if len(cells) != len(COLUMNS):
            problems.append(f"{path}:{n}: needs {len(COLUMNS)} columns, has {len(cells)}")
            continue
        out.append(dict(zip(COLUMNS, cells, strict=True)))
    return out, problems


def files_tokens(text: str) -> list[tuple[str, str | None]]:
    """One row's `files` as (kind, count or None) tokens."""
    tokens = []
    for raw in text.split(","):
        kind, sep, count = raw.strip().partition("=")
        tokens.append((kind.strip(), count.strip() if sep else None))
    return tokens


def check_files(where: str, text: str) -> list[str]:
    """What is wrong with one row's `files`: empty, unknown, twice, or a bad motions count."""
    if not text.strip():
        return [f"{where}: files is empty; name the kinds the port ships, or it has no files"]
    problems: list[str] = []
    seen: set[str] = set()
    for kind, count in files_tokens(text):
        if not kind:
            problems.append(f"{where}: files has an empty kind")
            continue
        if kind not in FILE_KINDS:
            problems.append(f"{where}: file kind {kind!r} isn't one of {', '.join(FILE_KINDS)}")
            continue
        if kind in seen:
            problems.append(f"{where}: file kind {kind!r} is listed twice")
            continue
        seen.add(kind)
        if kind == "motions":
            if count is None:
                problems.append(f"{where}: motions needs the number of slots the port ships, as motions=3")
                continue
            slots = parse_int(count)
            if slots is None or not 1 <= slots <= MOTION_SLOTS:
                problems.append(f"{where}: motions={count!r} isn't a slot count in 1..{MOTION_SLOTS}")
        elif count is not None:
            problems.append(f"{where}: only motions takes a count, not {kind!r}")
    return problems


def motions_count(row: dict[str, str]) -> int:
    """The number of motion-list slots a row ships, 0 when it ships none."""
    for kind, count in files_tokens(row["files"]):
        if kind == "motions" and count is not None:
            slots = parse_int(count)
            return slots if slots is not None else 0
    return 0


def check_rows(rows: list[dict[str, str]]) -> list[str]:
    """What is wrong with the registry's rows."""
    problems: list[str] = []
    seen: dict[tuple[str, int], str] = {}
    keys: dict[str, str] = {}
    monster_ids: list[int] = []
    for n, row in enumerate(rows, start=2):
        where = f"row {n} ({row.get('key') or 'no key'})"
        kind = row["kind"]
        if kind != "monster":
            problems.append(f"{where}: kind {kind!r} has no id range in this tool yet")
            continue
        ident = parse_int(row["id"])
        if ident is None:
            problems.append(f"{where}: id {row['id']!r} isn't a number")
            continue
        if not MONSTER_FIRST <= ident <= MONSTER_LAST:
            problems.append(f"{where}: monster id {ident} isn't in {MONSTER_FIRST}..{MONSTER_LAST}")
        elif (kind, ident) in seen:
            problems.append(f"{where}: id {ident} is already {seen[(kind, ident)]}'s")
        else:
            seen[(kind, ident)] = row["key"]
            monster_ids.append(ident)
        if not KEY.match(row["key"]):
            problems.append(f"{where}: key {row['key']!r} isn't lowercase words joined by hyphens")
        elif row["key"] in keys:
            problems.append(f"{where}: key {row['key']!r} is already row {keys[row['key']]}")
        else:
            keys[row["key"]] = str(n)
        if row["source_game"] not in SOURCE_GAMES:
            problems.append(f"{where}: source_game {row['source_game']!r} isn't one of {', '.join(SOURCE_GAMES)}")
        if not MONSTER_KEY.match(row["source_key"]):
            problems.append(f"{where}: a monster's source_key is its file name, as em001")
        if not row["name"].strip():
            problems.append(f"{where}: no name")
        stand_in = parse_int(row["stand_in"])
        if stand_in is None or not 0 <= stand_in <= MH4U_MONSTER_LAST:
            problems.append(f"{where}: stand_in {row['stand_in']!r} isn't an MH4U monster id (0..{MH4U_MONSTER_LAST})")
        problems += check_files(where, row["files"])
    if monster_ids:
        wanted = list(range(MONSTER_FIRST, MONSTER_FIRST + len(monster_ids)))
        if sorted(monster_ids) != wanted:
            missing = sorted(set(wanted) - set(monster_ids))
            problems.append(f"monster ids must be consecutive from {MONSTER_FIRST}; missing {missing}")
    return problems


def c_identifier(key: str) -> str:
    return "MHUC_MONSTER_ID_" + key.upper().replace("-", "_")


def file_mask(row: dict[str, str]) -> str:
    """One row's `files` as the C expression of its kind bits."""
    kinds = {kind for kind, _count in files_tokens(row["files"])}
    return " | ".join(f"MHUC_FILES_{kind.upper()}" for kind in FILE_KINDS if kind in kinds)


def render_header(rows: list[dict[str, str]]) -> str:
    """The plugin's header for the registry's monster ids."""
    monsters = sorted((r for r in rows if r["kind"] == "monster"), key=lambda r: int(r["id"], 0))
    lines = [
        "/* Generated from data/ids/registry.csv by tools/check_ids.py --write.",
        " * Do not edit: edit the registry and run the tool. Licence: GPL-3.0-or-later. */",
        "#ifndef MHUC_IDS_H",
        "#define MHUC_IDS_H",
        "",
        f"/* MH4U's own monster ids are 0 to {MH4U_MONSTER_LAST}; a ported monster takes",
        f" * {MONSTER_FIRST} and up. {MONSTER_LAST} is the most a guild quest card's",
        " * one-byte id can hold (docs/decisions.md#0003-id-allocation-and-mod-saves). */",
        f"#define MHUC_MONSTER_FIRST {MONSTER_FIRST}",
        f"#define MHUC_MONSTER_LAST {MONSTER_LAST}",
        "",
        "/* The kinds of file a ported id's resource record names. The record the plugin builds",
        " * rewrites the id token only in the paths of the kinds a port ships; the rest keep the",
        " * stand-in's path, because MH4U does not tolerate a missing file. */",
    ]
    for n, kind in enumerate(FILE_KINDS):
        lines.append(f"#define MHUC_FILES_{kind.upper()} 0x{1 << n:04x}u")
    lines += [
        "",
        "/* One ported monster: the id it takes, the MH4U monster id whose rows the reader",
        " * hooks answer with until the port ships this monster's own rows, the number of",
        " * motion-list slots it ships from slot 0, and the kinds of file it ships",
        " * (MHUC_FILES_* bits). */",
        "typedef struct MhucMonsterId {",
        "    unsigned char id;",
        "    unsigned char stand_in;",
        "    unsigned char motions;",
        "    unsigned short files;",
        "} MhucMonsterId;",
        "",
        f"#define MHUC_MONSTER_COUNT {len(monsters)}",
        "static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT] = {",
    ]
    for row in monsters:
        lines.append(f"    {{{int(row['id'], 0)}, {int(row['stand_in'], 0)}, "
                     f"{motions_count(row)}, {file_mask(row)}}},")
    lines += ["};", ""]
    for row in monsters:
        lines.append(f"/* {row['name']}, {row['source_game']} {row['source_key']} */")
        lines.append(f"#define {c_identifier(row['key'])} {int(row['id'], 0)}")
    lines += ["", "#endif", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--registry", default=REGISTRY)
    ap.add_argument("--header", default=HEADER)
    ap.add_argument("--write", action="store_true", help="write the plugin's header from the registry")
    args = ap.parse_args(argv)

    rows, problems = read_registry(args.registry)
    problems += check_rows(rows)
    if problems:
        for p in problems:
            print(p)
        print("the registry is wrong; ids are permanent once shipped (docs/decisions.md#0003)", file=sys.stderr)
        return 1
    header = render_header(rows)
    if args.write:
        os.makedirs(os.path.dirname(os.path.abspath(args.header)), exist_ok=True)
        with open(args.header, "w", encoding="utf-8", newline="") as f:
            f.write(header)
        print(f"wrote {os.path.relpath(args.header, ROOT)}")
        return 0
    on_disk = ""
    if os.path.exists(args.header):
        with open(args.header, encoding="utf-8", newline="") as f:
            on_disk = f.read()
    if on_disk != header:
        print(f"{os.path.relpath(args.header, ROOT)} isn't what the registry generates: "
              "run tools/check_ids.py --write")
        return 1
    monsters = [r for r in rows if r["kind"] == "monster"]
    first, last = (int(monsters[0]["id"], 0), int(monsters[-1]["id"], 0)) if monsters else (0, -1)
    print(f"ids ok ({os.path.relpath(args.registry, ROOT)}: {len(monsters)} monsters, ids {first}..{last})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
