"""rEnemyCmd (EMC): a monster's AI bytecode, and MH3U's script as MH4U's (specs/emc.md).

MH3U and MH4U share the file shape (magic, group table, script table) but not the script
language: the version word differs, the class has 13 group rows against 23, and 15 opcodes
that both games have take a different number of arguments. Reading and writing are therefore
per version, and the conversion needs both games' own instruction-length tables, read from
their code images: the repository never holds the tables' bytes.

The tables' addresses (USA builds): MH3U `0x00b11325`, 113 opcodes; MH4U `0x00ffe9f4`, 146
(specs/emc.md, check A3). A table value below `0x80` is the opcode's argument count; `0x80` and
up opens a block whose next byte is a sub-code: `0x00` opens the block and the table value's
low nibble is its argument count, `0x01` is a case whose value is one to four bytes (the table
value's high nibble), `0x02` is the else, `0xff` ends the block.

What the converter changes is only the instruction stream: the 14 opcodes below gain one
argument, which MH4U's evaluator reads, and `0x67` loses one (check A5). No action pair
(`00 cat num`) and no script call (`14 nn`) changes, no motion number exists in an EMC, and
groups 0 to 12 keep their order because a state selects its group by number. Groups 13 to 22
are empty in a converted file: MH3U has none and MH4U's loader reads 23 rows.
"""
from __future__ import annotations

import struct

MAGIC = b"EMC\0"
VERSION_MH3U = 0x20110601
VERSION_MH4U = 0x20120804
GROUPS_MH3U = 13
GROUPS_MH4U = 23
# (address in the game's decompressed code image, opcode count): specs/emc.md, check A3.
TABLES = {"mh3u": (0x00B11325, 113), "mh4u": (0x00FFE9F4, 146)}
CODE_BASE = 0x00100000       # a 3DS code.bin's first byte, so an address is also its offset minus this
GROUP_ROW = 16
SCRIPT_ROW = 16
SCRIPT_ALIGN = 16
END = 0xFF

# The opcodes MH3U and MH4U both have whose open form gains one argument in MH4U, and where the
# byte goes (specs/emc.md, check A5). MH4U's evaluator reads it; MH3U's instruction has none.
# `("linear", 1)` inserts it at instruction offset 1, before the first argument (`0x01`, `0x1b`);
# `("block", 1)` inserts it at offset 1 too, after the block's sub-code (`0x00`), and only on the
# open form: a case's value width and the else/end forms are the same in both games.
GAINED = {
    0x01: "linear", 0x1B: "linear",
    0x0B: "block", 0x11: "block", 0x16: "block", 0x1D: "block", 0x2E: "block",
    0x33: "block", 0x4B: "block", 0x57: "block", 0x58: "block", 0x6C: "block",
    0x6D: "block", 0x70: "block",
}
# The one MH3U opcode whose open form loses its argument in MH4U: MH4U's evaluator uses the
# constant 0 where MH3U read this byte, so only the byte 0 has a translation (check A5).
DROPPED = 0x67
# The values the converter writes for the added arguments. 0 is the first entry of the table MH4U
# indexes (a target or per-monster state entry) and what MH3U's evaluator reads without an index,
# for every opcode but 0x70: MH3U's 0x70 compares against a threshold from a global object, not
# against entry 0, so its added byte's value is unverified and the converter refuses the opcode.
FILLER = 0
UNVERIFIED = frozenset({0x70})

# The opcodes MH4U's evaluator was read for (specs/emc.md, check A5): the address of the handler
# in MH4U USA v1.3.0's recompiled code. Recorded here so a reader can redo the check.
HANDLERS = {
    0x01: 0x0092CE60, 0x0B: 0x0092B4D4, 0x11: 0x00950188, 0x16: 0x009505B0,
    0x1B: 0x00950808, 0x1D: 0x00950920, 0x2E: 0x00951274, 0x33: 0x0095162C,
    0x4B: 0x009412F4, 0x57: 0x0095265C, 0x58: 0x0095267C, 0x67: 0x00952AC8,
    0x6C: 0x00952D40, 0x6D: 0x00952E90, 0x70: 0x00952F58,
}


