# Task 3: InferenceX review and benchmark configs to reproduce

Date: 2026-10-27. This replaces section E1 of the Phase 1 memo.

## 1. InferenceX: what it is, what it gives us

- **Repo:** [SemiAnalysisAI/InferenceX](https://github.com/SemiAnalysisAI/InferenceX), Apache-2.0. Benchmarks live under `inferencex-e2e/`. Formerly InferenceMAX. It runs nightly on CI, and states that only this repo holds official results.
- **Public read API, no auth:** [OpenAPI spec](https://inferencex.semianalysis.com/api/openapi.json).
  - `/api/v1/availability`: 7,031 configuration-date rows as of today.
  - `/api/v1/benchmarks?model=…`: raw rows, with `date`, `runId` and `exactRun` for dated snapshots.
  - `/api/v1/tco-feed`: throughput at interactivity tiers 30/50/75/100 tok/s/user.
- **Every row is reproducible.** It carries:
  - the exact container image **with sha256 digest**;
  - a `recipe_fingerprint`;
  - TP/EP/DP layout, concurrency, precision and speculative-decoding method;
  - about 80 metrics: input and output throughput per GPU, TTFT/TPOT/ITL/E2E at p50–p95, KV-cache usage, CPU cache hit rate, and power and joules per token.
- **Two workload types:**
  - `single_turn`: synthetic, 1k/1k, 1k/8k and 8k/1k tokens in/out.
  - `agentic_traces`: replays real multi-turn agent traces with the [AgentX harness](https://github.com/SemiAnalysisAI/agentx-harness). That's a fork of NVIDIA AIPerf, `pip install agentx-harness==1.0.7`, and SemiAnalysis says the traces were collected from more than $3M of usage.
- **Cost method:** $/M = TCO $/chip-hr × 10⁶ / (3,600 × tok/s/chip).
  - The TCO is SemiAnalysis's own, from a survey and their model. Example: GB200 at $2.21/GPU-hr (Aug 2025 survey).
  - Utilization is **not discounted**: every point on the curve is priced as if the GPU is 100% busy at that concurrency.
  - The denominator can be total tokens or output tokens, so check which before comparing.

**What InferenceX does not do, and therefore what's still ours:**
1. Utilization under real demand. They price a saturated point; we derive average utilization from a demand curve plus a p95 latency target.
2. Reconciliation against market prices. They compare $/M across chips; we compare against what OpenRouter hosts actually charge (V1).
3. Market GPU rental prices instead of owner TCO.
4. The application layer.

**This changes the plan:**
- Our own benchmarks become **reproduction (V2), not discovery**, and shrink from about $1,400 to about $350–450.
- InferenceX's agentic traces can feed our queueing simulation instead of synthetic arrivals, if the dataset licence allows (see open items).

**Terms, checked 2026-10-27:**
- **InferenceX:** the [About FAQ](https://inferencex.semianalysis.com/about) says "All data is freely available" and that it can be used for your own analysis. No licence is named, and the footer says "All rights reserved."
  - **Policy:** use the data, attribute it, and publish derived comparisons and individual cited values. Don't mirror their rows in bulk.
  - Reference runs are recorded in [data/inferencex/reference_runs.csv](../data/inferencex/reference_runs.csv): IDs, run URLs and configurations only.
- **AgentX traces:** dataset `semianalysis_cc_traces_weka_062126`, from 393 Claude Code sessions with prompts and code removed. Median input is 142k tokens per request and median output 444, and 44% of sessions use subagents.
  - **No licence is stated**, so it's analysis only, and we don't republish it.
- **This plan is superseded on budget by [zero_cost_plan.md](zero_cost_plan.md).** Self-run GPU benchmarks are now optional.

## 2. "Beyond Benchmarks: The Economics of AI Inference" (arXiv 2510.26136)

- **Authors:** Zhuang et al., Oct 2025, CC-BY-4.0.
- **Method:** 9 small and medium models (up to 36B) on 2×A800, using vLLM and a medical evaluation set (WiNEval-3.0, 2,993 requests).
- **Cost basis:** depreciation over 3 years, power and maintenance, giving about $0.79/GPU-hr. Utilization is fixed at 1, which the authors call an "idealized baseline".
- **What it doesn't do:** no $/token figures are reported and there's no comparison with API prices or margins.

**Verdict: no overlap threat.** It's a useful citation for the problem we fix: its cost-to-serve assumes 100% utilization and never touches a market price.

## 3. Selection criteria

1. InferenceX has a recent run on **H100 or H200** with **vLLM or SGLang**, which is the hardware we can rent.
2. The model has **many distinct hosts on OpenRouter**, which V1 needs. Counts below are from our 2026-10-27 snapshot, base models only.
3. It fits on **one node** (≤8 GPUs).
4. At least one config bridges to **MLPerf** for the second V2 reference.

| Candidate | InferenceX Hopper coverage | OpenRouter providers | Decision |
|---|---|---|---|
| DeepSeek V4.1 Flash | H100 and H200, vLLM and SGLang, fp4 + MTP, **agentic traces**, runs up to **2026-10-26** | **33** | ✅ **R2: V1 flagship** |
| gpt-oss-120B | H100 vLLM fp4, single-turn 1k/1k, 8k/1k, 1k/8k; TP2/4/8; up to 2026-05-17 | 23 | ✅ **R1: cheap calibration plus a second V1 point** |
| DeepSeek-R1-0528 | H200 SGLang fp8 8k/1k TP8, up to 2026-10-22 (75 dated runs since 2025-09) | not checked | ✅ **R3: MLPerf bridge** (DeepSeek-R1 is in MLPerf Inference v5.1 [U]) |
| GLM-5.3 | Hopper runs not in recent availability | 37 | ❌ No Hopper reference |
| Kimi K3 | H200 vLLM agentic, but stale (2026-09-13); a 2.8T model | 21 | ❌ Too big for our budget |
| MiniMax M3 | H100/H200 vLLM, agentic up to 2026-10-23 | 12 | ⏸ Reserve, if R2 fails to deploy |
| Qwen3.5-397B | H100/H200 SGLang, agentic up to 2026-10-21 | 10 | ⏸ Reserve |
| Llama 3.3 70B | Hopper runs stale (2025-10-29) | 9 | ❌ Dropped. Replaced by R3 for the MLPerf link and by R1 for calibration. |

## 4. Configs to reproduce

Each config pins the **same image digest** as the InferenceX run we compare against, records the digest and `recipe_fingerprint` it matches, and uses the same TP/EP, precision, speculative decoding, workload and concurrency points.

| ID | Model | Hardware | Engine (image to pin) | Layout | Workload | Concurrency points | InferenceX reference |
|---|---|---|---|---|---|---|---|
| **R1** | gpt-oss-120B | 2×H100 SXM | `vllm/vllm-openai:v0.21.0` | TP2 | single_turn 1k/1k and 8k/1k | 4, 8, 16, 32, 64 | 2026-05-17 run. Best output: 2,079 tok/s/GPU (1k/1k) |
| **R2a** | DeepSeek V4.1 Flash | 4×H200 | `vllm/vllm-openai:v0.32.0` | TP4, fp4, MTP | agentic_traces (AgentX 1.0.7, same public dataset) | 1, 8, 32, 128 (4 of their 8) | 2026-10-24 run. Best output: 445 tok/s/GPU |
| **R2b** (optional) | DeepSeek V4.1 Flash | 8×H100 SXM | vLLM nightly `e4a5b55…`, pinned by digest | TP8, fp4, MTP | agentic_traces | 1, 8, 28 | 2026-10-26 run. Best output: 129 tok/s/GPU |
| **R3** | DeepSeek-R1-0528 | 8×H200 | `lmsysorg/sglang:v0.5.22-cu130` | TP8, fp8, no speculative decoding | single_turn 8k/1k | 4, 8, 16, 32, 64 | 2026-10-22 run. Best output: 150 tok/s/GPU |

Every run records the following:
- Engine arguments and the image digest.
- `nvidia-smi -q` output: power limit, clocks, ECC.
- NVLink topology.
- Driver and CUDA versions.
- Per-request latencies.
- Server metrics: KV usage and prefix-cache hit rate.
- **3 repeats** at each point.

### V2 pass criteria (fixed now, before any run)

- **Same image, same layout as InferenceX:**
  - Median output throughput per GPU and median TPOT within **±10%** of InferenceX at **≥4 of 5** concurrency points (≥3 of 4 for R2).
  - The deviation has the same sign at no more than 80% of points, meaning no systematic bias beyond noise.
- **R3 against MLPerf:** within **±25%** of the closest matching MLPerf H200 submission. MLPerf entries are tuned vendor builds, usually TRT-LLM.
- **If a config fails:**
  - Check the hardware first: power limit, PCIe vs SXM, NVLink.
  - If it still fails, rerun once on a second provider.
  - Two failing providers means we report the gap and use InferenceX's numbers as the cost layer, labelled as such.

### Budget

Prices are assumptions until quotes are recorded in the source registry: H100 at about $2.2/GPU-hr, H200 at about $3.5/GPU-hr.

| ID | GPU-hours | Est. $ |
|---|---|---|
| R1 | 2 × ~4 h (incl. weight download and 3 repeats) | ~$20 |
| R2a | 4 × ~7 h (4 points × ~1 h each per trace replay, plus setup) | ~$100 |
| R2b | 8 × ~5 h | ~$90 |
| R3 | 8 × ~5 h (~700 GB of weights to download) | ~$140 |
| Contingency ×1.3 | | ~$100 |
| **Total** | | **~$350 without R2b, ~$450 with it** |

## 5. Next steps

1. Check the InferenceX API terms of use and the AgentX dataset licence. If they bar reuse, R2 falls back to single_turn 8k/1k, using their H200 rows.
2. Pull the exact InferenceX reference rows, by `runId`, for R1–R3. Commit their IDs and our extract, after the terms check.
3. Get dated quotes for 2×H100, 4×H200 and 8×H200 from 2–3 neoclouds and add them to the source registry.
4. Find the closest MLPerf Inference H200 DeepSeek-R1 result for R3: [U], need to confirm the round and that the entry exists.
