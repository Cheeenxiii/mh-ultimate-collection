#!/usr/bin/env python3
"""The fields two games' paired action handlers read, as a map a port can be written against.

A monster's action handlers keep their state in a work block: MH3U reaches it at
`*(this+0x1a48)`, MH4U at `*(this+0xe28)`, MHXX at `*(this+0x10a8)`. For a shared action the
two handlers call the same engine functions in the same order, so a field read on one side
sits at the point its counterpart sits on the other. This tool pairs the handlers
(monster_actions.py's `pairs`), reads each handler's loads, stores and calls in program
order, aligns the two event streams, and prints the offset correspondences with how many of
the pairs agree on each.

It reproduces, and checks, [README.md](README.md)'s "The 3U work block on MH4U's layout":
`check` re-derives each row of that page and compares its stated pair count, so the map
cannot drift from the code it was read from.

    map   --a-inv A.tsv --b-inv B.tsv --a-exheader E --a-code C --a-range LO HI \
          --b-exheader E --b-code C --b-range LO HI [--extra-pairs F] [-o map.txt]
    check --page reference/README.md  (the same game arguments)  [--extra-pairs F]

The inventories are `monster_actions.py list`'s TSVs. `--extra-pairs` adds handler pairs
`pairs` leaves out (its one-to-several cases, and a pair read by hand); by default the check
takes the engine function twins from the page itself -- its "The 73 with an MH4U counterpart"
table -- so a row's verdict cannot drift from the table that records it. A pair whose fields
contradict the rest of the map is reported as misaligned and contributes no field votes.

Addresses, offsets and counts only. The inventories and any output are derived from game
code: keep them outside the repository.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import os
import re
import struct
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

README = os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md")
MAP_HEADING = "### The 3U work block on MH4U's layout"
BASE_HEADING = "### The base-class helpers behind category 0"
WORK = {"mh3u": 0x1A48, "mh4u": 0x0E28, "mhxx": 0x10A8}
TOKEN = 0x4000            # the most bytes one handler scan decodes
LOCAL = 0x500             # a branch this close to the entry is inside the handler
CALL_KEY = ("call",)


class Code:
    """One game's decompressed code, addressed by its virtual address."""

    def __init__(self, data: bytes, base: int):
        self.data, self.base = data, base

    def word(self, a: int) -> int:
        return struct.unpack_from("<I", self.data, a - self.base)[0]

    def bytes(self, a: int, n: int) -> bytes:
        return self.data[a - self.base:a - self.base + n]


class Game:
    """A code image, the range of the monster's own code, and its block pointer field."""

    def __init__(self, name: str, code: Code, lo: int = 0, hi: int = 0):
        if name not in WORK:
            raise ValueError(f"unknown game {name!r} (known: {', '.join(WORK)})")
        self.name, self.code, self.work = name, code, WORK[name]
        self.own = (lo, hi) if hi else (0, 0)


def load_game(name: str, exheader_path: str, code_path: str, lo: int, hi: int) -> Game:
    """A game's code, decompressed the way the other reference tools read it."""
    import fork  # noqa: F401  (the fork's tools on sys.path)

    import codebin2elf
    import exheader as exh
    with open(exheader_path, "rb") as f:
        header = exh.parse(f.read())
    with open(code_path, "rb") as f:
        data = codebin2elf.load_code(header, f.read())
    return Game(name, Code(data, header.text.address), lo, hi)


# ── one handler's events ─────────────────────────────────────────────────────

@dataclass
class Event:
    kind: str                 # 'field' or 'call'
    addr: int
    space: str = ""           # 'work' or 'this'
    off: int = 0
    size: int = 4
    write: bool = False
    target: int = 0
    args: tuple = ()

    def key(self):
        """What two events must share to correspond: a call to a call, a field read of the
        same width and direction to another."""
        if self.kind == "call":
            return CALL_KEY
        return ("field", self.space, self.size, self.write)

    def __str__(self) -> str:
        if self.kind == "call":
            return f"call {self.target:#x}"
        return f"{'w' if self.write else 'r'}{self.size} {self.space}+{self.off:#x}"


def _size(mnem: str) -> int:
    if mnem.endswith("b") and mnem != "sub":
        return 1
    if mnem.endswith("h") or mnem in ("ldrsb", "ldrsh"):
        return 2
    return 4


def _writes(mnem: str) -> bool:
    return mnem.startswith("st") or mnem.startswith("vst")


