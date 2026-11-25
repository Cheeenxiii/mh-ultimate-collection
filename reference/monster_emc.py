#!/usr/bin/env python3
"""The native actions a monster's AI script starts, and the script cut by its instruction table.

A monster's AI is its EMC script (rEnemyCmd, specs/emc.md). Its bytecode starts the monster
class's native actions as `00 cat num`, runs other action scripts as `14 nn`, and picks a
weighted branch with `02 ..`; the rest opens a condition block. This reads the `00 cat num`
pairs out of a monster's script, so a port can tell an action the AI picks in a normal fight
from one nothing in the AI reaches.

The file layout is verified in all three games (check A1), but the bytecode reading below is
MHGU Definitive Edition's heuristic (`tools/emc.py`, GPL-3.0-or-later), which infers the
instruction lengths; MH4U and MHXX share version 0x20120804, MH3U's is older (0x20110601).
Treat the result as the set of actions a script names, not as a complete decode: it can miss
a call and, on a newer script, name a pair a random branch guard happened to spell.

`--lens` cuts every script with the game's own instruction-length table, so a script's
instructions can be read rather than guessed (`--check` prints the counts only). The table is
a byte per opcode in the game's code: a value below 0x80 is the opcode's argument count; 0x80
and up opens a block whose next byte is a subcode (0x00 opens, 0x01 is a case, 0x02 the else,
0xff the end). specs/emc.md lays the rules out and lists each game's table. CODE is a flat
decompressed code.bin (first byte address 0x00100000, so OFFSET is the address minus that) or
an ELF read at the virtual address; every script ends with 0xff.

    monster_emc.py FILE            counts and the native actions, one per line
    monster_emc.py FILE --json     {"version": ..., "groups": [...], "actions": [[cat, num], ...]}
    monster_emc.py FILE --lens CODE OFFSET COUNT --check   the script layout and the table's cuts
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


def tokens(script: bytes, lens: bytes) -> tuple[list[bytes], bytes]:
    """(instructions, rest): the script cut by the length table, and what is left when it stops.

    The rest is empty when the script ends with the 0xff end marker. A script whose opcode is at
    or past the table before its end does not cut cleanly; `rest` is where the cut stopped.
    """
    out, i = [], 0
    while i < len(script):
        op = script[i]
        if op >= len(lens):
            if i == len(script) - 1 and op == 0xFF:
                return out, b""
            return out, script[i:]
        v = lens[op]
        if v < 0x80:
            n = 1 + v
        else:
            if i + 1 >= len(script):
                return out, script[i:]
            sub = script[i + 1]
            n = 2 + (v & 0x0F) if sub == 0 else 2 + (v >> 4) - 7 if sub == 1 else 2
        if i + n > len(script):
            return out, script[i:]
        out.append(script[i:i + n])
        i += n
    return out, b""


def actions(data: bytes) -> set[tuple[int, int]]:
    """Every native action the monster's script names, over all groups."""
    _, groups = parse(data)
    out: set[tuple[int, int]] = set()
    for group in groups:
        for script in group:
            out |= refs(script)
    return out


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


def read_lens(code: str, offset: int, count: int) -> bytes:
    """The instruction-length table at an offset in a flat image, or at a virtual address in an ELF.

    A flat image is a decompressed 3DS code.bin, whose first byte is address 0x00100000, so the
    offset is the address minus 0x00100000. An ELF (the recompiler's or the fork's
    codebin2elf.py's output) is read at the virtual address, mapped through its PT_LOAD rows.
    """
    if offset < 0 or count <= 0:
        raise ValueError("--lens needs an offset of 0 or more and a count above 0")
    with open(code, "rb") as f:
        data = f.read()
    at = _elf_offset(data, offset) if data[:4] == b"\x7fELF" else offset
    lens = data[at:at + count]
    if len(lens) != count:
        raise ValueError("--lens runs past the end of the code image")
    return lens


def _elf_offset(data: bytes, vaddr: int) -> int:
    """A virtual address's file offset, through an ELF's program headers."""
    if len(data) < 52 or data[4] != 1 or data[5] != 1:
        raise ValueError("--lens: the ELF isn't a 32-bit little-endian one")
    phoff, = struct.unpack_from("<I", data, 28)
    phentsize, phnum = struct.unpack_from("<HH", data, 42)
    for i in range(phnum):
        row = phoff + i * phentsize
        if struct.unpack_from("<I", data, row)[0] != 1:      # PT_LOAD
            continue
        off, va, _pa, filesz = struct.unpack_from("<IIII", data, row + 4)
        if va <= vaddr < va + filesz:
            return off + vaddr - va
    raise ValueError("--lens: the address isn't in an ELF's loaded segments")


def check(data: bytes, lens: bytes) -> str:
    """Counts only: the file's cuts and the opcodes its scripts use."""
    version, groups = parse(data)
    scripts = [s for group in groups for s in group]
    clean, rest, ops = 0, 0, set()
    for script in scripts:
        cut, left = tokens(script, lens)
        clean += not left
        rest += bool(left)
        ops |= {t[0] for t in cut}
    total = sum(len(group) for group in groups)
    return (f"EMC version 0x{version:08x} ({VERSIONS.get(version, 'unknown')}), "
            f"{len(groups)} groups, {total} scripts\n"
            f"table: {len(lens)} ops; clean {clean}, not clean {rest}; "
            f"{len(ops)} op ids used, highest 0x{max(ops) if ops else 0:02x}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="a monster's rEnemyCmd (.emc / *_cmdtbl / em_cmd00)")
    ap.add_argument("--json", action="store_true", help="write the whole inventory as JSON")
    ap.add_argument("--lens", nargs=3, metavar=("CODE", "OFFSET", "COUNT"),
                    help="the code image holding the instruction-length table, its file offset "
                         "and its op count; gives each script's cuts")
    ap.add_argument("--check", action="store_true",
                    help="with --lens: print the cuts' counts only, not the actions")
    args = ap.parse_args(argv)
    with open(args.file, "rb") as f:
        data = f.read()
    if args.check:
        if not args.lens:
            ap.error("--check needs --lens CODE OFFSET COUNT")
        code, offset, count = args.lens
        lens = read_lens(code, int(offset, 0), int(count, 0))
        print(check(data, lens))
        return 0
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
