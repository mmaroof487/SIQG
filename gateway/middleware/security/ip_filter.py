"""IP allow/blocklist middleware."""
from fastapi import HTTPException, Request
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


async def check_ip_filter(request: Request):
    """
    Check if request IP is in allow/blocklist.
    - If blocklist contains IP, always reject (403)
    - If allowlist is defined and IP not in it, reject (403)
    """
    redis = request.app.state.redis
    client_ip = request.client.host if request.client else "unknown"
    
    # Check blocklist first
    is_blocked = await redis.sismember("ip:blocklist", client_ip)
    if is_blocked:
        logger.warning(f"Blocked IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Your IP is blocked")
    
    # Check allowlist (if set)
    allowlist_exists = await redis.exists("ip:allowlist")
    if allowlist_exists:
        is_allowed = await redis.sismember("ip:allowlist", client_ip)
        if not is_allowed:
            logger.warning(f"IP not in allowlist: {client_ip}")
            raise HTTPException(status_code=403, detail="Your IP is not in the allowlist")
