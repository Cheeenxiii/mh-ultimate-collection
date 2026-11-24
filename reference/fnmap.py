#!/usr/bin/env python3
"""Map functions between two games' code (or a game and a CRO module): which function of
game B is game A's function X.

Each side is the recompiler's analysis of that code (tools/recomp/analysis.py): exact
function bodies, jump tables resolved, call targets. Every function becomes a sequence of
normalised instruction tokens (mnemonic and operand kinds; registers, immediates and
addresses dropped, since compilers and struct layouts differ between games) and its call
sites (token index, callee).

The map grows in four ways, each measured on MH4U against MH3U and MHXX (the monster-port
design doc in the content repository has the numbers):
  1. anchors: functions whose token sequence is unique in both games and identical;
  2. propagation: in a mapped pair, calls at aligned positions map their callees,
     when the votes agree and the callees look alike (ratio >= 0.4);
  3. vtable slots, on request: the slots of a class both games name (reference/mt_vtables.py),
     aligned in order, map their functions when they look alike (ratio >= 0.6);
     then slots bracketed by mapped slots at equal distances in both games map by position;
  4. similarity, on request: the best candidate by a 4-gram index and alignment ratio,
     accepted only when clear (ratio >= 0.7 and 0.1 ahead of the next), then 2 again.

    side  --game mh4u|mh3u|mhxx [--module x.cro --crs static.crs] [--entries FILE] -o x.side
    map   A.side B.side -o map.tsv [--vtables A.vt B.vt] [--similar ADDR_FILE]
          [--module-side M.side] [--seed PAIRS]

The .side files and the map hold addresses and hashes only, but they are derived from game
code: keep them outside the repository.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import hashlib
import itertools
import os
import pickle
import struct
import sys
import zlib
from array import array
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fork  # noqa: E402,F401  (the fork's tools on sys.path)

import games  # noqa: E402

ANCHOR_MIN = 12          # tokens; shorter identical functions are too common to trust
PROPAGATE_MIN = 0.5      # ratio a non-identical pair needs before its calls vote
CALLEE_MIN = 0.4         # ratio a proposed callee pair needs
CLEAR_MIN, CLEAR_MARGIN = 0.7, 0.1
SLOT_MIN = 0.6           # ratio an aligned vtable slot pair needs (unless both are mapped already)
BRACKET_MIN = 0.3        # ratio a slot pair placed by position alone needs
NGRAM = 4
VENEER = 0xE51FF004      # ldr pc, [pc, #-4]: a CRO's jump to the word after it


# ── tokens ───────────────────────────────────────────────────────────────────

def tokens(img: bytes, base: int, mode: str, insns: list[int]) -> list[tuple[str, int | None]]:
    """(token, branch or call target) per instruction, in address order."""
    from capstone import CS_ARCH_ARM, CS_MODE_ARM, CS_MODE_THUMB, Cs
    from capstone.arm import (
        ARM_GRP_CALL,
        ARM_GRP_JUMP,
        ARM_OP_FP,
        ARM_OP_IMM,
        ARM_OP_MEM,
        ARM_OP_REG,
        ARM_REG_PC,
        ARM_REG_SP,
    )
    md = _md.get(mode)
    if md is None:
        md = _md[mode] = Cs(CS_ARCH_ARM, CS_MODE_THUMB if mode == "thumb" else CS_MODE_ARM)
        md.detail = True
    out: list[tuple[str, int | None]] = []
    for a in insns:
        i = next(md.disasm(img[a - base:a - base + 4], a, 1), None)
        if i is None:
            out.append(("?", None))
            continue
        target = i.operands[-1].imm if i.operands and i.operands[-1].type == ARM_OP_IMM else None
        if i.group(ARM_GRP_CALL) and target is not None:
            out.append(("CALL", target))
            continue
        if i.group(ARM_GRP_JUMP):
            out.append(("J" + i.mnemonic[1:], target))
            continue
        ops = []
        for o in i.operands:
            if o.type == ARM_OP_REG:
                name = i.reg_name(o.reg)
                ops.append(name if name in ("sp", "lr", "pc") else "r")
            elif o.type == ARM_OP_IMM:
                ops.append("#")
            elif o.type == ARM_OP_MEM:
                ops.append("[pc]" if o.mem.base == ARM_REG_PC else "[sp]" if o.mem.base == ARM_REG_SP else "[r]")
            elif o.type == ARM_OP_FP:
                ops.append("#f")
            else:
                ops.append("?")
        out.append((i.mnemonic + " " + ",".join(ops), None))
    return out


_md: dict = {}


# ── one side ─────────────────────────────────────────────────────────────────

@dataclass
class Fn:
    seq: array                                   # token ids (CRC-32 of each token)
    sites: list[tuple[int, int]] = field(default_factory=list)  # (token index, callee entry)
    external: list[int] = field(default_factory=list)  # targets outside this side (a CRO's static calls)
    ext_sites: list[tuple[int, int]] = field(default_factory=list)  # the same, as (token index, target)

    @property
    def digest(self) -> str:
        return hashlib.sha1(self.seq.tobytes()).hexdigest()


@dataclass
class Side:
    name: str
    fns: dict[int, Fn]


def make_fn(toks: list[tuple[str, int | None]], entry: int, owner, external=None) -> Fn:
    """`owner(addr)` gives the function an address belongs to, or None (outside the side);
    `external(target)` may name the outside address a call target forwards to (a CRO veneer);
    it is asked first, since a veneer need not be an analysed function."""
    seq = array("I", (zlib.crc32(t.encode()) for t, _ in toks))
    sites, ext, ext_sites = [], [], []
    for k, (t, target) in enumerate(toks):
        if target is None:
            continue
        x = external(target & ~1) if external else None
        if x is not None:
            ext.append(x)
            ext_sites.append((k, x))
            continue
        o = owner(target)
        if o is not None and (t == "CALL" or o != entry):
            sites.append((k, o))
    return Fn(seq, sites, ext, ext_sites)


def side_from_analysis(name: str, funcs: dict, img: bytes, base: int, external=None) -> Side:
    """`funcs`: entry -> recomp Function. `external(entry)`: see make_fn."""
    import bisect
    starts = sorted(funcs)
    ends = {a: max(f.insns) for a, f in funcs.items() if f.insns}

    def owner(t: int) -> int | None:
        t &= ~1
        if t in funcs:
            return t
        i = bisect.bisect_right(starts, t) - 1
        if i >= 0 and starts[i] in ends and t <= ends[starts[i]] + 3:
            return starts[i]
        return None

    fns = {a: make_fn(tokens(img, base, f.mode, sorted(f.insns)), a, owner, external) for a, f in funcs.items()}
    return Side(name, fns)


def save_side(side: Side, path: str) -> None:
    """Plain data only, so any script can load it (not just this one run as __main__)."""
    data = {"name": side.name,
            "fns": {a: (f.seq.tobytes(), f.sites, f.external, f.ext_sites) for a, f in side.fns.items()}}
    with open(path, "wb") as fh:
        pickle.dump(data, fh, protocol=4)


def load_side(path: str) -> Side:
    with open(path, "rb") as fh:
        data = pickle.load(fh)
    fns = {}
    for a, (seq, sites, ext, *rest) in data["fns"].items():   # sides saved before ext_sites have 3
        arr = array("I")
        arr.frombytes(seq)
        fns[a] = Fn(arr, list(sites), list(ext), list(rest[0]) if rest else [])
    return Side(data["name"], fns)


def merge_module(static: Side, module: Side) -> Side:
    """One side for a game's static code and a CRO module loaded with it: the module's calls
    into the static code (its veneers' targets) become call sites, so propagation from a
    mapped module function reaches the static functions it imports."""
    fns = dict(static.fns)
    for a, f in module.fns.items():
        sites = sorted(f.sites + [(k, x) for k, x in f.ext_sites if x in static.fns])
        fns[a] = Fn(f.seq, sites, f.external, f.ext_sites)
    return Side(f"{static.name}+{module.name}", fns)


def read_entries(path: str) -> dict[int, str]:
    """More function entries: one address per line (bit 0 set for Thumb), `#` comments."""
    out = {}
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if line:
                a = int(line.split()[0], 16)
                out.setdefault(a & ~1, "thumb" if a & 1 else "arm")
    return out


def read_pairs(path: str) -> list[tuple[int, int]]:
    """Seed pairs, one `A-address B-address` per line (a map's own format works)."""
    out = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if p and not line.startswith("#"):
                out.append((int(p[0], 16), int(p[1], 16)))
    return out


# ── matching ─────────────────────────────────────────────────────────────────

def ratio(a: array, b: array) -> tuple[float, difflib.SequenceMatcher | None]:
    la, lb = len(a), len(b)
    if not la or not lb or min(la, lb) / max(la, lb) < 0.5:
        return 0.0, None
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.quick_ratio() < CALLEE_MIN:
        return 0.0, None
    return sm.ratio(), sm


class Mapper:
    def __init__(self, a: Side, b: Side):
        self.a, self.b = a, b
        self.m: dict[int, int] = {}
        self.r: dict[int, int] = {}
        self.how: dict[int, str] = {}
        self._done: set[tuple[int, int]] = set()
        self._ratios: dict[tuple[int, int], float] = {}

    def add(self, x: int, y: int, how: str) -> None:
        self.m[x], self.r[y], self.how[x] = y, x, how

    def anchors(self) -> int:
        def uniq(side: Side) -> dict[str, int]:
            c = collections.Counter(f.digest for f in side.fns.values() if len(f.seq) >= ANCHOR_MIN)
            return {f.digest: a for a, f in side.fns.items() if len(f.seq) >= ANCHOR_MIN and c[f.digest] == 1}
        ua, ub = uniq(self.a), uniq(self.b)
        n = 0
        for h in ua.keys() & ub.keys():
            if ua[h] not in self.m and ub[h] not in self.r:
                self.add(ua[h], ub[h], "identical")
                n += 1
        return n

    def _votes(self, pairs) -> dict[int, collections.Counter]:
        votes: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
        for x, y in pairs:
            if (x, y) in self._done:
                continue
            self._done.add((x, y))
            fa, fb = self.a.fns[x], self.b.fns[y]
            if fa.seq == fb.seq:
                if len(fa.sites) == len(fb.sites):
                    for (_, ca), (_, cb) in zip(fa.sites, fb.sites, strict=False):
                        votes[ca][cb] += 2
                continue
            r, sm = ratio(fa.seq, fb.seq)
            if sm is None or r < PROPAGATE_MIN:
                continue
            da, db = dict(fa.sites), dict(fb.sites)
            for tag, i1, i2, j1, _j2 in sm.get_opcodes():
                if tag == "equal":
                    for k in range(i2 - i1):
                        if i1 + k in da and j1 + k in db:
                            votes[da[i1 + k]][db[j1 + k]] += 1
        return votes

    def propagate(self, rounds: int = 20) -> int:
        total = 0
        for _rnd in range(rounds):
            new = 0
            for ca, cnt in self._votes(list(self.m.items())).items():
                if ca in self.m or ca not in self.a.fns:
                    continue
                (cb, n), *rest = cnt.most_common()
                if cb in self.r or cb not in self.b.fns or (rest and rest[0][1] * 2 > n):
                    continue
                fa, fb = self.a.fns[ca], self.b.fns[cb]
                r = 1.0 if fa.seq == fb.seq else ratio(fa.seq, fb.seq)[0]
                if r >= CALLEE_MIN:
                    self.add(ca, cb, f"call {r:.2f}")
                    new += 1
            total += new
            if not new:
                break
        return total

    def _r(self, x: int, y: int) -> float:
        key = (x, y)
        r = self._ratios.get(key)
        if r is None:
            fa, fb = self.a.fns.get(x), self.b.fns.get(y)
            r = 0.0 if fa is None or fb is None else 1.0 if fa.seq == fb.seq else ratio(fa.seq, fb.seq)[0]
            self._ratios[key] = r
        return r

    def align_slots(self, sa: list[int], sb: list[int]) -> list[tuple[int, int, float]]:
        """Pairs of slots of one class's vtables in the two games, aligned in order
        (slots get added and dropped between versions); only pairs that score."""
        def score(x, y):
            if not x or not y:
                return 0.3 if x == y else -0.3          # empty slots line up too
            if x in self.m:
                return 1.0 if self.m[x] == y else -1.0
            if y in self.r:
                return -1.0
            return self._r(x, y) - 0.5
        n, k = len(sa), len(sb)
        best = [[0.0] * (k + 1) for _ in range(n + 1)]
        for i in range(n):
            row, nxt = best[i], best[i + 1]
            for j in range(k):
                nxt[j + 1] = max(row[j] + score(sa[i], sb[j]), row[j + 1], nxt[j])
        out, i, j = [], n, k
        while i and j:
            sc = score(sa[i - 1], sb[j - 1])
            if best[i][j] == best[i - 1][j - 1] + sc and sc > 0:
                if sa[i - 1] and sb[j - 1]:
                    out.append((sa[i - 1], sb[j - 1], sc))
                i, j = i - 1, j - 1
            elif best[i][j] == best[i - 1][j]:
                i -= 1
            else:
                j -= 1
        return out

    def vtables(self, pairs: list[tuple[list[int], list[int]]]) -> int:
        """Map the slots of vtables known to belong to the same class in both games
        (mt_vtables.py; classes paired by name). A slot function inherited by many
        classes collects a vote from each; the clear winner is taken, at SLOT_MIN."""
        votes: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
        for sa, sb in _even(pairs):
            for x, y, _ in self.align_slots(sa, sb):
                if x not in self.m:
                    votes[x][y] += 1
        n = 0
        for x, cnt in votes.items():
            (y, c), *rest = cnt.most_common()
            if y in self.r or (rest and rest[0][1] * 2 > c) or self._r(x, y) < SLOT_MIN:
                continue
            self.add(x, y, f"slot {self._r(x, y):.2f}")
            n += 1
        return n

    def brackets(self, pairs: list[tuple[list[int], list[int]]]) -> int:
        """An unmapped slot between two mapped slots of the same class, whose gap is the
        same size in both games, takes the slot at the same offset: position alone, for
        functions rewritten past recognition (leave-one-out on mapped slots: 97.8% right
        against MHXX, 99.5% against MH3U). Lengths must be within a factor of 3, and the
        pair must still look a little alike (BRACKET_MIN): an inherited slot in one game
        against an override in the other is the same slot, not the same function."""
        votes: dict[int, collections.Counter] = collections.defaultdict(collections.Counter)
        for sa, sb in _even(pairs):
            pos = {}
            for i, x in enumerate(sa):
                y = self.m.get(x) if x else None
                js = [j for j, z in enumerate(sb) if y is not None and z == y]
                if len(js) == 1:
                    pos[i] = js[0]
            keys = sorted(pos)
            for i0, i1 in itertools.pairwise(keys):
                if pos[i1] - pos[i0] != i1 - i0:
                    continue
                for i in range(i0 + 1, i1):
                    x, y = sa[i], sb[pos[i0] + i - i0]
                    if x and y and x not in self.m and y not in self.r:
                        votes[x][y] += 1
        n = 0
        for x, cnt in votes.items():
            (y, _), *rest = cnt.most_common()
            if rest or y in self.r or x not in self.a.fns or y not in self.b.fns:
                continue
            la, lb = len(self.a.fns[x].seq), len(self.b.fns[y].seq)
            if 3 * min(la, lb) < max(la, lb) or self._r(x, y) < BRACKET_MIN:
                continue
            self.add(x, y, f"bracket {self._r(x, y):.2f}")
            n += 1
        return n

    def similar(self, wanted: list[int]) -> int:
        """Clear best matches for the given unmapped functions of side A, then propagation."""
        index = NgramIndex(self.b)
        n = 0
        for x in wanted:
            if x in self.m or x not in self.a.fns or len(self.a.fns[x].seq) < 6:
                continue
            best = index.query(self.a.fns[x].seq, 2)
            if is_clear(best) and best[0][1] not in self.r:
                self.add(x, best[0][1], f"similar {best[0][0]:.2f}")
                n += 1
        return n + self.propagate()


def _even(pairs):
    """Slots as function entries: the Thumb bit dropped."""
    return [([x & ~1 for x in sa], [y & ~1 for y in sb]) for sa, sb in pairs]


def is_clear(best: list[tuple[float, int]]) -> bool:
    return bool(best) and best[0][0] >= CLEAR_MIN and (len(best) < 2 or best[0][0] - best[1][0] >= CLEAR_MARGIN)


class NgramIndex:
    def __init__(self, side: Side, min_len: int = 6, max_df: int = 400):
        self.side, self.max_df = side, max_df
        self.inv: dict[int, list[int]] = collections.defaultdict(list)
        self.grams: dict[int, set[int]] = {}
        for a, f in side.fns.items():
            if len(f.seq) >= min_len:
                g = self.grams[a] = _grams(f.seq)
                for x in g:
                    self.inv[x].append(a)

    def query(self, seq: array, k: int = 3) -> list[tuple[float, int]]:
        g = _grams(seq)
        cnt: collections.Counter = collections.Counter()
        for x in g:
            lst = self.inv.get(x)
            if lst and len(lst) <= self.max_df:
                cnt.update(lst)
        short = sorted(((c / len(g | self.grams[a]), a) for a, c in cnt.most_common(40)), reverse=True)[:15]
        scored = sorted(((difflib.SequenceMatcher(None, seq, self.side.fns[a].seq, autojunk=False).ratio(), a)
                         for _, a in short), reverse=True)
        return scored[:k]


def _grams(seq: array) -> set[int]:
    return {hash(tuple(seq[i:i + NGRAM])) for i in range(len(seq) - NGRAM + 1)}


# ── command line ─────────────────────────────────────────────────────────────

def _analyse(img, entries, data_segs):
    import recompile as R
    from recomp.analysis import Analyzer
    an = Analyzer(img)
    if data_segs:
        extra = R.data_pointer_closure(img, an, data_segs, an.analyze_all(entries))
        entries = {**entries, **extra}
    return an.analyze_all(entries)


def cmd_side(args) -> int:
    import codebin2elf
    import cro as crolib
    import exheader as exh
    import recompile as R
    from recomp.analysis import Image
    if args.module:
        with open(args.crs, "rb") as f:
            crs = crolib.Cro(f.read())
        with open(args.module, "rb") as f:
            ld = crolib.load(f.read(), 0x02000000, crolib.static_segments(crs))
        lo, hi = ld.text
        img = Image(ld.image, ld.base, hi - ld.base)
        entries = crolib.entry_points(ld, crs)
        for a, m in read_entries(args.entries).items() if args.entries else ():
            entries.setdefault(a, m)
        funcs = _analyse(img, entries, ld.data_segments())

        def veneer(t):                      # ldr pc, [pc, #-4]; .word static
            off = t - ld.base
            if lo <= t < hi - 4 and not t & 3:
                w, lit = struct.unpack_from("<2I", ld.image, off)
                if w == VENEER and not lo <= lit & ~1 < hi:
                    return lit & ~1
            return None
        side = side_from_analysis(ld.cro.name, funcs, ld.image, ld.base, veneer)
    else:
        ns = argparse.Namespace(game="" if args.game == "mh4u" else args.game, exheader=args.exheader,
                                code=args.code, functions=None, extra=None, hooks=None, tunables=None,
                                out=None)
        game = games.resolve_args(ns)            # the same tables a recompile of that game uses
        with open(ns.exheader, "rb") as f:
            header = exh.parse(f.read())
        with open(ns.code, "rb") as f:
            code = codebin2elf.load_code(header, f.read())
        if game:
            games.check_game_code(game, code)
        img = Image(code, header.text.address, R.code_size(header, code))
        entries = R.load_entries(ns.functions, ns.extra or [])
        for a, m in read_entries(args.entries).items() if args.entries else ():
            entries.setdefault(a, m)
        entries.update({a: m for a, m in R.init_array_entries(img).items() if a not in entries})
        entries = {a: m for a, m in entries.items() if img.in_text(a)}
        segs = [(header.ro.address, header.ro.size), (header.data.address, header.data.size)]
        funcs = _analyse(img, entries, segs)
        side = side_from_analysis(args.game, funcs, code, header.text.address)
    save_side(side, args.output)
    print(f"{side.name}: {len(side.fns)} functions")
    return 0


def cmd_map(args) -> int:
    a, b = load_side(args.a), load_side(args.b)
    if args.module_side:
        b = merge_module(b, load_side(args.module_side))
    mp = Mapper(a, b)
    if args.seed:
        seeds = [(x, y) for x, y in read_pairs(args.seed) if x in a.fns and y in b.fns]
        for x, y in seeds:
            if x not in mp.m and y not in mp.r:
                mp.add(x, y, "seed")
        print(f"seeds: {len(seeds)}")
    print(f"anchors: {mp.anchors()}")
    if args.vtables:
        import mt_vtables
        va, vb = (mt_vtables.read_tsv(p) for p in args.vtables)
        names = [(n, n) for n in sorted(va.keys() & vb.keys())]
        names += [tuple(p.split("=", 1)) for p in args.class_pair]
        pairs = [(va[x].slots, vb[y].slots) for x, y in names
                 if x in va and y in vb and va[x].slots and vb[y].slots]
        print(f"vtable slots ({len(pairs)} classes): {mp.vtables(pairs)}")
        print(f"propagated: {mp.propagate()}")
        print(f"bracketed slots: {mp.brackets(pairs)}")
    print(f"propagated: {mp.propagate()}")
    if args.similar:
        with open(args.similar) as f:
            wanted = [int(x.split()[0], 16) for x in f if x.strip() and not x.startswith("#")]
        print(f"similar (and their propagation): {mp.similar(wanted)}")
    with open(args.output, "w") as f:
        f.write(f"# {a.name}\t{b.name}\thow\n")
        f.writelines(f"0x{x:08x}\t0x{mp.m[x]:08x}\t{mp.how[x]}\n" for x in sorted(mp.m))
    print(f"total: {len(mp.m)} -> {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("side", help="analyse one game's code (or one CRO module)")
    p.add_argument("--game", default="mh4u", help="mh4u, or a reference game in games/")
    p.add_argument("--exheader")
    p.add_argument("--code")
    p.add_argument("--module", help="a .cro module instead of code.bin")
    p.add_argument("--crs", help="the game's static.crs (with --module)")
    p.add_argument("--entries", help="more function entries, one address per line (code only "
                   "tail calls reach, such as a monster's action handlers)")
    p.add_argument("-o", "--output", required=True)
    p = sub.add_parser("map", help="map side A's functions to side B's")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--similar", help="file of side-A addresses to also match by similarity")
    p.add_argument("--module-side", help="a CRO module's side, merged into B (B is its game's static side)")
    p.add_argument("--seed", help="pairs known by other means (A B per line), added before anything else")
    p.add_argument("--vtables", nargs=2, metavar=("A.vt", "B.vt"),
                   help="mt_vtables.py output for each side: align the slots of same-named classes")
    p.add_argument("--class-pair", action="append", default=[], metavar="A=B",
                   help="with --vtables, also align class A's slots with class B's")
    p.add_argument("-o", "--output", required=True)
    args = ap.parse_args(argv)
    return cmd_side(args) if args.cmd == "side" else cmd_map(args)


if __name__ == "__main__":
    sys.exit(main())
