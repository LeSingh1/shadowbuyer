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

from scout_interface import get_all_vendors, get_trash_talk, get_vendor, store_negotiation_decision


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

    _hr("5. Storing a sample Negotiation Decision in Evermind")
    store_negotiation_decision("datadog", {
        "action": "counter",
        "target_price": "$1,950/host/year",
        "rationale": "New Relic went private — use pricing instability as leverage",
        "leverage": "Splunk/Cisco acquisition uncertainty cited as eval alternative",
    })
    print("  Decision stored in Evermind: negotiation_decision/datadog")

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
