"""MT Framework camera lists (`.lcm`, rCameraList), as specs/camera.md lays them out.

A camera list is a table of cameras by id: the cut-in, mount and kill cameras a monster's
actions post by number. Each camera is a record with a frame count and up to four animation
tracks; a track is the same 0x24-byte structure an LMT motion list uses, pointing at a key
buffer and at a bounds block.

Versions: MH4U writes 4 (record 0x9c), MHXX writes 5 (the same record behind a 16-byte zero
prefix, 0xac). MH3U registers the class but ships no file of it (specs/camera.md#versions).

Source: PredatorCZ's RevilLib (GPL-3.0) for the track and keyframe layouts
(`src/mtf_lmt/bone_track.cpp`, `codecs.hpp`, `codecs.cpp`), read through specs/lmt.md; MH4U's
own loader `0x0023b808` for the header, the table and which fields are file offsets.
"""
from __future__ import annotations

import math
import struct
from collections import Counter
from dataclasses import dataclass

MAGIC = b"LCM\0"
VERSION_MH4U = 4
VERSION_MHXX = 5
RECORD_SIZE = {VERSION_MH4U: 0x9C, VERSION_MHXX: 0xAC}
PREFIX = {VERSION_MH4U: 0, VERSION_MHXX: 16}     # zero bytes in front of each MHXX record
TABLE = 8                                          # the count table's offset
FIRST_RECORD = TABLE + 4 * 256                     # 0x408
TRACK_OFFSETS = (0x1C, 0x40, 0x64)                 # three tracks, MH4U's record coordinates
TRACK_SIZE = 0x24
BOUNDS_SIZE = 0x20
FOURTH = 0x88                                      # the fourth, shorter block
FOURTH_SIZE = 0x14
# The words MH4U's loader relocates (0x0023b8a4 to 0x0023b9a4): buffer offsets at +0x0c and
# bounds offsets at +0x20 of each track, and the fourth block's +0x10.
TRACK_KEY = 0x0C
TRACK_BOUNDS = 0x20
FOURTH_KEY = 0x10
# The loader's relocation list, in MH4U record coordinates, including the fourth block's own
# offset at +0x98 (track 3 would start at +0x88, its +0x10).
OFFSET_FIELDS = (TRACK_OFFSETS[0] + TRACK_KEY, TRACK_OFFSETS[0] + TRACK_BOUNDS,
                 TRACK_OFFSETS[1] + TRACK_KEY, TRACK_OFFSETS[1] + TRACK_BOUNDS,
                 TRACK_OFFSETS[2] + TRACK_KEY, TRACK_OFFSETS[2] + TRACK_BOUNDS,
                 FOURTH + FOURTH_KEY)

# LMT v2 keyframe buffer types that occur in camera tracks (RevilLib's TrackV2BufferTypes),
# with the name, the key's size in bytes, and whether the key stores its own frame gap.
# Types 8 to 10 and the 11 to 13 pair encodings are the rest of the LMT registry; types 11 to 13
# occur in MH4U's non-monster camera lists, 8 to 10 in none (check C1).
CODECS: dict[int, tuple[str, int, bool]] = {
    1: ("SingleVector3", 12, False),
    2: ("StepRotationQuat3", 12, False),
    3: ("LinearVector3", 16, True),
    4: ("BiLinearVector3_16bit", 8, True),
    5: ("BiLinearVector3_8bit", 4, True),
    6: ("LinearRotationQuat4_14bit", 8, True),
    7: ("BiLinearRotationQuat4_7bit", 4, True),
    11: ("BiLinearRotationQuatXW_14bit", 4, True),
    12: ("BiLinearRotationQuatYW_14bit", 4, True),
    13: ("BiLinearRotationQuatZW_14bit", 4, True),
    14: ("BiLinearRotationQuat4_11bit", 6, True),
    15: ("BiLinearRotationQuat4_9bit", 5, True),
}
ROTATIONS = frozenset({2, 6, 7, 11, 12, 13, 14, 15})


class CameraError(ValueError):
    pass


@dataclass(frozen=True)
class Track:
    buffer_type: int
    usage: int
    joint_type: int
    bone: int
    weight: float
    size: int
    offset: int
    reference: tuple[float, float, float, float]
    bounds: int


