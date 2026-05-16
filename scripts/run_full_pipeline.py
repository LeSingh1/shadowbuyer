"""End-to-end Datadog run: scrape -> Evermind write -> Actionbook quote ->
Evermind write -> trash-talk extraction. Produces the demo path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import evermind_client  # noqa: E402
from actionbook_quote_hunter import hunt_quote  # noqa: E402
from scrape_vendors import build_profile  # noqa: E402
from vendor_targets import VENDORS  # noqa: E402


def run_for(slug: str) -> dict:
    meta = VENDORS[slug]
    profile = build_profile(slug)
    evermind_client.write("vendor_profile", slug, profile)

    contact_url = f"https://www.{slug}.com/contact-sales/" if slug != "grafana" else "https://grafana.com/contact/"
    quote = hunt_quote(meta["name"], contact_url)
    evermind_client.write("ae_quote", slug, quote)

    dig = quote.get("ae_response", {}).get("competitor_dig")
    if dig and dig != "TBD":
        evermind_client.write("trash_talk", slug, {
            "vendor": meta["name"],
            "competitor_dig": dig,
            "from_quote_key": slug,
        })
    return {"slug": slug, "profile_ok": "error" not in profile, "quote_ok": bool(quote)}


def main() -> None:
    results = {slug: run_for(slug) for slug in VENDORS}
    (ROOT / "fixtures" / "pipeline_report.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
