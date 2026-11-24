#!/usr/bin/env python3
"""Check mhuc's monster-data readers against the games' own loaders (specs/dttune.md, specs/dtbase.md,
specs/dtbparts.md, specs/emstatus.md).

For every MHXX `rEnemyDtTune`, `rEnemyDtBase` or `rEnemyDtBaseParts` file or MH3U `rEnemyStatus` file in a RomFS, run
the game's loader in Unicorn and log where it reads, then compare with the blocks `mhuc.formats.dttune`, `dtbase`,
`dtbparts` / `emstatus` find:

  mhxx           the stream loader (vtable slot 11): every call to the stream read 0x0028140c logs (file offset, size),
                 and the reader's blocks must be the loader's reads. The loaders: dttune 0x002b7f80, dtbase
                 0x002b6f88, dtbparts 0x0058e424.
  mh3u           the walk after the load (0x0029c744): every call to the cursor step 0x00298918 logs (offset, size);
                 the reader's blocks must be the same list

usage: loader_trace.py {mhxx,mhxx-dtbase,mhxx-dtbparts,mh3u} --exheader exheader.bin --code code.bin --romfs romfs.bin

The code must be the version the addresses belong to: MHXX v1.4 (the v4.8.0 update's code.bin; the data comes from
the game's RomFS, which the update doesn't patch for these files), MH3U USA. Prints counts only.
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
import fork  # noqa: E402,F401  (the fork's tools on sys.path)

import codebin2elf  # noqa: E402
import exheader as exh  # noqa: E402

from mhuc.formats import arc, dtbase, dtbparts, dttune, emstatus, romfs  # noqa: E402

GAMES = {
    "mhxx": dict(type_id=0x48E8AC29, loader=0x002B7F80, read=0x0028140C, stream=0x002819D8, alloc=0x0012C420,
                 ctor=0x002E4408),
    "mhxx-dtbase": dict(type_id=0x59D9C3DA, loader=0x002B6F88, read=0x0028140C, stream=0x002819D8,
                        alloc=0x0012C420, new=0x00B071B4, new_arr=0x00B07170, ctor=0x002E4408),
    "mhxx-dtbparts": dict(type_id=0x1BBC291E, loader=0x0058E424, read=0x0028140C, stream=0x002819D8,
                          new=0x00B07170, ctor=0x002E4408),
    "mh3u": dict(type_id=0x4DEE8265, walk=0x0029C744, step=0x00298918, flag=0x00298970),
}
READERS = {"mhxx": dttune, "mhxx-dtbase": dtbase, "mhxx-dtbparts": dtbparts}
OBJ, FILE, STACK, FAKE = 0x20000000, 0x30000000, 0x40000000, 0x50000000
RET = FAKE + 0x100
VTABLE = FAKE + 0x400
BX_LR = b"\x1e\xff\x2f\xe1"


class Machine:
    def __init__(self, exheader: str, code: str):
        from unicorn import UC_ARCH_ARM, UC_MODE_ARM, Uc
        with open(exheader, "rb") as f:
            header = exh.parse(f.read())
        with open(code, "rb") as f:
            image = codebin2elf.load_code(header, f.read())
        base, end = header.text.address, header.bss_address + header.bss_size
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.mem_map(base, (end - base + 0xFFF) & ~0xFFF)
        self.uc.mem_write(base, image)
        for at, size in ((OBJ, 0x100000), (FILE, 0x1000000), (STACK - 0x100000, 0x200000), (FAKE, 0x10000)):
            self.uc.mem_map(at, size)
        self.uc.mem_write(RET, BX_LR)
        self.uc.mem_write(FAKE + 0x200, BX_LR)
        self.uc.mem_write(FAKE + 0x300, BX_LR)                  # returns from the loader's own vtable call
        self.uc.mem_write(FAKE, struct.pack("<I", FAKE + 0x40))                  # fake allocator object:
        self.uc.mem_write(FAKE + 0x40, struct.pack("<16I", *[FAKE + 0x200] * 16))  # every slot allocates
        self.uc.mem_write(VTABLE, struct.pack("<16I", *[FAKE + 0x300] * 16))     # every slot is a no-op

    def run(self, start: int, hook, obj: dict[int, int] | None = None) -> str | None:
        """run `start` with r0 = a zeroed object (words of `obj` set first) and r1 = a stream object"""
        from unicorn import UC_HOOK_CODE
        from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_SP
        uc = self.uc
        uc.mem_write(OBJ, bytes(0x1000))
        for off, value in (obj or {}).items():
            uc.mem_write(OBJ + off, struct.pack("<I", value))
        h = uc.hook_add(UC_HOOK_CODE, hook)
        uc.reg_write(UC_ARM_REG_R0, OBJ)
        uc.reg_write(UC_ARM_REG_R1, FAKE + 0x800)
        uc.reg_write(UC_ARM_REG_SP, STACK)
        uc.reg_write(UC_ARM_REG_LR, RET)
        err = None
        try:
            uc.emu_start(start, RET, count=5_000_000)
        except Exception as e:  # noqa: BLE001  (a fault after the last read is reported, not fatal)
            err = f"{type(e).__name__} at {uc.reg_read(UC_ARM_REG_PC):#x}"
        uc.hook_del(h)
        return err


def trace_mhxx(m: Machine, g: dict, data: bytes) -> list[tuple[int, int]]:
    from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2
    st = {"pos": 0, "heap": FILE, "log": []}

    def back(uc, value):
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def alloc(uc, size_reg):
        p = (st["heap"] + 15) & ~15
        st["heap"] = p + max(uc.reg_read(size_reg), 1) + 64
        back(uc, p)

    def hook(uc, addr, _size, _):
        if addr == g["stream"]:
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))
        elif addr == g["read"]:
            dst, n = uc.reg_read(UC_ARM_REG_R1), uc.reg_read(UC_ARM_REG_R2)
            chunk = data[st["pos"]:st["pos"] + n]
            uc.mem_write(dst, chunk + bytes(n - len(chunk)))
            st["log"].append((st["pos"], n))
            st["pos"] += n
            back(uc, len(chunk))
        elif addr == g.get("alloc"):
            back(uc, FAKE)
        elif addr == g.get("new"):
            alloc(uc, UC_ARM_REG_R0)
        elif addr == g.get("new_arr"):
            alloc(uc, UC_ARM_REG_R0)
        elif addr == g.get("ctor"):
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))   # an array constructor: no data read
        elif addr == FAKE + 0x200:
            alloc(uc, UC_ARM_REG_R1)
        elif addr == RET:
            uc.emu_stop()
    m.run(g["loader"], hook, {0: VTABLE})       # the loaders call their object's vtable slot 15 first
    return st["log"]


def trace_mh3u(m: Machine, g: dict, data: bytes) -> list[tuple[int, int]]:
    from unicorn.arm_const import UC_ARM_REG_R1, UC_ARM_REG_SP
    m.uc.mem_write(FILE, data)
    log = []

    def hook(uc, addr, _size, _):
        if addr == g["step"]:
            cur = struct.unpack("<I", uc.mem_read(uc.reg_read(UC_ARM_REG_R1), 4))[0]
            n = struct.unpack("<I", uc.mem_read(uc.reg_read(UC_ARM_REG_SP), 4))[0]
            if n:
                log.append((cur - FILE, n))
        elif addr == RET:
            uc.emu_stop()
    m.run(g["walk"], hook, {0x60: FILE})   # the walk starts from the loaded copy's address at +0x60
    return log


def merged(spans) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for o, n in spans:
        if out and out[-1][0] + out[-1][1] == o:
            out[-1] = (out[-1][0], out[-1][1] + n)
        else:
            out.append((o, n))
    return out


def covers(ours: list[tuple[int, int]], log: list[tuple[int, int]], size: int) -> bool:
    """True when the loader read the whole file and `ours` splits the same bytes: every block starts where a read
    starts, every read starts inside a block, and both cover the file from the first block on."""
    if not log or merged(log)[0][0] != 0 or sum(n for _, n in log) != size:
        return False
    first = min((o for o, _ in ours), default=size)
    starts = {o for o, _ in ours}
    if not all(n > 0 for _, n in ours) or sum(n for _, n in ours) != size - first:
        return False
    if sum(n for o, n in log if o + n <= first) != first:
        return False
    for o, n in log:
        if o + n <= first:
            continue
        if o < first:
            return False
        if o not in starts and not any(a < o < a + b for a, b in ours):
            return False
    for a, b in ours:
        if not any(o == a for o, _ in log):
            return False
        if a + b > size:
            return False
    return True


def files(image: str, type_id: int):
    img = romfs.open_image(image)
    seen = set()
    for f in img.files():
        if not f.path.endswith(".arc"):
            continue
        try:
            a = arc.read(img.read(f))
        except arc.ArcError:
            continue
        for e in a.entries:
            if e.type_id == type_id and e.path not in seen:
                seen.add(e.path)
                yield e.data


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("game", choices=sorted(GAMES))
    ap.add_argument("--exheader", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--romfs", required=True)
    args = ap.parse_args(argv)
    g = GAMES[args.game]
    m = Machine(args.exheader, args.code)
    c: Counter = Counter()
    for data in files(args.romfs, g["type_id"]):
        c["files"] += 1
        if args.game.startswith("mhxx"):
            log = trace_mhxx(m, g, data)
            ours = [(o, n) for _, o, n in READERS[args.game].blocks(data)]
        else:
            log = trace_mh3u(m, g, data)
            ours = [(o, n) for name, o, n in emstatus.blocks(data) if not name.endswith((" head", " count"))]
        c["loader reads the whole file" if sum(n for _, n in log) == len(data) else "loader stops early"] += 1
        same = ours == log if args.game == "mh3u" else covers(ours, log, len(data))
        c["mhuc's blocks are the loader's" if same else "mhuc's blocks DIFFER"] += 1
    for k, v in sorted(c.items()):
        print(f"{k}: {v}")
    return 0 if c["mhuc's blocks DIFFER"] == 0 and c["files"] else 1


if __name__ == "__main__":
    sys.exit(main())
