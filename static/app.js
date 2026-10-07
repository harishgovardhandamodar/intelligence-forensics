const $=id=>document.getElementById(id);
const escH=s=>String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
const escA=escH;
const TABS=[...document.querySelectorAll('#tabs button')].map(b=>b.dataset.t);
const trowState=(cols,msg,cls='mut')=>`<tr><td class="${cls}" colspan="${cols}">${escH(msg)}</td></tr>`;
const activateTab=(name,push)=>{if(!TABS.includes(name))name='overview';TABS.forEach(t=>{const on=t===name,btn=document.querySelector(`#tabs button[data-t="${t}"]`),sec=$('s-'+t);if(btn)btn.classList.toggle('on',on);if(sec)sec.classList.toggle('on',on);});if(push!==false){const h='#'+name;if(location.hash!==h)history.pushState(null,'',h);}if(name==='live'){startLiveStream();loadTs();}else{stopLiveStream();}if(name==='security')loadSecurity();document.title='Intelligence Forensics — '+name;};
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
  $('hdr').textContent=`v${o.version||'?'} · fox:${o.fox} model:${o.model} reqs:${o.requests} svcs:${o.services} recon:${o.reconstructions} agent-runs:${o.agent_runs}`;
  $('stats').innerHTML=['requests|'+o.requests,'services|'+o.services,'reconstructions|'+o.reconstructions,'agentic runs|'+o.agent_runs,'fox|'+o.fox,'model|'+o.model].map(s=>{const[k,v]=s.split('|');return `<div class="card stat"><div class="v">${escH(v)}</div><div class="k">${escH(k)}</div></div>`}).join('');
 }catch(e){$('hdr').textContent='overview failed: '+e;$('stats').innerHTML=`<div class="card warn">overview failed: ${escH(e)}</div>`;}
 await sec('#t-svc tbody',async()=>{
  const sv=await j('/api/services');
  $('t-svc').querySelector('tbody').innerHTML=sv.services.map(s=>`<tr><td><code>${escH(s.service)}</code></td><td>${escH(s.requests)}</td><td>${escH(s.total_tokens)}</td><td class="mut">${Object.entries(s.models).map(([m,c])=>escH(m).split(':')[0]+'&times;'+escH(c)).join('<br>')}</td><td><b>${escH(s.project||'')}</b><br><span class="mut">${escH((s.pipeline_summary||'').slice(0,140))}</span></td><td>${scoreCell(s.score,s.grade)}<br><span class="mut" title="vibe index: thin prompt-wrapper vs engineered system">&#x26a1;${escH(s.vibe)} ${escH(s.vibe_label)}</span></td></tr>`).join('');wireTable('#t-svc','#filt-svc');});
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
  $('t-runs').querySelector('tbody').innerHTML=runs.map(r=>`<tr><td><a href="#" data-run="${escA(r.run_id)}">${escH(r.run_id)}</a></td><td class="mut">${escH(r.model||'')}</td><td class="mut">${escH((r.services||[]).join(', ').slice(0,80))}</td><td>${escH(r.elapsed_s??'?')}s</td><td>${escH(r.errors??0)}</td></tr>`).join('')||'<tr><td class="mut">no runs yet</td></tr>';
  document.querySelectorAll('[data-run]').forEach(a=>a.onclick=e=>{e.preventDefault();showRun(a.dataset.run);});
  loadTrend();
  try{const b=await j('/api/runs');let md;if(b.length){const d=await j('/api/runs/'+b[0].run_id);md=d.brief||'';}else{const inv=await j('/api/investigation');md=inv.readme||'no brief yet — launch an agentic run';}$('brief').innerHTML=renderMarkdown(md.slice(0,6000));renderMermaid($('brief'));}catch(e){$('brief').innerHTML=`<span class="warn">brief unavailable: ${escH(e)}</span>`;}
  try{
   const m=await j('/api/fox/live');const peers=(m.mesh&&(m.mesh.peers||[]))||[];
   $('t-mesh').querySelector('tbody').innerHTML=peers.map(p=>{const h=p.health||{};return `<tr><td><code>${escH(p.machine||p.node_id)}</code></td><td class="${p.online?'ok':'warn'}">${escH(p.online)}</td><td>${escH((p.hardware||{}).kind||'?')}</td><td>${escH(h.llm_requests_1h??'?')}</td><td class="mut">${escH((h.services||[]).map(s=>s.name).join(', ').slice(0,120))}</td></tr>`}).join('')||'<tr><td class="mut">no peers</td></tr>';
  }catch(e){$('t-mesh').querySelector('tbody').innerHTML=`<tr><td class="warn">mesh failed: ${escH(e)}</td></tr>`;}
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
 try{const d=await j('/api/runs/'+id);$('run-brief').innerHTML=renderMarkdown((d.brief||'').slice(0,8000));renderMermaid($('run-brief'));}catch(e){$('run-brief').innerHTML=`<span class="warn">brief failed: ${escH(e)}</span>`;}
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
  svg+=`<g><rect x=${p.x} y=${p.y} width=${BW} height=${BH} rx=6 fill="#161b22" stroke="${ecol(n.status)}" stroke-width="1.5"><title>${escH(n.id)} · ${escH(n.ms)}ms</title></rect><text x=${p.x+8} y=${p.y+17} fill="#e6edf3" font-size="11">${escH(n.label)}</text><text x=${p.x+8} y=${p.y+33} fill="#8b949e" font-size="10">${escH(n.sub)}</text></g>`;}));
 $('run-dag').innerHTML=svg+'</svg>';
 const mx=Math.max(...g.nodes.map(n=>n.prompt_tokens+n.completion_tokens),1);
 $('run-cost').innerHTML=g.nodes.slice().sort((a,b)=>(b.prompt_tokens+b.completion_tokens)-(a.prompt_tokens+a.completion_tokens)).map(n=>{const t=n.prompt_tokens+n.completion_tokens;
  return `<div class="row" style="margin:3px 0"><code style="min-width:200px">${escH(n.id)}</code><div style="flex:1;background:#00000040;border-radius:4px"><div style="width:${(100*t/mx).toFixed(1)}%;background:#1f6feb;border-radius:4px">&nbsp;</div></div><span class="mut">${escH(t)} tok · ${escH((n.ms/1000).toFixed(1))}s</span></div>`;}).join('');
 const badge=a=>a==='match'?'<span class=ok>match</span>':a==='partial'?'<span class=warn>partial</span>':a==='disagree'?'<span style="color:#f85149">disagree</span>':'<span class=mut>?</span>';
 $('t-conf').querySelector('tbody').innerHTML=g.services.map(s=>{const c=s.confidence;
  const bar=c==null?'<span class="mut">—</span>':`<div style="background:#00000040;border-radius:4px;min-width:110px"><div style="width:${(c*100).toFixed(0)}%;background:#3fb950;border-radius:4px">&nbsp;</div></div> ${escH(c.toFixed(2))}`;
  return `<tr><td><code>${escH(s.service)}</code></td><td>${bar}</td><td class="mut">${escH(s.heuristic_project||'')}</td><td>${escH(s.llm_project||'')}<br><span class="mut">${escH((s.what_building||'').slice(0,130))}</span></td><td>${badge(s.agreement)}</td></tr>`;}).join('');
 const withGaps=g.services.filter(s=>(s.critic_gaps||[]).length);
 $('run-gaps').innerHTML=withGaps.length?withGaps.map(s=>`<div style="margin:6px 0"><b>${escH(s.service)}</b>${s.critic_gaps.map(q=>`<div class="mut">• ${escH(q)}</div>`).join('')}</div>`).join(''):'<span class="mut">no critic gaps — quick mode skips the critic stage</span>';
 $('run-quotes').innerHTML=g.services.map(s=>((s.evidence_quotes||[]).length?`<div style="margin:6px 0"><b>${escH(s.service)}</b>${s.evidence_quotes.map(q=>`<div class="mut">&ldquo;${escH(q.slice(0,160))}&rdquo;</div>`).join('')}</div>`:'')).join('')||'<span class="mut">no quotes recorded</span>';
};
const loadTrend=async()=>{try{const t=await j('/api/runs-compare?limit=5');
 $('t-trend').querySelector('tbody').innerHTML=t.services.map(s=>`<tr><td><code>${escH(s)}</code></td><td>${t.cols.map(c=>{const v=c.confidence[s];return `<span title="${escA(c.run_id)}${c.quick?' (quick)':''}" style="display:inline-block;min-width:52px;margin-right:6px;padding:2px 6px;border-radius:4px;background:${v==null?'#21262d':'#1f6feb'};font-size:12px">${v==null?'—':escH(v.toFixed(2))}</span>`;}).join('')}</td></tr>`).join('');
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
const liveRow=e=>`<tr><td class="mut">${escH(liveTime(e.t))}</td><td>${liveDir(e.dir)}</td><td><code>${escH(e.service)}</code></td><td class="mut">${escH((e.model||'').split(':')[0])}</td><td class="mut">${escH((e.prompt_head||'').slice(0,120))}${e.queue_ms!=null?` <span class="mut">· queued ${escH(Math.round(e.queue_ms))}ms</span>`:''} <span class="mut">· ${escH((e.prompt_tokens||0)+(e.completion_tokens||0))} tok</span></td></tr>`;
let liveES=null, liveLastSeq=0;
const liveTbody=()=>$('t-feed').querySelector('tbody');
const renderFeed=evs=>{const tb=liveTbody();if(!evs.length)return;if(tb.querySelectorAll('tr').length===1&&tb.textContent.indexOf('no events')>=0)tb.innerHTML='';tb.insertAdjacentHTML('afterbegin',evs.map(liveRow).join(''));const rows=tb.querySelectorAll('tr');for(let i=rows.length-1;i>=120;i--)rows[i].remove();};
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
 $('sec-msg').textContent=`scan: ${r.n_findings||0} findings, risk ${r.risk_rating||'low'}`;
 const tot=r.totals||{};
 $('sec-stats').innerHTML=['critical','high','medium','low'].map(k=>`<div class="card stat"><div class="v ${SEC_CLS(k)}">${tot[k]||0}</div><div class="k">${k}</div></div>`).join('');
 $('sec-exp').innerHTML=(r.exposure||[]).map(f=>`<div style="margin:4px 0"><b class="${SEC_CLS(f.severity)}">${escH(f.kind)}</b> <span class=mut>${escH(f.source)}</span> — ${escH(f.detail||'')}</div>`).join('')||'<span class="mut">no exposure issues</span>';
 $('t-sec-secrets').querySelector('tbody').innerHTML=(r.secrets||[]).slice(0,200).map(f=>`<tr><td>${escH(f.kind)}</td><td class="${SEC_CLS(f.severity)}">${escH(f.severity)}</td><td class=mut>${escH(f.source)}:${escH(f.line)}</td><td><code>${escH(f.match)}</code></td></tr>`).join('')||trowState(4,'no secret/PII survivors','ok');
 $('sec-inject').innerHTML=(r.injections||[]).slice(0,200).map(f=>`<tr><td>${escH(f.kind)}</td><td class="${SEC_CLS(f.severity)}">${escH(f.severity)}</td><td class=mut>${escH(f.source)}:${escH(f.line)}</td><td><code>${escH(f.snippet||f.match)}</code></td></tr>`).join('')||trowState(4,'no injection patterns','ok');
 $('sec-perm').innerHTML=(r.permissions||[]).slice(0,200).map(f=>`<tr><td>${escH(f.source)}</td><td class="${SEC_CLS(f.severity)}">${escH(f.mode)}</td><td>${escH(f.severity)}</td></tr>`).join('')||trowState(3,'no permission issues');
 const tr=r.tracked_evidence||{};
 $('sec-tracked').textContent=(st&&st.assessment&&st.assessment.risk_rating)?`LLM assessment: ${st.assessment.risk_rating}`:'';
 $('sec-stored').innerHTML=st?`<div class=mut>last scan ${new Date((st.generated_at||0)*1000).toLocaleString()} — ${escH((st.assessment||{}).summary||'(no LLM summary)')}</div>`:'<span class=mut>no stored security.json yet</span>';
 wireTable('#t-sec-secrets',null);
}
const TRUST_CLS=s=>(s==='fail'?'warn':(s==='warn'?'':'ok'));
function renderTrust(resp){
 const rules=resp.rules||[],sum=resp.summary||{};
 const s=$('sec-trust-sum');
 if(s)s.textContent=`${sum.pass||0} pass · ${sum.warn||0} warn · ${sum.fail||0} fail`;
 const tb=$('t-sec-trust')&&$('t-sec-trust').querySelector('tbody');
 if(!tb)return;
 tb.innerHTML=rules.map(r=>`<tr><td><b>${escH(r.rule)}</b></td><td class="${TRUST_CLS(r.status)}">${escH(r.status)}</td><td class=mut>${escH(r.severity)}</td><td>${escH(r.detail)}</td></tr>`).join('')||trowState(4,'no assertions');
 wireTable('#t-sec-trust',null);
}
function renderRisk(resp){
 const rows=resp.services||[],sum=resp.summary||{};
 const s=$('sec-risk-sum');
 if(s)s.textContent=`${sum.n_services||0} services · worst ${escH(sum.worst||'low')}`;
 const tb=$('t-sec-risk')&&$('t-sec-risk').querySelector('tbody');
 if(!tb)return;
 tb.innerHTML=rows.map(r=>{const g=r.signals||{};return `<tr><td>${escH(r.service)}</td><td class="${SEC_CLS(r.band)}">${escH(r.band)}</td><td>${r.score}</td><td class=mut>${r.n}</td><td>${g.pii||0}</td><td>${g.injection||0}</td><td>${g.cross_service_reuse||0}</td></tr>`;}).join('')||trowState(7,'no requests yet');
 wireTable('#t-sec-risk',null);
}
function loadSecurity(){
 $('sec-msg').textContent='loading…';
 j('/api/security').then(renderSecurity).catch(e=>{$('sec-msg').textContent='security failed: '+e;});
 j('/api/trust').then(renderTrust).catch(()=>{});
 j('/api/risk').then(renderRisk).catch(()=>{});
}
function secScan(){
 $('sec-msg').textContent='scanning (deterministic + LLM)…';
 pj('/api/security/scan').then(()=>loadSecurity()).catch(e=>{$('sec-msg').textContent='scan failed: '+e;});
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
 if(st.running){$('live-state').innerHTML=`<span class="${stateCls}">● ${escH(bits[0])}</span>`+bits.slice(1).map(b=>' · <span class="mut">'+escH(b)+'</span>').join('');}
 else{$('live-state').textContent='○ stopped';}
 if(!st.running){stopLiveStream();}
 if(!st.running)return;
 try{const f=await j('/api/live/feed?limit=40');
  liveTbody().innerHTML=f.events.map(liveRow).join('')||liveEmpty;
  liveLastSeq=f.last_seq||liveLastSeq;
  startLiveStream();
 }catch(e){}
 try{const r=await j('/api/live/rates?window_s=300');
  $('t-rates').querySelector('tbody').innerHTML=r.services.map(s=>`<tr><td><code>${escH(s.service)}</code></td><td>${escH(s.req)}</td><td>${escH(s.tokens)}</td><td>${escH(s.req_per_min)}</td><td>${escH(s.tok_per_min)}</td></tr>`).join('')||'<tr><td class="mut" colspan=5>no completed requests in window</td></tr>';
 }catch(e){}
 try{const sv=await j('/api/services');
  const cur=$('sel-live').value;
  $('sel-live').innerHTML=sv.services.map(s=>`<option value="${escA(s.service)}">${escH(s.service)}</option>`).join('');
  if(cur)$('sel-live').value=cur;
 }catch(e){}
};
$('b-live-start').onclick=async()=>{const i=+$('inp-live-int').value||5;try{await pj('/api/live/start',{interval_s:i});}catch(e){}loadLive();};
$('b-live-stop').onclick=async()=>{try{await pj('/api/live/stop');}catch(e){}loadLive();};
$('b-live-recon').onclick=async()=>{const s=$('sel-live').value;if(!s)return;const mode=$('sel-lmode').value;$('live-recon-msg').textContent='reconstructing…';
 try{
  try{const st=await j('/api/live/status');if(!st.running)await pj('/api/live/start');}catch(e){}
  const d=await j(`/api/live/reconstruction?service=${encodeURIComponent(s)}&n=5&mode=${mode}&history=200`);
  $('live-recon-msg').textContent=`${d.steps.length} steps (${d.history_rows} history + ${d.live_rows} live), converged=${d.converged}`;
  $('t-liveprog').querySelector('tbody').innerHTML=d.steps.map(st=>{const dl=st.delta||{};
   return `<tr><td>${escH(st.step)}</td><td>${scoreCell(st.score.score,st.score.grade)}</td><td>${escH(st.requests)}</td><td><b>${escH(st.project||'')}</b></td><td>${dl.project_changed?'<span class="warn">flip</span>':'<span class="ok">stable</span>'}</td></tr>`;}).join('');
  loadLive();
 }catch(e){$('live-recon-msg').textContent='failed: '+e;}};
setInterval(()=>{const s=$('s-live');if(s&&s.classList.contains('on')){loadLive();const a=$('chk-tsauto');if(a&&a.checked)loadTs();}},4000);
const loadReports=async()=>{
 try{
  const d=await j('/api/reports'),rl=$('report-list');if(!rl)return;
  rl.innerHTML=(d.reports||[]).slice(0,5).map(r=>`<div><b>${escH(r.id)}</b> · risk ${escH(r.risk||'?')} · ${escH(r.n_findings??'?')} findings · ${escH(r.n_services??'?')} svcs · <a href="/api/evidence/file?name=${encodeURIComponent('reports/'+r.id+'/report.html')}&download=1">html</a> · <a href="/api/evidence/file?name=${encodeURIComponent('reports/'+r.id+'/report.md')}">md</a></div>`).join('')||'<span class=mut>no reports yet</span>';
 }catch(e){const rl=$('report-list');if(rl)rl.textContent='reports failed: '+e;}
};
$('b-inv').onclick=async()=>{$('runmsg').textContent='investigating…';try{const r=await pj('/api/investigate');$('runmsg').textContent=r.report||JSON.stringify(r);load();}catch(e){$('runmsg').textContent='failed: '+e;}};
$('b-report').onclick=async()=>{$('runmsg').textContent='generating unified report…';try{const r=await pj('/api/reports/run');const d=r.diff||{};$('runmsg').textContent=`report ${r.id} (db-changed=${d.db_changed??'?'}${(d.services_added||[]).length?' +'+d.services_added.join(','):''}) — see Reports below`;loadReports();}catch(e){$('runmsg').textContent='report failed: '+e;}};
$('b-agent').onclick=async()=>{$('runmsg').textContent='launching…';const q=$('opt-quick').checked;try{const r=await pj('/api/runs',{quick:q});$('runmsg').textContent='run '+JSON.stringify(r)+' — refresh Agentic tab in a few min';}catch(e){$('runmsg').textContent='launch failed: '+e;}};
const _sb=$('b-sec-scan');if(_sb)_sb.onclick=secScan;
load();
activateTab(location.hash.slice(1)||'overview',false);
