"""mhuc xfs on generated files only: both byte orders, nested objects, arrays, strings, resources."""
from __future__ import annotations

import json
import struct

import pytest
from mhuc import cli, xfs


def build(e: str, classes, root) -> bytes:
    """classes: [(dti_id, [(name, type, attr)])]; root: (class_index, [values per property])."""
    n = len(classes)
    defs, names = [], b""
    name_base = 4 * n + sum(8 + xfs.PROP_ENTRY * len(props) for _, props in classes)
    for dti_id, props in classes:
        d = struct.pack(e + "IHH", dti_id, 2 * len(props), 0)
        for name, t, attr in props:
            off = name_base + len(names)
            names += name.encode() + b"\0"
            d += struct.pack(e + "II", off, t << 24 | attr << 16 | 0) + b"\0" * 0x20
        defs.append(d)
    offsets, pos = [], 4 * n
    for d in defs:
        offsets.append(pos)
        pos += len(d)
    block = struct.pack(e + f"{n}I", *offsets) + b"".join(defs) + names
    magic = b"XFS\0" if e == "<" else b"\0SFX"
    header = magic + struct.pack(e + "HHIIII", 15, 1, 6, 0, n, len(block))
    return header + block + obj(e, classes, root)


def obj(e: str, classes, node) -> bytes:
    index, values = node
    body = b""
    for (_name, t, attr), v in zip(classes[index][1], values, strict=True):
        items = v if attr & xfs.ARRAY else [v]
        body += struct.pack(e + "I", len(items))
        for it in items:
            if t in xfs.OBJECTS:
                body += obj(e, classes, it)
            elif t in xfs.SCALARS:
                body += struct.pack(e + xfs.SCALARS[t], it)
            elif t in xfs.STRINGS:
                body += it.encode() + b"\0"
            elif t == 0x80:
                body += b"\2" + it[0].encode() + b"\0" + it[1].encode() + b"\0"
            else:
                c, k = xfs.FIXED[t]
                body += struct.pack(e + c * k, *it)
    head = struct.pack(e + "I", (0x8000 | index) << 16 | 1)
    return head + struct.pack(e + "I", 4 + len(body)) + body


CLASSES = [
    (0x4EC7B399, [("mNo", 0x06, 0), ("mName", 0x0E, 0), ("mItems", 0x01, xfs.ARRAY), ("mTex", 0x80, 0),
                  ("mPos", 0x14, 0)]),
    (0x00001234, [("mId", 0x05, 0), ("mNum", 0x04, 0), ("mRate", 0x0C, 0)]),
]
ROOT = (0, [7, "supply", [(1, [100, 2, 0.5]), (1, [101, 10, 1.0])], ("rTexture", "gui\\icon"), [1.0, 2.0, 3.0, 0.0]])


@pytest.mark.parametrize("e", ["<", ">"])
def test_round_trip_both_orders(e):
    x = xfs.read(build(e, CLASSES, ROOT))
    assert x.endian == ("little" if e == "<" else "big") and x.version == 15
    assert [p.name for p in x.classes[0].props] == ["mNo", "mName", "mItems", "mTex", "mPos"]
    assert x.classes[0].props[2].type_name == "class" and x.classes[0].props[2].attr == xfs.ARRAY
    r = x.root
    assert r["class"] == "0x4EC7B399" and r["mNo"] == 7 and r["mName"] == "supply"
    assert [i["mId"] for i in r["mItems"]] == [100, 101] and r["mItems"][1]["mRate"] == 1.0
    assert r["mTex"] == {"kind": 2, "class": "rTexture", "path": "gui\\icon"}
    assert r["mPos"] == [1.0, 2.0, 3.0, 0.0]


def test_size_mismatch_and_trailing_bytes_are_errors():
    good = build("<", CLASSES, ROOT)
    with pytest.raises(xfs.XfsError):
        xfs.read(good + b"\0")
    with pytest.raises(xfs.XfsError):
        xfs.read(b"NOPE" + good[4:])
    bad = bytearray(good)
    root_at = xfs.HEADER + struct.unpack_from("<I", good, 0x14)[0]
    struct.pack_into("<I", bad, root_at + 4, 3)  # wrong size field
    with pytest.raises(xfs.XfsError):
        xfs.read(bytes(bad))


def test_cli_dump(tmp_path, capsys):
    f = tmp_path / "supp_001.supp"
    f.write_bytes(build("<", CLASSES, ROOT))
    assert cli.main(["xfs", "dump", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["classes"][0]["props"][0] == {"name": "mNo", "type": "u32", "attr": 0}
    assert out["root"]["mItems"][0]["mNum"] == 2
