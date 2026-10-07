#!/usr/bin/env python3
"""Investigation dashboard — view everything intelligence-forensics collected.

Run with the repo venv (has fastapi/uvicorn):
    /home/fox/codebase/.venv/bin/python dashboard.py [--port 8211]
or:
    IF_PORT=8211 /home/fox/codebase/.venv/bin/python -m uvicorn dashboard:app --host 0.0.0.0 --port 8211
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from iforensics import config, store, infer, agents as ag, ollama_client

app = FastAPI(title="Intelligence Forensics Dashboard", version="0.2.0")
app.mount("/static", StaticFiles(directory=os.path.join(config.BASE_DIR, "static")), name="static")

# Bump on every deploy — shown in the header so cached pages are detectable.
APP_VERSION = "0.5.0-live"

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Intelligence Forensics</title>
<style>
:root{--bg:#0d1117;--fg:#e6edf3;--mut:#8b949e;--acc:#58a6ff;--card:#161b22;--line:#30363d;--ok:#3fb950;--warn:#d29922}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,sans-serif;margin:0}
header{padding:14px 20px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:17px;margin:0}header .sub{color:var(--mut);font-size:12px}
nav{display:flex;gap:6px;padding:10px 20px;border-bottom:1px solid var(--line);flex-wrap:wrap}
nav button{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px 12px;cursor:pointer}
nav button.on{border-color:var(--acc);color:var(--acc)}
main{padding:16px 20px;max-width:1200px}section{display:none}section.on{display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.stat .v{font-size:22px;font-weight:700}.stat .k{color:var(--mut);font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600}code{background:#00000040;padding:1px 5px;border-radius:4px;font-size:12px}
pre{white-space:pre-wrap;background:#00000040;padding:10px;border-radius:6px;max-height:420px;overflow:auto;font-size:12px}
.mut{color:var(--mut)}.ok{color:var(--ok)}.warn{color:var(--warn)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}input,select{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:6px 10px}
button.act{background:#1f6feb;color:#fff;border:0;border-radius:6px;padding:7px 14px;cursor:pointer}button.act:disabled{opacity:.5}
a{color:var(--acc)}
#design-doc h2{font-size:19px;margin:14px 0 8px;border-bottom:1px solid var(--line);padding-bottom:6px}
#design-doc h3{font-size:16px;margin:12px 0 6px}
#design-doc h4{font-size:14px;margin:10px 0 4px}
#design-doc p{margin:6px 0}
#design-doc ul,#design-doc ol{margin:6px 0;padding-left:22px}
#design-doc li{margin:2px 0}
#design-doc blockquote{border-left:3px solid var(--acc);margin:8px 0;padding:4px 10px;color:var(--mut)}
#design-doc hr{border:0;border-top:1px solid var(--line);margin:12px 0}
#design-doc table{margin:8px 0}
.diagram-wrap{background:#0a0e14;border:1px solid var(--line);border-radius:8px;padding:10px;margin:10px 0;overflow-x:auto}
.diagram-wrap pre.mermaid{background:none;padding:0;margin:0;max-height:none;border:0}
.code-wrap{background:#00000040;border:1px solid var(--line);border-radius:8px;margin:10px 0}
.code-lang{font-size:11px;color:var(--mut);padding:4px 10px;border-bottom:1px solid var(--line)}
#design-rail a.on{font-weight:700}
</style></head><body>
<header><h1>&#x1f575; Intelligence Forensics</h1><span class=sub id=hdr>loading&hellip;</span></header>
<nav id=tabs>
<button data-t=overview class=on>Overview</button><button data-t=live>Live tap</button><button data-t=services>Services</button><button data-t=recon>Reconstructions</button><button data-t=agents>Agentic runs</button><button data-t=mesh>Mesh</button><button data-t=evidence>Evidence</button><button data-t=design>Design</button>
</nav><main>
<section id=s-overview class=on><div class=grid id=stats></div><div class=card><h3>Latest brief</h3><pre id=brief>loading&hellip;</pre></div>
<div class=card><h3>Run investigation</h3><div class=row>
<button class=act id=b-inv>Re-run heuristic investigation</button>
<button class=act id=b-agent>Launch agentic run (Qwen 3.8-27B)</button>
<label class=mut><input type=checkbox id=opt-quick checked> quick (top-3, no critic)</label>
<span class=mut id=runmsg></span></div></div></section>
<section id=s-services><div class=card><table id=t-svc><thead><tr><th>service</th><th>reqs</th><th>tokens</th><th>models</th><th>inferred build</th><th>score / vibe</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-live><div class=card><h3>Tap <span class=mut id=live-state style="font-weight:normal"></span></h3>
<div class=row><button class=act id=b-live-start>Start tap</button><button class=act id=b-live-stop>Stop</button>
<label class=mut>every <input id=inp-live-int type=number value=5 min=1 max=60 style="width:56px">s</label>
<span class=mut>API-level sniff of fox :8210 — queue IN, completed OUT, model load SYS. Raw pcap needs the <code>pcap</code> compose profile (see README).</span></div></div>
<div class=card><h3>Rates <span class=mut style="font-weight:normal">— live window</span></h3><table id=t-rates><thead><tr><th>service</th><th>req</th><th>tokens</th><th>req/min</th><th>tok/min</th></tr></thead><tbody><tr><td class=mut colspan=5>tap not running</td></tr></tbody></table></div>
<div class=card><h3>Live reconstruction <span class=mut style="font-weight:normal">— recent history + live rows since tap started</span></h3>
<div class=row><select id=sel-live></select><select id=sel-lmode><option value=cumulative>cumulative</option><option value=window>window</option></select>
<button class=act id=b-live-recon>Reconstruct live</button><span class=mut id=live-recon-msg></span></div>
<table id=t-liveprog><thead><tr><th>step</th><th>score</th><th>queries</th><th>inferred build</th><th>Δ vs prev</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Feed <span class=mut style="font-weight:normal">— newest first, auto-refresh</span></h3><table id=t-feed><thead><tr><th>time</th><th>dir</th><th>service</th><th>model</th><th>detail</th></tr></thead><tbody><tr><td class=mut colspan=5>tap not running</td></tr></tbody></table></div></section>
<section id=s-recon><div class=card><div class=row><select id=sel-recon></select><select id=sel-file></select></div><pre id=recon-view>pick a reconstruction&hellip;</pre></div>
<div class=card><h3>Partial &amp; progressive reconstruction <span class=mut style="font-weight:normal">— same service, re-profiled as Fox queries accumulate</span></h3>
<div class=row><select id=sel-pmode><option value=cumulative>cumulative (0..k — confidence growth)</option><option value=window>window (slice k alone — partial views)</option></select>
<label class=mut>steps <input id=inp-pn type=number value=5 min=2 max=12 style="width:56px"></label>
<button class=act id=b-prog>Build progression</button><span class=mut id=prog-msg></span></div>
<table id=t-prog><thead><tr><th>step</th><th>score</th><th>queries seen</th><th>window</th><th>inferred build</th><th>pipeline</th><th>Δ vs prev</th></tr></thead><tbody><tr><td class=mut colspan=7>pick a service, then Build progression</td></tr></tbody></table></div>
<div class=card><h3>Score curve <span class=mut style="font-weight:normal">— bars = queries seen, line = reconstruction score, ◆ = label flip</span></h3><div id=prog-chart class=mut>build a progression to chart it</div></div>
<div class=card><h3>Step detail</h3><pre id=prog-detail>click a step row&hellip;</pre></div></section>
<section id=s-agents><div class=card><table id=t-runs><thead><tr><th>run</th><th>model</th><th>services</th><th>elapsed</th><th>errors</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Reconstruction graph <span class=mut id=rg-title style="font-weight:normal"></span></h3>
<div id=run-dag class=mut>click a run above&hellip;</div>
<h3>Agent cost <span class=mut style="font-weight:normal">— tokens + wall time per agent (local model: $0.00)</span></h3><div id=run-cost></div>
<h3>Confidence &amp; agreement <span class=mut style="font-weight:normal">— LLM profiler vs heuristic rules</span></h3><table id=t-conf><thead><tr><th>service</th><th>confidence</th><th>heuristic says</th><th>LLM says</th><th>agree</th></tr></thead><tbody></tbody></table>
<h3>Critic gaps</h3><div id=run-gaps></div>
<h3>Evidence quotes <span class=mut style="font-weight:normal">— prompt lines the profiler cited</span></h3><div id=run-quotes></div></div>
<div class=card><h3>Across runs <span class=mut style="font-weight:normal">— profiler confidence per service, newest first</span></h3><table id=t-trend><thead><tr><th>service</th><th>trend</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Brief</h3><pre id=run-brief>click a run&hellip;</pre></div></section>
<section id=s-mesh><div class=card><table id=t-mesh><thead><tr><th>node</th><th>online</th><th>hw</th><th>llm/1h</th><th>services</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-evidence><div class=card><table id=t-ev><thead><tr><th>file</th><th>size</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-design><div class=row><div class=card style="min-width:230px"><h3>Documents</h3><div id=design-rail class=mut>loading&hellip;</div></div>
<div class=card style="flex:1"><h3 id=design-title>Design &amp; architecture</h3><div class=mut id=design-meta></div><div id=design-doc class=mut>pick a document&hellip;</div></div></div></section>
</main>
<script>
const $=id=>document.getElementById(id);
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('#tabs button').forEach(x=>x.classList.remove('on'));b.classList.add('on');document.querySelectorAll('main section').forEach(s=>s.classList.remove('on'));$('s-'+b.dataset.t).classList.add('on');});
const j=async u=>{const r=await fetch(u);return r.json()};
const gcls=g=>(g==='A'||g==='B')?'ok':'warn';
const scoreCell=(v,g)=>`<b class=${gcls(g)}>${v}</b> <span class=mut>${g}</span>`;
async function load(){
 const sec=async(id,fn)=>{try{await fn();}catch(e){const el=document.querySelector(id);if(el)el.innerHTML=`<tr><td class=warn>failed: ${e}</td></tr>`;}};
 try{
  const o=await j('/api/overview');
  $('hdr').textContent=`v${o.version||'?'} · fox:${o.fox} model:${o.model} reqs:${o.requests} svcs:${o.services} recon:${o.reconstructions} agent-runs:${o.agent_runs}`;
  $('stats').innerHTML=['requests|'+o.requests,'services|'+o.services,'reconstructions|'+o.reconstructions,'agentic runs|'+o.agent_runs,'fox|'+o.fox,'model|'+o.model].map(s=>{const[k,v]=s.split('|');return `<div class=card stat><div class=v>${v}</div><div class=k>${k}</div></div>`}).join('');
 }catch(e){$('hdr').textContent='overview failed: '+e;$('stats').innerHTML=`<div class="card warn">overview failed: ${e}</div>`;}
 await sec('#t-svc tbody',async()=>{
  const sv=await j('/api/services');
  $('t-svc').querySelector('tbody').innerHTML=sv.services.map(s=>`<tr><td><code>${s.service}</code></td><td>${s.requests}</td><td>${s.total_tokens}</td><td class=mut>${Object.entries(s.models).map(([m,c])=>m.split(':')[0]+'&times;'+c).join('<br>')}</td><td><b>${s.project||''}</b><br><span class=mut>${(s.pipeline_summary||'').slice(0,140)}</span></td><td>${scoreCell(s.score,s.grade)}<br><span class=mut title="vibe index: thin prompt-wrapper vs engineered system">⚡${s.vibe} ${s.vibe_label}</span></td></tr>`).join('');});
 const rc=await j('/api/reconstructions');
 $('sel-recon').innerHTML=rc.map(r=>`<option>${r.service}</option>`).join('');
 const showRecon=async()=>{const s=$('sel-recon').value;if(!s)return;const d=await j('/api/reconstructions/'+s);const files=Object.keys(d.files);$('sel-file').innerHTML=files.map(f=>`<option>${f}</option>`).join('');$('recon-view').textContent=d.files[files[0]]||'';};
 $('sel-recon').onchange=showRecon;$('sel-file').onchange=async()=>{const s=$('sel-recon').value,f=$('sel-file').value;const d=await j(`/api/reconstructions/${s}/file?path=${encodeURIComponent(f)}`);$('recon-view').textContent=d.content||JSON.stringify(d);};
 if(rc.length)showRecon();
 let progCache=null;
 const showProg=async()=>{const s=$('sel-recon').value;if(!s)return;const mode=$('sel-pmode').value,n=$('inp-pn').value||5;$('prog-msg').textContent='profiling…';
  try{const d=await j(`/api/reconstructions/${s}/progression?n=${n}&mode=${mode}`);progCache=d;
  $('prog-msg').textContent=`${d.steps.length} steps, converged=${d.converged}`;
  $('t-prog').querySelector('tbody').innerHTML=d.steps.map((st,i)=>{const dl=st.delta||{};const ch=dl.project_changed?'<span class=warn>label flip</span>':'<span class=ok>stable</span>';
   const ns=(dl.new_stages||[]).join(', ').slice(0,60);
   return `<tr><td><a href=# data-step=${i}>${st.step}</a></td><td>${scoreCell(st.score.score,st.score.grade)}<br><span class=mut>⚡${st.vibe.vibe} ${st.vibe.label}</span></td><td>${st.requests}</td><td class=mut>${st.window}</td><td><b>${st.project||''}</b><br><span class=mut>${st.n_templates} templates, ${st.n_instructions} instr</span></td><td class=mut>${(st.pipeline||[]).join(' → ').slice(0,90)}</td><td>${ch}${ns?'<br><span class=mut>+'+ns+'</span>':''}${dl.template_growth?'<br><span class=mut">tpl Δ '+(dl.template_growth>0?'+':'')+dl.template_growth+'</span>':''}</td></tr>`}).join('');
  drawProgChart(d.steps);
  const showStep=i=>{const st=progCache.steps[i];
   $('prog-detail').textContent=`step ${st.step} · ${st.requests} queries · ${st.window}\nproject: ${st.project}\nscore: ${st.score.score} (${st.score.grade}) — ${JSON.stringify(st.score.factors)}\nvibe: ${st.vibe.vibe} ${st.vibe.label} — ${JSON.stringify(st.vibe.factors)}\nmodels: ${JSON.stringify(st.models)}\npipeline: ${(st.pipeline||[]).join(' → ')}\nschema: ${(st.schema_hints||[]).join(', ')}\n\ntemplates:\n- ${(st.top_templates||[]).join('\\n- ')}\n\ninstructions:\n- ${(st.sample_instructions||[]).join('\\n- ')}`;};
  document.querySelectorAll('[data-step]').forEach(a=>a.onclick=e=>{e.preventDefault();showStep(+a.dataset.step);});
  window._showProgStep=showStep;
  }catch(e){$('prog-msg').textContent='failed: '+e;}};
 $('b-prog').onclick=showProg;$('sel-recon').addEventListener('change',()=>{progCache=null;$('prog-msg').textContent='';});
  const runs=await j('/api/runs').catch(e=>{document.querySelector('#t-runs tbody').innerHTML=`<tr><td class=warn>failed: ${e}</td></tr>`;return [];});
  $('t-runs').querySelector('tbody').innerHTML=runs.map(r=>`<tr><td><a href=# data-run="${r.run_id}">${r.run_id}</a></td><td class=mut>${r.model||''}</td><td class=mut>${(r.services||[]).join(', ').slice(0,80)}</td><td>${r.elapsed_s??'?'}s</td><td>${r.errors??0}</td></tr>`).join('')||'<tr><td class=mut>no runs yet</td></tr>';
  document.querySelectorAll('[data-run]').forEach(a=>a.onclick=e=>{e.preventDefault();showRun(a.dataset.run);});
  loadTrend();
  try{const b=await j('/api/runs');if(b.length){const d=await j('/api/runs/'+b[0].run_id);$('brief').textContent=(d.brief||'').slice(0,3000);}else{const inv=await j('/api/investigation');$('brief').textContent=(inv.readme||'no brief yet — launch an agentic run').slice(0,3000);}}catch(e){$('brief').textContent='unavailable';}
  try{
   const m=await j('/api/fox/live');const peers=(m.mesh&&(m.mesh.peers||[]))||[];
   $('t-mesh').querySelector('tbody').innerHTML=peers.map(p=>{const h=p.health||{};return `<tr><td><code>${p.machine||p.node_id}</code></td><td class=${p.online?'ok':'warn'}>${p.online}</td><td>${(p.hardware||{}).kind||'?'}</td><td>${h.llm_requests_1h??'?'}</td><td class=mut>${(h.services||[]).map(s=>s.name).join(', ').slice(0,120)}</td></tr>`}).join('')||'<tr><td class=mut>no peers</td></tr>';
  }catch(e){$('t-mesh').querySelector('tbody').innerHTML=`<tr><td class=warn>mesh failed: ${e}</td></tr>`;}
  try{
   const ev=await j('/api/evidence');
   $('t-ev').querySelector('tbody').innerHTML=ev.files.map(f=>`<tr><td><code>${f.name}</code></td><td class=mut>${f.size_mb} MB</td></tr>`).join('');
  }catch(e){$('t-ev').querySelector('tbody').innerHTML=`<tr><td class=warn>evidence failed: ${e}</td></tr>`;}
  loadDesignRail();
 }
const drawProgChart=steps=>{
 const W=680,H=240,pL=32,pB=24,pT=14,plotH=H-pB-pT-26,maxQ=Math.max(...steps.map(s=>s.requests),1);
 const X=i=>pL+(W-pL-12)*(steps.length===1?0.5:i/(steps.length-1));
 const Yq=q=>H-pB-(plotH)*(q/maxQ), Ys=s=>H-pB-(plotH)*(s/100);
 const gcol=g=>g==='A'?'#3fb950':g==='B'?'#a3d635':g==='C'?'#d29922':'#f85149';
 let g='';[0,25,50,75,100].forEach(v=>{g+=`<line x1=${pL} y1=${Ys(v)} x2=${W-8} y2=${Ys(v)} stroke="#30363d" stroke-width="1"/><text x=4 y=${Ys(v)+4} fill="#8b949e" font-size="10">${v}</text>`;});
 let bars='',labels='';
 steps.forEach((st,i)=>{const bw=Math.max(8,Math.min(40,(W-pL)/steps.length*0.45));
  bars+=`<rect x=${(X(i)-bw/2).toFixed(1)} y=${Yq(st.requests).toFixed(1)} width=${bw.toFixed(1)} height=${(H-pB-Yq(st.requests)).toFixed(1)} fill="#1f6feb" opacity="0.45"><title>${st.requests} queries</title></rect>`;
  labels+=`<text x=${X(i)} y=${H-10} fill="#8b949e" font-size="10" text-anchor="middle">${st.step}</text>`;
  if(st.delta&&st.delta.project_changed)labels+=`<text x=${X(i)} y=${H-pB+2} fill="#d29922" font-size="11" text-anchor="middle">◆</text>`;});
 const pts=steps.map((st,i)=>`${X(i).toFixed(1)},${Ys(st.score.score).toFixed(1)}`).join(' ');
 const dots=steps.map((st,i)=>`<circle cx=${X(i).toFixed(1)} cy=${Ys(st.score.score).toFixed(1)} r="6" fill="${gcol(st.score.grade)}" data-cstep=${i} style="cursor:pointer"><title>step ${st.step}: ${st.score.score} (${st.score.grade}) · ⚡${st.vibe.vibe} ${st.vibe.label}</title></circle>`).join('');
 $('prog-chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:720px">${g}${bars}<polyline points="${pts}" fill="none" stroke="#58a6ff" stroke-width="2"/>${dots}${labels}</svg>`;
 document.querySelectorAll('[data-cstep]').forEach(c=>c.onclick=()=>window._showProgStep&&window._showProgStep(+c.dataset.cstep));
};
const showRun=async id=>{
 try{const d=await j('/api/runs/'+id);$('run-brief').textContent=(d.brief||'').slice(0,6000);}catch(e){$('run-brief').textContent='brief failed: '+e;}
 try{const g=await j('/api/runs/'+id+'/graph');renderRunGraph(g);}catch(e){$('run-dag').textContent='graph failed: '+e;}
};
const renderRunGraph=g=>{
 $('rg-title').textContent=`${g.run_id} · ${g.model}${g.quick?' · quick':''} · ${g.elapsed_s}s · ${g.totals.agents_ok} ok/${g.totals.agents_error} err · ${g.totals.prompt_tokens+g.totals.completion_tokens} tok · $0.00 local`;
 const layers=['scout','profiler','critic','reporter'].filter(L=>g.nodes.some(n=>n.layer===L));
 const BW=180,BH=44,GX=46,GY=14,pad=16;
 const cols=layers.map(L=>g.nodes.filter(n=>n.layer===L));
 const rows=Math.max(...cols.map(c=>c.length));
 const W=pad*2+layers.length*BW+(layers.length-1)*GX, H=pad*2+rows*(BH+GY);
 const pos={};
 cols.forEach((col,ci)=>col.forEach((n,ri)=>{pos[n.id]={x:pad+ci*(BW+GX),y:pad+ri*(BH+GY)};}));
 const ecol=s=>s==='ok'?'#3fb950':s==='error'?'#f85149':'#8b949e';
 let svg=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px">`;
 g.edges.forEach(e=>{const a=pos[e.from],b=pos[e.to];if(!a||!b)return;
  svg+=`<line x1=${a.x+BW} y1=${a.y+BH/2} x2=${b.x} y2=${b.y+BH/2} stroke="#30363d" stroke-width="1.5"/>`;});
 cols.forEach(col=>col.forEach(n=>{const p=pos[n.id];
  svg+=`<g><rect x=${p.x} y=${p.y} width=${BW} height=${BH} rx=6 fill="#161b22" stroke="${ecol(n.status)}" stroke-width="1.5"><title>${n.id} · ${n.ms}ms</title></rect><text x=${p.x+8} y=${p.y+17} fill="#e6edf3" font-size="11">${n.label}</text><text x=${p.x+8} y=${p.y+33} fill="#8b949e" font-size="10">${n.sub}</text></g>`;}));
 $('run-dag').innerHTML=svg+'</svg>';
 const mx=Math.max(...g.nodes.map(n=>n.prompt_tokens+n.completion_tokens),1);
 $('run-cost').innerHTML=g.nodes.slice().sort((a,b)=>(b.prompt_tokens+b.completion_tokens)-(a.prompt_tokens+a.completion_tokens)).map(n=>{const t=n.prompt_tokens+n.completion_tokens;
  return `<div class=row style="margin:3px 0"><code style="min-width:200px">${n.id}</code><div style="flex:1;background:#00000040;border-radius:4px"><div style="width:${(100*t/mx).toFixed(1)}%;background:#1f6feb;border-radius:4px">&nbsp;</div></div><span class=mut>${t} tok · ${(n.ms/1000).toFixed(1)}s</span></div>`;}).join('');
 const badge=a=>a==='match'?'<span class=ok>match</span>':a==='partial'?'<span class=warn>partial</span>':a==='disagree'?'<span style="color:#f85149">disagree</span>':'<span class=mut>?</span>';
 $('t-conf').querySelector('tbody').innerHTML=g.services.map(s=>{const c=s.confidence;
  const bar=c==null?'<span class=mut>—</span>':`<div style="background:#00000040;border-radius:4px;min-width:110px"><div style="width:${(c*100).toFixed(0)}%;background:#3fb950;border-radius:4px">&nbsp;</div></div> ${c.toFixed(2)}`;
  return `<tr><td><code>${s.service}</code></td><td>${bar}</td><td class=mut>${s.heuristic_project||''}</td><td>${s.llm_project||''}<br><span class=mut>${(s.what_building||'').slice(0,130)}</span></td><td>${badge(s.agreement)}</td></tr>`;}).join('');
 const withGaps=g.services.filter(s=>(s.critic_gaps||[]).length);
 $('run-gaps').innerHTML=withGaps.length?withGaps.map(s=>`<div style="margin:6px 0"><b>${s.service}</b>${s.critic_gaps.map(q=>`<div class=mut>• ${q}</div>`).join('')}</div>`).join(''):'<span class=mut>no critic gaps — quick mode skips the critic stage</span>';
 $('run-quotes').innerHTML=g.services.map(s=>((s.evidence_quotes||[]).length?`<div style="margin:6px 0"><b>${s.service}</b>${s.evidence_quotes.map(q=>`<div class=mut>&ldquo;${q.slice(0,160)}&rdquo;</div>`).join('')}</div>`:'')).join('')||'<span class=mut>no quotes recorded</span>';
};
const loadTrend=async()=>{try{const t=await j('/api/runs-compare?limit=5');
 $('t-trend').querySelector('tbody').innerHTML=t.services.map(s=>`<tr><td><code>${s}</code></td><td>${t.cols.map(c=>{const v=c.confidence[s];return `<span title="${c.run_id}${c.quick?' (quick)':''}" style="display:inline-block;min-width:52px;margin-right:6px;padding:2px 6px;border-radius:4px;background:${v==null?'#21262d':'#1f6feb'};font-size:12px">${v==null?'—':v.toFixed(2)}</span>`;}).join('')}</td></tr>`).join('');
}catch(e){$('t-trend').querySelector('tbody').innerHTML=`<tr><td class=warn>trend failed: ${e}</td></tr>`;}};
const escH=s=>String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
const inlineMd=s=>escH(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2">$1</a>');
const renderMarkdown=md=>{
 const lines=String(md).split('\\n');
 let html='',fence=false,lang='',buf=[],table=[],para=[],inList=null;
 const flushPara=()=>{if(para.length){html+=`<p>${inlineMd(para.join(' '))}</p>`;para=[];}};
 const closeList=()=>{if(inList){html+=inList==='ul'?'</ul>':'</ol>';inList=null;}};
 const cells=r=>r.trim().replace(/^\||\|$/g,'').split('|').map(c=>inlineMd(c.trim()));
 const flushTable=()=>{if(!table.length)return '';
  const rows=table.filter(r=>!/^\|?[\s:|\-]+\|?\s*$/.test(r));table=[];
  if(!rows.length)return '';
  return `<table><thead><tr>${cells(rows[0]).map(c=>`<th>${c}</th>`).join('')}</tr></thead><tbody>${rows.slice(1).map(r=>`<tr>${cells(r).map(c=>`<td>${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`;};
 for(const line of lines){
  const m=line.match(/^\s*```(\w*)\s*$/);
  if(m){if(!fence){fence=true;lang=(m[1]||'').toLowerCase();buf=[];}
   else{const src=buf.join('\\n');fence=false;
    html+=lang==='mermaid'?`<div class=diagram-wrap><pre class=mermaid>${escH(src)}</pre></div>`:`<div class=code-wrap>${lang?`<div class=code-lang>${escH(lang)}</div>`:''}<pre>${escH(src)}</pre></div>`;}
   continue;}
  if(fence){buf.push(line);continue;}
  const t=line.trim();
  if(t===''){flushPara();closeList();html+=flushTable();continue;}
  if(/^\|.*\|\s*$/.test(line)){flushPara();closeList();table.push(line);continue;}
  html+=flushTable();
  const hm=line.match(/^(#{1,4})\s+(.*)/);
  if(hm){flushPara();closeList();html+=`<h${hm[1].length+1}>${inlineMd(hm[2])}</h${hm[1].length+1}>`;continue;}
  if(/^---+\s*$/.test(t)||/^\*\*\*+\s*$/.test(t)){flushPara();closeList();html+='<hr>';continue;}
  if(/^>\s?/.test(line)){flushPara();closeList();html+=`<blockquote>${inlineMd(line.replace(/^>\s?/,''))}</blockquote>`;continue;}
  let lm=line.match(/^\s*[-*]\s+(.*)/);
  if(lm){flushPara();if(inList!=='ul'){closeList();html+='<ul>';inList='ul';}html+=`<li>${inlineMd(lm[1])}</li>`;continue;}
  lm=line.match(/^\s*\d+[.)]\s+(.*)/);
  if(lm){flushPara();if(inList!=='ol'){closeList();html+='<ol>';inList='ol';}html+=`<li>${inlineMd(lm[1])}</li>`;continue;}
  closeList();para.push(t);
 }
 flushPara();closeList();html+=flushTable();
 return html;
};
const MERMAID_SRC=['/static/mermaid.min.js','https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'];
const renderMermaid=async root=>{
 const nodes=root.querySelectorAll('pre.mermaid');
 if(!nodes.length)return;
 const run=async()=>{try{window.mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'dark',themeVariables:{darkMode:true,background:'#0a0e14',primaryColor:'#1f6feb',primaryTextColor:'#e6edf3',lineColor:'#8b949e',textColor:'#e6edf3'}});}catch(e){}
  for(const n of nodes){try{await window.mermaid.run({nodes:[n],suppressErrors:true});}catch(e){}}};
 if(window.mermaid&&window.mermaid.run){try{await run();return;}catch(e){}}
 for(const src of MERMAID_SRC){
  try{
   await new Promise((res,rej)=>{if(document.querySelector(`script[data-mm="${src}"]`))return res();const s=document.createElement('script');s.dataset.mm=src;s.src=src;s.onload=res;s.onerror=rej;document.head.appendChild(s);});
   if(window.mermaid&&window.mermaid.run){await run();return;}
  }catch(e){}
 }
};
const loadDesignRail=async()=>{try{const idx=await j('/api/design/docs');
 const groups={};idx.docs.forEach(d=>{(groups[d.group]=groups[d.group]||[]).push(d);});
 $('design-rail').innerHTML=Object.entries(groups).map(([g,ds])=>`<div class=mut style="margin:6px 0 2px">${g}</div>${ds.map(d=>`<div><a href=# data-doc="${d.id}">${d.title}</a> <span class=mut>${d.available?d.diagrams+' diagrams':'—'}</span></div>`).join('')}`).join('');
 document.querySelectorAll('[data-doc]').forEach(a=>a.onclick=e=>{e.preventDefault();showDesignDoc(a.dataset.doc);});
 const first=(idx.docs||[]).find(d=>d.available);
 if(first)showDesignDoc(first.id);
}catch(e){$('design-rail').textContent='design index failed: '+e;}};
const showDesignDoc=async id=>{try{const d=await j('/api/design/docs/'+id);
 $('design-title').textContent=d.title;$('design-meta').textContent=`${d.group} · ${d.diagrams} diagrams`;
 document.querySelectorAll('[data-doc]').forEach(x=>x.classList.toggle('on',x.dataset.doc===id));
 $('design-doc').innerHTML=renderMarkdown(d.markdown);renderMermaid($('design-doc'));
}catch(e){$('design-doc').textContent='doc failed: '+e;}};
const liveDir=d=>d==='in'?'<span style="color:#58a6ff">IN</span>':d==='out'?'<span class=ok>OUT</span>':'<span class=warn>SYS</span>';
const liveTime=t=>new Date(t*1000).toTimeString().slice(0,8);
const loadLive=async()=>{
 let st={running:false};
 try{st=await j('/api/live/status');}catch(e){$('live-state').textContent='status failed: '+e;return;}
 $('live-state').textContent=st.running?`● live · ${st.events_buffered} events · ${st.polls} polls · up ${st.uptime_s||0}s`:'○ stopped';
 if(!st.running)return;
 try{const f=await j('/api/live/feed?limit=40');
  $('t-feed').querySelector('tbody').innerHTML=f.events.map(e=>`<tr><td class=mut>${liveTime(e.t)}</td><td>${liveDir(e.dir)}</td><td><code>${e.service}</code></td><td class=mut>${(e.model||'').split(':')[0]}</td><td class=mut>${(e.prompt_head||'').slice(0,120)} <span class=mut>· ${e.prompt_tokens+e.completion_tokens} tok</span></td></tr>`).join('')||'<tr><td class=mut colspan=5>no events yet — waiting for traffic</td></tr>';
 }catch(e){}
 try{const r=await j('/api/live/rates?window_s=300');
  $('t-rates').querySelector('tbody').innerHTML=r.services.map(s=>`<tr><td><code>${s.service}</code></td><td>${s.req}</td><td>${s.tokens}</td><td>${s.req_per_min}</td><td>${s.tok_per_min}</td></tr>`).join('')||'<tr><td class=mut colspan=5>no completed requests in window</td></tr>';
 }catch(e){}
 try{const sv=await j('/api/services');
  const cur=$('sel-live').value;
  $('sel-live').innerHTML=sv.services.map(s=>`<option>${s.service}</option>`).join('');
  if(cur)$('sel-live').value=cur;
 }catch(e){}
};
$('b-live-start').onclick=async()=>{const i=+$('inp-live-int').value||5;await (await fetch('/api/live/start',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({interval_s:i})})).json();loadLive();};
$('b-live-stop').onclick=async()=>{await fetch('/api/live/stop',{method:'POST'});loadLive();};
$('b-live-recon').onclick=async()=>{const s=$('sel-live').value;if(!s)return;const mode=$('sel-lmode').value;$('live-recon-msg').textContent='reconstructing…';
 try{
  try{const st=await j('/api/live/status');if(!st.running)await (await fetch('/api/live/start',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();}catch(e){}
  const d=await j(`/api/live/reconstruction?service=${encodeURIComponent(s)}&n=5&mode=${mode}&history=200`);
  $('live-recon-msg').textContent=`${d.steps.length} steps (${d.history_rows} history + ${d.live_rows} live), converged=${d.converged}`;
  $('t-liveprog').querySelector('tbody').innerHTML=d.steps.map(st=>{const dl=st.delta||{};
   return `<tr><td>${st.step}</td><td>${scoreCell(st.score.score,st.score.grade)}</td><td>${st.requests}</td><td><b>${st.project||''}</b></td><td>${dl.project_changed?'<span class=warn>flip</span>':'<span class=ok>stable</span>'}</td></tr>`;}).join('');
  loadLive();
 }catch(e){$('live-recon-msg').textContent='failed: '+e;}};
setInterval(()=>{const s=$('s-live');if(s&&s.classList.contains('on'))loadLive();},4000);
$('b-inv').onclick=async()=>{$('runmsg').textContent='investigating…';const r=await j('/api/investigate');$('runmsg').textContent=r.report||JSON.stringify(r);load();};
$('b-agent').onclick=async()=>{$('runmsg').textContent='launching…';const q=$('opt-quick').checked;const r=await (await fetch('/api/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({quick:q})})).json();$('runmsg').textContent='run '+JSON.stringify(r)+' — refresh Agentic tab in a few min';};
load();
</script></body></html>
"""


