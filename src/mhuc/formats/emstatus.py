"""MH3U `rEnemyStatus` (`enemy/emNNN/em_status00`, class id 0x4DEE8265): a monster's HP, parts, hitzones and tuning
(specs/emstatus.md).

The game loads the whole file and walks it with a cursor (MH3U USA code, 0x0029c744). Every block starts on a
16-byte boundary. Optional blocks are announced by a signed presence byte (non-zero = present), which takes a
16-byte slot of its own; a few blocks are sized by a count read inline. `blocks()` reproduces the walk without
reading a value other than those flags and counts; block names follow what MH4U's `.etd` holds in the same place
(specs/emd.md).
"""
from __future__ import annotations

import struct

MAGIC, VERSION = b"EMS\0", 0x20110824
ALIGN = 16


class EmStatusError(ValueError):
    pass


def blocks(d: bytes) -> list[tuple[str, int, int]]:
    """(name, file offset, size) of every block the walk passes, in its order. Raises EmStatusError if the walk leaves
    the file or doesn't end at its end."""
    if len(d) < 0x10 or d[:4] != MAGIC:
        raise EmStatusError("not an MH3U em_status (magic)")
    if struct.unpack_from("<I", d, 4)[0] != VERSION:
        raise EmStatusError(f"em_status version {struct.unpack_from('<I', d, 4)[0]:#x}, not {VERSION:#x}")
    out: list[tuple[str, int, int]] = []
    pos = 0x10
    end = len(d)

    def align() -> None:
        nonlocal pos
        pos = (pos + ALIGN - 1) // ALIGN * ALIGN

    def take(name: str, n: int) -> None:
        nonlocal pos
        if pos + n > end:
            raise EmStatusError(f"{name}: {n} bytes at {pos:#x} pass the end ({end:#x})")
        if n:
            out.append((name, pos, n))
        pos += n
        align()

    def flag() -> bool:
        nonlocal pos
        if pos >= end:
            raise EmStatusError(f"presence byte at {pos:#x} past the end")
        v = struct.unpack_from("<b", d, pos)[0]
        pos += 1
        align()
        return v != 0

    def inline(fmt: str) -> int:
        nonlocal pos
        size = struct.calcsize(fmt)
        if pos + size > end:
            raise EmStatusError(f"count at {pos:#x} past the end")
        v = struct.unpack_from("<" + fmt, d, pos)[0]
        pos += size
        return v

    take("header", 0x24)                    # base HP first (u32)
    take("block 0xf8", 0x18)
    take("block 0xfc", 0x18)
    if flag():
        take("part table", 0x10)            # 8 x u16 part HP
    if flag():
        take("block 0x6c", 0x10)
    if flag():
        take("block 0x70", 3)
    if flag():
        take("block 0x74", 0x30)
    take("hitzone table", 0x50)
    if flag():
        take("second hitzone-sized table", 0x50)
    n = inline("i")
    align()
    if n > 0:
        take("block 0x80", 24 * n)
    if flag():
        take("block 0x84", 0x18)
    take("block 0x88", 0x20)
    take("block 0x100", 0x10)
    if flag():
        take("block 0x104", 0x1C)
    if flag():
        take("block 0x114", 0x10)
        take("block 0x118", 0x1C)
        take("block 0x11c", 0x1C)
    if flag():
        take("block 0x120", 0x10)
        take("block 0x124", 0x1C)
        take("block 0x128", 8)
    if flag():
        take("block 0x12c", 0x10)
        take("block 0x130", 0x1C)
    if flag():
        take("block 0x94", 0x38)
    if flag():
        take("block 0x98", 0x34)
    if flag():
        take("block 0x9c", 4)
    if flag():                              # two s16, the second a count of 10-byte records, then a count of words
        start = pos
        inline("h")
        k = inline("h")
        out.append(("block 0x138 head", start, 4))
        align()
        if k > 0:
            take("block 0x13c", 10 * k)
        start = pos
        k = inline("h")
        out.append(("block 0x140 count", start, 2))
        align()
        if k > 0:
            take("block 0x140", 4 * k)
    if flag():
        take("ailment 0xa4", 0x10)
    for field in (0xA8, 0xAC, 0xB0, 0xB4):
        if flag():
            take(f"ailment {field:#x}", 0x0C)
    if flag():
        take("ailment 0xb8", 8)
    if flag():
        start = pos
        take("block 0xbc", 0x38)
        for i in range(8):                  # per part: a count byte at +0xe + i, then that many 32-byte records
            k = d[start + 0x0E + i]
            if k:
                take(f"block 0xbc part {i}", 32 * k)
    if flag():
        for field in (0x144, 0x148, 0x14C):  # each takes its 6 bytes whether its flag is set or not
            flag()
            take(f"block {field:#x}", 6)
    if pos != end:
        raise EmStatusError(f"walk ends at {pos:#x}, file at {end:#x}")
    return out


def block(d: bytes, name: str) -> bytes | None:
    for n, off, size in blocks(d):
        if n == name:
            return d[off:off + size]
    return None


PART_COUNT = 8
BREAK_RECORD = 6


def part_break_records(d: bytes) -> list[bytes] | None:
    """The parts' break records (walk block "block 0x74"), 8 records of 6 bytes, or None when absent.

    The code returns one shared default record for every part when the block is absent (0x84c56c); the records
    themselves are read by the part break test 0x835ebc and the update 0x837a60 (specs/emstatus.md).
    """
    b = block(d, "block 0x74")
    if b is None:
        return None
    return [b[BREAK_RECORD * i:BREAK_RECORD * (i + 1)] for i in range(PART_COUNT)]


def second_part_hp(d: bytes) -> list[int] | None:
    """The parts' second-level HP (walk block "block 0x6c"), 8 s16, or None when absent. Copied into the part's
    secondary HP slot by 0x8525a8 (specs/emstatus.md)."""
    b = block(d, "block 0x6c")
    if b is None:
        return None
    return list(struct.unpack("<8h", b))
