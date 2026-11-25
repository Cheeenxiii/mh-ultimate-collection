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
from mhuc.formats import arc, camera, mrl, tex

SLOTS = frozenset({0, 1, 2, 3, 4})
ROW = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                   frozenset({"model", "motions", "camera", "tail", "cmd"}), SLOTS)
SHIPPED_ROW = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                           frozenset({"model", "motions", "tail", "cmd"}), SLOTS)


def entry(path: str, data: bytes) -> arc.Entry:
    return arc.entry_from_file(path, data)


def camera_mhxx() -> bytes:
    """A one-camera MHXX camera list: header, 256-entry table, one zero record."""
    offsets = [0] * 256
    offsets[0] = 0x408
    return b"LCM\0" + struct.pack("<HH", 5, 256) + struct.pack("<256I", *offsets) + bytes(0xAC)


def material_mhxx() -> bytes:
    """A synthetic MHXX MRL 0x20: one texture reference and one material record."""
    refs = (struct.pack("<III", mrl.TEXTURE_CLASS, 0, 0)
            + b"enemy\\em001_00\\mod\\em001_00_BM".ljust(64, b"\0"))
    records = struct.pack("<II", 0, 0x12345678) + bytes(0x3C - 4)
    header = mrl.HEADER.pack(b"MRL\0", 0x20, 1, 1, mrl.SIGNATURES["mhxx"], 0x1C,
                             0x1C + len(refs))
    return header + refs + records


