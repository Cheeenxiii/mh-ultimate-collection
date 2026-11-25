"""File formats: known values computed independently of the code, and bugs met on real files."""
from __future__ import annotations

import struct
import zlib

import pytest

from mhuc import monsterdata
from mhuc.formats import classid, emd, hitdata, lmt, pica, sound, stq


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


def lmt_with_track_buffer_at(buffer: int, version: int = 67) -> bytes:
    track_at = 0x10 + lmt.ANIM
    d = bytearray(track_at + lmt.TRACK)
    d[:8] = b"LMT\0" + struct.pack("<HH", version, 1)
    struct.pack_into("<I", d, 8, 0x10)                       # one animation at 0x10
    struct.pack_into("<IIii", d, 0x10, track_at, 1, 10, 0)   # one track
    struct.pack_into("<fII", d, track_at + 4, 1.0, 16, buffer)
    return bytes(d)


def test_lmt_reads_mh3us_version_66_with_the_version_67_layout():
    # RevilLib puts LMT 66 and 67 in one layout (src/mtf_lmt/animation.inl, bone_track.inl)
    assert lmt.read(lmt_with_track_buffer_at(0x10, version=66))[0] == 66


def test_lmt_refuses_a_version_it_does_not_lay_out():
    with pytest.raises(lmt.LmtError, match="version 68"):
        lmt.read(lmt_with_track_buffer_at(0x10, version=68))


def test_lmt_refuses_a_track_buffer_outside_the_file():
    d = lmt_with_track_buffer_at(0x10)
    assert lmt.read(d)[1][0].tracks[0].buffer == 0x10
    with pytest.raises(lmt.LmtError, match="outside the file"):
        lmt.read(lmt_with_track_buffer_at(len(d) - 8))


def key_track(buffer_type: int, buffer: bytes, bounds: int = 0) -> tuple[bytes, lmt.Track]:
    at = 0x10
    d = bytearray(at + len(buffer) + bounds)
    d[at:at + len(buffer)] = buffer
    return bytes(d), lmt.Track(buffer_type, 0, 0, 0, 1.0, len(buffer), at, at + len(buffer) if bounds else 0)


def test_lmt_decodes_each_uncompressed_key_type():
    """specs/lmt.md, "Keyframe buffers": hand-computed keys of types 1, 2 and 3"""
    buffer = struct.pack("<3f", 1.0, 2.0, 3.0) + struct.pack("<3f", 4.0, 5.0, 6.0)
    d, t = key_track(1, buffer)
    assert [(k.frame, k.value) for k in lmt.decode_keys(d, t, 67)] == \
        [(0, (1.0, 2.0, 3.0, 1.0)), (1, (4.0, 5.0, 6.0, 1.0))]

    d, t = key_track(2, struct.pack("<3f", 0.5, 0.5, 0.5))
    assert lmt.decode_keys(d, t, 67)[0].value == (0.5, 0.5, 0.5, 0.5)   # w from 1 - |xyz|^2

    d, t = key_track(3, struct.pack("<3fI", 1.0, 2.0, 3.0, 5) + struct.pack("<3fI", 4.0, 5.0, 6.0, 2))
    assert [(k.frame, k.value[:3]) for k in lmt.decode_keys(d, t, 67)] == \
        [(0, (1.0, 2.0, 3.0)), (5, (4.0, 5.0, 6.0))]


def test_lmt_decodes_each_normalized_key_type():
    """type 4 stores three u16 (1/0xFFFF each) and type 5 three u8 (1/0xFF), the last field the frame gap"""
    d, t = key_track(4, struct.pack("<3HH", 0xFFFF, 0x8000, 0, 4))
    (k,) = lmt.decode_keys(d, t, 67)
    assert k.value == (1.0, 0x8000 / 0xFFFF, 0.0, 1.0)
    assert lmt.decode_keys(b"", lmt.Track(4, 0, 0, 0, 1.0, 0, 0, 0), 67) == []   # no buffer size, no keys

    d, t = key_track(5, struct.pack("<3BB", 0xFF, 0x80, 0, 7))
    assert lmt.decode_keys(d, t, 67)[0].value == (1.0, 0x80 / 0xFF, 0.0, 1.0)


