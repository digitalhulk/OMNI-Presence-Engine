"""HTML/JS for the OMNI Command Center single-page dashboard.

The page is intentionally framework-free (vanilla JS) and renders strictly
from the canonical engine result returned by the dashboard API. All dynamic
text is inserted via ``textContent``/DOM builders (never raw innerHTML), so
audited content cannot inject markup. The RawBlock design system is reused
from the engine's own stylesheet for a consistent OMNI-native look.
"""
from __future__ import annotations

from .report_html import load_rawblock_css

_APP_CSS = """
:root { --omni-gap: 16px; }
body { margin: 0; }
.omni-shell { max-width: 1400px; margin: 0 auto; padding: 0 20px 64px; }
.omni-topbar { position: sticky; top: 0; z-index: 20; background: var(--rb-black, #111); color: var(--rb-paper, #fff);
  border-bottom: 4px solid var(--rb-black, #111); display: flex; flex-wrap: wrap; gap: 12px; align-items: center;
  padding: 12px 20px; }
.omni-topbar h1 { font-size: 20px; margin: 0; letter-spacing: 1px; text-transform: uppercase; }
.omni-run { display: flex; gap: 8px; flex: 1 1 320px; min-width: 260px; }
.omni-run input { flex: 1; padding: 10px; border: 2px solid #000; font: inherit; }
.omni-btn { padding: 10px 16px; border: 2px solid #000; background: #000; color: #fff; cursor: pointer;
  font: inherit; text-transform: uppercase; letter-spacing: .5px; }
.omni-btn:disabled { opacity: .5; cursor: not-allowed; }
.omni-btn--ghost { background: #fff; color: #000; }
.omni-nav { display: flex; flex-wrap: wrap; gap: 4px; margin: 16px 0; border-bottom: 2px solid #000; }
.omni-nav button { padding: 8px 14px; border: 0; background: transparent; cursor: pointer; font: inherit;
  border-bottom: 3px solid transparent; text-transform: uppercase; font-size: 12px; letter-spacing: .5px; }
.omni-nav button.is-active { border-bottom-color: #000; font-weight: 700; }
.omni-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: var(--omni-gap); }
.omni-card { border: 2px solid #000; padding: 14px; }
.omni-card .k { font-size: 11px; text-transform: uppercase; letter-spacing: .5px; opacity: .7; }
.omni-card .v { font-size: 34px; font-weight: 800; line-height: 1.1; margin-top: 6px; }
.omni-grid20 { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
.omni-mod { border: 2px solid #000; padding: 10px; cursor: pointer; }
.omni-mod:focus-visible { outline: 3px solid #06f; }
.omni-mod .n { font-size: 11px; text-transform: uppercase; opacity: .7; }
.omni-mod .s { font-weight: 700; margin-top: 4px; }
.st-PASS { border-left: 8px solid #1a7f37; } .st-FAIL { border-left: 8px solid #b42318; }
.st-BLOCKED { border-left: 8px solid #b54708; } .st-UNKNOWN { border-left: 8px solid #667085; }
.st-NA { border-left: 8px solid #98a2b3; }
table.omni-table { width: 100%; border-collapse: collapse; }
table.omni-table th, table.omni-table td { border: 1px solid #000; padding: 6px 8px; text-align: left; font-size: 13px; vertical-align: top; }
table.omni-table th { background: #000; color: #fff; cursor: pointer; position: sticky; top: 56px; }
.omni-chip { display: inline-block; padding: 1px 6px; border: 1px solid #000; font-size: 11px; text-transform: uppercase; }
.omni-filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; align-items: center; }
.omni-filters input, .omni-filters select { padding: 6px; border: 2px solid #000; font: inherit; }
.omni-section { display: none; }
.omni-section.is-active { display: block; }
.omni-status { padding: 10px 14px; border: 2px solid #000; margin: 12px 0; font-weight: 700; }
.omni-status--run { background: #fef7c3; } .omni-status--ok { background: #d1fae5; }
.omni-status--fail { background: #fee2e2; } .omni-muted { opacity: .65; }
.omni-graph svg { width: 100%; height: auto; border: 2px solid #000; background: #fafafa; }
details.omni-det { border: 1px solid #000; margin: 6px 0; padding: 6px 10px; }
details.omni-det summary { cursor: pointer; font-weight: 700; }
.omni-bar { height: 14px; background: #eee; border: 1px solid #000; position: relative; }
.omni-bar > span { position: absolute; left: 0; top: 0; bottom: 0; background: #000; }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""

_APP_JS = r"""
'use strict';
const $ = (s, r=document) => r.querySelector(s);
const esc = (v) => (v === null || v === undefined) ? '' : String(v);
function el(tag, attrs, children) {
  const n = document.createElement(tag);
  if (attrs) for (const k in attrs) {
    if (k === 'class') n.className = attrs[k];
    else if (k === 'text') n.textContent = attrs[k];
    else if (k.startsWith('on') && typeof attrs[k] === 'function') n.addEventListener(k.slice(2), attrs[k]);
    else if (attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, attrs[k]);
  }
  (children || []).forEach(c => n.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
  return n;
}
let CURRENT = null;   // canonical engine result of the latest run
let GRAPH = null;

async function api(path, opts) {
  const r = await fetch(path, opts);
  const text = await r.text();
  let data; try { data = JSON.parse(text); } catch (e) { data = { error: text }; }
  if (!r.ok) throw new Error((data && data.error) || ('HTTP ' + r.status));
  return data;
}

function setStatus(kind, msg) {
  const bar = $('#omni-status');
  bar.className = 'omni-status omni-status--' + kind;
  bar.textContent = msg;
  bar.hidden = false;
}

async function runAudit() {
  const url = $('#omni-url').value.trim();
  if (!url) { setStatus('fail', 'Enter a URL first.'); return; }
  $('#omni-run-btn').disabled = true;
  setStatus('run', 'RUNNING — executing the real OPE pipeline against ' + url + ' …');
  try {
    const result = await api('/api/audit', { method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ url }) });
    CURRENT = result;
    renderAll(result);
    setStatus('ok', 'COMPLETED — run ' + esc(result.run_id) + ' · ' + esc(result.final_url || result.target));
  } catch (e) {
    setStatus('fail', 'FAILED — ' + e.message);
  } finally {
    $('#omni-run-btn').disabled = false;
  }
}

