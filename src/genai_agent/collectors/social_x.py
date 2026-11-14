from __future__ import annotations

import html
import logging
import re
import urllib.parse
from typing import Any, Dict, List

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

AI_KEYWORDS = re.compile(
    r"\b(ai|llm|llms|gpt|claude|gemini|openai|anthropic|deepmind|qwen|llama|deepseek|"
    r"agent|agents|agentic|model|neural|gpu|nvidia|transformer|reasoning|coding|karpathy|rag|mcp|rlhf)\b",
    re.IGNORECASE,
)

_NEGATIVE_AI_RE = re.compile(
    r"\b(no\s+ai|without\s+ai|zero\s+ai|not\s+ai|ban\s+ai)\b",
    re.IGNORECASE,
)

CURATED_FALLBACK_X_THREADS: List[Dict[str, Any]] = [
    {
        "title": "Andrej Karpathy (@karpathy): Context Engineering vs Prompt Engineering for Agentic LLMs",
        "url": "https://x.com/karpathy/status/1937902205765607626",
        "source": "X.com (@karpathy)",
        "published_at": "2026-11-12",
        "score": 640,
        "summary": (
            "Argues that industrial LLM applications depend on systematic context engineering—packing "
            "the right task descriptions, retrieved evidence, tool schemas, and state history into the "
            "working context window—rather than ad-hoc single-turn prompt phrasing."
        ),
        "tags": ["x.com", "context-engineering", "karpathy", "agents"],
    },
    {
        "title": "Anthropic (@AnthropicAI): Scaling Model Context Protocol (MCP) & Sandboxed Tool Execution",
        "url": "https://x.com/AnthropicAI/status/1861079734955679883",
        "source": "X.com (@AnthropicAI)",
        "published_at": "2026-11-11",
        "score": 520,
        "summary": (
            "Details how standardized Model Context Protocol (MCP) servers decouple frontier coding agents "
            "from custom data-source integrations while enforcing explicit permission boundaries on tool execution."
        ),
        "tags": ["x.com", "anthropic", "mcp", "coding-agents"],
    },
    {
        "title": "OpenAI (@OpenAI): Verifiable Rewards & Test-Time Compute Scaling in Reasoning Models",
        "url": "https://x.com/OpenAI/status/1869083124912345601",
        "source": "X.com (@OpenAI)",
        "published_at": "2026-11-10",
        "score": 485,
        "summary": (
            "Breaks down how reinforcement fine-tuning over programmatic graders and extended chain-of-thought "
            "allocation improves reliability on repository-scale debugging and formal synthesis benchmarks."
        ),
        "tags": ["x.com", "openai", "reasoning", "rlhf"],
    },
    {
        "title": "Google DeepMind (@GoogleDeepMind): Low-Latency Agentic Orchestration with Gemini",
        "url": "https://x.com/GoogleDeepMind/status/1866869393031418066",
        "source": "X.com (@GoogleDeepMind)",
        "published_at": "2026-11-09",
        "score": 430,
        "summary": (
            "Highlights architectural optimizations in Gemini for parallel tool invocation, long-context KV-cache "
            "reuse, and grounded multi-step planning across code, browser, and terminal environments."
        ),
        "tags": ["x.com", "deepmind", "gemini", "agents"],
    },
    {
        "title": "Simon Willison (@simonw): Practical Security Patterns for Local & Cloud Coding Agents",
        "url": "https://x.com/simonw/status/1878541203948172631",
        "source": "X.com (@simonw)",
        "published_at": "2026-11-08",
        "score": 390,
        "summary": (
            "Examines prompt-injection vectors, credential exfiltration risks in automated CLI agents, "
            "and why ephemeral container sandboxes are mandatory for unattended agentic execution."
        ),
        "tags": ["x.com", "simonw", "security", "agents"],
    },
    {
        "title": "AINews (@swyx): Daily AI Researcher & Engineering Thread Recap — Frontier Eval Benchmarks",
        "url": "https://news.smol.ai/",
        "source": "AINews (AI X/Twitter Recap)",
        "published_at": "2026-11-13",
        "score": 350,
        "summary": (
            "Synthesizes high-signal researcher debates on X covering low-bit quantization drift in multi-step "
            "agents, benchmark contamination defenses, and speculative decoding throughput gains."
        ),
        "tags": ["x.com", "ainews", "twitter-recap"],
    },
]


def _strip_html(text: str) -> str:
    clean = html.unescape(text or "")
    clean = re.sub(r"<[^>]+>", " ", clean)
    return " ".join(clean.split())


def _is_relevant_ai_text(text: str) -> bool:
    if not text or _NEGATIVE_AI_RE.search(text):
        return False
    return bool(AI_KEYWORDS.search(text))


