#!/usr/bin/env python3
"""Check the format specs in specs/ against the rules in specs/README.md.

- every spec (`*.md` other than README.md) starts with front matter naming class, extension,
  games and status;
- every field table (a table whose header has Offset and Status) has the columns Offset, Type,
  Name, Status and Source; each row's Status is verified, unverified or unknown, and its Source
  isn't empty;
- the front matter's status is no higher than its lowest field (unknown < unverified < verified);
- a field marked verified is backed by a Checks section;
- every .ksy has a .md of the same name.

Usage: check_specs.py [SPECS_DIR]   (default: specs/ next to tools/). Exit status 1 on problems.
"""
from __future__ import annotations

import os
import sys

STATUSES = ("unknown", "unverified", "verified")
REQUIRED = ("class", "extension", "games", "status")
COLUMNS = ("offset", "type", "name", "status", "source")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def check_text(name: str, text: str) -> list[str]:
    problems = []
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return [f"{name}: no front matter"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return [f"{name}: front matter isn't closed"]
    meta = {}
    for line in lines[1:end]:
        key, _, value = line.partition(":")
        meta[key.strip()] = value.strip()
    for key in REQUIRED:
        if not meta.get(key):
            problems.append(f"{name}: front matter lacks {key}")
    declared = meta.get("status", "")
    if declared and declared not in STATUSES:
        problems.append(f"{name}: front matter status {declared!r} isn't one of {', '.join(STATUSES)}")
    lowest = None
    has_checks = any(line.strip().lower().startswith("## checks") for line in lines)
    i = end + 1
    tables = 0
    while i < len(lines):
        line = lines[i]
        rule = lines[i + 1].replace("|", "").strip() if i + 1 < len(lines) else "x"
        if line.lstrip().startswith("|") and rule and set(rule) <= set("-: "):
            header = [c.lower() for c in _cells(line)]
            i += 2
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                rows.append(_cells(lines[i]))
                i += 1
            if "offset" not in header or "status" not in header:
                continue
            tables += 1
            missing = [c for c in COLUMNS if c not in header]
            if missing:
                problems.append(f"{name}: a field table lacks {', '.join(missing)}")
                continue
            si, so = header.index("status"), header.index("source")
            for row in rows:
                status = row[si] if si < len(row) else ""
                if status not in STATUSES:
                    problems.append(f"{name}: field {row[0]!r} has status {status!r}")
                    continue
                if not (so < len(row) and row[so]):
                    problems.append(f"{name}: field {row[0]!r} has no source")
                if status == "verified" and not has_checks:
                    problems.append(f"{name}: field {row[0]!r} is verified but there's no Checks section")
                rank = STATUSES.index(status)
                lowest = rank if lowest is None else min(lowest, rank)
        else:
            i += 1
    if tables == 0:
        problems.append(f"{name}: no field table")
    if declared in STATUSES and lowest is not None and STATUSES.index(declared) > lowest:
        problems.append(f"{name}: front matter says {declared} but a field is {STATUSES[lowest]}")
    return problems


def check_dir(root: str) -> list[str]:
    problems = []
    for dirpath, _, files in os.walk(root):
        for f in sorted(files):
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, root)
            if f.endswith(".md") and f != "README.md":
                with open(path, encoding="utf-8") as fh:
                    problems += check_text(rel, fh.read())
            elif f.endswith(".ksy") and not os.path.exists(path[:-4] + ".md"):
                problems.append(f"{rel}: no matching .md")
    return problems


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    root = argv[0] if argv else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "specs")
    problems = check_dir(root)
    for p in problems:
        print(p)
    if not problems:
        print(f"specs ok ({root})")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