def _newest_db() -> str | None:
    dbs = sorted(glob.glob(os.path.join(config.EVIDENCE_DIR, "fox_services_*.db")))
    if dbs:
        return dbs[-1]
    return config.find_fox_db()


def _service_rows(limit: int = 5000) -> list[dict]:
    db = _newest_db()
    if not db or not os.path.exists(db):
        return []
    return store.load_requests(db, limit=limit)


@app.get("/health")
def health():
    return {"status": "ok", "service": "intel-forensics", "model": ollama_client.MODEL}


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/api/overview")
def overview():
    rows = _service_rows(limit=5000)
    svcs = {r.get("service") for r in rows}
    recon = [d for d in glob.glob(os.path.join(config.RECON_DIR, "*")) if os.path.isdir(d)]
    try:
        fox = store.snapshot_api  # touch import; real check below
        import urllib.request
        with urllib.request.urlopen(config.FOX_URL + "/health", timeout=3) as r:
            fox_ok = "ok" if r.status == 200 else str(r.status)
    except Exception as e:  # noqa: BLE001
        fox_ok = f"down ({type(e).__name__})"
    return {"requests": len(rows), "services": len(svcs),
            "reconstructions": len(recon), "agent_runs": len(ag.list_runs()),
            "fox": fox_ok, "model": ollama_client.MODEL,
            "ollama": ollama_client.OLLAMA_URL, "version": APP_VERSION}