def function_insns(game: Game, entry: int) -> list:
    """The instructions reached from `entry`: local branches followed, a branch out kept as a
    tail call, returns stopping the flow. The bound keeps a literal pool to a few words."""
    from capstone.arm import ARM_OP_IMM
    code, out, todo = game.code, {}, [entry]
    while todo:
        x = todo.pop()
        while entry <= x < entry + TOKEN and x not in out:
            i = next(iter(_disasm(code, x)), None)
            if i is None:
                break
            out[x] = i
            m = i.mnemonic
            if m == "b" and i.operands and i.operands[0].type == ARM_OP_IMM:
                t = i.operands[0].imm
                if entry <= t < entry + LOCAL:
                    todo.append(t)
                break
            if m == "bx" or (m.startswith("pop") and "pc" in i.op_str):
                break
            if m.startswith("b") and m not in ("bl", "blx", "bic", "bics", "bfi", "bfc") \
                    and i.operands and i.operands[0].type == ARM_OP_IMM:
                t = i.operands[0].imm
                if entry <= t < entry + LOCAL:
                    todo.append(t)
            x += 4
    return [out[a] for a in sorted(out)]


def _disasm(code: Code, a: int):
    from capstone import CS_ARCH_ARM, CS_MODE_ARM, Cs
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    return md.disasm(code.bytes(a, 4), a, 1)


def scan(game: Game, entry: int) -> list[Event]:
    """A handler's field reads/stores and its calls, in address order.

    The work block pointer is followed through `*(this+WORK)` (both `ldr rX,[r0,#WORK]` and
    the constant-in-a-register form a compiler emits when the offset is large), and a field
    addressed as `small constant + work` is recognised too. Caller-saved registers are
    forgotten at a call; a call is recorded only when it leaves the monster's own code."""
    from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_OP_REG, ARM_REG_PC
    W = game.work
    insns = function_insns(game, entry)
    if not insns:
        return []
    byaddr = {i.address for i in insns}
    state: dict[int, dict] = {insns[0].address: {"r0": ("ptr", "this", 0)}}
    events: dict[int, list[Event]] = {}
    for _ in range(40):
        changed = False
        for i in insns:
            st = state.get(i.address)
            if st is None:
                continue
            st = dict(st)
            evs: list[Event] = []
            m = i.mnemonic
            mo = None
            for k in (1, 0):
                if len(i.operands) > k and i.operands[k].type == ARM_OP_MEM:
                    mo = i.operands[k].mem
                    break
            if mo is not None and mo.base and mo.disp is not None:
                base = i.reg_name(mo.base)
                v = st.get(base)
                if mo.index:
                    idx = st.get(i.reg_name(mo.index))
                    if v and v[0] == "c" and idx and idx[0] == "ptr" \
                            and idx[1] == "work" and idx[2] == 0 and v[2] != W:
                        evs.append(Event("field", i.address, "work", v[2],
                                         1 if m.endswith("b") else 4, _writes(m)))
                elif v and v[0] == "ptr":
                    off = v[2] + mo.disp
                    if not (v[1] == "this" and off == W):
                        evs.append(Event("field", i.address, v[1], off, _size(m), _writes(m)))
            tail = (m == "b" and i.operands and i.operands[0].type == ARM_OP_IMM
                    and not (entry <= i.operands[0].imm < entry + LOCAL))
            if (m in ("bl", "blx") or tail) and i.operands and i.operands[0].type == ARM_OP_IMM:
                t = i.operands[0].imm
                if tail or not (game.own[0] <= t < game.own[1]):
                    args = tuple(st[r][2] if r in st and st[r] and st[r][0] == "c" else None
                                 for r in ("r1", "r2", "r3"))
                    evs.append(Event("call", i.address, target=t, args=args))
            dst = i.reg_name(i.operands[0].reg) if (m in (
                "ldr", "ldrb", "ldrh", "ldrsb", "ldrsh", "mov", "movw", "add", "sub")
                and i.operands and i.operands[0].type == ARM_OP_REG) else None
            new: dict = {}
            if dst:
                if m == "mov" and len(i.operands) > 1 and i.operands[1].type == ARM_OP_REG:
                    new[dst] = st.get(i.reg_name(i.operands[1].reg))
                elif m in ("mov", "movw") and i.operands[1].type == ARM_OP_IMM:
                    new[dst] = ("c", 0, i.operands[1].imm)
                elif m in ("add", "sub") and i.operands[1].type == ARM_OP_REG:
                    v = st.get(i.reg_name(i.operands[1].reg))
                    im = i.operands[2].imm if len(i.operands) > 2 and \
                        i.operands[2].type == ARM_OP_IMM else 0
                    if m == "sub":
                        im = -im
                    if v and v[0] == "ptr":
                        new[dst] = ("ptr", v[1], v[2] + im)
                    elif v and v[0] == "c":
                        new[dst] = ("c", 0, v[2] + im)
                elif mo is not None and m.startswith(("ld", "vl")):
                    base = i.reg_name(mo.base)
                    v = st.get(base)
                    if mo.base == ARM_REG_PC:
                        new[dst] = ("c", 0, game.code.word(i.address + 8 + mo.disp))
                    elif mo.index:
                        idx = st.get(i.reg_name(mo.index))
                        if v and v[0] == "c" and idx and idx[0] == "ptr" \
                                and idx[1] == "this" and idx[2] == 0 and v[2] == W:
                            new[dst] = ("ptr", "work", 0)
                        else:
                            new[dst] = None
                    elif v and v[0] == "ptr":
                        off = v[2] + mo.disp
                        new[dst] = ("ptr", "work", 0) if (v[1] == "this" and off == W) else None
                    else:
                        new[dst] = None
            if m in ("bl", "blx"):
                new.update({r: None for r in ("r0", "r1", "r2", "r3", "ip", "lr")})
            nst = dict(st)
            nst.update(new)
            nst = {r: v for r, v in nst.items() if v is not None}
            succ = []
            if m == "b" and i.operands and i.operands[0].type == ARM_OP_IMM:
                succ = [i.operands[0].imm]
            elif m.startswith("b") and m not in ("bl", "blx", "bic", "bics") and i.operands \
                    and i.operands[0].type == ARM_OP_IMM:
                succ = [i.operands[0].imm, i.address + 4]
            elif m == "bx" or (m.startswith("pop") and "pc" in i.op_str):
                succ = []
            else:
                succ = [i.address + 4]
            for s in succ:
                if s not in byaddr:
                    continue
                old = state.get(s)
                if old is None:
                    state[s] = nst
                    changed = True
                else:
                    merged = {r: v for r, v in nst.items() if old.get(r) == v}
                    if merged != old:
                        state[s] = merged
                        changed = True
            events[i.address] = evs
        if not changed:
            break
    return [e for a in sorted(events) for e in events[a]]


