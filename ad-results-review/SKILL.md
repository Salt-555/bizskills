---
name: ad-results-review
description: Daily review and synthesis of ad campaign metrics across Meta Ads and Stripe. Compares ad spend to revenue, computes ROI/CPA, flags campaigns needing action (pause, scale, swap copy). Use when reviewing daily ad performance, checking campaign health, or synthesizing paid traffic results.
version: 1.0.0
metadata:
  hermes:
    category: business
    tags: [ads, meta, stripe, analytics, optimization]
---

# Ad Results Review

## Purpose
Pull daily ad metrics from Meta and purchase data from Stripe, synthesize into an actionable summary, and update campaign state files.

## Pipeline Position
ads-manager (launches campaigns) --> AD RESULTS REVIEW (daily monitor) --> execution-tracker (consumes summary)

## Credentials
All accessed via `os.getenv()` in `terminal` tool — NEVER in `execute_code` sandbox.

Required:
- `META_ADS_ACCESS_TOKEN`, `META_ADS_ACCOUNT_ID` — Meta API
- `STRIPE_SECRET_KEY` — Stripe payment data

## Workflow

### Step 1 — Find active campaigns
Use `execute_code` to glob `~/.hermes/data/ads/*/campaigns.json` where `status == "active"`.
If none: output "No active campaigns" and stop.

### Step 2 — Pull Meta metrics for each campaign
Campaign IDs are nested: `platforms.meta.campaign_id` in campaigns.json (not at top level).

**CRITICAL: `META_ADS_ACCOUNT_ID` may already include the `act_` prefix.** Before building any URL with `act_$META_ADS_ACCOUNT_ID`, inspect the env var:
```bash
python3 -c "import os; print(os.getenv('META_ADS_ACCOUNT_ID'))"
```
If it prints `act_1234567890`, use `$META_ADS_ACCOUNT_ID` directly (NOT `act_$META_ADS_ACCOUNT_ID`). Double-prefixing produces `act_act_...` and every call fails with "Object does not exist."

**Campaign migration awareness:** If ads-manager Workflow 4 (switch objective) was used, there will be a NEW active campaign AND an OLD paused campaign. The old campaign holds historical spend/clicks. Query both and sum their metrics for accurate lifetime totals. The new campaign starts from zero and may show 0 impressions for 24-48h while Meta enters learning phase.

For each active campaign, use `terminal` to call Meta API. The `time_range` JSON must be URL-encoded with urllib.parse.quote:
```bash
export YESTERDATE="YYYY-MM-DD"
cat > /tmp/encode_tr.py << 'EOF'
import urllib.parse, os
d = os.environ['YESTERDATE']
print(urllib.parse.quote('{"since":"'+d+'","until":"'+d+'"}'))
EOF
TIME_RANGE=$(python3 /tmp/encode_tr.py)
# Then use $TIME_RANGE in the Meta API URL
```
**Why the heredoc + export pattern?** Inline `python3 -c "...$YESTERDATE..."` fails when dates contain hyphens (e.g., `2026-04-21`) because bash expands them as arithmetic expressions before python sees them, causing `SyntaxError: leading zeros in decimal integer literals`. Always `export` the variable and read it via `os.environ` in a temp script.
Also pull last 7 days by expanding the time_range for trend context.

Extract link clicks from `actions` where `action_type == "link_click"` (this is the conversion/click count, separate from the top-level `clicks` which includes all click types).

**Also extract checkout signals:** Look for `initiate_checkout`, `offsite_conversion.fb_pixel_initiate_checkout`, and `onsite_web_initiate_checkout` in actions. These indicate visitors reached the payment step — if present but Stripe shows 0 purchases, the checkout flow is broken (not the ads).

