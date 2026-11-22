"""GMD text tables (rGUIMessage), versions 1 and 2 (specs/gmd.md).

Header, 0x28 bytes, little endian:
    0x00 char[4] "GMD\\0"     0x04 u32 version (0x00010201 v1, 0x00010302 v2)
    0x08 u32 language         0x0C u64 unknown
    0x14 u32 label count      0x18 u32 section (string) count
    0x1C u32 label bytes      0x20 u32 section bytes
    0x24 u32 name length      then the name and a NUL
MH3U's v1 tables have a 0x20-byte header: the same fields without the u64 (layout "v1-short").
v1: label entries {u32 section, u32 offset}. v2 on 3DS comes in two layouts (MHXX has both):
"v2", entries of 0x20 bytes {u32 section, u32 hash1, u32 hash2, u32 0, u64 offset, u64 link}
then 0x800 bytes of hash buckets; "v2-32", entries of 0x14 bytes {u32 section, u32 hash1,
u32 hash2, u32 offset, u32 link} then 0x400 bytes. The buckets follow only when there are
labels. The layout is told apart by the file size. Then the labels (NUL-terminated; offsets count
from the first entry's), then the strings, NUL-terminated, in section order.

Text obfuscation that some MT titles apply to the strings is not handled (none is assumed on
3DS; unverified).
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field

MAGIC = b"GMD\0"
V1, V2 = 0x00010201, 0x00010302
HEADER = struct.Struct("<4sIIQIIIII")
LANGUAGES = ("Japanese", "English", "French", "Spanish", "German", "Italian")


@dataclass
class Gmd:
    name: str
    strings: list[str]
    labels: dict[int, str] = field(default_factory=dict)   # section index -> label
    version: int = V1
    language: int = 1
    unknown: int = 0
    layout: str = ""          # "v1", "v1-short", "v2", "v2-32"; empty: the version's default
    raw_index: tuple | None = None   # (labels, entries+buckets, label bytes) as read, for round trips


def _cstr(data: bytes, pos: int) -> tuple[str, int]:
    end = data.index(b"\0", pos)
    return data[pos:end].decode("utf-8"), end + 1


LAYOUTS = {   # header size, entry size, bucket bytes
    "v1": (0x28, 8, 0), "v1-short": (0x20, 8, 0), "v2": (0x28, 0x20, 0x800), "v2-32": (0x28, 0x14, 0x400),
}
SHORT_HEADER = struct.Struct("<4sIIIIIII")


def layout_of(data: bytes) -> str:
    """Which layout a table uses, from its version and the size its counts imply."""
    version = struct.unpack_from("<I", data, 4)[0]
    if version == V1:
        nl, ns, lb, sb, nlen = struct.unpack_from("<5I", data, 0x0C)
        return "v1-short" if 0x20 + nlen + 1 + nl * 8 + lb + sb == len(data) else "v1"
    nl, ns, lb, sb, nlen = struct.unpack_from("<5I", data, 0x14)
    base = 0x28 + nlen + 1 + lb + sb
    if nl and base + nl * 0x14 + 0x400 == len(data):
        return "v2-32"
    return "v2"


def read(data: bytes) -> Gmd:
    if data[:4] != MAGIC:
        raise ValueError("not a GMD file (magic)")
    version = struct.unpack_from("<I", data, 4)[0]
    if version not in (V1, V2):
        raise ValueError(f"GMD version 0x{version:08x} isn't one mhuc knows")
    layout = layout_of(data)
    hsize, esize, buckets = LAYOUTS[layout]
    if layout == "v1-short":
        _, _, language, nlabels, nsections, label_bytes, _sb, name_len = SHORT_HEADER.unpack_from(data)
        unknown = 0
    else:
        (_, _, language, unknown, nlabels, nsections, label_bytes, _sb, name_len) = HEADER.unpack_from(data)
    pos = hsize
    name = data[pos:pos + name_len].decode("utf-8")
    pos += name_len + 1
    index_at = pos
    entries = []
    for _ in range(nlabels):
        if esize == 8:
            sec, off = struct.unpack_from("<iI", data, pos)
        elif esize == 0x14:
            sec, _h1, _h2, off, _link = struct.unpack_from("<iIIII", data, pos)
        else:
            sec, _h1, _h2, _z, off, _link = struct.unpack_from("<iIIIQQ", data, pos)
        pos += esize
        entries.append((sec, off))
    if nlabels:
        pos += buckets
    index = data[index_at:pos]
    labels = {}
    if entries:
        base = min(off for _, off in entries)
        for sec, off in entries:
            labels[sec] = _cstr(data, pos + off - base)[0]
    label_blob = data[pos:pos + label_bytes]
    pos += label_bytes
    strings = []
    for _ in range(nsections):
        s, pos = _cstr(data, pos)
        strings.append(s)
    return Gmd(name, strings, labels, version, language, unknown, layout, (dict(labels), index, label_blob))


def _label_hashes(label: str) -> tuple[int, int]:
    # placeholders: the real hash functions are unknown (specs/gmd.md)
    b = label.encode("utf-8")
    return zlib.crc32(b) ^ 0xFFFFFFFF, zlib.crc32(b + b) ^ 0xFFFFFFFF


def write(g: Gmd) -> bytes:
    """Serialise. Tables read from a file keep their label index (hashes, buckets) byte for byte
    while their labels are unchanged. New v2 indexes get zeroed buckets and placeholder hashes:
    fine for tools, not known to be accepted by the game (unverified)."""
    layout = g.layout or ("v1" if g.version == V1 else "v2")
    _, esize, buckets = LAYOUTS[layout]
    name = g.name.encode("utf-8")
    if g.raw_index is not None and g.raw_index[0] == g.labels:
        _, index, label_blob = g.raw_index
    else:
        index, label_blob = bytearray(), bytearray()
        for sec in sorted(g.labels):
            off = len(label_blob)
            label = g.labels[sec]
            h1, h2 = _label_hashes(label)
            if esize == 8:
                index += struct.pack("<iI", sec, off)
            elif esize == 0x14:
                index += struct.pack("<iIIII", sec, h1, h2, off, 0)
            else:
                index += struct.pack("<iIIIQQ", sec, h1, h2, 0, off, 0)
            label_blob += label.encode("utf-8") + b"\0"
        if g.labels:
            index += bytes(buckets)
    text = b"".join(s.encode("utf-8") + b"\0" for s in g.strings)
    if layout == "v1-short":
        header = SHORT_HEADER.pack(MAGIC, g.version, g.language, len(g.labels), len(g.strings),
                                   len(label_blob), len(text), len(name))
    else:
        header = HEADER.pack(MAGIC, g.version, g.language, g.unknown, len(g.labels), len(g.strings),
                             len(label_blob), len(text), len(name))
    return header + name + b"\0" + bytes(index) + bytes(label_blob) + text


def to_json(g: Gmd) -> dict:
    return {
        "name": g.name, "version": f"0x{g.version:08x}", "language": g.language,
        "entries": [{"index": i, "label": g.labels.get(i), "text": s} for i, s in enumerate(g.strings)],
    }
