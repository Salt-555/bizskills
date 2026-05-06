---
name: ad-campaign-strategy
description: "Full-funnel ad campaign strategy and copywriting. Takes an MVP or product, analyzes the audience, constructs the offer, designs the funnel, writes custom ad copy, and outputs an executable campaign blueprint. Use when asked to create an ad campaign, write ads, plan advertising, build a marketing funnel, or design a go-to-market ad strategy for any product."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [marketing, advertising, copywriting, funnel, campaign]
    category: business
    related_skills: [ads-manager, mvp-storefront, mvp-builder, execution-tracker]
---

# Ad Campaign Strategy

Full-funnel strategic planning and copywriting for advertising campaigns. The brain that tells ads-manager (the muscle) what to do.

**Key principle: Frameworks guide your thinking. They don't constrain your copy.** Every product has unique nuance — the Schwartz levels, Hormozi equation, and Hopkins principles are lenses for analysis, not templates to fill in. Read the product, understand the person who needs it, then write like a human who gets it.

## When This Skill Activates

- "Create an ad campaign for [product]"
- "Write ads for my MVP"
- "Plan the marketing funnel for [idea]"
- "How should we advertise this?"
- Post-storefront-deploy (pipeline integration)
- Any request to generate advertising copy or strategy

## Data Files

- Input: `~/.hermes/data/business-ideas.json` (when in pipeline mode)
- Output: `~/.hermes/data/ads/{idea-id}/campaign-blueprint.json`
- Wiki reference: `~/wiki/` (awareness frameworks, practitioner knowledge)

## MODE 1: Pipeline Integration (Post-Storefront)

Triggered after mvp-storefront deploys an MVP, or when invoked for an existing idea in business-ideas.json.

After blueprint is complete, if email_sequence is populated, hand off to email-campaigns skill to set up the nurture sequence files.

### Step 1 — Load the Idea

Read `~/.hermes/data/business-ideas.json` and find the target idea by ID.

Extract:
- `pain_point` — what problem does this solve
- `business_idea` — what is the product
- `topic` — the domain/category
- `estimated_ltv` — price point / expected value
- `landing_page_url` — where the funnel sends traffic
- Any existing copy, taglines, or positioning from the storefront deploy

### Step 1b — Verify Actual Product State (CRITICAL)

**The database can be stale. Before writing copy, verify what's actually live.**

1. **Check the landing page** — use `web_extract` on the `landing_page_url`. Read the current copy, pricing, positioning. The landing page is the source of truth for what buyers see, not the database entry.

2. **Check deploy metadata** — read `{local_repo_path}/deploy-metadata.json` for actual `price_cents`, `mvp_status`, and `last_deploy` date.

3. **Check the product itself** — if `local_repo_path` exists, read the product file (HTML, JS, etc.) to understand what's actually being delivered. Don't assume based on the idea description.

4. **Check for bundles** — the database may list separate ideas that are actually bundled into one product. Cross-reference `business_idea` field with the landing page and local repo.

**Why this matters:** During the Freelancer Toolkit campaign build, the database had two separate entries ($5 and $7) while the landing page already correctly positioned a $7 bundle. Writing copy based on the database would have produced wrong positioning.

After verification, write your confirmed understanding before proceeding: product name, actual price, what's included, current positioning.

### Step 2 — Audience Analysis

This is the most important step. Everything else flows from getting this right.

**Think through these questions (do NOT just fill in blanks):**

1. **Who has this problem?** Not "everyone." Get specific. What job do they do? What tools do they already use? What have they already tried? What frustrates them about existing solutions?

2. **Where are they on the awareness ladder?**
   - Do they even know this problem exists? (Unaware)
   - Do they feel the pain but not know solutions exist? (Problem Aware)
   - Do they know solutions exist but not your product? (Solution Aware)
   - Do they know your product exists but aren't convinced? (Product Aware)
   - Ready to buy, just need the deal? (Most Aware)

   **Most MVPs launch at cold traffic = Problem Aware or Solution Aware.** Default to Problem Aware unless the product is in an established category with known competitors.

3. **What sophistication stage is the market at?**
   - Is this a new category? (Stage 1: just state the benefit)
   - Are there competitors making similar claims? (Stage 2-3: need mechanism)
   - Is the market saturated with "solutions"? (Stage 4-5: need identity/angle)

4. **Where do they spend time online?** This determines channel selection, not convenience.

