"""reference/force_action.py: the debugging tool's forcing addresses must not drift from the games' code."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import force_action  # noqa: E402


def test_action_parses_decimal_and_hex():
    assert force_action.parse_action("3/17") == (3, 17)
    assert force_action.parse_action("0x3/0x11") == (3, 17)


def test_action_rejects_a_missing_or_out_of_range_byte():
    for text in ("3", "3/", "/17", "3/17x", "-1/2", "3/256"):
        try:
            force_action.parse_action(text)
        except ValueError:
            continue
        raise AssertionError(f"{text!r} should not parse")


def test_mh3u_pair_is_the_work_block_plus_its_category_byte():
    work = 0x0D000000
    addr = force_action.pair_address(
        "mh3u", 0x0C000000, lambda a: work if a == 0x0C000000 + 0x1A48 else 0
    )
    assert addr == work + 0xDF


def test_mhxx_pair_is_the_enemy_plus_its_category_byte():
    assert force_action.pair_address("mhxx", 0x0C000000, None) == 0x0C006BF0


def test_write_packet_writes_the_category_then_the_index():
    assert force_action.write_pair_packet(0x0C006BF0, 3, 17) == b"Mc006bf0,2:0311"
