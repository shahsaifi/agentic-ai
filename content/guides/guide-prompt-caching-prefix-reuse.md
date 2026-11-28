---
slug: guide-prompt-caching-prefix-reuse
order: 7
kicker: INFERENCE ECONOMICS
title: Prompt Caching & KV Prefix Reuse: Cache-Stable Agent Prompts for Lower Latency and Cost
subtitle: How prefix KV caching works across frontier APIs and self-hosted engines, why subtle prompt jitter destroys hit rates, and how to architect append-only agent contexts.
reading_time: 8 min read
updated: 2026-11-28
description: Engineering guide to LLM prompt caching and KV prefix reuse: RadixAttention and automatic prefix caching, eliminating prefix jitter, cache-stable agent layouts, and TTL economics.
keywords: prompt caching, kv cache, prefix reuse, radixattention, automatic prefix caching, ttft, agent latency, cost optimization
---

## How Prefix KV Caching Works Under the Hood

Every transformer inference call begins with the **prefill phase**: computing the Key ($K$) and Value ($V$) projection tensors for every token in the input prompt across all attention layers. Because causal self-attention is strictly left-to-right, the KV state of token $t$ depends only on tokens $1 \dots t$—never on anything that follows it.

**Prompt caching** (also called Automatic Prefix Caching in vLLM and RadixAttention in SGLang) exploits this mathematical invariant. Instead of recomputing prefill from scratch on every turn, the inference engine hashes fixed-size blocks of leading tokens (typically 16 to 64 tokens per block) and stores their computed KV tensors in GPU HBM, host DRAM, or a distributed KV tier. When a subsequent request arrives with the exact same leading token sequence, the engine skips prefill for the matched prefix and computes attention only over the uncached suffix.

For multi-turn coding agents, RAG assistants, and batch document extractors that resend 15,000 to 100,000 tokens of system instructions, tool schemas, and repository context on every turn, high cache hit rates routinely deliver:

- **50% to 90% lower input token cost** on hosted frontier APIs (Anthropic, OpenAI, Google Gemini).
- **3x to 8x lower Time to First Token (TTFT)**, because prefill FLOPs drop from quadratic over the entire conversation to linear over just the newest tool observation.
- **Higher serving throughput** on self-hosted clusters, freeing tensor-core capacity for concurrent decode batches.

## Why Real-World Agent Harnesses Accidentally Bust the Cache

Because KV prefix matching operates on **exact token-ID identity from token index zero**, a single mutated character near the top of the prompt invalidates the entire downstream cache. Production engineering teams routinely enable prompt caching yet observe hit rates below 15% due to subtle serialization bugs:

1. **Dynamic Timestamps in the System Prompt**: Injecting `Current time: 2026-11-28T14:22:09Z` or a per-request trace UUID in line two of the system prompt guarantees a 0% cache hit rate across requests. If the model needs the current date, inject only the calendar date (`2026-11-28`) or pass exact timestamps inside the latest user/tool turn at the tail of the prompt.
2. **Non-Deterministic Tool Schema Ordering**: Many agent frameworks assemble tool lists from unordered hash maps or dynamically filter tools per turn. Reordering two tool definitions—or adding one conditional tool mid-conversation—shifts every subsequent token position and invalidates the entire conversation history.
3. **Unstable JSON Key Serialization**: Serializing tool schemas or metadata dictionaries without `sort_keys=True` produces subtle key-order drift across workers or deploys, silently partitioning the KV cache.
4. **In-Place Context Mutation**: Editing an earlier message in the conversation array (for example, summarizing turn 3 in place while keeping turns 4–12) breaks prefix continuity from turn 3 onward.
5. **Tokenizer Boundary Drift**: Changing trailing whitespace or punctuation at the boundary of a cached breakpoint can merge with the next token in BPE tokenizers, changing the token ID of the boundary block and causing a cache miss.

## The Static-Prefix-First Prompt Architecture

Designing for 85%+ cache hit rates requires ordering every prompt section strictly from **most static** to **most volatile**, and treating conversation history as an **append-only log** between explicit compaction checkpoints.

