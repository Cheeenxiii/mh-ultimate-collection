"""`mhuc survey`: run the with-game-files checks of specs/ over a RomFS image and print counts.

It reads the image in place (mhuc.romfs) and every ARC inside it, and reports only counts,
versions and pass/fail tallies: nothing from the files themselves, so its output can go into
a spec or a report (CLAUDE.md, rule 1). Checks covered: C2, C3 (arc), T1, T3 (tex),
G1, G2 (gmd), M1 (mod), Q1, Q2 (quest).

Memory: each worker holds one archive and its decompressed entries at a time; keep the
worker count low on machines with little RAM (default 4).
"""
from __future__ import annotations

import struct
from collections import Counter
from multiprocessing import Pool

from . import arc, classid, gmd, pica, romfs, tex

QUEST_TYPES = ("rQuestData", "rSetEmMain", "rEmSetList", "rRem")
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


def survey_entry(type_name: str | None, data: bytes, st: dict) -> None:
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
    elif type_name == "rModel" or data[:4] == b"MOD\0":
        c = st.setdefault("mod", Counter())
        if data[:4] != b"MOD\0":
            c[f"other magic {data[:4]!r}"] += 1
            return
        c[f"version 0x{struct.unpack_from('<H', data, 4)[0]:04x}"] += 1


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
        survey_entry(name, e.data, st)
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
    for key in ("arc", "arc flags", "tex", "gmd", "mod", "quest"):
        if key in total:
            lines.append(f"{key}:")
            lines += [f"  {k}: {v}" for k, v in sorted(total[key].items())]
    return "\n".join(lines)