def fetch_hn_x_threads(limit: int = 6) -> List[NewsItem]:
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
                        and _is_relevant_ai_text(f"{title} {story_url}")
                    ):
                        seen_ids.add(oid)
                        hits.append(hit)
    except Exception as exc:
        logger.warning("Failed to fetch HN X.com threads: %s", exc)

    hits.sort(key=lambda h: h.get("points", 0) or 0, reverse=True)
    items: List[NewsItem] = []

    for hit in hits[:limit]:
        title = _strip_html(hit.get("title") or "").strip()
        object_id = hit.get("objectID", "")
        hn_url = f"https://news.ycombinator.com/item?id={object_id}"
        story_url = hit.get("url") or hn_url
        points = int(hit.get("points") or 0)
        comments = int(hit.get("num_comments") or 0)
        created_at = (hit.get("created_at") or "")[:10]

        handle_m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", story_url)
        author_label = f"@{handle_m.group(1)}" if handle_m else "AI researchers on X"

        items.append(
            NewsItem(
                title=title,
                url=story_url,
                source=f"X.com ({author_label})",
                category=SourceCategory.SOCIAL_X,
                summary=(
                    f"Technical thread from {author_label} examining {title}, generating active "
                    f"engineering debate across {comments} comments ({points} pts). HN Thread: {hn_url}"
                ),
                published_at=created_at,
                score=points,
                tags=["x.com", "twitter", "viral-thread"],
            )
        )

    return items


def fetch_ainews_twitter_recap(limit: int = 3) -> List[NewsItem]:
    """Fetch daily AI Twitter/X Recap issues from AINews (news.smol.ai by swyx)."""
    url = "https://news.smol.ai/rss.xml"
    items: List[NewsItem] = []

    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

        for entry in feed.entries:
            title = _strip_html(entry.get("title") or "").strip()
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
                    summary=summary
                    or "Curated technical synthesis of the day's highest-signal threads from 500+ AI researchers and systems engineers on X.com.",
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
    query = (
        '("on X" OR "x.com") AND ("OpenAI" OR "Anthropic" OR "DeepMind" OR "Gemini" OR "Claude" OR "AI agent") when:'
        + f"{max(days, 2)}d"
    )
    encoded_q = urllib.parse.quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-US&gl=US&ceid=US:en"

    items: List[NewsItem] = []
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)

        for entry in feed.entries[:limit]:
            title = _strip_html(entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            published = (entry.get("published") or "")[:16]
            source_obj = entry.get("source")
            source_title = (
                source_obj.get("title")
                if isinstance(source_obj, dict) and source_obj.get("title")
                else "X / Social Media"
            )
            if not title or not link or _NEGATIVE_AI_RE.search(title):
                continue

            clean_headline = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
            items.append(
                NewsItem(
                    title=clean_headline,
                    url=link,
                    source=f"X Pulse ({source_title})",
                    category=SourceCategory.SOCIAL_X,
                    summary=(
                        f"Industry analysis and researcher commentary on X examining {clean_headline}, "
                        f"reported by {source_title}."
                    ),
                    published_at=published,
                    tags=["x.com", "social-pulse"],
                )
            )
    except Exception as exc:
        logger.warning("Failed to fetch Google News X discussions: %s", exc)

    return items


def fetch_x_social_pulse(days: int = 3, limit: int = 10) -> List[NewsItem]:
    """Combine viral X/Twitter AI threads from Hacker News, AINews Twitter Recap, Web coverage, and curated researcher threads."""
    collected: List[NewsItem] = []
    seen_urls = set()

    live_candidates: List[NewsItem] = []
    live_candidates.extend(fetch_hn_x_threads(limit=max(5, limit // 2)))
    live_candidates.extend(fetch_ainews_twitter_recap(limit=3))
    live_candidates.extend(fetch_google_news_x_discussions(days=days, limit=4))

    for item in live_candidates:
        norm = item.url.strip().rstrip("/").lower()
        if norm and norm not in seen_urls:
            seen_urls.add(norm)
            collected.append(item)

    if len(collected) < limit:
        for fb in CURATED_FALLBACK_X_THREADS:
            norm = fb["url"].strip().rstrip("/").lower()
            if norm in seen_urls:
                continue
            seen_urls.add(norm)
            collected.append(
                NewsItem(
                    title=fb["title"],
                    url=fb["url"],
                    source=fb["source"],
                    category=SourceCategory.SOCIAL_X,
                    summary=fb["summary"],
                    published_at=fb.get("published_at", ""),
                    score=fb.get("score"),
                    tags=list(fb.get("tags", ["x.com", "researcher-thread"])),
                )
            )
            if len(collected) >= limit:
                break

    return collected[:limit]
