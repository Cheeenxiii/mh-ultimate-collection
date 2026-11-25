"""The real contract: our readers and writers against the game's own files."""
from __future__ import annotations

import hashlib
import math
import os
import re
import struct
import zlib
from collections import Counter

import check_ids
import pytest

from mhuc import cli, monsterassets, monsterdata, monstersound, monstertext
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
    lmd,
    lmt,
    lyt,
    mef,
    mod,
    mrl,
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


def test_every_mh4u_quest_patches_in_place_byte_for_byte(dump):
    """An unchanged in-place patch gives back the original .mib exactly, and a changed monster
    id changes only its four bytes; the builder is a converter, not the quest writer."""
    checked = 0
    for name, data in archives(dump("mh4u", "romfs.bin")):
        for e in arc.read(data).entries:
            if e.type_name != "rQuestData" or e.data[4:8] != b"v005":
                continue
            model = mibwrite.mib4_model(e.data)
            if not model["waves"] or not model["waves"][0]:
                continue
            checked += 1
            id0 = struct.unpack_from("<I", model["waves"][0][0])[0]
            assert mibwrite.mib4_set_wave_monster(e.data, id0) == e.data, f"{name}:{e.file_name}"
            changed = mibwrite.mib4_set_wave_monster(e.data, 125)
            assert changed != e.data
            first = next(i for i in range(len(e.data)) if e.data[i] != changed[i])
            at = first & ~3
            assert struct.unpack_from("<I", changed, at)[0] == 125
            assert changed[:at] == e.data[:at] and changed[at + 4:] == e.data[at + 4:]
    assert checked, "no .mib found"


def test_mh4u_arc_patch_keeps_the_other_entries(dump):
    """Replacing one quest inside a real archive keeps every other entry's stream; a full repack
    compresses them all again. The unchanged replacement returns the archive byte for byte."""
    for _name, data in archives(dump("mh4u", "romfs.bin")):
        a = arc.read(data)
        target = next((e for e in a.entries if e.file_name == "loc/quest/m10212.mib"), None)
        if target is None or target.data[4:8] != b"v005":
            continue
        assert arc.replace_entry(data, target.file_name, target.data) == data
        model = mibwrite.mib4_model(target.data)
        id0 = struct.unpack_from("<I", model["waves"][0][0])[0]
        patched = arc.replace_entry(data, target.file_name,
                                    mibwrite.mib4_set_wave_monster(target.data, id0 + 1))
        b = arc.read(patched)
        by_name = {e.file_name: e for e in b.entries}
        for e in a.entries:
            if e.file_name == target.file_name:
                continue
            assert by_name[e.file_name].compressed == e.compressed, e.file_name
            assert by_name[e.file_name].data == e.data
        assert by_name[target.file_name].data != target.data
        return
    pytest.skip("no quest archive with m10212")


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


def test_clean_mh4u_saves_leave_the_file_byte_for_byte_and_reencrypt_to_it(dump):
    """specs/save.md check S11: the converter changes no byte of a save that never met the mod, and
    re-encrypting its output with the file's own seed gives the file back."""
    from mhuc import save

    folder = dump("mh4u", "saves")
    with open(dump("mh4u", "save.key"), "rb") as f:
        key = f.read().strip()
    checked = 0
    for name in ("user1", "user2", "user3"):
        path = os.path.join(folder, name)
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            original = f.read()
        plain = dlccrypt.mh4u_save_decrypt(original, key)
        if len(plain) != save.CHARACTER_SIZE:
            continue
        seed = dlccrypt.mh4u_save_seed(original, key)
        cleaned, report = save.clean_character(plain)
        assert cleaned == plain, f"{name}: the converter changed a save that never met the mod"
        assert report == {"removed_items": [], "removed_guild_quests": []}, name
        assert dlccrypt.mh4u_save_encrypt(cleaned, key, "normal", seed) == original, name
        assert not save.character_problems(cleaned), name
        checked += 1
    assert checked >= 1, "no character save found"


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


