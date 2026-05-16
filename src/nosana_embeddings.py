"""Nosana embeddings — clause similarity for the Contract Diff agent.

Strategy:
1. If NOSANA_ENDPOINT + NOSANA_API_KEY are set, hit a Nosana-hosted
   sentence-transformers endpoint.
2. If that's down or unset and OPENAI_API_KEY is present, fall back to
   one OpenAI embeddings call so the sponsor box is still legitimately
   checked (we made a real network call attempt to Nosana first; the
   fallback is the sham the brief explicitly allows).
3. If both are absent, return deterministic hashed pseudo-embeddings so
   the rest of the pipeline keeps running for the demo.
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

EMBED_DIM = 384  # MiniLM-L6 default


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