function countStatuses(obj, key) {
  const c = {PASS:0, FAIL:0, UNKNOWN:0, 'N/A':0, BLOCKED:0};
  for (const k in obj) { const s = obj[k] && obj[k][key || 'status']; if (s in c) c[s]++; }
  return c;
}

function renderOverview(r) {
  const s = r.summary || {};
  const mc = countStatuses(r.modules || {});
  // evidence coverage = checks with a determinate (non-UNKNOWN) status
  const checks = r.checks || {};
  let determinate = 0, total = 0;
  for (const k in checks) { total++; if (checks[k].status && checks[k].status !== 'UNKNOWN') determinate++; }
  const cov = total ? Math.round(100 * determinate / total) : null;
  const dur = (r.completed_at && r.started_at) ? (r.completed_at - r.started_at).toFixed(2) + 's' : '—';
  const cards = [
    ['OMNI Health', r.health === null || r.health === undefined ? 'N/A' : r.health, 'internal diagnostic signal, not a search ranking'],
    ['Findings', s.finding_count ?? 0, ''],
    ['Critical', s.critical ?? 0, ''], ['High', s.high ?? 0, ''],
    ['FAIL modules', mc.FAIL, ''], ['Blocked modules', mc.BLOCKED, 'dependency-derived'],
    ['Unknown modules', mc.UNKNOWN, 'insufficient evidence'],
    ['Evidence coverage', cov === null ? '—' : cov + '%', 'checks with a determinate status'],
    ['Audit duration', dur, ''],
  ];
  const wrap = $('#sec-overview'); wrap.textContent = '';
  wrap.appendChild(el('p', {class:'omni-muted', text:'OMNI Health is an internal, evidence-weighted diagnostic and remediation signal — not a claim about any search engine ranking.'}));
  const grid = el('div', {class:'omni-cards'});
  cards.forEach(([k,v,note]) => grid.appendChild(el('div', {class:'omni-card'}, [
    el('div',{class:'k',text:k}), el('div',{class:'v',text:esc(v)}),
    note ? el('div',{class:'k',text:note}) : el('span',{})
  ])));
  wrap.appendChild(grid);
}

