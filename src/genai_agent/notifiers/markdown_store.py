from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import markdown

from genai_agent.collectors.podcasts import fetch_detailed_podcast_hub

EDITORIAL_CSS_AND_JS = """
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet">
  <style>
    /* Default: Warm Archival Paper (FT / Anthropic / Stripe Press inspired) */
    :root, [data-theme="sage"] {
      --bg: #F6F4EF;
      --surface: #FDFCF9;
      --surface-alt: #EFECE5;
      --ink: #141413;
      --ink-secondary: #4A4843;
      --ink-muted: #78756E;
      --border: #DCD7CC;
      --border-strong: #141413;
      --accent: #9E2A2B;
      --accent-hover: #7A1C1D;
      --link: #1D4ED8;
      --font-serif: 'Newsreader', Georgia, serif;
      --font-display: 'Instrument Serif', 'Newsreader', Georgia, serif;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
      --base-size: 16.5px;
    }

    [data-theme="sepia"] {
      --bg: #F2E9D8;
      --surface: #F9F3E6;
      --surface-alt: #E8DEC8;
      --ink: #251E18;
      --ink-secondary: #54473C;
      --ink-muted: #7D6D5F;
      --border: #D5C7B0;
      --border-strong: #251E18;
      --accent: #8C2D19;
      --accent-hover: #692010;
      --link: #0F5257;
    }

    [data-theme="dark"] {
      --bg: #111214;
      --surface: #18191C;
      --surface-alt: #202226;
      --ink: #ECEAE4;
      --ink-secondary: #A6A39B;
      --ink-muted: #706E68;
      --border: #2B2D31;
      --border-strong: #ECEAE4;
      --accent: #E07A5F;
      --accent-hover: #F29C85;
      --link: #7AA2F7;
    }

    * { box-sizing: border-box; }
    html {
      font-size: var(--base-size);
      scroll-behavior: smooth;
    }
    body {
      font-family: var(--font-serif);
      background-color: var(--bg);
      color: var(--ink);
      line-height: 1.68;
      margin: 0;
      padding: 0 20px 72px;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
    }

    .page-wrap {
      max-width: 1020px;
      margin: 0 auto;
    }

    /* Editorial Masthead */
    .masthead {
      padding-top: 20px;
      margin-bottom: 32px;
    }
    .masthead-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
      padding-bottom: 10px;
      border-bottom: 1px solid var(--border);
      font-family: var(--font-mono);
      font-size: 0.72rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-muted);
    }
    .controls {
      display: inline-flex;
      align-items: center;
      gap: 12px;
    }
    .ctrl-btn {
      background: none;
      border: none;
      padding: 2px 4px;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--ink-muted);
      cursor: pointer;
    }
    .ctrl-btn:hover, .ctrl-btn.active {
      color: var(--ink);
      text-decoration: underline;
      text-underline-offset: 4px;
      font-weight: 600;
    }

    .masthead-title-row {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      flex-wrap: wrap;
      gap: 16px;
      padding: 22px 0 18px;
      border-bottom: 2px solid var(--border-strong);
    }
    .masthead-title {
      font-family: var(--font-display);
      font-size: 3.1rem;
      font-weight: 400;
      line-height: 1;
      letter-spacing: -0.02em;
      margin: 0;
    }
    .masthead-title a {
      color: var(--ink);
      text-decoration: none;
    }
    .masthead-sub {
      font-family: var(--font-sans);
      font-size: 0.85rem;
      color: var(--ink-secondary);
      margin: 0;
    }

    .masthead-nav {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
      padding: 10px 0;
      border-bottom: 1px solid var(--border);
      font-family: var(--font-sans);
      font-size: 0.8rem;
      font-weight: 500;
    }
    .nav-links {
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
    }
    .nav-links a {
      color: var(--ink-secondary);
      text-decoration: none;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 0.74rem;
      font-weight: 600;
    }
    .nav-links a:hover, .nav-links a.active {
      color: var(--ink);
      text-decoration: underline;
      text-underline-offset: 5px;
      text-decoration-thickness: 1.5px;
    }

    /* Section Headers */
    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      border-top: 1px solid var(--border-strong);
      border-bottom: 1px solid var(--border);
      padding: 10px 0;
      margin: 36px 0 20px;
    }
    .section-head h2 {
      font-family: var(--font-mono);
      font-size: 0.78rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin: 0;
      color: var(--ink);
    }
    .section-head span {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--ink-muted);
    }

    /* Editorial Briefing Ledger (Top 10 List) */
    .briefing-list {
      display: flex;
      flex-direction: column;
    }
    .briefing-item {
      display: grid;
      grid-template-columns: 44px 1fr;
      gap: 16px;
      padding: 18px 0;
      border-bottom: 1px solid var(--border);
    }
    .briefing-item:last-child {
      border-bottom: none;
    }
    .briefing-num {
      font-family: var(--font-mono);
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--accent);
      padding-top: 3px;
    }
    .briefing-content h3 {
      font-family: var(--font-serif);
      font-size: 1.22rem;
      font-weight: 600;
      line-height: 1.35;
      margin: 0 0 6px;
    }
    .briefing-content h3 a {
      color: var(--ink);
      text-decoration: none;
    }
    .briefing-content h3 a:hover {
      color: var(--accent);
      text-decoration: underline;
      text-underline-offset: 3px;
    }
    .briefing-meta {
      font-family: var(--font-mono);
      font-size: 0.73rem;
      color: var(--ink-muted);
      margin-bottom: 8px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .briefing-meta a {
      color: var(--ink-secondary);
      text-decoration: underline;
      text-underline-offset: 2px;
    }
    .briefing-tag {
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
      color: var(--accent);
    }
    .briefing-summary {
      font-family: var(--font-serif);
      font-size: 0.98rem;
      color: var(--ink-secondary);
      margin: 0;
      line-height: 1.62;
    }

    /* Two-Column Editorial Split for X Threads & Podcasts */
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 36px;
      margin-top: 12px;
    }
    .note-list {
      display: flex;
      flex-direction: column;
    }
    .note-item {
      padding: 16px 0;
      border-bottom: 1px solid var(--border);
    }
    .note-item:last-child {
      border-bottom: none;
    }
    .note-kicker {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--ink-muted);
      margin-bottom: 4px;
    }
    .note-kicker strong {
      color: var(--ink);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .note-title {
      font-family: var(--font-sans);
      font-size: 0.96rem;
      font-weight: 600;
      line-height: 1.4;
      margin: 0 0 6px;
    }
    .note-title a {
      color: var(--ink);
      text-decoration: none;
    }
    .note-title a:hover {
      color: var(--accent);
      text-decoration: underline;
    }
    .note-body {
      font-family: var(--font-serif);
      font-size: 0.92rem;
      color: var(--ink-secondary);
      margin: 0 0 8px;
      line-height: 1.55;
    }
    .note-links {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      display: flex;
      gap: 14px;
    }
    .note-links a {
      color: var(--ink-secondary);
      text-decoration: underline;
      text-underline-offset: 3px;
    }
    .note-links a:hover {
      color: var(--ink);
    }

    /* Archive Table */
    .archive-table {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--font-sans);
      font-size: 0.88rem;
    }
    .archive-table th {
      text-align: left;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--ink-muted);
      padding: 8px 12px 8px 0;
      border-bottom: 1px solid var(--border);
    }
    .archive-table td {
      padding: 14px 12px 14px 0;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }
    .archive-date {
      font-family: var(--font-mono);
      font-size: 0.82rem;
      font-weight: 600;
      white-space: nowrap;
      width: 130px;
    }
    .archive-date a {
      color: var(--ink);
      text-decoration: none;
    }
    .archive-date a:hover {
      color: var(--accent);
      text-decoration: underline;
    }
    .archive-leads {
      color: var(--ink-secondary);
      line-height: 1.5;
    }
    .archive-leads a {
      color: var(--ink);
      text-decoration: underline;
      text-decoration-color: var(--border);
      text-underline-offset: 3px;
    }
    .archive-leads a:hover {
      text-decoration-color: var(--ink);
    }

    /* Callout Box for Executive Summary / Concept Deep-Dive */
    .editorial-callout {
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 3px solid var(--accent);
      padding: 20px 24px;
      margin: 20px 0 28px;
    }
    .editorial-callout h3 {
      font-family: var(--font-mono);
      font-size: 0.76rem;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--accent);
      margin: 0 0 10px;
    }
    .editorial-callout ul, .editorial-callout p {
      margin: 0;
      font-size: 0.96rem;
      color: var(--ink-secondary);
    }
    .editorial-callout li {
      margin-bottom: 8px;
    }

    .footer {
      margin-top: 56px;
      padding-top: 18px;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 12px;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--ink-muted);
    }
    .footer a {
      color: var(--ink-secondary);
      text-decoration: none;
    }
    .footer a:hover {
      text-decoration: underline;
    }

    @media (max-width: 760px) {
      .two-col { grid-template-columns: 1fr; gap: 16px; }
      .masthead-title { font-size: 2.25rem; }
      .briefing-item { grid-template-columns: 32px 1fr; gap: 10px; }
    }
  </style>
  <script>
    (function() {
      const savedTheme = localStorage.getItem('genai_theme') || 'sage';
      document.documentElement.setAttribute('data-theme', savedTheme);
      const savedSize = localStorage.getItem('genai_fontsize');
      if (savedSize) {
        document.documentElement.style.setProperty('--base-size', savedSize + 'px');
      }
    })();

    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('genai_theme', theme);
      updateControls();
    }

    function adjustFontSize(delta) {
      const current = parseFloat(localStorage.getItem('genai_fontsize') || '16.5');
      const next = Math.min(20, Math.max(14.5, current + delta));
      localStorage.setItem('genai_fontsize', next);
      document.documentElement.style.setProperty('--base-size', next + 'px');
    }

    function updateControls() {
      const theme = document.documentElement.getAttribute('data-theme') || 'sage';
      document.querySelectorAll('[data-theme-btn]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-theme-btn') === theme);
      });
    }

    window.addEventListener('DOMContentLoaded', updateControls);
  </script>
"""


