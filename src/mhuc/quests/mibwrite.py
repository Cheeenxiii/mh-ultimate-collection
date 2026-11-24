"""Write MH4U `.mib` files: a model that keeps every byte the readers don't explain, and a builder that lays the
blocks out again and recomputes every offset (specs/quest.md, "Writing a .mib"; check Q18).

`mib4_model(mib)` splits a `.mib` into its header and blocks; `mib4_build(model)` writes one back. The model is
plain data (bytes, lists, strings), so a converter can fill it from another game's quest, and an edit (a title,
a monster, a reward) is a change to the model. The builder uses one layout, the block order every DLC quest
shares, each block on a 0x20 boundary; it doesn't reproduce the packing of every original byte for byte.
"""
from __future__ import annotations

import struct

from .quest import QuestError, _u32, _utf16

HEADER = 0xF4
POINTERS = {"supply": 0x08, "reward_main": 0x1C, "reward_extra": 0x20, "reward_sub": 0x24, "waves": 0x28,
            "small": 0x2C, "intruders": 0x30, "langs": 0xBC, "presets": 0xE4}
REWARDS = ("main", "extra", "sub")
DEF = 0x28
INTRUDER = 0x2C


def _defs(m: bytes, o: int, stride: int, end) -> list[bytes]:
    out = []
    while not end(o):
        if len(out) >= 64 or o + stride > len(m):
            raise QuestError(f"list at {o:#x} doesn't end")
        out.append(m[o:o + stride])
        o += stride
    return out


def _targets(m: bytes) -> list[int]:
    """Every offset the header and its lists point at, to bound the blocks the model keeps raw."""
    t = [_u32(m, at) for at in POINTERS.values() if _u32(m, at)]
    o = _u32(m, 0x08)
    while m[o] != 0xFF:
        t.append(_u32(m, o + 4))
        o += 8
    for lang in struct.unpack_from("<5I", m, _u32(m, 0xBC)):
        t.append(lang)
        t.extend(struct.unpack_from("<7I", m, lang))
    return sorted(set(t)) + [len(m)]


def mib4_model(m: bytes) -> dict:
    if _u32(m, 0) != 0xA0 or m[4:8] != b"v005":
        raise QuestError("not an MH4U .mib (0xA0, v005)")
    header = bytearray(m[:HEADER])
    for at in POINTERS.values():  # offsets are the builder's business
        struct.pack_into("<I", header, at, 0)
    model: dict = {"header": bytes(header)}
    langs = struct.unpack_from("<5I", m, _u32(m, 0xBC))
    model["texts"] = [[_utf16(m, p) for p in struct.unpack_from("<7I", m, lang)] for lang in langs]
    pre = _u32(m, 0xE4)
    model["presets"] = m[pre:min(t for t in _targets(m) if t > pre)] if pre else None
    boxes, o = [], _u32(m, 0x08)
    while m[o] != 0xFF:
        boxes.append((m[o:o + 4], m[_u32(m, o + 4):_u32(m, o + 4) + 4 * m[o + 1]]))
        o += 8
    model["supply"] = boxes
    model["rewards"] = {}
    for name in REWARDS:
        box = _u32(m, POINTERS["reward_" + name])
        if box:
            items = _defs(m, _u32(m, box + 4), 6, lambda i: struct.unpack_from("<H", m, i)[0] == 0xFFFF)
            model["rewards"][name] = (m[box:box + 4], items)
    ends = lambda i: _u32(m, i) == 0xFFFFFFFF  # noqa: E731
    waves, w = [], _u32(m, 0x28)
    while _u32(m, w):
        waves.append(_defs(m, _u32(m, w), DEF, ends))
        w += 4
    model["waves"] = waves
    areas, a = [], _u32(m, _u32(m, 0x2C))
    while _u32(m, a) and _u32(m, a) < len(m):
        areas.append(_defs(m, _u32(m, a), DEF, ends))
        a += 4
    model["small_areas"] = areas
    model["intruders"] = _defs(m, _u32(m, 0x30), INTRUDER, lambda i: struct.unpack_from("<H", m, i)[0] == 0xFFFF)
    return model


class _Out:
    def __init__(self):
        self.b = bytearray()

    def align(self, n: int = 0x20) -> int:
        self.b += bytes(-len(self.b) % n)
        return len(self.b)

    def put(self, data: bytes, align: int = 0x20) -> int:
        at = self.align(align)
        self.b += data
        return at


def mib4_build(model: dict) -> bytes:
    out = _Out()
    out.b += model["header"][:HEADER]
    if len(out.b) != HEADER:
        raise QuestError(f"the header is {HEADER:#x} bytes")
    ptr: dict = {}
    tables = []
    for texts in model["texts"]:
        if len(texts) != 7:
            raise QuestError("each language has 7 strings")
        offs = [out.put(t.encode("utf-16-le") + b"\0\0") for t in texts]
        tables.append(out.put(struct.pack("<7I", *offs), 4))
    if len(tables) != 5:
        raise QuestError("a .mib has 5 languages")
    ptr["langs"] = out.put(struct.pack("<5I", *tables))
    ptr["presets"] = out.put(model["presets"]) if model.get("presets") else 0
    item_at = [out.put(items, 4) for _, items in model["supply"]]
    boxes = b"".join(head[:4] + struct.pack("<I", at) for (head, _), at in zip(model["supply"], item_at, strict=True))
    ptr["supply"] = out.put(boxes + b"\xff" + bytes(7))
    for name in REWARDS:
        if name not in model["rewards"]:
            ptr["reward_" + name] = 0
            continue
        head, items = model["rewards"][name]
        at = out.put(b"".join(items) + b"\xff\xff\0\0")
        ptr["reward_" + name] = out.put(head[:4] + struct.pack("<I", at), 4)
    end = b"\xff\xff\xff\xff" + bytes(4)
    area_at = [out.put(b"".join(defs) + end) for defs in model["small_areas"]]
    alist = out.put(struct.pack(f"<{len(area_at)}I", *area_at) + bytes(4))
    ptr["small"] = out.put(struct.pack("<3I", alist, alist, alist), 4)
    wave_at = [out.put(b"".join(defs) + end) for defs in model["waves"]]
    ptr["waves"] = out.put(struct.pack(f"<{len(wave_at)}I", *wave_at) + bytes(4))
    ptr["intruders"] = out.put(b"".join(model["intruders"]) + b"\xff\xff\0\0")
    out.align()
    for name, at in POINTERS.items():
        struct.pack_into("<I", out.b, at, ptr[name])
    return bytes(out.b)


