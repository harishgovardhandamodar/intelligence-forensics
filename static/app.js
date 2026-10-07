const $=id=>document.getElementById(id);
const escH=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const escA=escH;
const TABS=[...document.querySelectorAll('#tabs button')].map(b=>b.dataset.t);
const trowState=(cols,msg,cls='mut')=>`<tr><td class="${cls}" colspan="${cols}">${escH(msg)}</td></tr>`;
const activateTab=(name,push)=>{if(!TABS.includes(name))name='overview';TABS.forEach(t=>{const on=t===name,btn=document.querySelector(`#tabs button[data-t="${t}"]`),sec=$('s-'+t);if(btn)btn.classList.toggle('on',on);if(sec)sec.classList.toggle('on',on);});if(push!==false){const h='#'+name;if(location.hash!==h)history.pushState(null,'',h);}if(name==='live'){startLiveStream();loadTs();}else{stopLiveStream();}if(name==='security')loadSecurity();if(name==='findings')loadFindings();if(name==='timeline')loadChain();if(name==='graph')loadKnowledge();if(name==='ledger')loadLedger();if(name==='sim'){loadSimUsers();loadSimScenarios();loadSimRuns();}document.title='Intelligence Forensics — '+name;};
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>activateTab(b.dataset.t));
window.addEventListener('hashchange',()=>activateTab(location.hash.slice(1),false));
window.addEventListener('popstate',()=>activateTab(location.hash.slice(1),false));
const j=async u=>{const r=await fetch(u);return r.json()};
const pj=async(u,b)=>{const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})});return r.json();};
const gcls=g=>(g==='A'||g==='B')?'ok':'warn';
const scoreCell=(v,g)=>`<b class="${gcls(g)}">${escH(v)}</b> <span class="mut">${escH(g)}</span>`;
async function load(){
 const sec=async(id,fn)=>{try{await fn();}catch(e){const el=document.querySelector(id);if(el)el.innerHTML=trowState(8,'failed: '+e,'warn');}};
 try{
  const o=await j('/api/overview');
  $('hdr').textContent=`v${o.version||'?'}+js${o.js||'?'} · fox:${o.fox} model:${o.model} reqs:${o.requests} svcs:${o.services} recon:${o.reconstructions} agent-runs:${o.agent_runs}`;
  $('stats').innerHTML=['requests|'+o.requests,'services|'+o.services,'reconstructions|'+o.reconstructions,'agentic runs|'+o.agent_runs,'fox|'+o.fox,'model|'+o.model].map(s=>{const[k,v]=s.split('|');return `<div class="card stat"><div class="v">${escH(v)}</div><div class="k">${escH(k)}</div></div>`}).join('');
 }catch(e){$('hdr').textContent='overview failed: '+e;$('stats').innerHTML=`<div class="card warn">overview failed: ${escH(e)}</div>`;}
  await sec('#t-svc tbody',async()=>{
   const sv=await j('/api/services');
   svcCache=sv.services||[];
   $('t-svc').querySelector('tbody').innerHTML=sv.services.map(s=>`<tr data-svc="${escA(s.service)}"><td><code>${escH(s.service)}</code></td><td>${escH(s.requests)}</td><td>${escH(s.total_tokens)}</td><td class="mut">${Object.entries(s.models).map(([m,c])=>escH(m).split(':')[0]+'&times;'+escH(c)).join('<br>')}</td><td><b>${escH(s.project||'')}</b><br><span class="mut">${escH((s.pipeline_summary||'').slice(0,140))}</span></td><td>${scoreCell(s.score,s.grade)}<br><span class="mut" title="vibe index: thin prompt-wrapper vs engineered system">&#x26a1;${escH(s.vibe)} ${escH(s.vibe_label)}</span></td></tr>`).join('');wireTable('#t-svc','#filt-svc');});
 const rc=await j('/api/reconstructions');
 $('sel-recon').innerHTML=rc.map(r=>`<option value="${escA(r.service)}">${escH(r.service)}</option>`).join('');
 const showRecon=async()=>{const s=$('sel-recon').value;if(!s)return;const d=await j('/api/reconstructions/'+encodeURIComponent(s));const files=Object.keys(d.files);$('sel-file').innerHTML=files.map(f=>`<option value="${escA(f)}">${escH(f)}</option>`).join('');$('recon-view').textContent=d.files[files[0]]||'';};
 $('sel-recon').onchange=showRecon;$('sel-file').onchange=async()=>{const s=$('sel-recon').value,f=$('sel-file').value;const d=await j(`/api/reconstructions/${encodeURIComponent(s)}/file?path=${encodeURIComponent(f)}`);$('recon-view').textContent=d.content||JSON.stringify(d);};
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
   $('prog-detail').textContent=`step ${st.step} · ${st.requests} queries · ${st.window}
project: ${st.project}
score: ${st.score.score} (${st.score.grade}) — ${JSON.stringify(st.score.factors)}
vibe: ${st.vibe.vibe} ${st.vibe.label} — ${JSON.stringify(st.vibe.factors)}
models: ${JSON.stringify(st.models)}
pipeline: ${(st.pipeline||[]).join(' → ')}
schema: ${(st.schema_hints||[]).join(', ')}

templates:
- ${(st.top_templates||[]).join('\n- ')}

instructions:
- ${(st.sample_instructions||[]).join('\n- ')}`;};
  document.querySelectorAll('[data-step]').forEach(a=>a.onclick=e=>{e.preventDefault();showStep(+a.dataset.step);});
  window._showProgStep=showStep;
  }catch(e){$('prog-msg').textContent='failed: '+e;}};
 $('b-prog').onclick=showProg;$('sel-recon').addEventListener('change',()=>{progCache=null;$('prog-msg').textContent='';});
  const runs=await j('/api/runs').catch(e=>{document.querySelector('#t-runs tbody').innerHTML=`<tr><td class="warn">failed: ${escH(e)}</td></tr>`;return [];});
  $('t-runs').querySelector('tbody').innerHTML=runs.map(r=>r.status==='running'
   ?`<tr><td><code>${escH(r.run_id)}</code> <span class="pill">running ${escH(r.elapsed_s??'?')}s</span></td><td class="mut">${escH(r.model||'')}</td><td class="mut">queued behind Ollama — refresh to update</td><td>—</td><td>—</td></tr>`
   :`<tr><td><a href="#" data-run="${escA(r.run_id)}">${escH(r.run_id)}</a></td><td class="mut">${escH(r.model||'')}</td><td class="mut">${escH((r.services||[]).join(', ').slice(0,80))}</td><td>${escH(r.elapsed_s??'?')}s</td><td>${escH(r.errors??0)}</td></tr>`).join('')||'<tr><td class="mut">no runs yet</td></tr>';
  document.querySelectorAll('[data-run]').forEach(a=>a.onclick=e=>{e.preventDefault();showRun(a.dataset.run);});
  loadTrend();
  try{const b=(await j('/api/runs')).filter(r=>r.status!=='running');let md;if(b.length){const d=await j('/api/runs/'+b[0].run_id);md=d.brief||'';}else{const inv=await j('/api/investigation');md=inv.readme||'no brief yet — launch an agentic run';}$('brief').innerHTML=renderMarkdown(md.slice(0,6000));renderMermaid($('brief'));}catch(e){$('brief').innerHTML=`<span class="warn">brief unavailable: ${escH(e)}</span>`;}
  try{
   const m=await j('/api/fox/live');const peers=(m.mesh&&(m.mesh.peers||[]))||[];
   meshCache=peers;
   $('t-mesh').querySelector('tbody').innerHTML=peers.map(p=>{const h=p.health||{};return `<tr data-f='${escA(JSON.stringify(p))}'><td><code>${escH(p.machine||p.node_id)}</code></td><td class="${p.online?'ok':'warn'}">${escH(p.online)}</td><td>${escH((p.hardware||{}).kind||'?')}</td><td>${escH(h.llm_requests_1h??'?')}</td><td class="mut">${escH((h.services||[]).map(s=>s.name).join(', ').slice(0,120))}</td></tr>`}).join('')||'<tr><td class="mut">no peers</td></tr>';
  }catch(e){$('t-mesh').querySelector('tbody').innerHTML=`<tr><td class="warn">mesh failed: ${escH(e)}</td></tr>`;}
  try{drawTopo(await j('/api/topology'));}catch(e){$('topo').textContent='topology failed: '+e;}
  try{
   const ev=await j('/api/evidence');
   $('t-ev').querySelector('tbody').innerHTML=ev.files.map(f=>`<tr data-name="${escA(f.name)}" data-size="${escA(f.size_mb)}"><td><code>${escH(f.name)}</code></td><td class="mut">${escH(f.size_mb)} MB</td></tr>`).join('')||trowState(2,'no evidence files');
   $('t-ev').querySelectorAll('tbody tr[data-name]').forEach(r=>r.addEventListener('click',()=>showEvidence(r.dataset.name,r.dataset.size)));
   wireTable('#t-ev','#filt-ev');
  }catch(e){$('t-ev').querySelector('tbody').innerHTML=trowState(2,'evidence failed: '+e,'warn');}
  loadReports();
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
  bars+=`<rect x=${(X(i)-bw/2).toFixed(1)} y=${Yq(st.requests).toFixed(1)} width=${bw.toFixed(1)} height=${(H-pB-Yq(st.requests)).toFixed(1)} fill="#1f6feb" opacity="0.45"><title>${escH(st.requests)} queries</title></rect>`;
  labels+=`<text x=${X(i)} y=${H-10} fill="#8b949e" font-size="10" text-anchor="middle">${escH(st.step)}</text>`;
  if(st.delta&&st.delta.project_changed)labels+=`<text x=${X(i)} y=${H-pB+2} fill="#d29922" font-size="11" text-anchor="middle">◆</text>`;});
 const pts=steps.map((st,i)=>`${X(i).toFixed(1)},${Ys(st.score.score).toFixed(1)}`).join(' ');
 const dots=steps.map((st,i)=>`<circle cx=${X(i).toFixed(1)} cy=${Ys(st.score.score).toFixed(1)} r="6" fill="${gcol(st.score.grade)}" data-cstep="${i}" style="cursor:pointer"><title>step ${escH(st.step)}: ${escH(st.score.score)} (${escH(st.score.grade)}) · ${escH(st.vibe.vibe)} ${escH(st.vibe.label)}</title></circle>`).join('');
 $('prog-chart').innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:720px">${g}${bars}<polyline points="${pts}" fill="none" stroke="#58a6ff" stroke-width="2"/>${dots}${labels}</svg>`;
 document.querySelectorAll('[data-cstep]').forEach(c=>c.onclick=()=>window._showProgStep&&window._showProgStep(+c.dataset.cstep));
};
const showRun=async id=>{
 try{const d=await j('/api/runs/'+id);$('run-brief').innerHTML=renderMarkdown((d.brief||'').slice(0,8000));renderMermaid($('run-brief'));renderRunPanes(d);}catch(e){$('run-brief').innerHTML=`<span class="warn">brief failed: ${escH(e)}</span>`;}
 try{const g=await j('/api/runs/'+id+'/graph');renderRunGraph(g);}catch(e){$('run-dag').textContent='graph failed: '+e;}
 try{const v=await j('/api/runs/'+id+'/validation');renderRunClaims(v);}catch(e){const c=$('run-claims');if(c)c.innerHTML=`<span class="warn">validation failed: ${escH(e)}</span>`;}
};
const buildIntelRows=m=>{
 const h=(m&&m.heuristic_investigation)||{};
 return Object.keys(h).map(s=>{const p=h[s]||{},ev=p.evidence||{};
  return {service:s,project:p.project||'',requests:p.requests??'?',tokens:p.total_tokens??'?',
   models:Object.keys(p.models||{}),templates:(ev.templates||[]).length,
   instructions:(ev.instructions||[]).length,heads:(ev.sample_heads||[]).length};});
};
const renderRunPanes=d=>{
 const rows=buildIntelRows(d);
 const el=$('run-intel');
 if(el)el.innerHTML=rows.length?`<table><thead><tr><th>service</th><th>reqs</th><th>tokens</th><th>models</th><th>templates</th><th>instructions</th><th>sample heads</th></tr></thead><tbody>${rows.map(r=>`<tr><td><code>${escH(r.service)}</code><br><span class="mut">${escH(r.project)}</span></td><td>${escH(r.requests)}</td><td>${escH(r.tokens)}</td><td class="mut">${r.models.map(escH).join('<br>')||'—'}</td><td>${escH(r.templates)}</td><td>${escH(r.instructions)}</td><td>${escH(r.heads)}</td></tr>`).join('')}</tbody></table>`:'<span class="mut">no heuristic data</span>';
 renderRunLogs(d);
 renderRunVerdict(d);
};
const agentLogBlock=(title,payload,meta)=>{
 const body=payload==null?'<span class="mut">—</span>'
  :typeof payload==='string'?`<pre>${escH(payload.slice(0,3000))}</pre>`
  :`<pre>${escH(JSON.stringify(payload,null,1).slice(0,3000))}</pre>`;
 return `<details class="card coll"><summary><b>${escH(title)}</b>${meta?` <span class="mut">${escH(meta)}</span>`:''}<span class=chev>›</span></summary><div class=coll-body>${body}</div></details>`;
};
const renderRunLogs=d=>{
 const el=$('run-logs');if(!el)return;
 const a=(d&&d.agents)||{};
 const profs=a.profilers||{},crits=a.critics||{};
 let html=agentLogBlock('scout',a.scout&&(a.scout.content||a.scout.parsed||a.scout),
  a.scout?`${((a.scout.prompt_tokens||0)+(a.scout.completion_tokens||0))} tok · ${((a.scout.ms||0)/1000).toFixed(1)}s`:'');
 for(const s of Object.keys(profs))html+=agentLogBlock('profiler:'+s,profs[s].parsed||profs[s].content||profs[s],
  `${((profs[s].prompt_tokens||0)+(profs[s].completion_tokens||0))} tok`);
 for(const s of Object.keys(crits))html+=agentLogBlock('critic:'+s,crits[s].content||crits[s],
  crits[s].ms?`${(crits[s].ms/1000).toFixed(1)}s`:'');
 const rep=a.reporter||{};
 html+=agentLogBlock('reporter',rep.content||rep,'brief');
 el.innerHTML=html||'<span class="mut">no agent output recorded</span>';
};
const renderRunClaims=v=>{
 const el=$('run-claims');if(!el)return;
 const s=v.summary||{},svcs=v.services||{};
 const unproven=Object.keys(svcs).filter(k=>!svcs[k].proven);
 let html=`<div class="mut">proven ${escH(s.proven??'?')}/${escH(s.n_services??'?')} · contested ${escH(s.contested??0)}</div>`;
 html+=unproven.map(k=>`<div class="ev-block"><b>${escH(k)}</b> — unproven<span class="ev-src">${escH(((svcs[k]||{}).issues||[]).join('; ').slice(0,220))}</span></div>`).join('');
 html+=(v.brief_issues||[]).map(b=>`<div class="ev-block"><b>brief</b><span class="ev-src">${escH(String(b).slice(0,220))}</span></div>`).join('');
 el.innerHTML=html;
};
const renderRunVerdict=d=>{
 const el=$('rp-verdict');if(!el)return;
 const s=d.security;
 if(!s){el.innerHTML='<span class="mut">no security scan recorded for this run</span>';return;}
 const tot=s.totals||{};
 el.innerHTML=`<div class="kpis">`
  +`<div class="stat"><div class="v">${escH(s.risk_rating||'?')}</div><div class="k">risk rating</div></div>`
  +`<div class="stat"><div class="v">${escH(s.n_findings??'?')}</div><div class="k">findings</div></div>`
  +`</div><div class="mut">severity mix: `
  +['critical','high','medium','low'].map(k=>`${k} ${tot[k]||0}`).join(' · ')
  +` — <a href="#security">open the Security tab</a> for evidence and remediation</div>`;
};
const switchRunSub=v=>{
 document.querySelectorAll('[data-rs]').forEach(b=>b.classList.toggle('on',b.dataset.rs===v));
 ['intel','logs','findings','scores','verdict'].forEach(k=>{const p=$('rp-'+k);if(p)p.style.display=k===v?'':'none';});
};
const renderRunGraph=g=>{
 graphCache=g;
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
  svg+=`<g><rect x=${p.x} y=${p.y} width=${BW} height=${BH} rx=6 fill="#161b22" stroke="${ecol(n.status)}" stroke-width="1.5"><title>${escH(n.id)} · ${escH(n.ms)}ms</title></rect><text x=${p.x+8} y=${p.y+17} fill="#e6edf3" font-size="11">${escH(n.label)}</text><text x=${p.x+8} y=${p.y+33} fill="#8b949e" font-size="10">${escH(n.sub)}</text></g>`;}));
 $('run-dag').innerHTML=svg+'</svg>';
 const mx=Math.max(...g.nodes.map(n=>n.prompt_tokens+n.completion_tokens),1);
 $('run-cost').innerHTML=g.nodes.slice().sort((a,b)=>(b.prompt_tokens+b.completion_tokens)-(a.prompt_tokens+a.completion_tokens)).map(n=>{const t=n.prompt_tokens+n.completion_tokens;
  return `<div class="row" style="margin:3px 0"><code style="min-width:200px">${escH(n.id)}</code><div style="flex:1;background:#00000040;border-radius:4px"><div style="width:${(100*t/mx).toFixed(1)}%;background:#1f6feb;border-radius:4px">&nbsp;</div></div><span class="mut">${escH(t)} tok · ${escH((n.ms/1000).toFixed(1))}s</span></div>`;}).join('');
 const badge=a=>a==='match'?'<span class=ok>match</span>':a==='partial'?'<span class=warn>partial</span>':a==='disagree'?'<span style="color:#f85149">disagree</span>':'<span class=mut>?</span>';
 $('t-conf').querySelector('tbody').innerHTML=g.services.map(s=>{const c=s.confidence;
  const bar=c==null?'<span class="mut">—</span>':`<div style="background:#00000040;border-radius:4px;min-width:110px"><div style="width:${(c*100).toFixed(0)}%;background:#3fb950;border-radius:4px">&nbsp;</div></div> ${escH(c.toFixed(2))}`;
  return `<tr data-f='${escA(JSON.stringify(s))}'><td><code>${escH(s.service)}</code></td><td>${bar}</td><td class="mut">${escH(s.heuristic_project||'')}</td><td>${escH(s.llm_project||'')}<br><span class="mut">${escH((s.what_building||'').slice(0,130))}</span></td><td>${badge(s.agreement)}</td></tr>`;}).join('');
 const withGaps=g.services.filter(s=>(s.critic_gaps||[]).length);
 $('run-gaps').innerHTML=withGaps.length?withGaps.map(s=>`<div style="margin:6px 0"><b>${escH(s.service)}</b>${s.critic_gaps.map(q=>`<div class="mut">• ${escH(q)}</div>`).join('')}</div>`).join(''):'<span class="mut">no critic gaps — quick mode skips the critic stage</span>';
 $('run-quotes').innerHTML=g.services.map(s=>((s.evidence_quotes||[]).length?`<div style="margin:6px 0"><b>${escH(s.service)}</b>${s.evidence_quotes.map(q=>`<div class="mut">&ldquo;${escH(q.slice(0,160))}&rdquo;</div>`).join('')}</div>`:'')).join('')||'<span class="mut">no quotes recorded</span>';
};
const drawTopo=g=>{
 const el=$('topo');if(!el)return;
 const nodes=g.nodes||[];
 if(!nodes.length){el.className='mut';el.textContent='no topology data';return;}
 el.className='';
 const order=['machine','project','service','container','model'];
 const cols=order.map(L=>nodes.filter(n=>n.layer===L).slice(0,12));
 const shown=cols.reduce((a,c)=>a+c.length,0);
 const hidden=nodes.length-shown;
 const BW=168,BH=40,GX=42,GY=12,pad=14;
 const rows=Math.max(1,...cols.map(c=>c.length));
 const W=pad*2+cols.length*BW+(cols.length-1)*GX, H=pad*2+rows*(BH+GY)+18;
 const pos={};
 cols.forEach((col,ci)=>col.forEach((n,ri)=>{pos[n.id]={x:pad+ci*(BW+GX),y:pad+18+ri*(BH+GY)};}));
 const ecol=e=>e.kind==='calls'?'#1f6feb':e.kind==='gossip'?'#a371f7':e.kind==='observed_via'?'#21262d':'#30363d';
 const ncol=n=>n.layer==='machine'?(n.online===false?'#d29922':'#3fb950'):n.layer==='model'&&n.idle?'#8b949e':n.status&&n.status!=='running'&&n.status!=='?'?'#d29922':'#58a6ff';
 const sub=n=>n.layer==='machine'?`${n.hw||'?'} · ${n.llm_1h??0}/h`:n.layer==='service'?'llm traffic':n.layer==='model'?(n.idle?'pool, idle':'in use'):n.status||n.image||'';
 let svg=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px">`;
 order.forEach((L,ci)=>{if(!cols[ci].length)return;svg+=`<text x=${pad+ci*(BW+GX)} y=${pad+8} fill="#8b949e" font-size="10">${L}</text>`;});
 (g.edges||[]).forEach(e=>{const a=pos[e.from],b=pos[e.to];if(!a||!b)return;
  const lbl=e.kind==='calls'&&e.count?` ×${e.count}`:'';
  svg+=`<line x1=${a.x+BW} y1=${a.y+BH/2} x2=${b.x} y2=${b.y+BH/2} stroke="${ecol(e)}" stroke-width="${e.kind==='calls'?2:1.2}"><title>${escH(e.kind)}${escH(lbl)}</title></line>`;});
 cols.forEach(col=>col.forEach(n=>{const p=pos[n.id];const lab=n.label.length>22?n.label.slice(0,21)+'…':n.label;
  svg+=`<g><rect x=${p.x} y=${p.y} width=${BW} height=${BH} rx=6 fill="#161b22" stroke="${ncol(n)}" stroke-width="1.5"><title>${escH(n.id)}</title></rect><text x=${p.x+8} y=${p.y+16} fill="#e6edf3" font-size="11">${escH(lab)}</text><text x=${p.x+8} y=${p.y+31} fill="#8b949e" font-size="10">${escH(sub(n))}</text></g>`;}));
 svg+='</svg>';
 if(hidden>0)svg+=`<div class="mut">+${hidden} more nodes (capped at 12 per layer)</div>`;
 if((g.summary&&g.summary.errors||[]).length)svg+=`<div class="warn">partial: ${g.summary.errors.map(escH).join(', ')} unreachable</div>`;
 el.innerHTML=svg;
};
const SEV_CLS=s=>s==='critical'?'crit':s==='high'?'warn':s==='medium'?'':'mut';
const pill=s=>`<span class="pill ${SEV_CLS(s)}">${escH(s)}</span>`;
let findCache=null;
function renderFindings(d){
 findCache=d;
 const sum=d.summary||{};
 const s=$('find-sum');
 if(s)s.textContent=`${sum.total||0} findings`;
 const bars=$('find-bars');
 if(bars){const by=sum.by_severity||{},mx=Math.max(1,...Object.values(by));
  bars.innerHTML=['critical','high','medium','low'].map(k=>{const v=by[k]||0;
   return `<div class="row" style="margin:3px 0"><code style="min-width:70px">${k}</code><div style="flex:1;background:#00000040;border-radius:4px"><div class="${SEV_CLS(k)}" style="width:${(100*v/mx).toFixed(1)}%;background:currentColor;border-radius:4px">&nbsp;</div></div><span class="mut">${v}</span></div>`;}).join('');}
 renderFindRows();
}
function renderFindRows(){
 const tb=$('t-find')&&$('t-find').querySelector('tbody');if(!tb)return;
 const area=$('sel-find')&&$('sel-find').value;
 const rows=(findCache&&findCache.findings||[]).filter(f=>!area||f.area===area).slice(0,150);
  tb.innerHTML=rows.map(f=>{const lk=f.ref&&f.ref.startsWith('ledger:')?` <a href="#ledger" data-ledger-run="${escA(f.ref.slice(7))}">ledger</a>`:'';
   return `<tr data-f='${escA(JSON.stringify(f))}'><td>${pill(f.severity)}</td><td class="mut">${escH(f.area)}</td><td>${escH(f.title)}${lk}</td><td class="mut">${escH(f.detail||'')}</td></tr>`;}).join('')||trowState(4,'no findings — quiet mesh');
 wireTable('#t-find',null);
 tb.querySelectorAll('[data-ledger-run]').forEach(a=>a.onclick=e=>{e.preventDefault();activateTab('ledger');loadLedger(a.dataset.ledgerRun);});
}
async function loadFindings(){
 const el=$('find-bars');if(el){el.className='mut loading';el.textContent='loading…';}
 try{renderFindings(await j('/api/findings'));}catch(e){if(el){el.className='warn';el.textContent='findings failed: '+e;}}
}
const DIR_CLS=d=>d==='in'?'':'ok';
function renderChain(d){
 chainCache=(d.events||[]);
 const sum=d.summary||{};
 const s=$('chain-sum');
 if(s)s.textContent=`${sum.n||0} events · ${sum.chains||0} linked chains · ${sum.orphans||0} orphan completions (${sum.live||0} live + ${sum.history||0} history)`;
 const el=$('chain');if(!el)return;
 el.className='';
 el.innerHTML=(d.events||[]).slice().reverse().map(e=>{
  const t=new Date((e.t||0)*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  const q=e.queue_ms!=null?` · queue ${escH(e.queue_ms)}ms`:'';
  const ch=e.chain?` <span class="pill">chain ${escH(e.chain)}</span>`:'';
  return `<div class="ev" data-f='${escA(JSON.stringify({t:e.t,dir:e.dir,service:e.service,model:e.model,prompt_head:e.prompt_head,prompt_tokens:e.prompt_tokens,completion_tokens:e.completion_tokens,duration_ms:e.duration_ms,queue_ms:e.queue_ms,status:e.status,chain:e.chain,seq:e.seq}))}'><span class="dot ${DIR_CLS(e.dir)}"></span><div><div><span class="mut">${t}</span> <b>${escH(e.dir.toUpperCase())}</b> <code>${escH(e.service)}</code> <span class="mut">${escH(e.model||'')}</span>${ch}</div><div class="mut">${escH(e.prompt_head||'')} · ${escH(e.prompt_tokens||0)}+${escH(e.completion_tokens||0)} tok${q} · ${escH(e.status||'')}</div></div></div>`;}).join('')||'<span class="mut">no events</span>';
}
async function loadChain(){
 const el=$('chain');if(el){el.className='mut loading';el.textContent='loading…';}
 try{
  const sel=$('sel-chain');
  if(sel&&!sel.dataset.filled){const sv=await j('/api/services');sel.innerHTML='<option value="">all</option>'+sv.services.map(x=>`<option value="${escA(x.service)}">${escH(x.service)}</option>`).join('');sel.dataset.filled='1';}
  const svc=sel&&sel.value?`&service=${encodeURIComponent(sel.value)}`:'';
  const n=($('sel-chain-n')&&$('sel-chain-n').value)||100;
  renderChain(await j(`/api/chain?limit=${n}${svc}`));
 }catch(e){if(el){el.className='warn';el.textContent='chain failed: '+e;}}
}
function drawKnowledge(g){
 const el=$('kg');if(!el)return;
 const nodes=g.nodes||[];
 if(!nodes.length){el.className='mut';el.textContent='no knowledge data';return;}
 el.className='';
 const order=['service','template','model','finding','evidence'];
 const cols=order.map(L=>nodes.filter(n=>n.layer===L).slice(0,12));
 const BW=168,BH=40,GX=42,GY=12,pad=14;
 const rows=Math.max(1,...cols.map(c=>c.length));
 const W=pad*2+cols.length*BW+(cols.length-1)*GX, H=pad*2+rows*(BH+GY)+18;
 const pos={};
 cols.forEach((col,ci)=>col.forEach((n,ri)=>{pos[n.id]={x:pad+ci*(BW+GX),y:pad+18+ri*(BH+GY)};}));
 const ecol=e=>e.kind==='flagged'?'#f85149':e.kind==='calls'?'#1f6feb':e.kind==='reconstructed_as'?'#3fb950':'#30363d';
 const ncol=n=>n.layer==='finding'?((n.severity==='critical'||n.severity==='high')?'#f85149':n.severity==='medium'?'#d29922':'#8b949e'):n.layer==='template'?'#a371f7':'#58a6ff';
 const sub=n=>n.layer==='service'?`${n.requests||0} reqs`:n.layer==='model'?'model':n.layer==='finding'?`${escH(n.severity||'')}`:(n.count?`×${n.count}`:'');
 let svg=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px">`;
 order.forEach((L,ci)=>{if(!cols[ci].length)return;svg+=`<text x=${pad+ci*(BW+GX)} y=${pad+8} fill="#8b949e" font-size="10">${L}</text>`;});
 (g.edges||[]).forEach(e=>{const a=pos[e.from],b=pos[e.to];if(!a||!b)return;
  svg+=`<line x1=${a.x+BW} y1=${a.y+BH/2} x2=${b.x} y2=${b.y+BH/2} stroke="${ecol(e)}" stroke-width="1.2"><title>${escH(e.kind)}</title></line>`;});
 cols.forEach(col=>col.forEach(n=>{const p=pos[n.id];const lab=n.label.length>22?n.label.slice(0,21)+'…':n.label;
  svg+=`<g><rect x=${p.x} y=${p.y} width=${BW} height=${BH} rx=6 fill="#161b22" stroke="${ncol(n)}" stroke-width="1.5"><title>${escH(n.id)}</title></rect><text x=${p.x+8} y=${p.y+16} fill="#e6edf3" font-size="11">${escH(lab)}</text><text x=${p.x+8} y=${p.y+31} fill="#8b949e" font-size="10">${sub(n)}</text></g>`;}));
 svg+='</svg>';
 el.innerHTML=svg;
 const s=$('kg-sum'),sum=g.summary||{};
 if(s)s.textContent=`${sum.nodes||0} entities · ${sum.edges||0} links · ${sum.shared_templates||0} shared templates`;
}
async function loadKnowledge(){
 const el=$('kg');if(el){el.className='mut loading';el.textContent='loading…';}
 try{drawKnowledge(await j('/api/knowledge'));}catch(e){if(el){el.className='warn';el.textContent='graph failed: '+e;}}
}
const filterLedger=(entries,q)=>{const f=(q||'').toLowerCase().trim();if(!f)return entries;return entries.filter(e=>`${e.task_id||''} ${e.actor||''} ${e.action||''}`.toLowerCase().includes(f));};
let ledgerCache=[];
function renderLedgerRows(){
 const tb=$('t-ledger')&&$('t-ledger').querySelector('tbody');if(!tb)return;
 const q=$('filt-ledger')&&$('filt-ledger').value;
 const rows=filterLedger(ledgerCache,q).slice(-200);
 tb.innerHTML=rows.map(e=>`<tr data-f='${escA(JSON.stringify(e))}'><td class="mut">${escH(e.seq)}</td><td><code>${escH(e.actor)}</code></td><td>${escH(e.action)}</td><td class="mut">${escH(e.task_id||'—')}</td><td class="mut"><code>${escH((e.artifact_sha256||'').slice(0,12))}</code></td></tr>`).join('')||trowState(5,'no matching entries');
}
async function loadLedger(preset){
 const tb=$('t-ledger')&&$('t-ledger').querySelector('tbody');
 const v=$('ledger-verdict');
 try{
  const sel=$('sel-ledger');
  if(sel&&!sel.dataset.filled){const r=await j('/api/swarm/runs');sel.innerHTML=(r.runs||[]).map(x=>`<option value="${escA(x.run_id)}">${escH(x.run_id)}</option>`).join('')||'<option value="">no runs</option>';sel.dataset.filled='1';}
  if(preset&&sel){const has=[...(sel.options||[])].some(o=>o.value===preset);
   if(!has){const o=document.createElement('option');o.value=o.textContent=preset;if(sel.prepend)sel.prepend(o);else sel.appendChild(o);}
   sel.value=preset;}
  const rid=sel&&sel.value;
  if(!rid){if(tb)tb.innerHTML=trowState(5,'no ledger runs yet');return;}
  const [d,ver]=await Promise.all([j('/api/swarm/ledger?run_id='+encodeURIComponent(rid)),j('/api/swarm/verify?run_id='+encodeURIComponent(rid))]);
  if(v){v.textContent=ver.ok?`chain OK — ${ver.checked} entries`:`BROKEN at seq ${ver.failed_at} (${ver.reason})`;v.className=ver.ok?'ok':'warn';}
  ledgerCache=d.entries||[];
  renderLedgerRows();
 }catch(e){if(v){v.textContent='ledger failed: '+e;v.className='warn';}}
 try{const q=await j('/api/swarm/queue');const qs=$('queue-sum');if(qs)qs.textContent=`${q.pending||0} pending · ${q.claimed||0} claimed · ${q.done||0} done · ${q.failed||0} failed`;
  const qt=$('t-queue')&&$('t-queue').querySelector('tbody');
  if(qt)qt.innerHTML=['pending','claimed','done','failed'].map(k=>`<tr><td>${k}</td><td>${q[k]||0}</td></tr>`).join('');
 }catch(e){}
}
function drawSimCurve(curves){
 const el=$('sim-curve');if(!el)return;
 const fields=Object.keys(curves||{});
 if(!fields.length){el.className='mut';el.textContent='no curve data';return;}
 el.className='';
 const W=640,H=180,padL=44,padR=10,padT=10,padB=24,bh=H-padT-padB;
 const cols=['#58a6ff','#3fb950','#d29922','#a371f7','#f85149'];
 let g='';
 [0,0.5,1].forEach(v=>{const y=padT+bh*(1-v);g+=`<line x1=${padL} y1=${y} x2=${W-padR} y2=${y} stroke="#30363d"/><text class=ax x=${padL-6} y=${y+3} text-anchor="end">${v}</text>`;});
 fields.forEach((f,fi)=>{
  const pts=(curves[f]||[]).map((p,i,a)=>`${(padL+i*(W-padL-padR)/Math.max(1,a.length-1)).toFixed(1)},${(padT+bh*(1-(p.accuracy||0))).toFixed(1)}`).join(' ');
  g+=`<polyline points="${pts}" fill="none" stroke="${cols[fi%cols.length]}" stroke-width="2"><title>${escH(f)}</title></polyline>`;
 });
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:680px">${g}</svg><div class="mut">${fields.map((f,fi)=>`<span class=k><span class=sw style="background:${cols[fi%cols.length]}"></span>${escH(f)}</span>`).join('')}</div>`;
}
async function loadSimUsers(){
 const sel=$('sel-sim');if(!sel)return;
 try{const d=await j('/api/sim/users');sel.innerHTML=(d.users||[]).map(u=>`<option value="${escA(u.user_id)}">${escH(u.user_id)} (${escH(u.pairs)} pairs)</option>`).join('')||'<option value="">no users — load demo or run sim/run.py</option>';
  const s=$('sim-sum');if(s)s.textContent=`backend: ${(d.backend||'?')}`;
  const dlp=await j('/api/sim/dlp').catch(()=>null);
  const ds=$('sim-dlp-sum'),dd=$('sel-sim-dlp');
  if(dlp&&ds)ds.textContent=`${dlp.mode}: ${dlp.interceptions||0} interceptions`;
  if(dlp&&dd)dd.value=dlp.mode;}catch(e){const s=$('sim-sum');if(s)s.textContent='sim failed: '+e;}
}
async function loadSimReport(){
 const sel=$('sel-sim'),uid=sel&&sel.value;
 const fc=$('sim-fields');
 if(!uid){if(fc)fc.innerHTML='<span class="mut">pick a user</span>';return;}
 try{const r=await j('/api/sim/report?user_id='+encodeURIComponent(uid));
  drawSimCurve(r.curves||{});
  if(fc)fc.innerHTML=`<div class="mut">${escH(r.recovered)}/${escH(r.n_fields)} fields recovered · mean accuracy ${escH(r.mean_accuracy)} · ${escH(r.clusters)} clusters</div>`+Object.entries(r.fields||{}).map(([f,v])=>`<div>${pill(v.recovered?'high':'low')} <code>${escH(f)}</code> <span class="mut">${escH(v.accuracy)} (${escH(v.matched)}/${escH(v.total)} chars)${v.recovered?' — RECOVERED':''}${v.direct_exposure?' · in log verbatim':''}</span></div>`).join('')
   +((r.reconstructed||[]).length?`<div class="mut" style="margin-top:6px">reconstructed values (carrier-independent assembly):</div>`+(r.reconstructed||[]).slice(0,6).map(s=>`<div><code>${escH(s.assembled)}</code> <span class="mut">coverage ${escH(s.coverage)} · ${escH(s.occurrences)} occurrences</span></div>`).join(''):'');
  const ee=$('sim-est');
  if(ee){const est=r.estimates||{};ee.innerHTML=`<div class="mut">exposure estimate (no ground truth): <b>${escH(est.exposure??'?')}</b> across ${escH(est.n_groups??0)} candidate groups</div>`;}
 }catch(e){if(fc)fc.textContent='report failed: '+e;}
}
function initTheme(){
 const root=document.documentElement;
 const apply=t=>{root.dataset.theme=t;try{localStorage.setItem('if-theme',t);}catch(_){}
  const b=$('b-theme');if(b)b.textContent=t==='light'?'◑':'◐';};
 let saved='dark';
 try{saved=localStorage.getItem('if-theme')||'dark';}catch(_){}
 apply(saved);
 const b=$('b-theme');if(b)b.onclick=()=>apply(root.dataset.theme==='light'?'dark':'light');
 return apply;
}
const toggleTheme=()=>initTheme()(document.documentElement.dataset.theme==='light'?'dark':'light');
const loadTrend=async()=>{try{const t=await j('/api/runs-compare?limit=5');
 trendCache=t;
 $('t-trend').querySelector('tbody').innerHTML=t.services.map(s=>`<tr data-f='${escA(JSON.stringify({service:s,cols:t.cols.map(c=>({run_id:c.run_id,quick:!!c.quick,confidence:c.confidence[s]??null}))}))}'><td><code>${escH(s)}</code></td><td>${t.cols.map(c=>{const v=c.confidence[s];return `<span title="${escA(c.run_id)}${c.quick?' (quick)':''}" style="display:inline-block;min-width:52px;margin-right:6px;padding:2px 6px;border-radius:4px;background:${v==null?'#21262d':'#1f6feb'};font-size:12px">${v==null?'—':escH(v.toFixed(2))}</span>`;}).join('')}</td></tr>`).join('');
}catch(e){$('t-trend').querySelector('tbody').innerHTML=`<tr><td class="warn">trend failed: ${escH(e)}</td></tr>`;}};
const safeHref=u=>/^(https?:|mailto:|#|\/)/i.test(String(u).trim())?String(u).trim():'#';
const inlineMd=s=>escH(s).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\[([^\]]+)\]\(([^)]+)\)/g,(m,txt,href)=>`<a href="${escA(safeHref(href))}">${txt}</a>`);
const renderMarkdown=md=>{
 const lines=String(md).split('\n');
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
   else{const src=buf.join('\n');fence=false;
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
 const fail=(n,e)=>{try{console.error('mermaid failed:',e);}catch(_){}
  const d=document.createElement('div');d.className='warn';
  d.textContent='diagram failed to render: '+((e&&e.message)||e||'parse error')+' — source kept below';
  n.replaceWith(d);};
 const run=async()=>{try{window.mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'dark',themeVariables:{darkMode:true,background:'#0a0e14',primaryColor:'#1f6feb',primaryTextColor:'#e6edf3',lineColor:'#8b949e',textColor:'#e6edf3'}});}catch(e){}
  for(const n of nodes){try{await window.mermaid.run({nodes:[n],suppressErrors:false});}catch(e){fail(n,e);}}};
 if(window.mermaid&&window.mermaid.run){try{await run();return;}catch(e){}}
 for(const src of MERMAID_SRC){
  try{
   await new Promise((res,rej)=>{if(document.querySelector(`script[data-mm="${src}"]`))return res();const s=document.createElement('script');s.dataset.mm=src;s.src=src;s.onload=res;s.onerror=rej;document.head.appendChild(s);});
   if(window.mermaid&&window.mermaid.run){await run();return;}
  }catch(e){}
 }
};
/* ---- generic table sort/filter/export ---- */
const cellText=(tr,i)=>{const td=tr.children[i];return td?td.textContent.trim():'';};
const sortTable=(table,col,dir)=>{const tb=table.tBodies[0];const rows=[...tb.rows].filter(r=>!r.querySelector('td[colspan]'));
 rows.sort((a,b)=>{const x=cellText(a,col),y=cellText(b,col);const nx=parseFloat(x.replace(/[^\d.\-]/g,'')),ny=parseFloat(y.replace(/[^\d.\-]/g,''));const both=!isNaN(nx)&&!isNaN(ny)&&/\d/.test(x)&&/\d/.test(y);const c=both?nx-ny:x.localeCompare(y);return dir<0?-c:c;});
 rows.forEach(r=>tb.appendChild(r));};
