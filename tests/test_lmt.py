"""LMT v67 reader and check L1 on a generated motion list (no game bytes)."""
from __future__ import annotations

import struct

import pytest
from mhuc import lmt, survey


def make_lmt() -> bytes:
    d = bytearray(0x200)
    d[:4] = b"LMT\0"
    struct.pack_into("<HH", d, 4, 67, 2)
    struct.pack_into("<II", d, 8, 0x20, 0)                # slot 1 empty
    struct.pack_into("<IIii", d, 0x20, 0x60, 1, 30, 0)    # one track, 30 frames
    struct.pack_into("<I", d, 0x20 + 0x34, 0)             # no events
    d[0x60:0x64] = bytes((4, 1, 0, 7))                    # buffer type 4, bone 7
    struct.pack_into("<fII", d, 0x64, 1.0, 0x10, 0x100)
    return bytes(d)


def test_read():
    version, anims = lmt.read(make_lmt())
    assert version == 67 and anims[1] is None
    a = anims[0]
    assert (a.frames, len(a.tracks), a.tracks[0].bone, a.tracks[0].buffer_type) == (30, 1, 7, 4)


def test_read_rejects_out_of_file_and_other_versions():
    bad = bytearray(make_lmt())
    struct.pack_into("<I", bad, 0x60 + 0x0C, 0x1F8)       # buffer runs past the end
    with pytest.raises(lmt.LmtError):
        lmt.read(bytes(bad))
    other = bytearray(make_lmt())
    struct.pack_into("<H", other, 4, 49)
    assert lmt.check(bytes(other))["L1 version not laid out"] == 1


def test_check_and_survey():
    c = lmt.check(make_lmt())
    assert c["L1 readable"] == 1 and c["L1 animations"] == 1 and c["L1 empty slots"] == 1
    st: dict = {}
    survey.survey_entry("rMotionList", make_lmt(), st)
    assert st["lmt"]["L1 tracks"] == 1


def test_survey_emc_and_sbc():
    emc = bytearray(0x60)
    emc[:4] = b"EMC\0"
    struct.pack_into("<II", emc, 4, 0x20120804, 1)
    struct.pack_into("<II", emc, 16, 2, 0x20)            # group 0: 2 scripts at 0x20
    st: dict = {}
    survey.survey_entry("rEnemyCmd", bytes(emc), st)
    assert st["emc"]["A1 version 0x20120804"] == 1 and st["emc"]["A1 scripts"] == 2
    assert st["emc"]["A1 groups and script tables inside"] == 1
    sbc = bytearray(0x48)
    sbc[:4] = b"SBC\xff"
    struct.pack_into("<IIIH", sbc, 4, 0x77CF8DF8, 0, 2, 1)
    survey.survey_entry("rCollision", bytes(sbc), st)
    assert st["sbc"]["S1 inner class 0x77cf8df8"] == 1 and st["sbc"]["S1 parts 1"] == 1
