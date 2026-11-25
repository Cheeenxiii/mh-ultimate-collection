"""The effect resources' readers refuse what the specs say can't happen (specs/mef.md, specs/efl.md).

The files here are synthetic: the real ones are checked in tests/test_with_game_files.py.
"""
from __future__ import annotations

import struct

import pytest

from mhuc.formats import efl, mef


def _mef(count: int, record: bytes | None = None) -> bytes:
    body = bytes(mef.MEF_RECORD) * count if record is None else record * count
    return mef.MEF_MAGIC + struct.pack("<II", mef.MEF_VERSION, count) + body


def test_mef_reads_its_records_and_keeps_them_unparsed():
    record = bytes(mef.MEF_RECORD)
    record = record[:0x0C] + struct.pack("<H", 0x0220) + record[0x0E:]
    parsed = mef.read_mef(_mef(2, record))
    assert len(parsed) == 2
    assert parsed.records[0].u16(0x0C) == 0x0220
    assert parsed.records[0].f32(0x38) == 0.0


def test_mef_refuses_a_length_that_is_not_its_header_and_records():
    with pytest.raises(mef.MefError, match="bytes for"):
        mef.read_mef(_mef(2)[:-1])


def test_mef_refuses_another_version():
    data = bytearray(_mef(1))
    struct.pack_into("<I", data, 4, 8)
    with pytest.raises(mef.MefError, match="version"):
        mef.read_mef(bytes(data))


def test_esq_reads_six_section_offsets_and_allows_an_empty_section():
    data = mef.ESQ_MAGIC + struct.pack("<II", mef.ESQ_VERSION, mef.ESQ_HEADER) + \
        struct.pack("<6I", 0x24, 0x30, 0x30, 0x40, 0x40, 0x50) + bytes(0x40)
    parsed = mef.read_esq(data)
    assert parsed.sections == (0x24, 0x30, 0x30, 0x40, 0x40, 0x50)


def test_esq_refuses_a_section_offset_that_moves_backwards():
    data = mef.ESQ_MAGIC + struct.pack("<II", mef.ESQ_VERSION, mef.ESQ_HEADER) + \
        struct.pack("<6I", 0x40, 0x30, 0x30, 0x40, 0x40, 0x50) + bytes(0x40)
    with pytest.raises(mef.MefError, match="section offset"):
        mef.read_esq(data)


def test_psl_reads_a_tiny_file_and_a_slot_table():
    assert mef.read_psl(mef.PSL_MAGIC + struct.pack("<HH", mef.PSL_VERSION, 0)).slots == ()
    table = struct.pack("<HH", mef.PSL_VERSION, 2) + struct.pack("<2I", 0, 0x10)
    parsed = mef.read_psl(mef.PSL_MAGIC + table + bytes(0x10))
    assert parsed.slots == (0, 0x10)


def test_psl_refuses_a_descriptor_that_is_not_where_the_slot_order_puts_it():
    table = struct.pack("<HH", mef.PSL_VERSION, 2) + struct.pack("<2I", 0, 0x20)
    with pytest.raises(mef.MefError, match="descriptor"):
        mef.read_psl(mef.PSL_MAGIC + table + bytes(0x20))


def _efl(version: int = 0x30111104, block: bytes = bytes(0x20)) -> bytes:
    header = efl.EFL_MAGIC + struct.pack("<II", version, len(block)) + struct.pack("<f", 60.0) + \
        struct.pack("<HH", 1, 2) + struct.pack("<I", 0x100) + bytes(0x18)
    return header + block


def test_efl_reads_its_header_and_block():
    parsed = efl.read_efl(_efl())
    assert parsed.version in efl.EFL_VERSIONS
    assert parsed.field_0c == 60.0
    assert parsed.field_10 == (1, 2)
    assert len(parsed.block) == parsed.block_size


def test_efl_refuses_a_block_size_that_does_not_fill_the_file():
    with pytest.raises(efl.EflError, match="block"):
        efl.read_efl(_efl()[:-1])


def test_efl_refuses_a_version_that_is_not_one_of_the_three():
    with pytest.raises(efl.EflError, match="version"):
        efl.read_efl(_efl(version=0x30111105))


def test_pel_reads_its_version_and_refuses_another():
    parsed = efl.read_pel(efl.PEL_MAGIC + struct.pack("<I", efl.PEL_VERSION) + b"body")
    assert parsed.version == efl.PEL_VERSION
    assert parsed.body == b"body"
    with pytest.raises(efl.EflError, match="version"):
        efl.read_pel(efl.PEL_MAGIC + struct.pack("<I", 14))
