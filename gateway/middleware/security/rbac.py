"""RBAC (Role-Based Access Control) middleware."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# Role-based permissions
ROLE_PERMISSIONS = {
    "admin": {
        "tables": "*",  # All tables
        "columns": "*",  # All columns
        "operations": ["SELECT", "INSERT", "UPDATE", "DELETE"],
    },
    "readonly": {
        "tables": "*",  # All tables
        "columns": "*",  # All columns (masked PII)
        "operations": ["SELECT"],
    },
    "guest": {
        "tables": ["public_data"],
        "columns": ["id", "name", "created_at"],
        "operations": ["SELECT"],
    },
}

# Column-to-role masking rules
COLUMN_MASKING_RULES = {
    "ssn": {"admin": False, "readonly": True, "guest": True},  # True = needs masking
    "credit_card": {"admin": False, "readonly": True, "guest": True},
    "email": {"admin": False, "readonly": True, "guest": False},
    "phone": {"admin": False, "readonly": True, "guest": False},
}


async def check_rbac(request: Request):
    """
    Verify user's role has permission for the operation.
    This is checked after the query plans have been analyzed.
    """
    role = getattr(request.state, "role", "guest")

    if role not in ROLE_PERMISSIONS:
        logger.warning(f"Invalid role: {role}")
        raise HTTPException(status_code=403, detail="Invalid role")

    request.state.permissions = ROLE_PERMISSIONS[role]


def needs_column_masking(column_name: str, role: str) -> bool:
    """Check if a column needs PII masking for the given role."""
    if column_name not in COLUMN_MASKING_RULES:
        return False

    return COLUMN_MASKING_RULES[column_name].get(role, False)


def mask_pii_value(column_name: str, value: str) -> str:
    """Mask PII values based on column type."""
    if not value or not isinstance(value, str):
        return value

    if column_name == "ssn":
        # SSN: 123-45-6789 → ***-**-6789
        return f"***-**-{value[-4:]}" if len(value) >= 4 else "***"

    elif column_name == "credit_card":
        # CC: 4532123456789012 → ****-****-****-9012
        clean = value.replace("-", "").replace(" ", "")
        if len(clean) >= 4:
            return f"****-****-****-{clean[-4:]}"
        return "****"

    elif column_name == "email":
        # email: user@example.com → u***@example.com
        parts = value.split("@")
        if len(parts) == 2:
            user, domain = parts
            masked_user = user[0] + "***" if len(user) > 1 else "***"
            return f"{masked_user}@{domain}"
        return "***"

    elif column_name == "phone":
        # phone: 1234567890 → ****67890
        if len(value) >= 4:
            return "*" * (len(value) - 4) + value[-4:]
        return "****"

    return value