@app.get("/api/services")
def services():
    from iforensics import score as scoring
    rows = _service_rows()
    if not rows:
        return {"services": []}
    inv = infer.investigate_all(rows)
    out = []
    for svc, p in inv["services"].items():
        s = scoring.score_profile(p)
        v = scoring.vibe_index(p, stable=True)
        out.append({"service": svc, "requests": p["requests"],
                    "total_tokens": p["total_tokens"], "models": p["models"],
                    "query_types": p.get("query_types"),
                    "project": p.get("project"),
                    "pipeline_summary": p.get("pipeline_summary"),
                    "pipeline": p.get("pipeline"),
                    "score": s["score"], "grade": s["grade"], "factors": s["factors"],
                    "vibe": v["vibe"], "vibe_label": v["label"]})
    return {"services": sorted(out, key=lambda s: -s["requests"])}


@app.get("/api/investigation")
def investigation():
    md_path = os.path.join(config.EVIDENCE_DIR, "INVESTIGATION.md")
    return {"readme": open(md_path).read() if os.path.exists(md_path) else ""}


@app.get("/api/investigate")
def investigate():
    from iforensics import report as report_mod
    from iforensics import fox_client
    api = fox_client.collect_all(hours=720, req_limit=2000)
    rows = _service_rows()
    if not rows:
        raise HTTPException(503, "no evidence DB rows available")
    inv = infer.investigate_all(rows)
    mesh = api.get("mesh_status") if isinstance(api.get("mesh_status"), dict) else None
    md = report_mod.render(inv, mesh=mesh)
    path = os.path.join(config.EVIDENCE_DIR, "INVESTIGATION.md")
    report_mod.write(md, path)
    return {"report": path, "requests": inv["n_requests"], "services": inv["n_services"]}