### Step 3 — Pull Stripe purchases
Use `terminal` to query Stripe. Save to temp file first (security scan blocks curl|python3 pipes). Convert dates to Unix timestamps:
```bash
export STRIPE_KEY="$STRIPE_SECRET_KEY"
export YEAR=2026
export MONTH=4
export DAY=21
cat > /tmp/encode_stripe.py << 'EOF'
import datetime, os
y, m, d = int(os.environ['YEAR']), int(os.environ['MONTH']), int(os.environ['DAY'])
start = int(datetime.datetime(y, m, d, 0, 0, 0).timestamp())
end = int(datetime.datetime(y, m, d+1, 0, 0, 0).timestamp())
print(start)
print(end)
EOF
UNIX_START=$(python3 /tmp/encode_stripe.py | head -n1)
UNIX_END=$(python3 /tmp/encode_stripe.py | tail -n1)
curl -s "https://api.stripe.com/v1/charges?limit=100&created%5Bgte%5D=$UNIX_START&created%5Blt%5D=$UNIX_END" \
  -u "$STRIPE_KEY:" -o /tmp/stripe_charges.json
# Then parse /tmp/stripe_charges.json with python3
```
**Why the heredoc + export pattern?** Same reason as Meta encoding — inline `python3 -c "...$DAY..."` with hyphens triggers bash arithmetic expansion errors.
Filter by `metadata.idea_id` or match `description` to product name.
Count successful charges and total revenue.

### Step 4 — Compute metrics
Calculate per-campaign:
- `spend` = Meta reported spend (USD)
- `clicks` = Meta link clicks
- `ctr` = clicks / impressions
- `cpc` = spend / clicks
- `purchases` = Stripe successful charges for this idea
- `revenue` = Stripe total (purchases × price)
- `cpa` = spend / purchases (None if 0 purchases)
- `roi` = (revenue - spend) / spend (None if 0 spend)
- `days_running` = today - launched_at

### Step 4.5 — Pull website analytics (NEW)

### Step 4.5 — Pull website analytics (NEW)

**First — check which MVPs actually have tracking installed:**  
```bash
grep -r "yourdomain.com/src/tracker.js" ~/.hermes/mvps/*/src/
```  
Not all MVPs may have the tracker script. Only those with the `<script src="https://yourdomain.com/src/tracker.js" data-source="...">` tag in their worker.js will report data.

**If the tracker is missing:**  
- Flag this explicitly in the report: "⚠️ ANALYTICS TRACKER MISSING — behavioral data unavailable"
- Consider sending an alert to the user to install the script
- Proceed with ad performance metrics only (Meta + Stripe), but note that conversion funnel diagnosis will be limited

**Primary method — web endpoint:**  
```bash
curl -s "https://yourdomain.com/track/analytics?days=1"
curl -s "https://yourdomain.com/track/analytics?days=7"
curl -s "https://yourdomain.com/track/events?date=YESTERDATE"
```  
... (rest unchanged)
**Fallback — direct Cloudflare KV API:**
If web endpoints fail, query the analytics KV namespace directly. The namespace binding is `ANALYTICS` on the `your-analytics` worker. Use the Cloudflare REST API:
```
GET /accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{KEY}
```
KV key schema:
- `events:YYYY-MM-DD` — raw event array
- `summary:YYYY-MM-DD` — daily aggregates (pageviews, clicks, scroll_depths, sections, sources)

Use the same heredoc + export pattern as Meta/Stripe encoding to avoid bash arithmetic errors with hyphens in dates. Query via `terminal` tool (credentials available in terminal env).

**What to look for:**
- `sources` breakdown — filter by `source == idea_id` to isolate ad-driven behavior. Internal traffic (e.g., `yourdomain.com`) can mask landing-page conversion issues.
- `scroll_depths` — if 25% is high but 75%+ is near zero, visitors bounce early (landing page problem)
- `sections` — which sections people actually see (hero vs values vs CTA)
- `clicks` — are people clicking buy buttons or just scrolling past?
- `pageviews` — total visits to correlate with ad clicks (discrepancy = bot traffic or tracking issues)
- `time_on_page` events — avg seconds per session; <15s = bounce, >60s = real engagement

**Red flags to flag in report:**
- High pageviews but 0 scroll depth events = page broken or loading too slow
- All scroll stops at same depth = content wall or visual cliff killing engagement
- Section views show hero seen but CTA section never reached = page too long, CTA buried
- Click events exist but none on buy button = CTA not visible or compelling enough
- **High scroll depth (75-100%) but zero CTA clicks** = CTA is broken, invisible, or uncompelling despite strong engagement
- Ad clicks (e.g., 17) but tracked pageviews (e.g., 31) seem mismatched — check if tracker fires before bounce
- **Meta reports many landing_page_views but analytics shows near-zero events for that source** = tracker was installed AFTER the campaign ran, or the `data-source` tag was missing/wrong during traffic. This is a broken funnel — don't blame the landing page for zero conversions if you can't verify visitor behavior.

