"""MH4U Extra Data readers (card*, otomo1) on generated data only (no game bytes)."""
from __future__ import annotations

import json
import struct

import pytest
from mhuc import cli, extdata


def make_otb(name: str = "Testcat", owner: str = "Maker", greeting: str = "Hi!", level: int = 7) -> bytes:
    head = bytearray(extdata.OTB_HEADER)
    head[8], head[0x0B], head[0x19] = level, 3, 2
    head[0x0C:0x0F] = bytes([10, 11, 12])
    head[0x1C:0x20] = bytes([1, 2, 3, 0xFF])
    head[0x20:0x24] = bytes([4, 5, 6, 0xFF])
    strings, offsets = b"", []
    for text in (owner, name, greeting):
        offsets.append(extdata.OTB_HEADER + 4 + len(strings))
        strings += text.encode("utf-16-le") + b"\0\0"
    table = extdata.OTB_HEADER + 4 + len(strings)
    return bytes(head) + struct.pack("<I", table) + strings + struct.pack("<3I", *offsets)


def make_slot(otb: bytes, file: str, last: int = 0x5A) -> bytes:
    slot = bytearray(extdata.OTOMO_SLOT)
    slot[:len(otb)] = otb
    slot[extdata.OTOMO_NAME:extdata.OTOMO_NAME + len(file)] = file.encode()
    slot[-1] = last
    return bytes(slot)


def test_card_layout_tiles_the_file():
    assert extdata.card_layout_problems() == []


def test_parse_otb_reads_fields_and_texts():
    rec = extdata.parse_otb(make_otb())
    assert (rec["level"], rec["forte"], rec["palico_id"]) == (7, 3, 2)
    assert rec["skills"]["quest"] == [10, 11, 12]
    assert (rec["owner"], rec["name"], rec["greeting"]) == ("Maker", "Testcat", "Hi!")
    assert rec["coat_rgb"] == [1, 2, 3] and rec["clothing_rgb"] == [4, 5, 6]


def test_parse_otb_rejects_bad_table():
    bad = bytearray(make_otb())
    struct.pack_into("<I", bad, extdata.OTB_HEADER, 0xFFFF)
    with pytest.raises(ValueError):
        extdata.parse_otb(bytes(bad))


def test_otomo_slots_skip_empty_and_read_names():
    data = make_slot(make_otb(), "ot001_xxx.otb", 0x11) + bytes(extdata.OTOMO_SLOT) \
        + make_slot(make_otb(name="Other"), "ot002_xxx.otb") + bytes(64)
    slots = extdata.otomo_slots(data)
    assert [(s["slot"], s["file"], s["name"]) for s in slots] == [(0, "ot001_xxx.otb", "Testcat"),
                                                                 (2, "ot002_xxx.otb", "Other")]
    assert slots[0]["last_byte"] == 0x11


def test_otomo_slot_with_stray_bytes_fails():
    slot = bytearray(make_slot(make_otb(), "ot001_xxx.otb"))
    slot[0x7E] = 1
    with pytest.raises(ValueError):
        extdata.otomo_slots(bytes(slot))


def test_card_summary_and_guild_quest():
    data = bytearray(extdata.CARD_SIZE)
    off, size, _ = extdata.CARD_SECTIONS["guild_quests"]
    rec = bytearray(size)
    rec[0:8] = "Ana".encode("utf-16-le") + b"\0\0"
    rec[0x28] = 0x51            # monster 1 id
    rec[0x28 + 9] = 3           # its spawn area
    rec[0x115] = 9              # area 1 map
    rec[0x128], rec[0x129], rec[0x12B] = 1, 140, 0x10
    data[off + size:off + 2 * size] = rec
    assert extdata.card_summary(bytes(data))["guild_quests"] == 1
    gq = extdata.parse_guild_quest(bytes(rec))
    assert gq["owner"] == "Ana" and gq["monsters"][0]["id"] == 0x51 and gq["monsters"][0]["spawn_area"] == 3
    assert gq["areas"][0]["map"] == 9 and gq["level"] == 140 and gq["monsters"][0]["frenzy"] == 0x10
    with pytest.raises(ValueError):
        extdata.card_summary(bytes(10))


def test_cli_extdata(tmp_path, capsys):
    path = tmp_path / "otomo1"
    path.write_bytes(make_slot(make_otb(), "ot001_xxx.otb") * 2)
    assert cli.main(["extdata", "check", "otomo", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"palicos": 2}
    assert cli.main(["extdata", "dump", "otomo", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)[1]["file"] == "ot001_xxx.otb"
