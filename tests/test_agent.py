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


def test_tech_talks_collector_and_boilerplate_sanitization(monkeypatch):
    from genai_agent.collectors import tech_talks
    from genai_agent.collectors.tech_talks import (
        FEATURED_TECH_TALK_CHANNELS,
        _is_valid_youtube_url,
        _strip_youtube_boilerplate,
        fetch_ai_tech_talks,
    )

    expected_channels = {
        "Google Cloud Tech": "UCJS9pqu9BzkAMNTmzNMNhvg",
        "IBM Technology": "UCKWaEZ-_VweaEx1j62do_vQ",
        "The Pragmatic Engineer": "UCPbwhExawYrn9xxI21TFfyw",
        "IBM Developer": "UCUm6InQvGI9-6vo1teGWINA",
        "Stanford Online (CS25)": "UCBa5G_ESCn8Yd4vw5U-gIcg",
        "LangChain": "UCC-lyoTfSrcJzA1ab3APAgw",
    }
    channel_map = {ch["name"]: ch["channel_id"] for ch in FEATURED_TECH_TALK_CHANNELS}
    for ch_name, ch_id in expected_channels.items():
        assert channel_map.get(ch_name) == ch_id

    assert _is_valid_youtube_url("https://www.youtube.com/watch?v=7xTGNNLPyMI")
    assert _is_valid_youtube_url("https://youtu.be/7xTGNNLPyMI")
    assert not _is_valid_youtube_url("https://example.com/watch?v=123")
    assert not _is_valid_youtube_url("javascript:alert(1)")

    raw_desc = (
        "00:00 Intro\n"
        "04:15 Transformer KV Cache Architecture\n"
        "<p>We present a deep dive into speculative decoding and multi-head latent attention for low-latency LLM inference.</p>\n"
        "Subscribe to our channel and join our Discord: https://discord.gg/test\n"
        "Sponsored by ExampleCorp — use code AI2026!\n"
        "#AI #LLMs #DeepLearning"
    )
    cleaned = _strip_youtube_boilerplate(raw_desc)
    assert "speculative decoding" in cleaned
    assert "00:00" not in cleaned
    assert "Subscribe to" not in cleaned
    assert "Sponsored by" not in cleaned
    assert "https://discord.gg" not in cleaned
    assert "#AI" not in cleaned
    assert "<p>" not in cleaned

    monkeypatch.setattr(tech_talks, "fetch_youtube_channel_feeds", lambda **kwargs: [])
    monkeypatch.setattr(tech_talks, "fetch_hn_youtube_tech_talks", lambda **kwargs: [])
    talks = fetch_ai_tech_talks(focus_topics=["LLMs", "AI Agents"], limit=8)
    assert len(talks) == 8
    sources = {item.source for item in talks}
    for ch_name in expected_channels:
        assert ch_name in sources
    for item in talks:
        assert isinstance(item, NewsItem)
        assert item.category == SourceCategory.TECH_TALK
        assert "youtube.com/watch" in item.url or "youtu.be/" in item.url
        assert len(item.summary) > 30



def test_tech_talks_prompt_fallback_and_html_rendering(tmp_path: Path):
    talk_item = NewsItem(
        title="Building Effective AI Agents: Architecture Patterns & Production Evals",
        url="https://www.youtube.com/watch?v=d5EltXhbcfA",
        source="Anthropic",
        category=SourceCategory.TECH_TALK,
        summary="Engineering breakdown of composable agent workflows versus autonomous multi-step loops.",
        published_at="2026-11-04",
        score=620,
    )
    paper_item = NewsItem(
        title="DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via RL",
        url="https://arxiv.org/abs/2501.12948",
        source="arXiv",
        category=SourceCategory.RESEARCH_PAPER,
        summary="Demonstrates pure reinforcement learning for reasoning models.",
        published_at="2026-11-06",
        score=420,
    )

    prompt = build_synthesis_prompt([paper_item, talk_item], ["AI Agents"], "2026-11-09")
    assert "## Tech Talks & Keynotes" in prompt
    assert "Building Effective AI Agents" in prompt

    fallback_md = build_fallback_markdown(
        items=[paper_item, talk_item],
        focus_topics=["AI Agents"],
        date_str="2026-11-09",
        breakdown={"arXiv": 1, "YouTube Tech Talks": 1},
    )
    assert "## Tech Talks & Keynotes" in fallback_md
    assert "- **[Building Effective AI Agents: Architecture Patterns & Production Evals](https://www.youtube.com/watch?v=d5EltXhbcfA)** — **Anthropic** · *2026-11-04*" in fallback_md
    assert "  - Engineering breakdown of composable agent workflows versus autonomous multi-step loops." in fallback_md
    for emoji in ("🚀", "🔥", "🎥", "📺", "▶️", "🎬"):
        assert emoji not in fallback_md

    digests_dir = tmp_path / "digests"
    docs_dir = tmp_path / "docs"
    ts = datetime(2026, 11, 9, 12, 0)
    save_markdown_digest(fallback_md, digests_dir, timestamp=ts, docs_dir=docs_dir)

    for html_file in (docs_dir / "index.html", docs_dir / "2026-11-09.html"):
        assert html_file.exists()
        content = html_file.read_text(encoding="utf-8")
        assert 'id="tech-talks"' in content
        assert "IV. Tech Talks &amp; Keynotes" in content
        assert '<a href="#tech-talks">Tech Talks</a>' in content
        assert "Watch on YouTube ↗" in content
        assert 'target="_blank" rel="noopener noreferrer"' in content
        assert "viewport-fit=cover" in content
        assert "max-width: 66ch;" in content


def test_published_docs_html_integrity():
    repo_docs = Path(__file__).resolve().parent.parent / "docs"
    if not repo_docs.exists():
        return
    required_channels = (
        "Google Cloud Tech",
        "IBM Technology",
        "The Pragmatic Engineer",
        "IBM Developer",
        "Stanford Online (CS25)",
        "LangChain",
    )
    for page in ("index.html", "2026-11-13.html"):
        html_path = repo_docs / page
        assert html_path.exists()
        text = html_path.read_text(encoding="utf-8")
        assert 'id="tech-talks"' in text
        assert "IV. Tech Talks &amp; Keynotes" in text
        assert '<a href="#tech-talks">Tech Talks</a>' in text
        assert "Watch on YouTube ↗" in text
        assert "viewport-fit=cover" in text
        assert "max-width: 66ch;" in text
        tech_talks_section = text.split('id="tech-talks"', 1)[1].split("</section>", 1)[0]
        for channel in required_channels:
            assert channel in tech_talks_section





