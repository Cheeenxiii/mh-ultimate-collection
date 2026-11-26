"""MH4U's saves: the character files `user1`..`user3` and `system`, read after `mhuc decrypt mh4u-save`.

A character save is 81,400 bytes decrypted, one character per file. The `system` save is 504 bytes
decrypted and shared by the three characters; `system_summary` reads the fields that are mapped so far.
`clean_character` removes the mod's data from the structures whose layout is mapped, which is what the
converter (`mhuc save clean`) writes back as a clean MH4U save (specs/save.md, check S11).
Offsets in this module are in the decrypted file, as `mhuc decrypt mh4u-save` writes it (the cipher's
8-byte header is gone). Layouts: specs/save.md, from the community save editor mh4edit (MIT) and the
MH4G save-editor wiki for the profile, pouches, quest counts and weapon usage, and from the mhff wiki
for the monster log; each field's status is in the spec.

No game data is stored here: the module holds offsets and shapes only, and reads a file the user supplies.
"""
from __future__ import annotations

import struct

from .extdata import parse_guild_quest

CHARACTER_SIZE = 81400          # decrypted user1..user3
ENCRYPTED_CHARACTER_SIZE = 81408
SYSTEM_SIZE = 504               # decrypted system
ENCRYPTED_SYSTEM_SIZE = 512

# The `system` save's fields, as far as they are mapped (specs/save.md, check S9). The names with an
# offset are the fields the spec still leaves unknown: the module reports their values without
# giving them a meaning.
SYSTEM_VERSION_AT = 0x00        # 0 before a character exists, 1 in the saves with characters
SYSTEM_TIME_AT = 0x04           # candidate: a Unix time; it moves between saves
SYSTEM_ENTRIES_AT = 0x08        # four u32; candidates: times (or ids) that stayed put
SYSTEM_ENTRY_COUNT = 4
SYSTEM_FLAGS_AT = 0x18          # 32 bytes; candidate: option bits or DLC/quest registration
SYSTEM_FLAGS_SIZE = 0x20
SYSTEM_MARK_AT = 0x38           # 1 in every save the game writes, including before a character
SYSTEM_CHARACTER_AT = 0x3C      # 0xFFFFFFFF before a character exists, then the selected slot
SYSTEM_UNKNOWN_0X40 = 0x40
SYSTEM_UNKNOWN_0X64 = 0x64

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
GUILD_QUEST_MONSTER_AT = 0x28   # five 40-byte monster records; the id is the record's first byte
GUILD_QUEST_MONSTER_SIZE = 40
GUILD_QUEST_MONSTER_COUNT = 5
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
ITEM_FLAGS_AT = 0xF220          # one bit per item id (2,176 bits); meaning unverified (specs/save.md)
ITEM_FLAGS_SIZE = 272
QUEST_FLAGS_AT = 0x11E          # 512 flag bits, bit 0 first; what they index is unknown (specs/save.md)
QUEST_FLAGS_SIZE = 64
QUEST_FLAGS_PREFIX_AT = 0x0112  # the 12-byte field just before the flags; per-character, unknown
SHARP_ARENA_AT = 0x131A4        # the arena leaderboard block (specs/save.md); partly mapped

# The converter's bounds: what MH4U itself can have written. MH4U's item ids end at 1,936 (itemName has
# 1,937 names, reference/README.md) and its monster ids at 123 (reference/README.md#mh4u-monster-tables);
# the item id is the low 11 bits of its u16 (specs/save.md). Anything above either is not MH4U's.
ITEM_ID_MASK = 0x7FF
ITEM_ID_LAST = 1936
MH4U_MONSTER_LAST = 123

# The blocks the spec lists. (name, offset, size); the unknown blocks keep their extent only.
BLOCKS = (
    ("profile", 0x0000, PROFILE_SIZE),
    ("equipped", EQUIPPED_AT, EQUIPPED_SIZE),
    ("equipped_indices", EQUIPPED_INDEX_AT, 14),
    ("unknown_0x0112", 0x0112, 12),
    ("quest_flags", 0x011E, 64),
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
    ("item_flags", ITEM_FLAGS_AT, 280),     # the 2,176 bits, then 8 zero bytes
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


def _bit_indices(data: bytes, at: int, size: int) -> list[int]:
    """The indices of the set bits of a little-endian bit array, bit 0 first."""
    return [i for i in range(size * 8) if (data[at + (i >> 3)] >> (i & 7)) & 1]


def guild_card(data: bytes) -> dict:
    """The guild-card records in the character save: quest counts, weapon usage and brigade points."""
    _check_size(data, CHARACTER_SIZE, "character save")
    counts = {name: _u16(data, QUEST_COUNTS_AT + 2 * i) for i, name in enumerate(QUEST_COUNT_NAMES)}
    usage = {}
    for table, at in zip(("village", "gathering", "arena"), WEAPON_USAGE_AT, strict=True):
        usage[table] = {name: _u16(data, at + 2 * i) for i, name in enumerate(WEAPON_USAGE_NAMES)}
    return {"quest_counts": counts, "weapon_usage": usage,
            "brigade_points": _u32(data, BRIGADE_POINTS_AT)}


def quest_lists(data: bytes) -> dict:
    """The per-category quest completion counts, and the unproved 512-bit flag array after them.

    The 64 bytes at 0x11E are a flag array (bit 0 the low bit of the first byte): all 512 bits are set in
    the completed saves and 51 in the mid-game one, but no check proves what the indices mean. The game's
    character-creation code clears the array and sets a bit per index, so the bits are flags; whether they
    are quest clears, story flags or something else is unknown (specs/save.md).
    """
    _check_size(data, CHARACTER_SIZE, "character save")
    counts = {name: _u16(data, QUEST_COUNTS_AT + 2 * i) for i, name in enumerate(QUEST_COUNT_NAMES)}
    bits = _bit_indices(data, QUEST_FLAGS_AT, QUEST_FLAGS_SIZE)
    return {"counts": counts,
            "candidate_clear_flags": {"offset": QUEST_FLAGS_AT, "size": QUEST_FLAGS_SIZE,
                                      "set_bits": len(bits), "indices": bits, "status": "unproved"}}


def item_flags(data: bytes) -> dict:
    """The 2,176-bit array at 0xF220, indexed by item id: how many bits are set and the highest one."""
    _check_size(data, CHARACTER_SIZE, "character save")
    bits = _bit_indices(data, ITEM_FLAGS_AT, ITEM_FLAGS_SIZE)
    return {"offset": ITEM_FLAGS_AT, "size": ITEM_FLAGS_SIZE, "set_bits": len(bits),
            "highest_set": bits[-1] if bits else None}


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
        "quest_lists": quest_lists(data), "item_flags": item_flags(data),
        "unmapped_blocks": unmapped_blocks(data),
    }


