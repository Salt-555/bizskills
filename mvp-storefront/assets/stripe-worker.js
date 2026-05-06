/**
 * ALLMIND MVP — Storefront Worker (Simplified)
 * =============================================
 * Payment Link → Success → Download. No custom checkout.
 * Proxy handles Stripe. This worker handles delivery.
 *
 * SETUP:
 *   1. Create a Stripe Payment Link (see deploy steps in SKILL.md)
 *   2. Set after_completion redirect to: {BASE_URL}/success?session_id={CHECKOUT_SESSION_ID}
 *   3. Register webhook pointing to: {BASE_URL}/webhook
 *
 * BINDINGS (set by deploy script):
 *   PAYMENTS           — Service Binding → payment-proxy
 *   PAYMENT_HMAC_SECRET — Secret for proxy auth
 *   BASE_URL           — Plain text, this worker's URL
 *   RESEND_KEY         — Secret, for transactional emails
 *
 * ROUTES:
 *   GET  /         — Landing page (links to Payment Link)
 *   GET  /success  — Post-payment page (auto-downloads product)
 *   POST /webhook  — Stripe webhook (sends download email)
 *   GET  /download — Serves the purchased zip
 *   GET  /privacy  — Privacy policy
 *   GET  /terms    — Terms of service
 */

// ─── Payment Proxy Client ───
async function signPayload(body, secret) {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  return Array.from(new Uint8Array(sig)).map(b => b.toString(16).padStart(2, '0')).join('');
}

