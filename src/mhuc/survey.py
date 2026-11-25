"""`mhuc survey`: run the with-game-files checks of specs/ over a RomFS image and print counts.

It reads the image in place (mhuc.romfs) and every ARC inside it, and reports only counts,
versions and pass/fail tallies: nothing from the files themselves, so its output can go into
a spec or a report (CLAUDE.md, rule 1). Checks covered: C2, C3 (arc), T1, T3 (tex),
G1, G2 (gmd), M1, M3 (mod), Q1, Q2, Q6, Q13, Q18 (quest), E1 (emd), E2 (MHXX dttune), E3 (MH3U
em_status), E4 (body, attack volume and attack record files), E7 (MHXX dtbase and dtbparts), E8 (MH3U attack
records against their hit volumes), E9 (MH3U em_status break blocks), E11 (MHXX dtbparts joint record kinds),
L1 (lmt), C1 (rCameraList), LY1 (MH4U layouts), A1 (rEnemyCmd), S1 (rCollision), X1 (XFS files in either
byte order), SN1 (sound
resources by kind, version and class id), SN6 (the MH3U wave, bank, request and stream request layouts), S4 (MH4U
stream requests), U1 (whether a stage resource references the water-surface class uOcean).

Memory: each worker holds one archive and its decompressed entries at a time; keep the
worker count low on machines with little RAM (default 4).
"""
from __future__ import annotations

import struct
from collections import Counter
from multiprocessing import Pool

from .formats import (
    arc,
    camera,
    classid,
    dtbase,
    dtbparts,
    dttune,
    emd,
    emstatus,
    gmd,
    hitdata,
    lmt,
    lyt,
    pica,
    romfs,
    sound,
    stq,
    tex,
    xfs,
)
from .formats import mod as modfile
from .quests import quest as questfile

QUEST_TYPES = ("rQuestData", "rSetEmMain", "rEmSetList", "rRem")

# Sound resources (specs/sound.md, check SN1), keyed by their first four bytes. The u32 after the
# magic is a version for the kinds in SOUND_VERSIONED; the rest pack flags into it.
SOUND_MAGIC: dict[bytes, str] = {
    b"MADP": "wave", b"SNDB": "bank", b"SREQ": "request",
    b"SBKR": "bank", b"SRQR": "request",
    b"STRQ": "stream request", b"STQR": "stream request",
    b"SES\x00": "area emitter",
    b"MSS\x00": "sequence",
    b"REV\x00": "reverb", b"REVR": "reverb",
    b"CFL\x00": "category filter", b"EQUR": "EQ",
}
SOUND_VERSIONED = {"wave", "bank", "request", "stream request", "area emitter", "sequence"}
# The class each game's registry gives a sound kind (specs/sound.md "Which class, which game"):
# MH4U and MH3U share the rLt* classes, MHXX has the next generation's rSound* ones.
_SOUND_CLASS_NAMES = (
    ("rLtSoundSourceADPCM", "wave"), ("rSoundSourceADPCM", "wave"),
    ("rLtSoundBank", "bank"), ("rSoundBank", "bank"),
    ("rLtSoundRequest", "request"), ("rSoundRequest", "request"),
    ("rLtSoundStreamRequest", "stream request"), ("rSoundStreamRequest", "stream request"),
    ("rMHSoundEmitter", "area emitter"), ("rFestaSoundEmitter", "area emitter"),
    ("rLtSoundReverb", "reverb"), ("rSoundReverb", "reverb"), ("rSoundEQ", "EQ"),
    ("rLtSoundCategoryFilter", "category filter"),
    ("rMHSoundSequence", "sequence"), ("rFestaSoundSequence", "sequence"), ("rSoundSequence", "sequence"),
    ("rSoundAttributeSe", "sound attribute se"),
)
SOUND_CLASSES: dict[int, str] = {classid.class_id(name): kind for name, kind in _SOUND_CLASS_NAMES}
SOUND_CLASS_NAMES: dict[int, str] = {classid.class_id(name): name for name, _ in _SOUND_CLASS_NAMES}

# Check U1: the water-surface class uOcean is engine code, not a resource class, so an ARC entry's
# type id would only be its class id if a stage data file stored the class itself. Stage resources
# live under these two path prefixes in every MT Framework Mobile game.
UOCEAN_ID = classid.class_id("uOcean")
UOCEAN_ID_BYTES = struct.pack("<I", UOCEAN_ID)
STAGE_PREFIXES = ("stage\\", "snake\\stage\\")

_IMG: romfs.Romfs | None = None


