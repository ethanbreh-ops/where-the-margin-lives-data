# Task 4: V5 anchors, the GPU-owner margin bridge

Date: 2026-10-27.
- Inputs: [data/filings/v5_inputs.csv](../data/filings/v5_inputs.csv).
- Calculation: [snapshots/filings/margin_bridge.py](../snapshots/filings/margin_bridge.py).
- Output: [data/filings/v5_bridge.csv](../data/filings/v5_bridge.csv).

## Sources

- **CoreWeave:** FY2025 10-K, filed 2026-03-02, accession 0001769628-26-000104.
- **Nebius:** FY2025 20-F, filed 2026-04-30, accession 0001104659-26-052948. The 20-F/A filed 2026-05-22 only adds Exhibit 97.1 (clawback policy) and doesn't change the financials.

The script fails if the line items don't sum exactly to the reported subtotals. Today they do for both companies.

## The finding: "gross margin" at a neocloud excludes the GPUs

Both companies report server depreciation **outside** cost of revenue:

- **CoreWeave.** Cost of revenue covers data center rent, power, power-distribution depreciation and operations staff. Depreciation of "servers, switches, networking equipment" sits in **Technology and infrastructure**: about $2.3bn of the $2.9bn in that line. (10-K, MD&A and expense definitions.)
- **Nebius.** Cost of revenues covers co-location, electricity, maintenance and personnel. Depreciation and amortization ($417.9m, "mainly servers and networking equipment") is a **separate line**.

So the widely quoted ~70% "gross margin" is a margin **before the cost of the main asset**. It isn't comparable to Nvidia's GAAP gross margin, which includes product cost.

## Bridge (FY2025)

| Company | Step | Margin | Status |
|---|---|---|---|
| CoreWeave | 1. Reported gross margin | **71.7%** | calculated |
| | 2. After server/network depreciation | **26.9%** | calculated |
| | 2a. …if servers used a 5-year life (not 6) | 17.9% | estimated |
| | 2a. …if servers used a 4-year life | 4.4% | estimated |
| | 3. GAAP operating margin | −0.9% | calculated |
| | 4. Pre-tax, after $1.2bn net interest | −23.7% | calculated |
| Nebius group | 1. Reported gross margin | **68.6%** | calculated |
| | 2. After all depreciation (4-year server life) | **−10.2%** | calculated |
| | 2a. …if servers used a 5-year life | 5.5% | estimated |
| | 3. GAAP operating margin (includes Avride losses) | −115.5% | calculated |
| Nebius AI cloud segment | 1. Adjusted EBITDA margin (company non-GAAP) | 12.3% | calculated |
| | 2. After depreciation, charging all group depreciation to the segment | −74.7% | estimated, lower bound |

**How the "estimated" rows work:**
- Depreciation is scaled by the ratio of useful lives, e.g. 6/4.
- This assumes all of CoreWeave's T&I depreciation is 6-year technology equipment, and ignores when assets entered service.
- Nebius's own estimate of the 4→5-year change is −$167.6m of FY2026 depreciation on assets in service at year-end 2025. That's the same direction as our estimate and a similar size.

## What this gives V5

- **The useful-life assumption is the biggest swing factor.**
  - CoreWeave uses 6 years. It moved from 5 to 6 in 2023.
  - Nebius used 4 years in FY2025 and moved to 5 from 2026-01-01.
  - Switching CoreWeave from 6 to 4 years moves its margin after depreciation by about 22 points.
  - **Our bottom-up GPU $/hr cost must state its depreciation life and show 4, 5 and 6 years as a sensitivity.**
- **The audited range for GPU-owner margin after asset cost, FY2025 at reported lives, is about −10% to +27%.** The implied infrastructure margin in our chain should fall in that range, or we explain why.

**Known reasons the chain could legitimately differ:**
1. **Spot vs contract prices.** CoreWeave revenue is mostly multi-year committed contracts, while our chain prices market rental. [U] The 10-K's customer-concentration and remaining-performance-obligation disclosures should confirm the contract mix. That's the next read.
2. **Growth-phase timing.** $9.4bn of construction in progress isn't yet depreciating. Assets placed in service during the year earn part-year revenue and part-year depreciation.
3. **Financing.** Interest of $1.2bn, 24% of revenue, is a real cost of owning GPUs. It sits below operating income, so a fully loaded $/GPU-hr needs a capital charge, not just depreciation.

## Caveats

- **Nebius's 20-F reports a material weakness in internal control over fixed assets,** specifically depreciation start dates. Its depreciation figures carry more uncertainty than usual.
- **Nebius depreciation is not disclosed by segment.** The segment-after-depreciation row is a bound, not a measurement.
- **CoreWeave's $2.3bn T&I depreciation is a rounded MD&A figure.** Total depreciation and amortization in the cash flow statement is $2,454m.
- **Two companies is a thin sample.** Hyperscalers don't disclose GPU-cloud margins, so they can only provide bounds.
- **Next filings to add:** Nebius 2026 quarterly reports (6-K) and CoreWeave's 2026 10-Qs. The first full year on Nebius's 5-year life will show whether the change was material.
