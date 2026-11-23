"""Blowfish, DLC crypto and quest readers on generated data only (no game bytes, no real keys)."""
from __future__ import annotations

import hashlib
import json
import struct

import pytest
from mhuc import arc, cli, dlccrypt, quest
from mhuc.blowfish import Blowfish, pi_words

KEY = b"synthetic test key"

# ── Blowfish ──────────────────────────────────────────────────────────────────


def test_pi_words():
    assert pi_words()[:2] == (0x243F6A88, 0x85A308D3)


@pytest.mark.parametrize("key,plain,cipher", [  # Eric Young's published test vectors
    ("0000000000000000", "0000000000000000", "4EF997456198DD78"),
    ("FFFFFFFFFFFFFFFF", "FFFFFFFFFFFFFFFF", "51866FD5B85ECB8A"),
    ("3000000000000000", "1000000000000001", "7D856F9A613063F2"),
])
def test_standard_vectors(key, plain, cipher):
    bf = Blowfish(bytes.fromhex(key))
    assert bf.ecb_encrypt(bytes.fromhex(plain)) == bytes.fromhex(cipher)
    assert bf.ecb_decrypt(bytes.fromhex(cipher)) == bytes.fromhex(plain)


def test_mt_variant_differs_and_round_trips():
    data = bytes(range(64))
    std, mt = Blowfish(KEY), Blowfish(KEY, mt=True)
    assert std.ecb_encrypt(data, "<") != mt.ecb_encrypt(data, "<")
    assert mt.ecb_decrypt(mt.ecb_encrypt(data, "<"), "<") == data


def test_ctr_is_its_own_inverse():
    bf, data = Blowfish(KEY), bytes(range(37))
    assert bf.ctr(bf.ctr(data, b"abcd", ">", "<"), b"abcd", ">", "<") == data


# ── DLC and Extra Data crypto ─────────────────────────────────────────────────


@pytest.mark.parametrize("mode", dlccrypt.MH4U_SAVE_MODES)
def test_mh4u_save_round_trip(mode):
    plain = bytes(range(256)) * 2 + b"\0" * 8
    enc = dlccrypt.mh4u_save_encrypt(plain, KEY, mode, seed=0xBEEF)
    assert dlccrypt.mh4u_save_decrypt(enc, KEY, mode) == plain
    with pytest.raises(dlccrypt.CryptoError):
        dlccrypt.mh4u_save_decrypt(enc, b"another key", mode)


@pytest.mark.parametrize("enc,dec", [
    (dlccrypt.mh4u_dlc_encrypt, dlccrypt.mh4u_dlc_decrypt),
    (dlccrypt.mh3u_dlc_encrypt, dlccrypt.mh3u_dlc_decrypt),
    (dlccrypt.mhxx_dlc_encrypt, dlccrypt.mhxx_dlc_decrypt),
])
def test_dlc_round_trips(enc, dec):
    for n in (1, 7, 8, 100):
        plain = bytes(range(n))
        assert dec(enc(plain, KEY), KEY) == plain
    with pytest.raises(dlccrypt.CryptoError):
        dec(enc(b"quest", KEY), b"another key")


def test_mh3u_and_mh4u_layouts_differ_only_in_the_cipher():
    a, b = dlccrypt.mh3u_dlc_encrypt(b"QTDS" * 9, KEY), dlccrypt.mh4u_dlc_encrypt(b"QTDS" * 9, KEY)
    assert len(a) == len(b) and a[-4:] == b[-4:] == struct.pack(">I", 36 + 20) and a != b


# ── MH4U .mib ─────────────────────────────────────────────────────────────────


