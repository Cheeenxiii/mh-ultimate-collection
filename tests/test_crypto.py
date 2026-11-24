"""Ciphers: a wrong byte here corrupts a save or makes the game reject a file."""
from __future__ import annotations

import pytest

from mhuc.crypto import dlccrypt
from mhuc.crypto.blowfish import Blowfish


@pytest.mark.parametrize("key, plain, cipher", [
    ("0000000000000000", "0000000000000000", "4EF997456198DD78"),
    ("FFFFFFFFFFFFFFFF", "FFFFFFFFFFFFFFFF", "51866FD5B85ECB8A"),
    ("0123456789ABCDEF", "1111111111111111", "61F9C3802281B096"),
])
def test_blowfish_matches_schneier_test_vectors(key, plain, cipher):
    p = int(plain, 16)
    left, right = Blowfish(bytes.fromhex(key)).encrypt_block(p >> 32, p & 0xFFFFFFFF)
    assert f"{left:08X}{right:08X}" == cipher


@pytest.mark.parametrize("mode", ["normal", "card", "quest"])
def test_save_cipher_decrypts_what_it_encrypts_in_every_mode(mode):
    key = b"test key, not the game's"
    plain = bytes(range(256)) * 4
    original = dlccrypt.mh4u_save_encrypt(plain, key, mode, seed=0xBEEF)
    decrypted = dlccrypt.mh4u_save_decrypt(original, key, mode)
    assert decrypted == plain
    assert dlccrypt.mh4u_save_encrypt(decrypted, key, mode, seed=0xBEEF) == original


def test_save_cipher_rejects_a_wrong_key():
    data = dlccrypt.mh4u_save_encrypt(bytes(64), b"right key")
    with pytest.raises(dlccrypt.CryptoError):
        dlccrypt.mh4u_save_decrypt(data, b"wrong key")
