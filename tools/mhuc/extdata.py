"""MH4U Extra Data besides quests: `card*` (guild cards, guild quests, sets), `cardbox` and `otomo1` (DLC Palicos).

Every function reads a file already decrypted with `mhuc decrypt mh4u-save` (mode `card` for `card*`, `normal` for
`cardbox` and `otomo1`). Layouts: specs/extdata.md, from the mhff wiki's "MH4U card1 Format", "MH4U Guild Quest
Structure" and "MH4U DLC Palico Format" pages (svanheulen/mhff, GPL-3.0), checked as that spec's checks E1-E4 say.
"""
from __future__ import annotations

import struct

# ── card* (offsets in the decrypted file) ──────────────────────────────────────

CARD_SIZE = 0x78BF8
# name: (offset, record size, count)
CARD_SECTIONS = {
    "header": (0x00000, 16, 1),
    "guild_cards": (0x00010, 4608, 100),
    "unknown64": (0x70810, 64, 100),
    "guild_quests": (0x72110, 304, 50),
    "equipment_sets": (0x75C70, 86, 40),
    "item_sets": (0x769E0, 156, 24),
    "unknown36": (0x77880, 36, 24),
    "shoutouts": (0x77BE0, 64, 18),
    "auto_shoutouts": (0x78060, 64, 6),
    "tail": (0x781E0, 2584, 1),
}
AUTO_SHOUTOUTS = ("mount", "pinned", "bomb", "slept", "stunned", "faint")


def card_layout_problems() -> list[str]:
    """The sections must tile the file exactly, in order (a check on the table itself)."""
    problems, pos = [], 0
    for name, (off, size, count) in CARD_SECTIONS.items():
        if off != pos:
            problems.append(f"{name} starts at {off:#x}, expected {pos:#x}")
        pos = off + size * count
    if pos != CARD_SIZE:
        problems.append(f"sections end at {pos:#x}, the file is {CARD_SIZE:#x}")
    return problems


def card_records(data: bytes, section: str) -> list[bytes]:
    off, size, count = CARD_SECTIONS[section]
    return [data[off + i * size: off + (i + 1) * size] for i in range(count)]


def card_summary(data: bytes) -> dict:
    """Used (non-zero) records per section; counts only."""
    if len(data) != CARD_SIZE:
        raise ValueError(f"a decrypted card file is {CARD_SIZE} bytes, not {len(data)}")
    return {name: sum(1 for r in card_records(data, name) if any(r)) for name in CARD_SECTIONS}


def _utf16z(raw: bytes) -> str:
    end = 0
    while end + 1 < len(raw) and raw[end:end + 2] != b"\0\0":
        end += 2
    return raw[:end].decode("utf-16-le", "replace")


def parse_guild_quest(rec: bytes) -> dict:
    """One 304-byte guild quest record (mhff "MH4U Guild Quest Structure"; unverified: no record seen yet)."""
    if len(rec) != 304:
        raise ValueError("a guild quest record is 304 bytes")
    monsters = []
    for i in range(5):
        m = rec[0x28 + 40 * i: 0x28 + 40 * (i + 1)]
        a = rec[0xF0 + 7 * i: 0xF0 + 7 * (i + 1)]
        monsters.append({"id": m[0], "spawn_area": m[9], "other_area": a[0], "sleep_area": a[1],
                         "spawn_subareas": list(a[2:7]), "frenzy": rec[0x12B + i]})
    areas = [{"map": rec[0x114 + 4 * i + 1], "entrance": rec[0x114 + 4 * i + 2],
              "exit": rec[0x114 + 4 * i + 3]} for i in range(5)]
    return {
        "owner": _utf16z(rec[0:24]),
        "unique_id": rec[0x18:0x20].hex(),
        "companion": rec[0x22], "poogie_type": rec[0x23], "companion_area": rec[0x24],
        "weapon_bias": rec[0x25], "armor_series_bias": rec[0x26], "armor_type_bias": rec[0x27],
        "monsters": monsters, "areas": areas,
        "initial_level": rec[0x128], "level": rec[0x129], "treasure_area": rec[0x12A],
    }


# ── otomo1 (DLC Palicos) ───────────────────────────────────────────────────────

OTOMO_SLOT = 0x90
OTOMO_SLOTS = 9
OTOMO_NAME = 0x80  # the slot's file name field, 15 bytes NUL-padded; byte 0x8F is unknown
OTB_HEADER = 0x24


def parse_otb(data: bytes) -> dict:
    """A DLC Palico record (`.otb`, mhff "MH4U DLC Palico Format"): a 0x24-byte header, the offset of a
    three-entry text-offset table, UTF-16 strings (owner, name, greeting)."""
    if len(data) < OTB_HEADER + 4:
        raise ValueError("too short for an .otb header")
    table = struct.unpack_from("<I", data, OTB_HEADER)[0]
    if not OTB_HEADER + 4 <= table <= len(data) - 12:
        raise ValueError(f"text table offset {table:#x} out of range")
    texts = struct.unpack_from("<3I", data, table)
    for t in texts:
        if not OTB_HEADER + 4 <= t < table:
            raise ValueError(f"text offset {t:#x} outside the string block")
    if data[0x1F] != 0xFF or data[0x23] != 0xFF:
        raise ValueError("colour terminators are not 0xFF")
    owner, name, greeting = (_utf16z(data[t:table]) for t in texts)
    return {
        "level": data[8], "forte": data[0x0B],
        "skills": {"quest": list(data[0x0C:0x0F]), "signature": data[0x0F], "meownster": data[0x10],
                   "casting": data[0x11], "team_attack": data[0x12]},
        "looks": {"coat": data[0x13], "clothing": data[0x14], "voice": data[0x15], "eyes": data[0x16],
                  "ears": data[0x17], "tail": data[0x18]},
        "palico_id": data[0x19],
        "coat_rgb": list(data[0x1C:0x1F]), "clothing_rgb": list(data[0x20:0x23]),
        "owner": owner, "name": name, "greeting": greeting,
        "size": table + 12,
    }


def otomo_slots(data: bytes) -> list[dict]:
    """The used Palico slots of a decrypted `otomo1`: the record, its file name and the unknown last byte."""
    out = []
    for i in range(OTOMO_SLOTS):
        s = data[i * OTOMO_SLOT: (i + 1) * OTOMO_SLOT]
        if len(s) < OTOMO_SLOT or not any(s):
            continue
        rec = parse_otb(s[:OTOMO_NAME])
        if any(s[rec["size"]:OTOMO_NAME]):
            raise ValueError(f"slot {i}: bytes between the record and the name field")
        rec["file"] = s[OTOMO_NAME:OTOMO_NAME + 15].split(b"\0")[0].decode("ascii")
        rec["slot"], rec["last_byte"] = i, s[OTOMO_SLOT - 1]
        out.append(rec)
    return out
