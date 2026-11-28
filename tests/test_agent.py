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
    from genai_agent.notifiers import markdown_store as ms
    from genai_agent.notifiers.markdown_store import _build_reddit_search_url

    # Synthetic Reddit generators/curated fakes must no longer exist
    for removed_symbol in (
        "_extract_reddit_rss_excerpt",
        "_find_reddit_discussion",
        "CURATED_REDDIT_DISCUSSIONS",
    ):
        assert not hasattr(ms, removed_symbol), f"Synthetic Reddit symbol {removed_symbol} should be removed"

    search_url = _build_reddit_search_url("Random Is Almost Enough: Benchmark Compression via BestRand")
    assert search_url.startswith("https://www.google.com/search?q=site:reddit.com+")
    assert "/comments/1gn" not in search_url
    assert "reddit.com/r/" not in search_url

    fallback_url = _build_reddit_search_url("The and for with from")
    assert fallback_url.startswith("https://www.google.com/search?q=site:reddit.com+")



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
        assert "briefing-reddit" not in content
        assert "reddit-comment" not in content
        assert "/comments/1gn" not in content
        assert "Find on Reddit" in content
        assert "https://www.google.com/search?q=site:reddit.com+" in content
        assert 'class="editorial-callout"' in content
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
        assert "briefing-reddit" not in text
        assert "reddit-comment" not in text
        assert "/comments/1gn" not in text
        assert "Find on Reddit" in text
        assert 'class="editorial-callout"' in text
        if page in ("2026-11-14.html", "2026-11-13.html"):
            tech_talks_section = text.split('id="tech-talks"', 1)[1].split("</section>", 1)[0]
            for channel in required_channels:
                assert channel in tech_talks_section

    for latest_page in ("index.html", "2026-11-14.html"):
        latest_text = (repo_docs / latest_page).read_text(encoding="utf-8")
        assert "Read Thread on X ↗" in latest_text
        assert "No entries recorded for this issue." not in latest_text
        assert "briefing-reddit" not in latest_text
        assert "reddit-comment" not in latest_text
        assert "Find on Reddit" in latest_text



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
    monkeypatch.delenv("GOOGLE_ADSENSE_SLOT_ID", raising=False)

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

    legal_no_ad_pages = ("contact.html", "terms.html", "privacy.html")
    trust_pages = ("about.html", "faq.html", "contact.html", "terms.html", "privacy.html")
    all_generated_pages = sorted(p.name for p in docs_dir.glob("*.html"))
    assert "index.html" in all_generated_pages
    assert "2026-11-14.html" in all_generated_pages
    assert "about.html" in all_generated_pages
    assert "guides.html" in all_generated_pages

    # State (a): GOOGLE_ADSENSE_CLIENT_ID set, GOOGLE_ADSENSE_SLOT_ID unset/empty
    for page_name in all_generated_pages:
        page_html = (docs_dir / page_name).read_text(encoding="utf-8")
        head_html = page_html.split("</head>", 1)[0]
        style_pos = head_html.find("<style>")
        assert style_pos != -1, f"{page_name} missing <style> in <head>"

        # Every page has SEO meta/canonical BEFORE <style>
        for marker in ('<meta name="description"', '<link rel="canonical"'):
            pos = head_html.find(marker)
            assert pos != -1, f"{page_name} missing {marker} in <head>"
            assert pos < style_pos, f"{page_name}: {marker} must appear before <style>"

        if page_name in legal_no_ad_pages:
            assert "google-adsense-account" not in page_html, f"{page_name} must not include google-adsense-account"
            assert "adsbygoogle.js" not in page_html, f"{page_name} must not include adsbygoogle.js"
        else:
            for marker in (
                '<meta name="google-adsense-account" content="ca-pub-1234567890123456">',
                "adsbygoogle.js?client=ca-pub-1234567890123456",
            ):
                pos = head_html.find(marker)
                assert pos != -1, f"{page_name} missing {marker} in <head>"
                assert pos < style_pos, f"{page_name}: {marker} must appear before <style>"

    for page_name in ("index.html", "2026-11-14.html", "tech-talks.html", "privacy.html"):
        page_html = (docs_dir / page_name).read_text(encoding="utf-8")
        assert 'id="subscribe"' in page_html
        assert '<a href="#subscribe">Subscribe</a>' in page_html
        assert "sibforms.com/serve/" in page_html
        assert 'name="EMAIL"' in page_html
        assert "beehiiv" not in page_html.lower()

    for page_name in ("index.html", "2026-11-14.html"):
        page_html = (docs_dir / page_name).read_text(encoding="utf-8")
        body_after_style = page_html.split("</style>")[-1]
        assert '<ins class="adsbygoogle"' not in page_html
        assert "editorial-ad-slot" not in body_after_style

    # State (b): GOOGLE_ADSENSE_CLIENT_ID set + valid GOOGLE_ADSENSE_SLOT_ID
    monkeypatch.setenv("GOOGLE_ADSENSE_SLOT_ID", "1234567890")
    save_markdown_digest(md, digests_dir, timestamp=datetime(2026, 11, 14, 9, 0), docs_dir=docs_dir)

    for page_name in ("index.html", "2026-11-14.html"):
        page_html = (docs_dir / page_name).read_text(encoding="utf-8")
        body_after_style = page_html.split("</style>")[-1]
        assert '<ins class="adsbygoogle"' in body_after_style
        assert 'data-ad-slot="1234567890"' in body_after_style
        assert "editorial-ad-slot" in body_after_style

    for page_name in trust_pages:
        page_html = (docs_dir / page_name).read_text(encoding="utf-8")
        body_after_style = page_html.split("</style>")[-1]
        assert '<ins class="adsbygoogle"' not in page_html
        assert "editorial-ad-slot" not in body_after_style

    # State (c): Invalid GOOGLE_ADSENSE_SLOT_ID values do NOT render <ins class="adsbygoogle"
    for invalid_slot in ("abc", "123", "12345", "123456789012345678901", "123456abc"):
        monkeypatch.setenv("GOOGLE_ADSENSE_SLOT_ID", invalid_slot)
        save_markdown_digest(md, digests_dir, timestamp=datetime(2026, 11, 14, 9, 0), docs_dir=docs_dir)
        for page_name in ("index.html", "2026-11-14.html"):
            page_html = (docs_dir / page_name).read_text(encoding="utf-8")
            body_after_style = page_html.split("</style>")[-1]
            assert '<ins class="adsbygoogle"' not in page_html, f"invalid slot {invalid_slot!r} rendered <ins>"
            assert "editorial-ad-slot" not in body_after_style, f"invalid slot {invalid_slot!r} rendered ad wrapper"


