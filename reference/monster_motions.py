#!/usr/bin/env python3
"""Which motion (animation) index each of a monster's action handlers starts, and how two
games' action ids compare.

A monster's current action is a category and an index byte. The dispatcher (the address
`monster_actions.py` walks) reaches a handler per action id, and the handler starts an
animation by calling the game's motion-start wrapper with the motion index in r1:

    MH4U  0x0094e318   `mov r2,#0; b 0x0091908c`
    MHXX  0x008eb108   `mov r2,#0; b 0x008b393c`
    MH3U  0x00828828   tail-calls 0x0083771c, which sets the model's motion

The wrappers are engine functions of the base enemy class, so one address serves every
monster of that game; `--motion` overrides it. The action ids being the same, the indices
can be compared: the same action should start the same animation.

    list    --game mh4u|mh3u|mhxx ... --dispatcher ADDR [--motion ADDR] [--functions TSV] -o x.tsv
    compare A.tsv B.tsv [--values]

`list` takes the same code arguments as monster_actions.py: --exheader/--code/--range for
MH4U and MH3U, --module/--crs/--base for a MHXX CRO module. It writes one row per action
(`cat idx handler motion how`), where `how` is `constant`, `computed` (the wrapper is called
but its index is not a constant), `none` (no call) or `no-handler` (the action's work is
inline). `compare` counts the common ids that start the same index and lists the ones that
differ, plus the counts that could not be compared and why. With `--game-a`/`--lmt-a` and
`--game-b`/`--lmt-b` it also compares the motions themselves: a motion index packs its LMT
file and animation slot (MH4U and MHXX `file << 8 | slot`, MH3U `file * 100 + slot`), and the
animation's frame count, loop frame and track count are its signature. The output splits the
differing ids into same motion at another index (equal signature, or the signature found
elsewhere in the other game), different motion, and no animation at the decoded index;
`--mapping` writes the per-id mapping.

The output holds motion indices read from the games' code: keep the TSVs outside the
repository (reference/README.md; CLAUDE.md rule 1).
"""
from __future__ import annotations

import argparse
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# The wrapper a handler calls to start an animation, per game. Why these: docs/checks.md, R1.
MOTION = {"mh4u": 0x0094E318, "mhxx": 0x008EB108, "mh3u": 0x00828828}
SCAN_CAP = 0x600              # a handler block's extent, when no function table bounds it
MAX_MOTION = 0x2000           # indices above this are a register we didn't follow, not a motion
HEADER = "# cat\tidx\thandler\tmotion\thow\n"


def functions_table(path: str) -> dict[int, int]:
    """address -> size from a tools/build_function_table.py TSV."""
    out = {}
    with open(path) as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            p = line.split("\t")
            if not p[0].startswith("0x"):
                continue
            out[int(p[0], 16)] = int(p[1], 16)
    return out


def default_functions(game: str) -> str:
    import fork

    if game == "mh4u":
        return os.path.join(fork.ROOT, "config", "functions.tsv")
    return os.path.join(fork.HERE, "games", game, "functions.tsv")


def load(args):
    """(code, function table or None, module entry addresses or None)."""
    import monster_actions

    if args.module:
        import cro as crolib
        with open(args.crs, "rb") as f:
            crs = crolib.Cro(f.read())
        with open(args.module, "rb") as f:
            loaded = crolib.load(f.read(), args.base, crolib.static_segments(crs))
        lo, hi = loaded.text
        code = monster_actions.Code(loaded.image, loaded.base, *(args.range or (lo, hi)))
        return code, None, set(crolib.entry_points(loaded, crs))
    code = monster_actions.load_code(args)
    return code, functions_table(args.functions or default_functions(args.game)), None


def block_end(handler: int, table, entries) -> int:
    """Where the handler's code can stop: its own function, else the enclosing one's end."""
    if entries is not None:
        after = [a for a in entries if a > handler]
        return min(min(after) if after else handler + SCAN_CAP, handler + SCAN_CAP)
    if handler in table:
        return handler + table[handler]
    start = max([a for a in table if a <= handler] or [handler])
    end = start + table.get(start, 0)
    if end <= handler:
        end = handler + SCAN_CAP
    return min(end, handler + SCAN_CAP)


