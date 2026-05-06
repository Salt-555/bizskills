---
name: email-campaigns
description: "Email sequence management for MVPs — nurture leads, onboard customers, win back churned, request testimonials. Reads sequences from campaign-blueprint.json, sends via Resend, tracks state locally. Use when asked to set up email sequences, nurture campaigns, send drip emails, or manage subscriber lists for any product."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [marketing, email, nurture, sequences, automation]
    category: business
    related_skills: [ad-campaign-strategy, execution-tracker, mvp-storefront]
---

# Email Campaigns

Email sequence management for MVPs. The missing link between cold traffic (ads) and warm conversion (purchase).

**Key principle: Email is where Problem Aware becomes Product Aware.** Ads catch attention. Landing pages present the offer. Email builds the relationship that converts fence-sitters.

## When This Skill Activates

- "Set up email sequences for [product]"
- "Start a nurture campaign"
- "Send win-back emails"
- "Add a lead magnet"
- After ad-campaign-strategy generates a blueprint with email_sequence
- When execution-tracker triggers win-back or testimonial emails

## Credentials

All via `~/.hermes/.env`, accessed through `terminal` tool:
```
RESEND_KEY=re_xxxxx        # Already set (used by mvp-storefront for transactional emails)
```

Resend free tier: 100 emails/day, 3,000/month. Sufficient for MVP scale.
Domain: yourdomain.com (already verified with Resend DNS records).

**Sender addresses:** Use `noreply@yourdomain.com` for sequences, `hello@yourdomain.com` for personal-feeling emails. Both send via the same Resend key.

## Send Budget Management (CRITICAL — Free Tier, Shared Across ALL Products)

Resend free tier limits: **100 emails/day, 3,000/month.** This is ONE Resend account shared across ALL MVPs.

### Global Budget (Not Per-Product)

```
Daily cap: 80 (reserve 20 for transactional/urgent across ALL products)
Monthly cap: 2,800 (reserve 200 for transactional/urgent)

Before sending, check GLOBAL state:
  sent_today = count of ALL send-log entries today (all products)
  sent_this_month = sum of ALL send-log entries this month (all products)
  remaining_today = 80 - sent_today
  remaining_month = 2800 - sent_this_month
  budget = min(remaining_today, remaining_month)
```

### Priority System (Cross-Product)

When budget is tight, emails compete ACROSS products. Higher revenue / active ad campaigns get priority:

| Priority | Type | When | Rationale |
|---|---|---|---|
| 1 (highest) | Transactional | Post-purchase download, receipt | They paid — deliver immediately |
| 2 | Nurture step 0 | First email, product with ACTIVE ads | Ads are spending money to generate these leads — don't waste them |
| 3 | Nurture step 0 | First email, product without active ads | Still valuable, but no ad spend at risk |
| 4 | Testimonial request | 7+ days post-purchase, high-LTV product | Social proof for the best products |
| 5 | Nurture steps 1-3 | Ongoing sequences | Diminishing returns per step |
| 6 | Win-back | Churned users, any product | Lowest conversion rate |

### Per-Product Fair Allocation (When Budget Is Abundent)

If remaining budget > total demand, no allocation needed — send everything.

If demand exceeds budget:
1. Sort ALL queued emails across ALL products by priority
2. Send up to budget limit globally
3. Defer remainder to tomorrow

This naturally favors active campaigns and purchases over dormant sequences.

### Monthly Budget Tracking (Global)

```json
{
  "month": "2026-04",
  "total_sent": 0,
  "total_limit": 2800,
  "by_product": {
    "invoice-followup-generator": {"sent": 0, "nurture": 0, "testimonial": 0, "winback": 0},
    "future-product-2": {"sent": 0},
    "future-product-3": {"sent": 0}
  }
}
```

Track in `~/.hermes/data/email/monthly-budget.json`. Updated by daily send processor.

### Scaling Signal

When monthly usage hits 2,000/2,800 (70%): flag to Salt that Resend upgrade may be needed soon.
When monthly usage hits 2,500/2,800 (90%): reduce to transactional + priority 2 only. Alert Salt.

Resend paid: $20/month for 50,000 emails. Upgrade trigger: when consistently hitting 2,500+/month.

## Data Files

```
~/.hermes/data/email/
├── subscribers.json                    # Master subscriber list
├── sequences/{idea-id}/                # Per-product sequences
│   ├── nurture.json                    # Lead nurture sequence
│   ├── winback.json                    # Win-back sequence
│   ├── testimonial.json                # Testimonial request sequence
│   └── custom/{sequence-name}.json     # Custom sequences
└── send-log/
    └── YYYY-MM-DD.json                 # Daily send log (what was sent, to whom, status)
```

## Core Concepts

### Subscriber Lifecycle

