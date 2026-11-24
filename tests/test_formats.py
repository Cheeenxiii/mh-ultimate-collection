"""File formats: known values computed independently of the code, and bugs met on real files."""
from __future__ import annotations

import struct
import zlib

import pytest

from mhuc import monsterdata
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


def test_emd_attack_records_end_at_the_terminator_not_at_an_unpointed_block():
    """specs/emd.md word 28, check E10: with word 29 clear, the list's 0xFFFF record ends it; the data after it
    belongs to no header word and must not be read as records"""
    d = bytearray(0x200)
    d[:4] = b"etd\0"
    struct.pack_into("<I", d, 4 * 28, 0x80)                   # attack records at 0x80, word 29 = 0
    struct.pack_into("<H", d, 0x80 + 40 * 2, 0xFFFF)          # the third record is the terminator
    struct.pack_into("<I", d, 0x80 + 40 * 3, 0x12345678)      # unpointed block after it
    counts = emd.check_etd(bytes(d))
    assert counts["E10 etd attack lists"] == 1
    assert counts["E10 etd attack records"] == 2
    assert counts["E10 etd attack record 0 all zero"] == 1
    assert "E10 etd attack lists with no terminator" not in counts


def test_mhxx_attack_volume_whose_first_word_is_ffff_is_kept():
    """MHXX's HTS counts hold no closing record (only MH3U's do): a real record starting 0xFFFF stays"""
    record = b"\xff\xff" + bytes(46)
    d = struct.pack("<4sIII", b"HTS\0", 0x20131015, 1, 0) + struct.pack("<II", 1, 24) + record
    assert hitdata.groups(d) == (48, [[record]])


def test_mh3u_attack_record_maps_onto_the_mh4u_bytes_it_shares():
    """specs/hitdata.md HTD: bytes 0x00-0x11 stay, the volume group goes to 0x19, the count one more to 0x1a, the
    signed byte to 0x1d; the bytes with no MH4U counterpart stay zero"""
    record = bytearray(32)
    record[:0x12] = bytes(range(0x12))
    record[0x15] = 7
    record[0x16] = 3
    record[0x17] = 9
    record[0x18] = 0xFE
    out = monsterdata._htd_to_4u(bytes(record))
    assert out[:0x12] == bytes(range(0x12))
    assert (out[0x19], out[0x1A], out[0x1D]) == (7, 4, 0xFE)
    assert out[0x12:0x19] == bytes(7) and out[0x1B:0x1D] == bytes(2) and out[0x1E:] == bytes(40 - 0x1E)


def test_mh3u_empty_attack_record_stays_empty():
    assert monsterdata._htd_to_4u(bytes(32)) == bytes(40)


def test_htd_volume_group_must_be_below_the_hts_group_count():
    """check E8: an HTD record whose +0x15 indexes past the monster's HTS groups is counted, not accepted"""
    close = b"\xff\xff" + bytes(38)
    hts = struct.pack("<4sIII", b"HTS\0", 0x20110212, 2, 0)
    hts += struct.pack("<II", 2, 32) + struct.pack("<II", 1, 112) + bytes(40) + close + close
    inside, outside = bytearray(32), bytearray(32)
    inside[0x15], outside[0x15] = 1, 2
    htd = struct.pack("<4sIII", b"HTD\0", 0x20110209, 2, 0) + bytes(inside) + bytes(outside)
    counts = hitdata.check_htd(htd, hts)
    assert counts["E8 htd volume group below the HTS group count"] == 1
    assert counts["E8 htd volume group OUTSIDE"] == 1
