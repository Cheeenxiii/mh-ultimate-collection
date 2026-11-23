"""Check E1 (specs/emd.md) on generated .emd/.etd pairs (no game bytes)."""
from __future__ import annotations

import struct

from mhuc import arc, classid, cli, emd


def make_emd(parts=(0, 3), rows=(0, 1)) -> bytes:
    d = bytearray(0x200)
    d[:4] = b"emd\0"
    struct.pack_into("<I", d, 4 * 8, 0x100)
    p = 0x100
    for part, row in zip(parts, rows, strict=True):
        struct.pack_into("<5H", d, p, 1, 2, 1, row, part)
        p += emd.BODY
    struct.pack_into("<H", d, p, 0xFFFF)
    struct.pack_into("<I", d, 4 * 34, 0x180)
    struct.pack_into("<iHHII", d, 0x180, 4, 6, 0, 1, 0)
    struct.pack_into("<i", d, 0x190, -1)
    return bytes(d)


def make_etd() -> bytes:
    d = bytearray(0x200)
    d[:4] = b"etd\0"
    struct.pack_into("<I", d, 0x10, 4200)
    struct.pack_into("<I", d, 4 * 7, 0xA0)          # hitzone table 0xA0..0xC0: 32 bytes
    struct.pack_into("<I", d, 4 * 27, 0xC0)         # one attack-volume group
    struct.pack_into("<I", d, 4 * 28, 0xC4)         # attack records 0xC4..0x114: 2 records
    struct.pack_into("<I", d, 4 * 29, 0x114)
    struct.pack_into("<I", d, 0xC0, 0x140)
    struct.pack_into("<H", d, 0x140 + emd.HIT, 0xFFFF)  # one volume, then the end
    return bytes(d)


def test_check_emd_and_etd():
    c = emd.check_emd(make_emd())
    assert c["E1 emd magic emd\\0"] == 1 and c["E1 emd word 8 records"] == 2
    assert c["E1 emd body shape 1"] == 2 and c["E1 emd visibility rows"] == 1
    assert c["E1 emd visibility condition 6"] == 1
    t = emd.check_etd(make_etd())
    assert t["E1 etd base HP 1..100000"] == 1 and t["E1 etd attack volumes"] == 1
    assert t["E1 etd attack records"] == 2 and t["E1 etd attack records whole"] == 1
    assert t["E1 etd words 5-34: OUTSIDE"] == 0


def test_check_pair_row_size():
    c = emd.check_pair(make_emd(rows=(0, 1)), make_etd())
    assert c["E1 pair parts within 8"] == 1
    assert c["E1 pair hitzone table bytes / rows used = 16"] == 1


def test_unterminated_list_is_counted():
    bad = bytearray(make_emd())
    struct.pack_into("<I", bad, 4 * 8, 0x1F0)       # a list starting near the end never finds 0xFFFF
    assert emd.check_emd(bytes(bad))["E1 emd word 8 list doesn't end"] == 1


def test_cli_on_an_arc(tmp_path, capsys):
    entries = [arc.Entry("enemy\\em001\\data\\em001", classid.id_of_extension("emd"), make_emd()),
               arc.Entry("enemy\\em001\\data\\em001", classid.id_of_extension("etd"), make_etd())]
    path = tmp_path / "em_data.arc"
    path.write_bytes(arc.write(arc.Archive(0x11, entries)))
    assert cli.main(["emd", "check", str(path)]) == 0
    out = capsys.readouterr().out
    assert "E1 pairs: 1" in out and "E1 pair parts within 8: 1" in out
