"""Check E1 of specs/emd.md: MH4U `.emd` (rEnemyData) and `.etd` (rEnemyTuneData) against the layout taken from
MHGU Definitive Edition's readers. Every function returns counts (a Counter), never bytes from the files.

  check_emd(data)       header offsets, body records (shape, part, hitzone row), visibility rows
  check_etd(data)       header offsets, attack volumes, attack records
  check_pair(emd, etd)  body records' hitzone rows and parts against the .etd's tables; the hitzone row size
"""
from __future__ import annotations

import struct
from collections import Counter

EMD_WORDS = {8: "body", 9: "camera body", 13: "w13", 16: "arena points", 20: "map-hit sphere", 21: "w21",
             22: "w22", 33: "breaks", 34: "visibility", 35: "severs", 38: "w38", 40: "slope fit", 43: "joints"}
ETD_PTRS = range(5, 35)
BODY, VIS, HIT, ATTACK = 44, 16, 40, 40
HITZONE_ROWS, HITZONE_ROW = 8, 10


def _w(d: bytes, i: int) -> int:
    return struct.unpack_from("<I", d, 4 * i)[0] if 4 * i + 4 <= len(d) else 0


def body_records(d: bytes, word: int) -> list[tuple[int, int, int, int, int]] | None:
    """(bone A, bone B, shape, hitzone row, part) per record, or None if the list doesn't end in the file."""
    p, out = _w(d, word), []
    if not p:
        return []
    while p + BODY <= len(d):
        a, b, shape, row, part = struct.unpack_from("<5H", d, p)
        if a == 0xFFFF:
            return out
        out.append((a, b, shape, row, part))
        p += BODY
    return None


def vis_rows(d: bytes) -> list[tuple[int, int, int, int, int]] | None:
    p, out = _w(d, 34), []
    if not p:
        return []
    while p + VIS <= len(d):
        g, cond, mode, param, thr = struct.unpack_from("<iHHII", d, p)
        if g == -1:
            return out
        out.append((g, cond, mode, param, thr))
        p += VIS
    return None


def check_emd(d: bytes) -> Counter:
    c = Counter()
    c["E1 emd magic emd\\0" if d[:4] == b"emd\0" else f"E1 emd magic other {d[:4]!r}"] += 1
    for word, name in EMD_WORDS.items():
        v = _w(d, word)
        c[f"E1 emd word {word} ({name}) " + ("0" if not v else "inside" if v < len(d) else "OUTSIDE")] += 1
    for word in (8, 9):
        recs = body_records(d, word)
        if recs is None:
            c[f"E1 emd word {word} list doesn't end"] += 1
            continue
        c[f"E1 emd word {word} records"] += len(recs)
        for _, _, shape, _, part in recs:
            c[f"E1 emd body shape {shape}" if shape <= 2 else "E1 emd body shape OTHER"] += 1
            c["E1 emd body part < 8" if part < 8 else "E1 emd body part >= 8"] += 1
    rows = vis_rows(d)
    if rows is None:
        c["E1 emd visibility rows don't end"] += 1
    else:
        c["E1 emd visibility rows"] += len(rows)
        for _, cond, mode, _, _ in rows:
            c[f"E1 emd visibility condition {cond}"] += 1
            c[f"E1 emd visibility mode {mode}" if mode <= 1 else "E1 emd visibility mode OTHER"] += 1
    return c


def _block_end(d: bytes, start: int, words: range) -> int:
    """the next header offset after start (the block's end), else the file's end"""
    nxt = [v for v in (_w(d, i) for i in words) if start < v < len(d)]
    return min(nxt) if nxt else len(d)


def check_etd(d: bytes) -> Counter:
    c = Counter()
    c["E1 etd magic etd\\0" if d[:4] == b"etd\0" else f"E1 etd magic other {d[:4]!r}"] += 1
    for i in ETD_PTRS:
        v = _w(d, i)
        c["E1 etd words 5-34: 0" if not v else "E1 etd words 5-34: inside" if v < len(d) else
          "E1 etd words 5-34: OUTSIDE"] += 1
    hp = _w(d, 4)
    c["E1 etd base HP 1..100000" if 0 < hp <= 100000 else "E1 etd base HP out of range"] += 1
    a, b = _w(d, 27), _w(d, 28)
    if a and b and a < b <= len(d) and (b - a) % 4 == 0:
        groups = 0
        for i in range((b - a) // 4):
            p = struct.unpack_from("<I", d, a + 4 * i)[0]
            if not p:
                continue
            groups += 1
            while p + HIT <= len(d) and struct.unpack_from("<H", d, p)[0] != 0xFFFF:
                c["E1 etd attack volumes"] += 1
                p += HIT
            if p + HIT > len(d):
                c["E1 etd attack volume group doesn't end"] += 1
        c["E1 etd attack volume groups"] += groups
    elif a or b:
        c["E1 etd word 27/28 not a group table"] += 1
    if b:
        end = _w(d, 29) or _block_end(d, b, range(29, 35))
        if (end - b) % ATTACK == 0:
            c["E1 etd attack records whole"] += 1
        elif not _w(d, 29) and end == len(d):
            c["E1 etd attack records run to an unpointed tail"] += 1  # word 29 is 0 and no block follows
        else:
            c["E1 etd attack records NOT whole"] += 1
        c["E1 etd attack records"] += (end - b) // ATTACK
    return c


def check_pair(emd: bytes, etd: bytes) -> Counter:
    """Body records against the .etd: parts within the part table (8 parts), the hitzone table's size (8 rows of 10
    bytes: check E1) and the body records' rows within it."""
    c = Counter()
    recs = (body_records(emd, 8) or []) + (body_records(emd, 9) or [])
    if not recs:
        c["E1 pair no body records"] += 1
        return c
    c["E1 pair parts within 8" if max(r[4] for r in recs) < 8 else "E1 pair part >= 8"] += 1
    start = _w(etd, 7)
    if not start or start >= len(etd):
        c["E1 pair no hitzone table"] += 1
        return c
    size = _block_end(etd, start, ETD_PTRS) - start
    c["E1 pair hitzone table 8 x 10 bytes" if size == HITZONE_ROWS * HITZONE_ROW else
      f"E1 pair hitzone table {size} bytes"] += 1
    c["E1 pair hitzone rows within 8" if max(r[3] for r in recs) < HITZONE_ROWS else "E1 pair hitzone row >= 8"] += 1
    return c