Write this analysis as clear prose, not a form. If you can't articulate who this person is and why they'd care, you're not ready to write copy yet.

### Step 3 — Offer Construction

Apply the Hormozi value equation to the product:

```
Value = (Dream Outcome × Perceived Likelihood of Achievement)
        ÷
        (Time Delay × Effort and Sacrifice)
```

**Work through each variable honestly:**

1. **Dream Outcome:** What does life look like after using this? Not features — the actual transformation. Be vivid. "You'll have a faster website" is weak. "You'll never lose a customer to a slow page again — every visitor gets the experience you designed, instantly" is strong.

2. **Perceived Likelihood:** Why should they believe this will work for THEM specifically?
   - What proof can we show? (Even early-stage: demo screenshots, the logic of the mechanism, creator credibility)
   - What guarantee removes risk? (Money-back, free trial, "if it doesn't do X in Y days, full refund")
   - What social proof exists or can be gathered? (Beta users, testimonials, "built by someone who had this problem")

3. **Time Delay:** How fast do they get results?
   - Can they see value in the first session? (Instant gratification)
   - What's the realistic timeline to their dream outcome?
   - Can we accelerate it? (Templates, presets, done-for-you elements)

4. **Effort and Sacrifice:** How much work do they have to do?
   - Is it truly plug-and-play or does it require setup?
   - Can we reduce effort further? (Better docs, video walkthrough, smart defaults)

**Now design the offer stack:**
- Core product (what they get)
- Bonuses (stack value — templates, extras, companion tools)
- Guarantee (risk reversal — stronger = better conversion)
- Urgency (if genuine — limited launch price, early-bird, etc.)
- Price framing (anchor against value, not cost)

Write this as a clear offer description, not a template.

### Step 4 — Funnel Design

Map the conversion path from first touch to purchase.

**For cold traffic (most common at launch):**

```
[Ad] → [Landing Page] → [Decision Point]
                           ├── Buy now (high intent)
                           ├── Free trial / lead magnet (medium intent)
                           └── Leave (retarget later)
```

Design each stage:

1. **First touchpoint (the ad):** What stops the scroll? What's the hook? What awareness level are we writing at?

2. **Landing page flow:** How does the page move the visitor from awareness stage to purchase?
   - Above fold: hook + promise (matches ad)
   - Below fold: problem agitation → mechanism → proof → offer → CTA
   - What objection handling is needed?

3. **Nurture path (if not buying immediately):**
   - What lead magnet or free trial makes sense?
   - What email sequence nurtures Problem Aware → Product Aware?
   - How many emails? What does each one do?

4. **Retargeting:** What do we show people who visited but didn't convert? (Different angle, social proof, urgency)

**Write this as a flow description, not a diagram.** Include what each stage is trying to accomplish psychologically.

### Step 5 — Write the Ad Copy

This is where frameworks guide but don't constrain. Write like a human who understands the product and the person who needs it.

**For each ad, write:**

1. **The hook** (first line that stops the scroll)
2. **The body** (problem → agitation → mechanism → proof → CTA)
3. **The CTA** (specific action, not vague "learn more")

**Generate multiple variants for testing:**

- **Variant A — Problem-focused:** Lead with the pain. Make them feel it before offering relief.
- **Variant B — Mechanism-focused:** Lead with HOW it works differently. For Solution Aware audiences.
- **Variant C — Outcome-focused:** Lead with the dream. Paint the after-state.
- **Variant D — Social proof:** Lead with someone else's result. Testimonial-driven.

**For each platform, adapt the format:**

**Google Ads (Responsive Search Ads):**
- 10 headlines (30 chars max each)
- 4 descriptions (90 chars max each)
- 15 keywords (mix of phrase match and exact match, high-intent terms)

**Meta Ads (Facebook/Instagram):**
- Primary text (125 chars max — the hook)
- Headline (40 chars max)
- Description (30 chars max)
- 8-10 interest targeting categories

**Email Sequence (if funnel includes nurture):**
- Email 1: Problem agitation (Day 0)
- Email 2: Mechanism education (Day 1-2)
- Email 3: Social proof / case study (Day 3-4)
- Email 4: Offer + urgency (Day 5-7)

**Each piece of copy should be tagged with:**
- `awareness_target`: which Schwartz level it's written for
- `angle`: which approach (problem, mechanism, outcome, proof)
- `sophistication_assumed`: what market stage this assumes

