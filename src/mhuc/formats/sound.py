"""A monster's sound resources: waves (`MADP`), banks (`SNDB`/`SBKR`), requests (`SREQ`/`SRQR`)
and sound calls (`MSS`).

The layouts are in specs/sound.md. MH4U and MH3U share the classes, but MH3U ships one file version
older in every kind: waves `MADP` 4 against 5, banks `SNDB` 10 against 11, requests `SREQ` 6
against 8, sound calls `MSS` 0x20110404 against 0x20120123. MHXX has the next generation's bank
(`SBKR` 4) and request (`SRQR` 5) magics, its waves are already version 5 and its sound call
`MSS` 0x20131015 has MH4U's layout. Check SN6 lays MH3U's layouts out against its whole RomFS;
SN7/SN8 lay MH4U's and MHXX's out against the monster archives.

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
# MHXX writes version 5 too, but its mono effect keeps 8 more bytes before the data and an 8-byte
# stamp in place of version 5's second 0x60, then 24 bytes after it (specs/sound.md, check SN7).
WAVE_DATA_GU = 0x68
WAVE_STAMP_GU = 0x120907E0
WAVE_TAIL_GU = 24


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
    layout: str = ""               # "mh4u", "mh3u" or "mhxx"


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
        if data_offset not in (WAVE_DATA_V5, WAVE_DATA_GU):
            raise SoundError(f"data at {data_offset:#x}, not MH4U's 0x60 or MHXX's 0x68")
        if _u32(data, 0x28) != 0:
            raise SoundError("version 5 mono's word 0x28 isn't 0")
        if data_offset == WAVE_DATA_V5:
            if _u32(data, 0x2C) != WAVE_DATA_V5:
                raise SoundError("version 5 mono's 0x2C isn't 0x60")
            layout = "mh4u"
        else:
            if _u32(data, 0x2C) != WAVE_STAMP_GU:
                raise SoundError(f"MHXX's 0x2C is {_u32(data, 0x2C):#x}, not {WAVE_STAMP_GU:#x}")
            layout = "mhxx"
        if data_offset + data_size > len(data):
            raise SoundError("data runs past the end of the file")
        seek_count = 0
        trailing = len(data) - data_offset - data_size
        if layout == "mhxx" and trailing != WAVE_TAIL_GU:
            raise SoundError(f"{trailing} bytes after MHXX's wave data, not {WAVE_TAIL_GU}")
        if layout == "mh4u" and trailing:
            raise SoundError(f"{trailing} bytes after MH4U's wave data")
    return Wave(version, channels, samples, rate, word_14, word_18, data_offset, data_size,
                seconds, seek_count, trailing, "mh3u" if version == 4 else layout)


def check_wave(data: bytes) -> dict:
    """The counts check SN6 keeps for one wave; read_wave has already validated it."""
    wave = read_wave(data)
    counts = {f"SN6 wave {('mono', 'stereo')[wave.channels - 1]}": 1}
    if wave.seek_count:
        counts["SN6 wave with a seek table"] = 1
    if wave.data_size == 0:
        counts["SN6 empty wave"] = 1
    return counts


def wave_to_v5(data: bytes) -> bytes:
    """MH3U's version 4 mono effect wave as MH4U's version 5: the header moves, the audio doesn't.

    The decoder block (16 coefficients and four state words) sits at 0x2C on version 4 and 0x30 on
    version 5; the sample data comes right after it. Version 5 also writes 0x60 (the data offset)
    at 0x1C and 0x2C and 0 at 0x28, where version 4 has the data offset and the seek marker. The
    eight bytes at 0x58 are unused in both versions. A version 5 wave is returned unchanged.
    """
    wave = read_wave(data)
    if wave.layout == "mh4u":
        return data
    if wave.channels != 1:
        raise SoundError("a stereo wave is a music stream, not a monster's effect")
    if wave.seek_count:
        raise SoundError("a wave with a seek table is a music stream, not a monster's effect")
    if wave.layout == "mhxx":
        coefs, state = 0x38, 0x58
    else:
        coefs, state = 0x2C, 0x4C
    header = bytearray(WAVE_DATA_V5)
    header[0:4] = WAVE_MAGIC
    struct.pack_into("<I", header, 4, 5)
    header[8:12] = data[8:12]
    struct.pack_into("<6I", header, 0x0C, wave.samples, wave.rate, wave.word_14, wave.word_18,
                     WAVE_DATA_V5, wave.data_size)
    struct.pack_into("<f", header, 0x24, wave.seconds)
    struct.pack_into("<I", header, 0x28, 0)
    struct.pack_into("<I", header, 0x2C, WAVE_DATA_V5)
    header[0x30:0x50] = data[coefs:coefs + 0x20]        # coefficients
    header[0x50:0x58] = data[state:state + 8]           # gain, predictor/scale, history 1, history 2
    start = wave.data_offset
    return bytes(header) + data[start:start + wave.data_size]


# ---------------------------------------------------------------- banks

BANK_MAGIC = b"SNDB"
BANK_VERSIONS = (10, 11)
# MHXX writes the next generation's bank, same container and record shapes, other magic and flags
# (specs/sound.md, check S3): `SBKR` version 4.
BANK_GU_MAGIC = b"SBKR"
BANK_GU_VERSION = 4
BANK_LAYOUTS = {(BANK_MAGIC, 10), (BANK_MAGIC, 11), (BANK_GU_MAGIC, BANK_GU_VERSION)}
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
    if len(data) < BANK_HEADER or data[:4] not in (BANK_MAGIC, BANK_GU_MAGIC):
        raise SoundError("not a bank (magic)")
    version, groups_n, entries_n, tail_n = struct.unpack_from("<4I", data, 4)
    if (data[:4], version) not in BANK_LAYOUTS:
        raise SoundError(f"{data[:4]!r} version {version}, not MH4U's SNDB 11, MH3U's SNDB 10 "
                         f"or MHXX's SBKR 4")
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


def write_bank(bank: Bank, version: int = 11, rename=None) -> bytes:
    """Lay a bank out again as `version`, optionally moving every entry's path.

    The three layouts share the container, so a conversion only needs the version it writes (11 for
    MH4U) and a path map; the group records, the entries' type ids and parameters and the tail are
    copied as they are.
    """
    rename = rename or (lambda p: p)
    out = bytearray(BANK_MAGIC + struct.pack("<4I", version, len(bank.groups), len(bank.entries),
                                             len(bank.tail)))
    for g in bank.groups:
        out += struct.pack("<HHII", g.id, g.flags, g.first, g.x)
    for e in bank.entries:
        if len(e.params) != BANK_PARAMS:
            raise SoundError(f"{e.name}: {len(e.params)} parameter bytes, not {BANK_PARAMS}")
        name = rename(e.name).encode("latin-1")
        if b"\0" in name:
            raise SoundError(f"{e.name!r}: a path can't hold a NUL")
        out += name + b"\0" + struct.pack("<I", e.type_id) + e.params
    for value, index in bank.tail:
        out += struct.pack("<fI", value, index)
    return bytes(out)


WAVE_TYPE_ID = 0x67195A2E     # rLtSoundSourceADPCM, the type every MH4U/MH3U bank entry names
WAVE_TYPE_ID_GU = 0x79C47B59  # rSoundSourceADPCM, MHXX's wave class


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


# MHXX's request uses the next generation's magic and version but not MHGU Switch's record size:
# its records are 100 bytes (MH4U's 92-byte record plus two zero words), and the string table is
# MH4U's offsets-then-names (specs/sound.md, check S3).
GU_REQUEST_MAGIC = b"SRQR"
GU_REQUEST_VERSION = 5
GU_REQUEST_HEADER = 0x10
GU_REQUEST_SIZES = (100,)       # MHXX 3DS; MHGU Switch writes 132, which mhuc does not read


@dataclass(frozen=True)
class GuRequestRecord:
    """One record as its u32 words: 25 on MHXX. Words 0 to 21 are MH4U's."""
    words: tuple[int, ...]

    @property
    def id(self) -> int:
        return self.words[0] & 0xFFFF

    @property
    def bank(self) -> int | None:
        return None if self.words[21] == NO_BANK else self.words[21]


