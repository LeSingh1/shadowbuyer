"""Evermind memory client — persistent store for vendor profiles, AE quotes,
negotiation decisions, and the trash-talk moat.

Falls back to a local JSON file when EVERMIND_API_KEY isn't set so the rest
of the pipeline keeps working in offline demo mode.
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
EVERMIND_NAMESPACE = os.getenv("EVERMIND_NAMESPACE", "shadowbuyer")

# Buckets — the four memory categories the brief calls out
BUCKETS = {
    "vendor_profile",
    "ae_quote",
    "negotiation_decision",
    "trash_talk",
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
    if not EVERMIND_API_KEY:
        return False
    try:
        r = requests.post(
            f"{EVERMIND_BASE_URL}/v1/memories",
            headers={"Authorization": f"Bearer {EVERMIND_API_KEY}"},
            json={
                "namespace": EVERMIND_NAMESPACE,
                "bucket": bucket,
                "key": key,
                "value": value,
                "timestamp": int(time.time()),
            },
            timeout=30,
        )
        r.raise_for_status()
        return True
    except Exception:
        return False


def _live_read(bucket: str, key: str) -> dict[str, Any] | None:
    if not EVERMIND_API_KEY:
        return None
    try:
        r = requests.get(
            f"{EVERMIND_BASE_URL}/v1/memories/{EVERMIND_NAMESPACE}/{bucket}/{key}",
            headers={"Authorization": f"Bearer {EVERMIND_API_KEY}"},
            timeout=30,
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def write(bucket: str, key: str, value: dict[str, Any]) -> dict[str, Any]:
    if bucket not in BUCKETS:
        raise ValueError(f"unknown bucket {bucket!r}; expected one of {sorted(BUCKETS)}")
    record = {
        "id": str(uuid.uuid4()),
        "bucket": bucket,
        "key": key,
        "value": value,
        "ts": int(time.time()),
        "via": "live" if _live_write(bucket, key, value) else "local",
    }
    data = _local_load()
    data[bucket][key] = record
    _local_save(data)
    return record


def read(bucket: str, key: str) -> dict[str, Any] | None:
    live = _live_read(bucket, key)
    if live is not None:
        return live
    data = _local_load()
    return data.get(bucket, {}).get(key)


def list_bucket(bucket: str) -> list[dict[str, Any]]:
    data = _local_load()
    return list(data.get(bucket, {}).values())


def verify() -> dict[str, Any]:
    """Round-trip check called from scripts/verify_evermind.py before 2 PM."""
    probe_key = f"_verify_{int(time.time())}"
    payload = {"hello": "shadowbuyer", "demo": "datadog"}
    written = write("vendor_profile", probe_key, payload)
    read_back = read("vendor_profile", probe_key)
    ok = read_back is not None and (
        read_back.get("value", {}).get("hello") == "shadowbuyer"
        or read_back.get("hello") == "shadowbuyer"
    )
    return {"ok": ok, "via": written["via"], "key": probe_key, "read_back": read_back}


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