def test_adsense_prerequisites_crawlability_and_trust_pages(tmp_path: Path, monkeypatch):
    import re
    import xml.etree.ElementTree as ET

    monkeypatch.setenv("GOOGLE_ADSENSE_CLIENT_ID", "ca-pub-1234567890123456")
    monkeypatch.setenv("GOOGLE_ADSENSE_SLOT_ID", "1234567890")
    monkeypatch.setenv("CONTACT_EMAIL", "")

    md = (
        "# Generative AI Technical Briefing — 2026-11-14\n\n"
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Test Frontier Paper](https://arxiv.org/abs/2611.00001)\n"
        "**Research** (arXiv) · 120 pts · *2026-11-14*\n"
        "- Rigorous architectural evaluation of test-time compute scaling.\n"
    )
    docs_dir = tmp_path / "docs"
    save_markdown_digest(md, tmp_path / "digests", timestamp=datetime(2026, 11, 14, 9, 0), docs_dir=docs_dir)

    # robots.txt explicitly allows AdSense crawlers + all crawlers and advertises the sitemap
    robots = (docs_dir / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: Mediapartners-Google" in robots
    assert "User-agent: Google-Display-Ads-Bot" in robots
    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert "Sitemap: https://jabi.io/sitemap.xml" in robots
    assert "Disallow" not in robots

    # sitemap is valid XML, deduplicated (excludes latest_date duplicate and legal utility pages),
    # and lists core + editorial/evergreen pages
    sitemap = (docs_dir / "sitemap.xml").read_text(encoding="utf-8")
    root = ET.fromstring(sitemap)
    locs = [el.text for el in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    for expected in (
        "https://jabi.io/",
        "https://jabi.io/about.html",
        "https://jabi.io/faq.html",
        "https://jabi.io/guides.html",
        "https://jabi.io/guide-agent-harness-engineering.html",
        "https://jabi.io/guide-llm-inference-quantization.html",
        "https://jabi.io/guide-rag-context-engineering.html",
        "https://jabi.io/guide-llm-evaluation-benchmarks.html",
        "https://jabi.io/guide-cascaded-model-routing.html",
    ):
        assert expected in locs, f"sitemap.xml missing {expected}"
    for excluded in (
        "https://jabi.io/2026-11-14.html",
        "https://jabi.io/contact.html",
        "https://jabi.io/terms.html",
        "https://jabi.io/privacy.html",
    ):
        assert excluded not in locs, f"sitemap.xml should exclude {excluded}"

    # trust pages exist and every page footer links to all of them, with proper <head> ordering
    legal_no_ad_pages = ("contact.html", "terms.html", "privacy.html")
    trust_pages = ("about.html", "faq.html", "contact.html", "terms.html", "privacy.html")
    for name in trust_pages:
        assert (docs_dir / name).exists()
    every_page = ("index.html", "2026-11-14.html", "tech-talks.html", "guides.html") + trust_pages
    for name in every_page:
        page = (docs_dir / name).read_text(encoding="utf-8")
        for link in ('href="about.html"', 'href="faq.html"', 'href="contact.html"',
                     'href="terms.html"', 'href="privacy.html"'):
            assert link in page, f"{name} missing {link}"
        head = page.split("</head>", 1)[0]
        style_pos = head.find("<style>")
        assert style_pos != -1
        for marker in ('<meta name="description"', '<link rel="canonical"'):
            pos = head.find(marker)
            assert pos != -1, f"{name} missing {marker}"
            assert pos < style_pos, f"{name}: {marker} must appear before <style>"
        if name in legal_no_ad_pages:
            assert "google-adsense-account" not in page
            assert "adsbygoogle.js" not in page
        else:
            for marker in ('<meta name="google-adsense-account"', "adsbygoogle.js?client="):
                pos = head.find(marker)
                assert pos != -1, f"{name} missing {marker}"
                assert pos < style_pos, f"{name}: {marker} must appear before <style>"

    # About and FAQ have substantial original text
    faq_text = re.sub(r"<[^>]+>", " ", (docs_dir / "faq.html").read_text(encoding="utf-8"))
    assert len(faq_text.split()) >= 400
    about_text = re.sub(r"<[^>]+>", " ", (docs_dir / "about.html").read_text(encoding="utf-8"))
    assert len(about_text.split()) >= 400

    # contact page defaults to mailto:editor@jabi.io and respects CONTACT_EMAIL override
    contact_default = (docs_dir / "contact.html").read_text(encoding="utf-8")
    assert "mailto:editor@jabi.io" in contact_default
    assert "github.com" in contact_default and "issues" in contact_default
    contact_body = contact_default.split("</header>", 1)[1].split("<footer", 1)[0]
    assert 'href="faq.html"' not in contact_body

    monkeypatch.setenv("CONTACT_EMAIL", "editor@example.com")
    save_markdown_digest(md, tmp_path / "digests", timestamp=datetime(2026, 11, 14, 9, 0), docs_dir=docs_dir)
    assert "mailto:editor@example.com" in (docs_dir / "contact.html").read_text(encoding="utf-8")

    # ad slots: never on trust pages, never near the subscribe box or other controls
    for name in trust_pages:
        page = (docs_dir / name).read_text(encoding="utf-8")
        assert "editorial-ad-slot" not in page.split("</style>")[-1]
        assert '<ins class="adsbygoogle"' not in page
    for name in ("index.html", "2026-11-14.html"):
        body = (docs_dir / name).read_text(encoding="utf-8").split("</style>")[-1]
        sub_pos = body.find('class="subscribe-box"')
        matches = list(re.finditer(r'<ins class="adsbygoogle"', body))
        assert len(matches) >= 1, f"Expected rendered ad slot in {name} when GOOGLE_ADSENSE_SLOT_ID is valid"
        for m in matches:
            assert abs(m.start() - sub_pos) > 1500


def test_zero_synthetic_reddit_and_x_template_filler(tmp_path: Path, monkeypatch):
    from genai_agent.collectors import social_x
    from genai_agent.notifiers.markdown_store import _clean_excerpt

    # 1. Verify _clean_excerpt strips legacy X template filler
    template_samples = [
        "Technical thread from @karpathy examining nanoGPT scaling, generating active engineering debate across 120 comments (450 pts).",
        "Industry analysis and researcher commentary on X examining DeepSeek R2, reported by VentureBeat.",
        "Researcher and engineering discussion on X examining test-time compute.",
    ]
    for sample in template_samples:
        cleaned = _clean_excerpt(sample)
        assert "Technical thread from @" not in cleaned
        assert "Industry analysis and researcher commentary on X examining" not in cleaned
        assert "Researcher and engineering discussion on X examining" not in cleaned

    # 2. Verify fetch_hn_x_threads never emits template filler
    class _FakeResp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "hits": [
                    {
                        "title": "Karpathy on agent harnesses",
                        "url": "https://x.com/karpathy/status/1234567890",
                        "objectID": "999001",
                        "points": 320,
                        "num_comments": 85,
                        "created_at": "2026-11-27T10:00:00Z",
                        "story_text": "",
                    }
                ]
            }

    class _FakeClient:
        def __init__(self, *a, **kw):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, *a, **kw):
            return _FakeResp()

    monkeypatch.setattr(social_x.httpx, "Client", _FakeClient)
    hn_x_items = social_x.fetch_hn_x_threads(limit=2)
    assert len(hn_x_items) == 1
    assert "Technical thread from @" not in hn_x_items[0].summary

    # 3. Verify rendered HTML has zero synthetic Reddit blocks and zero X template filler
    md = (
        "# Generative AI Technical Briefing — 2026-11-27\n\n"
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Deterministic Agent Harnesses](https://arxiv.org/abs/2611.01234)\n"
        "**Research** (arXiv) · 180 pts · *2026-11-27*\n"
        "- Evaluates bounded tool loops and deterministic verification gates.\n\n"
        "## Notable X Threads\n\n"
        "- **[Karpathy on agent harnesses](https://x.com/karpathy/status/1234567890)** — *X.com (@karpathy)*\n"
        "  - Technical thread from @karpathy examining agent harnesses, generating active engineering debate.\n"
    )
    docs_dir = tmp_path / "docs"
    save_markdown_digest(md, tmp_path / "digests", timestamp=datetime(2026, 11, 27, 9, 0), docs_dir=docs_dir)
    for page in ("index.html", "2026-11-27.html"):
        html = (docs_dir / page).read_text(encoding="utf-8")
        assert "briefing-reddit" not in html
        assert "reddit-comment" not in html
        assert "/comments/1gn" not in html
        assert "Find on Reddit" in html
        assert "https://www.google.com/search?q=site:reddit.com+" in html
        assert "Technical thread from @" not in html
        assert "Industry analysis and researcher commentary on X examining" not in html
        assert "Researcher and engineering discussion on X examining" not in html


