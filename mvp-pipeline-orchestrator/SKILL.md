---
name: mvp-pipeline-orchestrator
description: "Pipeline orchestrator for the full MVP lifecycle — knows which skill to load at each phase. Thin router, not an implementation guide. Use when planning or executing a multi-phase MVP from idea through launch."
version: 2.0.0
author: ALLMIND
required_environment_variables: []
metadata:
  hermes:
    tags: [business, pipeline, orchestration, mvp]
    related_skills: [idea-miner, mvp-storefront, mvp-builder, ads-manager, execution-tracker, sales-tracker, kanban-orchestrator]
---

# MVP Pipeline Orchestrator

Thin router for the full MVP lifecycle. Knows which skill to load at each phase. Does NOT implement anything — delegates to domain skills.

## When to Use

- "Build an MVP for X" (full pipeline)
- "Take this idea from concept to launch"
- Multi-phase requests spanning research → deploy → ads
- You need the big picture before diving into a single skill

When NOT to use: single-phase tasks ("deploy storefront", "write ad copy") — load that specific skill directly.

## The Pipeline

```
Phase 0    Phase 1          Phase 2        Phase 3       Phase 4
─────────  ───────────────  ────────────   ──────────    ───────────
idea-miner → mvp-storefront (full) → mvp-builder → ads-manager → execution-tracker / sales-tracker
            │                    │               │                  │
            └── payments on ────┘       └── build product ────────┘
```

**No market-testing phase.** Build time is hours, not weeks — skip the middleman. Deploy full storefront with payments from day one.

## Phase Map — Load These Skills, In This Order

### Phase 0: Mine the Idea → `idea-miner`
**Trigger:** "I have an idea", "find business ideas", "what should I build"
**Load:** `skill_view("idea-miner")`
**Output:** Structured idea in `business-ideas.json` with pain point, audience, price estimate.
**Gate to next:** Idea saved to database + user approves direction.

### Phase 1: Deploy Full Storefront → `mvp-storefront`
**Trigger:** "deploy storefront", "set up landing page", "go live"
**Load:** `skill_view("mvp-storefront")` — use **full mode** (payments, Stripe webhook, download flow from the start).
**Output:** Live URL at `{name}.yourdomain.com`, payments working, idea status = `storefront_deployed`.
**Gate to next:** Storefront verified live + user says "build the product" OR skip if downloadable zip.

### Phase 2: Build the Product → `mvp-builder`
**Trigger:** "build the product", "implement this idea", "the actual tool"
**Load:** `skill_view("mvp-builder")` — follows its chunk-by-chunk methodology.
**Output:** Product routes merged into worker, deployed, auth-gated behind purchase.
**Gate to next:** End-to-end test passes (purchase → access works).

### Phase 3: Launch Ads → `ads-manager`
**Trigger:** "run ads", "launch campaign", "start traffic"
**Load:** `skill_view("ads-manager")`, then `skill_view("ad-campaign-strategy")` for copy.
**Output:** Campaign running, conversion event = purchase, CPA tracked.

### Phase 4: Monitor & Track → `execution-tracker` + `sales-tracker`
**Trigger:** "monitor this", "track performance", "how are sales"
**Load:** `skill_view("execution-tracker")` for automated monitoring, `skill_view("sales-tracker")` for revenue queries.

## Short-Circuit Paths

| Scenario | Phases Used | Skip |
|----------|------------|------|
| Downloadable zip product (no app) | 0 → 1(full) | 2, 3, 4 |
| User has validated idea | Start at Phase 1 | 0 |
| Quick calculator tool | 0 → 1(full) → 2(client-side only) | 3, 4 |

## Kanban Integration

Use kanban when the pipeline needs **multi-agent decomposition** or **survives a crash**:

### When to use Kanban vs sequential execution

**Run sequentially (no kanban):**
- Single agent executing phases one-by-one in this session
- User is present and can approve gates interactively
- Pipeline completes within one conversation turn

**Use Kanban (`kanban-orchestrator`):**
- Multiple specialists needed per phase (e.g., researcher + builder + ops)
- Work should survive a crash or restart
- User wants to interject at any step later
- Subtasks can run in parallel across phases
- Audit trail matters

### How to invoke Kanban for the pipeline

Load `skill_view("kanban-orchestrator")`, then decompose the pipeline into tasks:

```
T0  planner         decompose MVP pipeline for {idea_id}
T1  researcher      mine idea / validate pain point          parents: T0
T2  ops             deploy full storefront                    parents: T1
T3  backend-eng     build product                             parents: T2
T4  ops             launch ads                                parents: T3
```

Each task loads its own downstream skill (`idea-miner`, `mvp-storefront`, etc.) when it executes. The kanban dispatcher handles dependencies, parallelism, and crash recovery.

See `kanban-orchestrator` for the full decomposition playbook, specialist roster conventions, and lifecycle management.

## Execution Protocol

When asked to run a full pipeline:

1. **Show the plan** — which phases apply, estimated timeline per phase
2. **Get approval** at each gate before proceeding
3. **Load the skill** for that phase with `skill_view()`
4. **Follow that skill's methodology** exactly — don't improvise steps
5. **Update business-ideas.json** after each phase (skills handle this)
6. **Report status** — what completed, what's next

## Environment Variables by Phase

Each skill declares its own `required_environment_variables` — they auto-load when you call `skill_view()`. No need to manage them here:

| Phase | Skill | Auto-Loads |
|-------|-------|-----------|
| 1 (storefront) | mvp-storefront | CLOUDFLARE_TOKEN, STRIPE_SECRET_KEY, PAYMENT_HMAC_SECRET, RESEND_KEY |
| 2 (product) | mvp-builder | CLOUDFLARE_TOKEN, STRIPE_SECRET_KEY |

Just load the skill — credentials appear automatically.

## Pitfalls

- **Don't skip storefront for product.** Storefront defines the integration contract (KV schema, payment flow). Building product first means guessing at the surface.
- **Don't duplicate skills.** This orchestrator loads them; it doesn't reimplement their steps.
- **Payments from day one.** No market-testing phase — if build time is hours, validate with real transactions, not email signups.
