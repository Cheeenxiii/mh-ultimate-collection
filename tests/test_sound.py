"""The sound formats and their conversion, against bytes computed by hand.

A round trip through our own reader and writer proves nothing (CLAUDE.md); each test below builds
the file the format describes with `struct.pack` from values chosen here, so the expected bytes are
independent of the code under test.
"""
from __future__ import annotations

import struct

import pytest

from mhuc.formats import sound

# ---------------------------------------------------------------- sound call

def _mh3u_call(version: int = 0x20110404, table_len: int = 2048, count: int = 1) -> bytes:
    """One record, key 0, one event at frame 5, laid out as the spec says for `version`."""
    pair_at = 0x10 + 2 * table_len
    data_at = 0x10 + 8 * 1
    record = struct.pack("<IHHII", 0, 1, 0, 0xFFFFFFFF, data_at)
    record += struct.pack("<II", 5, data_at + 4)
    record += struct.pack("<HH", 0xFFFF, 0)          # the sentinel: u16 0xffff, u16 0
    record += struct.pack("<HH", 5, 0)               # the event starts with its frame
    table = struct.pack(f"<{table_len}H", *range(count), *([0xFFFF] * (table_len - count)))
    return struct.pack("<4s3I", b"MSS\0", version, 0x01000000 | count, 0) + table \
        + struct.pack("<II", 0, pair_at + 8 * count) + record


def test_sound_call_writer_moves_mh3us_records_into_mh4us_container():
    """specs/sound.md SN8: MH3U's 2048-row table and pair table become MH4U's 512-row ones, and the
    records move with them; their bytes (which hold only record-relative offsets) do not change."""
    source = _mh3u_call()
    sequence = sound.read_sequence(source)
    assert (sequence.version, sequence.count, sequence.records[0].key) == (0x20110404, 1, 0)

    converted = sound.write_sequence(sequence)
    pair_at = 0x10 + 2 * 512
    body = sequence.records[0].body
    expected = struct.pack("<4s3I", b"MSS\0", 0x20120123, 0x01000000 | 1, 0)
    expected += struct.pack("<512H", 0, *([0xFFFF] * 511))
    expected += struct.pack("<II", 0, pair_at + 8) + body
    assert converted == expected
    assert struct.unpack_from("<I", converted, 4)[0] == 0x20120123
    assert struct.unpack_from("<I", converted, pair_at + 4)[0] == pair_at + 8

    back = sound.read_sequence(converted)
    assert [r.key for r in back.records] == [r.key for r in sequence.records]
    assert back.records[0].body == body


def test_sound_call_reader_rejects_an_event_offset_that_misses_its_frame():
    """The record's pair offsets are its only cross-checks; one that points at the wrong place is
    a file the engine would misread, so the reader refuses it."""
    broken = bytearray(_mh3u_call())
    pair_at = 0x10 + 2 * 2048
    record_at = struct.unpack_from("<I", broken, pair_at + 4)[0]
    struct.pack_into("<H", broken, record_at + 0x1C, 6)     # the event's frame, now not the pair's 5
    with pytest.raises(sound.SoundError, match="no u16 frame 5"):
        sound.read_sequence(bytes(broken))


# ---------------------------------------------------------------- waves

def _v4_wave(data_size: int = 0x100) -> bytes:
    samples, rate = 28, 8000
    header = bytearray(0x5C)
    header[0:4] = b"MADP"
    struct.pack_into("<I", header, 4, 4)
    header[8:12] = bytes((1, 0, 0, 1))
    struct.pack_into("<6I", header, 0x0C, samples, rate, 0, 0, 0x5C, data_size)
    struct.pack_into("<f", header, 0x24, samples / rate)
    struct.pack_into("<I", header, 0x28, 0x33480000)
    header[0x2C:0x4C] = bytes(range(0x20))                  # coefficients
    header[0x4C:0x54] = bytes((0, 0, 0x26, 0, 0, 0, 0, 0))  # gain, ps, histories
    return bytes(header) + bytes((0xA5,)) * data_size


def test_wave_to_v5_moves_the_decoder_block_and_keeps_the_audio():
    """MH3U's version 4 header becomes MH4U's version 5: the block at 0x2C moves to 0x30, the state
    at 0x4C to 0x50, and the data moves to 0x60 unchanged (specs/sound.md, SN7)."""
    source = _v4_wave()
    converted = sound.wave_to_v5(source)
    wave = sound.read_wave(converted)
    assert (wave.version, wave.layout, wave.data_offset) == (5, "mh4u", 0x60)
    assert converted[0x30:0x50] == source[0x2C:0x4C]
    assert converted[0x50:0x58] == source[0x4C:0x54]
    assert converted[0x60:] == source[0x5C:]
    assert struct.unpack_from("<I", converted, 0x28)[0] == 0
    assert struct.unpack_from("<I", converted, 0x2C)[0] == 0x60
    assert struct.unpack_from("<I", converted, 0x0C)[0] == 28
    assert struct.unpack_from("<I", converted, 0x10)[0] == 8000


