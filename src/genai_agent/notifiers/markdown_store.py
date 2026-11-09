from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import markdown

from genai_agent.collectors.podcasts import fetch_detailed_podcast_hub

SHARED_CSS_AND_THEME_JS = """
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:ital,wght@0,400;0,700;1,400&family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&family=JetBrains+Mono:wght@400;500;600&family=Literata:ital,opsz,wght@0,7..72,400;0,7..72,500;0,7..72,600;1,7..72,400&display=swap" rel="stylesheet">
  <style>
    /* Default: Warm Botanical Sage Paper (Zero Pure-White Glare) */
    :root, [data-theme="sage"] {
      --bg: #EFECE6;
      --bg-pattern: radial-gradient(rgba(15, 118, 110, 0.05) 1px, transparent 1px);
      --bg-elevated: #F9F6F0;
      --bg-card-inner: #F2EFE9;
      --text: #222623;
      --text-secondary: #525852;
      --border: #DCD6CA;
      --accent: #0F766E;
      --accent-hover: #0D9488;
      --accent-soft: rgba(15, 118, 110, 0.10);
      --accent-warm: #B45309;
      --accent-warm-soft: rgba(180, 83, 9, 0.10);
      --x-accent: #1D9BF0;
      --x-card-bg: #FCFBF8;
      --x-border: #D6D0C4;
      --gradient: linear-gradient(135deg, #0F766E 0%, #3B82F6 55%, #D97706 100%);
      --shadow: 0 6px 24px -4px rgba(34, 38, 35, 0.06), 0 2px 6px -1px rgba(34, 38, 35, 0.04);
      --font-body: 'Literata', Georgia, serif;
      --font-sans: 'Atkinson Hyperlegible', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-display: 'Fraunces', Georgia, serif;
      --font-mono: 'JetBrains Mono', monospace;
      --base-size: 17.5px;
    }

    /* Mode 2: Kindle Warm Sepia Parchment */
    [data-theme="sepia"] {
      --bg: #F4ECD8;
      --bg-pattern: radial-gradient(rgba(146, 64, 14, 0.05) 1px, transparent 1px);
      --bg-elevated: #FAF4E6;
      --bg-card-inner: #EFE6D2;
      --text: #2C221E;
      --text-secondary: #5C4D43;
      --border: #DFD2BA;
      --accent: #9A3412;
      --accent-hover: #B45309;
      --accent-soft: rgba(154, 52, 18, 0.10);
      --accent-warm: #0F766E;
      --accent-warm-soft: rgba(15, 118, 110, 0.10);
      --x-accent: #0284C7;
      --x-card-bg: #FDF8EC;
      --x-border: #D8C8AE;
      --gradient: linear-gradient(135deg, #9A3412 0%, #D97706 55%, #0F766E 100%);
      --shadow: 0 6px 24px -4px rgba(44, 34, 30, 0.07);
    }

    /* Mode 3: Low-Blue-Light Nord Midnight Slate */
    [data-theme="dark"] {
      --bg: #13171F;
      --bg-pattern: radial-gradient(rgba(94, 234, 212, 0.04) 1px, transparent 1px);
      --bg-elevated: #1B212C;
      --bg-card-inner: #232B38;
      --text: #E2E8F0;
      --text-secondary: #94A3B8;
      --border: #2E3846;
      --accent: #5EEAD4;
      --accent-hover: #2DD4BF;
      --accent-soft: rgba(94, 234, 212, 0.12);
      --accent-warm: #FBBF24;
      --accent-warm-soft: rgba(251, 191, 36, 0.12);
      --x-accent: #38BDF8;
      --x-card-bg: #161B24;
      --x-border: #2E3A4C;
      --gradient: linear-gradient(135deg, #2DD4BF 0%, #818CF8 55%, #FBBF24 100%);
      --shadow: 0 10px 30px -6px rgba(0, 0, 0, 0.5);
    }

    * { box-sizing: border-box; }
    html {
      font-size: var(--base-size);
      scroll-behavior: smooth;
    }
    body {
      font-family: var(--font-body);
      background-color: var(--bg);
      background-image: var(--bg-pattern);
      background-size: 24px 24px;
      color: var(--text);
      line-height: 1.78;
      letter-spacing: 0.005em;
      margin: 0;
      padding: 0 16px 64px;
      transition: background-color 0.25s ease, color 0.25s ease;
      -webkit-font-smoothing: antialiased;
    }

    #progress-bar {
      position: fixed;
      top: 0;
      left: 0;
      width: 0%;
      height: 4px;
      background: var(--gradient);
      z-index: 1000;
      transition: width 0.1s ease-out;
    }

    .container {
      max-width: 900px;
      margin: 0 auto;
    }

    .top-nav {
      position: sticky;
      top: 10px;
      z-index: 100;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      padding: 12px 18px;
      margin: 14px 0 20px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 14px;
      box-shadow: var(--shadow);
      font-family: var(--font-sans);
    }
    .brand {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 0.96rem;
      color: var(--text);
      text-decoration: none;
    }
    .brand-dot {
      width: 12px;
      height: 12px;
      border-radius: 4px;
      background: var(--gradient);
      display: inline-block;
      transform: rotate(45deg);
    }
    .nav-actions {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }
    .pill-link {
      padding: 5px 12px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      font-family: var(--font-mono);
      text-decoration: none;
      background: var(--bg-card-inner);
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
      color: var(--bg-elevated);
      border-color: var(--accent);
    }
    .comfort-group {
      display: inline-flex;
      align-items: center;
      background: var(--bg-card-inner);
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 2px;
      gap: 2px;
    }
    .comfort-btn {
      cursor: pointer;
      background: transparent;
      color: var(--text-secondary);
      border: none;
      border-radius: 999px;
      padding: 4px 10px;
      font-size: 0.76rem;
      font-weight: 700;
      font-family: var(--font-sans);
      transition: all 0.15s ease;
    }
    .comfort-btn:hover, .comfort-btn.active {
      background: var(--bg-elevated);
      color: var(--accent);
      box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    .jump-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 22px;
      padding: 12px 16px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 12px;
      font-family: var(--font-sans);
      align-items: center;
    }
    .jump-label {
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-secondary);
      margin-right: 4px;
    }

    .hero {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 36px;
      margin-bottom: 28px;
      box-shadow: var(--shadow);
      position: relative;
      overflow: hidden;
    }
    .hero::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 5px;
      background: var(--gradient);
    }
    .hero-badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: var(--font-mono);
      font-size: 0.74rem;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      padding: 5px 12px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      margin-bottom: 12px;
    }

    .card {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 40px 44px;
      box-shadow: var(--shadow);
    }

    .section-panel {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 28px 32px;
      margin-top: 26px;
      box-shadow: var(--shadow);
    }
    .section-panel.x-panel {
      border-top: 4px solid var(--x-accent);
    }
    .section-panel.podcast-panel {
      border-top: 4px solid var(--accent-warm);
    }

    /* Authentic X / Twitter Post Snippet Cards */
    .x-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 16px;
      margin: 18px 0 10px;
    }
    .x-tweet-card {
      background: var(--x-card-bg);
      border: 1px solid var(--x-border);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      font-family: var(--font-sans);
      transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
    }
    .x-tweet-card:hover {
      transform: translateY(-2px);
      border-color: var(--x-accent);
      box-shadow: var(--shadow);
    }
    .x-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .x-author {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .x-avatar {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: var(--gradient);
      color: #FFFFFF;
      font-weight: 700;
      font-size: 0.88rem;
      font-family: var(--font-mono);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .x-name-row {
      display: flex;
      align-items: center;
      gap: 5px;
      font-weight: 700;
      font-size: 0.92rem;
      color: var(--text);
      line-height: 1.2;
    }
    .x-verified {
      color: var(--x-accent);
      font-size: 0.88rem;
    }
    .x-handle {
      font-size: 0.78rem;
      color: var(--text-secondary);
      font-family: var(--font-mono);
    }
    .x-logo {
      font-size: 1.15rem;
      font-weight: 700;
      color: var(--text-secondary);
      text-decoration: none !important;
      line-height: 1;
    }
    .x-title {
      font-size: 0.98rem;
      font-weight: 700;
      color: var(--text);
      margin: 0 0 8px;
      line-height: 1.4;
    }
    .x-title a {
      color: var(--text);
      text-decoration: none;
    }
    .x-title a:hover {
      color: var(--x-accent);
      text-decoration: underline;
    }
    .x-body {
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.58;
      margin: 0 0 14px;
    }
    .x-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 8px;
      padding-top: 12px;
      border-top: 1px solid var(--border);
      font-size: 0.76rem;
      font-family: var(--font-mono);
      color: var(--text-secondary);
    }
    .x-metrics {
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }
    .x-metric-pill {
      background: var(--bg-card-inner);
      padding: 3px 9px;
      border-radius: 999px;
      border: 1px solid var(--border);
      font-weight: 600;
    }
    .x-links {
      display: inline-flex;
      gap: 10px;
      font-weight: 700;
    }
    .x-links a {
      color: var(--x-accent);
      text-decoration: none;
    }
    .x-links a:hover {
      text-decoration: underline;
    }

    /* Stylized Podcast Episode Cards */
    .pod-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 16px;
      margin: 18px 0 10px;
    }
    .pod-card {
      background: var(--x-card-bg);
      border: 1px solid var(--x-border);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      font-family: var(--font-sans);
      transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
    }
    .pod-card:hover {
      transform: translateY(-2px);
      border-color: var(--accent-warm);
      box-shadow: var(--shadow);
    }
    .pod-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
    }
    .pod-show-info {
      display: flex;
      align-items: center;
      gap: 11px;
    }
    .pod-artwork {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: linear-gradient(135deg, #D97706 0%, #7C3AED 100%);
      color: #FFFFFF;
      font-size: 1.15rem;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      box-shadow: 0 3px 10px rgba(217, 119, 6, 0.22);
    }
    .pod-show-name {
      font-weight: 700;
      font-size: 0.88rem;
      color: var(--accent-warm);
      line-height: 1.25;
    }
    .pod-sub {
      font-size: 0.75rem;
      color: var(--text-secondary);
      font-family: var(--font-mono);
    }
    .pod-duration {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
      background: var(--accent-warm-soft);
      color: var(--accent-warm);
      padding: 4px 10px;
      border-radius: 999px;
      white-space: nowrap;
    }
    .pod-title {
      font-size: 0.98rem;
      font-weight: 700;
      color: var(--text);
      margin: 0 0 8px;
      line-height: 1.4;
    }
    .pod-title a {
      color: var(--text);
      text-decoration: none;
    }
    .pod-title a:hover {
      color: var(--accent-warm);
      text-decoration: underline;
    }
    .pod-body {
      font-size: 0.88rem;
      color: var(--text-secondary);
      line-height: 1.58;
      margin: 0 0 14px;
    }
    .pod-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      padding-top: 12px;
      border-top: 1px solid var(--border);
    }
    .pod-wave {
      font-family: var(--font-mono);
      font-size: 0.76rem;
      letter-spacing: 2px;
      color: var(--text-secondary);
      opacity: 0.75;
    }
    .pod-play-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: var(--accent-warm-soft);
      color: var(--accent-warm) !important;
      border: 1px solid var(--border);
      padding: 5px 13px;
      border-radius: 999px;
      font-size: 0.78rem;
      font-weight: 700;
      text-decoration: none !important;
      transition: all 0.15s ease;
    }
    .pod-play-btn:hover {
      background: var(--accent-warm);
      color: #FFFFFF !important;
    }

    h1, h2 {
      font-family: var(--font-display);
      font-weight: 600;
      letter-spacing: -0.02em;
      line-height: 1.28;
      color: var(--text);
    }
    h1 {
      font-size: 2.05rem;
      margin: 4px 0 16px;
    }
    h2 {
      font-size: 1.48rem;
      margin: 36px 0 16px;
      padding-bottom: 10px;
      border-bottom: 2px solid var(--border);
    }

    h3 {
      font-family: var(--font-display);
      font-size: 1.16rem;
      font-weight: 600;
      margin: 24px 0 0;
      line-height: 1.42;
      padding: 18px 22px 8px;
      background: var(--bg-card-inner);
      border-top-left-radius: 14px;
      border-top-right-radius: 14px;
      border: 1px solid var(--border);
      border-left: 4px solid var(--accent);
      border-bottom: none;
    }
    h3 + p {
      font-family: var(--font-sans);
      font-size: 0.86rem;
      color: var(--text-secondary);
      background: var(--bg-card-inner);
      margin: 0;
      padding: 2px 22px 10px;
      border-left: 4px solid var(--accent);
      border-right: 1px solid var(--border);
    }
    h3 + p + ul {
      background: var(--bg-card-inner);
      margin: 0 0 18px 0;
      padding: 4px 24px 18px 40px;
      border: 1px solid var(--border);
      border-left: 4px solid var(--accent);
      border-top: none;
      border-bottom-left-radius: 14px;
      border-bottom-right-radius: 14px;
    }

    a {
      color: var(--accent);
      text-decoration: underline;
      text-decoration-thickness: 1.5px;
      text-underline-offset: 3px;
      transition: color 0.15s ease;
    }
    a:hover {
      color: var(--accent-hover);
    }

    blockquote {
      font-family: var(--font-sans);
      margin: 18px 0 26px;
      padding: 16px 22px;
      background: var(--accent-soft);
      border-left: 4px solid var(--accent);
      border-radius: 12px;
      color: var(--text);
      font-size: 0.92rem;
      line-height: 1.65;
    }

    ul, ol {
      padding-left: 24px;
    }
    li {
      margin-bottom: 10px;
    }
    li strong {
      font-family: var(--font-sans);
    }

    hr {
      border: none;
      border-top: 1px dashed var(--border);
      margin: 34px 0;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(370px, 1fr));
      gap: 20px;
      margin-top: 18px;
    }
    .day-card {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 26px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      transition: transform 0.18s ease, border-color 0.18s ease;
    }
    .day-card:hover {
      transform: translateY(-3px);
      border-color: var(--accent);
    }
    .day-card h3 {
      background: none;
      border: none;
      padding: 0;
      margin: 6px 0 10px;
      font-family: var(--font-display);
      font-size: 1.35rem;
    }
    .day-card h3 a {
      text-decoration: none;
    }
    .day-card ul {
      padding-left: 18px;
      margin: 8px 0 20px;
      color: var(--text-secondary);
      font-size: 0.9rem;
      font-family: var(--font-sans);
    }
    .day-card li { margin-bottom: 7px; }

    .cta-btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-family: var(--font-sans);
      background: var(--accent);
      color: var(--bg-elevated) !important;
      padding: 10px 20px;
      border-radius: 10px;
      font-size: 0.88rem;
      font-weight: 700;
      text-decoration: none !important;
      align-self: flex-start;
      transition: transform 0.15s ease, opacity 0.15s ease;
    }
    .cta-btn:hover {
      opacity: 0.92;
      transform: translateX(2px);
    }

    .footer {
      text-align: center;
      font-family: var(--font-sans);
      font-size: 0.84rem;
      color: var(--text-secondary);
      margin-top: 42px;
      padding-top: 20px;
      border-top: 1px solid var(--border);
    }

    @media (max-width: 640px) {
      .card, .hero, .section-panel { padding: 22px 18px; }
      .grid, .x-grid, .pod-grid { grid-template-columns: 1fr; }
      h1 { font-size: 1.6rem; }
      .top-nav { position: static; }
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
      const savedFont = localStorage.getItem('genai_fontfamily');
      if (savedFont === 'sans') {
        document.documentElement.style.setProperty('--font-body', "var(--font-sans)");
      }
    })();

    function setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('genai_theme', theme);
      updateToolbarState();
    }

    function toggleFontFamily() {
      const current = localStorage.getItem('genai_fontfamily') || 'serif';
      const next = current === 'serif' ? 'sans' : 'serif';
      localStorage.setItem('genai_fontfamily', next);
      if (next === 'sans') {
        document.documentElement.style.setProperty('--font-body', "var(--font-sans)");
      } else {
        document.documentElement.style.setProperty('--font-body', "'Literata', Georgia, serif");
      }
      updateToolbarState();
    }

    function adjustFontSize(delta) {
      const current = parseFloat(localStorage.getItem('genai_fontsize') || '17.5');
      const next = Math.min(22, Math.max(15, current + delta));
      localStorage.setItem('genai_fontsize', next);
      document.documentElement.style.setProperty('--base-size', next + 'px');
    }

    function updateToolbarState() {
      const theme = document.documentElement.getAttribute('data-theme') || 'sage';
      document.querySelectorAll('[data-theme-btn]').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-theme-btn') === theme);
      });
      const font = localStorage.getItem('genai_fontfamily') || 'serif';
      const fontBtn = document.getElementById('font-toggle-btn');
      if (fontBtn) {
        fontBtn.textContent = font === 'serif' ? 'Aa Serif' : 'Aa Sans';
      }
    }

    window.addEventListener('DOMContentLoaded', () => {
      updateToolbarState();
      document.querySelectorAll('h2').forEach(h => {
        const text = h.textContent.toLowerCase();
        if (text.includes('tl;dr') || text.includes('executive')) h.id = 'tldr';
        else if (text.includes('concept')) h.id = 'concept';
        else if (text.includes('top 10')) h.id = 'top10';
        else if (text.includes('x.com') || text.includes('twitter')) h.id = 'x-pulse';
        else if (text.includes('podcast') || text.includes('audio')) h.id = 'podcasts';
      });
      window.addEventListener('scroll', () => {
        const bar = document.getElementById('progress-bar');
        if (!bar) return;
        const winScroll = document.body.scrollTop || document.documentElement.scrollTop;
        const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        bar.style.width = (height > 0 ? (winScroll / height) * 100 : 0) + '%';
      });
    });
  </script>
"""

