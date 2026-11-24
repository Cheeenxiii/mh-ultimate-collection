"""Survey counts sound resources by kind, version and class id (specs/sound.md, check SN1)."""
from __future__ import annotations

import struct

from mhuc import survey
from mhuc.formats import arc, classid


def sound(magic: bytes, version: int) -> bytes:
    return magic + struct.pack("<I", version) + bytes(8)


def test_survey_counts_the_same_sound_kind_in_both_games_class_namespaces():
    """MH4U's rLtSoundBank and MHXX's rSoundBank are different ids and magics for one kind"""
    mh4u_bank = classid.class_id("rLtSoundBank")
    mhxx_bank = classid.class_id("rSoundBank")
    mhxx_wave = classid.class_id("rSoundSourceADPCM")
    data = arc.write(arc.Archive(version=0x13, entries=[
        arc.Entry(path="a\\snd", type_id=mh4u_bank, data=sound(b"SNDB", 11)),
        arc.Entry(path="a\\snd", type_id=mhxx_bank, data=sound(b"SBKR", 4)),
        arc.Entry(path="a\\wav", type_id=mhxx_wave, data=sound(b"MADP", 5)),
    ]))
    st: dict = {}
    survey.survey_arc(data, st)
    counts = st["sound"]
    assert counts["bank SNDB v11"] == 1
    assert counts["bank SBKR v4"] == 1
    assert counts["wave MADP v5"] == 1
    assert counts[f"bank SBKR type 0x{mhxx_bank:08x} rSoundBank"] == 1
    assert counts[f"wave MADP type 0x{mhxx_wave:08x} rSoundSourceADPCM"] == 1
    assert sum(n for k, n in counts.items() if k == "wave MADP v5") == 1


def test_survey_counts_a_loose_sound_file_that_has_no_class_id():
    st: dict = {}
    survey.survey_entry(None, sound(b"STQR", 4), st)
    counts = st["sound"]
    assert counts["stream request STQR v4"] == 1
    assert counts["stream request STQR loose"] == 1
    assert not [k for k in counts if "type 0x" in k]
