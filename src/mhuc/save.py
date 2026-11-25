"""MH4U's saves: the character files `user1`..`user3` and `system`, read after `mhuc decrypt mh4u-save`.

A character save is 81,400 bytes decrypted, one character per file. Offsets in this module are in the
decrypted file, as `mhuc decrypt mh4u-save` writes it (the cipher's 8-byte header is gone). Layouts:
specs/save.md, from the community save editor mh4edit (MIT) and the MH4G save-editor wiki for the
profile, pouches, quest counts and weapon usage, and from the mhff wiki for the monster log; each field's
status is in the spec.

No game data is stored here: the module holds offsets and shapes only, and reads a file the user supplies.
"""
from __future__ import annotations

import struct

from .extdata import parse_guild_quest

CHARACTER_SIZE = 81400          # decrypted user1..user3
ENCRYPTED_CHARACTER_SIZE = 81408
SYSTEM_SIZE = 504               # decrypted system
ENCRYPTED_SYSTEM_SIZE = 512

PROFILE_SIZE = 0x40
EQUIPPED_SIZE = 7 * 28
EQUIPPED_AT = 0x0040
EQUIPPED_INDEX_AT = 0x0104
POUCH_GUNNER_AT = 0xCAF4
POUCH_GUNNER_COUNT = 8
POUCH_ITEM_AT = 0xCB14
POUCH_ITEM_COUNT = 24
ITEM_BOX_AT = 0x015E
ITEM_BOX_COUNT = 1400
EQUIPMENT_BOX_AT = 0x173E
EQUIPMENT_BOX_COUNT = 1400
EQUIPMENT_SIZE = 28
PALICO_MAIN_AT = 0xC4B0
PALICO_AT = 0xF338
PALICO_COUNT = 56               # one main Palico, then 55 others
PALICO_SIZE = 232
GUILD_QUEST_AT = 0xDCA8
GUILD_QUEST_COUNT = 10
GUILD_QUEST_SIZE = 304
MONSTER_LOG_AT = 0x12E5C
MONSTER_LOG_COUNT = 82
MONSTER_LOG_SIZE = 10
QUEST_COUNTS_AT = 0x12620      # seven u16, in the order below
QUEST_COUNT_NAMES = ("village_low", "gathering_low", "gathering_high", "guild_quests",
                     "arena", "village_high", "gathering_g")
WEAPON_USAGE_AT = (0x12796, 0x127B6, 0x127D6)   # village, gathering, arena; fourteen u16 each
WEAPON_USAGE_NAMES = ("great_sword", "sns", "hammer", "lance", "hbg", "lbg", "long_sword",
                      "switch_axe", "gunlance", "bow", "dual_blades", "hunting_horn",
                      "insect_glaive", "charge_blade")
BRIGADE_POINTS_AT = 0xE8A0
BITFIELD_AT = 0xF220
BITFIELD_SIZE = 280             # 2,240 bits; meaning unknown (specs/save.md)
SHARP_ARENA_AT = 0x131A4        # the arena leaderboard block (specs/save.md); partly mapped

# The blocks the spec lists. (name, offset, size); the unknown blocks keep their extent only.
BLOCKS = (
    ("profile", 0x0000, PROFILE_SIZE),
    ("equipped", EQUIPPED_AT, EQUIPPED_SIZE),
    ("equipped_indices", EQUIPPED_INDEX_AT, 14),
    ("unknown_0x0112", 0x0112, 0x4C),
    ("item_box", ITEM_BOX_AT, ITEM_BOX_COUNT * 4),
    ("equipment_box", EQUIPMENT_BOX_AT, EQUIPMENT_BOX_COUNT * EQUIPMENT_SIZE),
    ("unknown_0xB05E", 0xB05E, 0xAE6),
    ("palico_gear_box", 0xBB44, 0x96C),
    ("palico_main", PALICO_MAIN_AT, PALICO_SIZE),
    ("unknown_0xC598", 0xC598, 0x55C),
    ("pouch_gunner", POUCH_GUNNER_AT, POUCH_GUNNER_COUNT * 4),
    ("pouch_items", POUCH_ITEM_AT, POUCH_ITEM_COUNT * 4),
    ("unknown_0xCB74", 0xCB74, 0x1134),
    ("guild_quests", GUILD_QUEST_AT, GUILD_QUEST_COUNT * GUILD_QUEST_SIZE),
    ("unknown_0xE888", 0xE888, 0x998),
    ("bitfield", BITFIELD_AT, BITFIELD_SIZE),
    ("palicos", PALICO_AT, (PALICO_COUNT - 1) * PALICO_SIZE),
    ("unknown_0x12510", 0x12510, 0xF0),
    ("guild_card", 0x12600, 0xBA4),
    ("arena_leaderboard", SHARP_ARENA_AT, 0x5D0),
    ("unknown_0x13774", 0x13774, 0x27C),
    ("unknown_0x139F0", 0x139F0, 0x408),
)


