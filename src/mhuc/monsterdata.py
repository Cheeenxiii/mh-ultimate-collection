"""Rebuild the parts of an MH4U monster's `.etd`/`.emd` (specs/emd.md) that a source game's own files also hold, and
compare them with MH4U's. MHXX: specs/dttune.md, specs/dtbase.md, specs/dtbparts.md and specs/hitdata.md; MH3U:
specs/emstatus.md and specs/hitdata.md.

`from_mhxx` / `from_mh3u` return {field: value in MH4U's layout}; `from_mh4u` reads the same fields from MH4U's pair;
`compare` gives, per field, whether it is equal, and for record lists how many records are. Nothing returned or printed
holds a value from the files.
"""
from __future__ import annotations

import struct

from .formats import dtbase, dtbparts, dttune, emstatus, hitdata

ETD_PTRS = range(5, 35)
AILMENT_WORDS = range(17, 25)


def _w(d: bytes, i: int) -> int:
    return struct.unpack_from("<I", d, 4 * i)[0]


def _etd_block(etd: bytes, word: int) -> bytes | None:
    p = _w(etd, word)
    if not p or p >= len(etd):
        return None
    nxt = [v for v in (_w(etd, i) for i in ETD_PTRS) if p < v < len(etd)]
    return etd[p:min(nxt) if nxt else len(etd)]


def _emd_block(emd: bytes, word: int) -> bytes | None:
    """The bytes at `.emd` header word `word`, up to the next offset word that points inside the file."""
    p = _w(emd, word)
    if not p or p >= len(emd):
        return None
    nxt = [v for v in (_w(emd, i) for i in range(2, 48)) if p < v < len(emd)]
    return emd[p:min(nxt) if nxt else len(emd)]


def _terminated(d: bytes, p: int, size: int, end: bytes) -> list[bytes]:
    out = []
    while p + size <= len(d) and d[p:p + len(end)] != end:
        out.append(d[p:p + size])
        p += size
    return out


