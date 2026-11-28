---
slug: guide-structured-outputs-decoding
order: 8
kicker: DECODING & RELIABILITY
title: Structured Outputs & Constrained Decoding: Grammar Enforcement, Schema Design, and Failure Recovery
subtitle: How FSM and CFG token masking guarantee valid JSON at decode time, why rigid schemas degrade reasoning accuracy, and how to design resilient extraction pipelines.
reading_time: 8 min read
updated: 2026-11-28
description: Engineering guide to LLM structured outputs and constrained decoding: FSM/CFG logit masking, reasoning-first vs JSON-first trade-offs, flat schema design, and semantic failure recovery.
keywords: structured outputs, constrained decoding, json schema, fsm, cfg, grammar enforcement, outlines, xgrammar, llguidance
---

## How Constrained Decoding Guarantees Syntactic Validity

When production software parses LLM responses into database records, API calls, or workflow state machines, prompt-only instructions ("Respond strictly in valid JSON without markdown fences") fail on 1% to 5% of edge cases—trailing commas, unescaped quotes inside code snippets, hallucinated enum values, or conversational preambles.

**Constrained decoding** eliminates syntactic parse errors at the sampling layer. Before the inference engine samples the next token from the model's output logit vector, a grammar engine inspects the current parser state and applies a bitmask that sets the logit of every grammatically illegal vocabulary token to $-\infty$.

### FSM vs. CFG Grammar Backends

Modern serving engines (vLLM, SGLang, llama.cpp, and hosted structured-output APIs) compile JSON Schemas or regex patterns into one of two formal automata:

1. **Finite-State Machines (FSM / Regex Automata)**: Ideal for flat JSON objects, enums, numbers, ISO dates, and regular expressions. Each FSM state maps to a precomputed vocabulary bitmask, allowing $O(1)$ mask lookup per decode step (pioneered by Outlines).
2. **Context-Free Grammars (CFG / Pushdown Automata)**: Required for recursive or arbitrarily nested JSON schemas, balanced brackets, and programming-language grammars. High-performance runtimes such as **XGrammar** and **LLGuidance** split vocabulary tokens into context-independent tokens (precomputed offline) and context-dependent tokens (evaluated dynamically via stack transitions), keeping CPU masking overhead under 50 microseconds per token.

Additionally, **jump-forward (compressed) decoding** recognizes deterministic structural tokens—such as `{"status":"`, field names, and closing braces—and appends them in a single step without running unnecessary transformer forward passes.

## The Hidden Accuracy Tax of Rigid Schemas

A widespread mistake in LLM application engineering is assuming that because constrained decoding guarantees 100% valid JSON, it also improves task accuracy. Empirical evaluations consistently show the opposite when schemas are poorly designed: **forcing a model directly into a deeply nested JSON structure before it can reason degrades math, classification, and multi-hop extraction accuracy by 5% to 20%**.

Two mechanisms cause this degradation:

- **Forced Premature Commitment**: If the schema places `"verdict": "approve" | "reject"` as the first key before `"evidence"` or `"rationale"`, causal attention forces the model to choose the answer in token three before generating the intermediate reasoning tokens needed to verify edge cases.
- **Tokenization Misalignment**: Masking out natural whitespace or forcing terse rigid field formats pushes the model off its post-training distribution. When a model wants to hedge or explain an ambiguity but the grammar only allows an integer, the mask forces it to pick a high-probability but semantically arbitrary number.

### Reasoning-First vs. JSON-First Patterns

