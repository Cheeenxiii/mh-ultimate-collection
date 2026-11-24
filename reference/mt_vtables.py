#!/usr/bin/env python3
"""Recover the instance vtable of every MT Framework class in an ARM code.bin.

Each class's DTI (tools/mt_dti.py) is an object whose own vtable has `newInstance` in
slot 2. newInstance gets an allocator (a getter call), allocates, runs the constructor and
returns the object. This tool:
  1. emulates the DTI initialisers, as mt_dti does, and reads each DTI's vtable pointer;
  2. finds the allocator getter: the most common first call made by the newInstance slots;
  3. emulates each newInstance with that getter replaced by a fake allocator (every
     virtual slot hands out fresh zeroed memory), and records every vtable pointer the
     constructors store at offset 0 of the new object: the last one is the class's own,
     the earlier ones its bases' (useful when the class's constructor faults part-way);
  4. measures each vtable: consecutive words pointing into .text, up to the next
     known vtable.

usage: mt_vtables.py --exheader exheader.bin --code code.bin [--classes mt_classes.tsv] -o vt.tsv

The output lists, per class: DTI, instance vtable, slot count and how it was found. The
slots themselves are read from code.bin by `slots()`; they are addresses only, but the
file is derived from game code: keep it outside the repository.
"""
from __future__ import annotations

import argparse
import collections
import os
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fork  # noqa: E402,F401  (the fork's tools on sys.path)

import codebin2elf
import exheader as exh
import mt_dti

NEW_INSTANCE_SLOT = 2
FAKE, STUBS, HEAP = 0x0C000000, 0x0C001000, 0x10000000
HEAP_SIZE = 0x04000000
STUB_COUNT = 256


@dataclass
class ClassVt:
    name: str
    dti: int
    dti_vtable: int | None = None
    parent: int | None = None
    new_instance: int | None = None
    vtable: int | None = None
    chain: list[int] = field(default_factory=list)   # vtables stored at obj+0, in order
    size: int = 0
    how: str = ""
    slots: list[int] = field(default_factory=list)


class Mem:
    """Word reads over code.bin as mapped (text, ro, data) and any CRO modules loaded
    beside it. `code` regions hold functions; `data` regions hold vtables."""

    def __init__(self):
        self.regions: list[tuple[int, bytes]] = []
        self.code: list[tuple[int, int]] = []
        self.data: list[tuple[int, int]] = []

    def add(self, base: int, image: bytes, code: list[tuple[int, int]],
            data: list[tuple[int, int]]) -> None:
        self.regions.append((base, image))
        self.code += code
        self.data += data

    def u32(self, a: int) -> int | None:
        for base, image in self.regions:
            off = a - base
            if 0 <= off <= len(image) - 4:
                return struct.unpack_from("<I", image, off)[0]
        return None

    def is_code(self, w: int | None) -> bool:
        return w is not None and (w & 1 or not w & 3) and \
            any(lo <= (w & ~1) < hi for lo, hi in self.code)

    def in_ro(self, a: int) -> bool:
        return any(lo <= a < hi for lo, hi in self.data)


@dataclass
class Module:
    name: str
    base: int
    image: bytes


# ── step 1: DTIs and their vtables ───────────────────────────────────────────

def dti_vtables(img: mt_dti.Image, ctor: int | None = None
                ) -> dict[int, tuple[str, int | None, int | None]]:
    """DTI address -> (class name, DTI vtable, parent DTI), by emulating every class initialiser and
    reading each DTI's word 0 once its initialiser has run."""
    from unicorn import UcError

    ctor = ctor if ctor is not None else mt_dti.detect_ctor(img)
    calls = mt_dti.find_callers(img, ctor)
    starts = sorted({s for s in (mt_dti.find_function_start(img, c) for c in calls) if s})
    vts: dict[int, int] = {}

    def after(mu, new):
        for d in new:
            try:
                vts[d] = struct.unpack("<I", bytes(mu.mem_read(d, 4)))[0]
            except UcError:
                pass

    classes = mt_dti.emulate(img, ctor, starts, after=after)
    return {a: (d.name, vts.get(a), d.parent) for a, d in classes.items()}


