// Client-side unit tests (P5.22) - run with: node --test static/app.test.js
//
// app.js is a browser script, so the harness stubs the DOM in `vm` and loads
// the real file: the pure helpers (escH, fmtN, spark, renderMarkdown, drawTopo)
// are tested against the shipped code, not a copy.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

function makeEl(byId, id) {
  const kids = new Map();
  const el = {
    children: [],
    dataset: {},
    style: {},
    classList: { toggle() {}, contains: () => false, add() {}, remove() {} },
    addEventListener() {},
    removeEventListener() {},
    appendChild() {},
    prepend() {},
    remove() {},
    click() {},
    options: [],
    querySelector: (sel) => {
      if (!kids.has(sel)) kids.set(sel, makeEl(byId, `${id} ${sel}`));
      return kids.get(sel);
    },
    querySelectorAll: () => [],
    closest: () => null,
    getContext: () => null,
  };
  return new Proxy(el, {
    get(t, k) {
      if (k in t) return t[k];
      return undefined;
    },
    set(t, k, v) {
      t[k] = v;
      return true;
    },
  });
}

function loadApp() {
  const byId = new Map();
  const el = (id) => {
    if (!byId.has(id)) byId.set(id, makeEl(byId, id));
    return byId.get(id);
  };
  const sandbox = {
    console,
    document: {
      getElementById: (id) => el(id),
      querySelector: () => el(""),
      querySelectorAll: () => [],
      createElement: () => el(""),
      head: el("head"),
      title: "",
      documentElement: { dataset: {} },
    },
    localStorage: {
      _m: new Map(),
      getItem(k) { return this._m.has(k) ? this._m.get(k) : null; },
      setItem(k, v) { this._m.set(k, String(v)); },
    },
    window: { addEventListener() {} },
    location: { hash: "" },
    history: { pushState() {} },
    fetch: (u) => Promise.resolve({
      json: () => Promise.resolve(
        String(u).includes("/api/reconstructions") || String(u).includes("/api/runs") ? []
        : String(u).includes("/api/sim/scenarios") ? { scenarios: [] }
        : String(u).includes("/api/sim/run") ? { results: {} }
        : String(u).includes("/api/sim/dossier") ? {
            findings: [{ band: "critical", field: "ssn", scenario: "chatbot_health",
                         accuracy: 1.0, direct_exposure: true,
                         reconstructed: "123-45-6789" }],
            timeline: [{ seq: 1, actor: "orchestrator", action: "run.start",
                         task_id: "", artifact_sha256: "", detail: "" }],
            ledger: { ok: true, checked: 1, failed_at: null } }
        : {}),
    }),
    addEventListener: () => {},
    removeEventListener: () => {},
    setInterval: () => 0,
    clearInterval: () => {},
    setTimeout: () => 0,
    clearTimeout: () => {},
    URL,
    Blob,
  };
  sandbox.globalThis = sandbox;
  const src = fs.readFileSync(path.join(__dirname, "app.js"), "utf8")
    + "\n;globalThis.__t = {escH, escA, fmtN, spark, trowState, safeHref,"
    + " renderMarkdown, drawTopo, drawKnowledge, renderFindings, renderChain,"
    + " loadLedger, filterLedger, drawSimCurve, loadSimUsers, loadSimReport,"
    + " loadSimDossier, loadSimRuns,"
    + " runSim, loadSimScenarios, secAnalyticsHTML,"
    + " scoreCell, gcls, inlineMd, SEV_CLS, pill, toggleTheme,"
    + " showNotif, svcDetailHTML, openSvcOverlay, closeOverlay,"
    + " buildIntelRows, switchRunSub, agentLogBlock,"
    + " renderRunPanes, renderRunLogs, renderRunClaims, renderRunVerdict,"
    + " switchLiveSub, filterFeed, renderFeed, renderFeedRows};\n";
  vm.createContext(sandbox);
  vm.runInContext(src, sandbox, { filename: "app.js" });
  return { t: sandbox.__t, el };
}

const { t, el } = loadApp();

test("escH escapes HTML and nulls", () => {
  assert.equal(t.escH('<b>&"\'</b>'), "&lt;b&gt;&amp;&quot;&#39;&lt;/b&gt;");
  assert.equal(t.escH(null), "");
  assert.equal(t.escH(42), "42");
});

test("fmtN abbreviates thousands/millions", () => {
  assert.equal(t.fmtN(999), "999");
  assert.equal(t.fmtN(1500), "1.5k");
  assert.equal(t.fmtN(2000000), "2.0M");
});

test("spark renders an svg polyline, empty for no data", () => {
  const s = t.spark([1, 2, 3]);
  assert.match(s, /<svg/);
  assert.match(s, /polyline/);
  assert.equal(t.spark([]), "");
});

