"""The effect resources and converters on one monster's archives: Rathian (em001) in all three games.

The whole-RomFS pass over every monster archive is in tests/test_with_game_files.py; this file is
the converter's contract on one monster the three games share, so it stays light: four archives.
"""
from __future__ import annotations

import pytest

from mhuc.formats import arc, classid, efl, mef, romfs

pytestmark = pytest.mark.game_files

ARCHIVES = {"mh4u": "/data/em001.arc", "mh3u": "/arc/enemy/em001.arc", "mhxx": "/arc/enemy/em001_00.arc"}
IDS = {classid.class_id(name): name for name in
       ("rMhMotionEffect", "rEffectSequence", "rProofEffectMotSequenceList", "rEffectList", "rProofEffectList")}


def _entries(dump, game: str):
    image = romfs.open_image(dump(game, "romfs.bin"))
    for f in image.files():
        if f.path == ARCHIVES[game]:
            return arc.read(image.read(f)).entries
    raise AssertionError(f"{ARCHIVES[game]} isn't in the dump")


def _of(entries, name: str) -> list[bytes]:
    type_id = classid.class_id(name)
    return [e.data for e in entries if e.type_id == type_id]


def test_mh4u_rathians_motion_effects_and_effect_lists_round_trip(dump):
    entries = _entries(dump, "mh4u")
    motion, lists = _of(entries, "rMhMotionEffect"), _of(entries, "rEffectList")
    assert (len(motion), len(lists)) == (2, 26)
    for data in motion:
        assert mef.read_mef(data).to_bytes() == data
    for data in lists:
        assert efl.read_efl(data).to_bytes() == data


def test_mh3u_rathians_effect_sequence_round_trips_and_its_effect_lists_convert(dump):
    entries = _entries(dump, "mh3u")
    sequences, lists = _of(entries, "rEffectSequence"), _of(entries, "rEffectList")
    assert (len(sequences), len(lists)) == (1, 19)
    for data in sequences:
        assert mef.read_esq(data).to_bytes() == data
    for data in lists:
        assert efl.read_efl(data).to_bytes() == data
        converted = efl.from_mh3u(data)
        assert efl.read_efl(converted).version == efl.EFL_VERSION["mh4u"]
        assert converted[efl.EFL_HEADER:] == data[efl.EFL_HEADER:], "the block is carried unchanged"


def test_mhxx_rathians_motion_effects_round_trip_and_its_effect_lists_convert(dump):
    entries = _entries(dump, "mhxx")
    sequences = _of(entries, "rProofEffectMotSequenceList")
    proofs, lists = _of(entries, "rProofEffectList"), _of(entries, "rEffectList")
    assert (len(sequences), len(proofs), len(lists)) == (5, 2, 43)
    for data in sequences:
        assert mef.read_psl(data).to_bytes() == data
    for data in proofs:
        assert efl.read_pel(data).to_bytes() == data
    for data in lists:
        assert efl.read_efl(data).to_bytes() == data
        converted = efl.from_mhxx(data)
        assert efl.read_efl(converted).version == efl.EFL_VERSION["mh4u"]
        assert converted[efl.EFL_HEADER:] == data[efl.EFL_HEADER:], "the block is carried unchanged"
