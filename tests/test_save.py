"""The character and system save reader's slices: offsets and shapes, on a synthetic save (specs/save.md).

The synthetic save is built here from the spec's offsets, so a wrong offset or slice in `mhuc.save` shows up as
a wrong value, not as a round trip through our own writer. The real files are `tests/test_with_game_files.py`.
"""
from __future__ import annotations

import struct

import pytest

from mhuc import cli, save
from mhuc.crypto import dlccrypt


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
    data[save.ITEM_FLAGS_AT] = 0x01                  # bit 0: item id 0 held
    data[save.QUEST_FLAGS_AT + 1] = 0x04             # bit 10: a candidate quest flag
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
    assert save.quest_lists(data)["candidate_clear_flags"]["indices"] == [10]
    assert save.item_flags(data)["set_bits"] == 1
    assert save.item_flags(data)["highest_set"] == 0
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


def test_clean_removes_the_mods_items_and_guild_quests_and_nothing_else():
    data = character_save()
    # a ported item in the item box and in the item pouch, and a second guild quest naming a ported monster;
    # the ids are literals so a changed bound in the module fails this test, not follows it
    data[0x15E + 4:0x15E + 8] = struct.pack("<HH", 1937, 1)      # MH4U's last item id is 1,936
    data[save.POUCH_ITEM_AT:save.POUCH_ITEM_AT + 4] = struct.pack("<HH", 2000, 1)
    at = save.GUILD_QUEST_AT + save.GUILD_QUEST_SIZE
    data[at:at + 24] = utf16("Ported", 24)
    data[at + save.GUILD_QUEST_MONSTER_AT] = 124                 # MH4U's last monster id is 123

    cleaned, report = save.clean_character(data)
    assert [slot["slot"] for slot in save.item_box(cleaned)] == [0], "MH4U's own item slot 0 must stay"
    assert save.pouches(cleaned)["item"][0] == {"slot": 0, "item": 0, "count": 0}
    assert save.guild_quests(cleaned)[0]["owner"] == "Owner", "MH4U's own guild quest must stay"
    assert save.guild_quests(cleaned)[1] is None
    assert report == {"removed_items": [{"where": "item_box", "slot": 1},
                                        {"where": "item_pouch", "slot": 0}],
                      "removed_guild_quests": [{"slot": 1}]}
    cleared = (set(range(0x15E + 4, 0x15E + 8))
               | set(range(save.POUCH_ITEM_AT, save.POUCH_ITEM_AT + 4))
               | set(range(at, at + save.GUILD_QUEST_SIZE)))
    changed = {i for i in range(len(data)) if data[i] != cleaned[i]}
    assert changed <= cleared, f"bytes outside the cleared slots changed: {sorted(changed - cleared)[:8]}"
    assert save.character_problems(cleaned) == []
    assert save.clean_character(cleaned) == (cleaned, {"removed_items": [], "removed_guild_quests": []})


def test_clean_leaves_a_save_that_never_met_the_mod_byte_for_byte():
    data = character_save()
    cleaned, report = save.clean_character(data)
    assert cleaned == bytes(data)
    assert report == {"removed_items": [], "removed_guild_quests": []}


def test_the_clean_command_keeps_the_files_own_seed_and_refuses_system(tmp_path):
    key = b"a test key"
    original = dlccrypt.mh4u_save_encrypt(bytes(character_save()), key, "normal", 0xABCD)
    key_path, src = tmp_path / "save.key", tmp_path / "user1"
    key_path.write_bytes(key)
    src.write_bytes(original)
    out = tmp_path / "user1.clean"
    assert cli.main(["save", "clean", str(src), "--key", str(key_path), "--out", str(out)]) == 0
    assert out.read_bytes() == original, "a clean save must come back byte for byte, its seed kept"

    system = tmp_path / "system"
    system.write_bytes(bytes(save.SYSTEM_SIZE))
    assert cli.main(["save", "clean", str(system), "--out", str(tmp_path / "system.clean")]) == 1
    assert not (tmp_path / "system.clean").exists()


def test_a_save_of_the_wrong_size_is_refused_not_sliced():
    with pytest.raises(save.SaveError):
        save.profile(bytes(100))
    with pytest.raises(save.SaveError):
        save.system_summary(bytes(save.CHARACTER_SIZE))


def test_system_save_summary_lists_the_mapped_fields():
    data = bytearray(save.SYSTEM_SIZE)
    struct.pack_into("<I", data, save.SYSTEM_VERSION_AT, 1)
    struct.pack_into("<I", data, save.SYSTEM_TIME_AT, 0x01020304)
    for i in range(save.SYSTEM_ENTRY_COUNT):
        struct.pack_into("<I", data, save.SYSTEM_ENTRIES_AT + 4 * i, 100 + i)
    data[save.SYSTEM_FLAGS_AT:save.SYSTEM_FLAGS_AT + save.SYSTEM_FLAGS_SIZE] = b"\xff" * save.SYSTEM_FLAGS_SIZE
    struct.pack_into("<I", data, save.SYSTEM_MARK_AT, 1)
    struct.pack_into("<I", data, save.SYSTEM_CHARACTER_AT, 0xFFFFFFFF)
    struct.pack_into("<I", data, save.SYSTEM_UNKNOWN_0X40, 2)
    struct.pack_into("<I", data, save.SYSTEM_UNKNOWN_0X64, 1)

    summary = save.system_summary(data)
    assert summary["version"] == 1
    assert summary["timestamp_0x04"] == 0x01020304
    assert [entry["value"] for entry in summary["timestamps_0x08"]] == [100, 101, 102, 103]
    assert summary["flags_0x18"]["words"] == [0xFFFFFFFF] * 8
    assert summary["flags_0x18"]["set_bits"] == 256
    assert summary["word_0x38"] == 1
    assert summary["character_0x3c"] is None
    assert (summary["word_0x40"], summary["word_0x64"]) == (2, 1)
    assert summary["last_nonzero"] == save.SYSTEM_UNKNOWN_0X64
    assert save.system_problems(data) == []


def test_system_save_reports_the_selected_character_slot():
    data = bytearray(save.SYSTEM_SIZE)
    struct.pack_into("<I", data, save.SYSTEM_MARK_AT, 1)
    struct.pack_into("<I", data, save.SYSTEM_CHARACTER_AT, 0)
    assert save.system_summary(data)["character_0x3c"] == 0


def test_system_save_summary_reports_the_files_extent():
    data = bytearray(save.SYSTEM_SIZE)
    struct.pack_into("<I", data, 0, 1)
    data[0x20] = 0x7F
    summary = save.system_summary(data)
    assert summary["nonzero_bytes"] == 2
    assert summary["first_nonzero"] == 0 and summary["last_nonzero"] == 0x20
    assert summary["flags_0x18"]["set_bits"] == 7
    assert save.system_problems(data) == []
