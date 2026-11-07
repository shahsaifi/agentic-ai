from __future__ import annotations

import logging
from typing import List

import httpx

from genai_agent.config import AgentConfig

logger = logging.getLogger(__name__)


def chunk_text(text: str, max_chars: int = 3900) -> List[str]:
    """Split a long digest into chunks under `max_chars` along paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks: List[str] = []
    current_lines: List[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if len(line) > max_chars:
            # Force-split an oversized line
            if current_lines:
                chunks.append("".join(current_lines).strip())
                current_lines = []
                current_len = 0
            for i in range(0, len(line), max_chars):
                chunks.append(line[i : i + max_chars].strip())
            continue

        if current_len + len(line) > max_chars and current_lines:
            chunks.append("".join(current_lines).strip())
            current_lines = [line]
            current_len = len(line)
        else:
            current_lines.append(line)
            current_len += len(line)

    if current_lines:
        chunks.append("".join(current_lines).strip())

    return [c for c in chunks if c]


def send_telegram_digest(config: AgentConfig, markdown_content: str) -> bool:
    """Send the digest to Telegram via Bot API."""
    if not config.telegram_bot_token or not config.telegram_chat_id:
        logger.warning("Telegram bot token or chat ID missing; skipping Telegram notification.")
        return False

    api_url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    chunks = chunk_text(markdown_content, max_chars=3800)

    try:
        with httpx.Client(timeout=20.0) as client:
            for idx, chunk in enumerate(chunks, start=1):
                header = f"({idx}/{len(chunks)})\n" if len(chunks) > 1 else ""
                payload = {
                    "chat_id": config.telegram_chat_id,
                    "text": header + chunk,
                    "disable_web_page_preview": True,
                }
                resp = client.post(api_url, json=payload)
                resp.raise_for_status()
        return True
    except Exception as exc:
        logger.error("Failed to send Telegram notification: %s", exc)
        return False
