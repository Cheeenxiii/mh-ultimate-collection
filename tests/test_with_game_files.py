"""The real contract: our readers and writers against the game's own files."""
from __future__ import annotations

import hashlib
import math
import os
import re
import struct
from collections import Counter

import pytest

from mhuc import cli, monsterdata, monstersound
from mhuc.crypto import dlccrypt
from mhuc.crypto.blowfish import Blowfish
from mhuc.formats import (
    arc,
    camera,
    classid,
    dtbase,
    dtbparts,
    dttune,
    efl,
    emd,
    emstatus,
    hitdata,
    lmt,
    mef,
    mod,
    romfs,
    sound,
    stq,
    xfs,
)
from mhuc.quests import mibwrite, quest

pytestmark = pytest.mark.game_files


def archives(path: str):
    image = romfs.open_image(path)
    for f in image.files():
        if f.path.endswith(".arc"):
            yield f.path, image.read(f)


def test_every_mh4u_archive_repacks_byte_for_byte(dump):
    checked, failed = 0, []
    for name, data in archives(dump("mh4u", "romfs.bin")):
        checked += 1
        if arc.write(arc.read(data)) != data:
            failed.append(name)
    assert checked, "no .arc found"
    assert not failed, f"{len(failed)} of {checked} archives differ, first: {failed[:3]}"


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


# names match by prefix, so cardbox comes before card
MODES = {"quest": "quest", "cardbox": "normal", "card": "card", "otomo": "normal"}


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


def test_mh4u_saves_reencrypt_and_their_structures_close(dump):
    """specs/save.md checks S1 and S3 to S7: each file re-encrypts byte for byte, and the structures tile."""
    from mhuc import save

    folder = dump("mh4u", "saves")
    with open(dump("mh4u", "save.key"), "rb") as f:
        key = f.read().strip()
    names = [n for n in ("system", "user1", "user2", "user3") if os.path.exists(os.path.join(folder, n))]
    assert names, "no save file found"
    characters = 0
    for name in names:
        with open(os.path.join(folder, name), "rb") as f:
            original = f.read()
        first = Blowfish(key).ecb_decrypt(original[:8], "<")
        seed = struct.unpack_from("<I", first)[0] >> 16
        plain = dlccrypt.mh4u_save_decrypt(original, key)
        assert dlccrypt.mh4u_save_encrypt(plain, key, "normal", seed) == original, name
        if len(plain) == save.CHARACTER_SIZE:
            problems = save.character_problems(plain)
            assert not problems, f"{name}: {problems[:3]}"
            data = save.dump_character(plain)
            assert data["profile"]["name"], f"{name}: the character has no name"
            assert len(data["monster_log"]) == 82, name
            assert len(data["guild_quests"]) == 10, name
            assert len(data["palicos"]) >= 1, name
            assert data["profile"]["hunter_rank"] <= 999, name
            # S8: every item id the save holds has its bit in the 2,176-bit array at 0xF220.
            held = {slot["item"] for slot in data["item_box"]}
            for pouch in data["pouches"].values():
                held |= {slot["item"] for slot in pouch if slot["item"]}
            assert all((plain[save.ITEM_FLAGS_AT + (i >> 3)] >> (i & 7)) & 1 for i in held), \
                f"{name}: an item id the save holds has no flag bit"
            candidate = data["quest_lists"]["candidate_clear_flags"]
            assert 0 <= candidate["set_bits"] <= 512, name
            characters += 1
        else:
            assert not save.system_problems(plain), name
            system = save.system_summary(plain)
            assert system["word_0x38"] == 1, name
            assert system["character_0x3c"] in (None, 0, 1, 2), name
    assert characters >= 1, "no character save found"


def test_every_mh4u_stream_request_reads_and_matches_the_wave_it_names(dump):
    """specs/sound.md check S4: every .stq's tables and names close, and each stream record's length, sample count,
    channels, rate and loop start/end are the .mca header's own"""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    files = {f.path: f for f in image.files()}
    stqs = [f for f in files.values() if f.path.lower().endswith(".stq")]
    assert stqs, "no .stq found"
    streams = sequences = 0
    for f in stqs:
        s = stq.read(image.read(f))
        ids = [q.id for q in s.sequences]
        assert ids == sorted(ids) and len(set(ids)) == len(ids), f"{f.path}: request ids aren't unique and ascending"
        assert {q.stream for q in s.sequences if q.stream is not None} == set(range(len(s.streams))), \
            f"{f.path}: a stream isn't used"
        sequences += len(s.sequences)
        for stream in s.streams:
            path = "/" + stream.name.replace("\\", "/") + ".mca"
            assert path in files, f"{f.path}: {stream.name} isn't in the RomFS"
            wave = image.read(files[path])
            samples, rate, loop_start, loop_end = struct.unpack_from("<4I", wave, 0x0C)
            got = (stream.size, stream.samples, stream.channels, stream.rate, stream.loop_start, stream.loop_end)
            assert got == (len(wave), samples, wave[8], rate, loop_start, loop_end), f"{f.path}: {stream.name}"
            streams += 1
    assert streams >= 400, f"{streams} streams in {len(stqs)} .stq"
    assert sequences >= 1000, f"{sequences} sequences in {len(stqs)} .stq"


def monster_entries(path: str):
    image = romfs.open_image(path)
    for f in image.files():
        if f.path.startswith("/arc/enemy/") and f.path.endswith(".arc"):
            yield f.path, arc.read(image.read(f)).entries


def test_every_mhxx_and_mh3u_monster_data_file_is_laid_out_to_its_last_byte(dump):
    """dttune.blocks, dtbase.blocks, dtbparts.blocks and emstatus.blocks raise unless the layout ends exactly at the
    file's end; hitdata raises unless the records tile the file (checks E2 to E4, E7)"""
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


