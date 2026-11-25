#!/usr/bin/env python3
"""Check data/ids/registry.csv and keep the plugin's generated header in step with it.

The registry is the one file that records every id a ported content takes
(docs/decisions.md#0003-id-allocation-and-mod-saves). It is a CSV with one row per id:

    kind,id,key,source_game,source_key,name,stand_in,files,notes

- `kind`      what kind of id it is. Monster ids are checked today; another kind needs its
              range and rules added here first.
- `id`        the id in MH4U. Monsters start at 124 (MH4U uses 0 to 123). 124 to 223 are
              permanent; a monster ported after that range is full takes an id from 256 up,
              which the plugin lends a byte of 224 to 255 to for each quest that names it.
              224 to 255 are therefore not registry ids.
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
              covers every path in its group, except motions, which takes the motion-list slots
              shipped, as a slot or a range: `motions=0-4` or `motions=0,2,3,4`. A slot it does
              not name keeps the stand-in's path.
- `notes`     free text.

Rules checked: each id is inside its kind's range and unique, permanent monster ids are
consecutive from 124 (every permanent id up to the highest one used needs a row in each table;
pooled ids may skip), each key, source game and source key is valid, `files` names known kinds
once each and gives `motions` slots in 0..5, and every line of the plugin's header is the one
this file generates.

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
# `motions` names the slots the port ships as a list, and the rest keep the stand-in's path.
MOTION_SLOTS = 6
# MH4U's own monster ids are 0 to 123 (reference/README.md#mh4u-monster-tables). 124 to 223
# are the permanent ids; 224 to 255 are the bytes a quest lends from the pool, whose monsters
# take ids from 256 up (docs/decisions.md#0003). 255 is what a guild quest card's one-byte
# monster id can hold, and 0xffffffff ends a quest's monster list (specs/quest.md), so a
# registry id stops before it.
MONSTER_FIRST = 124
PERMANENT_LAST = 223
POOL_FIRST = 224
POOL_LAST = 255
REGISTRY_POOL_FIRST = 256
REGISTRY_POOL_LAST = 0xFFFFFFFE
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


SLOT = re.compile(r"\d+\Z")
SLOT_RANGE = re.compile(r"(\d+)-(\d+)\Z")


def files_tokens(text: str) -> list[tuple[str, str | None]]:
    """One row's `files` as (kind, value or None) tokens.

    `motions` is the one kind with a value, and that value is a comma-separated slot list:
    `motions=0-4` or `motions=0,2,3,4`. The commas in the slot list are part of the motions
    value, not another kind, so a bare number after a motions token extends it.
    """
    tokens: list[list[str | None]] = []
    for raw in text.split(","):
        piece = raw.strip()
        kind, sep, value = piece.partition("=")
        kind = kind.strip()
        if sep:
            tokens.append([kind, value.strip()])
        elif tokens and tokens[-1][0] == "motions" and SLOT.match(piece):
            tokens[-1][1] = f"{tokens[-1][1]},{piece}"
        elif SLOT_RANGE.match(piece) or SLOT.match(piece):
            tokens.append([piece, None])
        else:
            tokens.append([kind, None])
    return [(str(kind), value) for kind, value in tokens]


def slots_of(value: str) -> tuple[list[int], str | None]:
    """The slots a motions value names, and the first part that isn't a slot or a range."""
    slots: list[int] = []
    for part in value.split(","):
        part = part.strip()
        span = SLOT_RANGE.match(part)
        if span:
            first, last = int(span.group(1)), int(span.group(2))
            if first > last:
                return slots, part
            slots.extend(range(first, last + 1))
        elif SLOT.match(part):
            slots.append(int(part))
        else:
            return slots, part
    return slots, None


def motion_slots(text: str) -> list[int] | None:
    """The motion-list slots one row's `files` names, sorted, or None when it ships none."""
    for kind, value in files_tokens(text):
        if kind != "motions":
            continue
        if value is None:
            return []
        slots, _bad = slots_of(value)
        return sorted(set(slots))
    return []


