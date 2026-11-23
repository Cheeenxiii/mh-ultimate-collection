"""mhuc catalog overlap: matching by wiki page on generated rows, and data/catalog/overlap.md kept current."""
from __future__ import annotations

import os

from mhuc import catalog, cli

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def rows(*items):
    return [{"game": g, "monster": n, "size": s, "page_source": p} for g, n, s, p in items]


def test_overlap_matches_by_page():
    data = rows(("MH4U", "Old Name", "large", "u/a"), ("MHGU", "New Name", "large", "u/a"),
                ("MHGU", "Other", "small", "u/b"), ("MH3U", "Old Name", "large", "u/c"))
    out = catalog.overlap(data, "monster", "size")
    assert out["MHGU"] == ([("New Name", "large", "Old Name")], [("Other", "small", "")])
    assert out["MH3U"] == ([], [("Old Name", "large", "")])  # same name, other page: no match


def test_overlap_md_is_current():
    path = os.path.join(ROOT, "data", "catalog", "overlap.md")
    with open(path, encoding="utf-8") as f:
        assert f.read() == catalog.render(os.path.join(ROOT, "data", "catalog")), \
            "run: mhuc catalog overlap --out data/catalog/overlap.md"


def test_cli_prints(capsys):
    assert cli.main(["catalog", "overlap", "--dir", os.path.join(ROOT, "data", "catalog")]) == 0
    assert capsys.readouterr().out.startswith("# What MH4U already has")