def _merge(total: dict, part: dict) -> None:
    for k, v in part.items():
        if isinstance(v, Counter):
            total.setdefault(k, Counter()).update(v)
        elif isinstance(v, int):
            total[k] = max(total.get(k, 0), v) if k.startswith("max_") else total.get(k, 0) + v


def tex_expected_size(data: bytes) -> int | None:
    """The file length mhff's header reading implies, or None if the format is unknown."""
    w1, w2, w3 = struct.unpack_from("<3I", data, 4)
    kind = w1 >> 28 & 0xF
    mips, width, height = w2 & 0x3F, w2 >> 6 & 0x1FFF, w2 >> 19 & 0x1FFF
    count, fmt_id = w3 & 0xFF, w3 >> 8 & 0xFF
    fmt = tex.FORMATS.get(fmt_id)
    if fmt is None or not mips or not count:
        return None
    size = 16 + (0x6C if kind == 6 else 0) + 4 * mips * count
    for m in range(mips):
        size += count * pica.data_size(fmt, max(8, width >> m), max(8, height >> m))
    return size


def _read_stream_request(data: bytes) -> dict:
    """Check SN6's stream request read; the S4 counters belong to MH4U's version only."""
    stq.read(data)
    return {}


def _sound(st: dict, data: bytes, kind: str, type_id: int | None) -> None:
    """Count one sound resource by kind, magic and version, and by class id when it sits in an ARC."""
    c = st.setdefault("sound", Counter())
    magic = data[:4].decode("latin-1").rstrip("\x00")
    version = struct.unpack_from("<I", data, 4)[0] if len(data) >= 8 else 0
    if kind in SOUND_VERSIONED and len(data) >= 8:
        c[f"{kind} {magic} v{version if version < 0x100 else f'0x{version:x}'}"] += 1
    else:
        c[f"{kind} {magic}"] += 1
    if kind == "stream request" and data[:4] == stq.MAGIC and version == stq.VERSION:
        try:
            c.update(stq.check(data))
        except stq.StqError:
            c["S4 .stq not read"] += 1
    # Check SN6: read the kind with the version-aware reader. MH4U's wave version 5 is read for
    # its mono effects; its stereo music layout isn't laid out, so those count as not read.
    reader = {"wave": sound.check_wave, "bank": sound.check_bank,
              "request": sound.check_request}.get(kind)
    if reader is None and kind == "stream request" and data[:4] == stq.MAGIC:
        reader = _read_stream_request
    if reader is not None:
        try:
            c.update(reader(data))
            c[f"SN6 {kind} read"] += 1
        except (sound.SoundError, stq.StqError):
            c[f"SN6 {kind} not read"] += 1
    # Check SN8: the sound call's three versions. They are small; reading every one is cheap.
    if kind == "sequence":
        try:
            c.update(sound.check_sequence(data))
            c["SN8 sequence read"] += 1
        except sound.SoundError:
            c["SN8 sequence not read"] += 1
    if type_id is None:
        c[f"{kind} {magic} loose"] += 1
    else:
        name = SOUND_CLASS_NAMES.get(type_id) or classid.name_of(type_id) or "?"
        c[f"{kind} {magic} type 0x{type_id:08x} {name}"] += 1


def survey_stage(path: str, data: bytes, type_id: int | None, st: dict) -> None:
    """Check U1: count stage resources and whether any references the water-surface class uOcean.

    MH4U keeps uOcean's class and code; whether its stages ever create the object is a data
    question, asked here over every entry whose stored path is a stage resource.
    """
    low = path.lower()
    if not low.startswith(STAGE_PREFIXES):
        return
    c = st.setdefault("stage", Counter())
    c["U1 stage-path entries"] += 1
    if type_id == UOCEAN_ID:
        c["U1 entries typed uOcean"] += 1
    if b"uOcean" in data:
        c["U1 stage entries naming uOcean"] += 1
    if UOCEAN_ID_BYTES in data:
        c["U1 stage entries carrying uOcean's class id"] += 1
    # Positive control: a water-surface resource name 3U and MH4U both use for baked surfaces.
    if b"suimen" in data or "suimen" in low:
        c["U1 stage entries naming a suimen surface"] += 1