class EmcError(ValueError):
    pass


def lengths(code: bytes, game: str) -> bytes:
    """A game's instruction-length table from its decompressed code image (`game` is mh3u or mh4u)."""
    if game not in TABLES:
        raise EmcError(f"no instruction-length table for {game!r}; the games are {', '.join(TABLES)}")
    address, count = TABLES[game]
    at = address - CODE_BASE
    table = code[at:at + count]
    if len(table) != count:
        raise EmcError(f"the {game} code image is too short for the length table at {address:#x}: "
                       f"is it still compressed?")
    if not table or table[0] == 0:
        raise EmcError(f"no instruction-length table at {game}'s {address:#x}: the code image's layout differs")
    return table


def cut(script: bytes, lens: bytes) -> list[bytes]:
    """A script's instructions, by a game's length table; refuses a script that doesn't cut cleanly.

    A script ends with `0xff`, which no table has: an opcode at or past the table ends it, and it
    must be the last byte. Anything else past the table, an instruction running past the script, or
    a script that ends without `0xff`, is refused.
    """
    out: list[bytes] = []
    i = 0
    while i < len(script):
        op = script[i]
        if op >= len(lens):
            if op == END and i == len(script) - 1:
                return out
            raise EmcError(f"instruction at {i} has opcode {op:#04x}, past the {len(lens)}-opcode table")
        value = lens[op]
        if value < 0x80:
            size = 1 + value
        else:
            if i + 1 >= len(script):
                raise EmcError(f"block opcode {op:#04x} at {i} has no sub-code")
            sub = script[i + 1]
            if sub == 0x00:
                size = 2 + (value & 0x0F)
            elif sub == 0x01:
                size = 3 + ((value >> 4) - 8) if value >= 0x90 else 3
            else:
                size = 2
        if i + size > len(script):
            raise EmcError(f"instruction {op:#04x} at {i} needs {size} bytes, the script has {len(script) - i}")
        out.append(script[i:i + size])
        i += size
    raise EmcError(f"the script has no {END:#04x} end marker")


def parse(data: bytes) -> tuple[int, list[list[bytes]]]:
    """(version, groups of scripts): the header, the group tables and every script's bytes."""
    if len(data) < 0x10 + GROUP_ROW or data[:4] != MAGIC:
        raise EmcError("not an EMC (magic) or too short for a group table")
    version, groups, zero = struct.unpack_from("<III", data, 4)
    if zero:
        raise EmcError(f"the header's word at 0x0c is {zero:#x}, not zero")
    if 0x10 + GROUP_ROW * groups > len(data):
        raise EmcError(f"{groups} group rows run past the file")
    out: list[list[bytes]] = []
    for g in range(groups):
        count, table, r8, rc = struct.unpack_from("<IIII", data, 0x10 + GROUP_ROW * g)
        if r8 or rc:
            raise EmcError(f"group {g}'s row has nonzero reserved words")
        if table + SCRIPT_ROW * count > len(data):
            raise EmcError(f"group {g}'s script table runs past the file")
        scripts = []
        for i in range(count):
            length, offset, s8, sc = struct.unpack_from("<IIII", data, table + SCRIPT_ROW * i)
            if s8 or sc:
                raise EmcError(f"group {g} script {i}'s row has nonzero reserved words")
            if offset + length > len(data):
                raise EmcError(f"group {g} script {i} runs past the file")
            scripts.append(data[offset:offset + length])
        out.append(scripts)
    return version, out


