"""3DS RomFS images (IVFC level 3), read in place so a dump's files never need unpacking.

`romfs.bin` as the fork's tools/extract_ncch.py --romfs writes it. Layout (little endian):
    IVFC header: magic "IVFC", 0x10000, master hash size u32, three levels of
    (logical offset u64, size u64, block size log2 u32, reserved u32); level 3 starts at
    align(0x60 + master hash size, level-3 block size).
    Level 3: header (length u32, then offset/size u32 pairs for the directory hash table,
    directory metadata, file hash table, file metadata, and the file data offset).
    Directory entry: parent, sibling, first child, first file, hash link, name length, name (UTF-16).
    File entry: parent, sibling, data offset u64, data size u64, hash link, name length, name.
    0xFFFFFFFF means none.
Source: https://www.3dbrew.org/wiki/RomFS
"""
from __future__ import annotations

import os
import struct
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

NONE = 0xFFFFFFFF
IVFC_MAGIC = b"IVFC"


class RomfsError(ValueError):
    pass


@dataclass(frozen=True)
class File:
    path: str     # "/arc/em/em001.arc"
    offset: int   # absolute offset in the image
    size: int


def _align(x: int, a: int) -> int:
    return (x + a - 1) // a * a


def level3_offset(head: bytes) -> int:
    """Where level 3 starts, from the IVFC header (or 0 for a bare level-3 image)."""
    if head[:4] != IVFC_MAGIC:
        return 0
    master = struct.unpack_from("<I", head, 0x08)[0]
    block_log2 = struct.unpack_from("<I", head, 0x0C + 2 * 0x18 + 0x10)[0]
    return _align(0x60 + master, 1 << block_log2)


class Romfs:
    def __init__(self, f: BinaryIO):
        self.f = f
        f.seek(0)
        self.base = level3_offset(f.read(0x60))
        f.seek(self.base)
        hdr = f.read(0x28)
        if len(hdr) < 0x28:
            raise RomfsError("image too short")
        vals = struct.unpack("<10I", hdr)
        if vals[0] != 0x28:
            raise RomfsError(f"level-3 header length 0x{vals[0]:x}, expected 0x28")
        _, _, _, dmeta_off, dmeta_size, _, _, fmeta_off, fmeta_size, self.data_off = vals
        self.dmeta = self._read(dmeta_off, dmeta_size)
        self.fmeta = self._read(fmeta_off, fmeta_size)

    def _read(self, off: int, size: int) -> bytes:
        self.f.seek(self.base + off)
        data = self.f.read(size)
        if len(data) != size:
            raise RomfsError("metadata runs past the end of the image")
        return data

    @staticmethod
    def _name(meta: bytes, at: int, length: int) -> str:
        return meta[at:at + length].decode("utf-16-le")

    def files(self) -> Iterator[File]:
        """Every file, depth first, in the image's own order."""
        stack = [(0, "")]
        while stack:
            d, prefix = stack.pop()
            _, _, child, file, _, nlen = struct.unpack_from("<6I", self.dmeta, d)
            name = self._name(self.dmeta, d + 0x18, nlen)
            path = f"{prefix}/{name}" if d else ""
            while file != NONE:
                _, sib, off, size, _, flen = struct.unpack_from("<IIQQII", self.fmeta, file)
                fname = self._name(self.fmeta, file + 0x20, flen)
                yield File(f"{path}/{fname}", self.base + self.data_off + off, size)
                file = sib
            kids = []
            while child != NONE:
                kids.append(child)
                child = struct.unpack_from("<I", self.dmeta, child + 4)[0]
            stack.extend((k, path) for k in reversed(kids))

    def read(self, entry: File) -> bytes:
        self.f.seek(entry.offset)
        return self.f.read(entry.size)


def open_image(path: str | os.PathLike) -> Romfs:
    return Romfs(open(path, "rb"))  # noqa: SIM115 - the Romfs owns the handle