@dataclass(frozen=True)
class Fourth:
    count: int
    size: int
    first: float
    second: float
    offset: int


@dataclass(frozen=True)
class Record:
    frames: int
    flag: int
    aspect: float
    tracks: tuple[Track, Track, Track]
    fourth: Fourth
    raw: bytes          # the 0x9c-byte record, MH4U's coordinates (MHXX's 16-byte prefix stripped)


@dataclass(frozen=True)
class CameraList:
    version: int
    count: int
    order: tuple[int, ...]              # camera ids in file order
    records: dict[int, Record]
    data: bytes                         # the data area after the records, unchanged
    data_start: int                     # where that data area began in the file read

    @property
    def record_size(self) -> int:
        return RECORD_SIZE[self.version]

    @property
    def prefix(self) -> int:
        return PREFIX[self.version]


def _u32(data: bytes, at: int) -> int:
    return struct.unpack_from("<I", data, at)[0]


def _in(data: bytes, at: int, size: int, what: str) -> None:
    if at < 0 or at + size > len(data):
        raise CameraError(f"{what} runs past the end of the file")


def _track(raw: bytes, base: int, data: bytes) -> Track:
    buffer_type, usage, joint, bone = raw[base], raw[base + 1], raw[base + 2], raw[base + 3]
    weight = struct.unpack_from("<f", raw, base + 4)[0]
    size, offset = struct.unpack_from("<II", raw, base + 8)
    reference = struct.unpack_from("<4f", raw, base + 0x10)
    bounds = _u32(raw, base + TRACK_BOUNDS)
    _in(data, offset, size, "a track's key buffer")
    if bounds:
        _in(data, bounds, BOUNDS_SIZE, "a track's bounds block")
    return Track(buffer_type, usage, joint, bone, weight, size, offset, reference, bounds)


def read(data: bytes) -> CameraList:
    """Parse a camera list. Raises CameraError on anything the loader would refuse or a reader can't split."""
    if len(data) < TABLE or data[:4] != MAGIC:
        raise CameraError("not a camera list (magic)")
    version, count = struct.unpack_from("<HH", data, 4)
    if version not in RECORD_SIZE:
        raise CameraError(f"camera list version {version} isn't one mhuc knows "
                          f"({VERSION_MH4U} MH4U, {VERSION_MHXX} MHXX)")
    _in(data, TABLE, 4 * count, "the camera table")
    table = struct.unpack_from(f"<{count}I", data, TABLE)
    ids = [i for i in range(count) if table[i]]
    order = sorted(ids, key=lambda i: table[i])
    size, prefix = RECORD_SIZE[version], PREFIX[version]
    first = FIRST_RECORD
    data_start = first + size * len(order)
    if order:
        _in(data, first, size * len(order), "the camera records")
    for k, i in enumerate(order):
        if table[i] != first + size * k:
            raise CameraError(f"camera {i}'s record isn't where the contiguous layout puts it")
    records: dict[int, Record] = {}
    for i in order:
        at = table[i]
        if prefix and data[at:at + prefix] != bytes(prefix):
            raise CameraError(f"camera {i}'s {prefix}-byte prefix isn't zero")
        raw = data[at + prefix:at + size]
        tracks = tuple(_track(raw, base, data) for base in TRACK_OFFSETS)
        fourth = Fourth(_u32(raw, FOURTH), _u32(raw, FOURTH + 4),
                        struct.unpack_from("<f", raw, FOURTH + 8)[0],
                        struct.unpack_from("<f", raw, FOURTH + 0x0C)[0],
                        _u32(raw, FOURTH + FOURTH_KEY))
        if fourth.offset:
            _in(data, fourth.offset, fourth.size, "the fourth block's key data")
        records[i] = Record(_u32(raw, 0x10), _u32(raw, 0x14),
                            struct.unpack_from("<f", raw, 0x18)[0], tracks, fourth, raw)
    return CameraList(version, count, tuple(order), records, data[data_start:], data_start)


