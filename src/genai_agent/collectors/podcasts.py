from __future__ import annotations

import logging
import re
from typing import Dict, List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

DEFAULT_PODCAST_FEEDS: Dict[str, str] = {
    "Latent Space (AI Engineer Podcast)": "https://api.substack.com/feed/podcast/1084089.rss",
    "The TWIML AI Podcast": "https://twimlai.com/feed",
    "Practical AI Podcast": "https://changelog.com/practicalai/feed",
    "No Priors: AI Podcast": "https://feeds.megaphone.fm/nopriors",
    "Lex Fridman Podcast": "https://lexfridman.com/feed/podcast/",
}


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(clean.split())


def _format_duration(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if ":" in raw:
        return raw
    if raw.isdigit():
        secs = int(raw)
        hours, rem = divmod(secs, 3600)
        mins = rem // 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    return raw


def fetch_ai_podcasts(
    feeds: Dict[str, str] | None = None,
    max_per_feed: int = 1,
) -> List[NewsItem]:
    """Fetch recent Generative AI podcast episodes from top AI engineering and research podcasts."""
    target_feeds = feeds or DEFAULT_PODCAST_FEEDS
    items: List[NewsItem] = []

    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for show_name, feed_url in target_feeds.items():
            try:
                resp = client.get(feed_url)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries[:max_per_feed]:
                    title = (entry.get("title") or "").strip()
                    link = (entry.get("link") or "").strip()
                    if not link and entry.get("enclosures"):
                        link = entry.enclosures[0].get("href", "")
                    raw_summary = entry.get("summary") or entry.get("description") or ""
                    summary = _strip_html(raw_summary)[:420]
                    published = (
                        entry.get("published")
                        or entry.get("updated")
                        or ""
                    )[:16]
                    duration = _format_duration(entry.get("itunes_duration", ""))
                    if duration:
                        summary = f"🎧 {duration} — {summary}"

                    if not title or not link:
                        continue

                    items.append(
                        NewsItem(
                            title=title,
                            url=link,
                            source=show_name,
                            category=SourceCategory.PODCAST,
                            summary=summary,
                            published_at=published,
                            tags=["podcast", "audio"],
                        )
                    )
            except Exception as exc:
                logger.warning("Failed to fetch podcast feed %s: %s", show_name, exc)

    return items
