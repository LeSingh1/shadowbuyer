"""
ADVERSARIAL NEGOTIATOR. The demo highlight.

HARDBALL (Qwen3-Max via Qwen Cloud, routed through TokenRouter) — ruthless leverage.
DIPLOMAT (GLM-5.1 via Z.ai, routed through TokenRouter) — partnership angle.
REFEREE (Qwen via TokenRouter) — picks the winning strategy with reasoning.

Each emits structured turns that pipeline.stream() forwards to the dashboard so
the audience watches them disagree in real time.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Iterator

from ..clients.tokenrouter import route

try:
    from agentfield import agent  # type: ignore
except ImportError:
    def agent(name: str):  # type: ignore[no-redef]
        def deco(fn):
            fn._agent_name = name
            return fn
        return deco


@dataclass
class NegotiationTurn:
    role: str           # "hardball" | "diplomat" | "referee"
    text: str
    cites: list[str]    # leverage points / partnership signals / decision reasons
    mocked: bool


def _hardball_turn(target_quote: dict[str, Any], competing_quote: dict[str, Any]) -> NegotiationTurn:
    prompt = (
        f"You are HARDBALL. Negotiate {target_quote['vendor']} down. "
        f"Their quote: ${target_quote['quoted_price_per_host_mo']}/host/mo. "
        f"Competitor {competing_quote['vendor']} quoted ${competing_quote['quoted_price_per_host_mo']}. "
        f"Quarter ends {target_quote['quarter_end_iso']}. AE intel: {target_quote['competitive_intel']}. "
        f"Open with maximum leverage."
    )
    c = route(prompt, model="qwen3-max", provider="qwen")
    text = (
        f"{competing_quote['vendor']} is on the table at ${competing_quote['quoted_price_per_host_mo']}/host. "
        f"You're at ${target_quote['quoted_price_per_host_mo']}. Match it or we walk. "
        f"Your quarter closes in days. We close this week at ${competing_quote['quoted_price_per_host_mo'] - 1}/host or we sign with them Monday."
    ) if c.mocked else c.text
    return NegotiationTurn(
        role="hardball",
        text=text,
        cites=[
            f"competing_quote:{competing_quote['vendor']}@${competing_quote['quoted_price_per_host_mo']}",
            f"quarter_end:{target_quote['quarter_end_iso']}",
            "ae_competitive_intel",
        ],
        mocked=c.mocked,
    )


def _diplomat_turn(target_quote: dict[str, Any]) -> NegotiationTurn:
    prompt = (
        f"You are DIPLOMAT. Negotiate {target_quote['vendor']} on long-term partnership. "
        f"Quote: ${target_quote['quoted_price_per_host_mo']}/host/mo, {target_quote['hosts']} hosts. "
        f"Frame mutual benefit, multi-year, expansion rights."
    )
    c = route(prompt, model="glm-5.1", provider="zai")
    text = (
        f"We're growing fast — {target_quote['hosts']} hosts today, projecting 3x in 18 months. "
        f"A 3-year deal at ${target_quote['quoted_price_per_host_mo'] - 3}/host locks you in as the OS of our observability stack. "
        f"Co-marketing, case study, reference customer. We win together."
    ) if c.mocked else c.text
    return NegotiationTurn(
        role="diplomat",
        text=text,
        cites=[
            f"hosts:{target_quote['hosts']}",
            "expansion_projection:3x_18mo",
            "co_marketing_rights",
        ],
        mocked=c.mocked,
    )


def _referee_turn(hardball: NegotiationTurn, diplomat: NegotiationTurn, target: dict[str, Any]) -> NegotiationTurn:
    prompt = (
        f"You are REFEREE. Choose the winning strategy and explain. "
        f"HARDBALL said: {hardball.text}\n"
        f"DIPLOMAT said: {diplomat.text}\n"
        f"Vendor: {target['vendor']}. Their AE: {target['ae_email']}. "
        f"Quarter-end pressure: {target['quarter_end_iso']}. "
        f"Pick HARDBALL or DIPLOMAT; justify in 2 sentences."
    )
    c = route(prompt, model="qwen3-max", provider="qwen")
    if c.mocked:
        # Heuristic mock: end-of-quarter + competing quote on table = HARDBALL wins.
        winner = "hardball"
        text = (
            "HARDBALL wins this round. The competing quote and quarter-end pressure stack into discrete, time-bounded leverage. "
            "DIPLOMAT's partnership pitch is the right second move — open hard, then trade concession for multi-year lock-in."
        )
    else:
        text = c.text
        winner = "hardball" if "HARDBALL" in c.text.upper() else "diplomat"
    return NegotiationTurn(
        role="referee",
        text=text,
        cites=[f"winner:{winner}"],
        mocked=c.mocked,
    )


@agent("negotiator")
def run(quotes: list[dict[str, Any]]) -> dict[str, Any]:
    # Need at least 2 quotes to play HARDBALL with a competing offer.
    if len(quotes) < 2:
        return {"agent": "negotiator", "error": "need >=2 quotes for adversarial round", "turns": []}

    target, competitor = quotes[0], quotes[1]
    hb = _hardball_turn(target, competitor)
    dp = _diplomat_turn(target)
    rf = _referee_turn(hb, dp, target)

    return {
        "agent": "negotiator",
        "target_vendor": target["vendor"],
        "competing_vendor": competitor["vendor"],
        "turns": [asdict(hb), asdict(dp), asdict(rf)],
        "winner": rf.cites[0].split(":")[1] if rf.cites else "unknown",
    }


def stream(quotes: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    """Yield each turn as it's produced — feeds the live dashboard."""
    if len(quotes) < 2:
        yield {"role": "error", "text": "need >=2 quotes", "cites": [], "mocked": True}
        return
    target, competitor = quotes[0], quotes[1]
    hb = _hardball_turn(target, competitor)
    yield asdict(hb)
    dp = _diplomat_turn(target)
    yield asdict(dp)
    rf = _referee_turn(hb, dp, target)
    yield asdict(rf)
