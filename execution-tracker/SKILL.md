---
name: execution-tracker
description: Autonomous post-launch monitoring and optimization - collects metrics, signals decisions, and takes actions autonomously. Use when asked to track MVP performance, run daily business reports, monitor revenue/churn, or automate optimization decisions across deployed products.
---

# Execution Tracker - Autonomous Business Optimization

## Purpose
Monitor deployed MVPs, collect performance metrics, signal strategic decisions, and autonomously optimize where possible. The "set it and forget it" layer that runs your businesses.

## Philosophy
- Measure everything that matters
- Signal decisions with data, not feelings
- Automate optimizations within safe boundaries
- Report daily, act autonomously, escalate strategically

## Setup (One-Time)

### Initial Configuration
When first run, create config file at `/workspace/playground/data/execution-tracker-config.json`:

```json
{
  "mvps": [],
  "settings": {
    "daily_report_time": "09:00",
    "telegram_reports": true,
    "autonomous_optimization": true,
    "safe_mode": false,
    "auto_pause_ads_on_kill": true,
    "kill_escalation_days": 7,
    "pause_before_kill_confirm": true
  },
  "thresholds": {
    "double_down": {
      "cac_ltv_ratio": 5,
      "conversion_rate": 0.05,
      "mrr_growth": 0.20,
      "max_churn": 0.05
    },
    "optimize": {
      "cac_ltv_ratio": 3,
      "conversion_rate": 0.02
    },
    "pivot": {
      "days_no_growth": 30,
      "high_traffic_low_conversion": 0.01
    },
    "kill": {
      "cac_ltv_ratio": 3,
      "days_no_growth": 90,
      "max_burn": 500
    }
  }
}
```

### Add MVP to Tracking
Either:
1. Auto-detected from business-ideas.json (mvp_status = "deployed")
2. Manual add via command

**MVP Tracking Record:**
```json
{
  "id": "expense-tracker",
  "name": "Expense Tracker",
  "deployed_date": "2026-03-01",
  "mvp_url": "https://expense-tracker.pages.dev",
  "api_url": "https://expense-tracker-api.workers.dev",
  "stripe_product_id": "prod_xxx",
  "database_connection": "d1://expense-tracker-db",
  "analytics_site_id": "plausible-site-id",
  "status": "active",
  "metrics_history": []
}
```

## Daily Workflow (Runs Autonomously)

### Step 1: Collect Metrics (All MVPs) - PARALLEL SUBAGENT VERSION

**1a. Identify Deployed MVPs**

Read `/workspace/playground/data/execution-tracker-config.json` to get list of tracked MVPs.
Filter for `status == "active"` and extract:
- mvp_id, name, mvp_url, api_url
- stripe_product_id, database_connection, analytics_site_id
- ad_campaigns_file path (if exists)

**1b. Parallel Metrics Collection via Subagents (NEW)**

IF you have N >= 2 deployed MVPs, SPAWN PARALLEL SUBAGENTS for metrics collection:

1. Use the `delegate_task` tool with batch mode:
   - Call `delegate_task(tasks=[...], max_iterations=15)` where tasks is an array of N task objects
   - Each task object has:
     - **goal**: "Collect complete metrics snapshot for MVP {mvp_name} (ID: {mvp_id}). Return ONLY a JSON object with these exact keys: mvp_id, date, revenue, traffic, engagement, health, ads. If any metric is unavailable, return null for that field. Do NOT include markdown formatting or explanations."
     - **context**: "{mvp_name} configuration:\n- ID: {mvp_id}\n- MVP URL: {mvp_url}\n- API URL: {api_url}\n- Stripe Product ID: {stripe_product_id}\n- Database Connection: {database_connection}\n- Analytics Site ID: {analytics_site_id}\n\nData file paths:\n- Ad campaigns: /workspace/playground/data/ads/{mvp_id}/campaigns.json\n- Ad metrics: /workspace/playground/data/ads/{mvp_id}/metrics/\n- Metrics output directory: /workspace/playground/data/mvp-metrics/{mvp_id}/\n\nCredentials available via environment: STRIPE_API_KEY, PLAUSIBLE_API_KEY"
     - **toolsets**: ["terminal", "file"]

