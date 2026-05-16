"""
QUOTE HUNTER agent. Owned by Person B (Actionbook). We consume the output.
Mocked here so the pipeline runs end-to-end before Person B's piece lands.
"""
from __future__ import annotations

from typing import Any

try:
    from agentfield import agent  # type: ignore
except ImportError:
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


_MOCK_QUOTES = {
    "Datadog": {
        "vendor": "Datadog",
        "ae_email": "morgan.chen@datadog.com",
        "list_price_per_host_mo": 23,
        "quoted_price_per_host_mo": 19.50,
        "hosts": 500,
        "annual_quote_usd": 117_000,
        "competitive_intel": "AE called Honeycomb 'a toy for tiny teams' and warned that Grafana 'falls over above 100 hosts.' Strong end-of-quarter pressure.",
        "quarter_end_iso": "2026-06-30",
    },
    "New Relic": {
        "vendor": "New Relic",
        "ae_email": "priya.r@newrelic.com",
        "list_price_per_host_mo": 25,
        "quoted_price_per_host_mo": 16.00,
        "hosts": 500,
        "annual_quote_usd": 96_000,
        "competitive_intel": "AE conceded Datadog parity on APM, pitched 'better unit economics post-PE.' Offered 14-month deal for price of 12.",
        "quarter_end_iso": "2026-06-30",
    },
}


@agent("quote_hunter")
def run(vendors: list[dict[str, Any]]) -> dict[str, Any]:
    # In real flow Person B's Actionbook job posts back to us. For now: lookup mocks.
    quotes = []
    for v in vendors:
        q = _MOCK_QUOTES.get(v["name"])
        if q:
            quotes.append(q)
    return {
        "agent": "quote_hunter",
        "quotes": quotes,
        "source": "mock",  # flip to "actionbook" when Person B wires in
    }
