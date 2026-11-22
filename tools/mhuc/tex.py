"""MT Framework Mobile textures (rTexture, .tex) on 3DS (specs/tex.md).

Header, four little-endian u32 words (bit fields from mhff n3ds/tex.py):
    word0  "TEX\\0"
    word1  bits 0-11 version (0xA5 MH4U; 0xA6 seen too), 12-23 unknown, 24-27 size shift,
           28-31 kind (2 plain, 6 cube map)
    word2  bits 0-5 mip count, 6-18 width, 19-31 height
    word3  bits 0-7 texture count, 8-15 format, 16-28 unknown (1)
Cube maps have 0x6C more bytes here. Then u32 offsets[mips * textures] from the start of the
pixel data, then the pixel data (mhuc.pica's layouts).
"""
from __future__ import annotations

import struct
from dataclasses import dataclass

from . import pica

MAGIC = 0x00584554
# MT format number -> PICA format. Entries marked "?" in specs/tex.md are mhff's guesses.
FORMATS = {
    1: "RGBA4", 2: "RGBA5551", 3: "RGBA8", 4: "RGB565", 5: "A8", 7: "LA8",
    11: "ETC1", 12: "ETC1A4", 14: "A4", 15: "L4", 16: "L8", 17: "RGB8",
}
FORMAT_IDS = {v: k for k, v in FORMATS.items()}


@dataclass
class Texture:
    width: int
    height: int
    fmt: str                 # PICA format name
    levels: list[bytes]      # mip levels in GPU layout, largest first (first texture only)
    version: int = 0xA5
    unknown1: int = 0
    kind: int = 2
    texture_count: int = 1
    unknown3: int = 1


def read(data: bytes) -> Texture:
    w0, w1, w2, w3 = struct.unpack_from("<4I", data)
    if w0 != MAGIC:
        raise ValueError("not a TEX file (magic)")
    version, unknown1, kind = w1 & 0xFFF, w1 >> 12 & 0xFFF, w1 >> 28 & 0xF
    mips, width, height = w2 & 0x3F, w2 >> 6 & 0x1FFF, w2 >> 19 & 0x1FFF
    count, fmt_id, unknown3 = w3 & 0xFF, w3 >> 8 & 0xFF, w3 >> 16 & 0x1FFF
    if fmt_id not in FORMATS:
        raise ValueError(f"texture format {fmt_id} isn't one mhuc knows")
    if kind == 6:
        raise ValueError("cube maps aren't supported yet (specs/tex.md)")
    pos = 16
    offsets = struct.unpack_from(f"<{mips * count}I", data, pos)
    start = pos + 4 * mips * count
    fmt = FORMATS[fmt_id]
    levels = []
    for m in range(mips):
        w, h = max(8, width >> m), max(8, height >> m)
        o = start + offsets[m]
        levels.append(data[o:o + pica.data_size(fmt, w, h)])
    return Texture(width, height, fmt, levels, version, unknown1, kind, count, unknown3)


def write(t: Texture) -> bytes:
    if t.kind != 2 or t.texture_count != 1:
        raise ValueError("only plain single textures can be written")
    mips = len(t.levels)
    w1 = t.version | t.unknown1 << 12 | t.kind << 28
    w2 = mips | t.width << 6 | t.height << 19
    w3 = t.texture_count | FORMAT_IDS[t.fmt] << 8 | t.unknown3 << 16
    offsets, pos = [], 0
    for lvl in t.levels:
        offsets.append(pos)
        pos += len(lvl)
    return struct.pack("<4I", MAGIC, w1, w2, w3) + struct.pack(f"<{mips}I", *offsets) + b"".join(t.levels)


def to_rgba(t: Texture, level: int = 0, flip_y: bool = False) -> tuple[int, int, bytes]:
    w, h = max(8, t.width >> level), max(8, t.height >> level)
    return w, h, pica.decode(t.fmt, t.levels[level], w, h, flip_y)


def from_rgba(fmt: str, width: int, height: int, rgba: bytes, flip_y: bool = False) -> Texture:
    return Texture(width, height, fmt, [pica.encode(fmt, rgba, width, height, flip_y)])


def write_ppm(path: str, width: int, height: int, rgba: bytes) -> None:
    """A binary PPM (no alpha): viewable anywhere, written with the standard library only."""
    rgb = bytearray()
    for i in range(0, len(rgba), 4):
        rgb += rgba[i:i + 3]
    with open(path, "wb") as f:
        f.write(f"P6\n{width} {height}\n255\n".encode() + bytes(rgb))
