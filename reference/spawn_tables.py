r"""MH4U's spawn tables: the entry layout, the records resolved through them, and the addition path.

MH4U's effect spawn (`0x391b28`) turns a MEF record's type (`+0x03`), time (`+0x06`) and bone
(`+0x08`) into a base and a sub index, and the pair names an `effect\efl\...` path through the
pointer tables at `0xeede7c`, `0xeede98` and `0xef895c` (`0x390c48`, `0x390ef8`, `0xc0a2a8`).
`specs/mef.md` lays the tables out and records what is verified; this tool is its check.

    --read     the tables' shapes and counts (no RomFS needed)
    --romfs    resolve every MEF record of every MH4U monster archive through them
    --probe    run the spawn's real code (`0x391c74` to `0x391d88`) under Unicorn on one record
               and print the path it asks the effect manager for
    --add      the same probe after two .data writes that make an unused type name a ported
               effect's own path: the addition path `specs/mef.md` records

Addresses are MH4U USA v1.3.0. Nothing here is stored in the repository: paths are read from
the player's own dump and printed only.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys

import fork  # noqa: F401  (puts the fork's tools on sys.path)

import codebin2elf
import exheader

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from mhuc.formats import arc, classid, mef, romfs  # noqa: E402

# The tables, from specs/mef.md ("MH4U's spawn tables").
BASE_TABLE = 0xEEDE7C       # u16[14], the per-type base
TYPE_TABLE = 0xEEDE98       # u32[15], the per-type (time, joint-segment) arrays
TYPE4_TABLE = 0xEED988      # u32[13], the type-4 time table
PATHS = 0xEF895C            # u32[283], base -> an array of effect-list path pointers
TYPE_BASE_REMAP = {5: 0xEED9BC, 11: 0xEEDC0C, 12: 0xEEDE0C}   # the types whose base comes from time
TYPE_COUNT = 14
TYPE_POINTERS = 15
PATH_ENTRIES = 283          # the entry after it (0xef8dc8) is an array of path strings


class Image:
    """The loaded code image, addressed the way the game addresses it."""

    def __init__(self, header, code: bytes):
        self.header = header
        self.code = code
        self.text = header.text.address
        self.ro = header.ro.address
        self.data = header.data.address
        self.end = self.data + header.data.size
        self.bss = header.bss_address
        self.bss_end = self.bss + header.bss_size

    def read(self, addr: int, size: int) -> bytes:
        if not (self.text <= addr and addr + size <= self.end):
            raise ValueError(f"{addr:#x}+{size:#x} is outside the image")
        at = addr - self.text
        return self.code[at:at + size]

    def u16(self, addr: int) -> int:
        return struct.unpack("<H", self.read(addr, 2))[0]

    def u32(self, addr: int) -> int:
        return struct.unpack("<I", self.read(addr, 4))[0]

    def cstr(self, addr: int) -> str:
        out = b""
        while True:
            ch = self.read(addr + len(out), 1)
            if ch == b"\0":
                return out.decode("latin-1")
            out += ch


def load(image: Image, path: str) -> list[str]:
    out = []
    at = image.u32(path)
    if at == 0:
        return out
    index = 0
    while True:
        ptr = image.u32(at + 4 * index)
        if ptr == 0:
            return out
        out.append(image.cstr(ptr))
        index += 1


def segment(image: Image, table: int, key: int) -> int | None:
    """`0x390ef8`: the segment remap.

    Records are (u32 key, u32 value). The last record whose key <= `key` maps the input to
    `key + value - thatKey` (a u16), and the call succeeds only when that is below the *next*
    record's value. Returns the u16 it writes, or None when it fails.
    """
    index = 0
    last = None
    value = None
    while True:
        at = table + 8 * index
        k = image.u32(at)
        if k == 0xFFFFFFFF or k > key:
            break
        last, value = k, image.u32(at + 4)
        index += 1
    if last is None:
        return None
    out = (key + value - last) & 0xFFFF
    bound = image.u32(table + 8 * index + 4)
    return out if out < bound else None


def time_entry(image: Image, type_index: int, time: int) -> int | None:
    """`0x390c48`: the joint-segment table a type's (time, table) array gives for `time`."""
    table = image.u32(TYPE_TABLE + 4 * type_index)
    if table == 0:                       # 0x390c48: no time table for this type
        return None
    index = 0
    while True:
        at = table + 8 * index
        k = image.u32(at)
        if k == 0xFFFFFFFF:
            return None
        if k == time:
            return image.u32(at + 4)
        index += 1


