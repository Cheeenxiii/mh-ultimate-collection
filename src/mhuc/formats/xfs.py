"""MT Framework XFS: reflection-serialised objects (specs/xfs.md).

An XFS file carries its own schema: one definition per class (DTI id and the property list its
createProperty() registers), then the root object. So any XFS file decodes without per-class code.

Byte order follows the magic: `XFS\\0` in file order is a little-endian file (the 3DS games, MH4U too),
`\\0SFX` a big-endian one (Wii U). Three words differ between the two:

- a class definition's property count is the count itself in a little-endian file and twice the count in a
  big-endian one (Cha-Cha xfs.md);
- a property's type, attr and size are three fields (u8, u8, u16), so the size is a u16 in the file's byte
  order;
- an object's class word is `class index << 1 | 1` little-endian and `0x8000 | class index` big-endian, the
  same flag-and-index bitfield laid out from the other end. The index is 0-based into the file's offsets.

The little-endian layout is checked against every XFS file of MH3U's and MH4U's RomFS (specs/xfs.md, check
X1); the big-endian one is Cha-Cha's and is not checked here.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

HEADER = 0x18
PROP_ENTRY = 0x28

TYPE_NAMES = {
    0x01: "class", 0x02: "classref", 0x03: "bool", 0x04: "u8", 0x05: "u16", 0x06: "u32", 0x07: "u64",
    0x08: "s8", 0x09: "s16", 0x0A: "s32", 0x0B: "s64", 0x0C: "f32", 0x0D: "f64", 0x0E: "string",
    0x0F: "color", 0x10: "point", 0x11: "size", 0x12: "rect", 0x13: "matrix", 0x14: "vector3",
    0x15: "vector4", 0x16: "quaternion", 0x20: "cstring", 0x40: "vector2?", 0x80: "resource",
}
SCALARS = {0x03: "?", 0x04: "B", 0x05: "H", 0x06: "I", 0x07: "Q", 0x08: "b", 0x09: "h", 0x0A: "i",
           0x0B: "q", 0x0C: "f", 0x0D: "d"}
FIXED = {0x0F: ("I", 1), 0x10: ("i", 2), 0x11: ("I", 2), 0x12: ("I", 4), 0x13: ("f", 16), 0x14: ("f", 4),
         0x15: ("f", 4), 0x16: ("f", 4), 0x40: ("f", 2)}
OBJECTS = (0x01, 0x02)
STRINGS = (0x0E, 0x20)
ARRAY = 0x20  # attr bit


class XfsError(ValueError):
    pass


@dataclass
class Prop:
    name: str
    type: int
    attr: int
    size: int

    @property
    def type_name(self) -> str:
        return TYPE_NAMES.get(self.type, f"0x{self.type:02x}")


@dataclass
class ClassDef:
    dti_id: int
    props: list[Prop] = field(default_factory=list)


@dataclass
class Xfs:
    endian: str
    version: int
    subversion: int
    classes: list[ClassDef]
    root: dict


def _cstring(data: bytes, off: int) -> tuple[str, int]:
    end = data.index(b"\0", off)
    return data[off:end].decode("utf-8", "replace"), end + 1


def read(data: bytes) -> Xfs:
    if data[:4] == b"XFS\0":
        e = "<"
    elif data[:4] == b"\0SFX":
        e = ">"
    else:
        raise XfsError("not an XFS file")
    version, subversion, _, _, n, def_size = struct.unpack_from(e + "HHIIII", data, 4)
    offsets = struct.unpack_from(e + f"{n}I", data, HEADER)
    classes = []
    for off in offsets:
        o = HEADER + off
        dti_id = struct.unpack_from(e + "I", data, o)[0]
        count_word = struct.unpack_from(e + "H", data, o + 4)[0]
        # the same field as the count in a little-endian file and as twice the count in a big-endian one
        count = count_word // 2 if e == ">" else count_word
        cd = ClassDef(dti_id)
        for i in range(count):
            p = o + 8 + i * PROP_ENTRY
            name_off = struct.unpack_from(e + "I", data, p)[0]
            name, _ = _cstring(data, HEADER + name_off)
            typ, attr = data[p + 4], data[p + 5]
            size = struct.unpack_from(e + "H", data, p + 6)[0]
            cd.props.append(Prop(name, typ, attr, size))
        classes.append(cd)
    root, end = _object(data, HEADER + def_size, e, classes)
    if end != len(data):
        raise XfsError(f"{len(data) - end} bytes after the root object")
    return Xfs("little" if e == "<" else "big", version, subversion, classes, root)


def _object(data: bytes, o: int, e: str, classes: list[ClassDef]) -> tuple[dict, int]:
    if e == "<":
        head, instance = struct.unpack_from("<HH", data, o)
        flag, index = head & 1, head >> 1
    else:
        head, instance = struct.unpack_from(">HH", data, o)
        flag, index = head & 0x8000, head & 0x7FFF
    (size,) = struct.unpack_from(e + "I", data, o + 4)
    if not flag or index >= len(classes):
        raise XfsError(f"bad object header at 0x{o:x}")
    start, p = o + 4, o + 8
    cd = classes[index]
    obj: dict = {"class": f"0x{cd.dti_id:08X}", "instance": instance}
    for prop in cd.props:
        (count,) = struct.unpack_from(e + "I", data, p)
        p += 4
        values = []
        for _ in range(count):
            v, p = _value(data, p, e, prop.type, classes)
            values.append(v)
        obj[prop.name] = values if prop.attr & ARRAY else (values[0] if values else None)
    if p - start != size:
        raise XfsError(f"object at 0x{o:x} uses {p - start} bytes, its size says {size}")
    return obj, p


def _value(data: bytes, p: int, e: str, t: int, classes: list[ClassDef]):
    if t in OBJECTS:
        return _object(data, p, e, classes)
    if t in SCALARS:
        f = e + SCALARS[t]
        return struct.unpack_from(f, data, p)[0], p + struct.calcsize(f)
    if t in FIXED:
        c, k = FIXED[t]
        f = e + c * k
        return list(struct.unpack_from(f, data, p)), p + struct.calcsize(f)
    if t in STRINGS:
        return _cstring(data, p)
    if t == 0x80:
        kind = data[p]
        p += 1
        if kind != 2:
            return {"kind": kind}, p
        cls, p = _cstring(data, p)
        path, p = _cstring(data, p)
        return {"kind": kind, "class": cls, "path": path}, p
    raise XfsError(f"property type 0x{t:02x} has no known encoding")