def test_rathian_attack_records_rebuild_from_mh3u(dump):
    """specs/hitdata.md HTD: MH3U's 32-byte records carry MH4U's bytes 0x00-0x11, the volume group, the +0x16 count
    and the signed byte (check E8); the other MH4U bytes don't come back"""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    em_data = next(arc.read(image.read(f)).entries for f in image.files() if f.path.endswith("em_data.arc"))
    mh4u = monsterdata.from_mh4u(_entry(em_data, 0x0A0E48D4, "em001"), _entry(em_data, 0x3D8BBBAC, "em001"))
    u3 = dict(monster_entries(dump("mh3u", "romfs.bin")))["/arc/enemy/em001.arc"]
    rebuilt = monsterdata.from_mh3u(_entry(u3, 0x4DEE8265, "em_status"), _entry(u3, 0x1AC7B52D, "em_body"),
                                    _entry(u3, 0x1AC7B52D, "em_cambody"), _entry(u3, 0x5653C1B0, "em_hitsize"),
                                    _entry(u3, 0x0C6016B9, "em_hitdata"))
    got, want = rebuilt["attack records"], mh4u["attack records"]
    assert len(got) == 45, len(got)

    def shared(r: bytes) -> bytes:
        return r[:0x12] + r[0x19:0x1B] + r[0x1D:0x1E]

    assert sum(shared(a) == shared(b) for a, b in zip(got, want, strict=False)) == 19
    assert sum(a[0x19] == b[0x19] for a, b in zip(got, want, strict=False)) == 38
    assert sum(a[0x1A] == b[0x1A] for a, b in zip(got, want, strict=False)) == 42
    assert sum(a[0x1D] == b[0x1D] for a, b in zip(got, want, strict=False)) == 37


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


def test_rathian_part_record_rebuilds_from_mh3u(dump):
    """specs/emstatus.md, "Part record mapping": MH3U's part HP and 6-byte break record rebuild MH4U's 10-byte part
    record. On Rathian the part HPs agree on 5 parts (MH4U retuned 3), the break record's four bytes on all 8, and the
    second-level HP on 7 (MH4U retuned the tail's); 3U has no kind field for MH4U's last u16."""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    em_data = next(arc.read(image.read(f)).entries for f in image.files() if f.path.endswith("em_data.arc"))
    mh4u = monsterdata.from_mh4u(_entry(em_data, 0x0A0E48D4, "em001"), _entry(em_data, 0x3D8BBBAC, "em001"))
    u3 = dict(monster_entries(dump("mh3u", "romfs.bin")))["/arc/enemy/em001.arc"]
    rebuilt = monsterdata.from_mh3u(_entry(u3, 0x4DEE8265, "em_status"), _entry(u3, 0x1AC7B52D, "em_body"),
                                    _entry(u3, 0x1AC7B52D, "em_cambody"), _entry(u3, 0x5653C1B0, "em_hitsize"),
                                    _entry(u3, 0x0C6016B9, "em_hitdata"))
    got = [struct.unpack_from("<HBBBBHH", rebuilt["part table"], 10 * i) for i in range(8)]
    want = [struct.unpack_from("<HBBBBHH", mh4u["part table"], 10 * i) for i in range(8)]
    hp = sum(a[0] == b[0] for a, b in zip(got, want, strict=True))
    assert hp == 5, f"MH3U's part HP agrees with MH4U's on {hp} of 8 parts, expected 5 (MH4U retuned 3)"
    assert all(a[1:5] == b[1:5] for a, b in zip(got, want, strict=True)), \
        "MH3U's break record bytes aren't MH4U's part bytes 2 to 5"
    second = sum(a[5] == b[5] for a, b in zip(got, want, strict=True))
    assert second == 7, f"MH3U's second-level HP agrees with MH4U's on {second} of 8 parts, expected 7"
    assert all(a[6] == 0 for a in got), "MH3U has no kind field, so the rebuilt kind must stay 0"


def test_mh4u_part_kinds_count_what_the_insect_glaive_reader_returns(dump):
    """specs/emd.md, check E13: MH4U's 0x936904 returns a part record's kind byte. Over all 110 .etd files the kind
    is 0 on 236 of 880 parts, 1 on 189, 2 on 141, 3 on 256 and 4 on 58; em081 is the only file whose eight are 0."""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    em_data = next(arc.read(image.read(f)).entries for f in image.files() if f.path.endswith("em_data.arc"))
    counts = Counter()
    all_zero = []
    for e in em_data:
        if e.type_id != 0x3D8BBBAC:
            continue
        counts.update(emd.check_etd(e.data))
        if not any(emd.part_kinds(e.data) or []):
            all_zero.append(e.path.replace("\\", "/").split("/")[-1])
    assert counts["E13 etd parts"] == 880, counts["E13 etd parts"]
    got = [counts[f"E13 etd part kind {k}"] for k in range(5)]
    assert got == [236, 189, 141, 256, 58], got
    assert "E13 etd part kind above 4" not in counts and "E13 etd part kind high byte nonzero" not in counts
    assert all_zero == ["em081"], all_zero


def test_only_four_mh3u_status_files_carry_the_second_level_hp_block(dump):
    """specs/emstatus.md, "Part record mapping": block 0x6C has no MH4U pair because the four files that carry it are
    Jhen Mohran, Duramboros, Rust Duramboros and Hallowed Jhen Mohran, which MH4U does not have
    (reference/README.md, "MH3U's ids to MH4U's")."""
    with_block = sorted({name for name, entries in monster_entries(dump("mh3u", "romfs.bin"))
                         for e in entries
                         if e.data[:4] == emstatus.MAGIC
                         and "block 0x6c" in {n for n, _, _ in emstatus.blocks(e.data)}})
    assert with_block == ["/arc/enemy/em025.arc", "/arc/enemy/em046.arc",
                          "/arc/enemy/em073.arc", "/arc/enemy/em085.arc"], with_block


def _images(dump) -> dict:
    """Each game's RomFS image and its file paths, so a model can be read without rescanning."""
    out = {}
    for game in ("mh3u", "mh4u"):
        image = romfs.open_image(dump(game, "romfs.bin"))
        out[game] = (image, {f.path: f for f in image.files()})
    return out


def motion_lists(image):
    """(name, bytes) for every motion list in an image: entries of its ARCs and loose `.lmt` files."""
    for f in image.files():
        if f.path.endswith(".arc"):
            for e in arc.read(image.read(f)).entries:
                if e.data[:4] == b"LMT\0":
                    yield e.file_name, e.data
        elif f.path.endswith(".lmt"):
            data = image.read(f)
            if data[:4] == b"LMT\0":
                yield f.path, data


