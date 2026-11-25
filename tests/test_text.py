"""The ported monsters' text table: the notes sources and the mod's built table."""
from __future__ import annotations

import os

import check_text
import pytest

from mhuc import monstertext

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def registry(rows):
    return [{"kind": "monster", "id": str(i), "key": k, "source_game": g, "source_key": "em001",
             "name": n, "stand_in": "1", "files": "model", "notes": ""}
            for i, k, g, n in rows]


def notes(*rows):
    return [dict(zip(monstertext.COLUMNS, r, strict=True)) for r in rows]


def row(ident, game="mhxx", source="table/HN_MonsterListMsg_jpn.gmd", entry="", index="34"):
    return (str(ident), game, source, entry, index)


REGISTRY = registry([(124, "rathian-gu", "mhxx", "Rathian"),
                     (125, "rathian-3u", "mh3u", "Rathian")])


def test_the_repository_notes_table_covers_every_ported_monster():
    assert monstertext.check(monstertext.registry_rows(), monstertext.read_notes()) == []


def test_a_ported_monster_without_a_notes_source_is_refused():
    problems = monstertext.check(REGISTRY, notes(row(124)))
    assert any("id 125" in p and "no notes source" in p for p in problems), problems


def test_a_notes_source_for_an_unported_id_is_refused():
    problems = monstertext.check(REGISTRY, notes(row(124), row(125, "mh3u"), row(126)))
    assert any("126" in p and "isn't a ported monster" in p for p in problems), problems


def test_a_notes_source_must_name_its_registry_game():
    problems = monstertext.check(REGISTRY, notes(row(124), row(125, "mhxx")))
    assert any("source_game" in p for p in problems), problems


def test_a_source_path_is_relative_to_the_romfs():
    problems = monstertext.check(REGISTRY, notes(row(124, source="/table/x.gmd"), row(125, "mh3u")))
    assert any("leading /" in p for p in problems), problems


@pytest.mark.parametrize("index", ["-1", "x"])
def test_a_source_index_is_a_non_negative_number(index):
    problems = monstertext.check(REGISTRY, notes(row(124, index=index), row(125, "mh3u")))
    assert any("source_index" in p for p in problems), problems


def test_a_notes_row_may_not_repeat_an_id():
    problems = monstertext.check(REGISTRY, notes(row(124), row(125, "mh3u"), row(124)))
    assert any("already" in p for p in problems), problems


def test_the_mod_text_table_round_trips():
    entries = [monstertext.TextEntry(124, "Rathian", "line one\nline two"),
               monstertext.TextEntry(125, "Rathian", "notes")]
    table = monstertext.read_mod_text(monstertext.write(entries))
    assert table == entries


def test_the_mod_text_table_refuses_a_truncated_entry():
    data = monstertext.write([monstertext.TextEntry(124, "Rathian", "notes")])
    with pytest.raises(monstertext.TextError, match="inside an entry"):
        monstertext.read_mod_text(data[:-2])


def test_the_builder_refuses_to_write_in_the_repository(tmp_path):
    entries = [monstertext.TextEntry(124, "Rathian", "notes")]
    with pytest.raises(monstertext.TextError, match="outside the repository"):
        monstertext.write_file(os.path.join(ROOT, "text.bin"), entries)


def test_the_checker_refuses_a_mod_table_that_differs_from_the_registry(tmp_path):
    path = tmp_path / "monster_text.bin"
    path.write_bytes(monstertext.write([monstertext.TextEntry(124, "Rathian", "notes"),
                                        monstertext.TextEntry(125, "Wyvern", "notes")]))
    problems = check_text.check_mod(str(path), REGISTRY, notes(row(124), row(125, "mh3u")))
    assert any("the registry says" in p for p in problems), problems


def test_the_checker_refuses_a_mod_table_missing_a_ported_id(tmp_path):
    path = tmp_path / "monster_text.bin"
    path.write_bytes(monstertext.write([monstertext.TextEntry(124, "Rathian", "notes")]))
    problems = check_text.check_mod(str(path), REGISTRY, notes(row(124), row(125, "mh3u")))
    assert any("no entry for id 125" in p for p in problems), problems
