"""MH4U's and MH3U's sound resources: waves (`MADP`), banks (`SNDB`) and requests (`SREQ`).

The layouts are in specs/sound.md. MH4U and MH3U share the classes, but MH3U ships one file version
older in every kind: waves `MADP` 4 against 5, banks `SNDB` 10 against 11 and requests `SREQ` 6
against 8. Check SN6 lays the older layouts out and checks them against MH3U's whole RomFS: the
bank and request containers are MH4U's, and a wave's decoder fields are MH4U's moved down by four
bytes, byte-identical for audio both games ship.

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
    if data_size % 0x100:
        raise SoundError(f"data size {data_size:#x} isn't a multiple of 0x100")
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
    wave = read_wave(data)
    counts = {f"SN6 wave {('mono', 'stereo')[wave.channels - 1]}": 1}
    if wave.seek_count:
        counts["SN6 wave with a seek table"] = 1
    if wave.data_size == 0:
        counts["SN6 empty wave"] = 1
    return counts


# ---------------------------------------------------------------- banks

BANK_MAGIC = b"SNDB"
BANK_VERSIONS = (10, 11)
BANK_HEADER = 0x14
BANK_GROUP = 12
BANK_PARAMS = 76               # per entry, after the wave path and the type id
BANK_TAIL = 8                  # {f32, u32} per tail record


@dataclass(frozen=True)
class BankGroup:
    """One group record: its id, flags (0x8000 | category << 11 | 2 × entry count), first entry."""
    id: int
    flags: int
    first: int
    x: int


@dataclass(frozen=True)
class BankEntry:
    """One wave entry: its RomFS-like path, the resource class id it names and 76 parameter bytes."""
    name: str
    type_id: int
    params: bytes


@dataclass(frozen=True)
class Bank:
    version: int
    groups: tuple[BankGroup, ...]
    entries: tuple[BankEntry, ...]
    tail: tuple[tuple[float, int], ...]   # {f32 value, u32 index}: one per header word 0x10


def read_bank(data: bytes) -> Bank:
    """Parse one bank. Raises SoundError unless its groups, entries and tail tile the file."""
    if len(data) < BANK_HEADER or data[:4] != BANK_MAGIC:
        raise SoundError("not a bank (magic)")
    version, groups_n, entries_n, tail_n = struct.unpack_from("<4I", data, 4)
    if version not in BANK_VERSIONS:
        raise SoundError(f"SNDB version {version}, not MH4U's 11 or MH3U's 10")
    at = BANK_HEADER + BANK_GROUP * groups_n
    if at > len(data):
        raise SoundError("group records run past the end of the file")
    groups = tuple(BankGroup(*struct.unpack_from("<HHII", data, BANK_HEADER + BANK_GROUP * i))
                   for i in range(groups_n))
    for g in groups:
        if g.first > entries_n:
            raise SoundError(f"group {g.id}: first entry {g.first} of {entries_n}")
    entries = []
    for i in range(entries_n):
        end = data.find(b"\0", at)
        if end < 0:
            raise SoundError(f"entry {i}: path at {at:#x} isn't NUL-terminated")
        path = data[at:end].decode("latin-1")
        params_at = end + 1 + 4
        if params_at + BANK_PARAMS > len(data):
            raise SoundError(f"entry {i}: parameters run past the end of the file")
        type_id, = struct.unpack_from("<I", data, end + 1)
        entries.append(BankEntry(path, type_id, data[params_at:params_at + BANK_PARAMS]))
        at = params_at + BANK_PARAMS
    if at + BANK_TAIL * tail_n != len(data):
        raise SoundError(f"tail of {tail_n} records at {at:#x} ends at {at + BANK_TAIL * tail_n:#x}, "
                         f"the file at {len(data):#x}")
    tail = tuple(struct.unpack_from("<fI", data, at + BANK_TAIL * i) for i in range(tail_n))
    return Bank(version, groups, tuple(entries), tail)


WAVE_TYPE_ID = 0x67195A2E     # rLtSoundSourceADPCM, the type every bank entry names


def check_bank(data: bytes) -> dict:
    """The counts check SN6 keeps for one bank; read_bank has already validated it."""
    bank = read_bank(data)
    counts = {"SN6 bank entries": len(bank.entries), "SN6 bank groups": len(bank.groups),
              "SN6 bank tail records": len(bank.tail)}
    other = sum(1 for e in bank.entries if e.type_id != WAVE_TYPE_ID)
    if other:
        counts["SN6 bank entries not a wave"] = other
    out_of_order = sum(1 for i, (_, index) in enumerate(bank.tail) if index & 0xFF != i)
    if out_of_order:
        counts["SN6 bank tail index out of order"] = out_of_order
    return counts


# ---------------------------------------------------------------- requests

REQUEST_MAGIC = b"SREQ"
REQUEST_VERSIONS = (6, 8)
REQUEST_HEADER = 0x10
REQUEST_RECORD = 92
REQUEST_WORDS = 23
NO_BANK = 0xFFFFFFFF


@dataclass(frozen=True)
class RequestRecord:
    """One 92-byte record, kept as its 23 u32 words; the fields that are known are the properties."""
    words: tuple[int, ...]

    @property
    def id(self) -> int:
        """The request id code asks for, the low half of word 0."""
        return self.words[0] & 0xFFFF

    @property
    def bank(self) -> int | None:
        """Which of the request's banks to load (word 0x54's index), or None when there is none."""
        return None if self.words[21] == NO_BANK else self.words[21]


@dataclass(frozen=True)
class Request:
    version: int
    records: tuple[RequestRecord, ...]
    banks: tuple[str, ...]   # the bank resources' paths, in the order a record's index names them


def read_request(data: bytes) -> Request:
    """Parse one request. Raises SoundError unless its records and its string table tile the file."""
    if len(data) < REQUEST_HEADER or data[:4] != REQUEST_MAGIC:
        raise SoundError("not a request (magic)")
    version, count, strings_at = struct.unpack_from("<3I", data, 4)
    if version not in REQUEST_VERSIONS:
        raise SoundError(f"SREQ version {version}, not MH4U's 8 or MH3U's 6")
    if strings_at != REQUEST_HEADER + REQUEST_RECORD * count:
        raise SoundError(f"string table at {strings_at:#x}, expected "
                         f"{REQUEST_HEADER + REQUEST_RECORD * count:#x} for {count} records")
    if strings_at + 4 > len(data):
        raise SoundError("no room for the string table")
    first, = struct.unpack_from("<I", data, strings_at)
    if first < strings_at or (first - strings_at) % 4:
        raise SoundError(f"first bank name at {first:#x}, not a whole number of offsets after {strings_at:#x}")
    names_n = (first - strings_at) // 4
    if strings_at + names_n * 4 > len(data):
        raise SoundError("string offsets run past the end of the file")
    banks, at = [], first
    for i in range(names_n):
        offset, = struct.unpack_from("<I", data, strings_at + 4 * i)
        if offset != at:
            raise SoundError(f"bank {i}: name at {offset:#x}, expected {at:#x}")
        end = data.find(b"\0", offset)
        if end < 0:
            raise SoundError(f"bank {i}: name at {offset:#x} isn't NUL-terminated")
        banks.append(data[offset:end].decode("latin-1"))
        at = end + 1
    if at != len(data):
        raise SoundError(f"bank names end at {at:#x}, the file at {len(data):#x}")
    records = tuple(RequestRecord(struct.unpack_from(f"<{REQUEST_WORDS}I", data,
                                                     REQUEST_HEADER + REQUEST_RECORD * i))
                    for i in range(count))
    for i, record in enumerate(records):
        if record.bank is not None and record.bank >= names_n:
            raise SoundError(f"record {i}: bank {record.bank} of {names_n}")
    return Request(version, records, tuple(banks))


def check_request(data: bytes) -> dict:
    """The counts check SN6 keeps for one request; read_request has already validated it."""
    request = read_request(data)
    return {"SN6 request records": len(request.records), "SN6 request banks": len(request.banks)}


