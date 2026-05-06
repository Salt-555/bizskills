---
name: mvp-builder
description: "Build the actual product for an MVP. Breaks ideas into atomic chunks, builds chunk-by-chunk, and wires into an existing storefront. Use when asked to build a product, implement an idea, or after mvp-storefront deploys."
version: 1.0.0
author: ALLMIND
license: proprietary
platforms: [linux]
compatibility: Requires deployed storefront (from mvp-storefront skill), Cloudflare account, and Python 3.11+
metadata:
  hermes:
    tags: [business, development, cloudflare, stripe]
    related_skills: [mvp-storefront, cloudflare-api, writing-plans, subagent-driven-development, systematic-debugging]
    requires_tools: [terminal]
required_environment_variables:
  - name: CLOUDFLARE_TOKEN
    prompt: Cloudflare API token
    help: Create at https://dash.cloudflare.com/profile/api-tokens with Workers permissions
    required_for: Worker deployment via Cloudflare REST API
  - name: STRIPE_SECRET_KEY
    prompt: Stripe secret key
    help: Get from https://dashboard.stripe.com/apikeys (starts with sk_)
    required_for: Creating Stripe prices when adjusting product pricing
---

# MVP Builder

Break an idea into chunks. Plan the build. Execute chunk by chunk. Wire into storefront.

## Trigger
"Build the product for X", "implement this idea", or after mvp-storefront deploys.

## Prerequisites
- A business idea (from business-ideas.json or user description)
- **Deployed storefront FIRST** (from mvp-storefront skill) — this is mandatory, not optional
  - The storefront defines the contract: KV schema, payment lifecycle, download flow
  - Storefront uses Stripe Payment Link — no custom checkout handler needed
  - Building product before storefront means guessing at integration surface — wrong order
  - Exception: standalone APIs with no checkout (rare). Even then, deploy storefront stub first.
- **Local source repo exists** at `~/.hermes/mvps/{script-name}/`
  - Expected structure (created by mvp-storefront):
    ```
    ~/.hermes/mvps/{script-name}/
    ├── README.md
    ├── src/
    │   └── worker.js          # Combined storefront + product worker
    ├── assets/
    │   └── product.html       # Downloadable product (if applicable)
    └── deploy-metadata.json   # KV IDs, Stripe IDs, URLs
    ```
  - If missing (legacy deploy), pull source from CF first, create repo retroactively
  - All product code goes in `src/` — never build in /tmp without saving to repo

## Phase 1: Decompose the Idea

Take the raw idea and extract exactly what the product DOES.

### 1a. Define the Core Loop
Every product has one core loop -- the thing the user does repeatedly.
Write it as: USER does ACTION to get OUTCOME.

Examples:
- "User enters a URL, gets a report on competitor pricing"
- "User connects Stripe, gets Slack alerts when webhooks fail"
- "User starts a timer, sees deep work hours tracked over time"

If you can't state the core loop in one sentence, the scope is too big. Cut.

### 1b. Identify the Atomic Units
Break the core loop into the smallest possible pieces:

```
CORE LOOP: "User enters a URL, gets a pricing page analysis"

ATOMS:
1. Input: Accept a URL from user
2. Fetch: Scrape the target page HTML
3. Extract: Pull pricing tiers, prices, feature lists from HTML
4. Format: Structure extracted data into readable report
5. Display: Show report to user in clean UI
6. Store: Save report to user's history
```

Each atom should be:
- Independently testable
- ~30 min to build
- One clear input -> one clear output

### 1c. Identify Dependencies
Map which atoms depend on which:

```
1 (Input) -> 2 (Fetch) -> 3 (Extract) -> 4 (Format) -> 5 (Display)
                                                    \-> 6 (Store)
```

Atoms without dependencies can be built in parallel.

### 1d. Classify the Tech for Each Atom

For each atom, determine:
- **Frontend only** -- HTML/JS in browser, no API needed
- **API route** -- Worker handles request, returns data
- **External API call** -- Worker calls a third-party API
- **KV read/write** -- Data storage in Cloudflare KV
- **Cron job** -- Runs on schedule, no user trigger
- **External dependency** -- Needs something we can't build (OAuth app, paid API key, etc.)

Flag any atom that has an external dependency -- that's a human blocker.

## Phase 2: Battle Plan

### 2a. Write the Plan Document

Load the `writing-plans` skill: `skill_view("writing-plans")`. Follow its methodology to create the implementation plan -- it enforces bite-sized tasks (2-5 min each), exact file paths, copy-pasteable code, and verification steps for each task.

