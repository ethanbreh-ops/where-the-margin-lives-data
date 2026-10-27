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
