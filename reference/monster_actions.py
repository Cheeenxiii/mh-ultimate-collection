#!/usr/bin/env python3
"""A monster's action inventory: every (category, index) its action dispatcher handles, and
the handler each one reaches.

MH4U, MH3U and MHXX run a monster's current action the same way: a dispatcher reads two
bytes, a category and an index, jumps through a table on the category, and each category
switches on the index (a jump table or a compare chain) to a case block. Most case blocks
tail-call the action's handler, some with constant arguments in r1-r3 (`pop {...}; mov r1,
#0; b handler`); a few do the work inline. A module's handler may be a static function,
reached through a veneer (`ldr pc, [pc, #-4]`).

The action ids are shared between games: where both games' handlers are already paired by
other means, the same (category, index) gives the same pair, so `pairs` turns two
inventories into handler pairs for `fnmap.py map --seed`.

    list   --game mh4u|mh3u|mhxx --exheader .. --code .. --dispatcher ADDR [--range LO HI] -o x.tsv
    list   --module roEm001.cro --crs static.crs --dispatcher ADDR -o x.tsv
    pairs  A.tsv B.tsv -o pairs.tsv     (handlers both games tail-call for the same action ids,
                                         kept only when each A handler meets one B handler)

`--range` bounds the monster's own code: a branch inside it is followed as part of the case
block, one outside is the handler (a module's own text is its range). The inventories hold
addresses only, but they are derived from game code: keep them outside the repository.
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

VENEER = 0xE51FF004            # ldr pc, [pc, #-4]
CASE_SPAN = 0x400              # a case block's own branches stay this close
TABLE_LOOKBACK = 3             # the bound's `cmp` may sit a few instructions before the jump


@dataclass
class Code:
    data: bytes
    base: int
    lo: int                    # the monster's own code
    hi: int

    def word(self, a: int) -> int:
        return struct.unpack_from("<I", self.data, a - self.base)[0]

    def insns(self, a: int, n: int = 64):
        from capstone import CS_ARCH_ARM, CS_MODE_ARM, Cs
        md = _md.get("arm")
        if md is None:
            md = _md["arm"] = Cs(CS_ARCH_ARM, CS_MODE_ARM)
            md.detail = True
        off = a - self.base
        return list(md.disasm(self.data[off:off + 4 * n], a))

    def veneer(self, a: int) -> int | None:
        if self.base <= a < self.base + len(self.data) - 8 and not a & 3 and self.word(a) == VENEER:
            return self.word(a + 4)
        return None


_md: dict = {}


@dataclass
class Action:
    cat: int
    idx: int | None            # None: the category has one action
    block: int                 # the case block
    fn: int | None             # the category's function, when it has its own
    kind: str                  # tail, inline, none, jump, long
    handler: int | None = None
    via_veneer: bool = False   # the handler is outside the code (a module's static import)
    args: dict[str, int] = field(default_factory=dict)
    calls: list[int] = field(default_factory=list)
    cond: bool = False         # the block tests something before its handler

    def row(self) -> str:
        def h(x):
            return "" if x is None else f"0x{x:08x}"
        args = ",".join(f"{k}={v}" for k, v in sorted(self.args.items()))
        return "\t".join([str(self.cat), "" if self.idx is None else str(self.idx), h(self.block), h(self.fn),
                          self.kind, h(self.handler), "1" if self.via_veneer else "0", args,
                          ",".join(h(c) for c in self.calls), "1" if self.cond else "0"])


HEADER = "# cat\tidx\tblock\tfn\tkind\thandler\tveneer\targs\tcalls\tcond\n"


def _imm(i, k):
    from capstone.arm import ARM_OP_IMM
    op = i.operands[k]
    return op.imm if op.type == ARM_OP_IMM else None


def _is_reg(i, k, reg=None):
    from capstone.arm import ARM_OP_REG
    op = i.operands[k]
    return op.type == ARM_OP_REG and (reg is None or op.reg == reg)


def find_switch(code: Code, a: int, limit: int = 24):
    """The first switch from `a`: a table jump (`cmp rX, #n; ldrlo pc, [pc, rX, lsl #2]`) or
    a compare chain on a byte just loaded. ({index: target}, default) or None."""
    ins = code.insns(a, limit + 40)
    for k, i in enumerate(ins[:limit]):
        if i.mnemonic in ("ldrlo", "ldrls") and i.op_str.startswith("pc, [pc, r"):
            cmps = [j for j in ins[max(0, k - TABLE_LOOKBACK):k] if j.mnemonic == "cmp"]
            if not cmps or _imm(cmps[-1], 1) is None:
                return None
            n = _imm(cmps[-1], 1) + (1 if i.mnemonic == "ldrls" else 0)
            nxt = ins[k + 1]
            dflt = {nxt.address}
            if nxt.mnemonic == "b":
                dflt.add(nxt.operands[0].imm)
            table = [code.word(i.address + 8 + 4 * x) for x in range(n)]
            return {x: t for x, t in enumerate(table) if t not in dflt}, min(dflt)
        if i.mnemonic in ("b", "bx") or i.mnemonic.startswith("pop"):
            break
    for k, i in enumerate(ins[:limit]):
        if i.mnemonic == "ldrb":
            reg = i.operands[0].reg
            cmp = [j for j in ins[k + 1:k + 4] if j.mnemonic == "cmp" and _is_reg(j, 0, reg)]
            if cmp:
                out, dflt = _chain(code, cmp[0].address, reg, set())
                return (out, dflt) if out else None
    return None


def _chain(code: Code, a: int, reg: int, seen: set):
    """`cmp r, #k; beq L` pairs, following the chain's other branches into its sub-chains."""
    out, dflt, cur = {}, None, None
    for i in code.insns(a, 64):
        if i.address in seen:
            break
        seen.add(i.address)
        m = i.mnemonic
        if m == "cmp" and _is_reg(i, 0, reg):
            cur = _imm(i, 1)
        elif m == "beq" and cur is not None:
            out[cur] = i.operands[0].imm
        elif m in ("bgt", "blt", "bge", "ble", "bhi", "blo", "bne") and cur is not None:
            sub, _ = _chain(code, i.operands[0].imm, reg, seen)
            out.update(sub)
        elif m == "b":
            t = i.operands[0].imm
            if i.address < t < i.address + 0x200 and t not in seen:
                sub, d = _chain(code, t, reg, seen)
                out.update(sub)
                dflt = dflt or d
            else:
                dflt = t
            break
        elif m.startswith("pop") or m == "bx":
            dflt = i.address
            break
    return out, dflt