This metadata matters for optimization later — when ads-manager sees performance data, it can correlate which strategic assumptions were correct.

### Step 6 — Creative Brief

What visual/production assets are needed:

1. **Ad creative direction:**
   - What imagery or video would support the copy?
   - Product screenshots? Demo video? Face-to-camera?
   - Color/mood/aesthetic guidance

2. **Proof to gather:**
   - What testimonials, screenshots, data points would strengthen the ads?
   - What can be collected from beta users or early customers?

3. **Testing matrix:**
   - What to test first (highest impact variables)
   - What to test second (after first round has data)
   - Minimum viable test: how many impressions/clicks before drawing conclusions

### Step 7 — Output the Campaign Blueprint

Write `~/.hermes/data/ads/{idea-id}/campaign-blueprint.json` with this structure:

```json
{
  "idea_id": "...",
  "product_name": "...",
  "landing_page_url": "...",
  "created_at": "ISO timestamp",
  
  "audience": {
    "description": "prose description of who this is for",
    "awareness_level": "problem_aware|solution_aware|product_aware",
    "sophistication_stage": 1-5,
    "demographics": {
      "age_range": [25, 54],
      "locations": ["US", "CA", "GB", "AU"],
      "interests": ["list", "of", "targeting", "interests"]
    },
    "channels": ["google_search", "meta", "email"],
    "channel_rationale": "why these channels"
  },
  
  "offer": {
    "dream_outcome": "...",
    "likelihood_factors": ["proof point 1", "proof point 2"],
    "time_to_value": "...",
    "effort_required": "...",
    "core_product": "...",
    "bonuses": ["bonus 1", "bonus 2"],
    "guarantee": "...",
    "urgency": "..." or null,
    "price": ...,
    "price_framing": "..."
  },
  
  "funnel": {
    "type": "cold_to_purchase|cold_to_lead|free_trial",
    "stages": [
      {
        "stage": "ad",
        "purpose": "...",
        "awareness_target": "..."
      },
      {
        "stage": "landing_page",
        "purpose": "...",
        "sections": ["hook", "problem", "mechanism", "proof", "offer", "cta"]
      },
      {
        "stage": "nurture",
        "type": "email_sequence|retargeting|both",
        "emails": [
          {
            "day": 0,
            "purpose": "problem agitation",
            "awareness_progression": "problem_aware → solution_aware"
          }
        ]
      }
    ]
  },
  
  "ads": {
    "google": {
      "campaign_type": "search",
      "variants": [
        {
          "variant_name": "A_problem",
          "awareness_target": "problem_aware",
          "angle": "problem",
          "headlines": ["h1", "h2", ...],
          "descriptions": ["d1", "d2", ...],
          "keywords": ["kw1", "kw2", ...]
        }
      ]
    },
    "meta": {
      "campaign_type": "traffic|leads|conversions",
      "variants": [
        {
          "variant_name": "A_problem",
          "awareness_target": "problem_aware",
          "angle": "problem",
          "primary_text": "...",
          "headline": "...",
          "description": "...",
          "interests": ["interest1", ...]
        }
      ]
    }
  },
  
  "email_sequence": [
    {
      "day": 0,
      "subject": "...",
      "body": "...",
      "purpose": "problem agitation",
      "awareness_progression": "problem_aware → solution_aware"
    }
  ],
  
  "creative_brief": {
    "visual_direction": "...",
    "assets_needed": ["screenshot", "demo_video", "testimonial"],
    "proof_to_gather": ["proof item 1", "proof item 2"]
  },
  
  "testing_plan": {
    "phase_1": {
      "test": "which variant wins",
      "variables": ["variant A vs B"],
      "min_sample": 100,
      "success_metric": "ctr > 2% or conversions > 0"
    },
    "phase_2": {
      "test": "what to test after winner found",
      "variables": ["..."]
    }
  },
  
  "budget": {
    "recommended_daily": 20,
    "channel_split": {"google": 10, "meta": 10},
    "monthly_cap": 600,
    "scaling_trigger": "CPA < LTV/5",
    "kill_trigger": "$60 spent, 0 conversions, CTR < 0.5%"
  }
}
```

### Step 8 — Handoff to Ads Manager and Email (Optional)