# ── step 2 and 3: newInstance ────────────────────────────────────────────────

def first_call(mem: Mem, fn: int, limit: int = 24) -> int | None:
    for a in range(fn, fn + 4 * limit, 4):
        w = mem.u32(a)
        if w is None:
            return None
        t = mt_dti.bl_target(a, w)
        if t is not None:
            return t
        if (w & 0x0FFFFFF0) == 0x012FFF10 or (w & 0xFFFF8000) == 0xE8BD8000:   # bx / pop {..pc}
            return None
    return None


def detect_getter(mem: Mem, new_instances: list[int]) -> int | None:
    c = collections.Counter(t for t in (first_call(mem, f) for f in new_instances) if t)
    return c.most_common(1)[0][0] if c else None


def emulate_new_instances(img: mt_dti.Image, mem: Mem, todo: dict[int, int], getter: int,
                          modules: list[Module] = (), max_insns: int = 400_000) -> dict[int, list[int]]:
    """newInstance address -> vtable pointers stored at offset 0 of the first allocation.
    `img.code` must already have its veneers into `modules` resolved (load())."""
    from unicorn import (
        UC_ARCH_ARM,
        UC_HOOK_CODE,
        UC_HOOK_MEM_READ_UNMAPPED,
        UC_HOOK_MEM_WRITE,
        UC_HOOK_MEM_WRITE_UNMAPPED,
        UC_MODE_ARM,
        Uc,
        UcError,
    )
    from unicorn.arm_const import (
        UC_ARM_REG_C1_C0_2,
        UC_ARM_REG_CPSR,
        UC_ARM_REG_FPEXC,
        UC_ARM_REG_LR,
        UC_ARM_REG_PC,
        UC_ARM_REG_R0,
        UC_ARM_REG_SP,
    )
    page = 0x1000
    mu = Uc(UC_ARCH_ARM, UC_MODE_ARM)
    mem_end = (img.mem_end + page - 1) & ~(page - 1)
    mu.mem_map(img.base, mem_end - img.base)
    writable = img.base + img.text_size
    pristine = img.code[img.text_size:].ljust(mem_end - writable, b"\0")
    mu.mem_write(img.base, img.code)
    for m in modules:
        mu.mem_map(m.base, (len(m.image) + page - 1) & ~(page - 1))
        mu.mem_write(m.base, m.image)
    stack_top, ret, scratch = 0x0F000000, 0x0E000000, 0x08000000
    mu.mem_map(stack_top - 0x100000, 0x100000)
    mu.mem_map(ret, page)
    mu.mem_map(scratch, 0x02000000)
    mu.mem_map(FAKE, 0x2000)
    mu.mem_map(HEAP, HEAP_SIZE)
    mu.reg_write(UC_ARM_REG_C1_C0_2, mu.reg_read(UC_ARM_REG_C1_C0_2) | (0xF << 20))
    mu.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
    # the fake allocator: an object whose vtable's every slot is a stub
    mu.mem_write(FAKE, struct.pack("<I", FAKE + 0x800))
    mu.mem_write(FAKE + 0x800, struct.pack(f"<{STUB_COUNT}I",
                                           *(STUBS + 4 * i for i in range(STUB_COUNT))))
    state = {"next": HEAP, "obj": None, "stores": []}

    def ret_to_lr(uc, value):
        uc.reg_write(UC_ARM_REG_R0, value)
        lr = uc.reg_read(UC_ARM_REG_LR)
        cpsr = uc.reg_read(UC_ARM_REG_CPSR)
        uc.reg_write(UC_ARM_REG_CPSR, cpsr | 0x20 if lr & 1 else cpsr & ~0x20)
        uc.reg_write(UC_ARM_REG_PC, lr & ~1)

    def at_getter(uc, _a, _s, _d):
        ret_to_lr(uc, FAKE)

    def at_stub(uc, _a, _s, _d):
        p = state["next"]
        if p + 0x100000 > HEAP + HEAP_SIZE:
            uc.emu_stop()
            return
        state["next"] = p + 0x100000                # 1 MB each: the largest class fits
        if state["obj"] is None:
            state["obj"] = p
        ret_to_lr(uc, p)

    def on_write(uc, _access, addr, size, value, _d):
        if addr == state["obj"] and size == 4 and mem.in_ro(value & 0xFFFFFFFF):
            state["stores"].append(value & 0xFFFFFFFF)

    # Constructors read singletons that are still null at this point: null and stray
    # pointers land on zeroed pages (mapped on first touch), and a call into the zero
    # page returns 0 at once.
    mu.mem_map(0, img.base)

    def on_unmapped(uc, _access, addr, _size, _value, _d):
        try:
            uc.mem_map(addr & ~(page - 1), page)
        except UcError:
            return False
        return True

    def at_null(uc, _a, _s, _d):
        ret_to_lr(uc, 0)

    mu.hook_add(UC_HOOK_MEM_READ_UNMAPPED | UC_HOOK_MEM_WRITE_UNMAPPED, on_unmapped)
    mu.hook_add(UC_HOOK_CODE, at_null, begin=0, end=img.base - 1)
    mu.hook_add(UC_HOOK_CODE, at_getter, begin=getter, end=getter)
    mu.hook_add(UC_HOOK_CODE, at_stub, begin=STUBS, end=STUBS + 4 * STUB_COUNT - 1)
    mu.hook_add(UC_HOOK_MEM_WRITE, on_write, begin=HEAP, end=HEAP + HEAP_SIZE - 1)
    out: dict[int, list[int]] = {}
    for fn, dti in todo.items():
        mu.mem_write(writable, pristine)
        mu.mem_write(0, bytes(img.base))
        if state["next"] != HEAP:
            mu.mem_write(HEAP, bytes(state["next"] - HEAP))
        state.update(next=HEAP, obj=None, stores=[])
        mu.reg_write(UC_ARM_REG_R0, dti)
        mu.reg_write(UC_ARM_REG_SP, stack_top - 0x1000)
        mu.reg_write(UC_ARM_REG_LR, ret)
        mu.mem_write(FAKE, struct.pack("<I", FAKE + 0x800))
        try:
            mu.emu_start(fn, ret, count=max_insns)
        except UcError:
            pass
        out[fn] = list(state["stores"])
    return out


