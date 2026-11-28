from __future__ import annotations

import html
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
from urllib.parse import quote_plus, urlparse

import markdown

from genai_agent.collectors.podcasts import FEATURED_PODCAST_SHOWS, fetch_detailed_podcast_hub
from genai_agent.collectors.social_x import CURATED_FALLBACK_X_THREADS
from genai_agent.collectors.tech_talks import (
    CURATED_FALLBACK_TECH_TALKS,
    fetch_detailed_tech_talks_hub,
)
from genai_agent.guides import EVERGREEN_GUIDES

EDITORIAL_CSS_AND_JS = """
  <meta name="theme-color" id="meta-theme-color" content="#F6F4EF">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="format-detection" content="telephone=no">
  <link rel="alternate" type="application/rss+xml" title="The GenAI Briefing (jabi.io)" href="https://jabi.io/feed.xml">
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
    .briefing-takeaway {
      font-family: var(--font-serif);
      font-size: 0.96rem;
      color: var(--ink-secondary);
      margin: 0 0 10px;
      padding: 6px 12px;
      border-left: 2px solid var(--accent);
      background: var(--surface);
      line-height: 1.6;
      max-width: 66ch;
    }
    .briefing-takeaway strong {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--accent);
      margin-right: 4px;
    }
    .guide-list {
      display: flex;
      flex-direction: column;
    }
    .guide-card {
      padding: 20px 0;
      border-bottom: 1px solid var(--border);
    }
    .guide-card:last-child {
      border-bottom: none;
    }
    .guide-kicker {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--accent);
      margin-bottom: 6px;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }
    .guide-kicker span.muted {
      color: var(--ink-muted);
    }
    .guide-card h3 {
      font-family: var(--font-serif);
      font-size: 1.24rem;
      font-weight: 600;
      line-height: 1.34;
      margin: 0 0 8px;
      max-width: 62ch;
    }
    .guide-card h3 a {
      color: var(--ink);
      text-decoration: none;
    }
    .guide-card h3 a:hover {
      color: var(--accent);
      text-decoration: underline;
      text-underline-offset: 3px;
    }
    .guide-article {
      max-width: 66ch;
    }
    .guide-article h1 {
      font-family: var(--font-display);
      font-size: 2.3rem;
      font-weight: 400;
      line-height: 1.15;
      margin: 8px 0 12px;
      color: var(--ink);
    }
    .guide-subtitle {
      font-family: var(--font-serif);
      font-size: 1.12rem;
      color: var(--ink-secondary);
      line-height: 1.55;
      margin: 0 0 24px;
      padding-bottom: 18px;
      border-bottom: 1px solid var(--border);
    }
    .guide-article h2 {
      font-family: var(--font-serif);
      font-size: 1.4rem;
      font-weight: 600;
      line-height: 1.3;
      margin: 32px 0 12px;
      color: var(--ink);
    }
    .guide-article h3 {
      font-family: var(--font-sans);
      font-size: 1.02rem;
      font-weight: 600;
      line-height: 1.4;
      margin: 24px 0 10px;
      color: var(--ink);
    }
    .guide-article p, .guide-article li {
      font-family: var(--font-serif);
      font-size: 1.02rem;
      line-height: 1.72;
      color: var(--ink-secondary);
    }
    .guide-article p {
      margin: 0 0 16px;
    }
    .guide-article ul, .guide-article ol {
      margin: 0 0 18px;
      padding-left: 22px;
    }
    .guide-article li {
      margin-bottom: 8px;
    }
    .guide-article code {
      font-family: var(--font-mono);
      font-size: 0.85em;
      background: var(--surface-alt);
      padding: 1px 5px;
      border-radius: 3px;
    }
    .guide-article table {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      font-family: var(--font-sans);
      font-size: 0.88rem;
    }
    .guide-article th, .guide-article td {
      text-align: left;
      padding: 10px 12px;
      border-bottom: 1px solid var(--border);
      vertical-align: top;
    }
    .guide-article th {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--ink-muted);
      border-bottom: 1px solid var(--border-strong);
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
      max-width: 66ch;
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

    /* Free Daily Email Digest Subscribe Box */
    .subscribe-box {
      background: var(--surface);
      border: 1px solid var(--border);
      border-top: 2px solid var(--border-strong);
      border-left: 3px solid var(--accent);
      padding: 22px 24px;
      margin: 36px 0 28px;
    }
    .subscribe-kicker {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      color: var(--accent);
      margin-bottom: 6px;
    }
    .subscribe-box h3 {
      font-family: var(--font-serif);
      font-size: 1.24rem;
      font-weight: 600;
      margin: 0 0 6px;
      color: var(--ink);
    }
    .subscribe-copy {
      font-family: var(--font-serif);
      font-size: 0.95rem;
      color: var(--ink-secondary);
      margin: 0 0 14px;
      line-height: 1.6;
      max-width: 66ch;
    }
    .subscribe-form {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 10px;
    }
    .subscribe-input {
      flex: 1 1 260px;
      max-width: 380px;
      padding: 9px 12px;
      font-family: var(--font-sans);
      font-size: 16px;
      color: var(--ink);
      background: var(--bg);
      border: 1px solid var(--border);
      border-radius: 3px;
      outline: none;
    }
    .subscribe-input:focus {
      border-color: var(--accent);
    }
    .subscribe-btn {
      padding: 10px 16px;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--bg);
      background: var(--ink);
      border: 1px solid var(--ink);
      border-radius: 3px;
      cursor: pointer;
      touch-action: manipulation;
    }
    .subscribe-btn:hover {
      background: var(--accent);
      border-color: var(--accent);
    }
    .subscribe-meta {
      font-family: var(--font-mono);
      font-size: 0.71rem;
      color: var(--ink-muted);
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
    }
    .subscribe-meta a {
      color: var(--ink-secondary);
      text-decoration: underline;
      text-underline-offset: 3px;
    }
    .subscribe-status {
      font-family: var(--font-mono);
      font-size: 0.75rem;
      color: var(--accent);
      margin-top: 8px;
      display: none;
    }

    /* Non-intrusive Google AdSense Editorial Sponsorship Slot */
    .editorial-ad-slot {
      margin: 56px 0;
      clear: both;
      padding: 14px 18px;
      background: var(--surface);
      border: 1px solid var(--border);
      text-align: center;
    }
    .editorial-ad-label {
      font-family: var(--font-mono);
      font-size: 0.66rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--ink-muted);
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
      .subscribe-box {
        padding: 16px;
        margin: 24px 0 20px;
      }
      .subscribe-input {
        max-width: 100%;
        width: 100%;
      }
      .subscribe-btn {
        width: 100%;
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

    function handleSubscribe(event) {
      const form = event.target;
      const action = (form.getAttribute('action') || '').trim();
      const input = form.querySelector('input[type="email"]');
      const email = input ? input.value.trim() : '';
      if (!action || action === '#' || !email.includes('@')) {
        event.preventDefault();
        return false;
      }
      return true;
    }

    window.addEventListener('DOMContentLoaded', updateControls);
  </script>
"""


def _strip_emojis(text: str) -> str:
    """Remove decorative emoji prefixes from legacy markdown headings and badges."""
    return re.sub(
        r"[🚀⚡🧠📄🏢🛠️🔥🏆🎧🎯✨📅⬆️🎙️🍏📌🌐🎥📺▶️🎬]+\s*",
        "",
        text or "",
    ).strip()


def _harden_rendered_markdown_html(html_text: str) -> str:
    """Strip any raw script tags and enforce target=_blank rel='noopener noreferrer' on external links."""
    if not html_text:
        return ""
    cleaned = re.sub(r"(?is)<script\b[^>]*>.*?</script>", "", html_text)

    def _add_rel(match: re.Match) -> str:
        tag = match.group(0)
        href = match.group(1)
        if href.startswith("https://jabi.io"):
            return tag
        if 'rel="' not in tag and "rel='" not in tag:
            tag = tag[:-1] + ' target="_blank" rel="noopener noreferrer">'
        return tag

    return re.sub(r'<a\s+[^>]*href="(https?://[^"]+)"[^>]*>', _add_rel, cleaned)


_PROFANITY_RE = re.compile(r"\b(shit|fuck|damn|asshole|bitch|crap|wtf)\b", re.IGNORECASE)
_ARCHIVE_URL_RE = re.compile(r"https?://(?:www\.)?archive\.(?:ph|is|today)/\S*", re.IGNORECASE)


def _sanitize_title_profanity(text: str) -> str:
    """Mask explicit profanity in third-party headlines so rendered HTML and RSS remain publisher-safe."""
    if not text:
        return ""
    return _PROFANITY_RE.sub(lambda m: m.group(0)[0] + "***", text)
_LEGACY_X_BOILERPLATE_RES = (
    re.compile(r"^Technical thread from (?:@\S+|AI researchers on X) examining .+", re.IGNORECASE),
    re.compile(r"^Industry analysis and researcher commentary on X examining .+", re.IGNORECASE),
    re.compile(r"^Researcher and engineering discussion(?: on X)? examining .+", re.IGNORECASE),
    re.compile(r"^Technical discussion on X examining .+", re.IGNORECASE),
    re.compile(r"^Trending AI discussion on X covered by [^.]+\.?$", re.IGNORECASE),
)


