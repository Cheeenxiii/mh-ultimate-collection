"""reference/monster_motions.py: R1's counts and the handler scan's rules must not drift."""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_motions  # noqa: E402


def motion(value):
    return {"motion": value, "how": "constant"}


def test_compare_counts_same_different_and_not_compared():
    a = {
        (3, 17): motion(257),
        (7, 0): motion(1030),
        (1, 4): motion(16),
        (2, 0): {"motion": None, "how": "none"},
        (9, 1): motion(1036),
    }
    b = {
        (3, 17): motion(257),
        (7, 0): motion(1031),
        (1, 4): motion(16),
        (2, 0): motion(5),
        (9, 1): {"motion": None, "how": "no-handler"},
        (12, None): motion(1),
    }
    r = monster_motions.compare(a, b)
    assert r["common"] == 5
    assert r["same"] == [(1, 4), (3, 17)]
    assert r["different"] == [(7, 0)]
    assert r["skipped"] == collections.Counter({("none", "constant"): 1, ("constant", "no-handler"): 1})


def test_category_only_action_ids_print_without_an_index():
    assert monster_motions.fmt_id((8, None)) == "8"
    assert monster_motions.fmt_ids([(8, None), (3, 17)]) == "8 3/17"


def test_conditions_do_not_hide_a_register_write():
    assert monster_motions.conditionless("ldreq") == "ldr"
    assert monster_motions.conditionless("blne") == "bl"
    assert monster_motions.conditionless("bne") == "b"
    assert monster_motions.conditionless("movs") == "movs"
    assert monster_motions.conditionless("bl") == "bl"


def test_block_end_is_the_function_or_the_enclosing_one():
    table = {0x1000: 0x40, 0x2000: 0x20}
    assert monster_motions.block_end(0x1000, table, None) == 0x1040
    assert monster_motions.block_end(0x1010, table, None) == 0x1040
    assert monster_motions.block_end(0x1000, None, {0x1008, 0x1100}) == 0x1008
    assert monster_motions.block_end(0x1000, {}, None) == 0x1000 + monster_motions.SCAN_CAP