def test_mh3u_motion_lists_read_as_version_66(dump):
    """specs/lmt.md check L3: MH3U's motion lists are LMT version 66. RevilLib puts 66 and 67 in the
    same class layouts, so one reader covers both: every animation, track table, keyframe buffer,
    bounds block and event block the files name lies inside its file, every buffer is a whole number
    of keys at its type's stride, every track weighs 1.0, and every animation carries an event block,
    marked by bit 0x800000 of its flags."""
    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    versions, buffer_types, weights, usage = set(), set(), set(), Counter()
    lists = animations = empty = tracks = 0
    buffered = bounds = 0
    for name, data in motion_lists(image):
        lists += 1
        version, anims = lmt.read(data)
        versions.add(version)          # read raises if a block is outside the file
        for a in anims:
            if a is None:
                empty += 1
                continue
            animations += 1
            tracks += len(a.tracks)
            assert a.events and a.flags & 0x800000, name
            for t in a.tracks:
                buffer_types.add(t.buffer_type)
                weights.add(t.weight)
                usage[t.usage] += 1
                buffered += bool(t.buffer_size)
                bounds += bool(t.bounds)
                assert not t.buffer_size or t.buffer_size % lmt.KEY_STRIDES[t.buffer_type] == 0, (name, t.buffer_size)
    assert versions == {66}, versions
    assert (lists, animations, empty, tracks) == (387, 8336, 7258, 270420), \
        (lists, animations, empty, tracks)
    assert buffer_types == {1, 2, 3, 4, 5, 6, 7, 11, 12, 13}, sorted(buffer_types)
    assert weights == {1.0}, weights
    assert usage == {0: 237990, 1: 13286, 2: 10696, 3: 75, 4: 8300, 5: 73}, usage
    assert (buffered, bounds) == (231142, 51794), (buffered, bounds)


def test_mh3u_player_motion_tracks_address_bones_by_id(dump):
    """specs/lmt.md check L2, on MH3U: the 15 player motion lists carry the hunter body's bone ids,
    not indexes into a 20-entry list; ids 20 and 21 belong to some armour sets' helms and are never
    keyframed, and track 255 is root motion."""
    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    seen = set()
    for f in image.files():
        if not f.path.startswith("/arc/player/mot/"):
            continue
        for e in arc.read(image.read(f)).entries:
            if e.data[:4] == b"LMT\0":
                _version, anims = lmt.read(e.data)
                seen |= {t.bone for a in anims if a for t in a.tracks}
    assert seen == set(range(22)) | {255}, sorted(seen)


KEYFRAME_COUNTS = {   # lists, animations, empty slots, tracks, tracks with a buffer, keys
    "mh4u": (1466, 23412, 25633, 732404, 603620, 40672238),
    "mhxx": (988, 21154, 57010, 677909, 569298, 33075719),
    "mh3u": (387, 8336, 7258, 270420, 231142, 16788906),
}
KEYFRAME_ALL = {      # tracks by the type byte at track +0x00
    "mh4u": {1: 71515, 2: 57269, 3: 641, 4: 24613, 5: 12999, 6: 362290, 7: 110522,
             11: 66482, 12: 19469, 13: 6604},
    "mhxx": {1: 62925, 2: 45686, 3: 3, 4: 21593, 5: 13735, 6: 321115, 7: 113725,
             11: 71569, 12: 20887, 13: 6671},
    "mh3u": {1: 15671, 2: 23607, 3: 214, 4: 10000, 5: 6470, 6: 143814, 7: 32333,
             11: 26368, 12: 11310, 13: 633},
}
KEYFRAME_BOUNDS = {   # tracks with a bounds block, by buffer type (types 1 and 2 have no buffer at all)
    "mh4u": {4: 24613, 5: 12999, 7: 110522, 11: 66482, 12: 19469, 13: 6604},
    "mhxx": {4: 21593, 5: 13735, 7: 113725, 11: 71569, 12: 20887, 13: 6671},
    "mh3u": {4: 10000, 5: 6470, 6: 2991, 7: 32333},
}
# version 66's types 11 to 13 are signed magnitude: keys whose value is a unit quaternion within 0.01
KEYFRAME_V66_UNIT = {11: 1628374, 12: 718846, 13: 21795}


def _length(v) -> float:
    return sum(c * c for c in v) ** 0.5


def test_every_motion_keyframe_buffer_decodes_in_all_three_games(dump):
    """specs/lmt.md check L4: every keyframe buffer of the three games' 2,841 motion lists decodes, its keys
    start at frame 0 and end at the animation's frame count - 1, every type 3 to 13 track carries one while
    types 1 and 2 never do, and the quaternion types come out unit (version 67 after the bounds block, version
    66's types 11 to 13 under their signed-magnitude reading)"""
    for game in ("mh4u", "mhxx", "mh3u"):
        image = romfs.open_image(dump(game, "romfs.bin"))
        counts, types, keyless, bounds = Counter(), Counter(), Counter(), Counter()
        norms = {}      # (buffer type, "raw" or "bounded") -> keys, summed |1-norm|, worst, unit within 0.01
        for name, data in motion_lists(image):
            counts["lists"] += 1
            version, anims = lmt.read(data)
            assert version == (66 if game == "mh3u" else 67), name
            for a in anims:
                if a is None:
                    counts["empty"] += 1
                    continue
                counts["animations"] += 1
                for t in a.tracks:
                    counts["tracks"] += 1
                    types[t.buffer_type] += 1
                    if not t.buffer_size:
                        keyless[t.buffer_type] += 1
                        continue
                    counts["buffered"] += 1
                    keys = lmt.decode_keys(data, t, version, a.frames)
                    counts["keys"] += len(keys)
                    assert keys[0].frame == 0, (name, t.buffer_type)
                    assert keys[-1].frame == a.frames - 1, (name, t.buffer_type, a.frames, keys[-1].frame)
                    ascending = all(keys[i].frame < keys[i + 1].frame for i in range(len(keys) - 1))
                    assert ascending, (name, t.buffer_type)
                    assert all(math.isfinite(c) for k in keys for c in k.value), (name, t.buffer_type)
                    b = lmt.bounds(data, t)
                    bounds[t.buffer_type] += bool(b)
                    if t.buffer_type in (4, 5):        # normalized components, offset + scale x value
                        scale, offset = b
                        for k in keys:
                            v = tuple(o + s * c for o, s, c in zip(offset, scale, k.value, strict=True))
                            assert all(min(o, o + s) - 1e-3 <= c <= max(o, o + s) + 1e-3
                                       for o, s, c in zip(offset, scale, v, strict=True)), (name, t.buffer_type)
                    if t.buffer_type in (6, 7, 11, 12, 13):
                        bounded = t.buffer_type == 7 or (t.buffer_type in (11, 12, 13) and version == 67)
                        if bounded:
                            assert b is not None, (name, t.buffer_type)
                        slot = norms.setdefault((t.buffer_type, "bounded" if bounded else "raw"),
                                                [0, 0.0, 0.0, 0])
                        for k in keys:
                            v = k.value
                            if bounded:
                                scale, offset = b
                                v = tuple(o + s * c for o, s, c in zip(offset, scale, v, strict=True))
                            d = abs(1 - _length(v))
                            slot[0] += 1
                            slot[1] += d
                            slot[2] = max(slot[2], d)
                            slot[3] += d <= 0.01
        got = (counts["lists"], counts["animations"], counts["empty"], counts["tracks"],
               counts["buffered"], counts["keys"])
        assert got == KEYFRAME_COUNTS[game], (game, got)
        assert dict(types) == KEYFRAME_ALL[game], (game, dict(types))
        assert dict(keyless) == {1: KEYFRAME_ALL[game][1], 2: KEYFRAME_ALL[game][2]}, (game, dict(keyless))
        assert {t: n for t, n in bounds.items() if n} == KEYFRAME_BOUNDS[game], (game, dict(bounds))
        for (buffer_type, mode), (n, total, worst, unit) in norms.items():
            mean = total / n
            if buffer_type == 6:
                assert mean < 1e-3 and worst < 1e-3, (game, buffer_type, mode, mean, worst)
            elif buffer_type == 7:
                assert mean < 0.01 and worst < 0.14, (game, buffer_type, mode, mean, worst)
            elif game == "mh3u":
                assert unit == KEYFRAME_V66_UNIT[buffer_type], (game, buffer_type, mode, unit)
            else:
                assert mean < 1e-3 and worst < 0.009, (game, buffer_type, mode, mean, worst)


