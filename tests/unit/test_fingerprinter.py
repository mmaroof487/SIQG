"""Unit tests for query fingerprinting."""
import pytest
from middleware.performance.fingerprinter import (
    normalize_query,
    fingerprint_query,
    extract_tables_from_query,
)


def test_normalize_query_whitespace():
    """Test that whitespace is normalized."""
    q1 = "SELECT * FROM users"
    q2 = "SELECT  *  FROM  users"
    assert normalize_query(q1) == normalize_query(q2)


def test_normalize_query_case():
    """Test that case is normalized."""
    q1 = "SELECT * FROM USERS"
    q2 = "select * from users"
    assert normalize_query(q1) == normalize_query(q2)


def test_normalize_query_string_literals():
    """Test that string literals are replaced."""
    q1 = "SELECT * FROM users WHERE name = 'John'"
    q2 = "SELECT * FROM users WHERE name = 'Jane'"
    assert normalize_query(q1) == normalize_query(q2)


def test_normalize_query_numbers():
    """Test that numbers are replaced."""
    q1 = "SELECT * FROM users WHERE id = 123"
    q2 = "SELECT * FROM users WHERE id = 456"
    assert normalize_query(q1) == normalize_query(q2)


def test_fingerprint_consistency():
    """Test that same normalized query produces same fingerprint."""
    q1 = "SELECT * FROM users WHERE id = 1"
    q2 = "SELECT * FROM users WHERE id = 999"
    assert fingerprint_query(q1) == fingerprint_query(q2)


def test_extract_tables():
    """Test table extraction from query."""
    query = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
    tables = extract_tables_from_query(query)
    assert "users" in tables
    assert "orders" in tables


def test_extract_tables_single():
    """Test table extraction for simple query."""
    query = "SELECT * FROM products"
    tables = extract_tables_from_query(query)
    assert tables == ("products",)
