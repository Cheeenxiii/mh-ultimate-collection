"""reference/: the one piece with no check of its own. A wrong AES gives garbage Switch code."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reference"))
import aes128  # noqa: E402

KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
PLAIN = bytes.fromhex("00112233445566778899aabbccddeeff")
CIPHER = bytes.fromhex("69c4e0d86a7b0430d8cdb78070b4c55a")     # FIPS-197, appendix C.1


def test_pure_python_aes_matches_fips197():
    aes = aes128.PyAES(KEY)
    assert aes.encrypt_block(PLAIN) == CIPHER
    assert aes.decrypt_block(CIPHER) == PLAIN


def test_aes_ecb_through_libcrypto_or_python_matches_fips197():
    assert aes128.ecb_encrypt(KEY, PLAIN) == CIPHER
