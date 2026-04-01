"""
Honeypot detection and intrusion blocking module.
Detects suspicious table access patterns and auto-blocks attacking IPs.
"""

from fastapi import HTTPException
from starlette.requests import Request
from utils.logger import get_logger

logger = get_logger(__name__)

# Configurable honeypot tables
HONEYPOT_TABLES = ["secret_keys", "admin_passwords", "encryption_keys"]
HONEYPOT_BLOCK_DURATION_HOURS = 24


async def check_honeypot(request: Request, query: str):
    """
    Check if query targets honeypot table.
    Raises 403 Forbidden if detected.
    Currently simple implementation - IP blocking can be added later.
    """
    try:
        # Case-insensitive check
        query_upper = query.upper()

        for honeypot_table in HONEYPOT_TABLES:
            if honeypot_table.upper() in query_upper:
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"

                logger.warning(
                    f"🚨 Honeypot detection: Table '{honeypot_table}' accessed from {client_ip}"
                )

                raise HTTPException(
                    status_code=403,
                    detail=f"Access to this resource is forbidden"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Honeypot check error: {e}")
        # Fail open on error - don't block legitimate requests
        return
