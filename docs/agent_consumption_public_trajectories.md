# Agent token consumption from public SWE-bench trajectories

Date: 2026-10-27.
- Extractor: [snapshots/swebench/extract_trajectories.py](../snapshots/swebench/extract_trajectories.py).
- Data: [data/swebench/](../data/swebench/).

This replaces most of the paid agent runs in the Phase 1 measurement plan (section E2). It cost **$0**.

## Source and method

- **Submissions.** These are the SWE-bench "bash-only" submissions in [SWE-bench/experiments](https://github.com/SWE-bench/experiments) that used **mini-SWE-agent v2.0.0**. That's 13 folders, each running 500 SWE-bench Verified tasks, one attempt each, with the same scaffold.
- **Trajectories.** They're in the public S3 bucket `swe-bench-submissions`.
- **Per-call log.** Every model call logs input tokens (which include cache reads and writes), cache-read tokens, cache-write tokens, output tokens, reasoning tokens and dollar cost.
- **Token semantics checked.** Recomputing one Claude Opus 4.6 trajectory's cost from its tokens at list price reproduces the logged cost exactly ($0.403641).
- **Task outcome.** "Resolved" comes from the evaluation harness's own `report.json` per task. The repo's `per_instance_details.json` is kept only as a cross-check, because it turned out to be wrong for one submission.
- **Audit trail.** Raw trajectories aren't stored. Each task row records the S3 ETag and size, so the exact object can be re-fetched and verified.

## Checks passed

- 6,500 tasks and 323,492 model calls extracted.
- **The sum of per-call costs equals the published per-task cost for all 6,500 tasks.**
- Extracted success rates match the published headline to within 0.5 points for 12 of 13 submissions.

## Data problems found upstream, all flagged in `submissions.csv` → `data_issue`

1. **`20260219_mini-v2.0.0_gpt-5-2-codex`: its trajectories are byte-identical to `gpt-5-2-high`** (500 of 500 ETags), and every call logs `gpt-5.2-2025-12-11`. The folder doesn't contain Codex runs. **Excluded.**
2. **`gemini-3-pro-high`: `per_instance_details.json` marks all 500 tasks unresolved,** against a published 69.6%. The harness reports give 70.6%, so 5 tasks differ from the headline.
3. **`claude-4-5-haiku-high`:** the summary file and the harness reports disagree on 2 tasks.
4. **`claude-4-5-sonnet-high`:** 2 tasks have no harness verdict.

**Token classes that some providers didn't report.** These are left blank, never set to 0:
- **Gemini:** cache-read tokens are missing on some calls, so its cache share is a lower bound (≥).
- **Claude 4.6 Opus:** reasoning tokens are missing, so its reasoning share is a lower bound.
- **Non-Anthropic providers:** cache writes aren't reported.

## Results (12 submissions, Codex duplicate excluded)

| Model | Resolved | $/attempt | $/success | Tokens/attempt (k) | Tokens/success (k) | Input:output | Cache-read share of input | Reasoning share of output |
|---|---|---|---|---|---|---|---|---|
| gemini-3-pro-high | 70.6% | $0.960 | $1.360 | 1573 | 2228 | 88:1 | ≥84% | ≥79% |
| claude-4-5-opus-high | 76.8% | $0.754 | $0.982 | 671 | 874 | 69:1 | 95% | 25% |
| claude-4-5-sonnet-high | 71.2% | $0.658 | $0.924 | 1059 | 1488 | 71:1 | 97% | 21% |
| claude-4-6-opus | 75.6% | $0.552 | $0.730 | 451 | 596 | 63:1 | 93% | ≥16% |
| glm-5-high | 72.8% | $0.534 | $0.734 | 1667 | 2290 | 119:1 | 88% | 34% |
| gpt-5-2-high | 72.8% | $0.474 | $0.651 | 659 | 905 | 48:1 | 83% | 73% |
| deepseek-3-2-high | 70.0% | $0.448 | $0.640 | 2382 | 3403 | 88:1 | 68% | 59% |
| gemini-3-flash-high | 75.8% | $0.356 | $0.470 | 1716 | 2264 | 84:1 | ≥72% | 75% |
| claude-4-5-haiku-high | 67.0% | $0.331 | $0.494 | 1792 | 2674 | 96:1 | 97% | 25% |
| kimi-k2-5-high | 70.8% | $0.147 | $0.207 | 905 | 1279 | 96:1 | 91% | 39% |
| minimax-2-5-high | 75.8% | $0.073 | $0.097 | 1245 | 1642 | 106:1 | 95% | 37% |
| gpt-5-mini | 56.2% | $0.047 | $0.084 | 268 | 476 | 63:1 | 46% | 41% |

Unless noted, figures are means per task. $/success = total cost ÷ resolved tasks. "Tokens" = input + output.

## Observations

These are facts about this dataset, not conclusions yet.

1. **Agentic coding is input-bound.** There are 48–119 input tokens per output token, and 68–97% of input is served from cache, except gpt-5-mini at 46%. Agent cost is therefore driven mainly by **cache-read price and prefill**, not output price.
   - This affects the bottom-up chain directly. The workload mix we cost on GPUs should be prefill- and cache-heavy, so the 8k/1k single-turn benchmark is closer than 1k/1k. InferenceX's agentic-trace runs are closer still.
2. **At similar success rates, $/success spans about 14×.** Compare MiniMax 2.5 ($0.097, 75.8%) with Claude 4.6 Opus ($0.730, 75.6%), on the same scaffold and tasks. Most of the gap is price per token, not tokens used: MiniMax uses 2.8× *more* tokens per success.
3. **One generation pair goes against prediction 3.** Claude 4.5 Opus (high) → 4.6 Opus: tokens per success fell from 874k to 596k (0.68×) and $/success from $0.98 to $0.73. That's one pair, the reasoning settings differ, and the benchmark is contaminated. Prediction 3 concerns *future* releases, so this doesn't settle it, but it's a warning that "consumption inflation" may not hold for the newest generation.
   - **Pre-registration note:** we've now looked at this data. Prediction 3's threshold must be justified independently of it, and the report must say we saw it first.

## Limits

- **SWE-bench Verified is contaminated** (OpenAI, 2026-02-23), which inflates success rates and so deflates $/success. Cost per *attempt* and tokens per attempt are less affected, but not immune: a model that "remembers" a fix may need fewer steps.
- **One attempt per task.** There's no direct measure of run-to-run noise. Use a bootstrap over tasks for confidence intervals, and treat differences between models smaller than that interval as zero.
- **Dollar cost is at the API list price at run time** (Feb 2026), through whatever route the submitter used. GLM-5, for example, went via OpenRouter. It's what a buyer paid, not cost-to-serve.
- **Mini-SWE-agent is a deliberately minimal scaffold.** Products like Claude Code, Cursor and Codex add retrieval, sub-agents and larger contexts, so absolute token counts here are probably a **lower bound** on product usage [U].
- **Only one scaffold version (v2.0.0) is comparable.** Comparing models over time needs future submissions on v2.x, which aren't guaranteed to be comparable either (a v2.4.2 submission exists).
