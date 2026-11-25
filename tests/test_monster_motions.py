"""reference/monster_motions.py: R1's counts and the handler scan's rules must not drift."""
from __future__ import annotations

import collections
import os
import struct
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_motions  # noqa: E402
import monster_versions  # noqa: E402


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


def test_placement_takes_an_elsewhere_animation_from_the_source_game():
    """`elsewhere` is a fact about the target's own lists; the port still copies the source's
    animation from the source game's slot."""
    a = {(7, 1): dict(motion=0x41A, how="constant")}          # file 4, slot 26: empty
    b = {(7, 1): dict(motion=209, how="constant")}            # file 2, slot 9
    lmts_a = [[None] * 100 for _ in range(5)]
    lmts_a[0][3] = (175, -1, 42)                              # the same animation, another slot
    lmts_b = [[None] * 30 for _ in range(3)]
    lmts_b[2][9] = (175, -1, 42)
    s = monster_motions.content_split(a, b, "mh4u", lmts_a, "mh3u", lmts_b)
    rows, unresolved = monster_motions.placement(s, "mh4u", "mh3u")
    assert unresolved == []
    assert rows == [dict(target=(4, 26), source=(2, 9), how="elsewhere", actions=[(7, 1)])]


def lmt(version: int = 67) -> bytes:
    """One animation (frames 1, loop 0, no tracks) at offset 12."""
    return (b"LMT\0" + struct.pack("<HH", version, 1) + struct.pack("<I", 12)
            + struct.pack("<IIii", 0, 0, 1, 0) + bytes(44))


class FakeFiles:
    """Only what lmts() reads: the archive's entries, each with a type, a path and data."""

    def __init__(self, entries):
        self._entries = entries

    def entries(self, game, path):
        return self._entries


def entry(path: str, data: bytes) -> SimpleNamespace:
    return SimpleNamespace(type_id=monster_versions.LMT_CLASS, path=path.replace("/", "\\"), data=data)


def test_motion_lists_are_indexed_by_the_file_number_each_game_encodes():
    # MH3U names its lists mot_emNNN_{file}00 and packs a motion index as file * 100 + slot.
    files = FakeFiles([entry("enemy/em001/mot/mot_em001_000", lmt(66)),
                       entry("enemy/em001/mot/mot_em001_100", lmt(66))])
    lists = monster_versions.lmts(files, "mh3u", "em001")
    assert len(lists) == 2 and all(x == [(1, 0, 0)] for x in lists), lists

    # MH4U names them emNNN_{file} and a variant's archive holds the base's; a missing file stays None.
    files = FakeFiles([entry("enemy/em001/mot/em001_0", lmt()),
                       entry("enemy/em001/mot/em001_2", lmt())])
    lists = monster_versions.lmts(files, "mh4u", "em003")
    assert len(lists) == 3
    assert lists[0] == [(1, 0, 0)] and lists[1] is None and lists[2] == [(1, 0, 0)], lists


def test_an_animation_is_the_same_by_its_frames_and_loop_not_its_track_count():
    # MH4U's Zinogre animations carry 46 tracks to MH3U's 37 for the same motion.
    assert monster_motions.same_motion((345, -1, 46), (345, -1, 37))
    assert not monster_motions.same_motion((347, 0, 42), (489, 62, 42))


def test_a_category_7_id_with_a_different_signature_is_not_resolved():
    # Category 7's shared handler can start more than one motion, so its first constant is not
    # the whole move: a differing signature there is unresolved, not a different animation.
    a = {(7, 2): {"motion": 0, "how": "constant"}}
    b = {(7, 2): {"motion": 100, "how": "constant"}}
    same_a = [[(189, -1, 46)], [(1, 0, 1)]]
    same_b = [[(69, -1, 37)], [(1, 0, 1)]]
    split = monster_motions.content_split(a, b, "mh4u", same_a, "mh3u", same_b)
    assert split["different"] == []
    assert [x[0] for x in split["unresolved"]] == [(7, 2)]

    a[(3, 2)] = {"motion": 0, "how": "constant"}
    b[(3, 2)] = {"motion": 100, "how": "constant"}
    split = monster_motions.content_split(a, b, "mh4u", same_a, "mh3u", same_b)
    assert [x[0] for x in split["different"]] == [(3, 2)]