Create a markdown plan at `/tmp/{product-id}-battle-plan.md`:

```markdown
# {Product Name} — Battle Plan

## Core Loop
{one sentence}

## Atoms
| # | Name | Type | Depends On | Est. Time | Status |
|---|------|------|------------|-----------|--------|
| 1 | Accept URL input | Frontend | — | 15m | pending |
| 2 | Scrape target page | API route | 1 | 30m | pending |
| 3 | Extract pricing data | API route | 2 | 45m | pending |
| 4 | Format report | API route | 3 | 20m | pending |
| 5 | Display report UI | Frontend | 4 | 30m | pending |
| 6 | Save to history | KV write | 4 | 15m | pending |

## Build Order
Round 1 (no deps): [1]
Round 2 (needs round 1): [2]
Round 3 (needs round 2): [3]
Round 4 (needs round 3): [4, 6] (parallel)
Round 5 (needs round 4): [5]

## Blockers
- None / list any external dependencies

## Integration Points
- Auth: email from KV purchase record (mvp-storefront)
- Data: KV namespace {id} (from storefront deploy)
- Routes: merge into existing worker at {worker_url}
```

### 2b. Load into Todo Tool

Convert the build order into actionable todos:

```
todo([
  {id: "chunk-1", content: "Atom 1: Accept URL input — HTML form on /app page", status: "pending"},
  {id: "chunk-2", content: "Atom 2: Scrape target page — POST /api/analyze, fetch + return HTML", status: "pending"},
  {id: "chunk-3", content: "Atom 3: Extract pricing — parse HTML for pricing patterns", status: "pending"},
  ...
  {id: "integrate", content: "Wire all atoms into combined worker + redeploy", status: "pending"},
  {id: "test", content: "End-to-end test: input -> output works for purchased user", status: "pending"},
  {id: "db-update", content: "Update business-ideas.json: mvp_status = product_deployed", status: "pending"},
])
```

### 2c. Present Plan to User

Show the battle plan. Get approval or adjustments before building.
This is the checkpoint -- building starts after approval.

## Phase 3: Build Chunk by Chunk

### Execution Strategy: Choose One

**Option A: Subagent-Driven (recommended for 4+ atoms)**
Load `skill_view("subagent-driven-development")`. Dispatch each atom as an independent subagent via `delegate_task`. Each subagent gets:
- The atom spec from the battle plan
- The relevant template files
- Isolated context (no cross-contamination between atoms)
After each subagent completes, run two-stage review: spec compliance then code quality.
Use this when atoms are independent and parallelizable.

**Option B: Sequential (for 1-3 atoms or tightly coupled work)**
Build each atom yourself, one at a time. Better when atoms have tight dependencies or you need to iterate on the design.

### 3a. For Each Chunk

1. Set todo status to in_progress
2. Build the atom (code it -- or dispatch to subagent/opencode)
3. Test it in isolation (unit test or manual verify)
4. If test fails: load `skill_view("systematic-debugging")` -- diagnose root cause before retrying
5. Mark todo as completed
6. Move to next chunk

### 3b. Building Rules

- ONE atom at a time. Don't combine chunks.
- Test after each atom. Don't build 3 atoms then test.
- If an atom takes > 1 hour, it's too big. Split it.
- If an atom fails, load systematic-debugging. Diagnose before retrying. Don't just re-run.
- Each atom should produce a testable artifact (a function, a route, a UI component).
- For each atom, consider test-driven-development: write the test first, verify it fails, then build. Load `skill_view("test-driven-development")` for the methodology.

### 3c. Building Blocks (Templates)

Templates in `assets/` -- load with `skill_view("mvp-builder", file_path="assets/...")`:

- `auth-middleware.js` -- Purchase verification (email lookup in KV)
- `app-shell.html` -- ALLMIND-branded app UI shell with API helpers
- `combined-worker-template.js` -- How storefront + product routes merge

These are starting points, not copy-paste solutions. Adapt to the product.

## Phase 3.5: Price Assessment (Before Integration)

Before wiring into the storefront, verify the price makes sense.

### Check the Idea's Price Point
Read from business-ideas.json: `price_point`, `price_rationale`, `who_pays`.

### Validate Against Build Reality
Now that you've built the atoms, you know what the product actually does. Ask:

1. **Does the product deliver more value than the price in first use?**
   - $3 tool must save at least 15 minutes of work (at any wage)
   - $5 tool must save at least 30 minutes or replace a manual process
   - $7+ tool must provide ongoing value or professional-grade output