@app.get("/api/reconstructions")
def reconstructions():
    out = []
    for d in sorted(glob.glob(os.path.join(config.RECON_DIR, "*"))):
        if not os.path.isdir(d):
            continue
        meta_path = os.path.join(d, "RECONSTRUCTED.json")
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except Exception:  # noqa: BLE001
                pass
        out.append({"service": os.path.basename(d),
                    "project": meta.get("inferred_project", ""),
                    "requests": (meta.get("reconstructed_from") or {}).get("requests", 0)})
    return out


@app.get("/api/reconstructions/{svc}")
def reconstruction(svc: str):
    base = os.path.join(config.RECON_DIR, svc)
    if not os.path.isdir(base):
        raise HTTPException(404, "unknown service")
    files = {}
    for root, _, fns in os.walk(base):
        for fn in fns:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, base)
            try:
                with open(fp) as f:
                    files[rel] = f.read()[:20000]
            except Exception:  # noqa: BLE001
                pass
    return {"service": svc, "files": files}


@app.get("/api/reconstructions/{svc}/file")
def reconstruction_file(svc: str, path: str):
    base = os.path.realpath(os.path.join(config.RECON_DIR, svc))
    target = os.path.realpath(os.path.join(base, path))
    if not target.startswith(base) or not os.path.isfile(target):
        raise HTTPException(404, "bad path")
    with open(target) as f:
        return {"content": f.read()[:30000]}


