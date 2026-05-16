"""ShadowBuyer data layer demo — runs the Datadog golden path end-to-end.

Run: python demo.py
     python demo.py --live   (forces fresh Bright Data pull if key is set)

Person A's Scout agent imports: from src.scout_interface import get_vendor, get_trash_talk
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from contract_similarity import run_demo as run_contract_demo
from negotiation_brief import build_brief
from nosana_embeddings import ping_nosana
from scout_interface import get_all_vendors, get_trash_talk, get_vendor, store_negotiation_decision
from trash_talk_report import build_report as build_trash_talk_report


def _hr(label: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print("=" * 60)


def run_demo(live: bool = False) -> None:
    _hr("1. Vendor Profiles (Scout output)")
    vendors = get_all_vendors()
    for slug, v in vendors.items():
        g2 = v.get("g2") or {}
        funding = v.get("funding") or {}
        print(
            f"  {v.get('name', slug):15} "
            f"G2={g2.get('rating', '?')} ({g2.get('review_count', '?')} reviews)  "
            f"status={funding.get('status', '?')}"
        )

    _hr("2. Datadog — detailed profile")
    dd = get_vendor("datadog")
    print(json.dumps(dd, indent=2))

    _hr("3. AE Quote + Negotiation Intel (Quote Hunter output)")
    for slug in ["datadog", "newrelic", "honeycomb", "grafana", "splunk"]:
        v = get_vendor(slug)
        q = v.get("ae_quote", {})
        print(
            f"  {v.get('name', slug):15}  "
            f"quote={q.get('first_quote', 'N/A'):35}  "
            f"discount={q.get('discount_offered', 'N/A')}"
        )

    _hr("4. Trash-Talk Moat (the competitive intel angle)")
    for t in get_trash_talk():
        vendor = t.get("vendor", "?")
        dig = t.get("competitor_dig", "?")
        print(f"  [{vendor}] \"{dig}\"")

    _hr("5. Negotiation Brief — Datadog golden path")
    brief = build_brief("datadog")
    print(f"  List price:   {brief['list_quote']['raw']}")
    print(f"  Counter:      {brief['recommended_counter']}")
    print(f"  Walk-away:    {brief['walk_away_threshold']}")
    print(f"  Leverage ({len(brief['leverage_points'])} points):")
    for lp in brief["leverage_points"]:
        print(f"    • {lp[:110]}")
    print(f"  Brief saved -> fixtures/brief_datadog.json + Evermind negotiation_decision/brief_datadog")

    _hr("5b. Trash-Talk Moat — competitive intel from all AE calls")
    tt_report = build_trash_talk_report()
    for entry in tt_report["entries"]:
        print(f"  [{entry['vendor_speaking']}]: \"{entry['intel'][:80]}\"")
        print(f"    Play: {entry['how_to_use'][:110]}")
        print()

    _hr("5b. Nosana — live API ping + clause similarity embeddings")
    nosana_ping = ping_nosana()
    nosana_ping = ping_nosana()
    print(f"  Nosana API ping: status={nosana_ping['status']} http={nosana_ping.get('http', 'N/A')}")
    contract = run_contract_demo()
    print(f"  Embedding provider: {contract['embedding_provider']}")
    for label, r in contract["clause_groups"].items():
        for cmp in r["comparisons"]:
            print(f"  [{label}] clause {cmp['clause_a_idx']+1} vs {cmp['clause_b_idx']+1}: "
                  f"sim={cmp['similarity']:.3f}  risk={cmp['divergence_risk']}")
    if contract["high_risk_flags"]:
        print(f"\n  HIGH RISK ({len(contract['high_risk_flags'])} flags):")
        for flag in contract["high_risk_flags"][:3]:
            note = flag.get("comparison", {}).get("note", "")
            print(f"    [{flag['group']}] {note}")

    _hr("6. Sponsor Coverage")
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/check_sponsor_coverage.py"],
        capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if "[PASS]" in line or "[FAIL]" in line:
            print(" ", line.strip())

    print("\n  Demo complete. All fixtures cached in fixtures/.")
    print("  Add API keys to .env and re-run with --live for real data.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Force fresh Bright Data pulls")
    args = parser.parse_args()
    run_demo(live=args.live)