def test_no_motion_list_uses_the_float_track_block_in_all_three_games(dump):
    """specs/lmt.md check L5: the float-track block at animation +0x38 is unused in all three games
    (+0x38 is 0 and RevilLib's 0x40000 flag clear in every animation of the 2,841 motion lists), and
    the four bytes at +0x3C are not a field: they are 0 except in the highest-offset animation of
    some lists, where the next block starts and they are that block's first word. It also checks the
    two flags the loader reads: 0x2000000 is never set, and 0x1000000 (702 MHXX animations) marks a
    motion that shares its track table with an earlier one that doesn't set it."""
    counts, nonzero, shared = Counter(), Counter(), Counter()
    flags = {game: Counter() for game in ("mh4u", "mhxx", "mh3u")}
    for game in ("mh4u", "mhxx", "mh3u"):
        image = romfs.open_image(dump(game, "romfs.bin"))
        for name, data in motion_lists(image):
            version, anims = lmt.read(data)
            assert version == (66 if game == "mh3u" else 67), name
            present = [a for a in anims if a is not None]
            counts["lists"] += 1
            if not present:                                  # every slot empty: nothing to read
                counts["empty lists"] += 1
                continue
            highest = max(a.offset for a in present)
            blocks = set()                       # every block start the list names
            for a in present:
                blocks.add(struct.unpack_from("<I", data, a.offset)[0])      # track table
                blocks.add(a.events)
                for t in a.tracks:
                    blocks.add(t.buffer)
                    blocks.add(t.bounds)
                if a.events:
                    for g in range(lmt.GROUPS):
                        blocks.add(struct.unpack_from("<I", data, a.events + lmt.GROUP * g + 0x44)[0])
            blocks.discard(0)
            tables: dict[int, list] = {}
            for a in present:
                tables.setdefault(struct.unpack_from("<I", data, a.offset)[0], []).append(a)
            for tr, same in tables.items():                        # a shared track table is relocated once
                if len(same) == 1:
                    continue
                shared[game] += 1
                unflagged = [a for a in same if not a.flags & 0x1000000]
                assert len(unflagged) == 1, (name, tr, len(unflagged))
                assert all(a.offset > unflagged[0].offset for a in same if a.flags & 0x1000000), (name, tr)
            for a in present:
                counts["animations"] += 1
                flags[game][a.flags] += 1
                assert a.floats is None, (name, a.offset)              # no float-track block
                assert not a.flags & 0x40000, (name, a.offset)         # no float-track flag
                assert not a.flags & 0x2000000, (name, a.offset)       # the loader's event-list skip bit
                if a.offset + 0x40 > len(data):
                    continue
                if struct.unpack_from("<I", data, a.offset + 0x3C)[0]:
                    assert a.offset == highest, (name, a.offset, highest)
                    assert a.offset + 0x3C in blocks, (name, a.offset)
                    nonzero[game] += 1
    assert (counts["lists"], counts["animations"]) == (2841, 52902), dict(counts)
    assert dict(nonzero) == {"mh4u": 1466, "mhxx": 972, "mh3u": 383}, dict(nonzero)
    assert dict(shared) == {"mhxx": 525}, dict(shared)
    assert flags == {"mh4u": {0x800000: 23412},
                     "mhxx": {0x800000: 19767, 0x800001: 685, 0x1800000: 702},
                     "mh3u": {0x800000: 8336}}, {g: dict(c) for g, c in flags.items()}


def _r_model(image, files, arc_path: str) -> bytes:
    return next(e.data for e in arc.read(image.read(files[arc_path])).entries if e.type_name == "rModel")


HUNTER_PARTS = (  # part, MH3U bone ids, MH4U bone ids; MH4U's id 0 is MH3U's pelvis, id 13
    ("body", set(range(20)), set(range(13)) | set(range(14, 20))),
    ("arm", {2, 5, 6, 7, 8, 9, 10, 11, 12}, {2, 5, 6, 7, 8, 9, 10, 11, 12}),
    ("leg", {13, 14, 15, 16, 17, 18, 19}, {0, 14, 15, 16, 17, 18, 19}),
    ("wst", {1, 13, 14, 15, 17, 18}, {0, 1, 14, 15, 17, 18}),
    ("helm", {2, 3, 4}, {2, 3, 4}),
)
HUNTER_ARMOUR = (1, 2, 3, 10, 20, 50, 100, 150, 200, 212)


