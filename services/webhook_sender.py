from typing import Any

import aiohttp

from utils.logger import setup_logger

logger = setup_logger(__name__)


async def send_to_webhook(payload: dict[str, Any], webhook_url: str) -> bool:
    timeout = aiohttp.ClientTimeout(total=10)

    if not webhook_url.strip():
        logger.error("Webhook URL is empty")
        return False

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(webhook_url, json=payload) as response:
                if 200 <= response.status < 300:
                    logger.info("Payload sent successfully to webhook")
                    return True

                response_text = await response.text()
                logger.error(
                    "Webhook returned non-success status=%s body=%s",
                    response.status,
                    response_text,
                )
                return False
    except aiohttp.ClientError as exc:
        logger.exception("Webhook request failed: %s", exc)
        return False
