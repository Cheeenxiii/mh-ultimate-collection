"""File formats: known values computed independently of the code, and bugs met on real files."""
from __future__ import annotations

import json
import os
import struct
import zlib

import pytest

from mhuc import cli, monsterdata
from mhuc.formats import camera, classid, emd, hitdata, lmd, lmt, lyt, pica, sound, stq, xfs


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


def lmt_with_float_tracks() -> bytes:
    """One animation whose +0x38 names a float-track block, laid out from RevilLib's float_track.inl and .hpp:
    four FloatTrack records, then group 0's two FloatFrames. No game file carries this block (check L5)."""
    floats_at = 0x10 + lmt.ANIM
    keys_at = floats_at + lmt.FLOAT_TRACK * lmt.FLOAT_GROUPS
    d = bytearray(keys_at + 2 * lmt.FLOAT_KEY)
    d[:8] = b"LMT\0" + struct.pack("<HH", 67, 1)
    struct.pack_into("<I", d, 8, 0x10)                                 # one animation at 0x10
    struct.pack_into("<IIii", d, 0x10, 0, 0, 10, -1)                   # no tracks
    struct.pack_into("<I", d, 0x10 + 0x30, 0x800000)                  # flags, as every animation has
    struct.pack_into("<I", d, 0x10 + 0x38, floats_at)                 # float-track block
    struct.pack_into("<4BII", d, floats_at, 0, 1, 2, 3, 2, keys_at)   # group 0: remaps, 2 keys, their offset
    struct.pack_into("<4BII", d, floats_at + lmt.FLOAT_TRACK, 0, 0, 0, 0, 0, 0)        # groups 1 to 3 empty
    struct.pack_into("<I", d, floats_at + 2 * lmt.FLOAT_TRACK, 0)
    struct.pack_into("<I", d, floats_at + 3 * lmt.FLOAT_TRACK, 0)
    struct.pack_into("<Ifff", d, keys_at, 0xCD000003, 1.5, -2.0, 0.25)   # 3 components, frame 0, pad 0xCD
    struct.pack_into("<Ifff", d, keys_at + lmt.FLOAT_KEY, 0xCD000501, 0.0, 0.0, 1.0)   # 1 component, frame 5
    return bytes(d)


def test_lmt_reads_the_float_track_block():
    """specs/lmt.md, "Float-track block": the animation's four groups and their keys, values computed by hand from
    RevilLib's float_track.inl (remaps, key count, frames offset) and float_track.hpp (FloatFrame)."""
    _version, (a,) = lmt.read(lmt_with_float_tracks())
    assert a is not None and a.floats is not None
    assert [t.remaps for t in a.floats] == [(0, 1, 2, 3), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]
    assert [t.frames for t in a.floats][0] != 0
    assert all(t.frames == 0 for t in a.floats[1:])
    assert a.floats[0].keys == [lmt.FloatKey(3, 0, (1.5, -2.0, 0.25)), lmt.FloatKey(1, 5, (0.0, 0.0, 1.0))]
    assert all(t.keys == [] for t in a.floats[1:])
    assert lmt.read(lmt_with_track_buffer_at(0x10))[1][0].floats is None   # +0x38 = 0: no block


def test_lmt_refuses_a_float_track_block_outside_the_file():
    d = bytearray(lmt_with_float_tracks())
    struct.pack_into("<I", d, 0x10 + 0x38, len(d) - 0x10)
    with pytest.raises(lmt.LmtError, match="outside the file"):
        lmt.read(bytes(d))


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


