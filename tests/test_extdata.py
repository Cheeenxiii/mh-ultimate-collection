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


def test_set_otb_texts_moves_the_table():
    rec = make_otb(name="Cat")
    new = extdata.set_otb_texts(rec, name="A much longer name")
    got = extdata.parse_otb(new)
    assert (got["owner"], got["name"], got["greeting"]) == ("Maker", "A much longer name", "Hi!")
    assert new[:extdata.OTB_HEADER] == rec[:extdata.OTB_HEADER]
    table = struct.unpack_from("<I", new, extdata.OTB_HEADER)[0]
    offsets = struct.unpack_from("<3I", new, table)
    assert offsets[0] == 0x28 and all(o % 8 == 0 for o in offsets) and table % 4 == 0
    assert extdata.set_otb_texts(new) == new  # stable once in the game's layout
    with pytest.raises(ValueError):
        extdata.set_otb_texts(rec, greeting="x" * 60)


def test_rename_palico_keeps_other_slots(tmp_path, capsys):
    data = make_slot(make_otb(), "ot001_xxx.otb", 7) + make_slot(make_otb(name="Two"), "ot002_xxx.otb", 9)
    new = extdata.rename_palico(data, 1, "Renamed")
    assert new[:extdata.OTOMO_SLOT] == data[:extdata.OTOMO_SLOT]
    s = extdata.otomo_slots(new)[1]
    assert (s["name"], s["file"], s["hash_ok"]) == ("Renamed", "ot002_xxx.otb", True)
    assert not any("slot 1" in p for p in extdata.otomo_problems(new + bytes(64)))
    assert extdata.otomo_slots(extdata.rename_palico(data, 0, "X", last_byte=0))[0]["last_byte"] == 0
    with pytest.raises(ValueError):
        extdata.rename_palico(data + bytes(extdata.OTOMO_SLOT), 2, "X")
    src, out = tmp_path / "o", tmp_path / "o2"
    src.write_bytes(data)
    assert cli.main(["extdata", "rename", "otomo", str(src), "--slot", "0", "--name", "Y", "--out", str(out)]) == 0
    assert extdata.otomo_slots(out.read_bytes())[0]["name"] == "Y"


def test_put_otomo_slot_writes_hash_byte_and_tail():
    rec = make_otb()
    data = extdata.put_otomo_slot(bytes(0x21F8), 0, rec, "ot001_xxx.otb")
    digest = extdata.otomo_digest(rec)
    assert data[extdata.OTOMO_SLOT - 1] == digest[15]
    tail = data[extdata.OTOMO_SLOT:extdata.OTOMO_SLOT + extdata.OTOMO_TAIL]
    assert tail[:4] == digest[16:] and tail[8:] == struct.pack(">I", 0x94)
    assert extdata.otomo_problems(data) == []
    data = extdata.put_otomo_slot(data, 1, make_otb(name="Next"), "ot002_xxx.otb")  # the tail moves on
    assert [s["slot"] for s in extdata.otomo_slots(data)] == [0, 1] and extdata.otomo_problems(data) == []
    bad = extdata.put_otomo_slot(data, 1, make_otb(name="Next"), "ot002_xxx.otb", last_byte=digest[15] ^ 1)
    assert extdata.otomo_problems(bad) and not extdata.otomo_slots(bad)[1]["hash_ok"]


def test_cli_encrypt_round_trips(tmp_path, capsys):
    from mhuc import dlccrypt
    key, plain = tmp_path / "k", tmp_path / "p"
    key.write_bytes(b"synthetic test key")
    plain.write_bytes(bytes(range(256)) * 4)
    out = tmp_path / "e"
    assert cli.main(["encrypt", "mh4u-save", str(plain), str(out), "--key", str(key), "--seed", "0x4321"]) == 0
    enc = out.read_bytes()
    assert dlccrypt.mh4u_save_decrypt(enc, b"synthetic test key") == plain.read_bytes()
    assert enc == dlccrypt.mh4u_save_encrypt(plain.read_bytes(), b"synthetic test key", seed=0x4321)