def test_the_mh4u_hunter_skeleton_is_mh3us_with_the_pelvis_renumbered(dump):
    """specs/mod.md check M4: MH4U's hunter has MH3U's ids and parent tree with the empty root
    dropped and the pelvis renumbered 13 to 0, so a 3U motion needs its bone ids rewritten
    (docs/underwater.md); the bind pose is MH3U's too, except on MH4U's remodelled armour"""
    games = _images(dump)
    extra = {20, 21}   # some helmets carry two more bones, in both games
    for gender in ("f", "m"):
        for part, want3, want4 in HUNTER_PARTS:
            checked = 0
            for armour in HUNTER_ARMOUR:
                path3 = f"/arc/player/mod/{gender}/pl{armour:03d}/{gender}_{part}{armour:03d}.arc"
                d3 = _r_model(*games["mh3u"], path3) if path3 in games["mh3u"][1] else None
                path4 = f"/data/pl_{gender}_{part}{armour:03d}.arc"
                d4 = _r_model(*games["mh4u"], path4) if path4 in games["mh4u"][1] else None
                if d3 is None or d4 is None:
                    continue
                checked += 1
                b3 = {b["id"]: b for b in mod.bones(d3)}
                b4 = {b["id"]: b for b in mod.bones(d4)}
                assert want3 <= set(b3) <= want3 | extra, (gender, part, armour, sorted(set(b3)))
                assert want4 <= set(b4) <= want4 | extra, (gender, part, armour, sorted(set(b4)))
                if 0 in b3:     # the MH3U-only empty root: no mesh, at the origin
                    assert b3[0]["furthest"] == b3[0]["parent_distance"] == 0 and b3[0]["position"] == (0, 0, 0), \
                        (gender, part, armour)
                if part == "body":
                    assert b4[0]["furthest"] > 0, (gender, armour)   # MH4U's id 0 is the pelvis, mesh and all
                for i, u4 in b4.items():
                    if i in extra:      # outside the motion rig; the two games don't always agree
                        continue
                    u3 = b3[13 if i == 0 else i]
                    want_parent = 0 if u3["parent_id"] in (0, 13) else u3["parent_id"]
                    assert u4["parent_id"] == (0xFF if i == 0 else want_parent), \
                        (gender, part, armour, i, want_parent, u4["parent_id"])
                    if armour == 1:     # MH3U's bind pose, on the one set every part has
                        assert u4["parent_distance"] == pytest.approx(u3["parent_distance"], abs=1e-3), \
                            (gender, part, i)
                        assert u4["position"] == pytest.approx(u3["position"], abs=1e-3), (gender, part, i)
            assert checked >= 8, (gender, part, checked)


def test_mh4u_motion_tracks_address_bones_by_id(dump):
    """specs/lmt.md check L2: a track's bone field is the model's bone id, not its index, so a
    3U-to-4U motion only needs the ids rewritten. MH4U's Rathian model has 43 bones with ids up to
    202 and its motions carry ids 60 to 145, which no 43-entry list could index."""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    files = {f.path: f for f in image.files()}
    entries = arc.read(image.read(files["/data/em001.arc"])).entries
    ids = {b["id"] for b in mod.bones(next(e.data for e in entries if e.file_name.endswith("em001.mod")))}
    seen = set()
    for e in entries:
        if e.type_name == "rMotionList":
            _version, anims = lmt.read(e.data)
            seen |= {t.bone for an in anims if an for t in an.tracks}
    high = {i for i in ids if 60 <= i <= 145}   # ids a 43-entry list cannot hold
    assert len(ids) == 43 and max(ids) == 202 and len(high) == 18 and high <= seen, \
        (len(ids), max(ids), len(high), sorted(high - seen))
    # the player's common and per-weapon motions use exactly the hunter body's ids (13 is absent)
    human = {b["id"] for b in mod.bones(_r_model(image, files, "/data/pl_f_body001.arc"))}
    for path in ["/data/pl_mot_lco.arc"] + [f"/data/pl_w{i:02d}.arc" for i in range(14)]:
        seen = set()
        for e in arc.read(image.read(files[path])).entries:
            if e.type_name == "rMotionList" and e.file_name.startswith("player/"):
                _version, anims = lmt.read(e.data)
                seen |= {t.bone for an in anims if an for t in an.tracks}
        assert seen - {255} == human, (path, sorted(seen - {255} ^ human))


def test_every_monster_camera_list_reads_and_converts(dump):
    """specs/camera.md check C1: the camera lists of MH4U's and MHXX's monster arcs, and MH3U's none."""
    def monster_cameras(game, pattern):
        image = romfs.open_image(dump(game, "romfs.bin"))
        arcs, with_camera, blobs = 0, 0, {}
        for f in image.files():
            if not re.fullmatch(pattern, f.path):
                continue
            arcs += 1
            a = arc.read(image.read(f))
            found = False
            for e in a.entries:
                if e.type_name == "rCameraList":
                    found = True
                    blobs.setdefault(hashlib.sha1(e.data).hexdigest(), e.data)
            with_camera += found
        return arcs, with_camera, blobs

    def bad(camera_data):
        counters = camera.check(camera_data)
        return {k: v for k, v in counters.items()
                if "not read" in k or "don't" in k or "isn't" in k or "no decoder" in k
                or "without a buffer" in k or "outside 0 and 1" in k}

    mh4u_arcs, mh4u_with, mh4u = monster_cameras("mh4u", r"/data/em\d{3}\.arc")
    assert (mh4u_arcs, mh4u_with, len(mh4u)) == (123, 86, 32), (mh4u_arcs, mh4u_with, len(mh4u))
    for data in mh4u.values():
        assert camera.read(data).version == camera.VERSION_MH4U
        assert camera.convert(data, camera.VERSION_MH4U) == data
        assert camera.from_mhxx(camera.to_mhxx(data)) == data
        assert not bad(data), (bad(data), len(data))

    mhxx_arcs, mhxx_with, mhxx = monster_cameras("mhxx", r"/arc/enemy/.*\.arc")
    assert (mhxx_arcs, mhxx_with, len(mhxx)) == (137, 93, 57), (mhxx_arcs, mhxx_with, len(mhxx))
    for data in mhxx.values():
        assert camera.read(data).version == camera.VERSION_MHXX
        v4 = camera.from_mhxx(data)
        assert camera.read(v4).version == camera.VERSION_MH4U
        assert camera.to_mhxx(v4) == data
        assert not bad(v4), (bad(v4), len(v4))

    # MH3U registers rCameraList but ships no file of it: the 3U port has no source camera.
    mh3u_arcs, mh3u_with, mh3u = monster_cameras("mh3u", r"/arc/enemy/em\d{3}\.arc")
    assert (mh3u_arcs, mh3u_with, mh3u) == (85, 0, {}), (mh3u_arcs, mh3u_with, mh3u)


def rathian_camera(dump, game, arc_path):
    """The rCameraList entry in one monster archive, or None."""
    image = romfs.open_image(dump(game, "romfs.bin"))
    archive = next(f for f in image.files() if f.path == arc_path)
    return next((e.data for e in arc.read(image.read(archive)).entries if e.type_name == "rCameraList"), None)


