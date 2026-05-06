/**
 * Combined Worker Template — Storefront + Product (Proxy Architecture)
 * =====================================================================
 * Merges mvp-storefront routes with product routes in a single Worker.
 * Uses Service Binding to payment-proxy proxy — NO Stripe key here.
 *
 * TEMPLATE INSTRUCTIONS:
 * 1. Start with a deployed storefront worker (from mvp-storefront skill)
 * 2. The payment proxy handles Stripe session lookup (deployed via deploy_worker.py proxy)
 * 3. Landing page links directly to Stripe Payment Link — no /checkout handler
 * 4. Add product-specific routes and handlers
 * 4. Replace all {{PLACEHOLDER}} values
 *
 * REQUIRED BINDINGS (set by deploy script):
 *   PAYMENTS           — Service Binding → payment-proxy
 *   PAYMENT_HMAC_SECRET — Secret for proxy auth
 *   STRIPE_PRICE_ID    — Plain text, price for checkout
 *   BASE_URL           — Plain text, this worker's URL
 *   CUSTOMERS          — KV namespace
 *   SALES_TRACKING     — KV namespace
 */

// ─── Payment Proxy Client ───
async function signPayload(body, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' },
    false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function callProxy(env, route, payload) {
  const body = JSON.stringify(payload);
  const signature = await signPayload(body, env.PAYMENT_HMAC_SECRET);
  const proxyReq = new Request(`https://proxy${route}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Proxy-Signature': signature },
    body,
  });
  const resp = await env.PAYMENTS.fetch(proxyReq);
  const data = await resp.json();
  if (!resp.ok || !data.success) throw new Error(data.error || `Proxy error ${resp.status}`);
  return data.data;
}

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

// ─── Response Helpers ───
function jsonResponse(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*', ...extraHeaders },
  });
}

function htmlResponse(html, extraHeaders = {}) {
  return new Response(html, {
    headers: { 'Content-Type': 'text/html;charset=UTF-8', ...extraHeaders },
  });
}

// ═══════════════════════════════════════════
// AUTH FUNCTIONS
// ═══════════════════════════════════════════

function getEmail(request) {
  const url = new URL(request.url);
  const emailParam = url.searchParams.get('email');
  if (emailParam) return emailParam.toLowerCase().trim();
  const cookies = request.headers.get('Cookie') || '';
  const match = cookies.match(/fp_email=([^;]+)/);
  if (match) return decodeURIComponent(match[1]).toLowerCase().trim();
  return null;
}

async function verifyPurchase(email, env) {
  if (!email) return false;
  try {
    const record = await env.CUSTOMERS.get(`email:${email}`);
    if (!record) return false;
    const data = JSON.parse(record);
    return data.status === 'purchased';
  } catch (e) { return false; }
}

// Cookie scoped to THIS subdomain only — never .yourdomain.com
function setEmailCookie(email, hostname) {
  const domain = hostname || '';
  return `fp_email=${encodeURIComponent(email)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=${60 * 60 * 24 * 365}`;
}

// ═══════════════════════════════════════════
// STOREFRONT HANDLERS
// ═══════════════════════════════════════════

// No checkout handler — landing page links directly to Stripe Payment Link
// Payment Link URL is set in landing page HTML via {{PAYMENT_LINK_URL}}

async function handleWebhook(request, env) {
  let event;
  try { event = JSON.parse(await request.text()); } catch (e) { return jsonResponse({ error: 'Invalid payload' }, 400); }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    let email = session.metadata?.email || session.customer_email || null;

    if (!email && session.customer) {
      try {
        const customerData = await callProxy(env, '/session', { session_id: session.id });
        email = customerData.email || null;
      } catch (e) {
        console.error(`[webhook] Email lookup failed: ${e.message}`);
      }
    }

    if (email) {
      // Store purchase record
      const record = {
        email,
        stripeCustomerId: session.customer,
        paymentIntentId: session.payment_intent,
        status: 'purchased',
        purchasedAt: new Date().toISOString(),
      };
      await env.CUSTOMERS.put(`email:${email}`, JSON.stringify(record));
      await env.CUSTOMERS.put(`stripe:${session.customer}`, email);

      // Sales tracking (optional)
      if (env.SALES_TRACKING) {
        const productId = session.metadata?.product || '{{PRODUCT_NAME}}';
        let tracking = JSON.parse(await env.SALES_TRACKING.get(productId) || '{"total_sales":0,"revenue_cents":0,"sales":[]}');
        tracking.total_sales += 1;
        tracking.revenue_cents += session.amount_total;
        tracking.last_sale_at = new Date().toISOString();
        await env.SALES_TRACKING.put(productId, JSON.stringify(tracking));
      }
    }
  }
  return jsonResponse({ received: true });
}

async function handleSuccess(request, env) {
  const sessionId = new URL(request.url).searchParams.get('session_id');
  let email = '';
  if (sessionId) {
    try {
      const sessionData = await callProxy(env, '/session', { session_id: sessionId });
      email = sessionData.email || '';
    } catch (e) {
      console.error(`[success] Session lookup failed: ${e.message}`);
    }
  }
  return htmlResponse(successPage(email));
}

// ═══════════════════════════════════════════
// ★ PRODUCT HANDLERS
// ═══════════════════════════════════════════

function appPage(email) {
  // Return app-shell.html with {{MAIN_CONTENT}} and {{APP_SCRIPT}} filled in
  return `<!-- Load assets/app-shell.html template and fill placeholders -->`;
}

function successPage(email) {
  const downloadUrl = email ? `/download?email=${encodeURIComponent(email)}` : '#';
  // Return success page HTML with auto-download trigger
  return `<!-- Success page: download_url=${downloadUrl}, email=${email} -->`;
}

function landingPage(env) {
  // Landing page with Payment Link — no /checkout call, just <a href="PAYMENT_LINK_URL">
  return `<!-- Landing page with Payment Link -->`;
}

async function handleApi(request, env, email, path) {
  const method = request.method;

  if (method === 'GET' && path === '/api/items') {
    const list = await env.CUSTOMERS.list({ prefix: `data:${email}:` });
    const items = [];
    for (const key of list.keys) {
      const val = await env.CUSTOMERS.get(key.name);
      if (val) items.push(JSON.parse(val));
    }
    return jsonResponse({ items });
  }

  if (method === 'POST' && path === '/api/items') {
    const body = await request.json();
    const id = crypto.randomUUID();
    const item = { id, ...body, createdAt: new Date().toISOString(), email };
    await env.CUSTOMERS.put(`data:${email}:${id}`, JSON.stringify(item));
    return jsonResponse({ item }, 201);
  }

  const deleteMatch = path.match(/^\/api\/items\/([a-f0-9-]+)$/);
  if (method === 'DELETE' && deleteMatch) {
    await env.CUSTOMERS.delete(`data:${email}:${deleteMatch[1]}`);
    return jsonResponse({ deleted: true });
  }

  return jsonResponse({ error: 'Not found' }, 404);
}

// ═══════════════════════════════════════════
// ★ ROUTER
// ═══════════════════════════════════════════

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    try {
      let response;

      // Public storefront routes
      if (path === '/' || path === '') response = htmlResponse(landingPage(env));
      else if (path === '/privacy') response = htmlResponse(privacyPage());
      else if (path === '/terms') response = htmlResponse(termsPage());
      else if (request.method === 'GET' && path === '/success') response = await handleSuccess(request, env);
      else if (request.method === 'POST' && path === '/webhook') response = await handleWebhook(request, env);

      // Product routes (auth required)
      else if (path === '/app' || path.startsWith('/api/')) {
        const email = getEmail(request);
        const authed = await verifyPurchase(email, env);
        if (!authed) {
          response = Response.redirect(new URL('/', request.url).toString(), 302);
        } else {
          const cookieHeader = { 'Set-Cookie': setEmailCookie(email, url.hostname) };
          if (path === '/app') response = htmlResponse(appPage(email), cookieHeader);
          else response = await handleApi(request, env, email, path);
        }
      }

      else response = jsonResponse({ error: 'Not found' }, 404);

      return addSecurityHeaders(response);
    } catch (e) {
      console.error(`Error: ${e.message}`);
      return addSecurityHeaders(jsonResponse({ error: 'Internal error' }, 500));
    }
  },
};