def survey_entry(type_name: str | None, data: bytes, st: dict, type_id: int | None = None) -> None:
    if data[:4] in (b"XFS\0", b"\0SFX"):
        c = st.setdefault("xfs", Counter())
        try:
            x = xfs.read(data)
        except (xfs.XfsError, struct.error, IndexError, UnicodeDecodeError):
            c["X1 not read"] += 1
        else:
            c["X1 read"] += 1
            c[f"version {x.version}.{x.subversion}"] += 1
            c[f"{x.endian}-endian"] += 1
            c[f"{len(x.classes)} class definitions"] += 1
            c["loose" if type_id is None else f"type 0x{type_id:08x}"] += 1
    kind = SOUND_MAGIC.get(data[:4])
    if kind is None and type_id is not None:
        kind = SOUND_CLASSES.get(type_id)
    if kind is not None:
        _sound(st, data, kind, type_id)
        return
    if type_name == "rTexture" or data[:4] == b"TEX\0":
        c = st.setdefault("tex", Counter())
        if data[:4] != b"TEX\0" or len(data) < 16:
            c["bad magic"] += 1
            return
        w1, _, w3 = struct.unpack_from("<3I", data, 4)
        c[f"version 0x{w1 & 0xFFF:x}"] += 1
        c[f"kind {w1 >> 28 & 0xF}"] += 1
        c[f"format {w3 >> 8 & 0xFF}"] += 1
        exp = tex_expected_size(data)
        if exp is None:
            c["T1 unknown format"] += 1
        elif exp == len(data):
            c["T1 size matches"] += 1
        else:
            c["T1 size differs"] += 1
        if w1 >> 28 & 0xF == 2 and (w3 & 0xFF) == 1 and exp == len(data):
            try:
                c["T3 round trip ok" if tex.write(tex.read(data)) == data else "T3 round trip differs"] += 1
            except ValueError:
                c["T3 not readable"] += 1
    elif type_name == "rGUIMessage" or data[:4] == b"GMD\0":
        c = st.setdefault("gmd", Counter())
        if data[:4] != b"GMD\0":
            c[f"other magic {data[:4]!r}"] += 1
            return
        version = struct.unpack_from("<I", data, 4)[0]
        c[f"version 0x{version:08x}"] += 1
        try:
            g = gmd.read(data)
        except (ValueError, UnicodeDecodeError, IndexError, struct.error):
            c["G1 not readable"] += 1
            return
        c["G1 readable"] += 1
        c[f"language {g.language}"] += 1
        c[f"layout {g.layout}"] += 1
        c["G2 round trip ok" if gmd.write(g) == data else "G2 round trip differs"] += 1
        ok, n = gmd.hash_check(g)
        if n:
            c["G3 label hashes match"] += ok
            c["G3 label hashes differ"] += n - ok
    elif type_name == "rMotionList" or data[:4] == b"LMT\0":
        st.setdefault("lmt", Counter()).update(lmt.check(data))
    elif type_name == "rCameraList" or data[:4] == b"LCM\0":
        st.setdefault("camera", Counter()).update(camera.check(data))
    elif type_name == "rLayout" or data[:4] == b"lyt\0":
        st.setdefault("lyt", Counter()).update(lyt.check(data))
    elif data[:4] == b"QTDS":
        c = st.setdefault("quest", Counter())
        try:
            q = questfile.parse_qtds(data)
            c["Q13 QTDS read"] += 1
            c["Q13 record is the whole file" if q["size"] == len(data) else "Q13 bytes after the record"] += 1
        except (questfile.QuestError, struct.error, UnicodeDecodeError, IndexError) as e:
            c[f"Q13 QTDS not read: {str(e)[:40]}"] += 1
    elif type_name == "rQuestData" and data[4:8] == b"v005":
        c = st.setdefault("quest", Counter())
        try:
            q = questfile.parse_mib4(data)
        except (questfile.QuestError, struct.error, UnicodeDecodeError, IndexError):
            c["Q6 .mib not read"] += 1
            return
        c["Q6 .mib read"] += 1
        c[f"Q6 carve table {q['carve_table']}"] += 1
        c["Q6 stars 1..10" if 1 <= q["stars"] <= 10 else "Q6 stars outside 1..10"] += 1
        c["Q6 time 1..50" if 1 <= q["time_min"] <= 50 else "Q6 time outside 1..50"] += 1
        from .quests import mibwrite
        try:
            model = mibwrite.mib4_model(data)
            rebuilt = mibwrite.mib4_build(model)
            same = questfile.parse_mib4(rebuilt) == q and mibwrite.mib4_model(rebuilt) == model
            c["Q18 builder round trip ok" if same else "Q18 builder round trip differs"] += 1
            c["Q18 byte-identical" if rebuilt == data else "Q18 laid out differently"] += 1
        except (questfile.QuestError, struct.error, ValueError):
            c["Q18 model not built"] += 1
    elif type_name == "rEnemyCmd" or data[:4] == b"EMC\0":
        c = st.setdefault("emc", Counter())
        if data[:4] != b"EMC\0" or len(data) < 16:
            c[f"A1 other magic {data[:4]!r}"] += 1
            return
        version, groups = struct.unpack_from("<II", data, 4)
        c[f"A1 version 0x{version:08x}"] += 1
        if 16 + 16 * groups > len(data):
            c["A1 group table OUTSIDE"] += 1
            return
        tables = [struct.unpack_from("<II", data, 16 + 16 * g) for g in range(groups)]
        inside = all(o + 16 * n <= len(data) for n, o in tables)
        c["A1 groups and script tables inside" if inside else "A1 a script table OUTSIDE"] += 1
        c["A1 scripts"] += sum(n for n, _ in tables)
    elif type_name == "rCollision" or data[:4] == b"SBC\xff":
        c = st.setdefault("sbc", Counter())
        if data[:4] != b"SBC\xff" or len(data) < 0x20:
            c[f"S1 other magic {data[:4]!r}"] += 1
            return
        c[f"S1 inner class 0x{struct.unpack_from('<I', data, 4)[0]:08x}"] += 1
        c[f"S1 parts {'1' if struct.unpack_from('<H', data, 0x10)[0] == 1 else 'several'}"] += 1
    elif data[:4] == dttune.MAGIC:
        c = st.setdefault("monster data", Counter())
        try:
            dttune.blocks(data)
            c["E2 dttune layout ends at the file's end"] += 1
        except dttune.DttuneError as e:
            c[f"E2 dttune {str(e).split(',')[0]}"] += 1
    elif data[:4] == dtbase.MAGIC:
        c = st.setdefault("monster data", Counter())
        try:
            dtbase.blocks(data)
            c["E7 dtbase layout ends at the file's end"] += 1
        except dtbase.DtBaseError as e:
            c[f"E7 dtbase {str(e).split(',')[0]}"] += 1
    elif data[:4] == dtbparts.MAGIC:
        c = st.setdefault("monster data", Counter())
        try:
            dtbparts.blocks(data)
            c["E7 dtbparts layout ends at the file's end"] += 1
            kinds = [r[4] for r in dtbparts.records(data, "joint records", 13)]   # s32 joint, then kind
            if kinds:
                c["E11 dtbparts joint records"] += len(kinds)
                for kind in kinds:
                    c[f"E11 dtbparts joint record kind {kind}"] += 1
                c["E11 dtbparts no joint record of kind 0" if 0 not in kinds
                  else "E11 dtbparts SEVER RECORD of kind 0"] += 1
        except dtbparts.DtbPartsError as e:
            c[f"E7 dtbparts {str(e).split(',')[0]}"] += 1
    elif data[:4] == emstatus.MAGIC:
        c = st.setdefault("monster data", Counter())
        try:
            walk = emstatus.blocks(data)
            c["E3 em_status walk ends at the file's end"] += 1
            names = {n for n, _, _ in walk}
            if "block 0x74" in names:
                records = emstatus.part_break_records(data) or []
                c["E9 em_status break block 8 x 6 bytes"] += 1
                c["E9 em_status break block with its 3-byte companion (0x70)"
                  if "block 0x70" in names else "E9 em_status break block WITHOUT its companion"] += 1
                c["E9 em_status parts with a non-default break record"] += sum(
                    1 for r in records if r[:4] != bytes(4))
            if "block 0x6c" in names:
                hp = emstatus.second_part_hp(data) or []
                c["E9 em_status second part HP block 8 x s16"] += 1
                c["E9 em_status parts with a non-zero second HP"] += sum(1 for v in hp if v)
        except emstatus.EmStatusError as e:
            c[f"E3 em_status {str(e).split(':')[0]}"] += 1
    elif data[:4] in (hitdata.BDD[0], hitdata.HTS[0], hitdata.HDE[0], hitdata.HTD[0]):
        c = st.setdefault("monster data", Counter())
        kind = {hitdata.BDD[0]: "bdd", hitdata.HTS[0]: "hts", hitdata.HDE[0]: "hde", hitdata.HTD[0]: "htd"}[data[:4]]
        try:
            n = len(hitdata.groups(data)[1]) if kind == "hts" else len(hitdata.records(data, kind))
            c[f"E4 {kind} v{struct.unpack_from('<I', data, 4)[0]:#x} tiles the file"] += 1
            c[f"E4 {kind} {'groups' if kind == 'hts' else 'records'}"] += n
        except hitdata.HitDataError:
            c[f"E4 {kind} does NOT tile the file"] += 1
    elif type_name == "rEnemyData":
        st.setdefault("emd", Counter()).update(emd.check_emd(data))
    elif type_name == "rEnemyTuneData":
        st.setdefault("emd", Counter()).update(emd.check_etd(data))
    elif type_name == "rModel" or data[:4] == b"MOD\0":
        c = st.setdefault("mod", Counter())
        if data[:4] != b"MOD\0":
            c[f"other magic {data[:4]!r}"] += 1
            return
        c[f"version 0x{struct.unpack_from('<H', data, 4)[0]:04x}"] += 1
        c.update(modfile.check(data))


