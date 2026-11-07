from __future__ import annotations

import logging
import re
import time
from typing import List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

# Reddit requires a descriptive User-Agent header in `<platform>:<app ID>:<version>` format
REDDIT_USER_AGENT = "macOS:genai-learning-agent:v0.1.0 (educational AI news digest)"
DEFAULT_USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"


def _strip_html(text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", text or "")
    return " ".join(clean.split())


def fetch_hacker_news_ai(days: int = 2, limit: int = 8) -> List[NewsItem]:
    """Fetch top recent Generative AI discussions and links from Hacker News via Algolia."""
    url = "https://hn.algolia.com/api/v1/search_by_date"
    queries = ["LLM", "AI", "Claude", "Gemini", "OpenAI"]
    seen_ids = set()
    all_hits = []

    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": DEFAULT_USER_AGENT}, follow_redirects=True) as client:
            for q in queries:
                params = {
                    "query": q,
                    "tags": "story",
                    "numericFilters": "points>20",
                    "hitsPerPage": str(max(limit, 6)),
                }
                resp = client.get(url, params=params)
                resp.raise_for_status()
                for hit in resp.json().get("hits", []):
                    oid = hit.get("objectID")
                    if oid and oid not in seen_ids:
                        seen_ids.add(oid)
                        all_hits.append(hit)
    except Exception as exc:
        logger.warning("Failed to fetch Hacker News AI stories: %s", exc)

    hits_sorted = sorted(all_hits, key=lambda h: h.get("points", 0) or 0, reverse=True)
    items: List[NewsItem] = []

    for hit in hits_sorted[:limit]:
        title = (hit.get("title") or "").strip()
        object_id = hit.get("objectID", "")
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
        story_url = hit.get("url") or hn_url
        points = hit.get("points", 0)
        num_comments = hit.get("num_comments", 0)
        created_at = (hit.get("created_at") or "")[:10]

        if not title:
            continue

        summary = f"Hacker News discussion ({points} points, {num_comments} comments). Discussion: {hn_url}"
        if hit.get("story_text"):
            summary += " | " + _strip_html(hit["story_text"])[:400]

        items.append(
            NewsItem(
                title=title,
                url=story_url,
                source="Hacker News",
                category=SourceCategory.COMMUNITY_NEWS,
                summary=summary,
                published_at=created_at,
                score=points,
                tags=["hackernews", "community"],
            )
        )

    return items


def fetch_reddit_ai(
    subreddits: List[str] | None = None,
    limit_per_sub: int = 5,
) -> List[NewsItem]:
    """Fetch top recent posts from AI subreddits (r/LocalLLaMA, r/MachineLearning)."""
    if not subreddits:
        subreddits = ["LocalLLaMA", "MachineLearning"]

    items: List[NewsItem] = []
    with httpx.Client(timeout=12.0, headers={"User-Agent": REDDIT_USER_AGENT}, follow_redirects=True) as client:
        for sub in subreddits:
            json_url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit_per_sub + 4}"
            sub_items: List[NewsItem] = []
            try:
                resp = client.get(json_url)
                resp.raise_for_status()
                children = resp.json().get("data", {}).get("children", [])

                for child in children:
                    post = child.get("data", {})
                    if post.get("stickied"):
                        continue
                    title = (post.get("title") or "").strip()
                    permalink = f"https://www.reddit.com{post.get('permalink', '')}"
                    selftext = _strip_html(post.get("selftext") or "")
                    score = post.get("score", 0)
                    created_utc = post.get("created_utc")
                    pub_date = (
                        time.strftime("%Y-%m-%d", time.gmtime(created_utc))
                        if created_utc
                        else None
                    )
                    if not title:
                        continue

                    sub_items.append(
                        NewsItem(
                            title=title,
                            url=permalink,
                            source=f"Reddit r/{sub}",
                            category=SourceCategory.COMMUNITY_NEWS,
                            summary=selftext[:500] if selftext else f"Discussion on r/{sub} ({score} upvotes).",
                            published_at=pub_date,
                            score=score,
                            tags=["reddit", f"r/{sub}"],
                        )
                    )
                    if len(sub_items) >= limit_per_sub:
                        break
            except Exception as exc:
                logger.debug("Reddit JSON fallback to RSS for r/%s (%s)", sub, exc)
                try:
                    rss_url = f"https://www.reddit.com/r/{sub}/hot/.rss"
                    resp = client.get(rss_url)
                    resp.raise_for_status()
                    feed = feedparser.parse(resp.text)
                    for entry in feed.entries[:limit_per_sub]:
                        title = (entry.get("title") or "").strip()
                        link = entry.get("link") or ""
                        summary = _strip_html(entry.get("summary") or "")
                        published = (entry.get("updated") or entry.get("published") or "")[:10]
                        if title and link:
                            sub_items.append(
                                NewsItem(
                                    title=title,
                                    url=link,
                                    source=f"Reddit r/{sub}",
                                    category=SourceCategory.COMMUNITY_NEWS,
                                    summary=summary[:500],
                                    published_at=published,
                                    tags=["reddit", f"r/{sub}"],
                                )
                            )
                except Exception as rss_exc:
                    logger.debug("Skipped Reddit r/%s: %s", sub, rss_exc)

            items.extend(sub_items)

    return items
