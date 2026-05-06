---
name: mvp-freemium-paywall
description: "Add a client-side freemium paywall to an MVP served by a Cloudflare Worker using localStorage gating and Stripe Checkout. Use when an existing MVP needs a freemium model with some features free and others paywalled, and there is no backend session store."
required_environment_variables: []
metadata:
  hermes:
    tags: [mvp, paywall, freemium, stripe, cloudflare-workers]
---

# MVP Freemium Paywall

Add a client-side freemium paywall to a static HTML app served by a Cloudflare
Worker. Free tier stays fully functional; paid panels are gated with a lock card.
Purchase via Stripe Link sets a localStorage flag and redirects back with a
bypass parameter.

## When to use this

- The app is a single-page HTML shell inside a Cloudflare Worker (`APP_HTML`).
- There is **no backend session store** — server-side auth is not available.
- You want **feature-level gating** (e.g., tabs/panels) rather than a hard paywall.
- The price point is a **one-time payment** (not subscription).

## Decision: Client-side gating

Because the Worker serves static HTML with no session database, use:
- `localStorage.setItem('cc_unlocked', '1')` set on the Stripe success page.
- `URLSearchParams(location.search).get('access') === 'unlocked'` as a bypass
  for direct links from Stripe receipts or emails.

This is bypassable via dev tools, which is acceptable for an MVP.

## Steps

### 1. Inject paywall CSS

Add styles inside the `<style>` block of `APP_HTML`. Use a **structural** lock
card instead of an absolute overlay. Overlays with `backdrop-filter: blur()`
block clicks, create z-index wars, and break on mobile.

```css
.panel-body {
  display: none;
}
.panel-body.unlocked {
  display: block;
}
.lock-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 2rem;
  min-height: 50vh;
  gap: 0.5rem;
}
.lock-card h3 {
  margin-bottom: 0.25rem;
}
.paywall-btn {
  margin-top: 0.75rem;
  background: #C5A55A;
  color: #0A0A0A;
  padding: 0.6rem 1.2rem;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 600;
}
```

### 2. Wrap paid panels with paywall HTML

For each paid panel/tab (e.g., `#p-reverse`, `#p-supplies`, `#p-spells`), wrap
its content in a `.lock-card` and `.panel-body` structure:

```html
<div id="p-reverse" class="panel-content">
  <div class="lock-card">
    <h3>Unlock Full Access</h3>
    <p>Get all features for a one-time payment of $7.</p>
    <a href="https://buy.stripe.com/XXXXXXX" class="paywall-btn">Unlock Now</a>
  </div>
  <div class="panel-body">
    <!-- original panel content goes here -->
  </div>
</div>
```

**Leave the free tab untouched** (e.g., `#p-lookup`). Its content goes directly
inside the panel without `.lock-card` or `.panel-body` wrappers.

### 3. Replace tab switcher with unlock check

Remove or rename the old `switchTab` function. Add `checkUnlock()`:

```javascript
function checkUnlock() {
  const unlocked = localStorage.getItem('cc_unlocked') === '1' ||
                   new URLSearchParams(location.search).get('access') === 'unlocked';
  document.querySelectorAll('.panel-body').forEach(el => {
    el.classList.toggle('unlocked', unlocked);
  });
  document.querySelectorAll('.lock-card').forEach(el => {
    el.style.display = unlocked ? 'none' : 'flex';
  });
}
```

Update any `switchTab` calls to call `checkUnlock()` after tab switches.

### 4. Call checkUnlock on init

In the app init block, after building dynamic content:

```javascript
checkUnlock();
```

### 5. Update success page to unlock and redirect

On the Stripe success page HTML inside the Worker:

```javascript
localStorage.setItem('cc_unlocked', '1');
setTimeout(() => location.href = '/app', 2500);
```

Change the success page button to:

```html
<a href="/app" class="btn">Open Coven Compass</a>
```

### 6. Update Stripe `appUrl` with bypass param

In the Worker JS where `appUrl` is built for Stripe Checkout metadata:

```javascript
const appUrl = `${env.BASE_URL}/app?access=unlocked`;
```

This ensures post-purchase links from Stripe emails bypass the paywall.

### 7. Sync price across all surfaces

After changing the Stripe price, grep the Worker file for **all** price strings
(landing page hero, pricing comparison, bottom CTA, meta description, paywall
copy, success page) and sync them. Common spots:

- Hero CTA button text
- Pricing comparison card
- Bottom CTA button text
- Meta description / OG tags
- Paywall overlay copy
- Success page copy

Use a single search-and-verify pass:

```bash
grep -oE '\$7|\$12' src/worker.js   # should show only $7, zero $12
```

## Verification

After deploying the Worker:

### Confirm paywall is NOT on the landing page