def case(code: Code, a: int, depth: int = 0) -> dict:
    """What a case block does: the handler it tail-calls (with the constants it leaves in
    r1-r3), the functions it calls first, and whether it tests something on the way."""
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    regs: dict[str, int | None] = {}
    calls: list[int] = []
    cond = False
    for i in code.insns(a, 48):
        m = i.mnemonic
        if m == "nop":
            continue
        if m == "mov" and len(i.operands) == 2 and i.operands[0].type == ARM_OP_REG:
            r = i.reg_name(i.operands[0].reg)
            src = i.operands[1]
            regs[r] = src.imm if src.type == ARM_OP_IMM else \
                regs.get(i.reg_name(src.reg)) if src.type == ARM_OP_REG else None
            continue
        if m == "bl":
            t = i.operands[0].imm
            calls.append(code.veneer(t) or t)
            regs = {}
            continue
        if m.startswith("b") and m not in ("b", "bl", "bx", "blx", "bic", "bics") and i.operands \
                and i.operands[0].type == ARM_OP_IMM:
            cond = True
            continue
        if m == "b":
            t = i.operands[0].imm
            if code.veneer(t) is None and code.lo <= t < code.hi and a < t <= a + CASE_SPAN and depth < 3:
                r = case(code, t, depth + 1)       # the block's own continuation
                r["calls"] = calls + r["calls"]
                r["cond"] = r["cond"] or cond
                return r
            v = code.veneer(t)
            args = {k: v_ for k in ("r1", "r2", "r3") if (v_ := regs.get(k)) is not None}
            return {"kind": "tail", "handler": v if v is not None else t, "via_veneer": v is not None,
                    "args": args, "calls": calls, "cond": cond}
        if (m.startswith("pop") and "pc" in i.op_str) or m == "bx":
            return {"kind": "inline" if calls else "none", "calls": calls, "cond": cond}
        if m.startswith("ldr") and i.op_str.startswith("pc"):
            return {"kind": "jump", "calls": calls, "cond": cond}
    return {"kind": "long", "calls": calls, "cond": cond}


def category_function(code: Code, block: int) -> int | None:
    """A category block that only jumps on (`nop` or `pop {...}`, then `b fn`) to the
    monster's own code: the category's function."""
    for i in code.insns(block, 4):
        if i.mnemonic == "nop" or (i.mnemonic.startswith("pop") and "pc" not in i.op_str):
            continue
        if i.mnemonic == "b":
            t = i.operands[0].imm
            return t if code.lo <= t < code.hi else None
        return None
    return None


