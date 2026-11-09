from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import markdown

from genai_agent.collectors.podcasts import fetch_detailed_podcast_hub

EDITORIAL_CSS_AND_JS = """
  <meta name="theme-color" id="meta-theme-color" content="#F6F4EF">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="format-detection" content="telephone=no">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap" rel="stylesheet">
  <style>
    /* Default: Warm Archival Paper (FT / Anthropic / Stripe Press inspired) */
    :root, [data-theme="sage"] {
      --bg: #F6F4EF;
      --surface: #FDFCF9;
      --surface-alt: #EFECE5;
      --ink: #121211;
      --ink-secondary: #2B2926;
      --ink-muted: #6B6860;
      --border: #DCD7CC;
      --border-strong: #121211;
      --accent: #9E2A2B;
      --accent-hover: #7A1C1D;
      --link: #1D4ED8;
      --font-serif: 'Newsreader', Georgia, serif;
      --font-display: 'Instrument Serif', 'Newsreader', Georgia, serif;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
      --base-size: 17px;
    }

    [data-theme="sepia"] {
      --bg: #F2E9D8;
      --surface: #F9F3E6;
      --surface-alt: #E8DEC8;
      --ink: #221B15;
      --ink-secondary: #382E26;
      --ink-muted: #6E5F52;
      --border: #D5C7B0;
      --border-strong: #221B15;
      --accent: #8C2D19;
      --accent-hover: #692010;
      --link: #0F5257;
    }

    [data-theme="dark"] {
      --bg: #111214;
      --surface: #18191C;
      --surface-alt: #202226;
      --ink: #F2F0EA;
      --ink-secondary: #D0CDC4;
      --ink-muted: #8A877F;
      --border: #2B2D31;
      --border-strong: #F2F0EA;
      --accent: #E07A5F;
      --accent-hover: #F29C85;
      --link: #7AA2F7;
    }

    * {
      box-sizing: border-box;
      -webkit-tap-highlight-color: transparent;
    }
    html {
      font-size: var(--base-size);
      scroll-behavior: smooth;
      -webkit-text-size-adjust: 100%;
      text-size-adjust: 100%;
      overflow-x: hidden;
    }
    body {
      font-family: var(--font-serif);
      background-color: var(--bg);
      color: var(--ink);
      line-height: 1.72;
      margin: 0;
      padding:
        env(safe-area-inset-top, 0px)
        max(20px, env(safe-area-inset-right, 20px))
        calc(72px + env(safe-area-inset-bottom, 0px))
        max(20px, env(safe-area-inset-left, 20px));
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
      overflow-x: hidden;
      overflow-wrap: break-word;
      word-break: break-word;
    }

    .page-wrap {
      max-width: 900px;
      margin: 0 auto;
      width: 100%;
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

    /* Category Filter Bar */
    .filter-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 8px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--border);
    }
    .filter-pill {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      padding: 5px 11px;
      border: 1px solid var(--border);
      background: var(--surface);
      color: var(--ink-secondary);
      cursor: pointer;
      border-radius: 3px;
      touch-action: manipulation;
    }
    .filter-pill:hover, .filter-pill.active {
      background: var(--ink);
      color: var(--bg);
      border-color: var(--ink);
      font-weight: 600;
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
      padding: 22px 0;
      border-bottom: 1px solid var(--border);
    }
    .briefing-item:last-child {
      border-bottom: none;
    }
    .briefing-num {
      font-family: var(--font-mono);
      font-size: 0.88rem;
      font-weight: 600;
      color: var(--accent);
      padding-top: 2px;
    }
    .briefing-content {
      min-width: 0;
    }
    .briefing-content h3 {
      font-family: var(--font-serif);
      font-size: 1.28rem;
      font-weight: 600;
      line-height: 1.34;
      letter-spacing: -0.01em;
      margin: 0 0 8px;
      max-width: 62ch;
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
      font-size: 0.72rem;
      color: var(--ink-muted);
      margin-bottom: 6px;
      display: flex;
      flex-wrap: wrap;
      gap: 6px 8px;
      align-items: center;
      line-height: 1.4;
    }
    .briefing-tag {
      text-transform: uppercase;
      letter-spacing: 0.06em;
      font-weight: 600;
      color: var(--accent);
    }
    .briefing-summary {
      font-family: var(--font-serif);
      font-size: 1.02rem;
      color: var(--ink-secondary);
      margin: 0 0 10px;
      line-height: 1.68;
      max-width: 66ch;
    }
    .briefing-summary var {
      font-family: var(--font-serif);
      font-style: italic;
      font-weight: 600;
      color: var(--ink);
    }
    .briefing-reddit {
      margin: 8px 0 10px;
      padding: 6px 12px;
      background: var(--surface);
      border: 1px solid var(--border);
      border-left: 3px solid var(--accent);
      font-family: var(--font-sans);
      font-size: 0.83rem;
      line-height: 1.48;
      color: var(--ink-secondary);
      max-width: 66ch;
    }
    .briefing-reddit strong {
      font-family: var(--font-mono);
      font-size: 0.71rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--accent);
      margin-right: 4px;
    }
    .briefing-reddit a {
      color: var(--ink);
      text-decoration: underline;
      text-decoration-color: var(--border);
      text-underline-offset: 2px;
    }
    .briefing-reddit a:hover {
      color: var(--accent);
      text-decoration-color: var(--accent);
    }
    .briefing-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
      margin-top: 8px;
      font-family: var(--font-mono);
      font-size: 0.73rem;
    }
    .briefing-actions a {
      color: var(--ink-secondary);
      text-decoration: none;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1px;
    }
    .briefing-actions a:hover {
      color: var(--accent);
      border-bottom-color: var(--accent);
    }

    /* Two-Column Editorial Split for X Threads & Podcasts */
    .two-col {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 36px;
      margin-top: 12px;
    }
    .two-col > section {
      min-width: 0;
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

    /* iPhone & Mobile Safari Optimizations */
    @media (max-width: 760px) {
      body {
        padding:
          env(safe-area-inset-top, 0px)
          max(16px, env(safe-area-inset-right, 16px))
          calc(56px + env(safe-area-inset-bottom, 0px))
          max(16px, env(safe-area-inset-left, 16px));
        line-height: 1.6;
      }
      .masthead {
        padding-top: 14px;
        margin-bottom: 22px;
      }
      .masthead-top {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        padding-bottom: 10px;
      }
      .controls {
        width: 100%;
        justify-content: flex-start;
        flex-wrap: wrap;
        gap: 6px;
      }
      .ctrl-btn {
        min-height: 32px;
        padding: 4px 8px;
        border: 1px solid var(--border);
        border-radius: 3px;
        touch-action: manipulation;
      }
      .ctrl-btn.active {
        border-color: var(--ink);
        background: var(--surface-alt);
        text-decoration: none;
      }
      .masthead-title-row {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        padding: 16px 0 14px;
      }
      .masthead-title {
        font-size: 2.2rem;
        line-height: 1.05;
      }
      .masthead-sub {
        font-size: 0.84rem;
        line-height: 1.45;
      }
      .masthead-nav {
        padding: 8px 0;
      }
      .nav-links {
        width: 100%;
        gap: 14px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        white-space: nowrap;
        padding-bottom: 2px;
      }
      .nav-links a {
        display: inline-block;
        padding: 4px 0;
      }
      .section-head {
        flex-direction: column;
        align-items: flex-start;
        gap: 4px;
        margin: 26px 0 14px;
      }
      .briefing-item {
        grid-template-columns: 28px 1fr;
        gap: 10px;
        padding: 15px 0;
      }
      .briefing-content h3 {
        font-size: 1.12rem;
        line-height: 1.35;
      }
      .briefing-summary {
        font-size: 0.94rem;
        line-height: 1.56;
      }
      .two-col {
        grid-template-columns: 1fr;
        gap: 12px;
      }
      .editorial-callout {
        padding: 14px 16px;
        margin: 14px 0 20px;
      }
      /* Stack Archive Table cleanly on iPhone screens */
      .archive-table thead {
        display: none;
      }
      .archive-table, .archive-table tbody, .archive-table tr, .archive-table td {
        display: block;
        width: 100%;
      }
      .archive-table tr {
        padding: 12px 0;
        border-bottom: 1px solid var(--border);
      }
      .archive-table td {
        padding: 2px 0;
        border-bottom: none;
      }
      .archive-date {
        width: auto;
        margin-bottom: 4px;
        color: var(--accent);
      }
      .footer {
        flex-direction: column;
        gap: 8px;
        margin-top: 40px;
      }
    }
  </style>
  <script>
    const THEME_COLORS = {
      sage: '#F6F4EF',
      sepia: '#F2E9D8',
      dark: '#111214'
    };

    function applyThemeColorMeta(theme) {
      const meta = document.getElementById('meta-theme-color');
      if (meta && THEME_COLORS[theme]) {
        meta.setAttribute('content', THEME_COLORS[theme]);
      }
    }

    (function() {
      const savedTheme = localStorage.getItem('genai_theme') || 'sage';
      document.documentElement.setAttribute('data-theme', savedTheme);
      applyThemeColorMeta(savedTheme);
      const savedSize = localStorage.getItem('genai_fontsize');
      if (savedSize) {
        document.documentElement.style.setProperty('--base-size', savedSize + 'px');
      }
    })();

    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('genai_theme', theme);
      applyThemeColorMeta(theme);
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
      applyThemeColorMeta(theme);
      document.querySelectorAll('[data-theme-btn]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-theme-btn') === theme);
      });
    }

    function filterBriefing(cat) {
      document.querySelectorAll('[data-filter-pill]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-filter-pill') === cat);
      });
      document.querySelectorAll('.briefing-item').forEach(item => {
        const itemCat = item.getAttribute('data-category') || '';
        item.style.display = (cat === 'all' || itemCat === cat) ? '' : 'none';
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
    best_sep = -1
    for sep in (". ", "? ", "! "):
        pos = cut.rfind(sep)
        if pos > best_sep:
            best_sep = pos
    if best_sep > 45:
        return cut[: best_sep + 1]
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
        <div>THE GENERATIVE AI TECHNICAL BRIEFING · {issue_label}</div>
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
          DAILY EDITION
        </div>
      </nav>
    </header>
    """