def _strip_emojis(text: str) -> str:
    """Remove decorative emoji prefixes from legacy markdown headings and badges."""
    return re.sub(
        r"[🚀⚡🧠📄🏢🛠️🔥🏆🎧🎯✨📅⬆️🎙️🍏📌🌐]+\s*",
        "",
        text or "",
    ).strip()


def _clean_excerpt(text: str, max_chars: int = 300) -> str:
    """Clean raw scraper boilerplate and cut on a full sentence boundary."""
    if not text:
        return ""
    import html as _html

    text = _html.unescape(text).strip()
    text = re.sub(r"^\*\*Takeaway:\*\*\s*", "", text)
    text = re.sub(r"^\*\*Summary:\*\*\s*", "", text)
    text = re.sub(r"^🎧\s*[0-9hm:\s]+—\s*", "", text)
    text = re.sub(
        r"Hacker News discussion \([^)]+\)\.\s*Discussion:\s*https?://\S+\s*(\|\s*)?",
        "",
        text,
    ).strip()
    text = re.sub(
        r"See also:\s*[^|]+-\s*https?://news\.ycombinator\.com/\S+",
        "",
        text,
    ).strip(" |")
    text = re.sub(
        r"Viral X thread discussed on Hacker News \([^)]+\)\.\s*HN Thread:\s*https?://\S+",
        "",
        text,
    ).strip()
    text = re.sub(
        r"^Active engineering discussion thread on \[Hacker News\]\([^)]+\)\.?$",
        "",
        text,
    ).strip()
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)
    text = re.sub(
        r"^Trending AI discussion on X covered by [^.]+\.?$",
        "",
        text,
    ).strip()
    text = re.sub(r"\*\*", "", text)
    text = " ".join(text.split())
    if not text:
        return ""

    # If legacy text was sliced mid-word/mid-sentence with '...', trim back to the last full sentence
    if text.endswith("..."):
        without_dots = text[:-3].rstrip()
        best_sep = -1
        for sep in (". ", "? ", "! "):
            pos = without_dots.rfind(sep)
            if pos > best_sep:
                best_sep = pos
        if best_sep > 40:
            text = without_dots[: best_sep + 1]
        else:
            last_sp = without_dots.rfind(" ")
            text = (without_dots[:last_sp].rstrip(",;:-") + ".") if last_sp > 0 else without_dots + "."

    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    for sep in (". ", "? ", "! ", "; "):
        pos = cut.rfind(sep)
        if pos > max_chars // 2:
            return cut[: pos + 1]
    last_space = cut.rfind(" ")
    return (cut[:last_space].rstrip(",;:-") + ".") if last_space > 0 else cut