def test_rathian_camera_converts_from_mhxx_and_mh4us_re_lays_to_itself(dump, tmp_path):
    """specs/camera.md: MHXX em001's list becomes MH4U's layout; MH4U em001 re-lays to itself."""
    mh4u = rathian_camera(dump, "mh4u", "/data/em001.arc")
    mhxx = rathian_camera(dump, "mhxx", "/arc/enemy/em001_00.arc")
    assert rathian_camera(dump, "mh3u", "/arc/enemy/em001.arc") is None     # MH3U ships no camera list
    source4, source5 = camera.read(mh4u), camera.read(mhxx)
    assert (source4.version, source5.version) == (4, 5)

    # MH4U's own file re-lays as version 4 unchanged, and its version 5 form inverts back.
    assert camera.convert(mh4u, 4) == mh4u
    assert camera.from_mhxx(camera.to_mhxx(mh4u)) == mh4u

    # MHXX's list converts to a version 4 file with the source's cameras and data; only the
    # seven relocated words move, by 16 per record.
    converted = camera.from_mhxx(mhxx)
    dst = camera.read(converted)
    assert dst.version == 4 and len(dst.records) == len(source5.records)
    assert dst.order == source5.order and dst.data == source5.data
    shift = 16 * len(source5.order)
    for camera_id in source5.order:
        a, b = source5.records[camera_id], dst.records[camera_id]
        assert (a.frames, a.flag, a.aspect) == (b.frames, b.flag, b.aspect)
        for ta, tb in zip(a.tracks, b.tracks, strict=True):
            assert (ta.buffer_type, ta.usage, ta.joint_type, ta.bone, ta.weight, ta.size,
                    ta.reference) == (tb.buffer_type, tb.usage, tb.joint_type, tb.bone, tb.weight,
                                      tb.size, tb.reference)
            assert tb.offset == ta.offset - shift
            assert tb.bounds == (ta.bounds - shift if ta.bounds else 0)
        assert b.fourth.offset == (a.fourth.offset - shift if a.fourth.offset else 0)
    assert camera.to_mhxx(converted) == mhxx

    # The two Rathians' lists share the ids MH4U's own file has and MHXX's keeps; each has
    # extra cameras of its own (MH4U 9, 10, 12..20; MHXX 40..44 and 50..53).
    assert set(source4.records) & set(source5.records) == {0, 1, 2, 4, 5, 8}

    # The command writes exactly the converted file from the player's MHXX list.
    source = tmp_path / "em001_00_cam.lcm"
    source.write_bytes(mhxx)
    out = tmp_path / "e001_cam.lcm"
    assert cli.main(["convert", "camera", str(source), "--from", "mhxx", "-o", str(out)]) == 0
    assert out.read_bytes() == converted


def test_every_mh3u_sound_file_reads_and_its_stream_requests_match_their_waves(dump):
    """specs/sound.md check SN6: every MH3U wave (MADP 4), bank (SNDB 10), request (SREQ 6) and stream request
    (STRQ 0x20) closes, every request's bank names are the bank resources beside them, and every stream record
    repeats the wave header it names"""
    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    files = {f.path: f for f in image.files()}
    counts: Counter = Counter()
    failed: list[str] = []
    banks: set[str] = set()
    request_banks: list[str] = []

    def one(data: bytes) -> None:
        magic = data[:4]
        try:
            if magic == sound.WAVE_MAGIC:
                sound.read_wave(data)
                counts["wave"] += 1
            elif magic == sound.BANK_MAGIC:
                sound.read_bank(data)
                counts["bank"] += 1
            elif magic == sound.REQUEST_MAGIC:
                request = sound.read_request(data)
                request_banks.extend(request.banks)
                counts["request"] += 1
            elif magic == stq.MAGIC:
                stq.read(data)
                counts["stream request"] += 1
        except (sound.SoundError, stq.StqError) as err:
            failed.append(f"{magic!r}: {err}")

    for path, f in files.items():
        if path.endswith(".arc"):
            for e in arc.read(image.read(f)).entries:
                if e.data[:4] == sound.BANK_MAGIC:
                    banks.add(e.path)
                if e.data[:4] in (sound.WAVE_MAGIC, sound.BANK_MAGIC, sound.REQUEST_MAGIC, stq.MAGIC):
                    one(e.data)
        elif path.lower().endswith((".mca", ".stq")):
            one(image.read(f))
    assert not failed, f"{len(failed)} sound files not read, first: {failed[:3]}"
    assert counts["wave"] == 10132 and counts["bank"] == 1225, counts
    assert counts["request"] == 1004 and counts["stream request"] == 106, counts
    missing = set(request_banks) - banks
    assert not missing, f"{len(missing)} request bank names aren't a bank resource beside them: {sorted(missing)[:3]}"

    streams = 0
    for path, f in files.items():
        if not path.lower().endswith(".stq"):
            continue
        for stream in stq.read(image.read(f)).streams:
            wave_path = "/" + stream.name.replace("\\", "/") + ".mca"
            assert wave_path in files, f"{path}: {stream.name} isn't in the RomFS"
            w = sound.read_wave(image.read(files[wave_path]))
            assert (stream.size, stream.samples, stream.channels, stream.rate, stream.loop_start, stream.loop_end) \
                == (files[wave_path].size, w.samples, w.channels, w.rate, w.word_14, w.word_18), \
                f"{path}: {stream.name}"
            streams += 1
    assert streams == 290, f"{streams} streams"


XFS_CLASSES = ("rTexLayout", "rStageData", "rStageCamera", "rSoundAttributeSe", "rDemoFade",
               "rDemoListeningPoint", "rQuestList", "rAinpc")


def xfs_entries(image):
    """Every known XFS file of an image: loose .supp/.pop/.list, and the XFS classes inside ARCs."""
    ids = {classid.class_id(n) for n in XFS_CLASSES}
    for f in image.files():
        data = image.read(f)
        if f.path.endswith(".arc"):
            for e in arc.read(data).entries:
                if e.type_id in ids:
                    yield f"{f.path}:{e.path}", e.type_id, e.data
        elif f.path.endswith((".supp", ".pop", ".list")):
            yield f.path, None, data


