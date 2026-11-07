from __future__ import annotations

import logging
import urllib.parse
from typing import List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"


def fetch_google_news_rss(
    topics: List[str] | None = None,
    days: int = 2,
    limit: int = 8,
) -> List[NewsItem]:
    """Fetch recent Generative AI articles via Google News RSS search query."""
    if not topics:
        topics = ["Generative AI", "Large Language Models", "Anthropic Claude", "Google Gemini", "OpenAI"]

    query = "(" + " OR ".join(f'"{t}"' for t in topics[:4]) + f") when:{max(days, 1)}d"
    encoded_q = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"

    items: List[NewsItem] = []
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

        for entry in feed.entries[:limit]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            published = (entry.get("published") or "")[:16]
            source_obj = entry.get("source")
            source_title = (
                source_obj.get("title")
                if isinstance(source_obj, dict) and source_obj.get("title")
                else "Google News (Web)"
            )

            if not title or not link:
                continue

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    source=f"Web Search ({source_title})",
                    category=SourceCategory.WEB_SEARCH,
                    summary=f"Recent web news coverage via {source_title}.",
                    published_at=published,
                    tags=["web-search", "news"],
                )
            )
    except Exception as exc:
        logger.warning("Failed to fetch Google News RSS: %s", exc)

    return items
