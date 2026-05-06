---
name: trend-synthesizer
description: "Synthesize business ideas from research papers, industry reports, benchmark studies, and cross-domain comparisons. Uses 5 synthesis modes (scale-down, benchmark gap, domain porting, workflow fragments, quantified friction) to find subtextual $3-10 product opportunities. Writes to business-ideas.json alongside idea-miner."
---

# Trend Synthesizer

Absorb widely from research, benchmarks, surveys, and industry data. Synthesize **specific** product opportunities for solo/individual buyers. No explicit "I'm complaining" signal required — you're looking for subtextual pain.

Shared database with `idea-miner`: `~/.hermes/data/business-ideas.json`

## Schema
Same as idea-miner. All fields identical.

## Quality Gate: The 5 Filters
Same 5 filters as idea-miner. Every idea MUST pass all 5.
- **Filter 3 (Willingness to Pay)** is different in synthesis mode: you infer it from quantified friction. If a study shows "X hours wasted per Y" — convert that to annual cost. If the cost > $7, there's willingness to pay.

## Pricing Framework
Same as idea-miner: one-time $3-10.

## Synthesis Method

### Step 1: Define Your Mining Topics

**IMPORTANT:** Before absorbing, pick 2-3 distinct domains (e.g., "finance + education + healthcare", "developer tools + legal + real estate"). This ensures cross-domain porting opportunities and prevents clustering all ideas in one field.

**Pre-Run Domain Audit (CRITICAL):** Read `business-ideas.json` first to identify GAP DOMAINS. Count existing ideas by domain—avoid domains with >3 entries unless you have a novel angle. Target UNDERCOVERED or UNCOVERED domains for highest leverage. Example: if database has 13 developer-tools ideas but 0 legal-tech, prioritize legal.

### Step 2: Wide Absorption

Pull from these sources. Use `web_search` to find URLs, `web_extract` to read content.

**Primary sources:**
1. arXiv papers (cs.AI, cs.LG, cs.SE, cs.HC, stat.ML)
2. Industry surveys (Stack Overflow Developer Survey, JetBrains Dev Ecosystem, State of AI)
3. Benchmark results and comparative studies
4. Conference proceedings and trend analyses
5. Reddit/HN discussion threads on specific topics
6. Industry reports (Gartner, Forrester summaries, white papers)

**Search patterns:**
- `site:arxiv.org [category] [topic] OR benchmark` — find papers
- `[domain] survey OR state of OR challenges 2025 OR 2026` — industry surveys
- `[domain] pain points OR frustration OR "waste time" OR "tedious"` — practitioner complaints
- `[domain] benchmark OR comparative study` — benchmark papers reveal unsolved problems
- `site:reddit.com [domain] OR [industry] tool OR spreadsheet` — find real complaints
- `site:news.ycombinator.com [topic]` — developer pain points (more accessible than Reddit)

**Content extraction:**
- Use `web_search` to find URLs
- Pass URLs directly to `web_extract` — handles PDFs, HTML, everything
- Abstract + conclusion for scan; full paper when promising
- Max 5 content fetches per run
- **Always extract quantified data:** Look for hours wasted, dollar costs, error rates, adoption percentages, survey results

### Step 2: Apply 5 Synthesis Modes

Don't look for complaints. Look for patterns across multiple sources:

#### Mode A: Scale Down Enterprise Problems
Papers describe teams/departments. Ask: "**What does this look like for ONE person?**"
- "Teams spend 2.5 hours/week on code review" -> pre-submission cleanup for solo devs
- "Enterprise CI/CD wastes 40% compute on redundant tests" -> test-optimizer for side projects
- Teams with 2-hour review cycles -> solo dev staring at their own PR with no CI

#### Mode B: Benchmark Gap Detection
If researchers built a benchmark to measure X, it means **no widely accepted tool solves X**.
- Benchmarks ARE the market validation. The benchmark exists because no product exists.
- "We benchmarked code quality" -> build the quality-check tool
- "We benchmarked API flakiness across 36 endpoints" -> build the flakiness-detector
- **Key question**: "They built the measuring stick — who built the SOLUTION?"

