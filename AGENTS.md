# Engineering Organization & Multi-Agent Workflow (`AGENTS.md`)

For non-trivial feature requests, UI/readability improvements, or collector additions in this repository, orchestrate work through the 4-stage Engineering Organization pipeline (defined in `.agents/skills/editorial-team-workflow/SKILL.md`):

1. **`product-manager`** (`EnableWriteTools=false`): Scopes requirements, UX/editorial standards (Swiss/Editorial layout, `66ch` measure, iPhone Mobile Safari `viewport-fit=cover`, zero emoji/boilerplate slop), and acceptance criteria.
2. **`staff-engineer`** (`EnableWriteTools=true`): Implements changes across `src/genai_agent/` and regenerates `docs/`.
3. **`qa-test-engineer`** (`EnableWriteTools=true`): Updates `tests/test_agent.py`, runs `.venv/bin/pytest -q`, and verifies rendered HTML in `docs/`.
4. **`security-engineer`** (`EnableWriteTools=true`): Audits `git diff` and `git status -s` for secrets/keys, checks RSS/HTML sanitization (`rel="noopener"`, HTML unescaping/stripping), and pushes to `origin main`.

## Workspace Guardrails
- **Never commit `.env` or API keys** to git.
- **Auto-Accept Edits**: Configured in `.agents/settings.json` (`"agentMode": "accept-edits"`). When launching the CLI, run `agy --mode=accept-edits` (or `agy --mode=auto`) so the entire `PM → Staff Engineer → QA → Security` pipeline executes without manual file-save prompts.
