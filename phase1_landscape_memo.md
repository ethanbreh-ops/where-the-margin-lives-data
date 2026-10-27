# Where the Margin Lives — Phase 1 Landscape Memo

Date: 2026-10-26. Status: working draft for the research partners, not for publication.

How claims are labelled:
- **[V]**: I checked it against a primary or near-primary source in this pass.
- **[S]**: secondary source only (press, blog, aggregator).
- **[U]**: I couldn't verify it. It comes from memory or is inferred. Check it before using it.

---

## Bottom line (read this first)

1. **The chain as framed is not differentiated.** The layer-by-layer "who makes money" exhibit already exists. The latest example is Wing VC, Aug 2026 [V]. Others include datagravity.dev and many "smile curve" posts. All of them build it from filings at the top and bottom of the stack and from press-reported margins in the middle. Measured cost-to-serve is also covered: SemiAnalysis InferenceX publishes continuous, open, measured $/M tokens across hardware [V]. Measured agent cost per task is covered too: Princeton's HAL [V].
2. **What nobody has done is connect the measured pieces into break-even thresholds and test them against real repricing events.** That is our contribution. The central question should be sharpened to (see B):
   > *For flat-priced AI products, how many tokens per user per period break even against the API price the product pays? Is agentic consumption per task growing faster than quality-adjusted token prices are falling? Does that race explain when and where repricing and limit events happened?*
3. **The model-provider layer for closed models cannot be measured from public data.** Parameter counts, architecture, batch sizes and hardware mix are not disclosed. We measure the open-weight host margin directly. We bound the closed-lab margin and label it as bounded. Treating it as measured would break Principle 4.
4. **Some things are time-critical.** Start daily OpenRouter snapshots now. History we don't capture is lost. The project's most defensible primary dataset is the cross-host price spread for the same model, and it accrues only from the day we start.

---

## A. Prior work we will be compared against

