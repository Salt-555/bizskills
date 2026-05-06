/**
 * ALLMIND MVP — Market Testing Worker
 * =====================================
 * Lightweight storefront for demand validation.
 * Landing page + email capture. No Stripe, no checkout, no download.
 *
 * BINDINGS (set by deploy script):
 *   SIGNUPS     — KV namespace for email capture
 *   BASE_URL    — Plain text, this worker's URL
 *
 * ROUTES:
 *   GET  /          — Landing page with email capture form
 *   POST /signup    — Stores email in KV
 *   GET  /count     — Returns signup count (for quick checks)
 *   GET  /privacy   — Privacy policy
 *   GET  /terms     — Terms of service
 *
 * When validated, redeploy as full-storefront (stripe-worker.js)
 * on the same worker. Same URL, no ad breakage.
 */

// ─── Security Headers ───
const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};
function addSecurityHeaders(response) {
  for (const [k, v] of Object.entries(securityHeaders)) response.headers.set(k, v);
  return response;
}

// ─── Helpers ───
function htmlResponse(html, status = 200) {
  return new Response(html, { status, headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
}
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } });
}

// ─── Route: POST /signup ───
async function handleSignup(request, env) {
  let body;
  try { body = await request.json(); }
  catch (e) { return jsonResponse({ error: 'Invalid JSON' }, 400); }

  const email = (body.email || '').trim().toLowerCase();
  if (!email || !email.includes('@')) return jsonResponse({ error: 'Valid email required' }, 400);

  // Check if already signed up
  const existing = await env.SIGNUPS.get(email);
  if (existing) return jsonResponse({ success: true, message: 'Already signed up', duplicate: true });

  // Store signup
  const record = JSON.stringify({
    email,
    signed_up_at: new Date().toISOString(),
    source: body.source || 'landing_page',
    utm_source: body.utm_source || null,
    utm_medium: body.utm_medium || null,
    utm_campaign: body.utm_campaign || null,
  });

  await env.SIGNUPS.put(email, record);

  // Increment counter
  let count = parseInt(await env.SIGNUPS.get('__count__') || '0');
  count++;
  await env.SIGNUPS.put('__count__', count.toString());

  return jsonResponse({ success: true, count });
}

// ─── Route: GET /count ───
async function handleCount(env) {
  const count = parseInt(await env.SIGNUPS.get('__count__') || '0');
  return jsonResponse({ count });
}

// ─── Router ───
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET, POST, OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type' } });
    }

    try {
      let response;
      if (path === '/' && request.method === 'GET') response = htmlResponse(LANDING_PAGE_HTML);
      else if (path === '/signup' && request.method === 'POST') response = await handleSignup(request, env);
      else if (path === '/count' && request.method === 'GET') response = await handleCount(env);
      else if (path === '/privacy' && request.method === 'GET') response = htmlResponse(PRIVACY_HTML);
      else if (path === '/terms' && request.method === 'GET') response = htmlResponse(TERMS_HTML);
      else response = jsonResponse({ error: 'Not found' }, 404);

      return addSecurityHeaders(response);
    } catch (e) {
      console.error(`Error: ${e.message}`);
      return addSecurityHeaders(jsonResponse({ error: 'Internal error' }, 500));
    }
  },
};