def test_lmt_decodes_each_packed_rotation_type():
    """types 6, 7 and 11 to 13, packed by hand: 14-bit signed magnitude, 7-bit unsigned, one axis plus w"""
    # type 6: w 0, z 0, y 0, x = -1 (raw 12288, the negative half), frame gap 3 in the top byte
    d, t = key_track(6, struct.pack("<Q", 12288 << 42 | 3 << 56))
    (k,) = lmt.decode_keys(d, t, 67)
    assert (k.frame, k.value) == (0, (-4095 / 4095.75, 0.0, 0.0, 0.0))
    d, t = key_track(6, struct.pack("<Q", 4096 << 42))              # the positive half: raw / 4095.75
    assert lmt.decode_keys(d, t, 67)[0].value[0] == 4096 / 4095.75

    # type 7: x = 64/127, w = 1, and a frame gap of 5 in the top nibble
    d, t = key_track(7, struct.pack("<I", 64 << 21 | 0x7F | 5 << 28))
    assert [(k.frame, k.value) for k in lmt.decode_keys(d, t, 67)] == [(0, (64 / 127, 0.0, 0.0, 1.0))]

    # types 11 to 13: the low 14 bits are the named axis, the next 14 are w, the top nibble the frame gap
    for buffer_type, axis in ((11, 0), (12, 1), (13, 2)):
        d, t = key_track(buffer_type, struct.pack("<I", 0x3FFF | 0x3FFF << 14 | 2 << 28))
        (k,) = lmt.decode_keys(d, t, 67)
        assert (k.frame, k.value) == (0, tuple(1.0 if i in (axis, 3) else 0.0 for i in range(4))), buffer_type

    # version 66 reads the same pair as signed magnitude (as type 6 does); version 67 as unsigned
    d, t = key_track(11, struct.pack("<I", 12288))
    assert lmt.decode_keys(d, t, 66)[0].value == (-4095 / 4095.75, 0.0, 0.0, 0.0)
    assert lmt.decode_keys(d, t, 67)[0].value == (12288 / 0x3FFF, 0.0, 0.0, 0.0)


def test_lmt_key_frames_accumulate_and_must_stay_inside_the_animation():
    d, t = key_track(3, struct.pack("<3fI", 0.0, 0.0, 0.0, 4) + struct.pack("<3fI", 0.0, 0.0, 0.0, 4))
    assert [k.frame for k in lmt.decode_keys(d, t, 67, frames=9)] == [0, 4]
    with pytest.raises(lmt.LmtError, match="past the animation"):
        lmt.decode_keys(d, t, 67, frames=4)


def test_lmt_refuses_a_key_buffer_it_cannot_split_into_keys():
    d, t = key_track(1, struct.pack("<3f", 1.0, 2.0, 3.0) + b"\0" * 4)
    with pytest.raises(lmt.LmtError, match="whole number of SingleVector3 keys"):
        lmt.decode_keys(d, t, 67)
    d, t = key_track(8, b"\0" * 12)
    with pytest.raises(lmt.LmtError, match="type 8"):
        lmt.decode_keys(d, t, 67)


def test_lmt_bounds_block_is_scale_then_offset():
    """specs/lmt.md: RevilLib applies the block as offset + scale x value, so its first vector scales"""
    buffer = b"\0" * 4
    d, t = key_track(5, buffer, bounds=0x20)
    d = bytearray(d)
    struct.pack_into("<4f", d, 0x14, 2.0, 2.0, 2.0, 2.0)      # scale
    struct.pack_into("<4f", d, 0x24, -1.0, -1.0, -1.0, -1.0)  # offset
    assert lmt.bounds(bytes(d), t) == ((2.0, 2.0, 2.0, 2.0), (-1.0, -1.0, -1.0, -1.0))


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


