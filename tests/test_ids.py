"""The id registry: ids are permanent once shipped, so the checks around them matter."""
from __future__ import annotations

import csv
import os
import subprocess
import sys

import check_ids
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLUMNS = ("kind", "id", "key", "source_game", "source_key", "name", "stand_in", "files", "notes")
POOLED_FIXTURE = os.path.join(ROOT, "tests", "fixtures", "registry-pooled.csv")


def write_registry(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def row(ident, key="rathian-gu", stand_in="1", kind="monster", files="model,motions=0-4,tail,cmd"):
    return [kind, str(ident), key, "mhxx", "em001", "Rathian", stand_in, files, ""]


def as_dict(fields):
    return dict(zip(COLUMNS, fields, strict=True))


def test_a_valid_registry_passes():
    assert check_ids.check_rows([as_dict(row(124))]) == []


@pytest.mark.parametrize("ident", [123, 0xFFFFFFFF])
def test_a_monster_id_outside_the_registry_ranges_is_refused(ident):
    problems = check_ids.check_rows([as_dict(row(ident))])
    assert any("isn't in 124..223" in p for p in problems), problems


@pytest.mark.parametrize("ident", [224, 239, 255])
def test_a_permanent_row_above_223_is_refused(ident):
    problems = check_ids.check_rows([as_dict(row(124)), as_dict(row(ident, key="pooled"))])
    assert any("is a byte the plugin lends from the pool" in p for p in problems), problems


def test_a_pooled_id_from_256_up_is_accepted():
    assert check_ids.check_rows([as_dict(row(124)), as_dict(row(256, key="pooled"))]) == []


def test_a_pooled_id_needs_no_consecutive_id_before_it():
    assert check_ids.check_rows([as_dict(row(124)), as_dict(row(300, key="pooled"))]) == []


def test_a_pooled_row_may_be_the_only_row():
    assert check_ids.check_rows([as_dict(row(256, key="pooled"))]) == []


def test_two_rows_may_not_share_an_id():
    rows = [as_dict(row(124)), as_dict(row(124, key="rathian-3u"))]
    assert any("is already" in p for p in check_ids.check_rows(rows))


def test_a_permanent_id_may_not_skip_one():
    rows = [as_dict(row(124)), as_dict(row(126, key="rathian-3u"))]
    assert any("consecutive" in p for p in check_ids.check_rows(rows))


def test_a_pooled_id_fills_no_permanent_gap():
    # 125 is missing from the permanent range; a pooled row doesn't stand in for it.
    rows = [as_dict(row(124)), as_dict(row(256, key="pooled"))]
    assert check_ids.check_rows(rows) == []
    rows = [as_dict(row(124)), as_dict(row(126, key="rathian-3u")), as_dict(row(256, key="pooled"))]
    assert any("consecutive" in p for p in check_ids.check_rows(rows))


def test_a_stand_in_is_an_mh4u_id():
    rows = [as_dict(row(124, stand_in="124"))]
    assert any("stand_in" in p for p in check_ids.check_rows(rows))


def test_an_unknown_kind_has_no_range_yet():
    rows = [as_dict(row(124, kind="map"))]
    assert any("no id range" in p for p in check_ids.check_rows(rows))


def test_a_file_kind_the_record_does_not_have_is_refused():
    problems = check_ids.check_rows([as_dict(row(124, files="model,wings"))])
    assert any("wings" in p and "isn't one of" in p for p in problems), problems


def test_a_file_kind_may_not_be_listed_twice():
    problems = check_ids.check_rows([as_dict(row(124, files="model,motions,model"))])
    assert any("'model' is listed twice" in p for p in problems), problems


def test_a_port_that_ships_no_files_is_refused():
    problems = check_ids.check_rows([as_dict(row(124, files=""))])
    assert any("files is empty" in p for p in problems), problems


def test_motions_must_say_which_slots_it_ships():
    problems = check_ids.check_rows([as_dict(row(124, files="model,motions"))])
    assert any("motions needs the slots" in p for p in problems), problems


@pytest.mark.parametrize("value", ["7", "0,7", "three", "4-2"])
def test_a_motions_slot_outside_the_six_slots_is_refused(value):
    problems = check_ids.check_rows([as_dict(row(124, files=f"model,motions={value}"))])
    assert any("not a slot or a range" in p or "isn't in 0..5" in p for p in problems), problems


@pytest.mark.parametrize("value", ["0,0", "0-2,1"])
def test_a_motions_slot_may_not_be_named_twice(value):
    problems = check_ids.check_rows([as_dict(row(124, files=f"model,motions={value}"))])
    assert any("names a slot twice" in p for p in problems), problems


def test_motions_takes_the_slots_it_ships_sparse_and_as_ranges():
    assert check_ids.motion_slots("model,motions=0-4") == [0, 1, 2, 3, 4]
    assert check_ids.motion_slots("model,motions=0,2,3,4") == [0, 2, 3, 4]
    assert check_ids.motion_slots("model") == []
    assert check_ids.motion_mask({"files": "model,motions=0,2,3,4"}) == 0x1D


def test_only_motions_takes_a_value():
    problems = check_ids.check_rows([as_dict(row(124, files="model=1,motions=0-4"))])
    assert any("only motions takes a value" in p for p in problems), problems


def test_the_header_carries_the_kinds_each_port_ships(tmp_path):
    registry = tmp_path / "registry.csv"
    header = tmp_path / "ids.h"
    modules = tmp_path / "modules.h"
    write_registry(registry, [row(124), row(125, key="rathian-3u", files="model,motions=0-2,tail")])
    args = ["--registry", str(registry), "--header", str(header), "--modules-header", str(modules)]
    assert check_ids.main(args + ["--write"]) == 0
    text = header.read_text()
    assert "#define MHUC_FILES_MODEL 0x0001u" in text
    assert "#define MHUC_FILES_MOTIONS 0x0002u" in text
    assert "#define MHUC_FILES_CMD 0x0040u" in text
    assert "#define MHUC_MOTION_SLOT(slot) (1u << (slot))" in text
    assert ("{124, 1, 0x1fu, /* slots 0, 1, 2, 3, 4 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | "
            "MHUC_FILES_TAIL | MHUC_FILES_CMD},") in text
    assert ("{125, 1, 0x07u, /* slots 0, 1, 2 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | "
            "MHUC_FILES_TAIL},") in text


def test_the_header_the_registry_generates_has_both_arrays(tmp_path, capsys):
    registry = tmp_path / "registry.csv"
    header = tmp_path / "ids.h"
    modules = tmp_path / "modules.h"
    write_registry(registry, [row(124), row(125, key="rathian-3u"), row(256, key="pooled")])
    args = ["--registry", str(registry), "--header", str(header), "--modules-header", str(modules)]
    assert check_ids.main(args + ["--write"]) == 0
    text = header.read_text()
    assert "MHUC_MONSTER_ID_RATHIAN_GU 124" in text
    assert "MHUC_MONSTER_COUNT 2" in text
    assert "MHUC_POOLED_MONSTER_COUNT 1" in text
    assert "static const MhucMonsterId mhuc_monster_ids[MHUC_MONSTER_COUNT]" in text
    assert "static const MhucMonsterId mhuc_pooled_monster_ids[MHUC_POOLED_MONSTER_COUNT]" in text
    assert ("{256, 1, 0x1fu, /* slots 0, 1, 2, 3, 4 */ MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | "
            "MHUC_FILES_TAIL | MHUC_FILES_CMD},") in text
    assert "MHUC_MONSTER_ID_POOLED 256" in text
    assert check_ids.main(args) == 0
    # A stale header is refused, so the runtime can never build from another id set.
    header.write_text(text.replace("124", "126"))
    assert check_ids.main(args) == 1
    assert "isn't what the registry generates" in capsys.readouterr().out


def test_the_module_table_has_one_entry_per_registered_id(tmp_path, capsys):
    registry = tmp_path / "registry.csv"
    header = tmp_path / "ids.h"
    modules = tmp_path / "modules.h"
    module_dir = tmp_path / "monsters"
    module_dir.mkdir()
    write_registry(registry, [row(124), row(125, key="rathian-3u"), row(256, key="pooled")])
    args = ["--registry", str(registry), "--header", str(header), "--modules-header", str(modules),
            "--module-dir", str(module_dir)]
    assert check_ids.main(args + ["--write"]) == 0
    text = modules.read_text()
    # The permanent ids first, then the pooled ones; a row per registered id, 0 without a module.
    assert "#define MHUC_MODULE_COUNT 3" in text
    assert '{124, "rathian-gu", 0},' in text
    assert '{125, "rathian-3u", 0},' in text
    assert '{256, "pooled", 0},' in text
    assert text.index('"rathian-gu"') < text.index('"rathian-3u"') < text.index('"pooled"')
    # The runtime checks this count against ids.h, so a missing or extra row must be caught.
    assert check_ids.main(args) == 0
    modules.write_text(text.replace("{256, \"pooled\", 0},", ""))
    assert check_ids.main(args) == 1
    assert "modules.h isn't what the registry generates" in capsys.readouterr().out


def test_a_monster_module_gives_its_row_the_module_ops(tmp_path):
    registry = tmp_path / "registry.csv"
    header = tmp_path / "ids.h"
    modules = tmp_path / "modules.h"
    module_dir = tmp_path / "monsters"
    module_dir.mkdir()
    (module_dir / "rathian-gu.c").write_text(
        "const struct MhucModuleOps mhuc_module_rathian_gu = {0};\n", encoding="utf-8")
    write_registry(registry, [row(124), row(125, key="rathian-3u")])
    args = ["--registry", str(registry), "--header", str(header), "--modules-header", str(modules),
            "--module-dir", str(module_dir)]
    assert check_ids.main(args + ["--write"]) == 0
    text = modules.read_text()
    assert "extern const struct MhucModuleOps mhuc_module_rathian_gu;" in text
    assert '{124, "rathian-gu", &mhuc_module_rathian_gu},' in text
    assert '{125, "rathian-3u", 0},' in text


def test_a_module_file_without_a_registry_row_is_refused(tmp_path, capsys):
    registry = tmp_path / "registry.csv"
    module_dir = tmp_path / "monsters"
    module_dir.mkdir()
    (module_dir / "giadrome-gu.c").write_text("int not_a_module;\n", encoding="utf-8")
    write_registry(registry, [row(124)])
    args = ["--registry", str(registry), "--header", str(tmp_path / "ids.h"),
            "--modules-header", str(tmp_path / "modules.h"), "--module-dir", str(module_dir)]
    assert check_ids.main(args) == 1
    assert "giadrome-gu.c is a module with no monster row in the registry" in capsys.readouterr().out


def test_a_module_file_must_export_its_symbol(tmp_path, capsys):
    registry = tmp_path / "registry.csv"
    module_dir = tmp_path / "monsters"
    module_dir.mkdir()
    (module_dir / "rathian-gu.c").write_text("int not_a_module;\n", encoding="utf-8")
    write_registry(registry, [row(124)])
    args = ["--registry", str(registry), "--header", str(tmp_path / "ids.h"),
            "--modules-header", str(tmp_path / "modules.h"), "--module-dir", str(module_dir)]
    assert check_ids.main(args) == 1
    assert "doesn't export mhuc_module_rathian_gu" in capsys.readouterr().out


def test_the_registry_gives_giadrome_the_slots_it_borrows():
    with open(os.path.join(ROOT, "data", "ids", "registry.csv"), newline="", encoding="utf-8") as f:
        rows = [as_dict(r) for r in list(csv.reader(f))[1:]]
    giadrome = next(r for r in rows if r["id"] == "126")
    assert giadrome["key"] == "giadrome-gu"
    assert (giadrome["source_game"], giadrome["source_key"]) == ("mhxx", "em034")
    assert giadrome["stand_in"] == "15"      # MH4U's Great Jaggi
    assert check_ids.motion_slots(giadrome["files"]) == [0, 2, 3, 4]


def test_the_pooled_fixture_is_a_registry_the_checker_accepts():
    with open(POOLED_FIXTURE, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert tuple(rows[0]) == COLUMNS
    assert check_ids.check_rows([as_dict(r) for r in rows[1:]]) == []
    assert any(row[1] == "256" for row in rows[1:]), rows


def test_the_repository_registry_and_its_header_agree():
    res = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_ids.py")], cwd=ROOT,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "4 permanent monsters" in res.stdout
    assert "0 pooled" in res.stdout