```
[Visitor sees ad] → [Landing page] → [Lead magnet / email capture]
                                            ↓
                                    [Subscriber added]
                                            ↓
                              ┌─────────────┴─────────────┐
                              ↓                           ↓
                        [Nurture sequence]          [Buys immediately]
                              ↓                           ↓
                        [Converts]              [Customer sequence]
                              ↓                           ↓
                        [Customer sequence]    [Testimonial request]
                                                        ↓
                                              [Win-back if inactive]
```

### Sequence Types

**1. Nurture Sequence** — Problem Aware → Product Aware → Purchase
- Trigger: new lead (email captured via landing page)
- Goal: educate, build trust, convert
- Length: 4-7 emails over 7-14 days
- Ends when: subscriber buys, or sequence completes

**2. Customer Sequence** — Onboard + delight
- Trigger: purchase (Stripe webhook)
- Goal: ensure they use the product, prevent regret, gather feedback
- Length: 3-5 emails over 7-14 days
- Ends when: sequence completes

**3. Testimonial Request** — Gather social proof
- Trigger: 7+ days after purchase, or usage detected
- Goal: get a quote, review, or case study
- Length: 2-3 emails
- Ends when: response received, or sequence completes

**4. Win-Back** — Re-engage inactive
- Trigger: execution-tracker detects churn/inactivity
- Goal: bring them back
- Length: 2-3 emails over 7-14 days
- Ends when: they re-engage, or sequence completes

---

## subscribers.json Schema

Master list of all subscribers across all products.

```json
{
  "subscribers": [
    {
      "email": "user@example.com",
      "added_at": "2026-04-14T10:00:00Z",
      "source": "meta_ad|organic|referral|purchase",
      "status": "active|unsubscribed|bounced",
      "products": {
        "invoice-followup-generator": {
          "lead": true,
          "customer": false,
          "purchased_at": null,
          "sequences": {
            "nurture": {
              "status": "active|completed|cancelled",
              "current_step": 2,
              "started_at": "...",
              "completed_at": null,
              "emails_sent": [
                {
                  "step": 0,
                  "sent_at": "...",
                  "resend_id": "...",
                  "opened": true,
                  "clicked": false
                }
              ]
            }
          }
        }
      }
    }
  ]
}
```

---

## WORKFLOW 1: Set Up Sequences from Blueprint

Triggered when ad-campaign-strategy outputs a campaign-blueprint.json with `email_sequence` populated.

### Step 1 — Read the blueprint
Load `~/.hermes/data/ads/{idea-id}/campaign-blueprint.json`. Extract `email_sequence` array.

### Step 2 — Convert to sequence format
Transform the blueprint's email objects into a sequence file:

```json
{
  "name": "nurture",
  "idea_id": "invoice-followup-generator",
  "trigger": "new_lead",
  "emails": [
    {
      "step": 0,
      "delay_days": 0,
      "subject": "...",
      "body_html": "...",
      "purpose": "problem agitation",
      "awareness_progression": "problem_aware → solution_aware"
    },
    {
      "step": 1,
      "delay_days": 2,
      "subject": "...",
      "body_html": "...",
      "purpose": "mechanism education",
      "awareness_progression": "solution_aware → product_aware"
    }
  ],
  "cancel_on": "purchase",
  "unsubscribe_url": true
}
```

### Step 3 — Write sequence file
Save to `~/.hermes/data/email/sequences/{idea-id}/nurture.json`.

### Step 4 — Set up landing page integration
For leads to enter the sequence, the landing page needs an email capture endpoint.

**Option A: Add to existing storefront worker**
Add a `POST /subscribe` route that:
1. Stores email in the product's KV (with `source: "lead"`)
2. Adds to subscribers.json (via cron or webhook)
3. Returns success

**Option B: Standalone email capture**
Use a simple form endpoint or Resend's built-in form handling.

### Step 5 — Report
Confirm sequences are ready, landing page integration path, and suggest scheduling the daily sender cronjob.

---

## WORKFLOW 2: Daily Send Processor

Runs via cronjob. Checks all active sequences and sends emails that are due.

Schedule: `0 10 * * *` (10am daily — after execution-tracker at 9am)

### Step 1 — Load subscribers
Read `~/.hermes/data/email/subscribers.json`.

### Step 2 — Check each active sequence
For each subscriber with `status: "active"`:
For each product with an active sequence:
For each active sequence:

1. Get the current step
2. Check the delay: `days_since_step_start >= email.delay_days`
3. Check cancel conditions:
   - If `cancel_on: "purchase"` and subscriber is now a customer → cancel sequence
   - If subscriber unsubscribed → cancel all sequences
4. If email is due and not cancelled → queue for sending

### Step 3 — Send queued emails
Apply GLOBAL budget rules before sending (shared Resend account across all products):