def convert(data: bytes, version: int) -> bytes:
    """Re-lay a camera list as `version`: every record keeps its bytes and the data area is
    copied, with the fields the loader relocates moved by the change in where the data starts."""
    if version not in RECORD_SIZE:
        raise CameraError(f"target version {version} isn't {VERSION_MH4U} or {VERSION_MHXX}")
    camera = read(data)
    if camera.version == version:
        return data
    ids = camera.order
    n = len(ids)
    shift = (PREFIX[version] - camera.prefix) * n
    size, prefix = RECORD_SIZE[version], PREFIX[version]
    out = bytearray(MAGIC + struct.pack("<HH", version, camera.count) + bytes(4 * camera.count))
    data_start = FIRST_RECORD + size * n
    for i in ids:
        raw = bytearray(camera.records[i].raw)
        for field in OFFSET_FIELDS:
            at = _u32(raw, field)
            if at:
                struct.pack_into("<I", raw, field, at + shift)
        struct.pack_into("<I", out, TABLE + 4 * i, len(out))
        out += bytes(prefix) + raw
    out += camera.data
    if len(out) != data_start + len(camera.data):
        raise CameraError("the re-laid camera list isn't the size its layout gives")
    return bytes(out)


def from_mhxx(data: bytes) -> bytes:
    """An MHXX camera list as MH4U reads it (version 5 -> 4)."""
    camera = read(data)
    if camera.version != VERSION_MHXX:
        raise CameraError(f"not an MHXX camera list (version {camera.version}, expected {VERSION_MHXX})")
    return convert(data, VERSION_MH4U)


def to_mhxx(data: bytes) -> bytes:
    """An MH4U camera list as MHXX holds it (version 4 -> 5), the inverse of `from_mhxx`."""
    camera = read(data)
    if camera.version != VERSION_MH4U:
        raise CameraError(f"not an MH4U camera list (version {camera.version}, expected {VERSION_MH4U})")
    return convert(data, VERSION_MHXX)


def _signed(value: int, bits: int) -> float:
    mask = (1 << bits) - 1
    return float(value - (mask + 1) if value > mask / 2 else value)


def key_value(codec: int, data: bytes, at: int) -> tuple[float, float, float, float]:
    """One keyframe's four components before the track's bounds block (RevilLib's Evaluate)."""
    if codec == 1:
        return struct.unpack_from("<3f", data, at) + (1.0,)
    if codec == 2:
        x, y, z = struct.unpack_from("<3f", data, at)
        return (x, y, z, math.sqrt(max(0.0, 1.0 - x * x - y * y - z * z)))
    if codec == 3:
        return struct.unpack_from("<3f", data, at) + (1.0,)
    if codec == 4:
        x, y, z = struct.unpack_from("<3H", data, at)
        return (x / 65535.0, y / 65535.0, z / 65535.0, 1.0)
    if codec == 5:
        x, y, z = data[at], data[at + 1], data[at + 2]
        return (x / 255.0, y / 255.0, z / 255.0, 1.0)
    if codec == 6:
        value = int.from_bytes(data[at:at + 8], "little")
        out = []
        for raw in ((value >> 42) & 0x3FFF, (value >> 28) & 0x3FFF,
                    (value >> 14) & 0x3FFF, value & 0x3FFF):
            sign = -1.0 if raw > 4095.5 else 0.0
            out.append((raw * (sign + 1.0) + (16383.0 - raw) * sign) / 4095.75)
        return tuple(out)
    if codec == 7:
        value = _u32(data, at)
        return tuple(((value >> shift) & 0x7F) / 127.0 for shift in (0, 7, 14, 21))
    if codec in (11, 12, 13):
        value = _u32(data, at)
        xyzw = [0.0, 0.0, 0.0, 0.0]
        xyzw[{11: 0, 12: 1, 13: 2}[codec]] = (value & 0x3FFF) / 16383.0
        xyzw[3] = ((value >> 14) & 0x3FFF) / 16383.0
        return tuple(xyzw)
    if codec == 14:
        value = int.from_bytes(data[at:at + 6], "little")
        x = value & 0x7FF
        y = (((value >> 11) << 6) | (data[at + 1] & 0x3F)) & 0x7FF
        z = (((value >> 22) << 1) | (data[at + 2] & 0x1)) & 0x7FF
        w = (value >> 33) & 0x7FF
        return (x / 2047.0, y / 2047.0, z / 2047.0, w / 2047.0)
    if codec == 15:
        value = int.from_bytes(data[at:at + 5], "little")
        x = ((value << 1) | (data[at + 1] & 0x1)) & 0x1FF
        y = (((value >> 9) << 2) | (data[at + 2] & 0x3)) & 0x1FF
        z = (((value >> 18) << 3) | (data[at + 3] & 0x7)) & 0x1FF
        w = (((value >> 27) << 4) | (data[at + 4] & 0xF)) & 0x1FF
        return (x / 511.0, y / 511.0, z / 511.0, w / 511.0)
    raise CameraError(f"no keyframe decoder for buffer type {codec}")


