"""MH4U's message tables (`.lmd`, rLayoutMessage) (specs/lmd.md).

MH4U keeps its text not in GMDs but in `rLayoutMessage` resources: a header of counts and
offsets, a table of 8-byte label entries, a table of 16-byte formatting entries (two per
message), a table of 12-byte string records and the NUL-terminated UTF-16LE strings. The
file stores no path: the code names each table by the path it is loaded from, e.g.
`eng\\msg\\emName_eng` in `core_common.arc`, whose message N is the name of monster N.

The game's loader rebases the header's four offsets into pointers and the string record's
first word into a string pointer (the runtime layout the message getters read); this reader
keeps the file's offsets and resolves them here. Source: our reading of MH4U USA v1.3.0's
code, the message loader `0x005aa2f0` and the getters `0x00cdfa18`, `0x00cdfa30` and
`0x00cdfb30` (reference/README.md#mh4u-monster-tables), checked on every `.lmd` of the five
languages (specs/lmd.md, check LM1).
"""
from __future__ import annotations

import struct
from collections import Counter
from dataclasses import dataclass

MAGIC = b"lmd\0"
VERSION = 0x0001010B
HEADER = 0x24
LABEL_SIZE = 8
FORMAT_SIZE = 16
RECORD_SIZE = 12


class LmdError(ValueError):
    pass


@dataclass(frozen=True)
class Message:
    """Message `index`: its text and the record's two lengths (equal in every file read)."""
    index: int
    text: str
    chars: int          # the record's +4 word: UTF-16 code units, NUL not counted
    width: int          # the record's +8 word: equal to `chars` in every file read


@dataclass(frozen=True)
class Lmd:
    version: int
    label_count: int       # header +0x08: 8-byte label entries (message ids)
    format_count: int      # header +0x0c: 16-byte formatting entries, two per message
    record_count: int      # header +0x10: 12-byte string records
    messages: tuple[Message, ...]
    data: bytes

    def message(self, index: int) -> Message | None:
        """Message `index`, or None when the table has no such id (id N names monster N)."""
        return self.messages[index] if 0 <= index < len(self.messages) else None


def _text(data: bytes, offset: int, chars: int, end: int) -> str:
    if offset + chars * 2 + 2 > end:
        raise LmdError(f"message at 0x{offset:x} runs past the string data")
    raw = data[offset:offset + chars * 2]
    if data[offset + chars * 2:offset + chars * 2 + 2] != b"\0\0":
        raise LmdError(f"message at 0x{offset:x} is not NUL-terminated")
    try:
        return raw.decode("utf-16-le")
    except UnicodeDecodeError as e:
        raise LmdError(f"message at 0x{offset:x} is not UTF-16LE") from e


def read(data: bytes) -> Lmd:
    if len(data) < HEADER:
        raise LmdError("shorter than the 0x24-byte header")
    if data[:4] != MAGIC:
        raise LmdError(f"not a message table: magic {data[:4]!r}")
    (version,) = struct.unpack_from("<I", data, 4)
    if version != VERSION:
        raise LmdError(f"version 0x{version:08x}, not 0x{VERSION:08x}")
    label_count, format_count, record_count, label_off, format_off, record_off, end = \
        struct.unpack_from("<7I", data, 8)
    if not HEADER <= label_off <= format_off <= record_off <= end <= len(data):
        raise LmdError("the header's offsets are not in file order")
    if label_off != HEADER:
        raise LmdError(f"the label table starts at 0x{label_off:x}, not 0x{HEADER:x}")
    if format_off != label_off + LABEL_SIZE * label_count:
        raise LmdError("the label table does not end at the formatting table")
    if record_off != format_off + FORMAT_SIZE * format_count:
        raise LmdError("the formatting table does not end at the string records")
    strings = record_off + RECORD_SIZE * record_count
    if strings > end:
        raise LmdError("the string records run past the string data")

    messages = []
    for index in range(record_count):
        offset, chars, width = struct.unpack_from("<3I", data, record_off + RECORD_SIZE * index)
        messages.append(Message(index, _text(data, offset, chars, end), chars, width))
    return Lmd(version, label_count, format_count, record_count, tuple(messages), data)


def check(data: bytes) -> Counter:
    """Check LM1's per-file tallies: read every message and count what the table holds."""
    c: Counter = Counter()
    try:
        table = read(data)
    except (LmdError, struct.error, IndexError):
        c["LM1 not read"] += 1
        return c
    c["LM1 read"] += 1
    c[f"version 0x{table.version:x}"] += 1
    c[f"label entries {table.label_count}"] += 1
    c[f"records {table.record_count}"] += 1
    c["messages"] += len(table.messages)
    c["non-empty messages"] += sum(1 for m in table.messages if m.text)
    c["messages whose two lengths agree"] += sum(1 for m in table.messages if m.chars == m.width)
    c["ASCII messages"] += sum(1 for m in table.messages if m.text.isascii())
    c["multi-line messages"] += sum(1 for m in table.messages if "\n" in m.text)
    return c


def to_json(table: Lmd) -> dict:
    """The table as JSON-able data for `mhuc lmd dump`."""
    return {
        "version": f"0x{table.version:x}",
        "label_count": table.label_count,
        "format_count": table.format_count,
        "record_count": table.record_count,
        "messages": [{"index": m.index, "chars": m.chars, "width": m.width, "text": m.text}
                     for m in table.messages],
    }
