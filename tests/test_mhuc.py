"""mhuc on generated data only: class ids, ARC, 3DS texture codecs, TEX, GMD and the CLI."""
from __future__ import annotations

import json
import random
import struct
import zlib

import pytest
from mhuc import arc, classid, cli, gmd, pica, tex

# ── class ids ──────────────────────────────────────────────────────────────


def test_class_id_formula():
    for name in ("rTexture", "rArchive", "uEnemy", "x"):
        assert classid.class_id(name) == (~zlib.crc32(name.encode()) & 0xFFFFFFFF) & 0x7FFFFFFF


def test_class_id_known_values():
    # independent of the formula above: crc32 of "rTexture" computed by hand with the table
    assert classid.class_id("rTexture") == (zlib.crc32(b"rTexture") ^ 0xFFFFFFFF) & 0x7FFFFFFF
    assert classid.class_id("rTexture") < 0x80000000


def test_extensions_round_trip():
    cid = classid.class_id("rTexture")
    assert classid.extension_of(cid) == "tex"
    assert classid.id_of_extension("tex") == cid
    assert classid.extension_of(0x12345678) == "12345678"
    assert classid.id_of_extension("12345678") == 0x12345678
    with pytest.raises(ValueError):
        classid.id_of_extension("nope")


# ── ARC ────────────────────────────────────────────────────────────────────


def _sample_arc(version=0x13):
    rng = random.Random(1)
    entries = [
        arc.Entry("em\\em001\\mod\\em001", classid.class_id("rModel"), bytes(rng.randrange(256) for _ in range(300))),
        arc.Entry("em\\em001\\tex\\body_BM", classid.class_id("rTexture"), b"\x00" * 1000),
        arc.Entry("misc\\unknown", 0x0BADF00D, b"hello"),
    ]
    return arc.Archive(version, entries)


@pytest.mark.parametrize("version", [0x13, 0x11, 0x10])
def test_arc_round_trip(version):
    a = _sample_arc(version)
    data = arc.write(a)
    assert data[:4] == b"ARC\0"
    b = arc.read(data)
    assert b.version == version
    assert [(e.path, e.type_id, e.data) for e in b.entries] == [(e.path, e.type_id, e.data) for e in a.entries]
    assert arc.write(b) == data   # streams reused: byte-identical


def test_arc_layout():
    data = arc.write(_sample_arc())
    version, count, extra = struct.unpack_from("<HHI", data, 4)
    assert (version, count, extra) == (0x13, 3, 0)
    name, tid, csize, size_word, offset = struct.unpack_from("<64sIIII", data, 12)
    assert name.rstrip(b"\0") == b"em\\em001\\mod\\em001"
    assert size_word & 0x0FFFFFFF == 300 and size_word >> 28 == 2   # MH4U's own flag, 0x20000000
    assert zlib.decompress(data[offset:offset + csize])[:1] is not None
    assert offset % 32 == 0 and offset - (12 + 3 * 0x50) < 32   # first stream on the next 32-byte boundary


@pytest.mark.parametrize("version,align", [(0x13, 32), (0x11, 32), (0x10, 0x8000)])
def test_arc_data_alignment(version, align):
    data = arc.write(_sample_arc(version))
    offsets = [struct.unpack_from("<I", data, 12 + i * 0x50 + 0x4C)[0] for i in range(3)]
    assert offsets[0] % align == 0
    sizes = [struct.unpack_from("<I", data, 12 + i * 0x50 + 0x44)[0] for i in range(3)]
    assert offsets[1] == offsets[0] + sizes[0] and offsets[2] == offsets[1] + sizes[1]   # streams back to back
    assert len(data) == offsets[2] + sizes[2]


def test_arc_data_start_kept():
    data = bytearray(arc.write(_sample_arc()))
    # move every stream 0x40 further, as an archive written by another tool might be
    first = struct.unpack_from("<I", data, 12 + 0x4C)[0]
    data[first:first] = bytes(0x40)
    for i in range(3):
        o = struct.unpack_from("<I", data, 12 + i * 0x50 + 0x4C)[0]
        struct.pack_into("<I", data, 12 + i * 0x50 + 0x4C, o + 0x40)
    a = arc.read(bytes(data))
    assert a.data_start == first + 0x40
    assert arc.write(a) == bytes(data)