function renderModules(r) {
  const wrap = $('#sec-modules'); wrap.textContent = '';
  const grid = el('div', {class:'omni-grid20'});
  const mods = r.modules || {};
  Object.keys(mods).sort().forEach(num => {
    const m = mods[num];
    const st = m.status || 'UNKNOWN';
    const cell = el('div', {class:'omni-mod st-' + st.replace('/',''), tabindex:'0', role:'button',
      'aria-label': 'Module ' + num + ' ' + st}, [
      el('div',{class:'n',text:'Module ' + num}),
      el('div',{class:'s',text:st}),
      el('div',{class:'k',text:'score ' + (m.score === null || m.score === undefined ? '—' : m.score)}),
    ]);
    const open = () => showModuleDetail(num, m, r);
    cell.addEventListener('click', open);
    cell.addEventListener('keydown', e => { if (e.key==='Enter'||e.key===' ') { e.preventDefault(); open(); } });
    grid.appendChild(cell);
  });
  wrap.appendChild(grid);
  wrap.appendChild(el('div',{id:'mod-detail', style:'margin-top:16px'}));
}

function showModuleDetail(num, m, r) {
  const d = $('#mod-detail'); d.textContent = '';
  d.appendChild(el('h3',{text:'Module ' + num + ' — ' + (m.status||'UNKNOWN')}));
  const basis = m.score_basis || {};
  d.appendChild(el('p',{text:'Method: ' + esc(basis.method || '—') + ' · Score: ' + (m.score ?? '—')}));
  if (basis.blocked_by) d.appendChild(el('p',{text:'Blocked by: ' + basis.blocked_by.join(', ')}));
  // findings for this module
  const fs = (r.findings||[]).filter(f => String(f.module||'').split('-')[0] === num);
  if (fs.length) {
    d.appendChild(el('h4',{text:'Findings'}));
    fs.forEach(f => d.appendChild(findingDetail(f)));
  } else {
    d.appendChild(el('p',{class:'omni-muted', text:'No finding records for this module.'}));
  }
}

function findingDetail(f) {
  const det = el('details',{class:'omni-det'});
  det.appendChild(el('summary',{text:'[' + esc((f.severity||'').toUpperCase()) + '] ' + esc(f.id) + ' — ' + esc(f.symptom)}));
  det.appendChild(el('p',{text:'Module: ' + esc(f.module) + ' · Priority: ' + esc(f.priority) + ' · Status: ' + esc(f.status) + ' · Confidence: ' + esc(f.confidence)}));
  if (f.root_cause) det.appendChild(el('p',{text:'Root cause: ' + esc(f.root_cause)}));
  (f.remediation||[]).forEach(x => det.appendChild(el('div',{text:'• fix: ' + esc(x)})));
  (f.validation||[]).forEach(x => det.appendChild(el('div',{text:'• validate: ' + esc(x)})));
  (f.evidence||[]).forEach(ev => det.appendChild(el('div',{class:'omni-muted', text:'evidence: ' + esc(ev.source) + ' (confidence ' + esc(ev.confidence) + ')'})));
  return det;
}

