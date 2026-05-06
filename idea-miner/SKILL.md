---
name: idea-miner
description: "Mine business ideas from real pain points online. Filters hard for buildability, willingness to pay, and competitive gap. Outputs vetted ideas to business-ideas.json with pricing model and feasibility assessment. Trash in = trash out -- this skill is the quality gate."
---

# Idea Miner

Find real pain points. Verify someone would pay to fix them. Output build-ready ideas.

## Idea Database
- **Path:** `~/.hermes/data/business-ideas.json` (was `~/workspace/playground/data/business-ideas.json`)
- **Schema per idea:**
```json
{
  "id": "slug-name",
  "topic": "category tag",
  "pain_point": "specific frustration people express",
  "who_pays": "exact persona who has this pain AND budget",
  "business_idea": "one-sentence solution",
  "competitive_gap": "why existing solutions don't cover this",
  "revenue_model": "one_time | subscription",
  "price_point": 5,
  "price_rationale": "why this price works for this buyer",
  "why_buildable": "why we can ship this on CF Workers + KV",
  "execution_difficulty": "easy | medium",
  "build_ready": false,
  "validation_status": "raw",
  "created": "2026-03-29"
}
```

## Quality Gate: The 5 Filters

Every idea MUST pass all 5 or it gets discarded. No exceptions.

### Filter 1: Specific Pain (not vague frustration)
BAD: "People find productivity tools overwhelming"
GOOD: "Freelancers on Upwork lose 30min/day copying time entries from Toggl to invoices"

The pain must be specific enough to write a Google ad for. If you can't target the ad, you can't find the buyer.

### Filter 2: Identifiable Buyer (not "people")
BAD: "Solo founders"
GOOD: "Shopify store owners doing $10k-50k/mo who manage their own email marketing"

The buyer must be:
- Findable online (subreddit, forum, community, keyword)
- Already spending money on tools in this space
- Able to make a purchase decision without committee approval

### Filter 3: Willingness to Pay (not just complaining)
Evidence of willingness to pay:
- People already paying for inferior alternatives
- People building janky workarounds (spreadsheets, manual processes)
- People asking "is there a tool that does X?"
- People saying "I'd pay for X"

NOT evidence: general complaints, philosophical discussions, wishlists

### Filter 4: Competitive Gap (not "simpler version of X")
BAD: "Like Pingdom but cheaper" -- Pingdom has a free tier
GOOD: "Pingdom doesn't monitor Stripe webhooks specifically -- you need custom logic for that"

Check: does a free tool already solve this? If yes, discard.
Check: is the gap real or just "I haven't looked hard enough"?

### Filter 5: Buildable on Our Stack (Downloadable HTML Tools)
Must be shippable as a self-contained HTML file (or small zip with HTML + assets):
- Zero dependencies — opens in any browser, works on any OS
- All processing client-side JavaScript (no server, no API keys for customer)
- No persistent connections, no user accounts, no ongoing maintenance
- Customer owns it forever — we sell the zip, they run it themselves

If it needs server-side processing, real-time data, or ongoing maintenance — either simplify to client-side or discard.

**Format priority:** Self-contained HTML > HTML + JSON data file > Node.js script (requires install) > Python script (requires install). Prefer the most portable option.

## Pricing Framework

One-time purchases, $3-10 sweet spot.
**Key marketing angle: "No subscription. Own it forever."**

| Price | Stripe Fee | Net | Use When |
|-------|-----------|-----|----------|
| $3 | $0.39 | $2.61 | Simple utility, impulse buy, high volume target |
| $5 | $0.45 | $4.55 | Standard tool, clear value, covers hosting with 1 sale |
| $7 | $0.50 | $6.50 | Tool with ongoing value, saves real time |
| $10 | $0.59 | $9.41 | Professional tool, B2B adjacent |

Pricing rule: the tool must save the buyer MORE than the price in time or money within the first use. If you can't articulate that, the price is wrong or the idea is wrong.

Below $3: Stripe's $0.30 fixed fee eats too much margin.
Above $10: Buyer expects more polish than an MVP delivers.

## Niche Market Scoring Matrix

When comparing multiple potential niches (e.g., trades vs HOA vs youth sports), use this 1-5 scoring framework for unbiased comparison:

| Criterion | What It Measures |
|-----------|-----------------|
| Pain intensity | 5 = people spending hours on workarounds, 1 = mild annoyance |
| Buyer accessibility | 5 = exact subreddit/community exists, 1 = hard to find |
| Willingness to pay | 5 = already paying for inferior alternatives, 1 = only complaining |
| Competitive gap | 5 = no one-time alternatives exist, 1 = free tools everywhere |

