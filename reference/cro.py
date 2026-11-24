#!/usr/bin/env python3
"""Read and load 3DS relocatable modules: CRO files and the static executable's CRS.

Some games keep part of their code outside code.bin. MHXX, for one, keeps each monster,
the player's weapons, the village, the title screen and more in `.cro` modules that its
static code loads at run time (RomFS `/modules_MasterRelease/`, plus `static.crs`, the
static executable's own export and import tables). A reference recompile of code.bin
alone has none of that code: the static side only holds veneers that the loader fills
with the modules' addresses.

Format: "CRO0" header at 0x80, then (offset, count) pairs for the tables below
(3dbrew, "CRO0"). A segment-offset tag is `offset << 4 | segment index`.

    info     <file>                      header, segments and table sizes
    imports  <module.cro> --crs <crs>    the static addresses a module imports

`load()` places a module at a chosen base, applies its own relocations and its imports
from the static executable, and returns the image, ready for the recompiler's Analyzer.
Addresses only: nothing here copies a module's bytes anywhere but memory.
"""
from __future__ import annotations

import argparse
import struct
import sys
from dataclasses import dataclass

MAGIC = b"CRO0"
HEADER = 0x80
TABLES = ("segments", "named_exports", "indexed_exports", "export_strings", "export_tree",
          "import_modules", "import_patches", "named_imports", "indexed_imports",
          "anon_imports", "import_strings", "static_anon", "relocations", "unk9")
TABLES_AT = 0xC8
SEG_TEXT, SEG_RO, SEG_DATA, SEG_BSS = 0, 1, 2, 3

R_ARM_ABS32, R_ARM_REL32, R_ARM_CALL, R_ARM_JUMP24, R_ARM_TARGET2 = 0x02, 0x03, 0x1C, 0x1D, 0x29


class CroError(ValueError):
    pass


@dataclass(frozen=True)
class Segment:
    offset: int    # in the file; 0 for .bss, which the loader allocates
    size: int
    kind: int      # SEG_TEXT, SEG_RO, SEG_DATA or SEG_BSS


@dataclass(frozen=True)
class Patch:
    target: int    # segment-offset tag of the word to patch
    type: int      # R_ARM_*
    segment: int   # relocations: index of the segment the symbol is in
    addend: int


@dataclass(frozen=True)
class ImportModule:
    name: str
    indexed: tuple[tuple[int, int], ...]   # (export index, patch list offset)
    anonymous: tuple[tuple[int, int], ...]  # (segment-offset tag in that module, patch list offset)


class Cro:
    def __init__(self, data: bytes):
        if len(data) < 0x138 or data[HEADER:HEADER + 4] != MAGIC:
            raise CroError("not a CRO0 module (no magic at 0x80)")
        self.data = data
        self.name = self._cstr(self._u32(0x84))
        self.file_size = self._u32(0x90)
        self.bss_size = self._u32(0x94)
        self.tables = {n: (self._u32(TABLES_AT + 8 * i), self._u32(TABLES_AT + 4 + 8 * i))
                       for i, n in enumerate(TABLES)}
        off, n = self.tables["segments"]
        self.segments = [Segment(*struct.unpack_from("<3I", data, off + 12 * i)) for i in range(n)]

    def _u32(self, off: int) -> int:
        return struct.unpack_from("<I", self.data, off)[0]

    def _cstr(self, off: int) -> str:
        end = self.data.find(b"\0", off)
        return self.data[off:end if end >= 0 else len(self.data)].decode("latin-1")

    def _rows(self, table: str, fmt: str) -> list[tuple]:
        off, n = self.tables[table]
        size = struct.calcsize(fmt)
        return [struct.unpack_from(fmt, self.data, off + size * i) for i in range(n)]

    def named_exports(self) -> list[tuple[str, int]]:
        return [(self._cstr(name), tag) for name, tag in self._rows("named_exports", "<II")]

    def anon_imports(self) -> list[tuple[int, int]]:
        """Imports from the static executable: (segment-offset tag there, patch list offset)."""
        return self._rows("anon_imports", "<II")

    def relocations(self) -> list[Patch]:
        return [Patch(t, ty, seg, add) for t, ty, seg, _, _, add in self._rows("relocations", "<IBBBBI")]

    def import_modules(self) -> list[ImportModule]:
        out = []
        for name, ih, ic, ah, ac in self._rows("import_modules", "<5I"):
            idx = tuple(struct.unpack_from("<II", self.data, ih + 8 * i) for i in range(ic))
            anon = tuple(struct.unpack_from("<II", self.data, ah + 8 * i) for i in range(ac))
            out.append(ImportModule(self._cstr(name), idx, anon))
        return out

    def patch_list(self, off: int) -> list[Patch]:
        """An import's patches: 12-byte entries up to the one flagged last."""
        out = []
        while True:
            if off + 12 > len(self.data):
                raise CroError(f"patch list runs past the end at 0x{off:x}")
            target, ty, last, _, _, addend = struct.unpack_from("<IBBBBI", self.data, off)
            out.append(Patch(target, ty, 0, addend))
            if last:
                return out
            off += 12


def static_segments(crs: Cro) -> list[int]:
    """Base address of each segment of the static executable: its CRS gives them absolute."""
    return [s.offset for s in crs.segments]