def _clean_excerpt(text: str, max_chars: int = 300) -> str:
    """Clean raw scraper boilerplate, legacy filler, profanity, sponsor copy, and bare URLs."""
    if not text:
        return ""

    text = html.unescape(text).strip()
    text = re.sub(r"[\u200b\u2060\ufeff]", "", text)
    text = re.sub(r"^\*\*(?:Takeaway|Summary|What happened|What's being discussed|Why listen):\*\*\s*", "", text)
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
        flags=re.IGNORECASE,
    ).strip(" |")
    text = re.sub(r"^See also\b.*$", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(
        r"Viral X thread discussed on Hacker News \([^)]+\)\.\s*HN Thread:\s*https?://\S+",
        "",
        text,
    ).strip()
    text = re.sub(r"\s*HN Thread:\s*https?://\S+", "", text).strip()
    text = re.sub(
        r"^Active engineering discussion thread on \[Hacker News\]\([^)]+\)\.?$",
        "",
        text,
    ).strip()
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)
    text = re.sub(r"\*\*", "", text).strip()

    for pat in _LEGACY_X_BOILERPLATE_RES:
        if pat.match(text):
            return ""

    # Strip podcast sponsor/promo lead-ins and inline promo bullets
    text = re.sub(
        r"Show Links\s*(?:[•\-\*]\s*)?.*?(?=In this episode|Today we|We discuss|Join us|On this episode|$)",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    text = re.sub(
        r"Get the top 80\+ AI Models.*?(?=In this episode|Today we|We discuss|Join us|On this episode|$)",
        "",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    ).strip()
    text = re.sub(
        r"[•\-\*]?\s*[^•\n]*(?:aibox\.ai|skool\.com|aichatdaily\.com|\$8\.99)[^•\n]*",
        " ",
        text,
        flags=re.IGNORECASE,
    ).strip()

    if _PROFANITY_RE.search(text):
        return ""

    if re.match(r"^https?://\S+$", text, flags=re.IGNORECASE):
        return ""
    text = _ARCHIVE_URL_RE.sub("", text).strip()
    text = re.sub(r"\(?\s*https?://\S+\s*\)?", " ", text)
    text = re.sub(r"\(\s*\)", "", text)
    text = " ".join(text.split()).strip(" •-*|")
    if not text:
        return ""

    # Drop truncated stub fragments left after sponsor stripping (e.g. "In this episode, we explore the.")
    if len(text) < 42 and re.search(r"\b(?:the|a|an|of|to|in|for|and|with)\.$", text, flags=re.IGNORECASE):
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
            title = _sanitize_title_profanity(_strip_emojis(m.group(2)))
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
            elif "Tech Talk" in cat_raw or "Keynote" in cat_raw or "YouTube" in meta_line:
                category = "Tech Talk"
            else:
                category = cat_raw

            src_match = re.search(r"\(([^)]+)\)", meta_line)
            source = src_match.group(1) if src_match else _domain_of(url)

            date_match = re.search(r"\*([0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]{3},\s+[0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{4})", meta_line)
            pub_date = date_match.group(1) if date_match else ""

            summary_bullets: List[str] = []
            why_bullets: List[str] = []
            for b in bullets:
                why_m = re.match(r"^\*{0,2}Why it matters:\*{0,2}\s*(.+)$", b, flags=re.IGNORECASE)
                if why_m:
                    why_bullets.append(why_m.group(1).strip())
                else:
                    summary_bullets.append(b)

            combined_summary = _clean_excerpt(" ".join(summary_bullets), max_chars=340)
            why_it_matters = _clean_excerpt(" ".join(why_bullets), max_chars=300) if why_bullets else ""

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
                    "why_it_matters": why_it_matters,
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
    """Parse 2-line markdown bullets from X, Podcast, or Tech Talk sections into structured notes."""
    notes: List[Dict[str, str]] = []
    lines = [ln for ln in (section_md or "").splitlines() if ln.strip()]
    idx = 0
    while idx < len(lines):
        line = lines[idx].strip()
        if line.startswith("- **["):
            m = re.match(r"^-\s+\*\*\[(.+)\]\((https?://[^)]+)\)\*\*(.*)$", line)
            title = _sanitize_title_profanity(_strip_emojis(m.group(1))) if m else _sanitize_title_profanity(line)
            url = m.group(2).strip() if m else "#"
            tail = m.group(3) if m else ""

            desc = ""
            if idx + 1 < len(lines) and not lines[idx + 1].strip().startswith("- **["):
                desc = lines[idx + 1].strip().lstrip("- ").strip()
                idx += 1

            hn_m = re.search(r"https://news\.ycombinator\.com/item\?id=\d+", tail + " " + desc)
            hn_url = hn_m.group(0) if hn_m else ""

            pts_m = re.search(r"(\d[\d,]*)\s*(?:pts|views)", tail + " " + desc)
            pts = pts_m.group(0).strip() if pts_m else ""

            dur_m = re.search(r"🎧\s*([0-9hm:\s]+)", tail + " " + desc)
            dur = dur_m.group(1).strip() if dur_m else ""

            date_m = re.search(
                r"\*([0-9]{4}-[0-9]{2}-[0-9]{2}|[A-Za-z]{3},\s+[0-9]{2}\s+[A-Za-z]{3}\s+[0-9]{4})\*",
                tail,
            )
            pub_date = date_m.group(1).strip() if date_m else ""

            handle_m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url)
            if handle_m and kind == "x":
                kicker = f"@{handle_m.group(1)}"
            elif "smol.ai" in url and kind == "x":
                kicker = "AINews · X Recap"
            else:
                show_m = re.search(r"—\s*(?:\*\*|\*)([^*]+)(?:\*\*|\*)", tail)
                kicker = _strip_emojis(show_m.group(1)) if show_m else _domain_of(url)

            if kind == "podcast":
                meta = dur or pub_date
            elif kind == "tech_talk":
                meta = pub_date or pts or "YouTube"
            else:
                meta = pts or pub_date

            clean_desc = _clean_excerpt(desc, max_chars=280)
            notes.append(
                {
                    "title": title,
                    "url": url,
                    "kicker": kicker,
                    "meta": meta,
                    "hn_url": hn_url,
                    "summary": clean_desc,
                }
            )
        idx += 1
    return notes


def _default_tech_talk_notes(limit: int = 8) -> List[Dict[str, str]]:
    """Build curated fallback tech talk notes when rendering legacy digests that predate Section IV."""
    notes: List[Dict[str, str]] = []
    for talk in CURATED_FALLBACK_TECH_TALKS[:limit]:
        notes.append(
            {
                "title": _strip_emojis(talk["title"]),
                "url": talk["url"],
                "kicker": talk["source"],
                "meta": talk.get("published_at", "YouTube"),
                "hn_url": "",
                "summary": _clean_excerpt(talk.get("summary", ""), max_chars=280),
            }
        )
    return notes


def _default_x_thread_notes(limit: int = 4) -> List[Dict[str, str]]:
    """Build curated researcher thread notes on X when a digest has fewer than 3 X entries."""
    notes: List[Dict[str, str]] = []
    for item in CURATED_FALLBACK_X_THREADS[:limit]:
        url = item["url"]
        handle_m = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)", url)
        kicker = f"@{handle_m.group(1)}" if handle_m else item.get("source", "X.com")
        score = item.get("score")
        meta = f"{score} pts" if score else item.get("published_at", "X.com")
        notes.append(
            {
                "title": _strip_emojis(item["title"]),
                "url": url,
                "kicker": kicker,
                "meta": meta,
                "hn_url": "",
                "summary": _clean_excerpt(item.get("summary", ""), max_chars=280),
            }
        )
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
        <p class="masthead-sub">Curated research papers, frontier lab engineering, tech talks, researcher threads &amp; audio briefings.</p>
      </div>
      <nav class="masthead-nav">
        <div class="nav-links">
          <a href="index.html" class="{'active' if active_page == 'index' else ''}">Front Page</a>
          <a href="{latest_date}.html" class="{'active' if active_page == 'daily' else ''}">Latest Issue ({latest_date})</a>
          <a href="guides.html" class="{'active' if active_page == 'guides' else ''}">Guides</a>
          <a href="tech-talks.html" class="{'active' if active_page == 'tech_talks' else ''}">Tech Talks Index</a>
          <a href="podcasts.html" class="{'active' if active_page == 'podcasts' else ''}">Podcasts Index</a>
          <a href="index.html#archive">Archive</a>
          <a href="#subscribe">Subscribe</a>
        </div>
        <div style="font-family:var(--font-mono);font-size:0.72rem;color:var(--ink-muted);">
          JABI.IO · DAILY EDITION
        </div>
      </nav>
    </header>
    """


DEFAULT_ADSENSE_CLIENT_ID = "ca-pub-4585099070726775"
_ADSENSE_CLIENT_RE = re.compile(r"^(?:ca-)?pub-(\d{10,20})$")


def _normalize_adsense_client_id(raw: str = "") -> str:
    """Validate and normalize a Google AdSense publisher ID to `ca-pub-XXXXXXXXXXXXXXXX`."""
    env_val = os.getenv("GOOGLE_ADSENSE_CLIENT_ID")
    if raw:
        candidate = raw.strip()
    elif env_val is not None:
        candidate = env_val.strip() or DEFAULT_ADSENSE_CLIENT_ID
    else:
        candidate = DEFAULT_ADSENSE_CLIENT_ID
    m = _ADSENSE_CLIENT_RE.match(candidate)
    if not m:
        return ""
    return f"ca-pub-{m.group(1)}"


def _render_adsense_head_snippet() -> str:
    """Return Google AdSense account meta tag and async script when `GOOGLE_ADSENSE_CLIENT_ID` is configured."""
    client_id = _normalize_adsense_client_id()
    if not client_id:
        return ""
    safe_client = html.escape(client_id, quote=True)
    return (
        f'\n  <meta name="google-adsense-account" content="{safe_client}">\n'
        f'  <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={safe_client}" crossorigin="anonymous"></script>'
    )


_ADSENSE_SLOT_RE = re.compile(r"^\d{6,20}$")


def _render_editorial_ad_slot() -> str:
    """Render a single, clearly labeled responsive AdSense unit when both client and slot IDs are configured."""
    client_id = _normalize_adsense_client_id()
    raw_slot = os.getenv("GOOGLE_ADSENSE_SLOT_ID", "").strip()
    if not client_id or not _ADSENSE_SLOT_RE.match(raw_slot):
        return ""
    safe_client = html.escape(client_id, quote=True)
    safe_slot = html.escape(raw_slot, quote=True)
    return f"""
    <aside class="editorial-ad-slot" aria-label="Advertisement">
      <div class="editorial-ad-label">Sponsored · Advertisement</div>
      <ins class="adsbygoogle"
           style="display:block"
           data-ad-client="{safe_client}"
           data-ad-slot="{safe_slot}"
           data-ad-format="auto"
           data-full-width-responsive="true"></ins>
      <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
    </aside>
    """


DEFAULT_BEEHIIV_FORM_ID = "787aaa82-e683-49f6-9a3b-3016da1d9905"
DEFAULT_BEEHIIV_SUBSCRIBE_URL = "https://jabi.beehiiv.com/subscribe"


def _render_subscribe_box_html() -> str:
    """Render the newsletter subscribe box (custom form action via env var, or live Beehiiv Slim Inline embed)."""
    raw_action = os.getenv("NEWSLETTER_FORM_ACTION", "").strip()
    safe_action = _safe_http_url(raw_action) if raw_action else "#"
    if safe_action != "#":
        return f"""
    <section id="subscribe" class="subscribe-box" aria-label="Subscribe to the daily email digest">
      <div class="subscribe-kicker">DAILY EMAIL DIGEST · JABI.IO</div>
      <h3>Receive The GenAI Briefing by Email</h3>
      <p class="subscribe-copy">The daily Top 10 research papers, engineering posts, researcher threads and tech talks, one email per issue.</p>
      <form class="subscribe-form" action="{safe_action}" method="post" target="_blank" rel="noopener noreferrer" onsubmit="return handleSubscribe(event)">
        <input type="email" name="email" class="subscribe-input" placeholder="you@company.com" required aria-label="Email address">
        <button type="submit" class="subscribe-btn">Subscribe →</button>
      </form>
      <div class="subscribe-meta">
        <a href="feed.xml">RSS Feed ↗</a>
        <span>·</span>
        <a href="privacy.html">Privacy</a>
      </div>
    </section>
    """
    form_id = html.escape(os.getenv("BEEHIIV_FORM_ID", DEFAULT_BEEHIIV_FORM_ID).strip() or DEFAULT_BEEHIIV_FORM_ID)
    sub_url = _safe_http_url(os.getenv("BEEHIIV_SUBSCRIBE_URL", DEFAULT_BEEHIIV_SUBSCRIBE_URL).strip() or DEFAULT_BEEHIIV_SUBSCRIBE_URL)
    return f"""
    <section id="subscribe" class="subscribe-box" aria-label="Subscribe to The GenAI Briefing">
      <div class="subscribe-kicker">DAILY EMAIL DIGEST · JABI.IO</div>
      <h3>Receive The GenAI Briefing by Email</h3>
      <p class="subscribe-copy">The daily Top 10 research papers, frontier lab engineering posts, researcher threads, and tech talks—delivered every morning via Beehiiv. Free, zero spam, one-click unsubscribe.</p>
      <div class="beehiiv-embed-wrap" style="margin: 14px 0 10px;">
        <script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="{form_id}"></script>
      </div>
      <div class="subscribe-meta">
        <a href="{sub_url}" target="_blank" rel="noopener noreferrer">Open Subscribe Page ↗</a>
        <span>·</span>
        <a href="feed.xml">RSS Feed (feed.xml) ↗</a>
        <span>·</span>
        <a href="privacy.html">Privacy</a>
      </div>
    </section>
    """


def _render_rss_feed_xml(archive_map: Dict[str, str], site_url: str = "https://jabi.io") -> str:
    """Render an RSS 2.0 feed (`docs/feed.xml`) of recent daily issues for email-to-RSS and feed readers."""
    base = site_url.rstrip("/")
    sorted_dates = sorted(archive_map.keys(), reverse=True)
    items_xml: List[str] = []

    for d in sorted_dates[:15]:
        top_items = _parse_top10_items(archive_map[d])
        bullet_lines = [
            f"<li><a href=\"{_safe_http_url(it['url'])}\">{html.escape(it['title'])}</a> — {html.escape(it['summary'])}</li>"
            for it in top_items[:10]
        ]
        desc_html = f"<ul>{''.join(bullet_lines)}</ul>" if bullet_lines else "Daily Generative AI Technical Briefing."
        issue_url = f"{base}/{d}.html"
        items_xml.append(
            f"""    <item>
      <title>The GenAI Briefing — {html.escape(d)}</title>
      <link>{issue_url}</link>
      <guid isPermaLink="true">{issue_url}</guid>
      <pubDate>{html.escape(d)}T07:00:00+08:00</pubDate>
      <description>{html.escape(desc_html)}</description>
    </item>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The GenAI Briefing (jabi.io)</title>
    <link>{base}/</link>
    <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml" />
    <description>Curated daily Generative AI research papers, frontier lab engineering, researcher threads on X, audio podcasts, and YouTube tech talks.</description>
    <language>en-us</language>
{chr(10).join(items_xml)}
  </channel>
