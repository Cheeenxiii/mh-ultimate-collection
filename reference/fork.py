"""Puts the engine fork's tools/ on sys.path, since these scripts reuse its recompiler.

The fork is found through the MH4U_FORK environment variable, or as a sibling checkout named
MH4UltimateDC-fork next to this repository.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.environ.get("MH4U_FORK") or os.path.join(HERE, "..", "..", "MH4UltimateDC-fork"))
TOOLS = os.path.join(ROOT, "tools")

if not os.path.isfile(os.path.join(TOOLS, "recompile.py")):
    raise SystemExit(f"no MH4UltimateDC fork at {ROOT}: clone it there or set MH4U_FORK")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)
