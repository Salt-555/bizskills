---
name: sales-tracker
description: "Query sales metrics from deployed MVPs, calculate performance indicators, flag products hitting kill criteria. Uses Cloudflare KV SALES_TRACKING namespaces populated by mvp-storefront webhooks."
compatibility: Requires CLOUDFLARE_TOKEN environment variable with Workers KV read permissions.
---

# Sales Tracker

Query sales data, calculate metrics, flag underperforming products.

## Data Source
Sales tracking KV namespaces created by `mvp-storefront` deploy script. Each product has a namespace named `{product-name}-sales-tracking`. The webhook writes sale records keyed by product_id (slug).

**Tracking record schema:**
```json
{
  "total_sales": 3,
  "revenue_cents": 1500,
  "first_sale_at": "2026-03-31T10:00:00Z",
  "last_sale_at": "2026-04-01T14:30:00Z",
  "sales": [
    {"timestamp": "...", "amount_cents": 500, "price_id": "price_xxx", "email_hash": "..."}
  ]
}
```

## Kill Criteria (Configurable)

| Metric | Kill Threshold | Double Down Signal |
|--------|----------------|--------------------|
| Time to first sale | >14 days with zero sales | <24 hours |
| Revenue after 30 days | <$50 total | >$200 |
| Revenue velocity | <$1/day averaged over 7 consecutive days | >$10/day sustained |

## Usage Patterns

### "Show me all product performance"
```python
# Read business-ideas.json for deployed products
# Query each sales tracking KV
# Calculate metrics, flag kills/double-downs
# Output summary table
```

### "How is [product-name] doing?"
```python
# Find product in database
# Query its sales tracking KV
# Return detailed metrics + status assessment
```

### "Flag products ready to kill"
```python
# Scan all live products
# Apply kill criteria
# Output list with reasoning
```

## Cloudflare API for KV Read

```
GET /accounts/{ACCOUNT_ID}/storage/kv/namespaces/{NAMESPACE_ID}/values/{KEY}
Headers: Authorization: Bearer {CLOUDFLARE_TOKEN}
```

Returns JSON body with `value` field containing the stored string.

## Implementation Notes

1. **Read business-ideas.json** to get list of deployed products and their sales_kv_id values
2. **Query each KV namespace** using Cloudflare REST API (no wrangler)
3. **Parse tracking record** and calculate derived metrics:
   - Days since deploy = today - deployed_at
   - Days since last sale = today - last_sale_at  
   - Revenue velocity = revenue_cents / max(days_since_deploy, 1)
4. **Apply kill criteria** and flag products
5. **Output formatted report**

## Example Output

```
=== SALES PERFORMANCE REPORT ===

Product: ai-writing-assistant
Deployed: 2026-03-28 (3 days ago)
Total Sales: 7
Revenue: $35.00
First Sale: Day 1 ✓
Last Sale: Today
Velocity: $11.67/day 🚀 DOUBLE DOWN
Status: HEALTHY

---

Product: pdf-compressor-tool
Deployed: 2026-03-20 (11 days ago)
Total Sales: 0
Revenue: $0.00
First Sale: NEVER
Velocity: $0/day
Status: ⚠️ KILL CANDIDATE — No sales after 11 days

---

Product: seo-meta-generator
Deployed: 2026-03-25 (6 days ago)
Total Sales: 2
Revenue: $10.00
First Sale: Day 4
Last Sale: Day 5
Velocity: $1.67/day
Status: ⚠️ AT RISK — Low velocity, may hit kill criteria
```

## Pitfalls

- KV namespaces are created per-product; need sales_kv_id from business-ideas.json
- Cloudflare API returns value as escaped JSON string — parse twice if needed
- Some products may have no tracking data yet (newly deployed) — handle gracefully
- Revenue velocity calculation should use max(days, 1) to avoid division by zero