COMFORT_CONTROLS_HTML = """
        <div class="comfort-group" title="Eye-friendly color palettes">
          <button class="comfort-btn" data-theme-btn="sage" onclick="setTheme('sage')">🌿 Sage</button>
          <button class="comfort-btn" data-theme-btn="sepia" onclick="setTheme('sepia')">📜 Sepia</button>
          <button class="comfort-btn" data-theme-btn="dark" onclick="setTheme('dark')">🌙 Night</button>
        </div>
        <div class="comfort-group" title="Reading font &amp; size">
          <button class="comfort-btn" id="font-toggle-btn" onclick="toggleFontFamily()">Aa Serif</button>
          <button class="comfort-btn" onclick="adjustFontSize(-1)">A-</button>
          <button class="comfort-btn" onclick="adjustFontSize(1)">A+</button>
        </div>
"""


def _extract_top_headlines(markdown_text: str, max_items: int = 3) -> List[Tuple[str, str]]:
    """Extract the top N numbered `(title, url)` pairs from a digest Markdown file."""
    headlines: List[Tuple[str, str]] = []
    for line in markdown_text.splitlines():
        m = re.match(r"^###\s+\d+\.\s+\[([^\]]+)\]\(([^)]+)\)", line.strip())
        if m:
            headlines.append((m.group(1), m.group(2)))
            if len(headlines) >= max_items:
                break
    if not headlines:
        for line in markdown_text.splitlines():
            m = re.match(r"^-\s+\*\*\[([^\]]+)\]\(([^)]+)\)", line.strip())
            if m:
                headlines.append((m.group(1), m.group(2)))
                if len(headlines) >= max_items:
                    break
    return headlines


