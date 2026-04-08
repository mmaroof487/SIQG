"""RBAC (Role-Based Access Control) middleware."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger
import re

logger = get_logger(__name__)

# Columns that should be completely denied (removed from result set) for specific roles
# Admin always sees all columns; other roles have denied columns stripped entirely
COLUMN_DENY_LIST = {
    "hashed_password": {"admin": False, "readonly": True, "guest": True},  # True = deny for this role
    "internal_notes": {"admin": False, "readonly": True, "guest": True},
}

# Column-to-role masking rules (partial redaction, not removal)
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


def is_column_denied(column_name: str, role: str) -> bool:
    """Check if a column is denied (completely removed) for the given role."""
    if column_name not in COLUMN_DENY_LIST:
        return False

    return COLUMN_DENY_LIST[column_name].get(role, False)


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
    Apply RBAC filtering to result rows based on user role:
    1. Remove denied columns entirely (hashed_password, internal_notes, etc.)
    2. Mask PII in allowed columns (email, phone, ssn, credit_card, etc.)
    3. Apply blind DLP regex protection to all string values

    Args:
        role: User role (admin, readonly, guest)
        rows: List of result row dicts

    Returns:
        Filtered and masked result rows
    """
    if role == "admin":
        # Admin sees all data unmasked and unfiltered
        return rows

    masked_rows = []
    for row in rows:
        masked_row = {}
        for column_name, value in row.items():
            # Step 1: Check if column is denied for this role – skip entirely if denied
            if is_column_denied(column_name, role):
                logger.debug(f"Denying column '{column_name}' for role '{role}'")
                continue  # Skip this column entirely

            # Step 2: Apply masking if column needs it
            if needs_column_masking(column_name, role):
                # Strict known column masking
                masked_row[column_name] = mask_pii_value(column_name, value)
            else:
                # Step 3: Catch-all alias bypass protection (blind DLP)
                masked_row[column_name] = blind_dlp_masking(value) if isinstance(value, str) else value

        masked_rows.append(masked_row)

    logger.debug(f"Applied RBAC filtering and PII masking for role '{role}'")
    return masked_rows


def strip_denied_columns(role: str, columns: list[str]) -> list[str]:
    """
    Filter out denied columns for the given role.
    Used to rewrite SELECT * into explicit allowed columns before execution.

    Args:
        role: User role (admin, readonly, guest)
        columns: All column names from the table schema

    Returns:
        List of columns the role is allowed to see
    """
    if role == "admin":
        return columns

    return [col for col in columns if not is_column_denied(col, role)]


async def check_time_based_access(request: Request):
    """
    Check if the user's role has time-based access restrictions.
    Raises HTTPException if access is not allowed at the current time.
    """
    from datetime import datetime
    import pytz

    role = getattr(request.state, "role", "guest")
    time_rules = settings.time_based_rbac

    # If no rules for this role, allow access
    if role not in time_rules:
        return

    rule = time_rules[role]
    allowed_hours = rule.get("allowed_hours")
    allowed_weekdays = rule.get("allowed_weekdays", [])
    timezone_str = rule.get("timezone", "UTC")

    # Parse timezone
    try:
        tz = pytz.timezone(timezone_str)
    except Exception:
        logger.warning(f"Invalid timezone: {timezone_str}, using UTC")
        tz = pytz.UTC

    # Get current time in the specified timezone
    now = datetime.now(tz)
    current_time = now.time()
    weekday_name = now.strftime("%A")

    # Check weekday restriction
    if allowed_weekdays and weekday_name not in allowed_weekdays:
        logger.warning(f"Access blocked for {role}: not an allowed weekday ({weekday_name})")
        blocked_until = "Monday 09:00"  # Generic message
        raise HTTPException(
            status_code=403,
            detail={
                "blocked": True,
                "block_reasons": [f"Access for {role} role is restricted. Allowed weekdays: {', '.join(allowed_weekdays)}"],
                "blocked_until": blocked_until,
                "current_time": now.isoformat(),
            }
        )

    # Check hour restriction (e.g. "09:00-17:00")
    if allowed_hours:
        try:
            start_str, end_str = allowed_hours.split("-")
            start_parts = start_str.strip().split(":")
            end_parts = end_str.strip().split(":")

            start_time = datetime.strptime(f"{start_parts[0]}:{start_parts[1]}", "%H:%M").time()
            end_time = datetime.strptime(f"{end_parts[0]}:{end_parts[1]}", "%H:%M").time()

            # Check if current time is within allowed hours
            if not (start_time <= current_time <end_time):
                logger.warning(f"Access blocked for {role}: outside allowed hours")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "blocked": True,
                        "block_reasons": [f"Access for {role} role is restricted to {allowed_hours} {timezone_str}"],
                        "allowed_hours": allowed_hours,
                        "current_time": now.isoformat(),
                    }
                )
        except ValueError as e:
            logger.warning(f"Invalid hour format in time-based RBAC: {e}")
            # If parsing fails, allow access (be permissive)