# ── two handlers, aligned ────────────────────────────────────────────────────

@dataclass
class Agreement:
    space: str
    off_a: int
    off_b: int


@dataclass
class Pairing:
    """One handler pair: the fields its two sides put together, and its alignment verdict."""
    a: int
    b: int
    fields: list[Agreement] = field(default_factory=list)
    calls: list[tuple[Event, Event]] = field(default_factory=list)
    misaligned: str = ""      # why its fields do not line up ("" when they do)


def align(ev_a: list[Event], ev_b: list[Event]) -> tuple[list[Agreement], list[tuple[Event, Event]]]:
    """The events the two streams share, in order: a call with a call, a field with a field
    of the same kind. Within a matching block the events are taken one for one."""
    sm = difflib.SequenceMatcher(None, [e.key() for e in ev_a], [e.key() for e in ev_b],
                                 autojunk=False)
    fields, calls = [], []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            x, y = ev_a[blk.a + k], ev_b[blk.b + k]
            if x.kind == "call" and y.kind == "call":
                calls.append((x, y))
            elif x.kind == "field" and y.kind == "field" and x.space == y.space:
                fields.append(Agreement(x.space, x.off, y.off))
    return fields, calls


def disagreement(index: int, fields: list[Agreement], support: dict) -> str:
    """Whether a pair contradicts what the rest of the map says.

    For each field, the map's other pairs are asked whether they put the same 3U offset at
    the pair's 4U offset (agreement), at another offset strongly enough that a different
    role is established (contradiction), or not at all (no evidence). A pair whose every
    settled field is contradicted is misaligned -- a shifted or wrongly paired handler -- and
    the map does not count it."""
    if len(fields) < 2:
        return ""
    agree = contradict = 0
    for f in fields:
        others = support[(f.space, f.off_a, f.off_b)] - {index}
        if others:
            agree += 1
        elif any(len(support[(sp, oa, ob)] - {index}) >= 2
                 for (sp, oa, ob) in support
                 if sp == f.space and oa == f.off_a and ob != f.off_b):
            contradict += 1
    if agree == 0 and contradict >= 2:
        return (f"all {contradict} of its settled fields contradict the rest of the map")
    return ""


