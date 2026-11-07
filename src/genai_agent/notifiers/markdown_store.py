from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import markdown

SHARED_CSS_AND_THEME_JS = """
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,500;0,6..72,600;1,6..72,400&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #FAF7F2;
      --bg-elevated: #FFFFFF;
      --bg-subtle: #F3EFE6;
      --text: #1C1917;
      --text-secondary: #57534E;
      --border: #E7E0D6;
      --accent: #4F46E5;
      --accent-soft: #EEF2FF;
      --accent-warm: #D97706;
      --gradient: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #D97706 100%);
      --shadow: 0 4px 20px -2px rgba(28, 25, 23, 0.06), 0 1px 3px -1px rgba(28, 25, 23, 0.04);
    }
    [data-theme="dark"] {
      --bg: #0F1117;
      --bg-elevated: #181B24;
      --bg-subtle: #212634;
      --text: #F3F4F6;
      --text-secondary: #9CA3AF;
      --border: #2A3040;
      --accent: #818CF8;
      --accent-soft: rgba(129, 140, 248, 0.14);
      --accent-warm: #FBBF24;
      --shadow: 0 8px 28px -4px rgba(0, 0, 0, 0.45);
    }
    * { box-sizing: border-box; }
    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.72;
      margin: 0;
      padding: 0 16px 48px;
      transition: background-color 0.2s ease, color 0.2s ease;
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
    }
    .top-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      padding: 18px 0;
      margin-bottom: 18px;
      border-bottom: 1px solid var(--border);
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 1.05rem;
      color: var(--text);
      text-decoration: none;
    }
    .brand-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: var(--gradient);
      display: inline-block;
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .pill-link {
      padding: 6px 13px;
      border-radius: 999px;
      font-size: 0.84rem;
      font-weight: 600;
      text-decoration: none;
      background: var(--bg-subtle);
      color: var(--text-secondary);
      border: 1px solid var(--border);
      transition: all 0.15s ease;
    }
    .pill-link:hover {
      border-color: var(--accent);
      color: var(--accent);
      text-decoration: none;
    }
    .pill-link.active {
      background: var(--accent);
      color: #FFFFFF;
      border-color: var(--accent);
    }
    .theme-btn {
      cursor: pointer;
      background: var(--bg-elevated);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 6px 13px;
      font-size: 0.83rem;
      font-weight: 600;
      font-family: inherit;
    }
    .hero {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 32px;
      margin-bottom: 24px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }
    .hero::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 4px;
      background: var(--gradient);
    }
    .hero-badge {
      display: inline-block;
      font-size: 0.76rem;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      padding: 4px 11px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      margin-bottom: 12px;
    }
    h1, h2 {
      font-family: 'Newsreader', Georgia, serif;
      letter-spacing: -0.015em;
      line-height: 1.25;
    }
    h1 {
      font-size: 2.15rem;
      margin: 4px 0 12px;
    }
    h2 {
      font-size: 1.55rem;
      margin: 34px 0 14px;
      padding-bottom: 8px;
      border-bottom: 1px solid var(--border);
    }
    h3 {
      font-size: 1.12rem;
      margin: 24px 0 8px;
      line-height: 1.45;
      padding: 16px 20px 6px;
      background: var(--bg-subtle);
      border-top-left-radius: 12px;
      border-top-right-radius: 12px;
      border: 1px solid var(--border);
      border-bottom: none;
    }
    h3 + p, h3 + p + ul {
      background: var(--bg-subtle);
      margin: 0;
      padding: 4px 20px 14px;
      border-left: 1px solid var(--border);
      border-right: 1px solid var(--border);
    }
    h3 + p + ul {
      padding-left: 38px;
      border-bottom: 1px solid var(--border);
      border-bottom-left-radius: 12px;
      border-bottom-right-radius: 12px;
      margin-bottom: 16px;
    }
    .card {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 34px;
      box-shadow: var(--shadow);
    }
    a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }
    a:hover {
      text-decoration: underline;
    }
    blockquote {
      margin: 16px 0 24px;
      padding: 14px 20px;
      background: var(--accent-soft);
      border-left: 4px solid var(--accent);
      border-radius: 10px;
      color: var(--text);
      font-size: 0.94rem;
    }
    hr {
      border: none;
      border-top: 1px solid var(--border);
      margin: 28px 0;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
      gap: 18px;
      margin-top: 16px;
    }
    .day-card {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 24px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .day-card:hover {
      transform: translateY(-2px);
      border-color: var(--accent);
    }
    .day-card h3 {
      background: none;
      border: none;
      padding: 0;
      margin: 6px 0 10px;
      font-family: 'Newsreader', Georgia, serif;
      font-size: 1.38rem;
    }
    .day-card ul {
      padding-left: 18px;
      margin: 8px 0 18px;
      color: var(--text-secondary);
      font-size: 0.92rem;
    }
    .day-card li { margin-bottom: 6px; }
    .cta-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent);
      color: #FFFFFF !important;
      padding: 10px 18px;
      border-radius: 10px;
      font-size: 0.9rem;
      font-weight: 600;
      text-decoration: none !important;
      align-self: flex-start;
    }
    .cta-btn:hover { opacity: 0.92; }
    .footer {
      text-align: center;
      font-size: 0.85rem;
      color: var(--text-secondary);
      margin-top: 36px;
      padding-top: 18px;
      border-top: 1px solid var(--border);
    }
    @media (max-width: 640px) {
      .card, .hero { padding: 20px; }
      .grid { grid-template-columns: 1fr; }
      h1 { font-size: 1.65rem; }
    }
  </style>
  <script>
    (function() {
      const saved = localStorage.getItem('genai_theme');
      if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.setAttribute('data-theme', 'dark');
      }
    })();
    function toggleTheme() {
      const current = document.documentElement.getAttribute('data-theme');
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('genai_theme', next);
    }
  </script>
"""