If ads credentials exist and the user wants to launch immediately, invoke ads-manager's Workflow 1, passing the blueprint as context. Ads-manager will use the blueprint's copy variants, keywords, and targeting rather than generating its own.

If email_sequence is populated in the blueprint, invoke email-campaigns Workflow 1 to set up the nurture sequence. The sequence files will be ready for the daily send processor to pick up when leads start coming in.

If credentials don't exist, inform the user that the blueprint is ready and can be executed manually or when credentials are configured.

---

## MODE 2: Standalone (No Pipeline)

When invoked for a product not in business-ideas.json:

1. Ask the user to describe their product (or extract from a URL they provide)
2. Same 7-step workflow, but skip Step 1 (no business-ideas.json to read)
3. Output blueprint to `~/.hermes/data/ads/standalone/{slug}/campaign-blueprint.json`
4. No ads-manager handoff (standalone products don't have pipeline integration)

---

## MODE 3: Copy Refresh

When existing campaigns are running and copy needs refreshing:

1. Load the existing campaign-blueprint.json
2. Load recent performance data from ads-manager metrics
3. Analyze which variants are winning and WHY (which awareness level, which angle)
4. Generate fresh variants that lean into what's working
5. Generate variants that test a new angle (in case the market shifted)
6. Update the blueprint with new variants (preserve old ones with performance data)

---

## CRITICAL: How to Write Good Copy

**Don't write ad copy. Write to one person.**

Before writing a single word, picture ONE specific human who needs this product. What are they doing right now? What just happened that made this problem painful? What would make them stop scrolling?

**Then write to that person. Like you're explaining something to a friend.**

Frameworks help you structure the argument:
- Schwartz tells you WHERE to start (awareness level)
- Hormozi tells you WHAT to emphasize (the value equation levers)
- Hopkins tells you HOW to prove it (specific claims, testing)
- Ogilvy tells you to RESEARCH first (know the product cold)

But the copy itself should sound like a human wrote it, not a formula.

**Red flags in copy:**
- Sounds like every other ad ("Unlock your potential!", "Game-changing!", "Revolutionary!")
- Makes claims without proof or mechanism
- Talks about the product instead of the person's problem
- Generic CTA ("Learn more" / "Click here")
- Written at the wrong awareness level for the channel

**Green flags:**
- Specific, concrete language ("3 clicks" not "easy to use")
- Names the pain precisely ("You're spending 4 hours on something that should take 20 minutes")
- Explains the mechanism ("Here's why this actually works...")
- Sounds like it was written by someone who's used the product
- CTA is specific ("Start your free trial" / "Get the template" / "See it in action")

---

## Pitfalls

- **Don't generate copy before understanding the audience.** The audience analysis in Step 2 is not optional busywork — it's the foundation. Skipping it produces generic copy.
- **Don't default to "Solution Aware" for cold traffic.** Most cold traffic is Problem Aware or at best Solution Aware. Writing Product Aware copy to cold traffic is the #1 campaign killer.
- **Don't write all variants from the same angle.** The point of testing is to discover which ANGLE resonates, not which phrasing of the same angle.
- **Don't ignore market sophistication.** If there are 50 competitors all saying "fast, easy, cheap," you need a mechanism or identity angle, not a bigger claim.
- **Don't skip the email sequence for cold funnels.** Cold traffic rarely converts on first touch. Email nurture is where Problem Aware becomes Product Aware.
- **Don't create artificial urgency.** Fake deadlines erode trust. If you use urgency, make it real (launch pricing, limited beta, seasonal).
- **Don't forget the blueprint metadata.** The `awareness_target` and `angle` tags on each ad variant are critical for optimization. Without them, performance data is just numbers with no strategic context.
- **Budget recommendations should be honest.** If the market is competitive and CPCs are $5+, say so. Don't recommend $10/day for a market that needs $50/day to get signal.

---

## Verification

After generating a campaign blueprint, verify:
- [ ] Audience analysis is specific (not "anyone who wants to save time")
- [ ] Awareness level is stated and copy matches it
- [ ] Offer includes guarantee and at least one bonus
- [ ] At least 3 ad variants with different angles exist per platform
- [ ] Each variant is tagged with awareness_target and angle
- [ ] Email sequence exists if funnel is cold-to-lead
- [ ] Testing plan specifies what to test and minimum sample size
- [ ] Budget recommendation is realistic for the market
- [ ] Blueprint JSON is valid and complete