# ── the page's tables ────────────────────────────────────────────────────────

@dataclass
class Row:
    a: str                    # 3U cell as written, e.g. work+0x38 / +0x3c
    b: str
    how: str
    line: int

    def offsets(self) -> list[tuple[str, int, list[int]]]:
        """(space, off_a, the off_b's the row offers) for each component of the row."""
        ca, alternatives = _components(self.a), _alternatives(self.b)
        if not ca or not alternatives:
            return []
        if len(ca) != len(alternatives):
            if len(ca) == 1:
                ca = ca * len(alternatives)
            elif len(alternatives) == 1:
                alternatives = alternatives * len(ca)
            else:
                return []
        out = []
        for (space, off_a), offs_b in zip(ca, alternatives, strict=False):
            if offs_b and all(space == s for s, _ in offs_b):
                out.append((space, off_a, [o for _, o in offs_b]))
        return out

    def counts(self) -> list[int]:
        """The pair counts the row states, one per component where it can be read."""
        text = self.how
        m = re.search(r"(?<![\d/])(\d+) and (\d+) pairs?\b", text)
        if m:
            return [int(m.group(1)), int(m.group(2))]
        m = re.search(r"(?<![\d/])(\d+) of the 57 pairs\b", text) or \
            re.search(r"(?<![\d/])(\d+) pairs?\b", text)
        return [int(m.group(1))] if m else []


def _components(cell: str) -> list[tuple[str, int]]:
    """`work+0x38 / +0x3c / +0x40`, `work+0xe3, +0xe4`, `*(this+0x1e70)` to a list."""
    cell = cell.replace("`", "").replace("*(this+0x", "this+0x").strip()
    if not cell or cell in ("—", "-"):
        return []
    head = re.match(r"(work|this)\+0x([0-9a-fA-F]+)", cell)
    if not head:
        return []
    space = head.group(1)
    out = [(space, int(head.group(2), 16))]
    for part in re.split(r"\s*[/,]\s*", cell[head.end():]):
        m = re.match(r"\+0x([0-9a-fA-F]+)$", part.strip())
        if m:
            out.append((space, int(m.group(1), 16)))
    return out


def _alternatives(cell: str) -> list[list[tuple[str, int]]]:
    """The b cell's components per component of the a cell; `or` gives two candidates."""
    options = [o.strip() for o in cell.replace("`", "").split(" or ")]
    per, space = [], None
    for o in options:
        o = o.replace("*(this+0x", "this+0x")
        comps = _components(o)
        if comps:
            space = comps[0][0]
        elif space and re.match(r"\+0x[0-9a-fA-F]+$", o):
            comps = [(space, int(o[3:], 16))]
        per.append(comps)
    n = max((len(c) for c in per), default=0)
    out = []
    for k in range(n):
        out.append([(space, off) for c in per if len(c) == n
                    for space, off in [c[k]]])
    return out


def read_map_rows(path: str = README) -> list[Row]:
    """The map's table rows, between the section heading and the next one."""
    rows, inside = [], False
    for n, line in enumerate(open(path), 1):
        if line.startswith(MAP_HEADING):
            inside = True
            continue
        if inside and line.startswith("### "):
            break
        if not inside or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        first = cells[0].strip("`")
        if first.startswith(("work+", "this+")):
            rows.append(Row(cells[0], cells[1], cells[3], n))
    return rows


def read_engine_pairs(path: str = README) -> dict[int, int]:
    """The 73 table's source -> MH4U counterparts, read off the page that records them."""
    try:
        import monster_handlers
        return {a: b for a, (b, _) in monster_handlers.read_reference(path)[0].items()}
    except Exception:          # a page without the table, or a bare checkout
        return {}


def read_pairs_file(path: str) -> list[tuple[int, int]]:
    """One `A-address B-address` per line (a map's own format works)."""
    out = []
    for line in open(path):
        p = line.split()
        if p and not line.startswith("#") and not p[0].startswith("#"):
            out.append((int(p[0], 16), int(p[1], 16)))
    return out


# ── the derivation ───────────────────────────────────────────────────────────