def _extract_top_headlines(markdown_text: str, max_items: int = 3) -> List[str]:
    """Extract the top N numbered headline titles from a digest Markdown file."""
    headlines: List[str] = []
    for line in markdown_text.splitlines():
        m = re.match(r"^###\s+\d+\.\s+\[([^\]]+)\]", line.strip())
        if m:
            headlines.append(m.group(1))
            if len(headlines) >= max_items:
                break
    if not headlines:
        for line in markdown_text.splitlines():
            m = re.match(r"^-\s+\*\*\[([^\]]+)\]", line.strip())
            if m:
                headlines.append(m.group(1))
                if len(headlines) >= max_items:
                    break
    return headlines


def _render_daily_digest_html(
    markdown_content: str,
    title: str,
    current_date: str,
    archive_dates: List[str],
) -> str:
    """Render a daily digest page (`YYYY-MM-DD.html`) with the Generative AI editorial theme."""
    body_html = markdown.markdown(
        markdown_content,
        extensions=["extra", "sane_lists", "nl2br"],
    )

    date_pills = []
    for d in sorted(archive_dates, reverse=True):
        active_cls = "pill-link active" if d == current_date else "pill-link"
        date_pills.append(f'<a class="{active_cls}" href="{d}.html">{d}</a>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {SHARED_CSS_AND_THEME_JS}
</head>
<body>
  <div class="container">
    <nav class="top-nav">
      <a class="brand" href="index.html">
        <span class="brand-dot"></span>
        <span>← All Editions (Index)</span>
      </a>
      <div class="nav-actions">
        {"".join(date_pills)}
        <button class="theme-btn" onclick="toggleTheme()">🌗 Theme</button>
      </div>
    </nav>
    <main class="card">
      {body_html}
    </main>
    <footer class="footer">
      Curated by <strong>Generative AI Learning &amp; News Agent</strong> · <a href="index.html">Back to Main Index</a>
    </footer>
  </div>
</body>
</html>"""


def _render_index_portal_html(
    archive_map: Dict[str, str],
) -> str:
    """Render `docs/index.html` as a dedicated Index & Directory page linking to every daily digest."""
    sorted_dates = sorted(archive_map.keys(), reverse=True)
    latest_date = sorted_dates[0] if sorted_dates else ""
    latest_md = archive_map.get(latest_date, "")
    latest_headlines = _extract_top_headlines(latest_md, max_items=4)

    latest_list_html = "".join(f"<li>{h}</li>" for h in latest_headlines)

    day_cards_html = []
    for idx, d in enumerate(sorted_dates):
        md_text = archive_map[d]
        headlines = _extract_top_headlines(md_text, max_items=3)
        hl_items = "".join(f"<li>{h}</li>" for h in headlines) or "<li>Top 10 curated GenAI papers, blogs, community threads & podcasts</li>"
        badge_label = "✨ Latest Edition" if idx == 0 else "📅 Daily Edition"
        day_cards_html.append(
            f"""
            <article class="day-card">
              <div>
                <span class="hero-badge">{badge_label} · ~4 min read</span>
                <h3><a href="{d}.html">GenAI Top 10 Digest — {d}</a></h3>
                <p style="margin:4px 0 8px;font-size:0.88rem;color:var(--text-secondary);">Top stories ranked by technical substance &amp; community reach:</p>
                <ul>{hl_items}</ul>
              </div>
              <a class="cta-btn" href="{d}.html">Read {d} Digest →</a>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Generative AI Learning &amp; News Hub — Daily Top 10 Index</title>
  {SHARED_CSS_AND_THEME_JS}
</head>
<body>
  <div class="container">
    <nav class="top-nav">
      <a class="brand" href="index.html">
        <span class="brand-dot"></span>
        <span>GenAI Learning &amp; News Hub</span>
      </a>
      <div class="nav-actions">
        <a class="pill-link active" href="index.html">📚 All Editions ({len(sorted_dates)})</a>
        <a class="pill-link" href="{latest_date}.html">Latest ({latest_date})</a>
        <button class="theme-btn" onclick="toggleTheme()">🌗 Theme</button>
      </div>
    </nav>

    <section class="hero">
      <span class="hero-badge">🧠 Curated for Fast Daily Learning</span>
      <h1>Generative AI Daily Top 10 &amp; Audio Hub</h1>
      <p style="color:var(--text-secondary);font-size:1.03rem;margin:0 0 18px;">
        Signal over noise: Every edition distills 50+ research papers (Hugging Face &amp; arXiv), AI lab blogs (OpenAI, Google, DeepMind, Anthropic), Hacker News &amp; r/LocalLLaMA engineering threads, and <strong>AI Podcasts</strong> into a <strong>5-minute Top 10 read</strong>.
      </p>
      <div style="background:var(--bg-subtle);border:1px solid var(--border);border-radius:12px;padding:16px 20px;margin-bottom:20px;">
        <div style="font-weight:700;font-size:0.92rem;margin-bottom:6px;color:var(--accent);">🔥 Featured in Latest Edition ({latest_date}):</div>
        <ul style="margin:0;padding-left:20px;font-size:0.93rem;">
          {latest_list_html}
        </ul>
      </div>
      <a class="cta-btn" href="{latest_date}.html">Open Latest Digest ({latest_date}) →</a>
    </section>

    <h2>📅 Daily Digest Editions</h2>
    <div class="grid">
      {"".join(day_cards_html)}
    </div>

    <footer class="footer">
      Powered by <strong>Google Gemini</strong> · Auto-curated Research, Engineering, &amp; AI Podcasts
    </footer>
  </div>
</body>
</html>"""


def save_markdown_digest(
    markdown_content: str,
    output_dir: Path,
    timestamp: datetime | None = None,
    docs_dir: Path | None = None,
) -> Path:
    """Save the digest to a dated Markdown file, update `latest.md`, and build GitHub Pages HTML (`index.html` directory + `<date>.html` pages)."""
    ts = timestamp or datetime.now()
    date_str = ts.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    dated_filename = f"{date_str}_genai_digest.md"
    dated_path = output_dir / dated_filename
    dated_path.write_text(markdown_content, encoding="utf-8")

    latest_path = output_dir / "latest.md"
    latest_path.write_text(markdown_content, encoding="utf-8")

    target_docs = docs_dir if docs_dir is not None else output_dir.parent / "docs"
    target_docs.mkdir(parents=True, exist_ok=True)
    (target_docs / ".nojekyll").write_text("", encoding="utf-8")

    archive_files = {
        p.name.split("_genai_digest.md")[0]: p
        for p in output_dir.glob("*_genai_digest.md")
    }
    archive_dates = sorted(archive_files.keys())
    archive_map: Dict[str, str] = {}

    for arch_date, md_path in archive_files.items():
        md_text = md_path.read_text(encoding="utf-8")
        archive_map[arch_date] = md_text
        arch_title = f"Generative AI Top 10 Digest — {arch_date}"
        arch_html = _render_daily_digest_html(
            markdown_content=md_text,
            title=arch_title,
            current_date=arch_date,
            archive_dates=archive_dates,
        )
        (target_docs / f"{arch_date}.html").write_text(arch_html, encoding="utf-8")

    # Render dedicated Index Portal Page at docs/index.html
    index_html = _render_index_portal_html(archive_map=archive_map)
    (target_docs / "index.html").write_text(index_html, encoding="utf-8")

    return dated_path
