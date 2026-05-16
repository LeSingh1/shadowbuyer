"""
CONTRACT DIFF agent (stretch). Compares vendor MSA to a standard template using
Nosana-hosted sentence-transformers embeddings; outputs a redline list.

Hour-4 territory — keep skeleton, fill in only if Negotiator is solid by 2pm.
"""
from __future__ import annotations

import os
from typing import Any

try:
    from agentfield import agent  # type: ignore
except ImportError:
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


_MOCK_REDLINES = [
    {"clause": "Limitation of Liability", "standard": "12 months fees cap", "vendor": "3 months fees cap", "severity": "high"},
    {"clause": "Auto-renewal", "standard": "30-day opt-out window", "vendor": "90-day opt-out window", "severity": "med"},
    {"clause": "Data Processing Addendum", "standard": "SCCs attached", "vendor": "Not attached", "severity": "high"},
    {"clause": "Price Lock", "standard": "Year-2 increase ≤5%", "vendor": "Year-2 increase ≤12%", "severity": "med"},
]


def _nosana_embed(texts: list[str]) -> list[list[float]] | None:
    if not os.getenv("NOSANA_ENDPOINT"):
        return None
    # TODO: POST to Nosana endpoint, return embeddings.
    # import httpx
    # r = httpx.post(os.environ["NOSANA_ENDPOINT"] + "/embed", json={"texts": texts}, timeout=10)
    # return r.json()["embeddings"]
    return None


@agent("contract_diff")
def run(vendor_msa_text: str | None = None, standard_template_text: str | None = None) -> dict[str, Any]:
    embeddings_available = _nosana_embed(["probe"]) is not None
    return {
        "agent": "contract_diff",
        "redlines": _MOCK_REDLINES,
        "embedding_backend": "nosana" if embeddings_available else "mock",
        "msa_provided": bool(vendor_msa_text),
    }