2. Wait for all subagent results to return (this is blocking parallel execution)

3. Parse each subagent's response:
   - Extract the JSON object from the response (may be wrapped in markdown code blocks)
   - Validate it has required keys: mvp_id, revenue, traffic, engagement, health, ads
   - If parsing succeeds, store in `metrics_by_mvp` dictionary keyed by mvp_id
   - If parsing fails for any subagent, fall back to serial collection (Step 1c) for that specific MVP only

4. Log which mode was used: "Collected metrics via parallel subagents" or "Fell back to serial collection for {mvp_id}"

**Performance Impact:**
- Serial: N MVPs × ~3 min each = 3N minutes total
- Parallel: ~5 minutes regardless of N (subagents run concurrently)
- With 10 MVPs: 30 min → 5 min (6x speedup)

IF N = 1 or all subagent spawns fail, skip to Step 1c (serial collection).

---

**1c. Serial Fallback Collection (For Single MVP or Subagent Failures)**

If NOT using parallel subagents, collect metrics for each MVP sequentially:
```python
ad_metrics = read_json(f"/workspace/playground/data/ads/{mvp.id}/metrics/{today}.json")

# Today's combined spend
ad_spend_today = (
    ad_metrics["google"]["spend_today"] +
    ad_metrics["meta"]["spend_today"]
)

# 30-day spend: sum all metrics files from last 30 days
metrics_files = list_files(f"/workspace/playground/data/ads/{mvp.id}/metrics/", last_n_days=30)
ad_spend_30d = sum(
    (f["google"]["spend_today"] + f["meta"]["spend_today"])
    for f in metrics_files
)
# OR use Meta's 30d field if available:
# ad_spend_30d = ad_metrics["meta"]["spend_30d"] + ad_metrics["google"]["spend_30d"]

# 30-day conversions
total_conversions_30d = sum(
    (f["google"]["conversions"] + f["meta"]["conversions"])
    for f in metrics_files
)

# Blended CPA (null if no conversions)
blended_cpa = (
    ad_spend_30d / total_conversions_30d
    if total_conversions_30d > 0 else None
)

# Best platform: lower CPA or higher conversions
g_cpa = ad_metrics["google"]["spend_30d"] / ad_metrics["google"]["conversions_30d"] if ad_metrics["google"]["conversions_30d"] > 0 else float("inf")
m_cpa = ad_metrics["meta"]["spend_30d"] / ad_metrics["meta"]["conversions_30d"] if ad_metrics["meta"]["conversions_30d"] > 0 else float("inf")
best_platform = "google" if g_cpa <= m_cpa else "meta"

# Active campaigns check
campaigns = read_json(f"/workspace/playground/data/ads/{mvp.id}/campaigns.json")
active_campaigns = any(c["status"] == "active" for c in campaigns)

# Ad signal from combined metrics
ad_signal = ad_metrics.get("signal", None)  # MAINTAIN/SCALE/DOUBLE_DOWN/PAUSE_ALL

g_spend = ad_metrics["google"]["spend_today"]
m_spend = ad_metrics["meta"]["spend_today"]
```

If file does not exist: set all ad fields to null/0, `active_campaigns=False`

```python
# Fallback when no ad data
ad_spend_today = 0
ad_spend_30d = 0
total_conversions_30d = 0
blended_cpa = None
best_platform = None
active_campaigns = False
ad_signal = None
g_spend = 0
m_spend = 0
```

Merge into the MVP's daily metrics snapshot:
```python
daily_snapshot["ads"] = {
    "ad_spend_today": ad_spend_today,
    "ad_spend_30d": ad_spend_30d,
    "total_conversions_30d": total_conversions_30d,
    "blended_cpa": blended_cpa,        # used as paid_cac in economics
    "best_platform": best_platform,
    "active_campaigns": active_campaigns,
    "ad_signal": ad_signal,
    "g_spend_today": g_spend,
    "m_spend_today": m_spend
}

# Burn rate: include ad spend in total monthly costs
total_monthly_spend = mrr_expenses + ad_spend_30d

# Economics: blended_cpa becomes paid_cac
economics["paid_cac"] = blended_cpa

# Signal classification: factor in ad_signal
# If ad_signal == "PAUSE_ALL", weight toward KILL/PIVOT
# If ad_signal == "DOUBLE_DOWN" or "SCALE", weight toward DOUBLE_DOWN
```

