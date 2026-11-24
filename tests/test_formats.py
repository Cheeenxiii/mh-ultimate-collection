"""File formats: known values computed independently of the code, and bugs met on real files."""
from __future__ import annotations

import struct
import zlib

import pytest

from mhuc.formats import classid, emd, hitdata, lmt, pica


def test_class_id_is_crc32_without_final_inversion_on_31_bits():
    expected = (zlib.crc32(b"rTexture") ^ 0xFFFFFFFF) & 0x7FFFFFFF
    assert classid.class_id("rTexture") == expected
    assert classid.extension_of(expected) == "tex"


def etc1_word(info: int, selectors: int = 0) -> int:
    return info << 32 | selectors


def test_etc1_individual_block_matches_hand_decoding():
    # both base colours 4-bit 8 (0x88), modifier table 0 (2, 8)
    info = (8 << 28) | (8 << 24) | (8 << 20) | (8 << 16) | (8 << 12) | (8 << 8)
    assert pica._etc1_decode_block(etc1_word(info)) == [(0x8A, 0x8A, 0x8A)] * 16   # selector 0: +2
    pixel5_selector3 = (1 << 5) | (1 << 21)                                       # -8
    assert pica._etc1_decode_block(etc1_word(info, pixel5_selector3))[5] == (0x80, 0x80, 0x80)


def test_etc1_differential_block_matches_hand_decoding():
    # base 5-bit 16 (0x84), delta -1 for the second half (15, 0x7B), table 0, no flip
    info = 2 | (16 << 27) | (16 << 19) | (16 << 11) | (7 << 24) | (7 << 16) | (7 << 8)
    colours = pica._etc1_decode_block(etc1_word(info))
    assert colours[0] == (0x86, 0x86, 0x86)     # first half (x < 2), +2
    assert colours[8] == (0x7D, 0x7D, 0x7D)     # second half (x >= 2), +2


def lmt_with_track_buffer_at(buffer: int) -> bytes:
    track_at = 0x10 + lmt.ANIM
    d = bytearray(track_at + lmt.TRACK)
    d[:8] = b"LMT\0" + struct.pack("<HH", 67, 1)
    struct.pack_into("<I", d, 8, 0x10)                       # one animation at 0x10
    struct.pack_into("<IIii", d, 0x10, track_at, 1, 10, 0)   # one track
    struct.pack_into("<fII", d, track_at + 4, 1.0, 16, buffer)
    return bytes(d)


def test_lmt_refuses_a_track_buffer_outside_the_file():
    d = lmt_with_track_buffer_at(0x10)
    assert lmt.read(d)[1][0].tracks[0].buffer == 0x10
    with pytest.raises(lmt.LmtError, match="outside the file"):
        lmt.read(lmt_with_track_buffer_at(len(d) - 8))


def test_emd_counts_a_body_list_that_runs_off_the_end_instead_of_crashing():
    d = bytearray(0x200)
    d[:4] = b"emd\0"
    struct.pack_into("<I", d, 4 * 8, 0x1F0)                  # body list, no 0xFFFF before the end
    counts = emd.check_emd(bytes(d))
    assert counts["E1 emd word 8 list doesn't end"] == 1


def test_mhxx_attack_volume_whose_first_word_is_ffff_is_kept():
    """MHXX's HTS counts hold no closing record (only MH3U's do): a real record starting 0xFFFF stays"""
    record = b"\xff\xff" + bytes(46)
    d = struct.pack("<4sIII", b"HTS\0", 0x20131015, 1, 0) + struct.pack("<II", 1, 24) + record
    assert hitdata.groups(d) == (48, [[record]])