#### Mode C: Cross-Domain Porting
Techniques from Domain A haven't been applied to Domain B. **This is the HIGHEST-LEVERAGE pattern.**
- CI linting for code -> what about for configs, data schemas, documentation?
- Spellcheck for prose -> what about for SQL queries, regex patterns, API payloads?
- Test flakiness detection for unit tests -> what about end-to-end API tests?
- **Key question**: "Has this been solved in Domain A but NOT in Domain B?"

#### Mode D: Manual Workflow Fragment
Papers describe multi-step processes. Extract the ONE tedious/error-prone step and productize it.
- "Researchers manually annotated 3000 test cases" -> automate the annotation
- "Developers manually check 47 compliance items" -> compliance checker
- **Key question**: "What's the most tedious step in this workflow?"

#### Mode E: Quantified Friction as Market Validation
When studies quantify waste (hours, error rates, dollar losses) — the numbers ARE market-size signals.
- "24.2% of AI-introduced bugs survive permanently" -> 130 hours/year of wasted debugging
- "60%+ of code review is formatting/style" -> automated pre-review formatter
- **Key question**: "If this wastes $X/year, what's the $7 tool that stops the bleeding?"

### Step 3: Cross-Pattern Analysis

After identifying opportunities via any mode, cross-reference:
- Do **multiple** studies/papers mention the same gap? That's a stronger signal.
- Has the problem been commoditized by **free** enterprise tools? Check Filter 4.
- Is the quantified pain big enough to justify $3-10 one-time? Check Filter 3.
- **Cross-domain validation**: If arxiv says X is a problem AND industry surveys agree, that's double-validated.

### Step 4: Apply the 5 Filters
Run each synthesized idea through Filters 1-5. Be ruthless.

For each that passes, determine:
- **Who exactly pays?** (specific individual persona, not "teams")
- **What exists already?** Search `[pain point] tool` and check top 3.
- **What would they pay?** Match to pricing framework.
- **Can we build it?** Map to CF Workers constraints.

### Step 5: Score and Rank
Score 1-5 on:
- **Pain intensity** (5 = hours wasted daily, 1 = mild annoyance)
- **Buyer accessibility** (5 = exact subreddit/keyword exists, 1 = hard to find)
- **Build simplicity** (5 = one API call + UI, 1 = multiple integrations)
- **Revenue clarity** (5 = obvious value > price, 1 = hard to justify charging)

Only save ideas scoring **12+/20**.

### Step 6: Select THE Winner
From the scored pool (12+/20), select exactly **ONE single best candidate** using this formula:

1. **Primary sort**: Total score (highest wins)
2. **Tiebreaker**: Highest "Pain intensity" (build what hurts most first)
3. **Final tiebreaker**: Lowest build complexity (quickest to market)

Mark the winner as `"recommended_for_build": true` in its database entry.

### Step 7: Save to Database
Append to `~/.hermes/data/business-ideas.json`.

**build_ready is FALSE by default.** Ideas go raw -> reviewed -> build_ready.

**Deduplication**: Compare against existing ideas. Skip if substantially similar to a raw or build_ready idea.

**Winner flagging**: Exactly ONE entry per run gets `"recommended_for_build": true` (selected via Step 6 formula).

## When to Stop — HARD CEILING

**This skill's ONLY job is to produce scored ideas in the database. It does NOT build anything.**

### STOP conditions (first one that triggers):
1. **Exactly 3 candidates scored 12+/20 written to database with 1 explicit recommendation marked** → STOP IMMEDIATELY. Output a clean summary table and wait for user direction.
2. 5 content fetches with no new qualifying patterns → stop
3. Evaluated 30+ opportunities → stop
4. User says "build one" → STOP synthesis, hand off to mvp-storefront

