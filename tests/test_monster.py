"""The monster converter: a ported monster's files get the port's own paths, and only the
kinds the registry's `files` column ships survive. A wrong path or a shipped kind the record
doesn't expect means the game loads another monster or nothing at all, so these are the checks
that matter."""
from __future__ import annotations

import csv
import json
import struct

import pytest

from mhuc import monsters
from mhuc.formats import arc, camera, tex

ROW = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                   frozenset({"model", "motions", "camera", "tail", "cmd"}), 5)
SHIPPED_ROW = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                           frozenset({"model", "motions", "tail", "cmd"}), 5)


def entry(path: str, data: bytes) -> arc.Entry:
    return arc.entry_from_file(path, data)


def camera_mhxx() -> bytes:
    """A one-camera MHXX camera list: header, 256-entry table, one zero record."""
    offsets = [0] * 256
    offsets[0] = 0x408
    return b"LCM\0" + struct.pack("<HH", 5, 256) + struct.pack("<256I", *offsets) + bytes(0xAC)


def source_entries() -> list[arc.Entry]:
    image = tex.from_rgba("RGBA8", 8, 8, bytes([1, 2, 3, 4]) * 64)
    image.version = 0xA6
    return [
        entry("enemy/em001/em001_00/mod/em001_00.mod", b"MOD\0" + bytes(8)),
        entry("enemy/em001/em001_00/mod/em001_00.mrl", b"MRL\0" + bytes(8)),
        entry("enemy/em001/em001_00/mod/em001_00_tail.mod", b"MOD\0" + bytes(4)),
        entry("enemy/em001/em001_00/mod/em001_00_tail.mrl", b"MRL\0" + bytes(4)),
        entry("enemy/em001/em001_00/mod/em001_00_BM.tex", tex.write(image)),
        entry("enemy/em001/em001_00/mot/em001_00_0.lmt", b"LMT\0" + struct.pack("<HH", 67, 0)),
        entry("enemy/em001/em001_00/mot/em001_00_4.lmt", b"LMT\0" + struct.pack("<HH", 67, 0)),
        entry("enemy/em001/em001_00/mot/em001_00_cam.lcm", camera_mhxx()),
        entry("enemy/cmd_tbl/em001_00_cmdtbl.emc", b"EMC\0" + struct.pack("<I", 0x20120804)),
        entry("sound/se/em/em001_00/wav/em001_vo_attack.79C47B59", b"MADP"),
        entry("effect/em/em001/em001_00_003.efl", b"EFL\0" + bytes(8)),
        entry("enemy/dt_tune/em001_00_dttune.48E8AC29", b"DTT\0"),
        entry("enemy/em_option/mot/em001_00_option.lmt", b"LMT\0" + struct.pack("<HH", 67, 0)),
        entry("arc/shell/em/em001_00_shell.arc", b"ARCS"),
    ]


def convert(row: monsters.Row = ROW, entries=None) -> tuple[arc.Archive, monsters.Report]:
    data = arc.write(arc.Archive(0x11, entries if entries is not None else source_entries()))
    converted, report = monsters.convert(data, row)
    return arc.read(converted), report


def test_the_port_gets_its_own_paths_and_mh4us_archive_version():
    out, _ = convert()
    assert out.version == 0x13
    assert [e.file_name for e in out.entries] == [
        "enemy/em124/mod/em124.mod",
        "enemy/em124/mod/em124.mrl",
        "enemy/em124/mod/em124_tail.mod",
        "enemy/em124/mod/em124_tail.mrl",
        "enemy/em001/em001_00/mod/em001_00_BM.tex",       # the material file names this path
        "enemy/em124/mot/em124_0.lmt",
        "enemy/em124/mot/em124_4.lmt",
        "enemy/em124/mot/e124_cam.lcm",
        "enemy/em124/data/em124_cmd.emc",
    ]


def test_the_model_motions_materials_and_ai_script_are_taken_as_is():
    out, _ = convert()
    source = {e.file_name: e.data for e in source_entries()}
    pairs = {
        "enemy/em124/mod/em124.mod": "enemy/em001/em001_00/mod/em001_00.mod",
        "enemy/em124/mod/em124.mrl": "enemy/em001/em001_00/mod/em001_00.mrl",
        "enemy/em124/mod/em124_tail.mod": "enemy/em001/em001_00/mod/em001_00_tail.mod",
        "enemy/em124/mod/em124_tail.mrl": "enemy/em001/em001_00/mod/em001_00_tail.mrl",
        "enemy/em124/mot/em124_0.lmt": "enemy/em001/em001_00/mot/em001_00_0.lmt",
        "enemy/em124/data/em124_cmd.emc": "enemy/cmd_tbl/em001_00_cmdtbl.emc",
    }
    for port_path, source_path in pairs.items():
        assert next(e for e in out.entries if e.file_name == port_path).data == source[source_path]


