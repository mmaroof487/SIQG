"""Unit tests for sensitivity_scanner.py — PII column detection."""
import pytest
from middleware.security.sensitivity_scanner import (
    scan_columns,
    ScanResult,
    ClassificationMethod,
)


def _col(table, col, schema="public"):
    return {"schema_name": schema, "table_name": table, "column_name": col}


# ── Tier 1: Regex ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_ssn_regex():
    results = await scan_columns([_col("users", "ssn")])
    assert len(results) == 1
    assert results[0].label == "ssn"
    assert results[0].classification_method == ClassificationMethod.REGEX


@pytest.mark.asyncio
async def test_detect_email_regex():
    results = await scan_columns([_col("users", "email_address")])
    assert any(r.label == "email" for r in results)


@pytest.mark.asyncio
async def test_detect_credit_card_regex():
    results = await scan_columns([_col("payments", "credit_card_number")])
    assert any(r.label == "credit_card" for r in results)


@pytest.mark.asyncio
async def test_detect_phone_regex():
    results = await scan_columns([_col("contacts", "mobile_number")])
    assert any(r.label == "phone" for r in results)


@pytest.mark.asyncio
async def test_detect_password_regex():
    results = await scan_columns([_col("users", "hashed_password")])
    assert any(r.label == "password" for r in results)


@pytest.mark.asyncio
async def test_detect_dob_regex():
    results = await scan_columns([_col("profiles", "date_of_birth")])
    assert any(r.label == "dob" for r in results)


# ── Tier 2: Dictionary ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detect_api_key_dict():
    results = await scan_columns([_col("config", "api_key")])
    assert len(results) == 1
    assert results[0].classification_method == ClassificationMethod.DICTIONARY


@pytest.mark.asyncio
async def test_detect_token_dict():
    results = await scan_columns([_col("sessions", "access_token")])
    assert len(results) == 1
    assert results[0].classification_method == ClassificationMethod.DICTIONARY


@pytest.mark.asyncio
async def test_detect_salary_dict():
    results = await scan_columns([_col("hr", "base_salary")])
    # "salary" is a regex pattern too, check it fires
    assert len(results) == 1


# ── Non-sensitive columns pass through ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_non_sensitive_columns_not_flagged():
    cols = [
        _col("products", "name"),
        _col("products", "price"),
        _col("products", "created_at"),
        _col("orders", "status"),
    ]
    results = await scan_columns(cols)
    assert results == []


# ── Multiple columns mixed ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mixed_columns():
    cols = [
        _col("users", "id"),
        _col("users", "email"),
        _col("users", "ssn"),
        _col("users", "name"),
        _col("users", "credit_card"),
    ]
    results = await scan_columns(cols)
    result_cols = {r.column_name for r in results}
    assert "email" in result_cols
    assert "ssn" in result_cols
    assert "credit_card" in result_cols
    assert "id" not in result_cols
    assert "name" not in result_cols


# ── Deduplication ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_no_duplicate_results():
    cols = [
        _col("users", "ssn"),
        _col("users", "ssn"),   # duplicate input
    ]
    results = await scan_columns(cols)
    assert len(results) == 1


# ── ScanResult.to_dict ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_to_dict():
    results = await scan_columns([_col("users", "ssn")])
    d = results[0].to_dict()
    assert d["table_name"] == "users"
    assert d["column_name"] == "ssn"
    assert d["label"] == "ssn"
    assert 0.0 <= d["confidence"] <= 1.0


# ── Sorting ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_results_sorted_by_table_then_column():
    cols = [
        _col("users", "ssn"),
        _col("accounts", "credit_card"),
        _col("users", "email"),
    ]
    results = await scan_columns(cols)
    names = [(r.table_name, r.column_name) for r in results]
    assert names == sorted(names)