CONDITIONS = ("eq", "ne", "cs", "hs", "cc", "lo", "mi", "pl", "vs", "vc",
              "hi", "ls", "ge", "lt", "gt", "le", "al")
MOVES = ("mov", "movs", "movw")


def conditionless(mnemonic: str) -> str:
    """`ldreq` -> `ldr`, `blne` -> `bl`: the condition doesn't change which register is set."""
    if mnemonic in MOVES + ("ldr", "bl", "b"):
        return mnemonic
    for c in CONDITIONS:
        if mnemonic.endswith(c):
            return mnemonic[:-len(c)]
    return mnemonic


def insns_through(code, start: int, end: int):
    """Instructions from `start` to `end`, stepping over words that aren't code (jump tables,
    literal pools): a linear disassembly stops at the first one and misses the handler's
    case blocks after it."""
    from capstone import CS_ARCH_ARM, CS_MODE_ARM, Cs
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    addr = start
    while addr < end:
        one = list(md.disasm(code.data[addr - code.base:addr - code.base + 4], addr))
        if not one:
            addr += 4
            continue
        yield one[0]
        addr = one[0].address + one[0].size


def motion_for(code, handler, table, entries, motion: int) -> dict:
    """The first constant index `handler` passes to the motion wrapper, or why there is none."""
    from capstone.arm import ARM_OP_IMM, ARM_OP_MEM, ARM_OP_REG, ARM_REG_PC

    if handler is None:
        return dict(motion=None, how="no-handler")
    end = block_end(handler, table, entries)
    regs: dict[str, int | None] = {}
    called = False
    for i in insns_through(code, handler, min(end, handler + SCAN_CAP)):
        mn = conditionless(i.mnemonic)
        if mn in MOVES and len(i.operands) == 2 and i.operands[0].type == ARM_OP_REG:
            rd = i.reg_name(i.operands[0].reg)
            src = i.operands[1]
            if src.type == ARM_OP_IMM:
                regs[rd] = src.imm
            elif src.type == ARM_OP_REG:
                regs[rd] = regs.get(i.reg_name(src.reg))
        elif mn == "ldr" and len(i.operands) == 2 and i.operands[0].type == ARM_OP_REG:
            mem = i.operands[1]
            if mem.type == ARM_OP_MEM and mem.mem.base == ARM_REG_PC:   # [pc, #imm]
                pc = (i.address + 8) & ~3
                regs[i.reg_name(i.operands[0].reg)] = code.word(pc + mem.mem.disp)
        elif mn in ("bl", "b") and i.operands and i.operands[0].type == ARM_OP_IMM:
            target = code.veneer(i.operands[0].imm) or i.operands[0].imm
            if target == motion:
                called = True
                index = regs.get("r1")
                if isinstance(index, int) and 0 < index < MAX_MOTION:
                    return dict(motion=index, how="constant")
            if mn == "bl":
                for r in ("r0", "r1", "r2", "r3"):
                    regs.pop(r, None)
    return dict(motion=None, how="computed" if called else "none")


def cmd_list(args) -> int:
    import monster_actions

    code, table, entries = load(args)
    actions = monster_actions.inventory(code, args.dispatcher)
    if entries is not None:
        entries |= {a.handler for a in actions if a.handler}
        entries |= {a.fn for a in actions if a.fn}
    rows = []
    for a in actions:
        handler = a.handler if a.kind == "tail" else None
        m = motion_for(code, handler, table, entries, args.motion or MOTION[args.game])
        rows.append((a.cat, a.idx, handler, m["motion"], m["how"]))
    with open(args.output, "w") as f:
        f.write(HEADER)
        for cat, idx, handler, motion, how in rows:
            f.write(f"{cat}\t{'' if idx is None else idx}\t"
                    f"{'' if handler is None else f'0x{handler:08x}'}\t"
                    f"{'' if motion is None else motion}\t{how}\n")
    counts = collections.Counter(x[4] for x in rows)
    print(f"{len(rows)} actions: " + ", ".join(f"{k} {n}" for k, n in counts.most_common()))
    return 0


def decode_motion(game: str, motion: int) -> tuple[int, int]:
    """A motion index's (LMT file, animation slot): MH3U packs file*100+slot, MH4U/MHXX file<<8|slot."""
    if game == "mh3u":
        return motion // 100, motion % 100
    return motion >> 8, motion & 0xFF


