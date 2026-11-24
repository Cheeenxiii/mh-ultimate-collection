#!/usr/bin/env python3
"""AES-128 in ECB, CTR and XTS (Nintendo's big-endian tweak), standard library only.

A pure-Python implementation (FIPS-197) is always available. When the system's
OpenSSL `libcrypto` can be loaded through `ctypes`, bulk ECB and CTR go through it
instead (hundreds of times faster); results are identical, and tests check both paths
against the FIPS-197 and NIST SP 800-38A vectors.

This module never reads keys from anywhere: callers pass them in.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import os

BLOCK = 16

# ── Pure-Python AES-128 ─────────────────────────────────────────────────────


def _xtime(b: int) -> int:
    b <<= 1
    return (b ^ 0x11B) if b & 0x100 else b


def _build_tables():
    sbox = [0] * 256
    inv = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0)
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q &= 0xFF
        if q & 0x80:
            q ^= 0x09
        x = q ^ ((q << 1 | q >> 7) & 0xFF) ^ ((q << 2 | q >> 6) & 0xFF) \
            ^ ((q << 3 | q >> 5) & 0xFF) ^ ((q << 4 | q >> 4) & 0xFF)
        sbox[p] = (x ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    for i, s in enumerate(sbox):
        inv[s] = i

    def mul(a: int, b: int) -> int:
        r = 0
        while b:
            if b & 1:
                r ^= a
            a = _xtime(a)
            b >>= 1
        return r

    te = [[0] * 256 for _ in range(4)]
    td = [[0] * 256 for _ in range(4)]
    for i in range(256):
        s = sbox[i]
        w = (mul(s, 2) << 24) | (s << 16) | (s << 8) | mul(s, 3)
        si = inv[i]
        v = (mul(si, 14) << 24) | (mul(si, 9) << 16) | (mul(si, 13) << 8) | mul(si, 11)
        for k in range(4):
            te[k][i] = ((w >> (8 * k)) | (w << (32 - 8 * k))) & 0xFFFFFFFF
            td[k][i] = ((v >> (8 * k)) | (v << (32 - 8 * k))) & 0xFFFFFFFF
    return sbox, inv, te, td, mul


SBOX, INV_SBOX, _TE, _TD, _gmul = _build_tables()


def _expand_key(key: bytes) -> list[int]:
    if len(key) != 16:
        raise ValueError("AES-128 needs a 16-byte key")
    w = [int.from_bytes(key[i:i + 4], "big") for i in range(0, 16, 4)]
    rcon = 1
    for i in range(4, 44):
        t = w[i - 1]
        if i % 4 == 0:
            t = ((t << 8) | (t >> 24)) & 0xFFFFFFFF
            t = (SBOX[t >> 24] << 24) | (SBOX[(t >> 16) & 0xFF] << 16) \
                | (SBOX[(t >> 8) & 0xFF] << 8) | SBOX[t & 0xFF]
            t ^= rcon << 24
            rcon = _xtime(rcon)
        w.append(w[i - 4] ^ t)
    return w


def _inv_mix(w: int) -> int:
    b = w.to_bytes(4, "big")
    m = _gmul
    return int.from_bytes(bytes([
        m(b[0], 14) ^ m(b[1], 11) ^ m(b[2], 13) ^ m(b[3], 9),
        m(b[0], 9) ^ m(b[1], 14) ^ m(b[2], 11) ^ m(b[3], 13),
        m(b[0], 13) ^ m(b[1], 9) ^ m(b[2], 14) ^ m(b[3], 11),
        m(b[0], 11) ^ m(b[1], 13) ^ m(b[2], 9) ^ m(b[3], 14),
    ]), "big")


class PyAES:
    """One AES-128 key, pure Python."""

    def __init__(self, key: bytes):
        self.ek = _expand_key(key)
        dk = []
        for r in range(10, -1, -1):
            rk = self.ek[4 * r:4 * r + 4]
            dk.extend(rk if r in (0, 10) else [_inv_mix(x) for x in rk])
        self.dk = dk

    @staticmethod
    def _rounds(block: bytes, k: list[int], t, box, enc: bool) -> bytes:
        t0, t1, t2, t3 = t
        s0, s1, s2, s3 = (int.from_bytes(block[i:i + 4], "big") ^ k[i // 4] for i in range(0, 16, 4))
        for r in range(1, 10):
            if enc:
                n0 = t0[s0 >> 24] ^ t1[(s1 >> 16) & 255] ^ t2[(s2 >> 8) & 255] ^ t3[s3 & 255]
                n1 = t0[s1 >> 24] ^ t1[(s2 >> 16) & 255] ^ t2[(s3 >> 8) & 255] ^ t3[s0 & 255]
                n2 = t0[s2 >> 24] ^ t1[(s3 >> 16) & 255] ^ t2[(s0 >> 8) & 255] ^ t3[s1 & 255]
                n3 = t0[s3 >> 24] ^ t1[(s0 >> 16) & 255] ^ t2[(s1 >> 8) & 255] ^ t3[s2 & 255]
            else:
                n0 = t0[s0 >> 24] ^ t1[(s3 >> 16) & 255] ^ t2[(s2 >> 8) & 255] ^ t3[s1 & 255]
                n1 = t0[s1 >> 24] ^ t1[(s0 >> 16) & 255] ^ t2[(s3 >> 8) & 255] ^ t3[s2 & 255]
                n2 = t0[s2 >> 24] ^ t1[(s1 >> 16) & 255] ^ t2[(s0 >> 8) & 255] ^ t3[s3 & 255]
                n3 = t0[s3 >> 24] ^ t1[(s2 >> 16) & 255] ^ t2[(s1 >> 8) & 255] ^ t3[s0 & 255]
            s0, s1, s2, s3 = (n0 ^ k[4 * r], n1 ^ k[4 * r + 1], n2 ^ k[4 * r + 2], n3 ^ k[4 * r + 3])
        st = (s0, s1, s2, s3)
        out = bytearray(16)
        for c in range(4):
            if enc:
                a, b, cc, d = st[c], st[(c + 1) % 4], st[(c + 2) % 4], st[(c + 3) % 4]
            else:
                a, b, cc, d = st[c], st[(c + 3) % 4], st[(c + 2) % 4], st[(c + 1) % 4]
            w = (box[a >> 24] << 24) | (box[(b >> 16) & 255] << 16) \
                | (box[(cc >> 8) & 255] << 8) | box[d & 255]
            out[4 * c:4 * c + 4] = (w ^ k[40 + c]).to_bytes(4, "big")
        return bytes(out)

    def encrypt_block(self, b: bytes) -> bytes:
        return self._rounds(b, self.ek, _TE, SBOX, True)

    def decrypt_block(self, b: bytes) -> bytes:
        return self._rounds(b, self.dk, _TD, INV_SBOX, False)


# ── Optional OpenSSL fast path (ctypes, no third-party package) ─────────────

_LIB = None


def _libcrypto():
    global _LIB
    if _LIB is not None:
        return _LIB or None
    _LIB = False
    if os.environ.get("AES128_PURE"):
        return None
    name = ctypes.util.find_library("crypto")
    for cand in filter(None, [name, "libcrypto.so.3", "libcrypto.so", "libcrypto.dylib"]):
        try:
            lib = ctypes.CDLL(cand)
            lib.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
            lib.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
            lib.EVP_aes_128_ecb.restype = ctypes.c_void_p
            lib.EVP_aes_128_ctr.restype = ctypes.c_void_p
            lib.EVP_CipherInit_ex.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                              ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
            lib.EVP_CIPHER_CTX_set_padding.argtypes = [ctypes.c_void_p, ctypes.c_int]
            lib.EVP_CipherUpdate.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                             ctypes.POINTER(ctypes.c_int), ctypes.c_char_p, ctypes.c_int]
            _LIB = lib
            return lib
        except (OSError, AttributeError):
            continue
    return None


def backend() -> str:
    return "openssl" if _libcrypto() else "python"


def _evp(cipher: str, key: bytes, iv: bytes | None, data: bytes, enc: bool) -> bytes:
    lib = _libcrypto()
    ctx = lib.EVP_CIPHER_CTX_new()
    if not ctx:
        raise MemoryError("EVP_CIPHER_CTX_new failed")
    try:
        ciph = lib.EVP_aes_128_ecb() if cipher == "ecb" else lib.EVP_aes_128_ctr()
        if lib.EVP_CipherInit_ex(ctx, ciph, None, key, iv, 1 if enc else 0) != 1:
            raise ValueError("EVP_CipherInit_ex failed")
        lib.EVP_CIPHER_CTX_set_padding(ctx, 0)
        out = ctypes.create_string_buffer(len(data) + 32)
        n = ctypes.c_int(0)
        if lib.EVP_CipherUpdate(ctx, out, ctypes.byref(n), data, len(data)) != 1:
            raise ValueError("EVP_CipherUpdate failed")
        return out.raw[:n.value]
    finally:
        lib.EVP_CIPHER_CTX_free(ctx)


# ── Modes ───────────────────────────────────────────────────────────────────


def ecb_encrypt(key: bytes, data: bytes) -> bytes:
    if len(data) % BLOCK:
        raise ValueError("ECB data must be a multiple of 16 bytes")
    if _libcrypto():
        return _evp("ecb", key, None, data, True)
    a = PyAES(key)
    return b"".join(a.encrypt_block(data[i:i + 16]) for i in range(0, len(data), 16))


def ecb_decrypt(key: bytes, data: bytes) -> bytes:
    if len(data) % BLOCK:
        raise ValueError("ECB data must be a multiple of 16 bytes")
    if _libcrypto():
        return _evp("ecb", key, None, data, False)
    a = PyAES(key)
    return b"".join(a.decrypt_block(data[i:i + 16]) for i in range(0, len(data), 16))


def ctr_crypt(key: bytes, iv: bytes, data: bytes) -> bytes:
    """AES-CTR with a 128-bit big-endian counter starting at `iv` (encrypt = decrypt)."""
    if len(iv) != 16:
        raise ValueError("CTR needs a 16-byte counter block")
    if _libcrypto():
        return _evp("ctr", key, iv, data, True)
    a = PyAES(key)
    ctr = int.from_bytes(iv, "big")
    out = bytearray(len(data))
    for i in range(0, len(data), 16):
        ks = a.encrypt_block(ctr.to_bytes(16, "big"))
        chunk = data[i:i + 16]
        out[i:i + len(chunk)] = bytes(x ^ y for x, y in zip(chunk, ks, strict=False))
        ctr = (ctr + 1) & ((1 << 128) - 1)
    return bytes(out)


def _gf_double(t: bytes) -> bytes:
    v = int.from_bytes(t, "little")
    v = ((v << 1) ^ (0x87 if v >> 127 else 0)) & ((1 << 128) - 1)
    return v.to_bytes(16, "little")


def _xts(key: bytes, data: bytes, sector: int, sector_size: int, enc: bool) -> bytes:
    if len(key) != 32:
        raise ValueError("XTS needs a 32-byte key (data key, tweak key)")
    if len(data) % sector_size or sector_size % BLOCK:
        raise ValueError("XTS data must be whole sectors")
    k1, k2 = key[:16], key[16:]
    out = bytearray()
    for s in range(len(data) // sector_size):
        # Nintendo's variant: the sector number is a big-endian 128-bit tweak.
        t = ecb_encrypt(k2, (sector + s).to_bytes(16, "big"))
        tweaks = []
        for _ in range(sector_size // BLOCK):
            tweaks.append(t)
            t = _gf_double(t)
        tw = b"".join(tweaks)
        blk = data[s * sector_size:(s + 1) * sector_size]
        x = bytes(a ^ b for a, b in zip(blk, tw, strict=False))
        y = ecb_encrypt(k1, x) if enc else ecb_decrypt(k1, x)
        out += bytes(a ^ b for a, b in zip(y, tw, strict=False))
    return bytes(out)


def xts_decrypt(key: bytes, data: bytes, sector: int = 0, sector_size: int = 0x200) -> bytes:
    return _xts(key, data, sector, sector_size, False)


def xts_encrypt(key: bytes, data: bytes, sector: int = 0, sector_size: int = 0x200) -> bytes:
    return _xts(key, data, sector, sector_size, True)
