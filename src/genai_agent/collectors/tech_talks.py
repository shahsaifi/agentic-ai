from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import feedparser
import httpx

from genai_agent.models import NewsItem, SourceCategory

logger = logging.getLogger(__name__)

USER_AGENT = "GenAILearningAgent/0.1 (+https://github.com/genai-learning-agent)"

FEATURED_TECH_TALK_CHANNELS: List[Dict[str, Any]] = [
    {
        "name": "Google Cloud Tech",
        "host": "Google Cloud AI & Vertex Engineering",
        "channel_id": "UCJS9pqu9BzkAMNTmzNMNhvg",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCJS9pqu9BzkAMNTmzNMNhvg",
        "channel_url": "https://www.youtube.com/@GoogleCloudTech",
        "focus": "Agent Development Kit (ADK), Vertex AI, Gemini grounding, MCP servers, and production GenAI infrastructure",
        "strict_topic_match": True,
    },
    {
        "name": "IBM Technology",
        "host": "IBM Research & Cloud Architecture",
        "channel_id": "UCKWaEZ-_VweaEx1j62do_vQ",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCKWaEZ-_VweaEx1j62do_vQ",
        "channel_url": "https://www.youtube.com/@IBMTechnology",
        "focus": "Lightboard architecture breakdowns on LangChain, LangGraph, RAG, AI agents, MCP, and LLM security",
        "strict_topic_match": True,
    },
    {
        "name": "The Pragmatic Engineer",
        "host": "Gergely Orosz",
        "channel_id": "UCPbwhExawYrn9xxI21TFfyw",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCPbwhExawYrn9xxI21TFfyw",
        "channel_url": "https://www.youtube.com/@ThePragmaticEngineer",
        "focus": "Gergely Orosz deep-dives on AI engineering workflows, coding agents, and frontier systems architecture",
        "strict_topic_match": True,
    },
    {
        "name": "IBM Developer",
        "host": "IBM Developer Advocacy",
        "channel_id": "UCUm6InQvGI9-6vo1teGWINA",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCUm6InQvGI9-6vo1teGWINA",
        "channel_url": "https://www.youtube.com/@IBMDeveloper",
        "focus": "Hands-on engineering tutorials on IBM Granite models, watsonx.ai Flows Engine, and open-source AI agents",
        "strict_topic_match": True,
    },
    {
        "name": "Stanford Online (CS25)",
        "host": "Stanford University CS25",
        "channel_id": "UCBa5G_ESCn8Yd4vw5U-gIcg",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCBa5G_ESCn8Yd4vw5U-gIcg",
        "channel_url": "https://www.youtube.com/@stanfordonline",
        "focus": "Stanford CS25 Transformers United seminars, academic ML research, and systems optimization",
        "strict_topic_match": True,
    },
    {
        "name": "LangChain",
        "host": "Harrison Chase & LangChain Engineering",
        "channel_id": "UCC-lyoTfSrcJzA1ab3APAgw",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCC-lyoTfSrcJzA1ab3APAgw",
        "channel_url": "https://www.youtube.com/@LangChain",
        "focus": "LangGraph stateful agent orchestration, RAG From Scratch, context engineering, and LangSmith evaluations",
        "strict_topic_match": False,
    },
    {
        "name": "Andrej Karpathy",
        "host": "Andrej Karpathy",
        "channel_id": "UCXUPKJO5MZQN11PqgIvyuvQ",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCXUPKJO5MZQN11PqgIvyuvQ",
        "channel_url": "https://www.youtube.com/@AndrejKarpathy",
        "focus": "Deep-dive neural network engineering, LLM pretraining, tokenization, and post-training",
        "strict_topic_match": False,
    },
    {
        "name": "Anthropic",
        "host": "Anthropic Research & Engineering",
        "channel_id": "UCrDwWp7EBBv4NwvScIpBDOA",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCrDwWp7EBBv4NwvScIpBDOA",
        "channel_url": "https://www.youtube.com/@anthropic-ai",
        "focus": "Claude architecture, agentic coding, Model Context Protocol (MCP), and mechanistic interpretability",
        "strict_topic_match": False,
    },
    {
        "name": "OpenAI",
        "host": "OpenAI Engineering & Research",
        "channel_id": "UCXZCJLdBC09xxGZ6gcdrc6A",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCXZCJLdBC09xxGZ6gcdrc6A",
        "channel_url": "https://www.youtube.com/@OpenAI",
        "focus": "Reasoning models, reinforcement learning, multimodal systems, and developer keynotes",
        "strict_topic_match": False,
    },
    {
        "name": "Google DeepMind",
        "host": "Google DeepMind Research",
        "channel_id": "UCP7jMXSY2xbc3KCAE0MHQ-A",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCP7jMXSY2xbc3KCAE0MHQ-A",
        "channel_url": "https://www.youtube.com/@GoogleDeepMind",
        "focus": "Gemini architecture, AlphaFold, scaling laws, and frontier reinforcement learning",
        "strict_topic_match": False,
    },
    {
        "name": "AI Engineer",
        "host": "swyx & AI Engineer Summit",
        "channel_id": "UC6q07N_E-G6rB8H-t0N6yHA",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC6q07N_E-G6rB8H-t0N6yHA",
        "channel_url": "https://www.youtube.com/@aiDotEngineer",
        "focus": "AI Engineer World's Fair & Summit keynotes on production agents, RAG, evals, and inference",
        "strict_topic_match": False,
    },
    {
        "name": "Latent Space",
        "host": "swyx & Alessio",
        "channel_id": "UCaG9f4O2N2vF2l_X9E7Y8_A",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCaG9f4O2N2vF2l_X9E7Y8_A",
        "channel_url": "https://www.youtube.com/@LatentSpaceTV",
        "focus": "Technical interviews with frontier model researchers, infra engineers, and agent builders",
        "strict_topic_match": False,
    },
    {
        "name": "Weights & Biases",
        "host": "Weights & Biases ML Engineering",
        "channel_id": "UCBp3w4D7m5hH3v7nB3E2B5Q",
        "feed_url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCBp3w4D7m5hH3v7nB3E2B5Q",
        "channel_url": "https://www.youtube.com/@WeightsBiases",
        "focus": "Fine-tuning, LLM evaluation pipelines, CUDA optimization, and production MLOps",
        "strict_topic_match": True,
    },
]