def _extract_section_markdown(markdown_text: str, section_keyword: str) -> str:
    """Extract a `## ...` section block matching `section_keyword` from a digest Markdown string."""
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


def _render_x_cards_html(x_section_md: str) -> str:
    """Parse X.com Markdown bullet items and render them as stylized Twitter/X Snippet Cards."""
    if not x_section_md.strip():
        return ""

    cards_html: List[str] = []
    lines = [ln for ln in x_section_md.splitlines() if ln.strip()]

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("- **["):
            m = re.match(r"^-\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*(.*)$", line)
            title = m.group(1) if m else line
            url = m.group(2) if m else "#"
            meta_tail = m.group(3) if m else ""

            desc = ""
            if idx + 1 < len(lines) and not lines[idx + 1].strip().startswith("- **["):
                desc = lines[idx + 1].strip().lstrip("- ").strip()
                desc = re.sub(r"^\*\*[^*]+:\*\*\s*", "", desc)
                desc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", desc)
                desc = re.sub(r"`([^`]+)`", r"<code>\1</code>", desc)
                idx += 1

            # Extract handle from URL or title
            handle_match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url)
            title_handle = re.search(r"@([A-Za-z0-9_]+)", title)
            if handle_match:
                handle = f"@{handle_match.group(1)}"
            elif title_handle:
                handle = f"@{title_handle.group(1)}"
            elif "smol.ai" in url or "AINews" in meta_tail:
                handle = "@swyx · AINews"
            else:
                handle = "@AI_Pulse"

            clean_title = re.sub(r"\s*\(@[A-Za-z0-9_]+\s+on\s+X\)", "", title)
            initials = "".join(ch for ch in handle if ch.isalnum())[:2].upper() or "AI"
            author_name = (
                "AINews X Recap"
                if "smol.ai" in url
                else (handle.lstrip("@") if handle != "@AI_Pulse" else "AI Researcher Pulse")
            )

            # Extract HN link & metrics if present
            hn_match = re.search(r"\[(HN Discussion)\]\(([^)]+)\)", meta_tail)
            hn_url = hn_match.group(2) if hn_match else ""
            pts_match = re.search(r"⬆️\s*([0-9,]+\s*pts)", meta_tail)
            pts_text = f"❤️ {pts_match.group(1)}" if pts_match else "🔥 Trending on X"
            comments_match = re.search(r"([0-9,]+\s*comments)", meta_tail)
            comments_text = f"💬 {comments_match.group(1)}" if comments_match else ""

            metric_pills = f'<span class="x-metric-pill">{pts_text}</span>'
            if comments_text:
                metric_pills += f'<span class="x-metric-pill">{comments_text}</span>'

            hn_link_html = (
                f'<a href="{hn_url}" target="_blank" rel="noopener">HN Thread ↗</a>'
                if hn_url
                else ""
            )

            cards_html.append(
                f"""
                <article class="x-tweet-card">
                  <div>
                    <div class="x-header">
                      <div class="x-author">
                        <div class="x-avatar">{initials}</div>
                        <div>
                          <div class="x-name-row">
                            <span>{author_name}</span>
                            <span class="x-verified" title="Verified AI Thread">✔</span>
                          </div>
                          <div class="x-handle">{handle}</div>
                        </div>
                      </div>
                      <a class="x-logo" href="{url}" target="_blank" rel="noopener" title="Open on X">𝕏</a>
                    </div>
                    <h4 class="x-title"><a href="{url}" target="_blank" rel="noopener">“{clean_title}”</a></h4>
                    <p class="x-body">{desc}</p>
                  </div>
                  <div class="x-footer">
                    <div class="x-metrics">{metric_pills}</div>
                    <div class="x-links">
                      {hn_link_html}
                      <a href="{url}" target="_blank" rel="noopener">Post on 𝕏 ↗</a>
                    </div>
                  </div>
                </article>
                """
            )
        idx += 1

    if not cards_html:
        return markdown.markdown(x_section_md, extensions=["extra", "sane_lists", "nl2br"])

    return f'<div class="x-grid">{"".join(cards_html)}</div>'