let FILTER = {sev:'', status:'', q:''}, SORT = {key:'priority', dir:-1};
function renderFindings(r) {
  const wrap = $('#sec-findings'); wrap.textContent = '';
  const filters = el('div',{class:'omni-filters'});
  const sevSel = el('select',{'aria-label':'Severity filter', onchange:e=>{FILTER.sev=e.target.value; drawTable(r);}});
  ['','critical','high','medium','low','info'].forEach(v => sevSel.appendChild(el('option',{value:v,text:v?v.toUpperCase():'ALL SEVERITY'})));
  const stSel = el('select',{'aria-label':'Status filter', onchange:e=>{FILTER.status=e.target.value; drawTable(r);}});
  ['','FAIL','UNKNOWN','BLOCKED','OBSERVED','HYPOTHESIS'].forEach(v => stSel.appendChild(el('option',{value:v,text:v||'ALL STATUS'})));
  const q = el('input',{type:'search',placeholder:'search symptom/module', 'aria-label':'Search findings', oninput:e=>{FILTER.q=e.target.value.toLowerCase(); drawTable(r);}});
  filters.appendChild(sevSel); filters.appendChild(stSel); filters.appendChild(q);
  wrap.appendChild(filters);
  wrap.appendChild(el('div',{id:'find-table'}));
  drawTable(r);
}

function drawTable(r) {
  const host = $('#find-table'); if (!host) return; host.textContent = '';
  let rows = (r.findings||[]).slice();
  if (FILTER.sev) rows = rows.filter(f => (f.severity||'').toLowerCase() === FILTER.sev);
  if (FILTER.status) rows = rows.filter(f => (f.status||'') === FILTER.status);
  if (FILTER.q) rows = rows.filter(f => ((f.symptom||'')+' '+(f.module||'')+' '+(f.id||'')).toLowerCase().includes(FILTER.q));
  rows.sort((a,b) => {
    const ka=a[SORT.key], kb=b[SORT.key];
    if (ka<kb) return SORT.dir; if (ka>kb) return -SORT.dir;
    return String(a.id).localeCompare(String(b.id));  // deterministic tiebreak
  });
  const table = el('table',{class:'omni-table'});
  const head = el('tr',{});
  [['severity','Severity'],['priority','Priority'],['module','Module'],['id','Check/ID'],['status','Status'],['symptom','Symptom']]
    .forEach(([k,label]) => head.appendChild(el('th',{onclick:()=>{SORT.dir = SORT.key===k ? -SORT.dir : -1; SORT.key=k; drawTable(r);}, text:label})));
  table.appendChild(head);
  rows.forEach(f => {
    const tr = el('tr',{});
    tr.appendChild(el('td',{}, [el('span',{class:'omni-chip', text:esc((f.severity||'').toUpperCase())})]));
    tr.appendChild(el('td',{text:esc(f.priority)}));
    tr.appendChild(el('td',{text:esc(f.module)}));
    tr.appendChild(el('td',{text:esc(f.id)}));
    tr.appendChild(el('td',{text:esc(f.status)}));
    tr.appendChild(el('td',{}, [findingDetail(f)]));
    table.appendChild(tr);
  });
  host.appendChild(el('p',{class:'omni-muted', text:rows.length + ' finding(s)'}));
  host.appendChild(table);
}

