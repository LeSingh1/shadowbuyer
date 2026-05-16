"""Scrape the 5 observability vendors and produce a structured profile per vendor.

Pulls G2 (rating, review excerpts), pricing page (visible text), and the
public status page. Writes one fixture per raw page and one structured
profile per vendor, plus an aggregate file for the dashboard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from brightdata_client import fetch
from vendor_targets import VENDORS

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def parse_g2(html: str) -> dict[str, Any]:
    soup = _soup(html)
    text = soup.get_text(" ", strip=True)
    rating_match = re.search(r"([0-5]\.\d)\s*(?:out of 5|stars)", text, re.IGNORECASE)
    review_count_match = re.search(r"([\d,]+)\s+reviews", text, re.IGNORECASE)
    review_blocks = [
        p.get_text(" ", strip=True)
        for p in soup.find_all(["p", "blockquote"])
        if 80 <= len(p.get_text(" ", strip=True)) <= 600
    ][:5]
    return {
        "rating": float(rating_match.group(1)) if rating_match else None,
        "review_count": int(review_count_match.group(1).replace(",", "")) if review_count_match else None,
        "review_excerpts": review_blocks,
    }


def parse_pricing(html: str) -> dict[str, Any]:
    soup = _soup(html)
    text = soup.get_text(" ", strip=True)
    money = re.findall(r"\$[\d,]+(?:\.\d+)?(?:\s*(?:/|per)\s*\w+)?", text)
    plan_names = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        t = h.get_text(" ", strip=True)
        if 3 <= len(t) <= 60:
            plan_names.append(t)
    return {
        "prices_seen": list(dict.fromkeys(money))[:20],
        "plan_headings": plan_names[:20],
    }


_STATUS_NOISE = re.compile(
    r"(get email|get text|get webhook|get incident|subscribe via|subscribe$|"
    r"atlassian|recaptcha|privacy policy|terms of service|"
    r"enter otp|resend otp|didn.t receive|channel.s webhook|"
    r"microsoft teams|by subscribing|"
    r"no incidents reported today|no downtime recorded|no data exists|"
    r"had a major outage\.$|had a partial outage\.$|"
    r"^operational degraded|partial outage major outage)",
    re.IGNORECASE,
)


def parse_status(html: str) -> dict[str, Any]:
    soup = _soup(html)
    text = soup.get_text(" ", strip=True).lower()
    indicators = ["operational", "degraded", "partial outage", "major outage", "investigating", "monitoring"]
    found = [w for w in indicators if w in text]

    incident_lines = []
    for tag in soup.find_all(["li", "div", "p", "span"]):
        t = tag.get_text(" ", strip=True)
        tl = t.lower()
        if not any(k in tl for k in ("incident", "outage", "degraded", "investigating", "resolved", "disruption")):
            continue
        if _STATUS_NOISE.search(t):
            continue
        if not (40 <= len(t) <= 400):
            continue
        incident_lines.append(t)

    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for line in incident_lines:
        key = line[:60]
        if key not in seen:
            seen.add(key)
            unique.append(line)

    # Atlassian statuspages always list all indicator words in the page even
    # when everything is healthy. Only treat as degraded if the page has
    # real incident entries alongside the indicator.
    active_degraded = any(w in found for w in ("degraded", "partial outage", "major outage", "investigating"))
    has_real_incidents = bool(unique)
    if active_degraded and has_real_incidents:
        current = "Degraded"
    elif "monitoring" in found and has_real_incidents:
        current = "Monitoring"
    else:
        current = "All Systems Operational"
    return {
        "current_status": current,
        "indicators_present": found,
        "recent_incidents": unique[:5],
    }


def build_profile(slug: str) -> dict[str, Any]:
    meta = VENDORS[slug]
    profile: dict[str, Any] = {"slug": slug, "name": meta["name"]}

    g2 = fetch(meta["g2"], cache_name=f"{slug}_g2")
    profile["g2"] = parse_g2(g2.get("html", ""))
    profile["g2"]["source_url"] = meta["g2"]
    profile["g2"]["served_from_cache"] = g2.get("_served_from_cache", False)

    pricing = fetch(meta["pricing"], cache_name=f"{slug}_pricing")
    profile["pricing"] = parse_pricing(pricing.get("html", ""))
    profile["pricing"]["source_url"] = meta["pricing"]

    status = fetch(meta["status"], cache_name=f"{slug}_status")
    profile["status"] = parse_status(status.get("html", ""))
    profile["status"]["source_url"] = meta["status"]

    profile["customer_logos_hint"] = meta["homepage"]
    (FIXTURES / f"{slug}_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return profile


def main() -> None:
    aggregate = {}
    for slug in VENDORS:
        try:
            aggregate[slug] = build_profile(slug)
            print(f"  ok  {slug}")
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {slug}: {exc}")
            aggregate[slug] = {"slug": slug, "error": str(exc)}
    (FIXTURES / "vendors_aggregate.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