@app.get("/api/reconstructions/{svc}/progression")
def reconstruction_progression(svc: str, n: int = 5, mode: str = "cumulative"):
    """Partial + progressive reconstructions from Fox-server queries.

    mode=cumulative: step k profiles queries[0..k] (confidence growth).
    mode=window: step k profiles only its own time slice (partial views).
    """
    from iforensics import progression as prog, score as scoring
    if mode not in ("cumulative", "window"):
        raise HTTPException(400, "mode must be cumulative|window")
    rows = _service_rows(limit=5000)
    if not any((r.get("service") or "") == svc for r in rows):
        raise HTTPException(404, "unknown service (no queries)")
    res = prog.progression(svc, rows, n=max(2, min(12, n)), mode=mode)
    return scoring.attach_scores(res)


class RunReq(BaseModel):
    quick: bool = True
    model: str | None = None
    only: list[str] | None = None


@app.get("/api/runs")
def runs():
    return ag.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    m = ag.load_run(run_id)
    if not m:
        raise HTTPException(404, "unknown run")
    return m


@app.get("/api/runs/{run_id}/graph")
def run_graph(run_id: str):
    """Chart-ready agentic reconstruction: DAG, costs, confidence,
    heuristic-vs-LLM agreement, critic gaps."""
    from iforensics import run_viz
    g = run_viz.build_run_graph(run_id)
    if not g:
        raise HTTPException(404, "unknown run")
    return g


