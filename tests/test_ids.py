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


def write_registry(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(COLUMNS)
        writer.writerows(rows)


def row(ident, key="rathian-gu", stand_in="1", kind="monster", files="model,motions=5,tail,cmd"):
    return [kind, str(ident), key, "mhxx", "em001", "Rathian", stand_in, files, ""]


def as_dict(fields):
    return dict(zip(COLUMNS, fields, strict=True))


def test_a_valid_registry_passes():
    assert check_ids.check_rows([as_dict(row(124))]) == []


@pytest.mark.parametrize("ident", [123, 256])
def test_a_monster_id_outside_124_to_255_is_refused(ident):
    problems = check_ids.check_rows([as_dict(row(ident))])
    assert any("isn't in 124..255" in p for p in problems), problems


def test_two_rows_may_not_share_an_id():
    rows = [as_dict(row(124)), as_dict(row(124, key="rathian-3u"))]
    assert any("is already" in p for p in check_ids.check_rows(rows))


def test_monster_ids_may_not_skip_one():
    rows = [as_dict(row(124)), as_dict(row(126, key="rathian-3u"))]
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


def test_motions_must_say_how_many_slots_it_ships():
    problems = check_ids.check_rows([as_dict(row(124, files="model,motions"))])
    assert any("motions needs the number of slots" in p for p in problems), problems


@pytest.mark.parametrize("count", ["0", "7", "three"])
def test_a_motions_count_outside_the_six_slots_is_refused(count):
    problems = check_ids.check_rows([as_dict(row(124, files=f"model,motions={count}"))])
    assert any("isn't a slot count in 1..6" in p for p in problems), problems


def test_only_motions_takes_a_count():
    problems = check_ids.check_rows([as_dict(row(124, files="model=1,motions=5"))])
    assert any("only motions takes a count" in p for p in problems), problems


def test_the_header_carries_the_kinds_each_port_ships(tmp_path):
    registry = tmp_path / "registry.csv"
    header = tmp_path / "ids.h"
    write_registry(registry, [row(124), row(125, key="rathian-3u", files="model,motions=3,tail")])
    args = ["--registry", str(registry), "--header", str(header)]
    assert check_ids.main(args + ["--write"]) == 0
    text = header.read_text()
    assert "#define MHUC_FILES_MODEL 0x0001u" in text
    assert "#define MHUC_FILES_MOTIONS 0x0002u" in text
    assert "#define MHUC_FILES_CMD 0x0040u" in text
    assert ("{124, 1, 5, MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | MHUC_FILES_TAIL | "
            "MHUC_FILES_CMD},") in text
    assert "{125, 1, 3, MHUC_FILES_MODEL | MHUC_FILES_MOTIONS | MHUC_FILES_TAIL}," in text


def test_the_header_the_registry_generates_is_what_the_check_compares(tmp_path, capsys):
    registry = tmp_path / "registry.csv"
    header = tmp_path / "ids.h"
    write_registry(registry, [row(124), row(125, key="rathian-3u")])
    args = ["--registry", str(registry), "--header", str(header)]
    assert check_ids.main(args + ["--write"]) == 0
    assert "MHUC_MONSTER_ID_RATHIAN_GU 124" in header.read_text()
    assert check_ids.main(args) == 0
    # A stale header is refused, so the plugin can never build from another id set.
    header.write_text(header.read_text().replace("124", "126"))
    assert check_ids.main(args) == 1
    assert "isn't what the registry generates" in capsys.readouterr().out


def test_the_repository_registry_and_its_header_agree():
    res = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_ids.py")], cwd=ROOT,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "2 monsters" in res.stdout