def test_excerpt_and_podcast_sanitization():
    from genai_agent.agent import _clean_sentence_excerpt
    from genai_agent.collectors.podcasts import _strip_html
    from genai_agent.notifiers.markdown_store import _clean_excerpt

    # Bare URLs, archive.ph, HTML-encoded URLs, See also, profanity
    junk_cases = [
        "https://archive.ph/abc123",
        "https:&#x2F;&#x2F;archive.ph&#x2F;xyz987",
        "https://example.com/only-a-url",
        "See also: https://news.ycombinator.com/item?id=12345",
        "This shit is completely broken in production.",
        "What the fuck happened to the KV cache benchmark?",
    ]
    for raw in junk_cases:
        assert _clean_sentence_excerpt(raw) == "", f"_clean_sentence_excerpt failed on {raw!r}"
        assert _clean_excerpt(raw) == "", f"_clean_excerpt failed on {raw!r}"

    # Podcast sponsor ad copy
    sponsor_desc = (
        "Show Links • Get the top 80+ AI Models at aibox.ai for $8.99 • "
        "Join our community at https://www.skool.com/ai-box — "
        "In this episode we benchmark FP8 quantization on H200 clusters."
    )
    for fn in (_clean_sentence_excerpt, _clean_excerpt, _strip_html):
        cleaned = fn(sponsor_desc)
        assert "Show Links" not in cleaned
        assert "aibox.ai" not in cleaned
        assert "skool.com" not in cleaned
        assert "$8.99" not in cleaned
        assert "FP8 quantization" in cleaned

    # Clean legitimate technical sentence preserved
    good = "Speculative decoding reduces decode latency by 2.1x without altering output distribution."
    assert _clean_sentence_excerpt(good) == good
    assert _clean_excerpt(good) == good
    assert _strip_html(f"<p>{good}</p>") == good