@dataclass
class Map:
    """The offsets the pairs and the twins put together, with their counts."""
    pair_votes: dict = field(default_factory=lambda: collections.defaultdict(collections.Counter))
    pair_sets: dict = field(default_factory=lambda: collections.defaultdict(set))
    twin_votes: dict = field(default_factory=lambda: collections.defaultdict(collections.Counter))
    twin_sets: dict = field(default_factory=lambda: collections.defaultdict(set))
    reads: dict = field(default_factory=lambda: collections.Counter())
    pairings: list[Pairing] = field(default_factory=list)
    handler_pairs: int = 0
    shared: int = 0

    def pairs_agreeing(self, space: str, off_a: int, off_b: int) -> int:
        """How many handler pairs put the two offsets together."""
        return len(self.pair_sets.get((space, off_a, off_b), ()))

    def twins_agreeing(self, space: str, off_a: int, off_b: int) -> int:
        return len(self.twin_sets.get((space, off_a, off_b), ()))


def derive(games: dict[str, Game], inv: dict[str, list], extra: list[tuple[int, int]],
           engine: dict[int, int]) -> Map:
    """The field correspondences from the handler pairs and the engine function twins."""
    import monster_actions as ma
    a, b = games["a"], games["b"]
    out = Map()
    pairs, stats = ma.pairs(inv["a"], inv["b"])
    out.shared = stats.get("shared", 0)
    out.handler_pairs = len(pairs)
    seen, scanned = set(), []
    for ha, hb in list(pairs) + list(extra):
        if (ha, hb) in seen:
            continue
        seen.add((ha, hb))
        ev_a, ev_b = scan(a, ha), scan(b, hb)
        for e in ev_a:
            if e.kind == "field":
                out.reads[(e.space, e.off)] += 1
        fields, calls = align(ev_a, ev_b)
        scanned.append(Pairing(ha, hb, fields, calls))
    # what the other pairs say each offset holds, then the pairs that agree with it
    support: dict[tuple[str, int, int], set[int]] = collections.defaultdict(set)
    targets: dict[tuple[str, int], set[int]] = collections.defaultdict(set)
    for i, p in enumerate(scanned):
        for f in p.fields:
            support[(f.space, f.off_a, f.off_b)].add(i)
            targets[(f.space, f.off_a)].add(f.off_b)
    for i, p in enumerate(scanned):
        p.misaligned = disagreement(i, p.fields, support)
        out.pairings.append(p)
        if p.misaligned:
            continue
        for f in p.fields:
            out.pair_votes[(f.space, f.off_a)][f.off_b] += 1
            out.pair_sets[(f.space, f.off_a, f.off_b)].add((p.a, p.b))
    for fa, fb in engine.items():
        for f in align(scan(a, fa), scan(b, fb))[0]:
            out.twin_votes[(f.space, f.off_a)][f.off_b] += 1
            out.twin_sets[(f.space, f.off_a, f.off_b)].add((fa, fb))
    return out


def command_map(args) -> int:
    games, inv = _inputs(args)
    engine = read_engine_pairs(args.page)
    extra = read_pairs_file(args.extra_pairs) if args.extra_pairs else []
    m = derive(games, inv, extra, engine)
    lines = [f"{m.handler_pairs} handler pairs from {m.shared} shared action ids"]
    for (space, off_a), votes in sorted(m.pair_votes.items()):
        off_b, n = votes.most_common(1)[0]
        lines.append(f"pair {space}+{off_a:#06x} -> +{off_b:#06x}  "
                     f"{m.pairs_agreeing(space, off_a, off_b)} pairs ({n} votes)")
    for (space, off_a), votes in sorted(m.twin_votes.items()):
        off_b, n = votes.most_common(1)[0]
        lines.append(f"twin {space}+{off_a:#06x} -> +{off_b:#06x}  "
                     f"{m.twins_agreeing(space, off_a, off_b)} twins ({n} votes)")
    strong = {k[:2] for k, ids in list(m.pair_sets.items()) + list(m.twin_sets.items())
              if len(ids) >= 2}
    for (space, off), n in sorted(m.reads.items()):
        if (space, off) not in strong:
            lines.append(f"unmapped {space}+{off:#06x}  {n} reads")
    for p in m.pairings:
        if p.misaligned:
            lines.append(f"misaligned {p.a:#010x}/{p.b:#010x}: {p.misaligned}")
    text = "\n".join(lines) + "\n"
    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"{len(lines) - 1} rows written to {args.output}")
    else:
        sys.stdout.write(text)
    return 0