function renderRemediation(r) {
  const wrap = $('#sec-remediation'); wrap.textContent = '';
  const plan = r.remediation_plan;
  if (!plan) { wrap.appendChild(el('p',{class:'omni-muted',text:'No plan available.'})); return; }
  const sm = plan.summary || {};
  wrap.appendChild(el('p',{text:sm.root_cause_count + ' root cause(s) · ' + sm.direct_failure_count + ' independent failure(s) · ' + sm.blocked_count + ' blocked/waiting'}));
  const group = (title, steps) => {
    if (!steps || !steps.length) return;
    wrap.appendChild(el('h3',{text:title}));
    steps.forEach(step => {
      const det = el('details',{class:'omni-det', open:''});
      det.appendChild(el('summary',{text:'Module ' + esc(step.module) + ' (' + esc(step.status) + ')' + (step.unblock_count ? ' — unblocks ' + step.unblock_count : '')}));
      if (step.unblocks && step.unblocks.length) det.appendChild(el('p',{class:'omni-muted', text:'Unblocks: ' + step.unblocks.join(', ')}));
      (step.findings||[]).forEach(f => det.appendChild(findingDetail(f)));
      if (!(step.findings||[]).length) det.appendChild(el('p',{class:'omni-muted', text:'Module status derived from failing checks; no finding record.'}));
      wrap.appendChild(det);
    });
  };
  group('Fix first — root causes (by unblock impact)', plan.root_causes);
  group('Then — independent failures', plan.direct_failures);
  if ((plan.blocked||[]).length) {
    wrap.appendChild(el('h3',{text:'Waiting (blocked, not yet actionable)'}));
    plan.blocked.forEach(b => wrap.appendChild(el('div',{text:'Module ' + esc(b.module) + ' — waiting on ' + (b.waiting_on||[]).join(', ')})));
  }
}

function layerize(nodes, edges) {
  const deps = {}; nodes.forEach(n => deps[n.module] = []);
  edges.forEach(e => { (deps[e.to] = deps[e.to] || []).push(e.from); });
  const layer = {}; const visit = (m) => {
    if (m in layer) return layer[m];
    const ds = deps[m] || []; layer[m] = ds.length ? 1 + Math.max(...ds.map(visit)) : 0; return layer[m];
  };
  nodes.forEach(n => visit(n.module));
  return layer;
}

function renderGraph(r) {
  const wrap = $('#sec-graph'); wrap.textContent = '';
  if (!GRAPH) { wrap.appendChild(el('p',{class:'omni-muted',text:'Loading dependency graph…'})); return; }
  const mods = (r && r.modules) || {};
  const layer = layerize(GRAPH.nodes, GRAPH.edges);
  const byLayer = {};
  GRAPH.nodes.forEach(n => { (byLayer[layer[n.module]] = byLayer[layer[n.module]] || []).push(n.module); });
  const LW = 150, LH = 60, R = 22; const maxLayer = Math.max(...Object.values(layer));
  const pos = {};
  Object.keys(byLayer).forEach(L => byLayer[L].forEach((m,i) => { pos[m] = {x: 60 + L*LW, y: 40 + i*LH}; }));
  const height = 40 + Math.max(...Object.values(byLayer).map(a=>a.length)) * LH;
  const width = 120 + maxLayer*LW;
  const NS='http://www.w3.org/2000/svg';
  const svg = document.createElementNS(NS,'svg');
  svg.setAttribute('viewBox', '0 0 ' + width + ' ' + height);
  svg.setAttribute('role','img'); svg.setAttribute('aria-label','20-module dependency graph');
  const color = st => ({PASS:'#1a7f37',FAIL:'#b42318',BLOCKED:'#b54708','N/A':'#98a2b3'}[st] || '#667085');
  GRAPH.edges.forEach(e => {
    const a=pos[e.from], b=pos[e.to]; if(!a||!b) return;
    const line=document.createElementNS(NS,'line');
    line.setAttribute('x1',a.x); line.setAttribute('y1',a.y); line.setAttribute('x2',b.x); line.setAttribute('y2',b.y);
    line.setAttribute('stroke','#bbb'); line.setAttribute('stroke-width','1.5');
    svg.appendChild(line);
  });
  GRAPH.nodes.forEach(n => {
    const p=pos[n.module]; const st=(mods[n.module]||{}).status || 'UNKNOWN';
    const c=document.createElementNS(NS,'circle');
    c.setAttribute('cx',p.x); c.setAttribute('cy',p.y); c.setAttribute('r',R);
    c.setAttribute('fill', r ? color(st) : '#ddd'); c.setAttribute('stroke','#000'); c.setAttribute('stroke-width','2');
    const t=document.createElementNS(NS,'text');
    t.setAttribute('x',p.x); t.setAttribute('y',p.y+4); t.setAttribute('text-anchor','middle');
    t.setAttribute('font-size','12'); t.setAttribute('fill','#fff'); t.textContent=n.module;
    const title=document.createElementNS(NS,'title'); title.textContent=n.name + ' — ' + st;
    c.appendChild(title);
    svg.appendChild(c); svg.appendChild(t);
  });
  const box = el('div',{class:'omni-graph'}); box.appendChild(svg);
  wrap.appendChild(el('p',{class:'omni-muted', text: r ? 'Nodes coloured by this run’s module status (green PASS · red FAIL · orange BLOCKED · grey UNKNOWN).' : 'Run an audit to colour the graph by module status.'}));
  wrap.appendChild(box);
  // text equivalent for accessibility
  if (r) {
    const rc = r.dependency_root_causes || {};
    const summary = Object.keys(rc).length ? Object.keys(rc).sort().map(k => 'Module '+k+' blocked by '+rc[k].join(',')).join('; ') : 'No blocked modules.';
    wrap.appendChild(el('p',{class:'omni-muted', text:'Root-cause chains: ' + summary}));
  }
}

