"""MT Framework Mobile shader packages (MFX, the games' `LtShaderPackage.lfx`), names only
(specs/mfx.md).

A material does not name the shader objects it uses (its blend, depth-stencil and rasterizer
states, its constant buffers, textures and samplers): it stores an *object id*,
`(jamcrc(name) & 0xfffff) << 12 | index`, where `index` is the object's slot in the game's one
shader package and the high 20 bits are the low 20 bits of the CRC-32 of the object's name with
no final inversion. Each game's package numbers its objects in its own order, so a material only
means the right objects in the game whose package it was made against; the package's own hash,
at 0x08, is the signature that game's materials carry (mrl.py).

The header (little endian):

    0x00  char[4]  magic "MFX\\0"
    0x04  u16      version, 0x34 in the three games
    0x06  u16      the game's revision (MH3U 0x63, MH4U 0x64, MHXX 0x69)
    0x08  u32      the package's hash, the signature its game's materials carry at 0x10
    0x0c  u32      object count
    0x20  u32      string table offset
    0x28  u32 ×    one offset per object, from the start of the file (0 for an empty slot)

An object entry starts with the offset of its name in the string table and holds its own slot
number at +0x0e. Only the names and slots are read here.
"""
from __future__ import annotations

import struct
import zlib

from . import romfs

MAGIC = b"MFX\0"
VERSION = 0x34
OBJECTS_AT = 0x28
STRINGS_AT = 0x20
# Where each game keeps its package in its RomFS.
PACKAGE_PATHS = {
    "mh4u": "/system/ltshader/LtShaderPackage.lfx",
    "mhxx": "/system/ltshader/LtShaderPackage.lfx",
    "mh3u": "/LtUserShader/LtUserShaderPackage.lfx",
}

INDEX_BITS = 12
INDEX_MASK = (1 << INDEX_BITS) - 1
HASH_MASK = 0xFFFFF


class MfxError(ValueError):
    pass


def name_hash(name: str) -> int:
    """The high 20 bits of an object id: the low 20 bits of `name`'s CRC-32, not inverted."""
    return (~zlib.crc32(name.encode("ascii"))) & HASH_MASK


def object_id(name: str, index: int) -> int:
    """The id a material stores for the object named `name` at slot `index`."""
    return name_hash(name) << INDEX_BITS | index


class Package:
    """A shader package's object names by slot, and its slots by name hash."""

    def __init__(self, data: bytes):
        if len(data) < OBJECTS_AT or data[:4] != MAGIC:
            raise MfxError("not an MFX shader package")
        version, self.revision, self.signature, count = struct.unpack_from("<HHII", data, 4)
        if version != VERSION:
            raise MfxError(f"MFX version {version:#x} is not {VERSION:#x}")
        if count > INDEX_MASK + 1 or OBJECTS_AT + 4 * count > len(data):
            raise MfxError(f"{count} objects don't fit the file")
        strings = struct.unpack_from("<I", data, STRINGS_AT)[0]
        self.names: dict[int, str] = {}
        for index in range(count):
            at = struct.unpack_from("<I", data, OBJECTS_AT + 4 * index)[0]
            if not at:
                continue
            if at + 0x10 > len(data):
                raise MfxError(f"object {index} at {at:#x} runs past the end")
            name_at = strings + struct.unpack_from("<I", data, at)[0]
            end = data.find(b"\0", name_at)
            if name_at >= len(data) or end < 0:
                raise MfxError(f"object {index}'s name is outside the file")
            self.names[index] = data[name_at:end].decode("ascii")
        self.by_hash: dict[int, int] = {}
        for index, name in self.names.items():
            self.by_hash.setdefault(name_hash(name), index)

    def name_of(self, word: int) -> str | None:
        """The object `word` names when it is one of this package's ids, else None: its slot must
        hold an object whose name hashes to the word's high 20 bits."""
        name = self.names.get(word & INDEX_MASK)
        if name is not None and name_hash(name) == word >> INDEX_BITS:
            return name
        return None

    def id_for(self, name: str) -> int | None:
        """This package's id for the object named `name`, or None when it has none."""
        index = self.by_hash.get(name_hash(name))
        if index is None or self.names[index] != name:
            return None
        return object_id(name, index)


def from_romfs(romfs_path: str, game: str) -> Package:
    """`game`'s own shader package, read from its RomFS image."""
    want = PACKAGE_PATHS[game]
    image = romfs.open_image(romfs_path)
    entry = next((f for f in image.files() if f.path == want), None)
    if entry is None:
        raise MfxError(f"{romfs_path} has no {want}")
    return Package(image.read(entry))
