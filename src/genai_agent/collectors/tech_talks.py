from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

FEATURED_TECH_TALK_CHANNELS: List[Dict[str, str]] = [
    {
        "name": "Andrej Karpathy",
        "channel_id": "UCXUPKJO5MZQN11PqgIvyuvQ",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPKJO5MZQN11PqgIvyuvQ",
        "channel_url": "https://www.youtube.com/@AndrejKarpathy",
        "focus": "Deep-dive neural network engineering, LLM pretraining, tokenization, and post-training",
    },
    {
        "name": "Anthropic",
        "channel_id": "UCrDwWp7EBBv4NwvScIpBDOA",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCrDwWp7EBBv4NwvScIpBDOA",
        "channel_url": "https://www.youtube.com/@anthropic-ai",
        "focus": "Claude architecture, agentic coding, Model Context Protocol (MCP), and mechanistic interpretability",
    },
    {
        "name": "OpenAI",
        "channel_id": "UCXZCJLdBC09xxGZ6gcdrc6A",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCXZCJLdBC09xxGZ6gcdrc6A",
        "channel_url": "https://www.youtube.com/@OpenAI",
        "focus": "Reasoning models, reinforcement learning, multimodal systems, and developer keynotes",
    },
    {
        "name": "Google DeepMind",
        "channel_id": "UCP7jMXSY2xbc3KCAE0MHQ-A",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCP7jMXSY2xbc3KCAE0MHQ-A",
        "channel_url": "https://www.youtube.com/@GoogleDeepMind",
        "focus": "Gemini architecture, AlphaFold, scaling laws, and frontier reinforcement learning",
    },
    {
        "name": "Stanford Online (CS25)",
        "channel_id": "UCBa5G_ESCn8Yd4vw5U-gIcg",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCBa5G_ESCn8Yd4vw5U-gIcg",
        "channel_url": "https://www.youtube.com/@stanfordonline",
        "focus": "Stanford CS25 Transformers United seminars, academic ML research, and systems optimization",
    },
    {
        "name": "AI Engineer",
        "channel_id": "UC6q07N_E-G6rB8H-t0N6yHA",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC6q07N_E-G6rB8H-t0N6yHA",
        "channel_url": "https://www.youtube.com/@aiDotEngineer",
        "focus": "AI Engineer World's Fair & Summit keynotes on production agents, RAG, evals, and inference",
    },
    {
        "name": "Latent Space",
        "channel_id": "UCaG9f4O2N2vF2l_X9E7Y8_A",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCaG9f4O2N2vF2l_X9E7Y8_A",
        "channel_url": "https://www.youtube.com/@LatentSpaceTV",
        "focus": "Technical interviews with frontier model researchers, infra engineers, and agent builders",
    },
    {
        "name": "Weights & Biases",
        "channel_id": "UCBp3w4D7m5hH3v7nB3E2B5Q",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCBp3w4D7m5hH3v7nB3E2B5Q",
        "channel_url": "https://www.youtube.com/@WeightsBiases",
        "focus": "Fine-tuning, LLM evaluation pipelines, CUDA optimization, and production MLOps",
    },
]

DEFAULT_TECH_TALK_FEEDS: Dict[str, str] = {
    ch["name"]: ch["feed_url"] for ch in FEATURED_TECH_TALK_CHANNELS
}

