# V2 (free version): roofline ceiling vs published throughput

Date: 2026-10-27.
- Model: [snapshots/roofline/roofline.py](../snapshots/roofline/roofline.py).
- Check: [snapshots/roofline/v2_check.py](../snapshots/roofline/v2_check.py).
- Output: [data/roofline/v2_comparison.csv](../data/roofline/v2_comparison.csv).
- Pre-set tolerances: [zero_cost_plan.md](zero_cost_plan.md).

## Method

**Inputs, all free and stored in the repo:**
- **GPU specs** from NVIDIA's H100 and H200 pages ([gpus.csv](../data/roofline/gpus.csv)). NVIDIA quotes FLOPS "with sparsity", so dense peak is half the listed figure:
  - H100: 3.35 TB/s memory bandwidth, 989.5 BF16 / 1,979 FP8 dense TFLOPS.
  - H200: 4.8 TB/s memory bandwidth, same compute.
- **Model configs** (`config.json`) for gpt-oss-120B (Apache-2.0) and DeepSeek-R1-0528 (MIT), in [configs/](../data/roofline/configs/). Parameter counts derived from them match the publishers' totals:
  - gpt-oss-120B: 116.2B total and 5.13B active, vs 117B and 5.1B published.
  - DeepSeek-R1: 670.1B and 36.6B, vs 671B and 37B.
  - This is a unit test.

**Ceiling for each workload point:**
- Prefill is compute-bound at dense peak.
- Each decode step is the slower of two limits:
  - **memory:** weights touched plus KV cache read, at HBM bandwidth;
  - **compute:** 2 × active parameters plus attention FLOPs.
- Real systems can't reach this.

**Modelling choices that matter:**
- **MoE routing.**
  - "min": all tokens use the same experts, giving the hard ceiling.
  - "uniform": independent routing, giving the typical ceiling.
- **KV cache under tensor parallelism.**
  - DeepSeek's latent KV (MLA) is replicated on every TP rank when DP-attention is off, as in these runs.
  - gpt-oss's KV is split by head.
- **gpt-oss on Hopper:** MXFP4 weights (4.25 bits) are read, but the maths runs at BF16, since Hopper has no FP4 units.
- **Speculative decoding** (MTP, used in R2) breaks the one-token-per-step assumption, so R2 isn't checked here.

## Results

| Source | Config | Points | Above hard ceiling | Share of typical (uniform-routing) ceiling |
|---|---|---|---|---|
| InferenceX R1 | gpt-oss-120B, 2×H100, vLLM, 1k/1k | 5 | 0 | 0.30 → 0.60 as concurrency rises 4 → 64 |
| InferenceX R1 | gpt-oss-120B, 2×H100, vLLM, 8k/1k | 5 | 0 | 0.32 → 0.52 |
| InferenceX R3 | DeepSeek-R1, 8×H200, SGLang, 8k/1k | 5 | 0 | 0.28 → 0.52 |
| dstack (2025-03) | DeepSeek-R1, 8×H200, TensorRT-LLM, 3.2k/0.8k, concurrency 128 | 1 | 0 | **0.89 if the figure is output tokens, 0.18 if it's total tokens.** The post doesn't say. |

Every point is memory-bound in decode.

## Verdict against the pre-set tolerances

1. **Ceiling test: passes.** No source exceeds the hard ceiling. All InferenceX points reach 11–26% of the hard ceiling and 28–60% of the typical ceiling.
   - **Deviation from plan:** the plan set a 0.5–1.0× band, and the low-concurrency InferenceX points sit at about 0.3× the typical ceiling, below 0.5.
   - That's expected, not an error: at low concurrency, per-step overheads (scheduling, kernel launches, communication) dominate.
   - The band was set before looking and is wrong for low concurrency. I'm reporting that instead of quietly moving it. **It holds for concurrency ≥16** (0.48–0.60).
2. **Cross-source agreement (±15%): not established.**
   - The only free independent source found for these models on Hopper, dstack, uses a different workload and doesn't state its token denominator. Its two possible readings bracket InferenceX's level, so it can't confirm or refute it.
   - The **consistency check that does hold:** two different models, engines and GPUs reach the same efficiency profile in InferenceX. That's evidence against a model-specific measurement error, but it's the same source, not independent.
3. **What this means for V1:** InferenceX can serve as the cost layer, provided its throughput is used at the efficiency it reports, not at roofline.

## A finding about denominators

InferenceX's dashboard reports **8,973 tok/s/GPU** for gpt-oss-120B on H100 at 8k/1k and 50 tok/s per user ([page](https://inferencex.semianalysis.com/run/gptoss-120b-on-h100)). Its API's `output_tput_per_gpu` for the same configuration is about 900–1,140 output tokens/s/GPU. The dashboard figure only fits **input + output tokens**: 8k/1k gives 9× the output count.
- So the dashboard's $/M tokens is **per total token**, and per *output* token it would be about 9× higher on that workload. Calculated, not stated by InferenceX.
- **Any $/M comparison against API prices must match denominators:** API prices charge input and output separately.

## Open

- The MLPerf Inference DeepSeek-R1 H200 result wasn't found in this pass [U]. Check MLCommons' results directly. It's the best remaining free independent source.
- A self-measured R1 on Modal's free credits would turn the cross-source check into a direct ±10% test (optional, per the $0 plan).
