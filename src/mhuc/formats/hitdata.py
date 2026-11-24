"""Monster hurt volumes, attack volumes and attack records of MH3U and MHXX (specs/hitdata.md):

  BDD  rBodyData (0x1AC7B52D)       hurt volumes (`bodydata`, `cambodydata`; MH3U `em_body00`, `em_cambody00`)
  HTS  rHitSize (0x5653C1B0)        attack volumes, in groups
  HDE  rHitDataEnemy (0x70BB64BA)   MHXX attack records
  HTD  rHitData (0x0C6016B9)        MH3U attack records

Each file is a 16-byte header (magic, version, u32 count, u32 0) and records. The loaders copy the file and check the
magic and the version only; the record sizes are the ones that tile every file (check E4).
"""
from __future__ import annotations

import struct

BDD = (b"BDD\0", {0x20110219: 44})                       # same version in both games
HTS = (b"HTS\0", {0x20110212: 40, 0x20131015: 48})       # MH3U, MHXX
HDE = (b"HDE\0", {0x20160121: 32})                       # MHXX
HTD = (b"HTD\0", {0x20110209: 32})                       # MH3U
KINDS = {"bdd": BDD, "hts": HTS, "hde": HDE, "htd": HTD}


class HitDataError(ValueError):
    pass


def _head(d: bytes, kind: str) -> tuple[int, int]:
    magic, sizes = KINDS[kind]
    if len(d) < 16 or d[:4] != magic:
        raise HitDataError(f"not a {kind} file (magic)")
    version, count = struct.unpack_from("<II", d, 4)
    if version not in sizes:
        raise HitDataError(f"{kind} version {version:#x} unknown")
    return sizes[version], count


def records(d: bytes, kind: str) -> list[bytes]:
    """BDD, HDE, HTD: the records. BDD lists end with a record whose first u16 is 0xFFFF, not counted in the header."""
    if kind == "hts":
        raise HitDataError("HTS holds groups: use groups()")
    size, count = _head(d, kind)
    n = count + 1 if kind == "bdd" else count
    if len(d) != 16 + n * size:
        raise HitDataError(f"{kind}: {len(d)} bytes, {count} records of {size} make {16 + n * size}")
    recs = [d[16 + i * size:16 + (i + 1) * size] for i in range(n)]
    if kind == "bdd":
        if struct.unpack_from("<H", recs[-1])[0] != 0xFFFF:
            raise HitDataError("bdd: the last record isn't the 0xFFFF end")
        recs.pop()
    return recs


def groups(d: bytes) -> tuple[int, list[list[bytes]]]:
    """HTS: (record size, groups). The header's count is the number of groups; a table of (u32 records, u32 offset)
    follows. MH3U's counts include each group's closing 0xFFFF record (dropped here), MHXX's don't."""
    size, count = _head(d, "hts")
    out, end = [], 16 + 8 * count
    for i in range(count):
        n, off = struct.unpack_from("<II", d, 16 + 8 * i)
        if off != end or off + n * size > len(d):
            raise HitDataError(f"hts group {i}: {n} records at {off:#x}, expected at {end:#x}")
        recs = [d[off + j * size:off + (j + 1) * size] for j in range(n)]
        if size == HTS[1][0x20110212]:      # MH3U: every non-empty group ends with its 0xFFFF record (check E4)
            if not recs or struct.unpack_from("<H", recs[-1])[0] != 0xFFFF:
                raise HitDataError(f"hts group {i} doesn't end with a 0xFFFF record")
            recs.pop()
        out.append(recs)
        end = off + n * size
    if end != len(d):
        raise HitDataError(f"hts groups end at {end:#x}, file at {len(d):#x}")
    return size, out
