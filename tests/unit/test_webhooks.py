"""Unit tests for webhook alerting."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
@patch("middleware.observability.webhooks.settings")
async def test_send_alert_skips_when_no_url(mock_settings):
    """Alert should be a no-op when webhook_url is empty."""
    mock_settings.webhook_url = ""

    from middleware.observability.webhooks import send_alert

    # Should not raise and should not attempt any HTTP call
    await send_alert("slow_query", "trace-1", "user-1", "test message")


@pytest.mark.asyncio
@patch("middleware.observability.webhooks.httpx.AsyncClient")
@patch("middleware.observability.webhooks.settings")
async def test_send_alert_posts_to_webhook(mock_settings, mock_client_cls):
    """Alert should POST to webhook URL with Discord embed format."""
    mock_settings.webhook_url = "https://discord.com/api/webhooks/test"
    mock_client = AsyncMock()
    # Properly mock async context manager (__aenter__ and __aexit__)
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)
    # Ensure post is awaitable
    mock_client.post = AsyncMock(return_value=None)

    from middleware.observability.webhooks import send_alert

    await send_alert("slow_query", "trace-1", "user-1", "Query slow")

    # Verify post was awaited
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert "embeds" in payload
    assert payload["embeds"][0]["title"] == "Argus Alert: slow_query"


@pytest.mark.asyncio
@patch("middleware.observability.webhooks.httpx.AsyncClient")
@patch("middleware.observability.webhooks.settings")
async def test_send_alert_does_not_crash_on_failure(mock_settings, mock_client_cls):
    """Webhook failure should be silently caught — never crash the main flow."""
    mock_settings.webhook_url = "https://discord.com/api/webhooks/test"
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("Network error"))
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

    from middleware.observability.webhooks import send_alert

    # Should not raise even though post fails
    await send_alert("circuit_open", "trace-2", "user-2", "DB down")


def test_color_for_event():
    """Event types should map to correct Discord embed colors."""
    from middleware.observability.webhooks import _color_for_event

    assert _color_for_event("slow_query") == 0xFFA500
    assert _color_for_event("anomaly") == 0xFF0000
    assert _color_for_event("honeypot_hit") == 0x8B0000
    assert _color_for_event("unknown") == 0x808080
