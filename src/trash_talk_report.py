"""Trash-Talk Moat — the competitive intel angle that makes ShadowBuyer unique.

AEs voluntarily reveal competitor weaknesses during sales calls.
ShadowBuyer captures this, stores it in Evermind, and uses it as leverage
in every subsequent negotiation. This is the moat.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import evermind_client as em
from scout_interface import get_all_vendors

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def build_report() -> dict:
    vendors = get_all_vendors()
    entries = []

    for slug, v in vendors.items():
        dig = v.get("trash_talk")
        if not dig or dig == "TBD":
            continue
        ae = v.get("ae_quote", {})
        entries.append({
            "vendor_speaking": v["name"],
            "their_quote": ae.get("first_quote"),
            "intel": dig,
            "how_to_use": _counter_play(v["name"], dig, vendors),
            "source": "AE sales call (via Actionbook quote capture)",
        })

    report = {
        "title": "ShadowBuyer Competitive Intel — Trash-Talk Moat",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": (
            f"{len(entries)} vendors volunteered competitive intel during sales calls. "
            "ShadowBuyer captures this automatically and uses it in negotiation."
        ),
        "entries": entries,
        "moat_explanation": (
            "Traditional procurement: you hear one AE's pitch and believe it. "
            "ShadowBuyer: you hear ALL AEs trash-talk each other, then use each "
            "statement as negotiation leverage against the vendor that made it. "
            "Datadog says New Relic has incidents? Tell Datadog you're evaluating "
            "New Relic anyway and watch the discount grow."
        ),
    }

    (FIXTURES / "trash_talk_moat.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    em.write("trash_talk", "moat_report", report)
    return report


def _counter_play(speaker: str, intel: str, vendors: dict) -> str:
    """Generate a specific negotiation counter-play from the trash-talk intel."""
    il = intel.lower()
    targets = [
        v["name"] for slug, v in vendors.items()
        if v["name"].lower() != speaker.lower()
        and v["name"].lower() in il
    ]
    if not targets:
        return (
            f"Feed {speaker}'s own words back to them: 'Your AE raised those exact "
            f"concerns about competitors — which is why we're keeping our options open. "
            f"Help us justify choosing you with a stronger commercial offer.'"
        )
    target = targets[0]
    # Build a specific play based on what was said
    if "reliable" in il or "incident" in il or "outage" in il:
        angle = "reliability"
        ask = "an SLA-backed uptime guarantee or credits"
    elif "lock" in il or "proprietary" in il or "vendor" in il:
        angle = "lock-in risk"
        ask = "a termination-for-convenience clause with no penalty"
    elif "cost" in il or "expensive" in il or "nickel" in il or "price" in il:
        angle = "total cost of ownership"
        ask = "a price-match or 20%+ discount to justify staying"
    else:
        angle = "competitive positioning"
        ask = "a better commercial offer"

    return (
        f"Reply to {speaker}: 'We appreciate the intel on {target}. "
        f"That's exactly why we have a parallel {target} eval running. "
        f"If {angle} is really your edge, prove it with {ask}.'"
    )


if __name__ == "__main__":
    report = build_report()
    print(f"\n{'='*60}")
    print(f"  {report['title']}")
    print(f"  {report['summary']}")
    print(f"{'='*60}")
    for e in report["entries"]:
        print(f"\n  [{e['vendor_speaking']}] said:")
        print(f"    \"{e['intel']}\"")
        print(f"  Counter-play: {e['how_to_use']}")
    print(f"\n  Moat:\n  {report['moat_explanation']}")
