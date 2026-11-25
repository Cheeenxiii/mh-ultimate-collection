"""reference/monster_motions.py: R1's counts and the handler scan's rules must not drift."""
from __future__ import annotations

import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import check_motion_tables  # noqa: E402
import monster_motions  # noqa: E402
import pytest


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


def test_repack_motion_addresses_the_converted_list_in_mh4u_packing():
    # MH3U packs file * 100 + slot; the converted list keeps the file order, MH4U file << 8 | slot.
    assert monster_motions.repack_motion("mh3u", 26) == 26
    assert monster_motions.repack_motion("mh3u", 209) == 0x209
    assert monster_motions.repack_motion("mh3u", 202) == 0x202
    # MHXX already packs file << 8 | slot, so its animations keep their index.
    assert monster_motions.repack_motion("mhxx", 0x41A) == 0x41A


def config(tmp_path, a, b, mapping):
    a_path = tmp_path / "a.tsv"
    b_path = tmp_path / "b.tsv"
    map_path = tmp_path / "map.tsv"
    a_path.write_text(monster_motions.HEADER + "".join(a))
    b_path.write_text(monster_motions.HEADER + "".join(b))
    map_path.write_text("# cat\tidx\tmotion_a\tmotion_b\thow\tsignature_a\tsignature_b\n" + "".join(mapping))
    return monster_motions.read_rows(str(a_path)), monster_motions.read_rows(str(b_path)), \
        monster_motions.read_mapping(str(map_path))


def test_the_table_translates_what_r1_resolved_and_leaves_the_rest_out(tmp_path):
    a = ["13\t5\t0x1000\t2\tconstant\n", "13\t6\t0x1000\t2\tconstant\n",
         "13\t8\t0x1000\t19\tconstant\n", "7\t36\t0x1000\t1052\tconstant\n",
         "1\t11\t0x1000\t17\tconstant\n", "8\t\t0x1000\t1027\tconstant\n",
         "2\t0\t0x1000\t\tnone\n", "3\t0\t0x1000\t\tno-handler\n"]
    b = ["13\t5\t0x2000\t19\tconstant\n", "13\t6\t0x2000\t26\tconstant\n",
         "13\t8\t0x2000\t26\tconstant\n", "7\t36\t0x2000\t211\tconstant\n",
         "1\t11\t0x2000\t17\tconstant\n", "8\t\t0x2000\t202\tconstant\n",
         "2\t0\t0x2000\t\tnone\n", "3\t0\t0x2000\t\tno-handler\n"]
    mapping = ["13\t5\t2\t19\tsame\t(1, 0, 1)\t(1, 0, 1)\n",
               "13\t6\t2\t26\tdifferent\t(1, 0, 1)\t(2, 0, 1)\n",
               "13\t8\t19\t26\tdifferent\t(1, 0, 1)\t(2, 0, 1)\n",
               "7\t36\t1052\t211\tunresolved\t\t\n",
               "8\t\t1027\t202\tsame\t(1, 0, 1)\t(1, 0, 1)\n"]
    rows_a, rows_b, rows_map = config(tmp_path, a, b, mapping)
    monster = dict(id="125", key="rathian-3u", name="Rathian", source_game="mh3u", source_key="em001")
    table = monster_motions.build_table(monster, rows_a, rows_b, rows_map, "mh3u")
    assert table["entries"] == [
        dict(cat=8, index=monster_motions.NO_INDEX, motion=0x403, source=0x202),
        dict(cat=13, index=5, motion=2, source=0x13),
        dict(cat=13, index=6, motion=2, source=0x1a),
        dict(cat=13, index=8, motion=0x13, source=0x1a),
    ]
    assert table["unresolved"] == [dict(cat=7, index=36, motion=0x41c)]
    assert (table["common"], table["compared"], table["same_index"], table["not_compared"]) == (8, 6, 1, 2)


def test_a_mapping_that_does_not_match_the_inventories_is_refused(tmp_path):
    a = ["13\t5\t0x1000\t2\tconstant\n", "13\t6\t0x1000\t2\tconstant\n", "1\t11\t0x1000\t17\tconstant\n"]
    b = ["13\t5\t0x2000\t19\tconstant\n", "13\t6\t0x2000\t26\tconstant\n", "1\t11\t0x2000\t17\tconstant\n"]
    monster = dict(id="125", key="rathian-3u", name="Rathian", source_game="mh3u", source_key="em001")
    good = ["13\t5\t2\t19\tsame\t\t\n", "13\t6\t2\t26\tsame\t\t\n"]
    rows_a, rows_b, rows_map = config(tmp_path, a, b, good)
    assert monster_motions.build_table(monster, rows_a, rows_b, rows_map, "mh3u")["entries"]
    for bad in (
        ["1\t11\t17\t17\tsame\t\t\n"],                    # a same-index id needs no row
        ["3\t0\t2\t19\tsame\t\t\n"],                      # not an id both games have
        ["13\t5\t2\t19\tsame\t\t\n", "13\t5\t2\t19\tsame\t\t\n"],   # 13/5 twice
        ["13\t5\t2\t19\tsame\t\t\n", "13\t6\t3\t26\tsame\t\t\n"],   # 13/6 asks 2, not 3
    ):
        rows_a, rows_b, rows_map = config(tmp_path, a, b, bad)
        with pytest.raises(ValueError):
            monster_motions.build_table(monster, rows_a, rows_b, rows_map, "mh3u")
    # 13/6's indices differ and the mapping has no row for it.
    rows_a, rows_b, rows_map = config(tmp_path, a, b, ["13\t5\t2\t19\tsame\t\t\n"])
    with pytest.raises(ValueError):
        monster_motions.build_table(monster, rows_a, rows_b, rows_map, "mh3u")


def test_the_header_has_one_table_per_ported_monster():
    monster = dict(id="125", key="rathian-3u", name="Rathian", source_game="mh3u", source_key="em001")
    table = dict(monster=monster, source="mh3u",
                 entries=[dict(cat=13, index=5, motion=2, source=0x13)],
                 unresolved=[dict(cat=7, index=36, motion=0x41c)],
                 common=174, compared=117, same_index=2, not_compared=57)
    other = dict(monster=dict(monster, id="124", key="rathian-gu", source_game="mhxx", source_key="em001"),
                 source="mhxx", entries=[], unresolved=[], common=273, compared=167,
                 same_index=167, not_compared=106)
    text = monster_motions.render_header([table, other])
    assert "#define MHUC_PORTED_MOTIONS_COUNT 2" in text
    assert "static const MhucMotion mhuc_motions_124 = NULL;" not in text
    assert "static const MhucMotion *const mhuc_motions_124 = NULL;" in text
    assert "    {13, 5, 0x002, 0x013}," in text
    assert "    0x0724, /* 7/36 */" in text
    assert "{125, 1, 1, 174, 117, 2, 57, mhuc_motions_125, mhuc_unresolved_125}," in text
    parsed = check_motion_tables.parse_header(text)
    assert parsed["count"] == 2
    assert parsed["meta"][0]["id"] == 125
    assert parsed["tables"][125]["entries"] == [dict(category=13, index=5, motion=2, source=0x13)]
