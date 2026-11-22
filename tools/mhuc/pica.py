"""3DS (PICA200) texture codecs: every format the GPU samples, tiled as it stores them.

Pixels go in and out as RGBA8 bytes, rows top to bottom (len = width * height * 4). Encoded
data is the GPU's layout: 8x8 tiles in row-major order, the pixels of a tile in Morton
(Z) order, each pixel little endian. ETC1 tiles hold four 4x4 blocks (top left, top right,
bottom left, bottom right); ETC1A4 puts each block's 64-bit alpha before its colour block.
Sources: 3dbrew "GPU/Textures", mhff n3ds/tex.py, Khronos ETC1 specification. Width and
height must be multiples of 8.

`flip_y`: the GPU's texture origin is the bottom-left corner. Whether MT Framework's .tex files
store rows bottom-up is unverified (specs/tex.md), so callers choose.
"""
from __future__ import annotations

import struct

# bits per pixel
FORMATS = {
    "RGBA8": 32, "RGB8": 24, "RGBA5551": 16, "RGB565": 16, "RGBA4": 16, "LA8": 16, "HILO8": 16,
    "L8": 8, "A8": 8, "LA4": 8, "L4": 4, "A4": 4, "ETC1": 4, "ETC1A4": 8,
}

ETC1_MODIFIERS = (
    (2, 8), (5, 17), (9, 29), (13, 42), (18, 60), (24, 80), (33, 106), (47, 183),
)


def data_size(fmt: str, width: int, height: int) -> int:
    return width * height * FORMATS[fmt] // 8


def _check(width: int, height: int) -> None:
    if width <= 0 or height <= 0 or width % 8 or height % 8:
        raise ValueError(f"{width}x{height}: 3DS textures are multiples of 8 in both directions")


def _morton(i: int) -> tuple[int, int]:
    """Position (x, y) in an 8x8 tile of the i-th pixel stored."""
    x = (i & 1) | ((i >> 1) & 2) | ((i >> 2) & 4)
    y = ((i >> 1) & 1) | ((i >> 2) & 2) | ((i >> 3) & 4)
    return x, y


_ORDER = [_morton(i) for i in range(64)]


def _tiled_positions(width: int, height: int):
    """(x, y) of each stored pixel, in storage order."""
    for ty in range(0, height, 8):
        for tx in range(0, width, 8):
            for x, y in _ORDER:
                yield tx + x, ty + y