| Prompt Layer | Stability Horizon | Placement Rule |
| :--- | :--- | :--- |
| **1. Core System Instructions** | Days to weeks (release-scoped) | Byte-identical across all users and turns; zero per-request variables |
| **2. Canonical Tool Schemas** | Release-scoped | Fixed alphabetical order, deterministic JSON serialization; never add/remove tools mid-session |
| **3. Shared Domain / Repo Context** | Hours to session-scoped | Stable repository map, API docs, or policy handbook; place explicit cache breakpoint here |
| **4. Append-Only Turn History** | Turn-scoped | Never mutate prior assistant or tool messages; append new observations strictly at the tail |
| **5. Ephemeral Turn Metadata** | Single-turn only | Current wall-clock timestamp, turn budget remaining, or user-specific runtime hints placed at the very end |

### Handling Dynamic Tool Availability Without Cache Busting

If an agent workflow restricts which tools are permitted during a specific phase (for example, disabling write tools during a read-only planning phase), do **not** delete those tool definitions from the prompt header. Instead, keep the full canonical tool schema list frozen in the cached prefix and enforce phase restrictions either via a lightweight reminder in the latest user turn or via constrained decoding / host-side tool gating. This preserves 100% prefix stability across phase transitions.

### Cache-Aware Context Compaction

When a long-running agent approaches its context budget, compacting on every turn destroys caching. Use **epoch-based compaction**: allow the append-only transcript to grow cleanly across 10–15 turns (enjoying near-100% prefix reuse on every turn), then perform a single clean compaction into a new pinned summary checkpoint that immediately becomes the stable prefix for the next epoch.

## Cache TTL Economics and Break-Even Math

Hosted API providers apply two distinct pricing models: **implicit prefix caching** (automatic discount with zero write surcharge, best-effort eviction) and **explicit cache breakpoints** (guaranteed reservation for a fixed TTL—commonly 5 minutes or 1 hour—with a 1.25x to 2.0x cache-write surcharge and a 0.1x cache-read rate).

Before adding explicit cache breakpoints everywhere, compute the break-even reuse count $N$:

- Suppose a cache write costs $1.25\times$ the base input rate and a cache read costs $0.10\times$.
- Break-even occurs when $1.25 + 0.10(N - 1) < N$, which solves to $N > 1.28$—meaning **just two hits within the TTL window** already save money.
- Conversely, if a 1-hour TTL costs $2.0\times$ on write, break-even requires at least three reads within the hour. For one-shot batch extraction jobs with unique documents per call, explicit caching on the document payload loses money; cache only the shared system prompt and extraction schema across the batch.

On self-hosted engines (vLLM, SGLang), KV prefix caching has zero write surcharge, but HBM capacity is finite. If your cache working set exceeds free KV-cache VRAM, thrashing evicts prefixes before turn 2 arrives. Enable **prefix-aware load balancing** (consistent hashing on the first 256–512 tokens or session ID) at the router layer so consecutive turns of the same agent session land on the same replica rather than round-robinning across cold GPUs.

## Multi-Agent Shared Prefix Design

When a parent orchestrator spawns parallel sub-agents to inspect files, run searches, or critique drafts, naive implementations write completely different system prompts for each worker—forfeiting shared KV state.

Instead, factor the **shared project context** (repository index, architectural invariants, coding conventions, and shared tool schemas) into a common leading prefix, and place the sub-agent's specialized role instructions and task prompt *after* the shared prefix. On both hosted APIs and RadixAttention-backed clusters, all parallel sub-agents then share a single prefilled KV tree for the heavy repository context, cutting aggregate TTFT and prefill GPU load dramatically.

## Prompt Caching Production Checklist

- [ ] Zero timestamps, request IDs, or random seeds appear inside the system prompt or tool schema block.
- [ ] Tool definitions are sorted deterministically and serialized with canonical JSON key ordering.
- [ ] Conversation turns are strictly append-only between periodic epoch-based compactions.
- [ ] Minimum prefix block length requirements (typically >= 1,024 tokens on hosted APIs) are verified for every cache breakpoint.
- [ ] Self-hosted deployments use session- or prefix-aware routing so multi-turn requests hit warm GPU replicas.
- [ ] Live dashboards track `cache_read_tokens / total_input_tokens`, p95 TTFT, and effective blended cost per 1M input tokens.
- [ ] CI tests assert byte-for-byte prefix stability between turn $N$ and turn $N+1$ on synthetic agent traces.
