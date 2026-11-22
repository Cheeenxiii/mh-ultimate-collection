"""GMD text tables (rGUIMessage), versions 1 and 2 (specs/gmd.md).

Header, 0x28 bytes, little endian:
    0x00 char[4] "GMD\\0"     0x04 u32 version (0x00010201 v1, 0x00010302 v2)
    0x08 u32 language         0x0C u64 unknown
    0x14 u32 label count      0x18 u32 section (string) count
    0x1C u32 label bytes      0x20 u32 section bytes
    0x24 u32 name length      then the name and a NUL
v1: label entries {u32 section, u32 offset}; v2 on 3DS ("mobile", Kuriimu2): label entries of
0x20 bytes {u32 section, u32 hash1, u32 hash2, u32 0, u64 offset, u64 list link}, then 0x800
bytes of hash buckets when there are labels. Then the labels (NUL-terminated; offsets count
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


def _cstr(data: bytes, pos: int) -> tuple[str, int]:
    end = data.index(b"\0", pos)
    return data[pos:end].decode("utf-8"), end + 1


def read(data: bytes) -> Gmd:
    if data[:4] != MAGIC:
        raise ValueError("not a GMD file (magic)")
    (_, version, language, unknown, nlabels, nsections, label_bytes, _section_bytes,
     name_len) = HEADER.unpack_from(data)
    if version not in (V1, V2):
        raise ValueError(f"GMD version 0x{version:08x} isn't one mhuc knows")
    pos = HEADER.size
    name = data[pos:pos + name_len].decode("utf-8")
    pos += name_len + 1
    entries = []
    for _ in range(nlabels):
        if version == V1:
            sec, off = struct.unpack_from("<iI", data, pos)
            pos += 8
        else:
            sec, _h1, _h2, _z, off, _link = struct.unpack_from("<iIIIQQ", data, pos)
            pos += 0x20
        entries.append((sec, off))
    if version == V2 and nlabels:
        pos += 0x800
    labels = {}
    if entries:
        base = entries[0][1]
        for sec, off in entries:
            labels[sec] = _cstr(data, pos + off - base)[0]
    pos += label_bytes
    strings = []
    for _ in range(nsections):
        s, pos = _cstr(data, pos)
        strings.append(s)
    return Gmd(name, strings, labels, version, language, unknown)


def _label_hashes(label: str) -> tuple[int, int]:
    # placeholders: the real hash functions are unknown (specs/gmd.md)
    b = label.encode("utf-8")
    return zlib.crc32(b) ^ 0xFFFFFFFF, zlib.crc32(b + b) ^ 0xFFFFFFFF


def write(g: Gmd) -> bytes:
    """Serialise. v2 writes zeroed hash buckets and placeholder hashes: fine for tools, not
    known to be accepted by the game (unverified)."""
    name = g.name.encode("utf-8")
    order = sorted(g.labels)
    label_blob = bytearray()
    entries = bytearray()
    for sec in order:
        off = len(label_blob)
        label = g.labels[sec]
        if g.version == V1:
            entries += struct.pack("<iI", sec, off)
        else:
            h1, h2 = _label_hashes(label)
            entries += struct.pack("<iIIIQQ", sec, h1, h2, 0, off, 0)
        label_blob += label.encode("utf-8") + b"\0"
    if g.version == V2 and order:
        entries += bytes(0x800)
    text = b"".join(s.encode("utf-8") + b"\0" for s in g.strings)
    header = HEADER.pack(MAGIC, g.version, g.language, g.unknown, len(order), len(g.strings),
                         len(label_blob), len(text), len(name))
    return header + name + b"\0" + bytes(entries) + bytes(label_blob) + text


def to_json(g: Gmd) -> dict:
    return {
        "name": g.name, "version": f"0x{g.version:08x}", "language": g.language,
        "entries": [{"index": i, "label": g.labels.get(i), "text": s} for i, s in enumerate(g.strings)],
    }
