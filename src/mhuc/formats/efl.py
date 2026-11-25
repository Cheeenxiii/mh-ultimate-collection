"""Effect lists: the resources that name the effects a monster can play.

MH4U, MH3U and MHXX all ship them as `rEffectList` (magic `EFL\\0`, extension `efl`) and MHXX also
ships `rProofEffectList` (`PEL\\0`, `pel`); `specs/efl.md` lays them out. The EFL header is
decoded and checked on every monster-archive file; the block it points at and the PEL body are
not, so they are handed back as bytes.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

EFL_MAGIC = b"EFL\0"
EFL_HEADER = 0x30
EFL_VERSIONS = {0x30111104: "MH4U", 0x30110616: "MH3U", 0x30120306: "MHXX"}
PEL_MAGIC = b"PEL\0"
PEL_VERSION = 15


class EflError(ValueError):
    pass


@dataclass(frozen=True)
class Efl:
    version: int
    block_size: int
    field_0c: float
    field_10: tuple[int, int]
    field_14: int
    block: bytes


def read_efl(data: bytes) -> Efl:
    if len(data) < EFL_HEADER or data[:4] != EFL_MAGIC:
        raise EflError("not an EFL file (magic)")
    version, block_size, field_0c = struct.unpack_from("<IIf", data, 4)
    if version not in EFL_VERSIONS:
        raise EflError(f"EFL version {version:#x} isn't one of the three laid out (specs/efl.md)")
    if len(data) != EFL_HEADER + block_size:
        raise EflError(f"{len(data)} bytes for a {EFL_HEADER:#x}-byte header and a {block_size:#x}-byte block")
    field_10 = struct.unpack_from("<HH", data, 0x10)
    field_14 = struct.unpack_from("<I", data, 0x14)[0]
    return Efl(version, block_size, field_0c, field_10, field_14, data[EFL_HEADER:])


@dataclass(frozen=True)
class Pel:
    version: int
    body: bytes   # everything after the 8-byte magic and version; the body isn't laid out yet


def read_pel(data: bytes) -> Pel:
    if len(data) < 8 or data[:4] != PEL_MAGIC:
        raise EflError("not a PEL file (magic)")
    version = struct.unpack_from("<I", data, 4)[0]
    if version != PEL_VERSION:
        raise EflError(f"PEL version {version} isn't the one every file carries (specs/efl.md: {PEL_VERSION})")
    return Pel(version, data[8:])
