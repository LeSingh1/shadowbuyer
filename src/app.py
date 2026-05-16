"""
ShadowBuyer FastAPI app.

- GET  /healthz            liveness + mock/live status
- POST /run                sync full pipeline, returns JSON snapshot
- GET  /run/stream         SSE stream (turns appear paced for the live demo)
- GET  /api/demo-state     cached full snapshot for the frontend
- GET  /                   minimal HTML dashboard, two columns + verdict
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Any

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from . import pipeline

app = FastAPI(title="ShadowBuyer", version="0.2.0")

_state_lock = threading.Lock()
_demo_state: dict[str, Any] = {"ok": False, "generated_at": None, "snapshot": None}


def _refresh_demo_state(category: str = "observability") -> dict[str, Any]:
    snapshot = pipeline.run(category=category)
    with _state_lock:
        _demo_state["ok"] = True
        _demo_state["generated_at"] = time.time()
        _demo_state["category"] = category
        _demo_state["snapshot"] = snapshot
    return snapshot


@app.on_event("startup")
def _warm_demo_state() -> None:
    _refresh_demo_state()


def _service_mode() -> dict[str, bool]:
    return {
        "tokenrouter_live": bool(os.getenv("TOKENROUTER_API_KEY")),
        "qwen_live": bool(os.getenv("QWEN_API_KEY")),
        "zai_live": bool(os.getenv("ZAI_API_KEY")),
        "evermind_live": bool(os.getenv("EVERMIND_API_KEY")),
        "nosana_live": bool(os.getenv("NOSANA_ENDPOINT")),
        "brightdata_live": bool(os.getenv("BRIGHTDATA_API_KEY")),
    }


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "service": "shadowbuyer", "version": app.version, "services": _service_mode()}


@app.post("/run")
def run(category: str = "observability", include_contract_diff: bool = False) -> dict[str, Any]:
    snapshot = pipeline.run(category=category, include_contract_diff=include_contract_diff)
    with _state_lock:
        _demo_state["ok"] = True
        _demo_state["generated_at"] = time.time()
        _demo_state["category"] = category
        _demo_state["snapshot"] = snapshot
    return snapshot


@app.get("/run/stream")
def run_stream(
    category: str = "observability",
    pace: bool = Query(True, description="set false to dump events with no delays"),
) -> StreamingResponse:
    def gen():
        last_summary: dict[str, Any] | None = None
        for event in pipeline.stream(category=category, pace=pace):
            if event.get("event") == "summary":
                last_summary = event.get("payload")
            yield f"data: {json.dumps(event, default=str)}\n\n"
        if last_summary:
            with _state_lock:
                _demo_state["ok"] = True
                _demo_state["generated_at"] = time.time()
                _demo_state["category"] = category
                # cheap refresh — full pipeline is already replayed via state warmer if needed
                _demo_state["snapshot"] = {"summary": last_summary} | (_demo_state.get("snapshot") or {})
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/demo-state")
def demo_state(refresh: bool = False) -> JSONResponse:
    if refresh or not _demo_state.get("ok"):
        _refresh_demo_state()
    with _state_lock:
        return JSONResponse(_demo_state)


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return _DASHBOARD_HTML


_DASHBOARD_HTML = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8" />
<title>ShadowBuyer — live negotiation</title>
<style>
  :root {
    --bg:#0a0c10; --panel:#11151c; --line:#1f2530;
    --ink:#e6e8ec; --muted:#7c8392;
    --hb:#ff5d6c; --dp:#3ee0a1; --rf:#ffc83d; --acc:#7aa2ff;
    --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 var(--mono);min-height:100vh}
  header{padding:18px 28px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap}
  header .brand{display:flex;align-items:center;gap:12px}
  header h1{margin:0;font-size:13px;letter-spacing:.22em;text-transform:uppercase;color:var(--acc)}
  header .tag{font-size:11px;color:var(--muted);letter-spacing:.18em;text-transform:uppercase}
  header .dot{width:8px;height:8px;border-radius:50%;background:var(--muted);box-shadow:0 0 0 0 rgba(122,162,255,.6);transition:background .25s}
  header .dot.live{background:var(--dp);animation:pulse 1.6s infinite}
  @keyframes pulse{0%{box-shadow:0 0 0 0 rgba(62,224,161,.55)}70%{box-shadow:0 0 0 10px rgba(62,224,161,0)}100%{box-shadow:0 0 0 0 rgba(62,224,161,0)}}
  header button{background:var(--acc);color:#0a0c10;border:0;padding:9px 18px;font:600 13px/1 var(--mono);letter-spacing:.05em;cursor:pointer;border-radius:2px}
  header button:disabled{opacity:.5;cursor:not-allowed}

  .meta{padding:14px 28px;border-bottom:1px solid var(--line);display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:16px}
  .meta .cell{display:flex;flex-direction:column;gap:4px}
  .meta .k{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
  .meta .v{font-size:15px;color:var(--ink)}
  .meta .v.big{font-size:22px;color:var(--rf)}

  .pipeline{padding:14px 28px;border-bottom:1px solid var(--line);display:flex;gap:8px;flex-wrap:wrap;align-items:center;font-size:12px;color:var(--muted)}
  .pipeline .step{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border:1px solid var(--line);border-radius:99px}
  .pipeline .step.active{color:var(--acc);border-color:var(--acc)}
  .pipeline .step.done{color:var(--dp);border-color:var(--dp)}
  .pipeline .arrow{color:var(--line)}

  main{display:grid;grid-template-columns:1fr 1fr;gap:18px;padding:24px 28px}
  .col{display:flex;flex-direction:column;gap:14px;min-height:200px}
  .col h2{margin:0;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--muted);padding-bottom:8px;border-bottom:1px dashed var(--line)}
  .col.hardball h2{color:var(--hb)}
  .col.diplomat h2{color:var(--dp)}

  .turn{background:var(--panel);border-left:3px solid var(--line);padding:14px 16px;border-radius:2px;opacity:0;transform:translateY(6px);animation:in .35s ease-out forwards}
  .turn.hardball{border-left-color:var(--hb)}
  .turn.diplomat{border-left-color:var(--dp)}
  @keyframes in{to{opacity:1;transform:translateY(0)}}
  .turn .head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:8px}
  .turn .round{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}
  .turn .price{font-size:13px;color:var(--rf)}
  .turn .headline{font-size:13px;font-weight:600;margin-bottom:6px}
  .turn .body{color:var(--ink);font-size:13px;line-height:1.55}
  .turn .cites{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
  .turn .cite{font-size:10px;padding:2px 8px;background:rgba(255,255,255,.04);color:var(--muted);border-radius:99px;letter-spacing:.04em}

  .verdict{margin:0 28px 28px;background:linear-gradient(180deg,rgba(255,200,61,.08),rgba(255,200,61,0));border:1px solid rgba(255,200,61,.35);padding:22px 24px;border-radius:4px;opacity:0;transform:translateY(8px);animation:in .45s ease-out forwards}
  .verdict h2{margin:0 0 4px;font-size:11px;letter-spacing:.22em;text-transform:uppercase;color:var(--rf)}
  .verdict .headline{font-size:18px;margin:8px 0 12px}
  .verdict .body{color:var(--ink);font-size:14px;line-height:1.6;max-width:880px}
  .verdict .savings{margin-top:18px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px}
  .verdict .savings .k{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted)}
  .verdict .savings .v{font-size:18px;color:var(--rf)}

  footer{padding:18px 28px;border-top:1px solid var(--line);color:var(--muted);font-size:11px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px}
  footer a{color:var(--acc);text-decoration:none}
  .mock-flag{color:var(--muted);font-size:10px;margin-left:6px}
  @media (max-width:820px){main{grid-template-columns:1fr}.meta{grid-template-columns:repeat(2,1fr)}.verdict .savings{grid-template-columns:repeat(2,1fr)}}
</style>
</head>
<body>
<header>
  <div class="brand">
    <span class="dot" id="dot"></span>
    <h1>ShadowBuyer · live negotiation</h1>
    <span class="tag" id="modetag">mock fallback</span>
  </div>
  <button id="go">Run negotiation →</button>
</header>

<section class="meta">
  <div class="cell"><span class="k">Vendor</span><span class="v" id="m-vendor">—</span></div>
  <div class="cell"><span class="k">Competing</span><span class="v" id="m-comp">—</span></div>
  <div class="cell"><span class="k">Hosts</span><span class="v" id="m-hosts">—</span></div>
  <div class="cell"><span class="k">List $/host/mo</span><span class="v" id="m-list">—</span></div>
  <div class="cell"><span class="k">Live target $/host/mo</span><span class="v big" id="m-price">—</span></div>
</section>

<section class="pipeline" id="pipeline">
  <span class="step" data-stage="scout">scout</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="quote_hunter">quote hunter</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="negotiator">negotiator</span>
  <span class="arrow">→</span>
  <span class="step" data-stage="referee">referee</span>
</section>

<main>
  <div class="col hardball"><h2>HARDBALL · Qwen3-Max via TokenRouter</h2><div id="hb"></div></div>
  <div class="col diplomat"><h2>DIPLOMAT · GLM-5.1 via Z.ai</h2><div id="dp"></div></div>
</main>

<section class="verdict" id="verdict" style="display:none">
  <h2>Referee verdict</h2>
  <div class="headline" id="v-headline"></div>
  <div class="body" id="v-body"></div>
  <div class="savings">
    <div><div class="k">Final $/host/mo</div><div class="v" id="v-final">—</div></div>
    <div><div class="k">Discount vs list</div><div class="v" id="v-disc">—</div></div>
    <div><div class="k">Annual savings</div><div class="v" id="v-save">—</div></div>
    <div><div class="k">Strategy</div><div class="v" id="v-strat">—</div></div>
  </div>
</section>

<footer>
  <div>shadowbuyer · adversarial procurement · <a href="/api/demo-state" target="_blank">/api/demo-state</a> · <a href="/healthz" target="_blank">/healthz</a></div>
  <div><a href="https://github.com/LeSingh1/shadowbuyer" target="_blank">source</a></div>
</footer>

<script>
const $ = id => document.getElementById(id);
const dot = $('dot'), go = $('go'), modetag = $('modetag');
const hbCol = $('hb'), dpCol = $('dp'), verdict = $('verdict');

function setStep(stage, state){
  document.querySelectorAll('.pipeline .step').forEach(s=>{
    if(s.dataset.stage===stage){ s.classList.remove('active','done'); s.classList.add(state); }
  });
}
function resetUI(){
  hbCol.innerHTML=''; dpCol.innerHTML=''; verdict.style.display='none';
  ['m-vendor','m-comp','m-hosts','m-list','m-price'].forEach(i=>$(i).textContent='—');
  document.querySelectorAll('.pipeline .step').forEach(s=>{s.classList.remove('active','done')});
}
function renderTurn(t){
  const col = t.role === 'hardball' ? hbCol : dpCol;
  const div = document.createElement('div');
  div.className = `turn ${t.role}`;
  const price = t.price_target_per_host_mo != null ? `$${Number(t.price_target_per_host_mo).toFixed(2)}/host` : '';
  const term  = t.deal_term_months ? ` · ${t.deal_term_months}mo` : '';
  const mock  = t.mocked ? '<span class="mock-flag">(mock)</span>' : '';
  div.innerHTML = `
    <div class="head"><span class="round">Round ${t.round}${mock}</span><span class="price">${price}${term}</span></div>
    <div class="headline">${t.headline||''}</div>
    <div class="body">${t.text}</div>
    <div class="cites">${(t.cites||[]).map(c=>`<span class="cite">${c}</span>`).join('')}</div>`;
  col.appendChild(div);
  if(t.price_target_per_host_mo != null){ $('m-price').textContent = `$${Number(t.price_target_per_host_mo).toFixed(2)}`; }
}
function renderVerdict(t, summary){
  $('v-headline').textContent = t.headline || '';
  $('v-body').textContent = t.text || '';
  if(summary){
    $('v-final').textContent = `$${Number(summary.final_price_per_host_mo).toFixed(2)}`;
    $('v-disc').textContent  = `${summary.discount_vs_list_pct}%`;
    $('v-save').textContent  = `$${Number(summary.annual_savings_vs_list_usd).toLocaleString()}`;
    $('v-strat').textContent = summary.winning_strategy || '—';
  }
  verdict.style.display='block';
}

go.onclick = () => {
  resetUI(); go.disabled=true; dot.classList.add('live');
  const es = new EventSource('/run/stream?category=observability');
  let lastSummary = null;
  es.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if(ev.event === 'stage_start'){
      setStep(ev.stage,'active');
      if(ev.stage === 'negotiator'){
        $('m-vendor').textContent = ev.target_vendor;
        $('m-comp').textContent = ev.competing_vendor;
        $('m-hosts').textContent = ev.hosts;
        $('m-list').textContent = `$${ev.list_price_per_host_mo}`;
        $('m-price').textContent = `$${Number(ev.starting_quote_per_host_mo).toFixed(2)}`;
      }
    } else if(ev.event === 'stage_done'){
      setStep(ev.stage,'done');
    } else if(ev.event === 'negotiator_turn'){
      const t = ev.turn;
      if(t.role === 'referee'){ setStep('referee','active'); renderVerdict(t, lastSummary); setStep('referee','done'); }
      else { renderTurn(t); }
    } else if(ev.event === 'summary'){
      lastSummary = ev.payload;
      // verdict may have rendered before summary arrived; patch numbers in.
      if(lastSummary){
        $('v-final').textContent = `$${Number(lastSummary.final_price_per_host_mo).toFixed(2)}`;
        $('v-disc').textContent  = `${lastSummary.discount_vs_list_pct}%`;
        $('v-save').textContent  = `$${Number(lastSummary.annual_savings_vs_list_usd).toLocaleString()}`;
        $('v-strat').textContent = lastSummary.winning_strategy || '—';
      }
    } else if(ev.event === 'done'){ es.close(); go.disabled=false; dot.classList.remove('live'); }
  };
  es.onerror = () => { es.close(); go.disabled=false; dot.classList.remove('live'); };
};

fetch('/healthz').then(r=>r.json()).then(h=>{
  const anyLive = Object.values(h.services||{}).some(Boolean);
  modetag.textContent = anyLive ? 'mixed: some sponsors live' : 'mock fallback';
}).catch(()=>{});
</script>
</body></html>"""
