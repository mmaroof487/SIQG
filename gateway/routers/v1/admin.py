"""Admin management router."""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Optional
from middleware.security.auth import get_current_user
from models import Role
from utils.logger import get_logger

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
logger = get_logger(__name__)


def require_admin(user=Depends(get_current_user)):
    """Check that user is admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


class IPRuleRequest(BaseModel):
    ip_address: str
    rule_type: str  # "allow" or "block"
    description: Optional[str] = None


@router.post("/ip-rules")
async def add_ip_rule(
    request: Request,
    payload: IPRuleRequest,
    admin=Depends(require_admin),
):
    """Add IP allow/blocklist rule."""
    if payload.rule_type not in ["allow", "block"]:
        raise HTTPException(status_code=400, detail="rule_type must be 'allow' or 'block'")

    redis = request.app.state.redis

    if payload.rule_type == "allow":
        await redis.sadd("ip:allowlist", payload.ip_address)
    else:
        await redis.sadd("ip:blocklist", payload.ip_address)

    logger.info(f"IP rule added: {payload.ip_address} {payload.rule_type}")

    return {"status": "ok", "message": f"IP {payload.ip_address} added to {payload.rule_type}list"}


@router.delete("/ip-rules/{ip_address}")
async def remove_ip_rule(
    request: Request,
    ip_address: str,
    admin=Depends(require_admin),
):
    """Remove IP rule from both lists."""
    redis = request.app.state.redis

    await redis.srem("ip:allowlist", ip_address)
    await redis.srem("ip:blocklist", ip_address)

    logger.info(f"IP rule removed: {ip_address}")

    return {"status": "ok", "message": f"IP {ip_address} removed from all lists"}


@router.get("/metrics/live")
async def get_metrics(request: Request, admin=Depends(require_admin)):
    """Get live metrics (stub for Phase 4)."""
    redis = request.app.state.redis

    return {
        "request_count": int(await redis.get("metric:request_count") or 0),
        "error_count": int(await redis.get("metric:error_count") or 0),
        "cache_hits": int(await redis.get("metric:cache_hits") or 0),
        "slow_queries": int(await redis.get("metric:slow_queries") or 0),
    }