def _gap(codec: int, data: bytes, at: int) -> int:
    if codec == 1 or codec == 2:
        return 1
    if codec == 3:
        return _u32(data, at + 0x0C)
    if codec == 4:
        return struct.unpack_from("<H", data, at + 6)[0]
    if codec == 5:
        return data[at + 3]
    if codec == 6:
        return data[at + 7]
    if codec == 7:
        return data[at + 3] >> 4
    if codec in (11, 12, 13):
        return data[at + 3] >> 4
    if codec == 14:
        return struct.unpack_from("<H", data, at + 4)[0] >> 12
    if codec == 15:
        return data[at + 4] >> 4
    raise CameraError(f"no frame-gap decoder for buffer type {codec}")


def keys(data: bytes, track: Track) -> list[tuple[int, tuple[float, float, float, float]]]:
    """A track's keys as (frame, value before the bounds block), as RevilLib decodes them."""
    if track.buffer_type not in CODECS:
        raise CameraError(f"no decoder for buffer type {track.buffer_type}")
    if track.size % CODECS[track.buffer_type][1]:
        raise CameraError(f"buffer type {track.buffer_type}'s keys don't tile its {track.size} bytes")
    stride = CODECS[track.buffer_type][1]
    out = []
    frame = 0
    for at in range(track.offset, track.offset + track.size, stride):
        out.append((frame, key_value(track.buffer_type, data, at)))
        frame += _gap(track.buffer_type, data, at)
    return out


def apply_bounds(track: Track, data: bytes,
                 value: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """A key with its track's bounds block applied, as RevilLib does: offset + scale * value."""
    if not track.bounds:
        return value
    scale = struct.unpack_from("<4f", data, track.bounds)
    offset = struct.unpack_from("<4f", data, track.bounds + 0x10)
    return tuple(offset[k] + scale[k] * value[k] for k in range(4))


def check(data: bytes) -> Counter:
    """Check C1's per-file tallies: the header and layout, then every track's keys."""
    c: Counter = Counter()
    try:
        camera = read(data)
    except (CameraError, struct.error, IndexError):
        c["C1 not read"] += 1
        return c
    c["C1 read"] += 1
    c[f"version {camera.version}"] += 1
    c[f"{camera.count} table entries"] += 1
    c[f"{len(camera.records)} cameras"] += 1
    for record in camera.records.values():
        c["frame counts"] += 1
        if record.flag not in (0, 1):
            c["flag outside 0 and 1"] += 1
        if record.fourth.offset:
            c["fourth block present"] += 1
        for track in record.tracks:
            c[f"buffer type {track.buffer_type}"] += 1
            if not track.offset:
                if track.size:
                    c["key size without a buffer"] += 1
                continue
            if track.buffer_type not in CODECS:
                c[f"buffer type {track.buffer_type} has no decoder"] += 1
                continue
            try:
                ks = keys(data, track)
            except (CameraError, struct.error, IndexError):
                c["keys don't tile"] += 1
                continue
            if sum(_gap(track.buffer_type, data, at)
                   for at in range(track.offset, track.offset + track.size, CODECS[track.buffer_type][1])
                   ) != record.frames - 1:
                c["key gaps don't cover the frames"] += 1
            if track.buffer_type in ROTATIONS:
                for _, value in ks:
                    q = apply_bounds(track, data, value)
                    if abs(math.sqrt(sum(v * v for v in q)) - 1.0) > 0.03:
                        c["rotation key isn't unit"] += 1
    return c
