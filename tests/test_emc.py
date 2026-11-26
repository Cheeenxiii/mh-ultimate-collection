"""The MH3U EMC converter: every instruction it changes is the one the games' tables say (specs/emc.md).

The byte strings here are hand-computed from the two games' arity rules, not from a round trip:
an opcode's arguments, a block's sub-code, a case value's width, and the 14 opcodes that gain an
argument in MH4U against the one that loses one.
"""
from __future__ import annotations

import struct

import pytest

from mhuc.formats import emc


def tables(gained: bool) -> bytes:
    """A 113/146-opcode synthetic length table: only the opcodes these tests use are set."""
    lens = bytearray(146)
    lens[0x00] = 2       # 00 cat num, a native action
    lens[0x02] = 1       # 02 ...
    lens[0x03] = 1       # an ordinary one-argument opcode, unchanged by the conversion
    lens[0x10] = 0       # no arguments
    lens[0x14] = 1       # 14 nn, runs action script nn
    lens[0x01] = 4 if gained else 3
    lens[0x1B] = 6 if gained else 5
    lens[0x0B] = 0x81 if gained else 0x80
    lens[0x11] = 0x81 if gained else 0x80
    lens[0x1D] = 0x82 if gained else 0x81
    lens[0x67] = 0x80 if gained else 0x81
    lens[0x70] = 0x81 if gained else 0x80
    return bytes(lens)


def emc_file(version: int, groups: list[list[bytes]], rows: int | None = None) -> bytes:
    """An EMC in the games' layout, rows defaulting to the version's group count."""
    rows = rows if rows is not None else (emc.GROUPS_MH3U if version == emc.VERSION_MH3U else emc.GROUPS_MH4U)
    out = bytearray(struct.pack("<4sIII", b"EMC\0", version, rows, 0)) + bytes(16 * rows)
    for g, scripts in enumerate(groups):
        table = len(out)
        struct.pack_into("<II", out, 0x10 + 16 * g, len(scripts), table)
        out += bytes(16 * len(scripts))
        for i, script in enumerate(scripts):
            struct.pack_into("<II", out, table + 16 * i, len(script), len(out))
            out += script + bytes(-len(script) % 16)
    return bytes(out)


def convert(groups: list[list[bytes]], src: bytes | None = None, dst: bytes | None = None) -> bytes:
    src = src if src is not None else tables(False)
    dst = dst if dst is not None else tables(True)
    return emc.convert(emc_file(emc.VERSION_MH3U, groups), src, dst)


def scripts(data: bytes) -> list[list[bytes]]:
    version, groups = emc.parse(data)
    assert version == emc.VERSION_MH4U
    return groups


def test_convert_adds_the_argument_after_the_subcode_and_before_a_linear_opcodes_arguments():
    """0x0b open gains a byte after its sub-code; 0x01 and 0x1b gain one before their arguments;
    a case value, the else and the end keep their shape; 0x67 loses its open argument."""
    source = (b"\x00\x03\x17"          # action 3/23
              b"\x01\xaa\xbb\xcc"      # 0x01 with three arguments
              b"\x1b\xa1\xa2\xa3\xa4\xa5"   # 0x1b with five
              b"\x0b\x00"              # a block open, no arguments
              b"\x0b\x01\x2a"          # a case, one-byte value
              b"\x0b\x02"              # else
              b"\x0b\xff"              # end
              b"\x1d\x00\x40"          # open, one argument
              b"\x1d\x02"
              b"\x67\x00\x00"          # 0x67 open, argument 0
              b"\x67\x02"
              b"\x14\x05"              # action script 5
              b"\xff")
    out = scripts(convert([[source]]))
    assert out[0][0] == (b"\x00\x03\x17"
                         b"\x01\x00\xaa\xbb\xcc"
                         b"\x1b\x00\xa1\xa2\xa3\xa4\xa5"
                         b"\x0b\x00\x00"
                         b"\x0b\x01\x2a"
                         b"\x0b\x02"
                         b"\x0b\xff"
                         b"\x1d\x00\x00\x40"
                         b"\x1d\x02"
                         b"\x67\x00"
                         b"\x67\x02"
                         b"\x14\x05"
                         b"\xff")


def test_convert_writes_23_group_rows_and_keeps_groups_0_to_12_in_order():
    groups = [[b"\x00\x01\x02\xff"], [b"\x14\x00\xff"], [b"\x10\xff"]]
    out = convert(groups)
    version, rows = emc.parse(out)
    assert version == emc.VERSION_MH4U
    assert len(rows) == 23
    assert [len(g) for g in rows] == [1, 1, 1] + [0] * 20
    assert rows[0][0] == b"\x00\x01\x02\xff"
    assert rows[1][0] == b"\x14\x00\xff"
    header = struct.unpack_from("<4sIII", out, 0)
    assert header == (b"EMC\0", emc.VERSION_MH4U, 23, 0)


def test_convert_refuses_the_opcode_whose_added_argument_is_unverified():
    with pytest.raises(emc.EmcError, match="0x70"):
        convert([[b"\x70\x00\xff"]])


def test_convert_refuses_a_0x67_argument_that_is_not_zero():
    with pytest.raises(emc.EmcError, match="only 0 converts"):
        convert([[b"\x67\x00\x17\xff"]])


def test_convert_refuses_a_source_that_is_not_mh3us():
    data = emc_file(emc.VERSION_MH4U, [[b"\x10\xff"]])
    with pytest.raises(emc.EmcError, match="not MH3U"):
        emc.convert(data, tables(True), tables(True))


def test_convert_refuses_a_source_with_the_wrong_group_count():
    data = emc_file(emc.VERSION_MH3U, [[b"\x10\xff"]], rows=12)
    with pytest.raises(emc.EmcError, match="13"):
        emc.convert(data, tables(False), tables(True))


def test_cut_refuses_a_script_without_an_end_marker_and_an_opcode_past_the_table():
    lens = tables(False)
    with pytest.raises(emc.EmcError, match="no .* end marker"):
        emc.cut(b"\x10", lens)
    with pytest.raises(emc.EmcError, match="past the"):
        emc.cut(b"\x10\x92\xff", lens)


def test_cut_refuses_an_instruction_that_runs_past_the_script():
    lens = tables(False)
    with pytest.raises(emc.EmcError, match="needs"):
        emc.cut(b"\x01\x00\xff", lens)


def test_lengths_reads_a_flat_code_image_and_refuses_a_short_one():
    code = bytearray(0x00B11325 - emc.CODE_BASE + 113)
    code[0x00B11325 - emc.CODE_BASE:] = bytes(range(1, 114))
    assert emc.lengths(bytes(code), "mh3u") == bytes(range(1, 114))
    with pytest.raises(emc.EmcError, match="too short"):
        emc.lengths(bytes(10), "mh4u")