def _scale(v: int, bits: int) -> int:
    return (v * 255 + ((1 << bits) - 1) // 2) // ((1 << bits) - 1)


def _q(v: int, bits: int) -> int:
    return (v * ((1 << bits) - 1) + 127) // 255


def _unpack_pixel(fmt: str, data: bytes, i: int) -> tuple[int, int, int, int]:
    if fmt == "RGBA8":
        a, b, g, r = data[4 * i:4 * i + 4]
        return r, g, b, a
    if fmt == "RGB8":
        b, g, r = data[3 * i:3 * i + 3]
        return r, g, b, 255
    if fmt in ("RGBA5551", "RGB565", "RGBA4", "LA8", "HILO8"):
        v = data[2 * i] | data[2 * i + 1] << 8
        if fmt == "RGBA5551":
            return _scale(v >> 11, 5), _scale(v >> 6 & 31, 5), _scale(v >> 1 & 31, 5), 255 * (v & 1)
        if fmt == "RGB565":
            return _scale(v >> 11, 5), _scale(v >> 5 & 63, 6), _scale(v & 31, 5), 255
        if fmt == "RGBA4":
            return _scale(v >> 12, 4), _scale(v >> 8 & 15, 4), _scale(v >> 4 & 15, 4), _scale(v & 15, 4)
        if fmt == "LA8":
            lum = v >> 8
            return lum, lum, lum, v & 0xFF
        return v >> 8, v & 0xFF, 0, 255   # HILO8: red = high byte, green = low byte
    if fmt in ("L8", "A8", "LA4"):
        v = data[i]
        if fmt == "L8":
            return v, v, v, 255
        if fmt == "A8":
            return 255, 255, 255, v
        lum = _scale(v >> 4, 4)
        return lum, lum, lum, _scale(v & 15, 4)
    # 4-bit: the low nibble is the first pixel
    v = data[i >> 1] >> (4 * (i & 1)) & 15
    if fmt == "L4":
        lum = _scale(v, 4)
        return lum, lum, lum, 255
    return 255, 255, 255, _scale(v, 4)   # A4


def _pack_pixels(fmt: str, pixels: list[tuple[int, int, int, int]]) -> bytes:
    out = bytearray()
    if fmt in ("L4", "A4"):
        vals = [_q((p[0] * 77 + p[1] * 150 + p[2] * 29) >> 8 if fmt == "L4" else p[3], 4) for p in pixels]
        for i in range(0, len(vals), 2):
            out.append(vals[i] | vals[i + 1] << 4)
        return bytes(out)
    for r, g, b, a in pixels:
        lum = (r * 77 + g * 150 + b * 29) >> 8
        if fmt == "RGBA8":
            out += bytes((a, b, g, r))
        elif fmt == "RGB8":
            out += bytes((b, g, r))
        elif fmt == "RGBA5551":
            out += struct.pack("<H", _q(r, 5) << 11 | _q(g, 5) << 6 | _q(b, 5) << 1 | (a >= 128))
        elif fmt == "RGB565":
            out += struct.pack("<H", _q(r, 5) << 11 | _q(g, 6) << 5 | _q(b, 5))
        elif fmt == "RGBA4":
            out += struct.pack("<H", _q(r, 4) << 12 | _q(g, 4) << 8 | _q(b, 4) << 4 | _q(a, 4))
        elif fmt == "LA8":
            out += bytes((a, lum))
        elif fmt == "HILO8":
            out += bytes((g, r))
        elif fmt == "L8":
            out.append(lum)
        elif fmt == "A8":
            out.append(a)
        elif fmt == "LA4":
            out.append(_q(lum, 4) << 4 | _q(a, 4))
        else:
            raise ValueError(fmt)
    return bytes(out)


# ── ETC1 ────────────────────────────────────────────────────────────────────

def _etc1_decode_block(word: int) -> list[tuple[int, int, int]]:
    """The 16 colours of a block, indexed x * 4 + y (the specification's pixel order)."""
    info, idx = word >> 32, word & 0xFFFFFFFF
    if info & 2:   # differential
        base = [info >> 27 & 31, info >> 19 & 31, info >> 11 & 31]
        delta = [info >> 24 & 7, info >> 16 & 7, info >> 8 & 7]
        second = [b + (d - 8 if d > 3 else d) for b, d in zip(base, delta, strict=True)]
        c1 = [(v << 3) | (v >> 2) for v in base]
        c2 = [(v << 3) | (v >> 2) for v in second]
    else:
        c1 = [(info >> s & 15) * 17 for s in (28, 20, 12)]
        c2 = [(info >> s & 15) * 17 for s in (24, 16, 8)]
    flip = info & 1
    tables = (ETC1_MODIFIERS[info >> 5 & 7], ETC1_MODIFIERS[info >> 2 & 7])
    out = []
    for i in range(16):
        x, y = i >> 2, i & 3
        second_half = (y >= 2) if flip else (x >= 2)
        base = c2 if second_half else c1
        a, b = tables[second_half]
        sel = (idx >> i & 1) | (idx >> (i + 15) & 2)
        m = (a, b, -a, -b)[sel]
        out.append(tuple(max(0, min(255, c + m)) for c in base))
    return out


def _etc1_encode_block(colours: list[tuple[int, int, int]]) -> int:
    """An individual-mode ETC1 block for 16 colours (x * 4 + y order): plain, not optimal."""
    best = None
    for flip in (0, 1):
        halves = ([i for i in range(16) if ((i & 3) < 2 if flip else (i >> 2) < 2)],
                  [i for i in range(16) if not ((i & 3) < 2 if flip else (i >> 2) < 2)])
        info, idx, err = flip, 0, 0
        for h, members in enumerate(halves):
            avg = [sum(colours[i][c] for i in members) // 8 for c in range(3)]
            base4 = [_q(v, 4) for v in avg]
            base = [v * 17 for v in base4]
            h_best = None
            for t, (a, b) in enumerate(ETC1_MODIFIERS):
                mods = (a, b, -a, -b)
                sels, e = [], 0
                for i in members:
                    choices = []
                    for s, m in enumerate(mods):
                        rec = [max(0, min(255, base[c] + m)) for c in range(3)]
                        choices.append((sum((rec[c] - colours[i][c]) ** 2 for c in range(3)), s))
                    ce, s = min(choices)
                    e += ce
                    sels.append((i, s))
                if h_best is None or e < h_best[0]:
                    h_best = (e, t, sels)
            e, t, sels = h_best
            err += e
            shifts = (28, 20, 12) if h == 0 else (24, 16, 8)
            for c in range(3):
                info |= base4[c] << shifts[c]
            info |= t << (5 if h == 0 else 2)
            for i, s in sels:
                idx |= (s & 1) << i | (s >> 1) << (i + 16)
        if best is None or err < best[0]:
            best = (err, info << 32 | idx)
    return best[1]


_ETC_BLOCKS = ((0, 0), (4, 0), (0, 4), (4, 4))


def _etc_blocks(width: int, height: int):
    for ty in range(0, height, 8):
        for tx in range(0, width, 8):
            for bx, by in _ETC_BLOCKS:
                yield tx + bx, ty + by


# ── public ──────────────────────────────────────────────────────────────────

def decode(fmt: str, data: bytes, width: int, height: int, flip_y: bool = False) -> bytes:
    """GPU-layout data to RGBA8 pixels, rows top to bottom."""
    _check(width, height)
    if len(data) < data_size(fmt, width, height):
        raise ValueError(f"{fmt} {width}x{height} needs {data_size(fmt, width, height)} bytes, got {len(data)}")
    out = bytearray(width * height * 4)

    def put(x, y, px):
        row = height - 1 - y if flip_y else y
        o = (row * width + x) * 4
        out[o:o + 4] = bytes(px)

    if fmt in ("ETC1", "ETC1A4"):
        step = 16 if fmt == "ETC1A4" else 8
        for n, (bx, by) in enumerate(_etc_blocks(width, height)):
            o = n * step
            alpha = struct.unpack_from("<Q", data, o)[0] if step == 16 else None
            colours = _etc1_decode_block(struct.unpack_from("<Q", data, o + step - 8)[0])
            for i, c in enumerate(colours):
                a = 255 if alpha is None else (alpha >> (4 * i) & 15) * 17
                put(bx + (i >> 2), by + (i & 3), (*c, a))
        return bytes(out)
    for i, (x, y) in enumerate(_tiled_positions(width, height)):
        put(x, y, _unpack_pixel(fmt, data, i))
    return bytes(out)


def encode(fmt: str, rgba: bytes, width: int, height: int, flip_y: bool = False) -> bytes:
    """RGBA8 pixels (rows top to bottom) to GPU-layout data."""
    _check(width, height)
    if len(rgba) != width * height * 4:
        raise ValueError("pixel buffer size doesn't match width * height * 4")

    def get(x, y):
        row = height - 1 - y if flip_y else y
        o = (row * width + x) * 4
        return tuple(rgba[o:o + 4])

    if fmt in ("ETC1", "ETC1A4"):
        out = bytearray()
        for bx, by in _etc_blocks(width, height):
            px = [get(bx + (i >> 2), by + (i & 3)) for i in range(16)]
            if fmt == "ETC1A4":
                alpha = 0
                for i, p in enumerate(px):
                    alpha |= _q(p[3], 4) << (4 * i)
                out += struct.pack("<Q", alpha)
            out += struct.pack("<Q", _etc1_encode_block([p[:3] for p in px]))
        return bytes(out)
    return _pack_pixels(fmt, [get(x, y) for x, y in _tiled_positions(width, height)])