def read_lmt(data: bytes) -> list[tuple[int, int, int] | None]:
    """Each animation's (frames, loop frame, track count). The MH3U version-66 files use the
    same animation header and track table as version 67 for this comparison (specs/lmt.md)."""
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
    from mhuc.formats import lmt

    if data[:4] != b"LMT\0":
        raise ValueError("not an LMT")
    version, count = struct.unpack_from("<HH", data, 4)
    if version not in (66, 67):
        raise ValueError(f"LMT version {version}: only 66 and 67 are read")
    out = []
    for offset in struct.unpack_from(f"<{count}I", data, 8):
        if not offset:
            out.append(None)
            continue
        lmt._in(data, offset, lmt.ANIM)
        tr, tc, frames, loop = struct.unpack_from("<IIii", data, offset)
        if tc:
            lmt._in(data, tr, lmt.TRACK * tc)
        out.append((frames, loop, tc))
    return out


def same_motion(a: tuple[int, int, int], b: tuple[int, int, int]) -> bool:
    """The same animation: same frames and loop, and the same track count or one more on
    MH4U's side (its skeleton has one fewer bone; specs/mod.md)."""
    return a[:2] == b[:2] and abs(a[2] - b[2]) <= 1


def content_split(a: dict, b: dict, game_a: str, lmts_a, game_b: str, lmts_b) -> dict:
    """How the differing ids' motions compare, with their animation signatures."""
    index_a = {}
    for fi, anims in enumerate(lmts_a):
        for slot, sig in enumerate(anims):
            if sig:
                index_a.setdefault(sig, []).append((fi, slot))
    same, same_track, elsewhere, different, unresolved, ambiguous = [], [], [], [], [], []
    for key in sorted(set(a) & set(b)):
        if a[key]["how"] != "constant" or b[key]["how"] != "constant":
            continue
        if a[key]["motion"] == b[key]["motion"]:
            continue
        fa, sa = decode_motion(game_a, a[key]["motion"])
        fb, sb = decode_motion(game_b, b[key]["motion"])
        xa = lmts_a[fa][sa] if fa < len(lmts_a) and sa < len(lmts_a[fa]) else None
        xb = lmts_b[fb][sb] if fb < len(lmts_b) and sb < len(lmts_b[fb]) else None
        if xa is None or xb is None:
            hits = index_a.get(xb, []) if xb is not None else []
            if len(hits) == 1:
                elsewhere.append((key, a[key]["motion"], b[key]["motion"], xb))
            elif len(hits) > 1:
                ambiguous.append((key, a[key]["motion"], b[key]["motion"], xb))
            else:
                unresolved.append((key, a[key]["motion"], b[key]["motion"], xa, xb))
        elif xa == xb:
            same.append((key, a[key]["motion"], b[key]["motion"], xa))
        elif same_motion(xa, xb):
            same_track.append((key, a[key]["motion"], b[key]["motion"], xa, xb))
        else:
            different.append((key, a[key]["motion"], b[key]["motion"], xa, xb))
    return dict(same=same, same_track=same_track, elsewhere=elsewhere, different=different,
                unresolved=unresolved + ambiguous, ambiguous=ambiguous)


def read_rows(path: str) -> dict[tuple[int, int | None], dict]:
    out = {}
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            cat, idx, _, motion, how = line.rstrip("\n").split("\t")
            out[(int(cat), int(idx) if idx else None)] = dict(
                motion=int(motion) if motion else None, how=how)
    return out


def compare(a: dict, b: dict) -> dict:
    """Counts for two inventories: common ids, same and different motion, and why not compared."""
    common = sorted(set(a) & set(b))
    same, different, skipped = [], [], collections.Counter()
    for key in common:
        x, y = a[key], b[key]
        if x["how"] != "constant" or y["how"] != "constant":
            skipped[(x["how"], y["how"])] += 1
        elif x["motion"] == y["motion"]:
            same.append(key)
        else:
            different.append(key)
    return dict(common=len(common), same=same, different=different, skipped=skipped)


def fmt_id(key: tuple[int, int | None]) -> str:
    cat, idx = key
    return str(cat) if idx is None else f"{cat}/{idx}"