def static_vtable(mem: Mem, fn: int, limit: int = 40) -> int | None:
    """Fallback: the literal newInstance stores through a register just before returning
    (`ldr rX, =vtable; str rX, [r0]`)."""
    lits: dict[int, int] = {}
    last = None
    for a in range(fn, fn + 4 * limit, 4):
        w = mem.u32(a)
        if w is None:
            break
        if (w & 0x0F7F0000) == 0x051F0000 and w >> 28 == 0xE:          # ldr rd, [pc, #imm]
            imm = w & 0xFFF
            v = mem.u32(a + 8 + (imm if w & 0x00800000 else -imm))
            if v is not None:
                lits[(w >> 12) & 0xF] = v
        elif (w & 0x0FF00FFF) == 0x05800000 and w >> 28 == 0xE:        # str rt, [rn]
            v = lits.get((w >> 12) & 0xF)
            if v is not None and mem.in_ro(v):
                last = v
        if (w & 0xFFFF8000) == 0xE8BD8000:                              # pop {.., pc}
            break
    return last


# ── step 4: lengths ──────────────────────────────────────────────────────────

def measure(mem: Mem, starts: list[int], cap: int = 1024) -> dict[int, int]:
    """Slots per vtable: words that point into .text or are 0 (MT vtables have empty
    slots), up to the next known vtable; trailing zeros don't count."""
    bounds = sorted(set(starts))
    out = {}
    for k, v in enumerate(bounds):
        stop = bounds[k + 1] if k + 1 < len(bounds) else v + 4 * cap
        n = last = 0
        while v + 4 * n < stop and n < cap:
            w = mem.u32(v + 4 * n)
            if w != 0 and not mem.is_code(w):
                break
            n += 1
            if w:
                last = n
        out[v] = last
    return out