def _render_podcast_cards_html(pod_section_md: str) -> str:
    """Parse AI Podcast Markdown bullet items and render them as stylized Audio Player Cards."""
    if not pod_section_md.strip():
        return ""

    cards_html: List[str] = []
    lines = [ln for ln in pod_section_md.splitlines() if ln.strip()]

    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("- **["):
            m = re.match(r"^-\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*(.*)$", line)
            title = m.group(1) if m else line
            url = m.group(2) if m else "#"
            meta_tail = m.group(3) if m else ""

            desc = ""
            if idx + 1 < len(lines) and not lines[idx + 1].strip().startswith("- **["):
                desc = lines[idx + 1].strip().lstrip("- ").strip()
                desc = re.sub(r"^\*\*[^*]+:\*\*\s*", "", desc)
                desc = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", desc)
                desc = re.sub(r"`([^`]+)`", r"<code>\1</code>", desc)
                idx += 1

            show_match = re.search(r"—\s*(?:\*|\*\*)([^*]+)(?:\*|\*\*)", meta_tail)
            show_name = show_match.group(1).strip() if show_match else "AI Podcast"

            dur_match = re.search(r"🎧\s*([0-9hm:\s]+)", meta_tail + " " + desc)
            duration_badge = f"🎧 {dur_match.group(1).strip()}" if dur_match else "🎧 Audio Episode"

            cards_html.append(
                f"""
                <article class="pod-card">
                  <div>
                    <div class="pod-header">
                      <div class="pod-show-info">
                        <div class="pod-artwork">🎙️</div>
                        <div>
                          <div class="pod-show-name">{show_name}</div>
                          <div class="pod-sub">AI Audio Deep-Dive</div>
                        </div>
                      </div>
                      <span class="pod-duration">{duration_badge}</span>
                    </div>
                    <h4 class="pod-title"><a href="{url}" target="_blank" rel="noopener">{title}</a></h4>
                    <p class="pod-body">{desc}</p>
                  </div>
                  <div class="pod-footer">
                    <span class="pod-wave">ılılılılılılılı</span>
                    <a class="pod-play-btn" href="{url}" target="_blank" rel="noopener">▶ Listen Episode ↗</a>
                  </div>
                </article>
                """
            )
        idx += 1

    if not cards_html:
        return markdown.markdown(pod_section_md, extensions=["extra", "sane_lists", "nl2br"])

    return f'<div class="pod-grid">{"".join(cards_html)}</div>'


