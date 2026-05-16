# ShadowBuyer — Data Layer Integration Guide

This file tells Person A's agents exactly how to call the data layer.

## Quick start

```python
import sys
sys.path.insert(0, "src")
from scout_interface import get_vendor, get_all_vendors, get_trash_talk, store_negotiation_decision
```

## Scout Agent — reading vendor intelligence

```python
# Single vendor (full profile: G2, pricing, status, funding, AE quote, trash-talk)
dd = get_vendor("datadog")
print(dd["g2"]["rating"])          # 4.4
print(dd["ae_quote"]["first_quote"])  # $2,300/host/year
print(dd["trash_talk"])            # "We're more reliable than New Relic during incidents."

# All 5 vendors at once (reads from cache, very fast)
vendors = get_all_vendors()
for slug, v in vendors.items():
    print(v["name"], v["g2"]["rating"], v["ae_quote"]["first_quote"])

# Competitive intel — who trash-talked whom
intel = get_trash_talk()
for item in intel:
    print(f"[{item['vendor']}] {item['competitor_dig']}")
```

Supported slugs: `datadog`, `newrelic`, `honeycomb`, `grafana`, `splunk`

## Negotiator Agent — pre-built negotiation briefs

```python
from negotiation_brief import build_brief, build_all_briefs

brief = build_brief("datadog")
print(brief["list_quote"]["raw"])       # $2,300/host/year
print(brief["recommended_counter"])     # $1,955.00
print(brief["walk_away_threshold"])     # $1,840.00
for point in brief["leverage_points"]:
    print(" •", point)
```

Brief is automatically stored in `fixtures/brief_<slug>.json` AND written
to Evermind under `negotiation_decision/brief_<slug>`.

## Contract Diff Agent — clause similarity via Nosana

```python
from contract_similarity import compare_clauses, run_demo
from nosana_embeddings import embed, cosine

# Compare two contract clauses
clauses = [
    "This Agreement auto-renews unless 90 days notice is given.",
    "Customer may terminate on 30 days notice.",
]
result = compare_clauses("auto_renewal", clauses)
for cmp in result["comparisons"]:
    print(cmp["similarity"], cmp["divergence_risk"], cmp["note"])

# Or run the full Datadog contract demo
report = run_demo()
# -> saves fixtures/contract_similarity.json
# -> report["high_risk_flags"] lists all HIGH divergence clauses
```

## Storing Negotiation Decisions back to Evermind

```python
# Person A's Negotiator calls this after making a decision
store_negotiation_decision("datadog", {
    "action": "counter",
    "target_price": "$1,950/host/year",
    "rationale": "Public company — month-end pressure. New Relic private = leverage.",
    "status": "pending_ae_response",
})
```

## Evermind buckets in use

| Bucket | Key pattern | Contents |
|--------|-------------|----------|
| `vendor_profile` | `<slug>` | Full vendor profile (G2, pricing, status, funding) |
| `vendor_profile` | `<slug>_funding` | Funding rounds + M&A status |
| `ae_quote` | `<slug>` | AE response (price, discount, competitor dig) |
| `negotiation_decision` | `<slug>` or `brief_<slug>` | Decisions + negotiation briefs |
| `trash_talk` | `<slug>` | AE competitive intel per vendor |

## Fixture files (offline fallback)

All API responses are cached. The demo never crashes.

| File | Contents |
|------|----------|
| `fixtures/vendors_aggregate.json` | All 5 vendors merged |
| `fixtures/<slug>_profile.json` | Per-vendor profile |
| `fixtures/quote_<slug>.json` | Per-vendor AE quote |
| `fixtures/brief_<slug>.json` | Per-vendor negotiation brief |
| `fixtures/trash_talk_moat.json` | Full trash-talk report |
| `fixtures/contract_similarity.json` | Clause similarity report |
| `fixtures/funding_rounds.json` | Funding + acquisition data |

## Running the demo

```bash
# Full end-to-end demo (Datadog golden path)
python demo.py

# Individual modules
python src/scout_interface.py       # vendor table
python src/negotiation_brief.py     # all 5 briefs
python src/trash_talk_report.py     # moat report
python src/contract_similarity.py   # clause similarity

# Verification scripts
python scripts/verify_evermind.py   # 4/4 buckets pass
python scripts/check_sponsor_coverage.py  # 4/4 sponsors pass
python scripts/smoke_brightdata.py  # live G2 scrape test
```
