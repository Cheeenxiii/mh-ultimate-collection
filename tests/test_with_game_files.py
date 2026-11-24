"""The real contract: our readers and writers against the game's own files."""
from __future__ import annotations

import os
import struct

import pytest

from mhuc.crypto import dlccrypt
from mhuc.crypto.blowfish import Blowfish
from mhuc.formats import arc, romfs
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