def _domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def _parse_top10_items(markdown_text: str) -> List[Dict[str, str]]:
    """Parse numbered `### 1. [Title](URL)` items from a digest Markdown file into structured dicts."""
    lines = markdown_text.splitlines()
    items: List[Dict[str, str]] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m = re.match(r"^###\s+(\d+)\.\s+\[(.+)\]\((https?://[^)]+)\)", line)
        if m:
            rank = int(m.group(1))
            title = _strip_emojis(m.group(2))
            url = m.group(3).strip()
            meta_line = ""
            bullets: List[str] = []
            i += 1
            while i < len(lines):
                sub = lines[i].strip()
                if sub.startswith("### ") or sub.startswith("## ") or sub == "---":
                    break
                if not sub:
                    i += 1
                    continue
                if not meta_line and not sub.startswith("- "):
                    meta_line = sub
                elif sub.startswith("- "):
                    bullets.append(sub[2:].strip())
                i += 1

            # Extract HN discussion URL and points if present
            hn_match = re.search(
                r"https://news\.ycombinator\.com/item\?id=\d+",
                meta_line + " " + " ".join(bullets),
            )
            hn_url = hn_match.group(0) if hn_match else ""
            pts_match = re.search(r"(\d[\d,]*)\s*(?:pts|points|upvotes)", meta_line + " " + " ".join(bullets))
            pts = pts_match.group(1) if pts_match else ""

            cat_match = re.search(r"\*\*([^*]+)\*\*", meta_line)
            cat_raw = _strip_emojis(cat_match.group(1)) if cat_match else "Briefing"
            if "Community" in cat_raw or "Hacker News" in meta_line:
                category = "Engineering"
            elif "Paper" in cat_raw or "arXiv" in meta_line or "Hugging Face" in meta_line:
                category = "Research"
            elif "Blog" in cat_raw or "Lab" in cat_raw:
                category = "Lab Release"
            else:
                category = cat_raw

            src_match = re.search(r"\(([^)]+)\)", meta_line)
            source = src_match.group(1) if src_match else _domain_of(url)

            date_match = re.search(r"\*([0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]{3},\s+[0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{4})", meta_line)
            pub_date = date_match.group(1) if date_match else ""

            combined_summary = _clean_excerpt(" ".join(bullets), max_chars=340)

            items.append(
                {
                    "rank": f"{rank:02d}",
                    "title": title,
                    "url": url,
                    "domain": _domain_of(url),
                    "category": category,
                    "source": source,
                    "points": pts,
                    "hn_url": hn_url,
                    "date": pub_date,
                    "summary": combined_summary,
                }
            )
            continue
        i += 1
    return items