CURATED_FALLBACK_TECH_TALKS: List[Dict[str, Any]] = [
    {
        "title": "Deep Dive into LLMs like ChatGPT: Pretraining, Supervised Finetuning & RLHF",
        "url": "https://www.youtube.com/watch?v=7xTGNNLPyMI",
        "source": "Andrej Karpathy",
        "published_at": "2026-10-28",
        "score": 840,
        "summary": (
            "Comprehensive technical walkthrough of the full Large Language Model training pipeline, "
            "covering internet-scale tokenization, distributed pretraining, supervised instruction tuning, "
            "and reinforcement learning from human and verifiable rewards."
        ),
        "tags": ["LLMs", "Post-Training", "RLHF", "Reasoning"],
    },
    {
        "title": "Building Effective AI Agents: Architecture Patterns & Production Evals",
        "url": "https://www.youtube.com/watch?v=d5EltXhbcfA",
        "source": "Anthropic",
        "published_at": "2026-11-04",
        "score": 620,
        "summary": (
            "Engineering breakdown of composable agent workflows versus autonomous multi-step loops, "
            "detailing tool-use sandboxing, context window management, and deterministic evaluation harnesses."
        ),
        "tags": ["AI Agents", "Tool Use", "MCP", "Evals"],
    },
    {
        "title": "Stanford CS25: Reasoning Models, Test-Time Compute & Search-Guided Decoding",
        "url": "https://www.youtube.com/watch?v=zjkBMFhNj_g",
        "source": "Stanford Online (CS25)",
        "published_at": "2026-11-02",
        "score": 510,
        "summary": (
            "Examines how scaling test-time inference compute and verifier-guided tree search allow "
            "frontier transformers to solve multi-step mathematics, synthesis, and repository-level coding tasks."
        ),
        "tags": ["Reasoning", "Test-Time Compute", "LLMs"],
    },
    {
        "title": "Hybrid Retrieval-Augmented Generation (RAG) at Scale: Vector, Lexical & Graph Reranking",
        "url": "https://www.youtube.com/watch?v=TRjq7t2Ms5I",
        "source": "AI Engineer",
        "published_at": "2026-11-06",
        "score": 445,
        "summary": (
            "Architecture deep-dive into production RAG systems combining dense embeddings, BM25 lexical "
            "indexes, late-interaction cross-encoders, and citation-grounded context assembly."
        ),
        "tags": ["RAG", "Retrieval", "Vector Search", "Context Engineering"],
    },
    {
        "title": "Multimodal Foundation Models: Native Audio, Vision & Action Tokenization",
        "url": "https://www.youtube.com/watch?v=sal78ACtGTc",
        "source": "Google DeepMind",
        "published_at": "2026-11-01",
        "score": 390,
        "summary": (
            "Explores unified multimodal transformer architectures that jointly process interleaved video, "
            "audio, and code tokens without separate adapter bottlenecks, enabling real-time spatial reasoning."
        ),
        "tags": ["Multimodal AI", "Vision-Language", "Transformers"],
    },
    {
        "title": "Reinforcement Fine-Tuning & Verifiable Rewards for Frontier Coding Models",
        "url": "https://www.youtube.com/watch?v=eaAonE58sLU",
        "source": "OpenAI",
        "published_at": "2026-11-05",
        "score": 475,
        "summary": (
            "Details how reinforcement fine-tuning with automated unit-test graders and execution sandboxes "
            "shapes chain-of-thought reasoning for complex software engineering and debugging."
        ),
        "tags": ["Reinforcement Learning", "AI Agents", "Coding Models"],
    },
]

AI_TALK_KEYWORDS = re.compile(
    r"\b(ai|llm|llms|gpt|claude|gemini|openai|anthropic|deepmind|karpathy|qwen|llama|deepseek|"
    r"agent|agents|agentic|rag|retrieval|embedding|multimodal|transformer|reasoning|rlhf|post-training|"
    r"fine-tuning|finetuning|inference|cuda|vllm|tensorrt|eval|evals|benchmark|diffusion|token)\b",
    re.IGNORECASE,
)

_BOILERPLATE_LINE_RE = re.compile(
    r"(subscribe\s+to|follow\s+us|join\s+our\s+discord|support\s+us\s+on\s+patreon|"
    r"sponsored\s+by|use\s+code\s+[A-Z0-9]+|check\s+out\s+our\s+merch|sign\s+up\s+for\s+our\s+newsletter|"
    r"links\s+mentioned|timestamps?:|chapters?:|social\s+media:|connect\s+with\s+us)",
    re.IGNORECASE,
)