def survey_arc(data: bytes, st: dict) -> None:
    c = st.setdefault("arc", Counter())
    if data[:4] != b"ARC\0":
        c["not an ARC"] += 1
        return
    version = struct.unpack_from("<H", data, 4)[0]
    c[f"version 0x{version:x}"] += 1
    try:
        a = arc.read(data)
    except arc.ArcError:
        c["C2 not readable"] += 1
        return
    c["C2 readable"] += 1
    c["C2 round trip ok" if arc.write(a) == data else "C2 round trip differs"] += 1
    if a.data_start is not None:
        align = arc.DATA_ALIGN[version]
        c[f"first stream on a {align:#x} boundary" if a.data_start % align == 0 else "first stream unaligned"] += 1
    flags = st.setdefault("arc flags", Counter())
    types = []
    for e in a.entries:
        flags[f"0x{e.flags:08x}"] += 1
        st["max_entry_size"] = max(st.get("max_entry_size", 0), len(e.data))
        if len(e.data) > 0x00FFFFFF:
            c["C3 entry over 0x00FFFFFF"] += 1
        name = classid.name_of(e.type_id)
        types.append(name)
        survey_stage(e.path, e.data, e.type_id, st)
        survey_entry(name, e.data, st, e.type_id)
    pairs: dict = {}
    for e, name in zip(a.entries, types, strict=True):
        if name in ("rEnemyData", "rEnemyTuneData"):
            pairs.setdefault(e.path, {})[name] = e.data
    for pair in pairs.values():
        if len(pair) == 2:
            st.setdefault("emd", Counter()).update(emd.check_pair(pair["rEnemyData"], pair["rEnemyTuneData"]))
            st["emd"]["E1 pairs"] += 1
    hit_pairs: dict = {}
    for e in a.entries:
        if e.data[:4] in (hitdata.HTD[0], hitdata.HTS[0]):
            hit_pairs.setdefault(e.path.rsplit("\\", 1)[0], {})[e.data[:4]] = e.data
    for pair in hit_pairs.values():
        if hitdata.HTD[0] in pair and hitdata.HTS[0] in pair:
            st.setdefault("monster data", Counter()).update(
                hitdata.check_htd(pair[hitdata.HTD[0]], pair[hitdata.HTS[0]]))
    q = [t for t in types if t in QUEST_TYPES]
    if q:
        qc = st.setdefault("quest", Counter())
        qc["quest archives"] += 1
        qc["Q1 last entry rQuestData" if types[-1] == "rQuestData" else "Q1 last entry other"] += 1
        qc["Q2 holds " + "+".join(sorted(set(q)))] += 1


def _init(path: str) -> None:
    global _IMG
    _IMG = romfs.open_image(path)


def _one(f: romfs.File) -> dict:
    st: dict = {}
    data = _IMG.read(f)
    if f.path.endswith(".arc"):
        survey_arc(data, st)
    else:
        survey_entry(None, data, st)
    return st


def survey(path: str, workers: int = 4) -> dict:
    files = list(romfs.open_image(path).files())
    total: dict = {"files": len(files)}
    with Pool(workers, _init, (path,), maxtasksperchild=500) as pool:
        for part in pool.imap_unordered(_one, files, chunksize=8):
            _merge(total, part)
    return total


def report(total: dict) -> str:
    lines = [f"files in image: {total['files']}"]
    if "max_entry_size" in total:
        lines.append(f"largest ARC entry: 0x{total['max_entry_size']:x} bytes")
    for key in ("arc", "arc flags", "tex", "gmd", "mod", "quest", "emd", "monster data", "lmt", "camera",
                "emc", "sbc", "xfs", "lyt", "stage", "sound"):
        if key in total:
            lines.append(f"{key}:")
            lines += [f"  {k}: {v}" for k, v in sorted(total[key].items())]
    return "\n".join(lines)