def test_etd_part_kinds_count_the_eighth_byte_of_each_part_record():
    """specs/emd.md word 5, check E13: MH4U's 0x936904 reads each part record's kind at +8; the check counts 0..4"""
    d = bytearray(0x100)
    d[:4] = b"etd\0"
    struct.pack_into("<I", d, 4 * 5, 0x80)                    # the part table at 0x80, 8 x 10 bytes
    kinds = (0, 1, 2, 3, 4, 0, 1, 2)
    for i, kind in enumerate(kinds):
        struct.pack_into("<H", d, 0x80 + 10 * i + 8, kind)
    assert emd.part_kinds(bytes(d)) == list(kinds)
    counts = emd.check_etd(bytes(d))
    assert counts["E13 etd parts"] == 8
    assert counts["E13 etd part kind 0"] == 2
    assert counts["E13 etd part kind 4"] == 1
    assert "E13 etd part kind above 4" not in counts


def test_etd_part_table_outside_the_file_is_counted_not_read():
    """specs/emd.md word 5, check E13: a table word that leaves fewer than 80 bytes is missing, not read"""
    d = bytearray(0x100)
    d[:4] = b"etd\0"
    struct.pack_into("<I", d, 4 * 5, 0xFC)
    assert emd.part_kinds(bytes(d)) is None
    assert emd.check_etd(bytes(d))["E13 etd part table missing or short"] == 1


def test_emd_word_35_records_end_at_the_minus_one_record_and_count_the_sever_ones():
    """specs/emd.md word 35, checks E11 and E12: kinds 0/3/5 are the severs; the index, limit, a and b are counted"""
    d = bytearray(0x140)
    d[:4] = b"emd\0"
    struct.pack_into("<I", d, 4 * 35, 0xC0)                                # after the 0xB8 header
    struct.pack_into("<iIIIII", d, 0xC0, 4, 4, 0, 0, 255, 0)               # a dtbparts joint record
    struct.pack_into("<iIIIII", d, 0xD8, 255, 0, 0, 0xFFFFFFFF, 0, 0)      # the (255, 0, 0, -1) marker
    struct.pack_into("<iIIIII", d, 0xF0, 143, 0, 1, 143, 0, 0)             # a kind-0 sever record
    struct.pack_into("<iIIIII", d, 0x108, -1, 0, 0, 0, 255, 0)             # the terminator
    recs = emd.joint_records(bytes(d))
    assert recs is not None, "word 35's list must end at its -1 record"
    assert [r[0] for r in recs] == [4, 255, 143, -1]
    counts = emd.check_emd(bytes(d))
    assert counts["E11 emd sever records"] == 1
    assert counts["E11 emd sever kind 0 joint 143"] == 1
    assert counts["E11 emd files with the (255, 0, 0, -1) marker"] == 1
    assert counts["E12 emd sever index 1"] == 1
    assert counts["E12 emd sever limit is the joint"] == 1
    assert counts["E12 emd sever a is 0"] == 1
    assert counts["E12 emd sever b is 0"] == 1


