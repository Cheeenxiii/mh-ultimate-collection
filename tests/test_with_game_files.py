"""The real contract: our readers and writers against the game's own files."""
from __future__ import annotations

import os
import struct

import pytest

from mhuc import monsterdata
from mhuc.crypto import dlccrypt
from mhuc.crypto.blowfish import Blowfish
from mhuc.formats import arc, dtbase, dtbparts, dttune, emstatus, hitdata, romfs
from mhuc.quests import mibwrite, quest

pytestmark = pytest.mark.game_files


def archives(path: str):
    image = romfs.open_image(path)
    for f in image.files():
        if f.path.endswith(".arc"):
            yield f.path, image.read(f)


def test_every_mh4u_archive_repacks_byte_for_byte(dump):
    failed = [name for name, data in archives(dump("mh4u", "romfs.bin")) if arc.write(arc.read(data)) != data]
    assert not failed, f"{len(failed)} archives differ, first: {failed[:3]}"


def test_every_mh4u_quest_rebuilds_with_the_same_fields(dump):
    checked, failed = 0, []
    for name, data in archives(dump("mh4u", "romfs.bin")):
        for e in arc.read(data).entries:
            if e.type_name == "rQuestData" and e.data[4:8] == b"v005":
                checked += 1
                model = mibwrite.mib4_model(e.data)
                rebuilt = mibwrite.mib4_build(model)
                if quest.parse_mib4(rebuilt) != quest.parse_mib4(e.data) or mibwrite.mib4_model(rebuilt) != model:
                    failed.append(f"{name}:{e.file_name}")
    assert checked, "no .mib found"
    assert not failed, f"{len(failed)} of {checked} quests change, first: {failed[:3]}"


MODES = {"quest": "quest", "card": "card", "otomo": "normal"}


def test_extra_data_files_reencrypt_byte_for_byte(dump):
    folder = dump("mh4u", "extdata")
    with open(dump("mh4u", "save.key"), "rb") as f:
        key = f.read().strip()
    checked = 0
    for name in sorted(os.listdir(folder)):
        mode = next((m for prefix, m in MODES.items() if name.startswith(prefix)), None)
        if mode is None:
            continue
        with open(os.path.join(folder, name), "rb") as f:
            original = f.read()
        first = original[:4] if mode == "card" else Blowfish(key).ecb_decrypt(original[:8], "<")
        seed = struct.unpack_from("<I", first)[0] >> 16             # card files keep 24 bytes in the clear
        plain = dlccrypt.mh4u_save_decrypt(original, key, mode)
        assert dlccrypt.mh4u_save_encrypt(plain, key, mode, seed) == original, name
        checked += 1
    assert checked, "no Extra Data file found"


def monster_entries(path: str):
    image = romfs.open_image(path)
    for f in image.files():
        if f.path.startswith("/arc/enemy/") and f.path.endswith(".arc"):
            yield f.path, arc.read(image.read(f)).entries


def test_every_mhxx_and_mh3u_monster_data_file_is_laid_out_to_its_last_byte(dump):
    """dttune.blocks, dtbase.blocks, dtbparts.blocks and emstatus.blocks raise unless the layout ends exactly at the
    file's end; hitdata raises unless the records tile the file (checks E2 to E4, E6)"""
    kinds = {b"BDD\0": "bdd", b"HTS\0": "hts", b"HDE\0": "hde", b"HTD\0": "htd"}
    counts = {"dttune": 0, "dtbase": 0, "dtbparts": 0, "em_status": 0, "hit data": 0}
    for game in ("mhxx", "mh3u"):
        for name, entries in monster_entries(dump(game, "romfs.bin")):
            for e in entries:
                try:
                    if e.data[:4] == dttune.MAGIC:
                        dttune.blocks(e.data)
                        counts["dttune"] += 1
                    elif e.data[:4] == dtbase.MAGIC:
                        dtbase.blocks(e.data)
                        counts["dtbase"] += 1
                    elif e.data[:4] == dtbparts.MAGIC:
                        dtbparts.blocks(e.data)
                        counts["dtbparts"] += 1
                    elif e.data[:4] == emstatus.MAGIC:
                        emstatus.blocks(e.data)
                        counts["em_status"] += 1
                    elif e.data[:4] in kinds:
                        kind = kinds[e.data[:4]]
                        hitdata.groups(e.data) if kind == "hts" else hitdata.records(e.data, kind)
                        counts["hit data"] += 1
                except ValueError as err:
                    pytest.fail(f"{name}:{e.file_name}: {err}")
    assert all(counts.values()), counts


def _entry(entries, type_id: int, *words: str) -> bytes:
    hits = [e.data for e in entries if e.type_id == type_id and all(w in e.path.replace("\\", "/") for w in words)]
    assert len(hits) == 1, (type_id, words, len(hits))
    return hits[0]


def test_rathian_hp_parts_and_hitzones_rebuild_from_mhxx_and_mh3u(dump):
    """The values the issue asks for: MH4U Rathian's base HP, part table and hitzone rows from MHXX's dttune; base HP
    and the hitzone rows MH4U didn't retune from MH3U's em_status (specs/dttune.md, specs/emstatus.md)"""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    em_data = next(arc.read(image.read(f)).entries for f in image.files() if f.path.endswith("em_data.arc"))
    mh4u = monsterdata.from_mh4u(_entry(em_data, 0x0A0E48D4, "em001"), _entry(em_data, 0x3D8BBBAC, "em001"))
    xx = dict(monster_entries(dump("mhxx", "romfs.bin")))["/arc/enemy/em001_00.arc"]
    rebuilt = monsterdata.from_mhxx(_entry(xx, 0x48E8AC29, "dt_tune/"), _entry(xx, 0x59D9C3DA, "dt_base/"),
                                    _entry(xx, 0x1BBC291E, "dt_base/"), _entry(xx, 0x1AC7B52D, "/body_data/"),
                                    _entry(xx, 0x1AC7B52D, "cam_body_data/"),
                                    _entry(xx, 0x5653C1B0, "enemy/hit_data/"), _entry(xx, 0x70BB64BA, "hit_data/"))
    for field in ("base HP", "part table", "hitzone table", "joint points", "joint records", "break parts"):
        assert rebuilt[field] == mh4u[field], f"MHXX {field} isn't MH4U's"
    assert len(mh4u["sever records"]) == 3 and rebuilt["sever records"] is None, \
        "MHXX's dtbase/dtbparts hold a block for MH4U's kind-0 (sever) records"
    sphere = sum(a == b for a, b in zip(rebuilt["map-hit sphere"], mh4u["map-hit sphere"], strict=False))
    assert sphere == 51, f"MHXX's map-hit sphere has {sphere} of 52 bytes in common with MH4U's, expected 51"
    u3 = dict(monster_entries(dump("mh3u", "romfs.bin")))["/arc/enemy/em001.arc"]
    status = _entry(u3, 0x4DEE8265, "em_status")
    rows = emstatus.block(status, "hitzone table")
    assert struct.unpack_from("<I", emstatus.block(status, "header"))[0] == mh4u["base HP"]
    same = [i for i in range(8) if rows[10 * i:10 * i + 10] == mh4u["hitzone table"][10 * i:10 * i + 10]]
    assert same == [0, 1, 3, 4, 6, 7], same
