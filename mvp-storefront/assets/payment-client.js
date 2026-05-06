/**
 * ALLMIND Payment Client
 * ======================
 * Include this in MVP workers that need payments.
 * Calls the payment proxy via Service Binding (env.PAYMENTS).
 *
 * SETUP: Worker must have a Service Binding named "PAYMENTS"
 *        pointing to the "payment-proxy" proxy worker.
 *        Plus a secret binding: PAYMENT_HMAC_SECRET
 *
 * USAGE:
 *   import { createCheckout, createCustomer, refund } from './payment-client.js';
 *   // or inline it (this file is designed to be pasted into worker code)
 */

// ─── HMAC Signature ───
async function signPayload(body, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' },
    false, ['sign']
  );
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

// ─── Proxy Caller ───
async function callProxy(env, route, payload) {
  if (!env.PAYMENTS) throw new Error('Service Binding "PAYMENTS" not configured');
  if (!env.PAYMENT_HMAC_SECRET) throw new Error('PAYMENT_HMAC_SECRET not set');

  const body = JSON.stringify(payload);
  const signature = await signPayload(body, env.PAYMENT_HMAC_SECRET);

  // Service Binding: direct RPC, no HTTP. Build a synthetic Request.
  const proxyReq = new Request(`https://proxy${route}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Proxy-Signature': signature,
    },
    body,
  });

  const resp = await env.PAYMENTS.fetch(proxyReq);
  const data = await resp.json();

  if (!resp.ok || !data.success) {
    throw new Error(data.error || `Proxy error ${resp.status}`);
  }
  return data.data;
}

// ─── Public API ───

export async function createCheckout(env, { email, priceId, successUrl, cancelUrl, metadata = {} }) {
  return callProxy(env, '/checkout', {
    email,
    price_id: priceId,
    success_url: successUrl,
    cancel_url: cancelUrl,
    metadata,
  });
}

export async function createCustomer(env, email) {
  return callProxy(env, '/customer', { email });
}

export async function charge(env, { customerId, amountCents, currency, description, paymentMethodId }) {
  return callProxy(env, '/charge', {
    customer_id: customerId,
    amount_cents: amountCents,
    currency,
    description,
    payment_method_id: paymentMethodId,
  });
}

export async function refund(env, { paymentIntentId, amountCents }) {
  return callProxy(env, '/refund', {
    payment_intent_id: paymentIntentId,
    amount_cents: amountCents,
  });
}
