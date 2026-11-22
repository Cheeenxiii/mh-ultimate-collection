"""MT Framework ARC archives, as the 3DS games use them (specs/arc.md).

Layout (little endian):
    0x00  char[4]  magic "ARC\\0"
    0x04  u16      version: 0x13 MH4U, 0x11 MHX/MHXX, 0x10 MH3U
    0x06  u16      entry count
    0x08  u32      (versions other than 7 and 8) unknown, 0 in files tools write
    then  entry[count], 0x50 bytes each:
          char[64] path, '\\'-separated, no extension, NUL padded
          u32      class id of the file's type (classid.class_id)
          u32      compressed size
          u32      size, with flags in the top bits (mask per version)
          u32      offset of the zlib stream from the start of the archive
    then  the zlib streams, back to back in entry order; the first one starts on a boundary
          (32 bytes in MH4U and MHXX, 0x8000 in MH3U: DATA_ALIGN)
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass

from . import classid

MAGIC = b"ARC\0"
ENTRY = struct.Struct("<64sIIII")
NAME_SIZE = 64
SIZE_MASK = {0x13: 0x0FFFFFFF, 0x11: 0x1FFFFFFF, 0x10: 0x1FFFFFFF}
# flags the games' own archives carry (specs/arc.md, check C2); MH4U also has 0xA0000000 on some models
FLAGS_DEFAULT = {0x13: 0x20000000, 0x11: 0x40000000, 0x10: 0x40000000}
DATA_ALIGN = {0x13: 32, 0x11: 32, 0x10: 0x8000}


class ArcError(ValueError):
    pass


@dataclass
class Entry:
    path: str          # "em\\em001\\mod\\em001" style, as stored (no extension)
    type_id: int       # class id
    data: bytes        # decompressed
    flags: int = 0     # top bits of the size word, kept for round trips
    compressed: bytes | None = None   # the original stream, reused when data is unchanged

    @property
    def type_name(self) -> str | None:
        return classid.name_of(self.type_id)

    @property
    def file_name(self) -> str:
        """The path with '/' and a file extension for its type."""
        return self.path.replace("\\", "/") + "." + classid.extension_of(self.type_id)


@dataclass
class Archive:
    version: int
    entries: list[Entry]
    header_extra: int = 0
    data_start: int | None = None   # offset of the first stream, kept for round trips


def _header_size(version: int) -> int:
    return 8 if version in (7, 8) else 12


def read(data: bytes, verify: bool = True) -> Archive:
    """Parse an archive. `verify` checks each stream's decompressed size against its entry."""
    if len(data) < 8 or data[:4] != MAGIC:
        raise ArcError("not an ARC file (magic)")
    version, count = struct.unpack_from("<HH", data, 4)
    if version not in SIZE_MASK:
        raise ArcError(f"ARC version 0x{version:x} isn't one mhuc knows (0x13 MH4U, 0x11 MHX/MHXX, 0x10 MH3U)")
    hsize = _header_size(version)
    extra = struct.unpack_from("<I", data, 8)[0] if hsize == 12 else 0
    if hsize + count * ENTRY.size > len(data):
        raise ArcError("table of contents runs past the end of the file")
    mask = SIZE_MASK[version]
    entries = []
    first = None
    for i in range(count):
        raw_name, type_id, csize, size_word, offset = ENTRY.unpack_from(data, hsize + i * ENTRY.size)
        name = raw_name.split(b"\0", 1)[0].decode("ascii")
        if offset + csize > len(data):
            raise ArcError(f"{name}: data runs past the end of the file")
        stream = data[offset:offset + csize]
        first = offset if first is None else min(first, offset)
        try:
            body = zlib.decompress(stream)
        except zlib.error as e:
            raise ArcError(f"{name}: bad zlib stream ({e})") from None
        size = size_word & mask
        if verify and len(body) != size:
            raise ArcError(f"{name}: {len(body)} bytes decompressed, the entry says {size}")
        entries.append(Entry(name, type_id, body, size_word & ~mask & 0xFFFFFFFF, stream))
    return Archive(version, entries, extra, first)


def write(arc: Archive, level: int = 9) -> bytes:
    """Serialise an archive. Entries whose data still matches their original stream reuse it."""
    mask = SIZE_MASK.get(arc.version)
    if mask is None:
        raise ArcError(f"can't write ARC version 0x{arc.version:x}")
    hsize = _header_size(arc.version)
    out = bytearray(MAGIC + struct.pack("<HH", arc.version, len(arc.entries)))
    if hsize == 12:
        out += struct.pack("<I", arc.header_extra)
    toc_at = len(out)
    out += bytes(ENTRY.size * len(arc.entries))
    start = arc.data_start
    if start is None or start < len(out):
        align = DATA_ALIGN[arc.version]
        start = (len(out) + align - 1) // align * align
    out += bytes(start - len(out))
    for i, e in enumerate(arc.entries):
        name = e.path.replace("/", "\\").encode("ascii")
        if len(name) >= NAME_SIZE:
            raise ArcError(f"{e.path}: path longer than {NAME_SIZE - 1} characters")
        if len(e.data) > mask:
            raise ArcError(f"{e.path}: too large for this ARC version")
        stream = e.compressed
        if stream is None or zlib.decompress(stream) != e.data:
            stream = zlib.compress(e.data, level)
        offset = len(out)
        out += stream
        flags = e.flags if e.flags else FLAGS_DEFAULT[arc.version]
        ENTRY.pack_into(out, toc_at + i * ENTRY.size, name, e.type_id, len(stream), len(e.data) | flags, offset)
    return bytes(out)


def entry_from_file(file_name: str, data: bytes) -> Entry:
    """An entry from a path with an extension (as Entry.file_name gives)."""
    stem, dot, ext = file_name.rpartition(".")
    if not dot or "/" in ext:
        raise ArcError(f"{file_name}: needs an extension naming its type")
    return Entry(stem.replace("/", "\\"), classid.id_of_extension(ext), data)
