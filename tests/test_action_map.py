"""reference/action_map.py: the shared-id map's classification and counts must not drift."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import action_map  # noqa: E402


def action(cat, idx, handler=None, args=None):
    return action_map.Action(cat, idx, handler, args or {})


def motion(index, how):
    return {"motion": index, "how": how}


def test_classify_says_what_each_pair_of_motion_kinds_needs():
    assert action_map.classify("constant", "constant", 257, 257) == action_map.SAME_INDEX
    assert action_map.classify("constant", "constant", 257, 258) == action_map.OTHER_INDEX
    assert action_map.classify("constant", "none", 5, None) == action_map.MHXX_MOTION
    assert action_map.classify("none", "constant", None, 5) == action_map.MH4U_MOTION
    assert action_map.classify("constant", "no-handler", 5, None) == action_map.MHXX_MOTION
    assert action_map.classify("no-handler", "constant", None, 5) == action_map.MH4U_MOTION
    assert action_map.classify("none", "none", None, None) == action_map.NO_MOTION
    assert action_map.classify("no-handler", "no-handler", None, None) == action_map.BOTH_INLINE
    assert action_map.classify("no-handler", "none", None, None) == action_map.MIXED
    assert action_map.classify("computed", "none", None, None) == action_map.MIXED


def test_read_actions_keeps_the_handler_and_case_arguments():
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
        f.write("# cat\tidx\tblock\tfn\tkind\thandler\tveneer\targs\tcalls\tcond\n")
        f.write("3\t17\t0x00800000\t0x00800000\ttail\t0x00801000\t0\t"
                "r1=1,r2=0\t0x00802000\t0\n")
        path = f.name
    try:
        action = action_map.read_actions(path)[(3, 17)]
    finally:
        os.unlink(path)
    assert action.handler == 0x00801000
    assert action.args == {"r1": 1, "r2": 0}


def test_an_id_mh4u_lacks_is_mhxx_only_and_needs_its_handler_unit():
    rows = action_map.build_map(
        {(3, 17): action(3, 17), (8, 0): action(8, 0, 0x5000)},
        {(3, 17): action(3, 17, 0x6000)},
        {(3, 17): motion(257, "constant"), (8, 0): motion(None, "none")},
        {(3, 17): motion(257, "constant")})
    by_key = {r.key: r for r in rows}
    assert by_key[(3, 17)].shared and by_key[(3, 17)].cls == action_map.SAME_INDEX
    assert not by_key[(8, 0)].shared and by_key[(8, 0)].cls == action_map.MHXX_ONLY
    assert by_key[(8, 0)].mh4u_handler is None
    summary = action_map.summarize(rows)
    assert summary["only"] == 1
    assert summary["units"] == {"0x00005000": [(8, 0)]}


def test_inline_actions_group_under_an_inline_unit():
    rows = action_map.build_map(
        {(17, None): action(17, None)},
        {},
        {(17, None): motion(None, "jump")},
        {})
    assert action_map.summarize(rows)["units"] == {"inline": [(17, None)]}


def test_case_block_argument_differences_are_reported():
    rows = action_map.build_map(
        {(3, 14): action(3, 14, args={"r1": 2, "r2": 0})},
        {(3, 14): action(3, 14, args={})},
        {(3, 14): motion(None, "none")},
        {(3, 14): motion(None, "no-handler")})
    summary = action_map.summarize(rows)
    assert not rows[0].args_same
    assert [key for key, _, _ in summary["arg_differ"]] == [(3, 14)]
    assert summary["counts"][action_map.MIXED] == 1


def test_the_summary_carries_no_motion_index():
    rows = action_map.build_map(
        {(3, 0): action(3, 0, 0x5000), (3, 1): action(3, 1, 0x5000)},
        {(3, 0): action(3, 0, 0x6000), (3, 1): action(3, 1, 0x6000)},
        {(3, 0): motion(0x1234, "constant"), (3, 1): motion(0x5678, "constant")},
        {(3, 0): motion(0x1234, "constant"), (3, 1): motion(0x5678, "none")})
    summary = action_map.summarize(rows)
    text = repr(summary)
    assert "4660" not in text and "22136" not in text   # 0x1234 and 0x5678 in decimal
    assert summary["counts"][action_map.SAME_INDEX] == 1
    assert summary["counts"][action_map.MHXX_MOTION] == 1
    # the map file itself does carry them: it is meant to stay outside the repository
    assert rows[0].tsv().split("\t")[7] == "4660"
