# The $0 plan

Date: 2026-10-27. **Constraint, set by the project owner: the project stays free.** This replaces every budget line in the Phase 1 memo (section E4) and the task 3 note.

## Paid items and their free replacements

| Was | Cost | Free replacement | Status | What we give up |
|---|---|---|---|---|
| Our own agent runs (E2) | ~$2,200 | **SWE-bench bash-only trajectories**: per-call tokens for 12 models on one scaffold. **SWE-rebench leaderboard**: fresh, uncontaminated tasks, repeated runs with standard errors, includes real products. | ✅ Built | Our own task set and seeds. Per-call token detail exists only for the contaminated Verified set; SWE-rebench gives per-problem totals. |
| GPU serving benchmarks R1–R3 (V2) | ~$350–450 | **V2 becomes a three-way agreement check:** InferenceX, other independent published results (MLPerf, vLLM/SGLang team posts, provider benchmarks), and **our own roofline bound** from spec sheets and model configs. | To do | **V2 weakens.** We don't measure; we check that independent measurements agree with each other and stay under the physical ceiling. The report must say so. |
| Optional self-measured point | $0 if within credits | **Modal Starter plan: $30/month of free credits** (about 7.5 H100-hours [S], [pricing](https://modal.com/pricing)). Enough for R1 (2×H100, ~3 h). | Optional | A payment card may be required [U], so set a $0 spending limit. Only if you want one measurement of our own. |
| GPU rental price series | Silicon Data licence | Wayback snapshots of neocloud price pages, plus a daily scrape of free public price listings (Vast.ai, RunPod, Lambda, etc.) [U on which have open endpoints], plus InferenceX's `costPerHour` and Silicon Data's free blog figures. | To do | List and spot prices only; contract prices stay private. That's acceptable: the filings cover contract economics (V5). |
| Diurnal demand curve | n/a (no source) | (a) **Hourly probes of free OpenRouter models:** 2 models × 24 h = 48 requests a day, under the 50/day free cap [S]. Needs a free key stored as a GitHub secret. Latency under load is a proxy for host utilisation. (b) **AgentX trace timing** (393 Claude Code sessions): analysis only, since no licence is stated. | Option | Still a proxy, not demand itself, so it stays "assumed" with a sensitivity range. |
| Power-user usage distribution | n/a | (a) Your own Claude Code logs on this machine, which record per-message token usage. Real power-user data, but personal: **only with your OK**, and published only in aggregate. (b) Public usage reports people post on GitHub. | Option | Severe selection bias, as before. |
| Excel for V8 | Licence | LibreOffice Calc (free) can recalculate an .xlsx headlessly, so the Excel–Python diff test runs free in CI. | Later | None material. |
| V7 practitioner review | n/a | Already free; it costs only people's time. | Later | n/a |

## What changes in the validation gates

- **V2 is downgraded,** from "we reproduce" to "independent sources agree, and none exceeds the roofline bound." Tolerances are fixed before looking:
  - InferenceX vs another independent source: ±15% on output tokens/s/GPU at matched configuration.
  - Every source must stay within ≥0.5× and ≤1.0× of roofline decode throughput.
  - If a self-measured R1 on free credits is added later, the original ±10% test applies to it.
- **V1 is unchanged.** It never needed our own GPUs; it needs a cost layer and the OpenRouter prices, both of which we have for free.
- **Agents (hypothesis E):** the kill test for run-to-run noise can now use SWE-rebench's standard errors from repeated runs, instead of a bootstrap only.

## Dropped

Nothing from the core question. Self-measured GPU throughput becomes optional, and the report's limitations section says it wasn't done.