def camera_v4_with_one_track() -> bytes:
    """A hand-built MH4U camera list: one camera whose first track is one type 4 key."""
    data_start = camera.FIRST_RECORD + camera.RECORD_SIZE[camera.VERSION_MH4U]
    d = bytearray(camera.MAGIC + struct.pack("<HH", camera.VERSION_MH4U, 256) + bytes(4 * 256))
    d += bytes(camera.RECORD_SIZE[camera.VERSION_MH4U])
    d += bytes(8 + camera.BOUNDS_SIZE)                                   # keys and bounds
    struct.pack_into("<I", d, camera.TABLE, camera.FIRST_RECORD)
    struct.pack_into("<I", d, camera.FIRST_RECORD + 0x10, 1)              # frame count
    track = camera.FIRST_RECORD + camera.TRACK_OFFSETS[0]
    d[track:track + 4] = bytes((4, 1, 0, 0))                             # type 4, local position
    struct.pack_into("<fII", d, track + 4, 0.0, 8, data_start)           # weight, key size, key offset
    struct.pack_into("<4f", d, track + 0x10, 1.0, 2.0, 3.0, 0.0)        # reference
    struct.pack_into("<I", d, track + camera.TRACK_BOUNDS, data_start + 8)
    struct.pack_into("<8f", d, data_start + 8, 1.0, 2.0, 3.0, 0.0, 4.0, 5.0, 6.0, 0.0)
    struct.pack_into("<4H", d, data_start, 0, 0x8000, 0xFFFF, 0)        # one key, no gap: frames-1 = 0
    return bytes(d)


def test_a_camera_list_converts_to_version_5_and_back_with_its_offsets():
    v4 = camera_v4_with_one_track()
    v5 = camera.to_mhxx(v4)
    data_start5 = camera.FIRST_RECORD + camera.RECORD_SIZE[camera.VERSION_MHXX]
    assert v5[:8] == camera.MAGIC + struct.pack("<HH", camera.VERSION_MHXX, 256)
    assert struct.unpack_from("<I", v5, camera.TABLE)[0] == camera.FIRST_RECORD
    assert v5[camera.FIRST_RECORD:camera.FIRST_RECORD + 16] == bytes(16)
    track5 = camera.FIRST_RECORD + 16 + camera.TRACK_OFFSETS[0]
    assert struct.unpack_from("<I", v5, track5 + camera.TRACK_KEY)[0] == data_start5
    assert struct.unpack_from("<I", v5, track5 + camera.TRACK_BOUNDS)[0] == data_start5 + 8
    assert len(v5) == data_start5 + 8 + camera.BOUNDS_SIZE
    assert camera.from_mhxx(v5) == v4


def test_the_camera_converter_writes_mh4us_layout(tmp_path):
    source = tmp_path / "e001_cam_mhxx.lcm"
    source.write_bytes(camera.to_mhxx(camera_v4_with_one_track()))
    out = tmp_path / "e001_cam.lcm"
    assert cli.main(["convert", "camera", str(source), "--from", "mhxx", "-o", str(out)]) == 0
    assert out.read_bytes() == camera_v4_with_one_track()


def test_the_camera_converter_re_lays_mh4us_own_file(tmp_path):
    source = tmp_path / "e001_cam.lcm"
    source.write_bytes(camera_v4_with_one_track())
    out = tmp_path / "e001_cam_re.lcm"
    assert cli.main(["convert", "camera", str(source), "--from", "mh4u", "-o", str(out)]) == 0
    assert out.read_bytes() == source.read_bytes()


def test_the_camera_converter_refuses_mh3u_which_has_no_camera_list(tmp_path):
    source = tmp_path / "e001_cam.lcm"
    source.write_bytes(camera_v4_with_one_track())
    assert cli.main(["convert", "camera", str(source), "--from", "mh3u", "-o", str(tmp_path / "x.lcm")]) == 1


def test_the_camera_converter_refuses_a_version_that_is_not_its_source(tmp_path):
    source = tmp_path / "e001_cam_mhxx.lcm"
    source.write_bytes(camera.to_mhxx(camera_v4_with_one_track()))
    assert cli.main(["convert", "camera", str(source), "--from", "mh4u", "-o", str(tmp_path / "x.lcm")]) == 1