```bash
curl -s https://YOURDOMAIN/ | grep -oE 'paywall|Unlock Full Access|panel-content|switchTab'
# Expected: empty output
```

### Confirm paywall IS on the app route

```bash
curl -s https://YOURDOMAIN/app | grep -oE 'lock-card|Unlock Full Access|checkUnlock|cc_unlocked'
# Expected: multiple hits
```

### Confirm free tab is untouched

```bash
curl -s https://YOURDOMAIN/app | grep -A3 'id="p-lookup"'
# Expected: no paywall overlay inside this panel
```

### Confirm success page sets localStorage

```bash
curl -s 'https://YOURDOMAIN/success?session_id=test' | grep -oE 'cc_unlocked|localStorage'
# Expected: hits present
```

## Paywall Patterns

### Tab-based gating (structural lock cards)
Best for apps with multiple independent panels/tabs. See Steps 1–3 above.
Free tab is untouched; paid tabs show a `.lock-card` that hides when unlocked.

### Screen-based funnel gating (overlay on specific screens)
Best for linear multi-screen flows (wizard / funnel). The paywall is a
full-screen overlay `<div>` inside a specific screen's HTML, controlled by
`display: none/flex` via JavaScript.

Screen-based paywall logic is typically scattered across **5 locations**:
1. **HTML overlay** — the `<div id="paywallOverlay">` inside the target screen
2. **CSS blur/lock class** — `.locked-content { filter: blur(10px); opacity: 0.4; }`
3. **Navigation gating** — base `goTo(screen)` blocks screens `>= N` unless unlocked
4. **Navigation override** — a wrapper `goTo = function(screen) { ... }` that also checks unlock
5. **State application** — `applyPaywallState()` toggles overlay, blur classes, and button text

To **move** a screen-based paywall (e.g. from Screen 3 to Screen 7), you must
patch all 5 locations coherently. Removing the overlay from Screen 3 but leaving
the nav gating in place will leave users stranded.

## Pitfalls

1. **Source of truth is `worker.js`, not `app.html`** — The repo may contain a
   standalone `app.html` that looks like the deployed app, but the live version
   is the `APP_HTML` string constant inside `worker.js`. Editing `app.html` has
   no effect. Always patch `worker.js`.
2. **Do not put paywall markup on the landing page (`/`)** — only on the app
   route (`/app`). Landing page should remain clean marketing HTML.
3. **Browser cache** — After deploy, a hard refresh (Ctrl+Shift+R) may be needed
   to see changes. Verify via `curl` to rule out cache.
4. **Orphan Stripe prices** — Each deploy that creates new Stripe Price objects
   will orphan old ones. Fix the deploy script to reuse an existing Price ID
   instead of creating new ones.
5. **Price drift** — Stripe price, landing page copy, paywall copy, and Meta
   Pixel value can diverge. Always grep for all dollar amounts after any price
   change.
6. **Tab state without init** — If `checkUnlock()` is not called after dynamic
   content is built, paid tabs may appear unlocked briefly or not gate correctly.
7. **Never use absolute overlay paywalls** — `position: absolute` with
   `backdrop-filter: blur()` blocks click events, creates z-index wars, and
   breaks layout consistency on mobile and across browsers. Use structural
   lock cards (`.lock-card` + `.panel-body`) in normal document flow instead.
   *(Exception: screen-based funnel overlays are acceptable when they replace
   the entire screen content rather than hovering over interactive elements.)*
8. **Cloudflare strips backslash escapes in template literals** — Inside the
   `APP_HTML` string of a Cloudflare Worker, `\'` gets stripped to `'`, breaking
   selectors like `document.querySelector('[data-tab=\'reverse\']')`. Avoid
   escaping single quotes entirely. Use `data-tab` attributes and select by
   `el.dataset.tab` instead of string-matching selectors with quotes.
9. **Success page is also inside `worker.js`** — The Stripe success page is
   typically a separate constant like `SUCCESS_PAGE_HTML` in the same Worker
   file, not a standalone file. Update it there when changing unlock logic or
   post-purchase redirects.

## Landing Page Preview-Blur Teaser

A distinct pattern from the app paywall: show a working demo on the landing page with some results visible, then blur the remaining results behind a frosted glass overlay with a centered purchase CTA. This converts cold traffic before sign-up. Full details: see `references/landing-page-blur-teaser.md`. 

**Critical rule:** Overlay positioning must always be calculated programmatically via JS measuring the DOM position of the first blurred card. Hardcoded pixel values (e.g., `top:110px`) will break on different screen sizes and content lengths. The user explicitly requires programmatic placement.

## Example file

`~/.hermes/mvps/coven-compass/src/worker.js` contains a working implementation
of this pattern.
