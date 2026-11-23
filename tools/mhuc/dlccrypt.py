"""DLC and Extra Data crypto of MH4U, MHXX and MH3U (specs/quest.md, checks Q4, Q9, Q11, Q14).

No key is stored here: every function takes the key, and the CLI reads it from a file the user supplies
(mhef's `mhef/n3ds.py` for MH4U's, goshawk's `utils/constants.py` for the login keys).
Layouts follow svanheulen/mhef (GPL-3.0) for MH4U and MHX/MHXX, and Cha-Cha (GPL-3.0) for MH3U.
"""
from __future__ import annotations

import hashlib
import struct

from .blowfish import Blowfish

MH4U_SAVE_MODES = ("normal", "card", "quest")


class CryptoError(ValueError):
    pass


def _swap_words(data: bytes) -> bytes:
    n = len(data) // 4
    return struct.pack(f">{n}I", *struct.unpack(f"<{n}I", data[:4 * n])) + data[4 * n:]


def _xor_u16(data: bytes, seed: int) -> bytes:
    words = list(struct.unpack(f"<{len(data) // 2}H", data))
    key = seed
    for i in range(len(words)):
        if key == 0:
            key = 1
        key = key * 0xB0 % 0xFF53
        words[i] ^= key
    return struct.pack(f"<{len(words)}H", *words)


def mh4u_save_decrypt(data: bytes, key: bytes, mode: str = "normal") -> bytes:
    """MH4U save and Extra Data (mhef SavedataCipher): Blowfish on little-endian words, then a 16-bit XOR
    stream seeded from the first word, then a checksum word. 'card' leaves the first 24 bytes in the clear;
    'quest' drops a 0x100-byte tail first."""
    if mode not in MH4U_SAVE_MODES:
        raise ValueError(f"mode is one of {MH4U_SAVE_MODES}")
    if mode == "quest":
        data = data[:-0x100]
    bf = Blowfish(key)
    if mode == "card":
        body = data[:24] + bf.ecb_decrypt(data[24:], "<")
    else:
        body = bf.ecb_decrypt(data, "<")
    seed = struct.unpack_from("<I", body)[0] >> 16
    rest = _xor_u16(body[4:], seed)
    csum, plain = struct.unpack_from("<I", rest)[0], rest[4:]
    if csum != sum(plain) & 0xFFFFFFFF:
        raise CryptoError("checksum mismatch: wrong key or mode")
    return plain


def mh4u_save_encrypt(plain: bytes, key: bytes, mode: str = "normal", seed: int = 0x1234) -> bytes:
    if mode not in MH4U_SAVE_MODES:
        raise ValueError(f"mode is one of {MH4U_SAVE_MODES}")
    body = struct.pack("<I", sum(plain) & 0xFFFFFFFF) + plain
    body = struct.pack("<I", (seed << 16) | 0x10) + _xor_u16(body, seed)
    bf = Blowfish(key)
    out = body[:24] + bf.ecb_encrypt(body[24:], "<") if mode == "card" else bf.ecb_encrypt(body, "<")
    return out + (b"\0" * 0x100 if mode == "quest" else b"")


def _unwrap_sha(plain: bytes) -> bytes:
    body, digest = plain[:-20], plain[-20:]
    if hashlib.sha1(body).digest() != digest:
        raise CryptoError("SHA-1 mismatch: wrong key")
    return body


def _ecb_file_decrypt(data: bytes, bf: Blowfish) -> bytes:
    size = struct.unpack(">I", data[-4:])[0]
    if size > len(data) - 4:
        raise CryptoError("size trailer larger than the file")
    return _unwrap_sha(bf.ecb_decrypt(data[:-4], "<")[:size])


def _ecb_file_encrypt(plain: bytes, bf: Blowfish) -> bytes:
    body = plain + hashlib.sha1(plain).digest()
    size = len(body)
    body += b"\0" * (-size % 8)
    return bf.ecb_encrypt(body, "<") + struct.pack(">I", size)


def mh4u_dlc_decrypt(data: bytes, key: bytes) -> bytes:
    """A server file of MH4U (mhef DLCCipher): Blowfish ECB on little-endian words over plain + SHA-1, padded
    to 8, then the plain-plus-hash size as a big-endian u32."""
    return _ecb_file_decrypt(data, Blowfish(key))


def mh4u_dlc_encrypt(plain: bytes, key: bytes) -> bytes:
    return _ecb_file_encrypt(plain, Blowfish(key))


def mh3u_dlc_decrypt(data: bytes, key: bytes) -> bytes:
    """A server file of MH3U: the same layout as MH4U's, with MtCipher (Blowfish's MT variant)."""
    return _ecb_file_decrypt(data, Blowfish(key, mt=True))


def mh3u_dlc_encrypt(plain: bytes, key: bytes) -> bytes:
    return _ecb_file_encrypt(plain, Blowfish(key, mt=True))


def mhxx_dlc_decrypt(data: bytes, key: bytes, signatures: int = 1) -> bytes:
    """A server file of MHXX (mhef DLCXCipher, one 0x100 signature for MHXX, two for MHX): Blowfish CTR over
    plain + SHA-1, then a 4-byte nonce, then the signatures (not verified here)."""
    buf = data[:len(data) - 0x100 * signatures]
    nonce, body = buf[-4:][::-1], buf[:-4]
    plain = Blowfish(key).ctr(body, nonce, ">", "<")
    return _unwrap_sha(plain)


def mhxx_dlc_encrypt(plain: bytes, key: bytes, nonce: bytes = b"\1\2\3\4", signatures: int = 1) -> bytes:
    """For tests and round trips: the signatures are zeros, which the game would reject."""
    body = plain + hashlib.sha1(plain).digest()
    return Blowfish(key).ctr(body, nonce, ">", "<") + nonce[::-1] + b"\0" * (0x100 * signatures)
