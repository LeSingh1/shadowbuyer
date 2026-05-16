"""Bright Data fetch wrapper with automatic fixture caching.

Live-first, cache-on-failure. Every successful fetch is persisted to
fixtures/ so the demo survives a Bright Data hiccup.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)

BRIGHTDATA_API_TOKEN = os.getenv("BRIGHTDATA_API_TOKEN", "")
BRIGHTDATA_ZONE = os.getenv("BRIGHTDATA_ZONE", "web_unlocker1")


class BrightDataError(RuntimeError):
    pass


def _cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _cache_path(name: str) -> Path:
    return FIXTURES_DIR / f"{name}.json"


def fetch(url: str, *, cache_name: str, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch a URL through Bright Data Web Unlocker.

    Persists the response to fixtures/<cache_name>.json. If the live call
    fails (no token, network error, non-2xx), returns the cached fixture
    if one exists. Raises BrightDataError only if both live and cache miss.
    """
    cache_file = _cache_path(cache_name)

    if not force_refresh and not BRIGHTDATA_API_TOKEN and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8"))

    live_error: str | None = None
    if BRIGHTDATA_API_TOKEN:
        try:
            payload = {
                "zone": BRIGHTDATA_ZONE,
                "url": url,
                "format": "raw",
            }
            r = requests.post(
                "https://api.brightdata.com/request",
                headers={
                    "Authorization": f"Bearer {BRIGHTDATA_API_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            r.raise_for_status()
            record = {
                "url": url,
                "fetched_at": int(time.time()),
                "status_code": r.status_code,
                "html": r.text,
            }
            cache_file.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            return record
        except Exception as exc:  # noqa: BLE001 — broad on purpose, fallback below
            live_error = f"{type(exc).__name__}: {exc}"

    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        cached["_served_from_cache"] = True
        if live_error:
            cached["_live_error"] = live_error
        return cached

    raise BrightDataError(
        f"Live fetch failed and no cache at {cache_file}. live_error={live_error}"
    )


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "https://www.g2.com/products/datadog/reviews"
    out = fetch(target, cache_name="smoketest")
    print(json.dumps({k: v for k, v in out.items() if k != "html"}, indent=2))
    print(f"html length: {len(out.get('html', ''))}")
