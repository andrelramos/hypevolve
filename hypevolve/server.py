"""FastAPI service and the self-contained execution timeline panel."""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .runtime import config_from_options, run_experiment
from .store import ExecutionStore


class StartRun(BaseModel):
    target: str
    test_cmd: str
    bench_cmd: str
    generations: int = Field(ge=0)
    max_hypotheses: int = Field(ge=1)
    harness: Literal["codex", "claude"]
    initial_prompt: str = ""
    model: str | None = None
    population_size: int = Field(default=4, ge=1)
    name: str | None = None


class HypothesisInput(BaseModel):
    text: str = Field(min_length=1)


def create_app(results_root: str | Path = "results") -> FastAPI:
    store = ExecutionStore(results_root)
    app = FastAPI(title="HypEvolve", version="0.2.0")
    app.state.store = store
    app.state.locks = set()

    def missing(exc: KeyError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/sessions")
    def list_sessions(): return store.list_sessions()

    @app.get("/api/sessions/{session_id}")
    def get_session(session_id: str):
        try: return store.session(session_id)
        except KeyError as exc: missing(exc)

    @app.get("/api/sessions/{session_id}/generations")
    def get_generations(session_id: str):
        try: return store.generations(session_id)
        except KeyError as exc: missing(exc)

    @app.get("/api/sessions/{session_id}/individuals/{individual_id}")
    def get_individual(session_id: str, individual_id: int):
        try: return store.individual(session_id, individual_id)
        except KeyError as exc: missing(exc)

    @app.get("/api/sessions/{session_id}/hypotheses")
    def list_hypotheses(session_id: str):
        try: return store.hypotheses(session_id)
        except KeyError as exc: missing(exc)

    @app.post("/api/sessions/{session_id}/hypotheses", status_code=201)
    def add_hypothesis(session_id: str, body: HypothesisInput):
        try: return store.add_hypothesis(session_id, body.text)
        except KeyError as exc: missing(exc)

    @app.patch("/api/sessions/{session_id}/hypotheses/{hypothesis_id}")
    def edit_hypothesis(session_id: str, hypothesis_id: str, body: HypothesisInput):
        try: return store.update_hypothesis(session_id, hypothesis_id, body.text)
        except KeyError as exc: missing(exc)

    @app.delete("/api/sessions/{session_id}/hypotheses/{hypothesis_id}", status_code=204)
    def delete_hypothesis(session_id: str, hypothesis_id: str):
        try: store.delete_hypothesis(session_id, hypothesis_id)
        except KeyError as exc: missing(exc)

    @app.post("/api/sessions", status_code=202)
    def start_run(body: StartRun, background: BackgroundTasks):
        session_id = body.name or datetime.now(UTC).strftime("run-%Y%m%dT%H%M%SZ")
        if session_id in app.state.locks:
            raise HTTPException(status_code=409, detail="execution already running")
        cfg = config_from_options(name=session_id, source_path=body.target, test_cmd=body.test_cmd,
            bench_cmd=body.bench_cmd, harness=body.harness, model=body.model,
            generations=body.generations, max_hypotheses=body.max_hypotheses,
            initial_prompt=body.initial_prompt, population_size=body.population_size)
        try:
            store.create_session(session_id, {"name": session_id, "source_path": cfg.source_path,
                "config": body.model_dump()})
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail="session id already exists") from exc
        def run() -> None:
            app.state.locks.add(session_id)
            try: run_experiment(cfg, store.root / session_id, store)
            finally: app.state.locks.discard(session_id)
        background.add_task(run)
        return {"id": session_id, "status": "queued"}

    @app.get("/", response_class=HTMLResponse)
    def dashboard(): return HTMLResponse(_PANEL)
    return app


