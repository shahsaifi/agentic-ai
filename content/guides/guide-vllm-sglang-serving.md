---
slug: guide-vllm-sglang-serving
order: 9
kicker: SERVING INFRASTRUCTURE
title: Production LLM Serving Engines: vLLM, SGLang, Continuous Batching, and Disaggregated Prefill
subtitle: Systems architecture for high-throughput open-weight serving—PagedAttention vs. RadixAttention, chunked prefill, parallelism topologies, and KV-aware autoscaling.
reading_time: 8 min read
updated: 2026-11-28
description: Engineering guide to production LLM serving with vLLM and SGLang: PagedAttention vs RadixAttention, continuous batching, chunked prefill, disaggregated prefill-decode, and KV-cache autoscaling.
keywords: vllm, sglang, pagedattention, radixattention, continuous batching, chunked prefill, disaggregated prefill, tensor parallelism, llm serving
---

## Memory Management: PagedAttention vs. RadixAttention

At production concurrency, the limiting factor in self-hosted LLM serving is rarely raw GPU FLOPs—it is **HBM capacity and KV-cache fragmentation**. Early serving stacks pre-allocated contiguous VRAM buffers sized to each request's `max_model_len`, wasting 60% to 80% of GPU memory on unused sequence slots and severely capping concurrent batch size.

Modern serving engines solve this with two complementary memory architectures:

1. **PagedAttention (vLLM)**: Borrows virtual memory paging from operating systems. Each sequence's KV cache is partitioned into fixed-size physical blocks (for example, 16 tokens per block) allocated lazily on demand and tracked via a logical-to-physical block table. Fragmentation drops below 4%, and identical prompts can share physical blocks via copy-on-write during beam search or parallel sampling. With Automatic Prefix Caching (APC) enabled, vLLM hashes completed blocks so future requests reuse matching prefixes.
2. **RadixAttention (SGLang)**: Organizes all cached KV blocks inside a **radix tree (prefix trie)** with LRU eviction. Whenever any request finishes, its KV cache remains indexed in the radix tree rather than being freed immediately. Multi-turn conversations, few-shot prompts, tree-of-thought branches, and parallel sub-agents sharing a common repository prefix automatically traverse and reuse the longest matching tree path with zero manual cache-key management.

In practice, both engines achieve high throughput on standard OpenAI-compatible workloads; vLLM offers the broadest model and hardware ecosystem, while SGLang frequently leads on heavy prefix-sharing agent loops and constrained-decoding pipelines due to tight integration between RadixAttention and its zero-overhead scheduler.

## Continuous Batching and Chunked Prefill

Static batching waits for the longest sequence in a batch to emit an end-of-sequence token before admitting new requests—leaving GPUs idle while short requests sit finished. **Continuous (iteration-level) batching** schedules at the granularity of a single forward pass: the moment any sequence completes, its KV blocks return to the free pool and a queued request enters on the very next iteration.

However, continuous batching alone suffers from **prefill-decode interference**:

- Decode steps are memory-bandwidth-bound and take 15–40 milliseconds.
- A newly arrived 32K-token RAG or coding-agent prompt requires a compute-bound prefill pass that can occupy the GPU for 1,500+ milliseconds.
- Without mitigation, every active user currently streaming tokens experiences a jarring 1.5-second freeze (a severe p99 TPOT/ITL spike) whenever a long prompt enters the batch.

**Chunked prefill** eliminates this head-of-line blocking by slicing long prefills into fixed token budgets (for example, 512 or 2,048 tokens per iteration) and piggybacking them onto active decode steps. Because decode steps underutilize tensor-core FLOPs while waiting on HBM bandwidth, fusing a small prefill chunk into a decode batch saturates compute with minimal impact on decode latency—turning tail-latency spikes into smooth, predictable streaming.

## Disaggregated Prefill-Decode Serving

Even with chunked prefill, co-locating prefill and decode on the same GPU pool forces an architectural compromise:

- **Prefill** prefers high tensor-core FLOPs and lower tensor parallelism (minimizing all-reduce sync overhead) to hit aggressive TTFT targets.
- **Decode** prefers high aggregate HBM bandwidth and larger effective batch sizes to maximize tokens/second per dollar while meeting TPOT SLOs.

**Disaggregated serving** (supported in vLLM, SGLang, Dynamo, and Mooncake-style architectures) splits the cluster into two specialized pools:

1. **Prefill Pool**: Processes incoming prompts at high compute utilization, computes the full KV cache, and transfers the KV blocks directly over high-speed interconnect (NVLink, InfiniBand RDMA, or RoCE) to an available decode worker.
2. **Decode Pool**: Receives the pre-populated KV blocks and runs uninterrupted, high-batch autoregressive decoding with zero prefill jitter.

Disaggregation pays off most clearly on workloads with **high input-to-output token ratios** (10:1 or higher—such as long-context RAG, document summarization, and multi-turn coding agents) and strict simultaneous TTFT + TPOT SLOs. For small clusters (1–4 nodes) or short-prompt chat workloads, chunked prefill on unified replicas remains simpler to operate and avoids KV-transfer network bottlenecks.

## Choosing Parallelism Topologies: TP vs. PP vs. DP

Selecting the wrong parallelism strategy wastes expensive GPU interconnect bandwidth and inflates per-token latency. Match the topology to model size and interconnect speed:

| Strategy | How Weights & Work Split | Interconnect Requirement | When to Use |
| :--- | :--- | :--- | :--- |
| **Data Parallelism (DP)** | Full model replicated per GPU/node; requests load-balanced across replicas | Standard Ethernet | **Default whenever the model fits on 1 GPU**; highest throughput per dollar and zero sync overhead |
| **Tensor Parallelism (TP)** | Individual weight matrices sharded across GPUs; all-reduce every layer | High-bandwidth NVLink / NVSwitch (intra-node) | When a model exceeds single-GPU VRAM or strict low-latency TPOT requires pooling HBM bandwidth across 2–8 GPUs on one node |
| **Pipeline Parallelism (PP)** | Consecutive transformer layers placed on different nodes; point-to-point activations | InfiniBand / fast Ethernet (inter-node) | Multi-node models (e.g., 400B+ dense/MoE) where TP across nodes would stall on network all-reduce |
| **Expert Parallelism (EP)** | Mixture-of-Experts routed experts distributed across GPUs with all-to-all dispatch | NVLink / InfiniBand | Large sparse MoE models (DeepSeek, Qwen-MoE) at high batch concurrency |

Never span Tensor Parallelism across slow PCIe or standard Ethernet links—the per-layer synchronization latency will destroy TPOT. Prefer `DP` replicas of the smallest `TP` degree that satisfies your VRAM headroom and decode latency SLO.

## Autoscaling on KV-Cache Utilization, Not GPU Compute %

Standard Kubernetes HPA rules scaling on `DCGM_FI_DEV_GPU_UTIL` fail badly for LLM serving. During decode, a GPU can report 90% utilization with only 4 concurrent requests (healthy, plenty of headroom) or 55% utilization while 98% of its KV-cache blocks are full and requests are preempting and swapping to CPU RAM.

Build autoscaling and admission control around **serving-native metrics**:

- **KV-Cache Block Utilization (`gpu_cache_usage_perc`)**: Trigger scale-out when sustained KV utilization crosses 70–75%. Above 90%, engines begin preempting active sequences, causing catastrophic latency cascades.
- **Waiting Queue Depth & Time-in-Queue**: Scale aggressively when `num_requests_waiting` rises above zero for more than a few seconds, signaling saturated admission capacity.
- **Prefix-Aware Routing Layer**: Place a lightweight router (such as SGLang Router or vLLM Production Stack) in front of replicas that tracks per-replica KV-cache load and routes requests with matching prompt prefixes to warm replicas—falling back to least-loaded routing when a warm replica's KV utilization exceeds 80%.

## Production Serving Capacity Checklist

- [ ] Separate p50/p95 SLOs established for TTFT, TPOT (inter-token latency), and end-to-end throughput.
- [ ] Continuous batching, chunked prefill, and prefix caching (APC / RadixAttention) enabled and load-tested under mixed prompt lengths.
- [ ] Tensor Parallelism kept strictly intra-node over NVLink; horizontal scaling handled via Data Parallelism replicas.
- [ ] Disaggregated prefill-decode evaluated when input-to-output token ratios exceed 10:1 under strict tail-latency SLOs.
- [ ] Autoscaler driven by KV-cache utilization (`gpu_cache_usage_perc`) and waiting queue depth rather than raw GPU compute %.
- [ ] Prefix-aware load balancing configured to maximize KV hit rates without creating hot-spot replicas.
- [ ] Graceful draining and readiness probes verify model weights and CUDA graphs are compiled before admitting live traffic.