def write(version: int, groups: list[list[bytes]]) -> bytes:
    """An EMC in the games' own layout: header, group rows, each group's script table and its scripts.

    `groups` may be shorter than the rows written: the rows it has no group for are empty. Each
    script is padded to 16 with zeroes; its table row is `length, offset, 0, 0`.
    """
    rows = max(GROUPS_MH3U, len(groups))
    out = bytearray(struct.pack("<4sIII", MAGIC, version, rows, 0)) + bytes(GROUP_ROW * rows)
    tables = []
    for g in range(rows):
        scripts = groups[g] if g < len(groups) else []
        if scripts:
            tables.append(len(out))
            out += bytes(SCRIPT_ROW * len(scripts))
        else:
            tables.append(0)
    for g in range(rows):
        if not tables[g]:
            continue
        struct.pack_into("<IIII", out, 0x10 + GROUP_ROW * g, len(groups[g]), tables[g], 0, 0)
        for i, script in enumerate(groups[g]):
            struct.pack_into("<IIII", out, tables[g] + SCRIPT_ROW * i, len(script), len(out), 0, 0)
            out += script + bytes(-len(script) % SCRIPT_ALIGN)
    return bytes(out)


def convert(data: bytes, src_lens: bytes, dst_lens: bytes) -> bytes:
    """An MH3U `rEnemyCmd` as MH4U's (specs/emc.md, "What a converter must do", check A5).

    Every script is cut with MH3U's table, its instructions translated, and written again; the
    output is cut with MH4U's table before it is returned, so a script the game could not read is
    refused. Rows 0 to 12 keep their group and script order, rows 13 to 22 are empty.
    """
    version, groups = parse(data)
    if version != VERSION_MH3U:
        raise EmcError(f"the source's version is {version:#010x}, not MH3U's {VERSION_MH3U:#010x}")
    if len(groups) != GROUPS_MH3U:
        raise EmcError(f"the source has {len(groups)} group rows, not MH3U's {GROUPS_MH3U}")
    if len(src_lens) < 113 or len(dst_lens) < 146:
        raise EmcError("the length tables are shorter than MH3U's 113 or MH4U's 146 opcodes")
    converted: list[list[bytes]] = []
    for g, scripts in enumerate(groups):
        out_group = []
        for i, script in enumerate(scripts):
            instructions = cut(script, src_lens)
            out_group.append(_script(instructions, g, i))
        converted.append(out_group)
    result = write(VERSION_MH4U, converted + [[] for _ in range(GROUPS_MH4U - GROUPS_MH3U)])
    version, out_groups = parse(result)
    if version != VERSION_MH4U or len(out_groups) != GROUPS_MH4U:
        raise EmcError("the converted file does not read back as MH4U's")
    for g, scripts in enumerate(out_groups):
        for i, script in enumerate(scripts):
            try:
                cut(script, dst_lens)
            except EmcError as e:
                raise EmcError(f"converted group {g} script {i} doesn't cut with MH4U's table: {e}") from None
    return result


def _script(instructions: list[bytes], group: int, index: int) -> bytes:
    """One script's instructions translated, with its end marker."""
    out = bytearray()
    for ins in instructions:
        out += _instruction(ins, group, index)
    out.append(END)
    return bytes(out)


def _instruction(ins: bytes, group: int, index: int) -> bytes:
    """One instruction as MH4U writes it (check A5)."""
    op = ins[0]
    if op in UNVERIFIED:
        raise EmcError(
            f"group {group} script {index} uses opcode {op:#04x}, whose added argument MH4U's evaluator "
            f"reads as a target index while MH3U's compares against a global threshold: the value to write "
            f"is unverified, so the file is not converted")
    if op == DROPPED:
        if ins[1] != 0x00:
            return ins
        if len(ins) != 3:
            raise EmcError(f"group {group} script {index}: opcode {op:#04x} opens with {len(ins) - 2} "
                           "arguments, expected 1")
        if ins[2] != 0:
            raise EmcError(
                f"group {group} script {index}: opcode {op:#04x} opens with {ins[2]:#04x}, but MH4U has "
                "no argument there and its evaluator uses 0: only 0 converts")
        return bytes([op, 0x00])
    if op not in GAINED:
        return ins
    where = GAINED[op]
    if where == "linear":
        return bytes([op, FILLER]) + ins[1:]
    if ins[1] != 0x00:                  # a case, the else or the block's end: same shape in both
        return ins
    return bytes([op, 0x00, FILLER]) + ins[2:]
