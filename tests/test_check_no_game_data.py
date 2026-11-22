"""tools/check_no_game_data.py on synthetic paths and contents."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import check_no_game_data as guard  # noqa: E402


def test_clean_text_passes():
    assert guard.problems("docs/design/x.md", b"# Title\n\nSome words.\n") == []


def test_rom_and_romfs_names_refused():
    assert "name" in guard.problems("stuff/game.cia", b"x")
    assert "name" in guard.problems("data/em/em001.arc", b"x")
    assert "name" in guard.problems("exefs/code.bin", b"x")
    assert "name" in guard.problems("baserom/readme.txt", b"x")


def test_binary_refused():
    assert "binary" in guard.problems("blob.dat", b"ARC\0\x13\0")
    assert "binary" in guard.problems("blob.txt", bytes([0xff, 0xfe, 0x80]))


def test_size_refused():
    assert "size" in guard.problems("big.txt", b"a" * (guard.MAX_SIZE + 1))


def test_hex_listing_refused():
    line = "00000000: " + " ".join(["4a"] * 16) + "\n"
    assert "listing" in guard.problems("dump.txt", (line * 60).encode())
    assert guard.problems("short.txt", (line * 10).encode()) == []


def test_main_reports(tmp_path, capsys):
    good = tmp_path / "a.md"
    good.write_text("hello\n")
    bad = tmp_path / "b.arc"
    bad.write_bytes(b"ARC\0")
    assert guard.main([str(good)]) == 0
    assert guard.main([str(good), str(bad)]) == 1
    assert "b.arc: name" in capsys.readouterr().out
