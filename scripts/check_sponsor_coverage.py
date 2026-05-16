"""Hour 5 gate — verifies all 4 sponsor APIs have real code references and
at least one fixture cached. Prints a pass/fail table and exits non-zero
if any sponsor is missing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"
SRC = ROOT / "src"


def check(name: str, src_files: list[str], fixture_globs: list[str]) -> dict:
    # Check source references
    src_ok = all((SRC / f).exists() for f in src_files)
    # Check at least one fixture exists
    fixtures_found = []
    for g in fixture_globs:
        fixtures_found.extend(list(FIXTURES.glob(g)))
    return {
        "src_ok": src_ok,
        "src_files": src_files,
        "fixtures": [f.name for f in fixtures_found],
        "fixtures_ok": bool(fixtures_found),
        "ok": src_ok and bool(fixtures_found),
    }


SPONSORS = {
    "Bright Data": check(
        "Bright Data",
        ["brightdata_client.py"],
        ["*_g2.json", "*_profile.json", "datadog_g2.json"],
    ),
    "Actionbook": check(
        "Actionbook",
        ["actionbook_quote_hunter.py"],
        ["quote_*.json"],
    ),
    "Evermind": check(
        "Evermind",
        ["evermind_client.py"],
        ["evermind_local.json"],
    ),
    "Nosana": check(
        "Nosana",
        ["nosana_embeddings.py"],
        ["embeddings_last.json"],
    ),
}

all_ok = all(v["ok"] for v in SPONSORS.values())
print(json.dumps(SPONSORS, indent=2))
print()
for sponsor, result in SPONSORS.items():
    status = "PASS" if result["ok"] else "FAIL"
    print(f"  [{status}] {sponsor}")
sys.exit(0 if all_ok else 1)
