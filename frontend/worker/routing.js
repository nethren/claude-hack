// Request routing for the hosted Groundline site, kept free of Cloudflare
// imports so it can be tested with node --test.
//
// Static files come from the assets binding. /api/* goes to the live backend
// container with the /api prefix removed, but only for the routes the app
// uses. Starting a run costs real model calls, so POST /runs is rate limited
// per visitor and across the whole site, and its body size is capped.

export const MAX_RUN_BODY_BYTES = 256 * 1024;

const ALLOWED = [
  ['GET', /^\/health$/],
  ['GET', /^\/scenarios\/demo\/(clear|counter|escalate)$/],
  ['POST', /^\/runs$/],
  ['GET', /^\/runs\/[A-Za-z0-9_-]{1,64}\/(events|fuel-co2)$/],
];

function json(status, detail, headers = {}) {
  return new Response(JSON.stringify({ detail }), {
    status, headers: { 'content-type': 'application/json', 'cache-control': 'no-store', ...headers },
  });
}

export async function route(request, env, backend) {
  const url = new URL(request.url);
  if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);

  const path = url.pathname.slice(4);
  if (!ALLOWED.some(([method, pattern]) => method === request.method && pattern.test(path))) {
    return json(404, 'Not found');
  }

  if (request.method === 'POST') {
    const visitor = request.headers.get('cf-connecting-ip') || 'unknown';
    const [mine, everyone] = await Promise.all([
      env.RUN_LIMIT_VISITOR.limit({ key: visitor }),
      env.RUN_LIMIT_SITE.limit({ key: 'site' }),
    ]);
    if (!mine.success || !everyone.success) {
      return json(429, 'Too many runs right now. Wait a minute and try again.', { 'retry-after': '60' });
    }
    const declared = Number(request.headers.get('content-length') || 0);
    if (declared > MAX_RUN_BODY_BYTES) return json(413, 'Scenario too large');
    const body = await request.arrayBuffer();
    if (body.byteLength > MAX_RUN_BODY_BYTES) return json(413, 'Scenario too large');
    url.pathname = path;
    return backend().fetch(new Request(url, { method: 'POST', headers: request.headers, body }));
  }

  url.pathname = path;
  return backend().fetch(new Request(url, request));
}
