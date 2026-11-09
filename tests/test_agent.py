from __future__ import annotations

from datetime import datetime
from pathlib import Path

from genai_agent.agent import (
    build_fallback_markdown,
    build_synthesis_prompt,
    exclude_previously_published_items,
)
from genai_agent.collectors import deduplicate_items
from genai_agent.models import NewsItem, SourceCategory
from genai_agent.notifiers import chunk_text, render_email_html, save_markdown_digest


def test_deduplicate_items():
    items = [
        NewsItem(
            title="Attention Is All You Need",
            url="https://arxiv.org/abs/1706.03762",
            source="arXiv",
            category=SourceCategory.RESEARCH_PAPER,
        ),
        NewsItem(
            title="Attention is all you need!",
            url="https://arxiv.org/abs/1706.03762/",
            source="Hugging Face",
            category=SourceCategory.RESEARCH_PAPER,
        ),
        NewsItem(
            title="Scaling Test-Time Compute",
            url="https://huggingface.co/papers/2408.03314",
            source="Hugging Face",
            category=SourceCategory.RESEARCH_PAPER,
        ),
    ]
    deduped = deduplicate_items(items)
    assert len(deduped) == 2
    assert deduped[0].title == "Attention Is All You Need"
    assert deduped[1].title == "Scaling Test-Time Compute"


def test_build_synthesis_prompt_and_fallback():
    items = [
        NewsItem(
            title="DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL",
            url="https://arxiv.org/abs/2501.12948",
            source="arXiv",
            category=SourceCategory.RESEARCH_PAPER,
            summary="Demonstrates pure reinforcement learning for reasoning models.",
            score=420,
        )
    ]
    prompt = build_synthesis_prompt(items, ["Reasoning Models", "RLHF"], "2026-11-06")
    assert "DeepSeek-R1" in prompt
    assert "Reasoning Models" in prompt
    assert "Technical Deep-Dive" in prompt

    hn_item = NewsItem(
        title="Show HN: Local LLM Runtime in Pure C",
        url="https://example.com/local-llm",
        source="Hacker News",
        category=SourceCategory.COMMUNITY_NEWS,
        summary="Hacker News discussion (850 points, 310 comments). Discussion: https://news.ycombinator.com/item?id=999999",
        score=850,
    )
    fallback = build_fallback_markdown(
        items=[items[0], hn_item],
        focus_topics=["Reasoning Models"],
        date_str="2026-11-06",
        breakdown={"arXiv": 1, "Hacker News": 1},
    )
    assert "DeepSeek-R1" in fallback
    assert "https://arxiv.org/abs/2501.12948" in fallback
    assert "Discussion: https://news.ycombinator.com" not in fallback
    assert "[850 pts on HN](https://news.ycombinator.com/item?id=999999)" in fallback


def test_telegram_chunk_text():
    text = "Paragraph 1\n\n" * 400
    chunks = chunk_text(text, max_chars=1000)
    assert len(chunks) > 1
    assert all(len(c) <= 1000 for c in chunks)


def test_save_markdown_and_render_html(tmp_path: Path):
    md = "# Daily Digest\n\n- **Paper 1**: Great breakthrough."
    ts = datetime(2026, 11, 6, 17, 30)
    saved = save_markdown_digest(md, tmp_path, timestamp=ts)
    assert saved.exists()
    assert (tmp_path / "latest.md").exists()
    assert saved.read_text(encoding="utf-8") == md

    html = render_email_html(md, title="Daily Digest")
    assert "<h1>Daily Digest</h1>" in html
    assert "<strong>Paper 1</strong>" in html


def test_exclude_previously_published_items(tmp_path: Path):
    prev_md = (
        "# Digest 2026-11-08\n"
        "### 1. [Old Repeated Story](https://example.com/old-story)\n"
    )
    (tmp_path / "2026-11-08_genai_digest.md").write_text(prev_md, encoding="utf-8")

    candidates = [
        NewsItem(
            title="Old Repeated Story",
            url="https://example.com/old-story",
            source="HN",
            category=SourceCategory.COMMUNITY_NEWS,
        )
    ] + [
        NewsItem(
            title=f"Fresh Story {i}",
            url=f"https://example.com/fresh-{i}",
            source="arXiv",
            category=SourceCategory.RESEARCH_PAPER,
        )
        for i in range(10)
    ]

    filtered = exclude_previously_published_items(
        items=candidates,
        output_dir=tmp_path,
        current_date_str="2026-11-09",
    )
    assert len(filtered) == 10
    assert all(i.url != "https://example.com/old-story" for i in filtered)


def test_reddit_waf_safe_links_and_rss_sanitization():
    from genai_agent.notifiers.markdown_store import (
        _extract_reddit_rss_excerpt,
        _find_reddit_discussion,
    )

    _, search_url = _find_reddit_discussion("Random Is Almost Enough Benchmark Compression")
    assert "reddit.com/r/" not in search_url or "/search/" not in search_url
    assert search_url.startswith("https://www.google.com/search?q=site:reddit.com+")

    raw_rss = (
        '<table><tr><td><p>When you approve a command in Claude Code, it is saved in settings.local.json.</p>'
        '</td></tr></table> &#32; submitted by &#32; <a href="https://www.reddit.com/user/test"> /u/test </a> '
        '<span><a href="https://www.reddit.com/r/ClaudeAI/">[link]</a></span> <span>[comments]</span>'
    )
    excerpt = _extract_reddit_rss_excerpt(raw_rss)
    assert "settings.local.json" in excerpt
    assert "submitted by" not in excerpt
    assert "[comments]" not in excerpt
    assert "<table" not in excerpt


