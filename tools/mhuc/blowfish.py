"""Blowfish, standard library only, with MT Framework's variant (MtCipher) as an option.

The P-array and S-boxes start from the hexadecimal digits of pi, computed here (Machin's formula), so no
table is copied. `mt=True` gives MtCipher's key schedule as Cha-Cha documents it (runtime/os/dlc_server.cpp,
GPL-3.0): the S-box loop advances one entry per encryption while writing two, so every entry ends up as
the left half of successive encryptions. Byte order is the caller's: blocks are given as two u32.
"""
from __future__ import annotations

import struct
from functools import lru_cache

ROUNDS = 16


@lru_cache(maxsize=1)
def pi_words(n: int = 18 + 1024) -> tuple[int, ...]:
    """The first n 32-bit words of pi's fractional part (0x243F6A88, 0x85A308D3, ...)."""
    prec = 32 * n + 64

    def atan_inv(x: int) -> int:
        one = 1 << prec
        term = total = one // x
        x2, k, sign = x * x, 1, -1
        while term:
            term //= x2
            total += sign * (term // (2 * k + 1))
            sign, k = -sign, k + 1
        return total

    pi = 16 * atan_inv(5) - 4 * atan_inv(239)
    frac = pi - (3 << prec)
    return tuple((frac >> (prec - 32 * (i + 1))) & 0xFFFFFFFF for i in range(n))


class Blowfish:
    def __init__(self, key: bytes, mt: bool = False):
        if not 1 <= len(key) <= 72:
            raise ValueError("Blowfish keys are 1 to 72 bytes")
        w = pi_words()
        self.p = list(w[:18])
        self.s = [list(w[18 + 256 * b: 18 + 256 * (b + 1)]) for b in range(4)]
        k = 0
        for i in range(18):
            word = 0
            for _ in range(4):
                word = (word << 8) | key[k]
                k = (k + 1) % len(key)
            self.p[i] ^= word
        left = right = 0
        for i in range(0, 18, 2):
            left, right = self.encrypt_block(left, right)
            self.p[i], self.p[i + 1] = left, right
        for i in range(0, 4 * 256, 1 if mt else 2):
            left, right = self.encrypt_block(left, right)
            self.s[i // 256][i % 256] = left
            j = i + 1
            if j < 4 * 256:
                self.s[j // 256][j % 256] = right

    def _f(self, x: int) -> int:
        s = self.s
        h = (s[0][x >> 24] + s[1][(x >> 16) & 0xFF]) & 0xFFFFFFFF
        return ((h ^ s[2][(x >> 8) & 0xFF]) + s[3][x & 0xFF]) & 0xFFFFFFFF

    def encrypt_block(self, left: int, right: int) -> tuple[int, int]:
        p = self.p
        for i in range(ROUNDS):
            left ^= p[i]
            right ^= self._f(left)
            left, right = right, left
        left, right = right, left
        return left ^ p[17], right ^ p[16]

    def decrypt_block(self, left: int, right: int) -> tuple[int, int]:
        p = self.p
        for i in range(17, 1, -1):
            left ^= p[i]
            right ^= self._f(left)
            left, right = right, left
        left, right = right, left
        return left ^ p[0], right ^ p[1]

    def _ecb(self, data: bytes, order: str, fn) -> bytes:
        if len(data) % 8:
            raise ValueError("ECB data must be a multiple of 8 bytes")
        fmt = order + "2I"
        out = bytearray(len(data))
        for i in range(0, len(data), 8):
            struct.pack_into(fmt, out, i, *fn(*struct.unpack_from(fmt, data, i)))
        return bytes(out)

    def ecb_encrypt(self, data: bytes, order: str = ">") -> bytes:
        """ECB over 8-byte blocks read as two u32 in `order` ('>' standard, '<' MT on 3DS/Wii U)."""
        return self._ecb(data, order, self.encrypt_block)

    def ecb_decrypt(self, data: bytes, order: str = ">") -> bytes:
        return self._ecb(data, order, self.decrypt_block)

    def ctr(self, data: bytes, prefix: bytes, in_order: str = ">", out_order: str = ">") -> bytes:
        """CTR as mhef's DLCXCipher uses it: counter block = 4 prefix bytes + a little-endian 32-bit counter
        from 0, read as two u32 in `in_order`, encrypted, written back in `out_order`, XORed with the data."""
        if len(prefix) != 4:
            raise ValueError("the CTR prefix is 4 bytes")
        out = bytearray(len(data))
        for n, i in enumerate(range(0, len(data), 8)):
            block = prefix + struct.pack("<I", n)
            ks = struct.pack(out_order + "2I", *self.encrypt_block(*struct.unpack(in_order + "2I", block)))
            chunk = data[i:i + 8]
            out[i:i + len(chunk)] = bytes(a ^ b for a, b in zip(chunk, ks, strict=False))
        return bytes(out)