**Internal traffic pollution:** Clicks from `yourdomain.com` (internal nav) can swamp ad-driven data. Always report ad-driven behavior separately by filtering `source == idea_id`.

Include a 2-3 line "Site Behavior" section in the daily report summarizing key patterns.

### Step 5 — Determine signal
Evaluate in priority order:
```
PAUSE_ALL:   days >= 3 AND clicks >= 100 AND spend > 15 AND purchases == 0
DOUBLE_DOWN: roi > 2.0 → increase daily_budget ×1.4 (cap: original ×2)
SCALE:       roi > 1.0 → increase daily_budget ×1.2 (cap: original ×2)  
SWAP_COPY:   impressions >= 100 AND ctr < 1.0 AND purchases == 0
KILL:        spend >= hard_stop AND purchases == 0
MAINTAIN:    default
```

### Step 6 — Update state files
Use `execute_code` to write `~/.hermes/data/ads/{idea_id}/metrics/YYYY-MM-DD.json`:
```json
{
  "date": "YYYY-MM-DD",
  "meta": {"impressions": 0, "clicks": 0, "ctr": 0, "spend": 0, "cpc": 0},
  "stripe": {"purchases": 0, "revenue": 0},
  "combined": {"cpa": null, "roi": null, "signal": "MAINTAIN"}
}
```

Then update `campaigns.json`:
- `daily_snapshots_cached` is a **dict** (not a list) — overwrite with:
  ```json
  {"last_updated": "YYYY-MM-DD", "impressions": 0, "clicks": 0, "ctr": 0, "conversions": 0, "spend": 0, "signal": "MAINTAIN"}
  ```
  Also sync the nested copy under `platforms.meta.daily_snapshots_cached` if it exists — stale nested snapshots cause incorrect dashboard reads by other skills.