def check_files(where: str, text: str) -> list[str]:
    """What is wrong with one row's `files`: empty, unknown, twice, or a bad motion slot."""
    if not text.strip():
        return [f"{where}: files is empty; name the kinds the port ships, or it has no files"]
    problems: list[str] = []
    seen: set[str] = set()
    for kind, value in files_tokens(text):
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
            if value is None:
                problems.append(f"{where}: motions needs the slots the port ships, as "
                                f"motions=0,2,3 or motions=0-4")
                continue
            slots, bad = slots_of(value)
            if bad is not None:
                problems.append(f"{where}: motions={value!r} has {bad!r}, not a slot or a range")
                continue
            out_of_range = [slot for slot in slots if not 0 <= slot < MOTION_SLOTS]
            if out_of_range:
                problems.append(f"{where}: motion slot {out_of_range[0]} isn't in "
                                f"0..{MOTION_SLOTS - 1}")
            if len(slots) != len(set(slots)):
                problems.append(f"{where}: motions={value!r} names a slot twice")
        elif value is not None:
            problems.append(f"{where}: only motions takes a value, not {kind!r}")
    return problems


def motion_mask(row: dict[str, str]) -> int:
    """The motion-list slots a row ships, as one bit per slot."""
    return sum(1 << slot for slot in (motion_slots(row["files"]) or []))


def check_rows(rows: list[dict[str, str]]) -> list[str]:
    """What is wrong with the registry's rows."""
    problems: list[str] = []
    seen: dict[tuple[str, int], str] = {}
    keys: dict[str, str] = {}
    permanent_ids: list[int] = []
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
        if not MONSTER_FIRST <= ident <= REGISTRY_POOL_LAST:
            problems.append(
                f"{where}: monster id {ident} isn't in {MONSTER_FIRST}..{PERMANENT_LAST} "
                f"(permanent) or {REGISTRY_POOL_FIRST}..{REGISTRY_POOL_LAST:#x} (pooled)")
        elif POOL_FIRST <= ident <= POOL_LAST:
            problems.append(
                f"{where}: monster id {ident} is a byte the plugin lends from the pool "
                f"({POOL_FIRST}..{POOL_LAST}); a monster ported after the permanent range "
                f"takes a registry id from {REGISTRY_POOL_FIRST} up")
        elif (kind, ident) in seen:
            problems.append(f"{where}: id {ident} is already {seen[(kind, ident)]}'s")
        else:
            seen[(kind, ident)] = row["key"]
            if ident <= PERMANENT_LAST:
                permanent_ids.append(ident)
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
    if permanent_ids:
        wanted = list(range(MONSTER_FIRST, MONSTER_FIRST + len(permanent_ids)))
        if sorted(permanent_ids) != wanted:
            missing = sorted(set(wanted) - set(permanent_ids))
            problems.append(f"permanent monster ids must be consecutive from {MONSTER_FIRST}; missing {missing}")
    return problems


def c_identifier(key: str) -> str:
    return "MHUC_MONSTER_ID_" + key.upper().replace("-", "_")


def file_mask(row: dict[str, str]) -> str:
    """One row's `files` as the C expression of its kind bits."""
    kinds = {kind for kind, _count in files_tokens(row["files"])}
    return " | ".join(f"MHUC_FILES_{kind.upper()}" for kind in FILE_KINDS if kind in kinds)


