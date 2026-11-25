"""MT Framework motion lists (`.lmt`, rMotionList), as specs/lmt.md lays them out (from MHGU Definitive Edition's
`tools/lmt.py`, read off MH4U files: version 67; and from RevilLib's version layouts, which put 66 and 67 in the
same class layouts, so MH3U's files read with the same code). `read` returns the structure; `check` gives check
L1's counts.
"""
from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass, field

ANIM, TRACK, BOUNDS, GROUP, GROUPS = 0x40, 0x24, 0x20, 0x48, 4
VERSIONS = (66, 67)      # 66 is MH3U's, 67 MH4U's, MHXX's and MHGU's; one layout covers both


class LmtError(ValueError):
    pass


@dataclass
class Track:
    buffer_type: int
    usage: int
    joint_type: int
    bone: int
    weight: float
    buffer_size: int
    buffer: int
    bounds: int


@dataclass
class Animation:
    offset: int
    frames: int
    loop_frame: int
    tracks: list[Track] = field(default_factory=list)
    events: int = 0          # event block offset (0 none)
    flags: int = 0           # bit 0x800000 is set exactly when `events` is


def _in(d: bytes, at: int, size: int) -> None:
    if not 0 < at or at + size > len(d):
        raise LmtError(f"block {at:#x}+{size:#x} outside the file")


def read(d: bytes) -> tuple[int, list[Animation | None]]:
    """(version, animations); a slot whose offset is 0 is None."""
    if d[:4] != b"LMT\0":
        raise LmtError("not an LMT")
    version, count = struct.unpack_from("<HH", d, 4)
    if version not in VERSIONS:
        raise LmtError(f"LMT version {version}: only {' and '.join(map(str, VERSIONS))} are laid out")
    out: list[Animation | None] = []
    for o in struct.unpack_from(f"<{count}I", d, 8):
        if not o:
            out.append(None)
            continue
        _in(d, o, ANIM)
        tr, tc, frames, loop = struct.unpack_from("<IIii", d, o)
        a = Animation(o, frames, loop, events=struct.unpack_from("<I", d, o + 0x34)[0],
                      flags=struct.unpack_from("<I", d, o + 0x30)[0])
        if tc:
            _in(d, tr, TRACK * tc)
        for k in range(tc):
            t = tr + TRACK * k
            bt, usage, jt, bone = d[t:t + 4]
            weight, size, buf = struct.unpack_from("<fII", d, t + 4)
            bnd = struct.unpack_from("<I", d, t + 0x20)[0]
            if buf:
                _in(d, buf, size)
            if bnd:
                _in(d, bnd, BOUNDS)
            a.tracks.append(Track(bt, usage, jt, bone, weight, size, buf, bnd))
        if a.events:
            _in(d, a.events, GROUP * GROUPS)
            for g in range(GROUPS):
                cnt, ptr = struct.unpack_from("<II", d, a.events + GROUP * g + 0x40)
                if ptr and cnt:
                    _in(d, ptr, 8 * cnt)
        out.append(a)
    return version, out


def check(d: bytes) -> Counter:
    """Check L1 (specs/lmt.md): version, readability, counts of animations, tracks and buffer types."""
    c = Counter()
    if d[:4] != b"LMT\0":
        c["L1 other magic"] += 1
        return c
    c[f"L1 version {struct.unpack_from('<H', d, 4)[0]}"] += 1
    try:
        _, anims = read(d)
    except (LmtError, struct.error) as e:
        c["L1 not readable" if "version" not in str(e) else "L1 version not laid out"] += 1
        return c
    c["L1 readable"] += 1
    for a in anims:
        if a is None:
            c["L1 empty slots"] += 1
            continue
        c["L1 animations"] += 1
        c["L1 tracks"] += len(a.tracks)
        c["L1 with events"] += bool(a.events)
        for t in a.tracks:
            c[f"L1 buffer type {t.buffer_type}"] += 1
    return c
