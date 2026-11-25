#!/usr/bin/env python3
"""The action port map: which MH4U handler each of a monster's shared MHXX action ids reaches,
which motion each side starts, and which ids MH4U does not have.

A monster's current action is a category byte and an index byte (docs/checks.md, R1), and the
action ids are shared: 273 of MHXX Rathian's 301 ids also exist in MH4U. For every id whose
handler starts a constant motion in both games the index is the same (R1), and the port ships
MHXX's motion lists under the ported monster's name, so a shared id runs MH4U's own handler and
starts MHXX's animation at the same index. This tool records that per id and finds the ids where
it does not hold.

    map XX_ACTIONS.tsv MH4U_ACTIONS.tsv XX_MOTIONS.tsv MH4U_MOTIONS.tsv [--out MAP.tsv]

The inputs are the inventories `monster_actions.py list` writes and the motion lists
`monster_motions.py list` writes, for the same monster in each game. The map file holds the
motion indices, so it stays outside the repository; the counts and the ids are what goes in
docs/checks.md (check R2).
"""
from __future__ import annotations

import argparse
import collections
import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monster_motions  # noqa: E402  (no fork import at load time: the map's tests need none)

# The start-motion kinds a handler scan reports (monster_motions.py).
HOW_CONSTANT = "constant"
HOW_NONE = "none"
HOW_INLINE = "no-handler"

# What a shared id needs from the port, by the pair of start-motion kinds.
SAME_INDEX = "same-index"        # both start the same constant index: MH4U's handler plays it
OTHER_INDEX = "other-index"      # both start a constant index, but different ones
MH4U_MOTION = "mh4u-motion"      # only MH4U starts one: MHXX's move starts no motion here
MHXX_MOTION = "mhxx-motion"      # only MHXX starts one: MH4U's handler starts nothing
NO_MOTION = "no-motion"          # neither starts one: timing-only or handled elsewhere
BOTH_INLINE = "both-inline"      # both act inline, no handler function
MIXED = "mixed"                  # one side acts inline and the other starts nothing
MHXX_ONLY = "mhxx-only"          # the id does not exist in MH4U

CLASSES = (SAME_INDEX, OTHER_INDEX, MH4U_MOTION, MHXX_MOTION, NO_MOTION, BOTH_INLINE, MIXED)


@dataclass
class Action:
    """One row of a `monster_actions.py list` file: an action id, its handler and case args."""
    cat: int
    idx: int | None
    handler: int | None
    args: dict[str, int]

    @property
    def key(self) -> tuple[int, int | None]:
        return (self.cat, self.idx)


@dataclass
class Row:
    """One of the monster's MHXX actions, with what the other game does with the id."""
    cat: int
    idx: int | None
    shared: bool
    mhxx_handler: int | None
    mh4u_handler: int | None
    mhxx_motion: int | None     # a motion index: game-derived, stays out of the repository
    mh4u_motion: int | None
    mhxx_how: str
    mh4u_how: str
    cls: str
    args_same: bool
    mhxx_args: dict[str, int]
    mh4u_args: dict[str, int]

    @property
    def key(self) -> tuple[int, int | None]:
        return (self.cat, self.idx)

    def tsv(self) -> str:
        def h(x):
            return "" if x is None else f"0x{x:08x}"

        def m(x):
            return "" if x is None else str(x)

        def a(d):
            return ",".join(f"{k}={v}" for k, v in sorted(d.items()))

        return "\t".join([
            str(self.cat), "" if self.idx is None else str(self.idx),
            "1" if self.shared else "0", h(self.mhxx_handler), h(self.mh4u_handler),
            self.mhxx_how, self.mh4u_how, m(self.mhxx_motion), m(self.mh4u_motion),
            self.cls, "1" if self.args_same else "0", a(self.mhxx_args), a(self.mh4u_args)])


HEADER = ("# cat\tidx\tshared\tmhxx_handler\tmh4u_handler\tmhxx_how\tmh4u_how\t"
          "mhxx_motion\tmh4u_motion\tclass\targs_same\tmhxx_args\tmh4u_args\n")


def read_actions(path: str) -> dict[tuple[int, int | None], Action]:
    """A `monster_actions.py list` inventory: cat, idx, block, fn, kind, handler, veneer, args."""
    out = {}
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            p = line.rstrip("\n").split("\t")
            args = {k: int(v) for k, v in (kv.split("=") for kv in p[7].split(",") if kv)}
            action = Action(int(p[0]), int(p[1]) if p[1] else None,
                            int(p[5], 16) if p[5] else None, args)
            out[action.key] = action
    return out


