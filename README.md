# ShadowBuyer

Autonomous B2B procurement agent swarm. Demo target: observability tools, live vendor = Datadog.

## Status (Hour 0–1)

- 4 agent stubs land mock JSON: scout, quote_hunter, negotiator, contract_diff
- Sequential pipeline runs end-to-end (`python3 -m src.pipeline`)
- FastAPI app with `/run`, `/run/stream` (SSE), `/healthz`, and live dashboard at `/`
- Docker + `zeabur.toml` ready — deploy empty app to Zeabur before noon
- Every external SDK call is mock-fallback by default; populate `.env` to flip live

## Sponsor wiring (one real reference each — confirm before judging)

| Sponsor       | Where it lives                                        | State |
|---            |---                                                    |---    |
| AgentField    | `@agent("…")` decorators on every agent run()         | stub-import w/ fallback |
| TokenRouter   | `src/clients/tokenrouter.py` — every LLM call routes  | mock until key set |
| Qwen Cloud    | Scout, Hardball, Referee (`provider="qwen"`)          | mock until key set |
| Z.ai          | Diplomat (`provider="zai"`)                           | mock until key set |
| Evermind      | `src/memory/evermind.py` — scout cache + decisions    | local-file fallback |
| Nosana        | `src/agents/contract_diff.py:_nosana_embed`           | mock until endpoint set |
| Bright Data   | `scout.run(bright_data_input=...)` parameter          | upstream from Person B |
| Actionbook    | Quote Hunter is Person B's job; we consume mock JSON  | mock until Person B ships |
| Zeabur        | `Dockerfile` + `zeabur.toml`                          | config ready, deploy pending |
| Qoder         | Used to build this; mention in pitch                  | n/a (process sponsor) |
| Claude Max    | Used to build this; mention in pitch                  | n/a (process sponsor) |

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.app:app --reload --port 8000
# open http://localhost:8000  → click "Run pipeline →"
```

## Deploy to Zeabur

The Dockerfile + `zeabur.toml` are ready. Auth required from your side:

```bash
# one-time
zeabur auth login

# from this directory
zeabur deploy
```

Empty-app target: deployed live URL by 11:30 AM, redeploys every hour.

## Demo highlight: adversarial negotiator

`/run/stream` (SSE) emits each negotiator turn as it's produced. The dashboard
renders HARDBALL (red), DIPLOMAT (green), REFEREE (gold) in real time so the
audience sees the disagreement, not just the verdict.

## Mock-fallback contract

Every external dependency has a deterministic mock so the demo never crashes:
- TokenRouter → returns tagged stub completions
- Evermind → JSON file (`.evermind-fallback.json`, gitignored)
- Nosana → static redline list
- Quote Hunter → hardcoded Datadog + New Relic quotes

Flipping a service to live = drop one env var. Failure of a live call should
fall back to mock (TODO: harden once real SDKs land).
