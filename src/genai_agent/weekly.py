from __future__ import annotations

import logging
import math
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Set, Tuple
from urllib.parse import urlparse

from genai_agent.guides import EVERGREEN_GUIDES

logger = logging.getLogger(__name__)

# 6 concrete engineering clusters: (Full Name, Short SEO Label, Keyword Rules)
WEEKLY_CLUSTERS: List[Tuple[str, str, Tuple[str, ...]]] = [
    (
        "Agentic Systems & Tool Use",
        "Agents",
        (
            "agent",
            "agentic",
            "mcp",
            "tool use",
            "tool-use",
            "tool calling",
            "harness",
            "orchestrat",
            "multi-agent",
            "sandbox",
            "computer-using",
            "computer use",
            "autonomous",
            "embodied",
            "robot",
            "manipulation",
            "workflow",
            "decision model",
            "long-horizon",
            "browser",
        ),
    ),
    (
        "Inference, Quantization & Architectures",
        "Inference",
        (
            "quantiz",
            "inference",
            "kv-cache",
            "kv cache",
            "deltanet",
            "mamba",
            "transformer",
            "distill",
            "speculative",
            "recurrent",
            "linear attention",
            "mixture-of",
            "moe",
            "kernel",
            "latency",
            "fp8",
            "int4",
            "pruning",
            "weight-space",
            "hyper-connection",
            "token-efficient",
            "sparse",
            "streaming asr",
            "bit-level",
            "architecture",
            "state space",
            "domestic chip",
        ),
    ),
    (
        "World Models, Video & 3D",
        "World Models",
        (
            "world model",
            "world-action",
            "world intelligence",
            "worldfoundry",
            "video",
            "3d",
            "4d",
            "gaussian",
            "3dgs",
            "splat",
            "spatial",
            "rendering",
            "view synthesis",
            "scene generation",
            "diffusion",
            "image generation",
            "image editing",
            "visual",
            "multimodal",
            "physical ai",
            "real-to-sim",
            "real2sim",
            "embodied mind",
        ),
    ),
    (
        "Evaluation, Benchmarks & Safety",
        "Evals & Safety",
        (
            "benchmark",
            "eval",
            "arena",
            "leaderboard",
            "judge",
            "annotator",
            "safety",
            "alignment",
            "forensic",
            "detection",
            "reliability",
            "privacy",
            "security",
            "leak",
            "misalignment",
            "proof",
            "diagnostic",
            "forecasting",
            "verification",
            "compliance",
        ),
    ),
    (
        "Coding Agents & DevTools",
        "Coding Agents",
        (
            "coding",
            "claude code",
            "code localizer",
            "code2video",
            "code golf",
            "fixer",
            "github",
            "cursor",
            "copilot",
            "codex",
            "swe-bench",
            "developer",
            "devtool",
            "ide",
            "compiler",
            "programming",
            "refactor",
            "terminal",
            "cli",
            "pixel as code",
            "vision with code",
            "antigravity",
        ),
    ),
    (
        "Frontier Labs & Ecosystem",
        "Frontier Labs",
        (
            "openai",
            "anthropic",
            "deepmind",
            "gemini",
            "gpt-",
            "claude",
            "qwen",
            "llama",
            "deepseek",
            "frontier",
            "open source",
            "open-weight",
            "technical report",
            "self-hosting",
            "nvidia",
            "nemotron",
            "fleet",
            "enterprise",
            "ecosystem",
            "foundation model",
        ),
    ),
]

_CLUSTER_SHORT_LABELS: Dict[str, str] = {name: short for name, short, _ in WEEKLY_CLUSTERS}

_CLUSTER_ENGINEERING_TAKEAWAY: Dict[str, str] = {
    "Agentic Systems & Tool Use": (
        "Production teams adopting multi-step agent loops should enforce hard step budgets, "
        "least-privilege execution sandboxes, and deterministic exit verification rather than relying on model self-assessment."
    ),
    "Inference, Quantization & Architectures": (
        "Serving teams should benchmark low-bit quantization and recurrent or linear-attention variants on "
        "end-to-end tool-calling schemas and p95 decode latency rather than perplexity alone."
    ),
    "World Models, Video & 3D": (
        "Multimodal and spatial pipelines benefit from explicit structural or physics-aware conditioning "
        "over isolated frame generation, with latency budgets validated on streaming workloads."
    ),
    "Evaluation, Benchmarks & Safety": (
        "Public leaderboard gains require cross-checking against private, execution-based regression suites "
        "and calibrated judge rubrics before promoting any checkpoint to production traffic."
    ),
    "Coding Agents & DevTools": (
        "Engineering organizations deploying autonomous coding agents should isolate repository credentials, "
        "restrict auto-approve rules, and gate pull requests on deterministic CI test suites."
    ),
    "Frontier Labs & Ecosystem": (
        "Teams evaluating new frontier and open-weight releases should map accuracy against unit cost via "
        "cascaded routing so routine requests stay on fast, low-cost model tiers."
    ),
}