def test_the_sns_weapon_rig_is_the_same_in_mh3u_and_mh4u_and_mh3u_has_no_weapon_motion(dump):
    """specs/mod.md check M5: MH3U's and MH4U's Sword and Shield models use the same three weapon
    rigs, with no bone renumbered, and MH3U ships no motion list for the weapon rig: its 50 player
    motion lists address the hunter, and its weapon arcs hold no motion list. MH4U's own weapon
    motion list addresses ids 0, 1 and 2; no SnS model has id 2."""
    games = _images(dump)

    def rigs(game, pattern):
        image, files = games[game]
        sword, shield = Counter(), Counter()
        for path in files:
            if not re.fullmatch(pattern, path):
                continue
            for e in arc.read(image.read(files[path])).entries:
                if e.type_name != "rModel":
                    continue
                sig = tuple((b["id"], b["parent_id"]) for b in mod.bones(e.data))
                (shield if "/sld" in e.file_name else sword)[sig] += 1
        return sword, shield

    sword3, shield3 = rigs("mh3u", r"/arc/weapon/mod/w01/w01_\d+\.arc")
    sword4, shield4 = rigs("mh4u", r"/data/pl_one\d+\.arc")
    two = ((0, 0xFF), (1, 0))          # id 0 root, id 1 its child: the sword's rig, and some shields'
    one = ((0, 0xFF),)                 # id 0 root alone: a one-bone sword or shield
    two_skeletons = two + ((0, 0xFF), (1, 0))   # two skeletons in one bone block: some shields'
    assert dict(sword3) == {two: 39, one: 15}, dict(sword3)
    assert dict(shield3) == {one: 33, two: 20, two_skeletons: 1}, dict(shield3)
    assert dict(sword4) == {two: 99, one: 29}, dict(sword4)
    assert dict(shield4) == {one: 100, two: 22, two_skeletons: 6}, dict(shield4)
    assert set(sword3) == set(sword4) and set(shield3) == set(shield4), "a rig exists in only one game"
    # every bone is id 0 or 1: no SnS model in either game has a bone id 2 or higher
    for counts in (sword3, shield3, sword4, shield4):
        assert all({i for i, _parent in sig} <= {0, 1} for sig in counts), "a SnS model has a bone above id 1"

    # MH4U's weapon motion list: ids 0, 1, 2 and 255; id 2 is not a bone of any SnS model
    image, files = games["mh4u"]
    wg = next(e.data for e in arc.read(image.read(files["/data/pl_w01.arc"])).entries
              if e.file_name == "weapon/one/mot/wg01.lmt")
    version, anims = lmt.read(wg)
    present = [a for a in anims if a]
    assert (version, len(anims), len(present)) == (67, 25, 19), (version, len(anims), len(present))
    assert dict(Counter(t.bone for a in present for t in a.tracks)) == {0: 11, 1: 22, 2: 10, 255: 2}, \
        "MH4U's wg01.lmt addresses bones other than 0, 1, 2 and 255"

    # MH3U has no weapon-rig motion list: the player's 50 lists are all it has, and none is in a weapon arc
    image, files = games["mh3u"]
    mot = [p for p in files if p.startswith("/arc/player/mot/")]
    player = [e for p in mot for e in arc.read(image.read(files[p])).entries if e.data[:4] == b"LMT\0"]
    assert len(mot) == 15 and len(player) == 50, (len(mot), len(player))
    assert all(e.file_name.startswith("player/mot/") for e in player)
    weapons = [p for p in files if p.startswith("/arc/weapon/")]
    assert len(weapons) == 574, len(weapons)
    assert not [e for p in weapons for e in arc.read(image.read(files[p])).entries if e.data[:4] == b"LMT\0"], \
        "an MH3U weapon arc holds a motion list"


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


def test_the_ported_monsters_text_comes_from_their_source_games(dump):
    dump("mhxx", "romfs.bin")
    dump("mh3u", "romfs.bin")
    entries = monstertext.build(os.environ["MHUC_DUMPS"])
    by_id = {e.id: e for e in entries}
    registry = {int(r["id"]): r for r in monstertext.registry_rows()}
    assert sorted(by_id) == sorted(registry)
    assert all(e.name == registry[e.id]["name"] for e in entries)   # the registry's names
    # The GU rows (MHXX JPN) have Japanese notes; the 3U rows (MH3U USA) have English ones.
    for ident in (124, 126):
        assert not by_id[ident].notes.isascii(), ident
        assert registry[ident]["source_game"] == "mhxx"
    for ident in (125, 127):
        assert by_id[ident].notes.isascii(), ident
        assert registry[ident]["source_game"] == "mh3u"
    assert all(len(e.notes) > 40 for e in entries)
    assert "\r" not in "".join(e.notes for e in entries)
    # the built table is what the plugin reads, and the checker accepts it
    table = monstertext.write(entries)
    assert monstertext.read_mod_text(table) == entries
    assert monstertext.check(monstertext.registry_rows(), monstertext.read_notes()) == []


