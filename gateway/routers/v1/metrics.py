from fastapi import APIRouter, Request
from middleware.observability.metrics import get_live_metrics

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("/live")
async def live_metrics(request: Request):
    return await get_live_metrics(request.app.state.redis)
