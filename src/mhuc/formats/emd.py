"""Check E1 of specs/emd.md: MH4U `.emd` (rEnemyData) and `.etd` (rEnemyTuneData) against the layout taken from
MHGU Definitive Edition's readers. Every function returns counts (a Counter), never bytes from the files.

  check_emd(data)       header offsets, body records (shape, part, hitzone row), visibility rows, and (check
                        E11) the word 35 joint records' kinds and its kind-0 sever records
  check_etd(data)       header offsets, attack volumes, attack records, and (check E13) the part table's kind
  check_pair(emd, etd)  body records' hitzone rows and parts against the .etd's tables; the hitzone row size
"""
from __future__ import annotations

import struct
from collections import Counter

EMD_WORDS = {8: "body", 9: "camera body", 13: "w13", 16: "arena points", 20: "map-hit sphere", 21: "w21",
             22: "w22", 33: "breaks", 34: "visibility", 35: "severs", 38: "w38", 40: "slope fit", 43: "joints"}
ETD_PTRS = range(5, 35)
BODY, VIS, JOINT, HIT, ATTACK = 44, 16, 24, 40, 40
HITZONE_ROWS, HITZONE_ROW = 8, 10
PART, PART_KIND = 10, 8


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


def joint_records(d: bytes) -> list[tuple[int, int, int, int, int, int]] | None:
    """Word 35's records: (joint, kind, index, limit, a, b) each, the joint -1 terminator last; [] when word 35 is 0;
    None if the list doesn't end in the file. A kind of 0 marks a sever/detach record (check E11); the records whose
    kind isn't 0 are MHXX's `dtbparts` joint records, and a (255, 0, 0, -1) record may separate the two."""
    p, out = _w(d, 35), []
    if not p:
        return []
    while p + JOINT <= len(d):
        rec = struct.unpack_from("<iIIIII", d, p)
        out.append(rec)
        p += JOINT
        if rec[0] == -1:
            return out
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
    joint_counts(c, d)
    return c


def joint_counts(c: Counter, d: bytes) -> None:
    """Check E11: word 35's kinds and sever/detach records, into `c`."""
    recs = joint_records(d)
    if recs is None:
        c["E1 emd word 35 list doesn't end"] += 1
        return
    if not recs:
        return
    c["E11 emd files with joint or sever records"] += 1
    sever = [r for r in recs if r[1] == 0 and r[0] not in (255, -1)]
    if any(r[0] == 255 and r[1] == 0 and r[3] == 0xFFFFFFFF for r in recs):
        c["E11 emd files with the (255, 0, 0, -1) marker"] += 1
    if not sever:
        return
    c["E11 emd files with sever records"] += 1
    c["E11 emd sever records"] += len(sever)
    for r in sever:
        c[f"E11 emd sever joint {r[0]}"] += 1
        c[f"E11 emd sever index {r[2]}"] += 1
        c["E11 emd sever limit is the joint" if r[3] == r[0] else "E11 emd sever limit is not the joint"] += 1
        c["E11 emd sever a is 0" if r[4] == 0 else "E11 emd sever a is not 0"] += 1
        c["E11 emd sever b is 0" if r[5] == 0 else "E11 emd sever b is not 0"] += 1


def _block_end(d: bytes, start: int, words: range) -> int:
    """the next header offset after start (the block's end), else the file's end"""
    nxt = [v for v in (_w(d, i) for i in words) if start < v < len(d)]
    return min(nxt) if nxt else len(d)


def attack_records(d: bytes) -> list[bytes] | None:
    """Word 28's 40-byte records, ending at the record whose first u16 is 0xFFFF (and whose other 38 bytes are 0,
    check E10); the terminator isn't returned. Word 29, when set, points one record past the terminator; when it is 0
    the records are still bounded by it, so the unpointed data after it isn't read as records. None if no terminator
    is found (inside word 29 or the next referenced offset)."""
    p = _w(d, 28)
    if not p:
        return []
    end = min(_w(d, 29) or _block_end(d, p, range(29, 35)), len(d))
    out = []
    while p + ATTACK <= end:
        r = d[p:p + ATTACK]
        if struct.unpack_from("<H", r, 0)[0] == 0xFFFF and not any(r[2:]):
            return out
        out.append(r)
        p += ATTACK
    return None


ATTACK_ZERO = ((0x15, 0x18), (0x1E, 0x1F), (0x21, 0x22), (0x23, 0x24), (0x24, 0x28))
ATTACK_VALUES = {0x13: (0, 0x08, 0x40), 0x14: (0, 2, 4), 0x1F: (0, 10), 0x20: (0, 1, 5, 6)}


def check_attack_records(d: bytes) -> Counter:
    """E10 of specs/emd.md: the attack record list's terminator and the bytes MH4U's own reader never reads."""
    c = Counter()
    recs = attack_records(d)
    if recs is None:
        c["E10 etd attack lists with no terminator"] += 1
        return c
    c["E10 etd attack lists"] += 1
    c["E10 etd attack records"] += len(recs)
    if recs and not any(recs[0]):
        c["E10 etd attack record 0 all zero"] += 1
    groups = (_w(d, 28) - _w(d, 27)) // 4 if _w(d, 27) < _w(d, 28) else 0
    for r in recs:
        for lo, hi in ATTACK_ZERO:
            name = f"+{lo:#04x}..+{hi - 1:#04x}" if hi - lo > 1 else f"+{lo:#04x}"
            c[f"E10 etd attack {name} zero" if not any(r[lo:hi]) else
              f"E10 etd attack {name} NOT zero"] += 1
        for off, values in ATTACK_VALUES.items():
            c[f"E10 etd attack +{off:#04x} in {values}" if r[off] in values else
              f"E10 etd attack +{off:#04x} OTHER {r[off]:#04x}"] += 1
        c["E10 etd attack volume group below the word-27 group count" if r[0x19] < groups else
          "E10 etd attack volume group OUTSIDE"] += 1
    return c


def part_kinds(d: bytes) -> list[int] | None:
    """Word 5's eight 10-byte part records' kind (the u16 at +8), in part order; None if word 5 or the 80 bytes it
    points at are outside the file. MH4U's own 0x936904 returns a record's kind, as the byte at +8 (check E13)."""
    p = _w(d, 5)
    if not p or p + 8 * PART > len(d):
        return None
    return [struct.unpack_from("<H", d, p + PART * i + PART_KIND)[0] for i in range(8)]


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
    c.update(check_attack_records(d))
    kinds = part_kinds(d)
    if kinds is None:
        c["E13 etd part table missing or short"] += 1
    else:
        c["E13 etd parts"] += len(kinds)
        for kind in kinds:
            c[f"E13 etd part kind {kind}" if kind in range(5) else "E13 etd part kind above 4"] += 1
            if kind > 0xFF:
                c["E13 etd part kind high byte nonzero"] += 1
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
