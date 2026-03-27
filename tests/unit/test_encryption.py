"""Unit tests for Phase 3 encryption/decryption helpers."""
from middleware.security.encryption import decrypt_value, encrypt_value


def test_encrypt_decrypt_roundtrip():
    plaintext = "secret@example.com"
    encrypted = encrypt_value(plaintext)
    decrypted = decrypt_value(encrypted)
    assert encrypted != plaintext
    assert decrypted == plaintext


def test_encrypt_uses_random_nonce():
    plaintext = "same-input"
    c1 = encrypt_value(plaintext)
    c2 = encrypt_value(plaintext)
    assert c1 != c2


def test_decrypt_invalid_ciphertext_graceful():
    invalid = "not-valid-base64"
    result = decrypt_value(invalid)
    assert result == invalid
