import httpx
from config import settings
from datetime import datetime
from utils.logger import get_logger

logger = get_logger(__name__)

async def send_alert(event_type: str, trace_id: str, user_id: str, message: str, extra: dict = None):
    if not settings.webhook_url:
        return

    payload = {
        "embeds": [{
            "title": f"Argus Alert: {event_type}",
            "description": message,
            "color": _color_for_event(event_type),
            "fields": [
                {"name": "Trace ID", "value": trace_id, "inline": True},
                {"name": "User", "value": str(user_id), "inline": True},
                {"name": "Time", "value": datetime.utcnow().isoformat(), "inline": True},
            ] + ([{"name": k, "value": str(v), "inline": True} for k, v in extra.items()] if extra else []),
        }]
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(settings.webhook_url, json=payload, timeout=5)
    except Exception as e:
        logger.warning(f"Failed to send webhook alert: {e}")
        pass   # Alerts should never crash the main flow

def _color_for_event(event_type: str) -> int:
    colors = {
        "slow_query": 0xFFA500,    # orange
        "anomaly": 0xFF0000,       # red
        "honeypot_hit": 0x8B0000,  # dark red
        "rate_limit": 0xFFFF00,    # yellow
        "circuit_open": 0xFF4500,  # red-orange
    }
    return colors.get(event_type, 0x808080)