def resolve(image: Image, type_index: int, time: int, joint: int) -> tuple[int, int] | None:
    """The (base, sub) pair the spawn computes, or None when it returns without an effect."""
    if type_index in TYPE_BASE_REMAP:
        base = segment(image, TYPE_BASE_REMAP[type_index], time)
        if base is None:
            return None
        base &= 0xFF
    else:
        base = image.u16(BASE_TABLE + 2 * type_index) & 0xFF
    if type_index == 4:
        pointer = image.u32(TYPE4_TABLE + 4 * time)
        if pointer == 0:
            return None
        base = (base + time) & 0xFFFF & 0xFF
    else:
        pointer = time_entry(image, type_index, time)
        if pointer is None:
            return None
    sub = segment(image, pointer, joint)
    return None if sub is None else (base, sub & 0xFF)


def path(image: Image, base: int, sub: int) -> str | None:
    """The effect list path a (base, sub) pair names: `0xc0a2a8`'s two table reads."""
    array = image.u32(PATHS + 4 * base)
    if array == 0:
        return None
    pointer = image.u32(array + 4 * sub)
    return image.cstr(pointer) if pointer else None


def base_paths(image: Image, base: int) -> list[str]:
    return load(image, PATHS + 4 * base)


def table_counts(image: Image) -> list[str]:
    """The shapes the spec records, read from the image."""
    lines = []
    lines.append(f"base table {BASE_TABLE:#x}: {TYPE_COUNT} u16, "
                 f"types 0 to {TYPE_COUNT - 1}: {[image.u16(BASE_TABLE + 2 * t) for t in range(TYPE_COUNT)]}")
    total = 0
    counts = []
    for t in range(TYPE_POINTERS):
        at = TYPE_TABLE + 4 * t
        pointer = image.u32(at)
        if pointer == 0:
            counts.append((t, None, 0))
            continue
        n = 0
        while image.u32(pointer + 8 * n) != 0xFFFFFFFF:
            n += 1
        counts.append((t, pointer, n))
        total += n
    lines.append(f"type table {TYPE_TABLE:#x}: {TYPE_POINTERS} u32; entries per type: "
                 f"{ {t: n for t, _, n in counts} }")
    lines.append(f"  (time, joint-segment) records over the types that have a table: {total}")
    t4 = [image.u32(TYPE4_TABLE + 4 * i) for i in range(13)]
    lines.append(f"type 4 table {TYPE4_TABLE:#x}: 13 u32, {sum(1 for p in t4 if p)} non-null")
    for t, table in sorted(TYPE_BASE_REMAP.items()):
        n = 0
        while image.u32(table + 8 * n) != 0xFFFFFFFF:
            n += 1
        lines.append(f"type {t} base remap {table:#x}: {n} (time, base) records")
    pointers = 0
    empty = 0
    subs = 0
    for b in range(PATH_ENTRIES):
        array = image.u32(PATHS + 4 * b)
        if array == 0:
            continue
        pointers += 1
        n = len(base_paths(image, b))
        subs += n
        empty += n == 0
    lines.append(f"path table {PATHS:#x}: {PATH_ENTRIES} u32, {pointers} non-null, "
                 f"{subs} path pointers, {empty} non-null entries with no path")
    return lines


def record_table(image: Image, romfs_path: str) -> tuple[int, int, int, list[str], list[tuple[str, int, int, int]]]:
    """Every MEF record of every MH4U monster archive, resolved through the tables."""
    image_files = romfs.open_image(romfs_path)
    mef_id = classid.class_id("rMhMotionEffect")
    records = 0
    resolved = 0
    out_of_range = 0
    no_path = 0
    dead: list[tuple[str, int, int, int]] = []
    distinct = set()
    for entry in image_files.files():
        if not (entry.path.startswith("/data/em") and entry.path.endswith(".arc")):
            continue
        archive = arc.read(image_files.read(entry))
        for resource in archive.entries:
            if resource.type_id != mef_id:
                continue
            for record in mef.read_mef(resource.data).records:
                records += 1
                type_index, time, bone = record.u8(3), record.u16(6), record.u16(8)
                joint = bone & 0xFF
                pair = resolve(image, type_index, time, joint)
                if pair is None:
                    dead.append((entry.path, type_index, time, joint))
                    continue
                base, sub = pair
                bound = len(base_paths(image, base))
                if sub >= bound:
                    out_of_range += 1
                found = path(image, base, sub)
                if found is None:
                    no_path += 1
                else:
                    resolved += 1
                    distinct.add(found)
    return records, resolved, out_of_range, sorted(distinct), dead


