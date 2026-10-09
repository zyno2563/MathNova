import test from 'node:test';
import assert from 'node:assert/strict';

test('printing expands all working and restores the reader’s disclosure choices', async () => {
  const handlers = new Map();
  const details = [{ open: false }, { open: true }, { open: false }];
  globalThis.window = { addEventListener: (type, callback) => handlers.set(type, callback) };
  globalThis.document = { querySelectorAll: () => details };
  await import('../frontend/js/result-actions.js');
  handlers.get('beforeprint')();
  assert.ok(details.every(node => node.open));
  // Browser preview settings can fire beforeprint again.
  handlers.get('beforeprint')();
  handlers.get('afterprint')();
  assert.deepEqual(details.map(node => node.open), [false, true, false]);
  handlers.get('beforeprint')();
  handlers.get('afterprint')();
  assert.deepEqual(details.map(node => node.open), [false, true, false]);
});
