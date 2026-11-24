#!/usr/bin/env python3
"""Recompile CRO modules (MHXX keeps its monsters, weapons and scenes in them) at fixed
bases, as one program with the static executable's recompile.

The modules are placed one after another from `--base` and loaded as the system's loader
would leave them (reference/cro.py: their own relocations, their imports from the static
executable, and here also their imports from each other). Each is analysed from its entry
points (code pointers in its data, and what the static executable imports from it) and
turned into C like any code. Its calls into the static executable or another module become
direct branches to their addresses, which reach that code through rc_call.

The static executable is recompiled with them, from code.bin with its own veneers into the
modules filled in as the loader leaves them (a recompile of code.bin as shipped folds them
into jumps to the loader's placeholder). The output directory holds the modules' C, that
static C, one function table for all of it, and `modules.tsv` (each module's base), so
`recomp.build` makes a single library and `recomp.modtest` can test the modules' functions
against the original in Unicorn with the same layout.

The fixed bases are an assumption the C bakes in (literal pools are folded into constants):
the library runs a module only if it's loaded at its base.

Static functions only modules call are invisible to a recompile of code.bin alone; the
second form lists every module's imports from the static code, for the game's
games/<game>/extra_entries.txt (addresses only), which recompile_game.py reads.

usage: recompile_module.py --game mhxx --exheader exheader.bin --code code.bin --crs static.crs
                           [--base 0x02000000] -o build/recomp-mhxx-modules <romfs>/*.cro
       recompile_module.py --static-entries extra_entries.txt --crs static.crs <romfs>/*.cro
"""
from __future__ import annotations

import argparse
import dataclasses
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fork  # noqa: E402,F401  (the fork's tools on sys.path)

import cro as crolib  # noqa: E402
import games  # noqa: E402
import recompile as R  # noqa: E402
from recomp.analysis import Analyzer, Image  # noqa: E402

DEFAULT_BASE = 0x02000000
ENTRY_RE = re.compile(r"^\s*\{0x([0-9a-f]{8})u, ([01]), (f_[0-9a-f]{8})\},$")


class ModuleAnalyzer(Analyzer):
    """A branch into other code (`outside`: the static executable's text, other modules'
    text) is a tail call, not a bad jump: a module reaches that code through veneers,
    `ldr pc, [pc, #-4]` with the import's address in the next word, which the analyser
    folds into a branch."""
    outside: tuple[tuple[int, int], ...] = ()

    def _classify(self, f, target, tmode, entries):
        if not self.img.in_text(target) and any(lo <= target < hi for lo, hi in self.outside):
            return "tail"
        return super()._classify(f, target, tmode, entries)


def static_text(crs: crolib.Cro) -> tuple[int, int]:
    """The static executable's code, from its CRS (whose segment offsets are addresses)."""
    s = next(s for s in crs.segments if s.kind == crolib.SEG_TEXT)
    return s.offset, s.offset + s.size


def recompile_module(img: Image, entries: dict[int, str], out: str, outside: list[tuple[int, int]],
                     data_segments: list[tuple[int, int]]) -> dict:
    """recompile.recompile with ModuleAnalyzer in place of the analyser."""
    analyzer = type("BoundModuleAnalyzer", (ModuleAnalyzer,), {"outside": tuple(outside)})
    saved, R.Analyzer = R.Analyzer, analyzer
    try:
        return R.recompile(img, entries, out, data_segments=data_segments)
    finally:
        R.Analyzer = saved


def load_all(crs: crolib.Cro, paths: list[str], base: int = DEFAULT_BASE) -> list[crolib.Loaded]:
    """The modules one after another from `base` (each at a 64 KiB boundary), with their
    imports from the static executable and from each other applied."""
    static_segs = crolib.static_segments(crs)
    lds = []
    for path in paths:
        with open(path, "rb") as f:
            ld = crolib.load(f.read(), base, static_segs)
        lds.append(ld)
        base = (base + len(ld.image) + 0xFFFF) & ~0xFFFF
    out = []
    for ld in lds:
        img = bytearray(ld.image)
        for _, sym, at, p in cross_imports(ld, lds):
            crolib.apply_patch(img, at, ld.base + at, p.type, sym, p.addend)
        out.append(dataclasses.replace(ld, image=bytes(img)))
    return out