def _extract_section_markdown(markdown_text: str, section_keyword: str) -> str:
    lines = markdown_text.splitlines()
    capturing = False
    collected: List[str] = []
    for line in lines:
        if line.startswith("## "):
            if capturing:
                break
            if section_keyword.lower() in line.lower():
                capturing = True
                continue
        elif capturing:
            if line.strip() == "---":
                break
            collected.append(line)
    return "\n".join(collected).strip()


def _parse_bullet_notes(section_md: str, kind: str = "x") -> List[Dict[str, str]]:
    """Parse 2-line markdown bullets from X or Podcast sections into structured notes."""
    notes: List[Dict[str, str]] = []
    lines = [ln for ln in section_md.splitlines() if ln.strip()]
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("- **["):
            m = re.match(r"^-\s+\*\*\[(.+)\]\((https?://[^)]+)\)\*\*(.*)$", line)
            title = _strip_emojis(m.group(1)) if m else line
            url = m.group(2).strip() if m else "#"
            tail = m.group(3) if m else ""

            desc = ""
            if idx + 1 < len(lines) and not lines[idx + 1].strip().startswith("- **["):
                desc = lines[idx + 1].strip().lstrip("- ").strip()
                idx += 1

            hn_m = re.search(r"https://news\.ycombinator\.com/item\?id=\d+", tail + " " + desc)
            hn_url = hn_m.group(0) if hn_m else ""

            pts_m = re.search(r"(\d[\d,]*)\s*pts", tail + " " + desc)
            pts = f"{pts_m.group(1)} pts" if pts_m else ""

            dur_m = re.search(r"🎧\s*([0-9hm:\s]+)", tail + " " + desc)
            dur = dur_m.group(1).strip() if dur_m else ""

            handle_m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url)
            if handle_m:
                kicker = f"@{handle_m.group(1)}"
            elif "smol.ai" in url:
                kicker = "AINews · X Recap"
            else:
                show_m = re.search(r"—\s*(?:\*|\*\*)([^*]+)(?:\*|\*\*)", tail)
                kicker = _strip_emojis(show_m.group(1)) if show_m else _domain_of(url)

            clean_desc = _clean_excerpt(desc, max_chars=260)
            notes.append(
                {
                    "title": title,
                    "url": url,
                    "kicker": kicker,
                    "meta": dur if kind == "podcast" else pts,
                    "hn_url": hn_url,
                    "summary": clean_desc,
                }
            )
        idx += 1
    return notes


