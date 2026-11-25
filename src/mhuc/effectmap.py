"""The source-to-MH4U effect-id tables the effect converters read.

`data/effectmap/<source>-mh4u/effect.csv` holds one row per source effect id: which MH4U effect
plays it, both names for review, and how the row was established. Like quests' `data/idmap/`, the
tables ship empty: the rows come from the maintainer's dumps and an in-game check, and a converter
refuses an effect id the table doesn't name rather than guessing a similar-looking one.
"""
from __future__ import annotations

import csv
import os

TABLE = "effect.csv"


class EffectMapError(ValueError):
    pass


def load(folder: str) -> dict[int, int]:
    """One source game's effect-id map: source id -> MH4U id, both read as integers."""
    path = os.path.join(folder, TABLE)
    rows: dict[int, int] = {}
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            source = (row.get("source") or "").strip()
            if not source:
                continue
            try:
                rows[int(source, 0)] = int((row.get("target") or "").strip(), 0)
            except ValueError as e:
                raise EffectMapError(f"{path}: row {source!r}: {e}") from None
    return rows


class EffectMap:
    """`rows` plus the source ids a conversion asked for and the table doesn't name."""

    def __init__(self, rows: dict[int, int]):
        self.rows = rows
        self.missing: list[int] = []

    def target(self, source: int) -> int | None:
        """The MH4U id for `source`, or None and the id recorded in `missing`."""
        target = self.rows.get(source)
        if target is None:
            self.missing.append(source)
        return target

    def check(self, what: str) -> None:
        """Raise, naming every unmapped id, if a conversion needed ids the table doesn't hold."""
        if self.missing:
            ids = ", ".join(f"{x:#x}" for x in sorted(set(self.missing)))
            raise EffectMapError(f"{what}: the effect-id map doesn't name {ids} "
                                 f"(data/effectmap; add the rows from your own dumps before converting)")
