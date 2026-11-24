"""Quest readers: MH4U `.mib`, MHXX `.mib` and its parts, MH3U `QTDS`, and Extra Data quest slots.

Layouts and their status are in specs/quest.md; field names follow it (and its sources: the mhff wiki,
mh3u-quest-studio). Every reader takes the decrypted bytes (see dlccrypt) and returns plain dicts.
"""
from __future__ import annotations

import hashlib
import struct

SLOT = 0x2010
SLOT_DATA = 0x2000


class QuestError(ValueError):
    pass


class _Reader:
    def __init__(self, data: bytes, off: int = 0):
        self.d, self.o = data, off

    def take(self, fmt: str):
        v = struct.unpack_from("<" + fmt, self.d, self.o)
        self.o += struct.calcsize("<" + fmt)
        return v if len(v) > 1 else v[0]


def _u32(d: bytes, o: int) -> int:
    return struct.unpack_from("<I", d, o)[0]


def _utf16(d: bytes, o: int) -> str:
    end = o
    while d[end:end + 2] != b"\0\0":
        end += 2
    return d[o:end].decode("utf-16-le")


# ── Extra Data slots ──────────────────────────────────────────────────────────


def mh4u_slots(data: bytes) -> list[tuple[int, str, bytes]]:
    """A decrypted MH4U `quest*` file: 40 slots of 0x2010 bytes; a used one holds the server's file decrypted
    up to its stated size (see mh4u_slot_mib), and its file name at 0x2000. Returns (slot, name, the slot's
    0x2000 bytes)."""
    out = []
    for k in range(len(data) // SLOT):
        s = data[k * SLOT:(k + 1) * SLOT]
        if _u32(s, 0) == 0xA0 and s[4:8] == b"v005":
            out.append((k, s[SLOT_DATA:].split(b"\0")[0].decode("ascii"), s[:SLOT_DATA]))
    return out


def mh4u_slot_mib(body: bytes) -> bytes:
    """The `.mib` in a used slot's 0x2000 bytes, checked: the `.mib`, its SHA-1 with bytes 0 and 1 zeroed,
    padding to 8 (the server file's ciphertext), the `.mib` size + 20 as a u32 BE, then zeros (check Q16)."""
    for end in range(len(body.rstrip(b"\0")), 0, -1):
        if end % 8 == 4:
            break
    else:
        raise QuestError("no size trailer")
    size = struct.unpack(">I", body[end - 4:end])[0]
    if size < 20 or (size + 7) // 8 * 8 != end - 4:
        raise QuestError("size trailer doesn't fit the slot")
    mib, digest = body[:size - 20], body[size - 20:size]
    if digest[:2] != b"\0\0" or digest[2:] != hashlib.sha1(mib).digest()[2:]:
        raise QuestError("hash doesn't match the .mib")
    return mib


def mh4u_pack_slot(mib: bytes, name: str, pad: bytes = b"\0" * 8) -> bytes:
    """A 0x2010-byte slot for `mib`, in the form the game stores a downloaded quest (check Q16). The padding
    bytes are the server file's ciphertext in the game's own slots; `pad` stands in for them."""
    size = len(mib) + 20
    padded = (size + 7) // 8 * 8
    body = mib + b"\0\0" + hashlib.sha1(mib).digest()[2:] + pad[:padded - size] + struct.pack(">I", size)
    if len(body) > SLOT_DATA or len(name) > SLOT - SLOT_DATA - 1:
        raise QuestError("the quest or its name doesn't fit a slot")
    return body.ljust(SLOT_DATA, b"\0") + name.encode("ascii").ljust(SLOT - SLOT_DATA, b"\0")


def mh4u_put_slot(data: bytes, k: int, slot: bytes) -> bytes:
    """A decrypted `quest*` file with slot k replaced."""
    if len(slot) != SLOT or not 0 <= k < len(data) // SLOT:
        raise QuestError("bad slot or index")
    return data[:k * SLOT] + slot + data[(k + 1) * SLOT:]


def mib4_patch(mib: bytes, quest_id: int | None = None, title: str | None = None) -> bytes:
    """An MH4U `.mib` with a new quest id (0xC0) and/or a new title in all five languages, in place: the
    layout and every offset stay as they are, so the title must fit where each language's old one was
    (its old length, NUL included); the rest of that space is zeroed."""
    out = bytearray(mib)
    if quest_id is not None:
        if not 0 <= quest_id <= 0xFFFF:
            raise QuestError("a quest id is a u16")
        struct.pack_into("<H", out, 0xC0, quest_id)
    if title is not None:
        new = title.encode("utf-16-le") + b"\0\0"
        for lang in struct.unpack_from("<5I", mib, _u32(mib, 0xBC)):
            at = _u32(mib, lang)  # title is the first of the seven strings
            room = len(_utf16(mib, at).encode("utf-16-le")) + 2
            if len(new) > room:
                raise QuestError(f"the title needs {len(new)} bytes; this quest has room for {room}")
            out[at:at + room] = new.ljust(room, b"\0")
    return bytes(out)


def mh3u_slots(data: bytes) -> list[tuple[int, str, bytes]]:
    """An MH3U 3DS `quest*` file (not encrypted): a u32, then 20 slots of 0x2010 bytes; a used one holds the
    server file decrypted (record, SHA-1 with two bytes zeroed, padding, u32 BE size) and its name at 0x2000.
    Returns (slot, name, the QTDS record)."""
    out = []
    for k in range((len(data) - 4) // SLOT):
        s = data[4 + k * SLOT:4 + (k + 1) * SLOT]
        if s[:4] != b"QTDS":
            continue
        size = None
        for r8 in range(8, SLOT_DATA - 3, 8):  # the size trailer sits right after the padded plaintext
            n = struct.unpack_from(">I", s, r8)[0]
            if 20 < n <= r8 and (n + 7) // 8 * 8 == r8 and not any(s[r8 + 4:SLOT_DATA]):
                size = n
                break
        if size is None:
            raise QuestError(f"slot {k}: no size trailer found")
        out.append((k, s[SLOT_DATA:].split(b"\0")[0].decode("ascii"), s[:size - 20]))
    return out


# ── MH4U .mib ─────────────────────────────────────────────────────────────────

MIB4_FIELDS = (("carve_table", 0x8A, "B"), ("ai_level", 0x8B, "B"), ("spawn_area", 0x8C, "B"),
               ("arena_fence", 0x8D, "B"), ("gathering_rank", 0x89, "B"), ("flags", 0xA0, "4B"),
               ("fee", 0xA4, "I"), ("reward", 0xA8, "I"), ("faint_penalty", 0xAC, "I"), ("sub_reward", 0xB0, "I"),
               ("time_min", 0xB4, "I"), ("intruder_chance", 0xB8, "I"), ("quest_id", 0xC0, "H"),
               ("stars", 0xC2, "H"), ("map", 0xC4, "B"), ("requirements", 0xC5, "2B"),
               ("main_hrp", 0x74, "I"), ("hrp_penalty", 0x78, "I"), ("sub_hrp", 0x7C, "I"),
               ("icons", 0xE8, "5H"))
MIB4_TEXTS = ("title", "success", "failure", "summary", "main_monsters", "client", "sub_quest")
MIB4_LANGS = ("eng", "fre", "spa", "ger", "ita")


def _monster_list(d: bytes, o: int, stride: int, end_fmt: str, end_value: int, first: int = 0) -> list[dict]:
    out = []
    while struct.unpack_from("<" + end_fmt, d, o)[0] != end_value:
        b = o + first
        if len(out) >= 64 or b + 0x28 > len(d):
            raise QuestError(f"monster list at 0x{o:x} doesn't end")
        mid, count = struct.unpack_from("<2I", d, b)
        cond, area = d[b + 8], d[b + 9]
        x, y, z = struct.unpack_from("<3f", d, b + 0x10)
        entry = {"monster": mid, "count": count, "condition": cond, "area": area, "frenzy": d[b + 0xF],
                 "pos": [x, y, z]}
        if first:
            entry["chance"] = struct.unpack_from("<I", d, o)[0]
        out.append(entry)
        o += stride
    return out


def parse_mib4(d: bytes) -> dict:
    if _u32(d, 0) != 0xA0 or d[4:8] != b"v005":
        raise QuestError("not an MH4U .mib (0xA0, v005)")
    q: dict = {name: struct.unpack_from("<" + f, d, o) if len(f) > 1 else struct.unpack_from("<" + f, d, o)[0]
               for name, o, f in MIB4_FIELDS}
    q["objectives"] = [dict(zip(("type", "target", "count"), struct.unpack_from("<IHH", d, o), strict=True))
                       for o in (0xCC, 0xD4, 0xDC)]
    q["monster_stats"] = [dict(zip(("size_pct", "size_var", "health", "attack", "defense", "stamina"),
                                   struct.unpack_from("<H5B", d, o), strict=True)) for o in range(0x34, 0x64, 8)]
    boxes, o = [], _u32(d, 0x08)
    while d[o] != 0xFF:
        box_id, n, items_at = d[o], d[o + 1], _u32(d, o + 4)
        boxes.append({"box": box_id, "items": [struct.unpack_from("<HH", d, items_at + 4 * i) for i in range(n)]})
        o += 8
    q["supply"] = boxes
    rewards = {}
    for name, at in (("main", 0x1C), ("extra", 0x20), ("sub", 0x24)):
        box = _u32(d, at)
        if not box:
            continue
        items, i = [], _u32(d, box + 4)
        while struct.unpack_from("<H", d, i)[0] != 0xFFFF:
            items.append(struct.unpack_from("<3H", d, i))
            i += 6
        rewards[name] = items
    q["rewards"] = rewards
    waves, w = [], _u32(d, 0x28)
    while _u32(d, w):
        waves.append(_monster_list(d, _u32(d, w), 0x28, "I", 0xFFFFFFFF))
        w += 4
    q["large_waves"] = waves
    areas, a = [], _u32(d, _u32(d, 0x2C))
    while _u32(d, a) and _u32(d, a) < len(d):
        areas.append(_monster_list(d, _u32(d, a), 0x28, "I", 0xFFFFFFFF))
        a += 4
    q["small_areas"] = areas
    q["intruders"] = _monster_list(d, _u32(d, 0x30), 0x2C, "H", 0xFFFF, first=4)
    langs = struct.unpack_from("<5I", d, _u32(d, 0xBC))
    q["text"] = {lang: dict(zip(MIB4_TEXTS, (_utf16(d, p) for p in struct.unpack_from("<7I", d, at)), strict=True))
                 for lang, at in zip(MIB4_LANGS, langs, strict=True)}
    return q


# ── MHXX .mib and parts ───────────────────────────────────────────────────────

MIBXX_FIELDS = (("count", 0x04, "I"), ("index", 0x08, "I"), ("quest_id", 0x0C, "I"), ("type", 0x10, "B"),
                ("village", 0x11, "B"), ("stars", 0x12, "B"), ("rank", 0x13, "B"), ("map", 0x14, "B"),
                ("start_area", 0x15, "B"), ("time_min", 0x16, "B"), ("faints", 0x17, "B"),
                ("clear_type", 0x1D, "B"), ("repel_hp_pct", 0x1E, "B"), ("fee", 0x31, "I"),
                ("village_points", 0x35, "I"), ("reward", 0x39, "I"), ("sub_reward", 0x3D, "I"),
                ("small_hp_atk_other", 0xA5, "3B"), ("icons", 0xD6, "5B"), ("message_class", 0xDF, "I"))


def parse_mibxx(d: bytes) -> dict:
    if len(d) != 249:
        raise QuestError(f"an MHXX .mib is 249 bytes, not {len(d)}")
    q: dict = {name: struct.unpack_from("<" + f, d, o) if len(f) > 1 else struct.unpack_from("<" + f, d, o)[0]
               for name, o, f in MIBXX_FIELDS}
    q["objectives"] = [dict(zip(("type", "target", "count"), struct.unpack_from("<BHH", d, o), strict=True))
                       for o in (0x1F, 0x24, 0x29)]
    q["bosses"] = [struct.unpack_from("<H", d, 0x64 + 13 * i)[0] for i in range(5)]
    q["message"] = d[0xE3:0xF1].split(b"\0")[0].decode("ascii", "replace")
    return q


def parse_sem(d: bytes) -> dict:
    magic, count, rnd, area, angle, x, y, z = struct.unpack_from("<fIIIffff", d)
    if magic != 1.0 or len(d) != 0x20:
        raise QuestError("not a .sem (32 bytes, magic 1.0)")
    return {"count": count, "round": rnd, "area": area, "angle": angle, "pos": [x, y, z]}


def parse_esl(d: bytes) -> list[list[dict]]:
    if d[:4] != b"esl\0":
        raise QuestError("not an .esl")
    areas, pos = [], 0x40
    for o in struct.unpack_from("<14I", d, 8):
        if not o:
            continue
        if o != pos or d[o:o + 4] != b"ESD\0":
            raise QuestError(f"area at 0x{o:x} isn't where the previous one ends")
        n = struct.unpack_from("<H", d, o + 8)[0]
        ents = []
        for i in range(n):
            e = o + 10 + 36 * i
            ents.append({"monster": d[e], "pos": list(struct.unpack_from("<3f", d, e + 0x0C)),
                         "param": struct.unpack_from("<H", d, e + 0x1C)[0]})
        areas.append(ents)
        pos = o + 10 + 36 * n
    if areas and pos != len(d):
        raise QuestError("bytes after the last area")
    return areas


def parse_rem(d: bytes) -> dict:
    if len(d) != 0xB8 or struct.unpack_from("<f", d)[0] != 1.0:
        raise QuestError("not a .rem (184 bytes, magic 1.0)")
    return {"flags": [struct.unpack_from("<2B", d, 8 + 2 * i) for i in range(8)],
            "slots": [struct.unpack_from("<HBB", d, 0x18 + 4 * i) for i in range(40)]}


def parse_supply(d: bytes) -> list[tuple[int, int, int]]:
    if len(d) != 0xA8 or struct.unpack_from("<f", d)[0] != 1.0:
        raise QuestError("not a supply list (168 bytes, magic 1.0)")
    return [struct.unpack_from("<HBB", d, 8 + 4 * i) for i in range(40)]


# ── MH3U QTDS ─────────────────────────────────────────────────────────────────

QTDS_LANGS = ("eng", "fre", "ger", "ita", "spa")
ARENA_SET, EM_SET, TAIL = 172, 45, 442


def has_arena_block(number: int) -> bool:
    return number // 100 in (201, 202, 203) or number // 10000 == 6


def parse_qtds(d: bytes) -> dict:
    r = _Reader(d)
    if r.take("4s") != b"QTDS":
        raise QuestError("not a QTDS record")
    q: dict = {"languages": r.take("I")}
    if q["languages"] != 5:
        raise QuestError("QTDS language count isn't 5")

    def text() -> dict:
        out = {}
        for lang in QTDS_LANGS:
            n = r.take("I")
            out[lang] = d[r.o:r.o + n].decode("utf-8")
            r.o += n
        return out

    q["name"] = text()
    q["number"] = r.take("H")
    q["objective"] = text()
    q["stars"], q["map"] = r.take("BB")
    q["sub_objective"] = text()
    q["time_min"] = r.take("H")
    q["failure"] = text()
    q["special"] = r.take("3H")
    q["client"] = text()
    q["description"] = text()
    tail = r.o
    q["main_small"] = r.take("BB")
    q["category"] = r.take("Q")
    names = ("type", "set_type", "start_type", "number", "hp_row", "attack_row", "other_row", "row4", "size",
             "size_param", "stamina")
    q["monsters"] = [dict(zip(names, r.take("11B"), strict=True)) for _ in range(5)]
    q["intruder"] = r.take("6B")
    slots = [r.take("HBB") for _ in range(64)]

    def table(rows):
        out = []
        for row in rows:
            if row[0] == 0:
                break
            out.append(row)
        return out

    q["rewards_a"], q["rewards_b"] = table(slots[0::2]), table(slots[1::2])
    q["fee"], q["reward"], q["faint_penalty"], q["main_hrp"], q["failure_hrp"] = r.take("5i")
    r.o = tail + 0x193
    q["clear_pattern"] = r.take("H")
    q["objectives"] = [dict(zip(("param", "target", "count"), r.take("IHh"), strict=True)) for _ in range(2)]
    q["arena_times"] = r.take("HH")
    q["unlock_required"], q["unlock_counted"], q["clears_required"] = r.take("QQB")
    if r.o - tail != TAIL:
        raise QuestError("QTDS tail isn't 442 bytes")
    if has_arena_block(q["number"]):
        n = r.take("I")
        r.o += EM_SET * n
        q["arena_monster_sets"] = n
        n = r.take("I")
        q["arena_gear_sets"] = [list(r.take("86H")) for _ in range(n)]
    q["size"] = r.o
    return q
