"""Quests: a .mib the game can't read, or a converted quest with invented ids, must never be written."""
from __future__ import annotations

import struct

import pytest

from mhuc.quests import convert, mibwrite, quest

LANGS, TEXTS = quest.MIB4_LANGS, quest.MIB4_TEXTS


def model() -> dict:
    header = bytearray(mibwrite.HEADER)
    struct.pack_into("<I", header, 0, 0xA0)
    header[4:8] = b"v005"
    struct.pack_into("<H", header, 0xC0, 60999)              # quest id
    definition = bytes(range(mibwrite.DEF))
    return {
        "header": bytes(header),
        "texts": [[f"{lang} {name}" for name in TEXTS] for lang in LANGS],
        "presets": None,
        # a supply box: its byte 1 counts the items that follow
        "supply": [(b"\0\x02\0\0", struct.pack("<2H", 1, 10) + struct.pack("<2H", 2, 5))],
        "rewards": {"main": (b"\0\x80\0\0", [struct.pack("<3H", 100, 7, 1)])},
        "waves": [[definition]],
        "small_areas": [[definition]],
        "intruders": [],
    }


def test_mib_builder_moves_every_block_when_the_title_grows():
    original = model()
    longer = mibwrite.mib4_set_texts(original, 0, "a title much longer than the one it replaces " * 3)
    built = mibwrite.mib4_build(longer)
    assert len(built) > len(mibwrite.mib4_build(original))
    reread = mibwrite.mib4_model(built)
    assert reread["texts"] == longer["texts"]
    for block in ("supply", "rewards", "waves", "small_areas", "header"):
        assert reread[block] == original[block], block


def test_converter_refuses_a_quest_with_ids_the_tables_do_not_map():
    parts = {
        "mib": {"map": 5, "time_min": 50, "fee": 100, "reward": 1000, "sub_reward": 0, "stars": 3, "rank": 1},
        "sem": {"b_m01em027_00.sem": {"round": 0, "count": 1, "area": 2, "pos": [0.0, 0.0, 0.0]}},
        "rem": {"rem0": {"slots": [(200, 1, 50)]}},
    }
    template = {"fields": {}, "waves": [], "small_areas": [], "rewards": {}, "supply": []}
    texts = {lang: {t: t for t in TEXTS} for lang in LANGS}
    tables = {"map": {"5": "1"}, "monster": {"em001": "1"}, "area": {"5:2": "3"}, "item": {}, "objective": {}}
    with pytest.raises(convert.ConvertError) as refused:
        convert.convert_mhxx(parts, template, tables, 61001, texts)
    assert "monster:em027" in str(refused.value)
    assert "item:200" in str(refused.value)
