# ShadowBuyer

Autonomous B2B procurement agent swarm. Demo category: observability tools. Live vendor: Datadog.

Demo arc: 6 agents collapse 6 weeks of SaaS procurement into 6 hours.

## Status (Hours 0–4 done)

Backend (Person A):
- ✅ 4 agents wired: Scout, Quote Hunter (consumer), Adversarial Negotiator (Hardball + Diplomat + Referee), Contract Diff
- ✅ Sequential pipeline; live SSE stream
- ✅ Two-column live dashboard with verdict, drafted email to AE, and 15-redline MSA review
- ✅ Mock-fallback contract: every external client returns deterministic stub data when keys are missing
- ✅ GitHub repo public at [LeSingh1/shadowbuyer](https://github.com/LeSingh1/shadowbuyer)
- ⏳ Zeabur deploy pending (needs `zeabur auth login` from Person A's terminal)

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.app:app --reload --port 8000
open http://localhost:8000   # click "Run negotiation →"
```

## Endpoints

| Method | Path | Returns |
|---|---|---|
| `GET`  | `/`                 | live dashboard (HTML) |
| `GET`  | `/healthz`          | `{ok, version, services: {tokenrouter_live, qwen_live, zai_live, evermind_live, nosana_live, brightdata_live}}` |
| `POST` | `/run`              | full pipeline snapshot (sync) — `{scout, quote_hunter, negotiator, contract_diff, summary}` |
| `GET`  | `/run/stream`       | SSE stream of stage + turn events (see contract below) |
| `GET`  | `/api/demo-state`   | cached snapshot, warmed on startup; pass `?refresh=true` to regenerate |
| `GET`  | `/api/email-draft`  | drafted AE email derived from the winning negotiation strategy |

## SSE stream contract (`/run/stream`)

Events arrive as `data: {json}\n\n`. Paced so the dashboard animates over ~7–8 seconds total.

| Event | Payload shape | Notes |
|---|---|---|
| `stage_start`           | `{stage, label, ...}`                                                        | One per pipeline stage |
| `stage_done`            | `{stage, payload?}`                                                          | Payload present for scout, quote_hunter, contract_diff |
| `negotiator_turn`       | `{turn: {round, role, headline, text, cites[], price_target_per_host_mo, deal_term_months, mocked}}` | role ∈ {hardball, diplomat, referee} |
| `contract_diff_summary` | `{vendor, redline_count, severity_counts: {high, med, low}, embedding_backend}` | Once, before redlines stream |
| `redline`               | `{redline: {clause_key, clause_title, severity, standard_text, vendor_text, similarity, deviation_summary, recommended_redline}}` | One per flagged clause |
| `summary`               | `{payload: {vendor, hosts, list_price_per_host_mo, final_price_per_host_mo, annual_savings_vs_list_usd, discount_vs_list_pct, winning_strategy, contract_redline_count, contract_high_severity, ...}}` | Once near end |
| `done`                  | `{}`                                                                          | Close the EventSource |

## Demo numbers (current mock)

- Vendor: Datadog · Competing: New Relic · Hosts: 500
- List: **$195/host/mo** ($2,340/host/yr, matches doc-spec AE response)
- Starting quote: $175.50 (10% AE discount)
- Final after 3-round adversarial negotiation: **$157.50/host/mo**
- **Annual savings vs list: $225,000** · **Discount: 19.2%**
- Winning strategy: HARDBALL · Email drafted to morgan.chen@datadog.com
- Contract Diff: **15 redlines** flagged · 7 high / 6 med / 2 low
  - High includes the auto-renewal trap and the missing data-deletion clause (doc pitch beats)

## Sponsor coverage (Person A's 5 + integration points for the rest)

| Sponsor       | Code reference                                                              | State                  |
|---            |---                                                                          |---                     |
| AgentField    | `@agent("…")` on every agent run()                                          | stub-import w/ fallback |
| TokenRouter   | `src/clients/tokenrouter.py` — every LLM call routes through it             | mock until key set     |
| Qwen Cloud    | Scout, Hardball (Qwen3-Max), Referee                                        | mock until key set     |
| Z.ai          | Diplomat (GLM-5.1)                                                          | mock until key set     |
| Evermind      | `src/memory/evermind.py` — scout cache, decisions; JSON file fallback        | local fallback         |
| Nosana        | `src/agents/contract_diff.py:_nosana_embed`                                 | mock until endpoint set |
| Bright Data   | `scout.run(bright_data_input=...)` parameter, `fixtures/observability_vendors_g2.json` | fixture; Person B replaces |
| Actionbook    | `src/agents/quote_hunter.py` reads `fixtures/<vendor>_ae_response.json`     | fixture; Person B drops in |
| Zeabur        | `Dockerfile`, `zeabur.toml`                                                 | config ready           |
| Qoder         | mentioned in pitch (process sponsor)                                        | n/a                    |
| Butterbase    | Person C consumes `/api/demo-state` + `/api/email-draft`                    | external               |

## Person B handoff — what to drop into `fixtures/`

The pipeline reads these files when present. Drop in real captures, no code change needed.

```
fixtures/
├── observability_vendors_g2.json     ← Bright Data scrape, shape: {vendors: [{name, g2_rating, ...}]}
├── datadog_ae_response.json          ← Actionbook capture, shape:
│                                        {vendor, ae_email, ae_name, first_quote, discount_offered,
│                                         competitor_dig, quarter_end_iso, hosts_quoted}
├── new_relic_ae_response.json        ← same shape, second vendor (currently inline-mocked)
├── standard_msa.json                 ← our standard MSA clauses (already populated)
└── vendor_msa_datadog.json           ← captured Datadog MSA (currently mocked, replace if you get one)
```

If `NOSANA_ENDPOINT` env var is set, `contract_diff` POSTs `{texts: [...]}` to `${endpoint}/embed` and expects `{embeddings: [[...], ...]}` back. Falls back to deterministic Jaccard+length similarity if endpoint absent/errors.

## Person C handoff — frontend contract

Render two things:
1. **Live negotiation column view** — consume `/run/stream`, render hardball + diplomat turns side-by-side as they arrive. Verdict card at the end. The built-in HTML dashboard at `/` shows the target aesthetic.
2. **Vendor snapshot view** — `GET /api/demo-state` returns the cached full snapshot. `summary` field has every number you need for the headline:
   - `summary.final_price_per_host_mo` (final)
   - `summary.annual_savings_vs_list_usd` (the CFO number)
   - `summary.discount_vs_list_pct`
   - `summary.contract_redline_count`, `summary.contract_high_severity`
   - `summary.winning_strategy` ∈ {hardball, diplomat}
3. **Email card** — `GET /api/email-draft` returns `{ok, email: {to, from, subject, body, strategy, cites, dry_run}}`. Render after the verdict.

## Mock-fallback contract

Every external dependency degrades to a deterministic mock so the demo cannot crash:
- TokenRouter → tagged stub completions, no API call
- Qwen / Z.ai → routed through TokenRouter, mock-passthrough
- Evermind → `.evermind-fallback.json` (gitignored)
- Nosana → Jaccard + length similarity heuristic
- Bright Data → `fixtures/observability_vendors_g2.json`
- Actionbook → `fixtures/<vendor>_ae_response.json` or inline fallback

Flipping any service to live = drop one env var. See `.env.example`.

## Deploy

```bash
# one-time
zeabur auth login

# from this directory
zeabur deploy
```

The `Dockerfile` exposes port 8000, runs `uvicorn src.app:app`. `zeabur.toml` sets a `/healthz` healthcheck and declares the env-var slots.
