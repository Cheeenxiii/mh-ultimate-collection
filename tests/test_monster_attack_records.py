"""reference/monster_attack_records.py: the in-image action-start record's layout and the
conversion onto MH4U's record must not drift from specs/actiondata.md."""
from __future__ import annotations

import os
import struct
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_attack_records as mar  # noqa: E402


def source_record():
    return {
        "motion a": 0x11, "argument a1": -3, "argument a2": 0, "flags a": 1,
        "motion b": 0x22, "argument b1": 7, "argument b2": 0, "flags b": 0,
        "turn motion a": 0x33, "turn motion b": 0x44,
        "threshold": 12.5, "clamp": 3.5,
    }


def test_a_record_is_written_and_read_back_field_for_field():
    assert mar.read_record(mar.write_record(source_record())) == source_record()


def test_a_short_buffer_is_refused():
    with pytest.raises(mar.RecordError):
        mar.read_record(b"\0" * (mar.RECORD - 4))


def test_the_motions_are_mapped_and_the_arguments_and_floats_are_carried():
    rebuilt = mar.rebuild(source_record(), {0x11: 0x101, 0x22: 0x102, 0x33: 0x103, 0x44: 0x104}, 9)
    assert (rebuilt["motion a"], rebuilt["motion b"]) == (0x101, 0x102)
    assert (rebuilt["turn motion a"], rebuilt["turn motion b"]) == (0x103, 0x104)
    assert (rebuilt["argument a1"], rebuilt["argument b1"]) == (-3, 7)
    assert (rebuilt["threshold"], rebuilt["clamp"]) == (12.5, 3.5)


def test_the_two_flag_words_come_from_mh4us_own_records_not_the_source():
    rebuilt = mar.rebuild(source_record(), {0x11: 0x101, 0x22: 0x102, 0x33: 0x103, 0x44: 0x104}, 0x99)
    assert (rebuilt["flags a"], rebuilt["flags b"]) == (0x99, 0x99)


def test_a_motion_the_map_lacks_is_refused_by_name():
    with pytest.raises(mar.RecordError, match="0x33"):
        mar.rebuild(source_record(), {0x11: 0x101, 0x22: 0x102, 0x44: 0x104}, 0)


def test_compare_groups_the_differing_fields_by_role():
    target = mar.rebuild(source_record(), {0x11: 0x101, 0x22: 0x102, 0x33: 0x103, 0x44: 0x104}, 0)
    target["argument b1"] = 8
    target["clamp"] = 1.0
    target["turn motion b"] = 0x999
    differences = mar.compare(mar.rebuild(source_record(),
                                         {0x11: 0x101, 0x22: 0x102, 0x33: 0x103, 0x44: 0x104}, 0),
                              target)
    assert differences == {"argument": ["argument b1"], "motion": ["turn motion b"], "float": ["clamp"]}


def test_an_animation_is_found_at_every_index_with_its_signature():
    lmts = [[(10, 0, 3), (20, -1, 4)], [(10, 0, 2)]]
    assert mar.candidates(lmts, "mh4u", (10, 0, 3)) == [0, 0x100]


def test_an_index_outside_the_motion_lists_has_no_signature():
    lmts = [[(10, 0, 3)]]
    assert mar.signature(lmts, "mh4u", 0x101) is None
    assert mar.signature(lmts, "mh3u", 0) == (10, 0, 3)
    assert mar.signature(lmts, "mh3u", 3) is None


def test_the_positional_pairing_pairs_the_same_quartet_in_both_games():
    # The readers read motion a from +0x00 and motion b from +0x10 in both games, so the
    # conversion maps each offset's motion to that offset's motion (N2's signature check is
    # what confirms the animation; this test only protects the slot pairing).
    fields = {f.offset: f.name for f in mar.FIELDS}
    assert fields[0x00] == "motion a" and fields[0x10] == "motion b"
    assert fields[0x20] == "turn motion a" and fields[0x22] == "turn motion b"


def test_a_value_curve_runs_to_its_negative_time_key():
    data = struct.pack("<ffffffff", 0.0, 5.0, 30.0, -2.0, -1.0, 0.0, 9.0, 9.0)
    assert mar.read_curve(data) == [(0.0, 5.0), (30.0, -2.0), (-1.0, 0.0)]


def test_a_value_curve_without_an_end_key_is_refused():
    data = struct.pack("<ff", 0.0, 1.0) * (mar.CURVE_KEYS_MAX + 1)
    with pytest.raises(mar.RecordError, match="no ending key"):
        mar.read_curve(data)
