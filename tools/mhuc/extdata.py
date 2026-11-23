"""MH4U Extra Data besides quests: `card*` (guild cards, guild quests, sets), `cardbox` and `otomo1` (DLC Palicos).

Every function reads a file already decrypted with `mhuc decrypt mh4u-save` (mode `card` for `card*`, `normal` for
`cardbox` and `otomo1`). Layouts: specs/extdata.md, from the mhff wiki's "MH4U card1 Format", "MH4U Guild Quest
Structure" and "MH4U DLC Palico Format" pages (svanheulen/mhff, GPL-3.0), checked as that spec's checks E1-E4 say.
"""
from __future__ import annotations

import hashlib
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
OTOMO_NAME = 0x80  # the slot's file name field, 15 bytes NUL-padded; byte 0x8F is SHA-1 byte 15
OTOMO_RECORD = 0x80  # the server's plaintext: the record zero-padded to 0x80 (then its SHA-1, check E6)
OTOMO_TAIL = 12  # after the last used slot: SHA-1 bytes 16..19, 4 padding bytes, the size 0x94 as a u32 BE
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


def otomo_digest(rec: bytes) -> bytes:
    """SHA-1 of a Palico record as the server sent it: zero-padded to 0x80 bytes."""
    return hashlib.sha1(rec.ljust(OTOMO_RECORD, b"\0")).digest()


def otomo_slots(data: bytes) -> list[dict]:
    """The used Palico slots of a decrypted `otomo1` (a slot is used when its name field is): the record,
    its file name, the last byte and whether that byte is the record's SHA-1 byte 15 (check E6)."""
    out = []
    for i in range(OTOMO_SLOTS):
        s = data[i * OTOMO_SLOT: (i + 1) * OTOMO_SLOT]
        if len(s) < OTOMO_SLOT or not s[OTOMO_NAME]:
            continue
        rec = parse_otb(s[:OTOMO_NAME])
        if any(s[rec["size"]:OTOMO_NAME]):
            raise ValueError(f"slot {i}: bytes between the record and the name field")
        rec["file"] = s[OTOMO_NAME:OTOMO_NAME + 15].split(b"\0")[0].decode("ascii")
        rec["slot"], rec["last_byte"] = i, s[OTOMO_SLOT - 1]
        rec["hash_ok"] = otomo_digest(s[:OTOMO_NAME])[15] == rec["last_byte"]
        out.append(rec)
    return out


def otomo_tail(rec: bytes, pad: bytes = b"\0" * 4) -> bytes:
    """The 12 bytes the game leaves after the last used slot (check E6); the padding bytes are the server
    file's ciphertext in the game's own data, and `pad` stands in for them."""
    return otomo_digest(rec)[16:] + pad[:4] + struct.pack(">I", OTOMO_RECORD + 20)


def otomo_problems(data: bytes) -> list[str]:
    """Check E6 on a decrypted `otomo1`: every slot's last byte, and the tail after the last used slot."""
    slots = otomo_slots(data)
    problems = [f"slot {s['slot']}: last byte isn't the record's SHA-1 byte 15" for s in slots if not s["hash_ok"]]
    if slots:
        last = slots[-1]["slot"]
        at = (last + 1) * OTOMO_SLOT
        rec = data[last * OTOMO_SLOT: last * OTOMO_SLOT + OTOMO_NAME]
        want = otomo_tail(rec)
        got = data[at:at + OTOMO_TAIL]
        if got[:4] != want[:4] or got[8:] != want[8:]:
            problems.append(f"the {OTOMO_TAIL} bytes after slot {last} aren't its hash tail and size")
    return problems


def set_otb_texts(rec: bytes, owner: str | None = None, name: str | None = None,
                  greeting: str | None = None) -> bytes:
    """Rebuild an `.otb` record with new strings: the header is kept, the strings and the text table are
    rewritten in the game's order and padding (owner, name, greeting, table); with the same strings the result
    is byte-identical to the game's records (check E2)."""
    old = parse_otb(rec)
    texts = [old["owner"] if owner is None else owner, old["name"] if name is None else name,
             old["greeting"] if greeting is None else greeting]
    out, offsets = bytearray(rec[:OTB_HEADER] + bytes(4)), []
    for t in texts:  # the game's padding (check E2): each string starts at align8(previous end + 1)
        offsets.append(len(out))
        out += t.encode("utf-16-le") + b"\0\0"
        out += bytes(-(len(out) + 1) % 8 + 1) if t is not texts[-1] else b""
    out += bytes(-(len(out) + 1) % 4 + 1)  # and the table at align4(end + 1)
    table = len(out)
    struct.pack_into("<I", out, OTB_HEADER, table)
    out = bytes(out) + struct.pack("<3I", *offsets)
    if len(out) > OTOMO_NAME:
        raise ValueError(f"the record would be {len(out)} bytes; a slot holds {OTOMO_NAME}")
    return out


def put_otomo_slot(data: bytes, slot: int, rec: bytes, file: str, last_byte: int | None = None) -> bytes:
    """`otomo1` with one slot replaced, in the form the game leaves (check E6): the record, zeros, the file name,
    the record's SHA-1 byte 15 (or `last_byte`); and, when no used slot follows, the 12-byte tail after it."""
    if not 0 <= slot < OTOMO_SLOTS:
        raise ValueError(f"slot is 0..{OTOMO_SLOTS - 1}")
    if len(rec) > OTOMO_NAME or not 0 < len(file) <= 15:
        raise ValueError("record or file name too long for a slot")
    s = bytearray(OTOMO_SLOT)
    s[:len(rec)] = rec
    s[OTOMO_NAME:OTOMO_NAME + len(file)] = file.encode("ascii")
    s[-1] = otomo_digest(rec)[15] if last_byte is None else last_byte
    out = bytearray(data[:slot * OTOMO_SLOT] + bytes(s) + data[(slot + 1) * OTOMO_SLOT:])
    if not any(x["slot"] > slot for x in otomo_slots(bytes(out))):
        at = (slot + 1) * OTOMO_SLOT
        old = data[at:at + OTOMO_TAIL] if len(data) >= at + OTOMO_TAIL else b""
        pad = old[4:8] if len(old) == OTOMO_TAIL and old[8:] == struct.pack(">I", OTOMO_RECORD + 20) else b"\0" * 4
        out[at:at + OTOMO_TAIL] = otomo_tail(rec, pad)
    return bytes(out)


def rename_palico(data: bytes, slot: int, name: str, last_byte: int | None = None) -> bytes:
    """Check E4's edit: give the Palico in `slot` a new name, keeping everything else; the check byte (and the
    tail, for the last slot) follow the new record unless `last_byte` is given."""
    found = {s["slot"]: s for s in otomo_slots(data)}
    if slot not in found:
        raise ValueError(f"slot {slot} is empty")
    s = found[slot]
    raw = data[slot * OTOMO_SLOT: slot * OTOMO_SLOT + s["size"]]
    return put_otomo_slot(data, slot, set_otb_texts(raw, name=name), s["file"], last_byte)
