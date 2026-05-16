"""Contract clause similarity — powered by Nosana embeddings.

Person A's Contract Diff agent calls this to find clauses in a new vendor
contract that are materially different from the baseline or from each other.

Demo: side-by-side comparison of real Datadog contract clause variations.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nosana_embeddings import cosine, embed, ping_nosana

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

# Realistic contract clause pairs for the observability vendor demo
DATADOG_CONTRACT_CLAUSES = {
    "auto_renewal": [
        "This Agreement will automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least 90 days prior to the end of the then-current term.",
        "The Subscription Term shall automatically renew for additional one (1) year periods unless Customer provides Datadog with written notice of non-renewal no fewer than sixty (60) days prior to the expiration of the then-current Subscription Term.",
        "Customer may terminate this Agreement at any time upon thirty (30) days written notice.",
    ],
    "price_increase": [
        "Datadog reserves the right to increase fees by up to 7% on each anniversary of the Effective Date.",
        "Pricing for renewal terms shall not increase by more than ten percent (10%) over the previous term's pricing without mutual written agreement.",
        "Fees are fixed for the duration of the initial Subscription Term. Renewal pricing is subject to Datadog's then-current list pricing.",
    ],
    "data_portability": [
        "Upon termination, Customer may export their data for a period of 30 days.",
        "Following termination or expiration, Customer shall have ninety (90) days to retrieve Customer Data before Datadog deletes it.",
        "Customer Data will be purged within 14 days of contract termination with no export option after that date.",
    ],
    "liability_cap": [
        "In no event shall Datadog's total aggregate liability exceed the amounts paid by Customer in the twelve (12) months preceding the claim.",
        "Each party's total cumulative liability arising out of or related to this Agreement is limited to fees paid in the three (3) months immediately preceding the event giving rise to the claim.",
        "Datadog's liability shall not exceed USD $10,000 regardless of the nature of the claim.",
    ],
}


def compare_clauses(label: str, clauses: list[str]) -> dict[str, Any]:
    """Embed a set of clauses and compute pairwise similarity."""
    result = embed(clauses)
    vecs = result["embeddings"]
    pairs = []
    for i in range(len(clauses)):
        for j in range(i + 1, len(clauses)):
            sim = cosine(vecs[i], vecs[j])
            risk = "LOW" if sim > 0.85 else "MEDIUM" if sim > 0.60 else "HIGH"
            pairs.append({
                "clause_a_idx": i,
                "clause_b_idx": j,
                "similarity": round(sim, 4),
                "divergence_risk": risk,
                "note": _risk_note(risk, label),
            })
    return {
        "label": label,
        "clauses": clauses,
        "provider": result["provider"],
        "comparisons": pairs,
    }


def _risk_note(risk: str, label: str) -> str:
    notes = {
        "HIGH": {
            "auto_renewal": "Renewal terms are materially different - flag for legal review.",
            "price_increase": "Price cap differs significantly - negotiate hardcap language.",
            "data_portability": "Data export windows vary widely - ensure 90-day minimum.",
            "liability_cap": "Liability caps diverge - insist on 12-month fee baseline.",
        },
        "MEDIUM": {
            "auto_renewal": "Similar intent, different notice periods - align to 60 days.",
            "price_increase": "Price language mostly consistent but check annual cap.",
            "data_portability": "Export rights similar but verify retention period.",
            "liability_cap": "Liability caps in same ballpark - confirm calculation method.",
        },
        "LOW": {
            "auto_renewal": "Renewal clauses are substantially equivalent.",
            "price_increase": "Price increase terms are consistent.",
            "data_portability": "Data portability terms are consistent.",
            "liability_cap": "Liability caps are equivalent.",
        },
    }
    return notes.get(risk, {}).get(label, f"{risk} divergence detected.")


def run_demo() -> dict[str, Any]:
    """Full contract similarity demo — called from demo.py."""
    nosana = ping_nosana()
    results = {}
    for label, clauses in DATADOG_CONTRACT_CLAUSES.items():
        results[label] = compare_clauses(label, clauses)

    report = {
        "vendor": "Datadog",
        "nosana_ping": nosana,
        "embedding_provider": list(results.values())[0]["provider"],
        "clause_groups": results,
        "high_risk_flags": [
            {
                "group": label,
                "comparison": cmp,
                "clause_a": results[label]["clauses"][cmp["clause_a_idx"]][:120],
                "clause_b": results[label]["clauses"][cmp["clause_b_idx"]][:120],
            }
            for label, r in results.items()
            for cmp in r["comparisons"]
            if cmp["divergence_risk"] == "HIGH"
        ],
    }
    (FIXTURES / "contract_similarity.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    report = run_demo()
    print(f"Nosana ping: {report['nosana_ping']['status']} (http {report['nosana_ping'].get('http', 'N/A')})")
    print(f"Embedding provider: {report['embedding_provider']}\n")
    for label, r in report["clause_groups"].items():
        print(f"  [{label.upper()}]")
        for cmp in r["comparisons"]:
            print(f"    Clause {cmp['clause_a_idx']+1} vs {cmp['clause_b_idx']+1}: "
                  f"sim={cmp['similarity']:.3f}  risk={cmp['divergence_risk']}  -- {cmp['note']}")
        print()
    if report["high_risk_flags"]:
        print(f"  HIGH RISK FLAGS ({len(report['high_risk_flags'])}):")
        for flag in report["high_risk_flags"]:
            print(f"    [{flag['group']}]")
            print(f"      A: {flag['clause_a']}...")
            print(f"      B: {flag['clause_b']}...")
