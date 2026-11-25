"""mods/monster_motions: the C plugin's translation and pass-through, run on a fake host.

The test itself is C (mods/monster_motions/tests/test_motions.c), compiled and run here: the
plugin is native code and the host it talks to is the engine's API, not Python."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "mods", "monster_motions", "tests", "test_motions.c")


def fork_root() -> str | None:
    """The engine fork's checkout, through reference/fork.py (MH4U_FORK or a sibling)."""
    sys.path.insert(0, os.path.join(ROOT, "reference"))
    try:
        import fork  # noqa: E402
    except SystemExit:
        return None
    return fork.ROOT


def test_the_plugin_translates_a_ported_monsters_motion_numbers(tmp_path):
    cc = shutil.which("cc")
    if cc is None:
        pytest.skip("no C compiler")
    fork = fork_root()
    include = os.path.join(fork, "include") if fork else None
    if include is None or not os.path.exists(os.path.join(include, "mh4u_plugin.h")):
        pytest.skip("MH4UltimateDC-fork isn't checked out next to this repository (set MH4U_FORK)")
    binary = tmp_path / "test_motions"
    build = subprocess.run([cc, "-std=c99", "-Wall", "-Wextra", "-I", include, SOURCE, "-o", str(binary)],
                           capture_output=True, text=True)
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run([str(binary)], capture_output=True, text=True)
    assert run.returncode == 0, run.stdout + run.stderr
