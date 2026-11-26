"""reference/monster_fields.py: the field map's derivation and its page rows.

The dumps are not in CI and neither is capstone (a fork requirement for the reference
tools), so the pair that must be reported is built from `Agreement` lists directly, and only
the disassembly tests are skipped where capstone is absent.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_fields as mf  # noqa: E402

MOV_R4_THIS = 0xE1A04000        # mov r4, r0: `this` survives a call in a callee-saved register
LDR_R1_WORK = 0xE5941040        # ldr r1, [r4, #0x40]: the test's block pointer field
BX_LR = 0xE12FFF1E


def _has_capstone() -> bool:
    try:
        import capstone  # noqa: F401
        return True
    except ImportError:
        return False


needs_capstone = pytest.mark.skipif(not _has_capstone(),
                                    reason="the scanner needs capstone, the fork's requirement")


def ldrb(rd: int, imm: int) -> int:
    return 0xE5D10000 | (rd << 12) | imm     # ldrb rd, [r1, #imm]


def bl(at: int, target: int) -> int:
    return 0xEB000000 | (((target - (at + 8)) >> 2) & 0xFFFFFF)


def function(base: int, off5: int, off6: int, call5: int, call6: int) -> mf.Code:
    """mov r4, r0; ldr r1, [r4, #0x40]; ldrb r2, [r1, #off5]; bl call5;
    ldr r1, [r4, #0x40]; ldrb r3, [r1, #off6]; bl call6; bx lr."""
    words = [MOV_R4_THIS, LDR_R1_WORK, ldrb(2, off5), bl(base + 12, call5),
             LDR_R1_WORK, ldrb(3, off6), bl(base + 24, call6), BX_LR]
    return mf.Code(b"".join(w.to_bytes(4, "little") for w in words), base)


def handler(code: mf.Code) -> mf.Game:
    game = mf.Game("mh4u", code)
    game.work = 0x40            # the test's block pointer field, small enough to encode
    return game


def pairing(off5: int = 0x105, off6: int = 0x106) -> mf.Pairing:
    a = handler(function(0x1000, 5, 6, 0x1800, 0x1804))
    b = handler(function(0x2000, off5, off6, 0x2800, 0x2804))
    fields, calls = mf.align(mf.scan(a, 0x1000), mf.scan(b, 0x2000))
    return mf.Pairing(0x1000, 0x2000, fields, calls)


def support_of(pairs: list[mf.Pairing]) -> dict:
    support: dict = {}
    for i, p in enumerate(pairs):
        for f in p.fields:
            support.setdefault((f.space, f.off_a, f.off_b), set()).add(i)
    return support


def test_a_pair_whose_fields_contradict_the_rest_is_reported():
    good = [[mf.Agreement("work", 5, 0x105), mf.Agreement("work", 6, 0x106)] for _ in range(3)]
    bad = [mf.Agreement("work", 5, 0x205), mf.Agreement("work", 6, 0x206)]
    support: dict = {}
    for i, fields in enumerate(good + [bad]):
        for f in fields:
            support.setdefault((f.space, f.off_a, f.off_b), set()).add(i)
    assert mf.disagreement(len(good), bad, support)          # the broken pair is named
    assert mf.disagreement(0, good[0], support) == ""        # the others are not


def test_a_pair_that_agrees_or_that_no_other_pair_judges_is_not_reported():
    agree = [mf.Agreement("work", 5, 0x105), mf.Agreement("work", 6, 0x106)]
    unique = [mf.Agreement("work", 0x200, 0x300), mf.Agreement("work", 0x204, 0x304)]
    support = {("work", 5, 0x105): {0, 1}, ("work", 6, 0x106): {0, 1},
               ("work", 0x200, 0x300): {2}, ("work", 0x204, 0x304): {2}}
    assert mf.disagreement(0, agree, support) == ""
    assert mf.disagreement(2, unique, support) == ""


def test_a_pair_with_one_field_is_not_judged():
    one = [mf.Agreement("work", 5, 0x200)]
    support = {("work", 5, 0x144): {0, 1, 2}, ("work", 5, 0x200): {3}}
    assert mf.disagreement(3, one, support) == ""


@needs_capstone
def test_a_handler_s_reads_are_its_fields_and_its_call_is_an_event():
    events = mf.scan(handler(function(0x1000, 5, 6, 0x1800, 0x1804)), 0x1000)
    assert [(e.kind, e.space, e.off) for e in events] == [
        ("field", "work", 5), ("call", "", 0), ("field", "work", 6), ("call", "", 0)]
    assert [e.target for e in events if e.kind == "call"] == [0x1800, 0x1804]
    assert all(e.size == 1 and not e.write for e in events if e.kind == "field")


@needs_capstone
def test_two_corresponding_handlers_line_up_field_for_field():
    p = pairing()
    assert [(f.space, f.off_a, f.off_b) for f in p.fields] == [
        ("work", 5, 0x105), ("work", 6, 0x106)]
    assert len(p.calls) == 2


@needs_capstone
def test_a_scanned_broken_pair_is_reported_like_a_crafted_one():
    good = [pairing(), pairing(), pairing()]
    bad = pairing(0x205, 0x206)
    support = support_of(good + [bad])
    assert mf.disagreement(len(good), bad.fields, support)
    assert mf.disagreement(2, good[2].fields, support) == ""


def test_the_page_rows_parse_to_offsets_and_counts(tmp_path):
    page = tmp_path / "README.md"
    page.write_text(
        mf.MAP_HEADING + "\n\n"
        "| MH3U | MH4U | role | how |\n"
        "|---|---|---|---|\n"
        "| `*(this+0x1a48)` | `*(this+0xe28)` | the block | both load it so |\n"
        "| work+0x5 | work+0x144 | the state byte | 49 of the 57 pairs |\n"
        "| work+0x28 / +0x2c | work+0x1d4 | the timer | 2 and 6 pairs |\n"
        "| work+0x2b6 | work+0x278 or +0x27c | the part byte | 3 pairs each way |\n"
        "| work+0x38 / +0x3c / +0x40 | work+0x198 / +0x19c / +0x1a0 | position | the twins read it |\n\n"
        "### The next section\n",
        encoding="utf-8")
    rows = mf.read_map_rows(str(page))
    assert [r.offsets() for r in rows] == [
        [("work", 0x5, [0x144])],
        [("work", 0x28, [0x1D4]), ("work", 0x2C, [0x1D4])],
        [("work", 0x2B6, [0x278, 0x27C])],
        [("work", 0x38, [0x198]), ("work", 0x3C, [0x19C]), ("work", 0x40, [0x1A0])],
    ]
    assert [r.counts() for r in rows] == [[49], [2, 6], [3], []]
    assert rows[1].line > rows[0].line        # the block-pointer row is not a field row


def test_a_page_without_the_map_section_has_no_rows(tmp_path):
    page = tmp_path / "README.md"
    page.write_text("### Somewhere else\n\n| a | b | c | d |\n|---|---|---|---|\n"
                    "| work+0x5 | work+0x144 | x | 1 pair |\n", encoding="utf-8")
    assert mf.read_map_rows(str(page)) == []
