"""Small shader packages laid out by hand from specs/mfx.md, for the converter's tests.

The source package numbers its objects like MH3U's (BSSolid in slot 0x91), the MH4U one like
MH4U's (BSSolid in slot 0x9e): a material made against one means other objects in the other.
"""
from __future__ import annotations

import struct

from mhuc.formats import mfx, mrl

SOURCE_OBJECTS = {0x91: "BSSolid", 0xc4: "DSZTestWrite", 0xd0: "RSMesh", 0x17: "IAObj4wtT"}
MH4U_OBJECTS = {0x9e: "BSSolid", 0xd2: "DSZTestWrite", 0xde: "RSMesh", 0x17: "IAObj4wtT",
                0x91: "SSLinear"}


def package_bytes(signature: int, objects: dict[int, str]) -> bytes:
    count = max(objects) + 1
    table_at = 0x28
    entries_at = table_at + 4 * count
    strings = b"\0"
    name_at = {}
    for index, name in sorted(objects.items()):
        name_at[index] = len(strings)
        strings += name.encode("ascii") + b"\0"
    entry = 0x10
    strings_at = entries_at + entry * len(objects)
    head = bytearray(table_at)
    head[:4] = b"MFX\0"
    struct.pack_into("<HHII", head, 4, 0x34, 0x64, signature, count)
    struct.pack_into("<I", head, 0x20, strings_at)
    table = bytearray(4 * count)
    body = b""
    for n, (index, _) in enumerate(sorted(objects.items())):
        struct.pack_into("<I", table, 4 * index, entries_at + entry * n)
        body += struct.pack("<IIIHH", name_at[index], 0, 0, 0, index)
    return bytes(head) + bytes(table) + body + strings


SOURCE = mfx.Package(package_bytes(mrl.SIGNATURES["mh3u"], SOURCE_OBJECTS))
SOURCE_XX = mfx.Package(package_bytes(mrl.SIGNATURES["mhxx"], SOURCE_OBJECTS))
MH4U = mfx.Package(package_bytes(mrl.SIGNATURES["mh4u"], MH4U_OBJECTS))
SHADERS = (SOURCE, MH4U)
SHADERS_XX = (SOURCE_XX, MH4U)


def model_header(meshes: int = 0, vertex_format: int = 0) -> bytes:
    """A 0x40-byte MOD 0xE6 header followed by `meshes` 0x30-byte mesh records, each with
    `vertex_format` at +0x14 (specs/mod.md)."""
    d = bytearray(0x40 + 0x30 * meshes)
    struct.pack_into("<4sHHHHII", d, 0, b"MOD\0", 0xE6, 0, meshes, 0, 0, 0)
    struct.pack_into("<I", d, 0x10 + 4 * 9, 0x40)        # meshes_at
    for i in range(meshes):
        struct.pack_into("<I", d, 0x40 + 0x30 * i + 0x14, vertex_format)
    return bytes(d)
