"""MH4U's and MH3U's stream requests (`.stq`, STRQ versions 0x22 and 0x20): specs/sound.md.

A stream request names the waves one music context can play and maps a request id to one of them
with a level. MH3U ships the same layout one version older, 0x20 (check SN6). Layout (little
endian):

    0x00  char[4]  magic "STRQ"
    0x04  u32      version 0x22 (MH4U) or 0x20 (MH3U)
    0x08  u32      stream count n
    0x0C  u32      sequence count m
    0x10  u32      stream table offset (0x18)
    0x14  u32      sequence table offset (0x18 + 36 n)
    then  n stream records, 36 bytes each, from the stream table offset:
          +0x00 u32 name offset        +0x04 u32 stream length, bytes
          +0x08 u32 sample count       +0x0C u32 channels
          +0x10 u32 sample rate        +0x14 u32 loop start
          +0x18 u32 loop end           +0x1C u32 wave class id
          +0x20 u32 2 (meaning unverified)
    then  m sequence records, 100 bytes each, from the sequence table offset:
          +0x00 u32 request id         +0x24 f32 level
          +0x5C u32 stream index (-1: none)  +0x60 u32 stream pointer slot (filled at load)
    then  the streams' names, NUL-terminated, '\\'-separated, no extension, in stream order,
          from the end of the sequence table to the end of the file.

The stream record's length, sample count, channels, rate and loop are the wave header's own
(specs/sound.md, "Wave"), which makes the record checkable against the `.mca` it names.
"""
from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass

MAGIC = b"STRQ"
VERSION = 0x22              # MH4U's; check S4 reads those
VERSIONS = (0x20, 0x22)    # MH3U's and MH4U's: one layout (check SN6)
HEADER = 0x18
STREAM = 36
SEQUENCE = 100


class StqError(ValueError):
    pass


@dataclass(frozen=True)
class Stream:
    name: str          # a RomFS path, '\\'-separated and without the .mca extension
    size: int          # the wave file's length in bytes
    samples: int
    channels: int
    rate: int
    loop_start: int
    loop_end: int      # 0 when the wave doesn't loop
    type_id: int       # 0x67195a2e, rLtSoundSourceADPCM
    unknown_20: int    # 2 in every MH4U stream; the spec leaves the field unverified


@dataclass(frozen=True)
class Sequence:
    id: int
    level: float       # dB when a stream is set; see specs/sound.md for the field's other use
    stream: int | None  # index into Stq.streams, or None (the record's 0xFFFFFFFF)


@dataclass(frozen=True)
class Stq:
    version: int
    streams: tuple[Stream, ...]
    sequences: tuple[Sequence, ...]


def read(data: bytes) -> Stq:
    """Parse one stream request. Raises StqError unless its tables and names close exactly."""
    if len(data) < HEADER or data[:4] != MAGIC:
        raise StqError("not a stream request (magic)")
    version, = struct.unpack_from("<I", data, 4)
    if version not in VERSIONS:
        raise StqError(f"STRQ version {version:#x}, not MH4U's {VERSION:#x} or MH3U's {VERSIONS[0]:#x}")
    nstreams, nsequences, stream_at, sequence_at = struct.unpack_from("<4I", data, 8)
    if stream_at != HEADER or sequence_at != stream_at + STREAM * nstreams:
        raise StqError(f"stream table at {stream_at:#x}, sequence table at {sequence_at:#x}: "
                       f"expected {HEADER:#x} and {HEADER + STREAM * nstreams:#x}")
    if stream_at + STREAM * nstreams > len(data) or sequence_at + SEQUENCE * nsequences > len(data):
        raise StqError("a table runs past the end of the file")

    streams = []
    names_at = sequence_at + SEQUENCE * nsequences
    expected = names_at
    for i in range(nstreams):
        (name_at, size, samples, channels, rate, loop_start, loop_end, type_id,
         unknown) = struct.unpack_from("<9I", data, stream_at + STREAM * i)
        if name_at != expected:
            raise StqError(f"stream {i}: name at {name_at:#x}, expected {expected:#x}")
        end = data.find(b"\0", name_at)
        if end < 0:
            raise StqError(f"stream {i}: name at {name_at:#x} isn't NUL-terminated")
        streams.append(Stream(data[name_at:end].decode("latin-1"), size, samples, channels, rate,
                              loop_start, loop_end, type_id, unknown))
        expected = end + 1
    if expected != len(data):
        raise StqError(f"names end at {expected:#x}, the file at {len(data):#x}")

    sequences = []
    for i in range(nsequences):
        at = sequence_at + SEQUENCE * i
        request_id, = struct.unpack_from("<I", data, at)
        level, = struct.unpack_from("<f", data, at + 0x24)
        stream, = struct.unpack_from("<I", data, at + 0x5C)
        if stream == 0xFFFFFFFF:
            sequences.append(Sequence(request_id, level, None))
        elif stream >= nstreams:
            raise StqError(f"sequence {request_id}: stream {stream} of {nstreams}")
        else:
            sequences.append(Sequence(request_id, level, stream))
    return Stq(version, tuple(streams), tuple(sequences))


def check(data: bytes) -> Counter:
    """The facts check S4 counts; `read` has already checked the layout."""
    s = read(data)
    c: Counter = Counter()
    c["S4 .stq read"] += 1
    c["S4 streams"] += len(s.streams)
    c["S4 sequences"] += len(s.sequences)
    c["S4 sequences with a stream"] += sum(1 for q in s.sequences if q.stream is not None)
    c["S4 sequences without a stream"] += sum(1 for q in s.sequences if q.stream is None)
    return c
