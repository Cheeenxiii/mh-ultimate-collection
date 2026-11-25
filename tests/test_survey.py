"""Survey counts sound resources by kind, version and class id (specs/sound.md, check SN1), and
stage resources that reference the water-surface class uOcean (docs/underwater.md, check U1)."""
from __future__ import annotations

import struct

from mhuc import survey
from mhuc.formats import arc, classid


def sound(magic: bytes, version: int) -> bytes:
    return magic + struct.pack("<I", version) + bytes(8)


def test_survey_counts_the_same_sound_kind_in_both_games_class_namespaces():
    """MH4U's rLtSoundBank and MHXX's rSoundBank are different ids and magics for one kind"""
    mh4u_bank = classid.class_id("rLtSoundBank")
    mhxx_bank = classid.class_id("rSoundBank")
    mhxx_wave = classid.class_id("rSoundSourceADPCM")
    mhxx_emitter = classid.class_id("rFestaSoundEmitter")
    data = arc.write(arc.Archive(version=0x13, entries=[
        arc.Entry(path="a\\snd", type_id=mh4u_bank, data=sound(b"SNDB", 11)),
        arc.Entry(path="a\\snd", type_id=mhxx_bank, data=sound(b"SBKR", 4)),
        arc.Entry(path="a\\wav", type_id=mhxx_wave, data=sound(b"MADP", 5)),
        arc.Entry(path="a\\ses", type_id=mhxx_emitter, data=sound(b"SES\x00", 0x20160706)),
    ]))
    st: dict = {}
    survey.survey_arc(data, st)
    counts = st["sound"]
    assert counts["bank SNDB v11"] == 1
    assert counts["bank SBKR v4"] == 1
    assert counts["wave MADP v5"] == 1
    assert counts[f"bank SBKR type 0x{mhxx_bank:08x} rSoundBank"] == 1
    assert counts[f"wave MADP type 0x{mhxx_wave:08x} rSoundSourceADPCM"] == 1
    assert counts["area emitter SES v0x20160706"] == 1
    assert counts[f"area emitter SES type 0x{mhxx_emitter:08x} rFestaSoundEmitter"] == 1
    assert sum(n for k, n in counts.items() if k == "wave MADP v5") == 1


def test_survey_check_u1_counts_only_stage_resources_that_reference_uOcean():
    """check U1: a stage entry that names uOcean, carries its class id or is typed it is counted;
    an entry outside a stage path is not, and a suimen surface is counted as the positive control"""
    data = arc.write(arc.Archive(version=0x13, entries=[
        arc.Entry(path="stage\\m01d\\m01a00d\\m01a00d-info", type_id=classid.class_id("rStageInfoSet"),
                  data=b"SIS\x00uOcean"),
        arc.Entry(path="stage\\m01d\\m01a00d\\m01a00d-id", type_id=classid.class_id("rStageInfoSet"),
                  data=b"SIS\x00" + struct.pack("<I", survey.UOCEAN_ID)),
        arc.Entry(path="stage\\m01d\\m01a00d\\m01a00d-ocean", type_id=survey.UOCEAN_ID, data=b""),
        arc.Entry(path="stage\\m01d\\m01a00d\\m01a00d-suimen", type_id=0x1234, data=b"suimen"),
        arc.Entry(path="em\\em001\\em001", type_id=0x1234, data=b"uOcean"),
    ]))
    st: dict = {}
    survey.survey_arc(data, st)
    counts = st["stage"]
    assert counts["U1 stage-path entries"] == 4
    assert counts["U1 stage entries naming uOcean"] == 1
    assert counts["U1 stage entries carrying uOcean's class id"] == 1
    assert counts["U1 entries typed uOcean"] == 1
    assert counts["U1 stage entries naming a suimen surface"] == 1


def test_survey_counts_a_loose_sound_file_that_has_no_class_id():
    st: dict = {}
    survey.survey_entry(None, sound(b"STQR", 4), st)
    counts = st["sound"]
    assert counts["stream request STQR v4"] == 1
    assert counts["stream request STQR loose"] == 1
    assert not [k for k in counts if "type 0x" in k]


def wave4() -> bytes:
    """A hand-built MH3U wave: mono, 8000 samples at 8000 Hz, 0x100 bytes of data at 0x5C."""
    d = bytearray(0x5C + 0x100)
    struct.pack_into("<4sI4B", d, 0, b"MADP", 4, 1, 0, 0, 1)
    struct.pack_into("<6I", d, 0x0C, 8000, 8000, 0, 0, 0x5C, 0x100)
    struct.pack_into("<f", d, 0x24, 1.0)
    struct.pack_into("<I", d, 0x28, 0x33480000)
    return bytes(d)


def test_survey_reads_the_sound_files_it_counts():
    """check SN6: a wave the reader accepts is counted as read; one it refuses as not read"""
    st: dict = {}
    survey.survey_entry(None, wave4(), st)
    assert st["sound"]["wave MADP v4"] == 1
    assert st["sound"]["SN6 wave read"] == 1
    st = {}
    survey.survey_entry(None, wave4()[:-1], st)
    assert st["sound"]["SN6 wave not read"] == 1


def empty_xfs() -> bytes:
    """A hand-built little-endian XFS: one class with no properties and a root object that has none."""
    d = bytearray(0x2C)
    d[:4] = b"XFS\0"
    struct.pack_into("<HH", d, 4, 15, 1)
    struct.pack_into("<II", d, 0x10, 1, 0x0C)      # one class, its definition block is 0x0C bytes
    struct.pack_into("<I", d, 0x18, 4)             # class 0 at 0x18 + 4
    struct.pack_into("<I", d, 0x1C, 0x12345678)    # its DTI id
    struct.pack_into("<I", d, 0x20, 0)             # no properties
    struct.pack_into("<HHI", d, 0x24, 1, 0, 4)     # class 0, instance 0, size 4
    return bytes(d)


def test_survey_counts_the_xfs_files_it_reads_and_refuses():
    """check X1: an XFS file the reader takes is counted by version and endianness, a broken one as not read"""
    st: dict = {}
    survey.survey_entry(None, empty_xfs(), st)
    assert st["xfs"]["X1 read"] == 1
    assert st["xfs"]["version 15.1"] == 1
    assert st["xfs"]["little-endian"] == 1
    assert st["xfs"]["loose"] == 1
    st = {}
    survey.survey_entry(None, empty_xfs()[:-1], st)
    assert st["xfs"]["X1 not read"] == 1


def test_survey_counts_a_camera_list_by_version():
    """specs/camera.md check C1 runs on every rCameraList the image holds."""
    data = arc.write(arc.Archive(version=0x13, entries=[
        arc.Entry(path="enemy\\em001\\mot\\e001_cam", type_id=classid.class_id("rCameraList"),
                  data=b"LCM\0" + struct.pack("<HH", 4, 0)),
    ]))
    st: dict = {}
    survey.survey_arc(data, st)
    counts = st["camera"]
    assert counts["C1 read"] == 1
    assert counts["version 4"] == 1
    assert counts["0 table entries"] == 1
