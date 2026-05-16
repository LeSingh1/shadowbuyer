"""
TokenRouter client. ALL LLM calls route through this per sponsor requirement.

Real SDK: pip install tokenrouter (verify exact package name with sponsor).
Until keys are in .env, route() returns mock completions tagged with the
upstream provider so the pipeline runs end-to-end.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

Provider = Literal["qwen", "zai", "openai"]


@dataclass
class Completion:
    text: str
    provider: Provider
    model: str
    mocked: bool


def route(prompt: str, model: str, provider: Provider, max_tokens: int = 1024) -> Completion:
    api_key = os.getenv("TOKENROUTER_API_KEY")
    if not api_key:
        return _mock(prompt, model, provider)

    # TODO: real TokenRouter SDK call goes here.
    # from tokenrouter import Client
    # client = Client(api_key=api_key)
    # resp = client.completions.create(model=model, provider=provider,
    #                                  prompt=prompt, max_tokens=max_tokens)
    # return Completion(text=resp.text, provider=provider, model=model, mocked=False)
    return _mock(prompt, model, provider)


def _mock(prompt: str, model: str, provider: Provider) -> Completion:
    snippet = prompt.strip().split("\n", 1)[0][:120]
    return Completion(
        text=f"[MOCK {provider}/{model}] would respond to: {snippet}",
        provider=provider,
        model=model,
        mocked=True,
    )