def test_the_camera_converter_refuses_to_write_in_the_repository(tmp_path):
    source = tmp_path / "e001_cam.lcm"
    source.write_bytes(camera_v4_with_one_track())
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(repo, "e001_cam.lcm")
    assert cli.main(["convert", "camera", str(source), "--from", "mh4u", "-o", out]) == 2
    assert not os.path.exists(out)


def test_camera_read_refuses_a_record_that_is_not_contiguous():
    v4 = bytearray(camera_v4_with_one_track())
    struct.pack_into("<I", v4, camera.TABLE, camera.FIRST_RECORD + 4)
    with pytest.raises(camera.CameraError, match="contiguous"):
        camera.read(bytes(v4))


def test_camera_read_refuses_an_mhxx_prefix_that_is_not_zero():
    v5 = bytearray(camera.to_mhxx(camera_v4_with_one_track()))
    v5[camera.FIRST_RECORD] = 1
    with pytest.raises(camera.CameraError, match="prefix"):
        camera.read(bytes(v5))

def lmt_version_66_to_convert() -> bytes:
    """One animation with a type 11 track (two hand-made signed keys), a type 3 track and one event."""
    tracks, buffers, events = 0x50, 0x98, 0xB0
    d = bytearray(0x1D8)
    d[:8] = b"LMT\0" + struct.pack("<HH", 66, 1)
    struct.pack_into("<I", d, 8, 0x10)
    struct.pack_into("<IIii", d, 0x10, tracks, 2, 10, -1)
    struct.pack_into("<II", d, 0x10 + 0x30, 0x00800000, events)
    # type 11, bone 5: x = +1 and -1 as version 66's signed magnitude (raw 4096 and 12287), w = 0 (0x3FFF)
    struct.pack_into("<4BfII", d, tracks, 11, 0, 0, 5, 1.0, 8, buffers)
    struct.pack_into("<I", d, buffers, 4096 | 5 << 28)         # x +1.0, w 0.0; the next key is 5 frames on
    struct.pack_into("<I", d, buffers + 4, 12287 | 0x3FFF << 14)
    # type 3, bone 0: a position key that conversion must carry untouched
    struct.pack_into("<4BfII", d, tracks + lmt.TRACK, 3, 1, 0, 0, 1.0, 16, buffers + 8)
    struct.pack_into("<3fI", d, buffers + 8, 1.5, -2.0, 3.0, 9)
    struct.pack_into("<II", d, events + 0x40, 1, 0x1D0)       # one event, its list after the block
    struct.pack_into("<II", d, 0x1D0, 0x1234, 3)
    return bytes(d)


def test_lmt_convert_reencodes_version_66s_rotation_keys_as_version_67s_unsigned_form():
    """specs/lmt.md, "Keyframe buffers": version 66 stores types 11 to 13 signed and version 67 unsigned behind a
    bounds block, so a converted list must decode to the same quaternions and keep the frames"""
    out = lmt.convert(lmt_version_66_to_convert())
    assert lmt.read(out)[0] == 67
    animation = lmt.read(out)[1][0]
    rotation, position = animation.tracks
    keys = lmt.decode_keys(out, rotation, 67, animation.frames)
    scale, offset = lmt.bounds(out, rotation)
    assert [k.frame for k in keys] == [0, 5]
    for key, (x, w) in zip(keys, [(1.0, 0.0), ((12287 - 0x3FFF) / 4095.75, 0.0)], strict=True):
        assert abs(offset[0] + scale[0] * key.value[0] - x) < 1e-4
        assert abs(offset[3] + scale[3] * key.value[3] - w) < 1e-4
    # the other track's keys are the source's bytes, unchanged, and the event block is carried
    assert lmt.decode_keys(out, position, 67)[0].value == (1.5, -2.0, 3.0, 1.0)
    assert lmt.decode_keys(out, position, 67)[0].frame == 0
    count, events = struct.unpack_from("<II", out, animation.events + 0x40)
    assert count == 1
    assert struct.unpack_from("<II", out, events) == (0x1234, 3)


