"""The repository rules: no game data, and specs that say how sure each field is."""
from __future__ import annotations

import os
import subprocess
import sys

import check_no_game_data as guard
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.parametrize("path, data, rule", [
    ("game/code.bin", b"text", "name"),
    ("dumps/notes.txt", b"text", "name"),
    ("notes/rom.cia", b"text", "name"),
    ("notes/blob.txt", b"abc\0def", "binary"),
    ("notes/big.txt", b"a" * ((1 << 20) + 1), "size"),
    ("notes/dump.txt", b"".join(b"%06x: " % i + b"00 11 22 33 44 55 66 77 88 99\n" for i in range(60)), "listing"),
])
def test_guard_refuses_game_files_and_what_looks_derived_from_them(path, data, rule):
    assert rule in guard.problems(path, data)


def test_guard_accepts_prose_and_the_reference_function_tables():
    assert guard.problems("docs/notes.md", b"# Notes\n\nSome words.\n") == []
    table = b"address\tsize\n" + b"0x00100000\t0x10\n" * 80_000
    assert guard.problems("reference/games/mhxx/functions.tsv", table) == []


@pytest.mark.parametrize("script", ["check_no_game_data.py", "check_specs.py", "check_ids.py",
                                    "check_text.py"])
def test_repository_passes_its_own_checks(script):
    res = subprocess.run([sys.executable, os.path.join(ROOT, "tools", script)], cwd=ROOT,
                         capture_output=True, text=True)
    assert res.returncode == 0, res.stdout + res.stderr
