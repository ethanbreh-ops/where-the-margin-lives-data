"""Per-call token usage from public SWE-bench bash-only (mini-SWE-agent) trajectories.

Source: SWE-bench/experiments on GitHub lists each submission (metadata.yaml,
per_instance_details.json); full trajectories sit in the public S3 bucket
swe-bench-submissions under bash-only/<submission>/trajs/.

Writes, per submission (so reruns skip finished ones):
  data/swebench/by_submission/<sub>.instances.csv
  data/swebench/by_submission/<sub>.calls.csv.gz
and combined:
  data/swebench/submissions.csv
  data/swebench/instances.csv
  data/swebench/calls.csv.gz

Token semantics (checked by recomputing logged cost from tokens at list price,
exact to the cent on Claude Opus 4.6): input_tokens INCLUDES cache reads and
cache writes. Token classes a provider did not report are left blank, never 0.

Raw trajectories are not stored (~GBs); each instance row keeps the S3 ETag and
size so the exact object can be re-fetched and verified.
"""

import argparse
import csv
import gzip
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

GH_API = "https://api.github.com/repos/SWE-bench/experiments/contents/evaluation/verified"
GH_RAW = "https://raw.githubusercontent.com/SWE-bench/experiments/main/evaluation/verified"
S3 = "https://swe-bench-submissions.s3.amazonaws.com"
USER_AGENT = "where-the-margin-lives-research/0.1"
COST_TOLERANCE = 1e-6  # USD per instance; costs are logged as floats

SUBMISSION_COLUMNS = [
    "submission", "model_display", "model_ids", "model_org", "os_model", "mini_version",
    "model_release_date", "resolved_pct_reported", "total_cost_reported",
    "instance_cost_reported", "instance_calls_reported",
    "resolved_pct_extracted", "instances_extracted", "data_issue",
]
INSTANCE_COLUMNS = [
    "submission", "instance_id", "resolved", "resolved_details", "exit_status", "cost_reported",
    "api_calls_reported", "n_calls", "cost_sum_calls", "cost_matches",
    "input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens",
    "reasoning_tokens", "token_classes_missing", "wall_clock_s", "traj_etag", "traj_bytes",
]
CALL_COLUMNS = [
    "submission", "instance_id", "call_idx", "timestamp", "model", "provider",
    "input_tokens", "cache_read_tokens", "cache_write_tokens", "output_tokens",
    "reasoning_tokens", "cost_usd",
]


def get(url, retries=5):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code == 404:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"{url}: {last}")


def list_submissions(pattern):
    names = [x["name"] for x in json.loads(get(GH_API)) if x["type"] == "dir"]
    return sorted(n for n in names if re.search(pattern, n))


def parse_metadata(text):
    """Pull the few scalar fields we need from metadata.yaml without a YAML library."""
    def field(key):
        m = re.search(rf"^\s*{key}:\s*(.*)$", text, re.M)
        return m.group(1).strip().strip("'\"") if m else ""
    model_ids = re.findall(r"^\s*model:\s*\n((?:\s*-\s*.+\n)+)", text, re.M)
    ids = re.findall(r"-\s*(\S+)", model_ids[0]) if model_ids else []
    return {
        "model_display": field("model_display") or field("name"),
        "model_ids": ";".join(ids),
        "model_org": field("model_org") or field("org"),
        "os_model": field("os_model"),
        "mini_version": field("mini-swe-agent_version"),
        "model_release_date": field("model_release_date"),
        "resolved_pct_reported": field("resolved"),
        "total_cost_reported": field("cost"),
        "instance_cost_reported": field("instance_cost"),
        "instance_calls_reported": field("instance_calls"),
    }


def list_trajs(sub):
    """{instance_id: (key, etag, size)} from the public S3 listing."""
    out, token = {}, None
    ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    while True:
        q = {"list-type": "2", "prefix": f"bash-only/{sub}/trajs/"}
        if token:
            q["continuation-token"] = token
        root = ET.fromstring(get(f"{S3}/?{urllib.parse.urlencode(q)}"))
        for c in root.findall("s3:Contents", ns):
            key = c.find("s3:Key", ns).text
            if key.endswith(".traj.json"):
                iid = key.rsplit("/", 1)[1].removesuffix(".traj.json")
                out[iid] = (key, c.find("s3:ETag", ns).text.strip('"'), int(c.find("s3:Size", ns).text))
        nxt = root.find("s3:NextContinuationToken", ns)
        if nxt is None:
            return out
        token = nxt.text


