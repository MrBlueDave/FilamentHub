"""Home Assistant Webhook integration service."""

import datetime
import logging
from typing import Any, Dict
import httpx

from app.config import HA_WEBHOOK_URL

logger = logging.getLogger("filamenthub.webhooks")


async def send_ha_webhook(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Sends an asynchronous webhook notification to Home Assistant.
    Non-blocking: failures or timeouts are caught and logged as warnings,
    ensuring that client requests never fail due to Home Assistant reachability issues.
    """
    webhook_url = (HA_WEBHOOK_URL or "").strip()
    if not webhook_url or webhook_url.lower() in ("none", "false", ""):
        return

    # Check for unconfigured dummy placeholders
    if "la_tua_webhook_url" in webhook_url:
        return

    body = {
        "event": event_type,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "data": payload
    }

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_url, json=body)
            if response.status_code >= 400:
                logger.warning(
                    f"Home Assistant webhook responded with HTTP {response.status_code} "
                    f"for event '{event_type}': {response.text[:200]}"
                )
            else:
                logger.debug(f"Home Assistant webhook delivered successfully for event '{event_type}'")
    except httpx.TimeoutException:
        logger.warning(f"Timeout sending Home Assistant webhook for event '{event_type}' (URL: {webhook_url})")
    except Exception as exc:
        logger.warning(f"Failed to send Home Assistant webhook for event '{event_type}': {exc}")