@app.get("/api/runs-compare")
def runs_compare(limit: int = 5):
    """Confidence per service across the last N runs (cross-run trend)."""
    from iforensics import run_viz
    return run_viz.compare_runs(max(2, min(10, limit)))


class LiveStartReq(BaseModel):
    interval_s: float = 5.0


@app.post("/api/live/start")
def live_start(req: LiveStartReq):
    """Attach the live tap to fox :8210 (queue + request deltas + model loads)."""
    from iforensics import live as live_mod
    return live_mod.start(max(1.0, min(60.0, req.interval_s or 5.0)))


@app.post("/api/live/stop")
def live_stop():
    from iforensics import live as live_mod
    return live_mod.stop()


@app.get("/api/live/status")
def live_status():
    from iforensics import live as live_mod
    t = live_mod.tap()
    return t.status() if t else {"running": False}


@app.get("/api/live/feed")
def live_feed(limit: int = 50):
    from iforensics import live as live_mod
    t = live_mod.tap()
    if not t:
        raise HTTPException(409, "tap not running (POST /api/live/start)")
    return {"events": t.snapshot(max(1, min(500, limit)))}


@app.get("/api/live/rates")
def live_rates(window_s: float = 300):
    from iforensics import live as live_mod
    return live_mod.rates(max(30.0, min(3600.0, window_s)))


