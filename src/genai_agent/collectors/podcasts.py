from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

# Featured Apple Podcasts + Engineering Podcasts
FEATURED_PODCAST_SHOWS: List[Dict[str, str]] = [
    {
        "name": "Generative AI 101",
        "host": "Emily Laird",
        "focus": "Foundational GenAI Concepts, Context Engineering & Model Evaluation",
        "feed_url": "https://feed.podbean.com/generativeai101/feed.xml",
        "apple_url": "https://podcasts.apple.com/sg/podcast/generative-ai-101/id1750985562",
    },
    {
        "name": "AI Optic: Anthropic & OpenAI News",
        "host": "Jaeden Schafer",
        "focus": "Breaking Frontier Lab Releases, AI Agents, Anthropic & OpenAI Strategy",
        "feed_url": "https://rss.art19.com/anthropic",
        "apple_url": "https://podcasts.apple.com/sg/podcast/ai-optic-anthropic-openai-news/id1725552927",
    },
    {
        "name": "AI Today Podcast",
        "host": "Kathleen Walch & Ronald Schmelzer",
        "focus": "AI Literacy, Enterprise AI Adoption & Real-World AI Leadership",
        "feed_url": "https://rss.buzzsprout.com/2502664.rss",
        "apple_url": "https://podcasts.apple.com/sg/podcast/ai-today-podcast/id1279927057",
    },
    {
        "name": "Latent Space (AI Engineer Podcast)",
        "host": "swyx & Alessio",
        "focus": "Deep Technical AI Engineering, Agents, Infra & Research",
        "feed_url": "https://api.substack.com/feed/podcast/1084089.rss",
        "apple_url": "https://podcasts.apple.com/us/podcast/latent-space-the-ai-engineer-podcast/id1674008350",
    },
    {
        "name": "The TWIML AI Podcast",
        "host": "Sam Charrington",
        "focus": "Academic ML Research & Frontier AI Interviews",
        "feed_url": "https://twimlai.com/feed",
        "apple_url": "https://podcasts.apple.com/us/podcast/the-twiml-ai-podcast-formerly-this-week-in-machine-learning/id1116303051",
    },
    {
        "name": "Practical AI Podcast",
        "host": "Chris Benson & Daniel Whitenack",
        "focus": "Making Artificial Intelligence Practical, Productive & Accessible",
        "feed_url": "https://changelog.com/practicalai/feed",
        "apple_url": "https://podcasts.apple.com/us/podcast/practical-ai-machine-learning-data-science-llm/id1406537385",
    },
]

DEFAULT_PODCAST_FEEDS: Dict[str, str] = {
    show["name"]: show["feed_url"] for show in FEATURED_PODCAST_SHOWS
}


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    # Remove boilerplate ad/sponsor footers if present
    clean = re.split(r"This episode is brought to you by|See Privacy Policy|Support the show", clean)[0]
    return " ".join(clean.split())


def _format_duration(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if ":" in raw:
        parts = [p for p in raw.split(":") if p.isdigit()]
        if len(parts) == 3:
            h, m, _ = int(parts[0]), int(parts[1]), int(parts[2])
            return f"{h}h {m}m" if h > 0 else f"{m}m"
        if len(parts) == 2:
            m, _ = int(parts[0]), int(parts[1])
            return f"{m}m"
        return raw
    if raw.isdigit():
        secs = int(raw)
        hours, rem = divmod(secs, 3600)
        mins = max(1, rem // 60)
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    return raw


def fetch_ai_podcasts(
    feeds: Dict[str, str] | None = None,
    max_per_feed: int = 1,
) -> List[NewsItem]:
    """Fetch recent Generative AI podcast episodes from top AI podcasts."""
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


def fetch_detailed_podcast_hub(episodes_per_show: int = 3) -> List[Dict[str, Any]]:
    """Fetch latest episodes with full summaries and Apple Podcast links for the dedicated Podcasts Hub page."""
    shows_data: List[Dict[str, Any]] = []

    with httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for show in FEATURED_PODCAST_SHOWS:
            episodes: List[Dict[str, str]] = []
            try:
                resp = client.get(show["feed_url"])
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                for entry in parsed.entries[:episodes_per_show]:
                    title = (entry.get("title") or "").strip()
                    enclosure_url = (
                        entry.enclosures[0].get("href", "")
                        if entry.get("enclosures")
                        else ""
                    )
                    link = (entry.get("link") or enclosure_url or show["apple_url"]).strip()
                    raw_summary = entry.get("summary") or entry.get("description") or ""
                    summary = _strip_html(raw_summary)[:520]
                    published = (entry.get("published") or entry.get("updated") or "")[:16]
                    duration = _format_duration(entry.get("itunes_duration", "")) or "Audio"

                    if title:
                        episodes.append(
                            {
                                "title": title,
                                "url": link,
                                "audio_url": enclosure_url or link,
                                "apple_url": show["apple_url"],
                                "summary": summary,
                                "published": published,
                                "duration": duration,
                            }
                        )
            except Exception as exc:
                logger.warning("Failed to fetch detailed podcast show %s: %s", show["name"], exc)

            if episodes:
                shows_data.append(
                    {
                        "name": show["name"],
                        "host": show["host"],
                        "focus": show["focus"],
                        "apple_url": show["apple_url"],
                        "episodes": episodes,
                    }
                )

    return shows_data
