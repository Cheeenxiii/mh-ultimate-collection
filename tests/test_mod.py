"""MOD reader and check M3 on a generated model (no game bytes)."""
from __future__ import annotations

import json
import struct

from mhuc import cli, mod, survey


def make_mod(vertices=(3, 3), stride=12) -> bytes:
    meshes_at, n = 0x40, len(vertices)
    vb_at = meshes_at + mod.MESH * n
    vb_size = stride * sum(vertices)
    ib_at = vb_at + vb_size
    d = bytearray(ib_at + 2 * 6)
    d[:4] = b"MOD\0"
    struct.pack_into("<HHHHII", d, 4, 0xE6, 0, n, 1, sum(vertices), 6)
    struct.pack_into("<12I", d, 0x10, 0, 0, vb_size, 0, 1, 0, 0, 0x40, 0x40, meshes_at, vb_at, ib_at)
    start = 0
    for i, nv in enumerate(vertices):
        o = meshes_at + mod.MESH * i
        struct.pack_into("<HHIIIIIIII", d, o, 0, nv, 0, stride << 16, start, 0, 0xABCD, 3 * i, 3, 0)
        start += nv
    return bytes(d)


def test_info_and_check():
    i = mod.info(make_mod())
    assert i["meshes"] == 2 and i["strides"] == [12] and i["vertex_formats"] == [0xABCD]
    c = mod.check(make_mod())
    assert c["M3 mesh vertices sum to the header's"] == 1
    assert c["M3 index ranges inside the index buffer"] == 1
    assert c["M3 vertex streams inside the vertex buffer"] == 1


def test_check_flags_a_bad_sum():
    bad = bytearray(make_mod())
    struct.pack_into("<I", bad, 0x0C, 99)
    assert mod.check(bytes(bad))["M3 mesh vertices don't sum to the header's"] == 1
    st: dict = {}
    survey.survey_entry("rModel", bytes(bad), st)
    assert st["mod"]["version 0x00e6"] == 1 and st["mod"]["M3 readable"] == 1


def test_cli(tmp_path, capsys):
    p = tmp_path / "m.mod"
    p.write_bytes(make_mod())
    assert cli.main(["mod", "info", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["m.mod"]["meshes"] == 2
