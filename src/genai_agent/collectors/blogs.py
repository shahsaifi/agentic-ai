from __future__ import annotations

import logging
import re
from typing import Dict, List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

DEFAULT_BLOG_FEEDS: Dict[str, str] = {
    "OpenAI News": "https://openai.com/news/rss.xml",
    "Google AI Blog": "https://blog.google/technology/ai/rss/",
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "Simon Willison (AI)": "https://simonwillison.net/tags/ai.atom",
    "Lilian Weng Blog": "https://lilianweng.github.io/index.xml",
    "LangChain Blog": "https://blog.langchain.dev/rss/",
}


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(clean.split())


def fetch_ai_company_blogs(
    feeds: Dict[str, str] | None = None,
    max_per_feed: int = 2,
) -> List[NewsItem]:
    """Fetch recent posts from official AI lab blogs and top AI engineering feeds."""
    target_feeds = feeds or DEFAULT_BLOG_FEEDS
    items: List[NewsItem] = []

    with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for source_name, feed_url in target_feeds.items():
            try:
                resp = client.get(feed_url)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries[:max_per_feed]:
                    title = (entry.get("title") or "").strip()
                    link = (entry.get("link") or "").strip()
                    raw_summary = entry.get("summary") or entry.get("description") or ""
                    summary = _strip_html(raw_summary)[:600]
                    published = (
                        entry.get("published")
                        or entry.get("updated")
                        or ""
                    )[:16]

                    if not title or not link:
                        continue

                    items.append(
                        NewsItem(
                            title=title,
                            url=link,
                            source=source_name,
                            category=SourceCategory.COMPANY_BLOG,
                            summary=summary,
                            published_at=published,
                            tags=["blog", source_name.lower().replace(" ", "-")],
                        )
                    )
            except Exception as exc:
                logger.warning("Failed to fetch blog feed %s (%s): %s", source_name, feed_url, exc)

    return items
