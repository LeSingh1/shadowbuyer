"""
Evermind persistent memory adapter.

Stores vendor history, AE quotes, and negotiation decisions across runs.
Falls back to a JSON file when EVERMIND_API_KEY is missing so demo
deterministically replays prior context.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_LOCAL_STORE = Path(__file__).parent.parent.parent / ".evermind-fallback.json"


def write(namespace: str, key: str, value: Any) -> bool:
    api_key = os.getenv("EVERMIND_API_KEY")
    if not api_key:
        return _local_write(namespace, key, value)
    # TODO: real Evermind SDK call.
    # from evermind import Client
    # Client(api_key=api_key).put(namespace, key, value)
    return _local_write(namespace, key, value)


def read(namespace: str, key: str) -> Any | None:
    api_key = os.getenv("EVERMIND_API_KEY")
    if not api_key:
        return _local_read(namespace, key)
    # TODO: real Evermind SDK call.
    return _local_read(namespace, key)


def _load() -> dict:
    if not _LOCAL_STORE.exists():
        return {}
    try:
        return json.loads(_LOCAL_STORE.read_text())
    except json.JSONDecodeError:
        return {}


def _local_write(namespace: str, key: str, value: Any) -> bool:
    data = _load()
    data.setdefault(namespace, {})[key] = {"value": value, "ts": time.time()}
    _LOCAL_STORE.write_text(json.dumps(data, indent=2, default=str))
    return True


def _local_read(namespace: str, key: str) -> Any | None:
    entry = _load().get(namespace, {}).get(key)
    return entry["value"] if entry else None
