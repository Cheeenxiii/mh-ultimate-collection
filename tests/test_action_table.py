"""tools/check_action_map.py: the generated action-id map must not drift from the per-id
table reference/README.md records, and the checker must name each way it can."""
from __future__ import annotations

import os

import check_action_map as cam
import monster_handlers as mh

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = os.path.join(ROOT, "mods", "monster_actions", "src", "actions.h")


def checked_in() -> str:
    return open(HEADER, encoding="utf-8").read()


def problems(text: str) -> list[str]:
    return cam.check(text, mh.read_registry(cam.REGISTRY), cam.read_page(cam.PAGE))


def test_the_checked_in_map_agrees_with_the_page_and_the_registry():
    assert problems(checked_in()) == []
    assert cam.read_page(cam.PAGE) == {
        "0/4": "0/0", "7/64": "7/35", "7/87": "7/92", "7/93": "7/92",
        **{f"10/{n}": "10/7" for n in range(7)},
        "11/5": "11/0", "11/15": "11/0", "11/26": "11/0", "11/28": "11/0", "13/9": "0/3"}


def test_a_dropped_id_is_named():
    text = checked_in().replace("    {7, 64, 7, 35},\n", "")
    found = problems(text)
    assert any("7/64" in p and "not the 16" in p for p in found)


def test_a_changed_target_is_named():
    text = checked_in().replace("    {7, 64, 7, 35},", "    {7, 64, 7, 46},")
    found = problems(text)
    assert any("different target ['7/64']" in p for p in found)


def test_action_4_is_refused_even_when_it_replaces_an_entry():
    text = checked_in().replace("    {0, 4, 0, 0},", "    {4, 255, 4, 255},")
    found = problems(text)
    assert any("action 4 needs new C" in p for p in found)


def test_a_table_that_is_not_sorted_is_named():
    text = checked_in().replace("    {0, 4, 0, 0},\n    {7, 64, 7, 35},",
                                "    {7, 64, 7, 35},\n    {0, 4, 0, 0},")
    found = problems(text)
    assert any("not sorted" in p for p in found)


def test_the_header_is_exactly_what_the_generator_writes(tmp_path):
    text = checked_in()
    mapping = {mh.action_id((e["category"], e["index"])):
               mh.action_id((e["target_category"], e["target_index"]))
               for e in cam.parse_header(text)["tables"][125]}
    targets = tmp_path / "targets.tsv"
    targets.write_text(
        "# action\ttarget\thandler\tproof\tR1\tmh4u_handler\n"
        + "".join(f"{source}\t{target}\t0x006971c0\tbody match\t\t0x006e2764\n"
                  for source, target in mapping.items()),
        encoding="utf-8")
    assert cam.check_generator(text, str(targets), mh.read_registry(cam.REGISTRY)) == []
    stale = text.replace("    {7, 64, 7, 35},", "    {7, 64, 7, 46},")
    assert cam.check_generator(stale, str(targets), mh.read_registry(cam.REGISTRY)) != []