@app.get("/api/live/reconstruction")
def live_reconstruction(service: str, n: int = 5, mode: str = "cumulative",
                        history: int = 200):
    """Progressive reconstruction over recent history + live rows.

    Sparse live traffic alone rarely fills a window, so the window is
    backfilled from recent fox history (oldest first) with tap-buffered
    live rows appended (deduped by id). Response reports the mix.
    """
    from iforensics import live as live_mod
    from iforensics import progression as prog, score as scoring
    if mode not in ("cumulative", "window"):
        raise HTTPException(400, "mode must be cumulative|window")
    hist = live_mod.history_rows(service, limit=max(0, min(2000, history)))
    live_rows: list[dict] = []
    t = live_mod.tap()
    if t:
        seen = {r.get("id") for r in hist}
        live_rows = [r for r in t.rows() if r.get("service") == service
                     and r.get("id") not in seen]
    rows = sorted(hist + live_rows, key=lambda r: r.get("ts", 0))
    if len(rows) < 2:
        raise HTTPException(409, f"only {len(rows)} rows for {service!r} — no history yet")
    res = scoring.attach_scores(prog.progression(service, rows, n=max(2, min(12, n)), mode=mode))
    res["history_rows"] = len(hist)
    res["live_rows"] = len(live_rows)
    res["tap_running"] = t is not None
    return res


