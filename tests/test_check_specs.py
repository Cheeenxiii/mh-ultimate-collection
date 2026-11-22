"""tools/check_specs.py on synthetic specs, and on the repository's own."""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import check_specs  # noqa: E402

GOOD = """---
class: rThing
extension: thg
games: MH4U
status: unverified
---

# Thing

| Offset | Type | Name | Status | Source |
|---|---|---|---|---|
| 0x00 | u32 | magic | unverified | someone's template |
| 0x04 | u32 | id | verified | ours |

## Checks

- C1: done.
"""


def test_good_spec():
    assert check_specs.check_text("x.md", GOOD) == []


def test_missing_front_matter():
    assert "no front matter" in check_specs.check_text("x.md", "# no\n")[0]
    bad = GOOD.replace("games: MH4U\n", "")
    assert any("lacks games" in p for p in check_specs.check_text("x.md", bad))


def test_bad_status_and_source():
    bad = GOOD.replace("| unverified | someone's template |", "| maybe | someone's template |")
    assert any("status 'maybe'" in p for p in check_specs.check_text("x.md", bad))
    bad = GOOD.replace("| unverified | someone's template |", "| unverified |  |")
    assert any("no source" in p for p in check_specs.check_text("x.md", bad))


def test_status_higher_than_fields():
    bad = GOOD.replace("status: unverified", "status: verified")
    assert any("front matter says verified" in p for p in check_specs.check_text("x.md", bad))


def test_verified_needs_checks():
    bad = GOOD.split("## Checks")[0]
    assert any("no Checks section" in p for p in check_specs.check_text("x.md", bad))


def test_missing_column():
    bad = GOOD.replace("| Offset | Type | Name | Status | Source |\n|---|---|---|---|---|",
                       "| Offset | Name | Status | Source |\n|---|---|---|---|")
    assert any("lacks type" in p for p in check_specs.check_text("x.md", bad))


def test_ksy_needs_md(tmp_path):
    (tmp_path / "a.ksy").write_text("meta: {id: a}\n")
    assert check_specs.check_dir(str(tmp_path)) == ["a.ksy: no matching .md"]


def test_repository_specs_pass():
    assert check_specs.check_dir(os.path.join(ROOT, "specs")) == []
