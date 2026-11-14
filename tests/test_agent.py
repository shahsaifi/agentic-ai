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
    prev_lines = [
        "# Digest 2026-11-08",
        "### 1. [Old Repeated Story](https://example.com/old-story)",
    ]
    for i in range(4):
        prev_lines.append(f"- **[Old X Thread {i}](https://x.com/researcher/status/{100 + i})** — *X.com*")
    for i in range(3):
        prev_lines.append(f"- **[Old Podcast {i}](https://example.com/pod-{i})** — *Podcast*")
    for i in range(8):
        prev_lines.append(f"- **[Old Tech Talk {i}](https://www.youtube.com/watch?v=talk00{i})** — **Channel**")
    (tmp_path / "2026-11-08_genai_digest.md").write_text("\n".join(prev_lines), encoding="utf-8")

    candidates = (
        [
            NewsItem(
                title="Old Repeated Story",
                url="https://example.com/old-story",
                source="HN",
                category=SourceCategory.COMMUNITY_NEWS,
            )
        ]
        + [
            NewsItem(
                title=f"Fresh Story {i}",
                url=f"https://example.com/fresh-{i}",
                source="arXiv",
                category=SourceCategory.RESEARCH_PAPER,
            )
            for i in range(10)
        ]
        + [
            NewsItem(
                title=f"Old X Thread {i}",
                url=f"https://x.com/researcher/status/{100 + i}",
                source="X",
                category=SourceCategory.SOCIAL_X,
            )
            for i in range(4)
        ]
        + [
            NewsItem(
                title=f"Old Podcast {i}",
                url=f"https://example.com/pod-{i}",
                source="Latent Space",
                category=SourceCategory.PODCAST,
            )
            for i in range(3)
        ]
        + [
            NewsItem(
                title=f"Old Tech Talk {i}",
                url=f"https://www.youtube.com/watch?v=talk00{i}",
                source="Google Cloud Tech",
                category=SourceCategory.TECH_TALK,
            )
            for i in range(8)
        ]
    )

    filtered = exclude_previously_published_items(
        items=candidates,
        output_dir=tmp_path,
        current_date_str="2026-11-09",
    )
    assert all(i.url != "https://example.com/old-story" for i in filtered)
    assert sum(1 for i in filtered if i.category == SourceCategory.SOCIAL_X) == 4
    assert sum(1 for i in filtered if i.category == SourceCategory.PODCAST) == 3
    assert sum(1 for i in filtered if i.category == SourceCategory.TECH_TALK) == 8



def test_reddit_waf_safe_links_and_rss_sanitization():
    from genai_agent.notifiers.markdown_store import (
        _extract_reddit_rss_excerpt,
        _find_reddit_discussion,
    )

    matched_curated, search_url = _find_reddit_discussion("Random Is Almost Enough Benchmark Compression via BestRand")
    assert isinstance(matched_curated, dict)
    for key in ("sub", "title", "url", "excerpt", "comments"):
        assert matched_curated.get(key)
    assert len(matched_curated["comments"]) >= 2
    assert "reddit.com/r/" not in search_url or "/search/" not in search_url
    assert search_url.startswith("https://www.google.com/search?q=site:reddit.com+")

    matched_fallback, fb_search_url = _find_reddit_discussion(
        "ZetaHyperion: Novel Topological Photonic Kernel Synthesis",
        summary="A completely novel architecture for optical tensor routing.",
        category="Research",
    )
    assert isinstance(matched_fallback, dict)
    for key in ("sub", "title", "url", "excerpt", "comments"):
        assert matched_fallback.get(key)
    assert len(matched_fallback["comments"]) >= 2
    assert fb_search_url.startswith("https://www.google.com/search?q=site:reddit.com+")

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
        _matches_focus_topics,
        _strip_youtube_boilerplate,
        fetch_ai_tech_talks,
    )

    assert not _matches_focus_topics("No AI, 52 min. Build all Linux Files utils in C by Hand", [])
    assert _matches_focus_topics("Deep Dive into LLM Reasoning and RLHF", [])


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
        assert '<a href="tech-talks.html"' in content
        assert "Tech Talks Index" in content
        assert '<a href="#tech-talks">Tech Talks</a>' not in content
        assert "Watch on YouTube ↗" in content
        assert "Read Thread on X ↗" in content
        assert '<details class="briefing-reddit">' in content
        assert '<div class="reddit-comment">' in content
        assert "No entries recorded for this issue." not in content.split("II. Researcher Threads on X", 1)[1].split("III. Audio", 1)[0]
        assert 'target="_blank" rel="noopener noreferrer"' in content
        assert "viewport-fit=cover" in content
        assert "max-width: 66ch;" in content



    tech_talks_html = docs_dir / "tech-talks.html"
    assert tech_talks_html.exists()
    tt_content = tech_talks_html.read_text(encoding="utf-8")
    assert '<a href="tech-talks.html" class="active">Tech Talks Index</a>' in tt_content
    assert "YOUTUBE CHANNEL ↗" in tt_content
    assert "Watch on YouTube ↗" in tt_content