@app.get("/api/design/docs")
def design_docs_index():
    """Every design document, in reading order, with diagram counts."""
    from iforensics import design_docs
    return design_docs.list_docs()


@app.get("/api/design/docs/{doc_id}")
def design_doc(doc_id: str):
    """One design document's Markdown. Fixed id index — traversal 404s."""
    from iforensics import design_docs
    try:
        return design_docs.get_doc(doc_id)
    except design_docs.UnknownDoc:
        raise HTTPException(404, "unknown doc")


@app.post("/api/runs")
def runs_create(req: RunReq):
    model = req.model or ollama_client.MODEL
    key = ag.launch_background(_service_rows, model=model,
                               quick=req.quick, only=req.only)
    return {"launched": key, "model": model, "quick": req.quick}


@app.get("/api/runs-pending/{key}")
def run_pending(key: str):
    return ag.background_status(key)


@app.get("/api/evidence")
def evidence():
    files = []
    if os.path.isdir(config.EVIDENCE_DIR):
        for root, _, fns in os.walk(config.EVIDENCE_DIR):
            for fn in fns:
                fp = os.path.join(root, fn)
                try:
                    sz = os.path.getsize(fp) / 1024 / 1024
                except OSError:
                    sz = 0
                files.append({"name": os.path.relpath(fp, config.EVIDENCE_DIR),
                              "size_mb": round(sz, 2)})
    return {"files": sorted(files, key=lambda f: f["name"], reverse=True)[:100]}


@app.get("/api/ollama")
def ollama():
    return ollama_client.ping()


@app.get("/api/fox/live")
def fox_live():
    from iforensics import fox_client
    out: dict = {}
    calls = {
        "stats": fox_client.stats_summary,
        "mesh": fox_client.mesh_status,
        "queue": fox_client.llm_queue,
    }
    for k, fn in calls.items():
        try:
            out[k] = fn() if k != "stats" else fn(24)
        except Exception as e:  # noqa: BLE001
            out[k] = {"_error": str(e)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("IF_PORT", "8211")))
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