- `total_spend_lifetime` (add yesterday's spend)
- `last_optimized` timestamp
- If signal triggered: update `status`, `current_daily_budget`, append to `optimization_history`
- **Meta API sync for KILL/PAUSE_ALL**: When pausing or killing a Meta campaign, update `campaigns.json` status AND call the Meta API to pause the campaign directly:
  ```bash
  curl -s -X POST "https://graph.facebook.com/v18.0/$CAMPAIGN_ID?status=PAUSED&access_token=$ACCESS_TOKEN"
  ```
  Failure to sync state means Meta continues spending while local state says paused.

### Step 7 — Format report
Output a concise daily summary:
```
AD DAILY REPORT — YYYY-MM-DD

[idea-id]
  Spend: $X.XX | Clicks: XX | CTR: X.X% | CPC: $X.XX
  Purchases: X | Revenue: $XX | CPA: $X.XX | ROI: X.XX
  Signal: MAINTAIN/SCALE/PAUSE/etc
  Days running: X | Budget: $X/day
  Action: [what was done or "no change"]

---

SITE BEHAVIOR — YYYY-MM-DD

  Pageviews: XX | Sources: {squeezed: X, coven-compass: X}
  Scroll depth: 25%: X | 50%: X | 75%: X | 100%: X
  Key sections seen: [list top sections]
  Click patterns: [buy buttons vs other clicks]
  Red flags: [any conversion funnel issues]
```

The SITE BEHAVIOR section should be 3-5 lines max. Focus on actionable insights: "75% of visitors never scroll past hero" is useful. "23 pageviews recorded" is not.

### Step 8 — Deliver
Send report to user via Telegram. If signal is PAUSE/KILL, alert immediately.

## Pitfalls
- Meta API returns yesterday's data only if called after midnight — schedule cron at 9am+ to avoid stale data
- **Campaign IDs are nested**: `platforms.meta.campaign_id` in campaigns.json, NOT at top level `campaign_id`
- **Check campaign status before pulling insights** — an ACTIVE campaign may still have $0 spend for a day if budget was exhausted or delivery was zero. Empty insights array with no error = campaign simply didn't spend. Distinguish from PAUSED campaigns (which also return empty data)
- **Tracker script may be missing from some MVPs** — not all storefronts have `<script src="https://yourdomain.com/src/tracker.js">`. Only MVPs with the script report to your-analytics. Search `~/.hermes/mvps/*/src/worker.js` for `tracker.js` to know which stores have data.
  - **Quick verification**: Use the reference script `references/check_tracker_installation.py` to get a summary of which MVPs have the tracker installed.
- **Meta API returns yesterday's data only if called after midnight** — schedule cron at 9am+ to avoid stale data
- **Campaign IDs are nested**: `platforms.meta.campaign_id` in campaigns.json, NOT at top level `campaign_id`
- **Meta `time_range` must be URL-encoded** — use `urllib.parse.quote()` on the JSON string, bare curly braces get stripped. **Always use a temp python script with `export`ed env vars** — inline `python3 -c "...$YESTERDATE..."` fails on dates with hyphens because bash treats `2026-04-21` as arithmetic (leading zero syntax error)
- **Stripe charges API**: write HTTP output to a temp file first, then parse with python3 — direct pipe to interpreter blocked by security scan. **Also avoid `cat file | python3 -m json.tool`** — security scan blocks any pipe from file/command to python interpreter. Use `python3 -c "import json; print(json.dumps(json.load(open('/tmp/file.json')), indent=2))"` instead
- Stripe unix timestamp conversion: same heredoc/export pattern applies — inline `python3 -c "...$DAY..."` with hyphens triggers bash arithmetic expansion errors
- Stripe charges API filters by `created` timestamp (Unix), not date string — convert dates with `datetime.timestamp()`
- Stripe bracket params need URL encoding: `created%5Bgte%5D` not `created[gte]`
- `ctr` from Meta is a full float string like "2.134647" — parse to float before comparing
- **`daily_snapshots_cached` is a dict** (keys: last_updated, impressions, clicks, ctr, conversions, spend, signal), NOT a list — overwrite, don't append
- Campaigns in `pre_launch` status should be skipped, not queried
- If Meta token expires, API returns error code 190 — alert user to refresh token
- Stripe webhook events are real-time but this skill uses polling — check charges endpoint, not events
- **Website analytics endpoint** is at `yourdomain.com/track/analytics?days=N` — returns JSON array of daily summaries. Events are tagged with `src` field matching MVP script names (e.g., "squeezed", "coven-compass"). Use `days=1` for yesterday, `days=7` for trend. Raw events at `/track/events?date=YYYY-MM-DD` for deep diagnosis.
- **KV analytics fallback**: analytics KV namespace keys follow `events:YYYY-MM-DD` and `summary:YYYY-MM-DD` schema. Use CF REST API directly if web endpoints fail.
- **`days_running` calculation**: `datetime.fromisoformat(campaigns['launched_at'])` may return offset-aware or offset-naive datetimes depending on the string format (with/without `Z` suffix). Always normalize: parse with `.replace('Z', '+00:00')`, then ensure both datetimes have `tzinfo=timezone.utc` before subtracting
- **Bounce-before-tracker gap**: if Meta reports 17 clicks but analytics shows 31 pageviews, some may be reloads/returns. But if clicks exceed pageviews, the tracker may fire too late (after bounce) or the landing page loads too slowly. Consider this when diagnosing zero-conversion funnels.
- **Zero spend on active campaign** = delivery failure, not just lack of budget. If an active campaign reports $0 spend and 0 impressions for a full day, check Meta Ads Manager directly for policy disapprovals, audience exhaustion, or billing issues.
- **Exception — brand-new purchase-optimized campaign with cold pixel:** A campaign created within the last 24-48h may legitimately show 0 impressions while Meta's algorithm learns. Do NOT flag as delivery failure until it has been active for 48+ hours. Distinguish by checking `created_time` on the ad set.
- **Young campaign override**: If a campaign is very new (days_running < 5) and total lifetime spend is still low, consider overriding aggressive PAUSE/KILL signals to MAINTAIN to avoid killing a purchase-optimized campaign before Meta's learning phase completes.
- **Analytics `days=1` may return empty array instead of yesterday's data**: Observed behavior — `/track/analytics?days=1` returned `[]` while `/track/analytics?days=7` correctly included yesterday's data (2026-05-05). The `days=1` endpoint may return only current-day partial data (which is empty if events haven't fired yet in the current server window). **Always query `days=7` as primary** and extract the entry where `date == YESTERDATE`. Use `days=1` only as a quick check, but verify it's non-empty before trusting it.
- Analytics `days=1` may return current-day data: The `/track/analytics?days=1` endpoint can return the current calendar day (server-local time or UTC) rather than "yesterday" as expected. Always verify the `date` field in the response matches the intended `YESTERDATE` before using the numbers. If mismatched, fall back to `/track/events?date=YESTERDATE` for raw event-level data.
- **Analytics sections reveal wrong landing page**: If `section_view` events show generic/root-domain content (e.g., "MISSION", "MANIFESTO", "EST. 2026") instead of product-specific sections, ad traffic is landing on the wrong page (likely the root domain instead of the product subdomain). Cross-check `landing_page_url` in `campaigns.json` against the `path` field in analytics events. A `path: "/"` with `src: "idea_id"` when the landing page should be a subdomain indicates a broken or misconfigured redirect.
- **Scroll-to-bounce rate from raw events**: Count unique sessions (`sid`) in raw events, then count how many have at least one `scroll_depth` event. `sessions_without_scroll / total_sessions` is a useful bounce proxy. >70% bounce with no scroll = landing page load or engagement problem.
- **Deep scroll + zero CTA click = CTA failure**: When 75-100% scroll depth is common among engaged users but `click` events show zero buy-button or checkout clicks, the CTA is likely broken, invisible below the fold, or the offer does not match the ad promise. This is one of the strongest signals for a SWAP_COPY or landing-page-fix decision.
- **Raw events API returns dict, not array**: The `/track/events?date=YYYY-MM-DD` endpoint returns `{"date": "...", "count": N, "events": [...]}` — NOT a flat JSON array. Access events via `data["events"]`, not directly on the root object. Hitting `.get()` on raw response without unwrapping causes `AttributeError: 'str' object has no attribute 'get'`.
- **Initiate checkout vs purchase gap**: Meta pixel may report `initiate_checkout` or `offsite_conversion.fb_pixel_initiate_checkout` actions while Stripe shows 0 purchases. This means visitors reach the payment step but abandon before completing — a checkout/payment flow problem, not an ad creative problem. Flag this explicitly in reports: "X checkouts initiated, 0 completed" points to pricing mismatch, broken payment form, or trust issues at checkout.
- **Click target tracking may be broken**: If ALL click events show `target=?` (unknown), the tracker.js click handler is not capturing button names. This means you cannot verify whether buy buttons are being clicked — treat as a data quality issue and flag for fix. Without proper click targets, "zero CTA clicks" conclusions are unreliable.
- **Interacting constraints — auto_stop, scheduled_end_date, hard_stop**: A campaign may hit multiple stop conditions simultaneously. Priority for decision-making:
  1. If `scheduled_end_date` has passed AND hard_stop breached → KILL (campaign is done).
  2. If `auto_stop` is enabled and stop_time is today/tomorrow → MAINTAIN or KILL; do not SCALE or DOUBLE_DOWN into an auto_stop window.
  3. If new campaign age < 5 days (post-migration) and lifetime spend is still low, override KILL/PAUSE_ALL to MAINTAIN to avoid killing a purchase-optimized campaign before Meta's learning phase completes.
- **Missing Stripe credentials**: If the `STRIPE_SECRET_KEY` environment variable is not set or returns an authentication error, use 0 purchases and $0 revenue as fallback values. This ensures the workflow completes and provides a baseline for campaign performance analysis. Flag the missing credentials in the report or via a separate alert to the user.

## Verification
- `metrics/YYYY-MM-DD.json` exists for each active campaign with all fields populated
- `campaigns.json` updated with latest cached metrics and spend totals
- Report delivered to Telegram with correct figures matching Meta dashboard
- Signal logic matches ads-manager optimization thresholds