def fmt_ids(ids, per_line: int = 10) -> str:
    return "\n".join(" ".join(fmt_id(k) for k in ids[k:k + per_line])
                     for k in range(0, len(ids), per_line)) or "none"


def cmd_compare(args) -> int:
    a, b = read_rows(args.a), read_rows(args.b)
    r = compare(a, b)
    compared = len(r["same"]) + len(r["different"])
    print(f"common {r['common']}, compared {compared}, same {len(r['same'])}, "
          f"different {len(r['different'])}, not compared {sum(r['skipped'].values())}")
    if r["skipped"]:
        print("not compared: " + ", ".join(f"{x}/{y} {n}" for (x, y), n in r["skipped"].most_common()))
    print("different ids:")
    print(fmt_ids(r["different"]))
    if args.values:
        for key in r["different"]:
            print(f"{fmt_id(key)} {a[key]['motion']} {b[key]['motion']}")
    if not (args.game_a or args.lmt_a or args.game_b or args.lmt_b):
        return 0
    if not (args.game_a and args.game_b and args.lmt_a and args.lmt_b):
        print("content comparison needs --game-a/--lmt-a and --game-b/--lmt-b", file=sys.stderr)
        return 2
    lmts_a = [read_lmt(open(path, "rb").read()) for path in args.lmt_a]
    lmts_b = [read_lmt(open(path, "rb").read()) for path in args.lmt_b]
    s = content_split(a, b, args.game_a, lmts_a, args.game_b, lmts_b)
    print(f"motions: same {len(s['same'])}, one track {len(s['same_track'])}, "
          f"found elsewhere {len(s['elsewhere'])}, different {len(s['different'])}, "
          f"not resolved {len(s['unresolved'])}")
    print("different motion ids:")
    print(fmt_ids([x[0] for x in s["different"]]))
    print("not resolved ids:")
    print(fmt_ids([x[0] for x in s["unresolved"]]))
    if args.mapping:
        with open(args.mapping, "w") as f:
            f.write("# cat\tidx\tmotion_a\tmotion_b\thow\tsignature_a\tsignature_b\n")
            def row(key, ma, mb, how, sa=None, sb=None):
                f.write(f"{key[0]}\t{'' if key[1] is None else key[1]}\t{ma}\t{mb}\t{how}\t"
                        f"{'' if sa is None else sa}\t{'' if sb is None else sb}\n")
            for key, ma, mb, sig in s["same"]:
                row(key, ma, mb, "same", sig, sig)
            for key, ma, mb, sa, sb in s["same_track"]:
                row(key, ma, mb, "same-track", sa, sb)
            for key, ma, mb, sig in s["elsewhere"]:
                row(key, ma, mb, "same-elsewhere", sig, sig)
            for key, ma, mb, sa, sb in s["different"]:
                row(key, ma, mb, "different", sa, sb)
            for item in s["unresolved"]:
                key, ma, mb = item[:3]
                row(key, ma, mb, "unresolved")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="the motion each of a monster's actions starts")
    p.add_argument("--game", required=True, choices=tuple(MOTION))
    p.add_argument("--exheader")
    p.add_argument("--code")
    p.add_argument("--module")
    p.add_argument("--crs")
    p.add_argument("--base", type=lambda s: int(s, 0), default=0x02000000, help="where the module is loaded")
    p.add_argument("--dispatcher", type=lambda s: int(s, 0), required=True)
    p.add_argument("--range", type=lambda s: int(s, 0), nargs=2, metavar=("LO", "HI"))
    p.add_argument("--motion", type=lambda s: int(s, 0), help="the motion-start wrapper (default: the game's)")
    p.add_argument("--functions", help="a functions.tsv; defaults to the game's table")
    p.add_argument("-o", "--output", required=True)
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("compare", help="count two inventories' common ids by motion")
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--values", action="store_true", help="also print the two indices")
    p.add_argument("--game-a", choices=tuple(MOTION))
    p.add_argument("--lmt-a", nargs="+", help="game A's LMT files, in file order")
    p.add_argument("--game-b", choices=tuple(MOTION))
    p.add_argument("--lmt-b", nargs="+", help="game B's LMT files, in file order")
    p.add_argument("--mapping", help="write the per-id motion mapping to this TSV")
    p.set_defaults(fn=cmd_compare)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
