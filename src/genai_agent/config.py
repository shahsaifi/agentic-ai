from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv


def _parse_bool(val: Optional[str], default: bool = False) -> bool:
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class AgentConfig:
    """Configuration for the Generative AI News & Learning Agent."""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Learning & Collection settings
    focus_topics: List[str] = field(
        default_factory=lambda: [
            "LLMs",
            "AI Agents",
            "RAG",
            "Multimodal AI",
            "Reasoning Models",
            "Post-Training & RLHF",
            "Inference Optimization",
        ]
    )
    lookback_days: int = 2
    max_items_per_source: int = 10
    digest_output_dir: Path = field(default_factory=lambda: Path("digests"))

    # Telegram settings
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email settings
    email_enabled: bool = False
    email_provider: str = "smtp"  # "smtp" or "resend"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""
    resend_api_key: str = ""

    # Publishing, Newsletter & Google AdSense settings (jabi.io)
    site_domain: str = "jabi.io"
    google_adsense_client_id: str = ""
    google_adsense_slot_id: str = ""
    newsletter_form_action: str = ""

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> AgentConfig:
        """Load configuration from .env file and environment variables."""
        if env_file:
            load_dotenv(env_file, override=False)
        else:
            load_dotenv(override=False)

        raw_topics = os.getenv(
            "LEARNING_FOCUS_TOPICS",
            "LLMs, AI Agents, RAG, Multimodal AI, Reasoning Models, Post-Training & RLHF, Inference Optimization",
        )
        focus_topics = [t.strip() for t in raw_topics.split(",") if t.strip()]

        gemini_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
            or ""
        ).strip()

        return cls(
            gemini_api_key=gemini_key,
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
            focus_topics=focus_topics,
            lookback_days=int(os.getenv("LOOKBACK_DAYS", "2")),
            max_items_per_source=int(os.getenv("MAX_ITEMS_PER_SOURCE", "10")),
            digest_output_dir=Path(os.getenv("DIGEST_OUTPUT_DIR", "digests")),
            telegram_enabled=_parse_bool(os.getenv("TELEGRAM_ENABLED"), False),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
            email_enabled=_parse_bool(os.getenv("EMAIL_ENABLED"), False),
            email_provider=os.getenv("EMAIL_PROVIDER", "smtp").strip().lower(),
            smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
            email_from=os.getenv("EMAIL_FROM", "").strip(),
            email_to=os.getenv("EMAIL_TO", "").strip(),
            resend_api_key=os.getenv("RESEND_API_KEY", "").strip(),
            site_domain=os.getenv("SITE_DOMAIN", "jabi.io").strip() or "jabi.io",
            google_adsense_client_id=os.getenv("GOOGLE_ADSENSE_CLIENT_ID", "").strip(),
            google_adsense_slot_id=os.getenv("GOOGLE_ADSENSE_SLOT_ID", "").strip(),
            newsletter_form_action=os.getenv("NEWSLETTER_FORM_ACTION", "").strip(),
        )
