---
slug: guide-llm-inference-quantization
order: 2
kicker: INFERENCE SYSTEMS
title: Production LLM Inference & Quantization: KV-Cache Economics, Low-Bit Calibration, and Decoding Latency
subtitle: A systems breakdown of memory-bandwidth bottlenecks, continuous batching, low-bit quantization failure modes, and speculative decoding for production serving.
reading_time: 7 min read
updated: 2026-11-28
description: Deep dive into production LLM inference and quantization: prefill vs decode bottlenecks, KV-cache memory math, W4A16/FP8/W4A4 trade-offs, and speculative decoding.
keywords: inference, quantization, kv-cache, fp8, w4a16, awq, gptq, speculative decoding, latency
---

## The Two Regimes of LLM Serving: Prefill vs. Decode

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
