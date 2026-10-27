"""API list-price history from the git history of LiteLLM's price file.

LiteLLM keeps a community-maintained JSON of per-token prices for ~4,000
model/provider keys (BerriAI/litellm, model_prices_and_context_window.json).
Every commit to it is a dated observation, so its git log is a raw price series.

Writes:
  data/litellm/commits.csv        every commit touching the file
  data/litellm/price_changes.csv  one row per (model key, price field) change
                                  between consecutive weekly samples

Method: take the last commit of each ISO week (UTC committer date), read the
file at that commit, and diff token-price fields against the previous sample.
Each change row brackets the change between two commits (prev_sha, sha), so an
exact commit can be found later by bisecting only that interval.

Caveat: a commit date is when someone updated LiteLLM, not when the provider
changed its price. The lag is unknown and must be audited against Wayback.

Downloads are cached in --cache (outside the repo; ~1-3 MB per sample).
"""

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal
from pathlib import Path

REPO = "BerriAI/litellm"
PATH = "model_prices_and_context_window.json"
USER_AGENT = "where-the-margin-lives-research/0.1"

CHANGE_COLUMNS = [
    "model_key", "litellm_provider", "mode", "field",
    "old_usd_per_m", "new_usd_per_m", "change",
    "prev_sha", "prev_commit_date", "sha", "commit_date",
]


def get(url, retries=4):
    headers = {"User-Agent": USER_AGENT}
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    last = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as r:
                return r.read(), r.headers
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {last}")


def list_commits():
    commits, page = [], 1
    while True:
        body, headers = get(
            f"https://api.github.com/repos/{REPO}/commits?path={PATH}&per_page=100&page={page}"
        )
        batch = json.loads(body)
        if not batch:
            break
        for c in batch:
            commits.append({
                "sha": c["sha"],
                "commit_date": c["commit"]["committer"]["date"],
                "author_date": c["commit"]["author"]["date"],
                "message": c["commit"]["message"].splitlines()[0][:200],
            })
        if 'rel="next"' not in (headers.get("Link") or ""):
            break
        page += 1
    return sorted(commits, key=lambda c: c["commit_date"])


def weekly_samples(commits):
    """Last commit of each ISO week, in date order."""
    by_week = {}
    for c in commits:
        iso = datetime.fromisoformat(c["commit_date"].replace("Z", "+00:00")).isocalendar()
        by_week[(iso[0], iso[1])] = c  # commits are sorted, so the last one wins
    return [by_week[k] for k in sorted(by_week)]


def load_at(sha, cache):
    cached = cache / f"{sha}.json"
    if not cached.exists():
        body, _ = get(f"https://raw.githubusercontent.com/{REPO}/{sha}/{PATH}")
        cached.write_bytes(body)
    # Decimal keeps prices exact (the file stores floats like 1.25e-06)
    return json.loads(cached.read_text(encoding="utf-8"), parse_float=Decimal)


def is_token_price_field(name):
    return "cost_per_token" in name or name.endswith("token_cost") or "_token_cost_" in name


def token_prices(spec):
    """{model_key: (provider, mode, {field: Decimal $/token})}, skipping the schema example."""
    out = {}
    for key, entry in spec.items():
        if key == "sample_spec" or not isinstance(entry, dict):
            continue
        fields = {
            k: Decimal(v) for k, v in entry.items()
            if is_token_price_field(k) and isinstance(v, (int, Decimal)) and not isinstance(v, bool)
        }
        out[key] = (entry.get("litellm_provider", ""), entry.get("mode", ""), fields)
    return out


def per_m(value):
    return "" if value is None else format((value * 1_000_000).normalize(), "f")


def diff(prev, cur, prev_commit, commit):
    rows = []
    for key in sorted(set(prev) | set(cur)):
        provider, mode, _ = cur.get(key) or prev[key]
        old_fields = prev.get(key, ("", "", {}))[2]
        new_fields = cur.get(key, ("", "", {}))[2]
        for field in sorted(set(old_fields) | set(new_fields)):
            old, new = old_fields.get(field), new_fields.get(field)
            if old == new:
                continue
            change = "added" if old is None else "removed" if new is None else "changed"
            rows.append({
                "model_key": key, "litellm_provider": provider, "mode": mode, "field": field,
                "old_usd_per_m": per_m(old), "new_usd_per_m": per_m(new), "change": change,
                "prev_sha": prev_commit["sha"] if prev_commit else "",
                "prev_commit_date": prev_commit["commit_date"] if prev_commit else "",
                "sha": commit["sha"], "commit_date": commit["commit_date"],
            })
    return rows


def write_csv(path, columns, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="data/litellm", type=Path)
    p.add_argument("--cache", required=True, type=Path, help="download cache, outside the repo")
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)

    commits = list_commits()
    write_csv(args.out / "commits.csv", ["sha", "commit_date", "author_date", "message"], commits)
    samples = weekly_samples(commits)
    print(f"{len(commits)} commits, {len(samples)} weekly samples "
          f"({samples[0]['commit_date']} .. {samples[-1]['commit_date']})")

    changes, prev, prev_commit, unreadable = [], {}, None, []
    for i, commit in enumerate(samples, 1):
        try:
            cur = token_prices(load_at(commit["sha"], args.cache))
        except (json.JSONDecodeError, RuntimeError) as e:
            # A commit with broken JSON is skipped; the next sample diffs against the last good one
            unreadable.append((commit["sha"], str(e)[:120]))
            continue
        changes += diff(prev, cur, prev_commit, commit)
        prev, prev_commit = cur, commit
        if i % 25 == 0:
            print(f"  {i}/{len(samples)} samples, {len(changes)} change rows")

    write_csv(args.out / "price_changes.csv", CHANGE_COLUMNS, changes)
    print(f"{len(changes)} change rows; {len(unreadable)} unreadable samples")
    for sha, err in unreadable:
        print(f"  unreadable {sha[:10]}: {err}")


if __name__ == "__main__":
    main()
