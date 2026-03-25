"""Unit tests for RBAC."""
import pytest
from middleware.security.rbac import (
    needs_column_masking,
    mask_pii_value,
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
    ("phone", "1234567890", "**6890"),
])
def test_pii_masking(column, value, expected):
    """Test PII masking."""
    result = mask_pii_value(column, value)
    assert result == expected