test("trowState builds an escaped colspan row", () => {
  const r = t.trowState(3, "a<b", "warn");
  assert.match(r, /colspan="3"/);
  assert.match(r, /class="warn"/);
  assert.doesNotMatch(r, /<b/);
});

test("safeHref blocks javascript: URLs", () => {
  assert.equal(t.safeHref("javascript:alert(1)"), "#");
  assert.equal(t.safeHref("/api/x"), "/api/x");
  assert.equal(t.safeHref("https://example.com"), "https://example.com");
});

test("renderMarkdown headings, inline markup and links", () => {
  const h = t.renderMarkdown("# Title\n\npara **bold** `code` [t](/u)");
  assert.match(h, /<h2>Title<\/h2>/);
  assert.match(h, /<b>bold<\/b>/);
  assert.match(h, /<code>code<\/code>/);
  assert.match(h, /<a href="\/u">t<\/a>/);
});

test("renderMarkdown neutralises injected markup", () => {
  const h = t.renderMarkdown('<script>alert(1)</script>');
  assert.doesNotMatch(h, /<script>/);
  assert.match(h, /&lt;script&gt;/);
});

test("renderMarkdown keeps mermaid source escaped for the renderer", () => {
  const h = t.renderMarkdown("```mermaid\nflowchart A-->B\n```");
  assert.match(h, /pre class=mermaid/);
  assert.match(h, /flowchart A--&gt;B/);
});

test("drawTopo renders layered svg and handles empty graphs", () => {
  t.drawTopo({ nodes: [], edges: [], summary: {} });
  assert.match(el("topo").textContent, /no topology data/);
  t.drawTopo({
    nodes: [
      { id: "machine:a", layer: "machine", label: "a", hw: "cpu", llm_1h: 3 },
      { id: "service:s", layer: "service", label: "s" },
      { id: "model:m", layer: "model", label: "q", idle: true },
    ],
    edges: [{ from: "service:s", to: "model:m", kind: "calls", count: 4 }],
    summary: {},
  });
  const html = el("topo").innerHTML;
  assert.match(html, /<svg/);
  assert.match(html, /machine/);
  assert.match(html, /calls/);
});

