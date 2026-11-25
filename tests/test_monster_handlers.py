"""reference/monster_handlers.py: the worklist's classification and the action-id map must not
drift from reference/README.md, which records them."""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_handlers as mh  # noqa: E402


def test_the_reference_tables_parse_to_the_counts_the_page_states():
    paired, lacking = mh.read_reference()
    assert len(paired) == 73 and len(lacking) == 28
    assert paired[0x00828828] == (0x0094E318, "call site of a paired handler")
    assert 0x00842A7C in lacking          # one of #55's 19


def test_a_category_only_action_is_written_without_an_index():
    assert mh.parse_action("4") == (4, None)
    assert mh.parse_action("7/64") == (7, 64)
    assert mh.action_name(4, None) == "4"
    assert mh.action_name(7, 64) == "7/64"


def test_a_source_data_pointer_is_marked_but_a_float_is_not():
    call = mh.Call(0x1000, 0x2000, {"r1": 0x00C4D800}, {"s0": 150.0})
    row = call.row()
    assert "r1=data:0x00c4d800" in row
    assert "s0=150" in row


def test_a_case_block_runs_to_its_terminator_and_a_function_to_its_next_entry():
    functions = {0x1000: 0x74, 0x1078: 0x10}      # the size is a little short
    assert mh.body(0x1000, functions) == (0x1000, 0x1078)
    far = {0x1000: 0x74, 0x2000: 0x10}
    assert mh.body(0x1000, far) == (0x1000, 0x1074)
    assert mh.body(0x1500, functions) == (0x1500, None)


def test_a_blocked_id_names_every_reason():
    unit = mh.Unit("7/64", 0x1000, "tail", False,
                   [mh.Call(0x10, 0x842A7C), mh.Call(0x20, 0x915D44, floats={"s0": 1.0}),
                    mh.Call(0x30, 0x84704C, ints={"r1": 0x00C4EE98}), mh.Call(0x40, 0x1234)],
                   [], [], [0x842A7C], [0x1234], [0x915D44], [0x84704C])
    assert unit.blocked
    reasons = unit.reasons()
    for text in ("#55 0x00842a7c", "float arg to 0x00915d44", "source data to 0x0084704c",
                 "unmapped 0x00001234"):
        assert text in reasons


def test_a_clean_id_is_translatable():
    unit = mh.Unit("13/9", 0x1000, "tail", False, [mh.Call(0x10, 0x915D44)], [],
                   [(0x915D44, 0x94E318, "map")], [], [], [], [])
    assert not unit.blocked
    assert unit.reasons() == "translatable"


def test_the_map_picks_the_shared_action_with_the_same_handler():
    units = {(0, 4): 0xA0, (0, 0): 0xA0, (1, 0): 0xB0}
    target = {(0, 0): "handler"}
    motions = {(0, 4): "", (0, 0): ""}
    rows = mh.target_rows(units, {}, target, motions, (0, 4))
    assert rows == [((0, 0), "body match",
                     "R1 not comparable (a handler starts no constant motion)", "handler")]


def test_the_map_uses_the_wrapper_tail_when_no_shared_id_reaches_the_same_handler():
    units = {(11, 15): 0x687E88, (11, 0): 0x84D864}
    tails = {(11, 15): 0x84D864}
    target = {(11, 0): "handler"}
    motions = {(11, 15): "", (11, 0): ""}
    rows = mh.target_rows(units, tails, target, motions, (11, 15))
    assert rows == [((11, 0), "tail match",
                     "R1 not comparable (a handler starts no constant motion)", "handler")]


def test_the_map_needs_a_shared_action_or_it_is_new_code():
    assert mh.target_rows({(4, None): 0x83CC24}, {}, {}, {}, (4, None)) == []


def test_the_map_names_the_motion_when_r1_can_compare_it():
    units = {(7, 64): 0x6971C0, (7, 65): 0x6971C0}
    target = {(7, 65): "h"}
    motions = {(7, 64): "42", (7, 65): "42"}
    rows = mh.target_rows(units, {}, target, motions, (7, 64))
    assert rows[0][2] == "R1 same motion 42"


def test_an_inventory_tsv_and_a_motion_tsv_are_read_by_the_columns_the_tools_write():
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
        f.write("# cat\tidx\tblock\tfn\tkind\thandler\tveneer\targs\tcalls\tcond\n")
        f.write("0\t0\t0x10\t0x10\ttail\t0x20\t0\t\t\t0\n")
        f.write("4\t\t0x30\t\ttail\t0x40\t0\t\t\t0\n")
        inventory = f.name
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
        f.write("# cat\tidx\thandler\tmotion\thow\n")
        f.write("0\t0\t0x20\t42\tconstant\n")
        motions = f.name
    try:
        inv = mh.read_inventory_tsv(inventory)
        assert inv[(0, 0)] == "0x20" and inv[(4, None)] == "0x40"
        assert mh.read_motions(motions)[(0, 0)] == "42"
    finally:
        os.unlink(inventory)
        os.unlink(motions)


def test_the_per_id_table_is_read_by_the_columns_targets_writes():
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False) as f:
        f.write("# action\ttarget\thandler\tproof\tR1\tmh4u_handler\n")
        f.write("7/64\t7/35\t0x006971c0\tbody match\tR1 same motion 205\t0x006e2764\n")
        f.write("7/64\t7/37\t0x006971c0\tbody match\tR1 same motion 205\t\n")
        path = f.name
    try:
        candidates = mh.read_targets(path)[(7, 64)]
    finally:
        os.unlink(path)
    assert len(candidates) == 2
    assert candidates[0].handler == 0x006E2764 and candidates[0].proof == "body match"
    assert candidates[1].handler is None          # MH4U's 7/37 is inline


def test_the_map_takes_the_lowest_shared_action_that_runs_an_mh4u_handler():
    inline = mh.Target((7, 64), (7, 35), None, "body match", "")
    handled = mh.Target((7, 64), (7, 92), 0x006E8E54, "body match", "")
    lower = mh.Target((7, 64), (7, 36), 0x006E8E54, "body match", "")
    assert mh.select_target([inline, handled]).target == (7, 92)
    assert mh.select_target([handled, lower]).target == (7, 36)
    # No candidate runs an MH4U handler: the lowest shared action is still the fallback.
    assert mh.select_target([inline]).target == (7, 35)


def test_an_id_with_no_shared_action_is_reported_as_new_code():
    mapped, new_code = mh.build_map({(0, 4): [mh.Target((0, 4), (0, 0), None, "body match", "")]},
                                    [(0, 4), (4, None)])
    assert mapped == [((0, 4), (0, 0))]
    assert new_code == [(4, None)]


def test_the_header_holds_the_map_and_leaves_the_gu_monster_empty():
    text = mh.render_header([((0, 4), (0, 0)), ((13, 9), (0, 3))], mh.read_registry())
    assert text.startswith(f"/* {mh.GENERATED}")
    assert "{0, 4, 0, 0}," in text and "{13, 9, 0, 3}," in text
    assert "mhuc_actions_124 = NULL;" in text
    assert text.count("static const MhucAction mhuc_actions_125[]") == 1
    assert "{125, 2, mhuc_actions_125}," in text


def test_a_category_only_action_uses_the_wildcard_index_in_the_header():
    text = mh.render_header([((4, None), (0, 0))], mh.read_registry())
    assert "{4, 255, 0, 0}," in text
    assert "#define MHUC_ACTION_NO_INDEX 0xff" in text
