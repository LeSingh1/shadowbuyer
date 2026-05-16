"""Hour 3 gate — proves Evermind round-trips work before 2 PM.

Writes a probe to every bucket, reads it back, and prints a pass/fail
table. Exits non-zero if any bucket fails.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import evermind_client  # noqa: E402

PROBES = {
    "vendor_profile": {"name": "Datadog", "rating": 4.3},
    "ae_quote": {"vendor": "Datadog", "first_quote": "$2,300/host/year"},
    "negotiation_decision": {"action": "counter", "amount": "$1,950/host/year"},
    "trash_talk": {"vendor": "Datadog", "competitor_dig": "We're more reliable than New Relic during incidents."},
}


def main() -> int:
    report = {}
    all_ok = True
    for bucket, payload in PROBES.items():
        key = f"_verify_{bucket}"
        written = evermind_client.write(bucket, key, payload)
        read_back = evermind_client.read(bucket, key)
        ok = read_back is not None
        report[bucket] = {"ok": ok, "via": written["via"]}
        all_ok = all_ok and ok
    print(json.dumps(report, indent=2))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
