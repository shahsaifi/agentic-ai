from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SourceCategory(str, Enum):
    RESEARCH_PAPER = "research_paper"
    COMMUNITY_NEWS = "community_news"
    COMPANY_BLOG = "company_blog"
    WEB_SEARCH = "web_search"
    PODCAST = "podcast"
    SOCIAL_X = "social_x"


@dataclass
class NewsItem:
    """Represents a single GenAI news article, research paper, or discussion."""

    title: str
    url: str
    source: str
    category: SourceCategory
    summary: str = ""
    published_at: Optional[str] = None
    score: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        return data

    def to_prompt_block(self, idx: int) -> str:
        """Format item compactly for LLM context injection."""
        meta_parts = [f"Source: {self.source}", f"Category: {self.category.value}"]
        if self.published_at:
            meta_parts.append(f"Published: {self.published_at}")
        if self.score is not None:
            meta_parts.append(f"Engagement/Upvotes: {self.score}")
        if self.authors:
            meta_parts.append(f"Authors: {', '.join(self.authors[:4])}")

        summary_clean = (self.summary or "").strip().replace("\n", " ")
        if len(summary_clean) > 650:
            summary_clean = summary_clean[:647] + "..."

        return (
            f"[{idx}] {self.title}\n"
            f"    URL: {self.url}\n"
            f"    {' | '.join(meta_parts)}\n"
            f"    Summary: {summary_clean}\n"
        )


@dataclass
class DigestResult:
    """Holds the synthesized learning digest and metadata from a run."""

    title: str
    markdown_content: str
    generated_at: datetime
    focus_topics: List[str]
    items_collected: int
    sources_breakdown: Dict[str, int] = field(default_factory=dict)
    saved_path: Optional[str] = None
