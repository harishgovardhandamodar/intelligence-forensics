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
    remove() {},
    click() {},
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
        String(u).includes("/api/reconstructions") || String(u).includes("/api/runs") ? [] : {}),
    }),
    addEventListener: () => {},
    removeEventListener: () => {},
    setInterval: () => 0,
    clearInterval: () => {},
    URL,
    Blob,
  };
  sandbox.globalThis = sandbox;
  const src = fs.readFileSync(path.join(__dirname, "app.js"), "utf8")
    + "\n;globalThis.__t = {escH, escA, fmtN, spark, trowState, safeHref,"
    + " renderMarkdown, drawTopo, drawKnowledge, renderFindings, renderChain,"
    + " scoreCell, gcls, inlineMd, SEV_CLS, pill, toggleTheme};\n";
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