class SaveError(ValueError):
    pass


def _utf16z(raw: bytes) -> str:
    end = 0
    while end + 1 < len(raw) and raw[end:end + 2] != b"\0\0":
        end += 2
    return raw[:end].decode("utf-16-le", "replace")


def _u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def _u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def _u64(data: bytes, off: int) -> int:
    return struct.unpack_from("<Q", data, off)[0]


def _check_size(data: bytes, size: int, what: str) -> None:
    if len(data) != size:
        raise SaveError(f"a decrypted {what} is {size} bytes, not {len(data)}")


def profile(data: bytes) -> dict:
    """The character's profile, the first 0x40 bytes (specs/save.md, check S2)."""
    _check_size(data, CHARACTER_SIZE, "character save")
    return {
        "name": _utf16z(data[0x00:0x18]),
        "gender": data[0x18], "face": data[0x19], "hair": data[0x1A], "clothing": data[0x1B],
        "voice": data[0x1C], "eye_color": data[0x1D], "features": data[0x1E],
        "features_rgb": list(data[0x1F:0x22]), "hair_rgb": list(data[0x22:0x25]),
        "clothing_rgb": list(data[0x25:0x28]), "skin_rgb": list(data[0x28:0x2B]),
        "unknown_0x2B": data[0x2B],
        "hunter_rank": _u32(data, 0x2C), "hunter_rank_points": _u32(data, 0x30),
        "funds": _u32(data, 0x34), "playtime_mh4g": _u32(data, 0x38),
        "playtime_mh4": _u32(data, 0x3C),
    }


def _equipment(rec: bytes) -> dict:
    """One 28-byte equipment record: kind byte, id and three decoration slots (specs/save.md)."""
    return {"kind": rec[0], "id": _u16(rec, 2),
            "slots": [_u16(rec, 6), _u16(rec, 8), _u16(rec, 10)]}


def equipped(data: bytes) -> list[dict]:
    """The seven worn pieces, in the game's order: weapon, chest, arms, waist, legs, head, talisman."""
    _check_size(data, CHARACTER_SIZE, "character save")
    return [{"part": part, **_equipment(data[EQUIPPED_AT + part * EQUIPMENT_SIZE:
                                               EQUIPPED_AT + (part + 1) * EQUIPMENT_SIZE])}
            for part in range(7)]


def equipped_indices(data: bytes) -> list[int | None]:
    """The equipment-box slot each worn piece comes from; None for 0xFFFF."""
    _check_size(data, CHARACTER_SIZE, "character save")
    raw = [_u16(data, EQUIPPED_INDEX_AT + 2 * i) for i in range(7)]
    return [None if v == 0xFFFF else v for v in raw]


def item_box(data: bytes) -> list[dict]:
    """Every used item-box slot, in box order. A slot is used when its id or count is non-zero."""
    _check_size(data, CHARACTER_SIZE, "character save")
    out = []
    for i in range(ITEM_BOX_COUNT):
        at = ITEM_BOX_AT + i * 4
        item, count = _u16(data, at), _u16(data, at + 2)
        if item or count:
            out.append({"slot": i, "item": item, "count": count})
    return out


