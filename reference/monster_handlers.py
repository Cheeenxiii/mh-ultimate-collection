#!/usr/bin/env python3
"""The translation worklist for a source monster's action handlers.

For each action id MH4U has no handler for, this names the handler the source game reaches,
the engine functions its case block and handler call (with the constants left in r0-r3 and
the floats left in s0-s3), and, for each call, either MH4U's counterpart or the reason the
call cannot be translated yet. It is the worklist behind
[reference/README.md](README.md)'s "The 17 ids MH4U has no action for" and the per-id records
there; its companions are monster_actions.py (which action reaches which handler) and
monster_motions.py (which animation a handler starts).

    worklist --game mh3u --exheader <exheader> --code <code.bin> --range LO HI \
        --dispatcher 0x00687d30 --functions games/mh3u/functions.tsv \
        --actions 0/4,4,7/64,7/87,7/93,10/0,10/1,10/2,10/3,10/4,10/5,10/6,11/5,11/15,11/26,11/28,13/9
    targets --game mh3u ... --target OTHER_ACTIONS.tsv [--motions MOTIONS.tsv]

`targets` is the action-id map: the missing id -> the shared action whose handler it reaches,
with "body match" (the same handler function) or "tail match" (a short wrapper ending on it)
as the proof, and R1's motion comparison where the handler starts a constant motion.

stdout holds ids and counts. The TSV `-o` writes holds addresses and constants only, but it
is derived from game code: keep it outside the repository.

The counterpart tables are not duplicated here: they are read from reference/README.md, so a
call's verdict cannot drift from the page it is recorded on. A call is

  paired     MH4U has a counterpart, from the "73 with an MH4U counterpart" table;
  #55        MH4U has none yet, from the "28 with no MH4U counterpart" table (issue #55);
  internal   inside the monster's own code, so the translated handler carries it too;
  unmapped   neither table names it: its counterpart has to be found by reading.

A call also carries the arguments the code leaves for it. A float argument cannot be given
through the plugin API's ABI 3 `call`, which sets r0-r2 only (a plugin cannot set the guest's
VFP registers), and a pointer into the source game's data cannot be carried into MH4U's data.
Either one is a second reason a handler waits.
"""
from __future__ import annotations

import argparse
import os
import re
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
POINTER_LO, POINTER_HI = 0x00100000, 0x01000000   # a value in this range is an address
INT_REGS = ("r0", "r1", "r2", "r3")
FLOAT_REGS = ("s0", "s1", "s2", "s3")
NEXT_ENTRY_SLACK = 0x30    # an auto-made function size may be a little short of its body
WRITE_FIRST = {
    "mov", "movs", "mvn", "mvns", "add", "adds", "sub", "subs", "rsb", "and", "orr", "eor",
    "lsl", "lsr", "asr", "ror", "mul", "mla", "umull", "smull", "ldr", "ldrb", "ldrh",
    "ldrsb", "ldrsh", "ldm", "ldmia", "vmov", "vldr", "vadd", "vsub", "vmul", "vdiv",
    "vcvt", "vneg", "vabs", "vsqrt", "vcmp", "vcmpe",
}


@dataclass
class Call:
    site: int
    target: int
    ints: dict[str, int] = field(default_factory=dict)
    floats: dict[str, float] = field(default_factory=dict)
    tail: bool = False

    def row(self) -> str:
        def show(v):
            return f"data:0x{v:08x}" if POINTER_LO <= v < POINTER_HI else f"0x{v:x}"
        ints = ",".join(f"{k}={show(v)}" for k, v in sorted(self.ints.items()))
        floats = ",".join(f"{k}={v:.6g}" for k, v in sorted(self.floats.items()))
        return f"{self.site:#010x}\t{'b' if self.tail else 'bl'}\t{self.target:#010x}\t{ints}\t{floats}"


@dataclass
class Unit:
    action: str
    handler: int
    kind: str
    handler_is_engine: bool
    engine: list[Call]
    internal: list[int]
    paired: list[tuple[int, int, str]]
    lacking: list[int]
    unmapped: list[int]
    floats: list[int]
    data: list[int]
    sub_engine: list[Call] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.lacking or self.unmapped or self.floats or self.data or
                    (self.handler_is_engine and self.handler not in
                     {a for a, _, _ in self.paired} and self.handler not in self.lacking))

    def reasons(self) -> str:
        out = []
        if self.lacking:
            out.append("#55 " + ",".join(f"0x{a:08x}" for a in self.lacking))
        if self.floats:
            out.append("float arg to " + ",".join(f"0x{a:08x}" for a in self.floats))
        if self.data:
            out.append("source data to " + ",".join(f"0x{a:08x}" for a in self.data))
        if self.unmapped:
            out.append("unmapped " + ",".join(f"0x{a:08x}" for a in self.unmapped))
        if self.handler_is_engine:
            out.append(f"handler is engine code 0x{self.handler:08x}")
        return "; ".join(out) if out else "translatable"