# --- the prototype: the spawn's real code under Unicorn -------------------------------------

MONSTER = 0x30001000
OWNER = 0x30002000
RECORD = 0x30003000
MANAGER = 0x30004000
VTABLE = 0x30005000
STUB = 0x30006000
SCRATCH = 0x30007000
SENTINEL = 0x30008000
PORT_ARRAY = 0x30009000
PORT_STRING = 0x30009100
PORT_TABLE = 0x30009200
PORT_SEGMENT = 0x30009300


def _probe(image: Image, record: bytes, writes: list[tuple[int, int]]) -> tuple[int, int, str | None]:
    """Run the spawn's resolution slice on `record` after `writes` (address, bytes)."""
    from unicorn import UC_ARCH_ARM, UC_MODE_ARM, Uc
    from unicorn.arm_const import (
        UC_ARM_REG_CPSR,
        UC_ARM_REG_LR,
        UC_ARM_REG_R5,
        UC_ARM_REG_R6,
        UC_ARM_REG_SP,
    )

    emu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    emu.mem_map(image.text & ~0xFFF, 0x1200000)
    emu.mem_map(0x20000000, 0x10000)
    emu.mem_map(0x30000000, 0x10000)
    emu.mem_write(image.text, image.code)

    # the record, the monster and its owner the slice reads
    emu.mem_write(RECORD, record)
    emu.mem_write(MONSTER, struct.pack("<I", 0) + struct.pack("<I", OWNER) + b"\0" * 0x18)
    emu.mem_write(MONSTER + 0x12, b"\0")
    # the effect manager `0xc0a2a8` calls through
    emu.mem_write(0x10572A4, struct.pack("<I", MANAGER))
    emu.mem_write(0x10572EC, struct.pack("<I", MANAGER))
    emu.mem_write(MANAGER, struct.pack("<I", VTABLE))
    emu.mem_write(VTABLE, b"\0" * 0x60)
    emu.mem_write(VTABLE + 0x38, struct.pack("<I", STUB))
    # ldr r3, [pc, #4]; str r2, [r3]; mov r0, #0; .word SCRATCH; bx lr
    emu.mem_write(STUB, struct.pack("<3I", 0xE59F3004, 0xE5832000, 0xE3A00000)
                  + struct.pack("<I", SCRATCH) + struct.pack("<I", 0xE12FFF1E))
    emu.mem_write(SENTINEL, struct.pack("<I", 0xEAFFFFFE))       # b .
    for addr, data in writes:
        emu.mem_write(addr, data)

    stack = 0x20000000 + 0x8000
    emu.mem_write(stack, b"\0" * 0x40)
    emu.reg_write(UC_ARM_REG_SP, stack)
    emu.reg_write(UC_ARM_REG_R5, MONSTER)
    emu.reg_write(UC_ARM_REG_R6, RECORD)
    emu.reg_write(UC_ARM_REG_LR, SENTINEL)
    emu.reg_write(UC_ARM_REG_CPSR, 0x13)                        # ARM mode, no flags
    emu.emu_start(0x391C74, 0x3922D8, count=20000)
    pointer = struct.unpack("<I", emu.mem_read(SCRATCH, 4))[0]
    # the pair the code computed is at sp+8 (base, u16) and sp+0xc (sub, u16)
    base = struct.unpack("<H", emu.mem_read(stack + 8, 2))[0]
    sub = struct.unpack("<H", emu.mem_read(stack + 0xC, 2))[0]
    if pointer and image.text <= pointer < image.end:
        text = image.cstr(pointer)
    elif pointer:
        raw = b""
        while True:
            ch = bytes(emu.mem_read(pointer + len(raw), 1))
            if ch == b"\0":
                break
            raw += ch
        text = raw.decode("latin-1")
    else:
        text = None
    return base, sub, text