**1c. Engagement (Database Query)**
```python
# Query D1 database
# SELECT COUNT(DISTINCT user_id) FROM activity WHERE date > NOW() - INTERVAL 1 DAY

metrics = {
    "daily_active_users": ...,
    "weekly_active_users": ...,
    "avg_session_duration": ...,
    "feature_usage": {
        "core_feature": usage_count,
        "secondary_feature": usage_count
    }
}
```

**1d. Health Metrics**
```python
# Ping endpoint
response = terminal("curl -w '%{http_code}' -s https://mvp.pages.dev/health")
uptime = 1 if response.output == "200" else 0

# Check Sentry for errors
# GET https://sentry.io/api/0/projects/{org}/{project}/issues/
error_count_24h = len(errors)

metrics = {
    "uptime": uptime,
    "errors_24h": error_count_24h,
    "response_time_ms": avg_response_time
}
```

**Store metrics:**
```python
# Append to /workspace/playground/data/mvp-metrics/{mvp-id}/2026-03-08.json
{
    "date": "2026-03-08",
    "revenue": {...},
    "traffic": {...},
    "engagement": {...},
    "health": {...}
}
```

### Step 2: Calculate Derived Metrics

For each MVP, calculate:

**Economics:**
- **LTV** = avg_monthly_revenue × avg_retention_months
  - If < 3 months data, estimate retention at 12 months
- **CAC** = total_ad_spend_30d / new_customers_30d
- **CAC:LTV ratio** = CAC / LTV
- **Months to recover CAC** = CAC / avg_monthly_revenue
- **Gross margin** = revenue - (hosting_costs + payment_fees)

**Growth:**
- **MRR growth rate** = (current_mrr - last_month_mrr) / last_month_mrr
- **Customer growth rate** = similar calculation
- **Burn rate** = monthly_costs - monthly_revenue (if negative)

**Engagement:**
- **DAU/MAU ratio** = daily_active / monthly_active (stickiness)
- **Activation rate** = users_who_used_core_feature / total_signups
- **Time to first value** = avg time from signup to first core action

### Step 3: Signal Classification

Based on thresholds, classify each MVP:

```python
def classify_mvp_status(metrics, thresholds):
    cac_ltv = metrics["cac"] / metrics["ltv"]
    
    # DOUBLE DOWN signals
    if (cac_ltv < 1/thresholds["double_down"]["cac_ltv_ratio"] and
        metrics["conversion_rate"] > thresholds["double_down"]["conversion_rate"] and
        metrics["mrr_growth"] > thresholds["double_down"]["mrr_growth"] and
        metrics["churn"] < thresholds["double_down"]["max_churn"]):
        return "DOUBLE_DOWN"
    
    # KILL signals
    if (cac_ltv > 1/thresholds["kill"]["cac_ltv_ratio"] or
        metrics["days_no_growth"] > thresholds["kill"]["days_no_growth"] or
        metrics["monthly_burn"] > thresholds["kill"]["max_burn"]):
        return "KILL"
    
    # PIVOT signals
    if (metrics["traffic"] > 1000 and 
        metrics["conversion_rate"] < thresholds["pivot"]["high_traffic_low_conversion"]):
        return "PIVOT"
    
    if metrics["days_no_growth"] > thresholds["pivot"]["days_no_growth"]:
        return "PIVOT"
    
    # Default to OPTIMIZE
    return "OPTIMIZE"
```

### Step 4: Autonomous Actions (The Magic)

Based on classification, take actions WITHOUT asking:

**DOUBLE DOWN (Winning MVPs):**

1. **Increase ad spend** (within limits):
```python
# If CAC < LTV/5, increase daily ad budget by 20%
# Max increase: 2x original budget
current_budget = get_ad_budget(mvp_id)
if current_budget * 2 < initial_budget * 2:
    new_budget = current_budget * 1.2
    set_ad_budget(mvp_id, new_budget)
    log_action("Increased ad budget to ${new_budget}/day (healthy CAC)")
```

