import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync(new URL('../frontend/sw.js', import.meta.url), 'utf8');
function setup(fetch, entries = new Map()) {
  const events = {}, writes = [], waiting = [];
  const cache = { match: async key => entries.get(key), put: async (key, response) => { writes.push(key); entries.set(key, response); } };
  const context = vm.createContext({
    self: { location: { origin: 'https://mathnova.test' }, addEventListener: (type, handler) => { events[type] = handler; } },
    caches: { open: async () => cache }, fetch, URL,
    setTimeout: callback => setTimeout(callback, 5), clearTimeout
  });
  vm.runInContext(source, context);
  context.event = { waitUntil: promise => waiting.push(promise) };
  return { events, writes, waiting, entries, run: request => { context.request = request; return vm.runInContext('networkFirst(request, event)', context); } };
}
const response = (name, marker = '1') => ({ name, ok: true, type: 'basic', headers: { get: () => marker }, clone() { return this; } });
const request = { url: 'https://mathnova.test/solver/?matrix=private-input', method: 'GET', mode: 'navigate' };

test('slow startup serves a cached page promptly and refreshes it when the server wakes', async () => {
  let resolve;
  const old = response('old'), fresh = response('fresh');
  const harness = setup(() => new Promise(r => { resolve = r; }), new Map([['https://mathnova.test/solver/', old]]));
  assert.equal(await harness.run(request), old);
  resolve(fresh); await Promise.all(harness.waiting);
  assert.equal(harness.entries.get('https://mathnova.test/solver/'), fresh);
  assert.deepEqual(harness.writes, ['https://mathnova.test/solver/'], 'user query must not become a stored cache key');
});

test('the hosting startup page never replaces a real cached page', async () => {
  const old = response('old');
  const harness = setup(async () => response('Render loading', null), new Map([['https://mathnova.test/solver/', old]]));
  assert.equal(await harness.run(request), old);
  assert.deepEqual(harness.writes, []);
});

test('fresh application responses win and offline navigation has a fallback', async () => {
  const fresh = response('fresh');
  const harness = setup(async () => fresh);
  assert.equal(await harness.run(request), fresh);
  const offline = response('offline');
  const unavailable = setup(async () => { throw Error('offline'); }, new Map([['/offline.html', offline]]));
  assert.equal(await unavailable.run(request), offline);
});

test('API requests, other origins and unknown routes bypass the cache entirely', () => {
  const harness = setup(() => { throw Error('must not intercept'); });
  for (const item of [
    { url: 'https://mathnova.test/api/health', method: 'GET' },
    { url: 'https://mathnova.test/api/calculus/differentiate', method: 'POST' },
    { url: 'https://other.test/js/app.js', method: 'GET' },
    { url: 'https://mathnova.test/arbitrary-path', method: 'GET' }
  ]) {
    harness.events.fetch({ request: item, respondWith: () => assert.fail('must pass through') });
  }
});