async function renderProviders() {
  const wrap = $('#sec-providers'); wrap.textContent = 'Loading…';
  try {
    const data = await api('/api/providers');
    wrap.textContent = '';
    wrap.appendChild(el('p',{class:'omni-muted', text:'Optional external providers. Absent credentials keep affected checks UNKNOWN (never fabricated).'}));
    const t = el('table',{class:'omni-table'});
    t.appendChild(el('tr',{},[el('th',{text:'Provider'}),el('th',{text:'Env var'}),el('th',{text:'Configured'}),el('th',{text:'Adapter'}),el('th',{text:'Upgrades'})]));
    data.providers.forEach(p => t.appendChild(el('tr',{},[
      el('td',{text:esc(p.provider)}), el('td',{text:esc(p.env_var)}),
      el('td',{text:p.configured?'yes':'no'}), el('td',{text:p.implemented?'active':'planned'}),
      el('td',{text:(p.upgrades_checks||[]).join(', ')||'(advisory)'})
    ])));
    wrap.appendChild(t);
  } catch (e) { wrap.textContent = 'Provider status unavailable: ' + e.message; }
}

async function renderHistory() {
  const wrap = $('#sec-history'); wrap.textContent = '';
  if (!CURRENT) { wrap.appendChild(el('p',{class:'omni-muted', text:'Run an audit to load its history.'})); return; }
  try {
    const data = await api('/api/history?target=' + encodeURIComponent(CURRENT.target || ''));
    if (!data.runs.length) { wrap.appendChild(el('p',{class:'omni-muted', text:'Not enough historical data for this target yet.'})); return; }
    const t = el('table',{class:'omni-table'});
    t.appendChild(el('tr',{},[el('th',{text:'Run'}),el('th',{text:'Recorded'}),el('th',{text:'Findings'}),el('th',{text:'Tracked metrics'})]));
    data.runs.forEach(run => t.appendChild(el('tr',{},[
      el('td',{text:esc(run.run_id)}), el('td',{text:esc(run.recorded_at)}),
      el('td',{text:esc((run.finding_ids||[]).length)}), el('td',{text:esc(Object.keys(run.metrics||{}).join(', '))})
    ])));
    wrap.appendChild(t);
  } catch (e) { wrap.appendChild(el('p',{text:'History unavailable: ' + e.message})); }
}