def test_lmt_convert_carries_a_version_67_list_unchanged():
    d = lmt.convert(lmt_version_66_to_convert())
    assert lmt.convert(d) == d
    with pytest.raises(lmt.LmtError, match="version 68"):
        lmt.convert(d[:4] + struct.pack("<H", 68) + d[6:])


def test_lmt_convert_refuses_a_float_track_block_it_does_not_move():
    # no motion list in the three games has one, so the converter has nothing to check a copy of it against
    d = bytearray(lmt_version_66_to_convert()) + bytes(0x30)
    struct.pack_into("<I", d, 0x10 + 0x38, len(d) - 0x30)
    with pytest.raises(lmt.LmtError, match="float-track block"):
        lmt.convert(bytes(d))


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


def test_emd_attack_flag_words_count_the_bits_the_readers_test():
    """specs/emd.md check E10: the two words at +0x10 and +0x14 are flag bitfields; the check counts the bits
    0xbe9c14/0xbe8dac read against the ones no reader tests, and the state's +0x44 bit 0 that no record sets"""
    d = bytearray(0x200)
    d[:4] = b"etd\0"
    struct.pack_into("<I", d, 4 * 28, 0x80)                   # attack records at 0x80, word 29 = 0
    struct.pack_into("<H", d, 0x80 + 40 * 1 + 0x10, 0x8000)   # bit 15: a reader tests it
    d[0x80 + 40 * 1 + 0x12] = 0x08                            # bit 19: no reader tests it
    struct.pack_into("<H", d, 0x80 + 40 * 2 + 0x10, 0x0400)   # bit 10: a reader tests it
    d[0x80 + 40 * 2 + 0x14] = 2                               # +0x44 bit 1: a reader tests it
    struct.pack_into("<H", d, 0x80 + 40 * 3, 0xFFFF)          # terminator
    counts = emd.check_attack_records(bytes(d))
    assert counts["E10 etd attack records"] == 3
    assert counts["E10 etd attack +0x40 has a bit a reader tests"] == 2
    assert counts["E10 etd attack +0x40 no bit a reader tests"] == 1
    assert counts["E10 etd attack +0x40 has a bit no reader tests"] == 1
    assert counts["E10 etd attack +0x44 bit 0 clear"] == 3
    assert counts["E10 etd attack +0x44 bit 0 set"] == 0
    assert counts["E10 etd attack +0x44 bits 1-2 set"] == 1
    assert counts["E10 etd attack +0x44 every set bit read"] == 3
    assert counts["E10 etd attack +0x44 has a bit no reader tests"] == 0


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