def _render_masthead(active_page: str, latest_date: str, edition_date: str = "") -> str:
    issue_label = f"ISSUE {edition_date or latest_date}" if (edition_date or latest_date) else "DAILY EDITION"
    return f"""
    <header class="masthead">
      <div class="masthead-top">
        <div>THE GENERATIVE AI TECHNICAL BRIEFING · {issue_label} · SINGAPORE (SGT)</div>
        <div class="controls">
          <span>PALETTE:</span>
          <button class="ctrl-btn" data-theme-btn="sage" onclick="setTheme('sage')">Paper</button>
          <button class="ctrl-btn" data-theme-btn="sepia" onclick="setTheme('sepia')">Sepia</button>
          <button class="ctrl-btn" data-theme-btn="dark" onclick="setTheme('dark')">Ink</button>
          <span>·</span>
          <button class="ctrl-btn" onclick="adjustFontSize(-0.5)">A-</button>
          <button class="ctrl-btn" onclick="adjustFontSize(0.5)">A+</button>
        </div>
      </div>
      <div class="masthead-title-row">
        <h1 class="masthead-title"><a href="index.html">The GenAI Briefing</a></h1>
        <p class="masthead-sub">Curated research papers, frontier lab engineering, researcher threads &amp; audio briefings.</p>
      </div>
      <nav class="masthead-nav">
        <div class="nav-links">
          <a href="index.html" class="{'active' if active_page == 'index' else ''}">Front Page</a>
          <a href="{latest_date}.html" class="{'active' if active_page == 'daily' else ''}">Latest Issue ({latest_date})</a>
          <a href="podcasts.html" class="{'active' if active_page == 'podcasts' else ''}">Podcasts Index</a>
          <a href="index.html#archive">Archive</a>
        </div>
        <div style="font-family:var(--font-mono);font-size:0.72rem;color:var(--ink-muted);">
          AUTO-PUBLISHED DAILY BY 07:00 SGT
        </div>
      </nav>
    </header>
    """