def equipment_box(data: bytes) -> list[dict]:
    """Every used equipment-box slot, in box order."""
    _check_size(data, CHARACTER_SIZE, "character save")
    out = []
    for i in range(EQUIPMENT_BOX_COUNT):
        rec = data[EQUIPMENT_BOX_AT + i * EQUIPMENT_SIZE: EQUIPMENT_BOX_AT + (i + 1) * EQUIPMENT_SIZE]
        if any(rec):
            out.append({"slot": i, **_equipment(rec)})
    return out


def pouches(data: bytes) -> dict:
    """The item pouch (24 slots, three pages of eight) and the gunner pouch (eight)."""
    _check_size(data, CHARACTER_SIZE, "character save")

    def slots(at: int, count: int) -> list[dict]:
        out = []
        for i in range(count):
            item, n = _u16(data, at + i * 4), _u16(data, at + i * 4 + 2)
            out.append({"slot": i, "item": item, "count": n})
        return out

    return {"item": slots(POUCH_ITEM_AT, POUCH_ITEM_COUNT),
            "gunner": slots(POUCH_GUNNER_AT, POUCH_GUNNER_COUNT)}


def guild_quests(data: bytes) -> list[dict | None]:
    """The ten guild-quest slots; None for an empty slot. The 304-byte record is extdata's layout."""
    _check_size(data, CHARACTER_SIZE, "character save")
    out = []
    for i in range(GUILD_QUEST_COUNT):
        rec = data[GUILD_QUEST_AT + i * GUILD_QUEST_SIZE: GUILD_QUEST_AT + (i + 1) * GUILD_QUEST_SIZE]
        out.append(parse_guild_quest(rec) if any(rec) else None)
    return out


def palicos(data: bytes) -> list[dict]:
    """The 56 Palico slots, main Palico first. An empty slot has no name and no experience."""
    _check_size(data, CHARACTER_SIZE, "character save")
    offsets = [PALICO_MAIN_AT] + [PALICO_AT + i * PALICO_SIZE for i in range(PALICO_COUNT - 1)]
    out = []
    for i, at in enumerate(offsets):
        rec = data[at:at + PALICO_SIZE]
        name = _utf16z(rec[0x00:0x18])
        exp = _u64(rec, 0x70)
        out.append({"slot": i, "name": name, "experience": exp, "used": bool(name or exp)})
    return out


def monster_log(data: bytes) -> list[dict]:
    """The 82 fixed ten-byte entries: kills, captures, largest, smallest and crown flags (all u16)."""
    _check_size(data, CHARACTER_SIZE, "character save")
    out = []
    for i in range(MONSTER_LOG_COUNT):
        at = MONSTER_LOG_AT + i * MONSTER_LOG_SIZE
        kills, captures, largest, smallest, crowns = struct.unpack_from("<5H", data, at)
        out.append({"entry": i, "kills": kills, "captures": captures, "largest": largest,
                    "smallest": smallest, "crowns": crowns})
    return out


def guild_card(data: bytes) -> dict:
    """The guild-card records in the character save: quest counts, weapon usage and brigade points."""
    _check_size(data, CHARACTER_SIZE, "character save")
    counts = {name: _u16(data, QUEST_COUNTS_AT + 2 * i) for i, name in enumerate(QUEST_COUNT_NAMES)}
    usage = {}
    for table, at in zip(("village", "gathering", "arena"), WEAPON_USAGE_AT, strict=True):
        usage[table] = {name: _u16(data, at + 2 * i) for i, name in enumerate(WEAPON_USAGE_NAMES)}
    return {"quest_counts": counts, "weapon_usage": usage,
            "brigade_points": _u32(data, BRIGADE_POINTS_AT),
            "bitfield_set_bits": sum(bin(b).count("1") for b in data[BITFIELD_AT:BITFIELD_AT + BITFIELD_SIZE])}


