from __future__ import annotations

import logging
import re
import urllib.parse
from typing import List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

AI_KEYWORDS = re.compile(
    r"\b(ai|llm|gpt|claude|gemini|openai|anthropic|deepmind|qwen|llama|deepseek|agent|agentic|model|neural|gpu|nvidia|transformer|reasoning|coding|karpathy|rag)\b",
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(clean.split())


def fetch_hn_x_threads(limit: int = 5) -> List[NewsItem]:
    """Fetch top-upvoted X.com / Twitter threads and discussions about AI from Hacker News."""
    url = "https://hn.algolia.com/api/v1/search_by_date"
    queries = ["x.com", "twitter.com"]
    seen_ids = set()
    hits = []

    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            for q in queries:
                params = {
                    "query": q,
                    "tags": "story",
                    "numericFilters": "points>5",
                    "hitsPerPage": "40",
                }
                resp = client.get(url, params=params)
                resp.raise_for_status()
                for hit in resp.json().get("hits", []):
                    oid = hit.get("objectID")
                    title = hit.get("title") or ""
                    story_url = hit.get("url") or ""
                    if (
                        oid
                        and oid not in seen_ids
                        and ("x.com/" in story_url or "twitter.com/" in story_url or "x.com" in title.lower())
                        and AI_KEYWORDS.search(f"{title} {story_url}")
                    ):
                        seen_ids.add(oid)
                        hits.append(hit)
    except Exception as exc:
        logger.warning("Failed to fetch HN X.com threads: %s", exc)

    hits.sort(key=lambda h: h.get("points", 0) or 0, reverse=True)
    items: List[NewsItem] = []

    for hit in hits[:limit]:
        title = (hit.get("title") or "").strip()
        object_id = hit.get("objectID", "")
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
        story_url = hit.get("url") or hn_url
        points = hit.get("points", 0)
        comments = hit.get("num_comments", 0)
        created_at = (hit.get("created_at") or "")[:10]

        items.append(
            NewsItem(
                title=title,
                url=story_url,
                source="X.com (via Hacker News)",
                category=SourceCategory.SOCIAL_X,
                summary=f"Viral X thread discussed on Hacker News ({points} pts, {comments} comments). HN Thread: {hn_url}",
                published_at=created_at,
                score=points,
                tags=["x.com", "twitter", "viral-thread"],
            )
        )

    return items


def fetch_ainews_twitter_recap(limit: int = 2) -> List[NewsItem]:
    """Fetch daily AI Twitter/X Recap issues from AINews (news.smol.ai by swyx)."""
    url = "https://news.smol.ai/rss.xml"
    items: List[NewsItem] = []

    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            if not title or "not much happened" in title.lower():
                continue
            link = (entry.get("link") or "").strip()
            raw_desc = entry.get("description") or entry.get("summary") or ""
            summary = _strip_html(raw_desc)[:450]
            published = (entry.get("published") or "")[:16]

            items.append(
                NewsItem(
                    title=f"AI Twitter/X Daily Recap: {title}",
                    url=link,
                    source="AINews (AI X/Twitter Recap)",
                    category=SourceCategory.SOCIAL_X,
                    summary=summary or "Curated recap of the top threads from 500+ AI researchers and engineers on X.com.",
                    published_at=published,
                    tags=["x.com", "ainews", "twitter-recap"],
                )
            )
            if len(items) >= limit:
                break
    except Exception as exc:
        logger.warning("Failed to fetch AINews Twitter recap: %s", exc)

    return items


def fetch_google_news_x_discussions(days: int = 3, limit: int = 4) -> List[NewsItem]:
    """Fetch breaking AI discussions originating on X.com via Google News search."""
    query = '("on X" OR "x.com") AND ("OpenAI" OR "Anthropic" OR "DeepMind" OR "Gemini" OR "Claude" OR "AI agent") when:' + f"{max(days, 2)}d"
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
                else "X / Social Media"
            )
            if not title or not link:
                continue

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    source=f"X Pulse ({source_title})",
                    category=SourceCategory.SOCIAL_X,
                    summary=f"Trending AI discussion on X covered by {source_title}.",
                    published_at=published,
                    tags=["x.com", "social-pulse"],
                )
            )
    except Exception as exc:
        logger.warning("Failed to fetch Google News X discussions: %s", exc)

    return items


def fetch_x_social_pulse(days: int = 3, limit: int = 6) -> List[NewsItem]:
    """Combine viral X/Twitter AI threads from Hacker News, AINews Twitter Recap, and Web coverage."""
    items: List[NewsItem] = []
    items.extend(fetch_hn_x_threads(limit=max(3, limit // 2)))
    items.extend(fetch_ainews_twitter_recap(limit=2))
    items.extend(fetch_google_news_x_discussions(days=days, limit=3))
    return items[:limit]