def test_every_mh3u_xfs_file_reads(dump):
    """check X1: MH3U's 543 XFS entries in ARCs and 302 loose XFS files all read and end exactly."""
    ids = {classid.class_id(n) for n in XFS_CLASSES}
    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    counts: Counter = Counter()
    failures = []
    for label, type_id, data in xfs_entries(image):
        counts[type_id] += 1
        try:
            x = xfs.read(data)
        except (xfs.XfsError, struct.error, IndexError, UnicodeDecodeError) as e:
            failures.append(f"{label}: {e}")
            continue
        if x.endian != "little":
            failures.append(f"{label}: {x.endian}-endian")
    assert not failures, f"{len(failures)} of {sum(counts.values())} XFS files not read, first: {failures[:3]}"
    assert counts[None] == 302, counts          # 196 .supp, 105 .pop, 1 .list
    assert sum(counts[t] for t in ids) == 543, counts   # 285 texlayouts and 258 other XFS entries
    assert counts[classid.class_id("rTexLayout")] == 285, counts


def test_mh4u_ships_no_texlayout_and_its_xfs_files_read(dump):
    """check X1: MH4U's only XFS files are eight rSoundAttributeSe; it has no rTexLayout anywhere."""
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    counts: Counter = Counter()
    failures = []
    for label, type_id, data in xfs_entries(image):
        counts[type_id] += 1
        try:
            x = xfs.read(data)
        except (xfs.XfsError, struct.error, IndexError, UnicodeDecodeError) as e:
            failures.append(f"{label}: {e}")
            continue
        if x.endian != "little":
            failures.append(f"{label}: {x.endian}-endian")
    assert not failures, f"{len(failures)} XFS files not read, first: {failures[:3]}"
    assert counts == Counter({classid.class_id("rSoundAttributeSe"): 8}), counts


# The monster archives of each game. A port's effects live in its monster's archive, so these,
# not the whole RomFS, are where the effect specs are checked.
MONSTER_ARCHIVES = {
    "mh4u": re.compile(r"/data/em\d{3}\.arc$"),
    "mh3u": re.compile(r"/arc/enemy/em\d{3}\.arc$"),
    "mhxx": re.compile(r"/arc/enemy/ems?\d{3}_\d{2}\.arc$"),
}


def _effect_entries(dump, game: str, classes: tuple[str, ...]):
    """Every entry of the named resource classes in `game`'s monster archives."""
    ids = {classid.class_id(name): name for name in classes}
    image = romfs.open_image(dump(game, "romfs.bin"))
    wanted = MONSTER_ARCHIVES[game]
    for f in image.files():
        if not wanted.search(f.path):
            continue
        for e in arc.read(image.read(f)).entries:
            if e.type_id in ids:
                yield ids[e.type_id], f"{f.path}:{e.path}", e.data


def test_every_mh4u_motion_effect_record_is_laid_out(dump):
    """check FX1: MH4U's MEF header and 0x48-byte records tile every file, and the fields the spec
    calls fixed are fixed."""
    entries, records, paths, failures = 0, 0, set(), []
    for _name, label, data in _effect_entries(dump, "mh4u", ("rMhMotionEffect",)):
        entries += 1
        paths.add(label.split(":", 1)[1])
        try:
            parsed = mef.read_mef(data)
        except mef.MefError as e:
            failures.append(f"{label}: {e}")
            continue
        records += len(parsed)
        for i, record in enumerate(parsed.records):
            zero = (record.u8(0x07), record.u8(0x09), record.u8(0x0F),
                    record.u32(0x24), record.u32(0x34), record.u32(0x44))
            if any(zero):
                failures.append(f"{label} record {i}: {zero} aren't the zeros the spec has")
            if not all(math.isfinite(record.f32(o)) for o in (0x38, 0x3C, 0x40)):
                failures.append(f"{label} record {i}: the three +0x38 floats aren't finite")
    assert not failures, f"{len(failures)} problems, first: {failures[:3]}"
    assert (entries, records, len(paths)) == (150, 6216, 96)


def test_every_mh3u_effect_sequence_header_is_laid_out(dump):
    """check FX2: MH3U's ESQ header holds six non-decreasing section offsets inside every file."""
    entries, failures = 0, []
    for _name, label, data in _effect_entries(dump, "mh3u", ("rEffectSequence",)):
        entries += 1
        try:
            mef.read_esq(data)
        except mef.MefError as e:
            failures.append(f"{label}: {e}")
    assert not failures, f"{len(failures)} problems, first: {failures[:3]}"
    assert entries == 44


def test_every_mhxx_motion_effect_and_proof_effect_list_is_laid_out(dump):
    """check FX2 and EF2: MHXX's PSL slot tables and descriptors, and its PEL magic and version."""
    motion, slots, proofs, failures = 0, 0, 0, []
    for name, label, data in _effect_entries(dump, "mhxx", ("rProofEffectMotSequenceList", "rProofEffectList")):
        if name == "rProofEffectList":
            proofs += 1
            try:
                efl.read_pel(data)
            except efl.EflError as e:
                failures.append(f"{label}: {e}")
            continue
        motion += 1
        try:
            parsed = mef.read_psl(data)
        except mef.MefError as e:
            failures.append(f"{label}: {e}")
            continue
        slots += len(parsed.slots)
        if parsed.slots and parsed.slots[0] != 0:
            failures.append(f"{label}: slot 0's offset is {parsed.slots[0]:#x}, not 0")
    assert not failures, f"{len(failures)} problems, first: {failures[:3]}"
    assert (motion, slots, proofs) == (507, 18831, 280)


def test_every_effect_list_header_is_laid_out(dump):
    """check EF1: every EFL in the three games' monster archives fills its block-size field and
    carries its game's version; the 60.0 at +0x0C is in all but one MH3U file."""
    expected = {"mh4u": (1937, 1937, 1937), "mh3u": (1496, 1495, 1478), "mhxx": (4042, 4042, 4042)}
    for game, (files, sixty, tail_zero) in expected.items():
        entries, sixties, tails, failures = 0, 0, 0, []
        for _name, label, data in _effect_entries(dump, game, ("rEffectList",)):
            entries += 1
            try:
                parsed = efl.read_efl(data)
            except efl.EflError as e:
                failures.append(f"{label}: {e}")
                continue
            if parsed.block_size % 16:
                failures.append(f"{label}: block size {parsed.block_size:#x} isn't a multiple of 16")
            if data[0x18:0x1C] != bytes(4) or data[0x1C:0x20] != bytes(4):
                failures.append(f"{label}: +0x18 or +0x1C isn't 0")
            tails += data[0x20:0x2C] == bytes(0xC)
            sixties += parsed.field_0c == 60.0
        assert not failures, f"{game}: {len(failures)} problems, first: {failures[:3]}"
        assert (entries, sixties, tails) == (files, sixty, tail_zero), \
            f"{game}: {entries} files, {sixties} with 60.0, {tails} with a zero 0x20 to 0x2C"


