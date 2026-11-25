"""Effect lists: the resources that name the effects a monster can play.

MH4U, MH3U and MHXX all ship them as `rEffectList` (magic `EFL\\0`, extension `efl`) and MHXX also
ships `rProofEffectList` (`PEL\\0`, `pel`); `specs/efl.md` lays them out. The EFL header is
decoded and checked on every monster-archive file; the block it points at is not, so it is carried
as bytes. That is what the cross-game converter rewrites: the header's version word is the one
field that differs by game, and the block moves unchanged.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

EFL_MAGIC = b"EFL\0"
EFL_HEADER = 0x30
EFL_VERSIONS = {0x30111104: "mh4u", 0x30110616: "mh3u", 0x30120306: "mhxx"}
EFL_VERSION = {game: version for version, game in EFL_VERSIONS.items()}
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
    raw: bytes      # the whole file, so the header bytes no field covers survive a round trip

    def to_bytes(self) -> bytes:
        """The file again."""
        return self.raw


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
    return Efl(version, block_size, field_0c, field_10, field_14, data[EFL_HEADER:], data)


def convert(data: bytes, version: int) -> bytes:
    """Re-lay an effect list as `version`: the version word is rewritten, every other byte is
    carried unchanged.

    The block's own layout is unverified, so this is a container conversion only: it is right for
    reading a source game's list as MH4U's class and for the fields the header lays out, and it
    says nothing about whether the source's block means what MH4U's reader would make of it.
    """
    if version not in EFL_VERSIONS:
        raise EflError(f"target version {version:#x} isn't one of the three laid out")
    parsed = read_efl(data)
    if parsed.version == version:
        return data
    return data[:4] + struct.pack("<I", version) + data[8:]


def from_mh3u(data: bytes) -> bytes:
    """An MH3U effect list as MH4U's class reads it (version `0x30110616` -> `0x30111104`)."""
    parsed = read_efl(data)
    if parsed.version != EFL_VERSION["mh3u"]:
        raise EflError(f"not an MH3U effect list (version {parsed.version:#x})")
    return convert(data, EFL_VERSION["mh4u"])


def from_mhxx(data: bytes) -> bytes:
    """An MHXX effect list as MH4U's class reads it (version `0x30120306` -> `0x30111104`)."""
    parsed = read_efl(data)
    if parsed.version != EFL_VERSION["mhxx"]:
        raise EflError(f"not an MHXX effect list (version {parsed.version:#x})")
    return convert(data, EFL_VERSION["mh4u"])


def to_mh3u(data: bytes) -> bytes:
    """An MH4U effect list as MH3U holds it (version `0x30111104` -> `0x30110616`)."""
    parsed = read_efl(data)
    if parsed.version != EFL_VERSION["mh4u"]:
        raise EflError(f"not an MH4U effect list (version {parsed.version:#x})")
    return convert(data, EFL_VERSION["mh3u"])


def to_mhxx(data: bytes) -> bytes:
    """An MH4U effect list as MHXX holds it (version `0x30111104` -> `0x30120306`)."""
    parsed = read_efl(data)
    if parsed.version != EFL_VERSION["mh4u"]:
        raise EflError(f"not an MH4U effect list (version {parsed.version:#x})")
    return convert(data, EFL_VERSION["mhxx"])


@dataclass(frozen=True)
class Pel:
    version: int
    raw: bytes      # the whole file; the body isn't laid out yet

    def to_bytes(self) -> bytes:
        """The file again."""
        return self.raw

    @property
    def body(self) -> bytes:
        return self.raw[8:]


def read_pel(data: bytes) -> Pel:
    if len(data) < 8 or data[:4] != PEL_MAGIC:
        raise EflError("not a PEL file (magic)")
    version = struct.unpack_from("<I", data, 4)[0]
    if version != PEL_VERSION:
        raise EflError(f"PEL version {version} isn't the one every file carries (specs/efl.md: {PEL_VERSION})")
    return Pel(version, data)
