"""mhuc.romfs and mhuc.survey on generated images only."""
from __future__ import annotations

import struct

import pytest
from mhuc import arc, classid, cli, gmd, romfs, survey, tex

NONE = 0xFFFFFFFF


def _name(s: str) -> bytes:
    b = s.encode("utf-16-le")
    return b + bytes(-len(b) % 4)


def build_level3(tree: dict) -> bytes:
    """A level-3 RomFS image from {"dir": {...}, "file": bytes}; hash tables are left empty."""
    dirs, files, data = [], [], bytearray()

    def walk(node: dict, name: str, parent: int) -> int:
        idx = len(dirs)
        dirs.append({"name": name, "parent": parent, "child": NONE, "file": NONE, "sibling": NONE})
        sub = [(k, v) for k, v in node.items() if isinstance(v, dict)]
        fls = [(k, v) for k, v in node.items() if not isinstance(v, dict)]
        prev = None
        for k, v in fls:
            fi = len(files)
            files.append({"name": k, "parent": idx, "sibling": NONE, "off": len(data), "size": len(v)})
            data.extend(v + bytes(-len(v) % 16))
            if prev is None:
                dirs[idx]["file"] = fi
            else:
                files[prev]["sibling"] = fi
            prev = fi
        prev = None
        for k, v in sub:
            ci = walk(v, k, idx)
            if prev is None:
                dirs[idx]["child"] = ci
            else:
                dirs[prev]["sibling"] = ci
            prev = ci
        return idx

    walk(tree, "", 0)
    doff, foff = [], []
    pos = 0
    for d in dirs:
        doff.append(pos)
        pos += 0x18 + len(_name(d["name"]))
    pos = 0
    for f in files:
        foff.append(pos)
        pos += 0x20 + len(_name(f["name"]))

    def ref(table, i):
        return NONE if i == NONE else table[i]

    dmeta = b"".join(struct.pack("<6I", doff[d["parent"]], ref(doff, d["sibling"]), ref(doff, d["child"]),
                                 ref(foff, d["file"]), NONE, len(d["name"]) * 2) + _name(d["name"]) for d in dirs)
    fmeta = b"".join(struct.pack("<IIQQII", doff[f["parent"]], ref(foff, f["sibling"]), f["off"], f["size"], NONE,
                                 len(f["name"]) * 2) + _name(f["name"]) for f in files)
    hash_table = struct.pack("<I", NONE)
    off = 0x28
    layout = []
    for blob in (hash_table, dmeta, hash_table, fmeta):
        layout += [off, len(blob)]
        off += len(blob)
    data_off = (off + 15) // 16 * 16
    out = struct.pack("<10I", 0x28, *layout, data_off) + hash_table + dmeta + hash_table + fmeta
    return out + bytes(data_off - len(out)) + bytes(data)


def wrap_ivfc(level3: bytes, master_hash_size: int = 0x20) -> bytes:
    head = bytearray(0x60)
    head[:4] = b"IVFC"
    struct.pack_into("<II", head, 4, 0x10000, master_hash_size)
    struct.pack_into("<I", head, 0x0C + 2 * 0x18 + 0x10, 12)   # level-3 block size 0x1000
    start = 0x1000
    return bytes(head) + bytes(start - 0x60) + level3


TREE = {"a.bin": b"hello", "arc": {"x.arc": b"ARC?", "deep": {"y.tex": b"0123456789"}}, "z.txt": b""}


@pytest.mark.parametrize("ivfc", [False, True])
def test_romfs_lists_and_reads(tmp_path, ivfc):
    img = build_level3(TREE)
    if ivfc:
        img = wrap_ivfc(img)
    p = tmp_path / "romfs.bin"
    p.write_bytes(img)
    r = romfs.open_image(p)
    files = {f.path: r.read(f) for f in r.files()}
    assert files == {"/a.bin": b"hello", "/z.txt": b"", "/arc/x.arc": b"ARC?", "/arc/deep/y.tex": b"0123456789"}


def test_romfs_level3_offset():
    assert romfs.level3_offset(b"\0" * 0x60) == 0
    assert romfs.level3_offset(wrap_ivfc(b"")[:0x60]) == 0x1000


def test_romfs_bad_header(tmp_path):
    p = tmp_path / "bad.bin"
    p.write_bytes(struct.pack("<10I", 0x30, *([0] * 9)))
    with pytest.raises(romfs.RomfsError):
        romfs.open_image(p)


def _sample_image(tmp_path):
    t = tex.write(tex.Texture(8, 8, "RGBA8", [bytes(range(256))]))
    g = gmd.write(gmd.Gmd("t", ["x"], {0: "L"}))
    m = b"MOD\0" + struct.pack("<H", 0xE6) + bytes(58)
    a = arc.write(arc.Archive(0x13, [
        arc.Entry("tex\\a", classid.class_id("rTexture"), t),
        arc.Entry("msg\\b", classid.class_id("rGUIMessage"), g),
        arc.Entry("mod\\c", classid.class_id("rModel"), m),
    ]))
    q = arc.write(arc.Archive(0x11, [arc.Entry("q\\r", classid.class_id("rRem"), b"r"),
                                     arc.Entry("q\\m", classid.class_id("rQuestData"), b"m")]))
    p = tmp_path / "romfs.bin"
    p.write_bytes(build_level3({"arc": {"a.arc": a, "q.arc": q}, "loose.gmd": g}))
    return p


def test_survey_counts(tmp_path):
    total = survey.survey(str(_sample_image(tmp_path)), workers=1)
    assert total["files"] == 3
    assert total["arc"]["C2 round trip ok"] == 2 and total["arc"]["version 0x13"] == 1
    assert total["tex"]["T1 size matches"] == 1 and total["tex"]["T3 round trip ok"] == 1
    assert total["gmd"]["G1 readable"] == 2 and total["gmd"]["G2 round trip ok"] == 2
    assert total["mod"]["version 0x00e6"] == 1
    assert total["quest"]["Q1 last entry rQuestData"] == 1
    assert total["quest"]["Q2 holds rQuestData+rRem"] == 1
    text = survey.report(total)
    assert "C2 round trip ok: 2" in text


def test_survey_tex_expected_size():
    t = tex.write(tex.Texture(16, 8, "ETC1", [bytes(64)]))
    assert survey.tex_expected_size(t) == len(t)


def test_cli_romfs_and_survey(tmp_path, capsys):
    p = _sample_image(tmp_path)
    assert cli.main(["romfs", "list", str(p)]) == 0
    assert "/arc/a.arc" in capsys.readouterr().out
    assert cli.main(["survey", str(p), "--workers", "1"]) == 0
    assert "files in image: 3" in capsys.readouterr().out