def test_a_texture_is_mh4us_version_and_otherwise_byte_identical():
    out, _ = convert()
    source = next(e for e in source_entries() if e.type_name == "rTexture")
    converted = next(e for e in out.entries if e.type_name == "rTexture")
    assert len(converted.data) == len(source.data)
    assert [i for i in range(len(source.data)) if source.data[i] != converted.data[i]] == [4]
    assert struct.unpack_from("<I", converted.data, 4)[0] & 0xFFF == 0xA5


def test_a_camera_list_is_converted_to_mh4us_version_and_round_trips():
    out, _ = convert()
    source = camera_mhxx()
    converted = next(e for e in out.entries if e.type_name == "rCameraList").data
    assert camera.read(converted).version == camera.VERSION_MH4U
    assert camera.to_mhxx(converted) == source


def test_sound_effects_shells_and_monster_data_are_left_out_with_a_reason():
    out, report = convert(SHIPPED_ROW)      # the shipped row: no camera
    names = {e.file_name for e in out.entries}
    assert not any(n.startswith(("sound/", "effect/", "arc/shell/")) for n in names)
    assert not any(n.endswith(".lcm") for n in names)
    assert (report.left_out[monsters.SOUND] ==
            ["sound/se/em/em001_00/wav/em001_vo_attack.79C47B59"])
    assert (report.left_out[monsters.CAMERA] == ["enemy/em001/em001_00/mot/em001_00_cam.lcm"])
    assert report.left_out[monsters.SHELL] == ["arc/shell/em/em001_00_shell.arc"]
    assert any("dt_tune" in p for p in report.left_out[monsters.MONSTER_DATA])
    assert report.left_out[monsters.OPTION] == ["enemy/em_option/mot/em001_00_option.lmt"]


def test_a_motion_slot_above_the_rows_count_is_left_out():
    row = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                       frozenset({"model", "motions"}), 1)
    out, report = convert(row)
    assert [e.file_name for e in out.entries if e.type_name == "rMotionList"] == [
        "enemy/em124/mot/em124_0.lmt"]
    assert any("motion slot 4" in reason for reason in report.left_out)


def test_an_archive_with_no_file_of_a_shipped_kind_is_refused():
    data = arc.write(arc.Archive(0x11, [entry("sound/se/x.mca", b"MADP")]))
    with pytest.raises(monsters.ConvertError, match="the row's files lists it, but em001_00 has none"):
        monsters.convert(data, ROW)


def write_registry(tmp_path, files="model,motions=5,tail,cmd"):
    path = tmp_path / "registry.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["kind", "id", "key", "source_game", "source_key", "name", "stand_in",
                         "files", "notes"])
        writer.writerow(["monster", "124", "rathian-gu", "mhxx", "em001", "Rathian", "1", files, ""])
    return str(path)


def test_the_registry_row_reads_the_files_column(tmp_path):
    row = monsters.registry_row(124, write_registry(tmp_path))
    assert row.source_key == "em001"
    assert row.files == {"model", "motions", "tail", "cmd"}
    assert row.motions == 5


def test_a_kind_this_converter_cannot_produce_is_refused(tmp_path):
    row = monsters.registry_row(124, write_registry(tmp_path, "model,sound"))
    with pytest.raises(monsters.ConvertError, match="sound"):
        monsters.convert(arc.write(arc.Archive(0x11, source_entries())), row)


def test_the_files_column_is_checked(tmp_path):
    for files in ("", "model,motions=9", "model,mystery", "model,motions=5,motions=2"):
        path = write_registry(tmp_path, files)
        with pytest.raises(monsters.ConvertError):
            monsters.registry_row(124, path)


def test_the_mod_folder_holds_the_ports_archive_and_a_manifest(tmp_path):
    converted, _ = monsters.convert(arc.write(arc.Archive(0x11, source_entries())), ROW)
    monsters.build_mod(str(tmp_path / "mod"), ROW, converted)
    manifest = json.loads((tmp_path / "mod" / "mod.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "Rathian (GU) files"
    written = arc.read((tmp_path / "mod" / "romfs" / "data" / "em124.arc").read_bytes())
    assert [e.file_name for e in written.entries] == [e.file_name for e in arc.read(converted).entries]
