---
name: mvp-enhancement-assessment
description: "Assess a deployed MVP for feature enhancement opportunities - examine live worker, understand data structures, scope options by effort/impact. Use when asked to add value, improve, or enhance an existing deployed MVP."
version: 1.0.0
author: ALLMIND
license: proprietary
metadata:
  hermes:
    tags: [business, mvp, enhancement, assessment]
    related_skills: [mvp-storefront, mvp-builder, execution-tracker]
    requires_tools: [terminal, browser]
required_environment_variables: []
---

# MVP Enhancement Assessment

Assess a deployed MVP for feature additions or value improvements. This is the pre-build step before implementing changes - understand what exists, scope options, recommend approach.

## When to Use

- "Add more value to {MVP}"
- "Improve/enhance {deployed product}"
- "What can we add to {MVP}?"
- Post-launch feature planning for any deployed MVP

## Workflow

### 1. Load Context

```bash
# Get deploy metadata (mode, URLs, Stripe IDs)
cat ~/.hermes/mvps/{name}/deploy-metadata.json

# List source files
ls -la ~/.hermes/mvps/{name}/src/
```

Load `mvp-storefront` skill first for env vars and deployment instructions.

### 2. Examine Live App

Navigate to the app URL (usually `/app` route) via browser tools:

```bash
browser_navigate("https://{name}.yourdomain.com/app")
browser_snapshot(full=true)  # See current UI structure
```

### 3. Inspect Data Structures

Use `browser_console` with JavaScript expressions to understand the data model:

```javascript
// Check main data object exists and size
typeof DB !== 'undefined' ? Object.keys(DB).length : 0

// Examine a sample entry structure
JSON.stringify(DB['sample_key'], null, 2)

// Check nested arrays/objects
JSON.stringify(DB['sample_key'].subfield.slice(0, 3), null, 2)
```

### 4. Read Worker Source

Find where data lives and how it's rendered:

```bash
# Find main data declaration
grep -n "var DB = {" ~/.hermes/mvps/{name}/src/worker.js

# Read rendering functions (showSheet, doReverse, etc.)
read_file with offset near data declaration
```

Key things to identify:
- Data schema (flat arrays vs nested objects)
- Rendering functions and their output format
- Paywall/unlock logic if applicable
- Current worker size (`ls -la` shows file size)

### 5. Assess Constraints

**Cloudflare Worker limits:**
- Total compressed size: ~1MB
- Typical headroom: current size to ~800KB for safety
- Inline data (JSON in JS): ~3x expansion from source chars
- Base64 images: ~140KB JPEG → ~184KB base64 → ~64KB gzipped

**Template literal pitfalls:**
- Multiple HTML constants = isolated CSS per page
- Embedded `<script>` tags need careful escaping (double quotes for apostrophes)
- `node -c` validates outer worker.js but not inner script content

### 6. Scope Options by Level

Present options as **Level N** tiers:

| Level | Effort | Risk | Description |
|-------|--------|------|-------------|
| 1 | <30 min | Low | Data additions, minor rendering changes |
| 2 | 1-2 hours | Medium | New data structures, UI components |
| 3 | Half day+ | Higher | Architecture changes, new routes |

### 7. Recommend Approach

Default recommendation: **Start with Level 1** unless user specifies otherwise. Rationale:
- Fast validation of whether the enhancement drives engagement/conversion
- Minimal risk to existing functionality
- Can iterate based on analytics data

## Output Format

Return assessment as:

```
## Current State
- Worker size: {X}KB ({Y}% of limit)
- Data structure: {description}
- Key rendering functions: {list}

## Enhancement Options

### Level 1: {Name} (EASY - ~{time})
What it adds, changes needed, size impact.

### Level 2: {Name} (MEDIUM - ~{time})  
What it adds, changes needed, size impact.

## Recommendation
Start with Level N because...
```

## Pitfalls

- **Never modify worker.js directly** - always work from local repo source
- **Check for duplicate code** between template literal boundaries before deploying
- **Validate embedded JS separately**: `curl` the live page, extract `<script>`, run `node -c`
- **Paywall scope changes** require updating both HTML overlays AND JS unlock checks
- **CSS classes must be duplicated** per HTML constant (APP_HTML, SUCCESS_HTML, etc.)

## After Assessment

If user approves a level:
1. Implement in local repo source files
2. Test locally if possible (`node -c worker.js`)
3. Deploy via mvp-storefront skill deployment steps
4. Verify live with browser tools
