"""Hour 0 smoke test — hit G2's Datadog page through Bright Data and prove
we got real HTML back."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from brightdata_client import fetch  # noqa: E402

URL = "https://www.g2.com/products/datadog/reviews"

if __name__ == "__main__":
    out = fetch(URL, cache_name="datadog_g2", force_refresh=True)
    html = out.get("html", "")
    print(f"status_code: {out.get('status_code')}")
    print(f"html length: {len(html)}")
    print(f"contains 'Datadog': {'Datadog' in html}")
    print(f"served_from_cache: {out.get('_served_from_cache', False)}")
    if out.get("_live_error"):
        print(f"live_error: {out['_live_error']}")