def _opt(d, *path):
    for p in path:
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def call_usage(msg):
    """Normalize one LLM call's usage across chat-completions and responses formats.

    Returns None for messages that are not model calls.
    """
    extra = msg.get("extra") or {}
    if "cost" not in extra:
        return None
    u = _opt(extra, "response", "usage") or msg.get("usage")
    if not u:
        return {"cost": extra["cost"], "usage_missing": True}
    if "input_tokens" in u and "prompt_tokens" not in u:  # OpenAI responses API
        inp, out = u.get("input_tokens"), u.get("output_tokens")
        cache_read = _opt(u, "input_tokens_details", "cached_tokens")
        cache_write = None
        reasoning = _opt(u, "output_tokens_details", "reasoning_tokens")
    else:
        inp, out = u.get("prompt_tokens"), u.get("completion_tokens")
        cache_read = u.get("cache_read_input_tokens")
        if cache_read is None:
            cache_read = _opt(u, "prompt_tokens_details", "cached_tokens")
        cache_write = u.get("cache_creation_input_tokens")
        if cache_write is None:
            cache_write = _opt(u, "prompt_tokens_details", "cache_creation_tokens")
        reasoning = _opt(u, "completion_tokens_details", "reasoning_tokens")
    resp = extra.get("response") or msg
    return {
        "cost": extra["cost"], "timestamp": extra.get("timestamp"),
        "model": resp.get("model", ""), "provider": resp.get("provider", ""),
        "input": inp, "cache_read": cache_read, "cache_write": cache_write,
        "output": out, "reasoning": reasoning,
    }


def blank(v):
    return "" if v is None else v


def parse_trajectory(sub, iid, traj, details, etag, size):
    calls, missing = [], set()
    for m in traj.get("messages") or []:
        c = call_usage(m)
        if c is None:
            continue
        if c.get("usage_missing"):
            missing.add("all")
        calls.append(c)
    sums = {}
    for k in ("input", "cache_read", "cache_write", "output", "reasoning"):
        vals = [c.get(k) for c in calls]
        if any(v is None for v in vals):
            missing.add(k)
        sums[k] = sum(v for v in vals if v is not None)
    times = [c["timestamp"] for c in calls if isinstance(c.get("timestamp"), (int, float))]
    cost_sum = sum(c["cost"] or 0 for c in calls)
    stats = _opt(traj, "info", "model_stats") or {}
    reported = details.get("cost", stats.get("instance_cost"))
    inst = {
        "submission": sub, "instance_id": iid, "resolved": blank(details.get("_report_resolved")),
        "resolved_details": blank(details.get("resolved")),
        "exit_status": _opt(traj, "info", "exit_status") or "",
        "cost_reported": blank(reported),
        "api_calls_reported": blank(details.get("api_calls", stats.get("api_calls"))),
        "n_calls": len(calls), "cost_sum_calls": round(cost_sum, 9),
        "cost_matches": reported is not None and abs(cost_sum - reported) <= COST_TOLERANCE,
        "input_tokens": sums["input"], "cache_read_tokens": sums["cache_read"],
        "cache_write_tokens": sums["cache_write"], "output_tokens": sums["output"],
        "reasoning_tokens": sums["reasoning"],
        "token_classes_missing": ";".join(sorted(missing)),
        "wall_clock_s": round(max(times) - min(times), 1) if len(times) > 1 else "",
        "traj_etag": etag, "traj_bytes": size,
    }
    rows = [{
        "submission": sub, "instance_id": iid, "call_idx": i,
        "timestamp": blank(c.get("timestamp")), "model": c.get("model", ""),
        "provider": c.get("provider", ""), "input_tokens": blank(c.get("input")),
        "cache_read_tokens": blank(c.get("cache_read")),
        "cache_write_tokens": blank(c.get("cache_write")),
        "output_tokens": blank(c.get("output")), "reasoning_tokens": blank(c.get("reasoning")),
        "cost_usd": blank(c.get("cost")),
    } for i, c in enumerate(calls)]
    return inst, rows


def write_csv(path, columns, rows, gz=False):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    data = buf.getvalue().encode("utf-8")
    if gz:
        with open(path, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0) as g:
            g.write(data)
    else:
        Path(path).write_bytes(data)