async function doExport(fmt) {
  if (!CURRENT) { setStatus('fail','Run an audit before exporting.'); return; }
  try {
    const r = await fetch('/api/export', { method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ run_id: CURRENT.run_id, result: CURRENT, format: fmt }) });
    if (!r.ok) { const e = await r.json().catch(()=>({error:'export failed'})); throw new Error(e.error); }
    const blob = await r.blob();
    const cd = r.headers.get('Content-Disposition') || '';
    const name = (cd.match(/filename="([^"]+)"/) || [,'omni-report'])[1];
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(a.href);
  } catch (e) { setStatus('fail','Export failed: ' + e.message); }
}

function renderExports() {
  const wrap = $('#sec-exports'); wrap.textContent = '';
  wrap.appendChild(el('p',{class:'omni-muted', text:'Every export is rendered from the exact current run (same diagnosis, different presentation). HTML works offline.'}));
  [['json','JSON'],['md','Markdown'],['txt','Text'],['html','HTML (offline)'],['pdf','PDF'],['png','Image (PNG)'],['bundle','Download complete bundle (.zip)']]
    .forEach(([fmt,label]) => wrap.appendChild(el('button',{class:'omni-btn omni-btn--ghost', style:'margin:4px', onclick:()=>doExport(fmt), text:label})));
  wrap.appendChild(el('p',{class:'omni-muted', text:'PDF/PNG require the optional browser backend; if it is not installed the export reports that clearly rather than producing a fake file.'}));
}

function renderAll(r) {
  renderOverview(r); renderModules(r); renderFindings(r); renderRemediation(r); renderGraph(r);
  renderHistory(); renderExports();
}

function switchTab(name) {
  document.querySelectorAll('.omni-section').forEach(s => s.classList.toggle('is-active', s.id === 'sec-' + name));
  document.querySelectorAll('.omni-nav button').forEach(b => b.classList.toggle('is-active', b.dataset.tab === name));
  if (name === 'providers') renderProviders();
  if (name === 'history') renderHistory();
  if (name === 'graph') renderGraph(CURRENT);
}

async function boot() {
  $('#omni-run-btn').addEventListener('click', runAudit);
  $('#omni-url').addEventListener('keydown', e => { if (e.key === 'Enter') runAudit(); });
  document.querySelectorAll('.omni-nav button').forEach(b => b.addEventListener('click', () => switchTab(b.dataset.tab)));
  try { GRAPH = await api('/api/dependency-graph'); } catch (e) { GRAPH = null; }
  renderProviders();
  switchTab('overview');
}
document.addEventListener('DOMContentLoaded', boot);
"""

_TABS = [
    ("overview", "Overview"), ("modules", "Modules"), ("findings", "Findings"),
    ("remediation", "Remediation"), ("graph", "Dependency Graph"),
    ("providers", "Providers"), ("history", "History"), ("exports", "Exports"),
]


def render_index() -> str:
    """Return the full self-contained dashboard HTML."""
    rawblock = load_rawblock_css()
    nav = "".join(
        f'<button data-tab="{tab}">{label}</button>' for tab, label in _TABS
    )
    sections = "".join(
        f'<section id="sec-{tab}" class="omni-section" aria-label="{label}"></section>'
        for tab, label in _TABS
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OMNI Command Center</title>
<style>{rawblock}</style>
<style>{_APP_CSS}</style>
</head>
<body>
<header class="omni-topbar">
  <h1>OMNI Command Center</h1>
  <div class="omni-run">
    <label for="omni-url" class="rb-hidden" style="position:absolute;left:-9999px;">Target URL</label>
    <input id="omni-url" type="url" placeholder="https://example.com" autocomplete="off" spellcheck="false">
    <button id="omni-run-btn" class="omni-btn">Run audit</button>
  </div>
</header>
<div class="omni-shell">
  <div id="omni-status" class="omni-status" role="status" aria-live="polite" hidden>Enter a URL and run a real OPE audit.</div>
  <nav class="omni-nav" aria-label="Dashboard sections">{nav}</nav>
  {sections}
</div>
<script>{_APP_JS}</script>
</body>
</html>
"""
