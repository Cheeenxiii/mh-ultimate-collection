"""reference/monster_versions.py: the player-visible rule must not drift.

The wiki's attack names differ between pages only by a translation marker or a qualifier, and
that normalization decides a `wiki` verdict, so it is pinned here with the verdict rule itself.
The game-file axes are compared through the dumps (tests marked `game_files`) or run by hand.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import monster_versions  # noqa: E402

URL = "https://monsterhunterwiki.org/wiki/Rathian_(MH4U)"


def test_attack_name_drops_the_marker_and_a_trailing_qualifier():
    assert monster_versions.attack_name("Bite (Unreviewed Translation)") == "Bite"
    assert monster_versions.attack_name("Bite n' Tail (Bite)") == "Bite n' Tail"
    assert monster_versions.attack_name("Fireball  (Left)") == "Fireball"
    assert monster_versions.attack_name("Bite n' Tail") == "Bite n' Tail"


def test_wiki_lists_that_differ_only_by_a_qualifier_are_the_same():
    attacks = {
        ("MH4U", "Rathian"): [("Bite", URL), ("Bite n' Tail (Bite)", URL)],
        ("MHGU", "Rathian"): [("Bite", URL), ("Bite n' Tail (Tail)", URL)],
    }
    verdict, detail, mh4u_url, src_url = monster_versions.wiki_visible(attacks, "Rathian", "MHGU")
    assert verdict == "same", detail
    assert mh4u_url == src_url == URL


def test_wiki_lists_that_add_or_lack_an_attack_differ():
    attacks = {
        ("MH4U", "Rathian"): [("Bite", URL), ("Running Backflip", URL)],
        ("MHGU", "Rathian"): [("Bite", URL), ("Fireball", URL)],
    }
    verdict, detail, _, _ = monster_versions.wiki_visible(attacks, "Rathian", "MHGU")
    assert verdict == "differs"
    assert "Running Backflip" in detail and "Fireball" in detail


def test_a_page_without_an_attack_list_is_not_compared():
    attacks = {("MH4U", "Rathian"): [("Bite", URL)]}
    verdict, detail, _, _ = monster_versions.wiki_visible(attacks, "Rathian", "MH3U")
    assert verdict == "not compared" and "no attack list" in detail


def test_verdict_needs_every_axis_same_or_any_axis_differing():
    assert monster_versions.verdict_of(("same", "same", "same", "same")) == "doesn't differ"
    assert monster_versions.verdict_of(("same", "differs", "same", "not compared")) == "differs"
    assert monster_versions.verdict_of(("same", "not compared", "same", "same")) == "not decided"