```python
# Load global budget state
monthly = read_json("~/.hermes/data/email/monthly-budget.json")

# Count ALL sends today across all products
sent_today = len(all_send_log_entries_today)  # from send-log/YYYY-MM-DD.json
sent_this_month = monthly["total_sent"]

daily_cap = monthly["daily_cap"]    # 80
monthly_cap = monthly["total_limit"]  # 2800
budget = min(daily_cap - sent_today, monthly_cap - sent_this_month)
```

Sort ENTIRE queue across ALL products by priority (see priority system above).
Send up to `budget` emails globally. Defer the rest.

For each sent email, use `terminal` to call Resend API:

```bash
curl -s -X POST "https://api.resend.com/emails" \
  -H "Authorization: Bearer $RESEND_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "{{YOUR_BRAND_NAME}} <noreply@yourdomain.com>",
    "to": ["user@example.com"],
    "subject": "Email subject from sequence",
    "html": "<p>Email body HTML</p>",
    "tags": [
      {"name": "idea_id", "value": "invoice-followup-generator"},
      {"name": "sequence", "value": "nurture"},
      {"name": "step", "value": "2"}
    ]
  }'
```

**Throttle:** Wait 1.1 seconds between sends (Resend rate limit = 1/sec).

If queue exceeds budget: process up to budget, log "X emails deferred (budget: Y remaining today, Z remaining this month across all products)".

After sending, update monthly-budget.json:
- Increment `total_sent` by count of sent emails
- Increment `by_product.{idea_id}.sent` by count per product
- If total_sent hits 2000: flag upgrade warning
- If total_sent hits 2500: restrict to priority 1-2 only, alert Salt

### Step 4 — Update state
For each sent email:
1. Record in subscriber's `sequences.{name}.emails_sent[]` with resend_id, sent_at
2. Advance `current_step` if this was the last email at current step
3. Mark sequence `completed` if no more emails
4. Append to daily send log

### Step 5 — Update subscribers.json
Write the updated file back.

### Step 6 — Report
Summary: X emails sent (Y deferred), Z sequences completed, W new subscribers, any bounces.
Global budget: daily (X/80), monthly (X/2,800).
Per-product breakdown from monthly-budget.json.
If approaching 2,000/month: flag "Consider Resend upgrade ($20/mo for 50K emails)".

---

## WORKFLOW 3: Add Subscriber (Lead Capture)

When someone enters their email (landing page form, lead magnet, etc.):

### Step 1 — Check if already exists
Read subscribers.json. If email exists:
- If `status: "unsubscribed"` → do nothing (respect opt-out)
- If already has active sequence for this product → do nothing
- If customer but no nurture sequence → don't add nurture (they already bought)

### Step 2 — Create subscriber record
```json
{
  "email": "new@example.com",
  "added_at": "2026-04-14T10:00:00Z",
  "source": "meta_ad",
  "status": "active",
  "products": {
    "invoice-followup-generator": {
      "lead": true,
      "customer": false,
      "purchased_at": null,
      "sequences": {
        "nurture": {
          "status": "active",
          "current_step": 0,
          "started_at": "2026-04-14T10:00:00Z",
          "completed_at": null,
          "emails_sent": []
        }
      }
    }
  }
}
```

### Step 3 — Start nurture sequence
If a nurture sequence exists for this product, mark it active at step 0.
The daily send processor will pick it up and send email 0 (delay_days: 0 = send immediately).

### Step 4 — Save
Append to subscribers.json.

---

## WORKFLOW 4: Customer Conversion (Post-Purchase)

Triggered by execution-tracker or manually when a purchase is detected.

### Step 1 — Update subscriber record
Find subscriber by email. Set:
- `products.{id}.customer = true`
- `products.{id}.purchased_at = now`
- Cancel nurture sequence (they bought)

### Step 2 — Start customer sequence
If a customer sequence exists for this product, activate it.
If not, skip (customer sequences are optional for simple products).

### Step 3 — Queue testimonial request
Set a delayed trigger: testimonial sequence starts 7 days after purchase.
This can be handled by the daily processor checking purchase dates.

---

## WORKFLOW 5: Win-Back (Execution-Tracker Integration)

When execution-tracker detects churned/inactive users, it calls this workflow.

### Step 1 — Load subscriber
Find by email in subscribers.json.

### Step 2 — Activate win-back sequence
Set `sequences.winback.status = "active"`, `current_step = 0`.

### Step 3 — Daily processor handles the rest
The daily send processor will send the win-back emails on schedule.

---

## WORKFLOW 6: Unsubscribe Handling

### One-Click Unsubscribe
Every email MUST include an unsubscribe link:
```
https://yourdomain.com/unsubscribe?email={{encoded_email}}&product={{idea_id}}
```