</rss>
"""


SITE_URL = "https://jabi.io"
DEFAULT_CONTACT_EMAIL = "editor@jabi.io"
GITHUB_ISSUES_URL = "https://github.com/shahsaifi/agentic-ai/issues"
_EMAIL_RE = re.compile(r"^[^@\s<>\"']+@[^@\s<>\"']+\.[^@\s<>\"']+$")


def _footer_trust_links() -> str:
    """Shared navigation and trust-page links rendered in every page footer."""
    return (
        '<a href="guides.html">Guides</a> · '
        '<a href="about.html">About</a> · '
        '<a href="faq.html">FAQ</a> · '
        '<a href="contact.html">Contact</a> · <a href="terms.html">Terms</a> · '
        '<a href="privacy.html">Privacy</a>'
    )


def _seo_head(
    page: str,
    description: str,
    canonical_page: str | None = None,
    noindex: bool = False,
) -> str:
    """Canonical URL, optional robots noindex, meta description and Open Graph tags."""
    target_page = canonical_page or page
    path = "" if target_page == "index.html" else target_page
    canonical = html.escape(f"{SITE_URL}/{path}", quote=True)
    desc = html.escape(description, quote=True)
    robots_line = '\n  <meta name="robots" content="noindex, follow">' if noindex else ""
    return (
        f'<meta name="description" content="{desc}">{robots_line}\n'
        f'  <link rel="canonical" href="{canonical}">\n'
        f'  <meta property="og:type" content="website">\n'
        f'  <meta property="og:site_name" content="The GenAI Briefing">\n'
        f'  <meta property="og:url" content="{canonical}">\n'
        f'  <meta property="og:description" content="{desc}">'
    )


def _detect_duplicate_digests(archive_map: Dict[str, str]) -> Dict[str, str]:
    """Detect duplicate historical digests by fingerprinting Top 10 URLs/titles; map duplicate_date -> canonical_date."""
    seen_fingerprints: Dict[Tuple[Tuple[str, str], ...], str] = {}
    duplicates: Dict[str, str] = {}
    for arch_date in sorted(archive_map.keys()):
        items = _parse_top10_items(archive_map[arch_date])
        if items:
            fp = tuple(
                (it["url"].strip().rstrip("/").lower(), it["title"].strip().lower())
                for it in items[:10]
            )
        else:
            fp = (("raw", " ".join(archive_map[arch_date].split())[:500]),)
        if fp in seen_fingerprints:
            duplicates[arch_date] = seen_fingerprints[fp]
        else:
            seen_fingerprints[fp] = arch_date
    return duplicates


def _render_robots_txt() -> str:
    """Allow all crawlers (explicitly including Google AdSense crawlers) and point to the sitemap."""
    return (
        "User-agent: Mediapartners-Google\n"
        "Allow: /\n\n"
        "User-agent: Google-Display-Ads-Bot\n"
        "Allow: /\n\n"
        "User-agent: *\n"
        "Allow: /\n\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )


def _render_sitemap_xml(
    archive_dates: List[str],
    latest_date: str,
    duplicate_dates: Set[str] | None = None,
) -> str:
    """Render `docs/sitemap.xml` with deduplicated content pages, evergreen guides, directories, and About/FAQ."""
    dup_set = duplicate_dates or set()
    entries: List[Tuple[str, str]] = [(f"{SITE_URL}/", latest_date)]
    for d in sorted(archive_dates, reverse=True):
        if d == latest_date or d in dup_set:
            continue
        entries.append((f"{SITE_URL}/{d}.html", d))
    entries.append((f"{SITE_URL}/guides.html", latest_date))
    for guide in EVERGREEN_GUIDES:
        entries.append((f"{SITE_URL}/{guide['slug']}.html", guide.get("updated_at") or latest_date))
    for page in ("tech-talks", "podcasts", "about", "faq"):
        entries.append((f"{SITE_URL}/{page}.html", latest_date))
    body = "\n".join(
        f"  <url><loc>{html.escape(loc)}</loc><lastmod>{html.escape(mod)}</lastmod></url>"
        for loc, mod in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n"
        "</urlset>\n"
    )


def _render_static_page_html(
    page_key: str,
    filename: str,
    title: str,
    description: str,
    kicker: str,
    body_html: str,
    latest_date: str,
    include_adsense: bool = True,
) -> str:
    """Shared layout for About / FAQ / Contact / Terms / Guides. AdSense head snippet is controlled via `include_adsense`."""
    adsense_snippet = _render_adsense_head_snippet() if include_adsense else ""
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{html.escape(title)}</title>
  {_seo_head(filename, description)}{adsense_snippet}
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page=page_key, latest_date=latest_date)}
    <div class="section-head">
      <h2>{html.escape(kicker)}</h2>
      <span>JABI.IO</span>
    </div>
    {body_html}
    {_render_subscribe_box_html()}
    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · {html.escape(kicker.upper())}</div>
      <div><a href="index.html">Front Page</a> · <a href="tech-talks.html">Tech Talks Index</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="{html.escape(latest_date)}.html">Latest Issue</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
    </footer>
  </div>
</body>
</html>"""


def _p(text: str) -> str:
    return f'<p class="briefing-summary">{text}</p>'


def _render_about_page_html(latest_date: str) -> str:
    """Render `docs/about.html` with >= 400 words of original publisher, editorial, and verification policy prose."""
    body = "\n".join(
        [
            '<div class="guide-article">',
            "<h2>Editorial Mission</h2>",
            _p(
                "<strong>The GenAI Briefing</strong> (<a href=\"https://jabi.io\">jabi.io</a>) is an independent daily "
                "technical publication built for software engineers, machine learning practitioners, researchers, and "
                "engineering leaders who build and operate generative AI systems in production. Every morning, we distill "
                "the highest-signal developments across peer-reviewed preprints, frontier lab engineering blogs, "
                "practitioner discussions, recorded keynotes, and audio interviews into a concise, scannable edition "
                "designed for deep technical reading rather than engagement bait."
            ),
            _p(
                "Modern generative AI moves across dozens of fragmented channels simultaneously: arXiv and Hugging Face "
                "Daily Papers publish hundreds of preprints each week, frontier laboratories release model weights and "
                "safety reports without a unified schedule, and critical implementation lessons surface first in Hacker "
                "News postmortems, researcher threads on X, or conference lectures. Our mission is to separate durable "
                "architectural advances—such as inference quantization, agent harness design, retrieval hygiene, and "
                "evaluation methodology—from recycled press releases and marketing hype."
            ),
            "<h2>Source Selection and Ranking Criteria</h2>",
            _p(
                "Each daily edition draws from a transparent set of primary technical sources: Hugging Face Daily Papers, "
                "arXiv (cs.CL and cs.AI), official engineering blogs from OpenAI, Anthropic, Google DeepMind, Google AI, "
                "and independent researchers such as Simon Willison and Lilian Weng, alongside high-signal engineering "
                "threads from Hacker News, curated researcher discussions on X, AI engineering podcasts, and technical "
                "talks from Stanford CS25, Google Cloud Tech, IBM Technology, LangChain, and The Pragmatic Engineer."
            ),
            _p(
                "Candidates are deduplicated against every previously published issue so recurring stories do not crowd "
                "out new work. The Top 10 Ranked Briefing intentionally balances research papers, practitioner engineering "
                "discussions, and lab releases, weighting both technical substance (clarity of empirical results, "
                "reproducibility, and architectural novelty) and verified community reach. Alongside daily issues, we "
                "publish original <a href=\"guides.html\">Evergreen Engineering Guides</a> that synthesize durable "
                "production patterns in agent harnesses, inference optimization, context engineering, evaluation harnesses, "
                "and cascaded model routing."
            ),
            "<h2>AI Assistance and Primary-Source Verification</h2>",
            _p(
                "The GenAI Briefing uses automated collection pipelines and AI-assisted synthesis to assemble, classify, "
                "and summarize large volumes of daily source material on a consistent morning schedule. Because automated "
                "summaries can occasionally compress nuance or omit caveats from a 30-page preprint, we enforce two strict "
                "editorial rules: first, every entry links directly to its primary source (paper, lab post, repository, "
                "or discussion thread) so readers can inspect the underlying evidence immediately; second, we never "
                "fabricate quotes, synthetic community comments, or unverified claims. Summaries are sanitized to strip "
                "promotional boilerplate, broken archive redirects, and low-signal scraper noise."
            ),
            "<h2>Corrections Policy</h2>",
            _p(
                "Accuracy matters more than speed. If an issue contains a misattributed claim, a broken primary-source "
                "link, a truncated technical summary, or a factual error, readers can report it directly through our "
                "<a href=\"contact.html\">Contact page</a> or public issue tracker. We review correction requests "
                "promptly and update affected archive pages directly when a substantive error is confirmed."
            ),
            "<h2>Advertising Independence</h2>",
            _p(
                "The GenAI Briefing is free to read and open via public RSS without paywalls or mandatory registration. "
                "To cover hosting and infrastructure costs, content pages may display clearly labeled advertisements "
                "served by Google AdSense. Advertising partners have zero influence over story selection, ranking order, "
                "guide topics, or editorial commentary. Utility and legal pages (Contact, Terms of Service, and Privacy "
                "Policy) are kept completely free of advertising scripts."
            ),
            "</div>",
        ]
    )
    return _render_static_page_html(
        "about",
        "about.html",
        "About & Editorial Policy — The GenAI Briefing (jabi.io)",
        "About The GenAI Briefing (jabi.io): editorial mission, source selection, AI-assistance disclosure, corrections policy, and advertising independence.",
        "About & Editorial Policy",
        body,
        latest_date,
        include_adsense=True,
    )


