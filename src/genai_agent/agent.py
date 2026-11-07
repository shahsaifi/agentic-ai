from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List

from google import genai
from google.genai import types

from genai_agent.collectors import (
    collect_all_sources,
    fetch_ai_company_blogs,
    fetch_ai_podcasts,
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

SYSTEM_INSTRUCTION = """You are a Principal Generative AI Research Scientist and Technical Educator.
Your goal is to curate the highest-signal Generative AI news, research papers, model releases, and engineering discussions into a clear, deeply educational Daily Learning Digest.

Guidelines:
1. Prioritize genuine technical substance (new architectures, post-training methods, agentic patterns, inference optimization, multimodal breakthroughs, open-weights releases, and benchmark insights) over marketing hype.
2. Always include clickable Markdown links `[Title](URL)` for every paper, blog post, or discussion you reference.
3. Make the digest actively educational: explain *why* a method or release matters and *how* it works under the hood.
"""


def build_synthesis_prompt(
    items: List[NewsItem],
    focus_topics: List[str],
    date_str: str,
) -> str:
    """Construct the synthesis prompt with collected items and learning structure."""
    items_block = "\n".join(item.to_prompt_block(i + 1) for i, item in enumerate(items))
    topics_str = ", ".join(focus_topics)

    return f"""Today's Date: {date_str}
Learner's Focus Topics: {topics_str}

Below are {len(items)} freshly collected items from Hugging Face Daily Papers, arXiv (cs.CL/cs.AI), AI Lab Blogs (OpenAI, Google AI, DeepMind, Hugging Face, Simon Willison, Lilian Weng, LangChain), Hacker News, Reddit (r/LocalLLaMA, r/MachineLearning), and Web News Search.

You also have Google Search Grounding enabled—use it (including `site:x.com` queries for breaking AI researcher threads) to verify hot Generative AI releases and discussions from the last 48 hours.

Create a comprehensive, well-structured Markdown digest using the exact sections below:

# 🚀 Generative AI Learning & News Digest — {date_str}

## ⚡ Executive TL;DR (Top 3 Breakthroughs)
- 3 concise bullet points summarizing the biggest announcements or research breakthroughs today, with links.

## 🧠 Concept of the Day (Technical Deep-Dive)
Pick the **single most educational technical concept, architecture, or method** from today's research papers or engineering posts and teach it clearly:
- **Concept**: Name & source paper/post link
- **The Core Problem**: What bottleneck or limitation does it address?
- **How It Works (Intuition & Mechanism)**: Step-by-step explanation of the method or architecture.
- **Why It Matters in Practice**: How engineers/researchers can apply this.

## 🏆 Top 10 Ranked by Content & Reach
Curate the top 10 highest-signal items across Research Papers (arXiv & Hugging Face), AI Lab Releases, and Community Engineering (Hacker News & r/LocalLLaMA). Format each item using this exact structure:
### 1. [Title](URL)
**Category Badge** (Source) · **⬆️ Score pts/upvotes**
- **What happened:** 1–2 sentences summarizing the release, paper, or discussion.
- **Why it matters:** 1 sentence on the practical takeaway.

---

## 🔥 Hot on X.com (AI Twitter Pulse)
Highlight 3–4 viral X.com / AI Twitter threads and discussions from researchers and engineers. Format each item using this exact 2-line bullet structure:
- **[Thread Headline (@handle on X)](URL)** — *X.com Thread* (⬆️ Score pts)
  - **What's being discussed:** 1–2 sentences summarizing the thread and debate.

---

## 🎧 AI Podcasts & Audio Deep-Dives
Include 3–4 relevant, high-signal AI podcast episodes from the collected feed. Format each item using this exact 2-line bullet structure:
- **[Episode Title](URL)** — *Podcast Show Name* (🎧 Duration)
  - **Why listen:** 1–2 sentences on what the episode covers.

---

## 🎯 Today's 15-Minute Learning Challenge
Propose 1 concrete hands-on mini-exercise or 2 thought-provoking architectural questions based on today's digest to help the reader actively retain what they learned.

---
### Collected Source Material:
{items_block}
"""


def rank_top_items(items: List[NewsItem], top_k: int = 10) -> List[NewsItem]:
    """Select the top K items balancing reach (upvotes/points) and content substance across categories."""
    by_cat: Dict[SourceCategory, List[NewsItem]] = {
        SourceCategory.RESEARCH_PAPER: [],
        SourceCategory.COMPANY_BLOG: [],
        SourceCategory.COMMUNITY_NEWS: [],
        SourceCategory.WEB_SEARCH: [],
        SourceCategory.PODCAST: [],
    }
    for item in items:
        by_cat.setdefault(item.category, []).append(item)

    # Sort each category by engagement score + summary richness
    for cat in by_cat:
        by_cat[cat].sort(
            key=lambda x: ((x.score or 0), len(x.summary or "")),
            reverse=True,
        )

    # Pick a balanced Top 10: 4 community, 4 papers, 2 official lab blogs
    quotas = [
        (SourceCategory.COMMUNITY_NEWS, 4),
        (SourceCategory.RESEARCH_PAPER, 4),
        (SourceCategory.COMPANY_BLOG, 2),
    ]
    selected: List[NewsItem] = []
    used_urls = set()

    for cat, quota in quotas:
        for item in by_cat[cat][:quota]:
            selected.append(item)
            used_urls.add(item.url)

    # Fill any remaining slots up to top_k by highest overall score (excluding podcasts & X social section)
    if len(selected) < top_k:
        remaining = [
            i
            for i in items
            if i.url not in used_urls
            and i.category not in (SourceCategory.PODCAST, SourceCategory.SOCIAL_X)
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
    """Generate a concise Top 10 Markdown digest ranked by content substance and community reach, plus X Pulse & Podcasts."""
    top_items = rank_top_items(items, top_k=10)
    x_posts = [i for i in items if i.category == SourceCategory.SOCIAL_X]
    podcasts = [i for i in items if i.category == SourceCategory.PODCAST]

    lines = [
        f"# 🚀 Top 10 Generative AI Learning & News Digest — {date_str}",
        "",
        f"> **Focus Topics:** {', '.join(focus_topics)}  ",
        f"> **Curated:** Top {len(top_items)} of {len(items)} items ranked by technical substance & community reach",
        "",
        "## 🏆 Top 10 Must-Read Highlights Today",
        "",
    ]

    cat_badges = {
        SourceCategory.RESEARCH_PAPER: "📄 Research Paper",
        SourceCategory.COMPANY_BLOG: "🏢 Official Lab Blog",
        SourceCategory.COMMUNITY_NEWS: "🔥 High-Reach Community",
        SourceCategory.WEB_SEARCH: "🌐 Industry News",
    }

    for idx, item in enumerate(top_items, start=1):
        badge = cat_badges.get(item.category, "📌 News")
        score_badge = f" · **⬆️ {item.score} pts/upvotes**" if item.score else ""
        pub_badge = f" · *{item.published_at}*" if item.published_at else ""
        lines.append(
            f"### {idx}. [{item.title}]({item.url})\n"
            f"**{badge}** ({item.source}){score_badge}{pub_badge}"
        )
        if item.summary:
            short_sum = item.summary[:320] + ("..." if len(item.summary) > 320 else "")
            lines.append(f"- **Takeaway:** {short_sum}")
        lines.append("")

    if x_posts:
        lines.append("---")
        lines.append("")
        lines.append("## 🔥 Hot on X.com (AI Twitter Pulse)")
        lines.append("")
        for xp in x_posts[:5]:
            score_badge = f" (⬆️ {xp.score} pts)" if xp.score else ""
            pub_badge = f" · *{xp.published_at}*" if xp.published_at else ""
            lines.append(f"- **[{xp.title}]({xp.url})** — **{xp.source}**{score_badge}{pub_badge}")
            if xp.summary:
                short_x = xp.summary[:280] + ("..." if len(xp.summary) > 280 else "")
                lines.append(f"  - {short_x}")
        lines.append("")

    if podcasts:
        lines.append("---")
        lines.append("")
        lines.append("## 🎧 AI Podcasts & Audio Deep-Dives")
        lines.append("")
        for pod in podcasts[:5]:
            pub_badge = f" (*{pod.published_at}*)" if pod.published_at else ""
            lines.append(f"- **[{pod.title}]({pod.url})** — **{pod.source}**{pub_badge}")
            if pod.summary:
                short_pod = pod.summary[:260] + ("..." if len(pod.summary) > 260 else "")
                lines.append(f"  - {short_pod}")
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

        try:
            response = client.models.generate_content(
                model=self.config.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.3,
                    tools=tools,
                ),
            )
            if response.text:
                return response.text.strip()
        except Exception as exc:
            if use_search_grounding:
                logger.warning(
                    "Search grounding call failed (%s); retrying synthesis without search tool.",
                    exc,
                )
                return self.synthesize_with_gemini(
                    items=items,
                    date_str=date_str,
                    use_search_grounding=False,
                )
            raise

        raise RuntimeError("Gemini returned an empty response.")

    def run_agentic_tool_calling(self, date_str: str) -> str:
        """Run Gemini in autonomous function-calling mode where the model invokes collector tools directly."""
        client = self._create_client()
        max_items = self.config.max_items_per_source
        days = self.config.lookback_days
        topics = self.config.focus_topics

        def tool_get_huggingface_papers() -> List[ dict ]:
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

        prompt = (
            f"Today is {date_str}. The learner's focus topics are: {', '.join(topics)}.\n"
            "Call all available news and research collector tools to gather the latest papers, "
            "company blog posts, Hacker News discussions, Reddit threads, and web news. "
            "Then synthesize the results into the full Generative AI Learning & News Digest "
            "(including Executive TL;DR, Concept of the Day Deep-Dive, Research Papers Spotlight, "
            "AI Lab Announcements, Engineering & Community Pulse, and Today's 15-Minute Learning Challenge)."
        )

        response = client.models.generate_content(
            model=self.config.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
                tools=[
                    tool_get_huggingface_papers,
                    tool_get_arxiv_papers,
                    tool_get_hacker_news,
                    tool_get_reddit_discussions,
                    tool_get_ai_company_blogs,
                    tool_get_web_news,
                ],
            ),
        )
        return (response.text or "").strip()

    def run(self, collect_only: bool = False, agentic_tools_mode: bool = False) -> DigestResult:
        """Collect sources, synthesize the learning digest, and return a DigestResult."""
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        title = f"Generative AI Learning & News Digest — {date_str}"

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
            max_per_source=self.config.max_items_per_source,
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
