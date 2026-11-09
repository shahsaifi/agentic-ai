---
name: editorial-team-workflow
description: >-
  Multi-agent team workflow for The GenAI Briefing. Use this skill whenever the user asks
  to add new AI sources, improve synthesis quality, redesign or polish the GitHub Pages
  frontend (docs/), optimize Mobile Safari readability, or run an end-to-end update using
  specialized subagents.
---

# GenAI Briefing Multi-Agent Team Workflow

This workspace uses a 4-agent team workflow to evolve and maintain **The GenAI Briefing** (`https://shahsaifi.github.io/agentic-ai/`).

## Team Roster (Define via `define_subagent` & Invoke via `invoke_subagent`)

1. **`source-curator`** (*GenAI Source & Feed Curator*)
   - **Scope**: `src/genai_agent/collectors/` (`papers.py`, `blogs.py`, `community.py`, `social_x.py`, `podcasts.py`, `web_search.py`).
   - **Role**: Adds/updates feeds, ensures 200 OK RSS/API reliability on GitHub Actions, and strips raw HTML/scraper boilerplate.

2. **`synthesis-editor`** (*Technical Synthesis & Anti-Slop Editor*)
   - **Scope**: `src/genai_agent/agent.py`, `digests/`.
   - **Role**: Maintains `rank_top_items`, `exclude_previously_published_items`, Gemini prompt instructions, and full-sentence excerpt truncation.

3. **`editorial-designer`** (*Swiss Editorial & Mobile Safari Frontend Engineer*)
   - **Scope**: `src/genai_agent/notifiers/markdown_store.py`, `docs/`.
   - **Role**: Maintains the FT / Anthropic / Stripe Press editorial aesthetic (`66ch` measure, high-contrast Paper/Sepia/Ink themes, 3-tier item layout, category filter bar, per-topic Reddit links, and iPhone Mobile Safari support).

4. **`qa-release-verifier`** (*Test & GitHub Pages Release Engineer*)
   - **Scope**: `tests/test_agent.py`, git workflow, and GitHub Pages verification.
   - **Role**: Runs `.venv/bin/pytest -q`, rebuilds `docs/` from `digests/`, ensures zero secrets are staged, and pushes to `origin main`.

## Standard Execution Pipeline

1. **Parallel Implementation**: Spawn `source-curator`, `synthesis-editor`, and/or `editorial-designer` via `invoke_subagent` depending on which layers the user request touches.
2. **Verification & Release**: Once implementation subagents complete, run or delegate to `qa-release-verifier` to execute:
   ```bash
   .venv/bin/pytest -q
   .venv/bin/python -c "from pathlib import Path; from genai_agent.notifiers import save_markdown_digest; out=Path('digests'); save_markdown_digest((out/'latest.md').read_text(), out)"
   ```
3. **Commit & Push**: Verify `git status -s` contains zero `.env` or secret files, then `git pull --rebase origin main && git push origin main`.
