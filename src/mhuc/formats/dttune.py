"""MHXX `rEnemyDtTune` (`enemy/dt_tune/emNNN_SS_dttune`, class id 0x48E8AC29): a monster's HP, parts, hitzones and
tuning, as a stream (specs/dttune.md).

The file is a 0x38-byte header and then blocks read one after another: their sizes come from ten count bytes and their
presence from 35 flag bytes in the header (0 = present). The order below is MHXX's loader's (v1.4 code, 0x002b7f80),
blocks named by what MH4U's `.etd` holds in the same place (specs/emd.md). `blocks()` lays a file out without reading a
value; `layout()` adds the header.
"""
from __future__ import annotations

import struct

MAGIC, VERSION = b"DTT\0", 0x0133A06C
HEADER = 0x38
COUNTS, FLAGS, NFLAGS = 0x08, 0x12, 0x23

# (name, flag index or None, size): a fixed block, read when its flag (if any) is 0
_HEAD = [("base HP", None, 4), ("part table", None, 0x50)]


class DttuneError(ValueError):
    pass


def header(d: bytes) -> tuple[list[int], list[int]]:
    if len(d) < HEADER or d[:4] != MAGIC:
        raise DttuneError("not an MHXX dttune (magic)")
    if struct.unpack_from("<I", d, 4)[0] != VERSION:
        raise DttuneError(f"dttune version {struct.unpack_from('<I', d, 4)[0]:#x}, not {VERSION:#x}")
    return list(d[COUNTS:COUNTS + 10]), list(d[FLAGS:FLAGS + NFLAGS])


def blocks(d: bytes) -> list[tuple[str, int, int]]:
    """(name, file offset, size) of every block the loader reads, in its order. Raises DttuneError if the file is
    shorter than the layout or longer (the loader reads exactly the layout)."""
    c, f = header(d)
    out: list[tuple[str, int, int]] = []
    pos = HEADER

    def take(name: str, n: int) -> None:
        nonlocal pos
        if n:
            out.append((name, pos, n))
            pos += n

    def has(i: int) -> bool:
        return f[i] == 0

    take("base HP", 4)
    take("part table", 0x50)
    take("part break bytes", c[0])
    take("hitzone table", 0x50)
    if has(0):
        take("second hitzone-sized table", 0x50)
    take("sensor records", 32 * c[1])
    take("distance ranges", 16 * c[2])
    take("range offsets", 12 * c[3])
    if has(1):                              # two optional blocks under one flag
        if has(2):
            take("block 0x80 a", 0x10)
        if has(3):
            take("block 0x80 b", 0x1C)
    if has(4):                              # three groups of optional blocks
        if has(5):
            for i, n in ((6, 0x10), (7, 0x20), (8, 0x28)):
                if has(i):
                    take(f"block 0x84 a{i - 5}", n)
        if has(9):
            for i, n in ((10, 0x10), (11, 0x20), (12, 0x20)):
                if has(i):
                    take(f"block 0x84 b{i - 9}", n)
        if has(13):
            for i, n in ((14, 0x10), (15, 0x20)):
                if has(i):
                    take(f"block 0x84 c{i - 13}", n)
    if has(16):
        take("rage", 0x7C)
    if has(17):
        take("block 0x8c", 4)
    if c[4]:                                # stamina-like table: one u16, c[5] lists of u16, c[6] words
        take("block 0x90 head", 2)
        for k in range(c[5]):
            if pos + 4 > len(d):
                raise DttuneError("dttune ends inside the 0x90 lists")
            n = struct.unpack_from("<I", d, pos)[0]
            take(f"block 0x90 list {k} count", 4)
            take(f"block 0x90 list {k} key", 2)
            take(f"block 0x90 list {k}", 2 * n)
        take("block 0x90 words", 4 * c[6])
    if has(18):
        take("ailment 0x94", 0x10)
    for i in range(19, 26):
        if has(i):
            take(f"ailment {0x98 + 4 * (i - 19):#x}", 0x0C)
    if has(26):
        take("block 0xb4", 0x0E)
    if has(27):
        for i in range(28, 32):
            if has(i):
                take(f"block 0xb8 {i - 28}", 6)
    take("part table 2", 24 * c[7])
    if has(32):
        take("block 0xc8", 0x90)
    if has(33):
        take("block 0xcc", 0x0C)
    take("focus records 1", 36 * c[8])
    take("focus records 2", 36 * c[9])
    if has(34):
        take("block 0xd8", 0x80)
    for k in range(5):
        take(f"scalar {k}", 4)
    if pos != len(d):
        raise DttuneError(f"layout ends at {pos:#x}, file at {len(d):#x}")
    return out


def block(d: bytes, name: str) -> bytes | None:
    for n, off, size in blocks(d):
        if n == name:
            return d[off:off + size]
    return None