def test_editorial_synthesis_callout_and_fallback_summary(tmp_path: Path):
    items = [
        NewsItem(
            title="Sparse Attention at 1M Context",
            url="https://arxiv.org/abs/2611.09999",
            source="arXiv",
            category=SourceCategory.RESEARCH_PAPER,
            summary="Demonstrates linear-time sparse attention kernels for million-token prefill.",
            published_at="2026-11-27",
            score=500,
        ),
        NewsItem(
            title="Show HN: Zero-Copy KV Cache Engine in Rust",
            url="https://example.com/kv-rust",
            source="Hacker News",
            category=SourceCategory.COMMUNITY_NEWS,
            summary="Systems breakdown of paged KV cache allocation with zero heap fragmentation.",
            published_at="2026-11-27",
            score=410,
        ),
        NewsItem(
            title="Anthropic Engineering: Deterministic Eval Harnesses",
            url="https://www.anthropic.com/engineering/evals",
            source="Anthropic",
            category=SourceCategory.COMPANY_BLOG,
            summary="Production methodology for grading multi-turn coding agents.",
            published_at="2026-11-27",
            score=350,
        ),
    ]

    fallback_md = build_fallback_markdown(
        items=items,
        focus_topics=["Inference", "AI Agents"],
        date_str="2026-11-27",
        breakdown={"arXiv": 1, "Hacker News": 1, "Anthropic": 1},
    )
    assert "## Executive Summary" in fallback_md
    assert "Lead Technical Signal" in fallback_md
    assert "Engineering & Community Focus" in fallback_md
    assert "Lab & Ecosystem Update" in fallback_md
    assert fallback_md.find("## Executive Summary") < fallback_md.find("## Top 10 Ranked Briefing")

    docs_dir = tmp_path / "docs"
    save_markdown_digest(fallback_md, tmp_path / "digests", timestamp=datetime(2026, 11, 27, 9, 0), docs_dir=docs_dir)
    for page in ("index.html", "2026-11-27.html"):
        html = (docs_dir / page).read_text(encoding="utf-8")
        body = html.split("</style>", 1)[1]
        callout_pos = body.find('class="editorial-callout"')
        sec1_pos = body.find("<h2>I. ")
        assert callout_pos != -1, f"{page} missing .editorial-callout"
        assert sec1_pos != -1, f"{page} missing Section I heading"
        assert callout_pos < sec1_pos, f"{page}: .editorial-callout must appear above Section I"


