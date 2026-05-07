---
name: ads-manager
description: Autonomous ad campaign management for Google Ads and Meta - launches campaigns, monitors performance, auto-optimizes budgets, kills losers, scales winners. Use when asked to launch ads, run a campaign, start advertising, manage ad spend, scale/pause ad campaigns, or test landing pages with paid traffic.
---

# Ads Manager - Autonomous Ad Campaign Engine

## Purpose
Launch, monitor, and optimize ad campaigns on Google Ads and Meta for validated business ideas.
Zero human involvement after credential setup.

## CRITICAL: Environment Access Rules

**execute_code sandbox has a SEPARATE environment.** os.getenv() returns None inside execute_code for ALL credentials.

**ALL API calls MUST use the `terminal` tool** (curl or python3). This is the only way to access credentials loaded from `~/.hermes/.env`.

- WRONG: execute_code with os.getenv('META_ADS_ACCESS_TOKEN') → returns None
- RIGHT: terminal with curl/python3 that reads env at runtime on the host machine

**Variable names** (note the _ADS_ infix):
- META_ADS_ACCESS_TOKEN (NOT META_ACCESS_TOKEN)
- META_ADS_ACCOUNT_ID, META_ADS_PAGE_ID, META_ADS_PIXEL_ID

This rule is NOT optional. Forgetting it wastes a full debugging cycle every time.

## Pipeline Position
idea-validator (deploy) --> AD CAMPAIGN STRATEGY (planning) --> ADS MANAGER (execution) --> execution-tracker (reads ad metrics)

ad-campaign-strategy generates campaign-blueprint.json with audience analysis, offer construction, funnel design, awareness-matched copy, and testing plan. ads-manager executes the blueprint via API calls.

If no blueprint exists, ads-manager falls back to template-based copy generation (legacy path).

## Credentials
All credentials stored in `~/.hermes/.env`, accessed via `os.getenv()`. NEVER read credential files as text.
The `execute_code` sandbox has a separate environment — credentials are NOT available there.
All API calls use the `terminal` tool (curl or python3) which has access to the real environment.

### Meta Ads (.env vars)
```
META_ADS_ACCESS_TOKEN=long_lived_token
META_ADS_ACCOUNT_ID=act_1234567890
META_ADS_PAGE_ID=123456789
META_ADS_PIXEL_ID=123456789012345
```

### Google Ads (.env vars)
```
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_oauth_client_id
GOOGLE_ADS_CLIENT_SECRET=your_oauth_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
```

Setup guide: See references/meta-ads-setup.md and references/google-ads-setup.md

## Data Files
- ~/.hermes/data/ads/{idea-id}/campaign-blueprint.json -- strategy blueprint from ad-campaign-strategy (optional)
- ~/.hermes/data/ads/{idea-id}/campaigns.json -- campaign state, IDs, budgets, history (see schema below)
- ~/.hermes/data/ads/{idea-id}/metrics/YYYY-MM-DD.json -- daily snapshots

### campaigns.json Schema (Source of Truth for Ad State)

This file is the single point of recovery. A fresh session with 0 context reads this file, queries the platforms for live metrics, and can resume managing immediately.

```json
{
  "idea_id": "invoice-followup-generator",
  "product_name": "Freelancer Toolkit",
  "landing_page_url": "https://invoice-followup-generator.yourdomain.com",
  "ltv": 7,
  "status": "active",
  "launched_at": "2026-04-14T10:30:00Z",
  "last_optimized": "2026-04-14T15:00:00Z",
  "original_daily_budget": 15,
  "current_daily_budget": 15,
  "monthly_cap": 450,
  "total_spend_lifetime": 0,

  "platforms": {
    "meta": {
      "enabled": true,
      "campaign_id": "12012345678901234",
      "ad_set_ids": ["12012345678901235"],
      "ad_ids": ["12012345678901236"],
      "creative_ids": ["12012345678901237"],
      "dashboard_url": "https://adsmanager.facebook.com/...",
      "status": "active",
      "last_error": null
    },
    "google": {
      "enabled": false,
      "reason": "Deferred — low search volume for this niche",
      "campaign_id": null,
      "ad_group_ids": [],
      "ad_ids": [],
      "dashboard_url": null,
      "status": "paused",
      "last_error": null
    }
  },

  "strategy": {
    "awareness_target": "problem_aware",
    "sophistication_stage": 3,
    "blueprint_path": "~/.hermes/data/ads/invoice-followup-generator/campaign-blueprint.json",
    "blueprint_loaded": true,
    "active_variant": "A_pain_story",
    "variants_tested": [
      {
        "variant_name": "A_pain_story",
        "angle": "problem",
        "awareness_target": "problem_aware",
        "platform": "meta",
        "ad_id": "12012345678901236",
        "creative_id": "12012345678901237",
        "launched_at": "2026-04-14T10:30:00Z",
        "paused_at": null,
        "final_metrics": null
      }
    ],
    "variants_queued": ["B_numbers", "C_mechanism", "D_contrast"]
  },

  "optimization_history": [
    {
      "date": "2026-04-14T10:30:00Z",
      "action": "LAUNCH",
      "reason": "Initial campaign launch",
      "details": "Meta only. Variant A_pain_story. $15/day.",
      "signal": "MAINTAIN"
    }
  ],

  "kill_criteria": {
    "trigger": "$75 spent, 0 purchases, CTR < 0.8%",
    "hard_stop": 150,
    "scaling_trigger": "CPA < $3.50",
    "scaling_cap_multiplier": 2.0
  },

  "daily_snapshots_cached": {
    "last_updated": "2026-04-14",
    "impressions": 0,
    "clicks": 0,
    "ctr": 0,
    "conversions": 0,
    "spend": 0,
    "signal": "MAINTAIN"
  }
}
```