def test_tech_talks_hub_all_13_channels():
    from genai_agent.collectors.tech_talks import (
        _is_valid_youtube_url,
        fetch_detailed_tech_talks_hub,
    )

    expected_all_13 = [
        "Google Cloud Tech",
        "IBM Technology",
        "The Pragmatic Engineer",
        "IBM Developer",
        "Stanford Online (CS25)",
        "LangChain",
        "Andrej Karpathy",
        "Anthropic",
        "OpenAI",
        "Google DeepMind",
        "AI Engineer",
        "Latent Space",
        "Weights & Biases",
    ]
    hub_data = fetch_detailed_tech_talks_hub(videos_per_channel=3, fetch_live=False)
    assert len(hub_data) == 13
    assert [ch["name"] for ch in hub_data] == expected_all_13
    for ch in hub_data:
        assert ch.get("host")
        assert ch.get("channel_url", "").startswith("https://www.youtube.com/")
        videos = ch.get("videos", [])
        assert len(videos) >= 1
        for vid in videos:
            assert _is_valid_youtube_url(vid["url"])
            assert len(vid.get("summary", "")) > 25


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
    for page in ("index.html", "2026-11-14.html", "2026-11-13.html"):
        html_path = repo_docs / page
        assert html_path.exists()
        text = html_path.read_text(encoding="utf-8")
        assert 'id="tech-talks"' in text
        assert "IV. Tech Talks &amp; Keynotes" in text
        assert '<a href="tech-talks.html"' in text
        assert "Tech Talks Index" in text
        assert '<a href="#tech-talks">Tech Talks</a>' not in text
        assert "Watch on YouTube ↗" in text
        assert "Read Thread on X ↗" in text
        assert "viewport-fit=cover" in text
        assert "max-width: 66ch;" in text
        tech_talks_section = text.split('id="tech-talks"', 1)[1].split("</section>", 1)[0]
        for channel in required_channels:
            assert channel in tech_talks_section

    for latest_page in ("index.html", "2026-11-14.html"):
        latest_text = (repo_docs / latest_page).read_text(encoding="utf-8")
        assert "Read Thread on X ↗" in latest_text
        assert "No entries recorded for this issue." not in latest_text
        assert latest_text.count('<details class="briefing-reddit">') == 10
        assert latest_text.count('<div class="reddit-comment">') == 20



    for nav_page in ("tech-talks.html", "index.html", "podcasts.html", "2026-11-14.html"):
        nav_path = repo_docs / nav_page
        assert nav_path.exists()
        nav_text = nav_path.read_text(encoding="utf-8")
        assert '<a href="tech-talks.html"' in nav_text
        assert "Tech Talks Index" in nav_text
        assert '<a href="#tech-talks">Tech Talks</a>' not in nav_text
        assert '<a href="#subscribe">Subscribe</a>' in nav_text
        assert 'id="subscribe"' in nav_text
        assert 'class="subscribe-box"' in nav_text
        assert "font-size: 16px;" in nav_text

    tt_text = (repo_docs / "tech-talks.html").read_text(encoding="utf-8")
    for idx in range(1, 14):
        assert f'id="channel-{idx}"' in tt_text
        assert f">{idx:02d}. " in tt_text
    assert "YOUTUBE CHANNEL ↗" in tt_text
    assert "Watch on YouTube ↗" in tt_text
    assert 'target="_blank" rel="noopener noreferrer"' in tt_text

    cname_path = repo_docs / "CNAME"
    assert cname_path.exists()
    assert cname_path.read_text(encoding="utf-8").strip() == "jabi.io"

    feed_path = repo_docs / "feed.xml"
    assert feed_path.exists()
    feed_xml = feed_path.read_text(encoding="utf-8")
    assert '<rss version="2.0"' in feed_xml
    assert "<link>https://jabi.io/</link>" in feed_xml
    assert "<item>" in feed_xml

    ads_path = repo_docs / "ads.txt"
    assert ads_path.exists()

    privacy_path = repo_docs / "privacy.html"
    assert privacy_path.exists()
    privacy_text = privacy_path.read_text(encoding="utf-8")
    assert "Google AdSense" in privacy_text
    assert "adssettings.google.com" in privacy_text


def test_subscribe_rss_and_adsense_readiness(tmp_path: Path, monkeypatch):
    import xml.etree.ElementTree as ET

    monkeypatch.setenv("GOOGLE_ADSENSE_CLIENT_ID", "ca-pub-1234567890123456")

    md = (
        "# Generative AI Technical Briefing — 2026-11-14\n\n"
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Test Frontier Paper](https://arxiv.org/abs/2611.00001)\n"
        "**Research** (arXiv) · 120 pts · *2026-11-14*\n"
        "- Rigorous architectural evaluation of test-time compute scaling.\n"
    )
    digests_dir = tmp_path / "digests"
    docs_dir = tmp_path / "docs"
    save_markdown_digest(md, digests_dir, timestamp=datetime(2026, 11, 14, 9, 0), docs_dir=docs_dir)

    assert (docs_dir / "CNAME").read_text(encoding="utf-8").strip() == "jabi.io"

    ads_txt = (docs_dir / "ads.txt").read_text(encoding="utf-8").strip()
    assert ads_txt == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0"

    feed_xml = (docs_dir / "feed.xml").read_text(encoding="utf-8")
    root = ET.fromstring(feed_xml)
    assert root.tag == "rss"
    assert "https://jabi.io" in feed_xml

    privacy_html = (docs_dir / "privacy.html").read_text(encoding="utf-8")
    assert "Google AdSense" in privacy_html
    assert "adssettings.google.com" in privacy_html

    for page_name in ("index.html", "2026-11-14.html", "tech-talks.html", "privacy.html"):
        page_html = (docs_dir / page_name).read_text(encoding="utf-8")
        assert '<meta name="google-adsense-account" content="ca-pub-1234567890123456">' in page_html
        assert "adsbygoogle.js?client=ca-pub-1234567890123456" in page_html
        assert 'id="subscribe"' in page_html
        assert '<a href="#subscribe">Subscribe</a>' in page_html

    index_html = (docs_dir / "index.html").read_text(encoding="utf-8")
    assert '<ins class="adsbygoogle"' in index_html







