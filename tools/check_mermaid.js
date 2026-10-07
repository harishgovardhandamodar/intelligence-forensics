#!/usr/bin/env node
// Regression check: parse EVERY ```mermaid block in design/*.md with the
// exact vendored library (static/mermaid.min.js) that the dashboard serves.
// Usage: node tools/check_mermaid.js  (exit 1 on any failure)
const fs = require('fs');
const path = require('path');
const { JSDOM } = require('/home/fox/.local/jsdom-test/node_modules/jsdom');

const dom = new JSDOM('<!DOCTYPE html><html><body></body></html>');
global.window = dom.window;
global.document = dom.window.document;
global.navigator = dom.window.navigator;
global.self = global.window;

const mermaid = require('/home/fox/codebase/intelligence-forensics/static/mermaid.min.js');

function blocks(mdFile) {
  const text = fs.readFileSync(mdFile, 'utf8');
  const out = [];
  const re = /```mermaid\s*\n([\s\S]*?)\n```/g;
  let m, i = 0;
  while ((m = re.exec(text)) !== null) out.push({i: ++i, src: m[1]});
  return out;
}

(async () => {
  mermaid.initialize({startOnLoad: false, securityLevel: 'strict'});
  const dir = '/home/fox/codebase/intelligence-forensics/design';
  let pass = 0, fail = 0;
  for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.md')).sort()) {
    for (const b of blocks(path.join(dir, f))) {
      try {
        await mermaid.parse(b.src);
        pass++;
      } catch (e) {
        fail++;
        console.log(`FAIL ${f} block#${b.i}: ${String(e.message || e).split('\n')[0]}`);
      }
    }
  }
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