2. **Email power users for testimonials** (via email-campaigns skill):
```python
# Find top 10% most active users
power_users = query_db("SELECT email FROM users WHERE activity_score > 90")
# Trigger testimonial sequence via email-campaigns
# email-campaigns handles the actual sending, tracking, and follow-ups
log_action(f"Triggered testimonial sequence for {len(power_users)} power users via email-campaigns")
```

3. **Start building next feature** (from usage data):
```python
# Identify most-requested feature from support emails or usage patterns
next_feature = analyze_feature_requests()
log_action(f"Recommendation: Build {next_feature} next (requested by 12 users)")
# Could even spawn subagent to build it autonomously if simple enough
```

**OPTIMIZE (Marginal MVPs):**

1. **A/B test pricing**:
```python
# Test 20% price reduction for new signups
create_stripe_price(
    product_id=mvp.stripe_product_id,
    amount=current_price * 0.8,
    nickname="test_lower_price"
)
update_landing_page_variant(
    mvp_id=mvp.id,
    variant="b",
    price=current_price * 0.8
)
log_action("Started A/B test: $10/mo vs $8/mo (testing price sensitivity)")
```

2. **Send win-back emails to churned users** (via email-campaigns skill):
```python
churned_users = query_db("""
    SELECT email, churned_date FROM users 
    WHERE status = 'churned' AND churned_date > NOW() - INTERVAL 30 DAY
""")

for user in churned_users:
    # Activate win-back sequence via email-campaigns
    # email-campaigns handles sending, timing, and follow-ups
    pass

log_action(f"Triggered win-back sequences for {len(churned_users)} churned users via email-campaigns")
```

3. **Improve onboarding**:
```python
# Identify where users drop off
dropoff_step = analyze_funnel()
# Generate hypothesis
hypothesis = f"Users dropping off at {dropoff_step} - likely too complex"
# Auto-create simplified version
log_action(f"Hypothesis: {hypothesis}. Consider simplifying {dropoff_step}.")
```

**PIVOT (Broken MVPs):**

1. **Generate customer interview questions**:
```python
questions = [
    "What problem were you trying to solve when you signed up?",
    "Why didn't you end up paying for [Product]?",
    "What would make this worth ${price}/month to you?",
    "What's your current solution for this problem?"
]

# Email 20 signups who didn't convert
non_converters = query_db("SELECT email FROM users WHERE paid = 0 LIMIT 20")
send_email(
    to=non_converters,
    subject="Quick question - $50 Amazon gift card",
    body=f"I'm trying to understand why [Product] wasn't worth it. 15-min call? You get $50 Amazon gift card."
)
log_action("Sent interview requests to 20 non-converting users")
```

2. **Test new positioning**:
```python
# Generate 3 alternative headlines using pain point analysis
alternatives = [
    "Stop wasting 2 hours/week on [task]",
    "Finally, [benefit] without [pain]",
    "The only [solution] you'll ever need"
]

# Deploy as landing page variants
for i, headline in enumerate(alternatives):
    create_landing_page_variant(mvp_id, variant=chr(97+i), headline=headline)

log_action("Testing 3 new headlines - will report results in 7 days")
```

**KILL (Dead MVPs):**

THIS IS THE ONLY ONE THAT REQUIRES APPROVAL, BUT ADS AUTO-PAUSE IMMEDIATELY:

