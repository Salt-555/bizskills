---
name: calculator-funnel-ux
description: |
  Principles for building integrity-preserving calculator funnels in MVPs.
  Covers how to reduce input friction without producing fictitious results,
  when to reframe the math model vs. keep fields visible, and common
  pitfalls in sales-funnel calculators.
metadata:
  hermes:
    category: business
    tags: [mvp, funnel, calculator, ux, conversion]
---

# Calculator Funnel UX Integrity

## Core Problem

Sales funnels often use calculators to generate personalized results. More inputs = more accuracy but also more friction. The temptation is to hide fields and hardcode defaults. **This destroys credibility if the defaults are wrong for the user.**

## The Golden Rule

> **Never hide a field with an arbitrary hardcoded default.**
>
> Either the math works without it, or the field stays visible.

## Two Valid Paths to Reduce Friction

### Path A: Reframe the Math Model (Preferred)

Change what the calculator computes so it needs fewer inputs.

**Example — Squeezed (parent support calculator):**

| Original Model | Reframed Model |
|----------------|----------------|
| "Can you afford to retire while supporting dependents?" | "What is your support costing your retirement wealth?" |
| Required: income, savings, contributions, tax rate, inflation, support amount, ages | Required: age, retirement age, monthly support |
| Complex formula with hidden defaults | Simple compound interest: `fv = monthly × fvFactor` |
| Risk: wrong defaults = nonsense output | Impossible to be "wrong" — it's math on money already spent |

**Why this works:** The emotional hook shifts from "can I afford this?" (requires personal financial audit) to "holy shit this costs how much?" (requires only one number they already know).

### Path B: Keep Critical Fields Visible

If the value prop genuinely requires those inputs, keep them. Reduce friction through other means:
- Inline validation with gentle error states
- Autofill from URL params (`?income=75000`)
- Progressive disclosure (show 3 fields, expand for "advanced")
- Smart defaults with explicit "Using US median — adjust if different" copy

## When Reframing Works Best

Reframe when the user's emotional response comes from:
- **Opportunity cost** (what they'd have if they did X instead)
- **Scale surprise** ("I had no idea it was THAT much")
- **Comparative loss** ("My neighbor who doesn't support their kids will have $X more")

Keep the full model when the user needs:
- **A specific actionable target** ("you can afford $847/mo")
- **A pass/fail assessment** ("you're on track" / "you're $340k short")

## Common Pitfalls

1. **The Landing-Page Calculator Trap** — Embedding the calculator directly on the landing page so the first thing visitors see is a form. A landing page must answer "What is this?" "Why should I care?" and "What does it cost?" BEFORE asking for data. If visitors must fill out fields to see any value, 80%+ will bounce before understanding the product. **Rule**: Landing page sells the outcome; calculator lives at `/app` or behind a clear CTA.

2. **The Median Trap** — Using US median income ($75k) as a default. Half your users are below this. Their results will be inflated.

3. **The Zero-Baseline Trap** — Hiding "current savings" and defaulting to $0 makes the calculator look bleak. But defaulting to $100k makes it look rosy. Neither is honest.

4. **The Dependency Inflation** — Hidden fields that get ADDED to the user's visible input. Example: user enters $500/mo for adult kids, but a hidden $500/mo "aging parents" field secretly doubles their number.

5. **The Confidence Fallacy** — Presenting precise numbers (`$1,847,293`) from imprecise inputs. Round aggressively. `$1.8M` feels more honest than `$1,847,293`.

## Verification Checklist

Before deploying a simplified calculator:

- [ ] Test with extreme inputs: $30k income, $0 savings, $2,000/mo support
- [ ] Test with high inputs: $200k income, $500k savings, $200/mo support
- [ ] Verify no hidden fields are being read by `getElementById`
- [ ] Verify `populateResults()` only uses properties returned by `calculate()`
- [ ] Check that print/summary views match the live calculator exactly
- [ ] Confirm bar chart max values don't divide by zero when baseline is 0

## The Squeezed Reframe Template

```javascript
// Before: complex retirement adequacy model
function calculate(inputs) {
  var targetRetirement = inputs.annualIncome * 0.8 * 25;
  var fvKeep = inputs.savings * growthFactor + inputs.contributions * fvFactor;
  var shortfall = targetRetirement - fvKeep;
  // ... requires income, savings, contributions, all with defaults
}

// After: pure opportunity cost model
function calculate(inputs) {
  var yearsLeft = inputs.retireAge - inputs.currentAge;
  var months = yearsLeft * 12;
  var fvFactor = (Math.pow(1 + r, months) - 1) / r;
  
  var monthlySupport = inputs.monthlyAdultSpend;
  var totalCashOut = monthlySupport * months;
  var fvIfInvested = monthlySupport * fvFactor;
  
  return {
    totalCashOut: totalCashOut,        // "You'll spend $X directly"
    fvIfInvested: fvIfInvested,        // "If invested, that's $X at retirement"
    fvReduce50: monthlySupport * 0.5 * fvFactor,
    fvReduce75: monthlySupport * 0.75 * fvFactor,
  };
}
```

## Deploy Checklist

After modifying calculator logic:
1. Update `calculate()` return signature
2. Update `populateResults()` to use new property names
3. Update `animateBars()` max calculation
4. Update print/summary views
5. Update paywall feature list (remove claims the new model can't support)
6. Update conversation scripts to reference user's actual support amount, not computed "affordable" amount
7. Clear localStorage key so returning users don't see cached old results
8. Deploy and verify with curl + browser