def _render_top10_ledger_html(items: List[Dict[str, str]]) -> str:
    rows: List[str] = []
    for it in items:
        meta_bits = [f'<span class="briefing-tag">{it["category"]}</span>', f'<span>{it["source"]}</span>']
        if it["domain"] and it["domain"] not in ("news.ycombinator.com",):
            meta_bits.append(f'<span>{it["domain"]}</span>')
        if it["points"]:
            if it["hn_url"] and it["hn_url"] != it["url"]:
                meta_bits.append(f'<a href="{it["hn_url"]}" target="_blank" rel="noopener">{it["points"]} pts · HN Discussion ↗</a>')
            else:
                meta_bits.append(f'<span>{it["points"]} pts</span>')
        elif it["hn_url"] and it["hn_url"] != it["url"]:
            meta_bits.append(f'<a href="{it["hn_url"]}" target="_blank" rel="noopener">HN Discussion ↗</a>')
        if it["date"]:
            meta_bits.append(f'<span>{it["date"]}</span>')

        summary_html = f'<p class="briefing-summary">{it["summary"]}</p>' if it["summary"] else ""

        rows.append(
            f"""
            <article class="briefing-item">
              <div class="briefing-num">{it["rank"]}</div>
              <div class="briefing-content">
                <div class="briefing-meta">{'<span>·</span>'.join(meta_bits)}</div>
                <h3><a href="{it["url"]}" target="_blank" rel="noopener">{it["title"]}</a></h3>
                {summary_html}
              </div>
            </article>
            """
        )
    return f'<div class="briefing-list">{"".join(rows)}</div>'


def _render_notes_column_html(notes: List[Dict[str, str]], action_label: str) -> str:
    if not notes:
        return '<p style="color:var(--ink-muted);font-size:0.9rem;">No entries recorded for this issue.</p>'
    blocks: List[str] = []
    for n in notes:
        links = [f'<a href="{n["url"]}" target="_blank" rel="noopener">{action_label} ↗</a>']
        if n["hn_url"] and n["hn_url"] != n["url"]:
            links.append(f'<a href="{n["hn_url"]}" target="_blank" rel="noopener">HN Thread ↗</a>')
        body_html = f'<p class="note-body">{n["summary"]}</p>' if n["summary"] else ""
        blocks.append(
            f"""
            <article class="note-item">
              <div class="note-kicker">
                <strong>{n["kicker"]}</strong>
                <span>{n["meta"]}</span>
              </div>
              <h4 class="note-title"><a href="{n["url"]}" target="_blank" rel="noopener">{n["title"]}</a></h4>
              {body_html}
              <div class="note-links">{"".join(links)}</div>
            </article>
            """
        )
    return f'<div class="note-list">{"".join(blocks)}</div>'