```python
if status == "KILL":
    # Calculate exact loss/runway
    monthly_burn = costs - revenue
    
    # AUTO-PAUSE ALL AD CAMPAIGNS IMMEDIATELY (safety first!)
    ads_paused = False
    try:
        campaigns_file = f"/workspace/playground/data/ads/{mvp.id}/campaigns.json"
        if os.path.exists(campaigns_file):
            campaigns = read_json(campaigns_file)
            for campaign in campaigns:
                if campaign.get("status") == "active":
                    # Pause Google Ads campaign
                    if "google" in campaign.get("platform", ""):
                        call_google_ads_api(f"PATCH /campaigns/{campaign['id']} status=PAUSED")
                    # Pause Meta ad set
                    elif "meta" in campaign.get("platform", ""):
                        call_meta_ads_api(f"POST /{campaign['ad_set_id']}/status=PAUSED")
                    
                    log_action(f"Auto-paused {campaign['platform']} campaign (KILL signal)")
            ads_paused = True
    except Exception as e:
        log_error(f"Failed to auto-pause ads: {e}")
    
    # Don't auto-kill - ask first, but keep ads paused
    message = f"""
🚨 KILL Signal: {mvp.name}

Economics are broken:
- CAC: ${metrics.cac}
- LTV: ${metrics.ltv}
- CAC:LTV ratio: {metrics.cac/metrics.ltv:.2f} (need < 0.33)
- Monthly burn: ${monthly_burn}
- Days no growth: {metrics.days_no_growth}

{'✅ **ADS AUTO-PAUSED** - No further spend while you decide' if ads_paused else '⚠️ **AD PAUSE FAILED** - Check manually'}

Reply within 7 days:
'kill {mvp.id}' → Confirm shutdown (ads stay paused)
'keep {mvp.id}' → Resume ads, continue monitoring
    """
    
    send_telegram_message(message)
    
    # Schedule escalation check (auto-confirm kill after 7 days if no response)
    schedule_cronjob(
        name=f"kill-escalation-{mvp.id}",
        schedule=f"0 {9} *+{settings['kill_escalation_days']} * *",
        prompt=f"""
Check KILL signal for {mvp.id}. If no user response after 7 days, auto-confirm kill.
Database: ~/workspace/playground/data/business-ideas.json
        """,
        deliver="telegram"
    )
```

### Step 5: Generate Daily Report

Send comprehensive report via Telegram:

```markdown
📊 Daily MVP Health Report - March 8, 2026

🚀 DOUBLE DOWN (2 MVPs)
━━━━━━━━━━━━━━━━━━━━━━━━
**Expense Tracker** 💰
- Revenue: $1,247 MRR (+$127 this week)
- Customers: 62 (+8 new, -1 churn)
- CAC: $12, LTV: $180 (15:1 ratio ✓)
- Conversion: 6.2%
- Ad Spend Today: $42 (Google: $28 / Meta: $14)
- Paid CAC: $14.00 (target: < LTV/5 = $36)
- Ad Signal: SCALE
- Best Platform: google
- Action Taken: Increased ad budget to $50/day
- Next: Build "Receipt OCR" feature (12 requests)

**Meal Planner** 🥗
- Revenue: $890 MRR (+$65 this week)
- Customers: 45 (+5 new, -0 churn)
- CAC: $18, LTV: $156 (8.7:1 ratio ✓)
- Conversion: 4.8%
- Ad Spend Today: $31 (Google: $12 / Meta: $19)
- Paid CAC: $19.50 (target: < LTV/5 = $31.20)
- Ad Signal: MAINTAIN
- Best Platform: meta
- Action Taken: Sent testimonial requests to 5 power users

⚙️ OPTIMIZE (1 MVP)
━━━━━━━━━━━━━━━━━━━━━━━━
**Habit Tracker** 📅
- Revenue: $340 MRR (+$12 this week)
- Customers: 17 (+1 new, -0 churn)
- CAC: $28, LTV: $120 (4.3:1 ratio)
- Conversion: 2.1% (needs improvement)
- Ad Spend Today: $22 (Google: $22 / Meta: $0)
- Paid CAC: $28.00 (target: < LTV/5 = $24.00 ⚠️)
- Ad Signal: MAINTAIN
- Best Platform: google
- Action Taken: Started A/B test $20/mo vs $15/mo
- Action Taken: Win-back emails to 8 churned users

🔄 PIVOT (1 MVP)
━━━━━━━━━━━━━━━━━━━━━━━━
**Budget App** 💸
- Revenue: $0 MRR
- Signups: 127 (0 conversions in 30 days)
- Traffic: 2,400 visitors (conversion 0%)
- Problem: High traffic, zero conversions
- Ad Spend Today: $18 (Google: $10 / Meta: $8)
- Paid CAC: N/A (0 conversions)
- Ad Signal: PAUSE_ALL
- Best Platform: N/A
- Action Taken: Testing 3 new headlines
- Action Taken: Sent interview requests (offering $50)
- Hypothesis: Price too high or value unclear

🚨 KILL CANDIDATE (1 MVP)
━━━━━━━━━━━━━━━━━━━━━━━━
**Workout Logger** 🏋️
- Revenue: $0 MRR (60 days post-launch)
- Signups: 23 total
- CAC: $45, no paying customers
- Monthly burn: $40
- Ad Spend Today: $15 (Google: $0 / Meta: $15)
- Paid CAC: N/A (0 conversions)
- Ad Signal: PAUSE_ALL
- Best Platform: N/A
- Recommendation: SHUT DOWN
- Reply 'kill workout-logger' to confirm

━━━━━━━━━━━━━━━━━━━━━━━━
💰 Portfolio Summary
- Total MRR: $2,477 (+$204 this week)
- Total customers: 124
- Avg CAC: $18
- Blended CAC:LTV: 9.2:1
- Monthly profit: $2,437 (after costs)
- Total Ad Spend (30d): $2,790 (Google: $1,860 / Meta: $930)
- Blended Paid CAC: $20.22 (across all converting MVPs)

🎯 Focus This Week:
1. Expense Tracker: Build receipt OCR
2. Meal Planner: Collect testimonials
3. Budget App: Run customer interviews
4. Decide: Kill workout-logger or pivot?
```