def _record(type_index: int, time: int, joint: int) -> bytes:
    record = bytearray(0x48)
    record[3] = type_index
    struct.pack_into("<H", record, 6, time)
    struct.pack_into("<H", record, 8, joint)
    return bytes(record)


def probe(image: Image, type_index: int, time: int, joint: int, add: bool) -> list[str]:
    writes: list[tuple[int, bytes]] = []
    if add:
        # The addition path specs/mef.md records: the port owns an unused type's whole chain.
        # Type 2's base is 2 (0xeede7c, unchanged), so two .data writes cover it: its time
        # table (0xeede98 + 2*4) and its base's path array (0xef895c + 2*4).
        string = b"effect\\efl\\em\\em125\\em125_000\0"
        writes = [
            (PORT_STRING, string),
            # segment table: joint 0 -> sub 0, the terminator's value is the bound the game checks
            (PORT_SEGMENT, struct.pack("<3I", 0, 0, 0xFFFFFFFF) + struct.pack("<I", 1)),
            # time table: (time 0 -> segment table), 0xffffffff-terminated
            (PORT_TABLE, struct.pack("<2I", 0, PORT_SEGMENT) + struct.pack("<I", 0xFFFFFFFF)),
            # path array: [0] the port's effect list, [1] 0
            (PORT_ARRAY, struct.pack("<2I", PORT_STRING, 0)),
            (TYPE_TABLE + 2 * 4, struct.pack("<I", PORT_TABLE)),
            (PATHS + 2 * 4, struct.pack("<I", PORT_ARRAY)),
        ]
    base, sub, text = _probe(image, _record(type_index, time, joint), writes)
    lines = [f"record type {type_index}, time {time}, bone {joint}: base {base}, sub {sub}"]
    lines.append(f"  the effect manager is asked for: {text!r}")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--exheader", required=True, help="MH4U v1.3.0's exheader.bin")
    parser.add_argument("--code", required=True, help="MH4U v1.3.0's code.bin")
    parser.add_argument("--romfs", help="MH4U's romfs.bin, for --romfs")
    parser.add_argument("--records", action="store_true", help="resolve every MEF record (needs --romfs)")
    parser.add_argument("--probe", nargs=3, type=lambda s: int(s, 0), metavar=("TYPE", "TIME", "JOINT"),
                        help="run the spawn's real code on one record")
    parser.add_argument("--add", action="store_true",
                        help="with --probe: patch the tables first, showing the addition path")
    parser.add_argument("--cross-check", action="store_true",
                        help="run the spawn's real code on a sample of (type, time, joint) and "
                             "compare it with the model above")
    args = parser.parse_args(argv)

    header = exheader.parse(open(args.exheader, "rb").read())
    code = codebin2elf.load_code(header, open(args.code, "rb").read())
    image = Image(header, code)
    print(f"text {image.text:#x}, ro {image.ro:#x}, data {image.data:#x}, bss {image.bss:#x}")
    for line in table_counts(image):
        print(line)
    if args.records:
        if not args.romfs:
            parser.error("--records needs --romfs")
        records, resolved, out_of_range, distinct, dead = record_table(image, args.romfs)
        print(f"MEF records: {records}; resolved to a path: {resolved}; "
              f"sub past its base's array: {out_of_range}; distinct paths: {len(distinct)}")
        print(f"records the tables give no effect: {len(dead)} at {dead}")
    if args.probe:
        for line in probe(image, *args.probe, add=args.add):
            print(line)
    if args.cross_check:
        agree = 0
        differ = []
        samples = 0
        for type_index in range(TYPE_POINTERS):
            times = [t for t in (0, 1, 3, 6, 7, 8, 13, 20, 31, 82, 103, 122)
                     if type_index != 4 or t < 13]
            for time in times:
                for joint in (0, 1, 6, 255):
                    samples += 1
                    pair = resolve(image, type_index, time, joint)
                    want = None if pair is None else path(image, *pair)
                    try:
                        base, sub, got = _probe(image, _record(type_index, time, joint), [])
                    except Exception as error:                       # an unmapped read the spec notes
                        differ.append((type_index, time, joint, "fault", str(error)))
                        continue
                    have = None if got is None else path(image, base, sub)
                    if have == want:
                        agree += 1
                    else:
                        differ.append((type_index, time, joint, want, have))
        print(f"cross-check: {agree} of {samples} samples agree with the model; differences: {differ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