Add a `GET /unsubscribe` route to the storefront worker that:
1. Decodes the email
2. Sets subscriber status to "unsubscribed"
3. Cancels all active sequences
4. Returns confirmation page

### List-Unsubscribe Header
For email clients that support it, add to every email:
```
List-Unsubscribe: <https://yourdomain.com/unsubscribe?email={{encoded_email}}>
List-Unsubscribe-Post: List-Unsubscribe=One-Click
```

This is a Resend header — add to the API call:
```json
{
  "headers": {
    "List-Unsubscribe": "<https://yourdomain.com/unsubscribe?email=...>",
    "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"
  }
}
```

---

## Writing Good Sequence Emails

Same principles as ad copy — write to one person, frameworks guide but don't constrain.

**Nurture Email 0 (Day 0 — immediate):**
- Subject: Something they'd actually open. Not "Welcome to [Product]!"
- Body: Acknowledge the problem they're dealing with. Provide one actionable insight. Soft mention of the product. No hard sell.
- Goal: Make them glad they gave you their email.

**Nurture Email 1 (Day 2):**
- Educate on the mechanism. WHY the product works differently.
- Goal: Move from Solution Aware to Product Aware.

**Nurture Email 2 (Day 4):**
- Social proof. Someone else's result. Specific numbers.
- Goal: Build trust.

**Nurture Email 3 (Day 7):**
- The offer. Remind them the product exists. Price, guarantee, CTA.
- Goal: Convert.

**Red flags in sequence emails:**
- Opening with "Hi {{first_name}}!" (feels template-y, everyone does it)
- Emails that could be sent to anyone (not specific to the product/problem)
- More than 1 CTA per email (confuses the reader)
- Daily emails (annoying for a $7 product — 2-3 per week max)

**Green flags:**
- Subject lines that create genuine curiosity
- Each email has ONE job (educate, prove, sell)
- Feels like advice from someone who understands the problem
- Unsubscribe link is easy to find (builds trust)

---

## Integration Points

**ad-campaign-strategy → email-campaigns:**
- Blueprint's `email_sequence` becomes the nurture sequence
- Each email tagged with `awareness_progression` for strategic tracking

**execution-tracker → email-campaigns:**
- Triggers win-back sequences for inactive users
- Triggers testimonial requests for active users
- Provides usage data to personalize sequences

**mvp-storefront → email-campaigns:**
- `POST /subscribe` route captures leads into sequences
- `GET /unsubscribe` route handles opt-outs
- Post-purchase webhook triggers customer sequence

**ads-manager → email-campaigns:**
- Subscriber count and conversion data inform ad optimization
- If nurture sequence converts well, increase ad spend (higher effective LTV)

---

## Cronjob Setup

```
Daily send processor: "0 10 * * *" (10am, after execution-tracker at 9am)
Prompt: Run email-campaigns Workflow 2 — daily send processor.
Check all active sequences, send due emails via Resend, update state.
Report summary via Telegram.
```

---

## Pitfalls

- **Resend free tier = 100 emails/day, 3,000/month. Budget 80/day, 2,800/month (reserve for transactional).** Every email must earn its send. Prioritize: transactional > first nurture > testimonial > ongoing nurture > win-back.
- **Don't blast.** With 500 subscribers in a nurture sequence, it takes 6+ days to send one email to everyone. This is fine — staggered sends actually look more natural to email providers than blast patterns.
- **Bounces kill domain reputation.** Verify emails before adding to sequences. If Resend reports a bounce, immediately set subscriber status to "bounced" and never send again.
- **Unsubscribe is NOT optional.** CAN-SPAM and GDPR require it. Every email must have it. Every request must be honored within 24 hours.
- **Don't email customers who already bought.** The nurture sequence must cancel on purchase. Nothing kills trust faster than "Buy our product!" emails after they already bought it.
- **Send log is your audit trail.** If someone complains, you need to prove what was sent, when, and that they opted in. Keep send-log/YYYY-MM-DD.json files.
- **Testimonial requests too early feel transactional.** Wait at least 7 days after purchase. Ideally wait for usage signals (execution-tracker data).
- **Subject lines matter more than body copy.** 47% of email recipients open based on subject line alone. Test subject lines, not body content.
- **HTML emails look different in every client.** Keep formatting minimal. Inline styles. No complex layouts. Plain-text fallback for every email.
- **Throttle sends (1.1 sec between).** Resend rate limit is 1/sec. Bursting triggers temporary blocks.
- **Monthly projection check.** If active subscribers × average sequence length > 2,800, you'll hit the monthly cap. Flag this early — either upgrade Resend or trim sequences.

---

## Verification

- subscribers.json exists and is valid JSON
- Sequence files exist for products with email_sequence in their blueprint
- Daily cronjob scheduled at 10am
- Test email sends successfully via Resend API
- Unsubscribe link works (test with curl)
- Send log files are being created daily
