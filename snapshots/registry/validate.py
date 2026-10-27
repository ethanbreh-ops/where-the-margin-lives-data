"""Validate registry/sources.csv against the source-registry schema (Principle 3).

Schema, one row per source:
  source_id          unique, UPPER-CASE letters, digits and hyphens
  source             human-readable name, incl. accession or version where relevant
  url                http(s) URL of the source itself
  effective_date     period the data describes (free text, required)
  access_date        YYYY-MM-DD, or "daily" for scheduled snapshots
  metric             the exact metric(s) taken
  units              units of those metrics
  model_or_workload  what the numbers are about
  status             observed | calculated | assumed | estimated
  source_tier        primary | audited_filing | third_party | secondary | press
  caveats            known biases and limits (required: "none" is not accepted)
  snapshot_path      repo path(s) of our dated copy, ";"-separated. "<date>" is a
                     wildcard; trailing "(...)" notes are ignored. Every path must
                     match at least one file in the repo.

Exit code 1 lists every violation; 0 means the registry is valid.
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "registry" / "sources.csv"

COLUMNS = [
    "source_id", "source", "url", "effective_date", "access_date", "metric", "units",
    "model_or_workload", "status", "source_tier", "caveats", "snapshot_path",
]
STATUSES = {"observed", "calculated", "assumed", "estimated"}
TIERS = {"primary", "audited_filing", "third_party", "secondary", "press"}


def snapshot_globs(value):
    for part in re.sub(r"\([^)]*\)", "", value).split(";"):
        part = part.strip()
        if part:
            yield part.replace("<date>", "*")


def validate(path=REGISTRY, root=ROOT):
    errors = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            return [f"header must be exactly: {','.join(COLUMNS)}"]
        rows = list(reader)
    seen = set()
    for n, r in enumerate(rows, start=2):
        sid = r["source_id"]
        where = f"line {n} ({sid or 'no id'})"
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]*", sid):
            errors.append(f"{where}: bad source_id")
        if sid in seen:
            errors.append(f"{where}: duplicate source_id")
        seen.add(sid)
        for col in COLUMNS:
            if not (r[col] or "").strip():
                errors.append(f"{where}: {col} is empty")
        if r["url"] and not re.match(r"https?://", r["url"]):
            errors.append(f"{where}: url must start with http(s)://")
        if r["access_date"] != "daily":
            try:
                date.fromisoformat(r["access_date"])
            except ValueError:
                errors.append(f"{where}: access_date must be YYYY-MM-DD or 'daily'")
        if r["status"] not in STATUSES:
            errors.append(f"{where}: status must be one of {sorted(STATUSES)}")
        if r["source_tier"] not in TIERS:
            errors.append(f"{where}: source_tier must be one of {sorted(TIERS)}")
        if r["caveats"].strip().lower() in ("none", "n/a", "-"):
            errors.append(f"{where}: caveats must name at least one limitation")
        for g in snapshot_globs(r["snapshot_path"] or ""):
            if not any(root.glob(g)):
                errors.append(f"{where}: snapshot_path '{g}' matches no file")
    return errors


def main():
    errors = validate()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    print(f"{REGISTRY.relative_to(ROOT)}: valid")


if __name__ == "__main__":
    main()