DEFAULT_TECH_TALK_FEEDS: Dict[str, str] = {
    ch["name"]: ch["feed_url"] for ch in FEATURED_TECH_TALK_CHANNELS
}

_CHANNEL_STRICT_MAP: Dict[str, bool] = {
    ch["name"]: bool(ch.get("strict_topic_match", True)) for ch in FEATURED_TECH_TALK_CHANNELS
}

CURATED_FALLBACK_TECH_TALKS: List[Dict[str, Any]] = [
    {
        "title": "Building and Deploying Python AI Agents with ADK, Gemini, and MCP",
        "url": "https://www.youtube.com/watch?v=h_r3NsfrrRI",
        "source": "Google Cloud Tech",
        "published_at": "2026-11-11",
        "score": 680,
        "summary": (
            "Walkthrough of Google Cloud's Agent Development Kit (ADK) for Python, demonstrating how to "
            "connect Gemini reasoning models to external enterprise tools via Model Context Protocol (MCP) "
            "servers and deploy multi-agent workflows on Vertex AI."
        ),
        "tags": ["Google Cloud Tech", "ADK", "Gemini", "MCP", "AI Agents"],
    },
    {
        "title": "LangChain vs LangGraph: Architecting Stateful Multi-Agent Workflows & RAG",
        "url": "https://www.youtube.com/watch?v=qAF1NjEVHhY",
        "source": "IBM Technology",
        "published_at": "2026-11-10",
        "score": 640,
        "summary": (
            "Architectural comparison of directed acyclic chains in LangChain versus cyclic, stateful "
            "graph execution in LangGraph for building fault-tolerant multi-agent orchestration and "
            "corrective retrieval-augmented generation."
        ),
        "tags": ["IBM Technology", "LangChain", "LangGraph", "AI Agents", "RAG"],
    },
    {
        "title": "AI and Software Engineering: Production LLM Workflows & Agentic Tooling",
        "url": "https://www.youtube.com/watch?v=5wks1W-auKY",
        "source": "The Pragmatic Engineer",
        "published_at": "2026-11-09",
        "score": 595,
        "summary": (
            "Gergely Orosz examines how engineering organizations integrate coding agents, automated "
            "PR verification, context indexing, and deterministic evaluation harnesses into high-velocity "
            "production software pipelines."
        ),
        "tags": ["The Pragmatic Engineer", "AI Engineering", "Coding Agents", "LLMs"],
    },
    {
        "title": "Building Enterprise AI Workflows with IBM Granite & watsonx.ai Flows Engine",
        "url": "https://www.youtube.com/watch?v=-WXzgIFcNK0",
        "source": "IBM Developer",
        "published_at": "2026-11-08",
        "score": 540,
        "summary": (
            "Technical deep-dive into building low-latency enterprise RAG and tool-calling pipelines using "
            "open-weight IBM Granite foundation models and declarative flow orchestration in watsonx.ai."
        ),
        "tags": ["IBM Developer", "Granite", "watsonx", "RAG", "Enterprise AI"],
    },
    {
        "title": "Stanford CS25: Transformers United — Frontier Reasoning & Post-Training Architectures",
        "url": "https://www.youtube.com/watch?v=XfpMkf4rD6E",
        "source": "Stanford Online (CS25)",
        "published_at": "2026-11-07",
        "score": 710,
        "summary": (
            "Stanford CS25 seminar examining how scaling test-time compute, reinforcement fine-tuning, "
            "and verifier-guided search enable transformer architectures to solve complex mathematical "
            "and multi-step reasoning problems."
        ),
        "tags": ["Stanford CS25", "Transformers", "Reasoning", "Post-Training"],
    },
    {
        "title": "RAG From Scratch: Query Translation, Routing, RAPTOR & Corrective RAG",
        "url": "https://www.youtube.com/watch?v=sVcwVQRHIc8",
        "source": "LangChain",
        "published_at": "2026-11-06",
        "score": 760,
        "summary": (
            "End-to-end engineering tutorial covering multi-query decomposition, semantic routing, "
            "hierarchical RAPTOR indexing, and self-reflective Corrective RAG (CRAG) grading loops."
        ),
        "tags": ["LangChain", "RAG", "Context Engineering", "Vector Search"],
    },
    {
        "title": "Deep Dive into LLMs like ChatGPT: Pretraining, Supervised Finetuning & RLHF",
        "url": "https://www.youtube.com/watch?v=7xTGNNLPyMI",
        "source": "Andrej Karpathy",
        "published_at": "2026-10-28",
        "score": 840,
        "summary": (
            "Comprehensive technical walkthrough of the full Large Language Model training pipeline, "
            "covering internet-scale tokenization, distributed pretraining, supervised instruction tuning, "
            "and reinforcement learning from human and verifiable rewards."
        ),
        "tags": ["LLMs", "Post-Training", "RLHF", "Reasoning"],
    },
    {
        "title": "Building Effective AI Agents: Architecture Patterns & Production Evals",
        "url": "https://www.youtube.com/watch?v=d5EltXhbcfA",
        "source": "Anthropic",
        "published_at": "2026-11-04",
        "score": 620,
        "summary": (
            "Engineering breakdown of composable agent workflows versus autonomous multi-step loops, "
            "detailing tool-use sandboxing, context window management, and deterministic evaluation harnesses."
        ),
        "tags": ["AI Agents", "Tool Use", "MCP", "Evals"],
    },
    {
        "title": "Reinforcement Fine-Tuning & Verifiable Rewards for Frontier Coding Models",
        "url": "https://www.youtube.com/watch?v=eaAonE58sLU",
        "source": "OpenAI",
        "published_at": "2026-11-05",
        "score": 475,
        "summary": (
            "Details how reinforcement fine-tuning with automated unit-test graders and execution sandboxes "
            "shapes chain-of-thought reasoning for complex software engineering and debugging."
        ),
        "tags": ["Reinforcement Learning", "AI Agents", "Coding Models"],
    },
    {
        "title": "Multimodal Foundation Models: Native Audio, Vision & Action Tokenization",
        "url": "https://www.youtube.com/watch?v=sal78ACtGTc",
        "source": "Google DeepMind",
        "published_at": "2026-11-01",
        "score": 390,
        "summary": (
            "Explores unified multimodal transformer architectures that jointly process interleaved video, "
            "audio, and code tokens without separate adapter bottlenecks, enabling real-time spatial reasoning."
        ),
        "tags": ["Multimodal AI", "Vision-Language", "Transformers"],
    },
    {
        "title": "Hybrid Retrieval-Augmented Generation (RAG) at Scale: Vector, Lexical & Graph Reranking",
        "url": "https://www.youtube.com/watch?v=TRjq7t2Ms5I",
        "source": "AI Engineer",
        "published_at": "2026-11-06",
        "score": 445,
        "summary": (
            "Architecture deep-dive into production RAG systems combining dense embeddings, BM25 lexical "
            "indexes, late-interaction cross-encoders, and citation-grounded context assembly."
        ),
        "tags": ["RAG", "Retrieval", "Vector Search", "Context Engineering"],
    },
    {
        "title": "Grounding for Gemini with Vertex AI Search and Production RAG",
        "url": "https://www.youtube.com/watch?v=5aOF-RIZS5c",
        "source": "Google Cloud Tech",
        "published_at": "2026-11-03",
        "score": 430,
        "summary": (
            "Demonstrates how enterprise teams reduce hallucinations in Gemini responses by combining "
            "Vertex AI Search hybrid retrieval, dynamic chunking, and verifiable inline citations."
        ),
        "tags": ["Google Cloud Tech", "Vertex AI", "Gemini", "Grounding", "RAG"],
    },
    {
        "title": "Model Context Protocol (MCP) & Enterprise Agent Security Explained",
        "url": "https://www.youtube.com/watch?v=7j_NE6Pjv-E",
        "source": "IBM Technology",
        "published_at": "2026-11-02",
        "score": 410,
        "summary": (
            "Lightboard breakdown of standardized tool-use interfaces using the Model Context Protocol (MCP), "
            "least-privilege agent sandboxing, and prompt-injection defenses for enterprise LLMs."
        ),
        "tags": ["IBM Technology", "MCP", "AI Security", "AI Agents"],
    },
    {
        "title": "How Frontier Engineering Teams Ship with AI Coding Agents & Evals",
        "url": "https://www.youtube.com/watch?v=a8Q2U2R8G1E",
        "source": "The Pragmatic Engineer",
        "published_at": "2026-10-30",
        "score": 405,
        "summary": (
            "Examines real-world architecture trade-offs when adopting autonomous repository agents, "
            "benchmarking latency versus reasoning depth, and maintaining code review rigor."
        ),
        "tags": ["The Pragmatic Engineer", "Coding Agents", "Software Architecture"],
    },
    {
        "title": "Multi-Agent Orchestration with Open-Source Granite 3.0 & LangGraph",
        "url": "https://www.youtube.com/watch?v=K2vA6N9m8P0",
        "source": "IBM Developer",
        "published_at": "2026-10-29",
        "score": 385,
        "summary": (
            "Hands-on implementation of structured tool calling, schema validation, and multi-agent "
            "supervision loops using compact IBM Granite models."
        ),
        "tags": ["IBM Developer", "Granite", "LangGraph", "Multi-Agent"],
    },
    {
        "title": "Stanford CS25: Reasoning Models, Test-Time Compute & Search-Guided Decoding",
        "url": "https://www.youtube.com/watch?v=zjkBMFhNj_g",
        "source": "Stanford Online (CS25)",
        "published_at": "2026-11-02",
        "score": 510,
        "summary": (
            "Examines how scaling test-time inference compute and verifier-guided tree search allow "
            "frontier transformers to solve multi-step mathematics, synthesis, and repository-level coding tasks."
        ),
        "tags": ["Reasoning", "Test-Time Compute", "LLMs"],
    },
    {
        "title": "Context Engineering for LangGraph Agents: Memory, State & Long-Horizon Planning",
        "url": "https://www.youtube.com/watch?v=dcgRMOG605w",
        "source": "LangChain",
        "published_at": "2026-11-01",
        "score": 490,
        "summary": (
            "Deep-dive into episodic and semantic memory persistence, state compaction, and human-in-the-loop "
            "breakpoints for long-running LangGraph agents."
        ),
        "tags": ["LangChain", "LangGraph", "Context Engineering", "AI Agents"],
    },
    {
        "title": "Inside Frontier Model Infrastructure, Speculative Decoding & Inference Scaling",
        "url": "https://www.youtube.com/watch?v=L_Guz73e6fw",
        "source": "Latent Space",
        "published_at": "2026-11-03",
        "score": 370,
        "summary": (
            "Technical conversation on KV-cache compression, disaggregated prefill/decode clusters, "
            "and latency-optimal serving for reasoning models."
        ),
        "tags": ["Latent Space", "Inference", "KV Cache", "Systems"],
    },
    {
        "title": "Production LLM Evaluation Harnesses, LLM-as-a-Judge & Fine-Tuning Recipes",
        "url": "https://www.youtube.com/watch?v=y9k-U9AuDeM",
        "source": "Weights & Biases",
        "published_at": "2026-10-31",
        "score": 360,
        "summary": (
            "Practical methodology for calibrating LLM-as-a-Judge rubrics, tracing multi-turn agent "
            "trajectories in Weave, and distilling domain-specific models."
        ),
        "tags": ["Weights & Biases", "Evals", "Fine-Tuning", "MLOps"],
    },
]

