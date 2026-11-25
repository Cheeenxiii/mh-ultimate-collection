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


def test_motion_index_packs_the_lmt_file_and_slot():
    assert monster_motions.decode_motion("mh4u", 1030) == (4, 6)
    assert monster_motions.decode_motion("mhxx", 257) == (1, 1)
    assert monster_motions.decode_motion("mh3u", 26) == (0, 26)
    assert monster_motions.decode_motion("mh3u", 206) == (2, 6)


def test_same_motion_allows_the_skeletons_one_extra_track():
    assert monster_motions.same_motion((133, 0, 42), (133, 0, 42))
    assert monster_motions.same_motion((147, -1, 43), (147, -1, 42))
    assert not monster_motions.same_motion((347, 0, 42), (489, 62, 42))


def test_content_split_finds_same_elsewhere_and_unresolved():
    a = {
        (3, 17): dict(motion=0x101, how="constant"),     # file 1, slot 1
        (13, 5): dict(motion=0x002, how="constant"),     # file 0, slot 2
        (7, 1): dict(motion=0x41A, how="constant"),      # file 4, slot 26: empty
        (7, 36): dict(motion=0x41C, how="constant"),     # file 4, slot 28: empty
    }
    b = {
        (3, 17): dict(motion=26, how="constant"),        # file 0, slot 26
        (13, 5): dict(motion=19, how="constant"),        # file 0, slot 19
        (7, 1): dict(motion=209, how="constant"),        # file 2, slot 9
        (7, 36): dict(motion=211, how="constant"),       # file 2, slot 11
    }
    lmts_a = [[None] * 100 for _ in range(5)]
    lmts_a[0][2] = (347, 0, 42)
    lmts_a[1][1] = (133, 0, 42)
    lmts_a[4][30] = (175, -1, 42)
    lmts_b = [[None] * 30 for _ in range(3)]
    lmts_b[0][19] = (489, 62, 42)
    lmts_b[0][26] = (133, 0, 42)
    lmts_b[2][9] = (175, -1, 42)
    lmts_b[2][11] = (200, 0, 42)
    s = monster_motions.content_split(a, b, "mh4u", lmts_a, "mh3u", lmts_b)
    assert [x[0] for x in s["same"]] == [(3, 17)]
    assert [x[0] for x in s["different"]] == [(13, 5)]
    assert [x[0] for x in s["elsewhere"]] == [(7, 1)]
    assert [x[0] for x in s["unresolved"]] == [(7, 36)]


def test_content_split_records_where_the_animation_was_found_elsewhere():
    a = {(7, 1): dict(motion=0x41A, how="constant")}          # file 4, slot 26: empty
    b = {(7, 1): dict(motion=209, how="constant")}            # file 2, slot 9: empty too
    lmts_a = [[None] * 100 for _ in range(5)]
    lmts_b = [[None] * 30 for _ in range(3)]
    lmts_b[2][9] = (175, -1, 42)
    lmts_a[0][3] = (175, -1, 42)
    s = monster_motions.content_split(a, b, "mh4u", lmts_a, "mh3u", lmts_b)
    assert s["elsewhere"] == [((7, 1), 0x41A, 209, (175, -1, 42), (0, 3))]


def test_placement_groups_actions_by_target_slot_and_source():
    a = {
        (3, 17): dict(motion=0x101, how="constant"),     # file 1, slot 1
        (7, 6): dict(motion=0x010, how="constant"),      # file 0, slot 16
        (7, 7): dict(motion=0x010, how="constant"),      # the same target and source
        (9, 1): dict(motion=17, how="constant"),         # the same index in both games
    }
    b = {
        (3, 17): dict(motion=26, how="constant"),        # file 0, slot 26
        (7, 6): dict(motion=19, how="constant"),         # file 0, slot 19
        (7, 7): dict(motion=19, how="constant"),
        (9, 1): dict(motion=17, how="constant"),
    }
    lmts_a = [[None] * 100 for _ in range(5)]
    lmts_a[1][1] = (133, 0, 42)
    lmts_a[0][16] = (489, 62, 42)
    lmts_b = [[None] * 30 for _ in range(3)]
    lmts_b[0][26] = (133, 0, 42)
    lmts_b[0][19] = (489, 62, 42)
    s = monster_motions.content_split(a, b, "mh4u", lmts_a, "mh3u", lmts_b)
    rows, unresolved = monster_motions.placement(s, "mh4u", "mh3u")
    assert unresolved == []
    assert rows == [
        dict(target=(0, 16), source=(0, 19), how="same", actions=[(7, 6), (7, 7)]),
        dict(target=(0, 17), source=(0, 17), how="same-index", actions=[(9, 1)]),
        dict(target=(1, 1), source=(0, 26), how="same", actions=[(3, 17)]),
    ]


def test_placement_refuses_a_target_slot_two_animations_want():
    a = {
        (13, 5): dict(motion=2, how="constant"),         # both target file 0, slot 2
        (13, 6): dict(motion=2, how="constant"),
    }
    b = {
        (13, 5): dict(motion=19, how="constant"),
        (13, 6): dict(motion=26, how="constant"),
    }
    lmts_a = [[None] * 100 for _ in range(5)]
    lmts_a[0][2] = (347, 0, 42)
    lmts_b = [[None] * 30 for _ in range(3)]
    lmts_b[0][19] = (489, 62, 42)
    lmts_b[0][26] = (133, 0, 42)
    s = monster_motions.content_split(a, b, "mh4u", lmts_a, "mh3u", lmts_b)
    rows, unresolved = monster_motions.placement(s, "mh4u", "mh3u")
    assert unresolved == []
    assert all(r["how"] == "conflict" and r["target"] == (0, 2) for r in rows)
    assert [r["actions"] for r in rows] == [[(13, 5)], [(13, 6)]]
    assert [r["source"] for r in rows] == [(0, 19), (0, 26)]