def cross_imports(ld: crolib.Loaded, lds: list[crolib.Loaded]):
    """`ld`'s imports from the other loaded modules: (module, address, image offset, patch)."""
    by_name = {x.cro.name: x for x in lds}
    for im in ld.cro.import_modules():
        src = by_name.get(im.name)
        if src is None:                  # the static executable ("|static|"), or not loaded
            continue
        exports = src.cro._rows("indexed_exports", "<I")
        pairs = [(tag, head) for tag, head in im.anonymous] + \
                [(exports[i][0], head) for i, head in im.indexed if i < len(exports)]
        for tag, head in pairs:
            sym = src.segment_bases[tag & 0xF] + (tag >> 4)
            for p in ld.cro.patch_list(head):
                yield src.cro.name, sym, ld.segment_bases[p.target & 0xF] + (p.target >> 4) - ld.base, p


def module_entries(ld: crolib.Loaded, crs: crolib.Cro, lds: list[crolib.Loaded]) -> dict[int, str]:
    """cro.entry_points, plus what other modules import from this one; an entry that is a
    veneer is ARM code whatever its pointer's bit 0 says, and a pointer into a veneer (its
    address word, or past its start) is data, not an entry."""
    entries = crolib.entry_points(ld, crs)
    lo, hi = ld.text
    for other in lds:
        if other is ld:
            continue
        for name, sym, _, _ in cross_imports(other, lds):
            if name == ld.cro.name and lo <= sym & ~1 < hi:
                entries.setdefault(sym & ~1, "thumb" if sym & 1 else "arm")
    def word(a):
        return struct.unpack_from("<I", ld.image, a - ld.base)[0] if lo <= a < hi - 3 else None
    for a in list(entries):
        w0 = a & ~3
        if word(w0 - 4) == VENEER or (word(w0) == VENEER and a != w0):
            del entries[a]               # a data word pointing at a veneer's address word or inside it
        elif a == w0 and word(a) == VENEER:
            entries[a] = "arm"
    return entries


def code_offset(header, addr: int) -> int:
    """Offset in the loaded code (text | ro | data, each padded to pages) of an address."""
    t, ro, d = header.text, header.ro, header.data
    for seg, off in ((t, 0), (ro, t.padded_size), (d, t.padded_size + ro.padded_size)):
        if seg.address <= addr < seg.address + seg.size:
            return off + addr - seg.address
    raise ValueError(f"0x{addr:08x} is in no segment")


def patch_veneers(header, code: bytes, crs: crolib.Cro, lds) -> bytes:
    """code.bin with the static executable's imports from the modules filled in."""
    out = bytearray(code)
    for ld in [lds] if isinstance(lds, crolib.Loaded) else lds:
        for tag, places in crolib.static_imports_of(crs, ld.cro.name):
            target = ld.segment_bases[tag & 0xF] + (tag >> 4)
            for at in places:
                struct.pack_into("<I", out, code_offset(header, at), target)
    return bytes(out)


def recompile_static(game: str, exheader: str, code_path: str, crs: crolib.Cro, lds, out: str) -> dict:
    """The game's static recompile (its tables, as recompile_game.py uses them), from
    code.bin with its veneers into `lds` filled in; a veneer's jump into a module is a
    tail call (ModuleAnalyzer)."""
    import codebin2elf
    import exheader as exh
    ns = argparse.Namespace(game=game, exheader=exheader, code=code_path, functions=None, extra=None,
                            hooks=None, tunables=None, out=None)
    cfg = games.resolve_args(ns)
    with open(exheader, "rb") as f:
        raw = f.read()
    header = exh.parse(raw)
    with open(code_path, "rb") as f:
        code = codebin2elf.load_code(header, f.read())
    if cfg:
        games.check_game_code(cfg, code)               # the shipped code is the one the tables fit
    code = patch_veneers(header, code, crs, lds)
    img = Image(code, header.text.address, R.code_size(header, code))
    segs = [(header.ro.address, header.ro.size), (header.data.address, header.data.size)]
    analyzer = type("BoundModuleAnalyzer", (ModuleAnalyzer,), {"outside": tuple(ld.text for ld in lds)})
    saved, R.Analyzer = R.Analyzer, analyzer
    try:
        return R.recompile(img, R.load_entries(ns.functions, ns.extra), out, data_segments=segs,
                           title_id=struct.unpack_from("<Q", raw, 0x200)[0])
    finally:
        R.Analyzer = saved