### Step 6: Update Database & Feed Learnings Back

After all actions, update:

**business-ideas.json:**
```json
{
  "id": "expense-tracker",
  "mvp_status": "deployed",
  "execution_status": "DOUBLE_DOWN",
  "current_mrr": 1247,
  "customers": 62,
  "cac_ltv_ratio": 15,
  "last_updated": "2026-03-08",
  "autonomous_actions_taken": [
    "2026-03-08: Increased ad budget to $50/day",
    "2026-03-07: Sent testimonial requests to 5 users"
  ]
}
```

**Feedback Loop to idea-miner:**

When status changes, update metadata for future idea generation:

**If DOUBLE_DOWN:**
- Add to `metadata.successful_topics`: topic tag from this idea
- Add to `metadata.replicate_patterns`: pain point category
- Increment `metadata.topic_success_count[topic]`
- Future idea-miner runs will prioritize similar topics

**If KILL (after user confirms):**
- Add to `metadata.failed_topics`: topic tag
- Add to `metadata.avoid_patterns`: pain point category  
- Increment `metadata.topic_failure_count[topic]`
- Future idea-miner runs will deprioritize similar topics
- If topic has 3+ failures, blacklist completely

**Learning Database Schema:**
```json
{
  "metadata": {
    "successful_topics": ["productivity", "saas-tools"],
    "failed_topics": ["marketplace", "social-network"],
    "replicate_patterns": ["ADHD productivity tools", "receipt scanning"],
    "avoid_patterns": ["two-sided marketplace", "user-generated content"],
    "topic_success_count": {"productivity": 3, "saas-tools": 2},
    "topic_failure_count": {"marketplace": 2, "social-network": 1}
  }
}
```

This creates a self-improving system that learns from execution success.

## Cronjob Setup

Schedule daily execution:

```python
from hermes_tools import schedule_cronjob

schedule_cronjob(
    name="execution-tracker-daily",
    schedule="0 9 * * *",  # 9am daily
    prompt="""
Run the execution-tracker skill with PARALLEL SUBAGENT metrics collection.

For each deployed MVP:
1a. Identify all active MVPs from config
1b. SPAWN PARALLEL SUBAGENTS if N>=2 (one per MVP) to collect metrics concurrently
    - Each subagent uses toolsets=['terminal', 'file']
    - Each returns JSON snapshot with revenue/traffic/engagement/health/ads
    - Main agent waits for all results, then merges
1c. Fallback to serial collection if subagents fail or N=1
2. Calculate derived metrics (CAC, LTV, growth rates)
3. Classify status (DOUBLE_DOWN, OPTIMIZE, PIVOT, KILL)
4. Take autonomous actions (increase ad spend, send emails, A/B tests)
5. Generate daily report
6. Send via Telegram

Performance: With N>=2 MVPs, metrics collection goes from 3N minutes → ~5 minutes.

Database: ~/workspace/playground/data/business-ideas.json
Config: /workspace/playground/data/execution-tracker-config.json
Metrics: /workspace/playground/data/mvp-metrics/{mvp-id}/

Action limits:
- Ad budget: Max 2x initial budget
- Email: Max 50 recipients/day per MVP
- A/B tests: Max 3 active variants
- Auto-kill: NEVER (always ask first)

Report via Telegram to home channel.
    """,
    deliver="telegram",
    repeat=None  # Run forever
)
```

