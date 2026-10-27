"""V2 (free version): do independent throughput measurements agree with each
other, and does every one sit under the roofline ceiling?

Sources:
  InferenceX  reference rows listed in data/inferencex/reference_runs.csv,
              fetched from the public API by row id
  dstack      8xH200 DeepSeek-R1 blog post (2025-03-18), aggregate figures only;
              entered by hand in data/roofline/external_results.csv

Writes data/roofline/v2_comparison.csv: each measured point next to its
ceiling ("min" routing = hard ceiling, "uniform" = typical) and the share of the
ceiling achieved.

Speculative decoding (R2, MTP) breaks the one-token-per-step assumption, so R2
is not checked against the roofline here.
"""

import csv
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import roofline as rf  # noqa: E402

ROOT = rf.ROOT
API = "https://inferencex.semianalysis.com/api/v1/benchmarks?model="
REFS = ROOT / "data" / "inferencex" / "reference_runs.csv"
EXTERNAL = ROOT / "data" / "roofline" / "external_results.csv"
GPUS = ROOT / "data" / "roofline" / "gpus.csv"
OUT = ROOT / "data" / "roofline" / "v2_comparison.csv"

# How each reference config maps onto the roofline inputs
CONFIGS = {
    "R1": {"api_model": "gpt-oss-120b", "config": "gpt-oss-120b.config.json",
           "compute_dtype": "bf16"},  # MXFP4 weights; Hopper has no FP4 math
    "R3": {"api_model": "DeepSeek-R1-0528", "config": "DeepSeek-R1-0528.config.json",
           "compute_dtype": "fp8"},
}
COLUMNS = [
    "source", "ref", "row_id", "model", "gpu", "n_gpu", "framework", "isl", "osl", "conc",
    "measured_output_tput_per_gpu", "ceiling_min_routing", "ceiling_uniform_routing",
    "share_of_hard_ceiling", "share_of_uniform_ceiling", "decode_bound", "verdict", "note",
]


def load_gpus():
    with open(GPUS, encoding="utf-8") as f:
        return {r["gpu"]: {k: float(v) for k, v in r.items()
                           if k in ("hbm_tb_s", "bf16_dense_tflops", "fp8_dense_tflops")}
                for r in csv.DictReader(f)}


def fetch(api_model):
    req = urllib.request.Request(API + urllib.parse.quote(api_model),
                                 headers={"User-Agent": "where-the-margin-lives-research/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return {row["id"]: row for row in json.loads(r.read())}


def judge(measured, hard):
    # Above the hard ceiling means the measurement or the model is wrong
    return "VIOLATES CEILING" if measured > hard else "ok"


def point(source, ref, row_id, model, gpu_name, gpus, n_gpu, framework, isl, osl, conc,
          measured, dtype, note):
    hard = rf.ceiling(model, gpus[gpu_name], n_gpu, isl, osl, conc, dtype, "min")
    typ = rf.ceiling(model, gpus[gpu_name], n_gpu, isl, osl, conc, dtype, "uniform")
    return {
        "source": source, "ref": ref, "row_id": row_id, "model": model.name, "gpu": gpu_name,
        "n_gpu": n_gpu, "framework": framework, "isl": round(isl), "osl": round(osl),
        "conc": conc, "measured_output_tput_per_gpu": round(measured, 1),
        "ceiling_min_routing": round(hard["output_tput_per_gpu"], 1),
        "ceiling_uniform_routing": round(typ["output_tput_per_gpu"], 1),
        "share_of_hard_ceiling": round(measured / hard["output_tput_per_gpu"], 3),
        "share_of_uniform_ceiling": round(measured / typ["output_tput_per_gpu"], 3),
        "decode_bound": hard["decode_bound"],
        "verdict": judge(measured, hard["output_tput_per_gpu"]), "note": note,
    }


def main():
    gpus = load_gpus()
    with open(REFS, encoding="utf-8") as f:
        refs = [r for r in csv.DictReader(f) if r["ref"] in CONFIGS]
    out = []
    for ref, spec in CONFIGS.items():
        model = rf.load_model(rf.CONFIGS / spec["config"])
        rows = fetch(spec["api_model"])
        for r in (x for x in refs if x["ref"] == ref):
            row = rows.get(r["row_id"])
            if row is None:
                print(f"{ref} row {r['row_id']} no longer served by the API", file=sys.stderr)
                continue
            mt = row["metrics"]
            # Use the lengths the benchmark actually sent, not the nominal ISL/OSL
            isl = mt.get("mean_input_tokens") or float(r["isl"])
            osl = mt.get("mean_output_tokens_actual") or float(r["osl"])
            out.append(point("InferenceX", ref, r["row_id"], model, r["hardware"], gpus,
                             int(r["decode_tp"]), r["framework"], isl, osl, int(r["conc"]),
                             mt["output_tput_per_gpu"], spec["compute_dtype"],
                             f"run {r['workflow_run_id']} {r['date']}"))
    with open(EXTERNAL, encoding="utf-8") as f:
        for e in csv.DictReader(f):
            model = rf.load_model(rf.CONFIGS / e["config"])
            out.append(point(e["source"], "", "", model, e["gpu"], gpus, int(e["n_gpu"]),
                             e["framework"], float(e["isl"]), float(e["osl"]), int(e["conc"]),
                             float(e["measured_output_tput_total"]) / int(e["n_gpu"]),
                             e["compute_dtype"], e["note"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    for p in out:
        print(f"{p['source']:10s} {p['ref']:3s} {p['model']:17s} {p['gpu']} x{p['n_gpu']} "
              f"{p['isl']:>5}/{p['osl']:<5} c={p['conc']:<4} measured={p['measured_output_tput_per_gpu']:>8} "
              f"hard={p['ceiling_min_routing']:>8} unif={p['ceiling_uniform_routing']:>8} "
              f"share={p['share_of_hard_ceiling']:.2f}/{p['share_of_uniform_ceiling']:.2f} "
              f"{p['decode_bound']:7s} {p['verdict']}")
    return 1 if any(p["verdict"] != "ok" for p in out) else 0


if __name__ == "__main__":
    sys.exit(main())
