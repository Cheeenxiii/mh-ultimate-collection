"""Motion effects: the resources that time a monster's effects to its animations.

MH4U ships them as `rMhMotionEffect` (magic `MEF\\0`, extension `mef`), MH3U as
`rEffectSequence` (`ESQ\\0`, `esq`) and MHXX as `rProofEffectMotSequenceList` (`PSL\\0`, `psl`);
`specs/mef.md` lays the three out. The MEF record's fields are placed from MH4U's own spawn
(`0x391b28`) and getter (`0x391904`), but the record carries no effect id: the spawn derives the
effect from the record's type, time and bone through the tables `specs/mef.md` lays out, so a
converter needs a source-to-(type, time, bone) map and the port's own tables installed. An ESQ
event's fields and a PSL descriptor's words are placed too (FX5 to FX9). What is not placed is the
PSL lists' contents, so `to_mh4u` still refuses to write an MH4U MEF from either source game.
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
ESQ_ENTRY = 0x3C
ESQ_TAIL = 0x258
ESQ_EVENT_SECTIONS = (0, 1, 2, 4)           # the sections of 0x3C-byte effect events
# The seven sections' entry sizes, by section index; section 6 (after the last offset) is a fixed
# 0x258-byte tail and has no stride. All seven offsets are relocated by the loader at 0x3b30cc.
ESQ_SECTION_STRIDE = {0: 0x3C, 1: 0x3C, 2: 0x3C, 3: 0x0C, 4: 0x3C, 5: 0x10}
PSL_MAGIC = b"PSL\0"
PSL_VERSION = 2
PSL_HEADER = 0x08
PSL_DESCRIPTOR = 0x10          # every descriptor sits 16 bytes after the last
PSL_DESCRIPTOR_SIZE = 0x0C     # its own three words; the fourth 16-byte slot is the list's first word


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
class EsqEvent:
    """One 0x3C-byte ESQ effect event (specs/mef.md, "MH3U ESQ entry").

    The motion index and frame are placed and checked (FX5): MH3U numbers a motion as
    `file * 100 + slot`, the same number its motion lists and action inventory use, and the frame
    is inside that animation for all but seven events (FX5 records them). The other fields are
    placed from the player (`0x332e8c`) and its spawn (`0x333a00`) in specs/mef.md; `raw` keeps
    them for a converter and for the fields FX8 leaves unverified.
    """
    section: int          # which of the four 0x3C-byte sections the event is in
    motion: int
    frame: float
    raw: bytes


@dataclass(frozen=True)
class Esq:
    version: int
    offsets: tuple[int, ...]   # the seven section offsets the header holds at +0x08, in header order
    body: bytes                # everything after the 0x24-byte header

    def to_bytes(self) -> bytes:
        """The file again: the header from its fields and the body unchanged."""
        return (ESQ_MAGIC + struct.pack("<I", self.version)
                + struct.pack("<7I", *self.offsets) + self.body)

    def events(self) -> tuple[EsqEvent, ...]:
        """Every 0x3C-byte event in the four event sections (0, 1, 2 and 4), in file order.

        An all-zero entry is padding the writer leaves at the end of a section; it is returned too,
        with motion 0 and frame 0.0, so a caller can count it.
        """
        out: list[EsqEvent] = []
        for section in ESQ_EVENT_SECTIONS:
            start, end = self.offsets[section], self.offsets[section + 1]
            for at in range(start, end, ESQ_ENTRY):
                raw = self.body[at - ESQ_HEADER:at - ESQ_HEADER + ESQ_ENTRY]
                motion, = struct.unpack_from("<I", raw, 0)
                frame, = struct.unpack_from("<f", raw, 4)
                out.append(EsqEvent(section, motion, frame, raw))
        return tuple(out)


def read_esq(data: bytes) -> Esq:
    if len(data) < ESQ_HEADER or data[:4] != ESQ_MAGIC:
        raise MefError("not an ESQ file (magic)")
    version, = struct.unpack_from("<I", data, 4)
    if version != ESQ_VERSION:
        raise MefError(f"ESQ version {version:#x} isn't the one laid out (specs/mef.md: {ESQ_VERSION:#x})")
    offsets = struct.unpack_from("<7I", data, 0x08)
    if offsets[0] != ESQ_HEADER:
        raise MefError(f"ESQ section 0 starts at {offsets[0]:#x}, not the header's end {ESQ_HEADER:#x}")
    previous = ESQ_HEADER
    for offset in offsets:
        if offset < previous or offset > len(data):
            raise MefError(f"ESQ section offset {offset:#x} isn't between {previous:#x} and {len(data):#x}")
        previous = offset
    for index, stride in ESQ_SECTION_STRIDE.items():
        size = offsets[index + 1] - offsets[index]
        if size % stride:
            raise MefError(f"ESQ section {index} is {size:#x} bytes, not a whole number of "
                           f"{stride:#x}-byte entries")
    if len(data) - offsets[6] != ESQ_TAIL:
        raise MefError(f"ESQ section 6 is {len(data) - offsets[6]:#x} bytes, not the {ESQ_TAIL:#x} "
                       "every file has")
    return Esq(version, offsets, data[ESQ_HEADER:])


@dataclass(frozen=True)
class PslDescriptor:
    """One slot's 12-byte PSL descriptor, every 16 bytes (specs/mef.md, "MHXX PSL").

    `frames` is the frame count of the animation in the motion list's slot `slot` (FX6); `flags` is
    `0x00200000` or `0x01200000`; `offset` is the file offset of the slot's effect list, in slot
    order and strictly increasing, the first at the end of the last descriptor's 12 bytes (FX9).
    """
    slot: int
    frames: int
    flags: int
    offset: int


@dataclass(frozen=True)
class Psl:
    version: int
    slots: tuple[int, ...]   # one offset per animation slot, 0 for a slot with no effects
    descriptors: tuple[PslDescriptor, ...]
    body: bytes              # everything after the slot table: its padding, the descriptors and the lists

    def to_bytes(self) -> bytes:
        """The file again: the header and slot table from its fields and the rest unchanged."""
        return (PSL_MAGIC + struct.pack("<HH", self.version, len(self.slots))
                + struct.pack(f"<{len(self.slots)}I", *self.slots) + self.body)

    def lists(self) -> tuple[tuple[int, int, int], ...]:
        """Each slot's effect list as (slot, start, end), in slot order; the last ends at the file's end.

        The list contents are not laid out (specs/mef.md#mhxx-psl); only their boundaries are.
        """
        size = PSL_HEADER + 4 * len(self.slots) + len(self.body)
        out = []
        for i, descriptor in enumerate(self.descriptors):
            end = self.descriptors[i + 1].offset if i + 1 < len(self.descriptors) else size
            out.append((descriptor.slot, descriptor.offset, end))
        return tuple(out)


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
    descriptors: list[PslDescriptor] = []
    for slot, offset in enumerate(slots):
        if offset == 0:
            continue
        expected = first + seen * PSL_DESCRIPTOR
        if offset != expected:
            raise MefError(f"slot descriptor {offset:#x} isn't at {expected:#x}")
        if offset + PSL_DESCRIPTOR_SIZE > len(data):
            raise MefError(f"slot descriptor {offset:#x} runs past the file's {len(data):#x} bytes")
        frames, flags, list_offset = struct.unpack_from("<3I", data, offset)
        descriptors.append(PslDescriptor(slot, frames, flags, list_offset))
        seen += 1
    if descriptors:
        first_list = first + PSL_DESCRIPTOR * (len(descriptors) - 1) + PSL_DESCRIPTOR_SIZE
        if descriptors[0].offset != first_list:
            raise MefError(f"the first effect list starts at {descriptors[0].offset:#x}, not "
                           f"{first_list:#x} after the last descriptor")
        previous = descriptors[0].offset
        for descriptor in descriptors[1:]:
            if descriptor.offset <= previous:
                raise MefError(f"effect list {descriptor.offset:#x} doesn't follow {previous:#x}")
            previous = descriptor.offset
        if descriptors[-1].offset > len(data):
            raise MefError(f"effect list {descriptors[-1].offset:#x} is past the file's {len(data):#x} bytes")
    return Psl(version, slots, tuple(descriptors), data[PSL_HEADER + 4 * count:])


# What a source game's motion effect still lacks before it can be written as MH4U's. The first
# item is the blocker: MH4U's record has no effect id (the spawn derives it from the type and the
# time), so the effectmap needs a source-to-(type, time) row before a record can name an effect.
UNVERIFIED = ("MH4U's record has no effect id: its spawn (0x391b28) derives the effect from the "
              "record's type (+0x03), time (+0x06) and bone (+0x08) through the tables at 0xeede7c, "
              "0xeede98, 0xef895c and the type 5/11/12 remaps, so a conversion needs a "
              "source-to-(type, time, bone) map and the port's own tables (specs/mef.md#carrying-a-"
              "source-effect-into-the-tables); data/effectmap's rows don't carry those values yet; the "
              "ESQ's scalars have no placed target fields, and the PSL lists are not laid out")


def to_mh4u(data: bytes, game: str, effectmap=None) -> bytes:
    """A source game's motion effect as MH4U's MEF.

    MH4U's own file round-trips. MH3U's ESQ and MHXX's PSL are read and checked, then refused:
    MH4U's record has no effect-id field (the spawn derives the effect from the record's type and
    time), the ESQ's scalars have no placed target fields, and the PSL lists are not laid out, so a
    converter written from them would carry guesses, not effects. `effectmap` (an
    `mhuc.effectmap.EffectMap`) is where the source-to-(type, time) rows will come from; it is not
    used until then.
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
