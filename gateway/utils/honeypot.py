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
        from middleware.performance.fingerprinter import extract_tables_from_query
        accessed_tables = extract_tables_from_query(query)
        honeypot_tables = [t.strip().lower() for t in settings.honeypot_tables_list]

        for honeypot_table in honeypot_tables:
            if honeypot_table in accessed_tables:
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
        # Fail closed on error to prevent bypassing security controls
        raise HTTPException(
            status_code=500,
            detail="Security verification failed"
        )