_PANEL = r'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>HypEvolve</title>
<style>
:root{color-scheme:dark;--bg:#10131a;--card:#171c27;--line:#354055;--ink:#e9edff;--muted:#9aa6c3;--ok:#51d39a;--bad:#ff7979;--accent:#7c9cff}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px ui-sans-serif,system-ui}header{padding:20px 28px;border-bottom:1px solid var(--line);display:flex;gap:14px;align-items:center}h1{font-size:20px;margin:0}select,button,input,textarea{background:#222a3a;color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:8px}main{padding:24px;max-width:1400px;margin:auto}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin-bottom:18px}.timeline{overflow-x:auto;padding:36px 12px 12px}.track{position:relative;display:flex;align-items:center;gap:72px;min-width:max-content}.track:before{content:"";position:absolute;left:0;right:0;height:3px;background:var(--line);top:20px}.generation{position:relative;text-align:center;color:var(--muted)}.dots{display:flex;gap:10px;margin-top:10px}.dot{z-index:1;width:18px;height:18px;border-radius:50%;background:var(--accent);padding:0;border:3px solid var(--card);cursor:pointer}.dot.fail{background:var(--bad)}.dot:hover{transform:scale(1.3)}.detail{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}pre{white-space:pre-wrap;max-height:280px;overflow:auto;background:#0c0f15;padding:12px;border-radius:7px}table{width:100%;border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid var(--line);text-align:left}.muted{color:var(--muted)}.ok{color:var(--ok)}.bad{color:var(--bad)}form{display:flex;gap:8px;align-items:center}form input{flex:1}@media(max-width:700px){.detail{grid-template-columns:1fr}header{padding:14px}main{padding:14px}}
</style><header><h1>HypEvolve</h1><span class="muted">Observatório de evolução de código</span><select id="sessions"></select></header><main><section class="card"><b id="title">Carregando sessões…</b><div class="muted" id="meta"></div><div class="timeline"><div class="track" id="timeline"></div></div></section><section class="card detail" id="detail"><span class="muted">Clique em uma bolinha para abrir o indivíduo.</span></section><section class="card"><h2>Hipóteses</h2><form id="add"><input name="text" placeholder="Nova hipótese para a próxima geração" required><button>Adicionar</button></form><table><thead><tr><th>ID</th><th>Hipótese</th><th>Status</th><th></th></tr></thead><tbody id="hypotheses"></tbody></table></section></main>
<script>
let current;const $=s=>document.querySelector(s);async function api(p,o){let r=await fetch('/api/'+p,o);if(!r.ok)throw Error(await r.text());return r.status===204?null:r.json()}function esc(x){return String(x??'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}async function load(id){current=id;let [s,gs,hs]=await Promise.all([api('sessions/'+id),api('sessions/'+id+'/generations'),api('sessions/'+id+'/hypotheses')]);$('#title').textContent=s.name||id;$('#meta').textContent=`${s.status||'unknown'} · ${s.source_path||''} · ${gs.length} gerações`;$('#timeline').innerHTML=gs.map(g=>`<div class=generation><b>Geração ${g.generation}</b><div class=dots>${g.individuals.map(i=>`<button class="dot ${i.passed?'':'fail'}" title="Indivíduo ${i.individual_id}" onclick="detail(${i.individual_id})"></button>`).join('')}</div><small>${g.individuals.length} hipóteses</small></div>`).join('');$('#hypotheses').innerHTML=hs.map(h=>`<tr><td>${esc(h.id)}</td><td>${esc(h.text)}</td><td>${esc(h.status)}</td><td><button onclick="editHyp('${h.id}','${encodeURIComponent(h.text)}')">Editar</button> <button onclick="delHyp('${h.id}')">Remover</button></td></tr>`).join('')}
async function detail(i){let x=await api(`sessions/${current}/individuals/${i}`);$('#detail').innerHTML=`<div><h2>Indivíduo ${i} · geração ${x.generation}</h2><p><b>Hipótese:</b> ${esc(x.hypothesis)||'não declarada'}</p><p>Teste determinístico: <span class="${x.passed?'ok':'bad'}">${x.passed?'aprovado':'reprovado'} (exit ${x.test_returncode??'—'})</span></p><p>Fitness: ${x.fitness} · ${x.speedup_vs_base}x vs base</p><h3>Prompt usado</h3><pre>${esc(x.agent_prompt)}</pre></div><div><h2>Saída da sessão</h2><pre>${esc(x.agent_stdout||x.agent_error)}</pre><h3>stdout do teste</h3><pre>${esc(x.test_stdout)}${x.test_stderr?'\n[stderr]\n'+esc(x.test_stderr):''}</pre></div>`}async function editHyp(id,text){let v=prompt('Hipótese',decodeURIComponent(text));if(v)await api(`sessions/${current}/hypotheses/${id}`,{method:'PATCH',headers:{'content-type':'application/json'},body:JSON.stringify({text:v})}),load(current)}async function delHyp(id){if(confirm('Remover hipótese?'))await api(`sessions/${current}/hypotheses/${id}`,{method:'DELETE'}),load(current)}$('#add').onsubmit=async e=>{e.preventDefault();let text=new FormData(e.target).get('text');await api(`sessions/${current}/hypotheses`,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({text})});e.target.reset();load(current)};async function init(){let ss=await api('sessions');let sel=$('#sessions');sel.innerHTML=ss.map(s=>`<option value="${esc(s.id)}">${esc(s.name||s.id)} · ${esc(s.status||'')}</option>`).join('');sel.onchange=()=>load(sel.value);if(ss.length)load(sel.value);else $('#title').textContent='Nenhuma execução ainda. Use o CLI ou POST /api/sessions.'}init();setInterval(()=>current&&load(current),5000);
</script></html>'''