_REDDIT_TOPIC_STOPWORDS = {
    "the", "a", "an", "of", "for", "in", "on", "to", "and", "or", "with", "via",
    "towards", "from", "its", "is", "are", "how", "what", "why", "new", "latest",
    "announced", "we", "our", "your", "my", "by", "model", "models", "ai", "llm",
    "llms", "using", "into", "over", "more", "most", "can", "will", "not", "this",
    "that", "have", "has", "been", "when", "where", "who", "all", "almost", "enough",
}

_CACHED_REDDIT_POOL: List[Dict[str, Any]] | None = None


def _tokenize_for_reddit(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9]{3,}", (text or "").lower())
    return {w for w in words if w not in _REDDIT_TOPIC_STOPWORDS}


def _get_reddit_topic_pool() -> List[Dict[str, Any]]:
    """Fetch top 100 active discussions across AI subreddits in a single RSS request and cache in memory."""
    global _CACHED_REDDIT_POOL
    if _CACHED_REDDIT_POOL is not None:
        return _CACHED_REDDIT_POOL
    _CACHED_REDDIT_POOL = []
    try:
        import feedparser
        import httpx

        rss_url = (
            "https://www.reddit.com/r/"
            "LocalLLaMA+MachineLearning+ClaudeAI+OpenAI+singularity+ArtificialIntelligence/"
            "hot/.rss?limit=100"
        )
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        with httpx.Client(timeout=8.0, headers={"User-Agent": ua}, follow_redirects=True) as client:
            resp = client.get(rss_url)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.text)
                for entry in feed.entries:
                    title = (entry.get("title") or "").strip()
                    link = (entry.get("link") or "").strip()
                    if not title or not link:
                        continue
                    m = re.search(r"/r/([^/]+)/", link)
                    sub = f"r/{m.group(1)}" if m else "Reddit"
                    _CACHED_REDDIT_POOL.append(
                        {
                            "title": title,
                            "url": link,
                            "sub": sub,
                            "tokens": _tokenize_for_reddit(title),
                        }
                    )
    except Exception:
        pass
    return _CACHED_REDDIT_POOL


