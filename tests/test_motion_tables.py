"""tools/check_motion_tables.py: the generated motion table is checked, never edited."""
from __future__ import annotations

import os

import check_motion_tables
import monster_motions
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = os.path.join(ROOT, "mods", "monster_motions", "src", "motions.h")
REGISTRY = os.path.join(ROOT, "data", "ids", "registry.csv")


def text() -> str:
    with open(HEADER, encoding="utf-8") as f:
        return f.read()


def registry() -> list[dict]:
    return monster_motions.read_registry(REGISTRY)


def problems_with(old: str, new: str) -> list[str]:
    changed = text().replace(old, new, 1)
    assert changed != text(), f"the header no longer holds {old!r}"
    return check_motion_tables.check(changed, registry())


def test_the_checked_in_table_passes():
    assert check_motion_tables.main([]) == 0


@pytest.mark.parametrize("old, new, message", [
    ("    {13, 5, 0x002, 0x013},", "    {13, 5, 0x002, 0x013},\n    {13, 5, 0x002, 0x013},", "appear twice"),
    ("    {1, 5, 0x011, 0x014},", "    {0, 5, 0x011, 0x014},", "aren't sorted"),
    ("    {13, 5, 0x002, 0x013},", "    {13, 5, 0x2002, 0x013},", "motion 0x2002 is out of range"),
    ("    {125, 96, 19, 174, 117, 2, 57,", "    {125, 95, 19, 174, 117, 2, 57,", "entry_count 95"),
    ("    {125, 96, 19, 174, 117, 2, 57,", "    {125, 96, 19, 175, 117, 2, 57,", "isn't R1's 174"),
    ("    0x0724, /* 7/36 */", "    0x0624, /* 6/36 */", "isn't category 7"),
    ("    0x0724, /* 7/36 */", "    0x0d05, /* 13/5 */", "both translated and left out"),
    ("    {124, 0, 0, 273, 167, 167, 106,", "    {126, 0, 0, 273, 167, 167, 106,", "aren't the registry's"),
])
def test_a_corrupted_table_is_refused(old, new, message):
    problems = problems_with(old, new)
    assert any(message in p for p in problems), problems


def test_a_table_without_the_generator_marker_is_refused():
    changed = text().split("\n", 1)[1]
    assert any("no generated marker" in p for p in check_motion_tables.check(changed, registry()))


def test_a_cut_short_table_is_refused():
    changed = text().split("#define MHUC_PORTED_MOTIONS_COUNT")[0]
    assert any("cut short" in p for p in check_motion_tables.check(changed, registry()))


def test_the_header_must_be_what_the_generator_writes(tmp_path, monkeypatch):
    reg = tmp_path / "registry.csv"
    reg.write_text("kind,id,key,source_game,source_key,name,stand_in,notes\n"
                   "monster,124,rathian-gu,mh3u,em001,Rathian,1,\n"
                   "monster,125,rathian-3u,mh3u,em001,Rathian,1,\n")
    a = tmp_path / "a.tsv"
    a.write_text(monster_motions.HEADER + "13\t5\t0x1000\t2\tconstant\n1\t11\t0x1000\t17\tconstant\n")
    b = tmp_path / "b.tsv"
    b.write_text(monster_motions.HEADER + "13\t5\t0x2000\t19\tconstant\n1\t11\t0x2000\t17\tconstant\n")
    mapping = tmp_path / "map.tsv"
    mapping.write_text("# cat\tidx\tmotion_a\tmotion_b\thow\tsignature_a\tsignature_b\n"
                       "13\t5\t2\t19\tsame\t\t\n")
    monkeypatch.setitem(check_motion_tables.R1_COUNTS, "mh3u",
                        dict(common=2, compared=2, same_index=1, not_compared=0, unresolved=0))
    tables = monster_motions.tables_from(
        monster_motions.read_registry(str(reg)), monster_motions.read_rows(str(a)),
        {"mh3u": (monster_motions.read_rows(str(b)), monster_motions.read_mapping(str(mapping)))})
    header = tmp_path / "motions.h"
    header.write_text(monster_motions.render_header(tables))
    args = ["--header", str(header), "--registry", str(reg), "--mh4u", str(a),
            "--source", "mh3u", str(b), str(mapping)]
    assert check_motion_tables.main(args) == 0
    header.write_text(header.read_text().replace("0x013", "0x014", 1))
    assert check_motion_tables.main(args) == 1