def test_every_mh4u_message_table_reads(dump):
    """check LM1: every rLayoutMessage entry of the five languages reads, in the base and update RomFS."""
    wanted = 920
    if True:
        image = romfs.open_image(dump("mh4u", "romfs.bin"))
        per_language: dict[str, int] = {}
        name_counts = {}
        failures = []
        for f in image.files():
            if not (f.path.endswith(".arc") and "/data/core_" in f.path):
                continue
            language = f.path.split("/")[1]
            for e in arc.read(image.read(f)).entries:
                if e.data[:4] != lmd.MAGIC:
                    continue
                per_language[language] = per_language.get(language, 0) + 1
                try:
                    table = lmd.read(e.data)
                except (lmd.LmdError, struct.error, IndexError, UnicodeDecodeError) as exc:
                    failures.append(f"{f.path}:{e.file_name}: {exc}")
                    continue
                if any(m.chars != m.width for m in table.messages):
                    failures.append(f"{f.path}:{e.file_name}: two lengths differ")
                if "/msg/emName_" in e.file_name or "/msg/emExp_" in e.file_name:
                    name_counts[e.file_name] = len(table.messages)
        assert not failures, f"{len(failures)} tables not read, first: {failures[:3]}"
        assert set(per_language) == {"eng", "fre", "ger", "ita", "spa"}, sorted(per_language)
        assert sum(per_language.values()) == wanted, per_language
        assert set(per_language.values()) == {wanted // 5}, per_language
        assert len(name_counts) == 10, name_counts          # emName and emExp in five languages
        assert set(name_counts.values()) == {123}, name_counts


def test_every_mh4u_layout_reads(dump):
    """check LY1: every rLayout entry of the five languages reads, and the per-language tallies agree."""
    layout_id = classid.class_id("rLayout")
    image = romfs.open_image(dump("mh4u", "romfs.bin"))
    per: dict[str, Counter] = {}
    failures = []
    for f in image.files():
        if not (f.path.endswith(".arc") and "/data/core_" in f.path):
            continue
        counts = per.setdefault(f.path.split("/")[1], Counter())
        for e in arc.read(image.read(f)).entries:
            if e.type_id != layout_id:
                continue
            counts["layouts"] += 1
            try:
                layout = lyt.read(e.data)
            except (lyt.LytError, struct.error, IndexError, UnicodeDecodeError) as exc:
                failures.append(f"{f.path}:{e.path}: {exc}")
                continue
            for node in layout.nodes:
                counts[node.type_name] += 1
            for texture in layout.textures:
                counts["texture paths" if texture.path else "empty texture slots"] += 1
            counts["roots with no child"] += sum(1 for r in layout.roots if not layout.children(r))
            term = layout.nodes[-1].offset + lyt.NODE_SIZES[layout.nodes[-1].type]
            root_off = struct.unpack_from("<I", e.data, 0x2C)[0]
            for node in layout.nodes:
                if node.name:
                    at = struct.unpack_from("<I", node.raw, 0x0C)[0]
                    if not term + 0x14 <= at < root_off:
                        failures.append(f"{f.path}:{e.path}: {node.name} at 0x{at:x}, outside the names")
    assert not failures, f"{len(failures)} layouts not read, first: {failures[:3]}"
    expected = Counter({"layouts": 165, "root": 1246, "picture": 18616, "group": 4825, "text": 4256,
                        "boundary": 702, "texture paths": 636, "empty texture slots": 13,
                        "roots with no child": 1})
    assert set(per) == {"eng", "fre", "ger", "ita", "spa"}, sorted(per)
    for language, counts in sorted(per.items()):
        assert counts == expected, f"{language}: {counts - expected} over, {expected - counts} short"


def test_the_gu_rathian_conversion_keeps_mhxxs_files_under_the_ports_paths(dump):
    from mhuc import monsters

    image = romfs.open_image(dump("mhxx", "romfs.bin"))
    source_file = next(f for f in image.files() if f.path == "/arc/enemy/em001_00.arc")
    source_data = image.read(source_file)
    image4 = romfs.open_image(dump("mh4u", "romfs.bin"))
    stand_in = image4.read(next(f for f in image4.files() if f.path == "/data/em001.arc"))
    row = monsters.registry_row(124)
    converted_data, report = monsters.convert(source_data, row, stand_in)
    converted = arc.read(converted_data)
    source = {e.file_name: e.data for e in arc.read(source_data).entries}
    stand_in_entries = {e.file_name: e.data for e in arc.read(stand_in).entries}
    assert converted.version == 0x13
    port = {
        "enemy/em001/em001_00/mod/em001_00_BM.tex",
        "enemy/em001/em001_00/mod/em001_00_NM_MIRROR.tex",
        "enemy/em124/mod/em124.mrl",
        "enemy/em124/mod/em124.mod",
        "enemy/em124/mod/em124_tail.mrl",
        "enemy/em124/mod/em124_tail.mod",
        "enemy/em124/mot/em124_0.lmt",
        "enemy/em124/mot/em124_1.lmt",
        "enemy/em124/mot/em124_2.lmt",
        "enemy/em124/mot/em124_3.lmt",
        "enemy/em124/mot/em124_4.lmt",
        "enemy/em124/data/em124_cmd.emc",
    }
    assert {e.file_name for e in converted.entries if e.file_name in port} == port
    # Every other entry is an entry of MH4U's stand-in archive the record keeps (the camera,
    # motion effects, sound and effect lists the row does not ship), at its original path.
    kept = [e for e in converted.entries if e.file_name not in port]
    assert {e.file_name for e in kept} == set(report.copied)
    assert all(e.file_name in stand_in_entries for e in kept)
    assert {e.file_name for e in kept if e.file_name.startswith("enemy/")} == {
        "enemy/em001/mot/e001_cam.lcm"}
    assert {e.file_name for e in kept if e.file_name.startswith("effect/mef/")} == {
        "effect/mef/em/em001_0.mef", "effect/mef/em/em001_1.mef"}
    assert "sound/call/em/em001.mss" in {e.file_name for e in kept}
    assert any(e.file_name.startswith("effect/efl/em/em001/") for e in kept)
    for e in kept:
        assert e.data == stand_in_entries[e.file_name], e.file_name
    taken = {
        "enemy/em124/mod/em124.mod": "enemy/em001/em001_00/mod/em001_00.mod",
        "enemy/em124/mod/em124.mrl": "enemy/em001/em001_00/mod/em001_00.mrl",
        "enemy/em124/mod/em124_tail.mod": "enemy/em001/em001_00/mod/em001_00_tail.mod",
        "enemy/em124/mod/em124_tail.mrl": "enemy/em001/em001_00/mod/em001_00_tail.mrl",
        "enemy/em124/mot/em124_0.lmt": "enemy/em001/em001_00/mot/em001_00_0.lmt",
        "enemy/em124/mot/em124_1.lmt": "enemy/em001/em001_00/mot/em001_00_1.lmt",
        "enemy/em124/mot/em124_2.lmt": "enemy/em001/em001_00/mot/em001_00_2.lmt",
        "enemy/em124/mot/em124_3.lmt": "enemy/em001/em001_00/mot/em001_00_3.lmt",
        "enemy/em124/mot/em124_4.lmt": "enemy/em001/em001_00/mot/em001_00_4.lmt",
        "enemy/em124/data/em124_cmd.emc": "enemy/cmd_tbl/em001_00_cmdtbl.emc",
    }
    for port_path, source_path in taken.items():
        got = next(e for e in converted.entries if e.file_name == port_path).data
        if port_path.endswith(".mrl"):
            # specs/mrl.md check MR1: the one byte range a taken material changes is the
            # signature at 0x10, which MH4U's loader checks for its own value.
            assert struct.unpack_from("<I", got, mrl.SIGNATURE_AT)[0] == mrl.SIGNATURES["mh4u"], port_path
            assert [i for i in range(len(source[source_path])) if source[source_path][i] != got[i]] \
                == list(range(mrl.SIGNATURE_AT, mrl.SIGNATURE_AT + 4)), port_path
        else:
            assert got == source[source_path], port_path
    for entry in converted.entries:
        if entry.type_name != "rTexture":
            continue
        before = source[entry.file_name]
        assert len(entry.data) == len(before), entry.file_name
        assert [i for i in range(len(before)) if before[i] != entry.data[i]] == [4], entry.file_name
    assert row.files == {"model", "motions", "tail", "cmd"} and row.motions == {0, 1, 2, 3, 4}
    assert sum(len(v) for v in report.left_out.values()) == 534

def test_mh3u_rathians_mod_archive_holds_her_files_at_her_ported_ids_paths(dump):
    """docs/architecture.md#monsters, issue #49: `mhuc convert monster` turns MH3U's `arc/enemy/em001.arc` into
    `/data/em125.arc`: her two models, materials and textures as they are, her three motion lists as LMT version 67,
    and nothing else."""
    from mhuc import monsterassets

    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    src = next(image.read(f) for f in image.files() if f.path == "/arc/enemy/em001.arc")
    source = [e for e in arc.read(src).entries if e.path.startswith("enemy\\em001\\")]
    mod = monsterassets.convert(src, 125)
    built = arc.read(mod.archive())
    assert {e.type_name for e in built.entries} == {"rModel", "rMaterial", "rTexture", "rMotionList"}
    assert Counter(e.type_name for e in built.entries) == {"rModel": 2, "rMaterial": 2, "rTexture": 2,
                                                           "rMotionList": 3}
    assert all(e.path.startswith("enemy\\em125\\") for e in built.entries)
    # the kept files are the source's bytes; only their paths (and the materials' texture paths) differ
    kept = {e.path.rsplit("\\", 1)[1]: e for e in source if e.type_name in ("rModel", "rTexture")}
    for e in built.entries:
        if e.type_name in ("rModel", "rTexture"):
            name = e.path.rsplit("\\", 1)[1].replace("em125", "em001")
            assert e.data == kept[name].data, e.path
    textures = {e.path for e in built.entries}
    for e in built.entries:
        if e.type_name == "rMaterial":
            assert b"enemy\\em001\\" not in e.data, e.path
            for path in monsterassets.TEXTURE_PATH.findall(e.data):
                assert path.decode() in textures, (e.path, path)
            # specs/mrl.md check MR1: MH4U's loader accepts its own signature only, so the one
            # field the material changes besides its texture paths is that signature.
            assert struct.unpack_from("<I", e.data, mrl.SIGNATURE_AT)[0] == mrl.SIGNATURES["mh4u"]
            source_material = next(x for x in source
                                   if x.path == e.path.replace("em125", "em001"))
            restored = e.data.replace(b"em125", b"em001")
            assert [i for i in range(len(source_material.data)) if source_material.data[i] != restored[i]] \
                == list(range(mrl.SIGNATURE_AT, mrl.SIGNATURE_AT + 4)), e.path
    # the motion lists are version 67 and hold the source's animations and tracks
    source_motions = sorted((e for e in source if e.type_name == "rMotionList"), key=lambda e: e.path)
    built_motions = sorted((e for e in built.entries if e.type_name == "rMotionList"), key=lambda e: e.path)
    assert [e.path for e in built_motions] == [f"enemy\\em125\\mot\\em125_{i}" for i in range(3)]
    for old, new in zip(source_motions, built_motions, strict=True):
        old_version, old_animations = lmt.read(old.data)
        new_version, new_animations = lmt.read(new.data)
        assert (old_version, new_version) == (66, 67)
        assert len(old_animations) == len(new_animations)
        for a, b in zip(old_animations, new_animations, strict=True):
            if a is None:
                assert b is None
                continue
            assert (a.frames, a.loop_frame, len(a.tracks), bool(a.events)) == \
                   (b.frames, b.loop_frame, len(b.tracks), bool(b.events))

def test_the_three_games_material_signature_is_their_own_and_names_hash_to_their_records(dump):
    """specs/mrl.md checks MR1 and MR2, issue #203: each game's material files carry that game's
    signature at 0x10 (MH4U's loader accepts only its own), and every material name its model
    lists hashes to one of the material file's 0x3c-byte records."""
    cases = {"mh4u": "/data/em001.arc", "mh3u": "/arc/enemy/em001.arc",
             "mhxx": "/arc/enemy/em001_00.arc"}
    pairs = 0
    for game, path in cases.items():
        image = romfs.open_image(dump(game, "romfs.bin"))
        source = arc.read(next(image.read(f) for f in image.files() if f.path == path))
        at_path = {}
        for e in source.entries:
            at_path.setdefault(e.path, []).append(e)
        for model_path, entries in at_path.items():
            models = [e for e in entries if e.type_name == "rModel"]
            materials = [e for e in entries if e.type_name == "rMaterial"]
            if not models or not materials:
                continue
            header = mod.header(models[0].data)
            mrl_data = materials[0].data
            assert struct.unpack_from("<I", mrl_data, mrl.SIGNATURE_AT)[0] == mrl.SIGNATURES[game], model_path
            hashes = set(mrl.material_hashes(mrl_data))
            for i in range(header["materials"]):
                name = models[0].data[header["materials_at"] + i * 0x80:
                                        header["materials_at"] + (i + 1) * 0x80].split(b"\0")[0]
                if name:
                    assert (~zlib.crc32(name)) & 0xFFFFFFFF in hashes, (game, model_path, name)
            pairs += 1
    assert pairs >= 3
def test_every_material_a_monster_model_names_is_keyed_in_its_material_file(dump):
    """specs/mrl.md check MR4: a model's material table holds 0x80-byte names (mod.md, check M6) and the
    material at the same path holds one 0x3c-byte record per name, keyed by the name's CRC-32 with no final
    inversion. Every model/material pair sharing a path in every monster archive of MH4U and MH3U is checked."""
    checked = 0
    for game, pattern in (("mh4u", r"/data/em\d+\.arc"), ("mh3u", r"/arc/enemy/em\d+\.arc")):
        image = romfs.open_image(dump(game, "romfs.bin"))
        for entry in image.files():
            if not re.fullmatch(pattern, entry.path):
                continue
            entries = arc.read(image.read(entry)).entries
            models = {e.path: e for e in entries if e.type_name == "rModel"}
            materials = {e.path: e for e in entries if e.type_name == "rMaterial"}
            for name, model in models.items():
                material = materials.get(name)
                if material is None:
                    continue
                keys = set(mrl.material_hashes(material.data))
                for material_name in monsterassets.material_names(model.data):
                    assert mrl.material_key(material_name) in keys, (entry.path, name, material_name)
                checked += 1
    assert checked > 100, f"only {checked} model/material pairs found"


def test_every_mh3u_motion_list_converts_to_version_67(dump):
    """specs/lmt.md check L6: `mhuc.formats.lmt.convert` rebuilds every MH3U motion list as version 67, keeping
    every animation's frames, tracks and events and every key's frames and components (type 11 to 13 within the
    version-67 unsigned field's half step)."""
    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    lists = animations = tracks = reencoded = 0
    worst = 0.0
    for name, data in motion_lists(image):
        version, source = lmt.read(data)
        assert version == 66, name
        out = lmt.convert(data)
        assert lmt.read(out)[0] == 67, name
        converted = lmt.read(out)[1]
        assert len(source) == len(converted), name
        for a, b in zip(source, converted, strict=True):
            if a is None:
                assert b is None, name
                continue
            animations += 1
            assert (a.frames, a.loop_frame, a.flags, bool(a.events)) == (b.frames, b.loop_frame, b.flags,
                                                                         bool(b.events)), name
            for t, u in zip(a.tracks, b.tracks, strict=True):
                tracks += 1
                assert (t.buffer_type, t.usage, t.joint_type, t.bone) == \
                       (u.buffer_type, u.usage, u.joint_type, u.bone), name
                keys, converted_keys = lmt.decode_keys(data, t, 66, a.frames), lmt.decode_keys(out, u, 67, b.frames)
                assert [k.frame for k in keys] == [k.frame for k in converted_keys], name
                if t.buffer_type in (11, 12, 13):
                    reencoded += 1
                    scale, offset = lmt.bounds(out, u)
                for k, v in zip(keys, converted_keys, strict=True):
                    values = v.value
                    if t.buffer_type in (11, 12, 13):
                        values = tuple(offset[i] + scale[i] * values[i] for i in range(4))
                    worst = max(worst, max(abs(p - q) for p, q in zip(k.value, values, strict=True)))
        lists += 1
    assert (lists, animations, tracks) == (387, 8336, 270420), (lists, animations, tracks)
    assert reencoded == 38311, reencoded
    assert worst < 6.2e-5, worst


def test_convert_monster_builds_her_files_and_sounds_into_one_folder(dump, tmp_path):
    """docs/architecture.md#3u-rathians-files and specs/sound.md SN9: `mhuc convert monster` writes one folder,
    `/data/em125.arc`, holding her models, materials, textures and motion lists and her converted sound set."""
    from mhuc import cli

    image = romfs.open_image(dump("mh3u", "romfs.bin"))
    sources = {"/arc/enemy/em001.arc": None, "/arc/sound/se/em/em001/snd_em001.arc": None}
    for f in image.files():
        if f.path in sources:
            sources[f.path] = tmp_path / os.path.basename(f.path)
            sources[f.path].write_bytes(image.read(f))
    out = tmp_path / "mod"
    assert cli.main(["convert", "monster", "--id", "125", "--romfs", dump("mh3u", "romfs.bin"),
                     "--mh4u-romfs", dump("mh4u", "romfs.bin"), "--out", str(out)]) == 0
    assert cli.main(["convert", "monster", "--id", "125", "--arc", str(sources["/arc/enemy/em001.arc"]),
                     "--sound-arc", str(sources["/arc/sound/se/em/em001/snd_em001.arc"]),
                     "--out", str(out)]) == 0
    built = arc.read((out / "romfs" / "data" / "em125.arc").read_bytes())
    paths = {e.path for e in built.entries}
    for path in ("enemy\\em125\\mod\\em125", "enemy\\em125\\mod\\em125_tail",
                 "enemy\\em125\\mod\\em125_BM", "enemy\\em125\\mod\\em125_NM_MIRROR",
                 "enemy\\em125\\mot\\em125_0", "enemy\\em125\\mot\\em125_1",
                 "enemy\\em125\\mot\\em125_2", "sound\\call\\em\\em125",
                 "sound\\se\\em\\em125\\snd_em125"):
        assert path in paths, path
    # The record keeps the stand-in's camera, motion effects, command and effect lists, and the
    # two motion slots the row does not ship; the archive carries a copy of each.
    for path in ("enemy\\em001\\mot\\e001_cam", "effect\\mef\\em\\em001_0",
                 "effect\\mef\\em\\em001_1", "enemy\\em001\\data\\em001_cmd",
                 "effect\\efl\\em\\em001\\em001_000", "enemy\\em001\\mot\\em001_3",
                 "enemy\\em001\\mot\\em001_4"):
        assert path in paths, path
    counts = Counter(e.type_name for e in built.entries)
    port_motions = [e for e in built.entries
                    if e.type_name == "rMotionList" and e.path.startswith("enemy\\em125\\")]
    assert len(port_motions) == 3 and counts["rLtSoundSourceADPCM"] == 48, counts
    for e in port_motions:
        assert lmt.read(e.data)[0] == 67


def test_the_giadrome_conversion_builds_its_folder_from_mhxxs_own_archive(dump, tmp_path):
    from types import SimpleNamespace
    image = romfs.open_image(dump("mhxx", "romfs.bin"))
    source_file = next(f for f in image.files() if f.path == "/arc/enemy/em034_00.arc")
    source_data = image.read(source_file)
    out = tmp_path / "giadrome"
    args = SimpleNamespace(id=126, romfs=dump("mhxx", "romfs.bin"), out=str(out), variant=0,
                           registry=None, game="mhxx", report=str(tmp_path / "report.txt"),
                           mh4u_romfs=dump("mh4u", "romfs.bin"))
    assert cli._convert_monster_files(args) == 0
    converted = arc.read((out / "romfs" / "data" / "em126.arc").read_bytes())
    source = {e.file_name: e.data for e in arc.read(source_data).entries}
    assert converted.version == 0x13
    # Giadrome's motion lists are MHXX's em014's (Velocidrome), at slots 0, 2, 3 and 4; the
    # converter renames them to the port's id but keeps the slot. Its AI script is left out:
    # the row does not ship `cmd`, because MHXX's EMC is not MH4U's (specs/emc.md).
    port = {
        "enemy/em034/em034_00/mod/em034_00_01_BM.tex",
        "enemy/em034/em034_00/mod/em034_00_01_NM_MQ_MIRROR.tex",
        "enemy/em126/mod/em126.mrl",
        "enemy/em126/mod/em126.mod",
        "enemy/em126/mot/em126_0.lmt",
        "enemy/em126/mot/em126_2.lmt",
        "enemy/em126/mot/em126_3.lmt",
        "enemy/em126/mot/em126_4.lmt",
    }
    image4 = romfs.open_image(dump("mh4u", "romfs.bin"))
    stand_in = image4.read(next(f for f in image4.files() if f.path == "/data/em015.arc"))
    stand_in_entries = {e.file_name: e.data for e in arc.read(stand_in).entries}
    assert {e.file_name for e in converted.entries if e.file_name in port} == port
    # The rest is the stand-in's (Great Jaggi's) archive: the row ships no camera, tail, mef,
    # sound, cmd or efl, so the record keeps those paths and the archive must carry them.
    kept = [e for e in converted.entries if e.file_name not in port]
    assert kept and all(e.file_name in stand_in_entries for e in kept)
    assert {e.file_name for e in kept if e.file_name.startswith("enemy/em015/mot/")} == {
        "enemy/em015/mot/e015_cam.lcm"}
    assert "effect/mef/em/em015_0.mef" in {e.file_name for e in kept}
    assert "sound/call/em/em015.mss" in {e.file_name for e in kept}
    assert "enemy/em015/data/em015_cmd.emc" in {e.file_name for e in kept}
    assert "effect/efl/em/em015/em015_000.efl" in {e.file_name for e in kept}
    taken = {
        "enemy/em126/mod/em126.mod": "enemy/em034/em034_00/mod/em034_00.mod",
        "enemy/em126/mod/em126.mrl": "enemy/em034/em034_00/mod/em034_00.mrl",
        "enemy/em126/mot/em126_0.lmt": "enemy/em014/em014_00/mot/em014_00_0.lmt",
        "enemy/em126/mot/em126_2.lmt": "enemy/em014/em014_00/mot/em014_00_2.lmt",
        "enemy/em126/mot/em126_3.lmt": "enemy/em014/em014_00/mot/em014_00_3.lmt",
        "enemy/em126/mot/em126_4.lmt": "enemy/em014/em014_00/mot/em014_00_4.lmt",
    }
    for port_path, source_path in taken.items():
        got = next(e for e in converted.entries if e.file_name == port_path).data
        if port_path.endswith(".mrl"):
            # specs/mrl.md check MR1: the one byte range a taken material changes is the
            # signature at 0x10, which MH4U's loader checks for its own value.
            assert struct.unpack_from("<I", got, mrl.SIGNATURE_AT)[0] == mrl.SIGNATURES["mh4u"], port_path
            assert [i for i in range(len(source[source_path])) if source[source_path][i] != got[i]] \
                == list(range(mrl.SIGNATURE_AT, mrl.SIGNATURE_AT + 4)), port_path
        else:
            assert got == source[source_path], port_path
    for entry in converted.entries:
        if entry.type_name != "rTexture":
            continue
        before = source[entry.file_name]
        assert len(entry.data) == len(before), entry.file_name
        assert [i for i in range(len(before)) if before[i] != entry.data[i]] == [4], entry.file_name
    assert not any("em034" in e.file_name and e.file_name.endswith("_cmd.emc")
                   for e in converted.entries)
    report = (tmp_path / "report.txt").read_text(encoding="utf-8")
    assert "left out (not in the row's files: cmd): enemy/cmd_tbl/em034_00_cmdtbl.emc" in report
def test_great_wroggis_conversion_ships_the_kinds_and_slots_its_row_names(dump, tmp_path):
    """docs/architecture.md#a-ported-monsters-files, issue #166: `mhuc convert monster --from mh3u` turns
    MH3U's `arc/enemy/em045.arc` into `/data/em127.arc` at the port's own id paths, and the archive holds
    exactly the kinds and motion slots its registry row ships, so the record the plugin builds from the row
    cannot name a missing file (#143)."""
    from mhuc import cli, monsterassets

    romfs_path = dump("mh3u", "romfs.bin")
    image = romfs.open_image(romfs_path)
    source_file = next(f for f in image.files() if f.path == "/arc/enemy/em045.arc")
    source = arc.read(image.read(source_file))

    out = tmp_path / "mod"
    assert cli.main(["convert", "monster", "--from", "mh3u", "--id", "127",
                     "--romfs", romfs_path, "--mh4u-romfs", dump("mh4u", "romfs.bin"),
                     "--out", str(out)]) == 0
    built = arc.read((out / "romfs" / "data" / "em127.arc").read_bytes())
    assert built.version == 0x13
    port = [e for e in built.entries if e.path.startswith("enemy\\em127\\")]
    assert Counter(e.type_name for e in port) == {
        "rModel": 1, "rMaterial": 1, "rTexture": 1, "rMotionList": 3}
    # The record keeps Great Jaggi's camera, motion effects, sound, command and effect lists
    # (the row ships model and motions only), so the archive carries MH4U's own copies.
    image4 = romfs.open_image(dump("mh4u", "romfs.bin"))
    stand_in = arc.read(image4.read(next(f for f in image4.files() if f.path == "/data/em015.arc")))
    stand_in_entries = {e.file_name for e in stand_in.entries}
    kept = [e for e in built.entries if not e.path.startswith("enemy\\em127\\")]
    assert kept and all(e.file_name in stand_in_entries for e in kept)
    assert {"enemy/em015/mot/e015_cam.lcm", "effect/mef/em/em015_0.mef",
            "sound/call/em/em015.mss", "enemy/em015/data/em015_cmd.emc"} <= {
        e.file_name for e in kept}

    # The registry's row and the built archive agree on the kinds and motion slots.
    rows, problems = check_ids.read_registry(monstersound.REGISTRY)
    assert problems == []
    row = next(r for r in rows if r["id"] == "127")
    assert row["source_key"] == "em045" and row["stand_in"] == "15"
    ships = {kind for kind, _ in check_ids.files_tokens(row["files"])}
    assert ships == {"model", "motions"}
    assert check_ids.motion_slots(row["files"]) == sorted(
        int(e.path.rsplit("_", 1)[1]) for e in port if e.type_name == "rMotionList")

    # The model and texture are the source's bytes; the materials name only textures the archive has.
    kept = {e.path.rsplit("\\", 1)[1].replace("em045", "em127"): e.data
            for e in source.entries if e.type_name in ("rModel", "rTexture")}
    for e in port:
        if e.type_name in ("rModel", "rTexture"):
            assert e.data == kept[e.path.rsplit("\\", 1)[1]], e.path
        if e.type_name == "rMaterial":
            assert b"enemy\\em045\\" not in e.data, e.path
            for path in monsterassets.TEXTURE_PATH.findall(e.data):
                assert path.decode() in {e.path for e in built.entries}, (e.path, path)

    # The motion lists are version 67 and keep the source's animations, tracks and events.
    source_motions = sorted((e for e in source.entries if e.type_name == "rMotionList"), key=lambda e: e.path)
    built_motions = sorted((e for e in port if e.type_name == "rMotionList"), key=lambda e: e.path)
    assert [e.path for e in built_motions] == [f"enemy\\em127\\mot\\em127_{i}" for i in range(3)]
    for old, new in zip(source_motions, built_motions, strict=True):
        old_version, before = lmt.read(old.data)
        new_version, after = lmt.read(new.data)
        assert (old_version, new_version) == (66, 67)
        assert len(before) == len(after)
        for a, b in zip(before, after, strict=True):
            if a is None:
                assert b is None
                continue
            assert (a.frames, a.loop_frame, len(a.tracks), bool(a.events)) == \
                   (b.frames, b.loop_frame, len(b.tracks), bool(b.events))