def mib4_set_texts(model: dict, index: int, text: str, langs: range = range(5)) -> dict:
    """The model with string `index` (0 title .. 6 sub-quest; quest.MIB4_TEXTS) set in the given languages."""
    new = dict(model)
    new["texts"] = [list(t) for t in model["texts"]]
    for lang in langs:
        new["texts"][lang][index] = text
    return new


# ── JSON form: the model with the known fields decoded and the rest as hex ─────

def _def_json(raw: bytes, first: int = 0) -> dict:
    b = raw[first:]
    mid, count = struct.unpack_from("<2I", b, 0)
    out = {"monster": mid, "count": count, "condition": b[8], "area": b[9], "frenzy": b[0xF],
           "pos": list(struct.unpack_from("<3f", b, 0x10)), "raw": raw.hex()}
    if first:
        out["chance"] = struct.unpack_from("<I", raw, 0)[0]
    return out


def _def_bytes(obj: dict, size: int, first: int = 0) -> bytes:
    b = bytearray(bytes.fromhex(obj["raw"]) if obj.get("raw") else bytes(size))
    if len(b) != size:
        raise QuestError(f"a definition is {size:#x} bytes")
    if first:
        struct.pack_into("<I", b, 0, obj.get("chance", struct.unpack_from("<I", b, 0)[0]))
    struct.pack_into("<2I", b, first, obj["monster"], obj["count"])
    b[first + 8], b[first + 9], b[first + 0xF] = obj["condition"], obj["area"], obj["frenzy"]
    struct.pack_into("<3f", b, first + 0x10, *obj["pos"])
    return bytes(b)


def model_to_json(model: dict) -> dict:
    from .quest import MIB4_FIELDS, MIB4_LANGS, MIB4_TEXTS
    h = model["header"]
    fields = {}
    for name, o, f in MIB4_FIELDS:
        v = struct.unpack_from("<" + f, h, o)
        fields[name] = list(v) if len(v) > 1 else v[0]
    return {
        "format": "mhuc mib4 model 1",
        "fields": fields,
        "header": h.hex(),
        "texts": {lang: dict(zip(MIB4_TEXTS, t, strict=True)) for lang, t in zip(MIB4_LANGS, model["texts"],
                                                                                 strict=True)},
        "presets": model["presets"].hex() if model.get("presets") else None,
        "supply": [{"head": head.hex(), "items": [list(struct.unpack_from("<HH", items, 4 * i))
                                                  for i in range(len(items) // 4)]}
                   for head, items in model["supply"]],
        "rewards": {name: {"head": head.hex(), "items": [list(struct.unpack("<3H", it)) for it in items]}
                    for name, (head, items) in model["rewards"].items()},
        "waves": [[_def_json(d) for d in wave] for wave in model["waves"]],
        "small_areas": [[_def_json(d) for d in area] for area in model["small_areas"]],
        "intruders": [_def_json(d, 4) for d in model["intruders"]],
    }


def model_from_json(obj: dict) -> dict:
    from .quest import MIB4_FIELDS, MIB4_LANGS, MIB4_TEXTS
    if obj.get("format") != "mhuc mib4 model 1":
        raise QuestError("not an mhuc mib4 model")
    h = bytearray(bytes.fromhex(obj["header"]))
    for name, o, f in MIB4_FIELDS:  # the decoded fields win over the raw header
        v = obj["fields"][name]
        struct.pack_into("<" + f, h, o, *(v if isinstance(v, list) else [v]))
    supply = []
    for box in obj["supply"]:
        head = bytearray(bytes.fromhex(box["head"]))
        head[1] = len(box["items"])  # the slot count follows the list
        supply.append((bytes(head), b"".join(struct.pack("<HH", *it) for it in box["items"])))
    return {
        "header": bytes(h),
        "texts": [[obj["texts"][lang][t] for t in MIB4_TEXTS] for lang in MIB4_LANGS],
        "presets": bytes.fromhex(obj["presets"]) if obj.get("presets") else None,
        "supply": supply,
        "rewards": {name: (bytes.fromhex(r["head"]), [struct.pack("<3H", *it) for it in r["items"]])
                    for name, r in obj["rewards"].items()},
        "waves": [[_def_bytes(d, DEF) for d in wave] for wave in obj["waves"]],
        "small_areas": [[_def_bytes(d, DEF) for d in area] for area in obj["small_areas"]],
        "intruders": [_def_bytes(d, INTRUDER, 4) for d in obj["intruders"]],
    }