@dataclass(frozen=True)
class GuRequest:
    version: int
    record_size: int
    records: tuple[GuRequestRecord, ...]
    banks: tuple[str, ...]


def read_request_gu(data: bytes) -> GuRequest:
    """Parse one MHXX/MHGU request. Raises SoundError unless its records and names tile the file.

    The header is MH4U's (magic, version, record count, string table offset), and so is the string
    table: one u32 offset per bank, then the NUL-terminated names, ending the file. Only the record
    size differs, and the caller reads words 0 to 21 as MH4U's.
    """
    if len(data) < GU_REQUEST_HEADER or data[:4] != GU_REQUEST_MAGIC:
        raise SoundError("not a GU request (magic)")
    version, count, strings_at = struct.unpack_from("<3I", data, 4)
    if version != GU_REQUEST_VERSION:
        raise SoundError(f"SRQR version {version}, not {GU_REQUEST_VERSION}")
    if count == 0:
        raise SoundError("no records")
    span = strings_at - GU_REQUEST_HEADER
    if span <= 0 or span % count:
        raise SoundError(f"{count} records can't fill {span} bytes")
    record_size = span // count
    if record_size not in GU_REQUEST_SIZES:
        raise SoundError(f"{record_size}-byte records, not MHXX's 100")
    if strings_at + 4 > len(data):
        raise SoundError("no room for the string table")
    first, = struct.unpack_from("<I", data, strings_at)
    if first < strings_at or (first - strings_at) % 4:
        raise SoundError(f"first bank name at {first:#x}, not a whole number of offsets after {strings_at:#x}")
    names_n = (first - strings_at) // 4
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
    words = record_size // 4
    records = tuple(GuRequestRecord(struct.unpack_from(f"<{words}I", data,
                                                       GU_REQUEST_HEADER + record_size * i))
                    for i in range(count))
    for i, record in enumerate(records):
        if record.bank is not None and record.bank >= names_n:
            raise SoundError(f"record {i}: bank {record.bank} of {names_n}")
    return GuRequest(version, record_size, records, tuple(banks))


