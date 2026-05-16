"""Negotiation Brief — the artifact Person A's Negotiator agent consumes.

Pulls vendor profile + AE quote + trash-talk from Evermind and assembles
a structured brief with recommended counter-offer, leverage points, and
walk-away threshold. Persists both to Evermind and fixtures/.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import evermind_client as em
from scout_interface import get_vendor

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

WALK_AWAY_DISCOUNT = 0.20  # we want at least 20% off list
TARGET_DISCOUNT = 0.15     # aim for 15%


def _parse_price(price_str: str) -> float | None:
    """Extract the first dollar figure from an AE quote string."""
    import re
    m = re.search(r"\$([\d,]+(?:\.\d+)?)", price_str or "")
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _leverage_points(vendor: dict) -> list[str]:
    points = []
    funding = vendor.get("funding", {})
    status = funding.get("status", "")

    if "Acquired by Cisco" in status:
        points.append("Cisco acquisition creates roadmap uncertainty — use as explicit alternative eval leverage.")
    if "taken private" in status.lower():
        points.append(f"{vendor['name']} went private — new owners need logos; use pricing instability angle.")
    if "Public" in status:
        points.append(f"{vendor['name']} is public — sales quarter-end pressure is real, hold for month-end close.")

    g2 = vendor.get("g2", {})
    excerpts = g2.get("review_excerpts", [])
    for ex in excerpts:
        el = ex.lower()
        if any(w in el for w in ("pricing", "expensive", "cost", "bill", "overpriced")):
            points.append(f"G2 reviewers call out pricing pain: \"{ex[:120]}...\"")
            break

    incidents = vendor.get("status", {}).get("recent_incidents", [])
    if incidents:
        points.append(f"Recent reliability incident: {incidents[0][:150]}")

    trash = vendor.get("trash_talk")
    if trash:
        points.append(f"AE volunteered competitive intel (use as counter): \"{trash}\"")

    return points


def build_brief(slug: str) -> dict[str, Any]:
    vendor = get_vendor(slug)
    ae = vendor.get("ae_quote", {})
    list_price_str = ae.get("first_quote", "")
    list_price = _parse_price(list_price_str)

    counter = None
    walk_away = None
    if list_price:
        counter = round(list_price * (1 - TARGET_DISCOUNT), 2)
        walk_away = round(list_price * (1 - WALK_AWAY_DISCOUNT), 2)

    brief: dict[str, Any] = {
        "vendor": vendor["name"],
        "slug": slug,
        "generated_at": int(time.time()),
        "list_quote": {
            "raw": list_price_str,
            "parsed_usd": list_price,
            "discount_offered_by_ae": ae.get("discount_offered"),
        },
        "recommended_counter": f"${counter:,.2f}" if counter else "TBD — negotiate on total contract value",
        "walk_away_threshold": f"${walk_away:,.2f}" if walk_away else "TBD",
        "leverage_points": _leverage_points(vendor),
        "competitor_alternatives": [
            s for s in ["datadog", "newrelic", "honeycomb", "grafana", "splunk"]
            if s != slug
        ],
        "ae_email": ae.get("ae_email"),
        "g2_rating": vendor.get("g2", {}).get("rating"),
        "g2_review_count": vendor.get("g2", {}).get("review_count"),
        "funding_status": vendor.get("funding", {}).get("status"),
        "trash_talk_intel": vendor.get("trash_talk"),
    }

    fixture_path = FIXTURES / f"brief_{slug}.json"
    fixture_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False), encoding="utf-8")
    em.write("negotiation_decision", f"brief_{slug}", brief)
    return brief


def build_all_briefs() -> dict[str, dict]:
    slugs = ["datadog", "newrelic", "honeycomb", "grafana", "splunk"]
    briefs = {s: build_brief(s) for s in slugs}
    (FIXTURES / "briefs_all.json").write_text(
        json.dumps(briefs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return briefs


if __name__ == "__main__":
    briefs = build_all_briefs()
    for slug, b in briefs.items():
        print(f"\n{'='*55}")
        print(f"  {b['vendor']}")
        print(f"  List: {b['list_quote']['raw']}")
        print(f"  Counter: {b['recommended_counter']}")
        print(f"  Walk-away: {b['walk_away_threshold']}")
        print(f"  Leverage points ({len(b['leverage_points'])}):")
        for lp in b["leverage_points"]:
            print(f"    • {lp[:100]}")