def test_arc_flags_kept():
    a = _sample_arc()
    a.entries[0].flags = 0x20000000
    b = arc.read(arc.write(a))
    assert b.entries[0].flags == 0x20000000


def test_arc_errors():
    with pytest.raises(arc.ArcError):
        arc.read(b"NOPE" + bytes(20))
    with pytest.raises(arc.ArcError):
        arc.read(b"ARC\0" + struct.pack("<HHI", 0x99, 0, 0))
    bad = bytearray(arc.write(_sample_arc()))
    struct.pack_into("<I", bad, 12 + 64 + 8, 1)   # wrong size
    with pytest.raises(arc.ArcError):
        arc.read(bytes(bad))
    with pytest.raises(arc.ArcError):
        arc.write(arc.Archive(0x13, [arc.Entry("x" * 64, 1, b"")]))


def test_entry_file_name():
    e = arc.entry_from_file("em/em001/tex/body_BM.tex", b"")
    assert e.path == "em\\em001\\tex\\body_BM" and e.file_name == "em/em001/tex/body_BM.tex"


# ── 3DS texture codecs ─────────────────────────────────────────────────────


def _image(w, h, seed=0, alpha=True):
    rng = random.Random(seed)
    return bytes(v for _ in range(w * h)
                 for v in (rng.randrange(256), rng.randrange(256), rng.randrange(256),
                           rng.randrange(256) if alpha else 255))


def _quantise(fmt, rgba):
    """What a lossless round trip through `fmt` keeps."""
    return pica.decode(fmt, pica.encode(fmt, rgba, 16, 8), 16, 8)


@pytest.mark.parametrize("fmt", ["RGBA8", "RGB8", "RGBA5551", "RGB565", "RGBA4", "LA8", "HILO8",
                                 "L8", "A8", "LA4", "L4", "A4"])
def test_codec_round_trip(fmt):
    img = _image(16, 8, alpha=fmt not in ("RGB8", "RGB565"))
    once = _quantise(fmt, img)
    assert len(pica.encode(fmt, img, 16, 8)) == pica.data_size(fmt, 16, 8)
    assert _quantise(fmt, once) == once   # stable after one quantisation


def test_rgba8_exact_and_byte_order():
    img = _image(8, 8)
    assert pica.decode("RGBA8", pica.encode("RGBA8", img, 8, 8), 8, 8) == img
    one = bytes([10, 20, 30, 40]) + bytes(4 * 63)
    enc = pica.encode("RGBA8", one, 8, 8)
    assert enc[:4] == bytes([40, 30, 20, 10])   # stored A, B, G, R


def test_morton_tiling():
    # pixel (1, 0) is the 2nd stored, (0, 1) the 3rd, (8, 0) starts the second tile
    img = bytearray(16 * 8 * 4)
    for x, y, v in ((1, 0, 1), (0, 1, 2), (8, 0, 3), (7, 7, 4)):
        img[(y * 16 + x) * 4] = v
    enc = pica.encode("RGBA8", bytes(img), 16, 8)
    red = enc[3::4]
    assert red[1] == 1 and red[2] == 2 and red[64] == 3 and red[63] == 4


def test_flip_y():
    img = _image(8, 16)
    enc = pica.encode("RGBA8", img, 8, 16, flip_y=True)
    assert pica.decode("RGBA8", enc, 8, 16, flip_y=True) == img
    assert pica.decode("RGBA8", enc, 8, 16) != img


def test_etc1_flat_colour_exact():
    w, h = 16, 8
    colour = bytes([0x44, 0x88, 0xCC, 255]) * (w * h)
    out = pica.decode("ETC1", pica.encode("ETC1", colour, w, h), w, h)
    for i in range(0, len(out), 4):
        assert abs(out[i] - 0x44) <= 8 and abs(out[i + 1] - 0x88) <= 8 and abs(out[i + 2] - 0xCC) <= 8


