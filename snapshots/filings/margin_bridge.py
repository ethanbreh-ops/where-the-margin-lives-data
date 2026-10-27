"""GPU-owner margin bridge (V5 anchors) from audited FY2025 filings.

Reads data/filings/v5_inputs.csv and writes data/filings/v5_bridge.csv.

The point of the bridge is Principle 4: a neocloud's reported "gross margin"
(revenue less cost of revenue) excludes depreciation of the GPU servers, which
both CoreWeave and Nebius report outside cost of revenue. The bridge steps from
that figure down to margin after the asset cost, then operating and pre-tax.

Every output row carries a status:
  calculated : arithmetic on observed inputs only
  estimated  : also depends on a stated simplifying assumption (see `basis`)
"""

import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUTS = ROOT / "data" / "filings" / "v5_inputs.csv"
OUTPUT = ROOT / "data" / "filings" / "v5_bridge.csv"


def load(path=INPUTS):
    with open(path, encoding="utf-8") as f:
        return {r["input_id"]: Decimal(r["value"]) for r in csv.DictReader(f)}


def pct(num, den):
    return (num / den * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def checks(x):
    """Reported subtotals must reconcile exactly; fail loudly if an input is mistyped."""
    errors = []
    crwv_opex = x["CRWV_COR"] + x["CRWV_TI"] + x["CRWV_SM"] + x["CRWV_GA"]
    if crwv_opex != x["CRWV_OPEX"]:
        errors.append(f"CoreWeave opex lines sum to {crwv_opex}, reported {x['CRWV_OPEX']}")
    if x["CRWV_REV"] - x["CRWV_OPEX"] != x["CRWV_OPINC"]:
        errors.append("CoreWeave revenue - opex != operating income")
    nbis_opex = x["NBIS_COR"] + x["NBIS_PD"] + x["NBIS_SGA"] + x["NBIS_DA"]
    if nbis_opex != x["NBIS_OPEX"]:
        errors.append(f"Nebius opex lines sum to {nbis_opex}, reported {x['NBIS_OPEX']}")
    if x["NBIS_REV"] - x["NBIS_OPEX"] != x["NBIS_OPLOSS"]:
        errors.append("Nebius revenue - opex != loss from operations")
    if x["CRWV_TI_DA"] > x["CRWV_DA_TOTAL"]:
        errors.append("CoreWeave T&I D&A exceeds total D&A")
    return errors


def bridge(x):
    rows = []

    def add(company, step, num, den, status, basis):
        rows.append({
            "company": company, "step": step, "numerator_usd_m": str(num),
            "denominator_usd_m": str(den), "margin_pct": str(pct(num, den)),
            "status": status, "basis": basis,
        })

    rev, cor, da = x["CRWV_REV"], x["CRWV_COR"], x["CRWV_TI_DA"]
    add("CoreWeave", "1. Reported gross margin (revenue - cost of revenue)", rev - cor, rev,
        "calculated", "Cost of revenue excludes server/network depreciation (in T&I)")
    add("CoreWeave", "2. Gross margin after server/network D&A", rev - cor - da, rev,
        "calculated", "Subtracts the ~$2.3bn T&I D&A (MD&A figure, rounded)")
    for life in (5, 4):
        scaled = (da * x["CRWV_LIFE"] / life).quantize(Decimal("1"))
        add("CoreWeave", f"2a. Step 2 if servers depreciated over {life} years", rev - cor - scaled, rev,
            "estimated", f"T&I D&A scaled by 6/{life}; assumes all of it is 6-year technology "
            "equipment and ignores in-service timing")
    add("CoreWeave", "3. GAAP operating margin", x["CRWV_OPINC"], rev,
        "calculated", "After remaining T&I (people, software), S&M, G&A")
    add("CoreWeave", "4. Pre-tax margin", x["CRWV_PRETAX"], rev,
        "calculated", "After $1.2bn net interest; financing cost of the GPU fleet")

    rev, cor, da = x["NBIS_REV"], x["NBIS_COR"], x["NBIS_DA"]
    add("Nebius group", "1. Reported gross margin (revenues - cost of revenues)", rev - cor, rev,
        "calculated", "Group incl. Avride and TripleTen; D&A is a separate line")
    add("Nebius group", "2. Gross margin after all D&A", rev - cor - da, rev,
        "calculated", "Group D&A, mainly servers and network equipment (4-year life)")
    scaled = (da * x["NBIS_LIFE"] / 5).quantize(Decimal("0.1"))
    add("Nebius group", "2a. Step 2 if servers depreciated over 5 years", rev - cor - scaled, rev,
        "estimated", "D&A scaled by 4/5; the company's own FY2026 estimate of the change is "
        f"-${x['NBIS_LIFE_SAVING']}m on year-end assets")
    add("Nebius group", "3. GAAP operating margin", x["NBIS_OPLOSS"], rev,
        "calculated", "Includes Avride (autonomous driving) losses")
    seg_rev, seg_ebitda = x["NBIS_SEG_REV"], x["NBIS_SEG_EBITDA"]
    add("Nebius AI cloud segment", "1. Segment Adjusted EBITDA margin", seg_ebitda, seg_rev,
        "calculated", "Company non-GAAP measure, before all D&A")
    add("Nebius AI cloud segment", "2. Segment margin after D&A (lower bound)", seg_ebitda - da, seg_rev,
        "estimated", "Charges all group D&A to the segment; D&A is not disclosed by segment")
    return rows


def main():
    x = load()
    errors = checks(x)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    rows = bridge(x)
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['company']:24s} {r['step']:58s} {r['margin_pct']:>7s}%  {r['status']}")


if __name__ == "__main__":
    main()