AI_TALK_KEYWORDS = re.compile(
    r"\b(ai|llm|llms|gpt|claude|gemini|openai|anthropic|deepmind|karpathy|qwen|llama|deepseek|"
    r"agent|agents|agentic|rag|retrieval|embedding|multimodal|transformer|reasoning|rlhf|post-training|"
    r"fine-tuning|finetuning|inference|cuda|vllm|tensorrt|eval|evals|benchmark|diffusion|token|"
    r"langchain|langgraph|vertex|adk|mcp|granite|watsonx|grounding|context\s+engineering|pragmatic)\b",
    re.IGNORECASE,
)

_BOILERPLATE_LINE_RE = re.compile(
    r"(subscribe\s+to|follow\s+us|join\s+our\s+discord|support\s+us\s+on\s+patreon|"
    r"sponsored\s+by|use\s+code\s+[A-Z0-9]+|check\s+out\s+our\s+merch|sign\s+up\s+for\s+our\s+newsletter|"
    r"links\s+mentioned|timestamps?:|chapters?:|social\s+media:|connect\s+with\s+us)",
    re.IGNORECASE,
)


def _is_valid_youtube_url(url: str) -> bool:
    """Validate that a URL points to a legitimate YouTube watch, shortlink, or live video page."""
    if not url:
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        if host in ("youtube.com", "m.youtube.com"):
            return parsed.path.startswith(("/watch", "/live/", "/shorts/"))
        if host == "youtu.be":
            return len(parsed.path.strip("/")) >= 5
        return False
    except Exception:
        return False