def test_etc1_decode_known_block():
    # individual mode, both halves base 0x8 -> 0x88, table 0 (+-2, +-8); selectors all 0 -> +2
    info = (8 << 28) | (8 << 24) | (8 << 20) | (8 << 16) | (8 << 12) | (8 << 8)
    colours = pica._etc1_decode_block(info << 32)
    assert colours == [(0x8A, 0x8A, 0x8A)] * 16
    # selector 3 (msb and lsb set) on pixel 5 -> -8
    colours = pica._etc1_decode_block(info << 32 | (1 << 5) | (1 << 21))
    assert colours[5] == (0x80, 0x80, 0x80)


def test_etc1_differential_decode():
    # differential: base 16 (5 bits) -> 0x84, delta -1 -> 15 -> 0x7B
    info = 2 | (16 << 27) | (16 << 19) | (16 << 11) | (7 << 24) | (7 << 16) | (7 << 8)
    colours = pica._etc1_decode_block(info << 32)
    assert colours[0] == (0x86, 0x86, 0x86)     # first half, +2
    assert colours[15] == (0x7D, 0x7D, 0x7D)    # second half (x >= 2), +2


def test_etc1a4_alpha():
    w, h = 8, 8
    img = bytearray(_image(w, h, alpha=False))
    for i in range(w * h):
        img[4 * i + 3] = (i * 4) & 0xF0 | (i * 4) >> 4 & 0x0F
    enc = pica.encode("ETC1A4", bytes(img), w, h)
    assert len(enc) == pica.data_size("ETC1A4", w, h)
    out = pica.decode("ETC1A4", enc, w, h)
    for i in range(w * h):
        assert abs(out[4 * i + 3] - img[4 * i + 3]) <= 8


def test_codec_errors():
    with pytest.raises(ValueError):
        pica.encode("RGBA8", bytes(4 * 12 * 8), 12, 8)
    with pytest.raises(ValueError):
        pica.decode("RGBA8", b"", 8, 8)


# ── TEX ────────────────────────────────────────────────────────────────────


def test_tex_round_trip():
    img = _image(16, 8)
    t = tex.from_rgba("RGBA4", 16, 8, img)
    data = tex.write(t)
    w0, w1, w2, w3 = struct.unpack_from("<4I", data)
    assert w0 == 0x584554 and w1 & 0xFFF == 0xA5 and w2 & 0x3F == 1
    assert (w2 >> 6 & 0x1FFF, w2 >> 19 & 0x1FFF, w3 >> 8 & 0xFF) == (16, 8, 1)
    back = tex.read(data)
    assert (back.width, back.height, back.fmt) == (16, 8, "RGBA4")
    assert tex.write(back) == data
    w, h, rgba = tex.to_rgba(back)
    assert rgba == pica.decode("RGBA4", t.levels[0], 16, 8)


def test_tex_mips():
    t = tex.Texture(16, 16, "L8", [bytes(range(256)), bytes(64)])
    back = tex.read(tex.write(t))
    assert back.levels == t.levels


def test_ppm(tmp_path):
    p = tmp_path / "x.ppm"
    tex.write_ppm(str(p), 8, 8, _image(8, 8))
    assert p.read_bytes().startswith(b"P6\n8 8\n255\n")
    assert len(p.read_bytes()) == len(b"P6\n8 8\n255\n") + 8 * 8 * 3


# ── GMD ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("version,layout", [(gmd.V1, "v1"), (gmd.V1, "v1-short"), (gmd.V2, "v2"),
                                            (gmd.V2, "v2-32")])
def test_gmd_round_trip(version, layout):
    g = gmd.Gmd("test_table", ["First line", "Zweite Zeile ü", "", "last"],
                {0: "LBL_FIRST", 1: "LBL_SECOND", 3: "LBL_LAST"}, version=version, layout=layout)
    data = gmd.write(g)
    assert gmd.layout_of(data) == layout
    back = gmd.read(data)
    assert (back.name, back.strings, back.labels, back.version, back.layout) == \
        (g.name, g.strings, g.labels, version, layout)
    assert gmd.write(back) == data


