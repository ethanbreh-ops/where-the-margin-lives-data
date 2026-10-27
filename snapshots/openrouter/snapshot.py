"""Daily snapshot of OpenRouter model and per-provider endpoint pricing.

Writes, for the UTC date of the run:
  data/openrouter/raw/<date>/models.json.gz      raw /api/v1/models response
  data/openrouter/raw/<date>/endpoints.json.gz   {model_id: raw /endpoints response}
  data/openrouter/raw/<date>/manifest.json       fetch metadata, failures, sha256 of raw files
  data/openrouter/normalized/<date>.csv          one row per (model, provider endpoint)

Raw files are the audit record; the CSV is derived from them and can be rebuilt
with --renormalize. Prices are kept as exact decimals (no floats) and converted
from $/token to $/M tokens.

Stdlib only, so it runs on a bare GitHub Actions runner.
"""

import argparse
import csv
import gzip
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

API = "https://openrouter.ai/api/v1"
USER_AGENT = "where-the-margin-lives-research/0.1 (daily price snapshot)"
SCRIPT_VERSION = "1"

# Per-token price fields converted to $/M tokens. Anything else in `pricing`
# (per-request, per-image, web search, ...) is kept verbatim in pricing_other.
PER_TOKEN_FIELDS = [
    "prompt",
    "completion",
    "input_cache_read",
    "input_cache_write",
    "input_cache_write_1h",
    "internal_reasoning",
]

CSV_COLUMNS = [
    "snapshot_date",
    "fetched_at_utc",
    "model_id",
    "base_model_id",
    "variant",
    "variant_same_as_base",
    "model_name",
    "model_created_utc",
    "provider_name",
    "endpoint_tag",
    "endpoint_name",
    "quantization",
    "service_tier",
    "context_length",
    "max_completion_tokens",
    "max_prompt_tokens",
    *[f"usd_per_m_{f}" for f in PER_TOKEN_FIELDS],
    "discount",
    "pricing_other",
    "status",
    "uptime_last_5m",
    "uptime_last_30m",
    "uptime_last_1d",
    "latency_last_30m",
    "throughput_last_30m",
    "supports_implicit_caching",
    "supports_tools",
    "supports_reasoning",
]

MAX_FAILURE_RATE = 0.05


def fetch_json(url, retries=4, timeout=60):
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
            last_err = e
            # 429 and 5xx are worth retrying; a 404 is not
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {last_err}")


def endpoints_path(model):
    # links.details points at the canonical slug; fall back to the public id
    details = (model.get("links") or {}).get("details")
    if details:
        return details.removeprefix("/api/v1")
    return f"/models/{model['id']}/endpoints"


def per_m(value):
    """$/token string -> $/M tokens string, exact. Blank if absent or unparseable."""
    if value in (None, ""):
        return ""
    try:
        return format((Decimal(str(value)) * 1_000_000).normalize(), "f")
    except InvalidOperation:
        return ""


def normalize(snapshot_date, fetched_at, models, endpoints_by_model):
    created = {m["id"]: m.get("created") for m in models}
    rows = []
    for model_id, resp in sorted(endpoints_by_model.items()):
        data = (resp or {}).get("data") or {}
        # Variants such as ":batch" or ":free" sometimes return exactly the base
        # model's endpoints; flag them so analyses don't double-count hosts.
        base_id, _, variant = model_id.partition(":")
        same_as_base = ""
        if variant and base_id in endpoints_by_model:
            base_eps = ((endpoints_by_model[base_id] or {}).get("data") or {}).get("endpoints")
            same_as_base = data.get("endpoints") == base_eps
        for ep in data.get("endpoints") or []:
            pricing = dict(ep.get("pricing") or {})
            discount = pricing.pop("discount", "")
            other = {k: v for k, v in pricing.items() if k not in PER_TOKEN_FIELDS}
            params = set(ep.get("supported_parameters") or [])
            ts = created.get(model_id)
            rows.append({
                "snapshot_date": snapshot_date,
                "fetched_at_utc": fetched_at,
                "model_id": model_id,
                "base_model_id": base_id,
                "variant": variant,
                "variant_same_as_base": same_as_base,
                "model_name": ep.get("model_name") or data.get("name", ""),
                "model_created_utc": (
                    datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else ""
                ),
                "provider_name": ep.get("provider_name", ""),
                "endpoint_tag": ep.get("tag", ""),
                "endpoint_name": ep.get("name", ""),
                "quantization": ep.get("quantization") or "",
                "service_tier": ep.get("service_tier") or "",
                "context_length": ep.get("context_length", ""),
                "max_completion_tokens": ep.get("max_completion_tokens", ""),
                "max_prompt_tokens": ep.get("max_prompt_tokens", ""),
                **{f"usd_per_m_{f}": per_m(pricing.get(f)) for f in PER_TOKEN_FIELDS},
                "discount": discount,
                "pricing_other": json.dumps(other, sort_keys=True) if other else "",
                "status": ep.get("status", ""),
                "uptime_last_5m": ep.get("uptime_last_5m", ""),
                "uptime_last_30m": ep.get("uptime_last_30m", ""),
                "uptime_last_1d": ep.get("uptime_last_1d", ""),
                "latency_last_30m": ep.get("latency_last_30m", ""),
                "throughput_last_30m": ep.get("throughput_last_30m", ""),
                "supports_implicit_caching": ep.get("supports_implicit_caching", ""),
                "supports_tools": "tools" in params,
                "supports_reasoning": "reasoning" in params,
            })
    return rows