def write_request(records: tuple[RequestRecord, ...], banks: tuple[str, ...],
                  version: int = 8) -> bytes:
    """Lay a request out as MH4U's version 8: 92-byte records, then the bank names.

    `records` are MH4U's 23-word records. The string table starts at `0x10 + 92 n`, one u32 offset
    per bank followed by the NUL-terminated names, with no padding (specs/sound.md).
    """
    count = len(records)
    strings_at = REQUEST_HEADER + REQUEST_RECORD * count
    out = bytearray(REQUEST_MAGIC + struct.pack("<3I", version, count, strings_at))
    for record in records:
        if len(record.words) != REQUEST_WORDS:
            raise SoundError(f"{len(record.words)} request words, not {REQUEST_WORDS}")
        out += struct.pack(f"<{REQUEST_WORDS}I", *record.words)
    at = strings_at + 4 * len(banks)
    offsets = []
    for name in banks:
        offsets.append(at)
        at += len(name.encode("latin-1")) + 1
    out += struct.pack(f"<{len(banks)}I", *offsets) if banks else b""
    for name in banks:
        out += name.encode("latin-1") + b"\0"
    return bytes(out)


# ---------------------------------------------------------------- sound calls

SEQUENCE_MAGIC = b"MSS\0"
SEQUENCE_LAYOUTS = {
    0x20110404: (2048, "MH3U"),
    0x20120123: (512, "MH4U"),
    0x20131015: (512, "MHXX/MHGU"),
}
SEQUENCE_HEADER = 0x10
SEQUENCE_SENTINEL = 0x0000FFFF
SEQUENCE_RECORD = 0x10        # key, event count, x, 0xffffffff, data offset


@dataclass(frozen=True)
class SequenceRecord:
    """One record exactly as stored: its key and every byte from its start to the next record's.

    The engine writes the record's events with offsets relative to the record itself, so a
    conversion that moves the records only has to move the pair table's file offsets.
    """
    key: int
    body: bytes


@dataclass(frozen=True)
class Sequence:
    version: int
    count: int
    table: tuple[int, ...]          # u16 per motion number: its record's row, or 0xffff
    records: tuple[SequenceRecord, ...]