def read_csv(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def resolved_from_report(sub, iid):
    """The evaluation harness's own verdict (logs/<iid>/report.json); None if absent.

    This is the primary source: per_instance_details.json is a derived summary and
    was found wrong for at least one submission (all False, against a 69.6% headline).
    """
    try:
        rep = json.loads(get(f"{S3}/bash-only/{sub}/logs/{urllib.parse.quote(iid)}/report.json"))
    except RuntimeError:
        return None
    rep = rep.get(iid, rep)  # harness versions differ: flat, or keyed by instance id
    return rep.get("resolved")


def extract_submission(sub, out_dir, workers):
    try:
        details = json.loads(get(f"{GH_RAW}/{sub}/per_instance_details.json"))
    except RuntimeError:
        details = {}  # costs then come from each trajectory's model_stats
    trajs = list_trajs(sub)

    def one(iid):
        key, etag, size = trajs[iid]
        traj = json.loads(get(f"{S3}/{urllib.parse.quote(key)}"))
        d = dict(details.get(iid, {}), _report_resolved=resolved_from_report(sub, iid))
        return parse_trajectory(sub, iid, traj, d, etag, size)

    instances, calls = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for inst, rows in pool.map(one, sorted(trajs)):
            instances.append(inst)
            calls.extend(rows)
    # Instances scored but with no trajectory are kept, so success rates use the full denominator
    for iid in sorted(set(details) - set(trajs)):
        instances.append({c: "" for c in INSTANCE_COLUMNS} | {
            "submission": sub, "instance_id": iid,
            "resolved": blank(resolved_from_report(sub, iid)),
            "resolved_details": blank(details[iid].get("resolved")),
            "cost_reported": blank(details[iid].get("cost")),
            "api_calls_reported": blank(details[iid].get("api_calls")),
            "token_classes_missing": "no_trajectory",
        })
    write_csv(out_dir / f"{sub}.instances.csv", INSTANCE_COLUMNS, instances)
    write_csv(out_dir / f"{sub}.calls.csv.gz", CALL_COLUMNS, calls, gz=True)
    bad = sum(1 for i in instances if str(i["cost_matches"]) != "True")
    return len(instances), len(calls), bad, len(set(details) - set(trajs))


def flag_issues(meta_rows, instances):
    """Submission-level QA, written to submissions.csv so analyses can filter on it."""
    by_sub = {}
    for r in instances:
        by_sub.setdefault(r["submission"], []).append(r)
    fingerprints = {s: tuple(sorted(r["traj_etag"] for r in rows)) for s, rows in by_sub.items()}
    for m in meta_rows:
        rows = by_sub.get(m["submission"], [])
        issues = []
        known = [r for r in rows if r["resolved"] in ("True", "False")]
        if known:
            pct = 100 * sum(r["resolved"] == "True" for r in known) / len(rows)
            m["resolved_pct_extracted"] = f"{pct:.1f}"
            if m["resolved_pct_reported"] and abs(pct - float(m["resolved_pct_reported"])) > 0.5:
                issues.append(f"resolved {pct:.1f}% vs reported {m['resolved_pct_reported']}%")
        if len(known) < len(rows):
            issues.append(f"{len(rows) - len(known)} instances without a harness verdict")
        if any(r["resolved"] != r["resolved_details"] for r in known if r["resolved_details"]):
            issues.append("per_instance_details disagrees with harness reports")
        # Identical trajectory sets mean one folder is a copy of another; the earlier name wins
        for other, fp in fingerprints.items():
            if other < m["submission"] and fp and fp == fingerprints.get(m["submission"]):
                issues.append(f"trajectories identical to {other}")
        m["instances_extracted"] = len(rows)
        m["data_issue"] = "; ".join(issues)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default="data/swebench", type=Path)
    p.add_argument("--pattern", default=r"_mini-v2\.0\.0_", help="regex on submission folder name")
    p.add_argument("--workers", default=16, type=int)
    p.add_argument("--limit", type=int, help="only the first N submissions (testing)")
    args = p.parse_args()
    by_sub = args.out / "by_submission"
    by_sub.mkdir(parents=True, exist_ok=True)

    subs = list_submissions(args.pattern)[: args.limit]
    meta_rows = []
    for sub in subs:
        meta = parse_metadata(get(f"{GH_RAW}/{sub}/metadata.yaml").decode("utf-8"))
        meta_rows.append({"submission": sub} | meta)
        if (by_sub / f"{sub}.calls.csv.gz").exists():
            print(f"{sub}: already extracted, skipping")
            continue
        t0 = time.time()
        try:
            n_inst, n_calls, bad, no_traj = extract_submission(sub, by_sub, args.workers)
        except RuntimeError as e:
            print(f"{sub}: FAILED {e}", file=sys.stderr)
            continue
        print(f"{sub}: {n_inst} instances, {n_calls} calls, {bad} cost mismatches "
              f"({no_traj} without trajectory), {time.time() - t0:.0f}s", flush=True)

    instances, calls = [], []
    for sub in subs:
        if (by_sub / f"{sub}.calls.csv.gz").exists():
            instances += read_csv(by_sub / f"{sub}.instances.csv")
            calls += read_csv(by_sub / f"{sub}.calls.csv.gz")
    flag_issues(meta_rows, instances)
    write_csv(args.out / "submissions.csv", SUBMISSION_COLUMNS, meta_rows)
    write_csv(args.out / "instances.csv", INSTANCE_COLUMNS, instances)
    write_csv(args.out / "calls.csv.gz", CALL_COLUMNS, calls, gz=True)
    print(f"combined: {len(meta_rows)} submissions, {len(instances)} instances, {len(calls)} calls "
          f"(extracted {datetime.now().isoformat(timespec='seconds')})")


if __name__ == "__main__":
    main()
