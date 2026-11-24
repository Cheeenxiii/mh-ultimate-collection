#!/usr/bin/env python3
"""Check mhuc's monster-data readers against the games' own loaders (specs/dttune.md, specs/emstatus.md).

For every MHXX `rEnemyDtTune` or MH3U `rEnemyStatus` file in a RomFS, run the game's loader in Unicorn and log
where it reads, then compare with the blocks `mhuc.formats.dttune` / `mhuc.formats.emstatus` find:

  mhxx  the stream loader (vtable slot 11, 0x002b7f80): every call to the stream read 0x0028140c logs
        (file offset, size); the reader's blocks must cover the same bytes, each starting where a read starts
  mh3u  the walk after the load (0x0029c744): every call to the cursor step 0x00298918 logs (offset, size); the
        reader's blocks must be the same list

usage: loader_trace.py {mhxx,mh3u} --exheader exheader.bin --code code.bin --romfs romfs.bin

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

from mhuc.formats import arc, dttune, emstatus, romfs  # noqa: E402

GAMES = {
    "mhxx": dict(type_id=0x48E8AC29, loader=0x002B7F80, read=0x0028140C, stream=0x002819D8, alloc=0x0012C420),
    "mh3u": dict(type_id=0x4DEE8265, walk=0x0029C744, step=0x00298918, flag=0x00298970),
}
OBJ, FILE, STACK, FAKE = 0x20000000, 0x30000000, 0x40000000, 0x50000000
RET = FAKE + 0x100
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
        self.uc.mem_write(FAKE, struct.pack("<I", FAKE + 0x40))                  # fake allocator object:
        self.uc.mem_write(FAKE + 0x40, struct.pack("<16I", *[FAKE + 0x200] * 16))  # every slot allocates

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
        elif addr == g["alloc"]:
            back(uc, FAKE)
        elif addr == FAKE + 0x200:
            p = (st["heap"] + 15) & ~15
            st["heap"] = p + max(uc.reg_read(UC_ARM_REG_R1), 1) + 64
            back(uc, p)
        elif addr == RET:
            uc.emu_stop()
    m.run(g["loader"], hook)
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
        if args.game == "mhxx":
            log = trace_mhxx(m, g, data)
            ours = [(o, n) for _, o, n in dttune.blocks(data)]
            c["loader reads the whole file" if sum(n for _, n in log) == len(data) else "loader stops early"] += 1
            same = merged(ours) == merged(log[1:]) and {o for o, _ in ours} <= {o for o, _ in log}
        else:
            log = trace_mh3u(m, g, data)
            ours = [(o, n) for name, o, n in emstatus.blocks(data) if not name.endswith((" head", " count"))]
            same = ours == log
        c["mhuc's blocks are the loader's" if same else "mhuc's blocks DIFFER"] += 1
    for k, v in sorted(c.items()):
        print(f"{k}: {v}")
    return 0 if c["mhuc's blocks DIFFER"] == 0 and c["files"] else 1


if __name__ == "__main__":
    sys.exit(main())