def command_check(args) -> int:
    games, inv = _inputs(args)
    page = args.page or README
    engine = read_engine_pairs(page)
    extra = read_pairs_file(args.extra_pairs) if args.extra_pairs else []
    rows = read_map_rows(page)
    if not rows:
        print(f"no map rows in {page}: nothing to check", file=sys.stderr)
        return 2
    m = derive(games, inv, extra, engine)
    bad = 0
    for r in rows:
        if ("unverified" in r.how or "layouts differ" in r.how
                or "read side by side" in r.how):
            print(f"skip   line {r.line}: {r.a} | {r.b} (hand-read: the tool cannot derive it)")
            continue
        offs, counts = r.offsets(), r.counts()
        if not offs:
            print(f"skip   line {r.line}: {r.a} | {r.b} (not a single offset row)")
            continue
        if len(offs) > 1:
            targets = {ob for _, _, cands in offs for ob in cands}
            got = {ob for space, oa, _ in offs for ob, p, t in
                   [(ob, m.pairs_agreeing(space, oa, ob), m.twins_agreeing(space, oa, ob))
                    for ob in targets] if p or t}
            missing = sorted(targets - got)
            if missing:
                print(f"FAIL   line {r.line}: {r.a} | {r.b}: no pair or twin reads "
                      + ", ".join(f"+{o:#x}" for o in missing) + " in that structure")
                bad += 1
            else:
                print(f"ok     line {r.line}: {r.a} | {r.b}: every component is read by a "
                      f"pair or a twin")
            continue
        for k, (space, oa, candidates) in enumerate(offs):
            want = counts[k] if k < len(counts) else (counts[0] if len(counts) == 1 else None)
            got = [(ob, m.pairs_agreeing(space, oa, ob), m.twins_agreeing(space, oa, ob))
                   for ob in candidates]
            best = max(got, key=lambda g: (g[1], g[2]))
            ok = (best[1] == want) if want is not None else bool(best[1] or best[2])
            if not ok and len(candidates) > 1:
                ok = any((p == want) if want is not None else bool(p or t) for _, p, t in got)
            if not ok:
                what = " or ".join(f"+{ob:#x} ({p} pairs, {t} twins)"
                                   for ob, p, t in got)
                print(f"FAIL   line {r.line}: {space}+{oa:#x} -> {what}: "
                      f"the page states {want if want is not None else 'a pair or a twin'}")
                bad += 1
            else:
                print(f"ok     line {r.line}: {space}+{oa:#x} -> +{best[0]:#x}: "
                      f"{best[1]} pairs, {best[2]} twin votes")
    for p in m.pairings:
        if p.misaligned:
            print(f"note   pair {p.a:#010x}/{p.b:#010x} is misaligned ({p.misaligned}); "
                  f"its votes are not counted")
    print(f"{len(rows)} rows checked, {bad} failed")
    return 0 if bad == 0 else 1


def _inputs(args):
    a_name, b_name = args.game_a or "mh3u", args.game_b or "mh4u"
    import monster_actions as ma
    games = {
        "a": load_game(a_name, args.a_exheader, args.a_code, *args.a_range),
        "b": load_game(b_name, args.b_exheader, args.b_code, *args.b_range),
    }
    inv = {"a": ma.read_inventory(args.a_inv), "b": ma.read_inventory(args.b_inv)}
    return games, inv


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="Addresses, offsets and counts only; keep the inventories and any output "
               "outside the repository.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (
        ("map", command_map, "print the field correspondences the handler pairs and the "
                             "engine twins support, with each row's count"),
        ("check", command_check, "re-derive reference/README.md's map rows and fail where a "
                                 "row's stated pair count disagrees with the code"),
    ):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--a-inv", required=True, help="game A's inventory (monster_actions.py list)")
        p.add_argument("--b-inv", required=True, help="game B's inventory")
        p.add_argument("--a-exheader", required=True)
        p.add_argument("--a-code", required=True, help="game A's code.bin")
        p.add_argument("--a-range", type=lambda s: int(s, 0), nargs=2, required=True,
                       metavar=("LO", "HI"), help="game A's monster code")
        p.add_argument("--b-exheader", required=True)
        p.add_argument("--b-code", required=True)
        p.add_argument("--b-range", type=lambda s: int(s, 0), nargs=2, required=True,
                       metavar=("LO", "HI"))
        p.add_argument("--game-a", default="mh3u", help="mh3u (default), mh4u or mhxx")
        p.add_argument("--game-b", default="mh4u")
        p.add_argument("--extra-pairs", metavar="FILE",
                       help="handler pairs read by hand to add: `3U 4U` per line (e.g. the "
                            "base handlers; the page's hand-read rows are marked)")
        p.add_argument("--page", default=README,
                       help="the page holding the engine-pair table (default: README.md)")
        if name == "map":
            p.add_argument("-o", "--output")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