def _render_daily_digest_html(
    markdown_content: str,
    title: str,
    current_date: str,
    archive_dates: List[str],
) -> str:
    """Render an individual daily briefing page (`YYYY-MM-DD.html`) in clean editorial style."""
    latest_date = sorted(archive_dates, reverse=True)[0] if archive_dates else current_date
    top10_items = _parse_top10_items(markdown_content)
    x_md = _extract_section_markdown(markdown_content, "X") or _extract_section_markdown(markdown_content, "Twitter")
    pod_md = _extract_section_markdown(markdown_content, "Podcast") or _extract_section_markdown(markdown_content, "Audio")
    tldr_md = _extract_section_markdown(markdown_content, "TL;DR") or _extract_section_markdown(markdown_content, "Executive Summary")
    concept_md = _extract_section_markdown(markdown_content, "Concept") or _extract_section_markdown(markdown_content, "Deep-Dive")

    tldr_html = ""
    if tldr_md:
        rendered_tldr = markdown.markdown(_strip_emojis(tldr_md), extensions=["extra", "sane_lists"])
        tldr_html = f'<div class="editorial-callout"><h3>Executive Summary</h3>{rendered_tldr}</div>'

    concept_html = ""
    if concept_md:
        rendered_concept = markdown.markdown(_strip_emojis(concept_md), extensions=["extra", "sane_lists"])
        concept_html = f'<div class="editorial-callout"><h3>Technical Deep-Dive</h3>{rendered_concept}</div>'

    top10_html = _render_top10_ledger_html(top10_items)
    x_html = _render_notes_column_html(_parse_bullet_notes(x_md, kind="x"), "Read Thread on X")
    pod_html = _render_notes_column_html(_parse_bullet_notes(pod_md, kind="podcast"), "Listen Episode")

    date_links = " · ".join(
        f'<a href="{d}.html" style="font-weight:{"700" if d == current_date else "400"};color:var(--ink);">{d}</a>'
        for d in sorted(archive_dates, reverse=True)
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The GenAI Briefing — {current_date}</title>
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="daily", latest_date=latest_date, edition_date=current_date)}

    <div style="font-family:var(--font-mono);font-size:0.74rem;color:var(--ink-muted);margin-bottom:20px;">
      ISSUES: {date_links}
    </div>

    {tldr_html}
    {concept_html}

    <div class="section-head">
      <h2>I. Top 10 Technical Briefing — {current_date}</h2>
      <span>RANKED BY SUBSTANCE &amp; COMMUNITY REACH</span>
    </div>
    {top10_html}

    <div class="two-col">
      <section>
        <div class="section-head">
          <h2>II. Researcher Threads on X</h2>
          <span>SOCIAL PULSE</span>
        </div>
        {x_html}
      </section>
      <section>
        <div class="section-head">
          <h2>III. Audio &amp; Podcast Briefings</h2>
          <span><a href="podcasts.html" style="color:var(--accent);text-decoration:none;">ALL SHOWS →</a></span>
        </div>
        {pod_html}
      </section>
    </div>

    <footer class="footer">
      <div>THE GENAI BRIEFING · ISSUE {current_date}</div>
      <div><a href="index.html">Front Page</a> · <a href="podcasts.html">Podcasts Index</a></div>
    </footer>
  </div>
</body>
</html>"""


def _render_index_portal_html(archive_map: Dict[str, str]) -> str:
    """Render `docs/index.html` as a high-density, editorial front page + archive ledger."""
    sorted_dates = sorted(archive_map.keys(), reverse=True)
    latest_date = sorted_dates[0] if sorted_dates else ""
    latest_md = archive_map.get(latest_date, "")

    top10_items = _parse_top10_items(latest_md)
    x_md = _extract_section_markdown(latest_md, "X") or _extract_section_markdown(latest_md, "Twitter")
    pod_md = _extract_section_markdown(latest_md, "Podcast") or _extract_section_markdown(latest_md, "Audio")
    tldr_md = _extract_section_markdown(latest_md, "TL;DR") or _extract_section_markdown(latest_md, "Executive Summary")

    tldr_html = ""
    if tldr_md:
        rendered_tldr = markdown.markdown(_strip_emojis(tldr_md), extensions=["extra", "sane_lists"])
        tldr_html = f'<div class="editorial-callout"><h3>Executive Summary — {latest_date}</h3>{rendered_tldr}</div>'

    top10_html = _render_top10_ledger_html(top10_items)
    x_html = _render_notes_column_html(_parse_bullet_notes(x_md, kind="x"), "Read Thread on X")
    pod_html = _render_notes_column_html(_parse_bullet_notes(pod_md, kind="podcast"), "Listen Episode")

    archive_rows: List[str] = []
    for d in sorted_dates:
        items_d = _parse_top10_items(archive_map[d])
        leads = " · ".join(
            f'<a href="{it["url"]}" target="_blank" rel="noopener">{it["title"]}</a>'
            for it in items_d[:3]
        )
        archive_rows.append(
            f"""
            <tr>
              <td class="archive-date"><a href="{d}.html">{d} →</a></td>
              <td class="archive-leads">{leads}</td>
            </tr>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The GenAI Briefing — Daily Research, Engineering &amp; Audio Index</title>
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="index", latest_date=latest_date, edition_date=latest_date)}

    {tldr_html}

    <div class="section-head">
      <h2>I. Lead Briefing — {latest_date} (Top 10)</h2>
      <span><a href="{latest_date}.html" style="color:var(--accent);text-decoration:none;">PERMALINK ({latest_date}) →</a></span>
    </div>
    {top10_html}

    <div class="two-col">
      <section id="x-highlights">
        <div class="section-head">
          <h2>II. Researcher Threads on X</h2>
          <span>CURATED THREADS</span>
        </div>
        {x_html}
      </section>
      <section id="podcast-highlights">
        <div class="section-head">
          <h2>III. Audio &amp; Podcast Briefings</h2>
          <span><a href="podcasts.html" style="color:var(--accent);text-decoration:none;">FULL PODCAST DIRECTORY →</a></span>
        </div>
        {pod_html}
      </section>
    </div>

    <section id="archive">
      <div class="section-head">
        <h2>IV. Past Issues Archive</h2>
        <span>{len(sorted_dates)} EDITIONS PUBLISHED</span>
      </div>
      <table class="archive-table">
        <thead>
          <tr>
            <th>Issue Date</th>
            <th>Lead Technical Stories</th>
          </tr>
        </thead>
        <tbody>
          {"".join(archive_rows)}
        </tbody>
      </table>
    </section>

    <footer class="footer">
      <div>THE GENAI BRIEFING · PUBLISHED DAILY AT 06:45 SGT</div>
      <div><a href="index.html">Front Page</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="{latest_date}.html">Latest Issue</a></div>
    </footer>
  </div>