def parse_action(text: str) -> tuple[int, int | None]:
    """"7/64", or "4" for a category with one action and no index."""
    if "/" in text:
        cat, idx = text.split("/", 1)
        return int(cat, 0), int(idx, 0)
    return int(text, 0), None


def action_name(cat: int, idx: int | None) -> str:
    return f"{cat}/{idx}" if idx is not None else str(cat)


def read_reference(path: str = README) -> tuple[dict[int, tuple[int, str]], dict[int, str]]:
    """The source -> MH4U counterpart tables, read off the page that records them."""
    paired, lacking = {}, {}
    section = None
    for line in open(path):
        if line.startswith("### The 73 with an MH4U counterpart"):
            section = "paired"
            continue
        if line.startswith("### The 28 with no MH4U counterpart"):
            section = "lacking"
            continue
        if line.startswith("### ") and section:
            break
        if section == "paired":
            m = re.match(r"\|\s*(0x[0-9a-fA-F]{8})\s*\|\s*(0x[0-9a-fA-F]{8})\s*\|(.*)\|", line)
            if m:
                paired[int(m.group(1), 16)] = (int(m.group(2), 16), m.group(3).strip())
        elif section == "lacking":
            m = re.match(r"\|\s*(0x[0-9a-fA-F]{8})\s*\|", line)
            if m:
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                lacking[int(m.group(1), 16)] = cells[-1]
    return paired, lacking


def read_functions(path: str) -> dict[int, int]:
    """Address -> size, from a reference game's function status table."""
    out = {}
    for line in open(path):
        cells = line.rstrip("\n").split("\t")
        if len(cells) >= 2 and cells[0].startswith("0x"):
            try:
                out[int(cells[0], 16)] = int(cells[1], 16)
            except ValueError:
                pass
    return out


_ENTRIES_CACHE: dict[int, list[int]] = {}


def body(entry: int, functions: dict[int, int]) -> tuple[int, int | None]:
    """The span to scan for one function.

    An address that is not a function entry is a case block: it runs to its terminator. For a
    function, the next entry wins when it is close to the table's size (the auto-made sizes
    can be short by a little); otherwise the size wins, since the next entry belongs to other
    code that happens to sit right after it."""
    if entry not in functions:
        return entry, None
    if id(functions) not in _ENTRIES_CACHE:
        _ENTRIES_CACHE[id(functions)] = sorted(functions)
    entries = _ENTRIES_CACHE[id(functions)]
    ahead = [a for a in entries if entry < a <= entry + functions[entry] + 0x30]
    if ahead:
        return entry, ahead[0]
    return entry, entry + functions[entry]


def _writes_first(mnemonic: str) -> bool:
    return mnemonic in WRITE_FIRST and not mnemonic.startswith("vst")