Only pursue niches scoring 14+/20. Document the scoring in chat before committing to build.

**Key signals of a ripe niche:**
- Subscription-fatigued buyers (paying $30-200/mo for bloated platforms)
- Non-technical volunteer operators (inherited the role, didn't choose it)
- Simple math problems being sold as platforms (budgets, tracking, splitting costs)
- No one selling one-time-download alternatives (entire market is subscription-only)
- Low incumbent satisfaction (sub-3-star reviews, vocal complaints)

## Workflow

### Step 1: Choose Mining Target

- IF user provided topic -> use it
- IF user said "trending" -> search current trending topics
- Check existing database for covered topics, execution_status feedback
- Deprioritize topics with 2+ KILL signals in execution history

### Step 2: Mine Pain Points (Multi-Source)

Search for SPECIFIC complaints, not general discussion:

**Search queries that find buyers:**
- `"I wish there was" [topic] site:reddit.com`
- `"I'd pay for" [topic] site:news.ycombinator.com`
- `"anyone know a tool" [topic] site:reddit.com`
- `[topic] "waste of time" OR "so frustrating" OR "manual process"`
- `[topic] "switched from" OR "looking for alternative"`

**arXiv browsing (academic/research topics):**
- Browse recent papers in these categories: cs.AI, cs.LG, cs.SE, cs.HC, stat.ML
- Look for explicit gaps:
  - Limitations sections ("our approach doesn't handle X")
  - Future work statements ("an interesting direction would be...")
  - Manual processes described that could be automated
  - Tools mentioned as "not yet available" or "would require"
- Extract from abstract + conclusion primarily; full paper only if needed
- **How to find papers:** Use `web_search` with queries like `site:arxiv.org cs.AI transformer` or `arxiv.org cs.SE automated testing` to find recent paper URLs, then pass the arxiv paper (HTML or PDF) URL directly to `web_extract` for content
- **Never use curl or terminal for web content** - `web_search` finds URLs, `web_extract` retrieves and converts them (including PDF-to-markdown). This handles anti-bot bypass and format conversion automatically

**General web content (blog posts, Reddit, HN, etc.):**
- Use `web_search` to find discussion URLs on the topic
- Pass those URLs directly to `web_extract` to get content
- Never use curl or terminal for web content - use the proper web tools

**Search queries that find garbage (avoid):**
- `[topic] trends 2026` -- produces thought-leader fluff
- `best [topic] tools` -- produces affiliate listicles
- `[topic] startup ideas` -- produces recycled ideas, not pain points

**Sources by quality:**
1. HN comments on Show HN posts (people saying what's missing)
2. Reddit r/SaaS, r/Entrepreneur, r/smallbusiness (people asking for tools)
3. IndieHackers discussions (people sharing what they'd pay for)
4. Niche subreddits for the specific domain (where the actual buyers hang out)
5. arXiv recent papers in relevant categories (researchers stating explicit gaps/limitations)

Extract from 2-3 sources. Max 5 content fetches total. Stop if no new insights after 3 fetches.

**User preference:** Do primary research, not pre-compiled "50 ideas" lists. Find real discussions, real complaints, real tool comparisons. If a blog post says "people complain about X" — go find the actual complaints, don't just cite the blog.

**arXiv caveat:** Researchers state problems, but aren't always paying customers. Extra scrutiny on Filters 2 & 3. A research gap ≠ market opportunity.

**Search engine behavior and fallbacks:**
- web_search often returns zero results for exact-phrase queries like `"I wish there was"` or `"frustrated with"`. When this happens, DO NOT give up. Pivot strategy:
  1. Search for the TOPIC directly (e.g., "freelance tax tracking", "contractor invoicing") instead of complaint phrases
  2. Use web_extract on known forum/discussion URLs to find actual complaints there
  3. Extract blog posts that list industry pain points — these are valid sources
- web_search may return SEO blog content for opinion-based queries. That's still useful — blog posts list problems people complain about; forum discussions reveal willingness to pay
- **NEVER use curl** — web_search finds URLs, web_extract retrieves them

**App review sites as signal source:** When mining niches with existing apps (spiritual, fitness, productivity), check JustUseApp.com and Trustpilot for billing complaints, pricing tiers, and user sentiment. These aggregate real reviews that Reddit searches might miss. See `references/witchy-niche-research.md` for worked example.

**Validated niche research files:** See `references/fishing-charter-niche.md` for pre-validated fishing charter/tour operator opportunity with full competitor pricing data.

**Alternative signal: existing tool search (FALLBACK when complaint searches fail)**
When primary complaint searches return nothing, search for EXISTING TOOLS solving the problem. If you find companies actively selling a solution, the market is validated even without direct complaint quotes. Search patterns:
- `[problem] tool` or `[problem] software` or `[problem] checker`
- `[niche] app review` — reveals pricing, hidden costs, user frustrations
- `[app name] vs [app name]` — comparison threads surface pain points and price sensitivity
- Look at pricing pages — are people paying? How much?
- Check if tools are growing (recent blog posts, updated pricing, new features)
- If 3+ tools exist with paying customers = strong signal. If 1-2 = possible gap.
- This inverts the search: instead of "who's complaining?", ask "who's already profiting from this pain?"

### Step 3: For Each Pain Point, Apply the 5 Filters

Run each pain point through filters 1-5 above. Be ruthless.

For each that passes, also determine:
- **Who exactly pays?** Name the persona, their budget, where they hang out online.
- **What exists already?** Search `[pain point] tool` and check top 3 results. Is there a gap?
- **What would they pay?** Match to pricing framework. Can you save them more than the price?
- **Can we build it?** Map to CF Workers constraints. What's the core loop? (see mvp-builder)

### Step 4: Score and Rank

Score each surviving idea 1-5 on:
- **Pain intensity** (5 = people spending hours on workarounds, 1 = mild annoyance)
- **Buyer accessibility** (5 = exact subreddit/keyword exists, 1 = hard to find)
- **Build simplicity** (5 = one API call + UI, 1 = multiple integrations + auth)
- **Revenue clarity** (5 = obvious value > price, 1 = hard to justify charging)

Total score = sum. Only save ideas scoring 12+ out of 20.

### Step 5: Save to Database

```python
idea = {
    "id": slugified_name,
    "topic": topic_tag,
    "pain_point": specific_pain,
    "who_pays": exact_persona,
    "business_idea": one_sentence_solution,
    "competitive_gap": why_existing_dont_cover,
    "revenue_model": "one_time",
    "price_point": calculated_price,
    "price_rationale": why_price_works,
    "why_buildable": stack_feasibility,
    "execution_difficulty": "easy" or "medium",
    "build_ready": False,  # NOT True. Raw ideas need review.
    "validation_status": "raw",
    "score": total_score,
    "score_breakdown": {"pain": X, "buyer": X, "build": X, "revenue": X},
    "created": today,
    "sources": [urls_where_pain_was_found]
}
```

**build_ready is FALSE by default.** Ideas go to raw -> reviewed -> build_ready. The user or a validation step promotes them.

**Deduplication:** Compare pain_point against existing ideas. Skip if substantially similar.

### Step 6: Output Summary

```
Mined [N] pain points, [M] passed filters, [K] saved to database.

Top candidate:
  [idea name] — $[price] one-time
  Pain: [specific pain]
  Buyer: [who pays]
  Gap: [competitive gap]
  Score: [X]/20

Next steps:
  Review ideas: "show raw ideas"
  Promote to build-ready: "approve [id]"
  Build it: "build mvp [id]" (after promoting)
  Mine more: "find [topic] ideas"
```

## Demographic-First Mining (Alternative to Pain-Point-First)

When you don't have a specific topic, start with WHO has money and is underserved, then find their pain. This inverts the normal flow.

**When to use:** User says "find a new vein" or "what's underserved" — no specific topic, wants to discover opportunity spaces.

**Workflow:**

### Step 1: Demographic Research
Search for spending data by demographic:
- `highest spending demographics online shopping [year] statistics`
- `which demographic spends most money online by age gender income`
- `online shopping demographics [year] trends`

Extract: who spends the most, who's growing, who's underserved by current marketing.

**Key data points to find:**
- Total spend by generation/segment
- Frequency of purchase
- Average order value
- Growth trajectory
- How much attention brands pay them (inverse = opportunity)

### Step 2: Sub-Segment Drill-Down
Within the top demographic, find specific high-value sub-segments:
- `Gen X / [demographic] subsegments spending behavior`
- Psychographic profiles (caretakers, professionals, hobbyists)
- Impulse buying rates by segment
- Willingness to pay indicators

**Filter for:** segments with high spend + low brand attention + reachable online.

### Step 3: Pain Point Extraction
Now search for their actual frustrations:
- `"[demographic]" biggest frustrations [topic area]`
- `site:reddit.com "[segment]" overwhelmed [pain area]`
- `"[segment]" [problem] "wish there was" OR "no good solution"`

**Pivot strategy when searches return empty:**
- Search for EXISTING TOOLS solving the problem instead of complaints
- Search for news articles covering the demographic's challenges
- Search academic/government reports (BLS, NIH, Pew) for quantified struggles
- If 3+ tools exist with paying customers = market validated

### Step 4: Gap Analysis
- Map existing solutions by category (logistics vs. financial vs. emotional)
- Identify the INTERSECTION where no tool exists (e.g., "care coordination + financial impact")
- The gap is usually between two adjacent categories that existing tools treat separately

### Step 5: Concept Development
For the strongest gap:
- Define the "moment of clarity" — what number/result would make someone say "oh shit"
- Map to the 5 Filters (same quality gate)
- Score using Niche Market Scoring Matrix

**Demographic-first vs. Pain-point-first:**
| Aspect | Demographic-First | Pain-Point-First |
|--------|------------------|-----------------|
| Start with | Who has money | What's broken |
| Best for | Discovering new niches | Targeting known problems |
| Risk | Demographic too broad | May miss underserved segments |
| Output | Opportunity space → specific idea | Specific pain → validated idea |

Both paths converge at Step 3 (pain point extraction) and share the same quality gate from there.

### Session Example (Apr 2026): Gen X Sandwich Generation
1. Demographic research revealed Gen X as highest spenders ($15.2T/yr), explicitly "overlooked" by brands
2. Sub-segment: "Caretaker Consumer" — managing kids + aging parents simultaneously ($1,384/mo on adult children, $40-50K median retirement savings)
3. Pain extraction: financial strain, time poverty, sibling coordination chaos, guilt about boundaries
4. Gap analysis: care coordination apps (CircleCare, CaringBridge) handle logistics but ignore finances; retirement calculators ignore the "supporting two generations" factor
5. Concept: "Sandwich Calculator" — shows true cost of being sandwiched on retirement runway, with boundary plan
- **Key sources:** NIQ "The X Factor" report, Advisor Perspectives on boomerang parenting, Capital One Shopping impulse buying stats
- **Web search note:** Many exact-phrase queries returned empty. Broad topic searches + news article extraction worked better.

## SaaS Unbundled Pattern (High-Leverage Mining Strategy)

Take expensive monthly SaaS tools and sell the core function as a one-time-purchase downloadable tool.

**Why this works:**
- SaaS charges monthly for stateless operations (input → process → output)
- Most users use the tool occasionally, not daily — subscription is overpriced for them
- "No subscription. Own it forever." is a proven marketing angle (Gumroad, Etsy sellers use this)
- Customer runs it on their machine — zero infrastructure/maintenance for us
- HN consensus: "simple, expensive tools doing one job poorly get replaced first"

**What to look for:**
1. SaaS tools where 80% of value is one feature (the rest is bloat)
2. Tools that do text-in/text-out processing (report generation, validation, scoring)
3. Monthly price > $20 for something you use < 5 times/month
4. The core function can run client-side in a browser (no server needed)

**Best categories:**
- Compliance/checker tools (Etsy trademark checker, SEO audit)
- Generators (invoice, contract, proposal, scope of work)
- Calculators (rate checker, project profitability, tax estimator)
- Scoring/matching (resume ATS check, content SEO score, client red flag score)

**Product format:** Self-contained HTML file in a zip. Browser-based, zero dependencies, works on any OS. Customer downloads, opens in browser, uses forever. Ship via our storefront (Stripe + Resend email + download endpoint).

**Existing validation:** Invoice generators selling on Gumroad ($5-15) and Etsy ("No Subscription" tagline). OpenClaw freelancer bundle: 10 tools, one-time purchase. WheelieNames: 1,000+ customers for one-time skill packs.

## Bundling Ideas Into Existing Products

Not every idea needs its own storefront. If a new idea shares the same buyer persona and adjacent pain point as an existing product, **combine them** into a single stronger product:

- Same audience + complementary tools = natural bundle (e.g., invoice follow-up + project pricing)
- Increases perceived value without increasing deploy/maintenance surface
- One Stripe product, one landing page, one download — simpler funnel
- Opportunity to raise price (2 tools at $7 > 1 tool at $5)

**When to bundle vs. separate:**
- Bundle: same buyer, adjacent pain, both fit in one HTML file
- Separate: different buyers, different marketing angles, or product is too large

To bundle: read existing worker from `~/.hermes/mvps/{name}/src/worker.js`, add new feature to the HTML product, update landing page copy, bump price, redeploy.

## Status Flow

```
raw -> reviewed -> build_ready -> storefront_deployed -> product_deployed -> live
                \\-> rejected
```

Only `raw -> reviewed` and `reviewed -> build_ready` happen in this skill.
Everything after `build_ready` is mvp-storefront and mvp-builder territory.

**Order matters: storefront FIRST, then product.** The storefront defines the integration contract (KV, email, payment, download). The product plugs into it — not the other way around.

## Subscription Fatigue Mining (High-Leverage Variant of SaaS Unbundled)

When mining a niche community, look for **subscription fatigue signals** specifically. This pattern appeared in witchy/spiritual apps and is generalizable.

**The pattern:** Niche communities often have 2-4 competing apps charging subscriptions for reference data that doesn't change (correspondences, lookup tables, calculators). The buyers are already spending money but resent the recurring cost.

**How to find these markets:**
1. Search `[niche] app review` or `[niche] subscription complaint` — Reddit threads comparing apps reveal hidden costs and frustrations
2. Search `[niche] app vs app` — comparison threads surface pricing details and user pain points
3. Check app store review sites (justuseapp.com, appshunter.io) for billing complaints
4. Search Etsy/Gumroad for `[niche] digital product` — if static PDFs sell well, an interactive one-time tool fills the gap
5. Search `[niche] free alternative` — direct signal that people want to escape subscriptions

**Example from witchy market run:**
- Moonly: $30 lifetime + $20 hidden upsell for birth chart → Reddit complaints
- MoonX: $99 lifetime or $30/year → comparison thread reveals price sensitivity
- Spells8: $29/mo for content that's largely static reference data
- Etsy: printable correspondence charts selling for $3-10 (static PDFs)
- Gap: No interactive, one-time-purchase correspondence lookup tool exists

**Key insight:** The pain isn't "I can't find this information" — it's "I can find it but it's scattered across 50 blog posts and the only interactive tools charge me monthly for data that never changes." That's a stronger pain than a missing feature.

**Bundling opportunity:** When multiple tools in a niche share the same buyer and underlying data, bundle them into one product (e.g., correspondence lookup + ritual planner in one HTML file).

## When to Stop

- Evaluated 30 pain points/opportunities (not 30 saved -- expect 8-15 to pass filters)
- 5 content fetches with no new qualifying ideas
- Score threshold not met for 7 consecutive evaluation attempts (topic exhausted)

## Learning Loop

If business-ideas.json contains ideas with execution feedback:
- Topics with DOUBLE_DOWN signals: mine deeper, look for adjacent problems
- Topics with KILL signals (2+): deprioritize or skip
- Price points that converted: use as baseline for similar ideas
- Competitive gaps that turned out to be wrong: update rejection patterns

**Pitfalls**
- Mining broad topics produces broad (useless) ideas. Narrow the search.
- Reddit complaints != market demand. Always check Filter 3 (willingness to pay).
- "Simpler version of X" is almost never a real gap. Free tiers killed that play.
- Setting build_ready: true on raw ideas sends garbage downstream. Don't do it.
- Scoring too generously to hit quota. Better to save 2 good ideas than 10 weak ones.
- Ignoring execution history. If SaaS tools keep getting KILL signals, stop mining SaaS tools.
- **Gumroad blocks web_extract** — returns Internal Server Error on product pages. Use search snippets from Gumroad category listings instead, or pivot to Etsy/app review sites for pricing validation.
- **WRONG TOOL FOR JOB**: This is a methodology skill, not an implementation skill. Do NOT wrap the workflow in execute_code/Python code. Use web_search, web_extract, read_file, write_file directly. Methodology skills = follow process with available tools. Implementation skills (btc-wallet, cloudflare-api) = write code to execute functionality.
- **Ad-hoc builds leave orphaned products**: Building outside these skills (or skipping Step 6) means the product won't exist in business-ideas.json, making it invisible to empire-ledger, execution-tracker, and future recall. If a deployed product is missing from the database: search session history → check Cloudflare Workers manually → retroactively add entry with mvp_status metadata.
- **NEVER use curl for web content**: web_search finds URLs, web_extract retrieves them (handles rendering, anti-bot bypass, format conversion including PDF-to-markdown). Using terminal/curl bypasses all of this and produces brittle, broken results. Always use the proper web tools.
- **Web search reality**: Exact-phrase searches ("I wish there was", "I'd pay for") on Reddit/HN consistently return empty via web_search. PIVOT instead: search broad topics (e.g., "freelance invoice late payments"), then web_extract actual discussion pages. Also look for real product signals: Gumroad/Etsy listings for competing tools, competitor pricing pages, Show HN launches — these validate market demand without needing explicit complaint quotes.