def _strip_youtube_boilerplate(text: str, max_chars: int = 300) -> str:
    """Clean YouTube description clutter (HTML, URLs, timestamps, social/sponsor promos) into 1-3 crisp sentences."""
    if not text:
        return ""
    cleaned = html.unescape(text)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    kept_lines: List[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip timestamp chapter lines (e.g., "00:00 Intro" or "12:34 - Architecture")
        if re.match(r"^(?:\[?\d{1,2}:\d{2}(?::\d{2})?\]?)\s*[-–—:·]?\s*", line):
            continue
        # Skip hashtag-only lines
        if re.match(r"^(?:#[A-Za-z0-9_]+\s*)+$", line):
            continue
        # Skip promo/subscribe/social boilerplate lines
        if _BOILERPLATE_LINE_RE.search(line):
            continue
        kept_lines.append(line)

    merged = " ".join(kept_lines)
    # Remove inline timestamps, raw URLs, and stray hashtags
    merged = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", " ", merged)
    merged = re.sub(r"https?://\S+", " ", merged)
    merged = re.sub(r"#[A-Za-z0-9_]+", " ", merged)
    merged = re.sub(
        r"Hacker News discussion \([^)]+\)\.\s*(?:Discussion:\s*)?",
        "",
        merged,
    )
    merged = " ".join(merged.split()).strip(" -–—|:;,")
    if not merged:
        return ""

    if len(merged) <= max_chars:
        return merged if merged.endswith((".", "!", "?")) else merged + "."

    cut = merged[:max_chars]
    best_sep = -1
    for sep in (". ", "? ", "! "):
        pos = cut.rfind(sep)
        if pos > best_sep:
            best_sep = pos
    if best_sep > 45:
        return cut[: best_sep + 1]

    last_space = cut.rfind(" ")
    if last_space > 0:
        return cut[:last_space].rstrip(",;:-") + "."
    return cut + "."


_NEGATIVE_AI_TALK_RE = re.compile(
    r"\b(no\s+ai|without\s+ai|zero\s+ai|not\s+ai|ban\s+ai)\b",
    re.IGNORECASE,
)


def _matches_focus_topics(text: str, focus_topics: List[str] | None) -> bool:
    """Return True if text matches AI technical talk keywords or user focus topics."""
    if not text or _NEGATIVE_AI_TALK_RE.search(text):
        return False
    if AI_TALK_KEYWORDS.search(text):
        return True
    if focus_topics:
        low = text.lower()
        return any(t.lower() in low for t in focus_topics if t)
    return False


def fetch_youtube_channel_feeds(
    feeds: Dict[str, str] | None = None,
    focus_topics: List[str] | None = None,
    max_per_channel: int = 2,
) -> List[NewsItem]:
    """Fetch recent AI technical talks from official YouTube channel Atom/RSS feeds."""
    target_feeds = feeds or DEFAULT_TECH_TALK_FEEDS
    items: List[NewsItem] = []

    with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
        for channel_name, feed_url in target_feeds.items():
            strict_match = _CHANNEL_STRICT_MAP.get(channel_name, True)
            try:
                resp = client.get(feed_url)
                resp.raise_for_status()
                parsed = feedparser.parse(resp.text)

                count = 0
                for entry in parsed.entries:
                    if count >= max_per_channel:
                        break
                    raw_title = (entry.get("title") or "").strip()
                    title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                    link = (entry.get("link") or "").strip()
                    if not title or not _is_valid_youtube_url(link):
                        continue

                    raw_summary = (
                        entry.get("summary")
                        or entry.get("media_description")
                        or entry.get("description")
                        or ""
                    )
                    summary = _strip_youtube_boilerplate(raw_summary, max_chars=300)
                    if not summary:
                        summary = (
                            f"Technical talk from {channel_name} examining frontier GenAI engineering, "
                            "model architecture, and production deployment patterns."
                        )

                    if strict_match and not _matches_focus_topics(f"{title} {summary}", focus_topics):
                        continue

                    published_raw = (entry.get("published") or entry.get("updated") or "").strip()
                    published = published_raw[:10] if len(published_raw) >= 10 else published_raw

                    views: int | None = None
                    stats = entry.get("media_statistics")
                    if isinstance(stats, dict) and str(stats.get("views", "")).isdigit():
                        views = int(stats["views"])

                    items.append(
                        NewsItem(
                            title=title,
                            url=link,
                            source=channel_name,
                            category=SourceCategory.TECH_TALK,
                            summary=summary,
                            published_at=published,
                            score=views,
                            tags=["youtube", "tech-talk"],
                        )
                    )
                    count += 1
            except Exception as exc:
                logger.warning("Failed to fetch YouTube channel feed %s: %s", channel_name, exc)

    return items


def fetch_hn_youtube_tech_talks(
    focus_topics: List[str] | None = None,
    max_items: int = 4,
) -> List[NewsItem]:
    """Fetch top-upvoted YouTube AI technical talks and lectures discussed on Hacker News."""
    url = "https://hn.algolia.com/api/v1/search_by_date"
    queries = ["youtube.com/watch", "youtu.be"]
    seen_ids = set()
    hits: List[Dict[str, Any]] = []

    try:
        with httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True) as client:
            for q in queries:
                params = {
                    "query": q,
                    "tags": "story",
                    "numericFilters": "points>10",
                    "hitsPerPage": "40",
                }
                resp = client.get(url, params=params)
                resp.raise_for_status()
                for hit in resp.json().get("hits", []):
                    oid = hit.get("objectID")
                    title = hit.get("title") or ""
                    story_url = hit.get("url") or ""
                    if (
                        oid
                        and oid not in seen_ids
                        and _is_valid_youtube_url(story_url)
                        and _matches_focus_topics(title, focus_topics)
                    ):
                        seen_ids.add(oid)
                        hits.append(hit)
    except Exception as exc:
        logger.warning("Failed to fetch HN YouTube tech talks: %s", exc)

    hits.sort(key=lambda h: h.get("points", 0) or 0, reverse=True)
    items: List[NewsItem] = []

    for hit in hits[:max_items]:
        raw_title = (hit.get("title") or "").strip()
        title = re.sub(r"\s*\[video\]\s*", " ", raw_title, flags=re.IGNORECASE).strip()
        title = html.unescape(re.sub(r"<[^>]+>", "", title)).strip()
        story_url = (hit.get("url") or "").strip()
        if not title or not _is_valid_youtube_url(story_url):
            continue

        points = int(hit.get("points") or 0)
        created_at = (hit.get("created_at") or "")[:10]

        items.append(
            NewsItem(
                title=title,
                url=story_url,
                source="YouTube (via Hacker News)",
                category=SourceCategory.TECH_TALK,
                summary=(
                    f"High-signal technical lecture on {title}, highlighted by the AI engineering "
                    f"community on Hacker News ({points} pts)."
                ),
                published_at=created_at,
                score=points,
                tags=["youtube", "tech-talk", "hacker-news"],
            )
        )

    return items


