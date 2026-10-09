import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
class Node {
  constructor(tag = 'div', attrs = {}, children = []) {
    this.tag = tag; this.children = []; this.events = {}; this.hidden = false;
    Object.assign(this, attrs);
    this.append(...children);
  }
  append(...children) { this.children.push(...children.filter(Boolean)); }
  get firstChild() { return this.children[0]; }
  removeChild(node) { this.children.splice(this.children.indexOf(node), 1); }
  addEventListener(type, callback) { this.events[type] = callback; }
  setAttribute(name, value) { this[name] = value; }
  scrollIntoView() {}
  querySelectorAll(tag) { return this.children.flatMap(child => typeof child === 'object' ? [...(child.tag === tag ? [child] : []), ...child.querySelectorAll(tag)] : []); }
}
const elements = new Map();
const el = (tag, attrs, children) => new Node(tag, attrs, children);
const method = { id: 'analyze', endpoint: '/analyze', label: 'Analyze', fields: [{ name: 'matrix', label: 'Matrix', type: 'textarea', value: '1,2\n3,4' }] };
let themeChange, requests = [], renderCalls = [], nextResponse;
const context = vm.createContext({
  MODULES: [{ id: 'linear-algebra', name: 'Linear algebra', methods: [method] }],
  forcingVisibility: () => [], walkthroughFor: () => null, mountShell: () => {},
  onChange: callback => { themeChange = callback; },
  post: async (endpoint, input) => { requests.push({ endpoint, input }); return nextResponse ? await nextResponse : { determinant: -2 }; },
  ApiError: class ApiError extends Error {},
  renderSolved: (result, module, method) => { renderCalls.push(result); return el('details', { open: false }); },
  resultActions: () => [], el,
  clear: node => { node.children = []; return node; },
  empty: text => el('p', { text }), alert: (kind, title, detail) => el('p', { text: detail }), renderLatex: () => {},
  document: { readyState: 'loading', addEventListener: () => {}, getElementById: id => { if (!elements.has(id)) elements.set(id, new Node()); return elements.get(id); } },
  location: { hash: '', href: 'http://localhost/solver/' },
  window: { addEventListener: () => {} }, URL, console, AbortController, setTimeout, clearTimeout
});
// Stub imported collaborators while exercising the actual solver page state and events.
const source = fs.readFileSync(new URL('../frontend/js/app.js', import.meta.url), 'utf8').replace(/^import .*;\n/gm, '');
vm.runInContext(source, context);
const run = code => vm.runInContext(code, context);
test('editing and changing theme keep answers tied to the submitted request', async () => {
  run('boot()');
  themeChange();
  assert.equal(requests.length, 0, 'switching theme before a calculation must not compute');
  await run('run()');
  assert.equal(requests.length, 1);
  const input = elements.get('method-form').querySelectorAll('textarea')[0];
  input.value = '5,0\n0,5'; input.events.input();
  assert.equal(run('dom.inputNotice.hidden'), false, 'edits must flag the displayed answer as stale');
  assert.equal(run('state.savedResult.fields[0].value'), '1,2\n3,4');
  run("dom.results.querySelectorAll('details')[0].open = false");
  themeChange();
  assert.equal(requests.length, 1, 'theme changes must not send edited inputs to the solver');
  assert.equal(run("dom.results.querySelectorAll('details')[0].open"), false, 'disclosure choice survives theme repaint');
  assert.equal(run('dom.inputNotice.hidden'), false);
  await run('run()');
  assert.equal(requests.length, 2);
  assert.equal(run('dom.inputNotice.hidden'), true, 'new result clears stale state');
  assert.equal(run('state.savedResult.fields[0].value'), '5,0\n0,5');
  let finish;
  nextResponse = new Promise(resolve => { finish = resolve; });
  const pending = run('run()');
  input.value = '9,0\n0,9'; input.events.input();
  finish({ determinant: 25 }); await pending;
  assert.equal(run('dom.inputNotice.hidden'), false, 'editing during a request must still flag the returned answer');
  assert.equal(run('state.savedResult.fields[0].value'), '5,0\n0,5');
  run("selectMethod('analyze')");
  const count = requests.length;
  themeChange();
  assert.equal(run('state.savedResult'), null);
  assert.equal(requests.length, count, 'method switch clears the saved answer');
});
