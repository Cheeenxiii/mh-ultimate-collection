"""Tests marked `game_files` read the player's own files from the folder in MHUC_DUMPS:

    mh4u/romfs.bin      MH4U USA v1.3.0's RomFS
    mh4u/extdata/       its Extra Data files, encrypted (quest1, card1, otomo1, ...)
    mh4u/save.key       the save cipher's key

They are skipped when MHUC_DUMPS isn't set, so they never run in CI. They print nothing from the files.
"""
from __future__ import annotations

import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "game_files: needs the player's own game files (MHUC_DUMPS)")


@pytest.fixture
def dump():
    root = os.environ.get("MHUC_DUMPS")
    if not root:
        pytest.skip("MHUC_DUMPS isn't set")

    def path(*parts: str) -> str:
        p = os.path.join(root, *parts)
        if not os.path.exists(p):
            pytest.skip(f"{os.path.join(*parts)} isn't in MHUC_DUMPS")
        return p
    return path