def xfs_one_class(endian: str) -> bytes:
    """An XFS file laid out by hand from specs/xfs.md: one class, two properties, one root object.

    The class is `mFlags` (u32) and `mNames` (string array); the root is class 0, instance 7, with
    mFlags 0x11223344 and mNames ["one", "two"]. Little-endian files write the count itself and the
    class word `index << 1 | 1`; big-endian ones twice the count and `0x8000 | index`.
    """
    def_at = 0x1C                     # offset 4 from 0x18, as the 3DS files do
    prop_at = def_at + 8
    names_at = prop_at + 2 * xfs.PROP_ENTRY
    names = b"mFlags\0mNames\0"
    def_size = names_at - 0x18 + len(names)
    root_at = 0x18 + def_size
    d = bytearray(root_at + 8 + 4 + 4 + 4 + 4 + 4)
    d[:4] = b"XFS\0" if endian == "<" else b"\0SFX"
    struct.pack_into(endian + "HH", d, 4, 15, 1)
    struct.pack_into(endian + "II", d, 0x10, 1, def_size)
    struct.pack_into(endian + "I", d, 0x18, def_at - 0x18)
    struct.pack_into(endian + "I", d, def_at, 0x12345678)
    if endian == "<":
        struct.pack_into("<I", d, def_at + 4, 2)                  # the count
    else:
        struct.pack_into(">HH", d, def_at + 4, 4, 0)              # the count, twice
    struct.pack_into(endian + "I", d, prop_at, names_at - 0x18)   # "mFlags"
    d[prop_at + 4], d[prop_at + 5] = 0x06, 0x00                   # type, attr
    struct.pack_into(endian + "H", d, prop_at + 6, 4)             # size
    p1 = prop_at + xfs.PROP_ENTRY
    struct.pack_into(endian + "I", d, p1, names_at - 0x18 + 7)    # "mNames"
    d[p1 + 4], d[p1 + 5] = 0x0E, 0x20                             # type, attr: array
    struct.pack_into(endian + "H", d, p1 + 6, 4)                  # size
    d[names_at:names_at + len(names)] = names
    struct.pack_into(endian + "HH", d, root_at, 1 if endian == "<" else 0x8000, 7)
    struct.pack_into(endian + "I", d, root_at + 4, 24)            # counts itself
    p = root_at + 8
    struct.pack_into(endian + "I", d, p, 1)
    struct.pack_into(endian + "I", d, p + 4, 0x11223344)
    struct.pack_into(endian + "I", d, p + 8, 2)
    d[p + 12:p + 16] = b"one\0"
    d[p + 16:p + 20] = b"two\0"
    return bytes(d)


def test_xfs_reads_the_little_endian_layout_of_the_3ds_games():
    """specs/xfs.md, little-endian: the count is itself, the class word `index << 1 | 1`, the flag bit 0"""
    x = xfs.read(xfs_one_class("<"))
    assert (x.endian, x.version, x.subversion) == ("little", 15, 1)
    assert [(p.name, p.type, p.attr, p.size) for p in x.classes[0].props] == [
        ("mFlags", 0x06, 0x00, 4), ("mNames", 0x0E, 0x20, 4)]
    assert x.root == {"class": "0x12345678", "instance": 7,
                      "mFlags": 0x11223344, "mNames": ["one", "two"]}


def test_xfs_reads_the_big_endian_layout_cha_cha_documents():
    """specs/xfs.md, big-endian: twice the count, the class word `0x8000 | index`, the flag bit 15"""
    x = xfs.read(xfs_one_class(">"))
    assert (x.endian, x.version, x.subversion) == ("big", 15, 1)
    assert len(x.classes[0].props) == 2
    assert x.root == {"class": "0x12345678", "instance": 7,
                      "mFlags": 0x11223344, "mNames": ["one", "two"]}


def test_xfs_refuses_a_little_endian_object_without_its_flag():
    """the little-endian object word carries its flag in bit 0; without it the file is not an object"""
    d = bytearray(xfs_one_class("<"))
    root_at = 0x18 + struct.unpack_from("<I", d, 0x14)[0]
    struct.pack_into("<H", d, root_at, 0)
    with pytest.raises(xfs.XfsError, match="bad object header"):
        xfs.read(bytes(d))


