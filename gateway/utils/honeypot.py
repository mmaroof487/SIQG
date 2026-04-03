"""
Honeypot detection and intrusion blocking module.
Detects suspicious table access patterns and auto-blocks attacking IPs.
"""

from fastapi import HTTPException
from starlette.requests import Request
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

HONEYPOT_BLOCK_DURATION_HOURS = 24


async def check_honeypot(request: Request, query: str):
    """
    Check if query targets honeypot table.
    Raises 403 Forbidden if detected.
    Uses config-driven table list from settings.honeypot_tables.
    """
    try:
        # Case-insensitive check against config-driven honeypot table list
        query_upper = query.upper()
        honeypot_tables = settings.honeypot_tables_list

        for honeypot_table in honeypot_tables:
            if honeypot_table.upper() in query_upper:
                # Get client IP
                client_ip = request.client.host if request.client else "unknown"

                logger.warning(
                    f"🚨 Honeypot detection: Table '{honeypot_table}' accessed from {client_ip}"
                )

                # Async IP ban via Redis blocklist with 24-hour expiration
                try:
                    redis = request.app.state.redis
                    block_duration_seconds = HONEYPOT_BLOCK_DURATION_HOURS * 3600
                    # Use setex for individual IP keys with TTL instead of persistent set
                    await redis.setex(f"argus:ip:blocklist:{client_ip}", block_duration_seconds, "1")
                    logger.warning(f"🔒 IP {client_ip} added to blocklist for {HONEYPOT_BLOCK_DURATION_HOURS} hours (honeypot triggered)")
                except Exception as ban_err:
                    logger.warning(f"IP ban failed (non-critical): {ban_err}")

                raise HTTPException(
                    status_code=403,
                    detail="Access to this resource is forbidden"
                )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Honeypot check error: {e}")
        # Fail open on error - don't block legitimate requests
        return