async function callProxy(env, route, payload) {
  const body = JSON.stringify(payload);
  const signature = await signPayload(body, env.PAYMENT_HMAC_SECRET);
  const resp = await env.PAYMENTS.fetch(new Request(`https://proxy${route}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Proxy-Signature': signature },
    body,
  }));
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

// ─── Helpers ───
function htmlResponse(html, status = 200) {
  return new Response(html, { status, headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
}
function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' } });
}

// ─── Route: GET /success ───
async function handleSuccess(request, env) {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get('session_id');
  let email = '';

  if (sessionId) {
    try {
      const sessionData = await callProxy(env, '/session', { session_id: sessionId });
      email = sessionData.email || '';
    } catch (e) {
      console.error(`[success] Session lookup failed: ${e.message}`);
    }
  }

  const downloadUrl = email ? `/download?email=${encodeURIComponent(email)}` : '#';
  const html = SUCCESS_PAGE_HTML
    .replace(/\{\{DOWNLOAD_URL\}\}/g, downloadUrl)
    .replace(/\{\{CUSTOMER_EMAIL\}\}/g, email);

  return htmlResponse(html);
}

// ─── Route: POST /webhook ───
async function handleWebhook(request, env) {
  let event;
  try { event = JSON.parse(await request.text()); }
  catch (e) { return jsonResponse({ error: 'Invalid payload' }, 400); }

  if (event.type === 'checkout.session.completed') {
    const session = event.data.object;
    let email = session.metadata?.email || session.customer_email || null;

    // Look up email from customer if not on session
    if (!email && session.customer) {
      try {
        const customerData = await callProxy(env, '/session', { session_id: session.id });
        email = customerData.email || null;
      } catch (e) {
        console.error(`[webhook] Email lookup failed: ${e.message}`);
      }
    }

    if (email) {
      await sendDownloadEmail(env, email);
    } else {
      console.error('[webhook] Could not determine customer email');
    }
  }

  return jsonResponse({ received: true });
}

// ─── Route: GET /download ───
async function handleDownload(request, env) {
  const url = new URL(request.url);
  const email = url.searchParams.get('email');
  if (!email) return htmlResponse('<h1>Email required</h1>', 400);

  if (typeof ZIP_DATA === 'undefined') return htmlResponse('<h1>Package not ready</h1>', 500);

  const zipBytes = Uint8Array.from(atob(ZIP_DATA), c => c.charCodeAt(0));
  return new Response(zipBytes, {
    status: 200,
    headers: {
      'Content-Type': 'application/zip',
      'Content-Disposition': 'attachment; filename="product.zip"',
      'Content-Length': zipBytes.length.toString(),
    },
  });
}

// ─── Email via Resend ───
async function sendDownloadEmail(env, email) {
  if (!env.RESEND_KEY) { console.log('[email] RESEND_KEY not set, skipping'); return; }

  const appUrl = `${env.BASE_URL}/app`;

  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${env.RESEND_KEY}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: '{{PRODUCT_NAME}} <noreply@yourdomain.com>',
      to: [email],
      subject: 'Your download is ready',
      html: `<div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:40px 24px">
        <h1 style="font-family:'Cormorant Garamond',serif;font-size:28px;margin-bottom:16px">You're in.</h1>
        <p style="color:#6B6560;font-size:15px;line-height:1.7;margin-bottom:24px">Thanks for your purchase. Your download is ready.</p>
        <a href="${appUrl}" style="display:inline-block;padding:14px 32px;background:#0A0A0A;color:#FAF7F2;text-decoration:none;font-size:12px;letter-spacing:.1em;text-transform:uppercase">Open App</a>
        <p style="color:#9B9590;font-size:13px;margin-top:24px">Bookmark this link: ${appUrl}</p>
        <hr style="border:none;border-top:1px solid #F0EBE3;margin:32px 0">
        <p style="color:#9B9590;font-size:12px">Works on any device with a browser.<br>Questions? support@yourdomain.com</p>
      </div>`,
    }),
  });

  if (!resp.ok) console.error(`[email] Failed: ${await resp.text()}`);
  else console.log(`[email] Download email sent to ${email}`);
}

// ─── Success Page HTML ───
const SUCCESS_PAGE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Download Ready</title>
<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', '{{META_PIXEL_ID}}');
fbq('track', 'PageView');
fbq('track', 'Purchase', {value: {{PRODUCT_PRICE}}, currency: 'USD'});
</script>
<noscript><img height="1" width="1" style="display:none"
src="https://www.facebook.com/tr?id={{META_PIXEL_ID}}&ev=PageView&noscript=1"/></noscript>
<!-- End Meta Pixel Code -->
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600&family=Inter:wght@300;400;500&display=swap');
:root{--cream:#FAF7F2;--gold:#C5A55A;--black:#0A0A0A;--stone:#6B6560;--stone-light:#9B9590}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;font-weight:300;line-height:1.7;color:#1A1A1A;background:var(--cream);display:flex;align-items:center;justify-content:center;min-height:100vh}
.container{max-width:520px;text-align:center;padding:24px}
.divider{width:48px;height:1px;background:var(--gold);margin:0 auto 32px}
h1{font-family:'Cormorant Garamond',serif;font-size:40px;font-weight:600;color:var(--black);margin-bottom:16px}
p{font-size:15px;color:var(--stone);margin-bottom:24px}
.download-btn{display:inline-block;padding:14px 32px;font-size:11px;font-weight:500;letter-spacing:.15em;text-transform:uppercase;background:var(--black);color:var(--cream);text-decoration:none;border-radius:2px;transition:background .3s}
.download-btn:hover{background:#2D2D2D}
.note{font-size:12px;color:var(--stone-light);margin-top:32px}
.manual-entry{margin-top:24px}
.manual-entry input{padding:10px 16px;font-size:14px;border:1px solid #ddd;border-radius:2px;width:280px;max-width:100%;font-family:'Inter',sans-serif}
.manual-entry button{padding:10px 20px;font-size:11px;font-weight:500;letter-spacing:.1em;text-transform:uppercase;background:var(--gold);color:var(--black);border:none;border-radius:2px;cursor:pointer;margin-left:8px}
</style></head><body>
<div class="container">
<div class="divider"></div>
<h1>You're in.</h1>
<p>Your download is ready. A copy has also been sent to your email.</p>
<a id="downloadBtn" href="{{DOWNLOAD_URL}}" class="download-btn">Download Package</a>
<div id="manualEntry" class="manual-entry" style="display:none">
<p>Something went wrong. Enter your purchase email:</p>
<input type="email" id="emailInput" placeholder="you@example.com">
<button onclick="window.location.href='/download?email='+encodeURIComponent(document.getElementById('emailInput').value)">Go</button>
</div>
<p class="note">Questions? <a href="mailto:support@yourdomain.com" style="color:var(--gold)">support@yourdomain.com</a></p>
</div>
<script>
if('{{DOWNLOAD_URL}}'=='#'){
  document.getElementById('downloadBtn').style.display='none';
  document.getElementById('manualEntry').style.display='block';
} else {
  setTimeout(function(){ window.location.href = '{{DOWNLOAD_URL}}'; }, 1500);
}
</script>
</body></html>`;

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
      if (path === '/') response = htmlResponse(LANDING_PAGE_HTML);
      else if (path === '/privacy') response = htmlResponse(PRIVACY_HTML);
      else if (path === '/terms') response = htmlResponse(TERMS_HTML);
      else if (request.method === 'GET' && path === '/success') response = await handleSuccess(request, env);
      else if (request.method === 'POST' && path === '/webhook') response = await handleWebhook(request, env);
      else if (request.method === 'GET' && path === '/download') response = await handleDownload(request, env);
      else response = jsonResponse({ error: 'Not found' }, 404);

      return addSecurityHeaders(response);
    } catch (e) {
      console.error(`Error: ${e.message}`);
      return addSecurityHeaders(jsonResponse({ error: 'Internal error' }, 500));
    }
  },
};