def _render_faq_page_html(latest_date: str) -> str:
    qa = [
        (
            "What is The GenAI Briefing?",
            'A free daily technical publication (<a href="about.html">read our full editorial policy</a>) that collects, '
            "synthesizes, and ranks generative AI research papers, frontier lab engineering posts, practitioner "
            "discussions, podcasts, and recorded talks, paired with original long-form engineering guides.",
        ),
        (
            "Who is it for?",
            "Software engineers, ML practitioners, researchers, and technical leaders who build or operate generative AI "
            "systems in production. It assumes technical familiarity and skips introductory explainers.",
        ),
        (
            "When is a new issue published?",
            "Every day at about 06:45 Singapore time (22:45 UTC). Each issue has its own permanent archive page, and "
            "past issues are indexed in the archive table on the front page.",
        ),
        (
            "What is the Daily Editorial Synthesis at the top of each issue?",
            "Above Section I, each issue includes an Executive Summary or Editorial Synthesis highlighting the dominant "
            "technical themes across that day's Top 10, the balance of research papers versus engineering discussions, "
            "the lead story, and the concrete engineering implication for production teams.",
        ),
        (
            "What are the Evergreen Engineering Guides?",
            'Our <a href="guides.html">Evergreen Engineering Guides</a> are original, in-depth technical references '
            "covering durable production topics—including agent harness engineering, LLM inference and quantization, "
            "context engineering beyond naive RAG, production evaluation harnesses, and cascaded model routing.",
        ),
        (
            "How do I read a Top 10 entry?",
            "Each entry shows a category tag (Research, Engineering, or Lab Release), the primary source, the date, and "
            "a concise summary. Below the summary are direct links to the original source, the Hacker News discussion "
            "when available, and a Reddit search link. Use the filter buttons above the list to focus on one category.",
        ),
        (
            "How are stories chosen?",
            "An automated pipeline gathers candidates from public primary sources, filters out items already featured in "
            "earlier issues, and ranks the remainder by technical substance and community reach while balancing research "
            "papers, engineering discussions, and lab releases.",
        ),
        (
            "Are the summaries AI-assisted, and how do you handle verification and corrections?",
            "Daily summaries are generated automatically from primary source material and may be AI-assisted. Every "
            "entry links directly to the original paper, blog post, or thread for primary-source verification. If you "
            'spot an error or broken link, report it via the <a href="contact.html">Contact page</a> and we will '
            'review and correct it. See our <a href="about.html">About &amp; Editorial Policy</a> for details.',
        ),
        (
            "Where can I find talks and podcasts?",
            'The <a href="tech-talks.html">Tech Talks Index</a> lists recent YouTube lectures and keynotes grouped by '
            'channel, and the <a href="podcasts.html">Podcasts Index</a> lists recent episodes of AI engineering shows. '
            "Both are linked in the navigation bar on every page.",
        ),
        (
            "How do I follow the briefing?",
            'Subscribe to the free daily email edition using the Beehiiv form at the bottom of any page (or directly at '
            '<a href="https://jabi.beehiiv.com/subscribe" target="_blank" rel="noopener noreferrer">jabi.beehiiv.com</a>), '
            'add the RSS feed at <a href="feed.xml">jabi.io/feed.xml</a> to any feed reader, or bookmark the front page.',
        ),
        (
            "Does the site show ads or track me?",
            "Content pages may display clearly labeled ads served by Google AdSense, which uses cookies. Details and "
            'opt-out links are in the <a href="privacy.html">Privacy Policy</a>. Utility pages (Contact, Terms, '
            "Privacy) carry no advertising scripts, and your theme and font-size choices stay in browser localStorage.",
        ),
        (
            "Is the content free to reuse?",
            "Original guides, editorial syntheses, and short summaries are provided for reading and discussion with "
            "attribution. Linked papers, articles, and videos belong to their respective authors. See the "
            '<a href="terms.html">Terms of Service</a> for details.',
        ),
    ]
    blocks: List[str] = []
    for q, a in qa:
        blocks.append(f'<h3 class="note-title">{html.escape(q)}</h3>\n{_p(a)}')
    body = "\n".join(blocks)
    return _render_static_page_html(
        "faq",
        "faq.html",
        "FAQ and Reading Guide — The GenAI Briefing (jabi.io)",
        "Frequently asked questions and a reading guide for The GenAI Briefing daily generative AI technical publication.",
        "FAQ and Reading Guide",
        body,
        latest_date,
        include_adsense=True,
    )


def _render_contact_page_html(latest_date: str) -> str:
    raw_email = os.getenv("CONTACT_EMAIL", "").strip()
    contact_email = raw_email if (raw_email and _EMAIL_RE.match(raw_email)) else DEFAULT_CONTACT_EMAIL
    safe_email = html.escape(contact_email, quote=True)
    safe_issues_url = _safe_http_url(GITHUB_ISSUES_URL)
    body = "\n".join(
        [
            _p(
                "To report a factual error, flag a broken link, suggest a primary technical source, or submit a privacy "
                "request, contact the editorial desk using either channel below. Please include the issue date and the "
                "entry URL when reporting a correction."
            ),
            _p(f'<strong>Editorial Email:</strong> <a href="mailto:{safe_email}">{safe_email}</a>'),
            _p(
                "<strong>Public Issue Tracker &amp; Source Suggestions:</strong> "
                f'<a href="{safe_issues_url}" target="_blank" rel="noopener noreferrer">github.com/shahsaifi/agentic-ai/issues ↗</a>'
            ),
            _p(
                "Publisher: The GenAI Briefing (jabi.io). Editorial corrections and source suggestions are reviewed "
                "within a few business days."
            ),
        ]
    )
    return _render_static_page_html(
        "contact",
        "contact.html",
        "Contact — The GenAI Briefing (jabi.io)",
        "How to contact The GenAI Briefing editorial desk for corrections, source suggestions, and privacy requests.",
        "Contact",
        body,
        latest_date,
        include_adsense=False,
    )


def _render_terms_page_html(latest_date: str) -> str:
    sections = [
        ("Use of the Site", "The GenAI Briefing (jabi.io) is provided for personal, informational reading. You may link to and quote short excerpts of the pages with attribution. You may not scrape the site in a way that degrades it for others."),
        ("No Warranty", "Content is provided as is. Summaries are generated automatically and may contain mistakes or omit context. Nothing here is professional, financial or legal advice. Verify important claims against the linked sources."),
        ("Third-Party Content and Links", "Headlines, excerpts and links point to material owned by others, including papers, articles, discussions, podcasts and videos. That material remains the property of its authors and is subject to their terms. We are not responsible for the content or availability of external sites."),
        ("Intellectual Property", "The layout, selection and original text of this site are the work of the publisher. Third-party names and trademarks belong to their owners and are used only to identify them."),
        ("Advertising", "Content pages may display advertisements served by Google AdSense and similar partners. Ads are labeled and do not influence which stories are selected. See the Privacy Policy for cookie and opt-out details."),
        ("Changes to These Terms", "These terms may be updated from time to time. The version on this page is the current one."),
        ("Contact", "Questions about these terms can be sent through the Contact page."),
    ]
    body = "\n".join(
        f'<h3 class="note-title">{html.escape(h)}</h3>\n{_p(html.escape(t))}' for h, t in sections
    )
    return _render_static_page_html(
        "terms",
        "terms.html",
        "Terms of Service — The GenAI Briefing (jabi.io)",
        "Terms of Service for The GenAI Briefing (jabi.io).",
        "Terms of Service",
        body,
        latest_date,
        include_adsense=False,
    )


