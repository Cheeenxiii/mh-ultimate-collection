"""tools/check_actions.py: a ledger row that disagrees with the dispatcher must be named."""
from __future__ import annotations

from types import SimpleNamespace

import check_actions as ca


def action():
    return SimpleNamespace(cat=3, idx=17, block=0x1000, handler=0x2000, kind="tail")


def ledger(**changed) -> list[dict]:
    row = {"action": "3/17", "cat": 3, "idx": 17, "block": 0x1000, "handler": 0x2000,
           "motion": 0x101, "status": "translated"}
    row.update(changed)
    return [row]


def problems(**changed) -> list[str]:
    return ca.check(ledger(**changed), {(3, 17): action()}, lambda _: 0x101,
                    ca.STATUSES["mhxx"])[0]


def test_a_row_that_agrees_with_the_dispatcher_has_no_problems():
    assert problems() == []


def test_a_ledger_block_handler_or_motion_that_disagrees_names_the_id():
    assert any("3/17" in p and "block" in p for p in problems(block=0x1004))
    assert any("3/17" in p and "handler" in p for p in problems(handler=0x3000))
    assert any("3/17" in p and "first motion" in p for p in problems(motion=0x102))


def test_a_gu_status_left_to_an_mh4u_handler_names_the_id():
    assert any("3/17" in p and "mh4u" in p for p in problems(status="mh4u"))


def test_a_3u_status_left_to_an_mh4u_handler_names_the_id():
    found = ca.check(ledger(status="mh4u"), {(3, 17): action()}, lambda _: 0x101,
                     ca.STATUSES["mh3u"])[0]
    assert any("3/17" in p and "mh4u" in p for p in found)