def render_header(rows: list[dict[str, str]]) -> str:
    """The plugin's header for the registry's permanent and pooled monster ids."""
    monsters = [r for r in rows if r["kind"] == "monster"]
    permanent = sorted((r for r in monsters if int(r["id"], 0) <= PERMANENT_LAST),
                       key=lambda r: int(r["id"], 0))
    pooled = sorted((r for r in monsters if int(r["id"], 0) > PERMANENT_LAST),
                    key=lambda r: int(r["id"], 0))
    lines = [
        "/* Generated from data/ids/registry.csv by tools/check_ids.py --write.",
        " * Do not edit: edit the registry and run the tool. Licence: GPL-3.0-or-later. */",
        "#ifndef MHUC_IDS_H",
        "#define MHUC_IDS_H",
        "",
        "#include <stdint.h>",
        "",
        f"/* MH4U's own monster ids are 0 to {MH4U_MONSTER_LAST}. A ported monster takes",
        f" * {MONSTER_FIRST} and up: {MONSTER_FIRST} to {PERMANENT_LAST} are permanent, and a",
        f" * monster registered from {REGISTRY_POOL_FIRST} up is lent a free byte from",
        f" * {POOL_FIRST} to {POOL_LAST} for each quest that names it",
        " * (docs/decisions.md#0003-id-allocation-and-mod-saves). */",
        f"#define MHUC_MONSTER_FIRST {MONSTER_FIRST}",
        f"#define MHUC_MONSTER_LAST {PERMANENT_LAST}",
        f"#define MHUC_MONSTER_POOL_FIRST {POOL_FIRST}",
        f"#define MHUC_MONSTER_POOL_LAST {POOL_LAST}",
        f"#define MHUC_MONSTER_POOL_SIZE {POOL_LAST - POOL_FIRST + 1}",
        f"#define MHUC_REGISTRY_POOL_FIRST {REGISTRY_POOL_FIRST}",
        "",
        "/* The kinds of file a ported id's resource record names. The record the plugin builds",
        " * rewrites the id token only in the paths of the kinds a port ships; the rest keep the",
        " * stand-in's path, because MH4U does not tolerate a missing file. */",
    ]
    for n, kind in enumerate(FILE_KINDS):
        lines.append(f"#define MHUC_FILES_{kind.upper()} 0x{1 << n:04x}u")
    lines += [
        "",
        f"#define MHUC_MOTION_SLOTS {MOTION_SLOTS}u",
        "#define MHUC_MOTION_SLOT(slot) (1u << (slot))",
        "",
        "/* One ported monster: the id it takes, the MH4U monster id whose rows the reader",
        " * hooks answer with until the port ships this monster's own rows, the motion-list slots",
        " * it ships (MHUC_MOTION_SLOT bits), and the kinds of file it ships (MHUC_FILES_* bits).",
        " * A slot or kind it does not ship keeps the stand-in's path. */",
        "typedef struct MhucMonsterId {",
        "    uint32_t id;",
        "    unsigned char stand_in;",
        "    unsigned char motion_mask;",
        "    unsigned short files;",
        "} MhucMonsterId;",
        "",
        "/* The permanent ids, consecutive from 124. */",
        f"#define MHUC_MONSTER_COUNT {len(permanent)}",
    ]
    if permanent:
        lines.append("static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT] = {")
        for row in permanent:
            slots = motion_slots(row["files"]) or []
            lines.append(f"    {{{int(row['id'], 0)}, {int(row['stand_in'], 0)}, "
                         f"0x{motion_mask(row):02x}u, /* slots {', '.join(map(str, slots)) or 'none'} */ "
                         f"{file_mask(row)}}},")
        lines.append("};")
    else:
        lines.append("/* Empty: a dummy entry keeps the array valid C. */")
        lines.append("static const MhucMonsterId mhuc_monster_ids[1] = {{0, 0, 0, 0}};")
    lines += [
        "",
        "/* The pooled ids: each is lent one byte of 224 to 255 for a quest that names it. */",
        f"#define MHUC_POOLED_MONSTER_COUNT {len(pooled)}",
    ]
    if pooled:
        lines.append("static const MhucMonsterId mhuc_pooled_monster_ids[MHUC_POOLED_MONSTER_COUNT] = {")
        for row in pooled:
            slots = motion_slots(row["files"]) or []
            lines.append(f"    {{{int(row['id'], 0)}, {int(row['stand_in'], 0)}, "
                         f"0x{motion_mask(row):02x}u, /* slots {', '.join(map(str, slots)) or 'none'} */ "
                         f"{file_mask(row)}}},")
        lines.append("};")
    else:
        lines.append("/* Empty: a dummy entry keeps the array valid C. */")
        lines.append("static const MhucMonsterId mhuc_pooled_monster_ids[1] = {{0, 0, 0, 0}};")
    lines.append("")
    for row in permanent + pooled:
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
    permanent = [int(r["id"], 0) for r in monsters if int(r["id"], 0) <= PERMANENT_LAST]
    pooled = [int(r["id"], 0) for r in monsters if int(r["id"], 0) > PERMANENT_LAST]
    print(f"ids ok ({os.path.relpath(args.registry, ROOT)}: {len(permanent)} permanent monsters, "
          f"ids {min(permanent, default=0)}..{max(permanent, default=0)}; {len(pooled)} pooled)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