## Safety Guardrails

**What it CAN do autonomously:**
- Increase ad spend (up to 2x initial budget)
- Send emails to users (testimonial requests, win-backs, interviews)
- Create A/B test variants
- Adjust pricing (within 20% range)
- Generate recommendations
- **Auto-pause ads on KILL signal** (stops money bleed immediately)

**What it CANNOT do (requires approval):**
- Kill an MVP (but keeps ads paused while waiting)
- Decrease ad spend to $0 (only suggest)
- Major feature changes
- Pivot positioning without testing first
- Spend > $500/month on any MVP

**Emergency stops:**
- If error rate > 10%, pause autonomous actions
- If MRR drops > 50% in 1 week, alert immediately
- If ad spend > 3x LTV, stop spending
- **Auto-pause ads when KILL signal detected** (7-day escalation timer)

**Kill Escalation:**
- KILL signals sent via Telegram with auto-pause confirmation
- User has 7 days to respond ('kill' or 'keep')
- If no response after 7 days, escalation cronjob auto-confirms kill
- Ads remain paused until explicit 'keep' command

## Manual Commands

User can intervene:

```bash
# Pause autonomous actions for an MVP
execution-tracker pause expense-tracker

# Override classification
execution-tracker set-status expense-tracker DOUBLE_DOWN

# Force action
execution-tracker increase-ad-budget expense-tracker 100

# Kill MVP (after KILL signal)
execution-tracker kill workout-logger

# Resume ads after false-positive KILL
execution-tracker resume-ads workout-logger

# Cancel pending escalation
execution-tracker cancel-escalation workout-logger
```

## Success Metrics

Track tracker performance:
- Actions taken vs manual interventions needed
- Time from signal to action
- Accuracy of classifications (did DOUBLE_DOWN MVPs succeed?)
- ROI of autonomous optimizations

## Pitfalls
- **Subagent JSON parsing failures** - Use regex extraction with fallback to serial collection. Don't block entire report if one subagent fails.
- Stripe API key in wrong mode (test vs live) returns test data as if it's real. Always verify key prefix: `sk_live_` for production.
- No MVPs with `mvp_status: "deployed"` in business-ideas.json means tracker runs and reports nothing. Check the DB before scheduling.
- KILL signal sent to Telegram but message is missed - **ads are auto-paused** so no money lost while waiting. If no response within 7 days, escalation cronjob auto-confirms kill.
- Analytics site ID misconfigured in the tracker config - traffic metrics always return 0. Cross-check against Plausible dashboard manually on first run.
- Autonomous email sending (win-backs, testimonials) can appear spammy if triggered daily. Check that cooldown logic prevents repeat sends to the same user.
- **Auto-pause may fail** if ad platform API is down or credentials expired - check Telegram alert for pause confirmation status.

## Verification
- Daily Telegram report arrives at 9am with data for all tracked MVPs
- With N>=2 MVPs, total runtime should be ~5-8 minutes (not 3N minutes - verify parallel speedup)
- All MVPs have at least one metrics file in `/workspace/playground/data/mvp-metrics/{mvp-id}/`
- Signal classifications match a manual spot-check of the underlying data
- Autonomous actions logged in `execution-tracker-config.json` under `autonomous_actions_taken`
- KILL candidate alerts pause - no auto-kill fires without explicit user confirmation

---

*The machine that runs your empire while you sleep. Build once, optimize forever.*