def apply_patch(img: bytearray, at: int, place: int, ty: int, sym: int, addend: int) -> None:
    """Write one relocation at image offset `at`; the word sits at address `place`."""
    word = struct.unpack_from("<I", img, at)[0]
    value = (sym + addend) & 0xFFFFFFFF
    if ty in (R_ARM_ABS32, R_ARM_TARGET2):
        new = value
    elif ty == R_ARM_REL32:
        new = (value - place) & 0xFFFFFFFF
    elif ty in (R_ARM_CALL, R_ARM_JUMP24):
        off = value - (place + 8)
        if ty == R_ARM_CALL and value & 1:          # BL to Thumb becomes BLX, H bit from bit 1
            new = 0xFA000000 | ((off >> 1) & 1) << 24 | (off >> 2) & 0xFFFFFF
        else:
            new = (word & 0xFF000000) | (off >> 2) & 0xFFFFFF
    else:
        raise CroError(f"relocation type 0x{ty:x} not handled")
    struct.pack_into("<I", img, at, new)


@dataclass
class Loaded:
    cro: Cro
    image: bytes                 # file bytes then .bss, at `base`
    base: int
    segment_bases: list[int]     # address of each segment
    imports: list[int]           # every static address the module imports, in table order
    patch_types: dict[int, int]  # count per relocation type, own relocations and imports

    @property
    def text(self) -> tuple[int, int]:
        s = self.cro.segments[0]
        return self.base + s.offset, self.base + s.offset + s.size

    def data_segments(self) -> list[tuple[int, int]]:
        """(address, size) of .rodata and .data, for a data-pointer scan."""
        return [(self.segment_bases[i], s.size) for i, s in enumerate(self.cro.segments)
                if s.kind in (SEG_RO, SEG_DATA) and s.size]


def load(data: bytes, base: int, static_segs: list[int]) -> Loaded:
    """The module as the loader leaves it at `base` (file offset 0), with .bss right after
    the file. Applies its relocations and its anonymous imports from the static executable."""
    cro = Cro(data)
    img = bytearray(data)
    bss_at = len(img)
    img += bytes(cro.bss_size)
    seg_off = [bss_at if s.kind == SEG_BSS else s.offset for s in cro.segments]
    seg_base = [base + o for o in seg_off]

    def file_off(tag: int) -> int:
        i = tag & 0xF
        if i >= len(seg_off):
            raise CroError(f"segment index {i} out of range")
        return seg_off[i] + (tag >> 4)

    types: dict[int, int] = {}
    for p in cro.relocations():
        at = file_off(p.target)
        apply_patch(img, at, base + at, p.type, seg_base[p.segment], p.addend)
        types[p.type] = types.get(p.type, 0) + 1
    imports = []
    for tag, head in cro.anon_imports():
        if (tag & 0xF) >= len(static_segs):
            raise CroError(f"import from static segment {tag & 0xF}, which the CRS doesn't have")
        sym = static_segs[tag & 0xF] + (tag >> 4)
        imports.append(sym)
        for p in cro.patch_list(head):
            at = file_off(p.target)
            apply_patch(img, at, base + at, p.type, sym, p.addend)
            types[p.type] = types.get(p.type, 0) + 1
    return Loaded(cro, bytes(img), base, seg_base, imports, types)


def static_imports_of(crs: Cro, module: str) -> list[tuple[int, list[int]]]:
    """What the static executable imports from `module`: (segment-offset tag in the module,
    static addresses patched with it). The veneers in code.bin that call into a module."""
    segs = static_segments(crs)
    out = []
    for m in crs.import_modules():
        if m.name != module:
            continue
        for tag, head in m.anonymous:
            out.append((tag, [segs[p.target & 0xF] + (p.target >> 4) for p in crs.patch_list(head)]))
    return out


def entry_points(loaded: Loaded, crs: Cro | None = None) -> dict[int, str]:
    """Function entries a recompile can start from: code pointers in the module's .rodata
    and .data after relocation, and the module addresses the static executable imports."""
    lo, hi = loaded.text
    out: dict[int, str] = {}
    for addr, size in loaded.data_segments():
        off = addr - loaded.base
        for k in range(0, size - 3, 4):
            w = struct.unpack_from("<I", loaded.image, off + k)[0]
            if lo <= w & ~1 < hi:
                out[w & ~1] = "thumb" if w & 1 else "arm"
    if crs is not None:
        for tag, _ in static_imports_of(crs, loaded.cro.name):
            a = loaded.segment_bases[tag & 0xF] + (tag >> 4)
            if lo <= a & ~1 < hi:
                out[a & ~1] = "thumb" if a & 1 else "arm"
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("info")
    p.add_argument("file")
    p = sub.add_parser("imports")
    p.add_argument("module")
    p.add_argument("--crs", required=True)
    args = ap.parse_args(argv)
    with open(getattr(args, "file", None) or args.module, "rb") as f:
        cro = Cro(f.read())
    if args.cmd == "info":
        print(f"name: {cro.name}  file size: 0x{cro.file_size:x}  bss: 0x{cro.bss_size:x}")
        for i, s in enumerate(cro.segments):
            print(f"segment {i}: kind {s.kind}  offset 0x{s.offset:x}  size 0x{s.size:x}")
        for n, (_off, count) in cro.tables.items():
            if count:
                print(f"{n}: {count}")
        for m in cro.import_modules():
            print(f"imports from {m.name}: {len(m.indexed)} indexed, {len(m.anonymous)} anonymous")
        return 0
    with open(args.crs, "rb") as f:
        crs = Cro(f.read())
    loaded = load(cro.data, 0x10000000, static_segments(crs))
    for a in loaded.imports:
        print(f"0x{a:08x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