def read_layout(path: str) -> list[tuple[str, int]]:
    """modules.tsv: (module name, base)."""
    with open(path) as f:
        return [(n, int(b, 16)) for n, b in (line.split() for line in f if line.strip() and not line.startswith("#"))]


def module_image(ld: crolib.Loaded) -> Image:
    """From the base to the end of the module's code: the analyser's text."""
    return Image(ld.image, ld.base, ld.text[1] - ld.base)


def read_table(path: str) -> tuple[list[tuple[int, int, str]], list[str]]:
    """A table.c's entries, and its lines after the table (text range, hooks, tunables)."""
    entries, tail, in_table = [], [], False
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("const RFuncEntry rc_func_table[]"):
                in_table = True
                continue
            if in_table:
                m = ENTRY_RE.match(line)
                if m:
                    entries.append((int(m.group(1), 16), int(m.group(2)), m.group(3)))
                    continue
                if line == "};":
                    in_table = False
                continue
            if entries and not line.startswith("const u32 rc_func_count"):
                tail.append(line)
    return entries, tail


def merge(static_src: str, module_srcs: list[str] | str, out_src: str) -> int:
    """out_src: the modules' C files, links to the static C files, one funcs.h and one
    table.c. Returns the number of functions in the merged table."""
    module_srcs = [module_srcs] if isinstance(module_srcs, str) else module_srcs
    os.makedirs(out_src, exist_ok=True)
    for name in os.listdir(out_src):
        os.remove(os.path.join(out_src, name))
    for name in sorted(os.listdir(static_src)):
        if name.endswith(".c") and name != "table.c":
            os.symlink(os.path.abspath(os.path.join(static_src, name)), os.path.join(out_src, name))
    for module_src in module_srcs:
        for name in sorted(os.listdir(module_src)):
            if name.endswith(".c") and name != "table.c":
                if os.path.exists(os.path.join(out_src, name)):
                    raise SystemExit(f"{name} is in two of the builds")
                shutil.copy2(os.path.join(module_src, name), os.path.join(out_src, name))
    decls = []
    for src in (static_src, *module_srcs):
        with open(os.path.join(src, "funcs.h")) as f:
            decls += [line for line in f if line.startswith("void ")]
    with open(os.path.join(out_src, "funcs.h"), "w") as f:
        f.write('#include "recomp.h"\n' + "".join(decls))
    static_entries, tail = read_table(os.path.join(static_src, "table.c"))
    rows = list(static_entries)
    for module_src in module_srcs:
        rows += read_table(os.path.join(module_src, "table.c"))[0]
    addrs = [a for a, _, _ in rows]
    if len(set(addrs)) != len(addrs):
        dup = min(a for a in addrs if addrs.count(a) > 1)
        raise SystemExit(f"function addresses are in two of the builds, e.g. 0x{dup:08x}")
    rows.sort()
    lines = ['#include "funcs.h"', "", "const RFuncEntry rc_func_table[] = {"]
    lines += [f"    {{0x{a:08x}u, {m}, {fn}}}," for a, m, fn in rows]
    lines += ["};", f"const u32 rc_func_count = {len(rows)};", *tail]
    with open(os.path.join(out_src, "table.c"), "w") as f:
        f.write("\n".join(lines) + "\n")
    return len(rows)


VENEER = 0xE51FF004      # ldr pc, [pc, #-4]: the word after it is where it jumps