def one_of_each_layout() -> bytes:
    """A hand-built MH4U layout: one texture slot and one root, picture, text and boundary.

    The offsets are worked out here, not read from a game file, so the reader is checked against
    the spec's layout rather than against its own output.
    """
    names_at, text_at, roots_at = 0x18C, 0x1A6, 0x1AC
    d = bytearray(roots_at + 4)
    d[:4] = b"lyt\0"
    struct.pack_into("<I", d, 4, lyt.VERSION)
    struct.pack_into("<10I", d, 8,
                     1, 1, 1, 1, 0, 1, 1,          # roots, textures, group+text, pictures, unknown, text, boundaries
                     0x30, 0x38, roots_at)          # texture slots, nodes, root table
    struct.pack_into("<II", d, 0x30, 0, 0x19D)      # one texture slot, its path below

    def name(at: int, text: str) -> None:
        d[at:at + len(text) + 1] = text.encode("ascii") + b"\0"

    def node(at: int, typ: int, depth: int, text: str, name_at: int, size: int) -> None:
        struct.pack_into("<5I", d, at, typ, depth,
                         (~zlib.crc32(text.encode("ascii")) & 0xFFFFFFFF), name_at, size)

    node(0x38, 2, 0, "root", names_at, 0x28)
    struct.pack_into("<ffIfI", d, 0x38 + 0x14, 1.5, -2.5, 0, 1.0, 0x201)
    node(0x60, 0, 1, "pic", names_at + 5, 0x6C)
    struct.pack_into("<5f", d, 0x60 + 0x14, 10.0, 20.0, 0.0, 30.0, 40.0)
    struct.pack_into("<3f", d, 0x60 + 0x28, 1.0, 1.0, 0.0)
    struct.pack_into("<4I", d, 0x60 + 0x40, 0xFFFFFFFF, 0x11223344, 0, 0)
    node(0xCC, 3, 1, "msg", names_at + 9, 0x7C)
    struct.pack_into("<I", d, 0xCC + 0x14, text_at)
    node(0x148, 4, 1, "hit", names_at + 13, 0x30)
    struct.pack_into("<4f", d, 0x148 + 0x14, 1.0, 2.0, 3.0, 4.0)
    struct.pack_into("<I", d, 0x178, 0xFF)          # terminator, then the 0x10 zero bytes
    name(names_at, "root")
    name(names_at + 5, "pic")
    name(names_at + 9, "msg")
    name(names_at + 13, "hit")
    name(0x19D, "tex\\pic")
    d[text_at:text_at + 6] = "Hi".encode("utf-16-le") + b"\0\0"
    return bytes(d)


def test_lyt_reads_the_header_nodes_textures_and_text():
    """specs/lyt.md: the header counts, the 8-byte texture slot, the 0x14-byte node header and
    the per-type data; the text string is UTF-16LE behind the record's +0x14 offset"""
    layout = lyt.read(one_of_each_layout())
    assert layout.version == lyt.VERSION and layout.root_count == 1
    assert [n.type_name for n in layout.nodes] == ["root", "picture", "text", "boundary"]
    assert [n.name for n in layout.nodes] == ["root", "pic", "msg", "hit"]
    assert [n.depth for n in layout.nodes] == [0, 1, 1, 1]
    assert layout.textures[0].path == "tex\\pic"
    assert [n.name for n in layout.children(0)] == ["pic", "msg", "hit"]
    assert layout.find("msg") is layout.nodes[2]
    root, picture, _, boundary = layout.nodes
    assert (root.fields["x"], root.fields["y"], root.fields["flags"]) == (1.5, -2.5, 0x201)
    assert (picture.fields["x"], picture.fields["y"], picture.fields["w"], picture.fields["h"]) == (
        10.0, 20.0, 30.0, 40.0)
    assert (boundary.fields["x"], boundary.fields["y"], boundary.fields["w"], boundary.fields["h"]) == (
        1.0, 2.0, 3.0, 4.0)
    assert layout.nodes[2].fields["text"] == "Hi"
    assert layout.nodes[3].size == 0x30


def test_lyt_read_refuses_a_file_that_is_not_a_layout():
    """the loader gates on `lyt\0` and version 0x70C before it reads any offset"""
    d = bytearray(one_of_each_layout())
    d[4:8] = struct.pack("<I", 0x70D)
    with pytest.raises(lyt.LytError, match="version 0x70d"):
        lyt.read(bytes(d))
    d = bytearray(one_of_each_layout())
    d[:4] = b"LYT\0"
    with pytest.raises(lyt.LytError, match="magic"):
        lyt.read(bytes(d))


def test_lyt_read_refuses_a_node_whose_hash_is_not_its_name():
    """the name hash is ~crc32(name); a wrong name or hash is refused"""
    d = bytearray(one_of_each_layout())
    d[0x38 + 8] ^= 1
    with pytest.raises(lyt.LytError, match="has hash"):
        lyt.read(bytes(d))


