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

    def to_bytes(self) -> bytes:
        """The file again: the header from its fields and the records unchanged."""
        return (MEF_MAGIC + struct.pack("<II", self.version, len(self.records))
                + b"".join(record.raw for record in self.records))


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
    body: bytes                 # everything after the 0x24-byte header

    def to_bytes(self) -> bytes:
        """The file again: the header from its fields and the body unchanged."""
        return (ESQ_MAGIC + struct.pack("<II", self.version, ESQ_HEADER) + struct.pack("<6I", *self.sections)
                + self.body)


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
    return Esq(version, sections, data[ESQ_HEADER:])


@dataclass(frozen=True)
class Psl:
    version: int
    slots: tuple[int, ...]   # one offset per animation slot, 0 for a slot with no effects
    body: bytes              # everything after the slot table: its padding, the descriptors and the lists

    def to_bytes(self) -> bytes:
        """The file again: the header and slot table from its fields and the rest unchanged."""
        return (PSL_MAGIC + struct.pack("<HH", self.version, len(self.slots))
                + struct.pack(f"<{len(self.slots)}I", *self.slots) + self.body)


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
    return Psl(version, slots, data[PSL_HEADER + 4 * count:])


# What a source game's motion effect still lacks before it can be written as MH4U's. The first
# item is the blocker: MH4U's loader (0x398f94) builds a u16 lookup table from each record's
# +0x04, but nothing read yet says what the table is looked up by, and a record the game never
# looks up never plays its effect.
UNVERIFIED = ("the record key at +0x04 is a unique u16 the loader indexes the records by, but what "
              "looks it up (an action, a motion or an animation event id) is unverified, and the source "
              "games' effect-id, frame, key and placement fields have no verified position")


def to_mh4u(data: bytes, game: str, effectmap=None) -> bytes:
    """A source game's motion effect as MH4U's MEF.

    MH4U's own file round-trips. MH3U's ESQ and MHXX's PSL are read and checked, then refused:
    their records' fields are not placed, so a converter written from them would carry guesses,
    not effects. `effectmap` (an `mhuc.effectmap.EffectMap`) is where the source-to-MH4U effect
    ids will come from once the fields are placed; it is not used until then.
    """
    if game == "mh4u":
        return read_mef(data).to_bytes()
    if game == "mh3u":
        read_esq(data)
    elif game == "mhxx":
        read_psl(data)
    else:
        raise MefError(f"unknown source game {game!r}")
    raise MefError(f"{game} motion effects can't become an MH4U MEF yet: {UNVERIFIED} "
                   "(specs/mef.md#what-a-converter-does)")