def branch_imports(ld: crolib.Loaded, static_segs: list[int]) -> set[int]:
    """The static addresses a module branches to: imports patched into a veneer's word or
    into a branch. Its other imports are data, some of it in the static .text."""
    out = set()
    for tag, head in ld.cro.anon_imports():
        sym = static_segs[tag & 0xF] + (tag >> 4)
        for p in ld.cro.patch_list(head):
            at = ld.segment_bases[p.target & 0xF] + (p.target >> 4) - ld.base
            before = struct.unpack_from("<I", ld.image, at - 4)[0] if at >= 4 else None
            if p.type in (crolib.R_ARM_CALL, crolib.R_ARM_JUMP24) or \
                    (p.type == crolib.R_ARM_ABS32 and before == VENEER):
                out.add(sym)
    return out


def static_entries(crs: crolib.Cro, modules: list[str]) -> dict[int, str]:
    """Every function the modules branch to in the static code: entry -> mode."""
    lo, hi = static_text(crs)
    segs = crolib.static_segments(crs)
    out: dict[int, str] = {}
    for path in modules:
        with open(path, "rb") as f:
            ld = crolib.load(f.read(), DEFAULT_BASE, segs)
        for a in branch_imports(ld, segs):
            if lo <= a & ~1 < hi:
                out.setdefault(a & ~1, "thumb" if a & 1 else "arm")
    return out


def write_static_entries(path: str, entries: dict[int, str], modules: int) -> None:
    with open(path, "w") as f:
        f.write(f"# static functions the game's {modules} CRO modules branch to (reference/recompile_module.py\n"
                "# --static-entries); code.bin alone doesn't show the ones only modules call\n")
        f.writelines(f"0x{a:08x} {m}\n" for a, m in sorted(entries.items()))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--crs", required=True, help="the game's static.crs")
    ap.add_argument("--game", default="mhxx", help="the reference game in games/ the modules belong to")
    ap.add_argument("--exheader", help="the game's exheader.bin")
    ap.add_argument("--code", help="the game's code.bin")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=DEFAULT_BASE, help="where the first module goes")
    ap.add_argument("-o", "--out")
    ap.add_argument("--static-entries", metavar="OUT", help="list the modules' static imports instead")
    ap.add_argument("modules", nargs="+", help=".cro files, in the order they're placed")
    args = ap.parse_args(argv)
    with open(args.crs, "rb") as f:
        crs = crolib.Cro(f.read())
    if args.static_entries:
        entries = static_entries(crs, args.modules)
        write_static_entries(args.static_entries, entries, len(args.modules))
        print(f"{len(entries)} static functions imported by {len(args.modules)} modules -> {args.static_entries}")
        return 0
    if not (args.exheader and args.code and args.out):
        ap.error("--exheader, --code and -o are needed to recompile modules")
    lds = load_all(crs, args.modules, args.base)
    res = recompile_static(args.game, args.exheader, args.code, crs, lds, os.path.join(args.out, "static"))
    print(f"static code, veneers into the modules filled in: {res['report']['functions']} functions")
    texts = [static_text(crs)] + [ld.text for ld in lds]
    srcs, total = [], 0
    for ld in lds:
        out = os.path.join(args.out, "modules", ld.cro.name)
        res = recompile_module(module_image(ld), module_entries(ld, crs, lds), out,
                               [t for t in texts if t != ld.text], ld.data_segments())
        rep = res["report"]
        total += rep["functions"]
        if rep["problems"]:
            print(f"  {ld.cro.name}: {rep['problems']} problems (see {out}/report.txt)")
        srcs.append(os.path.join(out, "src"))
    with open(os.path.join(args.out, "modules.tsv"), "w") as f:
        f.write("# module\tbase (reference/recompile_module.py)\n")
        f.writelines(f"{ld.cro.name}\t0x{ld.base:08x}\n" for ld in lds)
    print(f"{len(lds)} modules from 0x{args.base:08x} to 0x{lds[-1].base + len(lds[-1].image):08x}: "
          f"{total} functions")
    n = merge(os.path.join(args.out, "static", "src"), srcs, os.path.join(args.out, "src"))
    print(f"merged table: {n} functions -> {os.path.join(args.out, 'src')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
