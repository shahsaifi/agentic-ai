from __future__ import annotations

from typing import Dict, List

EVERGREEN_GUIDES: List[Dict[str, str]] = [
    {
        "slug": "guide-agent-harness-engineering",
        "title": "Agent Harness Engineering: Tool Loops, Sandboxing, and Deterministic Verification",
        "subtitle": "Why production reliability in autonomous coding and research agents depends on the runtime harness around the weights rather than prompt phrasing alone.",
        "kicker": "SYSTEMS ARCHITECTURE",
        "reading_time": "7 min read",
        "updated_at": "2026-11-28",
        "description": "Engineering guide to building reliable AI agent harnesses: bounded tool loops, context compaction, least-privilege sandboxing, and deterministic verification.",
        "body_markdown": """## Why the Harness Dominates Agent Reliability

A frontier language model is a stateless next-token predictor. On its own, it cannot inspect a repository, execute a test suite, recover from a broken build, or verify that a configuration change did not introduce a security regression. Every capability that turns a model into an autonomous engineering system lives in the **agent harness**: the orchestration loop, tool schemas, state management layer, execution sandbox, and verification gates surrounding the model.

In production evaluations across software engineering benchmarks and internal enterprise repositories, teams routinely observe that changing the harness produces larger accuracy and latency improvements than swapping between comparable frontier checkpoints. Different harnesses fail on different tasks because tool feedback formatting, retry policies, and context compaction directly govern what evidence remains visible inside the model's attention window on turn ten or turn thirty.

## Anatomy of a Production Tool Loop

A minimal chat completion loop (`while tool_call: execute()`) breaks down rapidly on multi-step engineering tasks. A production harness structures the loop into explicit, observable phases:

1. **Bounded Step Budget and Termination Conditions**: Every run requires a hard ceiling on tool invocations, wall-clock duration, and cumulative token spend. Without explicit termination rules, models enter repetitive edit-test-fail cycles when an environment dependency is missing or a test assertion is flaky.
2. **Structured Tool Schemas with Narrow Affordances**: Overloaded tools with twenty optional parameters invite schema hallucinations. Prefer small, composable primitives (`read_file` with line ranges, `edit_file` with exact target matching, `run_command` with explicit timeouts) whose error messages tell the model exactly how to recover.
3. **Idempotent Observation Formatting**: Raw terminal output frequently dumps thousands of lines of compiler noise or stack traces. The harness should truncate middle sections, preserve the exit code, head, and tail of `stderr`, and attach byte or line counts so the model knows when output was truncated.
4. **Explicit Planning and Checkpoint State**: For long-horizon tasks spanning more than ten tool calls, persisting a structured task ledger outside the conversational history prevents goal drift. When older tool outputs are compacted, the active plan and verified invariants remain pinned near the top of the context.

### Handling Partial Failures and Retry Policies

Not all tool errors are equal. A syntax error in a generated patch is recoverable by the model; an HTTP 429 rate limit or transient DNS failure is an infrastructure fault that should be retried by the harness with exponential backoff before exposing anything to the model. Distinguishing **infrastructure errors** from **semantic task errors** avoids polluting the conversation trace with noise that confuses the model into rewriting valid code.

## Context Compaction and Working-Memory Hygiene

Long-running coding agents accumulate tens of thousands of tokens of file reads, search hits, and build logs. Even when a model advertises a 200K or 1M token window, attention degradation and quadratic prefill latency make unbounded history expensive and brittle.

Effective harnesses treat context as managed memory rather than an append-only log:

- **Read-Once Eviction**: Replace superseded file reads with a short tombstone (`[Previously read src/auth.py lines 1-200; file was subsequently edited]`) once the file is modified.
- **Deterministic Diff Summaries**: When summarizing completed subtasks, preserve exact file paths, symbol names, command exit codes, and failing assertion messages verbatim. Lossy prose summaries cause agents to re-introduce bugs they already fixed.
- **Sub-Agent Isolation**: Delegate noisy exploratory work—such as searching across fifty files or triaging a large log directory—to a scoped sub-agent that returns only a compact, verified list of findings to the parent orchestrator.

## Least-Privilege Sandboxing and Security Boundaries

Giving an LLM shell access or outbound network privileges turns prompt injection into remote code execution. Any external document, web page, dependency README, or issue comment fetched during a run must be treated as untrusted input.

### Core Isolation Controls

- **Ephemeral Rootless Containers or MicroVMs**: Execute all shell commands inside disposable containers with dropped Linux capabilities, read-only root filesystems where possible, and explicit CPU, memory, and disk quotas.
- **Deny-by-Default Egress**: Block outbound network traffic from the execution sandbox except for an explicit allowlist of package registries or internal proxies. Never pass host environment secrets, cloud credentials, or `.env` files into the agent's shell environment.
- **Scoped Credential Brokering**: If the agent must open a pull request or query an internal API, broker the request through a host-side proxy that validates the target repository, branch, and payload rather than handing raw API tokens to the sandbox.
- **Human-in-the-Loop Approval Gates**: Classify tools by blast radius. Read-only inspection and local test execution can run autonomously; destructive file operations, database migrations, dependency upgrades, and external writes should require explicit human approval or deterministic policy checks.

## Deterministic Verification Before Completion

The single highest-leverage improvement in agent harness engineering is separating **generation** from **verification**. Language models are notoriously overconfident when asked whether their own patch is complete.

Instead of trusting self-assessment, wire deterministic verifiers directly into the harness exit gate:

1. **Static Analysis and Type Checking**: Run linters, formatters, and strict type checkers (`mypy`, `pyright`, `tsc`, `cargo check`) automatically after edits.
2. **Targeted and Regression Test Suites**: Require unit and integration tests to pass with exit code zero before the agent can declare success.
3. **Secret and Diff Hygiene Scans**: Inspect `git diff` and `git status` programmatically to verify that no credentials, unintended lockfile churn, or debug artifacts were introduced.
4. **Artifact Contract Checks**: For data or documentation pipelines, validate output schemas, broken links, and word-count or formatting constraints via deterministic scripts.

## Production Readiness Checklist

- [ ] Hard limits configured for max turns, max wall-clock time, and max token budget per run.
- [ ] Tool outputs truncated deterministically with exit codes and truncation notices preserved.
- [ ] Infrastructure retries handled outside the model context; semantic errors returned cleanly.
- [ ] Shell execution isolated in an ephemeral container or microVM with deny-by-default egress.
- [ ] Secrets and `.env` files excluded from the agent filesystem and environment variables.
- [ ] Deterministic verification gates (tests, linters, diff checks) enforced prior to task completion.
- [ ] Full structured telemetry logged for every turn: latency, token usage, tool arguments, and exit status.
""",
    },
    {
        "slug": "guide-llm-inference-quantization",
        "title": "Production LLM Inference & Quantization: KV-Cache Economics, Low-Bit Calibration, and Decoding Latency",
        "subtitle": "A systems breakdown of memory-bandwidth bottlenecks, continuous batching, low-bit quantization failure modes, and speculative decoding for production serving.",
        "kicker": "INFERENCE SYSTEMS",
        "reading_time": "7 min read",
        "updated_at": "2026-11-28",
        "description": "Deep dive into production LLM inference and quantization: prefill vs decode bottlenecks, KV-cache memory math, W4A16/FP8/W4A4 trade-offs, and speculative decoding.",
        "body_markdown": """## The Two Regimes of LLM Serving: Prefill vs. Decode

Optimizing Large Language Model inference begins with recognizing that a single request passes through two fundamentally different hardware regimes:

1. **Prefill (Compute-Bound)**: The entire input prompt is processed in parallel through dense matrix-matrix multiplications (GEMMs). Throughput scales with tensor-core FLOPs, and latency is governed by Time to First Token (TTFT).
2. **Decode (Memory-Bandwidth-Bound)**: Output tokens are generated autoregressively one step at a time. At low batch sizes, each step loads the entire model's weights and the growing Key-Value (KV) cache from HBM into on-chip SRAM just to compute a matrix-vector product. Latency is governed by Time Per Output Token (TPOT) and hardware memory bandwidth rather than peak FLOPs.

Conflating these two phases leads to poor cluster provisioning. Adding more compute without addressing memory bandwidth or KV-cache fragmentation barely moves decode latency, while large unchunked prefills stall co-located decode batches and cause severe p99 tail latency spikes.

## KV-Cache Economics and Memory Management

For long-context workloads and multi-turn agents, the KV cache—not model weights—often becomes the primary memory bottleneck. For a standard transformer using Grouped-Query Attention (GQA), the memory footprint per token scales linearly with layer count, KV head count, head dimension, and precision:

- At FP16/BF16, a 70B-class model with 8 KV heads can consume hundreds of megabytes per active 32K-token conversation.
- Multiply that across dozens of concurrent users, and VRAM saturates long before GPU compute utilization reaches fifty percent.

### Essential Memory Optimizations

- **PagedAttention and Block Allocation**: Traditional contiguous tensor allocation wastes substantial VRAM to internal and external fragmentation. Paged KV caches allocate fixed-size token blocks on demand, enabling near-zero waste and higher effective batch sizes.
- **Prefix Caching (Automatic KV Reuse)**: Agentic workloads and RAG pipelines repeatedly send identical system prompts, tool schemas, and retrieved documents. Content-addressed prefix caching hashes leading token blocks and reuses precomputed KV states across turns and concurrent requests, cutting TTFT by 50–85% on multi-turn loops.
- **Chunked Prefill and Disaggregated Serving**: Splitting long prefills into bounded chunks prevents a single 64K-token prompt from blocking decode tokens for other users. At high scale, separating prefill workers from decode workers allows each pool to optimize independently for TTFT and TPOT.
- **FP8 and INT8 KV-Cache Quantization**: Compressing cached keys and values from BF16 to FP8 roughly doubles effective batch capacity with negligible perplexity degradation when per-head or per-tensor scaling factors are calibrated properly.

## Low-Bit Quantization: Where Accuracy Actually Breaks

Quantizing model weights reduces memory footprint and directly accelerates bandwidth-bound decode. However, not all quantization schemes behave equally across tasks:

| Scheme | Primary Benefit | Typical Production Trade-Off |
| :--- | :--- | :--- |
| **FP8 (W8A8)** | Native Hopper/Blackwell tensor core speedups for both prefill and decode | Minimal accuracy loss (<0.5% on most evals); strong default for datacenter serving |
| **W4A16 (AWQ / GPTQ)** | ~3.5x weight memory reduction and faster low-batch decode | Small perplexity drift; sensitive to calibration set distribution |
| **W4A4 / NVFP4** | Maximum throughput and edge-device fit | Significant risk on structured tool calls, math, and multi-step reasoning without closed-loop distillation |

### Failure Modes in Quantized Agents

Standard perplexity benchmarks (such as WikiText-2) routinely mask catastrophic failures in production agents. In multi-turn tool calling, small logit perturbations caused by aggressive 4-bit activation quantization can flip a single JSON delimiter, hallucinate a parameter name, or prematurely emit an end-of-turn token.

To mitigate quantization drift:

1. **Calibrate on Domain-Representative Traces**: Never calibrate AWQ or GPTQ solely on generic web prose if your deployment serves code, SQL, or nested JSON tool schemas. Include real production prompts and multi-turn trajectories in the calibration dataset.
2. **Protect Sensitive Layers**: Keep embeddings, `lm_head`, and attention output projections in higher precision (BF16 or FP8) when quantizing MLP blocks to 4 bits.
3. **Evaluate End-to-End Task Success**: Always benchmark quantized checkpoints on your exact JSON schema compliance rate, coding pass@1, and refusal calibration—not just perplexity.

## Speculative Decoding and Continuous Batching

Once memory bandwidth is saturated, **speculative decoding** breaks the one-token-per-weight-load barrier. A lightweight draft model (or multi-token prediction head such as Eagle/Medusa) proposes *k* candidate tokens cheaply, and the target model verifies all *k* tokens in a single parallel forward pass. Because verification uses the exact target distribution via rejection sampling, speculative decoding is mathematically lossless.

Speculative decoding delivers its largest speedups (1.8x to 3.0x lower TPOT) on structured outputs—code edits, JSON payloads, and boilerplate refactoring—where draft acceptance rates exceed 75%. At very high batch sizes, however, verification compute competes with continuous batching throughput, so engines should dynamically disable or shorten draft length as batch utilization climbs.

## Inference Optimization Checklist

- [ ] Separate SLO targets defined for TTFT (p50/p95) and TPOT (p50/p95) under peak concurrency.
- [ ] Continuous batching and chunked prefill enabled to eliminate head-of-line blocking.
- [ ] Prefix caching verified on system prompts, tool definitions, and shared RAG context blocks.
- [ ] KV-cache capacity modeled explicitly for worst-case context length multiplied by target concurrency.
- [ ] Quantized checkpoints calibrated on production-like tool-use and code traces, not generic text alone.
- [ ] End-to-end task accuracy and JSON schema validity benchmarked before promoting any lower-bit build.
""",
    },
    {
        "slug": "guide-rag-context-engineering",
        "title": "Context Engineering Beyond Naive RAG: Hybrid Retrieval, Reranking, and Long-Context Hygiene",
        "subtitle": "How to design retrieval and context assembly pipelines that eliminate silent hallucinations, stale chunks, and lost-in-the-middle degradation.",
        "kicker": "RETRIEVAL & CONTEXT",
        "reading_time": "7 min read",
        "updated_at": "2026-11-28",
        "description": "Practical engineering guide to context engineering and production RAG: hybrid BM25 + dense retrieval, cross-encoder reranking, structure-aware chunking, and context hygiene.",
        "body_markdown": """## Why Naive Vector RAG Fails in Production

The textbook Retrieval-Augmented Generation prototype—split PDFs into fixed 500-token chunks, embed them with a dense encoder, fetch the top five cosine-similarity hits, and stuff them into a prompt—fails predictably in real engineering environments.

Four failure modes account for the majority of production RAG errors:

1. **Lexical Blindness**: Dense embeddings excel at semantic paraphrase but routinely miss exact identifiers—error codes (`ERR_TLS_CERT_ALTNAME_INVALID`), API version strings, part numbers, function names, and domain acronyms.
2. **Broken Structural Boundaries**: Fixed-size sliding windows slice tables in half, separate headings from their clauses, and strip the parent document metadata needed to interpret a paragraph accurately.
3. **Context Pollution and Lost-in-the-Middle**: Stuffing twenty marginally relevant chunks into a long context window dilutes attention, inflates latency, and causes the model to latch onto outdated or contradictory passages.
4. **Silent Retrieval Misses**: When the retriever fails to surface the relevant document, a standard generator rarely admits ignorance; instead, it blends parametric memory with tangential retrieved text into a plausible-sounding hallucination.

Moving from naive RAG to **context engineering** means treating retrieval, ranking, formatting, and citation verification as a disciplined information-retrieval pipeline.

## Structure-Aware Ingestion and Contextual Chunking

Retrieval quality is bounded by ingestion quality. Before choosing an embedding model, invest in preserving document structure:

- **Parse Native Semantics**: Convert HTML, Markdown, codebases, and PDFs into hierarchical trees (sections, subsections, tables, code blocks). Keep tables intact as Markdown or structured JSON rather than flattening cells into unreadable text.
- **Attach Parent Context to Every Chunk**: Prepend each chunk with its document title, section path (`Security Policy > Key Rotation > Production`), publication date, and source URI before indexing. This simple enrichment resolves pronouns and ambiguous references ("it must be rotated every 90 days") without requiring a separate graph database.
- **Index Code by AST, Not Line Count**: For software repositories, split by syntax tree boundaries (classes, functions, interfaces) and retain module imports and docstrings so retrieved snippets remain self-contained.

## Hybrid Retrieval and Cross-Encoder Reranking

Single-stage vector search is rarely sufficient for high-stakes enterprise knowledge bases. A two-stage retrieval architecture combines lexical precision with semantic recall:

1. **Stage 1 — Hybrid Candidate Generation**: Run a sparse lexical index (BM25 or SPLADE) in parallel with a dense vector index. Fuse the top 50–100 candidates from each using Reciprocal Rank Fusion (RRF) or calibrated score normalization. This guarantees that exact error codes and rare proper nouns are never dropped while preserving conceptual matches.
2. **Stage 2 — Cross-Encoder Reranking**: Pass the fused top 30–50 candidates through a dedicated cross-encoder reranker (which attends jointly over query and passage tokens) to select the final 5–8 passages. Cross-encoders are too slow to run over millions of documents, but over fifty candidates they add under 80 milliseconds while dramatically improving precision@5.
3. **Metadata and Freshness Filtering**: Enforce access-control lists (ACLs), tenant boundaries, and document-version filters *before* or *during* candidate retrieval—never rely on the LLM prompt to hide unauthorized or deprecated records.

### Query Transformation Without Over-Engineering

When user queries are conversational ("what did we decide about that migration last month?"), a lightweight query rewriter can resolve coreferences from recent chat turns and generate both a keyword query and a semantic query. Avoid multi-hop agentic retrieval loops for simple factual lookups; measure whether query expansion actually improves recall@10 on an offline test set before paying its latency tax.

## Long-Context Hygiene and Grounded Generation

Even with 200K+ token context windows, **long context does not replace retrieval**—it changes the granularity of what you retrieve. Instead of fetching isolated 200-word fragments, you can retrieve complete sections or full files while still filtering out irrelevant noise.

Apply strict hygiene when assembling the final prompt:

- **Explicit Provenance Envelopes**: Wrap every retrieved passage in structured tags containing a stable ID, source title, date, and URL (`<doc id="D3" source="runbook.md" updated="2026-10-12">`).
- **Position High-Signal Evidence Deliberately**: Place the highest-ranked passages at the beginning and end of the evidence block, where transformer attention recall is strongest.
- **Enforce Abstention and Inline Citations**: Instruct the model to cite chunk IDs for every factual claim and explicitly abstain when the retrieved evidence does not answer the question. Post-process responses to verify that every cited ID exists in the retrieved set.
- **Deduplicate Near-Identical Versions**: Collapse duplicate wiki mirrors and near-identical release notes prior to prompt assembly so one repeated document does not crowd out complementary sources.

## Context Engineering Checklist

- [ ] Ingestion pipeline preserves headings, tables, code AST boundaries, and document timestamps.
- [ ] Hybrid retrieval (BM25 + dense embeddings) fused via RRF or calibrated weights.
- [ ] Cross-encoder reranker evaluated on recall@k and MRR against a labeled golden query set.
- [ ] ACLs, tenant isolation, and freshness filters enforced deterministically at query time.
- [ ] Retrieved passages formatted with explicit source metadata and deduplicated before prompting.
- [ ] Groundedness and abstention rates tracked continuously on unanswerable and adversarial queries.
""",
    },
    {
        "slug": "guide-llm-evaluation-benchmarks",
        "title": "Evaluating Generative AI Systems in Production: Programmatic Graders, Judge Calibration, and Regression Harnesses",
        "subtitle": "How engineering teams replace vibe checks and saturated public leaderboards with deterministic CI gates, calibrated LLM judges, and online telemetry.",
        "kicker": "EVALUATION & QUALITY",
        "reading_time": "7 min read",
        "updated_at": "2026-11-28",
        "description": "Engineering guide to LLM evaluation in production: building golden datasets, programmatic graders, calibrating LLM-as-a-judge against human labels, and CI regression harnesses.",
        "body_markdown": """## Why Public Benchmarks Mislead Production Teams

Public leaderboards such as MMLU-Pro, SWE-bench, or GPQA are useful for tracking broad frontier capabilities, but they are poor predictors of whether a specific model or prompt change will improve your production system. Three structural gaps separate public benchmarks from real deployments:

1. **Distribution Mismatch**: Production traffic contains messy inputs, domain jargon, proprietary schemas, partial context, and adversarial edge cases that never appear in academic benchmarks.
2. **Contamination and Overfitting**: Frontier checkpoints may have seen public benchmark items or close paraphrases during pretraining or post-training, inflating scores without improving out-of-distribution robustness.
3. **System vs. Model Scope**: Users experience the entire system—retriever, prompt template, tool harness, post-processor, and model together. A model that scores higher in isolation can still regress end-to-end performance if its tool-calling formatting or verbosity breaks downstream parsers.

Reliable AI engineering requires owning a private, continuously evolving evaluation harness wired directly into CI/CD.

## Designing a Three-Tier Grading Architecture

Not every property of an LLM output requires an expensive model judge. Structure your evaluators from fastest and most deterministic to most nuanced:

### Tier 1: Programmatic and Reference-Based Graders

Always prefer deterministic code checks wherever a specification is verifiable:

- **Structural Contracts**: JSON schema validation, SQL/Python AST parsing, regex format compliance, and required citation ID verification.
- **Execution-Based Verification**: Running generated code against unit tests, executing generated SQL against a seeded sandbox database and comparing result sets, or checking tool-call argument types against API contracts.
- **Operational Guardrails**: Latency ceilings, output token bounds, PII redaction checks, and forbidden-string filters.

Programmatic graders run in milliseconds, cost zero tokens, and never suffer from judge variance.

### Tier 2: Calibrated LLM-as-a-Judge

For open-ended criteria—such as summary faithfulness, tone adherence, or root-cause completeness—a well-designed LLM judge scales far beyond manual review. However, naive prompts ("rate this answer 1 to 10") produce noisy, uncalibrated scores plagued by verbosity bias, position bias, and self-preference bias.

Make LLM judges trustworthy through four engineering disciplines:

1. **Binary or Narrow Rubrics Over 1–10 Scales**: Ask targeted pass/fail questions ("Does the summary introduce any numerical claim not supported by the source context?") or use a tightly defined 3-point rubric with concrete anchor examples.
2. **Chain-of-Thought Before Verdict**: Require the judge to extract supporting or contradicting quotes first, then emit the structured verdict.
3. **Position-Swapping for Pairwise Comparisons**: When comparing Candidate A against Candidate B, evaluate both `(A, B)` and `(B, A)` orders and treat disagreements as ties to eliminate order bias.
4. **Measure Judge Agreement Against Human Labels**: Label 100–200 stratified examples with domain experts and compute Cohen's kappa or precision/recall of the judge against human ground truth. Iterate on the judge prompt until agreement exceeds your threshold (typically >= 0.80) before trusting it in CI.

### Tier 3: Human Error Analysis and Production Telemetry

Automated evals only catch failure modes you already know to test. Schedule weekly error-analysis sessions where engineers inspect 30–50 real production traces—especially user retries, thumbs-down events, escalated tickets, and tool-loop timeouts. Classify each failure into an explicit taxonomy (retrieval miss, prompt ambiguity, schema drift, hallucinated citation, tool timeout, or model reasoning error) so engineering time goes toward the highest-frequency root cause rather than speculative prompt tweaks. Every recurring failure mode discovered during trace review should be converted into a new test case and added to the golden suite.

## Online Shadow Testing and Canary Rollouts

Offline golden sets catch known regressions, but live user traffic always surfaces novel edge cases. Before promoting a new model checkpoint, system prompt, or retrieval index to 100% of production traffic, run a staged rollout:

1. **Shadow Replay**: Mirror a 5–10% sample of live requests asynchronously to the candidate pipeline and run both Tier-1 programmatic graders and calibrated judges on the paired outputs without affecting user-facing latency.
2. **Canary Traffic with Automated Rollback**: Route 5% of live traffic to the candidate while monitoring business and system guardrails—p95 latency, JSON parse failure rate, escalation rate, and user retry rate. Roll back automatically if any guardrail breaches its control limit.
3. **Versioned Trace Archival**: Tag every production trace with the exact model ID, prompt commit hash, retriever index version, and tool schema version so regressions can be bisected deterministically weeks later.

## Managing Nondeterminism and Regression Gates

Even at `temperature=0`, floating-point non-associativity in batched GPU kernels and Mixture-of-Experts routing can introduce subtle output variance. Treat evaluation scores as statistical estimates rather than noiseless constants:

- **Stratified Golden Sets**: Maintain a fast smoke suite (50–100 high-signal cases) that runs on every pull request in under two minutes, and a comprehensive nightly suite (500–2,000 cases) covering long-tail regressions and adversarial inputs.
- **Multi-Trial Pass Rates**: For stochastic agentic tasks, report both `pass@k` (capability ceiling) and `pass^k` (consistency across *k* independent trials). Production reliability depends on `pass^k`, not lucky single-run wins.
- **Slice-Level Reporting**: Never gate solely on an aggregate average. A +3% overall improvement can hide a -15% regression on a critical customer segment, language, or tool category. Track metrics by task slice and fail builds when any critical slice drops below its floor.

## Evaluation Harness Checklist

- [ ] Private golden dataset version-controlled alongside code and refreshed monthly from real failure traces.
- [ ] Tier-1 deterministic graders verify schemas, citations, execution results, and latency bounds.
- [ ] LLM-as-a-judge rubrics use binary/narrow criteria and are calibrated against human-labeled ground truth.
- [ ] Pairwise judges run position-swapped evaluations to eliminate ordering bias.
- [ ] CI runs a fast smoke eval on every prompt, retriever, or model change; full suite runs nightly.
- [ ] Metrics tracked per task slice and reported with variance across repeated trials for agentic loops.
""",
    },
    {
        "slug": "guide-cascaded-model-routing",
        "title": "Cascaded Model Routing & Cost Optimization: Frontier Accuracy at Small-Model Latency",
        "subtitle": "Architectural patterns for combining fast small models, calibrated uncertainty triggers, and frontier escalation to cut inference spend by 60–80%.",
        "kicker": "ECONOMICS & ROUTING",
        "reading_time": "7 min read",
        "updated_at": "2026-11-28",
        "description": "Engineering guide to cascaded LLM routing and cost optimization: pre-routing vs confidence-based escalation, calibration curves, fallback resilience, and unit economics.",
        "body_markdown": """## The Economics of Monolithic Frontier Serving

Most production Generative AI workloads exhibit a sharply skewed difficulty distribution. Across customer support triage, entity resolution, document extraction, code review, and classification pipelines, 70% to 85% of incoming requests are routine and well within the capability envelope of a fast, compact model (7B–30B open weights or a lightweight hosted tier). Only the remaining 15% to 30%—ambiguous edge cases, multi-hop reasoning, subtle policy conflicts, or complex repository-wide refactors—genuinely require a frontier reasoning model.

Routing 100% of traffic to the largest frontier checkpoint incurs two compounding penalties:

1. **Unit-Cost Blowup**: Frontier models routinely cost 10x to 30x more per million output tokens than small models, turning high-volume background pipelines economically unviable.
2. **Latency Tax**: Users waiting for routine extractions or lookups absorb multi-second reasoning latency that adds zero accuracy on straightforward inputs.

**Cascaded model routing** resolves this trade-off by matching compute dynamically to query difficulty, achieving near-frontier accuracy at a fraction of the blended cost and median latency.

## Two Routing Architectures: Pre-Routing vs. Escalation Cascades

Production systems rely on two primary routing topologies, often combined in layers:

### 1. Pre-Execution Router (Predictive Dispatch)

A lightweight classifier—such as a fine-tuned DeBERTa encoder, a logistic regression over query embeddings and structural features, or a fast rule engine—inspects the request *before* generation and dispatches it directly to Tier 1 (small model) or Tier 2 (frontier model).

- **Strengths**: Zero wasted generation tokens on hard queries; lowest possible latency for frontier-bound requests.
- **Limitations**: The router only sees the input, not the model's intermediate reasoning. Some inputs look deceptively simple until the small model encounters an ambiguity mid-generation.

### 2. Confidence-Gated Cascade (Generate-Then-Escalate)

All requests initially hit the fast small model. A verifier or uncertainty estimator inspects the response; if confidence falls below a calibrated threshold, the request escalates to the frontier model (optionally passing the small model's draft or identified ambiguity).

- **Strengths**: Empirically much higher accuracy-per-dollar because the escalation decision uses actual generation signals.
- **Limitations**: Escalated requests pay the small model's latency plus the frontier model's latency, though if the small model runs in under 250ms, the overhead is modest relative to frontier TTFT.

## Designing Reliable Escalation Triggers

The difference between a naive cascade and a high-precision production router lies in how uncertainty is measured. Relying on a model's verbal self-report ("how confident are you from 1 to 10?") is notoriously poorly calibrated. Stronger escalation signals include:

- **Deterministic Verifier Failures**: In coding, SQL, or structured extraction, escalate automatically whenever schema validation fails, a unit test returns non-zero, or a citation check flags an ungrounded claim.
- **Logit Entropy and Token-Margin Thresholds**: For classification, entity matching, and routing tasks, inspect the log-probabilities of the decision tokens. High entropy or a narrow margin between the top two classes strongly correlates with real-world error.
- **Explicit Abstention / "Ask for Help" Tool**: Fine-tune or prompt the small model to emit a structured `ESCALATE_TO_FRONTIER` decision with a brief reason when evidence is conflicting or incomplete. On entity-resolution and moderation benchmarks, allowing a small model to defer 15–20% of ambiguous items to a frontier model routinely matches 98–99% of standalone frontier accuracy at roughly 4x lower cost.
- **Self-Consistency Disagreement**: For high-value non-streaming jobs, sample two cheap low-temperature completions from the small model; if they disagree on the final answer, escalate to the frontier model.

## Calibrating the Accuracy-Cost Pareto Frontier

Routing thresholds should never be chosen by intuition. Build an offline calibration curve using a labeled validation set:

1. Run both the small model and the frontier model across 500–1,000 representative production examples.
2. Record the uncertainty score (entropy, margin, or verifier signal) and correctness for every example.
3. Sweep the escalation threshold from 0% to 100% escalation rate, plotting **blended accuracy** against **blended cost per 1,000 requests** and **p95 latency**.
4. Select the operating point where marginal accuracy gain per additional dollar flattens—typically between 12% and 25% escalation.

Re-run this calibration curve whenever you upgrade either tier's model weights, change the system prompt, or observe domain drift in production traffic.

## Resilience, Quotas, and Multi-Provider Fallbacks

A routing layer also serves as your primary reliability shield. Decouple application code from specific model IDs by routing through logical capability tiers (`fast-extract`, `balanced-code`, `frontier-reasoner`). Configure circuit breakers that fail over gracefully across providers or regions when a frontier endpoint experiences elevated 5xx rates or rate-limit saturation, while logging the exact model version and routing decision on every trace for cost attribution and postmortem debugging.

## Cascaded Routing Checklist

- [ ] Application code targets logical capability tiers rather than hardcoded model IDs.
- [ ] Difficulty distribution measured on a labeled sample to quantify potential small-model coverage.
- [ ] Escalation triggers grounded in deterministic verifiers, log-prob margins, or explicit abstention—not verbal confidence scores.
- [ ] Accuracy-vs-cost Pareto curve calibrated offline before setting production thresholds.
- [ ] Escalation rate, blended cost per 1K requests, and per-tier latency monitored on live dashboards.
- [ ] Circuit breakers and fallback policies tested under simulated provider rate limits and timeouts.
""",
    },
]