def test_evergreen_guides_generation_and_standards(tmp_path: Path):
    import re

    emoji_re = re.compile(
        "["
        "\U0001F300-\U0001F9FF"
        "\U0001FA00-\U0001FAFF"
        "\u2600-\u26FF"
        "\u2700-\u27BF"
        "\uFE0F"
        "]"
    )
    expected_guides = (
        "guide-agent-harness-engineering.html",
        "guide-llm-inference-quantization.html",
        "guide-rag-context-engineering.html",
        "guide-llm-evaluation-benchmarks.html",
        "guide-cascaded-model-routing.html",
    )

    md = (
        "# Generative AI Technical Briefing — 2026-11-27\n\n"
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Test Frontier Paper](https://arxiv.org/abs/2611.00001)\n"
        "**Research** (arXiv) · 120 pts · *2026-11-27*\n"
        "- Rigorous architectural evaluation of test-time compute scaling.\n"
    )
    docs_dir = tmp_path / "docs"
    save_markdown_digest(md, tmp_path / "digests", timestamp=datetime(2026, 11, 27, 9, 0), docs_dir=docs_dir)

    guides_index = docs_dir / "guides.html"
    assert guides_index.exists()
    gi_html = guides_index.read_text(encoding="utf-8")
    assert "viewport-fit=cover" in gi_html
    assert "max-width: 66ch;" in gi_html
    assert not emoji_re.search(gi_html)

    index_html = (docs_dir / "index.html").read_text(encoding="utf-8")
    assert 'href="guides.html"' in index_html

    for guide_file in expected_guides:
        path = docs_dir / guide_file
        assert path.exists(), f"Missing generated guide {guide_file}"
        html = path.read_text(encoding="utf-8")
        assert "viewport-fit=cover" in html
        assert "max-width: 66ch;" in html
        assert not emoji_re.search(html), f"Emoji found in {guide_file}"
        assert 'href="guides.html"' in html
        assert f'href="{guide_file}"' in gi_html
        assert f'href="{guide_file}"' in index_html
        body = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.S)
        body = re.sub(r"<script[^>]*>.*?</script>", " ", body, flags=re.S)
        article = body.split("<article", 1)[1].split("</article>", 1)[0]
        word_count = len(re.sub(r"<[^>]+>", " ", article).split())
        assert word_count >= 800, f"{guide_file} has only {word_count} words (< 800)"


