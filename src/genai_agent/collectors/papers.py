from __future__ import annotations

import logging
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List

import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"


def fetch_huggingface_daily_papers(limit: int = 8) -> List[NewsItem]:
    """Fetch trending Generative AI research papers from Hugging Face Daily Papers."""
    url = "https://huggingface.co/api/daily_papers"
    items: List[NewsItem] = []
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        # Sort by upvotes descending
        sorted_papers = sorted(
            data,
            key=lambda x: x.get("paper", {}).get("upvotes", 0),
            reverse=True,
        )

        for entry in sorted_papers[:limit]:
            paper = entry.get("paper", {})
            paper_id = paper.get("id", "")
            title = (entry.get("title") or paper.get("title") or "").strip().replace("\n", " ")
            summary = (entry.get("summary") or paper.get("summary") or "").strip().replace("\n", " ")
            upvotes = paper.get("upvotes", 0)
            published_at = (entry.get("publishedAt") or paper.get("publishedAt") or "")[:10]
            authors = [
                a.get("name", "")
                for a in paper.get("authors", [])
                if isinstance(a, dict) and a.get("name")
            ]

            if not title or not paper_id:
                continue

            items.append(
                NewsItem(
                    title=title,
                    url=f"https://huggingface.co/papers/{paper_id}",
                    source="Hugging Face Daily Papers",
                    category=SourceCategory.RESEARCH_PAPER,
                    summary=summary,
                    published_at=published_at,
                    score=upvotes,
                    authors=authors,
                    tags=["huggingface", "daily-papers"],
                )
            )
    except Exception as exc:
        logger.warning("Failed to fetch Hugging Face Daily Papers: %s", exc)

    return items


def fetch_arxiv_papers(query_topics: List[str] | None = None, limit: int = 8) -> List[NewsItem]:
    """Fetch recent Generative AI papers from the arXiv API (cs.CL, cs.AI, cs.LG)."""
    if not query_topics:
        query_topics = ["large language model", "generative AI", "multimodal", "agentic", "reasoning"]

    topic_clause = " OR ".join(f'all:"{t}"' for t in query_topics[:5])
    search_query = f"(cat:cs.CL OR cat:cs.AI) AND ({topic_clause})"
    params = {
        "search_query": search_query,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": str(limit),
    }
    url = f"https://export.arxiv.org/api/query?{urllib.parse.urlencode(params)}"
    items: List[NewsItem] = []

    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            xml_text = resp.text

        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_text)

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            published_el = entry.find("atom:published", ns)

            title = (title_el.text if title_el is not None and title_el.text else "").strip()
            title = " ".join(title.split())
            summary = (summary_el.text if summary_el is not None and summary_el.text else "").strip()
            summary = " ".join(summary.split())
            link = (id_el.text if id_el is not None and id_el.text else "").strip()
            published = (
                published_el.text[:10]
                if published_el is not None and published_el.text
                else ""
            )

            authors = []
            for author_el in entry.findall("atom:author", ns):
                name_el = author_el.find("atom:name", ns)
                if name_el is not None and name_el.text:
                    authors.append(name_el.text.strip())

            if not title or not link:
                continue

            items.append(
                NewsItem(
                    title=title,
                    url=link,
                    source="arXiv (cs.CL / cs.AI)",
                    category=SourceCategory.RESEARCH_PAPER,
                    summary=summary,
                    published_at=published,
                    authors=authors,
                    tags=["arxiv", "research"],
                )
            )
    except Exception as exc:
        logger.warning("Failed to fetch arXiv papers: %s", exc)

    return items
