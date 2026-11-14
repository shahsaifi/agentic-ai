from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse

from google import genai
from google.genai import types

from genai_agent.collectors import (
    collect_all_sources,
    fetch_ai_company_blogs,
    fetch_ai_podcasts,
    fetch_ai_tech_talks,
    fetch_arxiv_papers,
    fetch_google_news_rss,
    fetch_hacker_news_ai,
    fetch_huggingface_daily_papers,
    fetch_reddit_ai,
    fetch_x_social_pulse,
)
from genai_agent.config import AgentConfig
from genai_agent.models import DigestResult, NewsItem, SourceCategory

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are the Chief Editor of a technical Generative AI research briefing (similar in tone to Anthropic Research notes, Simon Willison's blog, and Distill.pub).
Rules:
1. NO emojis, NO marketing hype, NO filler phrases ("In the fast-paced world of AI...", "game-changing", "revolutionary").
2. Write with high technical density, clarity, and precision.
3. Always include clickable Markdown links `[Title](URL)` for every paper, blog post, or discussion you reference.
"""


def _clean_sentence_excerpt(text: str, max_chars: int = 280) -> str:
    """Clean boilerplate and truncate on a complete sentence boundary instead of mid-word."""
    if not text:
        return ""
    text = re.sub(r"^🎧\s*[0-9hm:\s]+—\s*", "", text.strip())
    text = re.sub(
        r"Hacker News discussion \([^)]+\)\.\s*Discussion:\s*https?://\S+\s*(\|\s*)?",
        "",
        text,
    ).strip()
    text = re.sub(
        r"Viral X thread discussed on Hacker News \([^)]+\)\.\s*HN Thread:\s*https?://\S+",
        "",
        text,
    ).strip()
    text = " ".join(text.split())
    if not text:
        return ""
    if len(text) <= max_chars:
        return text

    cut = text[:max_chars]
    # Prefer cutting at the last period, question mark, or exclamation mark
    best_sep = -1
    for sep in (". ", "? ", "! "):
        pos = cut.rfind(sep)
        if pos > best_sep:
            best_sep = pos
    if best_sep > 45:
        return cut[: best_sep + 1]

    # Otherwise cut cleanly at the last word boundary
    last_space = cut.rfind(" ")
    if last_space > 0:
        return cut[:last_space].rstrip(",;:-") + "."
    return cut + "."


def _extract_hn_discussion_url(summary: str) -> str:
    m = re.search(r"https://news\.ycombinator\.com/item\?id=\d+", summary or "")
    return m.group(0) if m else ""


def _domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def build_synthesis_prompt(
    items: List[NewsItem],
    focus_topics: List[str],
    date_str: str,
) -> str:
    """Construct the synthesis prompt with collected items and clean editorial structure."""
    items_block = "\n".join(item.to_prompt_block(i + 1) for i, item in enumerate(items))
    topics_str = ", ".join(focus_topics)

    return f"""Date: {date_str}
Focus Topics: {topics_str}

Below are {len(items)} collected items from Hugging Face Daily Papers, arXiv (cs.CL/cs.AI), AI Lab Blogs (OpenAI, Google AI, DeepMind, Hugging Face, Simon Willison, Lilian Weng), Hacker News, Reddit (r/LocalLLaMA, r/MachineLearning), X.com, AI Podcasts, and YouTube Tech Talks (AI Engineer, Karpathy, Anthropic, OpenAI, DeepMind, Stanford CS25).

Write a crisp, high-signal technical briefing using the exact Markdown sections below. Do NOT use emojis in headings or bullets.

# Generative AI Technical Briefing — {date_str}

## Executive Summary
- 3 concise bullet points summarizing the most consequential technical developments today, with inline `[Title](URL)` links.

## Technical Deep-Dive
Select the single most substantive architecture, training method, or engineering pattern from today's items and explain it rigorously:
- **Subject**: Name & source `[Title](URL)`
- **Problem Statement**: What technical bottleneck or limitation does it address?
- **Mechanism**: How the method or architecture works under the hood.
- **Engineering Implication**: When and how practitioners should use it.

## Top 10 Ranked Briefing
Curate the top 10 highest-signal items across Research Papers, Lab Releases, and Engineering Discussions. Format each item using this exact structure:
### 1. [Title](URL)
**Category** (Source) · **Score pts** · *Date*
- **Summary:** 2 complete, self-contained sentences explaining the technical contribution and why it matters.

---

## Researcher Threads on X
Highlight 3–4 notable X.com / AI researcher discussions. Format each item using this exact 2-line bullet structure:
- **[Thread Headline (@handle)](URL)** — *X.com* (Score pts)
  - 1–2 complete sentences summarizing the technical argument or debate.

---

## Audio & Podcasts
Include 3–4 relevant AI podcast episodes from the feed. Format each item using this exact 2-line bullet structure:
- **[Episode Title](URL)** — *Show Name* (🎧 Duration)
  - 1–2 complete sentences on the core technical or strategic topic discussed.

---

## Tech Talks & Keynotes
Include 3–4 notable YouTube AI technical talks, keynotes, or lectures from the feed. Format each item using this exact 2-line bullet structure:
- **[Talk Title](URL)** — **Channel Name** · *Date*
  - 1–2 complete sentences explaining the technical architecture, benchmark, or engineering pattern presented.

---
### Collected Source Material:
{items_block}
"""


def exclude_previously_published_items(
    items: List[NewsItem],
    output_dir: Path,
    current_date_str: str,
) -> List[NewsItem]:
    """Filter out items whose URLs or titles were already featured in previous days' digests."""
    if not output_dir.exists():
        return items

    seen_urls: Set[str] = set()
    seen_titles: Set[str] = set()

    for md_path in sorted(output_dir.glob("*_genai_digest.md")):
        file_date = md_path.name.split("_genai_digest.md")[0]
        if file_date >= current_date_str:
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
            for m in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", text):
                title_raw, url_raw = m.group(1), m.group(2)
                norm_url = url_raw.strip().rstrip("/").lower()
                norm_title = "".join(ch.lower() for ch in title_raw if ch.isalnum())
                if norm_url:
                    seen_urls.add(norm_url)
                if len(norm_title) > 10:
                    seen_titles.add(norm_title)
        except Exception:
            continue

    if not seen_urls and not seen_titles:
        return items

    fresh_items: List[NewsItem] = []
    for item in items:
        norm_url = item.url.strip().rstrip("/").lower()
        norm_title = "".join(ch.lower() for ch in item.title if ch.isalnum())
        if norm_url in seen_urls or (len(norm_title) > 10 and norm_title in seen_titles):
            continue
        fresh_items.append(item)

    return fresh_items if len(fresh_items) >= 8 else items


def rank_top_items(items: List[NewsItem], top_k: int = 10) -> List[NewsItem]:
    """Select the top K items balancing reach (upvotes/points) and content substance across categories."""
    by_cat: Dict[SourceCategory, List[NewsItem]] = {
        SourceCategory.RESEARCH_PAPER: [],
        SourceCategory.COMPANY_BLOG: [],
        SourceCategory.COMMUNITY_NEWS: [],
        SourceCategory.WEB_SEARCH: [],
        SourceCategory.PODCAST: [],
        SourceCategory.SOCIAL_X: [],
        SourceCategory.TECH_TALK: [],
    }
    for item in items:
        by_cat.setdefault(item.category, []).append(item)

    for cat in by_cat:
        by_cat[cat].sort(
            key=lambda x: ((x.score or 0), len(x.summary or "")),
            reverse=True,
        )

    quotas = [
        (SourceCategory.RESEARCH_PAPER, 4),
        (SourceCategory.COMMUNITY_NEWS, 4),
        (SourceCategory.COMPANY_BLOG, 2),
    ]
    selected: List[NewsItem] = []
    used_urls = set()

    for cat, quota in quotas:
        for item in by_cat[cat][:quota]:
            selected.append(item)
            used_urls.add(item.url)

    if len(selected) < top_k:
        remaining = [
            i
            for i in items
            if i.url not in used_urls
            and i.category not in (SourceCategory.PODCAST, SourceCategory.SOCIAL_X, SourceCategory.TECH_TALK)
        ]
        remaining.sort(key=lambda x: ((x.score or 0), len(x.summary or "")), reverse=True)
        selected.extend(remaining[: top_k - len(selected)])

    return selected[:top_k]


def build_fallback_markdown(
    items: List[NewsItem],
    focus_topics: List[str],
    date_str: str,
    breakdown: Dict[str, int],
) -> str:
    """Generate a clean, editorial Top 10 Markdown briefing without emoji clutter or raw scraper boilerplate."""
    top_items = rank_top_items(items, top_k=10)
    x_posts = [i for i in items if i.category == SourceCategory.SOCIAL_X]
    podcasts = [i for i in items if i.category == SourceCategory.PODCAST]
    tech_talks = [i for i in items if i.category == SourceCategory.TECH_TALK]

    lines = [
        f"# Generative AI Technical Briefing — {date_str}",
        "",
        "## Top 10 Ranked Briefing",
        "",
    ]

    cat_labels = {
        SourceCategory.RESEARCH_PAPER: "Research",
        SourceCategory.COMPANY_BLOG: "Lab Post",
        SourceCategory.COMMUNITY_NEWS: "Engineering",
        SourceCategory.WEB_SEARCH: "Report",
        SourceCategory.TECH_TALK: "Tech Talk",
    }

    for idx, item in enumerate(top_items, start=1):
        label = cat_labels.get(item.category, "Brief")
        domain = _domain_of(item.url)
        hn_url = _extract_hn_discussion_url(item.summary)
        meta_parts = [f"**{label}** ({item.source})"]
        if domain and domain not in ("news.ycombinator.com", "huggingface.co", "arxiv.org"):
            meta_parts.append(f"`{domain}`")
        if item.score:
            if hn_url and hn_url != item.url:
                meta_parts.append(f"[{item.score} pts on HN]({hn_url})")
            else:
                meta_parts.append(f"{item.score} pts")
        if item.published_at:
            meta_parts.append(f"*{item.published_at}*")

        lines.append(f"### {idx}. [{item.title}]({item.url})")
        lines.append(" · ".join(meta_parts))

        excerpt = _clean_sentence_excerpt(item.summary, max_chars=300)
        if excerpt:
            lines.append(f"- {excerpt}")
        lines.append("")

    if x_posts:
        lines.append("---")
        lines.append("")
        lines.append("## Researcher Threads on X")
        lines.append("")
        for xp in x_posts[:4]:
            hn_url = _extract_hn_discussion_url(xp.summary)
            score_str = f" ({xp.score} pts)" if xp.score else ""
            pub_str = f" · *{xp.published_at}*" if xp.published_at else ""
            lines.append(f"- **[{xp.title}]({xp.url})** — *{xp.source}*{score_str}{pub_str}")
            excerpt = _clean_sentence_excerpt(xp.summary, max_chars=260)
            if excerpt:
                lines.append(f"  - {excerpt}")
            elif hn_url:
                lines.append(f"  - Active engineering discussion thread on [Hacker News]({hn_url}).")
        lines.append("")

    if podcasts:
        lines.append("---")
        lines.append("")
        lines.append("## Audio & Podcasts")
        lines.append("")
        for pod in podcasts[:4]:
            dur_m = re.search(r"🎧\s*([0-9hm:\s]+)", pod.summary or "")
            dur_str = f" (🎧 {dur_m.group(1).strip()})" if dur_m else ""
            pub_str = f" · *{pod.published_at}*" if pod.published_at else ""
            lines.append(f"- **[{pod.title}]({pod.url})** — **{pod.source}**{dur_str}{pub_str}")
            excerpt = _clean_sentence_excerpt(pod.summary, max_chars=260)
            if excerpt:
                lines.append(f"  - {excerpt}")
        lines.append("")

    if tech_talks:
        lines.append("---")
        lines.append("")
        lines.append("## Tech Talks & Keynotes")
        lines.append("")
        for talk in tech_talks[:4]:
            pub_str = f" · *{talk.published_at}*" if talk.published_at else ""
            lines.append(f"- **[{talk.title}]({talk.url})** — **{talk.source}**{pub_str}")
            excerpt = _clean_sentence_excerpt(talk.summary, max_chars=260)
            if excerpt:
                lines.append(f"  - {excerpt}")
        lines.append("")

    return "\n".join(lines)


class GenAILearningAgent:
    """Autonomous Gemini agent that pulls and synthesizes Generative AI news and papers."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def _create_client(self) -> genai.Client:
        if not self.config.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. Add it to your .env file or environment variables."
            )
        return genai.Client(api_key=self.config.gemini_api_key)

    def synthesize_with_gemini(
        self,
        items: List[NewsItem],
        date_str: str,
        use_search_grounding: bool = True,
    ) -> str:
        """Synthesize collected items into a structured learning digest using Gemini + Google Search Grounding."""
        client = self._create_client()
        prompt = build_synthesis_prompt(
            items=items,
            focus_topics=self.config.focus_topics,
            date_str=date_str,
        )

        tools = [types.Tool(google_search=types.GoogleSearch())] if use_search_grounding else None
        candidate_models = []
        for m in (self.config.gemini_model, "gemini-2.5-flash", "gemini-2.0-flash"):
            if m and m not in candidate_models:
                candidate_models.append(m)

        last_exc: Exception | None = None
        for model_name in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        temperature=0.25,
                        tools=tools,
                    ),
                )
                if response.text:
                    return response.text.strip()
            except Exception as exc:
                last_exc = exc
                logger.warning("Model %s (grounding=%s) failed: %s", model_name, use_search_grounding, exc)

        if use_search_grounding:
            return self.synthesize_with_gemini(
                items=items,
                date_str=date_str,
                use_search_grounding=False,
            )
        if last_exc:
            raise last_exc

        raise RuntimeError("Gemini returned an empty response.")

    def run_agentic_tool_calling(self, date_str: str) -> str:
        """Run Gemini in autonomous function-calling mode where the model invokes collector tools directly."""
        client = self._create_client()
        max_items = self.config.max_items_per_source
        days = self.config.lookback_days
        topics = self.config.focus_topics

        def tool_get_huggingface_papers() -> List[dict]:
            """Fetch trending daily AI research papers from Hugging Face."""
            return [i.to_dict() for i in fetch_huggingface_daily_papers(limit=max_items)]

        def tool_get_arxiv_papers(search_topics: List[str]) -> List[dict]:
            """Fetch recent arXiv research papers in cs.CL and cs.AI for given topics."""
            return [i.to_dict() for i in fetch_arxiv_papers(query_topics=search_topics or topics, limit=max_items)]

        def tool_get_hacker_news() -> List[dict]:
            """Fetch top Generative AI discussions from Hacker News."""
            return [i.to_dict() for i in fetch_hacker_news_ai(days=days, limit=max_items)]

        def tool_get_reddit_discussions() -> List[dict]:
            """Fetch top discussions from r/LocalLLaMA and r/MachineLearning."""
            return [i.to_dict() for i in fetch_reddit_ai(limit_per_sub=max(3, max_items // 2))]

        def tool_get_ai_company_blogs() -> List[dict]:
            """Fetch official blog announcements from OpenAI, Google AI, DeepMind, Hugging Face, and top researchers."""
            return [i.to_dict() for i in fetch_ai_company_blogs(max_per_feed=2)]

        def tool_get_web_news() -> List[dict]:
            """Fetch recent Generative AI news articles from Google News RSS."""
            return [i.to_dict() for i in fetch_google_news_rss(topics=topics, days=days, limit=max_items)]

        def tool_get_ai_tech_talks() -> List[dict]:
            """Fetch YouTube AI technical talks and keynotes from AI Engineer, Karpathy, Anthropic, OpenAI, DeepMind, and Stanford CS25."""
            return [i.to_dict() for i in fetch_ai_tech_talks(focus_topics=topics, limit=6)]

        prompt = (
            f"Today is {date_str}. Focus topics: {', '.join(topics)}.\n"
            "Call the collector tools to gather the latest papers, lab blog posts, community threads, and YouTube tech talks, "
            "then synthesize a clean, emoji-free Generative AI Technical Briefing."
        )

        response = client.models.generate_content(
            model=self.config.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.25,
                tools=[
                    tool_get_huggingface_papers,
                    tool_get_arxiv_papers,
                    tool_get_hacker_news,
                    tool_get_reddit_discussions,
                    tool_get_ai_company_blogs,
                    tool_get_web_news,
                    tool_get_ai_tech_talks,
                ],
            ),
        )
        return (response.text or "").strip()

    def run(self, collect_only: bool = False, agentic_tools_mode: bool = False) -> DigestResult:
        """Collect sources, synthesize the learning digest, and return a DigestResult."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        title = f"Generative AI Technical Briefing — {date_str}"

        if agentic_tools_mode and not collect_only:
            markdown_content = self.run_agentic_tool_calling(date_str=date_str)
            return DigestResult(
                title=title,
                markdown_content=markdown_content,
                generated_at=now,
                focus_topics=self.config.focus_topics,
                items_collected=-1,
                sources_breakdown={"Autonomous Tool-Calling Mode": 1},
            )

        items, breakdown = collect_all_sources(
            focus_topics=self.config.focus_topics,
            days=self.config.lookback_days,
            max_per_source=max(self.config.max_items_per_source, 16),
        )
        items = exclude_previously_published_items(
            items=items,
            output_dir=self.config.digest_output_dir,
            current_date_str=date_str,
        )

        if collect_only or not self.config.gemini_api_key:
            markdown_content = build_fallback_markdown(
                items=items,
                focus_topics=self.config.focus_topics,
                date_str=date_str,
                breakdown=breakdown,
            )
        else:
            try:
                markdown_content = self.synthesize_with_gemini(
                    items=items,
                    date_str=date_str,
                    use_search_grounding=True,
                )
            except Exception as exc:
                logger.warning("Gemini synthesis failed (%s); falling back to Top 10 ranker.", exc)
                markdown_content = build_fallback_markdown(
                    items=items,
                    focus_topics=self.config.focus_topics,
                    date_str=date_str,
                    breakdown=breakdown,
                )

        return DigestResult(
            title=title,
            markdown_content=markdown_content,
            generated_at=now,
            focus_topics=self.config.focus_topics,
            items_collected=len(items),
            sources_breakdown=breakdown,
        )
