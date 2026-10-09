import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { answerText, answerLatex, solutionText, plainValue } from '../frontend/js/solution-data.js';
const source = fs.readFileSync(new URL('../frontend/js/result-actions.js', import.meta.url), 'utf8').replace(/^import .*;\n/gm, '').replace('export function', 'function');
function setup(clipboard) {
  const nodes = [], blobs = [], revoked = [], timers = [], added = [];
  let printed = 0;
  const el = (tag, attrs = {}, children = []) => {
    const node = { tag, ...attrs, children, focus() { this.focused = true; }, select() { this.selected = true; }, click() { this.clicked = true; }, remove() { this.removed = true; } };
    nodes.push(node); return node;
  };
  const context = vm.createContext({ el, answerText, answerLatex, solutionText, plainValue, Blob,
    navigator: { clipboard }, window: { addEventListener() {}, print() { printed++; } },
    document: { body: { append: node => added.push(node) } },
    URL: { createObjectURL: blob => { blobs.push(blob); return 'blob:test'; }, revokeObjectURL: url => revoked.push(url) },
    setTimeout: callback => timers.push(callback)
  });
  vm.runInContext(source, context);
  vm.runInContext("resultActions({determinant:{text:'1/3',latex:'\\\\frac{1}{3}'}}, {id:'linear-algebra',name:'Linear Algebra'}, {id:'analyze',label:'Analyse matrix'}, {matrix:'1/3'})", context);
  return { nodes, blobs, revoked, timers, added, button: text => nodes.find(n => n.tag === 'button' && n.text === text), printed: () => printed };
}

test('clipboard denial exposes the exact answer for manual copying', async () => {
  const harness = setup({ writeText: async () => { throw Error('denied'); } });
  await harness.button('Copy answer').onClick();
  const manual = harness.nodes.find(n => n.tag === 'textarea');
  assert.equal(manual.hidden, false);
  assert.ok(manual.focused && manual.selected);
  assert.match(manual.value, /1\/3/);
});

test('download creates a complete text file, preserves inputs, and cleans up its temporary URL', async () => {
  const harness = setup({ writeText: async () => {} });
  harness.button('Download solution (.txt)').onClick();
  assert.match(await harness.blobs[0].text(), /Matrix: 1\/3/);
  assert.match(await harness.blobs[0].text(), /Not verified/);
  assert.equal(harness.added[0].download, 'mathnova-linear-algebra-analyze.txt');
  assert.ok(harness.added[0].clicked && harness.added[0].removed);
  harness.timers.forEach(callback => callback());
  assert.deepEqual(harness.revoked, ['blob:test']);
  harness.button('Print / Save PDF').onClick();
  assert.equal(harness.printed(), 1);
});
