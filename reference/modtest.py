#!/usr/bin/env python3
"""gametest for CRO modules recompiled with reference/recompile_module.py: each of the
modules' functions (with everything it calls, in the modules or the static executable)
against the original code in Unicorn, from identical random states.

Both machines get the static executable as gametest maps it, with its veneers into the
modules resolved as the loader would, and the modules loaded where they were recompiled
for (the build's modules.tsv). The verdicts are gametest's.

usage: python3 -m recomp.modtest --build build/recomp-mhxx-modules \\
           --exheader <work>/exheader.bin --code <work>/code.bin --crs static.crs <romfs>/*.cro \\
           [--only-module roEm001] [--cases 4] [--report r.tsv]
"""
from __future__ import annotations

import argparse
import collections
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fork  # noqa: E402,F401  (the fork's tools on sys.path)

import codebin2elf  # noqa: E402
import cro as crolib  # noqa: E402
import exheader as exh  # noqa: E402
import recompile_module as RM  # noqa: E402
from recomp import gametest as G  # noqa: E402
from recomp.harness.machines import Region  # noqa: E402

code_offset = RM.code_offset
patch_veneers = RM.patch_veneers


def module_regions(ld: crolib.Loaded) -> list[Region]:
    """The whole module image (file then .bss), writable: its .data and .bss change, and
    resetting the rest each case costs little."""
    size = G.page_up(len(ld.image))
    return [Region(ld.base, size, True, ld.image.ljust(size, b"\0"))]


def load_layout(build: str, crs: crolib.Cro, paths: list[str]) -> list[crolib.Loaded]:
    """The modules where the build put them: its modules.tsv names them in order."""
    layout = RM.read_layout(os.path.join(build, "modules.tsv"))
    by_name = {}
    for p in paths:
        with open(p, "rb") as f:
            by_name[crolib.Cro(f.read()).name] = p
    missing = [n for n, _ in layout if n not in by_name]
    if missing:
        raise SystemExit(f"modules.tsv names modules not given: {', '.join(missing[:5])}")
    lds = RM.load_all(crs, [by_name[n] for n, _ in layout], layout[0][1])
    for ld, (name, base) in zip(lds, layout, strict=False):
        if ld.base != base:
            raise SystemExit(f"{name} lands at 0x{ld.base:08x}, the build has it at 0x{base:08x}")
    return lds


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--build", required=True, help="reference/recompile_module.py's output (game.so in it)")
    ap.add_argument("--lib", help="default: <build>/game.so")
    ap.add_argument("--exheader", required=True)
    ap.add_argument("--code", required=True)
    ap.add_argument("--crs", required=True)
    ap.add_argument("modules", nargs="+", help="the .cro files (all those the build has)")
    ap.add_argument("--only-module", action="append", default=[], help="test only this module's functions")
    ap.add_argument("--cases", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--report", default="")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    with open(args.exheader, "rb") as f:
        header = exh.parse(f.read())
    with open(args.code, "rb") as f:
        code = codebin2elf.load_code(header, f.read())
    with open(args.crs, "rb") as f:
        crs = crolib.Cro(f.read())
    lds = load_layout(args.build, crs, args.modules)
    fixed, rw = G.build_regions(header, patch_veneers(header, code, crs, lds))
    for ld in lds:
        rw += module_regions(ld)
    # a jump outside the code (the static text up to the last module's) is a fault both ways
    G.TEXT_RANGE = (header.text.address, max(ld.text[1] for ld in lds))
    tester = G.Tester(args.lib or os.path.join(args.build, "game.so"), fixed, rw, args.seed)
    owner = {}
    for ld in lds:
        if not args.only_module or ld.cro.name in args.only_module:
            owner[ld.text] = ld.cro.name
    funcs = [(f, m, n) for f, m in tester.funcs for (lo, hi), n in owner.items() if lo <= f < hi]
    if args.only:
        wanted = {int(x, 16) for x in args.only.split(",")}
        funcs = [f for f in funcs if f[0] in wanted]
    rng = random.Random(args.seed)
    verdicts, outcomes_total, rows = collections.Counter(), collections.Counter(), []
    per_module: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    t0 = time.time()
    for addr, mode, name in funcs:
        outs, notes = [], []
        for _ in range(args.cases):
            o, note = tester.run_case(addr, bool(mode), rng)
            outs.append(o)
            notes.append(note)
            outcomes_total[o] += 1
        v = G.function_verdict(outs)
        verdicts[v] += 1
        per_module[name][v] += 1
        rows.append((addr, mode, name, v, next((nt for o, nt in zip(outs, notes, strict=False) if o == v), "")))
        if args.verbose and v not in ("pass", "agree-fault-only", "inconclusive"):
            print(f"  {name} {addr:#010x} {v}: {rows[-1][4]}", flush=True)
    print(f"modules: {len(per_module)}  functions: {len(funcs)}  cases: {sum(outcomes_total.values())}  "
          f"time: {time.time() - t0:.0f}s")
    print(f"case outcomes: {dict(outcomes_total)}")
    print(f"function verdicts: {dict(verdicts)}")
    bad = {n: c for n, c in per_module.items() if any(not k.startswith(("pass", "agree", "incon")) for k in c)}
    for n, c in sorted(bad.items()):
        print(f"  {n}: {dict(c)}")
    if tester.missing:
        print(f"targets not in the table: {', '.join(f'0x{t:08x}' for t in sorted(tester.missing)[:20])}")
    if args.report:
        with open(args.report, "w") as f:
            f.write("address\tmode\tmodule\tverdict\tnote\n")
            for addr, mode, name, v, note in rows:
                f.write(f"0x{addr:08x}\t{'thumb' if mode else 'arm'}\t{name}\t{v}\t{note}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