def slots(mem: Mem, vtable: int, size: int) -> list[int]:
    return [mem.u32(vtable + 4 * i) & 0xFFFFFFFF for i in range(size)]


# ── putting it together ──────────────────────────────────────────────────────

def recover(img: mt_dti.Image, mem: Mem, ctor: int | None = None,
            modules: list[Module] = ()) -> dict[str, ClassVt]:
    dtis = dti_vtables(img, ctor)
    out: dict[str, ClassVt] = {}
    for a, (name, dvt, parent) in dtis.items():
        c = out[name] = ClassVt(name, a, dvt, parent)
        if dvt is not None and mem.in_ro(dvt):
            ni = mem.u32(dvt + 4 * NEW_INSTANCE_SLOT)
            if mem.is_code(ni):
                c.new_instance = ni & ~1
    nis = {c.new_instance: c.dti for c in out.values() if c.new_instance}
    getter = detect_getter(mem, list(nis))
    stores = emulate_new_instances(img, mem, nis, getter, modules) if getter else {}
    for c in out.values():
        if not c.new_instance:
            continue
        c.chain = stores.get(c.new_instance, [])
        if c.chain:
            c.vtable, c.how = c.chain[-1], "emulated"
    from_chains(out)
    for c in out.values():
        if c.vtable is None and c.new_instance:
            v = static_vtable(mem, c.new_instance)
            if v is not None:
                c.vtable, c.how = v, "static"
    starts = [c.vtable for c in out.values() if c.vtable] + \
             [c.dti_vtable for c in out.values() if c.dti_vtable] + \
             [v for c in out.values() for v in c.chain]
    sizes = measure(mem, starts)
    for c in out.values():
        if c.vtable:
            c.size = sizes.get(c.vtable, 0)
            c.slots = slots(mem, c.vtable, c.size)
    return out


MODULE_BASE, MODULE_LIMIT = 0x02000000, 0x08000000


def from_chains(classes: dict[str, ClassVt]) -> int:
    """Vtables of classes with no instance of their own (abstract ones, mostly): the last
    vtable that every emulated descendant's constructor chain stores before its own and
    that no descendant owns, unless an ancestor owns it. Deepest classes first, so a vtable goes to
    the class nearest the instances that store it. Returns how many were found."""
    by_dti = {c.dti: c for c in classes.values()}
    children: dict[int, list[ClassVt]] = collections.defaultdict(list)
    for c in classes.values():
        if c.parent in by_dti:
            children[c.parent].append(c)

    def chains(c: ClassVt) -> list[list[int]]:
        out = [c.chain[:-1]] if c.how == "emulated" and c.chain else []
        for k in children.get(c.dti, []):
            out += chains(k)
        return out

    def ancestors(c: ClassVt):
        seen = set()
        while c.parent in by_dti and c.parent not in seen:
            seen.add(c.parent)
            c = by_dti[c.parent]
            yield c

    def descendants(c: ClassVt):
        for k in children.get(c.dti, []):
            yield k
            yield from descendants(k)

    n = 0
    for c in sorted(classes.values(), key=lambda c: -sum(1 for _ in ancestors(c))):
        if c.vtable is not None:
            continue
        cs = chains(c)
        if not cs:
            continue
        common = set(cs[0]).intersection(*cs[1:])
        cands = [v for v in cs[0] if v in common]
        if not cands:
            continue
        below = {d.vtable for d in descendants(c)}
        above = {a.vtable for a in ancestors(c)}
        for v in reversed(cands):          # nearest first, past those the subclasses own
            if v in above:
                break
            if v not in below:
                c.vtable, c.how = v, "chains"
                n += 1
                break
    return n