### State Recovery Rules

**What MUST be in campaigns.json (local):**
1. Platform IDs — campaign_id, ad_set_ids, ad_ids (without these, can't query the platform)
2. Strategic context — awareness_target, active_variant, variants_tested (without these, can't make intelligent decisions)
3. Business context — idea_id, ltv, kill_criteria (without these, can't evaluate performance)
4. Optimization history — what's been tried, why, and what happened (without this, repeats mistakes)
5. Blueprint reference — path to campaign-blueprint.json for copy variants

**What CAN be pulled fresh from the platform (not stored long-term):**
1. Live metrics — spend, impressions, clicks, CTR, conversions (pulled on demand)
2. Campaign status — active/paused/archived (pulled on demand)
3. Current creative — what's actually running (pulled on demand)

**What IS cached locally (updated daily by monitor):**
1. `daily_snapshots_cached` — last known metrics for quick reference without API calls
2. `total_spend_lifetime` — running total for kill criteria evaluation

### Recovery Workflow (Fresh Session)

```python
# 1. Read campaigns.json — get IDs + strategy
campaigns = read_json(f"~/.hermes/data/ads/{idea_id}/campaigns.json")

# 2. Pull live metrics from platform using stored IDs
meta_metrics = terminal(f"curl -s 'https://graph.facebook.com/v19.0/{campaigns['platforms']['meta']['campaign_id']}/insights?fields=impressions,clicks,ctr,actions,spend&access_token=$META_ADS_ACCESS_TOKEN'")

# 3. Load blueprint for copy context
blueprint = read_json(campaigns["strategy"]["blueprint_path"])

# 4. Load business context
idea = read_json("~/.hermes/data/business-ideas.json")  # find by idea_id

# 5. Full context restored. Make decisions.
```

**This is why campaigns.json is the most important file.** The platform knows the metrics. The blueprint knows the copy. campaigns.json is the GLUE that connects platform state to business strategy.

---

## CREDENTIAL CHECK
Before any API call, use `terminal` to check env vars are set:
```bash
python3 -c "
import os
meta = all([os.getenv('META_ADS_ACCESS_TOKEN'), os.getenv('META_ADS_ACCOUNT_ID')])
google = all([os.getenv('GOOGLE_ADS_DEVELOPER_TOKEN'), os.getenv('GOOGLE_ADS_REFRESH_TOKEN'), os.getenv('GOOGLE_ADS_LOGIN_CUSTOMER_ID')])
print(f'meta={meta} google={google}')
"
```
- If neither: alert Salt, print setup instructions, stop.
- If only one platform: proceed with that only, note the other is missing.

---

## WORKFLOW 1: Launch Campaigns
Trigger: idea-validator calls this after Cloudflare deploy, or "launch ads for {idea_id}"

### Step 1 - Load idea from DB
Use execute_code to read ~/.hermes/data/business-ideas.json and find idea by id.
Extract: pain_point, business_idea, topic, estimated_ltv (default 50 if missing).

### Step 2 - Load campaign blueprint OR generate ad copy

**First, check for a campaign blueprint:**
Use execute_code to check if `~/.hermes/data/ads/{idea_id}/campaign-blueprint.json` exists.

**If blueprint exists:** Load it and extract pre-written copy:
- From `ads.google.variants[0]`: headlines[], descriptions[], keywords[]
- From `ads.meta.variants[0]`: primary_text, headline, description, interests[]
- From `audience`: channel selection, targeting demographics, interests
- From `offer`: guarantee, urgency elements, price framing
- From `budget`: recommended daily budget, channel split

Use the FIRST variant (typically "A_problem" angle) as the primary ad. Store all variants in campaigns.json for later creative rotation.

**If no blueprint exists (legacy path):** Generate copy using the template below:
Using the idea's pain_point and business_idea, generate ALL copy before making any API call:

GOOGLE - Responsive Search Ad:
- 10 headlines, 30 chars max each. Mix: "Stop [Pain]", "Fix [X] Today", "[Benefit] In Minutes", "Try Free"
- 4 descriptions, 90 chars max each. Expand value prop, end with CTA.
- 15 keywords: phrase match and exact match. Focus high-intent terms.

META - Single Image Ad:
- Primary text: 125 chars max. Open with pain hook or question.
- Headline: 40 chars max. Solution promise.
- Description: 30 chars max. CTA.
- 8-10 interest categories derived from the topic.
- Audience: ages 25-54, countries US/CA/GB/AU.

### Step 3 - Create data directory
Use execute_code: os.makedirs ~/.hermes/data/ads/{idea_id}/metrics/, exist_ok=True

### Step 4 - Launch Google Ads campaign
Use `terminal` tool for all Google Ads API calls. Read creds from env at runtime.

Authentication: exchange refresh_token for access_token via google OAuth2 token endpoint:
```bash
python3 -c "
import os, urllib.request, urllib.parse, json
data = urllib.parse.urlencode({
    'client_id': os.getenv('GOOGLE_ADS_CLIENT_ID'),
    'client_secret': os.getenv('GOOGLE_ADS_CLIENT_SECRET'),
    'refresh_token': os.getenv('GOOGLE_ADS_REFRESH_TOKEN'),
    'grant_type': 'refresh_token'
}).encode()
req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
resp = json.loads(urllib.request.urlopen(req).read())
print(resp['access_token'])
"
```

Then use the access_token as Bearer header with developer-token header for all subsequent calls.
Create in sequence via curl, each as a separate mutate call:
1. Campaign budget: amountMicros = daily_budget_usd * 1_000_000, deliveryMethod = STANDARD
2. Campaign: channel SEARCH, biddingStrategy MANUAL_CPC, enhanced_cpc=true, search network only, start PAUSED
3. Ad group: type SEARCH_STANDARD, default CPC 1_000_000 micros ($1.00)
4. Keywords: single mutate call with all keywords, PHRASE and EXACT match types
5. Responsive Search Ad: all generated headlines and descriptions as AdTextAsset objects

On any error: print the full error, skip Google, continue to Meta. Never abort both platforms.
Store returned: campaign_id, ad_group_id, ad_id, budget_resource_name, dashboard URL.

### Step 5 - Launch Meta campaign
Use `terminal` tool for all Meta API calls. Base URL: https://graph.facebook.com/v19.0
Credentials accessed via `os.getenv()` — never load from files.

All Meta calls use curl with access token:
```bash
curl -s -X POST "https://graph.facebook.com/v19.0/act_$META_ADS_ACCOUNT_ID/campaigns" \
  -d "name=CampaignName&objective=OUTCOME_LEADS&status=ACTIVE&buying_type=AUCTION&special_ad_categories=[]&access_token=$META_ADS_ACCESS_TOKEN"
```

Create in sequence:
1. Campaign: objective=OUTCOME_LEADS, status=ACTIVE, buying_type=AUCTION, special_ad_categories=[]
2. Ad set: optimization_goal=LEAD_GENERATION, billing_event=IMPRESSIONS, bid_strategy=LOWEST_COST_WITHOUT_CAP,
   daily_budget in cents (USD * 100), targeting: geo US/CA/GB/AU, age 25-54,
   publisher_platforms facebook+instagram, interests via flexible_spec
3. Ad creative: object_story_spec with link_data (message, name, description, call_to_action SIGN_UP,
   picture=landing_url). Add pixel tracking_specs if META_ADS_PIXEL_ID is set.
4. Ad: link ad_set_id + creative_id

On any error: print, skip Meta. Don't abort if Google succeeded.
Store returned: campaign_id, ad_set_id, creative_id, ad_id, dashboard URL.

### Step 6 - Save campaign state to disk
Use execute_code to write ~/.hermes/data/ads/{idea_id}/campaigns.json with the FULL state:

Required fields on initial launch:
- idea_id, product_name, landing_page_url (from business-ideas.json)
- ltv (from business-ideas.json estimated_ltv or price_point)
- status: "active"
- launched_at: ISO timestamp
- last_optimized: ISO timestamp
- original_daily_budget, current_daily_budget
- monthly_cap (from blueprint or default 500)
- total_spend_lifetime: 0
- platforms.{meta,google}: enabled, campaign_id, ad_set_ids, ad_ids, creative_ids, dashboard_url, status, last_error
- strategy: awareness_target, sophistication_stage, blueprint_path, blueprint_loaded, active_variant (first variant name), variants_tested (array with initial variant), variants_queued (remaining variant names)
- optimization_history: single LAUNCH entry with reason, details, signal
- kill_criteria: trigger text, hard_stop amount, scaling_trigger, scaling_cap_multiplier
- daily_snapshots_cached: last_updated, zeros for metrics

This is the RECOVERY FILE. A fresh session reads this + queries platforms = full context.
statuses, budgets, dashboard URLs, original_daily_budget, launched_at timestamp, empty optimization_history.

### Step 7 - Update business-ideas.json
Set: ad_campaigns_active=true, ad_launch_date=today, ad_daily_budget={current_daily_budget}.
Also set: ad_platforms_active = list of enabled platforms (e.g. ["meta"]).

### Step 8 - Report to user
Output: campaign names/IDs, dashboard URLs, active platforms, daily budget,
active variant name + angle, queued variants for testing,
expected days to first optimization signal (3+ days, 100+ clicks).

---

## WORKFLOW 2: Daily Monitor + Optimize
Runs via cronjob at 8:50am daily (10 min before execution-tracker so metrics are fresh).
Schedule this with: cron "50 8 * * *", deliver to telegram.

### Step 1 - Find active campaigns
Use execute_code: glob ~/.hermes/data/ads/*/campaigns.json where status = "active".
If none: log "no active campaigns" and exit cleanly.

### Step 2 - Pull yesterday's metrics for each campaign

GOOGLE: Use `terminal` with curl to call REST searchStream endpoint with a GAQL query.
First refresh the access token (same OAuth2 exchange as Workflow 1 Step 4), then:
```bash
curl -s -X POST "https://googleads.googleapis.com/v14/customers/$GOOGLE_ADS_LOGIN_CUSTOMER_ID/googleAds:searchStream" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "developer-token: $GOOGLE_ADS_DEVELOPER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"SELECT metrics.impressions, metrics.clicks, metrics.ctr, metrics.conversions, metrics.cost_micros, metrics.average_cpc FROM campaign WHERE campaign.id = CAMPAIGN_ID AND segments.date = '\''YESTERDATE'\''"}'
```

META: Use `terminal` with curl.
```bash
curl -s "https://graph.facebook.com/v19.0/$CAMPAIGN_ID/insights?fields=impressions,clicks,ctr,actions,spend,cpc&time_range={'since':'YESTERDATE','until':'YESTERDATE'}&access_token=$META_ADS_ACCESS_TOKEN"
```
Extract conversions from actions where action_type in [lead, offsite_conversion.fb_pixel_lead].
Also pull date_preset=last_30_days for burn rate.

Graceful handling: missing env vars → record {error: credentials_missing}, still process other platform.

### Step 3 - Evaluate optimization signal, act on it

Compute in execute_code, evaluate in priority order:
```
days_running = (today - launched_at_date).days
blended_cpa  = total_spend / total_conversions  (None if zero conversions)

PAUSE_ALL:   days >= 3 AND total_clicks >= 100 AND total_spend > 60 AND conversions == 0
PAUSE_GOOG:  google_spend > 30 AND google_ctr < 0.5 AND google_conversions == 0
PAUSE_META:  meta_spend > 30 AND meta_ctr < 0.5 AND meta_conversions == 0
DOUBLE_DOWN: blended_cpa < ltv/10  →  multiply budget x1.4 (cap: original_budget * 2)
SCALE:       blended_cpa < ltv/5   →  multiply budget x1.2 (cap: original_budget * 2)
SWAP_COPY: impressions >= 100 AND ctr < 1.0  (evaluate per platform)
  - If campaign-blueprint.json exists AND has unused variants: rotate to the next variant (B, C, D). Log which angle is being tested.
  - If no blueprint or all variants exhausted: generate 3 fresh headline/text variants from original idea fields.
  - Call API to create new ad. Enable new ad, pause old ad. Log the swap.
MAINTAIN:    default, no action
```

PAUSE: call via `terminal` curl — campaigns:mutate (Google) or PATCH /{campaign_id} status=PAUSED (Meta).
       Update campaigns.json status. Send Telegram alert with reason.
SCALE within cap: call via `terminal` curl — campaignBudgets:mutate (Google) and PATCH /{ad_set_id} daily_budget (Meta).
SCALE above 2x cap: send Telegram to Salt asking approval. Record as "pending_approval". Do NOT execute.
SWAP_COPY above: Rotate to next blueprint variant if available, else generate fresh copy. Call API to create new ad.
           Enable new ad, pause old ad. Log the swap with which angle/awareness level is now active.

### Step 4 - Save daily snapshot and update campaigns.json
Use execute_code to write metrics/{yesterday}.json with all platform metrics and combined signal.

THEN update campaigns.json:
1. Update `daily_snapshots_cached` with latest metrics (impressions, clicks, ctr, conversions, spend, signal)
2. Update `total_spend_lifetime` (add yesterday's spend)
3. Update `last_optimized` timestamp
4. Update `current_daily_budget` if budget was changed
5. Update platform `status` fields if campaigns were paused/resumed
6. If SWAP_COPY was executed:
   - Move old variant from `variants_tested[].active` to `paused_at: timestamp, final_metrics: {...}`
   - Add new variant to `variants_tested` with `launched_at: now`
   - Update `active_variant` to new variant name
   - Remove new variant from `variants_queued`
   - Update platform `ad_ids` and `creative_ids` with new IDs
7. Append action to `optimization_history` with date, action, reason, details, signal

This history is CRITICAL for recovery. A fresh session needs to know what's been tested and why.

---

## WORKFLOW 3: Metrics Feed for Execution-Tracker
When execution-tracker runs, load today's ad snapshot per MVP:
Use execute_code to read ~/.hermes/data/ads/{mvp_id}/metrics/{today}.json if it exists.
Return: ad_spend_today, ad_spend_30d, total_conversions_30d, blended_cpa, best_platform, ad_signal.
If file not found: return nulls (monitor hasn't run yet today, not an error).

---

## INTEGRATION: AD CAMPAIGN STRATEGY
ad-campaign-strategy is the recommended upstream step before ads-manager. It generates campaign-blueprint.json with:
- Awareness-matched copy (tagged with which Schwartz level each variant targets)
- Multiple testing variants (different angles, not just rephrasing)
- Offer construction (bonuses, guarantee, urgency)
- Audience targeting (demographics, interests, channels)
- Budget recommendations

**Pipeline flow:** ad-campaign-strategy → ads-manager reads blueprint → executes via API → execution-tracker reads metrics

If blueprint exists when ads-manager launches, it uses blueprint copy and targeting (Step 2). If not, it falls back to template copy.

## INTEGRATION: IDEA-VALIDATOR
After successful wrangler deploy, run Credential Check above (env vars).
If credentials exist: first invoke ad-campaign-strategy to generate a blueprint, then invoke ads-manager Workflow 1.
If ad-campaign-strategy is not available: invoke ads-manager directly (uses legacy template copy).
If missing: print "Ads credentials not configured — add META_ADS_* and/or GOOGLE_ADS_* to ~/.hermes/.env"

## INTEGRATION: EXECUTION-TRACKER
In Step 1b (after Plausible metrics), load today's ad snapshot per MVP.
Merge into daily report: ad_spend_today, paid_cac, best_platform, ad_signal.
Add ad_spend_30d to burn rate. Surface SCALE/DOUBLE_DOWN signals as growth opportunities.

---

## EMERGENCY STOPS
Immediately PAUSE ALL and Telegram alert if:
- Token refresh fails (expired credentials) — re-check env vars, include re-auth steps in the alert
- Spend rate > 3x LTV in under 24 hours
- Account suspended/flagged (watch API error codes in responses)
- Idea's execution_status = "KILL" in business-ideas.json — never spend on dead products

---

## OPTIMIZATION THRESHOLDS
- Pause: $30 per platform + CTR <0.5% + 0 conversions (after 3 days, 100+ clicks)
- Scale: CPA < LTV/5 → +20% budget per cycle
- Double-down: CPA < LTV/10 → +40% budget per cycle
- Hard cap: 2x original budget requires Salt approval above
- Hard cap: $500/month per idea total

---

## WORKFLOW 4A: Add Image to Meta Ad Creative

**CRITICAL: You cannot update an existing creative's `object_story_spec`.** The API returns error 181573 ("Failed to update the creative"). You must create a new creative with the image and swap ads.

### Correct Flow (Verified May 2026)

**Step 1 — Generate/download the ad image**
Use `image_generate` tool for fastest results, or ComfyUI if available:
```python
# image_generate is preferred — faster than remote ComfyUI which often times out
image = image_generate(prompt="...", aspect_ratio="square")
# Download the returned URL to local file
curl -sL "$IMAGE_URL" -o /path/to/ad_image.png
```

**Step 2 — Upload image to ad account media library**
Use `POST /{ad_account_id}/adimages` (NOT `/page/photos` — that requires page-level permissions):
```bash
export $(grep META_ADS_ACCESS_TOKEN ~/.hermes/.env)
curl -s -X POST "https://graph.facebook.com/v18.0/act_$META_ADS_ACCOUNT_ID/adimages" \
  -F "file=@/path/to/ad_image.png" \
  --data-urlencode "access_token=$META_ADS_ACCESS_TOKEN"
```
Returns: `{"images": {"ad_image.png": {"hash": "abc123...", ...}}}`

**Step 3 — Create new ad with image_hash in creative**
Create a complete new ad (not just the creative) with inline object_story_spec including `image_hash`:
```bash
curl -s -X POST "https://graph.facebook.com/v18.0/act_$META_ADS_ACCOUNT_ID/ads" \
  -d "name=Ad Name with Image" \
  -d "adset_id=$ADSET_ID" \
  -d "status=ACTIVE" \
  -d 'creative={"object_story_spec":{"page_id":"'$META_ADS_PAGE_ID'","link_data":{"image_hash":"'"$IMAGE_HASH"'","link":"https://landing.url/","message":"Primary text here...","name":"Headline","description":"Description","call_to_action":{"type":"LEARN_MORE"}}}}' \
  -d "access_token=$META_ADS_ACCESS_TOKEN"
```

**Step 4 — Pause old ad, verify new one is active**
```bash
# Pause old text-only ad
curl -s -X POST "https://graph.facebook.com/v18.0/$OLD_AD_ID?status=PAUSED&access_token=$META_ADS_ACCESS_TOKEN"
```

### What NOT to do (common failures)
- **DO NOT** try `POST /{creative_id}` with new object_story_spec → error 181573
- **DO NOT** upload via `/page/photos` with ads token → OAuthException code 200 (needs page permissions)
- **DO NOT** use `image_file` in JSON body — must be multipart form data to `/adimages` endpoint
- **DO NOT** try to update creative then swap ad reference — create the new ad inline with full creative spec

### Image Generation: FAL vs ComfyUI
- **FAL (`image_generate` tool)** — preferred for single images. Fast, reliable, no server dependency.
- **ComfyUI remote** — often times out on 103GB VRAM card (shared with LLMs). Only use if you need batch generation or specific workflow control.

---

## WORKFLOW 4: Switch Campaign Objective (Meta Only)
Trigger: User wants to switch from traffic to conversion optimization, or any objective change.

**CRITICAL: You cannot change a Meta campaign's objective after creation.** The API returns success but ignores the change. You must create a NEW campaign tree and migrate.

### Migration Steps
1. **Read campaigns.json** — get old campaign_id, ad_set_id, creative_id, targeting spec.
2. **Fetch existing creative** — `GET /{creative_id}?fields=object_story_spec` to reuse it.
3. **Fetch existing ad set targeting** — `GET /{ad_set_id}?fields=targeting` to copy audience.
4. **Pause old campaign** — `POST /{old_campaign_id} -d status=PAUSED`
5. **Create new campaign** with desired objective (e.g. `OUTCOME_SALES`):
   ```bash
   curl -s -X POST "https://graph.facebook.com/v19.0/$META_ADS_ACCOUNT_ID/campaigns" \
     -d "name={New Campaign Name}" \
     -d "objective=OUTCOME_SALES" \
     -d "status=PAUSED" \
     -d "buying_type=AUCTION" \
     -d "special_ad_categories=[]" \
     -d "is_adset_budget_sharing_enabled=false" \
     -d "access_token=$META_ADS_ACCESS_TOKEN"
   ```
6. **Create new ad set** with purchase optimization:
   ```bash
   curl -s -X POST "https://graph.facebook.com/v19.0/$META_ADS_ACCOUNT_ID/adsets" \
     -d "name={New Ad Set Name}" \
     -d "campaign_id={NEW_CAMPAIGN_ID}" \
     -d "daily_budget={cents}" \
     -d "billing_event=IMPRESSIONS" \
     -d "optimization_goal=OFFSITE_CONVERSIONS" \
     -d "bid_strategy=LOWEST_COST_WITHOUT_CAP" \
     -d "targeting={copied_targeting_json}" \
     -d "promoted_object={\"pixel_id\":\"YOUR_PIXEL_ID\",\"custom_event_type\":\"PURCHASE\"}" \
     -d "attribution_spec=[{\"event_type\":\"CLICK_THROUGH\",\"window_days\":7},{\"event_type\":\"VIEW_THROUGH\",\"window_days\":1}]" \
     -d "status=PAUSED" \
     -d "access_token=$META_ADS_ACCESS_TOKEN"
   ```
   - The `promoted_object` field is REQUIRED for purchase optimization. Without it, the ad set optimizes for generic conversions, not purchases.
   - Include `attribution_spec` for proper conversion window tracking.
7. **Create new ad** reusing the old creative:
   ```bash
   curl -s -X POST "https://graph.facebook.com/v19.0/$META_ADS_ACCOUNT_ID/ads" \
     -d "name={New Ad Name}" \
     -d "adset_id={NEW_AD_SET_ID}" \
     -d "creative={\"creative_id\":\"OLD_CREATIVE_ID\"}" \
     -d "tracking_specs=[{\"action.type\":[\"offsite_conversion\"],\"offsite_pixel\":[\"$META_ADS_PIXEL_ID\"]}]" \
     -d "status=PAUSED" \
     -d "access_token=$META_ADS_ACCESS_TOKEN"
   ```
   - `tracking_specs` is REQUIRED for the new ad to attribute conversions to this campaign. Without it, Meta may count conversions in Events Manager but won't tie them back to the ad for optimization. Always include the pixel ID in tracking_specs when the objective is OUTCOME_SALES or any conversion goal.
8. **Activate new campaign, ad set, ad** with three PATCH calls.
9. **Optional: Set auto-stop** on the ad set for safety caps:
   ```bash
   curl -s -X POST "https://graph.facebook.com/v19.0/{ad_set_id}" \
     -d "stop_time=2026-04-30T17:00:00" \
     -d "access_token=$META_ADS_ACCESS_TOKEN"
   ```
10. **Update campaigns.json** — record old campaign as paused in `previous_campaigns`, update IDs to new ones, append `SWITCH_OBJECTIVE` to optimization_history.

### Cold Pixel Expectation
New purchase-optimized campaigns with a cold pixel (no historical purchase data) may show 0 impressions for 24-48 hours while Meta enters the learning phase. This is normal. Do not panic-pause before 48 hours unless the ad set shows a policy disapproval or billing error. Distinguish learning phase from delivery failure by checking the ad set's `created_time` — if it's less than 48 hours old, MAINTAIN.

### What This Preserves
- Creative (no need to re-upload images or rewrite copy)
- Targeting (same audience, same budget)
- Learning from old campaign (creative performance history stays with the creative_id)

### What This Resets
- Campaign learning phase (new campaign = fresh algorithm)
- Spend totals in campaigns.json (track old + new separately)
- Any campaign-level rules or schedules

---

## WORKFLOW 6: Full-Funnel Conversion Audit
Trigger: "check my funnel", "review my sales funnel for {idea_id}", "why isn't this converting?", "full funnel audit for {idea_id}"

### Purpose
When a campaign has healthy CTR but zero purchases, the bottleneck is rarely the ad — it's somewhere in the landing page → checkout → delivery → email chain. This workflow systematically traces every step and identifies the exact drop-off point.

### Data Sources to Query
| Layer | Source | What to check |
|-------|--------|---------------|
| Ads | Meta API | Creative copy, CTR, CPC, spend, campaign status, pixel events |
| Landing | web_extract + source code | Page renders, load speed, mobile UX, paywall timing |
| Checkout | Stripe API | Payment link config, price, success_url, customer_creation, checkout sessions |
| Delivery | Stripe webhook + worker.js | Webhook endpoint status, event handling, email sending |
| Business context | campaigns.json + business-ideas.json | LTV, kill criteria, pricing alignment |

### Audit Steps

**Step 1 — Read campaigns.json**
Use `execute_code` to load state, extract: idea_id, landing_page_url, ltv, kill_criteria, total_spend_lifetime, active_variant, platforms.{meta,google}.status.

**Step 2 — Pull live ad metrics**
Use `terminal` with Meta API:
- Campaign status (`GET /{campaign_id}?fields=effective_status`)
- Ad set status + daily_budget
- Ad creative copy (`GET /{creative_id}?fields=object_story_spec`)
- Insights: impressions, clicks, ctr, spend, cpc, actions (leads, purchases, landing_page_view)
- Extract conversions from `actions` array by `action_type`

**Step 3 — Query Stripe payment infrastructure**
Use `terminal` with Stripe API (STRIPE_SECRET_KEY from env):
- Payment link: `GET /v1/payment_links/{id}` → verify `active`, `after_completion.redirect.url`, `customer_creation` (must be "always" for email lookup)
- Product: `GET /v1/products/{id}` → verify active, name matches
- Recent checkout sessions: `GET /v1/checkout/sessions?payment_link={id}&limit=10` → check for `status=open` (abandoned) vs `complete`
- Webhook endpoint: `GET /v1/webhook_endpoints/{id}` → verify `status=enabled`, `enabled_events` includes `checkout.session.completed`, URL matches landing domain

**Step 4 — Analyze landing page source**
- `web_extract` the landing page URL to verify it renders and copy matches the ad promise
- Read the deployed worker.js (or source HTML) with `search_files` targeting: paywall, unlock, checkout, stripe, openPayment, success
- **CRITICAL PITFALL**: For Cloudflare Worker MVPs, the deployed app often lives as an `APP_HTML` constant inside `worker.js`, while `app.html` in the repo may be stale. Always verify which file is actually deployed.
- Map the user flow screen-by-screen. Identify where the paywall appears relative to value delivery.

**Step 5 — Cross-reference and diagnose**
Compare findings against known failure modes:

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| High CTR, 0 purchases, no checkout sessions | Paywall too early / promise mismatch | Move paywall later, show more value first |
| High CTR, abandoned checkout sessions | Price too high or unexpected charge | Test lower price, add clearer value stack |
| Checkout completes, no webhook email | Webhook misconfigured or worker not handling | Verify webhook URL, worker route, RESEND_KEY |
| Ad says "free" but landing paywalls immediately | Ad-landing disconnect | Align copy: "free estimate, full plan $X" |
| Spend > hard_stop, still running | Monitor not enforcing kill criteria | Fix daily monitor logic or run manual pause |
| Stale repo file deployed | app.html updated but worker.js APP_HTML not | Redeploy from correct source file |

**Step 6 — Report to user**
Structure the report:
1. **Flow summary** (ad → landing → checkout → delivery) with verified status of each link
2. **Ad performance** (CTR, CPC, spend, creative copy)
3. **Landing page assessment** (promise alignment, paywall timing, UX issues)
4. **Checkout health** (payment link config, abandoned vs completed sessions)
5. **Delivery health** (webhook, email)
6. **Prioritized recommendations** (what to fix first, what to A/B test)

---

## WORKFLOW 5: Campaign Database Sync / Audit
Trigger: "make sure the campaign database is up to date", "sync campaigns with Meta", or any manual health check.

### Purpose
Local `campaigns.json` can drift from Meta's actual state. End dates get clamped to timezone boundaries, campaigns get paused outside the pipeline, ghost campaigns accumulate in the Meta account, and spend totals diverge. This workflow reconciles everything.

### Step 1 — List local campaigns
Use `execute_code` to glob `~/.hermes/data/ads/*/campaigns.json`. Extract:
- `idea_id`, `status`, `platforms.meta.campaign_id`, `platforms.meta.status`
- `scheduled_end_date` or `auto_stop.stop_time`
- `total_spend_lifetime`

### Step 2 — List all Meta campaigns
Use `terminal`:
```bash
export META_TOKEN="$META_ADS_ACCESS_TOKEN"
export ACCT_ID="$(python3 -c "import os; v=os.getenv('META_ADS_ACCOUNT_ID',''); print(v if v.startswith('act_') else 'act_'+v)")"
curl -s "https://graph.facebook.com/v19.0/$ACCT_ID/campaigns?fields=id,name,effective_status,status&limit=50&access_token=$META_TOKEN"
```
Build a set of all campaign IDs in the Meta account.

### Step 3 — Find orphans (Meta has it, local doesn't)
For every Meta campaign ID not found in any local `campaigns.json`:
- If `effective_status == ACTIVE`: **immediate alert** — untracked spend.
- If `effective_status == PAUSED`: add it to the nearest local `campaigns.json` under `platforms.meta.untracked_campaigns` or `previous_campaigns` with a note, or recommend archiving it.

### Step 4 — Verify status parity
For each local campaign with a `campaign_id`:
- Query Meta: `GET /{campaign_id}?fields=id,effective_status`
- If local `status` != Meta `effective_status` (case-insensitive): update local to match Meta. If Meta says PAUSED but local says ACTIVE, the campaign was paused manually or by policy.

### Step 5 — Verify end dates
For each active campaign with a `scheduled_end_date` or `auto_stop`:
- Query the ad set: `GET /{ad_set_id}?fields=id,end_time,effective_status`
- If the returned `end_time` differs from local (even by a day): **update local** to match Meta's actual value. Meta clamps `end_time` to the nearest day boundary in the account timezone — the value you sent is rarely what gets stored.
- Also check the campaign's `stop_time` — it may differ from the ad set's `end_time`.

### Step 6 — Verify spend totals
Pull lifetime spend from Meta insights for each active/recent campaign:
```bash
curl -s "https://graph.facebook.com/v19.0/$CAMPAIGN_ID/insights?fields=spend&date_preset=lifetime&access_token=$META_TOKEN"
```
If Meta's lifetime spend differs significantly from local `total_spend_lifetime`, update local. Note that new campaigns (<24h) may return empty insights — that's normal.

### Step 7 — Update local DB and report
Use `execute_code` to write any corrections back to `campaigns.json`. Report findings:
- Orphans found (and action taken)
- Status mismatches fixed
- End date corrections
- Spend adjustments

This workflow should be run after any objective switch, end-date change, or whenever the user asks "is everything synced?"

---

## MANUAL COMMANDS
- "check my funnel for {idea_id}" → run Workflow 6: trace ad → landing → checkout → delivery, identify conversion bottleneck
- "pause ads for {idea_id}" → pause all campaigns, preserve data
- "resume ads for {idea_id}" → re-enable paused campaigns
- "scale ads {idea_id}" → approve a pending budget increase
- "show ad metrics for {idea_id}" → load campaigns.json, pull live metrics from platforms, display full state
- "show ad state for {idea_id}" → display campaigns.json without API calls (cached data only, useful when creds unavailable)
- "kill ads for {idea_id}" → pause permanently, write final spend/CAC to DB, update campaigns.json status to "killed"
- "swap creative for {idea_id}" → force fresh creative rotation now
- "switch ads to sales {idea_id}" → migrate traffic campaign to purchase-optimized sales campaign
- "recover ad state for {idea_id}" → fresh session recovery: read campaigns.json, pull live metrics, summarize full context (what's running, what's been tested, what's next)

The "recover" command is the key recovery tool. It reconstructs full context from:
1. campaigns.json (IDs + strategy + history)
2. Live platform queries (current metrics)
3. campaign-blueprint.json (copy variants)
4. business-ideas.json (LTV, kill criteria)

---

## Pitfalls
- All credentials live in `~/.hermes/.env` — never in files, never in execute_code sandbox. Use `terminal` tool for all API calls.
- `execute_code` sandbox has separate env — os.getenv() returns None there. Always use `terminal` for credential-dependent operations.
- Google Ads developer token at Basic Access level blocks conversion tracking. Apply for Standard Access before expecting conversion data.
- **Meta API: use curl, not Python urllib** — Meta Graph API PATCH/POST requests fail with HTTP 400 when sent via Python `urllib.request` (even with correct headers and JSON body). Use `curl -s -X POST "https://graph.facebook.com/v19.0/{id}?field=value&access_token=$META_TOKEN"` instead. This is the only reliable method for Meta API calls in this environment.
- **Meta interest IDs may be deprecated** — Always validate interest IDs via `/search?type=adinterest&q={term}` before using them. If ad set creation fails with error 1870247 ("Some detailed targeting options have been combined"), the error response includes `alternative_interest_id` for each deprecated ID. Parse the error, swap to alternatives, retry. Example: "Tarot card games" (6003384741543) → alternative 6003647522546.
- **Meta end_time timezone clamping** — Meta clamps `end_time` to the account's local timezone, not UTC. A UTC timestamp can fail as "End Date Is In The Past." Use `stop_time` instead (more forgiving) or add a buffer of 1-2 days beyond your intended end date when setting `end_time`.
- Daily monitor cronjob must be explicitly scheduled. Campaigns launch fine but optimization never fires without it.
- Google Ads campaigns start PAUSED by design. Must be manually enabled or set to ACTIVE after review to spend.
- Meta special ad categories (credit, housing, employment) require different targeting rules. Wrong category = campaign rejected.

## Token Scope Limitations

**META_ADS_ACCESS_TOKEN is Ads-only.** It can create/manage campaigns, ad sets, ads, and upload creative images via the ad creative endpoint. It CANNOT:
- Upload page photos (`/page/photos` requires `publish_actions` — deprecated)
- Post to page feed (`/page/feed` requires `pages_manage_posts` + `pages_read_engagement`)
- Change page profile picture (`/page/picture` rejects direct file uploads; needs a photo ID or URL first)
- Manage any page content

If you need page-level operations (profile pic, posts), you need a separate token with `pages_manage_posts` + `pages_read_engagement` scopes. The ads token will fail with OAuthException code 200 regardless of how you structure the request.

## Meta Ads API Pitfalls (Verified April 2026)

- **`advantage_audience` REQUIRED** — Add `"targeting_automation": {"advantage_audience": 0}` inside the targeting spec. 0 = custom targeting, 1 = Advantage+ (auto). Without this, all ad set creation fails with error 1870227.
- **Cannot update creative object_story_spec** — You cannot PATCH an existing creative's `object_story_spec` (error 181573). To change copy/image/link on a running ad: create a new ad with the updated creative inline, activate it, pause the old one. See Workflow 4A for image upload flow.
- **Image upload endpoint** — Use `POST /{ad_account_id}/adimages` (multipart form data) to get an `image_hash`. DO NOT use `/page/photos` with ads token (OAuthException code 200). The returned hash goes into `link_data.image_hash` in the creative spec.
- **FAL preferred for single images** — `image_generate` tool is faster than remote ComfyUI which often times out on shared GPU servers. Only use ComfyUI for batch generation or specific workflow control.
- **`is_adset_budget_sharing_enabled` required** — When creating campaigns without `campaign_budget_optimization`, you must pass `is_adset_budget_sharing_enabled=false`. Without it, campaign creation fails with error 4834011.
- **`promoted_object` REQUIRED for purchase optimization** — Ad sets with `optimization_goal=OFFSITE_CONVERSIONS` MUST include `promoted_object={"pixel_id":"...","custom_event_type":"PURCHASE"}`. Without this, Meta optimizes for generic conversions instead of purchase events, and the ad set won't feed conversion data back to the algorithm properly.
- **Interest IDs may be deprecated** — Always validate interest IDs via `/search?type=adinterest&q={term}` before using them. Many witchy/occult interests return empty or have been merged. Use the returned IDs, not guessed ones.
- **Image upload: use `image_file` not `image[file]`** — The `image_file` form field name works reliably for ad image uploads. `image[file]` may fail with OAuth code 1.
- **JSON body must include access_token** — When using `Content-Type: application/json`, the access_token must be inside the JSON body, not as a separate form parameter. Mixing `-d` flags with `-H "Content-Type: application/json"` causes malformed requests.
- **Campaign starts PAUSED** — Create campaigns/adsets/ads as PAUSED, then activate separately with a PATCH. This gives you a review window before spend begins.
- **Auto-stop via `stop_time`** — Set `stop_time=YYYY-MM-DDTHH:MM:SS` on an ad set to make it stop delivering automatically at that time. Useful for safety caps (e.g., "run for exactly 7 days"). The campaign and ad set remain ACTIVE in status but stop serving.

## Verification
- Env vars set in `~/.hermes/.env`: META_ADS_ACCESS_TOKEN, META_ADS_ACCOUNT_ID (and/or GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_REFRESH_TOKEN, GOOGLE_ADS_LOGIN_CUSTOMER_ID)
- campaigns.json created at `~/.hermes/data/ads/{idea_id}/campaigns.json` with valid campaign IDs, strategy section, optimization_history, kill_criteria
- campaigns.json has `strategy.active_variant` set and `strategy.variants_queued` populated
- campaigns.json has `strategy.blueprint_path` pointing to campaign-blueprint.json (if blueprint exists)
- Dashboard URLs in campaigns.json open in browser and show the campaigns
- business-ideas.json updated with `ad_campaigns_active: true` and `ad_launch_date`
- Daily monitor cronjob scheduled at `50 8 * * *` (verify with list_cronjobs)
- Recovery test: a fresh session can read campaigns.json + query platforms and get full context