def read_sequence(data: bytes) -> Sequence:
    """Parse one sound call (`MSS`). Raises SoundError unless its tables and records tile the file.

    The three versions share the layout (specs/sound.md): magic, version, a u32 whose low half is
    the record count and whose high half is 0x0100, a zero word, a u16 table of 512 rows (2048 on
    MH3U), a pair table of {u32 key, u32 record offset}, then the records. A record is a u32 key, a
    u16 event count, a u16 x, 0xffffffff, a u32 data offset (0x10 + 8 × event count), that many
    {u32 frame, u32 event offset} pairs, a u16 0xffff and a u16 0 sentinel, then the events; each event offset
    is relative to the record and starts with its u16 frame.
    """
    if len(data) < SEQUENCE_HEADER or data[:4] != SEQUENCE_MAGIC:
        raise SoundError("not a sound call (magic)")
    version, count_word, zero = struct.unpack_from("<3I", data, 4)
    if version not in SEQUENCE_LAYOUTS:
        raise SoundError(f"MSS version {version:#x} isn't MH3U's 0x20110404, MH4U's 0x20120123 "
                         f"or MHXX's 0x20131015")
    table_len, game = SEQUENCE_LAYOUTS[version]
    count = count_word & 0xFFFF
    if count_word >> 16 != 0x0100:
        raise SoundError(f"the count word {count_word:#010x}'s high half, not 0x0100")
    if zero:
        raise SoundError(f"word 0x0c is {zero:#x}, not 0")
    if count > table_len:
        raise SoundError(f"{count} records but only {table_len} table rows ({game})")
    table = struct.unpack_from(f"<{table_len}H", data, SEQUENCE_HEADER)
    want = tuple(range(count)) + (0xFFFF,) * (table_len - count)
    if table != want:
        raise SoundError(f"the table isn't rows 0..{count - 1} then 0xffff")
    pairs_at = SEQUENCE_HEADER + 2 * table_len
    if pairs_at + 8 * count > len(data):
        raise SoundError("the pair table runs past the end of the file")
    pairs = tuple(struct.unpack_from("<II", data, pairs_at + 8 * i) for i in range(count))
    first = pairs_at + 8 * count
    if not pairs:
        return Sequence(version, 0, table, ())
    if pairs[0][1] != first:
        raise SoundError(f"the first record is at {pairs[0][1]:#x}, not {first:#x}")
    records = []
    for i, (key, start) in enumerate(pairs):
        end = pairs[i + 1][1] if i + 1 < count else len(data)
        if not first <= start < end:
            raise SoundError(f"record {i}: at {start:#x}, past the file or the next record")
        body = data[start:end]
        rkey, events, x, minus_one, data_at = struct.unpack_from("<IHHII", body, 0)
        if rkey != key:
            raise SoundError(f"record {i}: key {rkey} in the record, {key} in the pair table")
        if minus_one != 0xFFFFFFFF:
            raise SoundError(f"record {i}: word 0x08 is {minus_one:#x}, not 0xffffffff")
        if data_at != SEQUENCE_RECORD + 8 * events:
            raise SoundError(f"record {i}: data offset {data_at:#x}, not "
                             f"{SEQUENCE_RECORD + 8 * events:#x}")
        if data_at + 4 > len(body) or struct.unpack_from("<I", body, data_at)[0] != SEQUENCE_SENTINEL:
            raise SoundError(f"record {i}: no 0xffff0000 sentinel at {data_at:#x}")
        last = data_at
        for j in range(events):
            frame, at = struct.unpack_from("<II", body, SEQUENCE_RECORD + 8 * j)
            if not last < at + 2 <= len(body):
                raise SoundError(f"record {i} event {j}: offset {at:#x} outside the record")
            if struct.unpack_from("<H", body, at)[0] != frame & 0xFFFF:
                raise SoundError(f"record {i} event {j}: no u16 frame {frame} at {at:#x}")
            last = at
        records.append(SequenceRecord(key, body))
    return Sequence(version, count, table, tuple(records))


def write_sequence(sequence: Sequence, version: int = 0x20120123) -> bytes:
    """Lay a sound call out as `version`, keeping every record's bytes.

    Moving the records is all a conversion does: the table shrinks from MH3U's 2048 rows to 512,
    the pair table follows it, and each pair's file offset moves with the records. The records
    themselves hold only record-relative offsets, so their bytes are copied unchanged.
    """
    if version not in SEQUENCE_LAYOUTS:
        raise SoundError(f"{version:#x} isn't a sound call version")
    table_len, _ = SEQUENCE_LAYOUTS[version]
    if sequence.count != len(sequence.records):
        raise SoundError(f"{sequence.count} records in the header, {len(sequence.records)} parsed")
    if sequence.count > table_len:
        raise SoundError(f"{sequence.count} records don't fit {version:#x}'s {table_len} rows")
    table = tuple(range(sequence.count)) + (0xFFFF,) * (table_len - sequence.count)
    pairs_at = SEQUENCE_HEADER + 2 * table_len
    at = pairs_at + 8 * sequence.count
    out = bytearray(SEQUENCE_MAGIC + struct.pack("<3I", version, 0x01000000 | sequence.count, 0))
    out += struct.pack(f"<{table_len}H", *table)
    for record in sequence.records:
        out += struct.pack("<II", record.key, at)
        at += len(record.body)
    for record in sequence.records:
        out += record.body
    return bytes(out)


def check_sequence(data: bytes) -> dict:
    """The counts check SN8 keeps for one sound call; read_sequence has already validated it."""
    sequence = read_sequence(data)
    counts = {"SN8 sequence records": sequence.count, "SN8 sequence events":
              sum(struct.unpack_from("<H", r.body, 4)[0] for r in sequence.records)}
    counts[f"SN8 sequence {SEQUENCE_LAYOUTS[sequence.version][1]}"] = 1
    return counts


