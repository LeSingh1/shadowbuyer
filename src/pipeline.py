"""
ShadowBuyer pipeline: Scout → Quote Hunter → Negotiator → (Contract Diff) → Output.
- run() returns a full snapshot for batch demos and /api/demo-state
- stream() yields paced events for the live dashboard
"""
from __future__ import annotations

import time
from typing import Any, Iterator

from .agents import scout, quote_hunter, negotiator, contract_diff

# Pacing for the live demo. ~3.2s of negotiator turns total — tense but not boring.
PACE_STAGE_S = 0.35
PACE_TURN_S = 0.55


def run(
    category: str = "observability",
    bright_data_input: dict | None = None,
    include_contract_diff: bool = False,
) -> dict[str, Any]:
    s = scout.run(category, bright_data_input)
    q = quote_hunter.run(s["vendors"])
    n = negotiator.run(q["quotes"])
    out: dict[str, Any] = {"scout": s, "quote_hunter": q, "negotiator": n}
    if include_contract_diff:
        out["contract_diff"] = contract_diff.run()
    out["summary"] = _summary(s, q, n)
    return out


def stream(
    category: str = "observability",
    bright_data_input: dict | None = None,
    pace: bool = True,
) -> Iterator[dict[str, Any]]:
    def _sleep(s: float) -> None:
        if pace:
            time.sleep(s)

    yield {"event": "stage_start", "stage": "scout", "label": "Researching observability vendors"}
    _sleep(PACE_STAGE_S)
    s = scout.run(category, bright_data_input)
    yield {"event": "stage_done", "stage": "scout", "payload": s}
    _sleep(PACE_STAGE_S)

    yield {"event": "stage_start", "stage": "quote_hunter", "label": "Pulling vendor quotes via Actionbook"}
    _sleep(PACE_STAGE_S)
    q = quote_hunter.run(s["vendors"])
    yield {"event": "stage_done", "stage": "quote_hunter", "payload": q}
    _sleep(PACE_STAGE_S)

    yield {
        "event": "stage_start",
        "stage": "negotiator",
        "label": f"Adversarial negotiation: {q['quotes'][0]['vendor']} vs {q['quotes'][1]['vendor']}",
        "target_vendor": q["quotes"][0]["vendor"],
        "competing_vendor": q["quotes"][1]["vendor"],
        "list_price_per_host_mo": q["quotes"][0]["list_price_per_host_mo"],
        "starting_quote_per_host_mo": q["quotes"][0]["quoted_price_per_host_mo"],
        "hosts": q["quotes"][0]["hosts"],
    }
    _sleep(PACE_STAGE_S)
    for turn in negotiator.stream(q["quotes"]):
        yield {"event": "negotiator_turn", "turn": turn}
        _sleep(PACE_TURN_S)
    yield {"event": "stage_done", "stage": "negotiator"}

    n = negotiator.run(q["quotes"])
    yield {"event": "summary", "payload": _summary(s, q, n)}
    yield {"event": "done"}


def _summary(s: dict, q: dict, n: dict) -> dict[str, Any]:
    if "error" in n:
        return {"ok": False, "reason": n["error"]}
    target = q["quotes"][0]
    list_price = target["list_price_per_host_mo"]
    final_price = n.get("final_price_per_host_mo") or target["quoted_price_per_host_mo"]
    hosts = target["hosts"]
    yr1_list_cost = list_price * hosts * 12
    yr1_final_cost = final_price * hosts * 12
    return {
        "ok": True,
        "vendor": n["target_vendor"],
        "competing_vendor": n["competing_vendor"],
        "hosts": hosts,
        "list_price_per_host_mo": list_price,
        "starting_quote_per_host_mo": target["quoted_price_per_host_mo"],
        "final_price_per_host_mo": final_price,
        "annual_savings_vs_list_usd": round(yr1_list_cost - yr1_final_cost, 2),
        "discount_vs_list_pct": round((list_price - final_price) / list_price * 100, 1),
        "winning_strategy": n.get("winner"),
        "round_count": sum(1 for t in n["turns"] if t["role"] in ("hardball", "diplomat")),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
