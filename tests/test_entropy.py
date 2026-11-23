"""mhuc entropy on generated data only."""
from __future__ import annotations

import random

from mhuc import cli, entropy


def test_entropy_bounds():
    assert entropy.entropy(b"") == 0.0
    assert entropy.entropy(b"\x00" * 1000) == 0.0
    assert abs(entropy.entropy(bytes(range(256)) * 16) - 8.0) < 1e-9
    assert abs(entropy.entropy(b"ab" * 500) - 1.0) < 1e-9


def test_verdicts():
    rnd = random.Random(1)
    noise = bytes(rnd.getrandbits(8) for _ in range(65536))
    text = b"Hunt a Rathalos in the Ancestral Steppe. " * 400
    assert entropy.measure("n", noise).verdict.startswith("dense")
    assert entropy.measure("t", text).verdict == "plain"
    assert entropy.measure("s", noise[:100]).verdict == "too small"
    # a short random file measures well under 8 bits per byte but is still dense
    short = entropy.measure("r", noise[:512])
    assert short.entropy < 7.8 and short.verdict.startswith("dense")
    assert entropy.measure("t2", text[:512]).verdict == "plain"
    assert 7.8 < entropy.dense_bar(1 << 20) <= entropy.DENSE


def test_block_alignment_and_zeros():
    m = entropy.measure("x", b"\x00\x01" * 8)
    assert m.block_aligned and m.zero_fraction == 0.5
    assert not entropy.measure("y", b"\x00" * 9).block_aligned


def test_walk_and_cli(tmp_path, capsys):
    rnd = random.Random(2)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "quest1").write_bytes(bytes(rnd.getrandbits(8) for _ in range(4096)))
    (tmp_path / "plain").write_bytes(b"\x00" * 4096)
    ms = entropy.walk([str(tmp_path)])
    assert [m.size for m in ms] == [4096, 4096]
    assert sorted(m.verdict for m in ms) == ["dense (encrypted or compressed)", "plain"]
    assert cli.main(["entropy", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "2 files, 1 dense" in out
