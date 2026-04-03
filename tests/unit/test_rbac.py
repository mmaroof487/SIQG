"""Unit tests for RBAC."""
import pytest
from middleware.security.rbac import (
    needs_column_masking,
    mask_pii_value,
    is_column_denied,
    apply_rbac_masking,
)


@pytest.mark.parametrize("column,role,expected", [
    ("ssn", "admin", False),
    ("ssn", "readonly", True),
    ("ssn", "guest", True),
    ("credit_card", "admin", False),
    ("credit_card", "readonly", True),
    ("email", "admin", False),
    ("email", "readonly", True),  # masked
    ("email", "guest", False),  # not masked for guest
    ("unknown_column", "admin", False),
])
def test_column_masking_rules(column, role, expected):
    """Test column masking rules."""
    result = needs_column_masking(column, role)
    assert result == expected


@pytest.mark.parametrize("column,value,expected", [
    ("ssn", "123-45-6789", "***-**-6789"),
    ("ssn", "12", "***"),
    ("credit_card", "4532123456789012", "****-****-****-9012"),
    ("email", "user@example.com", "u***@example.com"),
    ("phone", "1234567890", "12******90"),
])
def test_pii_masking(column, value, expected):
    """Test PII masking."""
    result = mask_pii_value(column, value)
    assert result == expected


@pytest.mark.parametrize("column,role,expected", [
    ("hashed_password", "admin", False),
    ("hashed_password", "readonly", True),
    ("hashed_password", "guest", True),
    ("internal_notes", "admin", False),
    ("internal_notes", "readonly", True),
    ("internal_notes", "guest", True),
    ("email", "admin", False),
    ("email", "readonly", False),  # email is not denied, only masked
    ("unknown_column", "readonly", False),
])
def test_column_deny_list(column, role, expected):
    """Test column denial rules - columns that should be completely removed."""
    result = is_column_denied(column, role)
    assert result == expected


def test_apply_rbac_masking_admin_unrestricted():
    """Admin should see all columns unmasked."""
    rows = [
        {
            "id": 1,
            "email": "user@example.com",
            "hashed_password": "$2b$12$kqksR1h2UMPvGT9s20R9r...",
            "ssn": "123-45-6789",
        }
    ]
    result = apply_rbac_masking("admin", rows)
    assert len(result) == 1
    assert result[0]["email"] == "user@example.com"
    assert result[0]["hashed_password"] == "$2b$12$kqksR1h2UMPvGT9s20R9r..."
    assert result[0]["ssn"] == "123-45-6789"


def test_apply_rbac_masking_readonly_denies_password():
    """Readonly should not see hashed_password (denied) but should see masked email."""
    rows = [
        {
            "id": 1,
            "email": "user@example.com",
            "hashed_password": "$2b$12$kqksR1h2UMPvGT9s20R9r...",
            "ssn": "123-45-6789",
        }
    ]
    result = apply_rbac_masking("readonly", rows)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert "hashed_password" not in result[0], "hashed_password should be denied for readonly"
    assert result[0]["email"] == "u***@example.com", "email should be masked for readonly"
    assert result[0]["ssn"] == "***-**-6789", "ssn should be masked for readonly"


def test_apply_rbac_masking_guest_denies_multiple():
    """Guest should have multiple columns denied (hashed_password, internal_notes)."""
    rows = [
        {
            "id": 1,
            "username": "testuser",
            "email": "user@example.com",
            "hashed_password": "$2b$12$...",
            "internal_notes": "VIP customer",
            "ssn": "123-45-6789",
        }
    ]
    result = apply_rbac_masking("guest", rows)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["username"] == "testuser"
    assert "hashed_password" not in result[0], "hashed_password should be denied for guest"
    assert "internal_notes" not in result[0], "internal_notes should be denied for guest"