def build_mib4(quest_id=60001) -> bytes:
    d = bytearray(0x400)
    struct.pack_into("<I4s", d, 0, 0xA0, b"v005")
    struct.pack_into("<I", d, 0x08, 0x100)                      # supply boxes
    struct.pack_into("<BBHI", d, 0x100, 0, 1, 0, 0x110)
    d[0x108] = 0xFF
    struct.pack_into("<HH", d, 0x110, 1, 2)
    struct.pack_into("<I", d, 0x1C, 0x120)                      # main reward box
    struct.pack_into("<BBHI", d, 0x120, 0, 0, 0, 0x128)
    struct.pack_into("<3HH", d, 0x128, 100, 5, 2, 0xFFFF)
    struct.pack_into("<2I", d, 0x28, 0x140, 0x180)              # large, small
    struct.pack_into("<2I", d, 0x140, 0x150, 0)                 # one wave
    struct.pack_into("<2IBB", d, 0x150, 7, 1, 0, 3)
    struct.pack_into("<3f", d, 0x160, 1.0, 2.0, 3.0)
    struct.pack_into("<I", d, 0x178, 0xFFFFFFFF)
    struct.pack_into("<3I", d, 0x180, 0x190, 0, 0)              # small: area list
    struct.pack_into("<2I", d, 0x190, 0x198, 0)
    struct.pack_into("<2I", d, 0x198, 20, 3)
    struct.pack_into("<I", d, 0x198 + 0x28, 0xFFFFFFFF)
    struct.pack_into("<I", d, 0x30, 0x200)                      # intruders: none
    struct.pack_into("<H", d, 0x200, 0xFFFF)
    struct.pack_into("<I", d, 0xBC, 0x260)                      # texts
    struct.pack_into("<5I", d, 0x260, *[0x280] * 5)
    struct.pack_into("<7I", d, 0x280, *[0x2A0 + 0x20 * i for i in range(7)])
    for i in range(7):
        s = f"text {i}".encode("utf-16-le")
        d[0x2A0 + 0x20 * i:0x2A0 + 0x20 * i + len(s)] = s
    struct.pack_into("<IHH", d, 0xCC, 1, 7, 1)
    struct.pack_into("<HHB", d, 0xC0, quest_id, 4, 11)
    struct.pack_into("<I", d, 0xB4, 50)
    return bytes(d)


def test_parse_mib4():
    q = quest.parse_mib4(build_mib4())
    assert q["quest_id"] == 60001 and q["stars"] == 4 and q["map"] == 11 and q["time_min"] == 50
    assert q["supply"] == [{"box": 0, "items": [(1, 2)]}]
    assert q["rewards"] == {"main": [(100, 5, 2)]}
    assert [m["monster"] for m in q["large_waves"][0]] == [7] and q["large_waves"][0][0]["pos"] == [1.0, 2.0, 3.0]
    assert [m["monster"] for m in q["small_areas"][0]] == [20]
    assert q["intruders"] == [] and q["objectives"][0] == {"type": 1, "target": 7, "count": 1}
    assert q["text"]["ger"]["client"] == "text 5"
    with pytest.raises(quest.QuestError):
        quest.parse_mib4(b"\0" * 0x100)


def test_mh4u_slots_and_cli(tmp_path, capsys):
    data = bytearray(40 * quest.SLOT + 120)
    for k, qid in ((0, 60001), (3, 60003)):
        s = k * quest.SLOT
        mib = build_mib4(qid)
        data[s:s + len(mib)] = mib
        name = f"m{qid:05d}.mib".encode()
        data[s + quest.SLOT_DATA:s + quest.SLOT_DATA + len(name)] = name
    slots = quest.mh4u_slots(bytes(data))
    assert [(k, n) for k, n, _ in slots] == [(0, "m60001.mib"), (3, "m60003.mib")]
    f = tmp_path / "quest1.bin"
    f.write_bytes(bytes(data))
    assert cli.main(["quest", "check", "mh4u", str(f)]) == 0
    assert "2 quests read, 0 files failed" in capsys.readouterr().out


