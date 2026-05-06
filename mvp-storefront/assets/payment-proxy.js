/**
 * ALLMIND Payment Proxy Worker
 * ============================
 * Central payment service. Holds the ONE Stripe key.
 * All MVP workers call this via Service Bindings.
 * Traffic never leaves Cloudflare's network.
 *
 * SETUP:
 *   1. Deploy this worker ONCE: payment-proxy
 *   2. Bind it to MVP workers via Service Binding (deploy script handles this)
 *   3. Set secrets via deploy script metadata (STRIPE_SECRET_KEY, PAYMENT_HMAC_SECRET)
 *
 * CALLED BY MVP WORKERS VIA SERVICE BINDING:
 *   env.PAYMENTS.fetch(request)  — direct RPC, no HTTP overhead
 *
 * ROUTES:
 *   POST /checkout    — Create Stripe Checkout session
 *   POST /session     — Retrieve checkout session by ID (for success page email)
 *   POST /charge      — Direct charge (for server-side payments)
 *   POST /refund      — Refund a payment
 *   POST /customer    — Create/get Stripe customer
 *   GET  /health      — Liveness check (no auth needed)
 *
 * AUTH: HMAC-SHA256 signature in X-Proxy-Signature header.
 *       Body = JSON payload. Signature = HMAC(secret, body).
 */

const STRIPE_API = 'https://api.stripe.com/v1';

// ─── HMAC Verification ───
async function verifySignature(body, signature, secret) {
  if (!signature || !secret) return false;
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' },
    false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const expected = Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
  return expected === signature;
}

// ─── Stripe API Helper ───
async function stripeFetch(env, method, path, params = {}) {
  const url = `${STRIPE_API}/${path}`;
  const opts = {
    method,
    headers: {
      'Authorization': `Bearer ${env.STRIPE_SECRET_KEY}`,
    },
  };
  if (method !== 'GET' && method !== 'DELETE') {
    opts.headers['Content-Type'] = 'application/x-www-form-urlencoded';
    opts.body = new URLSearchParams(params).toString();
  }
  const resp = await fetch(url, opts);
  const data = await resp.json();
  if (!resp.ok) {
    throw new Error(data.error?.message || `Stripe ${resp.status}`);
  }
  return data;
}

// ─── Handlers ───

async function handleCheckout(env, payload) {
  const { email, price_id, success_url, cancel_url, metadata = {} } = payload;
  if (!price_id) throw new Error('price_id required');

  // If email provided, get/create Stripe customer (legacy flow)
  // If no email, skip customer creation — Stripe collects email during checkout
  let customerId = payload.customer_id || null;
  if (!customerId && email) {
    const customer = await stripeFetch(env, 'POST', 'customers', { email });
    customerId = customer.id;
  }

  const params = {
    mode: 'payment',
    'line_items[0][price]': price_id,
    'line_items[0][quantity]': '1',
    success_url,
    cancel_url,
    // Always create a Stripe customer from checkout email
    customer_creation: 'always',
  };
  if (customerId) params.customer = customerId;

  // Flatten metadata
  for (const [k, v] of Object.entries(metadata)) {
    params[`metadata[${k}]`] = v;
  }
  if (email) params['metadata[email]'] = email;

  const session = await stripeFetch(env, 'POST', 'checkout/sessions', params);
  return { url: session.url, session_id: session.id, customer_id: customerId };
}

async function handleCharge(env, payload) {
  const { customer_id, amount_cents, currency = 'usd', description = '' } = payload;
  if (!customer_id || !amount_cents) throw new Error('customer_id and amount_cents required');

  return await stripeFetch(env, 'POST', 'payment_intents', {
    customer: customer_id,
    amount: String(amount_cents),
    currency,
    description,
    confirm: 'true',
    payment_method: payload.payment_method_id,
  });
}

async function handleRefund(env, payload) {
  const { payment_intent_id, amount_cents } = payload;
  if (!payment_intent_id) throw new Error('payment_intent_id required');

  const params = { payment_intent: payment_intent_id };
  if (amount_cents) params.amount = String(amount_cents);

  return await stripeFetch(env, 'POST', 'refunds', params);
}

async function handleSession(env, payload) {
  const { session_id } = payload;
  if (!session_id) throw new Error('session_id required');

  const session = await stripeFetch(env, 'GET', `checkout/sessions/${session_id}`);
  let email = session.customer_email || session.metadata?.email || null;

  // If email not on session, look it up from the customer object
  if (!email && session.customer) {
    try {
      const customer = await stripeFetch(env, 'GET', `customers/${session.customer}`);
      email = customer.email || null;
    } catch (e) {
      console.error(`[session] Customer lookup failed: ${e.message}`);
    }
  }

  return {
    email,
    status: session.payment_status,
    customer_id: session.customer,
  };
}

async function handleCustomer(env, payload) {
  const { email } = payload;
  if (!email) throw new Error('email required');

  // Search for existing customer
  const search = await stripeFetch(env, 'GET', `customers?email=${encodeURIComponent(email)}&limit=1`);
  if (search.data.length > 0) {
    return { id: search.data[0].id, created: false };
  }
  // Create new
  const customer = await stripeFetch(env, 'POST', 'customers', { email });
  return { id: customer.id, created: true };
}

// ─── Router ───

export default {
  async fetch(request, env) {
    // Health check — no auth needed
    if (request.method === 'GET' && new URL(request.url).pathname === '/health') {
      return new Response(JSON.stringify({ status: 'ok', service: 'payment-proxy' }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (request.method !== 'POST') {
      return jsonResponse({ error: 'POST only (except /health)' }, 405);
    }

    const path = new URL(request.url).pathname;

    try {
      // Read body for HMAC verification
      const body = await request.text();
      const signature = request.headers.get('X-Proxy-Signature');

      // Verify HMAC (skip for health)
      if (!env.PAYMENT_HMAC_SECRET) {
        return jsonResponse({ error: 'Proxy misconfigured: no HMAC secret' }, 500);
      }
      const valid = await verifySignature(body, signature, env.PAYMENT_HMAC_SECRET);
      if (!valid) {
        return jsonResponse({ error: 'Invalid signature' }, 401);
      }

      const payload = JSON.parse(body);
      let result;

      switch (path) {
        case '/checkout':
          result = await handleCheckout(env, payload);
          break;
        case '/session':
          result = await handleSession(env, payload);
          break;
        case '/charge':
          result = await handleCharge(env, payload);
          break;
        case '/refund':
          result = await handleRefund(env, payload);
          break;
        case '/customer':
          result = await handleCustomer(env, payload);
          break;
        default:
          return jsonResponse({ error: 'Unknown route' }, 404);
      }

      return jsonResponse({ success: true, data: result });

    } catch (e) {
      console.error(`Proxy error: ${e.message}`);
      // Never leak Stripe errors to callers — log internally only
      return jsonResponse({ error: 'Payment processing failed' }, 500);
    }
  },
};

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}
