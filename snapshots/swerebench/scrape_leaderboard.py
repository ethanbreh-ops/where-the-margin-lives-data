"""Snapshot of the SWE-rebench leaderboard (swe-rebench.com).

SWE-rebench evaluates agents on fresh GitHub tasks collected after each model's
release, so its numbers are not exposed to the contamination that affects
SWE-bench Verified. Each model has stats for many task windows: resolved rate,
standard error and pass@5 across repeated runs, cost per problem, tokens per
problem and cached-token share.

The page embeds that data as JSON in its Next.js payload. This script extracts
it and writes:
  data/swerebench/<date>.csv.gz    one row per (model, language, task window)
  data/swerebench/<date>.manifest.json  source sha256 and counts

Only the extracted numbers are stored, with attribution; the page itself is not
republished (no licence is stated for the leaderboard results).
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://swe-rebench.com/"
USER_AGENT = "Mozilla/5.0 (where-the-margin-lives-research/0.1)"
PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')

COLUMNS = [
    "snapshot_date", "model_id", "model_name", "release_date", "agent_version",
    "developer", "instance_type", "language", "window_from", "window_to",
    "resolved_rate_pct", "sem_pct", "pass_n_pct", "cost_per_problem_usd",
    "tokens_per_problem", "cached_token_pct",
]


def payload(html):
    """Concatenate the Next.js flight chunks into one decoded string."""
    return "".join(json.loads(f'"{c}"') for c in PUSH_RE.findall(html))


def extract_items(text):
    start = text.find('"items":[{"modelId"')
    if start < 0:
        raise ValueError("leaderboard items not found; the page layout may have changed")
    items, _ = json.JSONDecoder().raw_decode(text, start + len('"items":'))
    return items


def day(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).date().isoformat()


def rows(items, snapshot_date):
    out = []
    for it in items:
        meta = it.get("meta") or {}
        for language, windows in (it.get("rangeStats") or {}).items():
            for window, st in windows.items():
                lo, hi = (int(x) for x in window.split(":"))
                tokens = st.get("totalTokenUsage")
                cost = st.get("instanceCosts")
                out.append({
                    "snapshot_date": snapshot_date,
                    "model_id": it["modelId"], "model_name": it.get("modelName", ""),
                    "release_date": (it.get("release") or {}).get("date", ""),
                    "agent_version": it.get("agentVersion", ""),
                    "developer": meta.get("developer", ""),
                    "instance_type": meta.get("instance_type", ""),
                    "language": language, "window_from": day(lo), "window_to": day(hi),
                    "resolved_rate_pct": st.get("resolvedRate"), "sem_pct": st.get("sem"),
                    "pass_n_pct": st.get("passN"),
                    # The site shows 0 where it has no cost/token data; keep that as blank
                    "cost_per_problem_usd": cost if cost else "",
                    "tokens_per_problem": tokens if tokens else "",
                    "cached_token_pct": "" if st.get("cachedTokenPercentage") is None
                    else st["cachedTokenPercentage"],
                })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="data/swerebench", type=Path)
    p.add_argument("--html", type=Path, help="parse a saved page instead of fetching")
    args = p.parse_args()
    if args.html:
        raw = args.html.read_bytes()
    else:
        req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    snapshot_date = datetime.now(timezone.utc).date().isoformat()
    items = extract_items(payload(raw.decode("utf-8")))
    out_rows = rows(items, snapshot_date)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / f"{snapshot_date}.csv.gz"
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    w.writerows(out_rows)
    # mtime=0 so identical data gives identical bytes
    with open(csv_path, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as gz:
        gz.write(buf.getvalue().encode("utf-8"))
    manifest = {
        "source": URL, "snapshot_date": snapshot_date,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_sha256": hashlib.sha256(raw).hexdigest(), "models": len(items),
        "rows": len(out_rows),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    with open(args.out / f"{snapshot_date}.manifest.json", "w", newline="\n", encoding="utf-8") as f:
        f.write(json.dumps(manifest, indent=2) + "\n")
    print(f"{snapshot_date}: {len(items)} models, {len(out_rows)} rows")


if __name__ == "__main__":
    sys.exit(main())