def inventory(code: Code, dispatcher: int) -> list[Action]:
    top = find_switch(code, dispatcher, limit=12)
    if top is None:
        raise ValueError(f"no switch on the category at 0x{dispatcher:08x}")
    cats, _ = top
    out = []
    for cat, block in sorted(cats.items()):
        first = case(code, block)
        fn = category_function(code, block)
        if fn is not None:
            start, limit = fn, 24              # the category has a function of its own
        else:
            start, limit = block, 6            # the category's switch is in the dispatcher
        sw = find_switch(code, start, limit)
        if sw is None:
            out.append(Action(cat, None, block, fn, **(case(code, fn) if fn is not None else first)))
            continue
        for idx, target in sorted(sw[0].items()):
            out.append(Action(cat, idx, target, fn, **case(code, target)))
    return out


def read_inventory(path: str) -> list[Action]:
    out = []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            def x(s):
                return int(s, 16) if s else None
            args = {k: int(v) for k, v in (kv.split("=") for kv in p[7].split(",") if kv)}
            out.append(Action(int(p[0]), int(p[1]) if p[1] else None, x(p[2]), x(p[3]), p[4], x(p[5]),
                              p[6] == "1", args, [int(c, 16) for c in p[8].split(",") if c], p[9] == "1"))
    return out


def pairs(a: list[Action], b: list[Action]) -> tuple[list[tuple[int, int]], dict]:
    """Handler pairs from shared action ids: A's handler -> the one B handler it meets."""
    kb = {(x.cat, x.idx): x for x in b}
    meet: dict[int, set[int]] = collections.defaultdict(set)
    stats = collections.Counter()
    for x in a:
        y = kb.get((x.cat, x.idx))
        if y is None:
            stats["only in A"] += 1
            continue
        stats["shared"] += 1
        if x.kind == "tail" and y.kind == "tail":
            meet[x.handler].add(y.handler)
            stats["same args" if x.args == y.args else "other args"] += 1
    stats["only in B"] = len(set(kb) - {(x.cat, x.idx) for x in a})
    out = sorted((x, next(iter(ys))) for x, ys in meet.items() if len(ys) == 1)
    stats["handlers meeting one"] = len(out)
    stats["handlers meeting several"] = sum(1 for ys in meet.values() if len(ys) > 1)
    return out, dict(stats)


def load_code(args) -> Code:
    if args.module:
        import cro as crolib
        with open(args.crs, "rb") as f:
            crs = crolib.Cro(f.read())
        with open(args.module, "rb") as f:
            ld = crolib.load(f.read(), args.base, crolib.static_segments(crs))
        lo, hi = ld.text
        return Code(ld.image, ld.base, *(args.range or (lo, hi)))
    import codebin2elf
    import exheader as exh
    with open(args.exheader, "rb") as f:
        header = exh.parse(f.read())
    with open(args.code, "rb") as f:
        data = codebin2elf.load_code(header, f.read())
    if not args.range:
        raise SystemExit("--range LO HI: the monster's own code in code.bin")
    return Code(data, header.text.address, *args.range)


def cmd_list(args) -> int:
    code = load_code(args)
    acts = inventory(code, args.dispatcher)
    with open(args.output, "w") as f:
        f.write(HEADER)
        f.writelines(x.row() + "\n" for x in acts)
    kinds = collections.Counter(x.kind for x in acts)
    cats = collections.Counter(x.cat for x in acts)
    handlers = {x.handler for x in acts if x.kind == "tail"}
    print(f"{len(acts)} actions in {len(cats)} categories, {len(handlers)} distinct handlers; "
          + ", ".join(f"{k} {n}" for k, n in kinds.most_common()))
    print("per category: " + ", ".join(f"{c}: {n}" for c, n in sorted(cats.items())))
    return 0


def cmd_pairs(args) -> int:
    out, stats = pairs(read_inventory(args.a), read_inventory(args.b))
    with open(args.output, "w") as f:
        f.write("# A\tB\thow\n")
        f.writelines(f"0x{x:08x}\t0x{y:08x}\taction\n" for x, y in out)
    print(", ".join(f"{k}: {v}" for k, v in stats.items()))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("--game", default="mh4u", help="for the record only; the code is what --code holds")
    p.add_argument("--exheader")
    p.add_argument("--code")
    p.add_argument("--module")
    p.add_argument("--crs")
    p.add_argument("--base", type=lambda s: int(s, 0), default=0x02000000, help="where the module is loaded")
    p.add_argument("--dispatcher", type=lambda s: int(s, 0), required=True)
    p.add_argument("--range", type=lambda s: int(s, 0), nargs=2, metavar=("LO", "HI"))
    p.add_argument("-o", "--output", required=True)
    p = sub.add_parser("pairs")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("-o", "--output", required=True)
    args = ap.parse_args(argv)
    return {"list": cmd_list, "pairs": cmd_pairs}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
