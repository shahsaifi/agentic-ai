from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

from genai_agent.collectors.blogs import fetch_ai_company_blogs
from genai_agent.collectors.community import fetch_hacker_news_ai, fetch_reddit_ai
from genai_agent.collectors.papers import (
    fetch_arxiv_papers,
    fetch_huggingface_daily_papers,
)
from genai_agent.collectors.podcasts import fetch_ai_podcasts
from genai_agent.collectors.web_search import fetch_google_news_rss
from genai_agent.models import NewsItem


def deduplicate_items(items: List[NewsItem]) -> List[NewsItem]:
    """Deduplicate news items by normalized title and URL."""
    seen_urls = set()
    seen_titles = set()
    unique: List[NewsItem] = []

    for item in items:
        norm_url = item.url.strip().rstrip("/").lower()
        norm_title = "".join(ch.lower() for ch in item.title if ch.isalnum())
        if not norm_title or norm_url in seen_urls or norm_title in seen_titles:
            continue
        seen_urls.add(norm_url)
        seen_titles.add(norm_title)
        unique.append(item)

    return unique


def collect_all_sources(
    focus_topics: List[str] | None = None,
    days: int = 2,
    max_per_source: int = 8,
) -> Tuple[List[NewsItem], Dict[str, int]]:
    """Concurrently collect GenAI research papers, community discussions, blogs, and web news."""
    tasks = {
        "Hugging Face Daily Papers": lambda: fetch_huggingface_daily_papers(limit=max_per_source),
        "arXiv Papers": lambda: fetch_arxiv_papers(query_topics=focus_topics, limit=max_per_source),
        "Hacker News": lambda: fetch_hacker_news_ai(days=days, limit=max_per_source),
        "Reddit (r/LocalLLaMA & r/MachineLearning)": lambda: fetch_reddit_ai(
            limit_per_sub=max(3, max_per_source // 2)
        ),
        "AI Lab & Engineering Blogs": lambda: fetch_ai_company_blogs(max_per_feed=2),
        "AI Podcasts": lambda: fetch_ai_podcasts(max_per_feed=1),
        "Web News Search": lambda: fetch_google_news_rss(
            topics=focus_topics, days=days, limit=max_per_source
        ),
    }

    all_items: List[NewsItem] = []
    breakdown: Dict[str, int] = {}

    with ThreadPoolExecutor(max_workers=7) as executor:
        future_to_name = {executor.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                res = future.result()
                breakdown[name] = len(res)
                all_items.extend(res)
            except Exception:
                breakdown[name] = 0

    deduped = deduplicate_items(all_items)
    return deduped, breakdown


__all__ = [
    "fetch_huggingface_daily_papers",
    "fetch_arxiv_papers",
    "fetch_hacker_news_ai",
    "fetch_reddit_ai",
    "fetch_ai_company_blogs",
    "fetch_google_news_rss",
    "deduplicate_items",
    "collect_all_sources",
]
