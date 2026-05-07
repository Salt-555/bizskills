#!/usr/bin/env python3
"""
Sales Tracker — Query MVP sales performance and flag kill candidates.
Reads business-ideas.json, queries Cloudflare KV namespaces for sales data,
calculates metrics, applies kill criteria.

Usage:
  python3 query_sales.py              # All products summary
  python3 query_sales.py --kill-only  # Only products hitting kill criteria
  python3 query_sales.py <product-id> # Single product detail
"""
import os, sys, json, urllib.request, urllib.error, argparse
from datetime import datetime, timedelta

ACCOUNT_ID = "YOUR_CF_ACCOUNT_ID"
CF_TOKEN = os.environ.get("CLOUDFLARE_TOKEN")
DB_PATH = os.path.expanduser("~/.hermes/data/business-ideas.json")

# Kill criteria configuration
KILL_CRITERIA = {
    "no_sales_days": 14,      # Days with zero sales → kill
    "min_revenue_30d": 500,   # Cents. <$5 after 30 days → kill
    "min_velocity_cents_day": 100,  # <$1/day avg → at risk
}

def cf_kv_read(namespace_id, key):
    """Read a value from Cloudflare KV via REST API."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/storage/kv/namespaces/{namespace_id}/values/{key}"
    headers = {"Authorization": f"Bearer {CF_TOKEN}"}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            if result.get("success") and result["result"]:
                return result["result"]["value"]  # This is a JSON string
            return None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # Key doesn't exist yet
        print(f"KV read error for {key}: HTTP {e.code}")
        return None

def parse_tracking_data(raw_value):
    """Parse the tracking JSON string into a dict."""
    if not raw_value:
        return None
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse tracking data")
        return None

def calculate_metrics(tracking, deployed_at_str):
    """Calculate derived metrics from raw tracking data."""
    if not tracking:
        return {"status": "NO_DATA", "message": "No sales data available yet"}
    
    today = datetime.now()
    deployed_at = datetime.fromisoformat(deployed_at_str.replace("Z", "+00:00")).replace(tzinfo=None)
    days_since_deploy = (today - deployed_at).days
    
    first_sale_at = tracking.get("first_sale_at")
    last_sale_at = tracking.get("last_sale_at")
    
    # Parse timestamps
    if first_sale_at:
        first_sale_dt = datetime.fromisoformat(first_sale_at.replace("Z", "+00:00")).replace(tzinfo=None)
        days_to_first_sale = (first_sale_dt - deployed_at).days
    else:
        days_to_first_sale = None
    
    if last_sale_at:
        last_sale_dt = datetime.fromisoformat(last_sale_at.replace("Z", "+00:00")).replace(tzinfo=None)
        days_since_last_sale = (today - last_sale_dt).days
    else:
        days_since_last_sale = None
    
    # Revenue velocity
    revenue_cents = tracking.get("revenue_cents", 0)
    velocity = revenue_cents / max(days_since_deploy, 1)  # cents per day
    
    return {
        "total_sales": tracking.get("total_sales", 0),
        "revenue_cents": revenue_cents,
        "revenue_dollars": round(revenue_cents / 100, 2),
        "days_since_deploy": days_since_deploy,
        "days_to_first_sale": days_to_first_sale,
        "days_since_last_sale": days_since_last_sale,
        "velocity_cents_per_day": velocity,
        "velocity_dollars_per_day": round(velocity / 100, 2),
    }

def assess_status(metrics):
    """Apply kill criteria and return status + reasoning."""
    if metrics["status"] == "NO_DATA":
        return "NEW", "Just deployed, no data yet"
    
    reasons = []
    
    # Check: No sales after X days
    if metrics["days_to_first_sale"] is None:
        if metrics["days_since_deploy"] >= KILL_CRITERIA["no_sales_days"]:
            return "KILL", f"No sales after {metrics['days_since_deploy']} days"
        elif metrics["days_since_deploy"] >= 7:
            reasons.append(f"⚠️ No sales in {metrics['days_since_deploy']} days")
    
    # Check: Low revenue after 30 days
    if metrics["days_since_deploy"] >= 30:
        if metrics["revenue_cents"] < KILL_CRITERIA["min_revenue_30d"]:
            return "KILL", f"Only ${metrics['revenue_dollars']} after 30 days"
    
    # Check: Low velocity
    if metrics["velocity_cents_per_day"] < KILL_CRITERIA["min_velocity_cents_day"]:
        if metrics["total_sales"] > 0:  # Has some sales but slow
            reasons.append(f"⚠️ Low velocity: ${metrics['velocity_dollars_per_day']}/day")
    
    # Double down signals
    if metrics["days_to_first_sale"] == 0:
        reasons.append("🚀 First sale on day 1!")
    if metrics["velocity_cents_per_day"] >= 1000:  # $10/day
        reasons.append(f"🚀 High velocity: ${metrics['velocity_dollars_per_day']}/day")
    
    # Determine overall status
    if "KILL" in [r.split()[0] for r in reasons]:
        pass  # Already returned above
    elif any("🚀" in r for r in reasons):
        return "DOUBLE_DOWN", "; ".join(reasons)
    elif reasons:
        return "AT_RISK", "; ".join(reasons)
    else:
        return "HEALTHY", "Meeting performance expectations"

def format_status_indicator(status):
    """Return emoji/indicator for status."""
    indicators = {
        "NEW": "📦",
        "HEALTHY": "✅",
        "DOUBLE_DOWN": "🚀",
        "AT_RISK": "⚠️",
        "KILL": "💀",
        "NO_DATA": "❓"
    }
    return indicators.get(status, "❓")

def main():
    parser = argparse.ArgumentParser(description="Query MVP sales performance")
    parser.add_argument("product_id", nargs="?", help="Single product ID to query")
    parser.add_argument("--kill-only", action="store_true", help="Only show kill candidates")
    args = parser.parse_args()

    if not CF_TOKEN:
        print("ERROR: CLOUDFLARE_TOKEN not in env")
        sys.exit(1)

    # Read database
    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    with open(DB_PATH) as f:
        db = json.load(f)

    # Filter to live products only
    live_products = [
        p for p in db.get("ideas", [])
        if p.get("mvp_status") == "live" and "sales_kv_id" in p
    ]

    if args.product_id:
        # Single product query
        product = next((p for p in live_products if p["id"] == args.product_id), None)
        if not product:
            print(f"Product '{args.product_id}' not found or not live")
            sys.exit(1)
        
        tracking_raw = cf_kv_read(product["sales_kv_id"], product["id"])
        tracking = parse_tracking_data(tracking_raw)
        metrics = calculate_metrics(tracking, product.get("deployed_at", datetime.now().isoformat()))
        status, reasoning = assess_status(metrics)
        
        print(f"\n=== {product['id'].upper()} ===")
        print(f"Deployed: {product.get('deployed_at', 'unknown')}")
        print(f"Price: ${product.get('price_cents', 500)/100}")
        print()
        if metrics["status"] == "NO_DATA":
            print("No sales data available yet.")
        else:
            print(f"Total Sales: {metrics['total_sales']}")
            print(f"Revenue: ${metrics['revenue_dollars']}")
            print(f"Days Since Deploy: {metrics['days_since_deploy']}")
            if metrics["days_to_first_sale"] is not None:
                print(f"Days to First Sale: {metrics['days_to_first_sale']}")
            if metrics["days_since_last_sale"] is not None:
                print(f"Days Since Last Sale: {metrics['days_since_last_sale']}")
            print(f"Velocity: ${metrics['velocity_dollars_per_day']}/day")
        print()
        print(f"Status: {format_status_indicator(status)} {status.upper()}")
        print(f"Reasoning: {reasoning}")
        return

    # All products summary
    results = []
    for product in live_products:
        tracking_raw = cf_kv_read(product["sales_kv_id"], product["id"])
        tracking = parse_tracking_data(tracking_raw)
        metrics = calculate_metrics(tracking, product.get("deployed_at", datetime.now().isoformat()))
        status, reasoning = assess_status(metrics)
        
        results.append({
            "product": product,
            "metrics": metrics,
            "status": status,
            "reasoning": reasoning
        })

    # Filter if --kill-only
    if args.kill_only:
        results = [r for r in results if r["status"] in ("KILL", "AT_RISK")]

    # Output
    print(f"\n{'='*60}")
    print("SALES PERFORMANCE REPORT")
    print(f"{'='*60}\n")

    for r in results:
        p = r["product"]
        m = r["metrics"]
        status = r["status"]
        reasoning = r["reasoning"]
        
        print(f"Product: {p['id']}")
        if m["status"] == "NO_DATA":
            print(f"  Status: {format_status_indicator(status)} {status} — {reasoning}")
        else:
            print(f"  Deployed: {p.get('deployed_at', 'unknown')} ({m['days_since_deploy']} days ago)")
            print(f"  Total Sales: {m['total_sales']}")
            print(f"  Revenue: ${m['revenue_dollars']}")
            if m["days_to_first_sale"] is not None:
                first_sale_indicator = "✓" if m["days_to_first_sale"] <= 1 else ""
                print(f"  First Sale: Day {m['days_to_first_sale']} {first_sale_indicator}")
            if m["days_since_last_sale"] is not None:
                print(f"  Last Sale: {m['days_since_last_sale']} days ago")
            print(f"  Velocity: ${m['velocity_dollars_per_day']}/day")
        print(f"  Status: {format_status_indicator(status)} {status.upper()} — {reasoning}")
        print()

    # Summary
    kill_count = sum(1 for r in results if r["status"] == "KILL")
    double_down_count = sum(1 for r in results if r["status"] == "DOUBLE_DOWN")
    
    print(f"{'='*60}")
    print(f"Summary: {len(results)} products | 💀 {kill_count} kill candidates | 🚀 {double_down_count} double down")

if __name__ == "__main__":
    main()
