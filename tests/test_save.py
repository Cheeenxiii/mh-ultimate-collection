"""The character and system save reader's slices: offsets and shapes, on a synthetic save (specs/save.md).

The synthetic save is built here from the spec's offsets, so a wrong offset or slice in `mhuc.save` shows up as
a wrong value, not as a round trip through our own writer. The real files are `tests/test_with_game_files.py`.
"""
from __future__ import annotations

import struct

import pytest

from mhuc import save


def utf16(text: str, size: int) -> bytes:
    raw = text.encode("utf-16-le")
    assert len(raw) <= size
    return raw + b"\0" * (size - len(raw))


def character_save() -> bytearray:
    data = bytearray(save.CHARACTER_SIZE)
    data[0x00:0x18] = utf16("Tester", 24)
    data[0x18] = 1                                  # female
    data[0x19] = 2
    data[0x2C:0x30] = struct.pack("<I", 123)        # HR
    data[0x30:0x34] = struct.pack("<I", 4567)       # HR points
    data[0x34:0x38] = struct.pack("<I", 89012)      # funds
    data[0x38:0x3C] = struct.pack("<I", 3600)       # play time
    # worn weapon: kind 7, id 100, three decoration slots
    data[0x40:0x5C] = struct.pack("<BBHHHHH", 7, 0, 100, 0, 1, 2, 3) + b"\0" * 16
    for i in range(7):
        data[0x104 + 2 * i:0x106 + 2 * i] = struct.pack("<H", 42 if i == 0 else 0xFFFF)
    # item box slot 0: Potion, 10
    data[0x15E:0x162] = struct.pack("<HH", 8, 10)
    # equipment box slot 42 holds the worn weapon
    at = save.EQUIPMENT_BOX_AT + 42 * save.EQUIPMENT_SIZE
    data[at:at + 12] = struct.pack("<BBHHHHH", 7, 0, 100, 0, 1, 2, 3)
    # main Palico and one other
    data[0xC4B0:0xC4B0 + 24] = utf16("Pal", 24)
    data[0xC4B0 + 0x70:0xC4B0 + 0x78] = struct.pack("<Q", 1234)
    data[0xF338:0xF338 + 24] = utf16("Pal2", 24)
    data[0xF338 + 0x70:0xF338 + 0x78] = struct.pack("<Q", 5)
    # one guild quest: owner, unique id, one monster, levels
    at = save.GUILD_QUEST_AT
    data[at:at + 24] = utf16("Owner", 24)
    data[at + 0x18:at + 0x20] = bytes(range(8))
    data[at + 0x28] = 7
    data[at + 0x128] = 5
    data[at + 0x129] = 6
    # monster log entry 0
    data[save.MONSTER_LOG_AT:save.MONSTER_LOG_AT + 10] = struct.pack("<5H", 3, 1, 120, 90, 1)
    # guild card: HR, name, one quest count, one weapon-usage number, brigade points, one bit
    data[0x12606:0x12608] = struct.pack("<H", 123)
    data[0x12608:0x12620] = utf16("Tester", 24)
    data[save.QUEST_COUNTS_AT:save.QUEST_COUNTS_AT + 2] = struct.pack("<H", 1)
    data[save.WEAPON_USAGE_AT[0]:save.WEAPON_USAGE_AT[0] + 2] = struct.pack("<H", 2)
    data[save.BRIGADE_POINTS_AT:save.BRIGADE_POINTS_AT + 4] = struct.pack("<I", 1234)
    data[save.BITFIELD_AT] = 0x01
    return data


def test_character_save_slices_read_the_values_at_the_spec_offsets():
    data = character_save()
    profile = save.profile(data)
    assert profile["name"] == "Tester"
    assert (profile["gender"], profile["face"]) == (1, 2)
    assert (profile["hunter_rank"], profile["funds"], profile["playtime_mh4g"]) == (123, 89012, 3600)
    assert save.equipped(data)[0] == {"part": 0, "kind": 7, "id": 100, "slots": [1, 2, 3]}
    assert save.equipped_indices(data) == [42, None, None, None, None, None, None]
    assert save.item_box(data) == [{"slot": 0, "item": 8, "count": 10}]
    assert save.equipment_box(data) == [{"slot": 42, "kind": 7, "id": 100, "slots": [1, 2, 3]}]
    assert save.guild_quests(data)[0]["owner"] == "Owner"
    assert save.guild_quests(data)[0]["monsters"][0]["id"] == 7
    assert save.palicos(data)[0] == {"slot": 0, "name": "Pal", "experience": 1234, "used": True}
    assert save.palicos(data)[1]["name"] == "Pal2"
    assert save.monster_log(data)[0] == {"entry": 0, "kills": 3, "captures": 1, "largest": 120,
                                        "smallest": 90, "crowns": 1}
    card = save.guild_card(data)
    assert card["quest_counts"]["village_low"] == 1
    assert card["weapon_usage"]["village"]["great_sword"] == 2
    assert card["brigade_points"] == 1234
    assert card["bitfield_set_bits"] == 1
    assert save.character_problems(data) == []


def test_character_save_problems_name_the_slot_that_breaks_the_bound():
    data = character_save()
    struct.pack_into("<H", data, 0x15E + 2, 100)
    assert "item box slot 0 has count 100 above 99" in save.character_problems(data)

    data = character_save()
    struct.pack_into("<H", data, 0x104, 2000)
    assert "equipped index 2000 is outside the equipment box" in save.character_problems(data)

    data = character_save()
    struct.pack_into("<5H", data, save.MONSTER_LOG_AT, 3, 1, 10, 20, 1)
    assert "monster log entry 0 has largest 10 below smallest 20" in save.character_problems(data)

    data = character_save()
    struct.pack_into("<I", data, 0x34, 100_000_000)
    assert "funds 100000000 are above 99,999,999" in save.character_problems(data)


def test_a_save_of_the_wrong_size_is_refused_not_sliced():
    with pytest.raises(save.SaveError):
        save.profile(bytes(100))
    with pytest.raises(save.SaveError):
        save.system_summary(bytes(save.CHARACTER_SIZE))


def test_system_save_summary_reports_the_files_extent():
    data = bytearray(save.SYSTEM_SIZE)
    struct.pack_into("<I", data, 0, 1)
    data[0x20] = 0x7F
    summary = save.system_summary(data)
    assert summary["nonzero_bytes"] == 2
    assert summary["first_nonzero"] == 0 and summary["last_nonzero"] == 0x20
    assert summary["head_words"][0] == {"offset": 0, "value": 1}
    assert save.system_problems(data) == []