def test_emd_counts_every_sever_kind_and_the_block_a_sever_record_b_points_at():
    """specs/emd.md, checks E11 and E12: a kind-5 sever counts, and E12 follows the loader's b relocation:
    b inside the file, and the six u32 there inside it with three nonzero"""
    d = bytearray(0x300)
    d[:4] = b"emd\0"
    struct.pack_into("<I", d, 4 * 35, 0xC0)
    struct.pack_into("<iIIIII", d, 0xC0, 200, 5, 1, 200, 0, 0x2A0)         # a cut-type-3 sever, b -> 0x2A0
    struct.pack_into("<iIIIII", d, 0xD8, -1, 0, 0, 0, 255, 0)
    struct.pack_into("<6I", d, 0x2A0, 0x2C0, 0x2C4, 0x2C8, 0, 0, 0)       # the block: three offsets, three zeros
    counts = emd.check_emd(bytes(d))
    assert counts["E11 emd sever records"] == 1
    assert counts["E11 emd sever kind 5 joint 200"] == 1
    assert counts["E12 emd sever b inside the file"] == 1
    assert counts["E12 emd sever b block inside the file"] == 1
    assert counts["E12 emd sever b block with 3 nonzero words"] == 1
    assert "E12 emd sever b OUTSIDE the file" not in counts


def test_emd_counts_a_word_35_list_that_runs_off_the_end_instead_of_crashing():
    d = bytearray(0xC8)
    d[:4] = b"emd\0"
    struct.pack_into("<I", d, 4 * 35, 0xC0)                                # 24 bytes don't fit after 0xC0
    assert emd.joint_records(bytes(d)) is None
    assert emd.check_emd(bytes(d))["E1 emd word 35 list doesn't end"] == 1


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


def stq_with_stream(name: str = "sound\\bgm\\test", version: int = 0x22) -> bytes:
    """A hand-built STRQ: one stream, one sequence, then the stream's name."""
    stream_at, sequence_at = 0x18, 0x18 + 36
    name_at = sequence_at + 100
    d = bytearray(name_at + len(name) + 1)
    struct.pack_into("<4s5I", d, 0, b"STRQ", version, 1, 1, stream_at, sequence_at)
    struct.pack_into("<9I", d, stream_at, name_at, 0x1234, 0x1000, 2, 32728, 0, 0, 0x67195A2E, 2)
    struct.pack_into("<I", d, sequence_at, 7)
    struct.pack_into("<f", d, sequence_at + 0x24, -0.9)
    struct.pack_into("<I", d, sequence_at + 0x5C, 0)
    d[name_at:name_at + len(name)] = name.encode()
    return bytes(d)


def test_stq_reads_a_hand_built_stream_request():
    """specs/sound.md stream request: header 0x18, stream record 36 at 0x18, sequence record 100, then the names"""
    s = stq.read(stq_with_stream())
    assert [(x.name, x.size, x.samples, x.channels, x.rate, x.loop_start, x.loop_end, x.type_id, x.unknown_20)
            for x in s.streams] == [("sound\\bgm\\test", 0x1234, 0x1000, 2, 32728, 0, 0, 0x67195A2E, 2)]
    assert s.sequences[0].id == 7
    assert s.sequences[0].level == pytest.approx(-0.9)
    assert s.sequences[0].stream == 0


def test_stq_reads_mh3us_version_0x20_with_the_same_layout():
    """specs/sound.md stream request: MH3U's 0x20 closes exactly as MH4U's 0x22 does (check SN6)"""
    s = stq.read(stq_with_stream(version=0x20))
    assert (s.version, s.streams[0].name, s.sequences[0].id) == (0x20, "sound\\bgm\\test", 7)


def test_stq_refuses_a_stream_request_version_it_does_not_lay_out():
    with pytest.raises(stq.StqError, match="version 0x21"):
        stq.read(stq_with_stream(version=0x21))


def test_stq_refuses_a_sequence_naming_a_stream_past_the_table():
    d = bytearray(stq_with_stream())
    struct.pack_into("<I", d, 0x18 + 36 + 0x5C, 1)
    with pytest.raises(stq.StqError, match="stream 1 of 1"):
        stq.read(bytes(d))


def test_stq_refuses_names_that_do_not_fill_the_file():
    d = bytearray(stq_with_stream())
    struct.pack_into("<I", d, 0x18, 0x18 + 36 + 100 + 1)     # name offset one past the first name
    with pytest.raises(stq.StqError, match="name at"):
        stq.read(bytes(d))


