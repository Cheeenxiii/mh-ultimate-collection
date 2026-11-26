#!/usr/bin/env python3
"""Check the action ledgers in data/actions/ against the source game's code.

Each row records one action: the case block, the handler unit, the first motion constant the
handler starts, and whether the port translates it, leaves it to an MH4U handler, or still
owes it. The tool walks the source game's action dispatcher (reference/monster_actions.py),
takes the first motion each handler starts (reference/monster_motions.py, check R1), and
compares. It prints counts and ids only.

The GU ledger is checked against MHXX v1.4's `roEm001.cro` and the `static.crs` it imports
from; the 3U ledger against MH3U USA's `code.bin` and its `exheader.bin`. Exit status 1 on a
mismatch.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "reference"))

import monster_motions as motions  # noqa: E402

MODULE_BASE = 0x02000000
DISPATCHER = 0x02009704      # MHXX's action dispatcher, in a module loaded at MODULE_BASE
MOTION = {"mhxx": 0x008EB108, "mh3u": 0x00828828}   # the motion-start wrapper (docs/checks.md, R1)
LEDGER = {"mhxx": "rathian-gu.csv", "mh3u": "rathian-3u.csv"}
# A 3U id is never left to an MH4U handler: no shared action runs a source handler it lacks.
STATUSES = {"mhxx": ("translated", "mh4u", "pending"), "mh3u": ("translated", "pending")}
STATUS_LABEL = {"translated": "translated", "mh4u": "MH4U's own", "pending": "pending"}


def read_ledger(path: str) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            action, block, handler, motion, status = [c.strip() for c in line.split(",")]
            cat, _, idx = action.partition("/")
            rows.append({"action": action, "cat": int(cat, 0), "idx": int(idx, 0) if idx else None,
                         "block": int(block, 16), "handler": int(handler, 16) if handler else None,
                         "motion": int(motion, 16) if motion else None, "status": status})
    return rows


def check(rows: list[dict], inventory: dict, motion_of, statuses: tuple[str, ...]):
    """Compare ledger rows with a dispatcher's inventory: (problems, checked, counts).

    `motion_of(action)` returns the first constant motion the inventory's handler starts.
    """
    problems = []
    checked = {"block": 0, "handler": 0, "motion": 0}
    counts = {s: 0 for s in statuses}
    for row in rows:
        action = inventory.get((row["cat"], row["idx"]))
        if action is None:
            problems.append(f"{row['action']}: the dispatcher has no such action")
            continue
        checked["block"] += 1
        if action.block != row["block"]:
            problems.append(f"{row['action']}: block 0x{action.block:08x}, ledger 0x{row['block']:08x}")
        if row["handler"] is not None:
            checked["handler"] += 1
            if action.handler != row["handler"]:
                got = "none" if action.handler is None else f"0x{action.handler:08x}"
                problems.append(f"{row['action']}: handler {got}, ledger 0x{row['handler']:08x}")
        if row["motion"] is not None:
            checked["motion"] += 1
            got = motion_of(action)
            if got != row["motion"]:
                got_s = "none" if got is None else f"0x{got:x}"
                problems.append(f"{row['action']}: first motion {got_s}, ledger 0x{row['motion']:x}")
        if row["status"] not in statuses:
            problems.append(f"{row['action']}: status {row['status']}, not one of {', '.join(statuses)}")
        else:
            counts[row["status"]] += 1
    return problems, checked, counts


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        epilog="A 3U ledger status is `translated` or `pending`; the GU ledger also allows "
               "`mh4u`. Exit status 1 on a mismatch.")
    ap.add_argument("--game", choices=("mhxx", "mh3u"), default="mhxx",
                    help="the source game's code format (default: mhxx)")
    ap.add_argument("--module", help="MHXX v1.4's roEm001.cro (--game mhxx)")
    ap.add_argument("--crs", help="the static executable's CRS (--game mhxx)")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=MODULE_BASE,
                    help=f"where the module is loaded, --game mhxx (default: 0x{MODULE_BASE:08x})")
    ap.add_argument("--exheader", help="MH3U USA's exheader.bin (--game mh3u)")
    ap.add_argument("--code", help="MH3U USA's code.bin (--game mh3u)")
    ap.add_argument("--dispatcher", type=lambda s: int(s, 0),
                    help="the action dispatcher's address (--game mh3u needs it: 0x00687d30; "
                         f"default for --game mhxx: 0x{DISPATCHER:08x} + the module base)")
    ap.add_argument("--range", type=lambda s: int(s, 0), nargs=2, metavar=("LO", "HI"),
                    help="the monster's own code in code.bin (--game mh3u needs it)")
    ap.add_argument("--functions",
                    help="a functions.tsv bounding each handler's scan; defaults to the game's table")
    ap.add_argument("--ledger", help="the ledger to check; defaults to the game's in data/actions/")
    a = ap.parse_args()

    if a.game == "mh3u":
        missing = [f"--{name}" for name, value in
                   (("exheader", a.exheader), ("code", a.code), ("dispatcher", a.dispatcher),
                    ("range", a.range)) if value is None]
        if missing:
            ap.error("--game mh3u needs " + ", ".join(missing))
    elif a.module is None or a.crs is None:
        ap.error("--game mhxx needs --module and --crs")

    if a.game == "mhxx":
        dispatcher = a.dispatcher if a.dispatcher is not None else a.base + (DISPATCHER - MODULE_BASE)
    else:
        dispatcher = a.dispatcher
    ledger = a.ledger or os.path.join(ROOT, "data", "actions", LEDGER[a.game])

    import monster_actions  # the fork import only matters when a dump is read
    code, table, entries = motions.load(a)
    inventory = {(x.cat, x.idx): x for x in monster_actions.inventory(code, dispatcher)}
    if entries is not None:
        entries |= {x.handler for x in inventory.values() if x.handler}
        entries |= {x.fn for x in inventory.values() if x.fn}

    def motion_of(action):
        handler = action.handler if action.kind == "tail" else None
        return motions.motion_for(code, handler, table, entries, MOTION[a.game])["motion"]

    rows = read_ledger(ledger)
    problems, checked, counts = check(rows, inventory, motion_of, STATUSES[a.game])
    n = len(rows)
    summary = ", ".join(f"{STATUS_LABEL[s]} {counts[s]}" for s in STATUSES[a.game])
    print(f"{n} actions: blocks {checked['block']}/{n}, handlers {checked['handler']}/{n}, "
          f"first motions {checked['motion']}/{n}; {summary}")
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