_CLUSTER_TO_GUIDES: Dict[str, Tuple[str, ...]] = {
    "Agentic Systems & Tool Use": (
        "guide-agent-harness-engineering",
        "guide-rag-context-engineering",
        "guide-llm-evaluation-benchmarks",
    ),
    "Inference, Quantization & Architectures": (
        "guide-llm-inference-quantization",
        "guide-cascaded-model-routing",
        "guide-rag-context-engineering",
    ),
    "World Models, Video & 3D": (
        "guide-llm-inference-quantization",
        "guide-rag-context-engineering",
        "guide-llm-evaluation-benchmarks",
    ),
    "Evaluation, Benchmarks & Safety": (
        "guide-llm-evaluation-benchmarks",
        "guide-agent-harness-engineering",
        "guide-cascaded-model-routing",
    ),
    "Coding Agents & DevTools": (
        "guide-agent-harness-engineering",
        "guide-llm-evaluation-benchmarks",
        "guide-cascaded-model-routing",
    ),
    "Frontier Labs & Ecosystem": (
        "guide-cascaded-model-routing",
        "guide-llm-evaluation-benchmarks",
        "guide-llm-inference-quantization",
    ),
}

# Case-insensitive word-boundary patterns for Entity & Lab Momentum
ENTITY_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("OpenAI", re.compile(r"\bopenai\b", re.IGNORECASE)),
    ("Anthropic", re.compile(r"\banthropic\b", re.IGNORECASE)),
    ("Google", re.compile(r"\bgoogle\b", re.IGNORECASE)),
    ("DeepMind", re.compile(r"\bdeepmind\b", re.IGNORECASE)),
    ("NVIDIA", re.compile(r"\bnvidia\b", re.IGNORECASE)),
    ("Gemini", re.compile(r"\bgemini\b", re.IGNORECASE)),
    ("GPT", re.compile(r"\bgpt(?:[-\s]?\d[\w.-]*)?\b", re.IGNORECASE)),
    ("Claude", re.compile(r"\bclaude\b", re.IGNORECASE)),
    ("Mamba", re.compile(r"\bmamba\b", re.IGNORECASE)),
    ("Diffusion", re.compile(r"\bdiffusion\b", re.IGNORECASE)),
    ("MCP", re.compile(r"\bmcp\b", re.IGNORECASE)),
    ("Agents", re.compile(r"\bagents?\b|\bagentic\b", re.IGNORECASE)),
    ("World Model", re.compile(r"\bworld[\s-]+models?\b|\bworld[\s-]+action\b", re.IGNORECASE)),
    ("RL", re.compile(r"\b(?:rl|rlhf|rlvr)\b|\breinforcement\s+learning\b", re.IGNORECASE)),
    ("Quantization", re.compile(r"\bquantiz(?:ation|ed|ing)\b", re.IGNORECASE)),
]

_EMOJI_STRIP_RE = re.compile(r"[🚀⚡🧠📄🏢🛠️🔥🏆🎧🎯✨📅⬆️🎙️🍏📌🌐🎥📺▶️🎬]+\s*")


def _parse_iso_date(date_str: str) -> date | None:
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def _format_date_range(start_str: str, end_str: str) -> str:
    """Format e.g. '2026-11-16'..'2026-11-22' -> 'Nov 16–22', or cross-month 'Nov 30–Dec 6'."""
    d1 = _parse_iso_date(start_str)
    d2 = _parse_iso_date(end_str)
    if not d1 or not d2:
        return f"{start_str}–{end_str}"
    if d1 == d2:
        return f"{d1.strftime('%b')} {d1.day}"
    if d1.year == d2.year and d1.month == d2.month:
        return f"{d1.strftime('%b')} {d1.day}–{d2.day}"
    return f"{d1.strftime('%b')} {d1.day}–{d2.strftime('%b')} {d2.day}"