def _mhxx_wave(data_size: int = 0x100) -> bytes:
    samples, rate = 28, 8000
    header = bytearray(0x68)
    header[0:4] = b"MADP"
    struct.pack_into("<I", header, 4, 5)
    header[8:12] = bytes((1, 0, 0, 1))
    struct.pack_into("<6I", header, 0x0C, samples, rate, 0, 0, 0x68, data_size)
    struct.pack_into("<f", header, 0x24, samples / rate)
    struct.pack_into("<I", header, 0x2C, sound.WAVE_STAMP_GU)
    header[0x38:0x58] = bytes(range(0x20))
    header[0x58:0x60] = bytes((0, 0, 0x26, 0, 0, 0, 0, 0))
    header[0x60:0x68] = b"eLite\\so"
    return bytes(header) + bytes((0x5A,)) * data_size + bytes(24)


def test_wave_to_v5_drops_mhxxs_extra_block_and_24_byte_tail():
    """MHXX's version 5 is not MH4U's: coefficients at 0x38, state at 0x58, data at 0x68 and 24
    bytes after it. The conversion copies the audio to MH4U's offsets and writes no tail."""
    source = _mhxx_wave()
    converted = sound.wave_to_v5(source)
    wave = sound.read_wave(converted)
    assert (wave.layout, wave.trailing, wave.data_offset) == ("mh4u", 0, 0x60)
    assert converted[0x30:0x50] == source[0x38:0x58]
    assert converted[0x50:0x58] == source[0x58:0x60]
    assert converted[0x60:] == source[0x68:0x68 + wave.data_size]
    assert len(converted) == 0x60 + wave.data_size


# ---------------------------------------------------------------- banks

def test_bank_writer_keeps_the_group_bytes_and_renames_the_paths():
    """MH3U's and MH4U's bank containers are the same (SN6/SN7): a conversion writes version 11,
    the same group records and parameters, and the port's paths."""
    params = bytes(range(76))
    bank = sound.Bank(10, (sound.BankGroup(0, 0x8032, 0, 0),),
                      (sound.BankEntry("sound\\se\\em\\em001\\wav\\em001_a", sound.WAVE_TYPE_ID,
                                       params),),
                      ((0.5, 7),))
    out = sound.write_bank(bank, 11, lambda p: p.replace("em001", "em125").replace("\\wav\\", "\\wave\\"))
    expected = bytearray(struct.pack("<4s4I", b"SNDB", 11, 1, 1, 1))
    expected += struct.pack("<HHII", 0, 0x8032, 0, 0)
    expected += b"sound\\se\\em\\em125\\wave\\em125_a\0" + struct.pack("<I", sound.WAVE_TYPE_ID) + params
    expected += struct.pack("<fI", 0.5, 7)
    assert out == bytes(expected)


# ---------------------------------------------------------------- requests

def test_request_writer_lays_out_the_string_table_and_records():
    """MH4U's request: a 0x10-byte header, 92-byte records, then one u32 offset per bank and the
    NUL-terminated names, ending the file (specs/sound.md, SN7)."""
    words = tuple(range(23))
    out = sound.write_request((sound.RequestRecord(words),), ("sound\\se\\em\\em125\\snd_em125",))
    count = 1
    strings_at = 0x10 + 92 * count
    assert struct.unpack_from("<4s3I", out, 0)[0:4] == (b"SREQ", 8, count, strings_at)
    assert struct.unpack_from("<23I", out, 0x10) == words
    assert struct.unpack_from("<I", out, strings_at)[0] == strings_at + 4
    assert out[strings_at + 4:] == b"sound\\se\\em\\em125\\snd_em125\0"


def test_read_request_gu_takes_mhxxs_100_byte_records():
    """MHXX's SRQR is not MHGU's: the records are 100 bytes, words 0 to 21 where MH4U has them."""
    count = 1
    soff = 0x10 + 100 * count
    words = (0x7F000000, 0, 1, 0, 0x1000A, 0x14F, 2, 0xFFFF, 0xFFFF,
             0xC0400000, 0xC0400000) + tuple(range(11, 21)) + (0, 0, 0, 0)
    data = struct.pack("<4s3I", b"SRQR", 5, count, soff)
    data += struct.pack("<25I", *words)
    data += struct.pack("<I", soff + 4) + b"sound\\se\\em\\em001_00\\snd_em001_00\0"
    request = sound.read_request_gu(data)
    assert request.record_size == 100
    assert request.records[0].words == words
    assert request.records[0].id == 0
    assert request.banks == ("sound\\se\\em\\em001_00\\snd_em001_00",)
