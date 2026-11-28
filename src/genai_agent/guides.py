from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple


def _resolve_default_guides_dir() -> Path:
    """Resolve `content/guides` reliably in local dev, editable installs, and non-editable `pip install .` CI runs."""
    env_dir = (os.getenv("GENAI_GUIDES_DIR") or "").strip()
    if env_dir:
        candidate = Path(env_dir)
        if candidate.is_dir():
            return candidate

    candidates: List[Path] = []

    # 1. Repository root relative to source file (`src/genai_agent/guides.py` -> `../../content/guides`)
    src_root = Path(__file__).resolve().parents[2] / "content" / "guides"
    candidates.append(src_root)

    # 2. Current working directory and ancestors (handles `pip install .` in GitHub Actions)
    cwd = Path.cwd().resolve()
    candidates.append(cwd / "content" / "guides")
    for parent in cwd.parents:
        candidates.append(parent / "content" / "guides")

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    return src_root


def _parse_frontmatter(raw_text: str) -> Tuple[Dict[str, str], str]:
    """Parse simple YAML-style `key: value` frontmatter delimited by `---` using Python stdlib only."""
    text = raw_text.lstrip("\ufeff")
    if not text.startswith("---"):
        return {}, text.strip()

    lines = text.splitlines()
    end_idx = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break

    if end_idx is None:
        return {}, text.strip()

    meta: Dict[str, str] = {}
    for line in lines[1:end_idx]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, val = stripped.split(":", 1)
        key = key.strip().lower()
        val = val.strip()
        if len(val) >= 2 and ((val[0] == val[-1] == '"') or (val[0] == val[-1] == "'")):
            val = val[1:-1]
        meta[key] = val

    body = "\n".join(lines[end_idx + 1 :]).strip() + "\n"
    return meta, body


def _parse_sections(body_markdown: str) -> List[Tuple[str, List[str]]]:
    """Split Markdown body on `## ` headings into `(heading, blocks)` tuples."""
    sections: List[Tuple[str, List[str]]] = []
    current_heading: str | None = None
    current_lines: List[str] = []

    def _flush() -> None:
        if current_heading is None:
            return
        raw_block = "\n".join(current_lines).strip()
        blocks = [b.strip() for b in re.split(r"\n\s*\n", raw_block) if b.strip()]
        sections.append((current_heading, blocks))

    for line in body_markdown.splitlines():
        if line.startswith("## ") and not line.startswith("### "):
            _flush()
            current_heading = line[3:].strip()
            current_lines = []
        else:
            if current_heading is not None:
                current_lines.append(line)

    _flush()
    return sections


def _parse_keywords(raw: str) -> List[str]:
    if not raw:
        return []
    cleaned = raw.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    out: List[str] = []
    for part in cleaned.split(","):
        tok = part.strip().strip('"').strip("'").strip()
        if tok:
            out.append(tok)
    return out


def load_evergreen_guides(guides_dir: Path | None = None) -> List[Dict[str, Any]]:
    """Load and sort Evergreen Engineering Guides from `content/guides/*.md`."""
    target_dir = Path(guides_dir) if guides_dir is not None else _resolve_default_guides_dir()
    if not target_dir.is_dir():
        return []

    guides: List[Dict[str, Any]] = []
    for md_path in sorted(target_dir.glob("*.md")):
        raw = md_path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        slug = (meta.get("slug") or md_path.stem).strip()
        try:
            order = int((meta.get("order") or "999").strip())
        except ValueError:
            order = 999

        updated = (meta.get("updated_at") or meta.get("updated") or "2026-11-28").strip()
        title = (meta.get("title") or slug).strip()
        subtitle = (meta.get("subtitle") or meta.get("description") or "").strip()
        kicker = (meta.get("kicker") or "ENGINEERING GUIDE").strip()
        reading_time = (meta.get("reading_time") or "7 min read").strip()
        description = (meta.get("description") or subtitle).strip()
        keywords = _parse_keywords(meta.get("keywords") or "")
        sections = _parse_sections(body)

        guides.append(
            {
                "slug": slug,
                "order": order,
                "title": title,
                "subtitle": subtitle,
                "kicker": kicker,
                "reading_time": reading_time,
                "updated_at": updated,
                "updated": updated,
                "description": description,
                "keywords": keywords,
                "body_markdown": body,
                "sections": sections,
            }
        )

    guides.sort(key=lambda g: (int(g.get("order", 999)), str(g.get("slug", ""))))
    return guides


EVERGREEN_GUIDES: List[Dict[str, Any]] = load_evergreen_guides()
