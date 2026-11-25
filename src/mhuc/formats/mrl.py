"""MT Framework Mobile materials (MRL), header, name hashes and shader ids (specs/mrl.md).

A monster's model names its materials by name; the material file holds one record per name
whose first word hashes it. MH4U, MH3U and MHXX share one MRL layout at version 0x20, but a
material refers to its shader objects (states, constant buffers, textures, samplers) by their
slot in its own game's shader package (mfx.py), and carries that package's hash as its
*signature* at 0x10. MH4U's rMaterial load rejects a file whose signature is not its package's,
which leaves the resource it belongs to unloaded, and past that check it uses the slots as they
are. A ported material therefore keeps the source's file and body with its shader ids moved to
MH4U's slots for the same names and its signature rewritten; the texture paths it names are
moved in place by the caller.

The header (0x1c bytes, little endian):

    0x00  char[4]  magic "MRL\\0"
    0x04  u32      version, 0x20
    0x08  u32      material record count
    0x0c  u32      reference count
    0x10  u32      the hash of the shader package the file was made against (SIGNATURES)
    0x14  u32      reference array offset, 0x1c
    0x18  u32      material record array offset, 0x14 + 0x4c * reference count

The references start where the header ends. Each is 0x4c bytes: its first word is a class id,
0x241f5deb (rTexture's) with a 64-byte path at +0x0c, or 0 for an inline block whose data sits
there instead. Each material record is 0x3c bytes and its first word is (~crc32(name)) of one of
the model's material names; its words at +0x08, +0x0c and +0x10 are the blend, depth-stencil and
rasterizer state ids, and the command blocks after the records hold more ids. The rest is not
decoded.
"""
from __future__ import annotations

import struct
import zlib
from collections import Counter

from . import mfx

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


def _texture_paths(data: bytes, h: dict) -> list[range]:
    """The byte ranges of the texture references' path fields, which hold text, not ids."""
    out = []
    for i in range(h["references"]):
        at = h["references_at"] + REFERENCE * i
        if struct.unpack_from("<I", data, at)[0] == TEXTURE_CLASS:
            out.append(range(at + 0x0C, at + REFERENCE))
    return out


def shader_ids(data: bytes, package: mfx.Package) -> list[tuple[int, str]]:
    """Every shader-object id `data` stores for `package`, as (offset, object name).

    The ids sit in the material records (the blend, depth-stencil and rasterizer states) and in
    the command blocks after them (constant buffers, textures, samplers); the blocks are not
    decoded, so every aligned word past the header that is one of the package's ids counts,
    outside the texture paths. A word is an id only if its slot holds an object whose name
    hashes to its high 20 bits (specs/mfx.md).
    """
    h = read(data)
    skip = _texture_paths(data, h)
    out = []
    for at in range(HEADER.size, len(data) - 3, 4):
        if any(at in r for r in skip):
            continue
        name = package.name_of(struct.unpack_from("<I", data, at)[0])
        if name is not None:
            out.append((at, name))
    return out


def for_mh4u(data: bytes, source: mfx.Package, mh4u: mfx.Package) -> bytes:
    """A source game's material file made against MH4U's shader package.

    A material refers to its shader objects by slot in its own game's package (specs/mfx.md),
    and carries that package's hash as its signature at 0x10. MH4U's rMaterial load
    (`0x00be7000`) refuses a signature that is not its package's; past that check it uses the
    slots as they are, so a source material with only its signature rewritten draws with
    whatever MH4U keeps in those slots (MH3U's Rathian gets a sampler as her blend state). Each id
    is rewritten to MH4U's slot for the same object name, and the signature to MH4U's package.
    A file whose signature is not `source`'s is refused, and so is an object MH4U's package
    lacks.
    """
    h = read(data)
    if h["signature"] == mh4u.signature:
        return data
    if h["signature"] != source.signature:
        raise MrlError(f"MRL signature {h['signature']:#x} is not the source package's "
                       f"({source.signature:#x}); its shader ids can't be read")
    out = bytearray(data)
    struct.pack_into("<I", out, SIGNATURE_AT, mh4u.signature)
    for at, name in shader_ids(data, source):
        new = mh4u.id_for(name)
        if new is None:
            raise MrlError(f"shader object {name} (at {at:#x}) is not in MH4U's package")
        struct.pack_into("<I", out, at, new)
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