def load(exheader: str, code: str, module_paths: list[str] = (), crs_path: str | None = None
         ) -> tuple[mt_dti.Image, Mem, list[Module]]:
    """code.bin, and any CRO modules loaded one after another from MODULE_BASE with the
    static executable's veneers into them resolved, as the loader would."""
    import cro as crolib
    with open(exheader, "rb") as f:
        header = exh.parse(f.read())
    with open(code, "rb") as f:
        data = bytearray(codebin2elf.load_code(header, f.read()))
    mem = Mem()
    modules: list[Module] = []
    if module_paths:
        with open(crs_path, "rb") as f:
            crs = crolib.Cro(f.read())
        static_segs = crolib.static_segments(crs)
        base = MODULE_BASE
        for path in module_paths:
            with open(path, "rb") as f:
                ld = crolib.load(f.read(), base, static_segs)
            if base + len(ld.image) > MODULE_LIMIT:
                raise ValueError("modules don't fit below the emulator's scratch area")
            for tag, places in crolib.static_imports_of(crs, ld.cro.name):
                target = ld.segment_bases[tag & 0xF] + (tag >> 4)
                for at in places:
                    struct.pack_into("<I", data, at - header.text.address, target)
            modules.append(Module(ld.cro.name, base, ld.image))
            mem.add(base, ld.image, [ld.text], [(a, a + n) for a, n in ld.data_segments()])
            base = (base + len(ld.image) + 0xFFFF) & ~0xFFFF
    data = bytes(data)
    img = mt_dti.Image(data, header.text.address, header.text.size,
                       header.bss_address + header.bss_size)
    t = header.text.address
    mem.regions.insert(0, (t, data))
    mem.code.insert(0, (t, t + header.text.size))
    mem.data.insert(0, (header.ro.address, header.ro.address + header.ro.size))
    return img, mem, modules


def write_tsv(classes: dict[str, ClassVt], path: str) -> None:
    def h(v):
        return "" if v is None else f"0x{v:08x}"
    with open(path, "w", encoding="utf-8") as f:
        f.write("# MT Framework instance vtables recovered by reference/mt_vtables.py\n")
        f.write("name\tdti\tparent\tdti_vtable\tnew_instance\tvtable\tslots\thow\tchain\tslot_list\n")
        f.writelines(f"{c.name}\t{h(c.dti)}\t{h(c.parent)}\t{h(c.dti_vtable)}\t{h(c.new_instance)}\t"
                    f"{h(c.vtable)}\t{c.size}\t{c.how}\t{','.join(h(v) for v in c.chain)}\t"
                    f"{','.join(f'{v:x}' for v in c.slots)}\n"
                    for c in sorted(classes.values(), key=lambda c: c.name.lower()))


def read_tsv(path: str) -> dict[str, ClassVt]:
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith(("#", "name\t")) or not line.strip():
                continue
            name, dti, parent, dvt, ni, vt, size, how, chain, sl = line.rstrip("\n").split("\t")
            def num(s):
                return int(s, 16) if s else None
            out[name] = ClassVt(name, num(dti), num(dvt), num(parent), num(ni), num(vt),
                                [int(x, 16) for x in chain.split(",") if x], int(size), how,
                                [int(x, 16) for x in sl.split(",") if x])
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exheader", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--ctor", type=lambda s: int(s, 0), help="the DTI constructor, if known")
    ap.add_argument("--crs", help="the game's static.crs, with --module")
    ap.add_argument("--module", nargs="*", default=[], help="CRO modules to load beside code.bin")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args(argv)
    if args.module and not args.crs:
        ap.error("--module needs --crs")
    img, mem, modules = load(args.exheader, args.code, args.module, args.crs)
    classes = recover(img, mem, args.ctor, modules)
    write_tsv(classes, args.output)
    hows = collections.Counter(c.how or "none" for c in classes.values())
    print(f"classes: {len(classes)}; vtables: {', '.join(f'{k} {v}' for k, v in hows.most_common())}")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
