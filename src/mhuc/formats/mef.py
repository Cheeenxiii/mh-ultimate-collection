"""Motion effects: the resources that time a monster's effects to its animations.

MH4U ships them as `rMhMotionEffect` (magic `MEF\\0`, extension `mef`), MH3U as
`rEffectSequence` (`ESQ\\0`, `esq`) and MHXX as `rProofEffectMotSequenceList` (`PSL\\0`, `psl`);
`specs/mef.md` lays the three out. Only their containers are decoded: the MEF record fields, the
ESQ sections and the PSL descriptors are unverified, so they are handed back as bytes with
`u8`/`u16`/`u32`/`f32` helpers instead of names a converter could mistake for meanings.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

MEF_MAGIC = b"MEF\0"
MEF_VERSION = 9
MEF_HEADER = 0x0C
MEF_RECORD = 0x48
ESQ_MAGIC = b"ESQ\0"
ESQ_VERSION = 0x20110217
ESQ_HEADER = 0x24
PSL_MAGIC = b"PSL\0"
PSL_VERSION = 2
PSL_HEADER = 0x08
PSL_DESCRIPTOR = 0x10


class MefError(ValueError):
    pass


def _align(x: int, a: int) -> int:
    return (x + a - 1) // a * a


@dataclass(frozen=True)
class MefRecord:
    """One 0x48-byte MEF record, unparsed (specs/mef.md, "MEF record")."""
    raw: bytes

    def u8(self, offset: int) -> int:
        return self.raw[offset]

    def u16(self, offset: int) -> int:
        return struct.unpack_from("<H", self.raw, offset)[0]

    def u32(self, offset: int) -> int:
        return struct.unpack_from("<I", self.raw, offset)[0]

    def f32(self, offset: int) -> float:
        return struct.unpack_from("<f", self.raw, offset)[0]


@dataclass(frozen=True)
class Mef:
    version: int
    records: tuple[MefRecord, ...]

    def __len__(self) -> int:
        return len(self.records)


def read_mef(data: bytes) -> Mef:
    if len(data) < MEF_HEADER or data[:4] != MEF_MAGIC:
        raise MefError("not a MEF file (magic)")
    version, count = struct.unpack_from("<II", data, 4)
    if version != MEF_VERSION:
        raise MefError(f"MEF version {version} isn't the one laid out (specs/mef.md: {MEF_VERSION})")
    if len(data) != MEF_HEADER + count * MEF_RECORD:
        raise MefError(f"{len(data)} bytes for a {MEF_HEADER:#x}-byte header and {count} records "
                       f"of {MEF_RECORD:#x}")
    records = tuple(MefRecord(data[MEF_HEADER + i * MEF_RECORD:MEF_HEADER + (i + 1) * MEF_RECORD])
                    for i in range(count))
    return Mef(version, records)


@dataclass(frozen=True)
class Esq:
    version: int
    sections: tuple[int, ...]   # the six offsets the header holds, in header order


def read_esq(data: bytes) -> Esq:
    if len(data) < ESQ_HEADER or data[:4] != ESQ_MAGIC:
        raise MefError("not an ESQ file (magic)")
    version, header_size = struct.unpack_from("<II", data, 4)
    if version != ESQ_VERSION:
        raise MefError(f"ESQ version {version:#x} isn't the one laid out (specs/mef.md: {ESQ_VERSION:#x})")
    if header_size != ESQ_HEADER:
        raise MefError(f"ESQ header size {header_size:#x} isn't {ESQ_HEADER:#x}")
    sections = struct.unpack_from("<6I", data, 0x0C)
    previous = ESQ_HEADER
    for offset in sections:
        if offset < previous or offset > len(data):
            raise MefError(f"ESQ section offset {offset:#x} isn't between {previous:#x} and {len(data):#x}")
        previous = offset
    return Esq(version, sections)


@dataclass(frozen=True)
class Psl:
    version: int
    slots: tuple[int, ...]   # one offset per animation slot, 0 for a slot with no effects


def read_psl(data: bytes) -> Psl:
    if len(data) < PSL_HEADER or data[:4] != PSL_MAGIC:
        raise MefError("not a PSL file (magic)")
    version, count = struct.unpack_from("<HH", data, 4)
    if version != PSL_VERSION:
        raise MefError(f"PSL version {version} isn't the one laid out (specs/mef.md: {PSL_VERSION})")
    table_end = PSL_HEADER + 4 * count
    if table_end > len(data):
        raise MefError(f"{count} slot offsets need {table_end:#x} bytes, the file has {len(data):#x}")
    slots = struct.unpack_from(f"<{count}I", data, PSL_HEADER)
    first = _align(table_end, PSL_DESCRIPTOR)
    seen = 0
    for offset in slots:
        if offset == 0:
            continue
        if offset != first + seen * PSL_DESCRIPTOR:
            raise MefError(f"slot descriptor {offset:#x} isn't at {first + seen * PSL_DESCRIPTOR:#x}")
        if offset + PSL_DESCRIPTOR > len(data):
            raise MefError(f"slot descriptor {offset:#x} runs past the file's {len(data):#x} bytes")
        seen += 1
    return Psl(version, slots)
