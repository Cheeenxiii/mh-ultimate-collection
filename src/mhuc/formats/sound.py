"""MH4U's and MH3U's sound resources: waves (`MADP`), banks (`SNDB`) and requests (`SREQ`).

The layouts are in specs/sound.md. MH4U and MH3U share the classes, but MH3U ships one file version
older in every kind: waves `MADP` 4 against 5, banks `SNDB` 10 against 11 and requests `SREQ` 6
against 8. The older layouts are laid out and checked against MH3U's RomFS by check SN6; the wave
and bank records are the same size, and a wave's decoder fields are byte-identical to MH4U's for
audio both games ship (SN6).

Little endian throughout.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass


class SoundError(ValueError):
    pass


# ---------------------------------------------------------------- waves

WAVE_MAGIC = b"MADP"
WAVE_VERSIONS = (4, 5)
WAVE_HEADER_V4 = 0x2C          # + 0x30 bytes per channel
WAVE_BLOCK = 0x30              # one channel's decoder block: coefficients, state, 8 unknown bytes
WAVE_DATA_V5 = 0x60            # version 5 mono effect


@dataclass(frozen=True)
class Wave:
    """One `MADP` wave.

    `word_14` and `word_18` are 0x14 and 0x18 as stored: on an effect wave they are the loop flag
    and loop start, on a music stream the loop start and loop end (specs/sound.md, "Wave").
    `seek_count` is version 4's seek table length; the table follows the data, 20 bytes per entry.
    `trailing` is the file's length after `data_offset + data_size` (0 unless there is a seek table).
    """
    version: int
    channels: int
    samples: int
    rate: int
    word_14: int
    word_18: int
    data_offset: int
    data_size: int
    seconds: float
    seek_count: int
    trailing: int


def _u32(data: bytes, at: int) -> int:
    return struct.unpack_from("<I", data, at)[0]


def read_wave(data: bytes) -> Wave:
    """Parse one wave header. Raises SoundError unless its fields and its size agree."""
    if len(data) < 0x2C or data[:4] != WAVE_MAGIC:
        raise SoundError("not a wave (magic)")
    version = _u32(data, 4)
    if version not in WAVE_VERSIONS:
        raise SoundError(f"MADP version {version}, not MH4U's 5 or MH3U's 4")
    channels = data[8]
    if channels not in (1, 2):
        raise SoundError(f"{channels} channels, not 1 or 2")
    samples, rate, word_14, word_18, data_offset, data_size = struct.unpack_from("<6I", data, 0x0C)
    seconds, = struct.unpack_from("<f", data, 0x24)
    if rate == 0:
        raise SoundError("sample rate 0")
    if data_size == 0 or data_size % 0x100:
        raise SoundError(f"data size {data_size} isn't a positive multiple of 0x100")
    if abs(seconds - samples / rate) > max(1e-3, samples / rate * 1e-5):
        raise SoundError(f"{seconds} s for {samples} samples at {rate} Hz")
    if version == 4:
        expected = WAVE_HEADER_V4 + WAVE_BLOCK * channels
        if data_offset != expected:
            raise SoundError(f"data at {data_offset:#x}, expected {expected:#x} for {channels} channels")
        word_28 = _u32(data, 0x28)
        if word_28 >> 16 != 0x3348:
            raise SoundError(f"0x28 is {word_28:#x}, not 0x3348|seek count")
        seek_count = word_28 & 0xFFFF
        if data_offset + data_size > len(data):
            raise SoundError("data runs past the end of the file")
        trailing = len(data) - data_offset - data_size
        if trailing != 20 * seek_count:
            raise SoundError(f"{trailing} bytes after the data for {seek_count} seek entries")
    else:
        # Version 5's stereo (music) layout keeps its seek table in the header, after 0x30;
        # only the mono effect layout is laid out here (specs/sound.md, "Wave").
        if channels != 1:
            raise SoundError("MADP version 5 stereo: the music layout isn't laid out")
        if data_offset != WAVE_DATA_V5:
            raise SoundError(f"data at {data_offset:#x}, expected {WAVE_DATA_V5:#x}")
        if _u32(data, 0x28) != 0 or _u32(data, 0x2C) != WAVE_DATA_V5:
            raise SoundError("version 5 mono's 0x28/0x2C aren't 0 and 0x60")
        if data_offset + data_size > len(data):
            raise SoundError("data runs past the end of the file")
        seek_count = 0
        trailing = len(data) - data_offset - data_size
    return Wave(version, channels, samples, rate, word_14, word_18, data_offset, data_size,
                seconds, seek_count, trailing)


def check_wave(data: bytes) -> dict:
    """The counts check SN6 keeps for one wave; read_wave has already validated it."""
    return {}
