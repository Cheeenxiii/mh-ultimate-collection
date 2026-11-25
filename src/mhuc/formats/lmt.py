"""MT Framework motion lists (`.lmt`, rMotionList), as specs/lmt.md lays them out (from MHGU Definitive Edition's
`tools/lmt.py`, read off MH4U files: version 67; and from RevilLib's version layouts, which put 66 and 67 in the
same class layouts, so MH3U's files read with the same code). `read` returns the structure, `decode_keys` its
keyframes and `bounds` a track's bounds block; `check` gives check L1's counts.
"""
from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass, field

ANIM, TRACK, BOUNDS, GROUP, GROUPS = 0x40, 0x24, 0x20, 0x48, 4
VERSIONS = (66, 67)      # 66 is MH3U's, 67 MH4U's, MHXX's and MHGU's; the layout is the same, types 11-13 differ

# Keyframe buffer types, from RevilLib's src/mtf_lmt/codecs.hpp and the per-version registry in bone_track.cpp
# (the row for LMT 56 and up). Types 8, 9 and 10 are unused there, and 14 and 15 are named but don't occur in
# the three games, so they aren't decoded here. The value is a key's size in bytes.
KEY_STRIDES = {1: 12, 2: 12, 3: 16, 4: 8, 5: 4, 6: 8, 7: 4, 11: 4, 12: 4, 13: 4}
KEY_NAMES = {
    1: "SingleVector3", 2: "StepRotationQuat3", 3: "LinearVector3", 4: "BiLinearVector3_16bit",
    5: "BiLinearVector3_8bit", 6: "LinearRotationQuat4_14bit", 7: "BiLinearRotationQuat4_7bit",
    11: "BiLinearRotationQuatXW_14bit", 12: "BiLinearRotationQuatYW_14bit",
    13: "BiLinearRotationQuatZW_14bit",
}


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


@dataclass(frozen=True)
class Key:
    """One keyframe: its frame and the four components its buffer type decodes to (x, y, z, w).

    For the compressed position types the components are the normalized ones the buffer stores; the track's
    bounds block, when it has one, turns them into the track's values (`bounds`)."""
    frame: int
    value: tuple[float, float, float, float]


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


def _signed14(c: int) -> float:
    """A 14-bit field whose upper half is the negative half (a value above 8191.5 means the raw minus 16383); the
    scale is 0x3FFF / 4 = 4095.75, so a component spans [-2, 2] (RevilLib's LinearRotationQuat4_14bit)."""
    return (c - 0x3FFF if c > 8191.5 else c) / 4095.75


def _key_components(bt: int, d: bytes, at: int,
                    version: int) -> tuple[tuple[float, float, float, float], int]:
    """(components, frames to the next key) of the key at `at`, from RevilLib's codecs.

    A quaternion is stored x, y, z, w in the order the code names the fields, not the order of the packed bits.
    """
    if bt == 1:                                     # SingleVector3: three floats
        x, y, z = struct.unpack_from("<3f", d, at)
        return (x, y, z, 1.0), 1
    if bt == 2:                                     # StepRotationQuat3: x, y, z; w = sqrt(1 - |xyz|^2)
        x, y, z = struct.unpack_from("<3f", d, at)
        rest = 1.0 - (x * x + y * y + z * z)
        return (x, y, z, math.sqrt(rest) if rest > 1e-4 else 0.0), 1
    if bt == 3:                                     # LinearVector3: three floats and the frame delta
        x, y, z, delta = struct.unpack_from("<3fI", d, at)
        return (x, y, z, 1.0), delta
    if bt == 4:                                     # BiLinearVector3_16bit: three u16, then the frame delta
        x, y, z, delta = struct.unpack_from("<3HH", d, at)
        return (x / 0xFFFF, y / 0xFFFF, z / 0xFFFF, 1.0), delta
    if bt == 5:                                     # BiLinearVector3_8bit: three u8, then the frame delta
        x, y, z, delta = struct.unpack_from("<3BB", d, at)
        return (x / 0xFF, y / 0xFF, z / 0xFF, 1.0), delta
    if bt == 6:                                     # LinearRotationQuat4_14bit
        data, = struct.unpack_from("<Q", d, at)
        w, z, y, x = ((data >> shift) & 0x3FFF for shift in (0, 14, 28, 42))
        return (_signed14(x), _signed14(y), _signed14(z), _signed14(w)), data >> 56
    if bt == 7:                                     # BiLinearRotationQuat4_7bit
        data, = struct.unpack_from("<I", d, at)
        x, y, z, w = ((data >> shift) & 0x7F for shift in (21, 14, 7, 0))
        return (x / 0x7F, y / 0x7F, z / 0x7F, w / 0x7F), data >> 28
    if bt in (11, 12, 13):                          # BiLinearRotationQuat{X,Y,Z}W_14bit: two components
        data, = struct.unpack_from("<I", d, at)
        low, w = data & 0x3FFF, (data >> 14) & 0x3FFF
        # Version 67 stores the two components unsigned, the track's bounds block carrying the sign and scale;
        # version 66 (MH3U) stores them signed-magnitude, as type 6 does, and no type 11 to 13 track has bounds
        if version == 66:
            low, w = _signed14(low), _signed14(w)
        else:
            low, w = low / 0x3FFF, w / 0x3FFF
        component = {11: (low, 0.0, 0.0, w), 12: (0.0, low, 0.0, w), 13: (0.0, 0.0, low, w)}[bt]
        return component, data >> 28
    raise LmtError(f"keyframe buffer type {bt} isn't laid out")


def decode_keys(d: bytes, track: Track, version: int, frames: int = 0) -> list[Key]:
    """The track's keyframes, in order, as `Key(frame, components)`; `version` is the LMT file's.

    `frames`, when given, is the animation's frame count, and a key at or past it is an error. The components
    are the buffer's own values: the normalized ones for the compact position types, and for types 11 to 13
    unsigned (version 67, the bounds block carrying the sign) or signed (version 66). They are the values before
    the track's bounds block; `bounds` gives the block's scale and offset. Types 1 and 2 carry no frame field,
    so their keys are one frame apart.
    """
    size, bt = track.buffer_size, track.buffer_type
    if not size:
        return []
    stride = KEY_STRIDES.get(bt)
    if stride is None:
        raise LmtError(f"keyframe buffer type {bt} isn't laid out")
    if size % stride:
        raise LmtError(f"buffer size {size:#x} isn't a whole number of {KEY_NAMES[bt]} keys ({stride} bytes)")
    if track.buffer <= 0 or track.buffer + size > len(d):
        raise LmtError(f"keyframe buffer {track.buffer:#x}+{size:#x} outside the file")
    keys: list[Key] = []
    frame = 0
    for i in range(size // stride):
        components, delta = _key_components(bt, d, track.buffer + i * stride, version)
        if frames and frame >= frames:
            raise LmtError(f"key {i} at frame {frame} is past the animation's {frames}")
        keys.append(Key(frame, components))
        frame += delta
    return keys


def bounds(d: bytes, track: Track) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    """The track's bounds block as (scale, offset), the first and second f32 x 4, or None without one.

    RevilLib applies it to a key as offset + scale x component (its `minMax.max + minMax.min * out`), so the
    first vector scales and the second offsets; the pair isn't a min and a max.
    """
    if not track.bounds:
        return None
    return (struct.unpack_from("<4f", d, track.bounds),
            struct.unpack_from("<4f", d, track.bounds + 0x10))


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
