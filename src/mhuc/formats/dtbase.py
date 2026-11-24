"""MHXX `rEnemyDtBase` (`enemy/dt_base/emNNN_SS_dtbase`, class id 0x59D9C3DA): the part of a monster's data that
MH4U keeps in its `.emd` (specs/emd.md, specs/dtbase.md).

The file is read by `rEnemyDtBase`'s loader (MHXX v1.4 code, 0x002b6f88): an 8-byte header, 13 count/flag bytes, a long
run of scalars, then blocks whose sizes come from those bytes; a block whose count is 0 is absent. `blocks()` lays a
file out without reading a value; block names say what MH4U file block the bytes equal (check E5).
"""
from __future__ import annotations

import struct

MAGIC, VERSION = b"DTB\0", 0x15022601
HEADER = 0x15
COUNTS, NCOUNTS = 0x08, 13

# (name, count-or-flag byte index, kind, unit size): the blocks the loader reads after the scalar run
_TAIL = [
    ("map-hit sphere records", 9, 0x34),        # .emd word 20
    ("block 0x84", 10, 0x34),                   # .emd word 21
    ("block 0x70", 7, 0x40),                    # .emd word 38
    ("block 0x74", 8, 0x0C),                    # .emd word 39
    ("block 0x88", 11, 4),                      # .emd word 22
    ("block 0x7c", 2, 0x1C),
    ("block 0x6c", 0, 2),                       # .emd word 13
    ("block 0xa8", 4, 0x1C),                    # .emd word 43
    ("block 0xac", 5, 0x20),                    # .emd word 44's first records
    ("block 0x8c", 3, 2),
    ("block 0xb0", 6, 2),
]


class DtBaseError(ValueError):
    pass


def header(d: bytes) -> tuple[bytes, int]:
    """The 13 count/flag bytes (object +0xB8..+0xC4) and the object's 0xD0 size: counts where a loader loop reads
    that many records, presence flags (0 = present) at indexes 7, 8, 10, 11 and 12."""
    if len(d) < HEADER or d[:4] != MAGIC:
        raise DtBaseError("not an MHXX dtbase (magic)")
    if struct.unpack_from("<I", d, 4)[0] != VERSION:
        raise DtBaseError(f"dtbase version {struct.unpack_from('<I', d, 4)[0]:#x}, not {VERSION:#x}")
    return d[COUNTS:COUNTS + NCOUNTS], 0xD0


def blocks(d: bytes) -> list[tuple[str, int, int]]:
    """(name, file offset, size) of every block the loader reads, in its order. Raises DtBaseError if the layout
    doesn't end exactly at the file's end."""
    c, _ = header(d)
    out: list[tuple[str, int, int]] = []
    pos = HEADER

    def take(name: str, n: int) -> None:
        nonlocal pos
        if pos + n > len(d):
            raise DtBaseError(f"dtbase ends inside {name} at {pos:#x}")
        if n:
            out.append((name, pos, n))
        pos += n

    take("scalar 0x60", 4)
    take("bytes 0x64", 4)
    take("scalar 0x68", 4)
    take("byte 0xb4", 1)
    take("block 0x94", 0x14)
    if c[12]:
        take("byte 0x90", 1)
    for name, i, unit in _TAIL:
        if i in (7, 8, 10, 11, 12):
            if c[i]:
                take(name, unit)
        elif c[i]:
            take(name, unit * c[i])
    if c[1]:
        for k in range(c[1]):
            if pos + 4 > len(d):
                raise DtBaseError("dtbase ends inside a list's count")
            n = struct.unpack_from("<I", d, pos)[0]
            take(f"list {k} count", 4)
            take(f"list {k} records", 0x2C * n)
            take(f"list {k} tail", 13)
    if pos != len(d):
        raise DtBaseError(f"layout ends at {pos:#x}, file at {len(d):#x}")
    return out


def block(d: bytes, name: str) -> bytes | None:
    for n, off, size in blocks(d):
        if n == name:
            return d[off:off + size]
    return None


def records(d: bytes, name: str, size: int) -> list[bytes]:
    """The block's records, `size` bytes each; DtBaseError if its length isn't a whole number of them."""
    b = block(d, name)
    if b is None:
        return []
    if len(b) % size:
        raise DtBaseError(f"{name}: {len(b)} bytes isn't a whole number of {size}-byte records")
    return [b[i:i + size] for i in range(0, len(b), size)]
