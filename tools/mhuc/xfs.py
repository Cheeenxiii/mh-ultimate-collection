"""MT Framework XFS: reflection-serialised objects (specs/xfs.md).

An XFS file carries its own schema: one definition per class (DTI id and the property list its
createProperty() registers), then the root object. So any XFS file decodes without per-class code.

Byte order follows the magic: `XFS\\0` in file order is a little-endian file (3DS), `\\0SFX` a big-endian
one (Wii U). Packed words (a property's type/attr/size, an object's class/instance) are read as u32 in the
file's byte order, which reproduces the big-endian layout Cha-Cha documents; for little-endian files that
reading is unverified (specs/xfs.md, check X1).
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
        dti_id, count2, _ = struct.unpack_from(e + "IHH", data, o)
        cd = ClassDef(dti_id)
        for i in range(count2 // 2):
            p = o + 8 + i * PROP_ENTRY
            name_off, packed = struct.unpack_from(e + "II", data, p)
            name, _ = _cstring(data, HEADER + name_off)
            cd.props.append(Prop(name, packed >> 24, (packed >> 16) & 0xFF, packed & 0xFFFF))
        classes.append(cd)
    root, end = _object(data, HEADER + def_size, e, classes)
    if end != len(data):
        raise XfsError(f"{len(data) - end} bytes after the root object")
    return Xfs("little" if e == "<" else "big", version, subversion, classes, root)


def _object(data: bytes, o: int, e: str, classes: list[ClassDef]) -> tuple[dict, int]:
    head, size = struct.unpack_from(e + "II", data, o)
    index, instance = (head >> 16) & 0x7FFF, head & 0xFFFF
    if not head & 0x80000000 or index >= len(classes):
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
