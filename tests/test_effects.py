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


ESQ_OFFSETS = (0x24, 0x60, 0x9C, 0xD8, 0xE4, 0x120, 0x130)


def _esq(offsets: tuple[int, ...] = ESQ_OFFSETS, motion: int = 70, frame: float = 25.0) -> bytes:
    """A synthetic ESQ: the 0x24 header, seven offsets and sections of each one's stride.

    The seven sections are 0x3C, 0x3C, 0x3C, 0x0C, 0x3C, 0x10 and a fixed 0x258-byte tail (the
    offsets above are those sections' starts). The first 0x3C-byte entry carries the motion and
    frame under test.
    """
    total = ESQ_OFFSETS[6] + 0x258
    body = bytearray(total - mef.ESQ_HEADER)
    body[:mef.ESQ_ENTRY] = struct.pack("<If", motion, frame) + bytes(mef.ESQ_ENTRY - 8)
    return (mef.ESQ_MAGIC + struct.pack("<I", mef.ESQ_VERSION)
            + struct.pack("<7I", *offsets) + bytes(body))


def test_esq_reads_seven_section_offsets_and_its_events_motion_and_frame():
    parsed = mef.read_esq(_esq())
    assert parsed.offsets == ESQ_OFFSETS
    events = parsed.events()
    assert len(events) == 1 + 1 + 1 + 1          # one 0x3C entry in each of sections 0, 1, 2 and 4
    first = events[0]
    assert (first.section, first.motion, first.frame) == (0, 70, 25.0)
    assert all(event.motion == 0 and event.frame == 0.0 for event in events[1:])


def test_esq_refuses_a_first_section_that_does_not_start_at_the_headers_end():
    with pytest.raises(mef.MefError, match="section 0"):
        mef.read_esq(_esq(offsets=(0x28, 0x60, 0x9C, 0xD8, 0xE4, 0x120, 0x130)))


def test_esq_refuses_a_section_offset_that_moves_backwards():
    with pytest.raises(mef.MefError, match="section offset"):
        mef.read_esq(_esq(offsets=(0x24, 0x60, 0x50, 0xD8, 0xE4, 0x120, 0x130)))


def test_esq_refuses_a_section_that_is_not_a_whole_number_of_entries():
    with pytest.raises(mef.MefError, match="whole number"):
        mef.read_esq(_esq(offsets=(0x24, 0x50, 0x9C, 0xD8, 0xE4, 0x120, 0x130)))


def test_esq_refuses_a_tail_that_is_not_the_size_every_file_has():
    with pytest.raises(mef.MefError, match="section 6"):
        mef.read_esq(_esq()[:-1])


def _psl(frames: int = 347, flags: int = 0x200000, lists: bytes = bytes(12)) -> bytes:
    """A synthetic PSL: two slots, one effect slot whose descriptor is at 0x10 and list at 0x1C."""
    table = struct.pack("<HH", mef.PSL_VERSION, 2) + struct.pack("<2I", 0, 0x10)
    return (mef.PSL_MAGIC + table + struct.pack("<3I", frames, flags, 0x1C) + lists)


def test_psl_reads_its_descriptor_and_list_boundaries():
    assert mef.read_psl(mef.PSL_MAGIC + struct.pack("<HH", mef.PSL_VERSION, 0)).slots == ()
    parsed = mef.read_psl(_psl())
    assert parsed.slots == (0, 0x10)
    assert [(d.slot, d.frames, d.flags, d.offset) for d in parsed.descriptors] == \
        [(1, 347, 0x200000, 0x1C)]
    assert parsed.lists() == ((1, 0x1C, len(_psl())),)


def test_psl_refuses_a_descriptor_that_is_not_where_the_slot_order_puts_it():
    table = struct.pack("<HH", mef.PSL_VERSION, 2) + struct.pack("<2I", 0, 0x20)
    with pytest.raises(mef.MefError, match="descriptor"):
        mef.read_psl(mef.PSL_MAGIC + table + bytes(0x20))


def test_psl_refuses_a_first_list_that_does_not_start_after_the_last_descriptor():
    table = struct.pack("<HH", mef.PSL_VERSION, 2) + struct.pack("<2I", 0, 0x10)
    data = mef.PSL_MAGIC + table + struct.pack("<3I", 347, 0x200000, 0x20) + bytes(0x10)
    with pytest.raises(mef.MefError, match="first effect list"):
        mef.read_psl(data)


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


def test_mef_round_trips_its_bytes():
    data = _mef(3)
    assert mef.read_mef(data).to_bytes() == data


def test_esq_and_psl_round_trip_their_bytes():
    esq = _esq()
    assert mef.read_esq(esq).to_bytes() == esq
    tiny = mef.PSL_MAGIC + struct.pack("<HH", mef.PSL_VERSION, 0)
    assert mef.read_psl(tiny).to_bytes() == tiny
    psl = _psl(lists=bytes(12))
    assert mef.read_psl(psl).to_bytes() == psl


def test_efl_round_trips_and_converts_to_each_game_version():
    mh4u = _efl()
    assert efl.read_efl(mh4u).to_bytes() == mh4u
    mh3u = efl.to_mh3u(mh4u)
    mhxx = efl.to_mhxx(mh4u)
    assert efl.read_efl(mh3u).version == efl.EFL_VERSION["mh3u"]
    assert efl.read_efl(mhxx).version == efl.EFL_VERSION["mhxx"]
    assert efl.from_mh3u(mh3u) == mh4u
    assert efl.from_mhxx(mhxx) == mh4u
    assert efl.convert(mh3u, efl.EFL_VERSION["mh4u"])[0x30:] == mh4u[0x30:], "the block moved"


def test_efl_refuses_to_convert_from_the_wrong_game():
    with pytest.raises(efl.EflError, match="not an MHXX"):
        efl.from_mhxx(_efl(version=efl.EFL_VERSION["mh3u"]))


def test_pel_round_trips_its_bytes():
    data = efl.PEL_MAGIC + struct.pack("<I", efl.PEL_VERSION) + b"body"
    assert efl.read_pel(data).to_bytes() == data


def test_effect_map_loads_a_table_and_names_every_unmapped_id(tmp_path):
    from mhuc import effectmap
    folder = tmp_path / "mh3u-mh4u"
    folder.mkdir()
    (folder / "effect.csv").write_text("source,target,source_name,target_name,how\n0x46,544,a,b,match\n")
    rows = effectmap.load(str(folder))
    assert rows == {0x46: 544}
    m = effectmap.EffectMap(rows)
    assert m.target(0x46) == 544
    assert m.target(0x99) is None
    with pytest.raises(effectmap.EffectMapError, match="0x99"):
        m.check("test")


def test_mef_round_trips_an_mh4u_file_and_refuses_a_source_one():
    data = _mef(1)
    assert mef.to_mh4u(data, "mh4u") == data
    with pytest.raises(mef.MefError, match="can't become an MH4U MEF yet"):
        mef.to_mh4u(_esq(), "mh3u")