def test_mh4u_pack_slot_round_trips(tmp_path, capsys):
    mib = build_mib4(60005)
    slot = quest.mh4u_pack_slot(mib, "m60005.mib", pad=b"\xAA" * 8)
    assert len(slot) == quest.SLOT and slot[quest.SLOT_DATA:].rstrip(b"\0") == b"m60005.mib"
    size = len(mib) + 20
    assert slot[size - 20:size - 18] == b"\0\0"
    assert struct.unpack(">I", slot[(size + 7) // 8 * 8:(size + 7) // 8 * 8 + 4])[0] == size
    assert quest.mh4u_slot_mib(slot[:quest.SLOT_DATA]) == mib
    bad = bytearray(slot)
    bad[0x40] ^= 1
    with pytest.raises(quest.QuestError):
        quest.mh4u_slot_mib(bytes(bad[:quest.SLOT_DATA]))
    data = quest.mh4u_put_slot(bytes(40 * quest.SLOT + 120), 2, slot)
    assert [(k, n) for k, n, _ in quest.mh4u_slots(data)] == [(2, "m60005.mib")]
    qf, mf, out = tmp_path / "q", tmp_path / "m60007.mib", tmp_path / "q2"
    qf.write_bytes(data)
    mf.write_bytes(build_mib4(60007))
    assert cli.main(["questslot", "put", str(qf), "--slot", "5", "--mib", str(mf), "--out", str(out)]) == 0
    capsys.readouterr()
    assert cli.main(["questslot", "check", str(out)]) == 0
    assert "2 used slots, 2 with a matching hash and size" in capsys.readouterr().out
    broken = tmp_path / "broken"
    broken.write_bytes(quest.mh4u_put_slot(data, 0, bytes(bad)))
    assert cli.main(["questslot", "check", str(broken)]) == 1


def test_mib4_patch_and_copy_slot(tmp_path, capsys):
    mib = build_mib4(60001)
    old = quest.parse_mib4(mib)
    new = quest.mib4_patch(mib, quest_id=60999, title="UC")
    got = quest.parse_mib4(new)
    assert got["quest_id"] == 60999 and len(new) == len(mib)
    assert all(t["title"] == "UC" for t in got["text"].values())
    assert got["text"]["eng"]["success"] == old["text"]["eng"]["success"]
    with pytest.raises(quest.QuestError):
        quest.mib4_patch(mib, title="x" * 200)
    qf, out = tmp_path / "q", tmp_path / "q2"
    qf.write_bytes(quest.mh4u_put_slot(bytes(40 * quest.SLOT + 120), 0, quest.mh4u_pack_slot(mib, "m60001.mib")))
    assert cli.main(["questslot", "put", str(qf), "--slot", "1", "--from-slot", "0", "--id", "60999",
                     "--title", "UC", "--out", str(out)]) == 0
    slots = quest.mh4u_slots(out.read_bytes())
    assert [(k, n) for k, n, _ in slots] == [(0, "m60001.mib"), (1, "m60999.mib")]
    assert cli.main(["questslot", "put", str(out), "--slot", "1", "--from-slot", "0", "--id", "60998",
                     "--out", str(out)]) == 1  # used slot, no --replace
    assert quest.parse_mib4(quest.mh4u_slot_mib(slots[1][2]))["quest_id"] == 60999


def test_mib4_model_build_round_trip():
    from mhuc import mibwrite
    mib = build_mib4(60002)
    model = mibwrite.mib4_model(mib)
    out = mibwrite.mib4_build(model)
    assert quest.parse_mib4(out) == quest.parse_mib4(mib)
    assert mibwrite.mib4_model(out) == model and mibwrite.mib4_build(mibwrite.mib4_model(out)) == out
    assert len(out) % 0x20 == 0
    longer = mibwrite.mib4_build(mibwrite.mib4_set_texts(model, 0, "A much longer title than before " * 3))
    got = quest.parse_mib4(longer)
    assert all(t["title"].startswith("A much longer") for t in got["text"].values())
    assert got["large_waves"] == quest.parse_mib4(mib)["large_waves"]
    with pytest.raises(quest.QuestError):
        mibwrite.mib4_build(dict(model, texts=model["texts"][:4]))


def test_questslot_put_long_title_rebuilds(tmp_path, capsys):
    mib = build_mib4(60001)
    qf, out = tmp_path / "q", tmp_path / "q2"
    qf.write_bytes(quest.mh4u_put_slot(bytes(40 * quest.SLOT + 120), 0, quest.mh4u_pack_slot(mib, "m60001.mib")))
    title = "A title far longer than the synthetic one"
    assert cli.main(["questslot", "put", str(qf), "--slot", "1", "--from-slot", "0", "--id", "60998",
                     "--title", title, "--out", str(out)]) == 0
    body = quest.mh4u_slots(out.read_bytes())[1][2]
    got = quest.parse_mib4(quest.mh4u_slot_mib(body))
    assert got["quest_id"] == 60998 and got["text"]["ita"]["title"] == title


# ── MHXX ──────────────────────────────────────────────────────────────────────


def build_mibxx(quest_id=1010001) -> bytes:
    d = bytearray(249)
    struct.pack_into("<4sIII", d, 0, b"\0\0KC", 1, 0, quest_id)
    d[0x10:0x18] = bytes((1, 10, 6, 3, 2, 1, 50, 3))
    struct.pack_into("<BHH", d, 0x1F, 1, 25, 1)
    struct.pack_into("<H", d, 0x64, 25)
    struct.pack_into("<I", d, 0xDF, 0x242BB29A)
    d[0xE3:0xEE] = f"{quest_id}_jpn".encode()
    return bytes(d)


def build_esl(areas) -> bytes:
    body, offs, pos = b"", [], 0x40
    for ents in areas:
        offs.append(pos)
        a = b"ESD\0" + struct.pack("<IH", 20151214, len(ents))
        for mid, xyz in ents:
            e = bytearray(36)
            e[0], e[1] = mid, 0x10
            struct.pack_into("<3f", e, 0x0C, *xyz)
            a += bytes(e)
        body += a
        pos += len(a)
    return b"esl\0" + struct.pack("<I14I", 2, *(offs + [0] * (14 - len(offs)))) + body


def test_mhxx_parts():
    q = quest.parse_mibxx(build_mibxx())
    assert q["quest_id"] == 1010001 and q["time_min"] == 50 and q["message"] == "1010001_jpn"
    assert q["objectives"][0] == {"type": 1, "target": 25, "count": 1} and q["bosses"][0] == 25
    sem = struct.pack("<fIIIffff", 1.0, 1, 0, 3, 0.5, 1.0, 2.0, 3.0)
    assert quest.parse_sem(sem)["area"] == 3
    esl = build_esl([[(12, (1.0, 2.0, 3.0))], [(13, (0.0, 0.0, 0.0)), (14, (4.0, 5.0, 6.0))]])
    areas = quest.parse_esl(esl)
    assert [[e["monster"] for e in a] for a in areas] == [[12], [13, 14]] and areas[1][1]["pos"] == [4.0, 5.0, 6.0]
    assert quest.parse_esl(build_esl([])) == []
    with pytest.raises(quest.QuestError):
        quest.parse_esl(esl + b"\0")
    rem = struct.pack("<fI", 1.0, 1) + struct.pack("<2B", 1, 2) + b"\0" * 14
    rem += struct.pack("<HBBHBB", 5, 1, 60, 6, 1, 40)
    rem += b"\0" * (0xB8 - len(rem))
    assert quest.parse_rem(rem)["slots"][:2] == [(5, 1, 60), (6, 1, 40)]
    supp = struct.pack("<fI", 1.0, 1) + struct.pack("<HBB", 7, 10, 0) + b"\0" * 156
    assert quest.parse_supply(supp)[0] == (7, 10, 0)


def test_mhxx_cli_dump(tmp_path, capsys):
    entries = [arc.entry_from_file("quest/zako/emSetList/z_m00d_000.esl", build_esl([])),
               arc.entry_from_file("quest/questData/questData_1010001.mib", build_mibxx())]
    f = tmp_path / "q1010001.arc"
    f.write_bytes(arc.write(arc.Archive(0x11, entries)))
    assert cli.main(["quest", "dump", "mhxx", str(f)]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["q1010001.arc"]["mib"]["quest_id"] == 1010001 and out["q1010001.arc"]["esl"] == {"z_m00d_000.esl": []}


# ── MH3U QTDS ─────────────────────────────────────────────────────────────────


def build_qtds(number=20102) -> bytes:
    def text(s):
        return b"".join(struct.pack("<I", len(x)) + x for x in (f"{s} {lang}".encode() for lang in quest.QTDS_LANGS))

    d = b"QTDS" + struct.pack("<I", 5) + text("name") + struct.pack("<H", number) + text("objective")
    d += struct.pack("<BB", 3, 1) + text("sub") + struct.pack("<H", 50) + text("failure") + struct.pack("<3H", 0, 0, 0)
    d += text("client") + text("description")
    tail = bytearray(quest.TAIL)
    struct.pack_into("<11B", tail, 0x0A, 9, 0, 0, 1, 20, 30, 40, 0, 100, 0, 1)
    struct.pack_into("<HBB", tail, 0x47, 100, 1, 50)                    # table A, slot 0
    struct.pack_into("<HBB", tail, 0x4B, 200, 2, 50)                    # table B, slot 1
    struct.pack_into("<5i", tail, 0x147, 300, 3000, 1000, 100, 0)
    struct.pack_into("<H", tail, 0x193, 0)
    struct.pack_into("<IHh", tail, 0x195, 1, 9, 1)
    d += bytes(tail)
    if quest.has_arena_block(number):
        d += struct.pack("<I", 1) + b"\0" * quest.EM_SET + struct.pack("<I", 1) + struct.pack("<86H", *range(86))
    return d


def test_parse_qtds():
    q = quest.parse_qtds(build_qtds())
    assert q["number"] == 20102 and q["name"]["ita"] == "name ita" and q["time_min"] == 50
    assert q["monsters"][0]["type"] == 9 and q["rewards_a"] == [(100, 1, 50)] and q["rewards_b"] == [(200, 2, 50)]
    assert q["fee"] == 300 and q["objectives"][0] == {"param": 1, "target": 9, "count": 1}
    assert q["arena_monster_sets"] == 1 and q["arena_gear_sets"][0][:3] == [0, 1, 2]
    assert q["size"] == len(build_qtds())
    plain = quest.parse_qtds(build_qtds(10101))
    assert "arena_gear_sets" not in plain and plain["size"] == len(build_qtds(10101))


def test_mh3u_slots():
    rec = build_qtds()
    body = bytearray(rec + hashlib.sha1(rec).digest())
    body[len(rec):len(rec) + 2] = b"\0\0"           # the game zeroes the hash's first two bytes
    size = len(body)
    body += b"\x5A" * (-size % 8)                    # padding left as ciphertext: not zeros
    body += struct.pack(">I", size)
    data = bytearray(4 + 20 * quest.SLOT)
    struct.pack_into("<I", data, 0, 44)
    data[4 + quest.SLOT:4 + quest.SLOT + len(body)] = body
    data[4 + quest.SLOT + quest.SLOT_DATA:4 + quest.SLOT + quest.SLOT_DATA + 13] = b"q_20102.quest"
    slots = quest.mh3u_slots(bytes(data))
    assert [(k, n) for k, n, _ in slots] == [(1, "q_20102.quest")] and slots[0][2] == rec


def test_decrypt_cli(tmp_path, capsys):
    key, plain = tmp_path / "k.key", build_qtds()
    key.write_bytes(KEY + b"\n")
    enc = tmp_path / "q.quest"
    enc.write_bytes(dlccrypt.mh3u_dlc_encrypt(plain, KEY))
    out = tmp_path / "q.dec"
    assert cli.main(["decrypt", "mh3u-dlc", str(enc), str(out), "--key", str(key)]) == 0
    assert out.read_bytes() == plain
    key.write_bytes(b"wrong")
    assert cli.main(["decrypt", "mh3u-dlc", str(enc), str(out), "--key", str(key)]) == 1
