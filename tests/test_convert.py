"""mhuc convert: an MHXX quest (synthetic parts) into an MH4U .mib model, ids through id tables."""
from __future__ import annotations

import json

import pytest
from test_quest_tools import build_mib4

from mhuc import cli
from mhuc.quests import convert, mibwrite, quest

PARTS = {
    "mib": {"map": 3, "stars": 4, "time_min": 50, "fee": 300, "reward": 2700, "sub_reward": 0},
    "sem": {"b_m03em001_00.sem": {"count": 1, "round": 0, "area": 5, "angle": 0.0, "pos": [1.0, 2.0, 3.0]},
            "b_m03em027_00.sem": {"count": 1, "round": 1, "area": 2, "angle": 0.0, "pos": [4.0, 5.0, 6.0]}},
    "esl": {"e.esl": [[{"monster": 9, "pos": [7.0, 8.0, 9.0], "param": 0}]]},
    "rem": {"rem_1.rem": {"flags": [], "slots": [[100, 2, 30], [0, 0, 0]]}},
    "supply": [[200, 3, 0], [0, 0, 0]],
}
TABLES = {"monster": {"em001": "1", "em027": "0x1B", "small:9": "40"}, "map": {"3": "7"},
          "area": {"3:5": "5", "3:2": "2", "3:esl0": "4"}, "item": {"100": "1100", "200": "1200"},
          "objective": {}}
TEXTS = {lang: {t: f"{lang} {t}" for t in quest.MIB4_TEXTS} for lang in quest.MIB4_LANGS}


def template() -> dict:
    return json.loads(json.dumps(mibwrite.model_to_json(mibwrite.mib4_model(build_mib4(60001)))))


def test_convert_maps_ids_and_builds():
    out = convert.convert_mhxx(PARTS, template(), TABLES, 61001, TEXTS)
    got = quest.parse_mib4(mibwrite.mib4_build(mibwrite.model_from_json(out)))
    stars = quest.parse_mib4(build_mib4(60001))["stars"]
    assert (got["quest_id"], got["stars"], got["time_min"], got["map"]) == (61001, stars, 50, 7)
    assert any(p.startswith("stars") for p in out["placeholders"])
    assert [[(d["monster"], d["area"]) for d in w] for w in got["large_waves"]] == [[(1, 5)], [(0x1B, 2)]]
    assert got["large_waves"][0][0]["pos"] == [1.0, 2.0, 3.0]
    assert got["small_areas"][0][0]["monster"] == 40
    assert got["rewards"]["main"] == [(30, 1100, 2)]
    assert got["supply"][0]["items"] == [(1200, 3)]
    assert got["text"]["ger"]["title"] == "ger title"
    assert out["placeholders"]


def test_convert_refuses_unmapped_ids():
    tables = dict(TABLES, monster={"em001": "1"}, item={})
    with pytest.raises(convert.ConvertError) as e:
        convert.convert_mhxx(PARTS, template(), tables, 61001, TEXTS)
    assert "monster:em027" in str(e.value) and "item:100" in str(e.value) and "item:200" in str(e.value)


def test_convert_needs_all_texts():
    with pytest.raises(convert.ConvertError):
        convert.convert_mhxx(PARTS, template(), TABLES, 61001, {"eng": TEXTS["eng"]})


def test_load_tables_and_cli(tmp_path, capsys):
    tdir = tmp_path / "t"
    tdir.mkdir()
    for name, rows in TABLES.items():
        lines = ["source,target,source_name,target_name,how"] + [f"{k},{v},,,test" for k, v in rows.items()]
        (tdir / f"{name}.csv").write_text("\n".join(lines) + "\n")
    assert convert.load_tables(str(tdir)) == TABLES
    files = {"q.json": {"q1.arc": PARTS}, "t.json": template(), "x.json": TEXTS}
    for n, obj in files.items():
        (tmp_path / n).write_text(json.dumps(obj))
    out = tmp_path / "o.json"
    args = ["convert", "quest", str(tmp_path / "q.json"), "--template", str(tmp_path / "t.json"),
            "--texts", str(tmp_path / "x.json"), "--id", "61002", "--tables", str(tdir), "--out", str(out)]
    assert cli.main(args) == 0
    assert cli.main(["mib", "import", str(out), str(tmp_path / "o.mib")]) == 0
    assert quest.parse_mib4((tmp_path / "o.mib").read_bytes())["quest_id"] == 61002
    assert cli.main(args[:-4] + ["--tables", str(tmp_path / "empty"), "--out", str(out)]) == 1
    assert cli.main(["convert"]) == 2