| Pattern | How It Works | Best Production Use Case |
| :--- | :--- | :--- |
| **Native Reasoning + Constrained Final Block** | Allow free-form thinking tokens (or a reasoning model's dedicated trace), then constrain only the final JSON payload | Complex classification, legal/financial extraction, root-cause triage |
| **Rationale-First Schema Ordering** | Put `"reasoning"` or `"supporting_quotes"` as the *first* field in the JSON object, followed by `"decision"` and `"confidence"` | Non-reasoning fast models where a single structured pass is required |
| **Two-Stage Generate-Then-Extract** | Stage 1 solves the task in natural prose/markdown; Stage 2 uses a fast small model with constrained decoding to extract fields into JSON | High-stakes analytical tasks where top reasoning accuracy justifies an extra ~150ms extraction call |

## Designing Production-Grade Schemas

Schema architecture directly governs both model accuracy and grammar compilation latency. Follow five concrete design rules:

1. **Prefer Flat Objects Over Deep Nesting**: Keep object depth to two or three levels. Deeply nested wrapper objects waste output tokens on structural punctuation and increase the probability of schema confusion in smaller models.
2. **Use Discriminated Unions for Polymorphic Outputs**: Instead of one monolithic object with fifteen nullable optional fields, define explicit tagged union variants (for example, `{"type": "answer", "citation_ids": [...], "text": "..."}` vs. `{"type": "abstain", "missing_info": "..."}`). Models handle mutually exclusive branches far more reliably than sparse nullable bags.
3. **Always Include an Explicit Escape Hatch**: Never trap a constrained model when input data is missing or contradictory. Provide nullable fields (`string | null`), an `"unknown"` enum option, or an explicit `"abstain"` union branch so the model is never forced by the grammar to fabricate a value.
4. **Avoid Unbounded Complex Regexes**: Expressive lookaheads, huge numeric ranges, or complex email/URL regexes inside JSON Schema `pattern` fields can explode FSM state counts and trigger multi-second grammar compilation stalls on first request. Validate complex string formats in application code after decoding.
5. **Keep Field Descriptions Concise and Exact**: Use self-documenting snake_case keys (`invoice_total_cents` rather than `amount`) and specify units directly in the key name to eliminate unit-conversion hallucinations.

## Latency Overhead of Grammar Compilation and Caching

While per-token bitmasking is fast on modern runtimes, **initial grammar compilation** for a large JSON Schema with 50+ properties or nested `$ref` definitions can take 200ms to several seconds—directly inflating Time to First Token (TTFT) on cold requests.

To keep tail latency predictable:

- **Reuse Canonical Schemas**: Serve a small, versioned set of static schemas rather than dynamically synthesizing unique JSON Schemas per user request (for instance, embedding 500 user-specific IDs directly into a dynamic `enum` array on every call).
- **Pre-Warm Grammar Caches**: Both hosted APIs and self-hosted engines cache compiled FSM/CFG artifacts keyed by schema hash. Send a warm-up request for each production schema during container startup before adding a replica to the load balancer.
- **Watch Batch Interaction**: On self-hosted engines, CPU-side bitmask generation can bottleneck high-concurrency GPU decode loops if run synchronously on the Python event loop. Ensure asynchronous/C++ grammar backends (XGrammar or LLGuidance) are enabled and pinned to dedicated CPU threads.

## Handling Truncation and Semantic Validation Beyond Syntax

Syntactically valid JSON is necessary, not sufficient. Constrained decoding **cannot** prevent:

- **Max-Token Truncation**: If generation hits `max_tokens` mid-object, the output is truncated and unparseable despite grammar enforcement. Always inspect `finish_reason == "length"` before parsing, enforce bounded array/string lengths in the prompt, and implement an automatic retry with a higher token cap or a concise fallback schema.
- **Semantic Invariants and Cross-Field Constraints**: A grammar cannot verify that `line_items` sum to `invoice_total`, that `end_date >= start_date`, or that every `citation_id` actually exists in the retrieved context.
- **Self-Healing Validation Loop**: Run a deterministic validator (such as Pydantic with custom cross-field validators) immediately after JSON parsing. On semantic failure, feed the exact structured validation error back to the model for a single bounded repair turn—or escalate to a stronger model tier if the repair fails.

## Structured Outputs Production Checklist

- [ ] Constrained decoding (FSM/CFG) enabled for all machine-consumed JSON and tool-call payloads.
- [ ] Reasoning or evidence fields ordered *before* final classification or verdict fields in every decision schema.
- [ ] Every extraction schema includes explicit `null` or `"abstain"` escape hatches to prevent forced hallucinations.
- [ ] Schemas kept flat (<= 3 levels deep) with discriminated unions instead of sparse optional-field bags.
- [ ] Complex regex `pattern` constraints avoided in grammars; semantic and cross-field checks enforced post-decode in code.
- [ ] `finish_reason == "length"` handled explicitly with bounded retry/repair logic and logged as a distinct alert metric.
- [ ] Production schemas versioned, hashed, and pre-warmed on replica startup to avoid cold compilation TTFT spikes.
