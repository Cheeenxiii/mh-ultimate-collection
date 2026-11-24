"""MHXX `rEnemyDtBaseParts` (`enemy/dt_base/emNNN_SS_dtbparts`, class id 0x1BBC291E): a monster's break and joint
records (specs/dtbparts.md).

The file is read by `rEnemyDtBaseParts`'s loader (MHXX v1.4 code, 0x0058e424): an 8-byte header, 16 count bytes, a run
of scalars, then ten blocks whose sizes come from the counts; a count of 0 means the block is absent. Two blocks match
MH4U `.emd` blocks on the monsters both games have (check E5): +0x64 is MH4U `.emd` word 35's leading records and +0x60
is the break records of MH4U's part break table. `blocks()` lays a file out without reading a value.
"""
from __future__ import annotations

import struct

MAGIC, VERSION = b"DTP\0", 0x01339ECB
HEADER = 0x4D
COUNTS, NCOUNTS = 0x08, 16

# (name, count index, bytes per record): the loader's blocks, in its order
_TAIL = [
    ("break records", 0, 4),            # MH4U .emd word 32/33
    ("joint records", 1, 13),           # MH4U .emd word 35's leading records
    ("part break HP records", 2, 12),
    ("block 0x6c", 3, 16),
    ("block 0x70", 4, 15),
    ("block 0x74", 5, 24),
    ("block 0x78", 6, 4),
    ("visibility state records", 7, 5),
    ("block 0x80", 8, 4),
    ("block 0x84", 16, 4),
]


class DtbPartsError(ValueError):
    pass


def header(d: bytes) -> bytes:
    """The 16 count bytes (object +0x88..+0x97): a block is present when its byte isn't 0."""
    if len(d) < HEADER or d[:4] != MAGIC:
        raise DtbPartsError("not an MHXX dtbparts (magic)")
    if struct.unpack_from("<I", d, 4)[0] != VERSION:
        raise DtbPartsError(f"dtbparts version {struct.unpack_from('<I', d, 4)[0]:#x}, not {VERSION:#x}")
    return d[COUNTS:COUNTS + NCOUNTS]


def blocks(d: bytes) -> list[tuple[str, int, int]]:
    """(name, file offset, size) of every block the loader reads, in its order. Raises DtbPartsError if the layout
    doesn't end exactly at the file's end."""
    c = list(header(d)) + [d[0x4C]]
    out: list[tuple[str, int, int]] = []
    pos = HEADER

    def take(name: str, n: int) -> None:
        nonlocal pos
        if pos + n > len(d):
            raise DtbPartsError(f"dtbparts ends inside {name} at {pos:#x}")
        if n:
            out.append((name, pos, n))
        pos += n

    for name, i, unit in _TAIL:
        if c[i]:
            take(name, unit * c[i])
    if pos != len(d):
        raise DtbPartsError(f"layout ends at {pos:#x}, file at {len(d):#x}")
    return out


def block(d: bytes, name: str) -> bytes | None:
    for n, off, size in blocks(d):
        if n == name:
            return d[off:off + size]
    return None


def records(d: bytes, name: str, size: int) -> list[bytes]:
    """The block's records, `size` bytes each; DtbPartsError if its length isn't a whole number of them."""
    b = block(d, name)
    if b is None:
        return []
    if len(b) % size:
        raise DtbPartsError(f"{name}: {len(b)} bytes isn't a whole number of {size}-byte records")
    return [b[i:i + size] for i in range(0, len(b), size)]