</body>
</html>"""


def _render_podcasts_page_html(
    shows_data: List[Dict[str, Any]],
    latest_date: str,
) -> str:
    """Render `docs/podcasts.html` in the same clean editorial layout."""
    show_blocks: List[str] = []
    for idx, show in enumerate(shows_data, start=1):
        ep_notes: List[Dict[str, str]] = []
        for ep in show.get("episodes", []):
            ep_notes.append(
                {
                    "title": _strip_emojis(ep["title"]),
                    "url": ep["url"],
                    "kicker": ep.get("published") or show["name"],
                    "meta": ep.get("duration", ""),
                    "hn_url": "",
                    "summary": _clean_excerpt(ep.get("summary", ""), max_chars=340),
                }
            )
        notes_html = _render_notes_column_html(ep_notes, "Listen Episode")
        show_blocks.append(
            f"""
            <section id="show-{idx}">
              <div class="section-head">
                <h2>0{idx}. {show["name"]} — Host: {show["host"]}</h2>
                <span><a href="{show["apple_url"]}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none;">APPLE PODCASTS ↗</a></span>
              </div>
              <p style="font-family:var(--font-sans);font-size:0.84rem;color:var(--ink-muted);margin:0 0 8px;">Focus: {show["focus"]}</p>
              {notes_html}
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>The GenAI Briefing — Podcasts &amp; Episode Summaries</title>
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="podcasts", latest_date=latest_date)}
    {"".join(show_blocks)}
    <footer class="footer">
      <div>THE GENAI BRIEFING · AUDIO &amp; PODCASTS DIRECTORY</div>
      <div><a href="index.html">Front Page</a> · <a href="{latest_date}.html">Latest Issue</a></div>
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
    """Save the digest to a dated Markdown file, update `latest.md`, and build GitHub Pages HTML (`index.html`, `<date>.html`, `podcasts.html`)."""
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
        arch_title = f"The GenAI Briefing — {arch_date}"
        arch_html = _render_daily_digest_html(
            markdown_content=md_text,
            title=arch_title,
            current_date=arch_date,
            archive_dates=archive_dates,
        )
        (target_docs / f"{arch_date}.html").write_text(arch_html, encoding="utf-8")

    index_html = _render_index_portal_html(archive_map=archive_map)
    (target_docs / "index.html").write_text(index_html, encoding="utf-8")

    if docs_dir is None and output_dir.name == "digests":
        try:
            shows_data = fetch_detailed_podcast_hub(episodes_per_show=3)
            latest_d = archive_dates[-1] if archive_dates else date_str
            podcasts_page_html = _render_podcasts_page_html(
                shows_data=shows_data,
                latest_date=latest_d,
            )
            (target_docs / "podcasts.html").write_text(podcasts_page_html, encoding="utf-8")
        except Exception:
            pass

    return dated_path
