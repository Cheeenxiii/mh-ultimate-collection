"""The real contract: our readers and writers against the game's own files."""
from __future__ import annotations

import os
import struct
from collections import Counter

import pytest

from mhuc import monsterdata
from mhuc.crypto import dlccrypt
from mhuc.crypto.blowfish import Blowfish
from mhuc.formats import arc, dtbase, dtbparts, dttune, emstatus, hitdata, lmt, mod, romfs, sound, stq
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


# bytes one key takes in each keyframe buffer type, from RevilLib's src/mtf_lmt/codecs.hpp
LMT_KEY_STRIDE = {1: 12, 2: 12, 3: 16, 4: 8, 5: 4, 6: 8, 7: 4, 11: 4, 12: 4, 13: 4, 14: 6, 15: 6}


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
                assert not t.buffer_size or t.buffer_size % LMT_KEY_STRIDE[t.buffer_type] == 0, (name, t.buffer_size)
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
