import test from 'node:test';
import assert from 'node:assert/strict';
import { post } from '../frontend/js/api.js';

test('stalled requests time out and can be retried', async t => {
  t.mock.method(globalThis, 'fetch', (_path, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
  }));
  await assert.rejects(post('/api/example', {}, { timeoutMs: 10 }), { code: 'request_timeout' });
  globalThis.fetch.mock.mockImplementation(async () => ({ ok: true, json: async () => ({ ok: true, result: 3 }) }));
  assert.equal(await post('/api/example', {}), 3);
});

test('cancellation has a distinct error from server failure', async t => {
  t.mock.method(globalThis, 'fetch', (_path, { signal }) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
  }));
  const controller = new AbortController();
  const pending = post('/api/example', {}, { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { code: 'request_cancelled' });
});

test('deadline also covers a stalled response body', async t => {
  t.mock.method(globalThis, 'fetch', async (_path, { signal }) => ({
    ok: true,
    json: () => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
    })
  }));
  await assert.rejects(post('/api/example', {}, { timeoutMs: 10 }), { code: 'request_timeout' });
});

test('server validation messages remain intact', async t => {
  t.mock.method(globalThis, 'fetch', async () => ({
    ok: false, status: 400,
    json: async () => ({ ok: false, error: { code: 'invalid_input', message: 'Check the matrix rows.' } })
  }));
  await assert.rejects(post('/api/example', {}), { code: 'invalid_input', message: 'Check the matrix rows.', status: 400 });
});