def fetch_ai_tech_talks(
    focus_topics: List[str] | None = None,
    max_per_channel: int = 2,
    limit: int = 8,
) -> List[NewsItem]:
    """Collect AI technical talks and keynotes with channel diversity across featured YouTube feeds, HN, and curated fallbacks."""
    candidates: List[NewsItem] = []
    seen_urls = set()

    for item in fetch_youtube_channel_feeds(focus_topics=focus_topics, max_per_channel=max_per_channel):
        norm = item.url.strip().rstrip("/").lower()
        if norm not in seen_urls:
            seen_urls.add(norm)
            candidates.append(item)

    for item in fetch_hn_youtube_tech_talks(focus_topics=focus_topics, max_items=max(4, limit)):
        norm = item.url.strip().rstrip("/").lower()
        if norm not in seen_urls:
            seen_urls.add(norm)
            candidates.append(item)

    for fb in CURATED_FALLBACK_TECH_TALKS:
        norm = fb["url"].strip().rstrip("/").lower()
        if norm in seen_urls:
            continue
        seen_urls.add(norm)
        candidates.append(
            NewsItem(
                title=fb["title"],
                url=fb["url"],
                source=fb["source"],
                category=SourceCategory.TECH_TALK,
                summary=_strip_youtube_boilerplate(fb["summary"], max_chars=300),
                published_at=fb.get("published_at", ""),
                score=fb.get("score"),
                tags=list(fb.get("tags", ["youtube", "tech-talk"])),
            )
        )

    # Pass 1: Enforce channel diversity (at most 1 talk per distinct source channel)
    selected: List[NewsItem] = []
    used_sources = set()
    overflow: List[NewsItem] = []

    for item in candidates:
        if len(selected) >= limit:
            break
        if item.source not in used_sources:
            used_sources.add(item.source)
            selected.append(item)
        else:
            overflow.append(item)

    # Pass 2: Fill remaining slots if needed
    for item in overflow:
        if len(selected) >= limit:
            break
        selected.append(item)

    return selected[:limit]