def normalize_url(url: str) -> str:
    """Strip query, fragment, trailing slash, and www prefix for cross-day deduplication."""
    raw = (url or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        scheme = (parsed.scheme or "https").lower()
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parsed.path.rstrip("/")
        if not netloc:
            return raw.rstrip("/").lower()
        return f"{scheme}://{netloc}{path}"
    except Exception:
        return raw.rstrip("/").lower()


def _title_tokens(title: str) -> Set[str]:
    tokens = re.findall(r"[a-z0-9]+", (title or "").lower())
    return {t for t in tokens if len(t) > 1 or t.isdigit()}


def title_jaccard_similarity(title_a: str, title_b: str) -> float:
    """Compute token Jaccard similarity between two titles."""
    a = _title_tokens(title_a)
    b = _title_tokens(title_b)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _parse_points(raw_points: str | int | None) -> int:
    if isinstance(raw_points, int):
        return max(0, raw_points)
    if not raw_points:
        return 0
    cleaned = re.sub(r"[^0-9]", "", str(raw_points))
    return int(cleaned) if cleaned else 0


def classify_item_cluster(title: str, summary: str = "", source: str = "") -> str:
    """Classify a briefing item into one of 6 deterministic engineering clusters."""
    title_low = (title or "").lower()
    body_low = f"{summary or ''} {source or ''}".lower()

    best_cluster = "Frontier Labs & Ecosystem"
    best_score = 0

    for cluster_name, _short, keywords in WEEKLY_CLUSTERS:
        score = 0
        for kw in keywords:
            if kw in title_low:
                score += 2
            elif kw in body_low:
                score += 1
        if score > best_score:
            best_score = score
            best_cluster = cluster_name

    return best_cluster


def group_qualifying_weeks(
    archive_map: Dict[str, str],
    duplicate_dates: Set[str] | None = None,
    min_days: int = 5,
) -> Dict[str, List[str]]:
    """Group unique daily digest dates by ISO week (`YYYY-WXX`) and retain weeks with `>= min_days` unique issues."""
    dup_set = duplicate_dates or set()
    by_week: Dict[str, List[str]] = {}
    for d_str in sorted(archive_map.keys()):
        if d_str in dup_set:
            continue
        parsed = _parse_iso_date(d_str)
        if not parsed:
            continue
        iso = parsed.isocalendar()
        week_id = f"{iso.year}-W{iso.week:02d}"
        by_week.setdefault(week_id, []).append(d_str)

    return {
        week_id: sorted(dates)
        for week_id, dates in sorted(by_week.items())
        if len(dates) >= min_days
    }


def _select_primary_category(categories: Set[str]) -> str:
    for preferred in ("Lab Release", "Research", "Engineering", "Tech Talk"):
        if preferred in categories:
            return preferred
    return sorted(categories)[0] if categories else "Briefing"


def _source_weight(categories: Set[str]) -> float:
    if "Research" in categories or "Lab Release" in categories:
        return 1.25
    if "Engineering" in categories:
        return 1.15
    return 1.0


def _match_evergreen_guides(cluster_stats: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, str]]:
    """Map the week's top 2–3 clusters to matching Evergreen Guides."""
    guide_by_slug = {g["slug"]: g for g in EVERGREEN_GUIDES}
    selected: List[Dict[str, str]] = []
    seen_slugs: Set[str] = set()

    top_clusters = [c["cluster"] for c in cluster_stats if c["count"] > 0][:3]
    for cluster_name in top_clusters:
        for slug in _CLUSTER_TO_GUIDES.get(cluster_name, ()):
            if slug in guide_by_slug and slug not in seen_slugs:
                seen_slugs.add(slug)
                selected.append(guide_by_slug[slug])
                break
        if len(selected) >= limit:
            break

    # Fill any remaining slots from secondary guide mappings of top clusters, then global order
    if len(selected) < limit:
        for cluster_name in top_clusters:
            for slug in _CLUSTER_TO_GUIDES.get(cluster_name, ()):
                if slug in guide_by_slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    selected.append(guide_by_slug[slug])
                if len(selected) >= limit:
                    break
            if len(selected) >= limit:
                break

    for g in EVERGREEN_GUIDES:
        if len(selected) >= limit:
            break
        if g["slug"] not in seen_slugs:
            seen_slugs.add(g["slug"])
            selected.append(g)

    return selected[:limit]