def classify(mhxx_how: str, mh4u_how: str, mhxx_motion: int | None,
             mh4u_motion: int | None) -> str:
    """What porting the id needs, from the two games' start-motion kinds."""
    if mhxx_how == HOW_CONSTANT and mh4u_how == HOW_CONSTANT:
        return SAME_INDEX if mhxx_motion == mh4u_motion else OTHER_INDEX
    if mhxx_how == HOW_CONSTANT:
        return MHXX_MOTION
    if mh4u_how == HOW_CONSTANT:
        return MH4U_MOTION
    if mhxx_how == HOW_NONE and mh4u_how == HOW_NONE:
        return NO_MOTION
    if mhxx_how == HOW_INLINE and mh4u_how == HOW_INLINE:
        return BOTH_INLINE
    return MIXED


def build_map(xx_actions, mh4u_actions, xx_motions, mh4u_motions) -> list[Row]:
    """One row per MHXX action, in action-id order."""
    rows = []
    for key in sorted(xx_actions):
        xx = xx_actions[key]
        xx_motion = xx_motions.get(key, {"motion": None, "how": HOW_NONE})
        if key not in mh4u_actions:
            rows.append(Row(key[0], key[1], False, xx.handler, None, xx_motion["motion"], None,
                            xx_motion["how"], "", MHXX_ONLY, False, xx.args, {}))
            continue
        u4 = mh4u_actions[key]
        u4_motion = mh4u_motions.get(key, {"motion": None, "how": HOW_NONE})
        rows.append(Row(
            key[0], key[1], True, xx.handler, u4.handler,
            xx_motion["motion"], u4_motion["motion"], xx_motion["how"], u4_motion["how"],
            classify(xx_motion["how"], u4_motion["how"], xx_motion["motion"], u4_motion["motion"]),
            xx.args == u4.args, xx.args, u4.args))
    return rows


def handler_unit(row: Row) -> str:
    """The unit an MHXX-only id needs translated: its handler, or the block it runs inline."""
    if row.mhxx_handler is not None:
        return f"0x{row.mhxx_handler:08x}"
    return "inline"


def summarize(rows: list[Row]) -> dict:
    """Counts and ids only: no motion index leaves this function, so it can be printed."""
    shared = [r for r in rows if r.shared]
    only = [r for r in rows if not r.shared]
    counts = collections.Counter(r.cls for r in shared)
    skipped = collections.Counter((r.mhxx_how, r.mh4u_how) for r in shared
                                  if r.cls not in (SAME_INDEX, OTHER_INDEX))
    by_class = collections.defaultdict(list)
    for r in shared:
        by_class[r.cls].append(r.key)
    arg_differ = [(r.key, r.mhxx_args, r.mh4u_args) for r in shared if not r.args_same]
    units = collections.defaultdict(list)
    for r in only:
        units[handler_unit(r)].append(r.key)
    return dict(total=len(rows), shared=len(shared), only=len(only), counts=counts,
                by_class=by_class, skipped=skipped, arg_differ=arg_differ,
                units=units)


def print_summary(s: dict) -> None:
    print(f"actions {s['total']}, shared {s['shared']}, mhxx-only {s['only']}")
    print("shared: " + ", ".join(f"{c} {s['counts'][c]}" for c in CLASSES))
    if s["skipped"]:
        print("not compared: " + ", ".join(f"{x}/{y} {n}"
                                           for (x, y), n in s["skipped"].most_common()))
    for cls in (MH4U_MOTION, MHXX_MOTION, MIXED):
        if s["by_class"][cls]:
            print(f"{cls} ids ({len(s['by_class'][cls])}):")
            print(monster_motions.fmt_ids(s["by_class"][cls]))
    print(f"case-block arguments differ: {len(s['arg_differ'])}")
    for key, xx_args, u4_args in s["arg_differ"]:
        xx = ",".join(f"{k}={v}" for k, v in sorted(xx_args.items())) or "-"
        u4 = ",".join(f"{k}={v}" for k, v in sorted(u4_args.items())) or "-"
        print(f"  {monster_motions.fmt_id(key)} {xx} | {u4}")
    print(f"mhxx-only, by handler unit: {len(s['units'])}")
    for unit in sorted(s["units"]):
        ids = s["units"][unit]
        print(f"  {unit} ({len(ids)}): {monster_motions.fmt_ids(ids).replace(chr(10), '; ')}")


def write_map(rows: list[Row], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(HEADER)
        for row in rows:
            f.write(row.tsv() + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("map", help="pair two games' action and motion inventories")
    p.add_argument("xx_actions", help="monster_actions.py list for the source game")
    p.add_argument("mh4u_actions", help="monster_actions.py list for MH4U")
    p.add_argument("xx_motions", help="monster_motions.py list for the source game")
    p.add_argument("mh4u_motions", help="monster_motions.py list for MH4U")
    p.add_argument("--out", help="write the per-id map here (motion indices: keep it outside "
                                 "the repository)")
    args = ap.parse_args(argv)
    rows = build_map(read_actions(args.xx_actions), read_actions(args.mh4u_actions),
                     monster_motions.read_rows(args.xx_motions),
                     monster_motions.read_rows(args.mh4u_motions))
    if args.out:
        write_map(rows, args.out)
    print_summary(summarize(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