def _one_sound_set(image, paths):
    files = {f.path: f for f in image.files()}
    return [image.read(files[p]) for p in paths]


def test_a_mh3u_monsters_own_sound_set_converts_to_what_mh4u_loads(dump):
    """specs/sound.md check SN9: MH3U Rathian's sound set (the call in her monster arc, the waves,
    bank and request in the sound arc) converts to MH4U's versions, and every converted file reads
    with MH4U's readers: the audio is bit for bit, the bank keeps its entries, the request keeps
    its ids and indices, and the call keeps its keys and record bytes."""
    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    call, sound_arc = _one_sound_set(image, [r"/arc/enemy/em001.arc",
                                             r"/arc/sound/se/em/em001/snd_em001.arc"])
    sound_set = monstersound.read_sound_set(call, sound_arc)
    conversion = monstersound.convert(sound_set, "mh3u", "em001", 125)
    waves = {path: data for path, type_id, data in conversion.entries if type_id == monstersound.WAVE}
    banks = [data for path, type_id, data in conversion.entries if type_id == monstersound.BANK]
    requests = [data for path, type_id, data in conversion.entries if type_id == monstersound.REQUEST]
    calls = [data for path, type_id, data in conversion.entries if type_id == monstersound.SEQUENCE]
    assert (len(waves), len(banks), len(requests), len(calls)) == (48, 1, 1, 1)
    assert all(sound.read_wave(d).layout == "mh4u" for d in waves.values())

    source_bank = sound.read_bank(next(d for p, d in sound_set.banks.items() if "em001" in p))
    bank = sound.read_bank(banks[0])
    assert (bank.version, len(bank.groups), len(bank.entries)) == (11, len(source_bank.groups),
                                                                   len(source_bank.entries))
    source_waves = sound_set.waves
    for old, new in zip(source_bank.entries, bank.entries, strict=True):
        before = sound.read_wave(source_waves[old.name])
        after = sound.read_wave(waves[new.name])
        assert (before.samples, before.rate, before.seconds, before.word_14, before.word_18) == \
               (after.samples, after.rate, after.seconds, after.word_14, after.word_18), new.name
        assert source_waves[old.name][before.data_offset:before.data_offset + before.data_size] == \
               waves[new.name][after.data_offset:after.data_offset + after.data_size], new.name

    source_request = sound.read_request(next(iter(sound_set.requests.values())))
    request = sound.read_request(requests[0])
    assert [r.id for r in request.records] == [r.id for r in source_request.records]
    assert [r.words[2] for r in request.records] == [r.words[2] for r in source_request.records]
    assert [r.words[9] for r in request.records] == [r.words[9] for r in source_request.records]
    assert request.banks == ("sound\\se\\em\\em125\\snd_em125",)

    source_call = sound.read_sequence(next(iter(sound_set.sequences.values())))
    converted_call = sound.read_sequence(calls[0])
    assert converted_call.version == 0x20120123
    assert [r.key for r in converted_call.records] == [r.key for r in source_call.records]
    assert all(a.body == b.body for a, b in zip(converted_call.records, source_call.records, strict=True))
    assert len(converted_call.records) == 229


def test_a_mhxx_monsters_own_sound_set_converts_to_what_mh4u_loads(dump):
    """specs/sound.md check SN9 for MHXX: the bank's GU flags and parameter permutation reverse,
    the 100-byte request records become MH4U's 92-byte ones with words 0 to 21 kept, and the call
    only changes its version."""
    image = romfs.open_image(dump("mhxx", "romfs.bin"))
    sound_set = monstersound.read_sound_set(*_one_sound_set(image, [r"/arc/enemy/em001_00.arc"]))
    conversion = monstersound.convert(sound_set, "mhxx", "em001", 124)
    waves = {path: data for path, type_id, data in conversion.entries if type_id == monstersound.WAVE}
    banks = [data for path, type_id, data in conversion.entries if type_id == monstersound.BANK]
    requests = [data for path, type_id, data in conversion.entries if type_id == monstersound.REQUEST]
    calls = [data for path, type_id, data in conversion.entries if type_id == monstersound.SEQUENCE]
    assert (len(waves), len(banks), len(requests), len(calls)) == (198, 2, 1, 1)

    names = monstersound.Names("mhxx", "em001", 124)
    for path, body in sound_set.waves.items():
        before = sound.read_wave(body)
        after = sound.read_wave(waves[names.wave(path)])
        assert (before.samples, before.rate, before.word_14, before.word_18, before.seconds) == \
               (after.samples, after.rate, after.word_14, after.word_18, after.seconds), path
        assert body[0x68:0x68 + before.data_size] == \
               waves[names.wave(path)][0x60:0x60 + after.data_size], path
        assert body[0x38:0x58] == waves[names.wave(path)][0x30:0x50], path

    source_bank = sound.read_bank(next(d for p, d in sound_set.banks.items() if "em001_00" in p))
    bank = sound.read_bank(banks[0])
    assert (bank.version, len(bank.groups), len(bank.entries)) == (11, len(source_bank.groups),
                                                                   len(source_bank.entries))
    for group in bank.groups:
        assert group.flags & 0x8000
    for source, converted in zip(source_bank.entries, bank.entries, strict=True):
        p = source.params
        assert converted.params == p[0:2] + b"\x08" + p[3:12] + p[71:75] + p[12:71] + b"\x00"
        assert converted.name == names.wave(source.name)
        assert converted.type_id == sound.WAVE_TYPE_ID

    source_request = sound.read_request_gu(next(iter(sound_set.requests.values())))
    request = sound.read_request(requests[0])
    assert [r.id for r in request.records] == [r.id for r in source_request.records]
    for old, new in zip(source_request.records, request.records, strict=True):
        assert new.words[:8] == old.words[:8]
        assert new.words[8] == old.words[8] | 0x10000
        assert new.words[9:22] == old.words[9:22]
        assert new.words[22] == 0
    assert request.banks == ("sound\\se\\em\\em124\\snd_em124",
                             "sound\\se\\em\\em124\\snd_common")

    source_call = sound.read_sequence(next(iter(sound_set.sequences.values())))
    converted_call = sound.read_sequence(calls[0])
    assert converted_call.version == 0x20120123
    assert [r.key for r in converted_call.records] == [r.key for r in source_call.records]
    assert all(a.body == b.body for a, b in zip(converted_call.records, source_call.records, strict=True))
