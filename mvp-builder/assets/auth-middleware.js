/**
 * Auth Middleware — Purchase Verification
 * ========================================
 * Checks if an email has a valid purchase record in KV.
 * Used to gate /app and /api/* routes.
 *
 * Usage in main worker:
 *   const email = getEmail(request);
 *   if (!await verifyPurchase(email, env)) return redirectToLanding(request);
 */

// Extract email from request (query param or cookie)
function getEmail(request) {
  const url = new URL(request.url);

  // 1. Check query parameter
  const emailParam = url.searchParams.get('email');
  if (emailParam) return emailParam.toLowerCase().trim();

  // 2. Check cookie
  const cookies = request.headers.get('Cookie') || '';
  const match = cookies.match(/fp_email=([^;]+)/);
  if (match) return decodeURIComponent(match[1]).toLowerCase().trim();

  return null;
}

// Verify email has a purchase record in KV
async function verifyPurchase(email, env) {
  if (!email) return false;
  try {
    const record = await env.CUSTOMERS.get(`email:${email}`);
    if (!record) return false;
    const data = JSON.parse(record);
    return data.status === 'purchased';
  } catch (e) {
    return false;
  }
}

// Redirect to landing page (for non-purchasers)
function redirectToLanding(request) {
  const url = new URL('/', request.url);
  return Response.redirect(url.toString(), 302);
}

// Set email cookie on first authenticated visit (so user doesn't need ?email= every time)
function setEmailCookie(email) {
  return {
    'Set-Cookie': `fp_email=${encodeURIComponent(email)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${60 * 60 * 24 * 365}`
  };
}

// Auth wrapper — use this to protect any route handler
// Returns { authed: true, email, headers } or calls redirectToLanding
async function requirePurchase(request, env) {
  const email = getEmail(request);
  if (!email || !await verifyPurchase(email, env)) {
    return { authed: false, redirect: redirectToLanding(request) };
  }
  return {
    authed: true,
    email,
    headers: setEmailCookie(email)
  };
}
