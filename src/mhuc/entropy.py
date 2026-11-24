"""Tell encrypted or compressed files from plain ones, by byte entropy; counts only.

Used on save and Extra Data files, whose crypto isn't specified here yet (specs/quest.md, check Q3):
it prints each file's size, whether the size is a multiple of the 8-byte Blowfish block, its
Shannon entropy in bits per byte and a verdict. Nothing from the files is printed.
"""
from __future__ import annotations

import math
import os
from collections import Counter
from dataclasses import dataclass

# Above DENSE, a file of a few KiB or more is encrypted or compressed: plain game data (tables,
# text, models) sits well below it. A short random file measures lower than 8 (about 7.64 bits
# per byte at 512 bytes), so the bar is lowered to MARGIN under what random data of that size
# gives on average. Below MIN_SIZE the estimate is too noisy to call.
DENSE = 7.9
MARGIN = 0.15
MIN_SIZE = 256
BLOCK = 8


def dense_bar(size: int) -> float:
    """The entropy at or above which a file of this size counts as dense."""
    expected_random = 8 - 255 / (2 * size * math.log(2))  # Miller-Madow bias of the plug-in estimate
    return min(DENSE, expected_random - MARGIN)


@dataclass
class Measure:
    path: str
    size: int
    entropy: float
    zero_fraction: float

    @property
    def block_aligned(self) -> bool:
        return self.size % BLOCK == 0

    @property
    def verdict(self) -> str:
        if self.size < MIN_SIZE:
            return "too small"
        return "dense (encrypted or compressed)" if self.entropy >= dense_bar(self.size) else "plain"


def entropy(data: bytes) -> float:
    """Shannon entropy of data, in bits per byte (0.0 for empty data)."""
    if not data:
        return 0.0
    n = len(data)
    return -sum(c / n * math.log2(c / n) for c in Counter(data).values())


def measure(path: str, data: bytes) -> Measure:
    zeros = data.count(0) / len(data) if data else 0.0
    return Measure(path, len(data), entropy(data), zeros)


def walk(paths: list[str]) -> list[Measure]:
    """Measure every file named, and every file under every folder named, in sorted order."""
    out = []
    for p in paths:
        files = [p] if os.path.isfile(p) else sorted(
            os.path.join(d, f) for d, _, fs in os.walk(p) for f in fs)
        for f in files:
            with open(f, "rb") as fh:
                out.append(measure(f, fh.read()))
    return out


def report(measures: list[Measure]) -> str:
    lines = [f"{'size':>10}  {'%8':>3}  {'bits/B':>6}  {'zeros':>5}  verdict  path"]
    for m in measures:
        lines.append(f"{m.size:>10}  {'ok' if m.block_aligned else 'no':>3}  {m.entropy:6.3f}  "
                     f"{m.zero_fraction:5.3f}  {m.verdict}  {m.path}")
    dense = sum(m.verdict.startswith("dense") for m in measures)
    lines.append(f"{len(measures)} files, {dense} dense")
    return "\n".join(lines)
