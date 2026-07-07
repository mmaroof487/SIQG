from fastapi import APIRouter, Request, Depends, HTTPException
from middleware.observability.metrics import get_live_metrics
from middleware.security.auth import get_current_user

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

def require_admin(user=Depends(get_current_user)):
    """Check that user is admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@router.get("/live")
async def live_metrics(request: Request, user=Depends(require_admin)):
    """Live metrics — admin only. Returns request counts, latency, cache hit rates, error rates."""
    return await get_live_metrics(request.app.state.redis)
