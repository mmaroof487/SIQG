"""Unit tests for SQL injection validator."""
import pytest
from middleware.security.validator import detect_sql_injection, validate_query
from fastapi import HTTPException


def test_detect_or_injection():
    """Test OR 1=1 detection."""
    assert detect_sql_injection("SELECT * FROM users WHERE id=1 OR 1=1")
    assert detect_sql_injection("SELECT * FROM users WHERE id=1 OR '1'='1'")


def test_detect_union_select():
    """Test UNION SELECT detection."""
    assert detect_sql_injection("SELECT * FROM users UNION SELECT * FROM admin")


def test_detect_comment():
    """Test comment detection."""
    assert detect_sql_injection("SELECT * FROM users --")
    assert detect_sql_injection("SELECT * FROM users /* comment */")


def test_clean_query():
    """Test clean query passes."""
    assert not detect_sql_injection("SELECT * FROM users WHERE id = 1")
    assert not detect_sql_injection("SELECT id, name FROM users WHERE email LIKE '%@gmail.com'")


@pytest.mark.asyncio
async def test_validate_select_query():
    """Test SELECT query validation passes."""
    await validate_query("SELECT * FROM users")


@pytest.mark.asyncio
async def test_validate_insert_query():
    """Test INSERT query validation passes."""
    await validate_query("INSERT INTO users (name) VALUES ('test')")


@pytest.mark.asyncio
async def test_block_drop_table():
    """Test DROP TABLE is blocked."""
    with pytest.raises(HTTPException) as exc:
        await validate_query("DROP TABLE users")
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_block_injection():
    """Test SQL injection is blocked."""
    with pytest.raises(HTTPException) as exc:
        await validate_query("SELECT * FROM users WHERE id=1 OR 1=1")
    assert exc.value.status_code == 400


# ---- Tests for the 5 new injection patterns ----

def test_detect_sleep_injection():
    """Test time-based blind injection: SLEEP()."""
    assert detect_sql_injection("SELECT * FROM users WHERE id=1 AND SLEEP(5)")


def test_detect_waitfor_injection():
    """Test time-based blind injection: WAITFOR DELAY."""
    assert detect_sql_injection("SELECT * FROM users; WAITFOR DELAY '0:0:5'")


def test_detect_benchmark_injection():
    """Test time-based blind injection: BENCHMARK()."""
    assert detect_sql_injection("SELECT BENCHMARK(1000000, SHA1('test'))")


def test_detect_information_schema():
    """Test schema enumeration: information_schema."""
    assert detect_sql_injection("SELECT * FROM information_schema.tables")


def test_detect_stacked_select():
    """Test stacked queries: ;SELECT."""
    assert detect_sql_injection("SELECT 1; SELECT * FROM users")

