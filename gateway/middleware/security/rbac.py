"""RBAC (Role-Based Access Control) middleware."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger
import re

logger = get_logger(__name__)

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
    Loads role permissions from configuration (not hardcoded).
    """
    role = getattr(request.state, "role", "guest")
    role_permissions = settings.rbac_roles

    if role not in role_permissions:
        logger.warning(f"Invalid role: {role}")
        raise HTTPException(status_code=403, detail="Invalid role")

    request.state.permissions = role_permissions[role]


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
        # phone: 9876543210 -> 98******10
        if len(value) >= 4:
            stars = "*" * max(len(value) - 4, 2)
            return f"{value[:2]}{stars}{value[-2:]}"
        return "**"

    return value


def blind_dlp_masking(value: str) -> str:
    """
    Apply blind regex Data Loss Prevention (DLP) mask over any string, 
    preventing PII bypass via SQL column aliasing.
    """
    if not value or not isinstance(value, str):
        return value

    # Mask SSN: 123-45-6789 -> ***-**-****
    value = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****', value)
    
    # Mask Email (basic): user@example.com -> ***@***.***
    value = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', '***@***.***', value)
    
    # Mask Credit Cards (13-16 digits with optional spaces/dashes)
    value = re.sub(r'\b(?:\d[ -]*?){13,16}\b', '****-****-****-****', value)
    
    return value


def apply_rbac_masking(role: str, rows: list) -> list:
    """
    Apply PII masking to result rows based on user role.

    Args:
        role: User role (admin, readonly, guest)
        rows: List of result row dicts

    Returns:
        Masked result rows
    """
    if role == "admin":
        # Admin sees all data unmasked
        return rows

    masked_rows = []
    for row in rows:
        masked_row = {}
        for column_name, value in row.items():
            if needs_column_masking(column_name, role):
                # Strict known column masking
                masked_row[column_name] = mask_pii_value(column_name, value)
            else:
                # Catch-all alias bypass protection (blind DLP)
                masked_row[column_name] = blind_dlp_masking(value) if isinstance(value, str) else value
        masked_rows.append(masked_row)

    logger.debug(f"Applied PII masking for role '{role}'")
    return masked_rows