def _render_privacy_page_html(latest_date: str, include_adsense: bool = False) -> str:
    """Render `docs/privacy.html` with Privacy, Email, and Google AdSense disclosures. AdSense scripts are omitted by default."""
    adsense_snippet = _render_adsense_head_snippet() if include_adsense else ""
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>The GenAI Briefing (jabi.io) — Privacy Policy</title>
  {_seo_head('privacy.html', 'Privacy policy for jabi.io: email, cookies, Google AdSense and reader data.')}{adsense_snippet}
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="privacy", latest_date=latest_date)}

    <div class="section-head">
      <h2>I. About The GenAI Briefing (jabi.io)</h2>
      <span>EDITORIAL MISSION</span>
    </div>
    <p class="briefing-summary">
      <strong>The GenAI Briefing</strong> (<a href="https://jabi.io">jabi.io</a>) is an independent daily technical publication curating high-signal Generative AI research papers, frontier AI lab engineering posts, practitioner discussions, AI engineering podcasts, and YouTube technical keynotes. See our <a href="about.html">About &amp; Editorial Policy</a> page for details.
    </p>

    <div class="section-head">
      <h2>II. RSS Feed, Email Digest &amp; Reader Privacy</h2>
      <span>ZERO-SPAM GUARANTEE</span>
    </div>
    <p class="briefing-summary">
      Readers can subscribe to the daily email edition via <a href="https://jabi.beehiiv.com/subscribe" target="_blank" rel="noopener noreferrer">Beehiiv</a> or follow our public RSS feed (<a href="feed.xml"><code>https://jabi.io/feed.xml</code></a>). Email addresses submitted through the subscribe form are processed by Beehiiv solely to deliver The GenAI Briefing; they are never sold and include one-click unsubscribe in every issue. Reading preferences (such as Paper/Sepia/Ink theme palette and font size) are stored locally in your browser via <code>localStorage</code>.
    </p>

    <div class="section-head">
      <h2>III. Advertising &amp; Google AdSense Disclosure</h2>
      <span>COOKIE &amp; DART POLICY</span>
    </div>
    <p class="briefing-summary">
      To keep The GenAI Briefing free for engineers and researchers worldwide, content pages on <strong>jabi.io</strong> may display clearly labeled advertisements served by Google AdSense and third-party advertising partners.
    </p>
    <p class="briefing-summary">
      Third-party vendors, including Google, use cookies (such as the Google DART cookie) to serve ads based on a user&#x27;s prior visits to <strong>jabi.io</strong> or other websites on the internet. Google&#x27;s use of advertising cookies enables it and its partners to serve ads to users based on their visit to this site and/or other sites on the internet. Users may opt out of personalized advertising at any time by visiting <a href="https://adssettings.google.com" target="_blank" rel="noopener noreferrer">Google Ads Settings</a> or <a href="https://www.aboutads.info/choices/" target="_blank" rel="noopener noreferrer">aboutads.info</a>.
    </p>

    <div class="section-head">
      <h2>IV. Contact &amp; Editorial Corrections</h2>
      <span>PUBLISHER DESK</span>
    </div>
    <p class="briefing-summary">
      For editorial inquiries, paper submissions, or privacy requests, use the <a href="contact.html">Contact page</a>. See also our <a href="terms.html">Terms of Service</a>.
    </p>

    {_render_subscribe_box_html()}

    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · PRIVACY POLICY</div>
      <div><a href="index.html">Front Page</a> · <a href="tech-talks.html">Tech Talks Index</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
    </footer>
  </div>
</body>
</html>"""


def _render_guides_index_html(latest_date: str) -> str:
    """Render `docs/guides.html` listing all original Evergreen Engineering Guides."""
    cards: List[str] = []
    for idx, g in enumerate(EVERGREEN_GUIDES, start=1):
        word_count = len(g["body_markdown"].split())
        cards.append(
            f"""
            <article class="guide-card">
              <div class="guide-kicker">
                <span>{idx:02d} · {html.escape(g['kicker'])}</span>
                <span class="muted">· {html.escape(g['reading_time'])} ({word_count:,} words)</span>
                <span class="muted">· Updated {html.escape(g['updated_at'])}</span>
              </div>
              <h3><a href="{html.escape(g['slug'])}.html">{html.escape(g['title'])}</a></h3>
              <p class="briefing-summary">{html.escape(g['subtitle'])}</p>
              <div class="briefing-actions">
                <a href="{html.escape(g['slug'])}.html">Read Full Guide →</a>
              </div>
            </article>
            """
        )

    body = (
        '<div class="editorial-callout">'
        '<h3>Original Technical Deep Dives</h3>'
        '<p>Long-form engineering references written for practitioners building production LLM systems: '
        'architectural trade-offs, failure modes, and operational checklists that stay relevant beyond any single news cycle.</p>'
        '</div>'
        f'<div class="guide-list">{"".join(cards)}</div>'
    )
    return _render_static_page_html(
        "guides",
        "guides.html",
        "Evergreen Engineering Guides — The GenAI Briefing (jabi.io)",
        "Original Generative AI engineering guides on agent harnesses, LLM inference and quantization, context engineering, production evaluations, and cascaded model routing.",
        "Evergreen Engineering Guides",
        body,
        latest_date,
        include_adsense=True,
    )


def _render_guide_article_html(guide: Dict[str, str], latest_date: str) -> str:
    """Render an individual evergreen guide article page (`docs/{slug}.html`)."""
    slug = guide["slug"]
    filename = f"{slug}.html"
    rendered_body = _harden_rendered_markdown_html(
        markdown.markdown(
            guide["body_markdown"],
            extensions=["extra", "tables", "sane_lists"],
        )
    )
    word_count = len(guide["body_markdown"].split())

    related_items: List[str] = []
    for other in EVERGREEN_GUIDES:
        if other["slug"] == slug:
            continue
        related_items.append(
            f'<li><a href="{html.escape(other["slug"])}.html" style="color:var(--ink);text-decoration:underline;text-underline-offset:3px;">'
            f'{html.escape(other["title"])}</a> '
            f'<span style="font-family:var(--font-mono);font-size:0.72rem;color:var(--ink-muted);">({html.escape(other["kicker"])})</span></li>'
        )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>{html.escape(guide['title'])} — The GenAI Briefing (jabi.io)</title>
  {_seo_head(filename, guide['description'])}{_render_adsense_head_snippet()}
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="guides", latest_date=latest_date)}
    <div style="font-family:var(--font-mono);font-size:0.74rem;color:var(--ink-muted);margin-bottom:16px;">
      <a href="guides.html" style="color:var(--accent);text-decoration:none;">← ALL ENGINEERING GUIDES</a>
      <span> · {html.escape(guide['kicker'])} · {html.escape(guide['reading_time'])} · {word_count:,} WORDS · UPDATED {html.escape(guide['updated_at'])}</span>
    </div>
    <article class="guide-article">
      <h1>{html.escape(guide['title'])}</h1>
      <p class="guide-subtitle">{html.escape(guide['subtitle'])}</p>
      {rendered_body}
    </article>

    {_render_editorial_ad_slot()}

    <section aria-label="Related Engineering Guides">
      <div class="section-head">
        <h2>Related Engineering Guides</h2>
        <span><a href="guides.html" style="color:var(--accent);text-decoration:none;">ALL 5 GUIDES →</a></span>
      </div>
      <ul style="list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:10px;font-family:var(--font-serif);font-size:0.98rem;">
        {"".join(related_items)}
      </ul>
    </section>

    {_render_subscribe_box_html()}

    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · ENGINEERING GUIDES</div>
      <div><a href="index.html">Front Page</a> · <a href="tech-talks.html">Tech Talks Index</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="{html.escape(latest_date)}.html">Latest Issue</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
    </footer>
  </div>
</body>
</html>"""


_REDDIT_SEARCH_STOPWORDS = {
    "the", "a", "an", "of", "for", "in", "on", "to", "and", "or", "with", "via",
    "towards", "from", "its", "is", "are", "how", "what", "why", "new", "latest",
    "using", "into", "over", "more", "most", "can", "will", "not", "this", "that",
}


def _build_reddit_search_url(title: str) -> str:
    """Return a clean Google/Reddit search link for a briefing title without synthetic quotes or dead thread URLs."""
    clean = re.sub(r"[^A-Za-z0-9\-\s]", " ", title or "")
    words = [
        w
        for w in clean.split()
        if len(w) > 2 and w.lower() not in _REDDIT_SEARCH_STOPWORDS and not _PROFANITY_RE.match(w)
    ]
    query = " ".join(words[:5]) or "AI"
    return (
        "https://www.google.com/search?q=site:reddit.com+"
        "%28r%2FLocalLLaMA+OR+r%2FMachineLearning+OR+r%2FClaudeAI+OR+r%2FOpenAI+OR+r%2Fsingularity%29+"
        f"{quote_plus(query)}"
    )


_CACHED_URL_SUMMARIES: Dict[str, str] = {
    "https://github.com/anthropics/claude-code/issues/107757": (
        "Bug report detailing how Claude Code exposed a user's email address in outbound User-Agent HTTP headers "
        "during automated web searches."
    ),
    "https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-carbon/": (
        "Gemini 4 Carbon is Google's frontier model targeting cybersecurity, coding, and long-horizon reasoning capabilities."
    ),
    "https://8rank.ai/game/apple-intelligence-personal-knowledge-graph": (
        "Technical investigation of macOS background daemons that construct a local personal knowledge graph of "
        "contacts, communications, locations, and activity patterns."
    ),
    "https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-4-argon/": (
        "Announcing Gemini 4 Argon, Google's frontier model for real-world coding, enterprise knowledge work, "
        "and cyber defense."
    ),
    "https://caleb.software/posts/claude-to-pi.html": (
        "Practitioner comparison of migrating daily terminal coding workflows from Claude Code to Pi."
    ),
    "https://www.thestateofai.com/news/goldman-sachs-claude-code-traders-bankers": (
        "Report on Goldman Sachs deploying Claude Code across software engineering, trading, and investment banking teams."
    ),
    "https://apiiro.com/blog/coding-agents-leaking-secrets-github-dont-ask-again": (
        "Security analysis of how autonomous coding agents and permissive auto-approve settings can leak secrets "
        "into source repositories and CI pipelines."
    ),
    "https://antigravity.google/blog/gemini-4-hydrogen-in-google-antigravity/": (
        "Google Antigravity integrates Gemini 4 Hydrogen and multi-agent Orchestrator workflows for parallel "
        "codebase exploration, sub-agent delegation, and low-latency verification."
    ),
    "https://status.claude.com/incidents/nn11wk485zfn": (
        "Incident report detailing elevated API error rates across claude.ai, Claude Code, and platform.claude.com "
        "alongside cluster traffic rebalancing and mitigation steps."
    ),
    "https://github.com/hyperionaidev/smolmaxxing/": (
        "Open-source engineering toolkit and quantization recipes for running compact Large Language Models "
        "with minimal memory footprint on constrained and legacy edge hardware."
    ),
    "https://alignment.openai.com/misalignment-reports/covert-underperformance-on-safety-research-tasks/": (
        "Alignment evaluation report analyzing how frontier reasoning models can recognize safety-testing contexts "
        "and selectively underperform on capability elicitation benchmarks."
    ),
    "https://blog.google/innovation-and-ai/models-and-research/gemini-models/introducing-gemini-4-hydrogen/": (
        "Introducing Gemini 4 Hydrogen, a high-efficiency frontier model engineered for low-latency agentic loops "
        "and high-throughput coding workflows."
    ),
    "https://www.cbsnews.com/news/united-airlines-bans-ai-agents-booking-flights/": (
        "United Airlines updates its digital terms of service to restrict automated third-party AI booking agents "
        "from scraping inventory or executing autonomous ticket purchases."
    ),
}


def _safe_http_url(url: str) -> str:
    """Ensure a URL uses http/https scheme and escape it for safe HTML attribute rendering."""
    raw = (url or "").strip()
    if not raw:
        return "#"
    try:
        parsed = urlparse(raw)
        if parsed.scheme not in ("http", "https"):
            return "#"
        return html.escape(raw, quote=True)
    except Exception:
        return "#"


def _format_inline_math(text: str) -> str:
    """Escape HTML entities and convert raw inline LaTeX variables like `$L$` into clean typographic `<var>L</var>` tags."""
    if not text:
        return ""
    escaped = html.escape(text)
    return re.sub(r"\$([A-Za-z0-9_^{}\-]+)\$", r"<var>\1</var>", escaped)


def _enrich_missing_summary(title: str, url: str, hn_url: str, allow_network: bool = True) -> str:
    """Fetch a clean 1-2 sentence summary from article metadata or HN discussion when a story has no summary."""
    cache_key = url or hn_url or title
    if cache_key in _CACHED_URL_SUMMARIES:
        return _clean_excerpt(_CACHED_URL_SUMMARIES[cache_key], max_chars=280)
    if not allow_network:
        return ""

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
                            cand = _clean_excerpt(_html.unescape(m.group(1)).strip(), max_chars=280)
                            if len(cand) > 45:
                                extracted = cand
                                break
                    if not extracted:
                        for pm in re.finditer(r"<p[^>]*>(.*?)</p>", head, flags=re.IGNORECASE | re.DOTALL):
                            txt = re.sub(r"<[^>]+>", " ", pm.group(1))
                            txt = _clean_excerpt(" ".join(_html.unescape(txt).split()), max_chars=280)
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
                            clean_c = _clean_excerpt(" ".join(clean_c.split()), max_chars=260)
                            if len(clean_c) > 60:
                                extracted = f"Community note: {clean_c}"
                                break
    except Exception:
        pass

    final_summary = _clean_excerpt(extracted, max_chars=280) if extracted else ""
    _CACHED_URL_SUMMARIES[cache_key] = final_summary
    return final_summary


def _render_top10_ledger_html(items: List[Dict[str, str]], allow_network: bool = True) -> str:
    rows: List[str] = []
    cat_counts: Dict[str, int] = {}
    for it in items:
        cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1

    filter_pills = [
        f'<button class="filter-pill active" data-filter-pill="all" onclick="filterBriefing(\'all\')">All ({len(items)})</button>'
    ]
    for cat_name in ("Research", "Engineering", "Lab Release", "Tech Talk"):
        if cat_counts.get(cat_name):
            filter_pills.append(
                f'<button class="filter-pill" data-filter-pill="{cat_name}" onclick="filterBriefing(\'{cat_name}\')">{cat_name} ({cat_counts[cat_name]})</button>'
            )
    filter_bar_html = f'<div class="filter-bar">{"".join(filter_pills)}</div>'

    for it in items:
        # Tier 2: Substantive summary (auto-enriched if empty) + formatted inline math
        raw_summary = it["summary"] or _enrich_missing_summary(
            it["title"], it["url"], it["hn_url"], allow_network=allow_network
        )
        formatted_summary = _format_inline_math(raw_summary)
        summary_html = f'<p class="briefing-summary">{formatted_summary}</p>' if formatted_summary else ""

        why_text = it.get("why_it_matters") or ""
        why_html = (
            f'<p class="briefing-takeaway"><strong>Why it matters:</strong> {_format_inline_math(why_text)}</p>'
            if why_text
            else ""
        )

        reddit_search_url = _build_reddit_search_url(it["title"])
        safe_url = _safe_http_url(it["url"])
        safe_hn_url = _safe_http_url(it["hn_url"]) if it["hn_url"] else ""
        safe_reddit_search_url = _safe_http_url(reddit_search_url)
        safe_title = html.escape(it["title"])
        safe_cat = html.escape(it["category"])
        safe_src = html.escape(it["source"])
        safe_date = html.escape(it["date"])
        safe_domain = html.escape(it["domain"])

        # Tier 1: Clean, uncluttered kicker above the headline
        kicker_bits = [f'<span class="briefing-tag">{safe_cat}</span>', f'<span>{safe_src}</span>']
        if safe_date:
            kicker_bits.append(f'<span>{safe_date}</span>')

        # Tier 3: Dedicated Action & Discussion Bar below the summary
        action_links: List[str] = []
        source_label = f'Read Source ({safe_domain}) ↗' if safe_domain else "Read Source ↗"
        action_links.append(f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{source_label}</a>')

        if it["points"]:
            if safe_hn_url and it["hn_url"] != it["url"]:
                action_links.append(
                    f'<a href="{safe_hn_url}" target="_blank" rel="noopener noreferrer">HN Discussion ({html.escape(it["points"])} pts) ↗</a>'
                )
            else:
                action_links.append(f'<span>{html.escape(it["points"])} pts</span>')
        elif safe_hn_url and it["hn_url"] != it["url"]:
            action_links.append(f'<a href="{safe_hn_url}" target="_blank" rel="noopener noreferrer">HN Discussion ↗</a>')

        action_links.append(
            f'<a href="{safe_reddit_search_url}" target="_blank" rel="noopener noreferrer">Find on Reddit ↗</a>'
        )

        rows.append(
            f"""
            <article class="briefing-item" data-category="{safe_cat}">
              <div class="briefing-num">{html.escape(it["rank"])}</div>
              <div class="briefing-content">
                <div class="briefing-meta">{'<span>·</span>'.join(kicker_bits)}</div>
                <h3><a href="{safe_url}" target="_blank" rel="noopener noreferrer">{safe_title}</a></h3>
                {summary_html}
                {why_html}
                <div class="briefing-actions">{"".join(action_links)}</div>
              </div>
            </article>
            """
        )
    return f'{filter_bar_html}<div class="briefing-list">{"".join(rows)}</div>'


def _render_notes_column_html(
    notes: List[Dict[str, str]],
    action_label: str,
    empty_msg: str = "No entries recorded for this issue.",
) -> str:
    if not notes:
        return f'<p style="color:var(--ink-muted);font-size:0.9rem;">{html.escape(empty_msg)}</p>'
    blocks: List[str] = []
    for n in notes:
        safe_url = _safe_http_url(n["url"])
        safe_hn_url = _safe_http_url(n["hn_url"]) if n["hn_url"] else ""
        links = [f'<a href="{safe_url}" target="_blank" rel="noopener noreferrer">{html.escape(action_label)} ↗</a>']
        if safe_hn_url and n["hn_url"] != n["url"]:
            links.append(f'<a href="{safe_hn_url}" target="_blank" rel="noopener noreferrer">HN Thread ↗</a>')
        body_html = f'<p class="note-body">{html.escape(n["summary"])}</p>' if n["summary"] else ""
        blocks.append(
            f"""
            <article class="note-item">
              <div class="note-kicker">
                <strong>{html.escape(n["kicker"])}</strong>
                <span>{html.escape(n["meta"])}</span>
              </div>
              <h4 class="note-title"><a href="{safe_url}" target="_blank" rel="noopener noreferrer">{html.escape(n["title"])}</a></h4>
              {body_html}
              <div class="note-links">{"".join(links)}</div>
            </article>
            """
        )
    return f'<div class="note-list">{"".join(blocks)}</div>'


def _render_bullet_notes_html(
    section_md: str,
    kind: str = "tech_talk",
    empty_msg: str = "No entries recorded for this issue.",
    limit: int = 8,
) -> str:
    """Parse a bullet section markdown block and render it as editorial note cards."""
    notes = _parse_bullet_notes(section_md, kind=kind)
    if kind == "tech_talk":
        if not notes:
            notes = _default_tech_talk_notes(limit=limit)
        elif len(notes) < limit:
            seen_urls = {n["url"].strip().rstrip("/").lower() for n in notes}
            for fb_note in _default_tech_talk_notes(limit=limit):
                norm = fb_note["url"].strip().rstrip("/").lower()
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    notes.append(fb_note)
                if len(notes) >= limit:
                    break
        notes = notes[:limit]
    elif kind == "x":
        if len(notes) < 3:
            seen_urls = {n["url"].strip().rstrip("/").lower() for n in notes}
            for fb_note in _default_x_thread_notes(limit=max(limit, 4)):
                norm = fb_note["url"].strip().rstrip("/").lower()
                if norm not in seen_urls:
                    seen_urls.add(norm)
                    notes.append(fb_note)
                if len(notes) >= limit:
                    break
        notes = notes[:limit]
    action_map = {
        "x": "Read Thread on X",
        "podcast": "Listen Episode",
        "tech_talk": "Watch on YouTube",
    }
    action_label = action_map.get(kind, "Open Link")
    return _render_notes_column_html(notes, action_label=action_label, empty_msg=empty_msg)


_EDITORIAL_THEME_CLUSTERS: List[Tuple[str, Tuple[str, ...], str]] = [
    (
        "agentic harnesses and tool execution",
        ("agent", "harness", "computer-using", "mcp", "tool", "orchestrator", "sandbox", "coding", "claude code"),
        "Teams shipping autonomous workflows should isolate tool execution in ephemeral sandboxes and gate completion on deterministic tests rather than model self-assessment.",
    ),
    (
        "long-context architecture and inference efficiency",
        ("linear attention", "deltanet", "kv-cache", "quantiz", "inference", "distill", "speculative", "recurrent", "memory", "latency"),
        "Inference bottlenecks are shifting from raw FLOPs to state stability, memory bandwidth, and KV-cache economics—making prefix caching and task-calibrated quantization essential.",
    ),
    (
        "multimodal, video, and document intelligence",
        ("video", "vision", "document", "multimodal", "image", "3d", "spatial", "world model", "page"),
        "Production multimodal pipelines benefit from structural conditioning (cross-page context or 3D proxies) rather than encoding frames or pages in isolation.",
    ),
    (
        "evaluation benchmarks and reasoning reliability",
        ("benchmark", "eval", "reasoning", "math", "proof", "code golf", "arc-agi", "arena", "safety", "alignment"),
        "Public leaderboard gains require verification against private, execution-based regression suites before promoting a checkpoint into production.",
    ),
    (
        "frontier model releases and developer ecosystems",
        ("gemini", "gpt-", "claude", "qwen", "llama", "deepseek", "self-hosting", "open-weight"),
        "Evaluate new frontier and open-weight releases along the accuracy-cost Pareto curve using cascaded routing so routine traffic stays on fast, low-cost tiers.",
    ),
]


def _build_editorial_synthesis_html(
    top10_items: List[Dict[str, str]],
    current_date: str,
    x_count: int = 0,
    pod_count: int = 0,
    talk_count: int = 0,
) -> str:
    """Build a data-grounded Daily Editorial Synthesis callout when an issue lacks an explicit Executive Summary."""
    if not top10_items:
        return ""

    cat_counts: Dict[str, int] = {}
    for it in top10_items:
        cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1

    cat_bits = [f"{count} {cat}" for cat, count in sorted(cat_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    mix_text = ", ".join(cat_bits)

    corpus = " ".join(f"{it['title']} {it['summary']}" for it in top10_items).lower()
    matched_themes: List[Tuple[int, str, str]] = []
    for label, keywords, implication in _EDITORIAL_THEME_CLUSTERS:
        hits = sum(1 for kw in keywords if kw in corpus)
        if hits > 0:
            matched_themes.append((hits, label, implication))
    matched_themes.sort(key=lambda x: x[0], reverse=True)

    lead = top10_items[0]
    highest_pts_item = None
    best_pts = -1
    for it in top10_items:
        pts_raw = (it.get("points") or "").replace(",", "")
        if pts_raw.isdigit() and int(pts_raw) > best_pts:
            best_pts = int(pts_raw)
            highest_pts_item = it

    lead_link = f'<a href="{_safe_http_url(lead["url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--ink);text-decoration:underline;text-underline-offset:3px;">{html.escape(lead["title"])}</a>'

    theme_labels = [t[1] for t in matched_themes[:2]]
    if len(theme_labels) == 2:
        theme_phrase = f"{theme_labels[0]} and {theme_labels[1]}"
    elif len(theme_labels) == 1:
        theme_phrase = theme_labels[0]
    else:
        theme_phrase = "frontier model engineering and applied ML systems"

    implication_text = (
        matched_themes[0][2]
        if matched_themes
        else "Verify benchmark claims against primary sources and task-specific regression harnesses before changing production model routing."
    )

    bullets = [
        (
            f"<strong>Issue Focus ({html.escape(current_date)}):</strong> Today&#x27;s Top {len(top10_items)} "
            f"({html.escape(mix_text)}) centers on {html.escape(theme_phrase)}, led by {lead_link} "
            f"({html.escape(lead['source'])})."
        )
    ]

    if highest_pts_item and highest_pts_item["url"] != lead["url"] and best_pts > 0:
        hp_link = f'<a href="{_safe_http_url(highest_pts_item["url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--ink);text-decoration:underline;text-underline-offset:3px;">{html.escape(highest_pts_item["title"])}</a>'
        bullets.append(
            f"<strong>Highest Community Signal:</strong> {hp_link} drew {best_pts:,} points on "
            f"{html.escape(highest_pts_item['source'])}, alongside {x_count} curated X threads, "
            f"{pod_count} audio briefings, and {talk_count} recorded technical talks."
        )
    else:
        bullets.append(
            f"<strong>Cross-Channel Coverage:</strong> Complementing the ranked briefing are {x_count} researcher "
            f"threads on X, {pod_count} AI engineering podcast episodes, and {talk_count} recorded technical talks."
        )

    bullets.append(f"<strong>Engineering Implication:</strong> {html.escape(implication_text)}")

    li_html = "".join(f"<li>{b}</li>" for b in bullets)
    return (
        f'<div class="editorial-callout" aria-label="Daily Editorial Synthesis">'
        f"<h3>Daily Editorial Synthesis — {html.escape(current_date)}</h3>"
        f'<ul style="max-width:66ch;padding-left:18px;">{li_html}</ul>'
        f"</div>"
    )


def _render_daily_digest_html(
    markdown_content: str,
    title: str,
    current_date: str,
    archive_dates: List[str],
    canonical_date: str | None = None,
    allow_network: bool = True,
) -> str:
    """Render an individual daily briefing page (`YYYY-MM-DD.html`) in clean editorial style."""
    latest_date = sorted(archive_dates, reverse=True)[0] if archive_dates else current_date
    top10_items = _parse_top10_items(markdown_content)
    x_md = _extract_section_markdown(markdown_content, "X") or _extract_section_markdown(markdown_content, "Twitter")
    pod_md = _extract_section_markdown(markdown_content, "Podcast") or _extract_section_markdown(markdown_content, "Audio")
    talks_md = (
        _extract_section_markdown(markdown_content, "Tech Talk")
        or _extract_section_markdown(markdown_content, "Keynote")
        or _extract_section_markdown(markdown_content, "YouTube")
    )
    tldr_md = _extract_section_markdown(markdown_content, "TL;DR") or _extract_section_markdown(markdown_content, "Executive Summary")
    concept_md = _extract_section_markdown(markdown_content, "Concept") or _extract_section_markdown(markdown_content, "Deep-Dive")

    x_notes = _parse_bullet_notes(x_md, kind="x")
    pod_notes = _parse_bullet_notes(pod_md, kind="podcast")
    talk_notes = _parse_bullet_notes(talks_md, kind="tech_talk")

    if tldr_md:
        rendered_tldr = _harden_rendered_markdown_html(
            markdown.markdown(_strip_emojis(tldr_md), extensions=["extra", "sane_lists"])
        )
        tldr_html = f'<div class="editorial-callout"><h3>Executive Summary</h3>{rendered_tldr}</div>'
    else:
        tldr_html = _build_editorial_synthesis_html(
            top10_items=top10_items,
            current_date=current_date,
            x_count=max(len(x_notes), 3),
            pod_count=len(pod_notes),
            talk_count=max(len(talk_notes), 8),
        )

    concept_html = ""
    if concept_md:
        rendered_concept = _harden_rendered_markdown_html(
            markdown.markdown(_strip_emojis(concept_md), extensions=["extra", "sane_lists"])
        )
        concept_html = f'<div class="editorial-callout"><h3>Technical Deep-Dive</h3>{rendered_concept}</div>'

    top10_html = _render_top10_ledger_html(top10_items, allow_network=allow_network)
    x_html = _render_bullet_notes_html(x_md, kind="x", limit=4)
    pod_html = _render_notes_column_html(pod_notes, "Listen Episode")
    talks_html = _render_bullet_notes_html(talks_md, kind="tech_talk")

    date_links = " · ".join(
        f'<a href="{d}.html" style="font-weight:{"700" if d == current_date else "400"};color:var(--ink);">{d}</a>'
        for d in sorted(archive_dates, reverse=True)
    )

    is_duplicate = bool(canonical_date and canonical_date != current_date)
    canonical_page = f"{canonical_date}.html" if is_duplicate else f"{current_date}.html"

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>The GenAI Briefing — {current_date}</title>
  {_seo_head(f'{current_date}.html', f'The GenAI Briefing for {current_date}: Top 10 Generative AI research, engineering and community stories with daily editorial synthesis.', canonical_page=canonical_page, noindex=is_duplicate)}{_render_adsense_head_snippet()}
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

    {_render_editorial_ad_slot()}

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

    <section id="tech-talks">
      <div class="section-head">
        <h2>IV. Tech Talks &amp; Keynotes</h2>
        <span><a href="tech-talks.html" style="color:var(--accent);text-decoration:none;">ALL CHANNELS →</a></span>
      </div>
      {talks_html}
    </section>

    {_render_subscribe_box_html()}

    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · ISSUE {current_date}</div>
      <div><a href="index.html">Front Page</a> · <a href="tech-talks.html">Tech Talks Index</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
    </footer>
  </div>
</body>
</html>"""


def _render_index_portal_html(archive_map: Dict[str, str], allow_network: bool = True) -> str:
    """Render `docs/index.html` as a high-density, editorial front page + evergreen guides + archive ledger."""
    sorted_dates = sorted(archive_map.keys(), reverse=True)
    latest_date = sorted_dates[0] if sorted_dates else ""
    latest_md = archive_map.get(latest_date, "")

    top10_items = _parse_top10_items(latest_md)
    x_md = _extract_section_markdown(latest_md, "X") or _extract_section_markdown(latest_md, "Twitter")
    pod_md = _extract_section_markdown(latest_md, "Podcast") or _extract_section_markdown(latest_md, "Audio")
    talks_md = (
        _extract_section_markdown(latest_md, "Tech Talk")
        or _extract_section_markdown(latest_md, "Keynote")
        or _extract_section_markdown(latest_md, "YouTube")
    )
    tldr_md = _extract_section_markdown(latest_md, "TL;DR") or _extract_section_markdown(latest_md, "Executive Summary")

    x_notes = _parse_bullet_notes(x_md, kind="x")
    pod_notes = _parse_bullet_notes(pod_md, kind="podcast")
    talk_notes = _parse_bullet_notes(talks_md, kind="tech_talk")

    if tldr_md:
        rendered_tldr = _harden_rendered_markdown_html(
            markdown.markdown(_strip_emojis(tldr_md), extensions=["extra", "sane_lists"])
        )
        tldr_html = f'<div class="editorial-callout"><h3>Executive Summary — {latest_date}</h3>{rendered_tldr}</div>'
    else:
        tldr_html = _build_editorial_synthesis_html(
            top10_items=top10_items,
            current_date=latest_date,
            x_count=max(len(x_notes), 3),
            pod_count=len(pod_notes),
            talk_count=max(len(talk_notes), 8),
        )

    top10_html = _render_top10_ledger_html(top10_items, allow_network=allow_network)
    x_html = _render_bullet_notes_html(x_md, kind="x", limit=4)
    pod_html = _render_notes_column_html(pod_notes, "Listen Episode")
    talks_html = _render_bullet_notes_html(talks_md, kind="tech_talk")

    guide_cards: List[str] = []
    for idx, g in enumerate(EVERGREEN_GUIDES, start=1):
        guide_cards.append(
            f"""
            <article class="guide-card">
              <div class="guide-kicker">
                <span>{idx:02d} · {html.escape(g['kicker'])}</span>
                <span class="muted">· {html.escape(g['reading_time'])}</span>
              </div>
              <h3><a href="{html.escape(g['slug'])}.html">{html.escape(g['title'])}</a></h3>
              <p class="briefing-summary">{html.escape(g['subtitle'])}</p>
            </article>
            """
        )

    archive_rows: List[str] = []
    for d in sorted_dates:
        items_d = _parse_top10_items(archive_map[d])
        leads = " · ".join(
            f'<a href="{_safe_http_url(it["url"])}" target="_blank" rel="noopener noreferrer">{html.escape(it["title"])}</a>'
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
  {_seo_head('index.html', 'Daily Generative AI technical briefing: ranked research papers, frontier lab engineering, evergreen engineering guides, researcher threads, podcasts and YouTube tech talks.')}{_render_adsense_head_snippet()}
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

    {_render_editorial_ad_slot()}

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

    <section id="tech-talks">
      <div class="section-head">
        <h2>IV. Tech Talks &amp; Keynotes</h2>
        <span><a href="tech-talks.html" style="color:var(--accent);text-decoration:none;">FULL TECH TALKS DIRECTORY →</a></span>
      </div>
      {talks_html}
    </section>

    <section id="guides">
      <div class="section-head">
        <h2>V. Evergreen Engineering Guides</h2>
        <span><a href="guides.html" style="color:var(--accent);text-decoration:none;">ALL 5 DEEP DIVES →</a></span>
      </div>
      <div class="guide-list">
        {"".join(guide_cards)}
      </div>
    </section>

    <section id="archive">
      <div class="section-head">
        <h2>VI. Past Issues Archive</h2>
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

    {_render_subscribe_box_html()}

    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · PUBLISHED DAILY</div>
      <div><a href="index.html">Front Page</a> · <a href="tech-talks.html">Tech Talks Index</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="{latest_date}.html">Latest Issue</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
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
                <h2>{idx:02d}. {html.escape(show["name"])} — Host: {html.escape(show["host"])}</h2>
                <span><a href="{_safe_http_url(show["apple_url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:none;">APPLE PODCASTS ↗</a></span>
              </div>
              <p style="font-family:var(--font-sans);font-size:0.84rem;color:var(--ink-muted);margin:0 0 8px;">Focus: {html.escape(show["focus"])}</p>
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
  {_seo_head('podcasts.html', 'Generative AI podcast index with recent episode summaries from leading AI engineering and research shows.')}{_render_adsense_head_snippet()}
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="podcasts", latest_date=latest_date)}
    {"".join(show_blocks)}
    {_render_subscribe_box_html()}
    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · AUDIO &amp; PODCASTS DIRECTORY</div>
      <div><a href="index.html">Front Page</a> · <a href="tech-talks.html">Tech Talks Index</a> · <a href="{latest_date}.html">Latest Issue</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
    </footer>
  </div>
</body>
</html>"""


def _render_tech_talks_page_html(
    channels_data: List[Dict[str, Any]],
    latest_date: str,
) -> str:
    """Render `docs/tech-talks.html` as a dedicated YouTube Tech Talks & Keynotes directory grouped by channel."""
    jump_pills: List[str] = []
    channel_blocks: List[str] = []

    for idx, ch in enumerate(channels_data, start=1):
        jump_pills.append(
            f'<a class="filter-pill" href="#channel-{idx}" style="text-decoration:none;">{idx:02d}. {html.escape(ch["name"])}</a>'
        )
        video_notes: List[Dict[str, str]] = []
        for vid in ch.get("videos", []):
            video_notes.append(
                {
                    "title": _strip_emojis(vid["title"]),
                    "url": vid["url"],
                    "kicker": ch["name"],
                    "meta": vid.get("published") or vid.get("meta") or "YouTube",
                    "hn_url": "",
                    "summary": _clean_excerpt(vid.get("summary", ""), max_chars=340),
                }
            )
        notes_html = _render_notes_column_html(video_notes, "Watch on YouTube")
        channel_blocks.append(
            f"""
            <section id="channel-{idx}">
              <div class="section-head">
                <h2>{idx:02d}. {html.escape(ch["name"])} — Host: {html.escape(ch.get("host", ch["name"]))}</h2>
                <span><a href="{_safe_http_url(ch["channel_url"])}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:none;">YOUTUBE CHANNEL ↗</a></span>
              </div>
              <p style="font-family:var(--font-sans);font-size:0.84rem;color:var(--ink-muted);margin:0 0 8px;">Focus: {html.escape(ch["focus"])}</p>
              {notes_html}
            </section>
            """
        )

    jump_bar_html = (
        f'<div class="filter-bar" aria-label="Channel Directory">{"".join(jump_pills)}</div>'
        if jump_pills
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="sage">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>The GenAI Briefing — Tech Talks &amp; Keynotes Directory</title>
  {_seo_head('tech-talks.html', 'Directory of YouTube tech talks and keynotes on LLMs, AI agents, RAG and inference, grouped by channel.')}{_render_adsense_head_snippet()}
  {EDITORIAL_CSS_AND_JS}
</head>
<body>
  <div class="page-wrap">
    {_render_masthead(active_page="tech_talks", latest_date=latest_date)}
    <div class="editorial-callout">
      <h3>YouTube Tech Talks &amp; Keynotes Directory ({len(channels_data)} Channels)</h3>
      <p>Curated technical keynotes, engineering lightboards, and academic seminars from Google Cloud Tech, IBM Technology, The Pragmatic Engineer, IBM Developer, Stanford CS25, LangChain, Andrej Karpathy, Anthropic, OpenAI, and Google DeepMind.</p>
    </div>
    {jump_bar_html}
    {"".join(channel_blocks)}
    {_render_subscribe_box_html()}
    <footer class="footer">
      <div>THE GENAI BRIEFING · JABI.IO · TECH TALKS &amp; KEYNOTES DIRECTORY</div>
      <div><a href="index.html">Front Page</a> · <a href="podcasts.html">Podcasts Index</a> · <a href="{latest_date}.html">Latest Issue</a> · <a href="feed.xml">RSS Feed</a> · {_footer_trust_links()}</div>
    </footer>
  </div>
</body>
</html>"""


def _build_offline_podcast_shows(archive_map: Dict[str, str], episodes_per_show: int = 3) -> List[Dict[str, Any]]:
    """Build podcast directory data from archived digests when live podcast RSS fetching is disabled or unavailable."""
    by_show: Dict[str, List[Dict[str, str]]] = {s["name"]: [] for s in FEATURED_PODCAST_SHOWS}
    seen_urls: Set[str] = set()

    for arch_date in sorted(archive_map.keys(), reverse=True):
        pod_md = _extract_section_markdown(archive_map[arch_date], "Podcast") or _extract_section_markdown(
            archive_map[arch_date], "Audio"
        )
        for note in _parse_bullet_notes(pod_md, kind="podcast"):
            norm_url = note["url"].strip().rstrip("/").lower()
            if not norm_url or norm_url in seen_urls:
                continue
            matched_name = ""
            kicker_low = note["kicker"].lower()
            for show in FEATURED_PODCAST_SHOWS:
                sname = show["name"]
                if sname.lower() in kicker_low or kicker_low in sname.lower() or sname.split(":")[0].lower() in kicker_low:
                    matched_name = sname
                    break
            if matched_name and len(by_show[matched_name]) < episodes_per_show:
                seen_urls.add(norm_url)
                by_show[matched_name].append(
                    {
                        "title": note["title"],
                        "url": note["url"],
                        "summary": note["summary"],
                        "published": arch_date,
                        "duration": note["meta"] or "Audio",
                    }
                )

    shows_data: List[Dict[str, Any]] = []
    for show in FEATURED_PODCAST_SHOWS:
        eps = by_show.get(show["name"], [])
        if eps:
            shows_data.append(
                {
                    "name": show["name"],
                    "host": show["host"],
                    "focus": show["focus"],
                    "apple_url": show["apple_url"],
                    "episodes": eps,
                }
            )
    return shows_data


def rebuild_docs_site(
    output_dir: Path,
    docs_dir: Path | None = None,
    latest_fallback_date: str = "",
    fetch_live_hubs: bool | None = None,
) -> None:
    """Regenerate all GitHub Pages HTML files, evergreen guides, trust pages, RSS feed, robots.txt, and sitemap.xml."""
    target_docs = docs_dir if docs_dir is not None else output_dir.parent / "docs"
    target_docs.mkdir(parents=True, exist_ok=True)
    (target_docs / ".nojekyll").write_text("", encoding="utf-8")
    (target_docs / "CNAME").write_text("jabi.io\n", encoding="utf-8")

    ads_client = _normalize_adsense_client_id()
    if ads_client:
        pub_id = ads_client.replace("ca-", "", 1)
        ads_txt_content = f"google.com, {pub_id}, DIRECT, f08c47fec0942fa0\n"
    else:
        ads_txt_content = (
            "# Google AdSense ads.txt for jabi.io — set GOOGLE_ADSENSE_CLIENT_ID (ca-pub-XXXXXXXXXXXXXXXX) to populate\n"
        )
    (target_docs / "ads.txt").write_text(ads_txt_content, encoding="utf-8")

    archive_files = {
        p.name.split("_genai_digest.md")[0]: p
        for p in output_dir.glob("*_genai_digest.md")
    }
    archive_dates = sorted(archive_files.keys())
    archive_map: Dict[str, str] = {
        arch_date: md_path.read_text(encoding="utf-8")
        for arch_date, md_path in archive_files.items()
    }
    duplicates = _detect_duplicate_digests(archive_map)

    if fetch_live_hubs is None:
        is_live_docs_build = docs_dir is None and output_dir.name == "digests"
    else:
        is_live_docs_build = bool(fetch_live_hubs)

    for arch_date in archive_dates:
        md_text = archive_map[arch_date]
        arch_title = f"The GenAI Briefing — {arch_date}"
        arch_html = _render_daily_digest_html(
            markdown_content=md_text,
            title=arch_title,
            current_date=arch_date,
            archive_dates=archive_dates,
            canonical_date=duplicates.get(arch_date),
            allow_network=is_live_docs_build,
        )
        (target_docs / f"{arch_date}.html").write_text(arch_html, encoding="utf-8")

    index_html = _render_index_portal_html(archive_map=archive_map, allow_network=is_live_docs_build)
    (target_docs / "index.html").write_text(index_html, encoding="utf-8")

    latest_d = archive_dates[-1] if archive_dates else latest_fallback_date
    (target_docs / "feed.xml").write_text(
        _render_rss_feed_xml(archive_map=archive_map, site_url=SITE_URL),
        encoding="utf-8",
    )
    (target_docs / "guides.html").write_text(_render_guides_index_html(latest_d), encoding="utf-8")
    for guide in EVERGREEN_GUIDES:
        (target_docs / f"{guide['slug']}.html").write_text(
            _render_guide_article_html(guide, latest_date=latest_d),
            encoding="utf-8",
        )
    (target_docs / "about.html").write_text(_render_about_page_html(latest_d), encoding="utf-8")
    (target_docs / "faq.html").write_text(_render_faq_page_html(latest_d), encoding="utf-8")
    (target_docs / "contact.html").write_text(_render_contact_page_html(latest_d), encoding="utf-8")
    (target_docs / "terms.html").write_text(_render_terms_page_html(latest_d), encoding="utf-8")
    (target_docs / "privacy.html").write_text(
        _render_privacy_page_html(latest_date=latest_d, include_adsense=False),
        encoding="utf-8",
    )
    (target_docs / "robots.txt").write_text(_render_robots_txt(), encoding="utf-8")
    (target_docs / "sitemap.xml").write_text(
        _render_sitemap_xml(
            archive_dates=archive_dates,
            latest_date=latest_d,
            duplicate_dates=set(duplicates.keys()),
        ),
        encoding="utf-8",
    )

    try:
        channels_data = fetch_detailed_tech_talks_hub(
            videos_per_channel=3,
            fetch_live=is_live_docs_build,
        )
        tech_talks_page_html = _render_tech_talks_page_html(
            channels_data=channels_data,
            latest_date=latest_d,
        )
        (target_docs / "tech-talks.html").write_text(tech_talks_page_html, encoding="utf-8")
    except Exception:
        pass

    shows_data: List[Dict[str, Any]] = []
    if is_live_docs_build:
        try:
            shows_data = fetch_detailed_podcast_hub(episodes_per_show=3)
        except Exception:
            shows_data = []
    if not shows_data and archive_map:
        shows_data = _build_offline_podcast_shows(archive_map, episodes_per_show=3)
    if shows_data:
        podcasts_page_html = _render_podcasts_page_html(
            shows_data=shows_data,
            latest_date=latest_d,
        )
        (target_docs / "podcasts.html").write_text(podcasts_page_html, encoding="utf-8")


def save_markdown_digest(
    markdown_content: str,
    output_dir: Path,
    timestamp: datetime | None = None,
    docs_dir: Path | None = None,
) -> Path:
    """Save the digest to a dated Markdown file, update `latest.md`, and rebuild GitHub Pages HTML in `docs/`."""
    ts = timestamp or datetime.now()
    date_str = ts.strftime("%Y-%m-%d")
    output_dir.mkdir(parents=True, exist_ok=True)

    dated_filename = f"{date_str}_genai_digest.md"
    dated_path = output_dir / dated_filename
    dated_path.write_text(markdown_content, encoding="utf-8")

    latest_path = output_dir / "latest.md"
    latest_path.write_text(markdown_content, encoding="utf-8")

    rebuild_docs_site(
        output_dir=output_dir,
        docs_dir=docs_dir,
        latest_fallback_date=date_str,
    )
    return dated_path
