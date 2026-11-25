"""MT Framework Mobile materials (MRL), header only (specs/mrl.md).

A monster's model names its materials by name; the material file holds one record per name
whose first word hashes it. MH4U, MH3U and MHXX share one MRL layout at version 0x20, but each
game's loader only accepts the *signature* its own files carry at 0x10: MH4U's rMaterial load
compares it with the value the engine holds and rejects the file when it differs, which leaves
the resource it belongs to unloaded. A ported material therefore keeps every byte of the
source's file and only has its signature rewritten; the texture paths it names are moved in
place by the caller.

The header (0x1c bytes, little endian):

    0x00  char[4]  magic "MRL\\0"
    0x04  u32      version, 0x20
    0x08  u32      material record count
    0x0c  u32      reference count
    0x10  u32      the source game's signature (SIGNATURES)
    0x14  u32      reference array offset, 0x1c
    0x18  u32      material record array offset, 0x14 + 0x4c * reference count

The references start where the header ends. Each is 0x4c bytes: its first word is a class id,
0x241f5deb (rTexture's) with a 64-byte path at +0x0c, or 0 for an inline block whose data sits
there instead. Each material record is 0x3c bytes and its first word is (~crc32(name)) of one of
the model's material names; the rest is the material's shader and parameter data, not decoded.
The arrays are followed by more parameter data, whose placement is not decoded either. Only the
header and the name hash are needed to make a source material load and bind in MH4U.
"""
from __future__ import annotations

import struct
import zlib
from collections import Counter

MAGIC = b"MRL\0"
VERSION = 0x20
HEADER = struct.Struct("<4sIIIIII")

SIGNATURE_AT = 0x10
# The value each game's own material files carry at 0x10 (specs/mrl.md, check MR1).
SIGNATURES = {
    "mh4u": 0xcec1aa61,
    "mh3u": 0x3810b2e2,
    "mhxx": 0xeaca0cbd,
}
# The source games whose material layout is MH4U's, so only the signature needs rewriting.
SOURCE_SIGNATURES = frozenset({SIGNATURES["mh3u"], SIGNATURES["mhxx"]})

REFERENCE = 0x4C
MATERIAL_RECORD = 0x3C
REFERENCE_ARRAY = 0x1C
TEXTURE_CLASS = 0x241F5DEB      # rTexture's class id: a reference to a texture, its path at +0x0c


class MrlError(ValueError):
    pass


def read(data: bytes) -> dict:
    """The header's fields; refuses anything that is not an MRL 0x20."""
    if len(data) < HEADER.size:
        raise MrlError(f"{len(data)} bytes is shorter than the {HEADER.size}-byte header")
    magic, version, materials, references, signature, references_at, records_at = \
        HEADER.unpack_from(data)
    if magic != MAGIC:
        raise MrlError(f"magic {magic!r} is not MRL")
    if version != VERSION:
        raise MrlError(f"MRL version {version:#x} is not {VERSION:#x}")
    if references and references_at + REFERENCE * references > len(data):
        raise MrlError(f"{references} references at {references_at:#x} run past the end")
    if materials and records_at + 4 + MATERIAL_RECORD * materials > len(data):
        raise MrlError(f"{materials} material records at {records_at:#x} run past the end")
    return {"magic": magic, "version": version, "materials": materials, "references": references,
            "signature": signature, "references_at": references_at, "records_at": records_at}


def material_key(name: bytes | str) -> int:
    """The key a material record is filed under: the CRC-32 of its name with no final inversion,
    which is `crc32_string(~0, name)` in the engine (specs/mrl.md, MR2)."""
    if isinstance(name, str):
        name = name.encode("ascii")
    return (~zlib.crc32(name)) & 0xFFFFFFFF


def material_hashes(data: bytes) -> list[int]:
    """The name hashes of the material records, in the file's order."""
    h = read(data)
    return [struct.unpack_from("<I", data, h["records_at"] + 4 + MATERIAL_RECORD * i)[0]
            for i in range(h["materials"])]


def find_material(data: bytes, name: bytes | str) -> int | None:
    """The index of the record whose key is `name`'s, or None when the file has no such record."""
    key = material_key(name)
    hashes = material_hashes(data)
    return hashes.index(key) if key in hashes else None


def unbound(data: bytes, names: list[bytes]) -> list[bytes]:
    """The names `data` has no material record for."""
    hashes = set(material_hashes(data))
    return [name for name in names if material_key(name) not in hashes]


def for_mh4u(data: bytes) -> bytes:
    """A source game's material file with MH4U's signature at 0x10; every other byte kept.

    MH4U's rMaterial load (`0x00be7000`) rejects a file whose signature is not the one the
    engine holds, so a port must write MH4U's for the loader to accept it. An unknown signature
    is refused rather than rewritten: the layouts could differ and the loader would then read
    the body the wrong way.
    """
    h = read(data)
    if h["signature"] == SIGNATURES["mh4u"]:
        return data
    if h["signature"] not in SOURCE_SIGNATURES:
        raise MrlError(f"MRL signature {h['signature']:#x} is not MH3U's or MHXX's; this "
                       "converter only rewrites the signature of a layout it knows")
    out = bytearray(data)
    struct.pack_into("<I", out, SIGNATURE_AT, SIGNATURES["mh4u"])
    return bytes(out)


def check(data: bytes) -> Counter:
    """Check MR1: the header's offsets, the reference array and the material records' hashes."""
    c = Counter()
    try:
        h = read(data)
    except (MrlError, struct.error):
        c["MR1 not readable"] += 1
        return c
    c["MR1 readable"] += 1
    c[f"MR1 signature {h['signature']:#010x}"] += 1
    c["MR1 empty (no records)" if not h["materials"] and not h["references"]
      else "MR1 holds records"] += 1
    c["MR1 references at 0x1c" if h["references_at"] == REFERENCE_ARRAY
      else "MR1 references NOT at 0x1c"] += 1
    expected = h["references_at"] + REFERENCE * h["references"]
    c["MR1 records follow the references" if h["records_at"] == expected
      else "MR1 records do NOT follow the references"] += 1
    inline = 0
    for i in range(h["references"]):
        at = h["references_at"] + REFERENCE * i
        tag = struct.unpack_from("<I", data, at)[0]
        path = data[at + 0x0C:at + 0x0C + 64].split(b"\0")[0]
        if tag == TEXTURE_CLASS:
            c["MR1 texture reference with a path" if path
              else "MR1 texture reference without a path"] += 1
        elif tag == 0:
            inline += 1
        else:
            c[f"MR1 reference to class {tag:#010x}"] += 1
    c["MR1 inline references"] += inline
    hashes = material_hashes(data)
    c["MR1 material records with unique name hashes" if len(set(hashes)) == len(hashes)
      else "MR1 material records with a repeated name hash"] += 1
    return c
