---
name: editorial-team-workflow
description: >-
  Engineering organization workflow (Product Manager -> Staff Engineer -> QA/Test Engineer
  -> Security Engineer) for The GenAI Briefing. Activate this skill whenever implementing
  new features, sources, UI/readability improvements, or automated releases.
---

# Engineering Org Pipeline (`PM → Staff Eng → QA → Security`)

Use this multi-agent engineering workflow to take any user request from product specification through implementation, automated testing, security review, and deployment without manual file-by-file prompts.

## Pipeline Architecture

```text
[1. product-manager]
    │  Defines acceptance criteria, UX/readability spec & file tasks
    ▼
[2. staff-engineer]
    │  Implements Python backend (src/genai_agent/) & Editorial HTML/CSS (docs/)
    ▼
[3. qa-test-engineer]
    │  Writes/runs .venv/bin/pytest -q & validates rendered docs/*.html
    ▼
[4. security-engineer]
    │  Audits git diff for secrets, XSS/HTML sanitization & pushes to origin/main
```

## Subagent Definitions (via `define_subagent` / `invoke_subagent`)

### Stage 1: `product-manager` (Read-Only Spec)
- **EnableWriteTools**: `false`
- **Deliverable**: Scoped Product & UX Spec (acceptance criteria, Mobile Safari & `66ch` readability constraints, and exact file targets).

### Stage 2: `staff-engineer` (Implementation)
- **EnableWriteTools**: `true`
- **Deliverable**: Code changes in `src/genai_agent/` (`agent.py`, `collectors/`, `notifiers/markdown_store.py`) and regenerated `docs/`.

### Stage 3: `qa-test-engineer` (Testing & Verification)
- **EnableWriteTools**: `true`
- **Deliverable**: Passing unit tests in `tests/test_agent.py` (`.venv/bin/pytest -q`) and verified HTML output in `docs/`.

### Stage 4: `security-engineer` (Security Gate & Release)
- **EnableWriteTools**: `true`
- **Deliverable**:
  1. Secret scan (`git status -s`, `git diff` — zero `.env` or API keys).
  2. Input sanitization check on external RSS/HTML feeds (`target="_blank" rel="noopener"`, stripped raw HTML tags).
  3. Final commit & push (`git pull --rebase origin main && git push origin main`).