def test_stq_refuses_a_sequence_table_that_does_not_follow_the_stream_table():
    d = bytearray(stq_with_stream())
    struct.pack_into("<I", d, 0x14, 0x18 + 36 + 1)
    with pytest.raises(stq.StqError, match="sequence table at"):
        stq.read(bytes(d))


def wave(version: int = 4, channels: int = 1, seek: int = 0, offset: int | None = None,
         data_size: int = 0x100) -> bytes:
    """A hand-built MADP: samples and rate 8000 so the length is 1.0 s, then the data and seek table."""
    header = 0x2C + sound.WAVE_BLOCK * channels if version == 4 else 0x60
    d = bytearray((offset if offset is not None else header) + data_size + 20 * seek)
    struct.pack_into("<4sI4B", d, 0, b"MADP", version, channels, 0, 0, 1)
    struct.pack_into("<6I", d, 0x0C, 8000, 8000, 0, 0, offset if offset is not None else header, data_size)
    struct.pack_into("<f", d, 0x24, 1.0)
    if version == 4:
        struct.pack_into("<I", d, 0x28, 0x33480000 | seek)
    else:
        struct.pack_into("<II", d, 0x28, 0, 0x60)
    return bytes(d)


def test_sound_reads_mh3us_madp_version_4_and_its_seek_table():
    """specs/sound.md wave version 4: data offset 0x2C + 0x30 per channel, the seek count in 0x28's
    low half, and the seek table's 20-byte entries after the data"""
    w = sound.read_wave(wave(seek=2))
    assert (w.version, w.channels, w.samples, w.rate, w.data_offset, w.data_size) == (4, 1, 8000, 8000, 0x5C, 0x100)
    assert w.seconds == pytest.approx(1.0)
    assert (w.seek_count, w.trailing) == (2, 40)
    assert sound.read_wave(wave(channels=2)).data_offset == 0x8C


def test_sound_refuses_a_madp_version_4_offset_that_does_not_follow_the_channels():
    with pytest.raises(sound.SoundError, match=r"data at 0x5c, expected 0x8c for 2 channels"):
        sound.read_wave(wave(channels=2, offset=0x5C))


def test_sound_reads_an_empty_placeholder_wave():
    """one MH3U wave is a placeholder with no samples and no data (em045's blank voice)"""
    assert sound.read_wave(wave(data_size=0)).data_size == 0


def test_sound_refuses_a_seek_count_that_does_not_match_the_bytes_after_the_data():
    """the seek count is the only record of the table's length, so the file's size must confirm it"""
    d = bytearray(wave(seek=1))
    struct.pack_into("<I", d, 0x28, 0x33480000 | 2)
    with pytest.raises(sound.SoundError, match="20 bytes after the data for 2 seek entries"):
        sound.read_wave(bytes(d))


def test_sound_reads_mh4us_madp_version_5_mono_and_refuses_the_stereo_music_layout():
    """MH4U's mono effects put the data at 0x60; version 5's stereo music keeps a seek table in
    the header, which this reader doesn't lay out (specs/sound.md, "Wave")"""
    assert sound.read_wave(wave(version=5)).data_offset == 0x60
    d = bytearray(wave(version=5, channels=2, offset=0x60, data_size=0x100))
    d[8] = 2
    with pytest.raises(sound.SoundError, match="stereo"):
        sound.read_wave(bytes(d))


def bank(version: int = 10, tail: int = 1) -> bytes:
    """A hand-built SNDB: one group, two wave entries, then one {f32, u32} tail record per word 0x10."""
    groups, names = [(0, 0x8000 | 2, 0, 0)], ["sound\\se\\em\\em001\\wav\\a", "sound\\se\\em\\em001\\wav\\b"]
    d = bytearray(struct.pack("<4s4I", b"SNDB", version, len(groups), len(names), tail))
    for g in groups:
        d += struct.pack("<HHII", *g)
    for name in names:
        d += name.encode() + b"\0" + struct.pack("<I", 0x67195A2E) + bytes(sound.BANK_PARAMS)
    for i in range(tail):
        d += struct.pack("<fI", 0.5, i)
    return bytes(d)