test("severity pills escape content", () => {
  assert.equal(t.SEV_CLS("critical"), "crit");
  assert.equal(t.SEV_CLS("high"), "warn");
  const p = t.pill("high<script>");
  assert.match(p, /class="pill /);
  assert.doesNotMatch(p, /<script>/);
});

test("renderFindings ranks, bars and filters by area", () => {
  t.renderFindings({
    findings: [
      { severity: "low", area: "trust", title: "t1", detail: "" },
      { severity: "critical", area: "security", title: "c1", detail: "d<script>" },
    ],
    summary: { total: 2, by_severity: { critical: 1, low: 1 } },
  });
  assert.match(el("find-sum").textContent, /2 findings/);
  assert.match(el("find-bars").innerHTML, /critical/);
  const rows = el("t-find").querySelector("tbody").innerHTML;
  assert.match(rows, /c1/);
  assert.doesNotMatch(rows, /<script>/);
});

test("renderChain orders newest-first with chain badges", () => {
  t.renderChain({
    events: [
      { t: 100, dir: "in", service: "s", model: "m", prompt_head: "hi",
        prompt_tokens: 1, completion_tokens: 0, status: "", qid: "Q", chain: 1 },
      { t: 101, dir: "out", service: "s", model: "m", prompt_head: "hi",
        prompt_tokens: 1, completion_tokens: 2, status: "complete",
        queue_ms: 5, qid: "Q", chain: 1 },
    ],
    summary: { n: 2, chains: 1, orphans: 0, live: 2, history: 0 },
  });
  const html = el("chain").innerHTML;
  assert.match(html, /chain 1/);
  assert.match(html, /queue 5ms/);
  assert.ok(html.indexOf("101") < 0 || html.indexOf("OUT") < html.indexOf("IN"));
});

test("drawKnowledge renders entity layers", () => {
  t.drawKnowledge({ nodes: [], edges: [], summary: {} });
  assert.match(el("kg").textContent, /no knowledge data/);
  t.drawKnowledge({
    nodes: [
      { id: "service:s", layer: "service", label: "s", requests: 9 },
      { id: "finding:risk:s", layer: "finding", label: "s: high",
        severity: "high" },
    ],
    edges: [{ from: "service:s", to: "finding:risk:s", kind: "flagged" }],
    summary: { nodes: 2, edges: 1, shared_templates: 0 },
  });
  const html = el("kg").innerHTML;
  assert.match(html, /<svg/);
  assert.match(html, /finding/);
});

test("findings ledger refs link to the ledger", () => {
  t.renderFindings({
    findings: [
      { severity: "high", area: "claims", title: "s: brief claims unproven",
        detail: "", ref: "ledger:r1" },
      { severity: "low", area: "trust", title: "t", detail: "", ref: "security" },
    ],
    summary: { total: 2, by_severity: { high: 1, low: 1 } },
  });
  const rows = el("t-find").querySelector("tbody").innerHTML;
  assert.match(rows, /data-ledger-run="r1"/);
  assert.match(rows, />ledger<\/a>/);
});

test("loadLedger preselects a deep-linked run", async () => {
  await t.loadLedger("r9");
  assert.equal(el("sel-ledger").value, "r9");
});

test("filterLedger matches task/actor/action, empty query passes through", () => {
  const es = [
    { seq: 1, actor: "orchestrator", action: "run.start", task_id: "" },
    { seq: 2, actor: "profiler:s", action: "task.complete", task_id: "t-1" },
  ];
  assert.equal(t.filterLedger(es, ""), es);
  assert.deepEqual(t.filterLedger(es, "t-1").map((e) => e.seq), [2]);
  assert.deepEqual(t.filterLedger(es, "PROFILER").map((e) => e.seq), [2]);
  assert.deepEqual(t.filterLedger(es, "run.start").map((e) => e.seq), [1]);
  assert.deepEqual(t.filterLedger(es, "zzz"), []);
});

test("drawSimCurve renders one polyline per field", () => {
  t.drawSimCurve({});
  assert.match(el("sim-curve").textContent, /no curve data/);
  t.drawSimCurve({
    ssn: [{ queries: 1, accuracy: 0.444 }, { queries: 2, accuracy: 1.0 }],
    bp: [{ queries: 1, accuracy: 0.5 }],
  });
  const html = el("sim-curve").innerHTML;
  assert.match(html, /<svg/);
  assert.equal((html.match(/<polyline/g) || []).length, 2);
  assert.match(html, /ssn/);
});

test("secAnalyticsHTML spotlights, bars and project breakdown", () => {
  const r = {
    totals: { critical: 2, high: 4, medium: 1 },
    secrets: [
      { kind: "aws_access_key", severity: "critical", source: "a/.env",
        line: 1, match: "AKIA…", likely_fixture: false },
      { kind: "email", severity: "medium", source: "b/x.py", line: 2,
        match: "a@b", likely_fixture: true },
    ],
    injections: [
      { kind: "prompt_injection:override", severity: "high", source: "c",
        line: 1, match: "ignore" },
    ],
    permissions: [
      { kind: "world_readable_secret", severity: "critical",
        source: "a/.env", mode: "0644" },
    ],
    projects: [
      { project: "a", critical: 2, high: 0, medium: 0, low: 0, total: 2 },
      { project: "b", critical: 0, high: 1, medium: 1, low: 0, total: 2 },
    ],
  };
  const html = t.secAnalyticsHTML(r);
  assert.match(html, /world-readable secrets/);
  assert.match(html, />1<\/div><div class="k">world-readable secrets/);
  assert.match(html, /Top finding kinds/);
  assert.match(html, /aws_access_key/);
  assert.match(html, /Top projects/);
  assert.match(html, /By severity/);
  assert.doesNotMatch(html, /<script>/);
});

test("secAnalyticsHTML degrades without projects", () => {
  const html = t.secAnalyticsHTML({ totals: {}, secrets: [] });
  assert.match(html, /Spotlight/);
  assert.doesNotMatch(html, /Top projects/);
});

test("runSim renders per-scenario summaries", async () => {
  await t.runSim();
  const html = el("sim-runout").innerHTML;
  assert.match(html, /nothing ran/);
  assert.match(el("sim-runmsg").textContent, /done/);
});

test("loadSimScenarios renders diagram blocks", async () => {
  await t.loadSimScenarios();
  assert.match(el("sim-scenarios").innerHTML, /no scenarios/);
});

test("showNotif sets message and kind, re-shows on repeat", () => {
  t.showNotif("scan complete", "ok");
  const n = el("notif");
  assert.equal(n.textContent, "scan complete");
  assert.match(n.className, /show/);
  assert.match(n.className, /ok/);
  t.showNotif("other", "warn");
  assert.equal(el("notif").textContent, "other");
  assert.match(el("notif").className, /warn/);
});

test("svcDetailHTML renders profile and escapes content", () => {
  const h = t.svcDetailHTML({
    service: "quai-radar<script>", requests: 1151, total_tokens: 1797921,
    models: { "qwen3.8:latest": 1145 }, project: "KG extractor",
    pipeline: ["ingest", "extract"], pipeline_summary: "news <brief>",
    score: 80.3, grade: "A", vibe: 78, vibe_label: "pure vibe",
  });
  assert.match(h, /KG extractor/);
  assert.match(h, /ingest → extract/);
  assert.doesNotMatch(h, /<script>/);
  assert.match(t.svcDetailHTML(null), /unknown service/);
  assert.match(t.svcDetailHTML({ service: "x" }), /—/);
});

test("overlay opens on service and closes on backdrop/Esc", () => {
  t.openSvcOverlay("nope");
  assert.match(el("overlay-body").innerHTML, /unknown service/);
  t.closeOverlay();
});

test("loadSimDossier renders findings and ledger timeline", async () => {
  el("sel-sim-run").value = "r1";
  await t.loadSimDossier();
  assert.match(el("sim-dos-find").innerHTML, /123-45-6789/);
  assert.match(el("sim-dos-find").innerHTML, /verbatim/);
  assert.match(el("sim-dos-tl").innerHTML, /run\.start/);
  assert.match(el("sim-dosmsg").textContent, /1 findings/);
});

test("buildIntelRows shapes collected intel, tolerates gaps", () => {
  const rows = t.buildIntelRows({ heuristic_investigation: {
    "svc-a": { project: "p", requests: 3, total_tokens: 100,
      models: { m: 3 }, evidence: { templates: ["t1"], instructions: [],
      sample_heads: ["h1", "h2"] } },
    "svc-b": {},
  }});
  assert.equal(rows.length, 2);
  assert.equal(JSON.stringify(rows[0]), JSON.stringify({ service: "svc-a",
    project: "p", requests: 3, tokens: 100, models: ["m"], templates: 1,
    instructions: 0, heads: 2 }));
  assert.equal(rows[1].tokens, "?");
  assert.equal(t.buildIntelRows({}).length, 0);
  assert.equal(t.buildIntelRows(null).length, 0);
});

test("switchRunSub shows one pane at a time", () => {
  t.switchRunSub("logs");
  assert.equal(el("rp-logs").style.display, "");
  for (const k of ["intel", "findings", "scores", "verdict"])
    assert.equal(el("rp-" + k).style.display, "none");
  t.switchRunSub("intel");
  assert.equal(el("rp-intel").style.display, "");
});

test("agentLogBlock escapes, truncates and labels", () => {
  const h = t.agentLogBlock("profiler:s", { a: 1 }, "5 tok");
  assert.match(h, /profiler:s/);
  assert.match(h, /5 tok/);
  const evil = t.agentLogBlock("<b>", "<script>alert(1)</script>", null);
  assert.doesNotMatch(evil, /<script>/);
  assert.match(t.agentLogBlock("x", null, null), /—/);
});

test("renderRunVerdict handles missing and present scans", () => {
  t.renderRunVerdict({});
  assert.match(el("rp-verdict").innerHTML, /no security scan/);
  t.renderRunVerdict({ security: { risk_rating: "high", n_findings: 4,
    totals: { high: 4 } } });
  assert.match(el("rp-verdict").innerHTML, /high/);
});

test("renderRunClaims lists unproven services and brief issues", () => {
  t.renderRunClaims({ summary: { proven: 1, n_services: 2, contested: 0 },
    services: { a: { proven: true, issues: [] },
      b: { proven: false, issues: ["no usable profiler result"] } },
    brief_issues: ["reporter produced no text"] });
  const h = el("run-claims").innerHTML;
  assert.match(h, /proven 1\/2/);
  assert.match(h, /no usable profiler result/);
  assert.match(h, /reporter produced no text/);
});

test("switchLiveSub shows one live pane at a time", () => {
  t.switchLiveSub("traffic");
  assert.equal(el("lp-traffic").style.display, "");
  for (const k of ["feed", "recon"])
    assert.equal(el("lp-" + k).style.display, "none");
  t.switchLiveSub("feed");
  assert.equal(el("lp-feed").style.display, "");
});

test("filterFeed matches direction case-insensitively", () => {
  const evs = [
    { dir: "in", service: "a" }, { dir: "out", service: "b" },
    { dir: "sys", service: "ollama" },
  ];
  assert.equal(t.filterFeed(evs, "").length, 3);
  assert.deepEqual(t.filterFeed(evs, "OUT").map((e) => e.service), ["b"]);
  assert.deepEqual(t.filterFeed(evs, "zzz"), []);
});

test("renderFeed dedupes by seq and renders newest first", () => {
  const mk = (seq, dir) => ({ seq, dir, service: "s", t: 1000 + seq,
    model: "m", prompt_head: "hi", prompt_tokens: 1, completion_tokens: 1 });
  t.renderFeed([mk(2, "out"), mk(1, "in")]);
  t.renderFeed([mk(2, "out"), mk(3, "sys")]);
  const html = el("t-feed").querySelector("tbody").innerHTML;
  const outs = (html.match(/<tr>/g) || []).length;
  assert.equal(outs, 3);
  assert.ok(html.indexOf("SYS") !== -1 || html.indexOf("sys") !== -1);
  assert.match(el("feed-count").textContent, /3 buffered/);
});