def unmapped_blocks(data: bytes) -> list[dict]:
    """The blocks the spec leaves unread, with their size and how many bytes are non-zero."""
    _check_size(data, CHARACTER_SIZE, "character save")
    out = []
    for name, off, size in BLOCKS:
        if name.startswith("unknown"):
            out.append({"name": name, "offset": off, "size": size,
                        "nonzero_bytes": sum(1 for b in data[off:off + size] if b)})
    return out


def dump_character(data: bytes) -> dict:
    """Everything the reader knows about one character save, as JSON-ready values."""
    _check_size(data, CHARACTER_SIZE, "character save")
    return {
        "kind": "character", "size": len(data), "profile": profile(data),
        "equipped": equipped(data), "equipped_indices": equipped_indices(data),
        "pouches": pouches(data), "item_box": item_box(data),
        "equipment_box": equipment_box(data), "guild_quests": guild_quests(data),
        "palicos": [p for p in palicos(data) if p["used"]],
        "monster_log": monster_log(data), "guild_card": guild_card(data),
        "unmapped_blocks": unmapped_blocks(data),
    }


def system_summary(data: bytes) -> dict:
    """The `system` save's extent and the bytes that differ from zero; its fields are unmapped."""
    _check_size(data, SYSTEM_SIZE, "system save")
    nonzero = [i for i, b in enumerate(data) if b]
    words = [{"offset": 0x00 + 4 * i, "value": _u32(data, 4 * i)} for i in range(8)]
    return {"kind": "system", "size": len(data), "nonzero_bytes": len(nonzero),
            "first_nonzero": nonzero[0] if nonzero else None,
            "last_nonzero": nonzero[-1] if nonzero else None, "head_words": words}


def character_problems(data: bytes) -> list[str]:
    """What is structurally wrong with a character save; empty when it passes the spec's checks."""
    if len(data) != CHARACTER_SIZE:
        return [f"size is {len(data)}, expected {CHARACTER_SIZE}"]
    out = []
    p = profile(data)
    for field in ("hunter_rank", "funds"):
        if p[field] > 0xFFFFFFFF:
            out.append(f"{field} does not fit its 32 bits")
    if p["hunter_rank"] > 999:
        out.append(f"hunter rank {p['hunter_rank']} is above 999")
    if p["funds"] > 99_999_999:
        out.append(f"funds {p['funds']} are above 99,999,999")
    for item in item_box(data):
        if item["item"] > 0x7FF:
            out.append(f"item box slot {item['slot']} has id {item['item']} above 0x7FF")
        if item["count"] > 99:
            out.append(f"item box slot {item['slot']} has count {item['count']} above 99")
    for part, rec in enumerate(equipped(data)):
        if rec["kind"] > 20:
            out.append(f"equipped part {part} has kind {rec['kind']} above 20")
    for slot in equipped_indices(data):
        if slot is not None and slot >= EQUIPMENT_BOX_COUNT:
            out.append(f"equipped index {slot} is outside the equipment box")
    for rec in equipment_box(data):
        if rec["kind"] > 20:
            out.append(f"equipment slot {rec['slot']} has kind {rec['kind']} above 20")
    for i, quest in enumerate(guild_quests(data)):
        if quest is None:
            continue
        if quest["initial_level"] > 140 or quest["level"] > 140:
            out.append(f"guild quest {i} has a level above 140")
        for monster in quest["monsters"]:
            if monster["id"] > 123:
                out.append(f"guild quest {i} names monster id {monster['id']} above 123")
    for entry in monster_log(data):
        if entry["largest"] and entry["smallest"] and entry["largest"] < entry["smallest"]:
            out.append(f"monster log entry {entry['entry']} has largest {entry['largest']} "
                       f"below smallest {entry['smallest']}")
    for palico in palicos(data):
        if palico["used"] and not palico["name"]:
            out.append(f"Palico slot {palico['slot']} has experience but no name")
    return out


def system_problems(data: bytes) -> list[str]:
    """What is structurally wrong with a `system` save; empty when it passes."""
    if len(data) != SYSTEM_SIZE:
        return [f"size is {len(data)}, expected {SYSTEM_SIZE}"]
    return []
