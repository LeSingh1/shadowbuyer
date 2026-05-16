"""Evermind (EverMemOS) client — persistent conversational memory for ShadowBuyer.

API format: POST /api/v1/memories — stores messages with content/role.
GET memories: POST /api/v1/memories/get with filters.
Search: POST /api/v1/memories/search.

Falls back to local JSON store when EVERMIND_API_KEY isn't set.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
LOCAL_STORE = FIXTURES / "evermind_local.json"

EVERMIND_API_KEY = os.getenv("EVERMIND_API_KEY", "")
EVERMIND_BASE_URL = os.getenv("EVERMIND_BASE_URL", "https://api.evermind.ai")
EVERMIND_USER_ID = os.getenv("EVERMIND_USER_ID", "shadowbuyer-agent")

BUCKETS = {
    "vendor_profile",
    "ae_quote",
    "negotiation_decision",
    "trash_talk",
}


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {EVERMIND_API_KEY}",
        "Content-Type": "application/json",
    }


def _local_load() -> dict[str, Any]:
    if not LOCAL_STORE.exists():
        return {b: {} for b in BUCKETS}
    data = json.loads(LOCAL_STORE.read_text(encoding="utf-8"))
    for b in BUCKETS:
        data.setdefault(b, {})
    return data


def _local_save(data: dict[str, Any]) -> None:
    LOCAL_STORE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _live_write(bucket: str, key: str, value: dict[str, Any]) -> bool:
    """Store as a conversational memory message. Content encodes bucket+key+value."""
    if not EVERMIND_API_KEY:
        return False
    content = json.dumps({"bucket": bucket, "key": key, "value": value}, ensure_ascii=False)
    payload = {
        "user_id": EVERMIND_USER_ID,
        "messages": [{
            "sender_id": EVERMIND_USER_ID,
            "role": "user",
            "timestamp": int(time.time() * 1000),
            "content": content,
        }],
        "async_mode": True,
    }
    try:
        r = requests.post(
            f"{EVERMIND_BASE_URL}/api/v1/memories",
            headers=_headers(),
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return True
    except Exception:
        return False


def _live_search(bucket: str, key: str) -> dict[str, Any] | None:
    """Search memories for bucket+key combination."""
    if not EVERMIND_API_KEY:
        return None
    try:
        query = f"bucket:{bucket} key:{key}"
        r = requests.post(
            f"{EVERMIND_BASE_URL}/api/v1/memories/search",
            headers=_headers(),
            json={
                "query": query,
                "method": "hybrid",
                "top_k": 5,
                "memory_types": ["episodic_memory"],
                "filters": {"user_id": EVERMIND_USER_ID},
            },
            timeout=30,
        )
        r.raise_for_status()
        episodes = r.json().get("data", {}).get("episodes", [])
        for ep in episodes:
            content = ep.get("summary") or ep.get("episode") or ep.get("content", "")
            try:
                parsed = json.loads(content)
                if parsed.get("bucket") == bucket and parsed.get("key") == key:
                    return parsed.get("value")
            except Exception:
                pass
    except Exception:
        pass
    return None


def write(bucket: str, key: str, value: dict[str, Any]) -> dict[str, Any]:
    if bucket not in BUCKETS:
        raise ValueError(f"unknown bucket {bucket!r}; expected one of {sorted(BUCKETS)}")
    via = "live" if _live_write(bucket, key, value) else "local"
    record = {
        "id": str(uuid.uuid4()),
        "bucket": bucket,
        "key": key,
        "value": value,
        "ts": int(time.time()),
        "via": via,
    }
    data = _local_load()
    data[bucket][key] = record
    _local_save(data)
    return record


def read(bucket: str, key: str) -> dict[str, Any] | None:
    live = _live_search(bucket, key)
    if live is not None:
        return {"value": live, "via": "live"}
    data = _local_load()
    return data.get(bucket, {}).get(key)


def list_bucket(bucket: str) -> list[dict[str, Any]]:
    data = _local_load()
    return list(data.get(bucket, {}).values())


def verify() -> dict[str, Any]:
    probe_key = f"_verify_{int(time.time())}"
    payload = {"hello": "shadowbuyer", "demo": "datadog"}
    written = write("vendor_profile", probe_key, payload)
    read_back = read("vendor_profile", probe_key)
    ok = read_back is not None
    return {"ok": ok, "via": written["via"], "key": probe_key}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