### After stopping:
- Present the scored ideas in a clean table (id, score, topic, one-line)
- **Clearly mark ONE as: ⭐ RECOMMENDED FOR BUILD**
- Ask user if they want to build the recommended one or pick another from the shortlist
- DO NOT continue absorbing, extracting, or synthesizing after the hard ceiling is hit

**The handoff chain is: trend-synthesizer produces ideas → user picks one → mvp-storefront builds storefront → mvp-builder builds product**

### DO NOT:
- Keep researching after 3+ scored ideas are saved
- Keep validating ideas against more sources after scoring
- Jump into storefront or MVP building in this skill
- Re-synthesize the same domains

**Goal: Scored ideas in database. That's it. That's the deliverable.**

## Pitfalls
- **Cross-domain porting is the HIGHEST-LEVERAGE synthesis pattern.** A technique that works in domain A but hasn't been applied to domain B = free market opportunity. Always look for this explicitly (Mode C).
- **Force domain diversity:** Before running, pick 2-3 distinct topics (e.g., "finance + education + healthcare", not all developer tools). If all your synthesized ideas are from one domain, you failed Step 1. Restart with different domains.
- **Research ≠ Commercial**: Academic papers study problems; they rarely validate someone will pay $7 to fix it. Always check Filter 3 (willingness to pay).
- **Enterprise Trap**: Papers describe teams, departments, enterprises. Every idea must be remapped to individual buyer at $3-10. If you can't find the solo version, discard.
- **Benchmark Fallacy ≠ Solution Gap**: A benchmark proves measurement exists. Validate the gap is actually unfilled for individuals.
- **Synthesis Vagueness**: "AI code quality tool" is garbage. "Pre-commit AI-generated code smell checker for solo developers at $7 one-time" is specific enough to test.
- **Scoring generously**: Better to save 2 strong ideas than 10 weak ones.
- **NEVER use curl**: Use web_search + web_extract. web_extract handles PDF-to-markdown natively.
- **Ad-hoc builds leave orphaned products**: Building outside these skills (or skipping Step 6) means the product won't exist in business-ideas.json, making it invisible to empire-ledger, execution-tracker, and future recall. If a deployed product is missing from the database: search session history → check Cloudflare Workers manually → retroactively add entry with mvp_status metadata.
- **WRONG TOOL**: This is a methodology skill. Use web_search, web_extract, read_file, write_file directly.

**Content Extraction Reality Check:**
- **arXiv PDFs often timeout** (60k+ chars). If extraction fails, try the HTML version (`https://arxiv.org/html/[ID]`) or abstract only.
- **Reddit blocks scrapers** systematically. Use `site:news.ycombinator.com` searches instead for developer complaints - HN text pages are more accessible than Reddit JSON endpoints.
- **Academic journals (JMIR, MDPI)** frequently block web_extract. If extraction returns empty/error, skip to next source rather than retrying 3+ times.
- **Forbes/Industry sites** have anti-bot measures. Use `web_search` descriptions when full content isn't available - often enough for pain point identification.

**Search Snippet Data is VALID:** Quantified friction data IN SEARCH SNIPPETS (e.g., "70% of e-commerce traffic is organic", "20-21 hours/week on bookkeeping") counts as valid sources for synthesis. Don't waste fetches trying to extract full pages when the search result already contains the numbers you need. This is especially useful for industry surveys and benchmark summaries where key stats appear in meta descriptions.

**Fallback Strategy When Extraction Fails:**
If web extraction fails on large academic PDFs or industry surveys (common with 60k+ char content), **do not retry 3+ times**. Instead:
1. Leverage existing quantified friction data from previous runs in `business-ideas.json` as valid sources
2. Apply cross-domain porting (Mode C) to established patterns without needing fresh extraction
3. Cross-pattern analysis can use validated citations already in database (e.g., "24.2% AI bug survival rate" from prior arXiv:2403.17698 extraction)
4. This prevents wasted tool calls while still producing valid synthesized ideas using Mode C synthesis