def test_trust_eeat_seo_hygiene_and_duplicate_issue_canonical(tmp_path: Path, monkeypatch):
    import xml.etree.ElementTree as ET

    monkeypatch.setenv("GOOGLE_ADSENSE_CLIENT_ID", "ca-pub-1234567890123456")
    monkeypatch.delenv("CONTACT_EMAIL", raising=False)

    digests_dir = tmp_path / "digests"
    docs_dir = tmp_path / "docs"
    digests_dir.mkdir(parents=True, exist_ok=True)

    # Create historical digests where 2026-11-07 duplicates 2026-11-06 Top 10, plus a distinct latest 2026-11-14
    dup_body = (
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Shared Paper](https://arxiv.org/abs/2611.00006)\n"
        "**Research** (arXiv) · 120 pts · *2026-11-06*\n"
        "- Technical evaluation of inference scaling laws.\n"
    )
    for d in ("2026-11-06", "2026-11-07"):
        md = f"# Generative AI Technical Briefing — {d}\n\n{dup_body}"
        save_markdown_digest(md, digests_dir, timestamp=datetime.strptime(d, "%Y-%m-%d"), docs_dir=docs_dir)

    latest_md = (
        "# Generative AI Technical Briefing — 2026-11-14\n\n"
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Fresh Latest Paper](https://arxiv.org/abs/2611.00014)\n"
        "**Research** (arXiv) · 150 pts · *2026-11-14*\n"
        "- Novel sparse attention benchmark.\n"
    )
    save_markdown_digest(latest_md, digests_dir, timestamp=datetime(2026, 11, 14), docs_dir=docs_dir)

    # Duplicate issue 2026-11-07.html carries canonical -> 2026-11-06.html and noindex, follow
    dup_html = (docs_dir / "2026-11-07.html").read_text(encoding="utf-8")
    assert '<link rel="canonical" href="https://jabi.io/2026-11-06.html">' in dup_html
    assert '<meta name="robots" content="noindex, follow">' in dup_html

    # FAQ has no "Reddit brief" and documents Guides + Editorial Synthesis
    faq_html = (docs_dir / "faq.html").read_text(encoding="utf-8")
    assert "Reddit brief" not in faq_html
    assert "Guides" in faq_html or "guides.html" in faq_html
    assert "Editorial Synthesis" in faq_html

    # sitemap.xml excludes latest (2026-11-14.html), duplicate (2026-11-07.html), and legal pages;
    # includes 2026-11-06.html, about.html, guides.html, and all 5 guide-*.html
    root = ET.fromstring((docs_dir / "sitemap.xml").read_text(encoding="utf-8"))
    locs = [el.text for el in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert len(locs) == len(set(locs)), "sitemap.xml contains duplicate URLs"
    assert "https://jabi.io/2026-11-06.html" in locs
    assert "https://jabi.io/about.html" in locs
    assert "https://jabi.io/guides.html" in locs
    for excluded in (
        "https://jabi.io/2026-11-14.html",
        "https://jabi.io/2026-11-07.html",
        "https://jabi.io/contact.html",
        "https://jabi.io/terms.html",
        "https://jabi.io/privacy.html",
    ):
        assert excluded not in locs, f"sitemap.xml must exclude {excluded}"

    # Legal/utility pages have ZERO AdSense tags; content pages retain them
    for lp in ("contact.html", "terms.html", "privacy.html"):
        t = (docs_dir / lp).read_text(encoding="utf-8")
        assert "adsbygoogle.js" not in t
        assert "google-adsense-account" not in t
    for cp in ("index.html", "about.html", "faq.html", "guides.html", "guide-agent-harness-engineering.html"):
        t = (docs_dir / cp).read_text(encoding="utf-8")
        assert "adsbygoogle.js" in t
        assert "google-adsense-account" in t


def _assert_site_seo_invariants(docs_dir: Path, expected_daily_lead_keywords: dict[str, tuple[str, ...]] | None = None) -> None:
    """Shared SEO invariant assertions for generated and published docs/ sites."""
    import html as html_mod
    import json
    import re
    import xml.etree.ElementTree as ET

    html_files = sorted(p for p in docs_dir.glob("*.html") if p.name != "google1d91ff2686f20108.html")
    assert html_files, f"No HTML files found in {docs_dir}"

    for page_path in html_files:
        name = page_path.name
        text = page_path.read_text(encoding="utf-8")

        # 1. Single <h1> per page (masthead <h1> on index.html; <div class="masthead-title"> + 1 page <h1> on subpages)
        h1_matches = re.findall(r"<h1\b[^>]*>.*?</h1>", text, flags=re.S)
        assert len(h1_matches) == 1, f"{name}: expected exactly 1 <h1>, found {len(h1_matches)}"
        if name == "index.html":
            assert '<h1 class="masthead-title">' in text, "index.html must use <h1 class=\"masthead-title\">"
        else:
            assert '<div class="masthead-title">' in text, f"{name} must use <div class=\"masthead-title\">"

        # 2. Valid Schema.org JSON-LD (application/ld+json)
        ld_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text, flags=re.S)
        ld_types: list[str] = []
        ld_nodes: list[dict] = []
        for raw_ld in ld_blocks:
            parsed = json.loads(raw_ld)
            graph = parsed.get("@graph", [parsed])
            for node in graph:
                if isinstance(node, dict):
                    ld_nodes.append(node)
                    if "@type" in node:
                        ld_types.append(node["@type"])

        if name == "index.html":
            assert "WebSite" in ld_types and "Organization" in ld_types, f"index.html JSON-LD missing WebSite/Organization: {ld_types}"
        elif name.startswith("guide-"):
            assert "TechArticle" in ld_types and "BreadcrumbList" in ld_types, f"{name} JSON-LD missing TechArticle/BreadcrumbList: {ld_types}"
        elif name == "faq.html":
            assert "FAQPage" in ld_types, f"faq.html JSON-LD missing FAQPage: {ld_types}"
            faq_node = next(n for n in ld_nodes if n.get("@type") == "FAQPage")
            entries = faq_node.get("mainEntity", [])
            assert len(entries) >= 3, f"faq.html FAQPage mainEntity too small: {len(entries)}"
            for entry in entries:
                assert entry.get("@type") == "Question"
                assert entry.get("name")
                answer = entry.get("acceptedAnswer", {})
                assert answer.get("@type") == "Answer"
                answer_text = answer.get("text", "")
                assert answer_text
                assert not re.search(r"<[^>]+>", answer_text), f"Raw HTML tag found in FAQ acceptedAnswer.text: {answer_text!r}"
        elif re.match(r"^\d{4}-\d{2}-\d{2}\.html$", name):
            assert "CollectionPage" in ld_types and "BreadcrumbList" in ld_types, f"{name} JSON-LD missing CollectionPage/BreadcrumbList: {ld_types}"

        # 3. Titles & Descriptions
        m_title = re.search(r"<title>(.*?)</title>", text, flags=re.S)
        assert m_title, f"{name}: missing <title>"
        page_title = html_mod.unescape(m_title.group(1).strip())
        m_desc = re.search(r'<meta name="description" content="([^"]*)"', text)
        assert m_desc and m_desc.group(1).strip(), f"{name}: missing <meta name=\"description\">"
        page_desc = html_mod.unescape(m_desc.group(1).strip())

        if re.match(r"^\d{4}-\d{2}-\d{2}\.html$", name):
            date_slug = name[:-5]
            assert page_title != f"The GenAI Briefing — {date_slug}", f"{name}: bare title without lead story keywords"
            if expected_daily_lead_keywords and name in expected_daily_lead_keywords:
                lead_title_kw, lead_desc_kws = expected_daily_lead_keywords[name][0], expected_daily_lead_keywords[name]
                assert lead_title_kw in page_title, f"{name}: <title> {page_title!r} missing lead keyword {lead_title_kw!r}"
                for kw in lead_desc_kws:
                    assert kw in page_desc, f"{name}: meta description {page_desc!r} missing lead story {kw!r}"

        if name.startswith("guide-"):
            assert len(page_title) <= 68, f"{name}: guide <title> exceeds 68 chars ({len(page_title)}): {page_title!r}"
            h1_text = html_mod.unescape(re.sub(r"<[^>]+>", "", h1_matches[0]).strip())
            tech_node = next(n for n in ld_nodes if n.get("@type") == "TechArticle")
            assert tech_node.get("headline") == h1_text, f"{name}: JSON-LD headline {tech_node.get('headline')!r} != <h1> {h1_text!r}"
            assert len(h1_text) > len(page_title.split(" — ")[0]), f"{name}: <h1> should preserve full guide title"

        # 4. Open Graph & Twitter Cards
        for meta_marker in (
            'property="og:title"',
            'name="twitter:card"',
            'name="twitter:title"',
            'name="twitter:description"',
            'name="twitter:image"',
        ):
            assert meta_marker in text, f"{name}: missing {meta_marker}"

        # 5. Canonical Home Links (zero href="index.html")
        assert 'href="index.html' not in text, f"{name}: contains legacy href=\"index.html\""
        assert 'href="/"' in text, f"{name}: missing canonical home link href=\"/\""
        assert 'href="/#archive"' in text, f"{name}: missing canonical archive link href=\"/#archive\""

        # 6. Daily -> Evergreen Guides Cross-Linking
        if re.match(r"^\d{4}-\d{2}-\d{2}\.html$", name):
            assert 'id="evergreen-guides"' in text, f"{name}: missing id=\"evergreen-guides\""
            guides_sec = text.split('id="evergreen-guides"', 1)[1].split("</section>", 1)[0]
            assert 'href="guides.html"' in guides_sec, f"{name}: evergreen-guides missing href=\"guides.html\""
            guide_hrefs = set(re.findall(r'href="(guide-[^"]+\.html)"', guides_sec))
            assert len(guide_hrefs) == 3, f"{name}: evergreen-guides expected 3 unique guide links, got {len(guide_hrefs)}"

    # Valid sitemap.xml and feed.xml
    sitemap_root = ET.fromstring((docs_dir / "sitemap.xml").read_text(encoding="utf-8"))
    sitemap_locs = [el.text for el in sitemap_root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    assert sitemap_locs and len(sitemap_locs) == len(set(sitemap_locs)), "sitemap.xml empty or has duplicate URLs"

    feed_root = ET.fromstring((docs_dir / "feed.xml").read_text(encoding="utf-8"))
    assert feed_root.tag == "rss"
    assert len(feed_root.findall("./channel/item")) >= 1


def test_technical_seo_upgrades_generated_site(tmp_path: Path):
    md = (
        "# Generative AI Technical Briefing — 2026-11-28\n\n"
        "## Top 10 Ranked Briefing\n\n"
        "### 1. [Sparse Attention at Scale](https://arxiv.org/abs/2611.00001)\n"
        "**Research** (arXiv) · 240 pts · *2026-11-28*\n"
        "- Evaluates sub-quadratic attention kernels for 1M token context windows.\n\n"
        "### 2. [Deterministic Agent Harnesses](https://example.com/agent-harness)\n"
        "**Engineering** (Hacker News) · 180 pts · *2026-11-28*\n"
        "- Production verification loops for multi-step coding agents.\n\n"
        "### 3. [FP8 Calibration Tricks](https://example.com/fp8-calibration)\n"
        "**Systems** (Hugging Face) · 140 pts · *2026-11-28*\n"
        "- Post-training quantization benchmarks on H200 clusters.\n"
    )
    docs_dir = tmp_path / "docs"
    save_markdown_digest(md, tmp_path / "digests", timestamp=datetime(2026, 11, 28, 9, 0), docs_dir=docs_dir)

    _assert_site_seo_invariants(
        docs_dir,
        expected_daily_lead_keywords={
            "2026-11-28.html": ("Sparse Attention at Scale", "Deterministic Agent Harnesses"),
        },
    )


def test_published_docs_technical_seo_integrity():
    repo_docs = Path(__file__).resolve().parent.parent / "docs"
    if not repo_docs.exists():
        return
    _assert_site_seo_invariants(repo_docs)