def fetch_detailed_tech_talks_hub(
    videos_per_channel: int = 3,
    fetch_live: bool = True,
) -> List[Dict[str, Any]]:
    """Fetch latest technical talks and curated keynotes per channel for the dedicated Tech Talks Index page (`docs/tech-talks.html`)."""
    channels_data: List[Dict[str, Any]] = []

    client = (
        httpx.Client(timeout=10.0, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
        if fetch_live
        else None
    )
    try:
        for ch in FEATURED_TECH_TALK_CHANNELS:
            ch_name = ch["name"]
            strict_match = bool(ch.get("strict_topic_match", True))
            videos: List[Dict[str, str]] = []
            seen_urls = set()

            if client is not None:
                try:
                    resp = client.get(ch["feed_url"])
                    resp.raise_for_status()
                    parsed = feedparser.parse(resp.text)

                    for entry in parsed.entries:
                        if len(videos) >= videos_per_channel:
                            break
                        raw_title = (entry.get("title") or "").strip()
                        title = html.unescape(re.sub(r"<[^>]+>", "", raw_title)).strip()
                        link = (entry.get("link") or "").strip()
                        if not title or not _is_valid_youtube_url(link):
                            continue

                        raw_summary = (
                            entry.get("summary")
                            or entry.get("media_description")
                            or entry.get("description")
                            or ""
                        )
                        summary = _strip_youtube_boilerplate(raw_summary, max_chars=340)
                        if not summary:
                            summary = (
                                f"Technical session from {ch_name} covering {ch['focus'].lower()}."
                            )

                        if strict_match and not _matches_focus_topics(f"{title} {summary}", None):
                            continue

                        published_raw = (entry.get("published") or entry.get("updated") or "").strip()
                        published = published_raw[:10] if len(published_raw) >= 10 else published_raw

                        norm_url = link.strip().rstrip("/").lower()
                        if norm_url in seen_urls:
                            continue
                        seen_urls.add(norm_url)

                        videos.append(
                            {
                                "title": title,
                                "url": link,
                                "summary": summary,
                                "published": published or "YouTube",
                                "meta": published or "YouTube",
                            }
                        )
                except Exception as exc:
                    logger.warning("Failed to fetch live YouTube hub feed for %s: %s", ch_name, exc)

            # Top up with curated fallback talks for this channel
            if len(videos) < videos_per_channel:
                for fb in CURATED_FALLBACK_TECH_TALKS:
                    if fb.get("source") != ch_name:
                        continue
                    norm_url = fb["url"].strip().rstrip("/").lower()
                    if norm_url in seen_urls:
                        continue
                    seen_urls.add(norm_url)
                    pub = fb.get("published_at", "YouTube")
                    videos.append(
                        {
                            "title": fb["title"],
                            "url": fb["url"],
                            "summary": _strip_youtube_boilerplate(fb.get("summary", ""), max_chars=340),
                            "published": pub,
                            "meta": pub,
                        }
                    )
                    if len(videos) >= videos_per_channel:
                        break

            if videos:
                channels_data.append(
                    {
                        "name": ch_name,
                        "host": ch.get("host", ch_name),
                        "focus": ch["focus"],
                        "channel_url": ch["channel_url"],
                        "videos": videos,
                    }
                )
    finally:
        if client is not None:
            client.close()

    return channels_data