def analyze_week(
    week_id: str,
    day_items_map: Dict[str, List[Dict[str, str]]],
    prior_week_stats: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Run deterministic cross-day deduplication, cluster classification, WoW deltas, impact ranking, and entity counts."""
    sorted_dates = sorted(day_items_map.keys())
    deduped: List[Dict[str, Any]] = []

    for day_str in sorted_dates:
        for raw_item in day_items_map.get(day_str, []):
            title = (raw_item.get("title") or "").strip()
            url = (raw_item.get("url") or "").strip()
            if not title:
                continue
            norm_u = normalize_url(url)
            pts = _parse_points(raw_item.get("points"))
            src = (raw_item.get("source") or raw_item.get("domain") or "").strip()
            cat = (raw_item.get("category") or "Briefing").strip()
            domain = (raw_item.get("domain") or "").strip()
            hn_url = (raw_item.get("hn_url") or "").strip()
            summary = (raw_item.get("summary") or "").strip()

            matched = None
            for rec in deduped:
                if (norm_u and rec["norm_url"] and norm_u == rec["norm_url"]) or (
                    title_jaccard_similarity(title, rec["title"]) >= 0.72
                ):
                    matched = rec
                    break

            if matched is not None:
                matched["dates_set"].add(day_str)
                if pts > matched["peak_points"]:
                    matched["peak_points"] = pts
                if src:
                    matched["sources_set"].add(src)
                if cat:
                    matched["categories_set"].add(cat)
                if hn_url and not matched["hn_url"]:
                    matched["hn_url"] = hn_url
                if summary and not matched["_classify_summary"]:
                    matched["_classify_summary"] = summary
            else:
                deduped.append(
                    {
                        "title": title,
                        "url": url,
                        "norm_url": norm_u,
                        "domain": domain,
                        "hn_url": hn_url,
                        "dates_set": {day_str},
                        "peak_points": pts,
                        "sources_set": {src} if src else set(),
                        "categories_set": {cat} if cat else set(),
                        "_classify_summary": summary,
                    }
                )

    # Finalize deduplicated records, classify clusters, compute Weekly Impact Score
    cluster_counts: Dict[str, int] = {name: 0 for name, _, _ in WEEKLY_CLUSTERS}
    category_counts: Dict[str, int] = {}
    final_items: List[Dict[str, Any]] = []

    for rec in deduped:
        dates_list = sorted(rec["dates_set"])
        days_featured = len(dates_list)
        first_date = dates_list[0]
        sources_list = sorted(rec["sources_set"])
        categories_set = rec["categories_set"]
        primary_cat = _select_primary_category(categories_set)
        cluster = classify_item_cluster(
            rec["title"],
            summary=rec["_classify_summary"],
            source=" ".join(sources_list),
        )
        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
        category_counts[primary_cat] = category_counts.get(primary_cat, 0) + 1

        sw = _source_weight(categories_set)
        cross_source_bonus = 2.0 if (len(sources_list) > 1 or len(categories_set) > 1) else 0.0
        multi_day_bonus = 1.5 * (days_featured - 1)
        impact_score = round(math.log1p(rec["peak_points"]) * sw + cross_source_bonus + multi_day_bonus, 2)

        final_items.append(
            {
                "title": rec["title"],
                "url": rec["url"],
                "domain": rec["domain"],
                "hn_url": rec["hn_url"],
                "dates": dates_list,
                "first_date": first_date,
                "days_featured": days_featured,
                "peak_points": rec["peak_points"],
                "sources": sources_list,
                "source_label": " + ".join(sources_list) if sources_list else (rec["domain"] or "Primary Source"),
                "category": primary_cat,
                "cluster": cluster,
                "impact_score": impact_score,
            }
        )

    total_items = len(final_items)

    # Prior week shares for WoW delta computation
    prior_shares: Dict[str, float] | None = None
    if prior_week_stats and prior_week_stats.get("cluster_stats"):
        prior_shares = {
            row["cluster"]: float(row["share"])
            for row in prior_week_stats["cluster_stats"]
        }

    cluster_stats: List[Dict[str, Any]] = []
    for idx, (cluster_name, short_label, _kws) in enumerate(WEEKLY_CLUSTERS):
        cnt = cluster_counts.get(cluster_name, 0)
        share = round((cnt / total_items) * 100.0, 1) if total_items > 0 else 0.0
        if prior_shares is None:
            delta = None
            delta_label = "Baseline"
        else:
            prev_share = prior_shares.get(cluster_name, 0.0)
            delta = round(share - prev_share, 1)
            delta_int = int(round(delta))
            if delta_int > 0:
                delta_label = f"+{delta_int}%"
            elif delta_int < 0:
                delta_label = f"{delta_int}%"
            else:
                delta_label = "0%"
        cluster_stats.append(
            {
                "cluster": cluster_name,
                "short_label": short_label,
                "count": cnt,
                "share": share,
                "delta": delta,
                "delta_label": delta_label,
                "_order": idx,
            }
        )

    cluster_stats.sort(key=lambda r: (-r["count"], r["_order"]))
    for row in cluster_stats:
        row.pop("_order", None)

    # Rank Top 5 Pivotal Developments by Weekly Impact Score
    ranked_items = sorted(
        final_items,
        key=lambda it: (
            -it["impact_score"],
            -it["peak_points"],
            -it["days_featured"],
            it["first_date"],
            it["title"],
        ),
    )
    top5 = ranked_items[:5]

    # Entity & Lab Momentum (top 8 active entities with word-boundary counts across titles/sources)
    entity_counts: List[Dict[str, Any]] = []
    for entity_name, pattern in ENTITY_PATTERNS:
        hits = 0
        for it in final_items:
            haystack = f"{it['title']} {' '.join(it['sources'])}"
            if pattern.search(haystack):
                hits += 1
        if hits > 0:
            entity_counts.append({"entity": entity_name, "count": hits})
    entity_counts.sort(key=lambda e: (-e["count"], e["entity"]))
    top_entities = entity_counts[:8]

    # Related Evergreen Guides (3 matched guides)
    related_guides = _match_evergreen_guides(cluster_stats, limit=3)

    # Parse ISO year & week number
    m_week = re.match(r"^(\d{4})-W(\d{2})$", week_id)
    iso_year = int(m_week.group(1)) if m_week else (datetime.now().year)
    iso_week = int(m_week.group(2)) if m_week else 1

    start_date = sorted_dates[0] if sorted_dates else ""
    end_date = sorted_dates[-1] if sorted_dates else ""
    date_range_label = _format_date_range(start_date, end_date) if start_date and end_date else week_id

    dominant_cluster = cluster_stats[0] if cluster_stats else {
        "cluster": "Frontier Labs & Ecosystem",
        "short_label": "Frontier Labs",
        "count": 0,
        "share": 0.0,
        "delta": None,
        "delta_label": "Baseline",
    }

    return {
        "week_id": week_id,
        "iso_year": iso_year,
        "iso_week": iso_week,
        "dates": sorted_dates,
        "days_count": len(sorted_dates),
        "start_date": start_date,
        "end_date": end_date,
        "date_range_label": date_range_label,
        "total_items": total_items,
        "category_counts": category_counts,
        "cluster_stats": cluster_stats,
        "dominant_cluster": dominant_cluster,
        "top5": top5,
        "entity_momentum": top_entities,
        "related_guides": related_guides,
        "has_prior_week": prior_shares is not None,
    }


def build_deterministic_weekly_essay(week_stats: Dict[str, Any]) -> str:
    """Build a crisp, 3-paragraph deterministic analytical synthesis grounded strictly in computed week_stats."""
    iso_week = week_stats["iso_week"]
    iso_year = week_stats["iso_year"]
    date_range = week_stats["date_range_label"]
    days_count = week_stats["days_count"]
    total_items = week_stats["total_items"]
    clusters = week_stats.get("cluster_stats", [])
    top5 = week_stats.get("top5", [])
    entities = week_stats.get("entity_momentum", [])
    cat_counts = week_stats.get("category_counts", {})

    c1 = clusters[0] if len(clusters) > 0 else {"cluster": "Frontier Labs & Ecosystem", "count": 0, "share": 0.0, "delta": None, "delta_label": "Baseline"}
    c2 = clusters[1] if len(clusters) > 1 else {"cluster": "Agentic Systems & Tool Use", "count": 0, "share": 0.0, "delta": None, "delta_label": "Baseline"}

    # Paragraph 1: Macro distribution & WoW shifts
    if week_stats.get("has_prior_week"):
        non_null_deltas = [c for c in clusters if c.get("delta") is not None]
        biggest_gain = max(non_null_deltas, key=lambda c: c["delta"]) if non_null_deltas else None
        biggest_drop = min(non_null_deltas, key=lambda c: c["delta"]) if non_null_deltas else None
        shift_clauses: List[str] = []
        if biggest_gain and biggest_gain["delta"] > 0:
            shift_clauses.append(f"{biggest_gain['cluster']} expanded by {biggest_gain['delta_label']}")
        if biggest_drop and biggest_drop["delta"] < 0:
            shift_clauses.append(f"{biggest_drop['cluster']} contracted by {biggest_drop['delta_label']}")
        if shift_clauses:
            shift_sentence = f" Compared against the prior week, {' while '.join(shift_clauses)}."
        else:
            shift_sentence = " Cluster shares held steady relative to the prior week with no major structural reallocation."
    else:
        shift_sentence = " As the initial qualifying archive week, these shares establish the baseline distribution for subsequent week-over-week tracking."

    p1 = (
        f"Across {days_count} daily editions during Week {iso_week}, {iso_year} ({date_range}), "
        f"The GenAI Briefing indexed {total_items} deduplicated technical developments. "
        f"{c1['cluster']} led the weekly ledger with {c1['count']} items ({c1['share']:.1f}% share), "
        f"followed by {c2['cluster']} at {c2['count']} items ({c2['share']:.1f}% share).{shift_sentence}"
    )

    # Paragraph 2: Source mix & top velocity leaders
    mix_bits = [
        f"{cnt} {cat}"
        for cat, cnt in sorted(cat_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    mix_phrase = ", ".join(mix_bits) if mix_bits else f"{total_items} technical entries"

    multi_day_count = sum(1 for it in top5 if it.get("days_featured", 1) > 1)
    if len(top5) >= 2:
        t1, t2 = top5[0], top5[1]
        t1_pts = f"{t1['peak_points']:,} points" if t1["peak_points"] > 0 else "editorial selection"
        t2_pts = f"{t2['peak_points']:,} points" if t2["peak_points"] > 0 else "editorial selection"
        persistence_note = (
            f" {multi_day_count} of the top five developments persisted across multiple daily editions, confirming sustained practitioner attention."
            if multi_day_count > 0
            else " Community signal concentrated in sharp single-day releases rather than multi-day carryovers, indicating rapid daily turnover."
        )
        p2 = (
            f"The weekly source mix comprised {mix_phrase}. "
            f"Velocity leadership was anchored by \"{t1['title']}\" ({t1['cluster']}, {t1_pts}, first indexed {t1['first_date']}) "
            f"and \"{t2['title']}\" ({t2['cluster']}, {t2_pts}, {t2['first_date']}).{persistence_note}"
        )
    elif len(top5) == 1:
        t1 = top5[0]
        p2 = (
            f"The weekly source mix comprised {mix_phrase}, led by \"{t1['title']}\" "
            f"in {t1['cluster']} (first indexed {t1['first_date']})."
        )
    else:
        p2 = f"The weekly source mix comprised {mix_phrase} across primary research and engineering channels."

    # Paragraph 3: Entity momentum & engineering takeaway
    if entities:
        ent_phrase = ", ".join(f"{e['entity']} ({e['count']})" for e in entities[:4])
        entity_sentence = f"Entity and technical-concept tracking showed the highest recurring activity around {ent_phrase}."
    else:
        entity_sentence = "Activity was distributed broadly across independent research labs and open-source contributors without single-vendor concentration."

    takeaway = _CLUSTER_ENGINEERING_TAKEAWAY.get(
        c1["cluster"],
        "Verify benchmark gains against private execution-based regression suites before updating production model routing.",
    )
    p3 = f"{entity_sentence} {takeaway}"

    return f"{p1}\n\n{p2}\n\n{p3}"


def _build_weekly_gemini_prompt(week_stats: Dict[str, Any]) -> str:
    clusters_lines = "\n".join(
        f"- {c['cluster']}: {c['count']} items ({c['share']:.1f}%, WoW delta: {c['delta_label']})"
        for c in week_stats.get("cluster_stats", [])
    )
    top5_lines = "\n".join(
        f"{idx}. {it['title']} | Cluster: {it['cluster']} | Category: {it['category']} | Source: {it['source_label']} | Peak Points: {it['peak_points']} | Days Featured: {it['days_featured']} | First Date: {it['first_date']}"
        for idx, it in enumerate(week_stats.get("top5", []), start=1)
    )
    entity_lines = ", ".join(
        f"{e['entity']} ({e['count']})"
        for e in week_stats.get("entity_momentum", [])
    ) or "None concentrated"

    return (
        f"Write a tight, emoji-free 250–350 word analytical essay (exactly 3 short paragraphs, plain prose without headings or bullet lists) "
        f"for The GenAI Briefing (jabi.io) synthesizing Week {week_stats['iso_week']}, {week_stats['iso_year']} ({week_stats['date_range_label']}).\n\n"
        f"Rules:\n"
        f"1. Ground every claim strictly in the computed numbers and titles below. Do NOT invent metrics, quotes, or claims.\n"
        f"2. Zero emojis, zero marketing hype, zero filler phrases ('In the fast-paced world of AI...', 'game-changing', 'revolutionary').\n"
        f"3. Paragraph 1: Macro theme distribution and week-over-week shifts.\n"
        f"4. Paragraph 2: What the Top 5 pivotal developments signal technically for ML engineers.\n"
        f"5. Paragraph 3: Entity/lab momentum and concrete production engineering takeaway.\n\n"
        f"Computed Week Statistics:\n"
        f"- Week ID: {week_stats['week_id']} ({week_stats['start_date']} to {week_stats['end_date']}, {week_stats['days_count']} unique daily issues)\n"
        f"- Total Deduplicated Items: {week_stats['total_items']}\n"
        f"- Category Breakdown: {week_stats.get('category_counts', {})}\n"
        f"- Cluster Distribution:\n{clusters_lines}\n"
        f"- Top 5 Pivotal Developments:\n{top5_lines}\n"
        f"- Top Active Entities: {entity_lines}\n"
    )


def load_or_generate_weekly_essay(
    week_stats: Dict[str, Any],
    weekly_dir: Path,
    allow_gemini: bool = False,
) -> str:
    """Load cached `digests/weekly/{week_id}.md`, optionally generate once via Gemini, or fall back deterministically."""
    week_id = week_stats["week_id"]
    cache_path = weekly_dir / f"{week_id}.md"

    if cache_path.exists():
        cached = cache_path.read_text(encoding="utf-8").strip()
        if cached:
            return _EMOJI_STRIP_RE.sub("", cached).strip()

    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    if allow_gemini and api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)
            prompt = _build_weekly_gemini_prompt(week_stats)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "You are the Chief Editor of The GenAI Briefing (jabi.io). "
                        "Write crisp, high-density technical analysis in the style of Anthropic Research notes and Distill.pub. "
                        "Never use emojis, hype, or unsupported statistics."
                    ),
                    temperature=0.25,
                ),
            )
            generated = _EMOJI_STRIP_RE.sub("", (response.text or "").strip()).strip()
            if generated and len(generated.split()) >= 80:
                weekly_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(generated + "\n", encoding="utf-8")
                return generated
        except Exception as exc:
            logger.warning("Gemini weekly essay generation failed for %s (%s); using deterministic synthesis.", week_id, exc)

    return build_deterministic_weekly_essay(week_stats)


def build_weekly_reports(
    archive_map: Dict[str, str],
    duplicate_dates: Set[str],
    parse_items_fn: Callable[[str], List[Dict[str, str]]],
    weekly_dir: Path,
    allow_gemini: bool = False,
    min_days: int = 5,
) -> List[Dict[str, Any]]:
    """Compute all qualifying weekly synthesis reports in chronological order, attaching essays and WoW deltas."""
    qualifying = group_qualifying_weeks(
        archive_map=archive_map,
        duplicate_dates=duplicate_dates,
        min_days=min_days,
    )
    reports: List[Dict[str, Any]] = []
    prior_stats: Dict[str, Any] | None = None

    for week_id, dates in qualifying.items():
        day_items_map = {
            d: parse_items_fn(archive_map[d])
            for d in dates
            if d in archive_map
        }
        stats = analyze_week(
            week_id=week_id,
            day_items_map=day_items_map,
            prior_week_stats=prior_stats,
        )
        stats["essay_markdown"] = load_or_generate_weekly_essay(
            week_stats=stats,
            weekly_dir=weekly_dir,
            allow_gemini=allow_gemini,
        )
        reports.append(stats)
        prior_stats = stats

    return reports