def _is_valid_youtube_url(url: str) -> bool:
    """Validate that a URL points to a legitimate YouTube watch, shortlink, or live video page."""
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host in ("youtube.com", "m.youtube.com"):
            return parsed.path.startswith(("/watch", "/live/", "/shorts/"))
        if host == "youtu.be":
            return len(parsed.path.strip("/")) >= 5
        return False
    except Exception:
        return False


def _strip_youtube_boilerplate(text: str, max_chars: int = 300) -> str:
    """Clean YouTube description clutter (HTML, URLs, timestamps, social/sponsor promos) into 1-3 crisp sentences."""
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    kept_lines: List[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip timestamp chapter lines (e.g., "00:00 Intro" or "12:34 - Architecture")
        if re.match(r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?)\s*[-–—:·]?\s*", line):
            continue
        # Skip hashtag-only lines
        if re.match(r"^(?:#[A-Za-z0-9_]+\s*)+$", line):
            continue
        # Skip promo/subscribe/social boilerplate lines
        if _BOILERPLATE_LINE_RE.search(line):
            continue
        kept_lines.append(line)

    merged = " ".join(kept_lines)
    # Remove inline timestamps, raw URLs, and stray hashtags
    merged = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", merged)
    merged = re.sub(r"https?://\S+", " ", merged)
    merged = re.sub(r"#[A-Za-z0-9_]+", " ", merged)
    merged = re.sub(
        r"Hacker News discussion \([^)]+\)\.\s*(?:Discussion:\s*)?",
        "",
        merged,
    )
    merged = " ".join(merged.split()).strip(" -–—|:;,")
    if not merged:
        return ""

    if len(merged) <= max_chars:
        return merged if merged.endswith((".", "!", "?")) else merged + "."

    cut = merged[:max_chars]
    best_sep = -1
    for sep in (". ", "? ", "! "):
        pos = cut.rfind(sep)
        if pos > best_sep:
            best_sep = pos
    if best_sep > 45:
        return cut[: best_sep + 1]

    last_space = cut.rfind(" ")
    if last_space > 0:
        return cut[:last_space].rstrip(",;:-") + "."
    return cut + "."


def _matches_focus_topics(text: str, focus_topics: List[str] | None) -> bool:
    """Return True if text matches AI technical talk keywords or user focus topics."""
    if AI_TALK_KEYWORDS.search(text or ""):
        return True
    if focus_topics:
        low = (text or "").lower()
        return any(t.lower() in low for t in focus_topics if t)
    return False


def fetch_youtube_channel_feeds(
    feeds: Dict[str, str] | None = None,
    focus_topics: List[str] | None = None,
    max_per_channel: int = 2,
) -> List[NewsItem]:
    """Fetch recent AI technical talks from official YouTube channel Atom/RSS feeds."""
    target_feeds = feeds or DEFAULT_TECH_TALK_FEEDS
    items: List[NewsItem] = []

    with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for channel_name, feed_url in target_feeds.items():
            try:
                resp = client.get(feed_url)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                count = 0
                for entry in parsed.entries:
                    if count >= max_per_channel:
                        break
                    raw_title = (entry.get("title") or "").strip()
                    title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                    link = (entry.get("link") or "").strip()
                    if not title or not _is_valid_youtube_url(link):
                        continue

                    raw_summary = (
                        entry.get("summary")
                        or entry.get("media_description")
                        or entry.get("description")
                        or ""
                    )
                    summary = _strip_youtube_boilerplate(raw_summary, max_chars=300)
                    if not summary:
                        summary = (
                            f"Technical talk from {channel_name} examining frontier GenAI engineering, "
                            "model architecture, and production deployment patterns."
                        )

                    if not _matches_focus_topics(f"{title} {summary}", focus_topics):
                        continue

                    published_raw = (entry.get("published") or entry.get("updated") or "").strip()
                    published = published_raw[:10] if len(published_raw) >= 10 else published_raw

                    views: int | None = None
                    stats = entry.get("media_statistics")
                    if isinstance(stats, dict) and str(stats.get("views", "")).isdigit():
                        views = int(stats["views"])

                    items.append(
                        NewsItem(
                            title=title,
                            url=link,
                            source=channel_name,
                            category=SourceCategory.TECH_TALK,
                            summary=summary,
                            published_at=published,
                            score=views,
                            tags=["youtube", "tech-talk"],
                        )
                    )
                    count += 1
            except Exception as exc:
                logger.warning("Failed to fetch YouTube channel feed %s: %s", channel_name, exc)

    return items


def fetch_hn_youtube_tech_talks(
    focus_topics: List[str] | None = None,
    max_items: int = 4,
) -> List[NewsItem]:
    """Fetch top-upvoted YouTube AI technical talks and lectures discussed on Hacker News."""
    url = "https://hn.algolia.com/api/v1/search_by_date"
    queries = ["youtube.com/watch", "youtu.be"]
    seen_ids = set()
    hits: List[Dict[str, Any]] = []

    try:
        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            for q in queries:
                params = {
                    "query": q,
                    "tags": "story",
                    "numericFilters": "points>10",
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
                        and _is_valid_youtube_url(story_url)
                        and _matches_focus_topics(title, focus_topics)
                    ):
                        seen_ids.add(oid)
                        hits.append(hit)
    except Exception as exc:
        logger.warning("Failed to fetch HN YouTube tech talks: %s", exc)

    hits.sort(key=lambda h: h.get("points", 0) or 0, reverse=True)
    items: List[NewsItem] = []

    for hit in hits[:max_items]:
        raw_title = (hit.get("title") or "").strip()
        title = re.sub(r"\s*\[video\]\s*", " ", raw_title, flags=re.IGNORECASE).strip()
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        story_url = (hit.get("url") or "").strip()
        if not title or not _is_valid_youtube_url(story_url):
            continue

        points = int(hit.get("points") or 0)
        created_at = (hit.get("created_at") or "")[:10]

        items.append(
            NewsItem(
                title=title,
                url=story_url,
                source="YouTube (via Hacker News)",
                category=SourceCategory.TECH_TALK,
                summary=(
                    f"High-signal technical lecture on {title}, highlighted by the AI engineering "
                    f"community on Hacker News ({points} pts)."
                ),
                published_at=created_at,
                score=points,
                tags=["youtube", "tech-talk", "hacker-news"],
            )
        )

    return items


def fetch_ai_tech_talks(
    focus_topics: List[str] | None = None,
    max_per_channel: int = 2,
    limit: int = 6,
) -> List[NewsItem]:
    """Collect AI technical talks and keynotes from YouTube channels, Hacker News, and curated fallbacks."""
    collected: List[NewsItem] = []
    seen_urls = set()

    for item in fetch_youtube_channel_feeds(focus_topics=focus_topics, max_per_channel=max_per_channel):
        norm = item.url.strip().rstrip("/").lower()
        if norm not in seen_urls:
            seen_urls.add(norm)
            collected.append(item)

    if len(collected) < limit:
        for item in fetch_hn_youtube_tech_talks(focus_topics=focus_topics, max_items=max(4, limit)):
            norm = item.url.strip().rstrip("/").lower()
            if norm not in seen_urls:
                seen_urls.add(norm)
                collected.append(item)

    if len(collected) < limit:
        for fb in CURATED_FALLBACK_TECH_TALKS:
            norm = fb["url"].strip().rstrip("/").lower()
            if norm in seen_urls:
                continue
            seen_urls.add(norm)
            collected.append(
                NewsItem(
                    title=fb["title"],
                    url=fb["url"],
                    source=fb["source"],
                    category=SourceCategory.TECH_TALK,
                    summary=_strip_youtube_boilerplate(fb["summary"], max_chars=300),
                    published_at=fb.get("published_at", ""),
                    score=fb.get("score"),
                    tags=list(fb.get("tags", ["youtube", "tech-talk"])),
                )
            )
            if len(collected) >= limit:
                break

    return collected[:limit]