def _find_reddit_discussion(title: str) -> Tuple[Dict[str, str] | None, str]:
    """Return `(matched_thread_dict_or_None, topic_search_url)` for a briefing item."""
    from urllib.parse import quote_plus

    clean = re.sub(r"[^A-Za-z0-9\-\s]", " ", title or "")
    words = [w for w in clean.split() if len(w) > 2 and w.lower() not in _REDDIT_TOPIC_STOPWORDS]
    query = " ".join(words[:4]) or (title or "AI")
    search_url = (
        "https://www.reddit.com/r/LocalLLaMA+MachineLearning+ClaudeAI+OpenAI+singularity/search/"
        f"?q={quote_plus(query)}&restrict_sr=1&sort=top&t=month"
    )

    pool = _get_reddit_topic_pool()
    if not pool:
        return None, search_url

    story_tokens = _tokenize_for_reddit(title)
    if not story_tokens:
        return None, search_url

    best_entry: Dict[str, Any] | None = None
    best_score = 0
    title_low = (title or "").lower()

    for entry in pool:
        overlap = story_tokens & entry["tokens"]
        if not overlap:
            continue
        score = sum(3 if len(w) >= 6 else 2 for w in overlap)
        r_low = entry["title"].lower()
        for phrase in ("claude code", "gemini 4", "gpt-5", "gpt-6", "qwen", "deepseek", "llama", "scaling law"):
            if phrase in title_low and phrase in r_low:
                score += 5
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry and best_score >= 4:
        return {
            "title": best_entry["title"],
            "url": best_entry["url"],
            "sub": best_entry["sub"],
        }, search_url
    return None, search_url


