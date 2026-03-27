import pytest
from middleware.security.encryption import encrypt_value, decrypt_value, encrypt_query_values, decrypt_rows
from config import settings

def test_string_encryption():
    plain = "sensitive_data"
    enc = encrypt_value(plain)
    assert enc != plain
    assert decrypt_value(enc) == plain

def test_query_encryption_no_match():
    query = "SELECT * FROM public_table"
    enc = encrypt_query_values(query)
    assert enc == query

def test_query_encryption_matches():
    settings.encrypt_columns_list = ["email"]
    query = "INSERT INTO users (id, email) VALUES (1, 'secret@test.com')"
    enc = encrypt_query_values(query)
    assert "secret@test.com" not in enc
    assert "INSERT INTO users" in enc

def test_decrypt_rows_no_match():
    rows = [{"id": 1, "public_col": "data"}]
    dec = decrypt_rows(rows)
    assert dec[0]["public_col"] == "data"

def test_decrypt_rows_resolves():
    settings.encrypt_columns_list = ["email"]
    encrypted_val = encrypt_value("secret@test.com")
    rows = [{"id": 1, "email": encrypted_val}]
    dec = decrypt_rows(rows)
    assert dec[0]["email"] == "secret@test.com"
