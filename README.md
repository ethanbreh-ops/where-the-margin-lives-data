# Where the Margin Lives: data

Raw-data pipelines for the price-vs-cost project. Source definitions live in
[registry/sources.csv](registry/sources.csv).

## OpenRouter daily snapshot

[.github/workflows/openrouter-snapshot.yml](.github/workflows/openrouter-snapshot.yml)
runs [snapshots/openrouter/snapshot.py](snapshots/openrouter/snapshot.py) every day
at 06:17 UTC and commits the result.

| Path | What it is |
|---|---|
| `data/openrouter/raw/<date>/models.json.gz` | Raw `/api/v1/models` response. Gzipped with mtime 0, so identical content gives identical bytes. |
| `data/openrouter/raw/<date>/endpoints.json.gz` | `{model_id: raw /endpoints response}` for every listed model |
| `data/openrouter/raw/<date>/manifest.json` | Fetch times, counts, failed fetches, sha256 of each file |
| `data/openrouter/normalized/<date>.csv` | One row per (model, host endpoint). Exact-decimal prices in USD per M tokens, plus quantization, uptime and latency. |

The raw files are the audit record. The CSVs are derived from them, so after a
normalizer change you can rebuild them:

```bash
python snapshots/openrouter/snapshot.py --renormalize
```

Run it locally (stdlib only, Python 3.9 or later):

```bash
python snapshots/openrouter/snapshot.py --out data/openrouter
```

Exit codes:
- **0:** OK.
- **2:** the snapshot was written, but more than 5% of endpoint fetches failed. The workflow still commits, then marks the run failed.
- **1:** hard failure. Nothing is committed.

### Known limits
- One sample per day. Intraday price changes are missed.
- Listed prices only. Gives no information about volume or realized price.
- GitHub may delay scheduled runs and, on public repositories, disables them
  after 60 days without repository activity. Check the Actions tab weekly.

## LiteLLM price history

[snapshots/litellm/build_history.py](snapshots/litellm/build_history.py) samples the
last commit of each week to LiteLLM's community price file, then records every
per-token price that was added, removed or changed between consecutive samples.
Each row brackets the change between two commit SHAs, so the exact commit can be
bisected later.

```bash
python snapshots/litellm/build_history.py --out data/litellm --cache <dir outside the repo>
```

Commit dates are not effective dates. Audit against the Wayback Machine before
using this for event timing (see the LITELLM-PRICES entry in the registry).

## SWE-bench agent trajectories

[snapshots/swebench/extract_trajectories.py](snapshots/swebench/extract_trajectories.py)
pulls per-call token usage (input, cache read and write, output, reasoning, cost)
from the public mini-SWE-agent bash-only submissions, and takes each task's result
from the evaluation harness's own reports. It checks every task's summed call
cost against the published cost, and flags upstream data problems in
`data/swebench/submissions.csv`. See
[docs/agent_consumption_public_trajectories.md](docs/agent_consumption_public_trajectories.md).

```bash
python snapshots/swebench/extract_trajectories.py --out data/swebench
```
