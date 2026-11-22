"""data/catalog: every table has its README, a fixed header, no empty key cells, and a wiki
source URL on every row."""
from __future__ import annotations

import csv
import os

import pytest

CATALOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "catalog")
TABLES = {
    "monsters.csv": (["game", "monster", "size", "new_in_game", "class", "original_game", "source_game",
                      "list_source", "page_source"], ["game", "monster", "size"], ["list_source", "page_source"]),
    "maps.csv": (["game", "locale", "kind", "areas_in_game", "habitat", "page_source", "list_source"],
                 ["game", "locale", "kind"], ["page_source", "list_source"]),
    "weapons.csv": (["game", "weapon_class", "source"], ["game", "weapon_class"], ["source"]),
}
GAMES = {"MH3U", "MH4U", "MHGU"}


@pytest.mark.parametrize("name", sorted(TABLES))
def test_table(name):
    header, keys, sources = TABLES[name]
    assert os.path.exists(os.path.join(CATALOG, name.replace(".csv", ".md")))
    with open(os.path.join(CATALOG, name), newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        assert list(rows[0].keys()) == header
    seen = set()
    for row in rows:
        assert row["game"] in GAMES
        assert all(row[k] for k in keys), row
        assert all(row[s].startswith("https://monsterhunterwiki.org/wiki/") for s in sources), row
        key = tuple(row[k] for k in keys[:2])
        assert key not in seen, key
        seen.add(key)


def test_counts_are_plausible():
    with open(os.path.join(CATALOG, "weapons.csv"), newline="") as f:
        by_game = {}
        for row in csv.DictReader(f):
            by_game[row["game"]] = by_game.get(row["game"], 0) + 1
    assert by_game == {"MH3U": 12, "MH4U": 14, "MHGU": 14}