def test_sound_reads_mh3us_sndb_version_10():
    """specs/sound.md bank version 10: header 0x14, 12-byte group records, entries of a NUL path,
    a type id and 76 parameter bytes, then 8 × 0x10's value tail records"""
    b = sound.read_bank(bank())
    assert (b.version, len(b.groups), len(b.entries), len(b.tail)) == (10, 1, 2, 1)
    assert b.groups[0] == sound.BankGroup(id=0, flags=0x8002, first=0, x=0)
    assert [(e.name, e.type_id, len(e.params)) for e in b.entries] == \
        [("sound\\se\\em\\em001\\wav\\a", 0x67195A2E, 76), ("sound\\se\\em\\em001\\wav\\b", 0x67195A2E, 76)]
    assert b.tail == ((0.5, 0),)


def test_sound_refuses_a_bank_tail_that_does_not_end_the_file():
    d = bytearray(bank())
    struct.pack_into("<I", d, 0x10, 2)
    with pytest.raises(sound.SoundError, match="tail of 2 records"):
        sound.read_bank(bytes(d))


def test_sound_refuses_a_bank_group_whose_first_entry_is_past_the_entries():
    d = bytearray(bank())
    struct.pack_into("<I", d, sound.BANK_HEADER + 4, 3)
    with pytest.raises(sound.SoundError, match="first entry 3 of 2"):
        sound.read_bank(bytes(d))


def request(version: int = 6, records: int = 2) -> bytes:
    """A hand-built SREQ: request ids 0 and 1, both naming bank 0, then the one bank's path."""
    banks = ["sound\\se\\em\\em001\\snd_em001"]
    strings_at = sound.REQUEST_HEADER + sound.REQUEST_RECORD * records
    names_at = strings_at + 4 * len(banks)
    d = bytearray(names_at + len(banks[0]) + 1)
    struct.pack_into("<4s3I", d, 0, b"SREQ", version, records, strings_at)
    for i in range(records):
        words = [0] * sound.REQUEST_WORDS
        words[0], words[21] = 0x7F010000 | i, 0
        struct.pack_into(f"<{sound.REQUEST_WORDS}I", d, sound.REQUEST_HEADER + sound.REQUEST_RECORD * i, *words)
    struct.pack_into("<I", d, strings_at, names_at)
    d[names_at:names_at + len(banks[0])] = banks[0].encode()
    return bytes(d)


def test_sound_reads_mh3us_sreq_version_6():
    """specs/sound.md request version 6: header 0x10, 92-byte records, then one offset per bank and the
    NUL-terminated bank paths; word 0's low half is the request id and word 0x54 the bank index"""
    r = sound.read_request(request())
    assert (r.version, len(r.records), r.banks) == (6, 2, ("sound\\se\\em\\em001\\snd_em001",))
    assert [(x.id, x.bank) for x in r.records] == [(0, 0), (1, 0)]


def test_sound_refuses_a_request_record_naming_a_bank_past_the_string_table():
    d = bytearray(request())
    struct.pack_into("<I", d, sound.REQUEST_HEADER + sound.REQUEST_RECORD + 0x54, 1)
    with pytest.raises(sound.SoundError, match="record 1: bank 1 of 1"):
        sound.read_request(bytes(d))


def test_sound_refuses_a_request_string_table_that_does_not_follow_the_records():
    d = bytearray(request())
    struct.pack_into("<I", d, 0x0C, sound.REQUEST_HEADER + sound.REQUEST_RECORD + 4)
    with pytest.raises(sound.SoundError, match="string table at"):
        sound.read_request(bytes(d))