def _replace_x_section_with_cards(markdown_content: str) -> str:
    """Replace the raw `## 🔥 Hot on X.com` and `## 🎧 AI Podcasts` markdown lists with styled cards before rendering."""
    x_md = _extract_section_markdown(markdown_content, "X.com")
    if x_md:
        x_cards_html = _render_x_cards_html(x_md)
        pattern_x = re.compile(
            r"(##\s+🔥\s+Hot on X\.com[^\n]*\n)(.*?)(?=\n---\n|\n##\s+|\Z)",
            re.DOTALL,
        )
        markdown_content = pattern_x.sub(rf"\1\n{x_cards_html}\n", markdown_content)

    pod_md = _extract_section_markdown(markdown_content, "Podcast")
    if pod_md:
        pod_cards_html = _render_podcast_cards_html(pod_md)
        pattern_pod = re.compile(
            r"(##\s+🎧\s+AI Podcasts[^\n]*\n)(.*?)(?=\n---\n|\n##\s+|\Z)",
            re.DOTALL,
        )
        markdown_content = pattern_pod.sub(rf"\1\n{pod_cards_html}\n", markdown_content)

    return markdown_content


def _render_daily_digest_html(
    markdown_content: str,
    title: str,
    current_date: str,
    archive_dates: List[str],
) -> str:
    """Render a daily digest page (`YYYY-MM-DD.html`) with stylized X Snippet Cards and eye-friendly controls."""
    enriched_md = _replace_x_section_with_cards(markdown_content)
    body_html = markdown.markdown(
        enriched_md,
        extensions=["extra", "sane_lists", "nl2br"],
    )

    date_pills = []
    for d in sorted(archive_dates, reverse=True):
        active_cls = "pill-link active" if d == current_date else "pill-link"
        date_pills.append(f'<a class="{active_cls}" href="{d}.html">{d}</a>')

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  {SHARED_CSS_AND_THEME_JS}
</head>
<body>
  <div id="progress-bar"></div>
  <div class="container">
    <nav class="top-nav">
      <a class="brand" href="index.html">
        <span class="brand-dot"></span>
        <span>← All Editions</span>
      </a>
      <div class="nav-actions">
        <a class="pill-link" href="podcasts.html">🎙️ Podcasts Hub</a>
        {"".join(date_pills)}
        {COMFORT_CONTROLS_HTML}
      </div>
    </nav>

    <div class="jump-bar">
      <span class="jump-label">Jump to:</span>
      <a class="pill-link" href="#tldr">⚡ TL;DR</a>
      <a class="pill-link" href="#concept">🧠 Concept Deep-Dive</a>
      <a class="pill-link" href="#top10">🏆 Top 10 Ranked</a>
      <a class="pill-link" href="#x-pulse">🔥 Hot on 𝕏</a>
      <a class="pill-link" href="#podcasts">🎧 AI Podcasts</a>
    </div>

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
    """Render `docs/index.html` with Top 10 previews, stylized 𝕏 Snippet Cards, 🎧 Podcasts, and Daily Editions."""
    sorted_dates = sorted(archive_map.keys(), reverse=True)
    latest_date = sorted_dates[0] if sorted_dates else ""
    latest_md = archive_map.get(latest_date, "")
    latest_headlines = _extract_top_headlines(latest_md, max_items=4)

    latest_list_html = "".join(
        f'<li><a href="{url}" target="_blank" rel="noopener">{title} ↗</a></li>'
        for title, url in latest_headlines
    )

    x_pulse_md = _extract_section_markdown(latest_md, "X.com")
    x_pulse_html = _render_x_cards_html(x_pulse_md) or "<p>No X.com highlights extracted for this edition.</p>"

    podcasts_md = _extract_section_markdown(latest_md, "Podcast")
    podcasts_html = _render_podcast_cards_html(podcasts_md) or "<p>No podcast episodes extracted for this edition.</p>"

    day_cards_html = []
    for idx, d in enumerate(sorted_dates):
        md_text = archive_map[d]
        headlines = _extract_top_headlines(md_text, max_items=3)
        hl_items = (
            "".join(
                f'<li><a href="{url}" target="_blank" rel="noopener">{title} ↗</a></li>'
                for title, url in headlines
            )
            or f'<li><a href="{d}.html">Top 10 curated GenAI papers, lab blogs, X.com threads &amp; podcasts</a></li>'
        )
        badge_label = "✨ Latest Edition" if idx == 0 else "📅 Daily Edition"
        day_cards_html.append(
            f"""
            <article class="day-card">
              <div>
                <span class="hero-badge">{badge_label} · 5 min read</span>
                <h3><a href="{d}.html">GenAI Top 10 Digest — {d}</a></h3>
                <p style="margin:4px 0 8px;font-size:0.86rem;color:var(--text-secondary);font-family:var(--font-sans);">Top stories ranked by technical substance &amp; community reach:</p>
                <ul>{hl_items}</ul>
              </div>
              <a class="cta-btn" href="{d}.html">Read {d} Digest →</a>
            </article>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Generative AI Learning &amp; News Hub — Daily Top 10 Index</title>
  {SHARED_CSS_AND_THEME_JS}
</head>
<body>
  <div id="progress-bar"></div>
  <div class="container">
    <nav class="top-nav">
      <a class="brand" href="index.html">
        <span class="brand-dot"></span>
        <span>GenAI Learning Hub</span>
      </a>
      <div class="nav-actions">
        <a class="pill-link active" href="index.html">All Editions ({len(sorted_dates)})</a>
        <a class="pill-link" href="#x-highlights">🔥 Hot on 𝕏</a>
        <a class="pill-link" href="podcasts.html">🎙️ Podcasts Hub</a>
        <a class="pill-link" href="{latest_date}.html">Latest ({latest_date})</a>
        {COMFORT_CONTROLS_HTML}
      </div>
    </nav>

    <section class="hero">
      <span class="hero-badge">🧠 Eye-Friendly Daily AI Reader</span>
      <h1>Generative AI Daily Top 10, 𝕏 Pulse &amp; Audio Hub</h1>
      <p style="color:var(--text-secondary);font-size:1.02rem;margin:0 0 18px;">
        Signal over noise: Every edition distills 60+ research papers (Hugging Face &amp; arXiv), AI lab blogs (OpenAI, Google, DeepMind, Anthropic), Hacker News, r/LocalLLaMA, <strong>viral 𝕏 threads</strong>, and <strong>AI Podcasts</strong> into a calm, <strong>5-minute Top 10 read</strong>.
      </p>
      <div style="background:var(--bg-card-inner);border:1px solid var(--border);border-left:4px solid var(--accent);border-radius:12px;padding:16px 22px;margin-bottom:22px;font-family:var(--font-sans);">
        <div style="font-weight:700;font-size:0.9rem;margin-bottom:8px;color:var(--accent);">🏆 Top Headlines in Latest Edition ({latest_date}):</div>
        <ul style="margin:0;padding-left:20px;font-size:0.92rem;">
          {latest_list_html}
        </ul>
      </div>
      <a class="cta-btn" href="{latest_date}.html">Open Full {latest_date} Digest →</a>
    </section>

    <section id="x-highlights" class="section-panel x-panel">
      <span class="hero-badge">🔥 Live AI Social Pulse ({latest_date})</span>
      <h2 style="margin-top:4px;margin-bottom:6px;">Hot on 𝕏 (AI Twitter Highlights)</h2>
      {x_pulse_html}
    </section>

    <section id="podcast-highlights" class="section-panel podcast-panel">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
          <span class="hero-badge">🎧 Audio Deep-Dives ({latest_date})</span>
          <h2 style="margin-top:4px;margin-bottom:8px;border:none;padding:0;">Featured AI Podcast Episodes</h2>
        </div>
        <a class="cta-btn" href="podcasts.html">🎙️ Open Full Podcasts Hub →</a>
      </div>
      {podcasts_html}
    </section>

    <h2>📅 Daily Digest Editions</h2>
    <div class="grid">
      {"".join(day_cards_html)}
    </div>

    <footer class="footer">
      Powered by <strong>Google Gemini</strong> · Designed with low-glare reading palettes (Sage, Sepia, Night) &amp; optical book typography
    </footer>
  </div>
</body>
</html>"""


def _render_podcasts_page_html(
    shows_data: List[Dict[str, Any]],
    latest_date: str,
) -> str:
    """Render `docs/podcasts.html` featuring latest episode summaries from Generative AI 101, AI Optic, AI Today, and more."""
    show_sections: List[str] = []

    for idx, show in enumerate(shows_data, start=1):
        ep_cards: List[str] = []
        for ep in show.get("episodes", []):
            pub_text = f" · {ep['published']}" if ep.get("published") else ""
            ep_cards.append(
                f"""
                <article class="pod-card">
                  <div>
                    <div class="pod-header">
                      <div class="pod-show-info">
                        <div class="pod-artwork">🎙️</div>
                        <div>
                          <div class="pod-show-name">{show['name']}</div>
                          <div class="pod-sub">Host: {show['host']}{pub_text}</div>
                        </div>
                      </div>
                      <span class="pod-duration">🎧 {ep['duration']}</span>
                    </div>
                    <h4 class="pod-title"><a href="{ep['url']}" target="_blank" rel="noopener">{ep['title']}</a></h4>
                    <p class="pod-body">{ep['summary']}</p>
                  </div>
                  <div class="pod-footer">
                    <a class="pill-link" href="{show['apple_url']}" target="_blank" rel="noopener">🍏 Apple Podcasts ↗</a>
                    <a class="pod-play-btn" href="{ep['url']}" target="_blank" rel="noopener">▶ Listen Episode ↗</a>
                  </div>
                </article>
                """
            )

        show_sections.append(
            f"""
            <section class="section-panel podcast-panel" id="show-{idx}">
              <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;margin-bottom:10px;">
                <div>
                  <span class="hero-badge">🎙️ Show #{idx} · Host: {show['host']}</span>
                  <h2 style="margin:2px 0 6px;border:none;padding:0;">{show['name']}</h2>
                  <p style="margin:0;font-size:0.9rem;color:var(--text-secondary);font-family:var(--font-sans);"><strong>Focus:</strong> {show['focus']}</p>
                </div>
                <a class="cta-btn" href="{show['apple_url']}" target="_blank" rel="noopener">🍏 Subscribe on Apple Podcasts ↗</a>
              </div>
              <div class="pod-grid">
                {"".join(ep_cards)}
              </div>
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Generative AI Podcasts Hub — Latest Episode Summaries</title>
  {SHARED_CSS_AND_THEME_JS}
</head>
<body>
  <div id="progress-bar"></div>
  <div class="container">
    <nav class="top-nav">
      <a class="brand" href="index.html">
        <span class="brand-dot"></span>
        <span>← Back to GenAI Hub</span>
      </a>
      <div class="nav-actions">
        <a class="pill-link" href="index.html">All Editions</a>
        <a class="pill-link active" href="podcasts.html">🎙️ Podcasts Hub</a>
        <a class="pill-link" href="{latest_date}.html">Latest Digest ({latest_date})</a>
        {COMFORT_CONTROLS_HTML}
      </div>
    </nav>

    <section class="hero">
      <span class="hero-badge">🎧 Curated AI Audio Learning Hub</span>
      <h1>Generative AI Podcasts &amp; Episode Summaries</h1>
      <p style="color:var(--text-secondary);font-size:1.02rem;margin:0 0 16px;">
        Catch up on the latest episodes and key takeaways from <strong>Generative AI 101</strong>, <strong>AI Optic: Anthropic &amp; OpenAI News</strong>, <strong>AI Today Podcast</strong>, <strong>Latent Space</strong>, <strong>TWIML AI</strong>, and <strong>Practical AI</strong>.
      </p>
      <div style="display:flex;flex-wrap:wrap;gap:8px;font-family:var(--font-sans);">
        <a class="pill-link" href="#show-1">🎙️ Generative AI 101</a>
        <a class="pill-link" href="#show-2">🎙️ AI Optic (Anthropic &amp; OpenAI)</a>
        <a class="pill-link" href="#show-3">🎙️ AI Today Podcast</a>
        <a class="pill-link" href="#show-4">🎙️ Latent Space</a>
        <a class="pill-link" href="#show-5">🎙️ TWIML AI</a>
        <a class="pill-link" href="#show-6">🎙️ Practical AI</a>
      </div>
    </section>

    {"".join(show_sections)}

    <footer class="footer">
      Curated by <strong>Generative AI Learning &amp; News Agent</strong> · <a href="index.html">Back to Main Index</a>
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

    index_html = _render_index_portal_html(archive_map=archive_map)
    (target_docs / "index.html").write_text(index_html, encoding="utf-8")

    # Build dedicated Podcasts Hub page (`docs/podcasts.html`)
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
