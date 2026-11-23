"""idnames: inference on made-up observations; the CLI's refusal to write inside the repository."""
from __future__ import annotations

import os

from mhuc import cli, idnames


def test_infer_intersects_and_eliminates():
    obs = [({1, 2}, {"A", "B"}), ({1}, {"A", "C"}), ({2, 3}, {"B", "D"}), ({3, 4}, {"D", "E"})]
    assert idnames.infer(obs) == {1: ["A"], 2: ["B"], 3: ["D"], 4: ["E"]}


def test_infer_keeps_ambiguity():
    assert idnames.infer([({5, 6}, {"X", "Y"})]) == {5: ["X", "Y"], 6: ["X", "Y"]}


def test_categories():
    text = "[[Category:MH4U Rathian Quests]]\n[[Category:MH4U Low Rank Quests]]\n[[Category:MH4U Arena Quests]]"
    assert idnames.categories(text, "MH4U", {"Rathian", "Rathalos"}) == {"Rathian"}


def test_cli_refuses_repository_output(tmp_path):
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(repo, "ids.csv")
    assert cli.main(["idnames", "mh4u", str(tmp_path / "x"), "--cache", str(tmp_path), "--out", out]) == 2
    assert not os.path.exists(out)