const enhanceTable=table=>{if(!table||table.dataset.enh)return;table.dataset.enh='1';
 table.querySelectorAll('thead th').forEach((th,i)=>{th.style.cursor='pointer';th.title='click to sort';th.addEventListener('click',()=>{const dir=(th.dataset.dir==='asc')?-1:1;th.dataset.dir=dir===1?'asc':'desc';table.querySelectorAll('thead th').forEach(o=>{if(o!==th)delete o.dataset.dir;});sortTable(table,i,dir);});});};
const filterTable=(table,q)=>{const f=q.toLowerCase();[...table.tBodies[0].rows].forEach(r=>{const t=r.textContent.toLowerCase();r.style.display=(!f||t.includes(f))?'':'none';});};
const exportTable=(table,name,fmt)=>{const head=[...table.tHead.rows[0].cells].map(c=>c.textContent.trim());const body=[...table.tBodies[0].rows].filter(r=>r.style.display!=='none').map(r=>[...r.cells].map(c=>c.textContent.trim()));let blob,ext;if(fmt==='json'){blob=new Blob([JSON.stringify(body.map(r=>Object.fromEntries(r.map((v,i)=>[head[i]||('col'+i),v]))),null,2)],{type:'application/json'});ext='json';}else{const q=v=>'"'+String(v).replace(/"/g,'""')+'"';blob=new Blob([[head,...body].map(r=>r.map(q).join(',')).join('\n')],{type:'text/csv'});ext='csv';}const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${name}.${ext}`;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},0);};
const wireTable=(tableId,filterId)=>{const t=$(tableId);if(t)enhanceTable(t);const f=$(filterId);if(f&&t)f.addEventListener('input',()=>filterTable(t,f.value));};
document.querySelectorAll('[data-x]').forEach(b=>b.addEventListener('click',()=>exportTable($(b.dataset.x),b.dataset.name,b.dataset.name.endsWith('JSON')?'json':'csv')));
/* ---- evidence preview + download ---- */
const showEvidence=async(name,size)=>{$('ev-name').textContent=name;$('ev-dl').href=`/api/evidence/file?name=${encodeURIComponent(name)}&download=1`;$('ev-view').textContent='loading\u2026';
 try{const d=await j('/api/evidence/file?name='+encodeURIComponent(name));$('ev-view').textContent=d.binary?'(binary file \u2014 use Download)':(d.text+(d.truncated?'\n\n\u2026 truncated \u2026':''));$('ev-info').textContent=`${(d.size/1024).toFixed(1)} KB${d.truncated?' \u00b7 truncated':''}`;}catch(e){$('ev-view').textContent='preview failed: '+e;}};
const loadDesignRail=async()=>{try{const idx=await j('/api/design/docs');
 const groups={};idx.docs.forEach(d=>{(groups[d.group]=groups[d.group]||[]).push(d);});
 $('design-rail').innerHTML=Object.entries(groups).map(([g,ds])=>`<div class="mut" style="margin:6px 0 2px">${escH(g)}</div>${ds.map(d=>`<div><a href="#" data-doc="${escA(d.id)}">${escH(d.title)}</a> <span class="mut">${d.available?escH(d.diagrams)+' diagrams':'—'}</span></div>`).join('')}`).join('');
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
const liveEmpty='<tr><td class="mut" colspan=5>no events yet — waiting for traffic</td></tr>';
const liveRow=e=>`<tr data-f='${escA(JSON.stringify({t:e.t,dir:e.dir,service:e.service,model:e.model,prompt_head:e.prompt_head,prompt_tokens:e.prompt_tokens,completion_tokens:e.completion_tokens,duration_ms:e.duration_ms,queue_ms:e.queue_ms,status:e.status,seq:e.seq,query_type:e.query_type}))}'><td class="mut">${escH(liveTime(e.t))}</td><td>${liveDir(e.dir)}</td><td><code>${escH(e.service)}</code></td><td class="mut">${escH((e.model||'').split(':')[0])}</td><td class="mut">${escH((e.prompt_head||'').slice(0,120))}${e.queue_ms!=null?` <span class="mut">· queued ${escH(Math.round(e.queue_ms))}ms</span>`:''} <span class="mut">· ${escH((e.prompt_tokens||0)+(e.completion_tokens||0))} tok</span></td></tr>`;
let feedCache=[];
const feedDirFilter=()=>($('sel-feed-dir')&&$('sel-feed-dir').value)||'';
const filterFeed=(evs,q)=>{const f=(q||'').toLowerCase().trim();if(!f)return evs;return evs.filter(e=>(e.dir||'').toLowerCase()===f);};
function renderFeedRows(){
 const tb=liveTbody();if(!tb)return;
 const rows=filterFeed(feedCache,feedDirFilter()).slice(0,120);
 tb.innerHTML=rows.map(liveRow).join('')||liveEmpty;
 const c=$('feed-count');if(c)c.textContent=`${rows.length} shown · ${feedCache.length} buffered`;
}
const renderFeed=evs=>{
 if(evs&&evs.length){
  const seen=new Set(feedCache.map(e=>e.seq));
  for(const e of evs)if(e.seq==null||!seen.has(e.seq)){feedCache.push(e);if(e.seq!=null)seen.add(e.seq);}
  feedCache.sort((a,b)=>(b.seq||0)-(a.seq||0));
  feedCache=feedCache.slice(0,500);
 }
 renderFeedRows();
};
const switchLiveSub=v=>{
 document.querySelectorAll('[data-ls]').forEach(b=>b.classList.toggle('on',b.dataset.ls===v));
 ['feed','traffic','recon'].forEach(k=>{const p=$('lp-'+k);if(p)p.style.display=k===v?'':'none';});
};
let liveES=null, liveLastSeq=0;
const liveTbody=()=>$('t-feed').querySelector('tbody');
function startLiveStream(){if(liveES||!window.EventSource)return;liveES=new EventSource(`/api/live/stream?since_id=${liveLastSeq}`);liveES.onmessage=ev=>{let e;try{e=JSON.parse(ev.data)}catch(_){return}if(!e.seq||e.seq<=liveLastSeq)return;liveLastSeq=e.seq;renderFeed([e]);};liveES.onerror=()=>{if(liveES){liveES.close();liveES=null;}};}
function stopLiveStream(){if(liveES){liveES.close();liveES=null;}}

const tip=$('tip');
const showTip=(html,ev)=>{if(!tip)return;tip.innerHTML=html;tip.style.display='block';const p=12;tip.style.left=Math.min(ev.clientX+p,innerWidth-tip.offsetWidth-8)+'px';tip.style.top=Math.min(ev.clientY+p,innerHeight-tip.offsetHeight-8)+'px';};
const hideTip=()=>{if(tip)tip.style.display='none';};
const fmtN=n=>n>=1e6?(n/1e6).toFixed(1)+'M':n>=1000?(n/1000).toFixed(1)+'k':''+n;

let tsCache=null;
const TSCOL=['#1f6feb','#58a6ff','#3fb950','#d29922','#f778ba','#a371f7','#e6edf3','#8b949e'];
const spark=(vals,w=100,h=16)=>{if(!vals||!vals.length)return'';const mx=Math.max(1,...vals),mn=Math.min(...vals);const sx=i=>i*(w/(Math.max(1,vals.length-1)));const sy=v=>h-2-((v-mn)/((mx-mn)||1))*(h-4);return `<svg class=spark viewBox="0 0 ${w} ${h}" width=${w} height=${h}><polyline points="${vals.map((v,i)=>sx(i)+','+sy(v)).join(' ')}"/></svg>`;};
const tsMergedModels=()=>{const m={};for(const b of (tsCache&&tsCache.buckets)||[])for(const[k,v]of Object.entries(b.models||{}))m[k]=(m[k]||0)+v;return Object.entries(m).sort((a,b)=>b[1]-a[1]);};
function drawModelMix(){
 const el=$('ts-models');if(!el)return;const ms=tsMergedModels(),tot=ms.reduce((s,x)=>s+x[1],0);
 if(!tot){el.textContent='model mix: no data in window';return;}
 const top=ms.slice(0,6),other=ms.slice(6).reduce((s,x)=>s+x[1],0);let bar='',leg='';
 top.forEach(([m,c],i)=>{bar+=`<span style="width:${(c/tot*100).toFixed(2)}%;background:${TSCOL[i]}"></span>`;leg+=`<span class=k><span class=sw style="background:${TSCOL[i]}"></span>${escH(m)} ${Math.round(c/tot*100)}%</span>`;});
 if(other){bar+=`<span style="width:${(other/tot*100).toFixed(2)}%;background:${TSCOL[7]}"></span>`;leg+=`<span class=k><span class=sw style="background:${TSCOL[7]}"></span>other ${Math.round(other/tot*100)}%</span>`;}
 el.innerHTML=`<div class=mixbar>${bar}</div><div class=mut style="font-size:12px;margin-top:3px">${leg}</div>`;
}
function drawHeatmap(){
 const el=$('ts-heatmap');if(!el)return;const bs=(tsCache&&tsCache.buckets)||[];
 const svcs={};
 for(const b of bs)for(const[k,v]of Object.entries(b.services||{})){const o=svcs[k]||(svcs[k]={total:0,byT:{}});o.total+=v.req;o.byT[b.t]=v.req;}
 const names=Object.keys(svcs).sort((a,b)=>svcs[b].total-svcs[a].total).slice(0,8);
 if(!names.length||!bs.length){el.textContent='heatmap: no services in window';return;}
 const max=Math.max(1,...names.map(n=>Math.max(0,...Object.values(svcs[n].byT))));
 const row=t=>{let r='';for(const b of bs){const v=svcs[t].byT[b.t]||0;r+=`<span class=cell data-t="${b.t}" data-s="${escA(t)}" data-v="${v}" data-a="${(v/max).toFixed(3)}"></span>`;}return `<div class=hrow><span class=hlabel title="${escA(t)}">${escH(t)}</span><div class=cells>${r}</div></div>`;};
 el.innerHTML=`<div class=mut style="font-size:12px;margin-top:8px">service × time heatmap (brighter = more requests)</div>${names.map(row).join('')}`;
 el.querySelectorAll('.cell').forEach(c=>{const a=+c.dataset.a;c.style.background=`rgba(31,111,235,${(0.06+0.94*a).toFixed(2)})`;c.addEventListener('mousemove',ev=>showTip(`${new Date(+c.dataset.t*1000).toLocaleString()}\n${c.dataset.s}\nrequests  ${c.dataset.v}`,ev));c.addEventListener('mouseleave',hideTip);});
}
function drawTsChart(){
 const el=$('ts-chart');if(!el)return;
 const bs=(tsCache&&tsCache.buckets)||[];
 if(!bs.length){el.className='mut';el.textContent='no data in window';$('ts-legend').textContent='';return;}
 el.className='';el.innerHTML='';
 $('ts-legend').innerHTML='<span class=k><span class=sw style="background:#1f6feb"></span>requests</span><span class=k><span class=sw style="background:#58a6ff"></span>total tokens</span><span class=k><span class=sw style="background:#a371f7"></span>p95 ms</span><span class=k>req trend '+spark(bs.map(b=>b.req||0))+'</span>';
 const W=el.clientWidth||900,H=200,padL=48,padR=14,padT=14,padB=26;
 const maxR=Math.max(1,...bs.map(b=>b.req||0)),maxT=Math.max(1,...bs.map(b=>b.total_tokens||0));
 const bw=(W-padL-padR)/bs.length,bh=H-padT-padB;
 const yT=v=>padT+bh-(v/maxT)*bh;
 const maxLat=()=>Math.max(1,...bs.map(b=>b.p95_ms||0));
 let g='';
 for(let i=0;i<=2;i++){const v=maxR*i/2,y=padT+bh-(i/2)*bh;g+=`<line x1=${padL} y1=${y} x2=${W-padR} y2=${y} stroke="#30363d" stroke-width="1"/><text class=ax x=${padL-6} y=${y+3} text-anchor="end">${fmtN(Math.round(v))}</text>`;}
 bs.forEach((b,i)=>{const x0=padL+i*bw,gap=Math.max(1,bw*0.18),y=padT+bh-((b.req||0)/maxR)*bh;
  g+=`<rect class=bar x=${x0+gap} y=${y} width=${Math.max(1,bw-2*gap)} height=${Math.max(0,padT+bh-y)} rx=2></rect>`;
  const t=new Date(b.t*1000).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});
  if(bs.length<=14||i%Math.ceil(bs.length/10)===0)g+=`<text class=ax x=${x0+bw/2} y=${H-8} text-anchor="middle">${t}</text>`;});
 const xc=i=>padL+i*bw+bw/2;
 g+=`<polyline class=ln points="${bs.map((b,i)=>xc(i)+','+yT(b.total_tokens||0)).join(' ')}"/>`;
 g+=`<polyline class=ln p95 points="${bs.map((b,i)=>xc(i)+','+(padT+bh-((b.p95_ms||0)/Math.max(1,Math.max(...bs.map(x=>x.p95_ms||0))))*bh)).join(' ')}"/>`;
 bs.forEach((b,i)=>g+=`<rect class=hit data-i=${i} x=${padL+i*bw} y=${padT} width=${bw} height=${H-padT-padB}></rect>`);
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" width=${W} height=${H}>${g}</svg>`;
 el.querySelectorAll('.hit').forEach(h=>{const b=bs[+h.dataset.i];h.addEventListener('mousemove',ev=>showTip(`${new Date(b.t*1000).toLocaleString()}\nrequests  ${b.req}\ntokens    ${b.total_tokens}\np50/p95   ${b.p50_ms||0} / ${b.p95_ms||0} ms\nerrors    ${b.errors||0}`,ev));h.addEventListener('mouseleave',hideTip);});
}
function loadTs(){
 const el=$('ts-chart');if(!el)return;
 const b=$('sel-tsbucket').value,w=$('sel-tswindow').value;
 j(`/api/stats/timeseries?bucket=${encodeURIComponent(b)}&window=${encodeURIComponent(w)}&source=auto`).then(r=>{tsCache=r;const t=r.totals||{};
  $('ts-msg').textContent=`${t.req||0} req · ${t.total_tokens||0} tok · source ${r.source}`;drawTsChart();drawModelMix();drawHeatmap();})
 .catch(e=>{el.className='mut';el.textContent='failed: '+e;});
}
['sel-tsbucket','sel-tswindow'].forEach(id=>{const e=$(id);if(e)e.onchange=loadTs;});
let tsRz;addEventListener('resize',()=>{clearTimeout(tsRz);tsRz=setTimeout(drawTsChart,150);});
/* ---- security advisor tab (D6) ---- */
const SEC_CLS=s=>(s==='critical'||s==='high')?'warn':(s==='medium'?'':'mut');
function renderSecurity(resp){
 const r=resp.report||{},st=resp.stored;
 $('sec-msg').textContent=`scan (${r.scope||'app'}): ${r.n_findings||0} findings, risk ${r.risk_rating||'low'}`;
 const tot=r.totals||{};
 $('sec-stats').innerHTML=['critical','high','medium','low'].map(k=>`<div class="card stat"><div class="v ${SEC_CLS(k)}">${tot[k]||0}</div><div class="k">${k}</div></div>`).join('');
 const flag=f=>[(f.likely_fixture?'fixture?':null),(f.kind==='world_readable_secret'?'exposed!':null)].filter(Boolean).join(' ');
 $('t-sec-secrets').querySelector('tbody').innerHTML=(r.secrets||[]).slice(0,200).map(f=>`<tr data-f='${escA(JSON.stringify(f))}'><td>${escH(f.kind)}</td><td class="${SEC_CLS(f.severity)}">${escH(f.severity)}</td><td class=mut>${escH(f.source)}:${escH(f.line)}</td><td><code>${escH(f.match)}</code></td><td class=mut>${escH(flag(f))}</td></tr>`).join('')||trowState(5,'no secret/PII survivors','ok');
 $('sec-inject').innerHTML=(r.injections||[]).slice(0,200).map(f=>`<tr data-f='${escA(JSON.stringify(f))}'><td>${escH(f.kind)}</td><td class="${SEC_CLS(f.severity)}">${escH(f.severity)}</td><td class=mut>${escH(f.source)}:${escH(f.line)}</td><td><code>${escH(f.snippet||f.match)}</code></td></tr>`).join('')||trowState(4,'no injection patterns','ok');
 $('sec-perm').innerHTML=(r.permissions||[]).slice(0,200).map(f=>`<tr data-f='${escA(JSON.stringify(f))}'><td>${escH(f.source)}</td><td class="${SEC_CLS(f.severity)}">${escH(f.mode)}</td><td>${escH(f.severity)}</td></tr>`).join('')||trowState(3,'no permission issues');
 const tr=r.tracked_evidence||{};
 $('sec-tracked').textContent=(st&&st.assessment&&st.assessment.risk_rating)?`LLM assessment: ${st.assessment.risk_rating}`:'';
 $('sec-stored').innerHTML=st?`<div class=mut>last scan ${new Date((st.generated_at||0)*1000).toLocaleString()} — ${escH((st.assessment||{}).summary||'(no LLM summary)')}</div>`:'<span class=mut>no stored security.json yet</span>';
 wireTable('#t-sec-secrets',null);
 const pt=$('t-sec-proj')&&$('t-sec-proj').querySelector('tbody');
 if(pt)pt.innerHTML=(r.projects||[]).slice(0,30).map(p=>`<tr data-f='${escA(JSON.stringify(p))}'><td><code>${escH(p.project)}</code></td><td class="${SEC_CLS('critical')}">${escH(p.critical)}</td><td>${escH(p.high)}</td><td>${escH(p.medium)}</td><td class=mut>${escH(p.low)}</td><td><b>${escH(p.total)}</b></td></tr>`).join('')||trowState(6,'no project breakdown');
 secCache=r;
 renderSecView();
}
const SEV_HEX={critical:'#f85149',high:'#d29922',medium:'#a371f7',low:'#8b949e'};
function secAnalyticsHTML(r){
 r=r||{};
 const tot=r.totals||{};
 const all=[...(r.secrets||[]),...(r.injections||[]),...(r.permissions||[])];
 const byKind={};
 all.forEach(f=>{const k=f.kind||'?';byKind[k]=(byKind[k]||0)+1;});
 const topKinds=Object.entries(byKind).sort((a,b)=>b[1]-a[1]).slice(0,8);
 const mxK=Math.max(1,...topKinds.map(([,v])=>v));
 const bars=topKinds.map(([k,v])=>`<div class="row" style="margin:3px 0"><code style="min-width:190px">${escH(k)}</code><div style="flex:1;background:#00000040;border-radius:4px"><div style="width:${(100*v/mxK).toFixed(1)}%;background:#1f6feb;border-radius:4px">&nbsp;</div></div><span class="mut">${v}</span></div>`).join('')||'<span class="mut">no findings</span>';
 const sevRows=['critical','high','medium','low'].map(k=>{const v=tot[k]||0;
  return `<div class="row" style="margin:3px 0"><code style="min-width:70px">${k}</code><div style="flex:1;background:#00000040;border-radius:4px"><div style="width:${(100*v/Math.max(1,tot.critical||0,tot.high||0,tot.medium||0,tot.low||0)).toFixed(1)}%;background:${SEV_HEX[k]};border-radius:4px">&nbsp;</div></div><span class="mut">${v}</span></div>`;}).join('');
 const esc1=all.filter(f=>f.kind==='world_readable_secret').length;
 const fix=all.filter(f=>f.likely_fixture).length;
 const files=new Set(all.map(f=>f.source)).size;
 const projs=(r.projects||[]).slice(0,8);
 const mxP=Math.max(1,...projs.map(p=>p.total));
 const projRows=projs.map(p=>`<div class="row" style="margin:3px 0"><code style="min-width:190px">${escH(p.project)}</code><div style="flex:1;background:#00000040;border-radius:4px"><div style="width:${(100*p.total/mxP).toFixed(1)}%;background:#a371f7;border-radius:4px">&nbsp;</div></div><span class="mut">${p.total} (c${p.critical}/h${p.high})</span></div>`).join('');
 return `<div class=card><h3>Spotlight</h3><div class="grid stats">`
  +`<div class="card stat"><div class="v crit">${esc1}</div><div class="k">world-readable secrets</div></div>`
  +`<div class="card stat"><div class="v mut">${fix}</div><div class="k">likely fixtures</div></div>`
  +`<div class="card stat"><div class="v">${files}</div><div class="k">files with hits</div></div>`
  +`<div class="card stat"><div class="v">${(r.injections||[]).length}</div><div class="k">injection patterns</div></div>`
  +`</div></div><div class=card><h3>By severity</h3>${sevRows}</div>`
  +`<div class=card><h3>Top finding kinds</h3>${bars}</div>`
  +(projs.length?`<div class=card><h3>Top projects</h3>${projRows}</div>`:'');
}
let secView='table',secCache=null;
function renderSecView(){
 const an=$('sec-analytics'),tb=$('sec-tables');
 const showAn=secView==='analytics';
 if(an){an.style.display=showAn?'':'none';if(showAn)an.innerHTML=secAnalyticsHTML(secCache);}
 if(tb)tb.style.display=showAn?'none':'';
}
const TRUST_CLS=s=>(s==='fail'?'warn':(s==='warn'?'':'ok'));
function renderTrust(resp){
 trustCache=resp;
 const rules=resp.rules||[],sum=resp.summary||{};
 const s=$('sec-trust-sum');
 if(s)s.textContent=`${sum.pass||0} pass · ${sum.warn||0} warn · ${sum.fail||0} fail`;
 const tb=$('t-sec-trust')&&$('t-sec-trust').querySelector('tbody');
 if(!tb)return;
 tb.innerHTML=rules.map(r=>`<tr data-f='${escA(JSON.stringify(r))}'><td><b>${escH(r.rule)}</b></td><td class="${TRUST_CLS(r.status)}">${escH(r.status)}</td><td class=mut>${escH(r.severity)}</td><td>${escH(r.detail)}</td></tr>`).join('')||trowState(4,'no assertions');
 wireTable('#t-sec-trust',null);
}
function renderRisk(resp){
 riskCache=resp;
 const rows=resp.services||[],sum=resp.summary||{};
 const s=$('sec-risk-sum');
 if(s)s.textContent=`${sum.n_services||0} services · worst ${escH(sum.worst||'low')}`;
 const tb=$('t-sec-risk')&&$('t-sec-risk').querySelector('tbody');
 if(!tb)return;
 tb.innerHTML=rows.map(r=>{const g=r.signals||{};return `<tr data-f='${escA(JSON.stringify({service:r.service,band:r.band,score:r.score,n:r.n,signals:g}))}'><td>${escH(r.service)}</td><td class="${SEC_CLS(r.band)}">${escH(r.band)}</td><td>${r.score}</td><td class=mut>${r.n}</td><td>${g.pii||0}</td><td>${g.injection||0}</td><td>${g.cross_service_reuse||0}</td></tr>`;}).join('')||trowState(7,'no requests yet');
 wireTable('#t-sec-risk',null);
}
function loadSecurity(){
 const scope=($('sel-secscope')&&$('sel-secscope').value)||'app';
 $('sec-msg').textContent='loading…';
 j('/api/security?scope='+encodeURIComponent(scope)).then(renderSecurity).catch(e=>{$('sec-msg').textContent='security failed: '+e;});
 j('/api/trust').then(renderTrust).catch(()=>{});
 j('/api/risk').then(renderRisk).catch(()=>{});
}
function secScan(){
 $('sec-msg').textContent='scanning (deterministic + LLM)…';
 const scope=($('sel-secscope')&&$('sel-secscope').value)||'app';
 pj('/api/security/scan',{scope}).then(()=>{loadSecurity();showNotif('security scan complete','ok');}).catch(e=>{$('sec-msg').textContent='scan failed: '+e;showNotif('security scan failed','err');});
}
const loadLive=async()=>{
 let st={running:false};
 try{st=await j('/api/live/status');}catch(e){$('live-state').textContent='status failed: '+e;return;}
  const stateCls=st.possible_loss?'warn':(st.stale?'warn':'ok');
 const bits=[`live · ${st.events_buffered} events · ${st.polls} polls · up ${st.uptime_s||0}s`,
   `out ${st.out_seen||0} seen / ${st.out_lost||0} lost`];
 if(st.persisted&&st.persisted.files)bits.push(`${st.persisted.files} log day(s) · ${Math.round((st.persisted.bytes||0)/1024)}KB on disk`);
 if(st.stale)bits.push('stale '+(st.poll_age_s||'?')+'s since poll');
  if(st.possible_loss)bits.push('⚠ page overflow, older completions missed');
  (st.alerts||[]).slice(-3).forEach(a=>bits.push(`⚠ ${a.kind}${a.service?' '+a.service:''}: ${a.detail}`));
  const qx=[];
  if(st.inflight_pending!=null)qx.push(`queue ${st.inflight_pending} in flight · ${st.queue_joined||0} joined`);
  if(st.webhooks&&st.webhooks.configured)qx.push(`webhooks ${st.webhooks.configured} · last ${st.webhooks.last?(st.webhooks.last.ok?'ok':'FAILED'): 'never fired'}`);
  const qe=$('live-extra');if(qe)qe.innerHTML=qx.map(b=>`<span class="mut">${escH(b)}</span>`).join(' · ')||'';
  if(st.running){$('live-state').innerHTML=`<span class="${stateCls}">● ${escH(bits[0])}</span>`+bits.slice(1).map(b=>' · <span class="mut">'+escH(b)+'</span>').join('');}
  else{$('live-state').textContent='○ stopped';}
  if(!st.running){stopLiveStream();}
  if(!st.running)return;
  try{const f=await j('/api/live/feed?limit=40');
   feedCache=(f.events||[]).slice(0,500);
   renderFeedRows();
   liveLastSeq=f.last_seq||liveLastSeq;
   startLiveStream();
  }catch(e){}
  try{const r=await j('/api/live/rates?window_s=300');
  ratesCache=r.services||[];
  $('t-rates').querySelector('tbody').innerHTML=r.services.map(s=>`<tr data-f='${escA(JSON.stringify(s))}'><td><code>${escH(s.service)}</code></td><td>${escH(s.req)}</td><td>${escH(s.tokens)}</td><td>${escH(s.req_per_min)}</td><td>${escH(s.tok_per_min)}</td></tr>`).join('')||'<tr><td class="mut" colspan=5>no completed requests in window</td></tr>';
 }catch(e){}
 try{const sv=await j('/api/services');
  const cur=$('sel-live').value;
  $('sel-live').innerHTML=sv.services.map(s=>`<option value="${escA(s.service)}">${escH(s.service)}</option>`).join('');
  if(cur)$('sel-live').value=cur;
 }catch(e){}
};
$('b-live-start').onclick=async()=>{const i=+$('inp-live-int').value||5;try{await pj('/api/live/start',{interval_s:i});showNotif('tap started','ok');}catch(e){showNotif('tap start failed','err');}loadLive();};
$('b-live-stop').onclick=async()=>{try{await pj('/api/live/stop');showNotif('tap stopped','ok');}catch(e){showNotif('tap stop failed','err');}loadLive();};
const _sfd=$('sel-feed-dir');if(_sfd)_sfd.onchange=renderFeedRows;
document.querySelectorAll('[data-ls]').forEach(b=>b.addEventListener('click',()=>switchLiveSub(b.dataset.ls)));
$('b-live-recon').onclick=async()=>{const s=$('sel-live').value;if(!s)return;const mode=$('sel-lmode').value;$('live-recon-msg').textContent='reconstructing…';
 try{
  try{const st=await j('/api/live/status');if(!st.running)await pj('/api/live/start');}catch(e){}
  const d=await j(`/api/live/reconstruction?service=${encodeURIComponent(s)}&n=5&mode=${mode}&history=200`);
  $('live-recon-msg').textContent=`${d.steps.length} steps (${d.history_rows} history + ${d.live_rows} live), converged=${d.converged}`;
   $('t-liveprog').querySelector('tbody').innerHTML=d.steps.map(st=>{const dl=st.delta||{};
    return `<tr data-f='${escA(JSON.stringify(st))}'><td>${escH(st.step)}</td><td>${scoreCell(st.score.score,st.score.grade)}</td><td>${escH(st.requests)}</td><td><b>${escH(st.project||'')}</b></td><td>${dl.project_changed?'<span class="warn">flip</span>':'<span class="ok">stable</span>'}</td></tr>`;}).join('');
  loadLive();
 }catch(e){$('live-recon-msg').textContent='failed: '+e;}};
setInterval(()=>{const s=$('s-live');if(s&&s.classList.contains('on')){loadLive();const a=$('chk-tsauto');if(a&&a.checked)loadTs();}},4000);
const loadReports=async()=>{
 try{
  const d=await j('/api/reports'),rl=$('report-list');if(!rl)return;
  rl.innerHTML=(d.reports||[]).slice(0,5).map(r=>`<div><b>${escH(r.id)}</b> · risk ${escH(r.risk||'?')} · ${escH(r.n_findings??'?')} findings · ${escH(r.n_services??'?')} svcs · <a href="/api/evidence/file?name=${encodeURIComponent('reports/'+r.id+'/report.html')}&download=1">html</a> · <a href="/api/evidence/file?name=${encodeURIComponent('reports/'+r.id+'/report.md')}">md</a></div>`).join('')||'<span class=mut>no reports yet</span>';
 }catch(e){const rl=$('report-list');if(rl)rl.textContent='reports failed: '+e;}
};
$('b-inv').onclick=async()=>{$('runmsg').textContent='investigating…';try{const r=await pj('/api/investigate');$('runmsg').textContent=r.report||JSON.stringify(r);showNotif('heuristic investigation complete','ok');load();}catch(e){$('runmsg').textContent='failed: '+e;showNotif('investigation failed','err');}};
$('b-report').onclick=async()=>{$('runmsg').textContent='generating unified report…';try{const r=await pj('/api/reports/run');const d=r.diff||{};$('runmsg').textContent=`report ${r.id} (db-changed=${d.db_changed??'?'}${(d.services_added||[]).length?' +'+d.services_added.join(','):''}) — see Reports below`;showNotif('unified report '+r.id,'ok');loadReports();}catch(e){$('runmsg').textContent='report failed: '+e;showNotif('report failed','err');}};
$('b-agent').onclick=async()=>{$('runmsg').textContent='launching…';const q=$('opt-quick').checked;try{const r=await pj('/api/runs',{quick:q});if(r.detail){$('runmsg').textContent=r.detail+' — wait for a run to finish';showNotif(r.detail,'warn');}else{$('runmsg').textContent='run '+JSON.stringify(r)+' — refresh Agentic tab in a few min';showNotif('agentic run launched','ok');}}catch(e){$('runmsg').textContent='launch failed: '+e;showNotif('launch failed','err');}};
const _sb=$('b-sec-scan');if(_sb)_sb.onclick=secScan;
document.querySelectorAll('[data-rs]').forEach(b=>b.addEventListener('click',()=>switchRunSub(b.dataset.rs)));
const _ss=$('sel-secscope');if(_ss)_ss.onchange=loadSecurity;
const _sv=$('sel-secview');if(_sv)_sv.onchange=()=>{secView=_sv.value;renderSecView();};
const _sf=$('sel-find');if(_sf)_sf.onchange=renderFindRows;
const _bc=$('b-chain');if(_bc)_bc.onclick=loadChain;
const _bl=$('b-ledger');if(_bl)_bl.onclick=()=>loadLedger();
const _fl=$('filt-ledger');if(_fl)_fl.oninput=renderLedgerRows;
const _sd=$('b-sim-demo');if(_sd)_sd.onclick=async()=>{try{await pj('/api/sim/demo');loadSimUsers();}catch(e){const s=$('sim-sum');if(s)s.textContent='demo failed: '+e;}};
const _sr=$('b-sim-reset');if(_sr)_sr.onclick=async()=>{try{await pj('/api/sim/reset');loadSimUsers();const fc=$('sim-fields');if(fc)fc.innerHTML='';const c=$('sim-curve');if(c){c.className='mut';c.textContent='pick a user…';}}catch(e){}};
const _sp=$('b-sim-report');if(_sp)_sp.onclick=loadSimReport;
const _sdos=$('b-sim-dos');if(_sdos)_sdos.onclick=loadSimDossier;
const _sr2=$('b-sim-run');if(_sr2)_sr2.onclick=runSim;
async function runSim(){
 const m=$('sim-runmsg'),o=$('sim-runout');
 if(m)m.textContent='running…';
 try{
  const body={scenario:($('sel-sim-sc')&&$('sel-sim-sc').value)||'all',
   style:($('sel-sim-style')&&$('sel-sim-style').value)||'regular',
   dlp_mode:($('sel-sim-dlp')&&$('sel-sim-dlp').value)||'off'};
  const d=await pj('/api/sim/run',body);
  const rows=Object.entries(d.results||{}).map(([k,v])=>v.error?`<div>${escH(k)}: <span class="warn">${escH(v.error)}</span></div>`:`<div>${escH(k)}: <b>${escH(v.report.recovered)}/${escH(v.report.n_fields)} recovered</b> <span class="mut">mean ${escH(v.report.mean_accuracy)} · ${escH(v.n_turns)} turns</span></div>`).join('');
  if(o)o.innerHTML=rows||'<span class="mut">nothing ran</span>';
  if(m)m.textContent='done';
  showNotif('simulation batch complete','ok');
  const sel=$('sel-sim');if(sel)sel.dataset.filled='';
  loadSimUsers();loadSimRuns(d.run_id);
 }catch(e){if(m)m.textContent='run failed: '+e;showNotif('simulation failed','err');}
}
async function loadSimRuns(preset){
 const sel=$('sel-sim-run');if(!sel)return;
 try{const d=await j('/api/sim/runs');
  sel.innerHTML=(d.runs||[]).map(r=>`<option value="${escA(r)}">${escH(r)}</option>`).join('')||'<option value="">no runs yet</option>';
  if(preset)sel.value=preset;
 }catch(e){const m=$('sim-dosmsg');if(m)m.textContent='runs failed: '+e;}
}
async function loadSimDossier(){
 const sel=$('sel-sim-run'),rid=sel&&sel.value;
 const dm=$('sim-dosmsg'),df=$('sim-dos-find'),dd=$('sim-dos-doc'),dt=$('sim-dos-tl');
 if(!rid){if(dm)dm.textContent='pick a run';return;}
 try{
  const d=await j('/api/sim/dossier?run_id='+encodeURIComponent(rid));
  if(dm)dm.textContent=`${d.findings.length} findings · chain ${d.ledger.ok?'OK':'BROKEN'}`;
  const md=$('sim-dos-md');if(md)md.href='/api/sim/dossier.md?run_id='+encodeURIComponent(rid);
  if(df)df.innerHTML=(d.findings||[]).map(f=>`<div>${pill(f.band)} <code>${escH(f.field)}</code> <span class="mut">${escH(f.scenario)} · ${escH(f.accuracy)}${f.direct_exposure?' · in log verbatim':''}</span><div class="mut">${escH(f.reconstructed||'')}</div></div>`).join('')||'<span class="mut">no findings</span>';
  if(dd)dd.innerHTML='';// full markdown available via the markdown link (keeps the tab fast)
  if(dt)dt.innerHTML=`<h3>Ledger timeline</h3>`+(d.timeline||[]).map(e=>`<div class="ev"><span class="dot"></span><div><div><span class="mut">#${escH(e.seq)}</span> <code>${escH(e.actor)}</code> ${escH(e.action)} <span class="mut">${escH(e.task_id)}</span></div>${e.detail?`<div class="mut">${escH(e.detail)}</div>`:''}</div></div>`).join('')||'<span class="mut">no entries</span>';
 }catch(e){if(dm)dm.textContent='dossier failed: '+e;}
}
async function loadSimScenarios(){
 const el=$('sim-scenarios');if(!el)return;
 try{const d=await j('/api/sim/scenarios');
  el.innerHTML=(d.scenarios||[]).map(s=>`<div class=card><h3>${escH(s.title)} <span class="mut" style="font-weight:normal">${escH(s.id)}</span></h3><div>${escH(s.blurb)}</div><div class="mut">fields: ${(s.fields||[]).map(escH).join(', ')}</div><div class=diagram-wrap><pre class=mermaid>${escH(s.diagram)}</pre></div></div>`).join('')||'<span class="mut">no scenarios</span>';
  renderMermaid(el);
 }catch(e){el.textContent='scenarios failed: '+e;}
}
const _sd2=$('sel-sim-dlp');if(_sd2)_sd2.onchange=async()=>{try{await pj('/api/sim/dlp',{mode:_sd2.value});loadSimUsers();}catch(e){const s=$('sim-sum');if(s)s.textContent='dlp failed: '+e;}};
/* ---- AKM shell: toasts, service overlay (append-only; all data paths intact) ---- */
let svcCache=[];
let notifTimer=0;
function showNotif(msg,kind){
 const n=$('notif');if(!n)return;
 n.textContent=msg;n.className='notif show '+(kind||'');
 clearTimeout(notifTimer);notifTimer=setTimeout(()=>{n.className='notif';},4200);
}
function svcDetailHTML(s){
 if(!s)return '<span class="mut">unknown service</span>';
 const models=Object.entries(s.models||{}).map(([m,c])=>`<div class="row" style="margin:2px 0"><code style="min-width:170px">${escH(m)}</code><span class="mut">×${escH(c)}</span></div>`).join('')||'<span class="mut">—</span>';
 const pipe=(s.pipeline||[]).map(escH).join(' → ')||'<span class="mut">—</span>';
 return `<h2><code>${escH(s.service)}</code></h2>`
  +`<div class="mut">${escH(s.project||'')}</div>`
  +`<div class="kpis">`
  +`<div class="stat"><div class="v">${escH(s.requests??'?')}</div><div class="k">requests</div></div>`
  +`<div class="stat"><div class="v">${escH(s.total_tokens??'?')}</div><div class="k">tokens</div></div>`
  +`<div class="stat"><div class="v">${escH((s.score&&s.score.score)??s.score??'?')}</div><div class="k">score ${escH(s.grade||'')}</div></div>`
  +`</div><h3>Models</h3>${models}<h3>Pipeline</h3><div>${pipe}</div>`
  +(s.pipeline_summary?`<h3>Summary</h3><div class="mut">${escH(s.pipeline_summary)}</div>`:'')
  +(s.vibe?`<div class="mut" style="margin-top:6px">vibe: ${escH(s.vibe)} ${escH(s.vibe_label||'')}</div>`:'');
}
function openSvcOverlay(name){
 const s=(svcCache||[]).find(x=>x.service===name);
 const ov=$('overlay'),bd=$('overlay-body');if(!ov||!bd)return;
 bd.innerHTML=svcDetailHTML(s||null);
 ov.classList.add('show');
}
function closeOverlay(){const ov=$('overlay');if(ov)ov.classList.remove('show');}
const _ov=$('overlay');if(_ov)_ov.addEventListener('click',e=>{if(e.target===_ov)closeOverlay();});
window.addEventListener('keydown',e=>{if(e.key==='Escape')closeOverlay();});
function openSvcOverlayByEvent(e){const r=e.target&&e.target.closest?e.target.closest('[data-svc]'):null;if(r)openSvcOverlay(r.dataset.svc);}
const _svcT=$('t-svc');if(_svcT)_svcT.addEventListener('click',openSvcOverlayByEvent);
/* ---- universal row overlays: every table explains itself (AKM overlay pattern) ---- */
let meshCache=[],riskCache=null,trustCache=null,chainCache=[],ratesCache=[],trendCache=null,graphCache=null;
const SCORE_HELP={
 severity:{critical:'live credential or key material — rotate and revoke now',
  high:'sensitive data or broad exposure — fix this week',
  medium:'hardening gap — schedule it',low:'informational, no action needed'},
 band:{critical:'score ≥ 75 — highest inflow risk',high:'score 50–75 — elevated',
  medium:'score 25–50 — moderate',low:'score below 25 — quiet'},
 trust:{pass:'assertion holds on current code/config',
  warn:'holds with a caveat — read the detail',fail:'boundary violated — fix now'},
 agreement:{match:'heuristic and LLM labels agree',partial:'labels overlap partly',
  disagree:'labels contradict — one of them is wrong',unknown:'not enough signal either way'},
 grade:{A:'score ≥ 80 — strong reconstruction evidence',B:'score 65–80 — solid',
  C:'score 50–65 — thin',D:'below 50 — weak evidence'},
 vibe:{'pure vibe':'one model, copy-pasted prompts, no visible engineering',
  'hybrid':'mix of prompt reuse and structure','engineered system':'many templates, multi-model, staged pipeline'},
 queue_ms:'measured queue wait: OUT completion time minus its IN arrival (fox records no queue time, the tap joins the two events)',
 coverage:'fraction of secret slots filled by at least one fragment (1.0 = fully reassembled)',
 pii:'prompts matching secret/PII patterns that should have been masked upstream',
 injection:'prompts matching override/reveal/role-hijack phrasing',
 vol_z:'max prompt-token z-score vs the whole corpus — spikes mean anomalous volume',
 reuse:'prompts also seen (exact or near-dup) from another service — a leaked template',
 confidence:'LLM self-reported 0–1, not a measurement — weigh against agreement',
};
const sevPill=s=>`<span class="pill ${s==='critical'?'crit':s==='high'?'warn':s==='medium'?'':'mut'}">${escH(s||'?')}</span>`;
function showDetail(title,sub,rows,notes){
 const bd=$('overlay-body'),ov=$('overlay');if(!bd||!ov)return;
 bd.innerHTML=`<h2>${escH(title)}</h2>`+(sub?`<div class="mut">${escH(sub)}</div>`:'')
  +`<table><tbody>${(rows||[]).map(([k,v])=>`<tr><td class="mut" style="white-space:nowrap">${escH(k)}</td><td>${v}</td></tr>`).join('')}</tbody></table>`
  +((notes||[]).filter(Boolean).map(n=>`<div class="ev-block"><div>${escH(n)}</div></div>`).join(''));
 ov.classList.add('show');
}
const detailFindings=f=>{const where=f.where||(((f.source||'')+(f.line?':'+f.line:''))||'—');
 const evidence=f.match||f.snippet||((f.area==='risk'||f.area==='claims'||f.area==='fidelity'||f.area==='alert')?(f.detail||'—'):'—');
 const rows=[['severity',sevPill(f.severity)+' '+escH(SCORE_HELP.severity[f.severity]||'')],
  ['where',escH(where)],['evidence',`<code>${escH(evidence)}</code>`]];
 if(f.remediation)rows.push(['remediation',escH(f.remediation)]);
 if(f.status||f.likely_fixture)rows.push(['status',escH(f.status||'open')+(f.likely_fixture?' · likely fixture (test/docs path)':'')]);
 return {title:(f.kind||'finding'),sub:((f.area||'')+' finding'),
  rows,notes:[f.area==='risk'?'Risk bands score inflow danger: '+Object.entries({critical:75,high:50,medium:25}).map(([k,v])=>k+' ≥ '+v).join(', '):'']};};
const detailLedger=e=>({title:'ledger #'+(e.seq??'?'),sub:(e.actor||'')+' · '+(e.action||''),
 rows:[['actor',`<code>${escH(e.actor||'')}</code>`],['action',escH(e.action||'')],
  ['task',`<code>${escH(e.task_id||'—')}</code>`],
  ['artifact sha',`<code>${escH(e.artifact_sha256||'—')}</code>`],
  ['detail',escH(e.detail||'—')]],
 notes:['Each entry hashes the previous one: editing, deleting or reordering any entry breaks verification at exactly that sequence.']});
const detailMesh=p=>{const h=p.health||{};
 return {title:(p.machine||p.node_id||'peer'),sub:'mesh peer'+(p.online?'':' (offline)'),
 rows:[['online',String(!!p.online)],['hardware',escH((p.hardware||{}).kind||'?')],
  ['llm req/1h',escH(h.llm_requests_1h??'?')],
  ['services',(h.services||[]).map(s=>`<div>${escH(s.name)} <span class="mut">${escH(s.status||'')} · ${escH(s.running??'?')}/${escH(s.total??'?')} up</span></div>`).join('')||'<span class="mut">none reported</span>']],
 notes:['Peers arrive via fox gossip reads only — this app never probes or executes on them (trust boundary T2).']};};
const detailRisk=r=>{const g=r.signals||{};
 return {title:'risk: '+(r.service||'?'),sub:'inflow risk '+r.score+' / 100',
 rows:[['band',sevPill(r.band)+' '+escH(SCORE_HELP.band[r.band]||'')],['score',escH(r.score)],
  ['prompts',escH(r.n)],['PII hits',`${escH(g.pii||0)} — ${SCORE_HELP.pii}`],
  ['injections',`${escH(g.injection||0)} — ${SCORE_HELP.injection}`],
  ['volume z',`${escH(g.volume_z??0)} — ${SCORE_HELP.vol_z}`],
  ['cross-service reuse',`${escH(g.cross_service_reuse||0)} — ${SCORE_HELP.reuse}`]],notes:[]};};
const detailTrust=r=>({title:'boundary '+r.rule,sub:'status: '+r.status,
 rows:[['status',escH(r.status)+' — '+escH(SCORE_HELP.trust[r.status]||'')],
  ['severity',escH(r.severity||'')],['detail',escH(r.detail||'')],
  ['evidence',(r.evidence||[]).map(e=>`<div><code>${escH(e)}</code></div>`).join('')||'—']],notes:[]});
const detailRates=s=>({title:'rates: '+(s.service||'?'),sub:'live window rates',
 rows:[['requests',escH(s.req)],['tokens',escH(s.tokens)],
  ['req/min',escH(s.req_per_min)+' — requests ÷ window minutes'],
  ['tok/min',escH(s.tok_per_min)+' — tokens ÷ window minutes']],
 notes:['Computed over the rolling live window from completed (OUT) events only.']});
const detailConf=s=>({title:'scores: '+(s.service||'?'),sub:'profiler confidence vs heuristic',
 rows:[['confidence',`${escH(s.confidence==null?'—':s.confidence)} — ${escH(SCORE_HELP.confidence)}`],
  ['agreement',`${escH(s.agreement||'?')} — ${escH(SCORE_HELP.agreement[s.agreement]||'')}`],
  ['heuristic',escH(s.heuristic_project||'—')],['LLM',escH(s.llm_project||'—')],
  ['what building',escH((s.what_building||'').slice(0,300))],
  ['critic gaps',((s.critic_gaps||[]).join('; ')||'none').slice(0,400)],
  ['evidence quotes',String((s.evidence_quotes||[]).length)+' cited prompt lines']],
 notes:[]});
const detailTrend=d=>({title:'trend: '+(d.service||'?'),sub:'profiler confidence per run, newest first',
 rows:[['runs',(d.cols||[]).map(c=>`<div><code>${escH(c.run_id)}</code>${c.quick?' (quick)':''}: <b>${c.confidence==null?'—':escH(c.confidence.toFixed(2))}</b></div>`).join('')||'—']],
 notes:['Each cell is one run LLM self-reported confidence for this service.']});
const detailChain=e=>({title:(e.dir||'').toUpperCase()+' · '+(e.service||'?'),sub:new Date((e.t||0)*1000).toLocaleString(),
 rows:[['model',escH(e.model||'?')],['prompt',escH(e.prompt_head||'—')],
  ['tokens',`${escH(e.prompt_tokens||0)} + ${escH(e.completion_tokens||0)}`],
  ['queue wait',e.queue_ms!=null?escH(e.queue_ms)+'ms — '+SCORE_HELP.queue_ms:'— (no IN arrival seen)'],
  ['status',escH(e.status||'—')],['chain',e.chain?('linked IN→OUT #'+e.chain):'orphan (no qid link)']],
 notes:[]});
const detailFeed=e=>({title:(e.dir||'').toUpperCase()+' · '+(e.service||'?'),sub:new Date((e.t||0)*1000).toLocaleString(),
 rows:[['model',escH(e.model||'?')],['type',escH(e.query_type||'—')],
  ['prompt',escH(e.prompt_head||'—')],
  ['tokens',`${escH(e.prompt_tokens||0)} + ${escH(e.completion_tokens||0)}`],
  ['queue wait',e.queue_ms!=null?escH(e.queue_ms)+'ms — '+SCORE_HELP.queue_ms:'—'],
  ['status',escH(e.status||'—')],['seq',escH(e.seq??'—')]],notes:[]});
const detailProj=p=>({title:'project '+p.project,sub:p.total+' findings',
 rows:[['critical',p.critical],['high',p.high],['medium',p.medium],['low',p.low]],
 notes:['Rolled up from every finding whose source path starts with this top-level directory.']});
const detailProgStep=st=>{const dl=st.delta||{},sc=st.score||{},vb=st.vibe||{};
 const factors=sc.factors?Object.entries(sc.factors).map(([k,v])=>`${k} ${v}`).join(' · '):'';
 const vfactors=vb.factors?Object.entries(vb.factors).map(([k,v])=>`${k} ${v}`).join(' · '):'';
 return {title:'progression step '+st.step,sub:(st.mode||'')+' · '+(st.window||''),
 rows:[['requests',escH(st.requests)],['tokens',escH(st.tokens)],
  ['project',`<b>${escH(st.project||'')}</b> ${dl.project_changed?'<span class="warn">label flip</span>':'<span class="ok">stable</span>'}`],
  ['score',`${escH(sc.score??'?')} (${escH(sc.grade||'?')}) — ${escH(SCORE_HELP.grade[sc.grade]||'')}${factors?' — '+escH(factors):''}`],
  ['vibe',`${escH(vb.vibe??'?')} ${escH(vb.label||'')} — ${escH(SCORE_HELP.vibe[vb.label]||'')}${vfactors?' — '+escH(vfactors):''}`],
  ['pipeline',(st.pipeline||[]).map(escH).join(' → ')||'—'],
  ['models',Object.entries(st.models||{}).map(([m,c])=>`${escH(m)} ×${escH(c)}`).join('<br>')||'—'],
  ['templates',`${escH(st.n_templates??'?')} templates · ${escH(st.n_instructions??'?')} instructions`],
  ['new stages',((dl.new_stages||[]).map(escH).join(', ')||'none')+` (templates Δ ${dl.template_growth??0})`]],
 notes:['Each step re-profiles the service over more (cumulative) or shifted (window) queries; a flip means the inferred build changed.']};};
function rowClickHandler(build){
 return e=>{
  if(e.target&&e.target.closest&&e.target.closest('a'))return;
  const r=e.target&&e.target.closest?e.target.closest('[data-f]'):null;
  if(!r)return;let f=null;try{f=JSON.parse(r.dataset.f);}catch(_){return;}
  const d=build(f);if(d)showDetail(d.title,d.sub,d.rows,d.notes);
 };
}
function wireOverlay(tableSel,build){
 const host=document.querySelector(tableSel);if(!host)return;
 host.addEventListener('click',rowClickHandler(build));
}
wireOverlay('#t-find',f=>detailFindings(f));
wireOverlay('#t-sec-secrets',f=>detailFindings(f));
wireOverlay('#t-sec-proj',f=>detailProj(f));
wireOverlay('#t-sec-trust',f=>detailTrust(f));
wireOverlay('#t-sec-risk',f=>detailRisk(f));
wireOverlay('#t-mesh',f=>detailMesh(f));
wireOverlay('#t-rates',f=>detailRates(f));
wireOverlay('#t-ledger',f=>detailLedger(f));
wireOverlay('#t-conf',f=>detailConf(f));
wireOverlay('#t-trend',f=>detailTrend(f));
wireOverlay('#t-feed',f=>detailFeed(f));
wireOverlay('#t-liveprog',f=>detailProgStep(f));
const _chainHost=$('chain');if(_chainHost)_chainHost.addEventListener('click',rowClickHandler(detailChain));
const _inj=$('sec-inject'),_prm=$('sec-perm');
const _injT=_inj&&_inj.closest?_inj.closest('table'):null;
const _prmT=_prm&&_prm.closest?_prm.closest('table'):null;
if(_injT)_injT.addEventListener('click',rowClickHandler(detailFindings));
if(_prmT)_prmT.addEventListener('click',rowClickHandler(detailFindings));
initTheme();
load();
activateTab(location.hash.slice(1)||'overview',false);