2. **Is the price aligned with the buyer's context?**
   - Individual/hobbyist: $3-5 max (impulse buy territory)
   - Freelancer/solopreneur: $5-10 (tool purchase, no approval needed)
   - Small business: $7-15 (still impulse for a business)

3. **Does the margin work?**
   | Price | Stripe Fee | Net | Sales to cover $5/mo hosting |
   |-------|-----------|-----|------------------------------|
   | $3 | $0.39 | $2.61 | 2 |
   | $5 | $0.45 | $4.55 | 2 |
   | $7 | $0.50 | $6.50 | 1 |
   | $10 | $0.59 | $9.41 | 1 |

4. **Adjust if needed.** If the product turned out simpler than expected, price lower. If it turned out more powerful, consider pricing higher. Update business-ideas.json with the final price.

### Set Final Price in Storefront
The price gets baked into the Stripe product/price during mvp-storefront deploy. If the storefront is already deployed with a different price, create a new Stripe price and update the worker binding.

## Phase 4: Integration

### 4a. Merge Into Worker

Once all atoms are built and tested individually:

1. Read the existing storefront worker from `~/.hermes/mvps/{name}/src/worker.js`
2. Add auth middleware functions
3. Add product route handlers
4. Add app page HTML (inline in worker)
5. Update the router to include /app and /api/* routes
6. **Save the merged worker back to `src/worker.js`** — this is the canonical source

### 4b. Redeploy

Same Cloudflare REST API pattern as mvp-storefront:
```
PUT /accounts/{ACCOUNT_ID}/workers/scripts/{script-name}
```
Multipart form-data with metadata (re-bind all KV + secrets).
If product needs additional KV namespaces, create those first.

### 4c. Verify No Regression

After redeploy, test BOTH:
- Storefront routes still work (/checkout, /, /privacy, /terms)
- Product routes work (/app, /api/*)
- Auth gate works (no purchase = redirect, purchased = access)

## Phase 5: Update Pipeline

### 5a. Update business-ideas.json

```python
idea["mvp_status"] = "product_deployed"
idea["product_pattern"] = "web_tool"  # or webhook, monitor, api_proxy
idea["product_routes"] = ["/app", "/api/analyze"]
idea["local_repo_path"] = f"{os.path.expanduser('~')}/.hermes/mvps/{mvp_id}"
idea["last_updated"] = today
```

When both storefront + product verified working:
```python
idea["mvp_status"] = "live"
```

### 5b. Write deploy-metadata.json + Git Commit (REQUIRED)

After database update, commit the deployed state:

```bash
cd ~/.hermes/mvps/{script-name}

cat > deploy-metadata.json << 'EOF'
{
  "worker_url": "https://{script-name}.yourdomain.com",
  "kv_namespace_id": "{kv_id}",
  "sales_kv_id": "{sales_kv_id}",
  "stripe_product_id": "{product_id}",
  "stripe_price_id": "{price_id}",
  "deployed_at": "{ISO timestamp}",
  "last_deploy": "{ISO timestamp}",
  "mvp_status": "product_deployed"
}
EOF

git add -A && git commit -m "deploy: product live — {brief description}"
```

### 5c. Register with Execution Tracker

If execution-tracker config exists, add the MVP to tracking.

## Atom Type Reference

### Frontend Atoms
- HTML/CSS/JS only, no server call
- Test by loading in browser
- Examples: form inputs, data display, sorting/filtering, charts

### API Route Atoms
- Worker handles request -> returns JSON
- Test with curl or fetch
- Always scope to user's email (auth)
- Examples: CRUD operations, data processing, search

### External API Atoms
- Worker calls third-party API
- Test with mock data first, then live
- Handle rate limits, errors, timeouts
- Examples: Stripe queries, web scraping, LLM calls

### KV Storage Atoms
- Read/write to Cloudflare KV
- Key pattern: `data:{email}:{entity}:{id}`
- Test by writing then reading back
- KV limits: 100k reads/day free, eventually consistent (~60s)

### Cron Atoms
- Runs on schedule via Worker cron trigger
- No user request involved
- Store results in KV for later display
- Must configure cron trigger in Worker settings (not just code)

## Companion Skills (Load As Needed)

These are built-in skills that plug into the build process. Load them when you hit the relevant phase:

| Skill | When to Load | What It Does |
|-------|-------------|--------------|
| `writing-plans` | Phase 2 (battle plan) | Creates detailed plans with exact file paths, copy-paste code, test commands |
| `subagent-driven-development` | Phase 3 (4+ atoms) | Dispatches one subagent per atom via delegate_task, two-stage review |
| `systematic-debugging` | Any build failure | 4-phase root cause analysis -- no fix attempt without diagnosis |
| `test-driven-development` | Each atom build | Red/green/refactor cycle -- write failing test first, then implement |
| `mvp-storefront` | Before or after build | Deploy the payment/landing page infrastructure |
| `cloudflare-api` | Deploy phase | Cloudflare REST API helper patterns |

Don't load all at once. Load the relevant one when you enter that phase.

## Client-Side Tool Pattern (No Backend Needed)

For tools that are pure math/data-entry (calculators, trackers, planners), skip the entire auth + KV + API layer. Build as a self-contained HTML app hosted at `/app`.

**Architecture:**
- All logic in browser JS — no server calls
- `localStorage` for persistence (survives browser close, ~5MB limit per domain)
- CSV export for sharing data
- Hosted inline as `APP_HTML` constant in the worker (not a downloadable zip)
- No auth gate — the toolkit IS the product, landing page is the storefront

**localStorage pattern:**
```javascript
const STORAGE_KEY = 'product_data';
function loadData() { try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {} } catch(e) { return {} } }
function saveData(data) { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)) }
// Auto-save on every user action:
function updateItem(i, field, val) { items[i][field] = val; calcResults(); saveData() }
// On init, restore:
const data = loadData();
let items = data.items || [/* defaults */];
```

**Merging app into worker:**
1. Write app HTML to `src/app.html` (separate file for easy editing)
2. Escape for JS template literal: backticks → `` \` ``, `${` → `\${`
3. Add constant: `const APP_HTML = \`...\`;`
4. Add route before the 404 handler: `else if (path === '/app') response = htmlResponse(APP_HTML);`
5. Redeploy — landing page at `/`, app at `/app`

**Why host at /app instead of downloadable zip:**
- Mobile browsers block JS execution from locally opened HTML files (Android `content://` protocol, iOS sandbox)
- Same CF Worker, $0 additional cost
- Works on all devices — phone, tablet, desktop
- Customer opens a URL, no download needed

## Pitfalls
- Building too many atoms before testing -- test each one
- Atoms that are secretly two things -- split further
- Merging into worker breaks storefront -- always verify both after redeploy
- KV eventually consistent -- don't read immediately after write
- Worker CPU limit 10ms (free) / 50ms (paid) -- no heavy computation
- All secrets must be re-bound on every worker upload
- Email-in-URL auth is MVP-level. Fine for tools, not for sensitive data.
- **Image embedding size**: Hero image as base64 JPEG (~140KB) gzips to ~64KB — fine inline. Multiple large images will bloat the worker. Use CSS-only visuals for secondary sections; embed only one key image.
- **Template literal escaping**: When injecting HTML into a JS template literal, must escape ALL backticks and `${` sequences. Missing even one breaks the entire worker silently. Verify with `node -c worker.js` before deploy.

## Architecture Constraints (Cloudflare Workers)
- No persistent connections (WebSocket)
- No filesystem access
- CPU time limits (not wall time -- async fetch is free)
- KV is key-value only, no queries/indexes
- If product needs relational data, use D1 (Cloudflare SQL) instead
- Max 25 MB KV value, 512 byte key

## Security Requirements (Mandatory for Every Build)

### Subdomain Isolation
- Each MVP = one dedicated Worker, one set of KV namespaces, one scoped Stripe key
- No shared credentials between MVPs -- if one leaks, others are unaffected
- See mvp-storefront skill for full isolation protocol

### Cookie Scoping (Every Worker)
```javascript
// CORRECT - scoped to specific subdomain
response.headers.set('Set-Cookie', 'session=abc; Domain=mymvp.{your-account}.workers.dev; Secure; HttpOnly; SameSite=Strict; Path=/');

// WRONG - exposes cookie to all subdomains
response.headers.set('Set-Cookie', 'session=abc; Domain=.yourdomain.com');
```

### Security Headers (Every Response)
```javascript
const securityHeaders = {
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
};

function addSecurityHeaders(response) {
  for (const [key, value] of Object.entries(securityHeaders)) {
    response.headers.set(key, value);
  }
  return response;
}
```

### Auth Isolation
- Auth middleware must verify email against THIS worker's KV, not shared state
- Never trust auth tokens from other MVPs
- Webhook secrets (whsec_) must be per-MVP, not shared
