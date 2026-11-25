"""Tests marked `game_files` read the player's own files from the folder in MHUC_DUMPS:

    mh4u/romfs.bin      MH4U USA's RomFS from the game itself, not the v1.3.0 update's: the update's
                        RomFS holds only the 20 archives it patches, and no quest
    mh4u/extdata/       its Extra Data files, encrypted (quest1, card1, otomo1, ...)
    mh4u/save.key       the save cipher's key: the NUL-terminated string at 0xE05E04 in the player's own
                        decompressed code (EUR v1.1 or USA v1.3.0, specs/extdata.md)
    mh4u/saves/         the character saves: system and user1 to user3, encrypted (specs/save.md)
    mhxx/romfs.bin      MHXX's RomFS from the game itself (JPN v1.0): the v4.8.0 update doesn't patch the
                        monster archives
    mh3u/romfs.bin      MH3U USA's RomFS

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