def scan(code, start: int, end: int | None = None, seed_ints=None,
         seed_floats=None) -> list[Call]:
    """The calls in [start, end) and the constants left for them.

    `end` None means a case block: it stops at its terminator and a `b` out of it is a tail
    call, recorded with the constants left for it. A function is scanned to its end, and a
    `b` out of it is recorded while the scan goes on (its other basic blocks follow)."""
    from capstone.arm import ARM_OP_IMM, ARM_OP_REG
    ints: dict[str, int | None] = dict(seed_ints or {})
    floats: dict[str, float | None] = dict(seed_floats or {})
    out: list[Call] = []
    n = max(1, (end - start) // 4) + 2 if end is not None else 256
    for i in code.insns(start, n):
        if end is not None and i.address >= end:
            break
        m, ops = i.mnemonic, i.operands
        if m in ("bl", "blx") and ops and ops[0].type == ARM_OP_IMM:
            out.append(Call(i.address, code.veneer(ops[0].imm) or ops[0].imm,
                            {k: v for k, v in ints.items() if v is not None},
                            {k: v for k, v in floats.items() if v is not None}))
            ints, floats = dict(seed_ints or {}), dict(seed_floats or {})
            continue
        if m == "b" and ops and ops[0].type == ARM_OP_IMM:
            t = code.veneer(ops[0].imm) or ops[0].imm
            if end is None or not (start <= t < end):
                out.append(Call(i.address, t,
                                {k: v for k, v in ints.items() if v is not None},
                                {k: v for k, v in floats.items() if v is not None}, tail=True))
                ints, floats = dict(seed_ints or {}), dict(seed_floats or {})
                if end is None:
                    break
            continue
        if end is None and ((m.startswith("pop") and "pc" in i.op_str) or m == "bx"):
            break
        if m == "mov" and len(ops) == 2 and ops[0].type == ARM_OP_REG:
            name = i.reg_name(ops[0].reg)
            src = ops[1]
            if name in INT_REGS:
                if src.type == ARM_OP_IMM:
                    ints[name] = src.imm
                elif src.type == ARM_OP_REG:
                    ints[name] = ints.get(i.reg_name(src.reg))
                else:
                    ints[name] = None
            continue
        if m in ("ldr", "vldr") and ops and ops[0].type == ARM_OP_REG:
            name = i.reg_name(ops[0].reg)
            mem = ops[1].mem if len(ops) == 2 and ops[1].type == 3 else None
            if mem is not None and i.reg_name(mem.base) == "pc":
                word = code.word(i.address + 8 + mem.disp)
                if m == "ldr" and name in INT_REGS:
                    ints[name] = word
                elif m == "vldr" and name in FLOAT_REGS:
                    floats[name] = struct.unpack("<f", struct.pack("<I", word))[0]
                continue
            if name in INT_REGS:
                ints[name] = None
            elif name in FLOAT_REGS:
                floats[name] = None
            continue
        if m.startswith("vmov") and ops and ops[0].type == ARM_OP_REG and \
                i.reg_name(ops[0].reg) in FLOAT_REGS:
            floats[i.reg_name(ops[0].reg)] = None
            continue
        if ops and ops[0].type == ARM_OP_REG and _writes_first(m):
            name = i.reg_name(ops[0].reg)
            if name in INT_REGS:
                ints[name] = None
            elif name in FLOAT_REGS:
                floats[name] = None
    return out


def follow(code, target: int, entries: list[int]) -> int:
    """A function that is one `b` to another function is an alias for it."""
    start, end = body(target, entries)
    first = next(iter(code.insns(start, 2)), None)
    if first is not None and first.mnemonic == "b" and first.operands:
        t = code.veneer(first.operands[0].imm) or first.operands[0].imm
        if end is None or not (start <= t < end):
            return t
    return target


def sub_calls(code, internal, functions, lo, hi, seen=None) -> list[Call]:
    """The engine calls the unit's own sub-handlers make, so a #55 call under one is counted."""
    seen = set() if seen is None else seen
    out = []
    for entry in internal:
        entry = follow(code, entry, functions)
        if entry in seen:
            continue
        seen.add(entry)
        own = scan(code, *body(entry, functions))
        more = []
        for c in own:
            t = follow(code, c.target, functions)
            if lo <= t < hi:
                more.append(t)
            else:
                out.append(c)
        out.extend(sub_calls(code, more, functions, lo, hi, seen))
    return out


def unit(code, action, inv, functions, lo, hi) -> Unit | None:
    match = [a for a in inv if (a.cat, a.idx) == action]
    if not match:
        return None
    a = match[0]
    block = scan(code, a.block)
    handler = follow(code, a.handler if a.handler is not None else a.block, functions)
    handler_is_engine = not (lo <= handler < hi)
    # A case block may branch into the handler; the constants it left for it are the
    # handler's arguments.
    seed = next((c for c in block if c.tail and follow(code, c.target, functions) == handler), None)
    arg_ints = dict(seed.ints) if seed else {}
    arg_floats = dict(seed.floats) if seed else {}
    calls = [c for c in block if not c.tail]
    # A handler that only calls one of the monster's own functions is a stub: the unit is
    # the function it calls (0x686bcc -> 0x697888), with the arguments it passes along.
    while True:
        own = scan(code, *body(handler, functions), arg_ints, arg_floats)
        internal = [c for c in own if lo <= c.target < hi]
        engine = [c for c in own if not (lo <= c.target < hi)]
        if not engine and len(internal) == 1 and not handler_is_engine:
            arg_ints = {**arg_ints, **internal[0].ints}
            arg_floats = {**arg_floats, **internal[0].floats}
            handler = follow(code, internal[0].target, functions)
            continue
        break
    calls.extend(own)
    if handler_is_engine:
        calls.append(Call(a.block, handler))
    internal = sorted({c.target for c in calls if lo <= c.target < hi})
    engine = [c for c in calls if not (lo <= c.target < hi)]
    return Unit(action_name(a.cat, a.idx), handler, a.kind, handler_is_engine, engine,
                internal, [], [], [], [], [],
                sub_calls(code, internal, functions, lo, hi))


def classify(u: Unit, paired, lacking) -> Unit:
    for c in u.engine + u.sub_engine:
        t = c.target
        if t in paired:
            u.paired.append((t, paired[t][0], paired[t][1]))
        elif t in lacking:
            u.lacking.append(t)
        else:
            u.unmapped.append(t)
        if c.floats and t not in u.floats:
            u.floats.append(t)
        if any(POINTER_LO <= v < POINTER_HI for v in c.ints.values()) and t not in u.data:
            u.data.append(t)
    return u


def cmd_worklist(args) -> int:
    import monster_actions  # imported here: its fork import needs a checkout the tests lack
    code = monster_actions.load_code(args)
    inv = monster_actions.inventory(code, args.dispatcher)
    functions = read_functions(args.functions)
    paired, lacking = read_reference()
    wanted = [parse_action(x) for x in args.actions.split(",")] if args.actions else \
        [(a.cat, a.idx) for a in inv]
    rows, units = [], []
    for action in wanted:
        u = unit(code, action, inv, functions, code.lo, code.hi)
        if u is None:
            print(f"{action_name(*action)}: the source has no such action")
            continue
        units.append(classify(u, paired, lacking))
    if args.output:
        for u in units:
            rows.append(f"# {u.action}\thandler 0x{u.handler:08x}\t{u.kind}")
            rows.extend(c.row() for c in u.engine)
            rows.extend(f"# internal\t0x{i:08x}" for i in u.internal)
            rows.extend("# sub-handler\t" + c.row() for c in u.sub_engine)
        with open(args.output, "w") as f:
            f.write("\n".join(rows) + "\n")
    for u in units:
        direct_paired = sum(1 for c in u.engine if c.target in paired)
        print(f"{u.action:<6} handler 0x{u.handler:08x}  {direct_paired} paired, "
              f"{len(u.internal)} internal, {len(u.sub_engine)} sub-handler calls  "
              f"{'BLOCKED' if u.blocked else 'translatable'}"
              f"{': ' + u.reasons() if u.blocked else ''}")
    n = sum(u.blocked for u in units)
    print(f"{len(units)} ids: {n} blocked by what the source play needs, {len(units) - n} translatable")
    return 0


def read_motions(path: str) -> dict[tuple[int, int | None], str]:
    """(category, index) -> the motion a handler starts, from monster_motions.py's list."""
    out = {}
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        cells = line.rstrip("\n").split("\t")
        try:
            cat = int(cells[0], 0)
            idx = int(cells[1], 0) if cells[1] else None
        except (IndexError, ValueError):
            continue
        out[(cat, idx)] = cells[3] if len(cells) > 3 else ""
    return out


def read_inventory_tsv(path: str) -> dict[tuple[int, int | None], str]:
    """The action ids another game's inventory holds, and the handler each reaches
    (monster_actions.py's TSV)."""
    out = {}
    for line in open(path):
        if line.startswith("#") or not line.strip():
            continue
        cells = line.rstrip("\n").split("\t")
        try:
            out[(int(cells[0], 0), int(cells[1], 0) if cells[1] else None)] = \
                cells[5] if len(cells) > 5 and cells[5] else ""
        except (IndexError, ValueError):
            pass
    return out


def target_rows(units: dict, tails: dict, target: dict, motions: dict,
                action: tuple[int, int | None]) -> list[tuple[tuple[int, int | None], str, str, str]]:
    """The shared actions `action` can be sent to, with the proof it is the same move.

    `units` is action id -> the handler function it reaches, `tails` the handler a short
    wrapper ends on, `target` the other game's inventory (id -> its handler) and `motions`
    the source game's motion per id."""
    u = units.get(action)
    if u is None:
        return []
    shared = sorted(other for other, ou in units.items()
                    if ou == u and other != action and other in target)
    proof = "body match"
    if not shared and action in tails:
        shared = sorted(other for other, ou in units.items()
                        if ou == tails[action] and other != action and other in target)
        proof = "tail match"
    out = []
    mine = motions.get(action, "")
    for other in shared:
        theirs = motions.get(other, "")
        if not motions:
            r1 = "R1 not supplied"
        elif mine and theirs and mine == theirs:
            r1 = f"R1 same motion {mine}"
        elif mine and theirs:
            r1 = f"R1 differs ({mine} vs {theirs})"
        else:
            r1 = "R1 not comparable (a handler starts no constant motion)"
        out.append((other, proof, r1, target.get(other, "")))
    return out


def cmd_targets(args) -> int:
    """The action-id map for the ids that reach the same handler as an action MH4U has."""
    import monster_actions
    code = monster_actions.load_code(args)
    inv = monster_actions.inventory(code, args.dispatcher)
    functions = read_functions(args.functions)
    target = read_inventory_tsv(args.target)
    motions = read_motions(args.motions) if args.motions else {}
    wanted = [parse_action(x) for x in args.actions.split(",")] if args.actions else \
        [(a.cat, a.idx) for a in inv]
    units, tails = {}, {}
    for a in inv:
        u = follow(code, a.handler if a.handler is not None else a.block, functions)
        units[(a.cat, a.idx)] = u
        start, end = body(u, functions)
        if (end or start + 0x40) - start <= 0x40:
            own = scan(code, start, end)
            last = max((c.site for c in own), default=None)
            tail = [follow(code, c.target, functions) for c in own if c.tail and c.site == last]
            if tail:
                tails[(a.cat, a.idx)] = tail[0]
    rows = []
    mapped = 0
    for action in wanted:
        u = units.get(action)
        if u is None:
            print(f"{action_name(*action)}: the source has no such action")
            continue
        targets = target_rows(units, tails, target, motions, action)
        if not targets:
            print(f"{action_name(*action):<6} handler 0x{u:08x}  no shared action reaches "
                  f"this handler: new code")
            continue
        for other, proof, r1, their_handler in targets:
            print(f"{action_name(*action):<6} -> {action_name(*other):<6} "
                  f"handler 0x{u:08x}  {proof}; {r1}; MH4U handler {their_handler or 'none'}")
            rows.append(f"{action_name(*action)}\t{action_name(*other)}\t0x{u:08x}\t{proof}\t"
                        f"{r1}\t{their_handler}")
        mapped += 1
    if args.output:
        with open(args.output, "w") as f:
            f.write("# action\ttarget\thandler\tproof\n" + "\n".join(rows) + "\n")
    print(f"{mapped} of {len(wanted)} ids reach a handler a shared action also reaches")
    return 0


def cmd_selfcheck(_args) -> int:
    """The per-id records still name the ids and handlers the page states."""
    paired, lacking = read_reference()
    print(f"paired {len(paired)}, no counterpart {len(lacking)}")
    return 0 if (len(paired), len(lacking)) == (73, 28) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("worklist")
    p.add_argument("--game", default="mh3u")
    p.add_argument("--exheader")
    p.add_argument("--code")
    p.add_argument("--module")
    p.add_argument("--crs")
    p.add_argument("--base", type=lambda s: int(s, 0), default=0x02000000)
    p.add_argument("--dispatcher", type=lambda s: int(s, 0), required=True)
    p.add_argument("--range", type=lambda s: int(s, 0), nargs=2, metavar=("LO", "HI"))
    p.add_argument("--functions", required=True)
    p.add_argument("--actions", help="comma-separated, e.g. 0/4,4,7/64 (default: every action)")
    p.add_argument("-o", "--output")
    p.set_defaults(fn=cmd_worklist)
    p = sub.add_parser("targets")
    p.add_argument("--game", default="mh3u")
    p.add_argument("--exheader")
    p.add_argument("--code")
    p.add_argument("--module")
    p.add_argument("--crs")
    p.add_argument("--base", type=lambda s: int(s, 0), default=0x02000000)
    p.add_argument("--dispatcher", type=lambda s: int(s, 0), required=True)
    p.add_argument("--range", type=lambda s: int(s, 0), nargs=2, metavar=("LO", "HI"))
    p.add_argument("--functions", required=True)
    p.add_argument("--target", required=True, help="the other game's inventory TSV")
    p.add_argument("--motions", help="the source game's motion list TSV, for R1 evidence")
    p.add_argument("--actions", help="comma-separated, e.g. 0/4,4,7/64 (default: every action)")
    p.add_argument("-o", "--output")
    p.set_defaults(fn=cmd_targets)
    sub.add_parser("selfcheck").set_defaults(fn=cmd_selfcheck)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
