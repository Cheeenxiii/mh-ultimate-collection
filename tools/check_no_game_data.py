#!/usr/bin/env python3
"""Refuse game data, and files derived from it, in the repository's tracked files.

A smaller cousin of MH4UltimateDC's tools/check_no_game_data.py. Rules (each offending path is
printed with the rule it broke; exit status 1):

    name         ROM, RomFS and ExeFS names: .3ds .cci .cia .cxi .cfa .nsp .xci .arc .sav,
                 code.bin, exheader.bin, anything under baserom/ build/ dumps/ export/
    binary       a file with a NUL byte in its first 8 KiB or that isn't UTF-8 text
                 (game assets are binary; ours are text)
    size         a file over 1 MB
    listing      more than 50 lines of hex dump or C byte arrays

Usage: check_no_game_data.py [PATH...]   (default: `git ls-files` of the current repository)
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

FORBIDDEN_EXT = {".3ds", ".cci", ".cia", ".cxi", ".cfa", ".nsp", ".xci", ".arc", ".sav", ".bin",
                 ".png", ".jpg", ".jpeg", ".bmp", ".tga", ".ppm", ".wav", ".elf", ".zip", ".7z"}
FORBIDDEN_DIRS = {"baserom", "build", "dumps", "export"}
MAX_SIZE = 1 << 20
HEX_LINE = re.compile(r"^\s*(?:[0-9a-fA-F]{4,8}[:\s]\s*)?(?:[0-9a-fA-F]{2}\s+){8,}")
C_BYTES = re.compile(r"(?:0x[0-9a-fA-F]{2}\s*,\s*){16,}")


def problems(path: str, data: bytes) -> list[str]:
    """The rules `path` (with content `data`) breaks."""
    out = []
    parts = path.replace("\\", "/").split("/")
    ext = os.path.splitext(parts[-1])[1].lower()
    if ext in FORBIDDEN_EXT or parts[-1].lower() in {"code.bin", "exheader.bin"} \
            or any(p in FORBIDDEN_DIRS for p in parts[:-1]):
        out.append("name")
    if len(data) > MAX_SIZE:
        out.append("size")
    try:
        if b"\0" in data[:8192]:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "NUL")
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        out.append("binary")
        return out
    listing = sum(1 for line in text.splitlines() if HEX_LINE.match(line) or C_BYTES.search(line))
    if listing > 50:
        out.append("listing")
    return out


def tracked_files() -> list[str]:
    res = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in res.stdout.decode().split("\0") if p]


def main(argv: list[str] | None = None) -> int:
    paths = (argv if argv is not None else sys.argv[1:]) or tracked_files()
    bad = 0
    for path in paths:
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as f:
            data = f.read()
        for rule in problems(path, data):
            print(f"{path}: {rule}")
            bad += 1
    if bad:
        print("game data, or data derived from it, must never be committed (LEGAL.md)", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
