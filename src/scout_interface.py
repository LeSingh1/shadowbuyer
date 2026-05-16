"""Scout Interface — the single entry point Person A's Scout agent calls.

Usage:
    from scout_interface import get_vendor, get_all_vendors, get_trash_talk

All functions are cache-first: they read from Evermind if populated, else
fall back to fixtures/ JSON directly. Safe to call before API keys are set.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import evermind_client as em

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

SLUG_ALIASES = {
    "new_relic": "newrelic",
    "grafana_cloud": "grafana",
    "grafana cloud": "grafana",
    "new relic": "newrelic",
}

ALL_SLUGS = ["datadog", "newrelic", "honeycomb", "grafana", "splunk"]


def _normalise(slug: str) -> str:
    return SLUG_ALIASES.get(slug.lower().replace(" ", "_"), slug.lower().replace(" ", "_"))


def _fixture(name: str) -> dict[str, Any]:
    path = FIXTURES / name
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def get_vendor(slug: str) -> dict[str, Any]:
    """Return the full vendor profile for a single vendor.

    Merges: G2 data, pricing, status, funding, AE quote, trash-talk.
    """
    s = _normalise(slug)
    def _unwrap(rec: dict | None) -> dict:
        """Evermind stores data under a 'value' key; fixtures store it bare."""
        if rec is None:
            return {}
        return rec.get("value", rec)

    profile = _unwrap(em.read("vendor_profile", s)) or _fixture(f"{s}_profile.json")
    funding_rec = _unwrap(em.read("vendor_profile", f"{s}_funding")) or _fixture("funding_rounds.json").get(s, {})
    quote_slugs = [s, s.replace("newrelic", "new_relic").replace("grafana", "grafana_cloud")]
    quote: dict = {}
    for qs in quote_slugs:
        raw = em.read("ae_quote", qs)
        if raw:
            quote = _unwrap(raw)
            break
    if not quote:
        for qs in quote_slugs:
            q = _fixture(f"quote_{qs}.json")
            if q:
                quote = q
                break
    trash = _unwrap(em.read("trash_talk", s))
    return {
        "slug": s,
        "name": profile.get("name") or slug,
        "g2": profile.get("g2", {}),
        "pricing": profile.get("pricing", {}),
        "status": profile.get("status", {}),
        "funding": funding_rec,
        "ae_quote": quote.get("ae_response", {}),
        "trash_talk": trash.get("competitor_dig") or quote.get("ae_response", {}).get("competitor_dig"),
    }


def get_all_vendors() -> dict[str, dict[str, Any]]:
    """Return profiles for all 5 vendors. Uses aggregate cache when available."""
    agg = _fixture("vendors_aggregate.json")
    if agg:
        return agg
    return {s: get_vendor(s) for s in ALL_SLUGS}


def get_trash_talk() -> list[dict[str, Any]]:
    """Return deduplicated AE trash-talk intel, one entry per vendor."""
    records = em.list_bucket("trash_talk")
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for r in records:
        val = r.get("value", {})
        vendor = val.get("vendor") or val.get("vendor_speaking")
        dig = val.get("competitor_dig") or val.get("intel")
        if not vendor or not dig or dig == "TBD" or vendor in seen:
            continue
        # Skip the aggregate moat_report entry
        if vendor == "ShadowBuyer Competitive Intel":
            continue
        seen.add(vendor)
        result.append({"vendor": vendor, "competitor_dig": dig})
    if result:
        return result
    # Fallback: build from aggregate
    agg = get_all_vendors()
    return [
        {"vendor": v["name"], "competitor_dig": v["trash_talk"]}
        for v in agg.values()
        if v.get("trash_talk") and v["trash_talk"] != "TBD"
    ]


def get_ae_quote(slug: str) -> dict[str, Any]:
    """Return just the AE response for one vendor."""
    return get_vendor(slug).get("ae_quote", {})


def store_negotiation_decision(slug: str, decision: dict[str, Any]) -> None:
    """Person A's Negotiator calls this to persist a decision."""
    em.write("negotiation_decision", _normalise(slug), decision)


if __name__ == "__main__":
    print("=== All vendors ===")
    for slug in ALL_SLUGS:
        v = get_vendor(slug)
        print(f"  {v['name']:15} G2={v['g2'].get('rating')}  quote={v['ae_quote'].get('first_quote')}")

    print("\n=== Trash talk moat ===")
    for t in get_trash_talk():
        print(f"  [{t['vendor']}] \"{t['competitor_dig']}\"")
