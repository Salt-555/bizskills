---
name: idea-validator
description: "Optional pre-validation for higher-risk ideas. Creates landing pages with email capture, deploys to Cloudflare, and measures interest via ads BEFORE building. Default path is idea-miner -> mvp-builder (ship the MVP as the validation). Use this skill only when explicitly asked to validate first, or for ideas with >$500 build cost where testing demand is worth the delay."
---

# Idea Validator - Landing Page + Ad Test (Optional)

## When to Use This vs. Just Building

**DEFAULT: Skip validation, go straight to mvp-storefront + mvp-builder.**
MVPs are cheap ($3-10 one-time) and fast to build. The product itself is the best validation.

**Use this skill ONLY when:**
- User explicitly asks to "validate" or "test demand" before building
- Build cost is unusually high (>$500 or >2 days of work)
- Idea requires third-party API costs or commitments before launch
- User wants to test messaging/positioning before committing

**Do NOT use when:**
- It's a standard $3-10 one-time purchase tool (just build it)
- The idea can ship in under a day
- User says "build" or "ship" (use mvp-storefront + mvp-builder directly)

**Pipeline:** idea-miner (raw) -> user approval (build_ready) -> mvp-storefront (payments) -> mvp-builder (product)

## Validation Flow
1. Select idea from database (pending status)
2. Generate landing page HTML with email capture
3. Deploy to Cloudflare (Worker serves both page + signup endpoint)
4. User runs ads -> reports results
5. Update database with validation results
6. If validated -> proceed to mvp-builder

## Database Path
`~/.hermes/data/business-ideas.json`

## Idea Status Flow
```
pending -> testing -> validated -> build_ready
                  \-> rejected
```

## Workflow

### Step 1: Select Idea to Validate
- IF user provides idea_id -> use that specific idea
- IF user provides topic -> find first pending idea for that topic
- IF neither -> find first pending idea in database
- IF all validated -> notify user

### Step 2: Generate Landing Page
Create a high-converting, single-file HTML landing page. Use the shared template from `mvp-builder/references/landing-page-template.html` and customize all `{{PLACEHOLDER}}` tags.

**Output path:** `~/.hermes/validations/{idea_id}/index.html`

**Required Elements:**
- Hero with pain-focused headline (NOT feature-focused)
- Email capture form (single field, above fold)
- Problem section with relatable pain cards
- Solution section with 3 key benefits
- Social proof section (use estimates for validation)
- FAQ section (address common objections)
- Second CTA at bottom

**Headline Formulas (choose one):**
1. "[PAIN VERB]ing on [ACTIVITY]? Here's the fix."
2. "Finally, a way to [DESIRED OUTCOME]"
3. "Stop [PAIN] - Start [BENEFIT]"
4. "What if [ACTIVITY] could be [ADJECTIVE]?"

**Copy Principles:**
- Write to ONE person, not "you guys"
- Use "I" statements in pain points (makes it relatable)
- Focus on OUTCOMES, not PROCESS
- Keep form fields to ONE (email only for validation)
- Above the fold = headline + form + button

### Step 3: Deploy to Cloudflare
Deploy as a single Worker that serves both the landing page and handles signups.

Use `references/signup-worker.js` as the base. The worker:
- Serves the landing page HTML on GET /
- Accepts POST /signup with email capture
- Stores emails + timestamps in KV
- Returns count on GET /count

```bash
IDEA_ID="[idea-name]"
wrangler deploy --name $IDEA_ID-validator
```

### Step 4: Update Database
After deployment, update the idea:
- `validation_status` = "testing"
- `landing_page_url` = Worker URL
- `landing_page_created_at` = timestamp

### Step 5: Ad Platform Recommendations
Based on the business idea, recommend specific platforms:

| Platform | Best For | Expected CPC |
|----------|----------|--------------|
| Google Ads (Search) | High-intent, people actively searching | $1-3 |
| Meta (FB/IG) | Visual products, lifestyle/hobby | $0.50-2 |
| Reddit Ads | Niche communities, engaged discussions | $0.30-1 |
| Twitter/X Ads | B2B, tech-savvy early adopters | $0.50-2 |

**Traffic needed for statistical significance:**
- Minimum: 100 clicks to landing page
- Target conversion: 10-20% (clicks -> signups)
- Goal: 10-20 signups minimum
- Budget: $50-100 per platform tested
- Duration: 3-5 days minimum

### Step 6: Return Info to User
Output:
- Landing page URL
- Signup data endpoint URL
- Recommended ad platforms with targeting
- Budget recommendation
- Instructions: "Run ads for 3-5 days, then come back with results"

### Step 7: Process Validation Results
When user returns with ad results:

**Calculate:**
- CPA = ad_spend / signup_count
- Estimated LTV (SaaS: monthly_price x 12-24 months)
- Acceptable CAC = LTV / 3

**Validation Decision Matrix:**
- CPA < (LTV / 10) = STRONG -> set build_ready: true, proceed to mvp-builder
- CPA < (LTV / 5) = MODERATE -> refine messaging, test again
- CPA < (LTV / 3) = WEAK -> consider pivoting the pitch
- CPA > (LTV / 3) = REJECT -> economics don't work, move on

**Additional signals:**
- Landing page conversion >10% = strong product-market fit
- 5-10% = moderate interest
- <5% = messaging problem or weak idea

**Update database:**
- `validation_status` = "validated" or "rejected"
- `validated_at` = timestamp
- `cac` = cost per acquisition
- `estimated_ltv` = lifetime value estimate
- `validation_strength` = "STRONG" | "MODERATE" | "WEAK" | "REJECTED"
- `build_ready` = true (if STRONG)

## Hard Stops
- No pending ideas in database
- Cloudflare deployment fails
- User hasn't provided ad results yet for an idea in "testing" status

## Pitfalls
- `wrangler` not installed or not authenticated - check with `wrangler whoami` first
- KV namespace not created before worker deploy - signups silently fail
- Stopping ad test before 100 clicks - insufficient data, false negatives common
- Optimize for signups, not clicks (vanity metric trap)
- Social proof numbers with no basis destroy trust if real customers check later
- The biggest pitfall: spending a week validating something you could have built in a day. Default to building.

## Verification
- Landing page loads at Worker URL
- POST to `{url}/signup` with `{"email":"test@test.com"}` returns `{"success":true,"count":N}`
- GET to `{url}/count` returns signup count
- business-ideas.json updated with `validation_status: "testing"` and `landing_page_url`

---
*Validation is optional. The MVP itself is the ultimate validation. Use this only when the build cost justifies the delay.*