def test_lyt_read_refuses_a_header_count_that_does_not_match_the_chain():
    """every header count must equal the chain's, so a truncated or mislaid file is refused"""
    d = bytearray(one_of_each_layout())
    struct.pack_into("<I", d, 0x1C, 2)      # the text count
    with pytest.raises(lyt.LytError, match="2 text nodes"):
        lyt.read(bytes(d))


def test_lyt_dump_writes_the_tree_as_json(tmp_path, capsys):
    source = tmp_path / "ui000.lyt"
    source.write_bytes(one_of_each_layout())
    assert cli.main(["lyt", "dump", str(source)]) == 0
    dumped = json.loads(capsys.readouterr().out)
    assert dumped["root_count"] == 1
    assert [n["name"] for n in dumped["nodes"]] == ["root", "pic", "msg", "hit"]
    assert dumped["nodes"][2]["text"] == "Hi"


def lmd_bytes(messages):
    """A hand-built id-indexed message table: one label and one record per message."""
    n = len(messages)
    label_off = 0x24
    format_off = label_off + 8 * n
    record_off = format_off + 16 * 2 * n
    strings = record_off + 12 * n
    out = bytearray(strings)
    struct.pack_into("<4sI7I", out, 0, b"lmd\0", lmd.VERSION, n, 2 * n, n,
                     label_off, format_off, record_off, 0)
    for i in range(n):
        struct.pack_into("<2I", out, label_off + 8 * i, 0xDEADBEEF, 0x400000 + 2 * i)
        struct.pack_into("<4I", out, format_off + 32 * i, 1, i, 0, 0)
        struct.pack_into("<4I", out, format_off + 32 * i + 16, 0x16, 0, 0, 0)
    for i, text in enumerate(messages):
        raw = text.encode("utf-16-le")
        struct.pack_into("<3I", out, record_off + 12 * i, len(out), len(text), len(text))
        out += raw + b"\0\0"
    struct.pack_into("<I", out, 0x20, len(out))       # the string area ends here
    return bytes(out) + b"lmd\0"                        # 5-byte trailer, not read


def test_lmd_reads_messages_by_record_index_and_keeps_the_trailer_unread():
    data = lmd_bytes(["No enemy", "Rathian"])
    table = lmd.read(data)
    assert table.version == lmd.VERSION
    assert [m.text for m in table.messages] == ["No enemy", "Rathian"]
    assert [m.chars for m in table.messages] == [8, 7]
    assert table.message(1).text == "Rathian"
    assert table.message(2) is None


def test_lmd_reads_a_utf16_message_with_its_two_lengths():
    table = lmd.read(lmd_bytes(["Méga potion"]))
    assert table.messages[0].text == "Méga potion"
    assert table.messages[0].chars == table.messages[0].width == 11


def test_lmd_refuses_a_message_that_does_not_end_in_nul():
    data = bytearray(lmd_bytes(["Rathian"]))
    record = 0x4C                                               # one message: labels, then formatting, then this
    struct.pack_into("<3I", data, record, 0x58, 2, 2)           # two units of the string, no NUL after them
    with pytest.raises(lmd.LmdError, match="NUL"):
        lmd.read(bytes(data))


def test_lmd_refuses_offsets_not_in_file_order():
    data = bytearray(lmd_bytes(["Rathian"]))
    struct.pack_into("<I", data, 0x1C, 0x10)                        # record table before the labels
    with pytest.raises(lmd.LmdError, match="file order"):
        lmd.read(bytes(data))


def test_lmd_refuses_a_version_it_does_not_lay_out():
    data = bytearray(lmd_bytes(["Rathian"]))
    struct.pack_into("<I", data, 4, 0x00010201)
    with pytest.raises(lmd.LmdError, match="version"):
        lmd.read(bytes(data))