def from_mh4u(emd: bytes, etd: bytes) -> dict[str, object]:
    out: dict[str, object] = {"base HP": _w(etd, 4)}
    for word, name in ((5, "part table"), (7, "hitzone table")):
        b = _etd_block(etd, word)
        out[name] = b[:80] if b else None
    out["part HP"] = [struct.unpack_from("<H", out["part table"], 10 * i)[0] for i in range(8)]
    out["sensor records"] = _terminated(etd, _w(etd, 9), 28, b"\xff\xff\0\0") if _w(etd, 9) else []
    rows = _terminated(etd, _w(etd, 10), 16, struct.pack("<f", -1.0) * 4) if _w(etd, 10) else []
    out["distance ranges"] = rows
    offs = _etd_block(etd, 11)
    out["range offsets"] = [offs[12 * i:12 * i + 12] for i in range(len(rows))] if offs else [bytes(12)] * len(rows)
    rage = _etd_block(etd, 14)
    out["rage"] = rage[:56] if rage else None
    for word in AILMENT_WORDS:
        b = _etd_block(etd, word)
        out[f"etd word {word}"] = b[:16 if word == 17 else 12] if b else None
    w25 = _etd_block(etd, 25)
    out["etd word 25"] = w25[:14] if w25 else None
    p2 = _etd_block(etd, 29)
    out["part table 2"] = [p2[24 * i:24 * i + 24] for i in range(len(p2) // 24)] if p2 else []
    out["scalars"] = [_w(etd, i) for i in range(35, 40)]
    for word, name in ((8, "body records"), (9, "camera body records")):
        out[name] = _terminated(emd, _w(emd, word), 44, b"\xff\xff") if _w(emd, word) else []
    out["dtbase scalars"] = (emd[0x0C:0x10] + emd[0x10:0x14] + emd[0x30:0x34] + emd[0x6C:0x70] + emd[0x70:0x74]
                             + emd[0x14:0x18] + emd[0x78:0x7C] + emd[0x7C:0x80])
    recs44 = []
    b = _emd_block(emd, 44)
    if b:
        for i in range(0, len(b) - 31, 32):
            r = b[i:i + 32]
            if r[0] == 0xFF:
                break
            recs44.append(r)
    out["emd word 44 block"] = recs44
    sphere = _emd_block(emd, 20)
    out["map-hit sphere"] = sphere[:52] if sphere else None
    points = _emd_block(emd, 43)
    out["joint points"] = points[:56] if points else None
    recs = []
    b = _emd_block(emd, 35)
    if b:
        for i in range(0, len(b) - 23, 24):
            r = struct.unpack_from("<6I", b, i)
            if r[0] == 0xFFFFFFFF:
                break
            recs.append(r)
    out["joint records"] = [(j, k, i, n) for j, k, i, n, _, _ in recs if k != 0]
    severed, after_marker = [], False
    for j, k, i, n, _a, _b in recs:
        if (j, k, i, n) == (255, 0, 0, 0xFFFFFFFF):
            after_marker = True
        elif after_marker:
            severed.append((j, k, i, n))
    out["sever records"] = severed
    parts32 = []
    b = _emd_block(emd, 32)
    if b:
        for i in range(0, len(b) - 31, 32):
            r = b[i:i + 32]
            if r[0] == 0xFF:
                break
            parts32.append((r[0], r[1]))
    out["break parts"] = sorted({p for p, count in parts32 if count != 0xFF})
    groups = []
    b = _emd_block(emd, 33)
    if b:
        for i in range(0, len(b) - 7, 8):
            g, param = struct.unpack_from("<iI", b, i)
            if g == -1:
                break
            groups.append((g, param))
    out["break groups"] = groups
    a, b = _w(etd, 27), _w(etd, 28)
    groups = []
    for i in range((b - a) // 4 if a and b else 0):
        p = _w(etd[a:], i)
        groups.append(_terminated(etd, p, 40, b"\xff\xff") if p else [])
    out["attack volumes"] = groups
    end = _w(etd, 29) or min([v for v in (_w(etd, i) for i in range(29, 35)) if b < v < len(etd)] + [len(etd)])
    out["attack records"] = [etd[p:p + 40] for p in range(b, end - 39, 40)] if b else []
    return out


def _hde_to_4u(r: bytes) -> bytes:
    """MHXX's 32-byte attack record in MH4U's 40-byte layout: bytes 0..27 as they are, byte 18 rejoined from its two
    MHXX halves (bits 0-1 at 18, the rest at 31), byte 29 kept, the rest zero (specs/hitdata.md, HDE)."""
    if not any(r[:28]) and r[28] == 0xFE:          # the empty record
        return bytes(40)
    out = bytearray(40)
    out[:28] = r[:28]
    out[18] = (r[18] & 3) | (r[31] << 2)
    out[29] = r[29]
    return bytes(out)


def _htd_to_4u(r: bytes) -> bytes:
    """MH3U's 32-byte attack record in MH4U's 40-byte layout, for the fields the two share (specs/hitdata.md, HTD):
    bytes 0x00-0x11, the attack-volume group (0x15 -> 0x19), the count at 0x16 (one more -> 0x1a), and the signed byte
    (0x18 -> 0x1d). MH3U's other tail bytes have no MH4U counterpart and stay zero."""
    out = bytearray(40)
    out[:0x12] = r[:0x12]
    out[0x19] = r[0x15]
    out[0x1A] = r[0x16] + 1 if r[0x16] else 0
    out[0x1D] = r[0x18]
    return bytes(out)


HTD_CARRIED = {"label": "bytes 0x00-0x11, 0x19-0x1a and 0x1d",
               "ranges": ((0x00, 0x12), (0x19, 0x1B), (0x1D, 0x1E))}
HDE_CARRIED = {"label": "bytes 0-27 and 29", "ranges": ((0, 28), (29, 30))}


def from_mhxx(tune: bytes, base: bytes, parts: bytes, body: bytes, cambody: bytes, hitsize: bytes,
              attack: bytes) -> dict[str, object]:
    blk = {n: tune[o:o + s] for n, o, s in dttune.blocks(tune)}
    out: dict[str, object] = {"base HP": struct.unpack("<I", blk["base HP"])[0],
                              "part table": blk["part table"], "hitzone table": blk["hitzone table"]}
    out["part HP"] = [struct.unpack_from("<H", out["part table"], 10 * i)[0] for i in range(8)]
    sens = blk.get("sensor records", b"")
    out["sensor records"] = [sens[i:i + 4] + sens[i + 8:i + 32] for i in range(0, len(sens), 32)]
    rng = blk.get("distance ranges", b"")
    out["distance ranges"] = [rng[i:i + 16] for i in range(0, len(rng), 16)]
    offs = blk.get("range offsets", b"")
    out["range offsets"] = [offs[i:i + 12] for i in range(0, len(offs), 12)]
    out["rage"] = blk["rage"][:56] if "rage" in blk else None
    for k, word in enumerate(AILMENT_WORDS):
        b = blk.get(f"ailment {0x94 + 4 * k:#x}")
        out[f"etd word {word}"] = b
    out["etd word 25"] = blk.get("block 0xb4")
    p2 = blk.get("part table 2", b"")
    out["part table 2"] = [p2[i:i + 24] for i in range(0, len(p2), 24)]
    out["scalars"] = [struct.unpack("<I", blk[f"scalar {k}"])[0] for k in range(5)]
    for name, src in (("body records", body), ("camera body records", cambody)):
        recs = []
        for r in hitdata.records(src, "bdd"):
            if struct.unpack_from("<H", r, 4)[0] != 2 and r[2:4] == b"\xff\xff":
                r = r[:2] + b"\0\0" + r[4:]        # MHXX marks an unused bone B 0xFFFF, MH4U 0
            recs.append(r)
        out[name] = recs
    size, groups = hitdata.groups(hitsize)
    out["attack volumes"] = [[r[:28] + r[32:44] for r in g] for g in groups]
    out["attack records"] = [_hde_to_4u(r) for r in hitdata.records(attack, "hde")]
    out["dtbase scalars"] = (dtbase.block(base, "scalar 0x60") + dtbase.block(base, "bytes 0x64")
                             + dtbase.block(base, "scalar 0x68") + dtbase.block(base, "block 0x94"))
    w44 = dtbase.block(base, "block 0xac")
    out["emd word 44 block"] = [w44[i:i + 32] for i in range(0, len(w44), 32)] if w44 else []
    spheres = dtbase.records(base, "map-hit sphere records", 0x34)
    out["map-hit sphere"] = spheres[0] if spheres else None
    points = dtbase.block(base, "block 0xa8")
    out["joint points"] = points[:56] if points else None
    out["joint records"] = [struct.unpack("<IBII", r) for r in dtbparts.records(parts, "joint records", 13)]
    out["sever records"] = None                      # no block in dtbase or dtbparts holds them
    out["break parts"] = sorted({r[0] for r in dtbparts.records(parts, "break records", 4)
                                 if r[1] != 0xFF and r[0] != 0xFF})
    out["break groups"] = None
    out["_attack record carried"] = HDE_CARRIED
    return out


def from_mh3u(status: bytes, body: bytes, cambody: bytes, hitsize: bytes, attack: bytes) -> dict[str, object]:
    blk = {n: status[o:o + s] for n, o, s in emstatus.blocks(status)}
    out: dict[str, object] = {"base HP": struct.unpack_from("<I", blk["header"])[0],
                              "hitzone table": blk["hitzone table"]}
    if "part table" in blk:
        out["part HP"] = list(struct.unpack("<8H", blk["part table"]))
    out["distance ranges"] = [blk["block 0x100"]]
    for name, word, n in (("ailment 0xa4", 17, 16), ("ailment 0xa8", 18, 12), ("ailment 0xac", 19, 12),
                          ("ailment 0xb0", 20, 12), ("ailment 0xb4", 21, 12), ("ailment 0xb8", 24, 8)):
        if name in blk:
            out[f"etd word {word}"] = blk[name][:n]
    out["body records"] = hitdata.records(body, "bdd")
    out["camera body records"] = hitdata.records(cambody, "bdd")
    out["attack volumes"] = [[r[:8] + bytes(4) + r[12:] for r in g] for g in hitdata.groups(hitsize)[1]]
    out["attack records"] = [_htd_to_4u(r) for r in hitdata.records(attack, "htd")]
    out["_attack record carried"] = HTD_CARRIED
    return out


def _mask_volume(r: bytes) -> bytes:
    """MH3U's attack volumes carry bytes 8..11 that MH4U's records zero: compare without them"""
    return r[:8] + bytes(4) + r[12:]


def compare(src: dict[str, object], mh4u: dict[str, object]) -> list[tuple[str, str]]:
    """(field, verdict) for every field the source rebuilt. Verdicts count records, never show them."""
    out = []
    for name, value in src.items():
        if name.startswith("_"):
            continue
        ref = mh4u.get(name)
        if name in ("etd word 24",) and value is not None and ref is not None:
            ref = ref[:len(value)]                  # MH3U's last ailment block is MH4U's first 8 bytes
        if name == "etd word 25" and value is not None and ref is not None:
            value = value[:len(ref)]
        if name == "attack volumes":
            got = [x for g in value for x in g]
            want = [x for g in ref for x in g][:len(got)] if len(value) < len(ref) else [x for g in ref for x in g]
            if any(len(g) for g in value) and len(value) < len(ref):
                verdict = f"{len(value)} of {len(ref)} groups;"
            else:
                verdict = f"{len(value)} groups (MH4U {len(ref)});"
            mask = _mask_volume if any(len(r) == 40 and r[8:12] != bytes(4) for r in got) else (lambda r: r)
            eq = sum(mask(a) == mask(b) for a, b in zip(got, want, strict=False))
            out.append((name, f"{verdict} {eq} of {len(want)} records equal"))
        elif isinstance(value, list) and name == "break parts":
            ref = set(ref or [])
            common = sorted(set(value) & ref)
            out.append((name, "equal" if set(value) == ref else f"{len(common)} of {len(ref)} parts equal"))
        elif isinstance(value, list) and (not value or isinstance(value[0], tuple)):
            ref = ref or []
            equal = sum(a == b for a, b in zip(value, ref, strict=False))
            verdict = "equal (none on either side)" if not value and not ref else f"{equal} of {len(ref)} records equal"
            if len(value) != len(ref):
                verdict += f" (source has {len(value)})"
            out.append((name, verdict))
        elif isinstance(value, list) and value and isinstance(value[0], (bytes, bytearray)):
            eq = sum(a == b for a, b in zip(value, ref or [], strict=False))
            verdict = f"{eq} of {len(ref or [])} records equal"
            carried = src.get("_attack record carried") if name == "attack records" else None
            if carried:                              # the source's record carries a part of MH4U's 40 bytes
                same = sum(b"".join(a[x:y] for x, y in carried["ranges"])
                           == b"".join(b[x:y] for x, y in carried["ranges"])
                           for a, b in zip(value, ref or [], strict=False))
                verdict += f", {same} on {carried['label']}"
            out.append((name, verdict + ("" if len(value) == len(ref or []) else f" (source has {len(value)})")))
        elif isinstance(value, list):
            eq = sum(a == b for a, b in zip(value, ref or [], strict=False))
            out.append((name, f"{eq} of {len(ref or [])} equal"))
        elif value is None or ref is None:
            out.append((name, "absent in the source" if value is None else "absent in MH4U"))
        elif isinstance(value, (bytes, bytearray)) and len(value) == len(ref) and len(value) % 10 == 0 \
                and name == "hitzone table":
            rows = sum(value[i:i + 10] == ref[i:i + 10] for i in range(0, len(value), 10))
            out.append((name, "equal" if value == ref else f"{rows} of {len(value) // 10} rows equal"))
        elif isinstance(value, (bytes, bytearray)) and isinstance(ref, (bytes, bytearray)) and len(value) == len(ref):
            equal = sum(a == b for a, b in zip(value, ref, strict=False))
            out.append((name, "equal" if equal == len(value) else f"{equal} of {len(value)} bytes equal"))
        else:
            out.append((name, "equal" if value == ref else "differs"))
    return out
