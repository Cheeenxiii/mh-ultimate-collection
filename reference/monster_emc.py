#!/usr/bin/env python3
"""The native actions a monster's AI script starts.

A monster's AI is its EMC script (rEnemyCmd, specs/emc.md). Its bytecode starts the monster
class's native actions as `00 cat num`, runs other action scripts as `14 nn`, and picks a
weighted branch with `02 ..`; the rest opens a condition block. This reads the `00 cat num`
pairs out of a monster's script, so a port can tell an action the AI picks in a normal fight
from one nothing in the AI reaches.

The EMC header is verified in all three games (check A1), but the bytecode reading is MHGU
Definitive Edition's heuristic (`tools/emc.py`, GPL-3.0-or-later), which infers the instruction
lengths; MH4U and MHXX share version 0x20120804, MH3U's is older (0x20110601). Treat the result
as the set of actions a script names, not as a complete decode: it can miss a call and, on a
newer script, name a pair a random branch guard happened to spell.

    monster_emc.py FILE            counts and the native actions, one per line
    monster_emc.py FILE --json     {"version": ..., "groups": [...], "actions": [[cat, num], ...]}
"""
from __future__ import annotations

import argparse
import json
import struct
import sys

VERSIONS = {0x20120804: "MH4U/MHXX", 0x20110601: "MH3U"}
CATEGORY_MAX = 14           # a category above this at a token start is not a native-action opcode


def parse(data: bytes) -> tuple[int, list[list[bytes]]]:
    """(version, groups of scripts): the header and the group tables, each script a byte string."""
    if len(data) < 0x10 or data[:4] != b"EMC\0":
        raise ValueError("not an EMC (magic)")
    version, groups = struct.unpack_from("<II", data, 4)
    out = []
    for g in range(groups):
        count, table = struct.unpack_from("<II", data, 0x10 + 16 * g)
        scripts = []
        for i in range(count):
            length, offset = struct.unpack_from("<II", data, table + 16 * i)
            if offset + length > len(data):
                raise ValueError(f"group {g} script {i} runs past the file")
            scripts.append(data[offset:offset + length])
        out.append(scripts)
    return version, out


def refs(script: bytes) -> set[tuple[int, int]]:
    """The `00 cat num` native actions a script names, and the `14 nn` calls skipped over."""
    out: set[tuple[int, int]] = set()
    i = 0
    while i < len(script):
        b = script[i]
        if b == 0x00 and i + 2 < len(script) and script[i + 1] < CATEGORY_MAX:
            out.add((script[i + 1], script[i + 2]))
            i += 3
        elif b == 0x14 and i + 1 < len(script):
            i += 2
        elif b == 0x02 and i + 1 < len(script):
            i += 3 if script[i + 1] == 0x01 else 2
        elif i + 1 < len(script) and script[i + 1] in (0x00, 0x01):
            # a condition block opener with a sub-code and one argument
            i += 3
        else:
            i += 2 if i + 1 < len(script) and script[i + 1] in (0x02, 0xFF) else 1
    return out


def actions(data: bytes) -> set[tuple[int, int]]:
    """Every native action the monster's script names, over all groups."""
    _, groups = parse(data)
    out: set[tuple[int, int]] = set()
    for group in groups:
        for script in group:
            out |= refs(script)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="a monster's rEnemyCmd (.emc / *_cmdtbl / em_cmd00)")
    ap.add_argument("--json", action="store_true", help="write the whole inventory as JSON")
    args = ap.parse_args(argv)
    with open(args.file, "rb") as f:
        data = f.read()
    version, groups = parse(data)
    acts = actions(data)
    if args.json:
        json.dump({"version": version, "groups": [len(g) for g in groups],
                   "actions": [list(a) for a in sorted(acts)]}, sys.stdout, indent=1)
        print()
        return 0
    print(f"EMC version 0x{version:08x} ({VERSIONS.get(version, 'unknown')}), "
          f"{len(groups)} groups, {sum(len(g) for g in groups)} scripts")
    print(f"{len(acts)} native actions:")
    print(" ".join(f"{c}/{n}" for c, n in sorted(acts)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