| Work | What it answers well | Method | What it leaves open |
|---|---|---|---|
| **Epoch AI, "LLM inference prices have fallen rapidly but unequally across tasks"** (2025) [V] — [link](https://epoch.ai/data-insights/llm-inference-price-trends) | Quality-adjusted price decline: **9×–900×/yr** depending on the benchmark threshold. About 40×/yr for GPT-4-level GPQA. | For each benchmark threshold, takes the cheapest model at or above it and fits a log-linear regression over time. Prices come from Artificial Analysis plus Epoch's own database. | Price only, no cost. Epoch says margin compression may explain part of the drop but found no clear evidence. The fastest drops are recent and may not last. Price per token, not per task. |
| **Epoch, "The plunging price of thought"** (~47%/quarter, ~13×/yr at constant performance) [S] — [coverage](https://pasqualepillitteri.it/en/news/21044/epoch-ai-ai-prices-fall-47-percent-quarter) | Updated deflation rate | [U] | I couldn't confirm it on Epoch's site. **Mark unverified.** |
| **Erdil (Epoch), "Inference economics of language models"** (arXiv 2506.04645, Jun 2025) [V] — [link](https://arxiv.org/abs/2506.04645) | A theoretical cost-per-token vs serial-speed Pareto frontier covering compute, memory bandwidth, network and latency limits. It optimises over parallelism and batch size. | Analytic roofline-style model. Code reportedly at `ege-erdil/inference-economics` [U]. | Purely theoretical. Not reconciled against market prices or measured throughput. **This is our roofline baseline. We should use it, not rebuild it.** |
| **a16z, "Welcome to LLMflation"** (Appenzeller, Nov 2024) [V] — [link](https://a16z.com/llmflation-llm-inference-cost/) | Headline: ~10×/yr price decline at constant MMLU. GPT-3-class went from $60 to $0.06/M. | Wayback-archived price pages plus MMLU thresholds. | Uses MMLU, which is contaminated, as the authors note. Price, not cost. 2021–24 window. No consumption side. |
| **"The Price of Progress"** (arXiv 2511.23455) [V] — [link](https://arxiv.org/html/2511.23455v1) | Frontier price-per-performance falls ~5–10×/yr. Algorithmic efficiency ~3×/yr. | Multiple benchmarks, frontier models | Much lower than Epoch's range, which shows the index is sensitive to method. **We must pick and defend a definition. This is why we report two indices.** |
| **"Beyond Benchmarks: The Economics of AI Inference"** (arXiv 2510.26136) [V, title only] — [link](https://arxiv.org/abs/2510.26136) | [U] I haven't read it yet | [U] | **Read it this week. It may overlap with us.** |
| **SemiAnalysis InferenceX** (formerly InferenceMAX; v2 covers GB300 NVL72, MI355X, B200, H100) [V] — [dashboard](https://inferencex.semianalysis.com/blog) | **Measured** throughput vs interactivity on current open models (gpt-oss-120B, GLM-5, MiniMax M2.5/M3). Converted to $/M tokens with SemiAnalysis's TCO-based $/GPU-hr (e.g., GB200 at $2.21/GPU-hr in Aug 2025) [V]. Continuous and open source. | Continuous benchmark runs with tuned vLLM/SGLang/TRT-LLM, disaggregated serving and wide expert parallelism. | Costs assume 100% utilisation along the throughput curve and owner TCO, not market rental. No demand side, no API price reconciliation, no application layer. **This removes most of the case for our own large benchmark campaign** (see E). |
| **SemiAnalysis newsletter, AMD vs Nvidia inference cost** [V title] — [link](https://newsletter.semianalysis.com/p/amd-vs-nvidia-inference-benchmark-who-wins-performance-cost-per-million-tokens) | Hardware TCO comparisons | Proprietary TCO model plus benchmarks | Paywalled detail. The TCO model is not public. |
| **Princeton HAL — Holistic Agent Leaderboard** (ICLR 2026) [V] — [link](https://hal.cs.princeton.edu/about) | **Cost-aware agent evaluation.** 21,730 rollouts, 9 models, 9 benchmarks, about $40k [V]. A follow-up paper using HAL data reports a median SWE-bench Verified full run of **$163**, and per-task cost ranging from **$0.08 to $32**, a ~400× spread driven by model and scaffold [S/V via arXiv 2603.23749]. | Standard harness that tracks tokens and cost per run | Cost per attempt at API list price. Doesn't break out cached vs reasoning tokens in a form tied to cost-to-serve. Doesn't link to subscription pricing. **Their logs may be reusable. Ask before we spend our own budget.** |
| **Kapoor et al., "AI Agents That Matter"** (2024) [U — from memory] | Argues agent evaluations must report cost alongside accuracy (Pareto) | Re-evaluation of agent papers | Predecessor of HAL. Cite it for the framing. |
| **Artificial Analysis** [V as a data source via Epoch] | Per-provider price, output speed, TTFT, and an intelligence index for APIs | Black-box API probing | Price and speed, not cost. Historical depth and API terms: [U]. |
| **OpenRouter × a16z "State of AI" (100T tokens)** (Dec 2025; arXiv 2601.10088) [V] — [link](https://a16z.com/state-of-ai/) | Token volume by model, task, region and cohort. Open-weight share about one third. Chinese open-weight share went from ~1% to peaks near 30% [S]. | OpenRouter's internal logs | Critics note that a single large account lifted the May-2025 tool-use metrics, and possible regional-block evasion [S — [Implicator](https://www.implicator.ai/the-100-trillion-token-mirage-what-openrouters-ai-report-actually-reveals/)]. Skewed toward roleplay and price-sensitive traffic. |
| **Wing VC, "Who Makes Money When Inference Gets 10× Cheaper?"** (Zeoli, Aug 2026) [V] — [link](https://www.wing.vc/content/who-makes-money-when-inference-gets-10x-cheaper) | **This is the closest competitor to our exhibit.** Margin by layer: Nvidia 74.9% GAAP GM, TSMC 67.7%. Labs (press): OpenAI ~33% 2025, Anthropic ~40% 2025. Apps (press): Cursor −23% gross in the quarter to Jan 2026. | Scarcity framework plus historical analogies plus compiled reported figures | The author says the demand evidence "shows direction rather than a measured price elasticity" and calls the lab and app margins the "softest" numbers. **There is no bottom-up cost and no reconciliation. That gap is ours.** |
| **datagravity.dev "Who captures value in AI infrastructure"; smile-curve posts** [S] | Layer margin narratives | Compiled from filings and press | Internally inconsistent figures. Treat as directional only. |
| **Press-reported lab margins** (The Information via secondary sources) [S] | Anthropic 2025 GM forecast cut to ~40% (inference costs 23% above plan). ~38% including free users. OpenAI 2025 projected ~46%. OpenAI "compute margin" ~70% by Oct 2025, which is a different metric. — [example](https://www.webpronews.com/anthropic-slashes-2025-margin-forecast-to-40-amid-ai-cost-surge/) | Leaked internal financials | **The definitions differ (gross vs compute margin, with or without free users).** Exactly the conflation Principle 4 forbids. Use them only as secondary anchors, with the definition named. |
| **Academic serving systems:** vLLM/PagedAttention (SOSP'23), Sarathi-Serve and DistServe (OSDI'24), Splitwise (ISCA'24), LLM-Viewer roofline survey (Yuan et al. 2024) [U — from memory, standard literature] | Throughput/latency mechanics: KV paging, chunked prefill, prefill/decode disaggregation | Systems papers | No economics. Configs are often older models. Use for method citations only. |
| **Cost calculators** (Introl, Spheron, inference.net guides, many others) [V that they exist] | $/M = ($/hr) ÷ (tok/s × 3600) | Arithmetic on assumed throughput | Assumed utilisation and throughput. **This is the "token calculator" we said we would not build.** |
| **LiteLLM `model_prices_and_context_window.json`; simonw/llm-prices** [U — from memory] | Machine-readable API price tables | Community maintained | **The git history is a raw price time series.** Possibly the best source for V3 (see C). |

**Coverage matrix: what exists and what is open**

| Chain link | Already done well by | Open |
|---|---|---|
| GPU $/hr (market) | Silicon Data SDH100RT index [V] | Low-cost raw history |
| GPU $/hr → $/M tokens (measured) | **InferenceX** | Utilisation under real demand and SLOs |
| $/M cost vs $/M price (open-weight) | Nobody systematically | **Open: V1 is novel** |
| Price index (quality-adjusted) | Epoch, a16z, Price of Progress | Frontier vs quality-adjusted divergence. Per-task rather than per-token. |
| Tokens per task (agents) | HAL (cost per run) | Token-class breakdown over successive model releases with a fixed scaffold |
| App price vs API cost (break-even) | Anecdotes and press | **Open: V4 is novel** |
| Layer margins | Wing VC et al. (press-based) | Reconciliation against audited filings with consistent definitions |

---

## B. Verdict on differentiation

**As written, it is not differentiated enough.** "Build a reconciled price-vs-cost chain" will be read as "Wing VC's table, with better footnotes." Practitioners already know the shape: chips fat, neoclouds thin, labs improving, apps squeezed. Our bottom-up layer is also weaker than InferenceX at what InferenceX does.

**What is differentiated** is the mechanism and the test. Nobody has measured both sides of the race on the same tasks:
- the numerator: quality-adjusted $/token falling
- the denominator: tokens per successful task rising

Nobody has then priced the result against application plan prices and checked whether it predicts dated real events.

**Proposed sharper central question:**
> **"Does token deflation outrun consumption inflation?"** For a fixed set of agentic tasks, how does cost per *successful task* move across model generations? Combine two pieces: (i) the quality-adjusted price index and (ii) measured tokens per task. At what usage percentile does a flat-priced plan go underwater? Did the observed repricing events (Copilot premium-request enforcement on 2025-06-18, Cursor's 2025-06-16 Pro change, Claude Code weekly limits announced 2025-07-28 and effective 2025-08-28, Copilot's move to usage-based billing from 2026-06-01) happen when and where that threshold predicts?

The chain survives as **the supporting exhibit**, but with a different emphasis. It is measured where the public data allows (open-weight hosts, GPU rental, applications' API-denominated costs) and **bounded** where it doesn't (closed-lab cost to serve). It is not the headline.

Two secondary findings are cheap and novel enough to keep:
1. **The open-weight host spread.** For the same weights, the OpenRouter price vs our bottom-up cost at derived utilisation is the only directly measurable "provider margin" in the stack. It is also the real-world test of V1.
2. **The GPU-owner margin under consistent definitions.** CoreWeave's ~72% "gross margin" [V: FY2025 cost of revenue $1,453M = 28% of revenue, [10-K](https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm)] sits above a cost line that, per the 10-K text, is driven by rent and utilities. **I believe most GPU depreciation is excluded from cost of revenue and reported in a separate line [U — confirm in the 10-K income-statement captions].** If so, the commonly quoted figure is not comparable to Nvidia's GAAP gross margin. Exactly the Principle 4 point, documented from filings.

---

## C. Raw sources: availability, access, cost, biases, dead ends

| Source | Exists in usable form? | Access / cost | Time span | Biases / caveats | Verdict |
|---|---|---|---|---|---|
| **GPU spec sheets** (H100/H200/B200/GB200/MI300X/MI355X) | Yes | Vendor PDFs, free | n/a | Peak FLOPs are marketing numbers (sparsity). Use dense FP8/BF16. Achieved bandwidth is about 80–90% of peak [U]. | ✅ |
| **Open-weight model configs** (`config.json` on Hugging Face) | Yes | Free | n/a | Gives layers, heads, KV heads, hidden size, experts and active params, so exact KV bytes per token. MLA (DeepSeek-style) needs special handling. | ✅ |
| **Own serving benchmarks** (vLLM/SGLang on rented H100/H200) | We generate it | ~$2–3.5/GPU-hr neocloud (H100 neocloud index ~$2.00–2.26 in late 2025 [V, [Silicon Data](https://www.silicondata.com/blog/h100-rental-market-update-september-2025)]) | n/a | Our tuning will lag specialist hosts (FP4, speculative decoding, disaggregation, wide EP). **That will bias our cost upward. Treat it as an upper bound.** | ✅, but **scale it down** and reproduce InferenceX instead of competing with it |
| **InferenceX data** | Yes, public dashboard. Repo [U] | Free | ~Oct 2025 onward | Owner-TCO $/hr assumption. No utilisation discount. | ✅ **Primary throughput source.** Ours validates it (V2). |
| **MLPerf Inference** (MLCommons) | Yes | Free | v1–v5.x. **v6.0 not confirmed in this search [U]** | Heavily tuned vendor submissions (mostly TRT-LLM), offline/server scenarios, older models (Llama 2 70B, Llama 3.1 405B; DeepSeek-R1 added in v5.1 [U]) | ✅ for V2 with a wide tolerance |
| **GPU rental price time series** | Partly | **Silicon Data SDH100RT**: daily from May 2025, via Bloomberg, API or Kaiko, **paid** [V]. Free fragments on their blog. Vast.ai/RunPod/Lambda price pages via Wayback. | Index from May 2025. Wayback from ~2023 | Indices mix contract types. List prices ≠ contract prices (multi-year reserved rates are far lower and private) [U]. | ⚠️ **Free history is thin.** Either license SD or build our own from Wayback list prices. State that we observe spot/on-demand, not contract prices. |
| **Archived API price pages (Wayback CDX)** | Yes | Free. CDX API `web.archive.org/cdx/search/cdx?url=...` | 2020– | Some pages are JS-rendered (blank snapshots). Gaps between captures blur event dates by days. | ✅ Cross-check against the LiteLLM git history |
| **LiteLLM price JSON git history** [U that history is complete] | Likely | Free (`git log -p`) | ~2023– | Community-entered, occasional errors and lags | ✅ **Strong. Use it as the primary machine-readable series. Wayback is the audit.** |
| **OpenRouter per-model, per-provider prices** | Yes, current only: `/api/v1/models` [V], per-model endpoints listing per-provider pricing [U on exact path] | Free | **Current snapshot only. No official history [U].** | Prices are pass-through per the official FAQ [V]. Some third parties claim a ~10% markup [S]. | ✅ **Start the daily cron now.** Backfill sparsely from Wayback. |
| **OpenRouter token volume** | Partly: rankings and model-page charts. API access to history [U] | Free (scrape) | ~2023– on charts | Not the market: skews to roleplay, open-weight and price-sensitive developers. Excludes direct lab and enterprise traffic. A single large account can move the series [S]. | ⚠️ Use for within-OpenRouter share shifts only, never for total demand |
| **Own instrumented agent runs** | We generate it | API cost (see E) | n/a | Scaffold choice drives cost ~400× [S]. Our scaffold ≠ Cursor's or Claude Code's. | ✅ |
| **SWE-bench Verified as the task set** | Yes | Free | 2024– | **OpenAI stopped reporting it on 2026-02-23**, citing contamination and flawed tests. Its audit found 59.4% of 138 hard tasks had flawed tests [V — [OpenAI](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)]. Epoch rates it "Flawed" [V]. | ⚠️ **Contamination inflates success rate, which deflates cost per success.** Use SWE-bench Pro (public split) as primary [U on its size and licence]. Keep a Verified subset only for continuity with HAL. |
| **Public agent trajectories** (SWE-bench `experiments` repo, HAL logs) | Yes [U on token-class detail] | Free | 2024– | Submitters self-select. Token logs are often incomplete (cached and reasoning tokens missing). | ✅ For the cross-model trend. Our own runs fill the gaps. |
| **User-published usage logs** (e.g., `ccusage` output for Claude Code, Cursor usage screenshots) | Scattered | Free (scrape GitHub, Reddit, X) | 2025– | **Severe selection bias** (heavy users post, light users don't). API-equivalent $ uses list prices. | ⚠️ Good for the tail shape. **Can't identify the full distribution.** Anchor with company statements such as Anthropic's "<5% of subscribers" affected [V]. |
| **SEC filings** (CoreWeave 10-K FY2025 [V], Nebius 20-F, Nvidia 10-K, MSFT/AMZN/GOOGL/META 10-K/Q) | Yes | Free (EDGAR) | 2024– | Hyperscalers don't break out GPU-cloud margin. Depreciation useful-life choices (CoreWeave 6y [S, unverified], Nebius 4y [S], Lambda 5y [S]) swing margin a lot. | ✅ for V5. Hyperscaler AI margin is a **dead end** for point estimates; only bounds are possible. |
| **Dated archives of app pricing and limits** (Cursor, Copilot, Claude, ChatGPT, Windsurf) | Yes | Wayback, changelogs (GitHub changelog [V]), forums | 2024– | Limits are often undisclosed ("~40–80 h Sonnet/week" is press-estimated [S]) | ✅ for V4 event dates. ⚠️ for limit levels. |
| **Diurnal demand curve** | **No public measured source [U]** | n/a | n/a | n/a | ❌ **Dead end as observed data.** We can proxy it with OpenRouter hourly latency/throughput scraped over 4+ weeks (load shows up as latency) or published anecdotes. The demand curve becomes an **assumed** input with a sensitivity range, and the queueing simulation gives utilisation *conditional* on it. Label it honestly. |
| **Closed-model architecture** (param count, active params, hardware) | **No** | n/a | n/a | n/a | ❌ **Dead end.** We can't compute closed-lab cost to serve. Only bounds: an open-weight analogue at similar price and speed, plus press margins. |
| **Private-company margins** (Cursor, Perplexity, Replit, labs) | Press only | The Information (paid), secondary sources | 2024– | Definitions inconsistent. Unaudited. | Secondary anchors only, labelled as such |

---

## D. Hypotheses A–E: verdicts

| Hypothesis | Verdict | Why / how it is tested |
|---|---|---|
| **A. Margin paradox** (token prices fall but app/lab margins don't improve, because consumption per task rises) | ✅ **Survives. It becomes the central question.** | Testable: quality-adjusted price index (V3 backtest) × measured tokens per successful task across model generations with a fixed scaffold. Explains events (V4). |
| **B. Power users** (heavy-tailed usage makes flat pricing unprofitable) | ➡️ **Sub-analysis of A** | The break-even percentile needs the usage distribution. Data is self-selected (C), so we fit lognormal/Pareto to the tail only. Calibrate to the firm-stated anchor "<5% of subscribers affected" [V]. Report it as conditional. **Pre-commit:** if the Pareto vs lognormal choice moves the break-even percentile by more than 2× and the data can't discriminate (Vuong test), we report a range and make no point claim. |
| **C. Routing** (cheap-model routing captures margin) | ❌ **Cut, park as optional** | Savings depend on proprietary router quality. Testing it needs a router evaluation, which is a separate project. Revive it only if our agent logs show a large share of steps that a cheap model solves at equal success (a cheap probe in our own runs). |
| **D. Self-hosting** (self-host beats API above some utilisation) | ➡️ **Sub-analysis. It falls out of V1 for free.** | Break-even utilisation = API price ÷ (bottom-up cost at 100% util). One chart. Novel only where it uses derived utilisation, not assumed. |
| **E. Agents** (cost per successful task = cost per attempt ÷ success rate, rising) | ✅ **Survives. It is the "denominator" half of A.** | Our own logs. Must survive two checks: run-to-run variance and contamination (see G). |

---

## E. Measurement plan

### E1. Serving benchmarks (smaller than originally imagined; validation, not discovery)

Purpose: (1) reproduce InferenceX and MLPerf for comparable configurations (V2). (2) Produce our own throughput-vs-concurrency curves that feed the queueing simulation for the V1 models.

| # | Model (open weights) | Hardware | Engine | Precision | Workloads (ISL/OSL) | Why |
|---|---|---|---|---|---|---|
| B1 | Llama 3.1 8B Instruct | 1×H100 SXM | vLLM (pinned version) | BF16, FP8 | 1k/1k, 8k/1k | Cheap engine calibration. MLPerf v5.1 comparable [U] |
| B2 | Llama 3.3 70B Instruct | 4×H100 TP4 and 2×H200 TP2 | vLLM and SGLang | FP8 | 1k/1k, 8k/1k, 32k/1k (agentic long context) | MLPerf Llama-2-70B lineage. Long-context KV pressure |
| B3 | gpt-oss-120B | 1×H100 | vLLM | MXFP4 (native) | 1k/1k, 8k/1k | **Matches an InferenceX config (1k/1k) [V].** Heavy OpenRouter volume [U] |
| B4 | One frontier-class open MoE that is on InferenceX *and* has ≥5 OpenRouter hosts (candidates: GLM-5.x or MiniMax M2.5/M3 [V on InferenceX]; DeepSeek-V3.x [U]) | 8×H200 | SGLang (EP) | FP8 | 8k/1k, 32k/2k | The V1 model that matters. Closest to real agentic serving |

Protocol:
- Sweep concurrency at 1, 2, 4 … 256 until the p95 TPOT SLO breaks.
- Record TTFT, TPOT, p50/p95/p99, throughput (input and output tok/s), KV usage and prefix-cache hit rate.
- Workloads: fixed-seed synthetic plus one replayed trace from our own agent logs (real prefix reuse).
- Three repeats per point.
- Pin and record the engine version, driver, CUDA version, and the exact `vllm serve` / `sglang` arguments.

Roofline cross-check:
- Decode bound: tok/s ≤ (HBM BW × efficiency) ÷ (active-weight bytes + KV bytes read per token × batch), per batch.
- Prefill bound: FLOPs ≈ 2 × active params × tokens.
- Any measured point above roofline means a bug. A point below 50% of roofline needs an explanation.

**Compute budget:**
- B1: ~8 h × $2.2 ≈ $20
- B2: (4×H100 ~10 h ≈ $90) + (2×H200 ~10 h ≈ $70) ≈ $160
- B3: ~8 h ≈ $20
- B4: 8×H200 ~25 h × ~$28/h ≈ $700
- Setup waste and reruns ×1.5
- **≈ $1,400 total, ~60 GPU-node-hours of wall time, ~40 person-hours.** Prices [U] until quotes are snapshotted into the registry.

### E2. Agent runs

- **Task set:** 60 tasks.
  - 40 from SWE-bench Pro public, stratified by difficulty and repository.
  - 20 from the SWE-bench Verified subset that HAL ran, for comparability.
  - Freeze the task IDs in the pre-registration.
- **Scaffold:** one fixed open scaffold (mini-SWE-agent or OpenHands, version pinned), with fixed step and token caps.
- **Models:** ≥2 successive generations from each of 2 labs, plus 2 open-weight models served via OpenRouter. Example: Claude prior-gen/current-gen, GPT prior-gen/current-gen, 2 open-weight. Exact list frozen at pre-registration.
- **Seeds:** 3 per (task, model), giving **~1,440 runs** at 8 models.
- **Budget:**
  - HAL's median is about $0.33/task on Verified ($163 per 500), with the most expensive configuration at $32/task [S].
  - Assume an average of $1.50/attempt across the mix (frontier reasoning models dominate): **≈ $2,200**, with a cap of $3,000.
  - Run a 5-task × 2-model pilot first (~$30) to re-price this.
- **People-time:** ~30 h setup plus ~20 h monitoring and QA.

**Logging schema** (one row per LLM call; trajectory table keyed by run):

```
run_id, task_id, task_source, model_id, model_snapshot_date, provider, scaffold, scaffold_version,
seed, step_idx, call_ts_utc, input_tokens_uncached, input_tokens_cache_read, input_tokens_cache_write,
output_tokens_visible, output_tokens_reasoning, tool_calls, tool_name, retries (http/parse/rate-limit),
latency_ms_ttft, latency_ms_total, list_price_in, list_price_cache_read, list_price_cache_write,
list_price_out, price_snapshot_id, cost_usd_calc, http_status, error_class
-- per run:
run_id, resolved (bool), tests_passed, wall_clock_s, total_steps, terminated_reason (done/step_cap/token_cap/error)
```

Every price joins to `price_snapshot_id` in the source registry, so the API price is never hardcoded.

### E3. Data pipelines (cheap, start now)

- Daily OpenRouter `/models` plus per-model endpoint snapshots, written to a git repo through a GitHub Actions cron (free).
- Weekly Wayback CDX pulls for ~25 pricing pages (labs, apps, neoclouds).
- LiteLLM git history extraction.
- EDGAR pulls.
- ~25 person-hours, $0.

### E4. Total Phase-2/3 budget

| Item | $ | Hours |
|---|---|---|
| Serving benchmarks | ~1,400 | ~40 |
| Agent runs | ~2,200 (cap 3,000) | ~50 |
| Data (optional SDH100RT licence [U price]) | 0 / ? | ~25 |
| Model build (Excel + Python + diff harness) | 0 | ~80 |
| **Total** | **~$3.6k (cap ~$4.5k ex-licence)** | **~195 h** |

---

## F. Draft pre-registered predictions (finalise before analysis; numbers are placeholders to stress-test)

Each one is dated, has a metric we can compute from the registry, and has a clear falsifier. To be checked at +3 and +6 months from publication.

1. **Host spread persists.** For the 5 open-weight models with the most OpenRouter hosts, the ratio of the median-host to the cheapest-host blended price (3:1 input:output) stays **≥2.0×** at both checkpoints. *Falsified if* it is below 2.0× for ≥3 of the 5.
2. **The frontier doesn't deflate.** The list price of the flagship model at each of OpenAI, Anthropic and Google (blended 3:1, $/M) falls **≤25%** over 6 months. Meanwhile our quality-adjusted index (fixed-capability threshold) falls **≥40%**. *Falsified if* the frontier falls more than 25%, or quality-adjusted falls less than 40%.
3. **Consumption inflation.** For the next frontier release from at least 2 of those 3 labs, on our frozen task set and scaffold, the median total tokens per *successful* task is **≥1.2×** the predecessor's. *Falsified if* it is below 1.2× for both.
4. **Flat-rate erosion.** At least one of Cursor, Claude (Pro/Max), ChatGPT/Codex, Copilot or Windsurf will tighten an agentic usage limit or move a tier to usage-based billing within 6 months. **Warning: the base rate is high, so this one is weak.** Upgrade it by naming the product our break-even model flags as most underwater, and predicting *that* one.
5. **GPU rent stays range-bound.** The neocloud H100 index (SDH100RT or our own Wayback-built proxy) stays within **$1.70–2.60/GPU-hr** at both checkpoints. *Falsified if* it leaves the band.

Drop or rewrite any prediction that the Phase 2 data shows to be near-certain or near-impossible. A prediction that cannot fail is not one.

---

## G. Five largest execution risks, with kill or pivot criteria

1. **V1 fails: our bottom-up cost exceeds OpenRouter's cheapest host.** Likely, because hosts use FP4, speculative decoding, disaggregation, wide expert parallelism and better batching than our setup.
   *Pivot:* substitute InferenceX throughput for the cost layer. Our benchmarks become V2 evidence only.
   *Kill V1 as a finding if* the gap is still more than 2× unexplained after using InferenceX. The fallback becomes "hosts are pricing below plausible cost", which is itself a finding, but it requires subsidy evidence.
2. **The closed-lab layer can't be bounded usefully.** If the analogue-model bound on closed-lab cost to serve is wider than 3×, we publish no closed-lab margin at all. The chain then becomes open-weight plus application only. Say so in the limitations section.
3. **Agent cost signal is swamped by noise or contamination.** *Kill the consumption-trend claim (prediction 3, hypothesis E) if* seed-to-seed variance in tokens per success exceeds the between-generation difference (bootstrap 90% CI overlaps 1.0×). Also, if Pro and Verified success rates diverge by more than 20 percentage points for the same model, report Pro only and treat Verified as contaminated.
4. **V4 is not identifiable.** The events had stated non-margin causes (Anthropic cited account sharing, reselling and 24/7 background use [V]), they cluster in time, and the usage distribution is self-selected.
   *Pre-commit:* the test is whether the predicted break-even percentile is consistent with the firm-stated share affected (e.g., <5%), within a factor of 2. If it isn't, **we report that it doesn't explain the event.** No post-hoc rescue.
5. **Scope and capacity.** One person, ~195 hours, eight validation gates. V7 (practitioner reviewers) and V8 (agreement to the cent) are the easiest to under-deliver.
   - *V8 scope fix:* the to-the-cent agreement applies to all deterministic scenarios. Monte Carlo runs in Python only, because Excel can't reproduce numpy's random number generator. Excel checks summary statistics within a stated tolerance.
   - *Pivot:* if Phase 3 runs more than 4 weeks late, drop B4 and hypothesis D, and publish the narrower question.
   - *Recruit V7 reviewers now:* one inference engineer, one sell-side semis analyst, one AI-application finance lead, ideally one person from Epoch or HAL.

---

## H. Phased roadmap, with gates

| Phase | Weeks | Content | Exit gate |
|---|---|---|---|
| 1 | done | Landscape (this memo) | Sharpened question agreed |
| 2 | 1–3 | Source registry, price pipelines (OpenRouter cron, LiteLLM history, Wayback CDX), filings extraction, freeze the task set and model list, **freeze predictions and the V3 cutoff date** | **V6 drafted and frozen; V3 cutoff fixed before price data is examined after that date. V5 anchor table built (CoreWeave/Nebius/Nvidia, definitions explicit).** |
| 3 | 3–6 | Serving benchmarks B1–B4, roofline cross-check, queueing simulation with an assumed diurnal curve and its sensitivity | **V2** (within ±15% of InferenceX for matched configs; ±25% vs MLPerf, given the engine difference), then **V1** |
| 4 | 4–8 | Agent pilot, then the full 1,440 runs | Variance check (risk 3). Cost per success with CIs |
| 5 | 7–10 | Chain model: Excel (inputs/calcs/outputs/checks) plus Python, diff harness, tornado and Monte Carlo | **V8**, **V5** |
| 6 | 9–11 | Price indices with backtest, elasticity/event studies (within-model host price variation as the cleaner design), break-even vs events | **V3**, **V4** |
| 7 | 11–14 | Report, review | **V7**, publish with **V6** |
| 8 | after | Simulator on the Python core | Only if V1–V8 pass |

### First five tasks this week

1. **Start the daily OpenRouter snapshot cron.** Capture `/api/v1/models` plus per-model provider endpoints into a git repo through GitHub Actions. Day 1. Every day of delay is unrecoverable data.
2. **Build the price time series from the LiteLLM git history and audit it against Wayback CDX** for OpenAI, Anthropic and Google pricing pages. Report coverage gaps and JS-blank snapshots.
3. **Read InferenceX's methodology and repo, and read arXiv 2510.26136** ("Beyond Benchmarks"). Decide which 2 InferenceX configs B3/B4 will reproduce. Confirm or kill the B4 model choice against the OpenRouter host count.
4. **Extract V5 anchors from the CoreWeave FY2025 10-K and the Nebius 20-F.** Get the exact cost-of-revenue definition, where GPU depreciation sits, useful life, and depreciation as a % of revenue. Build a GPU-owner margin bridge from "reported gross margin" down to "gross margin incl. depreciation".
5. **Stand up the source-registry schema** (the fields from Principle 3, with the snapshot hash). Run the **5-task × 2-model agent pilot (~$30)** to re-price the agent budget and test the logging schema end to end.

---

## Sources consulted in this pass

- Epoch AI price trends: https://epoch.ai/data-insights/llm-inference-price-trends
- Epoch 2025 roundup: https://epoch.ai/blog/top-10-data-insights-and-gradient-updates-of-2025
- Epoch "47%/quarter" (secondary, unverified): https://pasqualepillitteri.it/en/news/21044/epoch-ai-ai-prices-fall-47-percent-quarter
- Erdil, Inference economics: https://arxiv.org/abs/2506.04645 · https://epoch.ai/publications/inference-economics-of-language-models
- Price of Progress: https://arxiv.org/html/2511.23455v1
- Beyond Benchmarks: https://arxiv.org/pdf/2510.26136
- a16z LLMflation: https://www.a16z.com/llmflation-llm-inference-cost
- a16z/OpenRouter State of AI: https://www.a16z.com/state-of-ai · https://www.alphaxiv.org/overview/2601.10088 · critique: https://www.implicator.ai/the-100-trillion-token-mirage-what-openrouters-ai-report-actually-reveals/
- SemiAnalysis InferenceX: https://inferencex.semianalysis.com/blog · https://inferencex.semianalysis.com/compare-per-dollar/gptoss-120b-gb200-vs-mi355x · https://newsletter.semianalysis.com/p/amd-vs-nvidia-inference-benchmark-who-wins-performance-cost-per-million-tokens
- HAL: https://hal.cs.princeton.edu/about · https://mlanthology.org/iclr/2026/kapoor2026iclr-holistic/ · https://arxiv.org/pdf/2603.23749
- Wing VC: https://www.wing.vc/content/who-makes-money-when-inference-gets-10x-cheaper
- datagravity: https://www.datagravity.dev/p/who-captures-value-in-ai-infrastructure
- Silicon Data: https://www.silicondata.com/products/silicon-index?gpu=h100 · https://www.silicondata.com/blog/h100-rental-market-update-september-2025 · https://www.silicondata.com/blog/h100-hyperscaler-index-april-2026
- CoreWeave FY2025 10-K: https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm · depreciation lives (secondary): https://beancount.io/it/blog/2026/07/10/gpu-cloud-depreciation-schedules-guide
- Lab margins (secondary): https://www.webpronews.com/anthropic-slashes-2025-margin-forecast-to-40-amid-ai-cost-surge/ · https://www.saastr.com/have-ai-gross-margins-really-turned-the-corner/
- SWE-bench Verified retirement: https://openai.com/es-ES/index/why-we-no-longer-evaluate-swe-bench-verified/ · https://epoch.ai/benchmarks/swe-bench-verified/review
- Cursor: https://techcrunch.com/2025/07/07/cursor-apologizes-for-unclear-pricing-changes-that-upset-users/ · https://simonwillison.net/2025/Jul/5/cursor-clarifying-our-pricing
- Claude Code limits: https://feeds.simonwillison.net/2025/Jul/28/anthropic · https://en.ain.ua/2025/07/30/anthropic-introduces-weekly-limits-for-claude-code/
- Copilot: https://github.blog/changelog/2025-06-18-update-to-github-copilot-consumptive-billing-experience/ · https://www.theregister.com/2025/06/20/github_begins_enforcing_premium_request/ · https://docs.github.com/en/copilot/reference/copilot-billing/request-based-billing-legacy/copilot-requests
- OpenRouter docs: https://openrouter.ai/docs/faq.md