def write_gz_json(path, obj):
    # mtime=0 so identical content gives identical bytes (and sha256)
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    with open(path, "wb") as f:
        with gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
            gz.write(raw)


def read_gz_json(path):
    with gzip.open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_text(path, text):
    # Always LF, so sha256 matches whether written on Windows or Linux
    with open(path, "w", newline="\n", encoding="utf-8") as f:
        f.write(text)


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def snapshot(out_root, workers):
    started = datetime.now(timezone.utc)
    snapshot_date = started.date().isoformat()
    fetched_at = started.isoformat(timespec="seconds")
    raw_dir = out_root / "raw" / snapshot_date
    raw_dir.mkdir(parents=True, exist_ok=True)
    (out_root / "normalized").mkdir(parents=True, exist_ok=True)

    models_resp = fetch_json(f"{API}/models")
    models = models_resp["data"]
    if (models_resp.get("links") or {}).get("next"):
        # Has never paginated so far; fail loudly rather than silently truncate
        raise RuntimeError("models response is paginated; snapshot.py needs updating")

    endpoints, failures = {}, {}

    def one(model):
        try:
            return model["id"], fetch_json(API + endpoints_path(model)), None
        except Exception as e:
            return model["id"], None, str(e)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for model_id, resp, err in pool.map(one, models):
            if err:
                failures[model_id] = err
            else:
                endpoints[model_id] = resp

    write_gz_json(raw_dir / "models.json.gz", models_resp)
    write_gz_json(raw_dir / "endpoints.json.gz", endpoints)
    rows = normalize(snapshot_date, fetched_at, models, endpoints)
    csv_path = out_root / "normalized" / f"{snapshot_date}.csv"
    write_csv(csv_path, rows)

    finished = datetime.now(timezone.utc)
    manifest = {
        "source": "openrouter",
        "script_version": SCRIPT_VERSION,
        "snapshot_date": snapshot_date,
        "fetched_at_utc": fetched_at,
        "finished_at_utc": finished.isoformat(timespec="seconds"),
        "models_listed": len(models),
        "models_with_endpoints": len(endpoints),
        "endpoint_rows": len(rows),
        "failures": failures,
        "sha256": {
            "models.json.gz": sha256(raw_dir / "models.json.gz"),
            "endpoints.json.gz": sha256(raw_dir / "endpoints.json.gz"),
            f"normalized/{snapshot_date}.csv": sha256(csv_path),
        },
    }
    write_text(raw_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    rate = len(failures) / max(len(models), 1)
    print(
        f"{snapshot_date}: {len(models)} models, {len(rows)} endpoint rows, "
        f"{len(failures)} failures ({rate:.1%})"
    )
    return 0 if rate <= MAX_FAILURE_RATE else 2


def renormalize(out_root):
    """Rebuild every normalized CSV from the raw snapshots."""
    for raw_dir in sorted((out_root / "raw").iterdir()):
        manifest = json.loads((raw_dir / "manifest.json").read_text(encoding="utf-8"))
        models = read_gz_json(raw_dir / "models.json.gz")["data"]
        endpoints = read_gz_json(raw_dir / "endpoints.json.gz")
        rows = normalize(manifest["snapshot_date"], manifest["fetched_at_utc"], models, endpoints)
        csv_name = f"normalized/{manifest['snapshot_date']}.csv"
        write_csv(out_root / csv_name, rows)
        # Raw hashes stay as recorded at fetch time; only the derived CSV's hash changes
        manifest["endpoint_rows"] = len(rows)
        manifest["sha256"][csv_name] = sha256(out_root / csv_name)
        manifest["renormalized_with_script_version"] = SCRIPT_VERSION
        write_text(raw_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"{raw_dir.name}: {len(rows)} rows")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="data/openrouter", type=Path)
    p.add_argument("--workers", default=4, type=int)
    p.add_argument("--renormalize", action="store_true", help="rebuild CSVs from raw only")
    args = p.parse_args()
    sys.exit(renormalize(args.out) if args.renormalize else snapshot(args.out, args.workers))


if __name__ == "__main__":
    main()
