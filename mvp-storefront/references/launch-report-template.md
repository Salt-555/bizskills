# MVP Deployed: [Project Name]

## URLs
- Landing: https://[project].workers.dev
- API: https://[project].workers.dev/api
- Stripe Dashboard: https://dashboard.stripe.com/test/products

## Test Results
- Landing page: [pass/fail]
- Stripe checkout: [pass/fail]
- Webhook: [pass/fail]
- Cancellation: [pass/fail]
- Privacy/Terms: [pass/fail]

## Monthly Costs
- Cloudflare Workers: $0-5 (100k req/day free)
- Stripe: 2.9% + $0.30/txn
- Auth: $0-25 (Clerk free tier)
- Total fixed: ~$0-40/mo

## Pre-Launch Checklist
- [ ] Switch Stripe to live mode
- [ ] Test with real card ($1 charge)
- [ ] Verify /privacy and /terms load
- [ ] Test cancellation flow end-to-end
- [ ] Test account deletion flow

## Launch Checklist
- [ ] Post on Product Hunt
- [ ] Share on Twitter/X
- [ ] Post in relevant subreddits
- [ ] Email validation signups (if any)

## Week 1
- [ ] Respond to emails within 4 hours
- [ ] Fix critical bugs immediately
- [ ] Track: signups, conversions, churn
- [ ] Ask first 10 customers for feedback

## Metrics to Track
- Conversion: visitor -> paid (target 2-5%)
- CAC: ad spend / customers
- LTV: avg monthly x retention months
- CAC:LTV ratio: target 1:3 minimum
- MRR, churn rate