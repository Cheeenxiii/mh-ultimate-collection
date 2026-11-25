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
    compare A.tsv B.tsv [--values] [--game-a/--lmt-a, --game-b/--lmt-b] [--mapping FILE]
    table   --mh4u A.tsv --source GAME B.tsv MAPPING [...] -o motions.h

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

`table` turns the comparison into the port's run-time translation
(reference/README.md, "A 3U Rathian's moves on MH4U's handlers"): from the two games'
inventories and `compare --mapping`'s per-id map, one table per ported monster in the
registry. An entry says: for this action id, MH4U's handler asks this motion number, and the
source game's animation sits at that index in the converted motion lists. The lists keep the
source game's grouping, so a source index is written in MH4U's packing (`file << 8 | slot`)
whatever the source game's packing was. The action ids the comparison cannot resolve
(`unresolved`, today category 7's computed index) are left out of the table and listed
separately; at run time those numbers pass through unchanged. A category-only action (the
game's category has one action, the index byte is unused) is keyed by category with index
0x100. The header holds action and motion numbers only and is checked in; its checker is
tools/check_motion_tables.py.

The output holds motion indices read from the games' code: keep the TSVs outside the
repository (reference/README.md; CLAUDE.md rule 1).
"""
from __future__ import annotations

import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

# The wrapper a handler calls to start an animation, per game. Why these: docs/checks.md, R1.
MOTION = {"mh4u": 0x0094E318, "mhxx": 0x008EB108, "mh3u": 0x00828828}
SCAN_CAP = 0x600              # a handler block's extent, when no function table bounds it
MAX_MOTION = 0x2000           # indices above this are a register we didn't follow, not a motion
HEADER = "# cat\tidx\thandler\tmotion\thow\n"
NO_INDEX = 0x100              # "the category has one action": the index byte is unused
GENERATOR = "reference/monster_motions.py table"


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
    """How the common ids' motions compare, with their animation signatures.

    `same_index` holds the ids whose two handlers start the same index; the rest split by
    content (`same`, `same_track`, `elsewhere`, `different`, `unresolved`, `ambiguous`). An
    `elsewhere` item also carries where in the source game's lists its signature was found."""
    index_a = {}
    for fi, anims in enumerate(lmts_a):
        for slot, sig in enumerate(anims):
            if sig:
                index_a.setdefault(sig, []).append((fi, slot))
    same, same_track, elsewhere, different, unresolved, ambiguous, same_index = (
        [], [], [], [], [], [], [])
    for key in sorted(set(a) & set(b)):
        if a[key]["how"] != "constant" or b[key]["how"] != "constant":
            continue
        if a[key]["motion"] == b[key]["motion"]:
            same_index.append((key, a[key]["motion"]))
            continue
        fa, sa = decode_motion(game_a, a[key]["motion"])
        fb, sb = decode_motion(game_b, b[key]["motion"])
        xa = lmts_a[fa][sa] if fa < len(lmts_a) and sa < len(lmts_a[fa]) else None
        xb = lmts_b[fb][sb] if fb < len(lmts_b) and sb < len(lmts_b[fb]) else None
        if xa is None or xb is None:
            hits = index_a.get(xb, []) if xb is not None else []
            if len(hits) == 1:
                elsewhere.append((key, a[key]["motion"], b[key]["motion"], xb, hits[0]))
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
                unresolved=unresolved + ambiguous, ambiguous=ambiguous, same_index=same_index)


def repack_motion(game: str, motion: int) -> int:
    """`motion`, an animation of `game`, as MH4U's motion start takes it.

    The converted motion lists keep the source game's grouping, so the LMT file keeps its
    position and the animation its slot; MH4U packs the index `file << 8 | slot`. MH3U's list
    groups are 000, 100, 200, ... (docs/checks.md, R1), so its group is its position."""
    file, slot = decode_motion(game, motion)
    return (file << 8) | slot


def read_mapping(path: str) -> list[dict]:
    """R1's per-id comparison, as `compare --mapping` writes it."""
    out = []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            cat, idx, motion_a, motion_b, how = line.rstrip("\n").split("\t")[:5]
            out.append(dict(cat=int(cat), idx=int(idx) if idx else None,
                            motion_a=int(motion_a) if motion_a else None,
                            motion_b=int(motion_b) if motion_b else None, how=how))
    return out


def table_index(key: tuple[int, int | None]) -> int:
    """The table's index field: the action's index byte, or NO_INDEX for a category-only action."""
    return NO_INDEX if key[1] is None else key[1]


def build_table(monster: dict, mh4u: dict, source: dict, mapping: list[dict],
                source_game: str) -> dict:
    """One ported monster's translations, the ids they leave out, and R1's counts.

    Refuses a mapping that doesn't match the inventories: every action id both handlers start
    a constant motion for is either in the mapping (their indices differ) or identical."""
    common = set(mh4u) & set(source)
    compared = sorted((k for k in common
                       if mh4u[k]["how"] == "constant" and source[k]["how"] == "constant"),
                      key=action_key)
    seen = {}
    for row in mapping:
        key = (row["cat"], row["idx"])
        if key in seen:
            raise ValueError(f"{monster['key']}: {fmt_id(key)} appears twice in the mapping")
        seen[key] = row
        if key not in compared:
            raise ValueError(f"{monster['key']}: the mapping has {fmt_id(key)}, which isn't an "
                             "action id both games start a constant motion for")
        if row["motion_a"] is None or row["motion_b"] is None:
            raise ValueError(f"{monster['key']}: {fmt_id(key)} has a mapping row without both "
                             "motion numbers")
        if row["motion_a"] != mh4u[key]["motion"] or row["motion_b"] != source[key]["motion"]:
            raise ValueError(f"{monster['key']}: {fmt_id(key)}'s mapping numbers aren't the two "
                             "inventories'")
        if mh4u[key]["motion"] == source[key]["motion"]:
            raise ValueError(f"{monster['key']}: {fmt_id(key)} starts the same index in both "
                             "games and needs no mapping row")
    entries, unresolved = [], []
    for key in compared:
        row = seen.get(key)
        if row is None:
            if mh4u[key]["motion"] != source[key]["motion"]:
                raise ValueError(f"{monster['key']}: {fmt_id(key)}'s indices differ but the "
                                 "mapping has no row for it")
            continue
        entry = dict(cat=key[0], index=table_index(key), motion=row["motion_a"])
        if row["how"] == "unresolved":
            unresolved.append(entry)
        else:
            entry["source"] = repack_motion(source_game, row["motion_b"])
            entries.append(entry)
    order = lambda e: (e["cat"], e["index"], e["motion"])  # noqa: E731
    entries.sort(key=order)
    unresolved.sort(key=order)
    return dict(monster=monster, source=source_game, entries=entries, unresolved=unresolved,
                common=len(common), compared=len(compared),
                same_index=sum(1 for k in compared if k not in seen),
                not_compared=len(common) - len(compared))


def render_header(tables: list[dict]) -> str:
    """The plugin's header: one motion table per ported monster, keyed by its id."""
    lines = [
        f"/* Generated from R1's comparison by {GENERATOR}.",
        " * Do not edit: run the tool against the player's own dumps. Licence: GPL-3.0-or-later. */",
        "#ifndef MHUC_MOTIONS_H",
        "#define MHUC_MOTIONS_H",
        "",
        "#include <stdint.h>",
        "",
        "/* One translation for a ported monster: for `category`/`index` (its current action),",
        " * MH4U's handler asks `motion`; the source game's animation is at `source` in the",
        " * converted motion lists, in MH4U's packing (`file << 8 | slot`; the converted lists",
        " * keep the source game's grouping). `index` is 0x100 for a category-only action.",
        " */",
        "typedef struct MhucMotion {",
        "    uint8_t category;",
        "    uint16_t index;",
        "    uint16_t motion;",
        "    uint16_t source;",
        "} MhucMotion;",
        "",
        "/* One ported monster's translations, keyed by its MH4U id (data/ids/registry.csv).",
        " * `unresolved` holds the action ids R1 cannot resolve yet, as",
        " * `category << 8 | index`: the plugin passes their motion numbers through unchanged.",
        " * The four counts are R1's for the pair this table was compared with;",
        " * tools/check_motion_tables.py checks them. */",
        "typedef struct MhucPortedMotions {",
        "    uint8_t id;",
        "    uint16_t entry_count;",
        "    uint16_t unresolved_count;",
        "    uint16_t common;",
        "    uint16_t compared;",
        "    uint16_t same_index;",
        "    uint16_t not_compared;",
        "    const MhucMotion *entries;",
        "    const uint16_t *unresolved;",
        "} MhucPortedMotions;",
        "",
    ]
    for t in tables:
        m, ident = t["monster"], int(t["monster"]["id"], 0)
        lines.append(f"/* {m['name']}, ported from {m['source_game']} {m['source_key']} "
                     f"({m['key']}, id {ident}): {len(t['entries'])} of R1's {t['compared']} "
                     f"compared action ids translated, {len(t['unresolved'])} left out "
                     f"(category 7's computed index), {t['same_index']} start the same index in "
                     f"both games; {t['not_compared']} of the {t['common']} common ids aren't "
                     f"compared. */")
        if t["entries"]:
            lines.append(f"static const MhucMotion mhuc_motions_{ident}[] = {{")
            lines += [f"    {{{e['cat']}, {e['index']}, 0x{e['motion']:03x}, 0x{e['source']:03x}}},"
                      for e in t["entries"]]
            lines.append("};")
        else:
            lines.append(f"static const MhucMotion *const mhuc_motions_{ident} = NULL;")
        if t["unresolved"]:
            lines.append(f"static const uint16_t mhuc_unresolved_{ident}[] = {{")
            lines += [f"    0x{(e['cat'] << 8) | (e['index'] & 0xff):04x}, "
                      f"/* {fmt_id((e['cat'], None if e['index'] == NO_INDEX else e['index']))} */"
                      for e in t["unresolved"]]
            lines.append("};")
        else:
            lines.append(f"static const uint16_t *const mhuc_unresolved_{ident} = NULL;")
        lines.append("")
    lines += [
        f"#define MHUC_PORTED_MOTIONS_COUNT {len(tables)}",
        "static const MhucPortedMotions mhuc_ported_motions[MHUC_PORTED_MOTIONS_COUNT] = {",
    ]
    for t in tables:
        ident = int(t["monster"]["id"], 0)
        lines.append(f"    {{{ident}, {len(t['entries'])}, {len(t['unresolved'])}, "
                     f"{t['common']}, {t['compared']}, {t['same_index']}, {t['not_compared']}, "
                     f"mhuc_motions_{ident}, mhuc_unresolved_{ident}}},")
    lines += ["};", "", "#endif", ""]
    return "\n".join(lines)


def read_registry(path: str) -> list[dict]:
    """The ported content rows data/ids/registry.csv holds (tools/check_ids.py's shape)."""
    import check_ids

    rows, problems = check_ids.read_registry(path)
    if problems:
        raise ValueError("; ".join(problems))
    return [r for r in rows if r["kind"] == "monster"]


def tables_from(registry: list[dict], mh4u: dict, sources: dict[str, tuple[dict, list[dict]]]) -> list[dict]:
    """One table per ported monster, in registry order.

    `sources` maps a source game to its R1 inventory and mapping. A ported monster whose source
    game has no comparison (a port from MH4U itself, or a game R1 wasn't run on) is refused."""
    out = []
    for row in sorted(registry, key=lambda r: int(r["id"], 0)):
        game = row["source_game"]
        if game not in sources:
            raise ValueError(f"{row['key']}: no --source for {game}, so its table can't be built")
        source, mapping_rows = sources[game]
        out.append(build_table(row, mh4u, source, mapping_rows, game))
    return out


def action_key(key: tuple[int, int | None]) -> tuple[int, int]:
    """Sort an action id with a category-only action before its indexed ones."""
    return (key[0], -1 if key[1] is None else key[1])


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
            for key, ma, mb, sig, _found in s["elsewhere"]:
                row(key, ma, mb, "same-elsewhere", sig, sig)
            for key, ma, mb, sa, sb in s["different"]:
                row(key, ma, mb, "different", sa, sb)
            for item in s["unresolved"]:
                key, ma, mb = item[:3]
                row(key, ma, mb, "unresolved")
    return 0


def cmd_table(args) -> int:
    mh4u = read_rows(args.mh4u)
    sources = {}
    for game, inventory, mapping in args.source:
        sources[game] = (read_rows(inventory), read_mapping(mapping))
    registry = read_registry(args.registry)
    tables = tables_from(registry, mh4u, sources)
    if not tables:
        raise ValueError(f"{args.registry} has no ported monster to build a table for")
    text = render_header(tables)
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    for t in tables:
        print(f"{t['monster']['key']}: {len(t['entries'])} entries, {len(t['unresolved'])} "
              f"unresolved, {t['same_index']} same index, {t['not_compared']} not compared "
              f"(of {t['common']} common)")
    print(f"wrote {args.output}")
    return 0


FALLBACK_GENERATOR = "reference/monster_motions.py fallback"


def monster_lists(romfs_path: str, game: str, key: str) -> list[bytes]:
    """A monster's motion list files in their file order.

    MH4U: `/data/emNNN.arc`, lists `enemy\\emNNN\\mot\\emNNN_<file>`. MH3U: `/arc/enemy/emNNN.arc`,
    lists `mot_emNNN_<file * 100>`. MHXX: `/arc/enemy/emNNN_00.arc`, lists `emNNN_00_<file>`.
    The converted lists keep this order (the port's record slot is the file number)."""
    sys.path.insert(0, os.path.join(HERE, "..", "src"))
    from mhuc.formats import arc, romfs

    path = {"mh4u": f"/data/{key}.arc", "mh3u": f"/arc/enemy/{key}.arc",
            "mhxx": f"/arc/enemy/{key}_00.arc"}[game]
    image = romfs.open_image(romfs_path)
    entry = next((f for f in image.files() if f.path == path), None)
    if entry is None:
        raise ValueError(f"{romfs_path} has no {path}")
    lists = []
    for e in arc.read(image.read(entry)).entries:
        if e.type_name != "rMotionList" or "\\mot\\" not in e.path:
            continue
        number = e.path.rsplit("_", 1)[-1]
        if not number.isdigit():
            continue
        file = int(number) // 100 if game == "mh3u" else int(number)
        lists.append((file, e.path, e.data))
    lists.sort()
    if [f for f, _, _ in lists] != list(range(len(lists))):
        raise ValueError(f"{path}: motion list numbers {[f for f, _, _ in lists]} aren't 0 to n-1")
    return [data for _, _, data in lists]


def identical_tracks(a: dict, b: dict) -> int:
    """How many (bone, usage) tracks two animations' decoded keys share exactly."""
    return sum(1 for k in set(a) & set(b) if a[k] == b[k])


def decoded_tracks(data: bytes, version: int, anim) -> dict:
    """An animation's keys per (bone, usage), rounded to 2 decimals so that the two LMT
    versions' encodings of one key compare equal."""
    from mhuc.formats import lmt

    out = {}
    for t in anim.tracks:
        try:
            keys = lmt.decode_keys(data, t, version, anim.frames)
        except lmt.LmtError:
            continue
        out[(t.bone, t.usage)] = [(k.frame,) + tuple(round(c, 2) for c in k.value) for k in keys]
    return out


def build_fallback(mh4u_files: list[bytes], source_files: list[bytes]) -> list[tuple[int, int]]:
    """(MH4U motion number, the source's animation) for every MH4U animation with exactly one
    source counterpart, both in MH4U's packing.

    A counterpart has the same signature (same_motion: frames, loop frame, track count). When
    several do, the one whose decoded keys equal MH4U's on strictly more tracks than any other
    is taken; otherwise the number is left out. This is keyed by the number alone, so it
    answers what the action-keyed table can't: a handler that computes its index (category 7)
    or starts a second motion. A number left out passes through; an identity is left out
    because it changes nothing."""
    sys.path.insert(0, os.path.join(HERE, "..", "src"))
    from mhuc.formats import lmt

    def anims(data):
        version, out = lmt.read(data)
        return version, out
    source = [anims(d) for d in source_files]
    by_frames = collections.defaultdict(list)
    for file, (_, items) in enumerate(source):
        for slot, a in enumerate(items):
            if a:
                by_frames[(a.frames, a.loop_frame)].append((file, slot, a))
    out = []
    for file, data in enumerate(mh4u_files):
        version, items = anims(data)
        for slot, a in enumerate(items):
            if not a:
                continue
            sig = (a.frames, a.loop_frame, len(a.tracks))
            hits = [(f, s, b) for f, s, b in by_frames.get(sig[:2], [])
                    if same_motion(sig, (b.frames, b.loop_frame, len(b.tracks)))]
            if len(hits) > 1:
                mine = decoded_tracks(data, version, a)
                scored = sorted(((identical_tracks(mine, decoded_tracks(source_files[f], source[f][0], b)),
                                  f, s) for f, s, b in hits), reverse=True)
                hits = [h for h in hits if (h[0], h[1]) == scored[0][1:]] \
                    if scored[0][0] > scored[1][0] else []
            motion = (file << 8) | slot
            if len(hits) == 1 and (hits[0][0] << 8 | hits[0][1]) != motion:
                out.append((motion, hits[0][0] << 8 | hits[0][1]))
    return out


def render_fallback(tables: list[dict]) -> str:
    """The plugin's second header: each ported monster's signature fallback."""
    lines = [
        f"/* Generated from the two games' motion lists by {FALLBACK_GENERATOR}.",
        " * Do not edit: run the tool against the player's own dumps. Licence: GPL-3.0-or-later. */",
        "#ifndef MHUC_FALLBACK_H",
        "#define MHUC_FALLBACK_H",
        "",
        "#include <stdint.h>",
        "",
        "/* MH4U's handler asks `motion` (file << 8 | slot of the stand-in's lists); the one source",
        " * animation with the same frames, loop frame and track count (one more on MH4U's side",
        " * allowed), or among several the one whose keys equal MH4U's on the most tracks, is at",
        " * `source` in the converted lists. Used when motions.h has no entry for the current",
        " * action. Sorted by motion. */",
        "typedef struct MhucMotionFallback {",
        "    uint16_t motion;",
        "    uint16_t source;",
        "} MhucMotionFallback;",
        "",
        "typedef struct MhucPortedFallback {",
        "    uint8_t id;",
        "    uint16_t count;",
        "    const MhucMotionFallback *entries;",
        "} MhucPortedFallback;",
        "",
    ]
    for t in tables:
        m, ident = t["monster"], int(t["monster"]["id"], 0)
        lines.append(f"/* {m['name']}, {m['source_game']} {m['source_key']} on MH4U em{int(m['stand_in'], 0):03d} "
                     f"({m['key']}, id {ident}): {len(t['entries'])} numbers. */")
        if t["entries"]:
            lines.append(f"static const MhucMotionFallback mhuc_fallback_{ident}[] = {{")
            lines += [f"    {{0x{a:03x}, 0x{b:03x}}}," for a, b in t["entries"]]
            lines.append("};")
        else:
            lines.append(f"static const MhucMotionFallback *const mhuc_fallback_{ident} = NULL;")
        lines.append("")
    lines += [f"#define MHUC_PORTED_FALLBACK_COUNT {len(tables)}",
              "static const MhucPortedFallback mhuc_ported_fallback[MHUC_PORTED_FALLBACK_COUNT] = {"]
    for t in tables:
        ident = int(t["monster"]["id"], 0)
        lines.append(f"    {{{ident}, {len(t['entries'])}, mhuc_fallback_{ident}}},")
    lines += ["};", "", "#endif", ""]
    return "\n".join(lines)


def cmd_fallback(args) -> int:
    romfs_of = {"mh4u": args.mh4u_romfs}
    for game, path in args.source_romfs:
        romfs_of[game] = path
    tables = []
    for row in sorted(read_registry(args.registry), key=lambda r: int(r["id"], 0)):
        game = row["source_game"]
        if game not in romfs_of:
            raise ValueError(f"{row['key']}: no --source-romfs for {game}")
        mh4u_lists = monster_lists(args.mh4u_romfs, "mh4u", f"em{int(row['stand_in'], 0):03d}")
        source_lists = monster_lists(romfs_of[game], game, row["source_key"])
        tables.append(dict(monster=row, entries=build_fallback(mh4u_lists, source_lists)))
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        f.write(render_fallback(tables))
    for t in tables:
        print(f"{t['monster']['key']}: {len(t['entries'])} fallback numbers")
    print(f"wrote {args.output}")
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
    p = sub.add_parser("table", help="the port's run-time motion table, one per ported monster")
    p.add_argument("--mh4u", required=True, help="R1's MH4U inventory (list -o)")
    p.add_argument("--source", nargs=3, action="append", required=True,
                   metavar=("GAME", "INVENTORY", "MAPPING"),
                   help="a source game's R1 inventory and its compare --mapping TSV; repeatable")
    p.add_argument("--registry", default=os.path.join(HERE, "..", "data", "ids", "registry.csv"),
                   help="the ported content registry (default: data/ids/registry.csv)")
    p.add_argument("-o", "--output", required=True, help="the generated header")
    p.set_defaults(fn=cmd_table)
    p = sub.add_parser("fallback", help="each ported monster's motion-number fallback by animation signature")
    p.add_argument("--mh4u-romfs", required=True, help="MH4U's RomFS image (the stand-ins' lists)")
    p.add_argument("--source-romfs", nargs=2, action="append", required=True, metavar=("GAME", "ROMFS"),
                   help="a source game's RomFS image; repeatable")
    p.add_argument("--registry", default=os.path.join(HERE, "..", "data", "ids", "registry.csv"),
                   help="the ported content registry (default: data/ids/registry.csv)")
    p.add_argument("-o", "--output", required=True, help="the generated header")
    p.set_defaults(fn=cmd_fallback)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