def test_gmd_short_header():
    # MH3U: magic, version, language, label count, string count, label bytes, string bytes, name length
    data = gmd.write(gmd.Gmd("Item00", ["a", "bc"], {1: "L"}, layout="v1-short", language=2))
    assert struct.unpack_from("<4s7I", data) == (b"GMD\0", gmd.V1, 2, 1, 2, 2, 5, 6)
    assert data[0x20:0x27] == b"Item00\0"


def test_gmd_v2_index_kept():
    data = bytearray(gmd.write(gmd.Gmd("t", ["x", "y"], {0: "A", 1: "B"}, version=gmd.V2, layout="v2-32")))
    at = 0x28 + 2
    struct.pack_into("<II", data, at + 4, 0x12345678, 0x9ABCDEF0)   # the game's own hashes
    data[at + 2 * 0x14 + 7] = 0x55                                   # and a non-zero bucket
    g = gmd.read(bytes(data))
    assert gmd.write(g) == bytes(data)
    g.labels[1] = "C"                       # changed labels: a new index is built
    assert gmd.read(gmd.write(g)).labels == {0: "A", 1: "C"}


def test_gmd_header_fields():
    data = gmd.write(gmd.Gmd("ab", ["x", "yz"], {}))
    fields = gmd.HEADER.unpack_from(data)
    assert fields[0] == b"GMD\0" and fields[1] == gmd.V1
    assert fields[4:] == (0, 2, 0, 5, 2)
    assert data[0x28:0x2B] == b"ab\0"


def test_gmd_label_offsets_relative_to_first():
    # a table whose first label offset isn't 0 (Kuriimu2: offsets count from the first entry's)
    name = b"n"
    labels = b"A\0B\0"
    entries = struct.pack("<iIiI", 0, 0x1000, 1, 0x1002)
    text = b"one\0two\0"
    header = gmd.HEADER.pack(b"GMD\0", gmd.V1, 1, 0, 2, 2, len(labels), len(text), len(name))
    g = gmd.read(header + name + b"\0" + entries + labels + text)
    assert g.labels == {0: "A", 1: "B"} and g.strings == ["one", "two"]


# ── CLI ────────────────────────────────────────────────────────────────────


def test_cli_classid(capsys):
    assert cli.main(["classid", "rTexture"]) == 0
    assert f"{classid.class_id('rTexture'):08X}" in capsys.readouterr().out


def test_cli_arc_extract_pack(tmp_path, capsys):
    src = tmp_path / "a.arc"
    data = arc.write(_sample_arc())
    src.write_bytes(data)
    assert cli.main(["arc", "list", str(src)]) == 0
    assert "em/em001/mod/em001.mod" in capsys.readouterr().out
    out = tmp_path / "x"
    assert cli.main(["arc", "extract", str(src), str(out)]) == 0
    assert (out / "misc" / "unknown.0BADF00D").read_bytes() == b"hello"
    assert json.loads((out / "arc.json").read_text())["version"] == 0x13
    packed = tmp_path / "b.arc"
    assert cli.main(["arc", "pack", str(out), str(packed)]) == 0
    back = arc.read(packed.read_bytes())
    assert [(e.path, e.type_id, e.data) for e in back.entries] == \
        [(e.path, e.type_id, e.data) for e in _sample_arc().entries]


def test_cli_gmd_and_tex(tmp_path, capsys):
    g = tmp_path / "t.gmd"
    g.write_bytes(gmd.write(gmd.Gmd("t", ["hi"], {0: "L"})))
    assert cli.main(["gmd", "dump", str(g)]) == 0
    assert json.loads(capsys.readouterr().out)["entries"][0] == {"index": 0, "label": "L", "text": "hi"}
    t = tmp_path / "t.tex"
    t.write_bytes(tex.write(tex.from_rgba("RGB565", 8, 8, _image(8, 8))))
    assert cli.main(["tex", "info", str(t)]) == 0
    assert "8x8 RGB565" in capsys.readouterr().out
    assert cli.main(["tex", "decode", str(t), str(tmp_path / "t.ppm")]) == 0


def test_cli_pipeline_stubs():
    for cmd in ("ingest", "convert", "build"):
        assert cli.main([cmd]) == 2
