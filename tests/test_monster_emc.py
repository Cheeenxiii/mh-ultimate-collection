"""reference/monster_emc.py: what makes an action AI-picked must not drift.

The EMC bytecode is MHGU Definitive Edition's heuristic, so the reader is pinned on a hand-built
script: the native-action opcode, the branch skip, and the category bound.
"""
from __future__ import annotations

import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_emc  # noqa: E402


def emc(version: int, groups: list[list[bytes]]) -> bytes:
    """An EMC in the games' layout: header, group tables, each group's script table and scripts."""
    out = bytearray(struct.pack("<4sIII", b"EMC\0", version, len(groups), 0)) + bytes(16 * len(groups))
    for g, scripts in enumerate(groups):
        table = len(out)
        struct.pack_into("<II", out, 0x10 + 16 * g, len(scripts), table)
        out += bytes(16 * len(scripts))
        for i, script in enumerate(scripts):
            struct.pack_into("<II", out, table + 16 * i, len(script), len(out))
            out += script + bytes(-len(script) % 16)
    return bytes(out)


def test_emc_reads_native_actions_and_skips_branches():
    data = emc(0x20120804, [
        [b"\x00\x03\x17\x14\x01"],                    # action 3/23, then action script 1
        [b"\x02\x01\x40\x00\x08\x00"],                # a weighted branch, then action 8/0
        [b"\x00\x0e\x05"],                            # category 14: not a native-action opcode
    ])
    version, groups = monster_emc.parse(data)
    assert version == 0x20120804
    assert [len(g) for g in groups] == [1, 1, 1]
    assert monster_emc.actions(data) == {(3, 23), (8, 0)}


def test_emc_cuts_scripts_with_the_length_table():
    """The arity rules: an opcode's argument count, and a block's sub-code and value width."""
    lens = bytearray(0x42)
    lens[0x00] = 2       # 00 cat num
    lens[0x10] = 0       # no arguments
    lens[0x40] = 0x81    # a block opener with one argument
    lens[0x41] = 0x90    # a case block whose value is two bytes
    script = (b"\x00\x03\x17"          # action 3/23
              b"\x10"                  # one byte
              b"\x40\x00\x05"          # block opener, sub-code 0, one argument
              b"\x40\x01\x2a"          # case, sub-code 1, one-byte value
              b"\x41\x01\x2a\x2b"      # case, sub-code 1, two-byte value
              b"\x40\x02"              # else
              b"\x40\xff"              # block end
              b"\xff")                 # the script's end marker
    cut, rest = monster_emc.tokens(script, bytes(lens))
    assert rest == b""
    assert cut == [b"\x00\x03\x17", b"\x10", b"\x40\x00\x05", b"\x40\x01\x2a",
                   b"\x41\x01\x2a\x2b", b"\x40\x02", b"\x40\xff"]


def test_emc_reports_a_script_that_does_not_cut_cleanly():
    lens = bytearray(0x42)
    lens[0x00] = 2
    lens[0x10] = 0
    # 0x00 needs two arguments and has none; 0x50 is past the table.
    assert monster_emc.tokens(b"\x10\x00", bytes(lens))[1] == b"\x00"
    assert monster_emc.tokens(b"\x10\x50\xff", bytes(lens))[1] == b"\x50\xff"


def test_emc_rejects_a_script_past_the_file():
    data = bytearray(emc(0x20110601, [[b"\x00\x01\x02"]]))
    table = struct.unpack_from("<I", data, 0x14)[0]    # group 0's script table
    struct.pack_into("<I", data, table + 4, len(data))  # script 0's offset points past the file
    try:
        monster_emc.parse(bytes(data))
    except ValueError as e:
        assert "past the file" in str(e)
    else:
        raise AssertionError("a script outside the file must be refused")
