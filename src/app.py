"""
ShadowBuyer FastAPI app. Endpoints:
- GET  /healthz       -> liveness
- POST /run           -> sync full pipeline, returns JSON
- GET  /run/stream    -> SSE stream (negotiator turns appear live)
- GET  /              -> minimal HTML dashboard
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from . import pipeline

app = FastAPI(title="ShadowBuyer", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "service": "shadowbuyer", "mode": "mock"}


@app.post("/run")
def run(category: str = "observability", include_contract_diff: bool = False) -> dict[str, Any]:
    return pipeline.run(category=category, include_contract_diff=include_contract_diff)


@app.get("/run/stream")
def run_stream(category: str = "observability") -> StreamingResponse:
    def gen():
        for event in pipeline.stream(category=category):
            yield f"data: {json.dumps(event, default=str)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html>
<html><head><title>ShadowBuyer — live</title>
<style>
  body { font: 14px ui-monospace, monospace; background:#0b0d10; color:#e6e6e6; padding:24px; max-width:900px; margin:auto; }
  h1 { font-size: 18px; letter-spacing: 0.12em; text-transform: uppercase; color:#9af; }
  button { background:#9af; color:#0b0d10; border:0; padding:8px 14px; font-weight:600; cursor:pointer; }
  .turn { margin: 12px 0; padding: 12px; border-left: 3px solid #444; }
  .hardball { border-color:#f55; }
  .diplomat { border-color:#5f7; }
  .referee  { border-color:#fc3; }
  .role { font-weight:700; text-transform:uppercase; letter-spacing:0.1em; margin-bottom:6px; }
  .cites { color:#888; font-size:12px; margin-top:6px; }
  .stage { color:#9af; margin-top:14px; }
  pre { background:#16191e; padding:10px; overflow:auto; }
</style></head>
<body>
<h1>ShadowBuyer / live negotiation</h1>
<button id="go">Run pipeline →</button>
<div id="out"></div>
<script>
document.getElementById('go').onclick = () => {
  const out = document.getElementById('out'); out.innerHTML = '';
  const es = new EventSource('/run/stream?category=observability');
  es.onmessage = (e) => {
    const ev = JSON.parse(e.data);
    if (ev.event === 'stage_start') {
      out.innerHTML += `<div class="stage">▸ ${ev.stage}</div>`;
    } else if (ev.event === 'stage_done' && ev.payload) {
      out.innerHTML += `<details><summary>${ev.stage} payload</summary><pre>${JSON.stringify(ev.payload, null, 2)}</pre></details>`;
    } else if (ev.event === 'negotiator_turn') {
      const t = ev.turn;
      out.innerHTML += `<div class="turn ${t.role}"><div class="role">${t.role}${t.mocked?' (mock)':''}</div>${t.text}<div class="cites">${(t.cites||[]).join(' · ')}</div></div>`;
    } else if (ev.event === 'done') { es.close(); }
  };
  es.onerror = () => es.close();
};
</script></body></html>"""
