#!/usr/bin/env python3
"""Check the translated-action ledger in data/actions/ against MHXX's recompiled module.

Each row records one action MH4U has no handler for: the case block, the handler unit, the
first motion constant the handler starts, and whether the port translates it, leaves it to an
MH4U handler, or still owes it. The tool walks the module's action dispatcher
(reference/monster_actions.py) and compares. It prints counts and ids only.

Usage:
    check_actions.py --module roEm001.cro --crs static.crs [--ledger data/actions/rathian-gu.csv]

The module is MHXX v1.4's roEm001.cro and the CRS the static executable it imports from (from
the player's own dump). Exit status 1 on a mismatch.
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "reference"))

import cro  # noqa: E402
import monster_actions as actions  # noqa: E402

MOTION = 0x008EB108          # MHXX's motion-start wrapper (docs/checks.md, R1)
MODULE_BASE = 0x02000000
DISPATCHER = 0x02009704


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


def first_motion(code: actions.Code, handler: int) -> int | None:
    """The first constant in r1 passed to the motion wrapper, as R1 defines it."""
    regs: dict[str, int | None] = {}
    for i in code.insns(handler, 400):
        from capstone.arm import ARM_OP_IMM, ARM_OP_REG
        m = i.mnemonic
        if m in ("mov", "ldr", "ldrlo") and len(i.operands) >= 2 and i.operands[0].type == ARM_OP_REG \
                and i.reg_name(i.operands[0].reg) == "r1":
            if i.operands[1].type == ARM_OP_IMM:
                regs["r1"] = i.operands[1].imm
            elif m.startswith("ldr") and "[pc" in i.op_str:
                try:
                    off = int(i.op_str.split("#")[-1].rstrip("]"), 0)
                    regs["r1"] = code.word(i.address + 8 + off)
                except ValueError:
                    regs["r1"] = None
            else:
                regs["r1"] = None
        if m in ("bl", "b") and i.operands and i.operands[0].type == ARM_OP_IMM:
            target = i.operands[0].imm
            if code.veneer(target) == MOTION:
                return regs.get("r1")
        if (m.startswith("pop") and "pc" in i.op_str) or (m == "bx" and i.op_str != "r1"):
            break
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--module", required=True, help="MHXX v1.4's roEm001.cro")
    ap.add_argument("--crs", required=True, help="the static executable's CRS")
    ap.add_argument("--ledger", default=os.path.join(ROOT, "data", "actions", "rathian-gu.csv"))
    ap.add_argument("--base", type=lambda s: int(s, 0), default=MODULE_BASE)
    a = ap.parse_args()
    with open(a.crs, "rb") as f:
        crs = cro.Cro(f.read())
    with open(a.module, "rb") as f:
        ld = cro.load(f.read(), a.base, cro.static_segments(crs))
    lo, hi = ld.text
    code = actions.Code(ld.image, a.base, lo, hi)
    inventory = {(x.cat, x.idx): x for x in actions.inventory(code, a.base + (DISPATCHER - MODULE_BASE))}
    rows = read_ledger(a.ledger)

    problems = []
    checked = {"block": 0, "handler": 0, "motion": 0}
    counts = {"translated": 0, "mh4u": 0, "pending": 0}
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
            got = first_motion(code, action.handler or action.block)
            if got != row["motion"]:
                got_s = "none" if got is None else f"0x{got:x}"
                problems.append(f"{row['action']}: first motion {got_s}, ledger 0x{row['motion']:x}")
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    print(f"{len(rows)} actions: blocks {checked['block']}/{len(rows)}, "
          f"handlers {checked['handler']}/{len(rows)}, first motions {checked['motion']}/{len(rows)}; "
          f"translated {counts['translated']}, MH4U's own {counts['mh4u']}, pending {counts['pending']}")
    for p in problems:
        print(f"  {p}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