def source_entries() -> list[arc.Entry]:
    image = tex.from_rgba("RGBA8", 8, 8, bytes([1, 2, 3, 4]) * 64)
    image.version = 0xA6
    return [
        entry("enemy/em001/em001_00/mod/em001_00.mod", b"MOD\0" + bytes(8)),
        entry("enemy/em001/em001_00/mod/em001_00.mrl", material_mhxx()),
        entry("enemy/em001/em001_00/mod/em001_00_tail.mod", b"MOD\0" + bytes(4)),
        entry("enemy/em001/em001_00/mod/em001_00_tail.mrl", material_mhxx()),
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


def stand_in_entries(key: str = "em001") -> list[arc.Entry]:
    """MH4U's own archive for the stand-in, shortened to one entry of each kind the record
    names, plus two data files it never names."""
    motion = b"LMT\0" + struct.pack("<HH", 67, 0)
    return [
        entry(f"enemy/{key}/mod/{key}.mod", b"MOD\0" + bytes(8)),
        entry(f"enemy/{key}/mod/{key}.mrl", b"MRL\0" + bytes(4)),
        entry(f"enemy/{key}/mod/{key}_BM.tex", b"TEX\0" + bytes(4)),
        entry(f"enemy/{key}/mod/{key}_tail.mod", b"MOD\0" + bytes(4)),
        entry(f"enemy/{key}/mod/{key}_tail.mrl", b"MRL\0" + bytes(2)),
        entry(f"enemy/{key}/mot/{key}_0.lmt", motion),
        entry(f"enemy/{key}/mot/{key}_1.lmt", motion),
        entry(f"enemy/{key}/mot/{key}_2.lmt", motion),
        entry(f"enemy/{key}/mot/{key}_3.lmt", motion),
        entry(f"enemy/{key}/mot/{key}_4.lmt", motion),
        entry(f"enemy/{key}/mot/e{key[2:]}_cam.lcm", b"LCM\0" + bytes(4)),
        entry(f"effect/mef/em/{key}_0.mef", b"MEF\0" + bytes(4)),
        entry(f"effect/mef/em/{key}_1.mef", b"MEF\0" + bytes(4)),
        entry(f"sound/call/em/{key}.mss", b"MSS\0" + bytes(4)),
        entry(f"sound/se/em/{key}/snd_{key}.sbk", b"SNDB" + bytes(4)),
        entry(f"enemy/{key}/data/{key}_cmd.emc", b"EMC\0" + bytes(4)),
        entry(f"effect/efl/em/{key}/{key}_000.efl", b"EFL\0" + bytes(4)),
        entry(f"effect/efl/em/{key}/{key}_001.efl", b"EFL\0" + bytes(4)),
        arc.Entry(f"enemy\\{key}\\em_status00", 0, b"STAT"),
        arc.Entry(f"enemy\\{key}\\em_hitdata00", 0, b"HIT\0"),
    ]


def stand_in_bytes(row: monsters.Row = ROW) -> bytes:
    return arc.write(arc.Archive(0x13, stand_in_entries(f"em{row.stand_in:03d}")))


def convert(row: monsters.Row = ROW, entries=None) -> tuple[arc.Archive, monsters.Report]:
    data = arc.write(arc.Archive(0x11, entries if entries is not None else source_entries()))
    converted, report = monsters.convert(data, row, stand_in_bytes(row))
    return arc.read(converted), report


def test_the_port_gets_its_own_paths_and_mh4us_archive_version():
    out, _ = convert()
    stand_in = {e.file_name for e in stand_in_entries()}
    assert out.version == 0x13
    assert [e.file_name for e in out.entries if e.file_name not in stand_in] == [
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
    # Every other entry is a stand-in entry the record keeps, copied at its original path.
    assert {e.file_name for e in out.entries if e.file_name in stand_in} == {
        "effect/mef/em/em001_0.mef",
        "effect/mef/em/em001_1.mef",
        "sound/call/em/em001.mss",
        "sound/se/em/em001/snd_em001.sbk",
        "effect/efl/em/em001/em001_000.efl",
        "effect/efl/em/em001/em001_001.efl",
    }


def test_the_kept_paths_are_the_stand_in_entries_byte_for_byte():
    """The record keeps the stand-in's path for a kind the port doesn't ship, and MH4U looks
    that path up in the archive the data path names: the port's own archive."""
    out, report = convert()
    stand_in = {e.file_name: e.data for e in stand_in_entries()}
    copied = [e for e in out.entries if e.file_name in stand_in]
    assert [e.file_name for e in copied] == report.copied
    for e in copied:
        assert e.data == stand_in[e.file_name], e.file_name
    # The stand-in's data files are not paths the record names, so they are not copied.
    assert not any(e.file_name in ("enemy/em001/em_status00", "enemy/em001/em_hitdata00")
                   for e in out.entries)


def test_the_model_motions_and_ai_script_are_taken_as_is_and_the_material_only_changes_its_signature():
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
        got, want = next(e for e in out.entries if e.file_name == port_path).data, source[source_path]
        if port_path.endswith(".mrl"):
            # specs/mrl.md check MR1: MH4U's loader accepts only its own signature at 0x10.
            assert struct.unpack_from("<I", got, mrl.SIGNATURE_AT)[0] == mrl.SIGNATURES["mh4u"]
            assert [i for i in range(len(want)) if want[i] != got[i]] == \
                list(range(mrl.SIGNATURE_AT, mrl.SIGNATURE_AT + 4))
        else:
            assert got == want


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
    stand_in = {e.file_name for e in stand_in_entries()}
    taken = {e.file_name for e in out.entries if e.file_name not in stand_in}
    assert not any(n.startswith(("sound/", "effect/", "arc/shell/")) for n in taken)
    assert not any(n.endswith(".lcm") for n in taken)
    assert (report.left_out[monsters.SOUND] ==
            ["sound/se/em/em001_00/wav/em001_vo_attack.79C47B59"])
    assert (report.left_out[monsters.CAMERA] == ["enemy/em001/em001_00/mot/em001_00_cam.lcm"])
    assert report.left_out[monsters.SHELL] == ["arc/shell/em/em001_00_shell.arc"]
    assert any("dt_tune" in p for p in report.left_out[monsters.MONSTER_DATA])
    assert report.left_out[monsters.OPTION] == ["enemy/em_option/mot/em001_00_option.lmt"]
    # The camera the record keeps is the stand-in's, copied under its own path.
    assert next(e for e in out.entries if e.type_name == "rCameraList").file_name == \
        "enemy/em001/mot/e001_cam.lcm"


def test_a_motion_slot_the_row_does_not_ship_is_copied_from_the_stand_in():
    row = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                       frozenset({"model", "motions"}), frozenset({0}))
    out, report = convert(row)
    stand_in = {e.file_name for e in stand_in_entries()}
    assert [e.file_name for e in out.entries
            if e.type_name == "rMotionList" and e.file_name not in stand_in] == [
        "enemy/em124/mot/em124_0.lmt"]
    copied = {e.file_name for e in out.entries if e.file_name in stand_in and e.type_name == "rMotionList"}
    assert copied == {f"enemy/em001/mot/em001_{slot}.lmt" for slot in (1, 2, 3, 4)}
    assert any("motion slot 4" in reason for reason in report.left_out)


def test_a_borrowed_motion_list_keeps_its_slot_under_the_ports_id():
    # MHXX shares a family's motions: Giadrome's lists sit under em014 (Velocidrome).
    row = monsters.Row(126, "giadrome-gu", "mhxx", "em034", "Giadrome", 15,
                       frozenset({"model", "motions"}), frozenset({0, 2, 3, 4}))
    entries = [
        entry("enemy/em034/em034_00/mod/em034_00.mod", b"MOD\0" + bytes(8)),
        entry("enemy/em014/em014_00/mot/em014_00_0.lmt", b"LMT\0" + struct.pack("<HH", 67, 0)),
        entry("enemy/em014/em014_00/mot/em014_00_2.lmt", b"LMT\0" + struct.pack("<HH", 67, 0)),
        entry("enemy/em014/em014_00/mot/em014_00_1.lmt", b"LMT\0" + struct.pack("<HH", 67, 0)),
    ]
    out, report = convert(row, entries)
    stand_in = {e.file_name for e in stand_in_entries("em015")}
    assert [e.file_name for e in out.entries
            if e.type_name == "rMotionList" and e.file_name not in stand_in] == [
        "enemy/em126/mot/em126_0.lmt", "enemy/em126/mot/em126_2.lmt"]
    assert any("motion slot 1" in reason for reason in report.left_out)
    # The row ships no camera, tail, mef, sound, cmd or efl, so the record keeps the stand-in's
    # paths and the archive carries a copy of each.
    copied = {e.file_name for e in out.entries if e.file_name in stand_in}
    assert "enemy/em015/mot/e015_cam.lcm" in copied
    assert "enemy/em015/mod/em015_tail.mod" in copied
    assert "sound/call/em/em015.mss" in copied


def test_a_command_the_row_does_not_ship_is_left_out():
    row = monsters.Row(124, "rathian-gu", "mhxx", "em001", "Rathian", 1,
                       frozenset({"model", "motions"}), SLOTS)
    out, report = convert(row)
    assert [e.file_name for e in out.entries if e.type_name == "rEnemyCmd"] == [
        "enemy/em001/data/em001_cmd.emc"]        # the stand-in's copy, not the source's
    assert report.left_out[next(r for r in report.left_out if "cmd" in r)] == [
        "enemy/cmd_tbl/em001_00_cmdtbl.emc"]


def test_an_archive_with_no_file_of_a_shipped_kind_is_refused():
    data = arc.write(arc.Archive(0x11, [entry("sound/se/x.mca", b"MADP")]))
    with pytest.raises(monsters.ConvertError, match="the row's files lists it, but em001_00 has none"):
        monsters.convert(data, ROW, stand_in_bytes())


def write_registry(tmp_path, files="model,motions=0-4,tail,cmd"):
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
    assert row.motions == {0, 1, 2, 3, 4}


def test_a_kind_this_converter_cannot_produce_is_refused(tmp_path):
    row = monsters.registry_row(124, write_registry(tmp_path, "model,sound"))
    with pytest.raises(monsters.ConvertError, match="sound"):
        monsters.convert(arc.write(arc.Archive(0x11, source_entries())), row, stand_in_bytes(row))


def test_the_files_column_is_checked(tmp_path):
    for files in ("", "model,motions=9", "model,mystery", "model,motions=0-4,motions=2",
                  "model,motions=4-2"):
        path = write_registry(tmp_path, files)
        with pytest.raises(monsters.ConvertError):
            monsters.registry_row(124, path)


def test_the_mod_folder_holds_the_ports_archive_and_a_manifest(tmp_path):
    converted, _ = monsters.convert(arc.write(arc.Archive(0x11, source_entries())), ROW, stand_in_bytes())
    monsters.build_mod(str(tmp_path / "mod"), ROW, converted)
    manifest = json.loads((tmp_path / "mod" / "mod.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "Rathian (GU) files"
    written = arc.read((tmp_path / "mod" / "romfs" / "data" / "em124.arc").read_bytes())
    assert [e.file_name for e in written.entries] == [e.file_name for e in arc.read(converted).entries]
