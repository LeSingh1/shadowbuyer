"""
ShadowBuyer pipeline: Scout → Quote Hunter → Negotiator → (Contract Diff) → Output.
Synchronous run() for batch demos; stream() yields events for the live dashboard.
"""
from __future__ import annotations

from typing import Any, Iterator

from .agents import scout, quote_hunter, negotiator, contract_diff


def run(category: str = "observability", bright_data_input: dict | None = None, include_contract_diff: bool = False) -> dict[str, Any]:
    s = scout.run(category, bright_data_input)
    q = quote_hunter.run(s["vendors"])
    n = negotiator.run(q["quotes"])
    out: dict[str, Any] = {"scout": s, "quote_hunter": q, "negotiator": n}
    if include_contract_diff:
        out["contract_diff"] = contract_diff.run()
    return out


def stream(category: str = "observability", bright_data_input: dict | None = None) -> Iterator[dict[str, Any]]:
    yield {"event": "stage_start", "stage": "scout"}
    s = scout.run(category, bright_data_input)
    yield {"event": "stage_done", "stage": "scout", "payload": s}

    yield {"event": "stage_start", "stage": "quote_hunter"}
    q = quote_hunter.run(s["vendors"])
    yield {"event": "stage_done", "stage": "quote_hunter", "payload": q}

    yield {"event": "stage_start", "stage": "negotiator"}
    for turn in negotiator.stream(q["quotes"]):
        yield {"event": "negotiator_turn", "turn": turn}
    yield {"event": "stage_done", "stage": "negotiator"}

    yield {"event": "done"}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
