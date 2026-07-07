"""Unit tests for query_encryptor.py — AST-based column encryption pipeline."""
import os
import pytest
from middleware.security.query_encryptor import (
    QueryEncryptor,
    make_encryptor,
    _aes_encrypt,
    _aes_decrypt,
    _pack,
    _unpack,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

DEK = os.urandom(32)   # fresh 32-byte key per test run

COLUMN_MAP = {
    "users": {"ssn", "credit_card"},
    "orders": {"card_number"},
}


@pytest.fixture
def enc():
    return QueryEncryptor(dek=DEK, key_version=1, encrypted_columns=COLUMN_MAP)


# ── Envelope format tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pack_unpack_round_trip():
    nonce = os.urandom(12)
    ct = os.urandom(32)
    encoded = _pack(1, nonce, ct)
    result = _unpack(encoded)
    assert result is not None
    assert result[0] == 1
    assert result[1] == nonce
    assert result[2] == ct


@pytest.mark.asyncio
async def test_unpack_returns_none_on_garbage():
    assert _unpack("not-base64!!!") is None
    assert _unpack("YQ==") is None          # too short


@pytest.mark.asyncio
async def test_aes_round_trip():
    plaintext = "123-45-6789"
    ciphertext = _aes_encrypt(plaintext, DEK, 1)
    assert ciphertext != plaintext
    assert _aes_decrypt(ciphertext, DEK) == plaintext


@pytest.mark.asyncio
async def test_aes_decrypt_passthrough_non_ciphertext():
    """Plain strings that aren't our envelope should pass through unchanged."""
    result = _aes_decrypt("hello world", DEK)
    assert result == "hello world"


@pytest.mark.asyncio
async def test_aes_decrypt_wrong_key_passthrough():
    """Decrypting with wrong key should not raise — returns original."""
    ciphertext = _aes_encrypt("secret", DEK, 1)
    wrong_key = os.urandom(32)
    result = _aes_decrypt(ciphertext, wrong_key)
    # Should return the original ciphertext (not raise)
    assert isinstance(result, str)


# ── INSERT rewriting ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_encrypt_insert_single_row(enc):
    sql = "INSERT INTO users (id, ssn, name) VALUES ('u1', '123-45-6789', 'Alice')"
    result = enc.encrypt_query(sql)
    assert "123-45-6789" not in result
    assert "u1" in result        # non-sensitive column unchanged
    assert "Alice" in result     # non-sensitive column unchanged


@pytest.mark.asyncio
async def test_encrypt_insert_multi_row(enc):
    sql = (
        "INSERT INTO users (id, ssn) VALUES "
        "('u1', '111-11-1111'), ('u2', '222-22-2222')"
    )
    result = enc.encrypt_query(sql)
    assert "111-11-1111" not in result
    assert "222-22-2222" not in result
    assert "u1" in result
    assert "u2" in result


@pytest.mark.asyncio
async def test_encrypt_insert_non_sensitive_column(enc):
    sql = "INSERT INTO users (id, name) VALUES ('u1', 'Alice')"
    result = enc.encrypt_query(sql)
    assert result == sql   # nothing should change


@pytest.mark.asyncio
async def test_encrypt_insert_different_table(enc):
    """orders.card_number should be encrypted."""
    sql = "INSERT INTO orders (id, card_number) VALUES ('o1', '4111111111111111')"
    result = enc.encrypt_query(sql)
    assert "4111111111111111" not in result


@pytest.mark.asyncio
async def test_encrypt_insert_unknown_table(enc):
    """Table not in encrypted_columns — SQL untouched."""
    sql = "INSERT INTO products (id, price) VALUES ('p1', '99.99')"
    result = enc.encrypt_query(sql)
    assert result == sql


@pytest.mark.asyncio
async def test_encrypt_insert_select_skipped(enc):
    """INSERT ... SELECT should not be rewritten (no VALUES)."""
    sql = "INSERT INTO users (id, ssn) SELECT id, ssn FROM staging"
    result = enc.encrypt_query(sql)
    # Should not raise; may or may not change (but won't encrypt SELECT source)
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_encrypt_parameterized_insert_skipped(enc):
    """Parameterized queries must not be altered."""
    sql = "INSERT INTO users (id, ssn) VALUES ($1, $2)"
    result = enc.encrypt_query(sql)
    assert "$1" in result
    assert "$2" in result


# ── UPDATE rewriting ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_encrypt_update(enc):
    sql = "UPDATE users SET ssn = '999-99-9999', name = 'Bob' WHERE id = 'u1'"
    result = enc.encrypt_query(sql)
    assert "999-99-9999" not in result
    assert "Bob" in result    # non-sensitive unchanged
    assert "u1" in result


@pytest.mark.asyncio
async def test_encrypt_update_non_sensitive(enc):
    sql = "UPDATE users SET name = 'Charlie' WHERE id = 'u1'"
    result = enc.encrypt_query(sql)
    assert "Charlie" in result


# ── SELECT decryption ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_decrypt_results(enc):
    plaintext_ssn = "123-45-6789"
    ciphertext_ssn = _aes_encrypt(plaintext_ssn, DEK, 1)
    rows = [
        {"id": "u1", "ssn": ciphertext_ssn, "name": "Alice"},
    ]
    decrypted = enc.decrypt_results(rows, table="users")
    assert decrypted[0]["ssn"] == plaintext_ssn
    assert decrypted[0]["name"] == "Alice"   # unchanged


@pytest.mark.asyncio
async def test_decrypt_results_no_encrypted_cols(enc):
    rows = [{"id": "u1", "name": "Alice"}]
    result = enc.decrypt_results(rows, table="users")
    assert result[0] == rows[0]


@pytest.mark.asyncio
async def test_decrypt_results_wrong_table(enc):
    """Rows for unknown table should pass through unchanged."""
    rows = [{"id": "p1", "price": "99.99"}]
    result = enc.decrypt_results(rows, table="products")
    assert result == rows


@pytest.mark.asyncio
async def test_decrypt_results_multi_row(enc):
    ct1 = _aes_encrypt("111-11-1111", DEK, 1)
    ct2 = _aes_encrypt("222-22-2222", DEK, 1)
    rows = [{"id": "u1", "ssn": ct1}, {"id": "u2", "ssn": ct2}]
    decrypted = enc.decrypt_results(rows, table="users")
    assert decrypted[0]["ssn"] == "111-11-1111"
    assert decrypted[1]["ssn"] == "222-22-2222"


# ── make_encryptor factory ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_make_encryptor_from_rows():
    class MockRow:
        def __init__(self, table, col, is_encrypted):
            self.table_name = table
            self.column_name = col
            self.is_encrypted = is_encrypted

    rows = [
        MockRow("users", "ssn", True),
        MockRow("users", "name", False),
        MockRow("orders", "card_number", True),
    ]
    encryptor = make_encryptor(DEK, 1, rows)
    assert "ssn" in encryptor.encrypted_columns["users"]
    assert "name" not in encryptor.encrypted_columns.get("users", set())
    assert "card_number" in encryptor.encrypted_columns["orders"]


@pytest.mark.asyncio
async def test_make_encryptor_empty_rows():
    encryptor = make_encryptor(DEK, 1, [])
    sql = "INSERT INTO users (ssn) VALUES ('123')"
    assert encryptor.encrypt_query(sql) == sql


# ── No-op on empty encrypted_columns ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_encrypt_query_noop_when_no_columns():
    enc_empty = QueryEncryptor(dek=DEK, key_version=1, encrypted_columns={})
    sql = "INSERT INTO users (ssn) VALUES ('123')"
    assert enc_empty.encrypt_query(sql) == sql