def system_summary(data: bytes) -> dict:
    """The `system` save's fields, as far as they are mapped (specs/save.md, check S9).

    The fields whose meaning is still unknown are reported by offset, not given a name, so a later
    session can map them without the reader claiming a meaning it hasn't checked.
    """
    _check_size(data, SYSTEM_SIZE, "system save")
    nonzero = [i for i, b in enumerate(data) if b]
    flags = [_u32(data, SYSTEM_FLAGS_AT + 4 * i) for i in range(SYSTEM_FLAGS_SIZE // 4)]
    character = _u32(data, SYSTEM_CHARACTER_AT)
    return {
        "kind": "system", "size": len(data),
        "version": _u32(data, SYSTEM_VERSION_AT),
        "timestamp_0x04": _u32(data, SYSTEM_TIME_AT),
        "timestamps_0x08": [{"offset": SYSTEM_ENTRIES_AT + 4 * i,
                             "value": _u32(data, SYSTEM_ENTRIES_AT + 4 * i)}
                            for i in range(SYSTEM_ENTRY_COUNT)],
        "flags_0x18": {"offset": SYSTEM_FLAGS_AT, "size": SYSTEM_FLAGS_SIZE, "words": flags,
                       "set_bits": sum(bin(word).count("1") for word in flags)},
        "word_0x38": _u32(data, SYSTEM_MARK_AT),
        "character_0x3c": None if character == 0xFFFFFFFF else character,
        "word_0x40": _u32(data, SYSTEM_UNKNOWN_0X40),
        "word_0x64": _u32(data, SYSTEM_UNKNOWN_0X64),
        "nonzero_bytes": len(nonzero),
        "first_nonzero": nonzero[0] if nonzero else None,
        "last_nonzero": nonzero[-1] if nonzero else None,
    }


def clean_character(data: bytes) -> tuple[bytes, dict]:
    """A character save with the mod's data removed, and what was removed (specs/save.md, check S11).

    Only the structures whose layout is mapped are cleaned: an item-box or pouch slot whose id is above
    MH4U's item list is emptied, and a guild-quest slot that names a monster above MH4U's last id is zeroed
    whole (MH4U wrote neither record, and a quest short one monster is not one MH4U wrote either). The
    unknown blocks, the item flags and the 512-bit flag array stay as they are because their meaning is
    unmapped, and a `system` save is refused for the same reason: its DLC/quest registration is not mapped.
    """
    _check_size(data, CHARACTER_SIZE, "character save")
    out = bytearray(data)
    items = []
    for where, at, count in (("item_box", ITEM_BOX_AT, ITEM_BOX_COUNT),
                             ("item_pouch", POUCH_ITEM_AT, POUCH_ITEM_COUNT),
                             ("gunner_pouch", POUCH_GUNNER_AT, POUCH_GUNNER_COUNT)):
        for i in range(count):
            slot = at + 4 * i
            item, n = _u16(data, slot), _u16(data, slot + 2)
            if (item or n) and (item & ITEM_ID_MASK) > ITEM_ID_LAST:
                out[slot:slot + 4] = b"\0" * 4
                items.append({"where": where, "slot": i})
    quests = []
    for i in range(GUILD_QUEST_COUNT):
        at = GUILD_QUEST_AT + i * GUILD_QUEST_SIZE
        rec = data[at:at + GUILD_QUEST_SIZE]
        if not any(rec):
            continue
        monster_ids = [rec[GUILD_QUEST_MONSTER_AT + GUILD_QUEST_MONSTER_SIZE * m]
                       for m in range(GUILD_QUEST_MONSTER_COUNT)]
        if any(monster_id > MH4U_MONSTER_LAST for monster_id in monster_ids):
            out[at:at + GUILD_QUEST_SIZE] = b"\0" * GUILD_QUEST_SIZE
            quests.append({"slot": i})
    return bytes(out), {"removed_items": items, "removed_guild_quests": quests}


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
