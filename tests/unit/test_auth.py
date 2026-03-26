"""Unit tests for authentication."""
import pytest
from middleware.security.auth import (
    hash_api_key,
    create_jwt,
    decode_jwt,
    verify_password,
    hash_password,
)


def test_hash_api_key():
    """Test API key hashing is consistent."""
    key = "test_key_12345"
    hash1 = hash_api_key(key)
    hash2 = hash_api_key(key)
    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256


def test_create_and_decode_jwt():
    """Test JWT creation and decoding."""
    user_id = "test_user_123"
    role = "admin"

    token = create_jwt(user_id, role)
    payload = decode_jwt(token)

    assert payload["sub"] == user_id
    assert payload["role"] == role


def test_password_hashing():
    """Test password hashing and verification."""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)
