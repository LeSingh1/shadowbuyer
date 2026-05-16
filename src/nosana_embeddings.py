"""Nosana embeddings — clause similarity for the Contract Diff agent.

Strategy:
1. Ping Nosana's deployment API (dashboard.k8s.prd.nos.ci) with our live
   key — this is the real sponsor API hit that checks the box.
2. If a NOSANA_ENDPOINT for a running deployment is set, call it for
   actual embeddings.
3. Fall back to pseudo-embeddings so the demo never crashes.
   The brief explicitly allows this sham: "one API hit so the sponsor box
   is checked."
"""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

NOSANA_ENDPOINT = os.getenv("NOSANA_ENDPOINT", "")
NOSANA_API_KEY = os.getenv("NOSANA_API_KEY", "")
NOSANA_DASHBOARD_API = "https://dashboard.k8s.prd.nos.ci/api"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EMBED_DIM = 384  # MiniLM-L6 default


def ping_nosana() -> dict:
    """Make a real authenticated Nosana API call — satisfies sponsor requirement.

    Lists deployments on the account. Returns the raw response so judges can
    see a live Nosana API hit in the demo output.
    """
    if not NOSANA_API_KEY:
        return {"status": "no_key"}
    try:
        r = requests.get(
            f"{NOSANA_DASHBOARD_API}/deployments",
            headers={"Authorization": f"Bearer {NOSANA_API_KEY}"},
            timeout=15,
        )
        r.raise_for_status()
        result = r.json()
        (FIXTURES / "nosana_deployments.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return {"status": "ok", "deployments": result.get("deployments", []), "http": r.status_code}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _pseudo_embedding(text: str, dim: int = EMBED_DIM) -> list[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    out: list[float] = []
    i = 0
    while len(out) < dim:
        out.append((h[i % len(h)] / 255.0) - 0.5)
        i += 1
    norm = math.sqrt(sum(x * x for x in out)) or 1.0
    return [x / norm for x in out]


def _embed_nosana(texts: list[str]) -> list[list[float]] | None:
    if not (NOSANA_ENDPOINT and NOSANA_API_KEY):
        return None
    try:
        r = requests.post(
            NOSANA_ENDPOINT,
            headers={"Authorization": f"Bearer {NOSANA_API_KEY}"},
            json={"inputs": texts, "model": "sentence-transformers/all-MiniLM-L6-v2"},
            timeout=60,
        )
        r.raise_for_status()
        payload = r.json()
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            return payload
        if "embeddings" in payload:
            return payload["embeddings"]
    except Exception:
        return None
    return None


def _embed_openai(texts: list[str]) -> list[list[float]] | None:
    if not OPENAI_API_KEY:
        return None
    try:
        r = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": "text-embedding-3-small", "input": texts},
            timeout=60,
        )
        r.raise_for_status()
        return [item["embedding"] for item in r.json()["data"]]
    except Exception:
        return None


def embed(texts: Iterable[str]) -> dict[str, list[list[float]] | str]:
    texts = list(texts)
    vecs = _embed_nosana(texts)
    if vecs is not None:
        provider = "nosana"
    else:
        vecs = _embed_openai(texts)
        if vecs is not None:
            provider = "openai_fallback"
        else:
            vecs = [_pseudo_embedding(t) for t in texts]
            provider = "pseudo"
    out = {"provider": provider, "embeddings": vecs}
    (FIXTURES / "embeddings_last.json").write_text(
        json.dumps({"provider": provider, "count": len(vecs), "dim": len(vecs[0]) if vecs else 0}),
        encoding="utf-8",
    )
    return out


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


if __name__ == "__main__":
    sample = [
        "Customer may terminate this agreement with 30 days written notice.",
        "Either party may terminate by providing thirty (30) days notice.",
        "The fee shall increase by 7% on each anniversary date.",
    ]
    out = embed(sample)
    print("provider:", out["provider"])
    vs = out["embeddings"]
    print(f"sim(0,1) similar termination clauses = {cosine(vs[0], vs[1]):.3f}")
    print(f"sim(0,2) different clause             = {cosine(vs[0], vs[2]):.3f}")
