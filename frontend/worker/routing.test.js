import assert from 'node:assert/strict';
import test from 'node:test';
import { MAX_RUN_BODY_BYTES, route } from './routing.js';

function setup({ visitorOk = true, siteOk = true } = {}) {
  const seen = [];
  const env = {
    ASSETS: { fetch: async (req) => new Response(`asset ${new URL(req.url).pathname}`) },
    RUN_LIMIT_VISITOR: { limit: async () => ({ success: visitorOk }) },
    RUN_LIMIT_SITE: { limit: async () => ({ success: siteOk }) },
  };
  const backend = () => ({ fetch: async (req) => {
    seen.push({ method: req.method, path: new URL(req.url).pathname, body: req.method === 'POST' ? await req.text() : null });
    return new Response('{"ok":true}', { headers: { 'content-type': 'application/json' } });
  } });
  return { env, backend, seen };
}
const req = (path, init) => new Request(`https://groundline.nethren.com${path}`, init);

test('static paths go to assets, never the backend', async () => {
  const { env, backend, seen } = setup();
  assert.equal(await (await route(req('/'), env, backend)).text(), 'asset /');
  assert.equal(await (await route(req('/data/dfw-layout.json'), env, backend)).text(), 'asset /data/dfw-layout.json');
  assert.equal(seen.length, 0);
});

test('allowed api routes are forwarded with /api stripped', async () => {
  const { env, backend, seen } = setup();
  for (const p of ['/api/health', '/api/scenarios/demo/counter', '/api/runs/abc123/events', '/api/runs/abc123/fuel-co2']) {
    assert.equal((await route(req(p), env, backend)).status, 200);
  }
  assert.equal((await route(req('/api/runs', { method: 'POST', body: '{"a":1}' }), env, backend)).status, 200);
  assert.deepEqual(seen.map((s) => s.path), ['/health', '/scenarios/demo/counter', '/runs/abc123/events', '/runs/abc123/fuel-co2', '/runs']);
  assert.equal(seen.at(-1).body, '{"a":1}');
});

test('other api routes are refused without reaching the backend', async () => {
  const { env, backend, seen } = setup();
  for (const [p, init] of [['/api/docs'], ['/api/scenarios/example'], ['/api/scenarios/demo/other'], ['/api/runs', {}], ['/api/health', { method: 'POST', body: '' }]]) {
    assert.equal((await route(req(p, init), env, backend)).status, 404, p);
  }
  assert.equal(seen.length, 0);
});

test('runs are rate limited per visitor and site-wide', async () => {
  for (const opts of [{ visitorOk: false }, { siteOk: false }]) {
    const { env, backend, seen } = setup(opts);
    const res = await route(req('/api/runs', { method: 'POST', body: '{}' }), env, backend);
    assert.equal(res.status, 429);
    assert.equal(seen.length, 0);
  }
});

test('oversized run bodies are refused', async () => {
  const { env, backend, seen } = setup();
  const res = await route(req('/api/runs', { method: 'POST', body: 'x'.repeat(MAX_RUN_BODY_BYTES + 1) }), env, backend);
  assert.equal(res.status, 413);
  assert.equal(seen.length, 0);
});