_CACHED_URL_SUMMARIES: Dict[str, str] = {}


def _format_inline_math(text: str) -> str:
    """Convert raw inline LaTeX variables like `$L$` into clean typographic `<var>L</var>` tags."""
    if not text:
        return ""
    return re.sub(r"\$([A-Za-z0-9_^{}\-]+)\$", r"<var>\1</var>", text)


def _enrich_missing_summary(title: str, url: str, hn_url: str) -> str:
    """Fetch a clean 1-2 sentence summary from article metadata or HN discussion when a story has no summary."""
    cache_key = url or hn_url or title
    if cache_key in _CACHED_URL_SUMMARIES:
        return _CACHED_URL_SUMMARIES[cache_key]

    import html as _html

    ua = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
    extracted = ""
    try:
        import httpx

        if url and not url.startswith("https://news.ycombinator.com"):
            with httpx.Client(timeout=4.5, headers={"User-Agent": ua}, follow_redirects=True) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    head = resp.text[:30000]
                    for pat in (
                        r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
                        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description["\']',
                        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
                    ):
                        m = re.search(pat, head, flags=re.IGNORECASE)
                        if m:
                            cand = _html.unescape(m.group(1)).strip()
                            if len(cand) > 45:
                                extracted = cand
                                break
                    if not extracted:
                        for pm in re.finditer(r"<p[^>]*>(.*?)</p>", head, flags=re.IGNORECASE | re.DOTALL):
                            txt = re.sub(r"<[^>]+>", " ", pm.group(1))
                            txt = " ".join(_html.unescape(txt).split())
                            if len(txt) > 65 and not txt.lower().startswith(("cookie", "subscribe", "sign in")):
                                extracted = txt
                                break

        if not extracted and hn_url:
            id_m = re.search(r"id=(\d+)", hn_url)
            if id_m:
                with httpx.Client(timeout=4.0, follow_redirects=True) as client:
                    r_hn = client.get(f"https://hn.algolia.com/api/v1/items/{id_m.group(1)}")
                    if r_hn.status_code == 200:
                        data = r_hn.json()
                        for ch in data.get("children", [])[:4]:
                            raw_c = ch.get("text") or ""
                            clean_c = re.sub(r"<[^>]+>", " ", raw_c)
                            clean_c = re.sub(r"via\s+https?://\S+", "", _html.unescape(clean_c))
                            clean_c = re.sub(r"https?://\S+", "", clean_c)
                            clean_c = re.sub(r"\s+,", ",", clean_c)
                            clean_c = " ".join(clean_c.split())
                            if len(clean_c) > 60:
                                extracted = f"Community note: {clean_c}"
                                break
    except Exception:
        pass

    final_summary = _clean_excerpt(extracted, max_chars=280) if extracted else ""
    _CACHED_URL_SUMMARIES[cache_key] = final_summary
    return final_summary


def _render_top10_ledger_html(items: List[Dict[str, str]]) -> str:
    rows: List[str] = []
    cat_counts: Dict[str, int] = {}
    for it in items:
        cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1

    filter_pills = [
        f'<button class="filter-pill active" data-filter-pill="all" onclick="filterBriefing(\'all\')">All ({len(items)})</button>'
    ]
    for cat_name in ("Research", "Engineering", "Lab Release"):
        if cat_counts.get(cat_name):
            filter_pills.append(
                f'<button class="filter-pill" data-filter-pill="{cat_name}" onclick="filterBriefing(\'{cat_name}\')">{cat_name} ({cat_counts[cat_name]})</button>'
            )
    filter_bar_html = f'<div class="filter-bar">{"".join(filter_pills)}</div>'

    for it in items:
        matched_reddit, reddit_search_url = _find_reddit_discussion(it["title"])

        # Tier 1: Clean, uncluttered kicker above the headline
        kicker_bits = [f'<span class="briefing-tag">{it["category"]}</span>', f'<span>{it["source"]}</span>']
        if it["date"]:
            kicker_bits.append(f'<span>{it["date"]}</span>')

        # Tier 2: Substantive summary (auto-enriched if empty) + formatted inline math
        raw_summary = it["summary"] or _enrich_missing_summary(it["title"], it["url"], it["hn_url"])
        formatted_summary = _format_inline_math(raw_summary)
        summary_html = f'<p class="briefing-summary">{formatted_summary}</p>' if formatted_summary else ""

        reddit_callout_html = ""
        if matched_reddit:
            r_title = matched_reddit["title"]
            if len(r_title) > 135:
                r_title = r_title[:132].rsplit(" ", 1)[0] + "..."
            reddit_callout_html = (
                f'<div class="briefing-reddit">'
                f'<strong>Reddit ({matched_reddit["sub"]}):</strong> '
                f'<a href="{matched_reddit["url"]}" target="_blank" rel="noopener">{r_title} ↗</a>'
                f'</div>'
            )

        # Tier 3: Dedicated Action & Discussion Bar below the summary
        action_links: List[str] = []
        source_label = f'Read Source ({it["domain"]}) ↗' if it["domain"] else "Read Source ↗"
        action_links.append(f'<a href="{it["url"]}" target="_blank" rel="noopener">{source_label}</a>')

        if it["points"]:
            if it["hn_url"] and it["hn_url"] != it["url"]:
                action_links.append(
                    f'<a href="{it["hn_url"]}" target="_blank" rel="noopener">HN Discussion ({it["points"]} pts) ↗</a>'
                )
            else:
                action_links.append(f'<span>{it["points"]} pts</span>')
        elif it["hn_url"] and it["hn_url"] != it["url"]:
            action_links.append(f'<a href="{it["hn_url"]}" target="_blank" rel="noopener">HN Discussion ↗</a>')

        if matched_reddit:
            action_links.append(
                f'<a href="{matched_reddit["url"]}" target="_blank" rel="noopener">{matched_reddit["sub"]} Thread ↗</a>'
            )
        else:
            action_links.append(
                f'<a href="{reddit_search_url}" target="_blank" rel="noopener">Reddit Topic ↗</a>'
            )

        rows.append(
            f"""
            <article class="briefing-item" data-category="{it["category"]}">
              <div class="briefing-num">{it["rank"]}</div>
              <div class="briefing-content">
                <div class="briefing-meta">{'<span>·</span>'.join(kicker_bits)}</div>
                <h3><a href="{it["url"]}" target="_blank" rel="noopener">{it["title"]}</a></h3>
                {summary_html}
                {reddit_callout_html}
                <div class="briefing-actions">{"".join(action_links)}</div>
              </div>
            </article>
            """
        )
    return f'{filter_bar_html}<div class="briefing-list">{"".join(rows)}</div>'


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
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
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
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
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
      <div>THE GENAI BRIEFING · PUBLISHED DAILY</div>
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
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
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
