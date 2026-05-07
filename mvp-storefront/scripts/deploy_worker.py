#!/usr/bin/env python3
"""
Deploy ALLMIND Workers via Cloudflare REST API.

Modes:
  python3 deploy_worker.py proxy                                              # Deploy payment proxy (ONCE)
  python3 deploy_worker.py build <name> [product-name]                        # Generate worker JS (edit copy, then deploy)
  python3 deploy_worker.py market-testing <name> <js-path> [product-name]     # Deploy pre-built worker (no Stripe)
  python3 deploy_worker.py mvp <script-name> <js-path> [name] [cents]         # Deploy full MVP worker (uses proxy)
  python3 deploy_worker.py download <script-name>                             # Download worker source to local repo

Build mode:
  Generates a market-testing worker JS in the local repo with templates filled.
  Shows remaining placeholders. Edit the file, fill in product copy, THEN deploy.

Market-testing mode:
  Deploys a pre-built landing page + email capture worker. No Stripe, no payment.
  Use this to test demand via ads before building the MVP.
  Same URL as the eventual full storefront — ads don't break on transition.

MVP mode (full storefront):
  Deploys an MVP worker that uses the payment proxy via Service Binding.
  This is the production path: Stripe checkout, webhook, download, email.
  Can be deployed fresh OR as a transition from market-testing (same script_name).

Proxy mode:
  Deploys the payment-proxy proxy worker with STRIPE_SECRET_KEY.
  Run this ONCE. All MVP workers bind to it via Service Bindings.
"""
import os, sys, json, urllib.request, urllib.error, re, hashlib, secrets, urllib.parse

ACCOUNT_ID = "YOUR_CF_ACCOUNT_ID"
CF_TOKEN=os.environ.get("CLOUDFLARE_TOKEN")
STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY")
BASE_API = "https://api.cloudflare.com/client/v4"
PROXY_NAME = "payment-proxy"
CUSTOM_DOMAIN = "yourdomain.com"
ZONE_ID = os.environ.get("CF_ZONE_ID", "")  # Set CF_ZONE_ID env var for custom domain setup
IDEAS_DB = os.path.expanduser("~/.hermes/data/business-ideas.json")

if not CF_TOKEN:
    print("ERROR: CLOUDFLARE_TOKEN not in env"); sys.exit(1)

# ─── Business Ideas DB Update ───
def update_ideas_db(script_name, deploy_info, mode):
    """Update business-ideas.json with deploy status."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    local_repo = os.path.join(os.path.expanduser("~/.hermes/mvps"), script_name)

    if not os.path.exists(IDEAS_DB):
        print(f"  Ideas DB not found at {IDEAS_DB} — skipping update")
        return

    with open(IDEAS_DB) as f:
        db = json.load(f)

    # Find idea by id matching script_name
    updated = False
    for idea in db.get("ideas", []):
        if idea.get("id") == script_name:
            idea["build_ready"] = True
            idea["deployed_at"] = today
            idea["worker_url"] = deploy_info.get("worker_url", "")
            idea["local_repo_path"] = local_repo
            idea["deploy_mode"] = mode

            if mode == "market-testing":
                idea["mvp_status"] = "market_testing"
                idea["signups_kv_id"] = deploy_info.get("signups_kv_id", "")
            elif mode == "full":
                idea["mvp_status"] = "storefront_deployed"
                idea["kv_namespace_id"] = deploy_info.get("kv_id", "")
                idea["sales_kv_id"] = deploy_info.get("sales_kv_id", "")
                idea["stripe_product_id"] = deploy_info.get("stripe_product_id", "")
                idea["stripe_price_id"] = deploy_info.get("stripe_price_id", "")

            updated = True
            print(f"  Ideas DB updated: {script_name} → mvp_status={idea['mvp_status']}")
            break

    if not updated:
        print(f"  WARNING: Idea '{script_name}' not found in {IDEAS_DB}")
        print(f"  Add it manually or the pipeline won't track this product")

    with open(IDEAS_DB, "w") as f:
        json.dump(db, f, indent=2)

# ─── CF API Helper ───
def cf_api(method, path, data=None):
    url = f"{BASE_API}{path}"
    headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
            errors = err.get("errors", [])
            print(f"CF API error {e.code}: {[x.get('message','unknown') for x in errors]}")
        except:
            print(f"CF API error {e.code}: (could not parse error)")
        sys.exit(1)

def stripe_api(method, path, params=None):
    url = f"https://api.stripe.com/v1/{path}"
    headers = {"Authorization": f"Bearer {STRIPE_KEY}"}
    body = None
    if params:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
            print(f"Stripe API error {e.code}: {err.get('error',{}).get('message','unknown')}")
        except:
            print(f"Stripe API error {e.code}: (could not parse error)")
        sys.exit(1)

def multipart_upload(script_name, metadata, js_content, extra_files=None):
    """Upload worker via multipart form. Returns API response dict."""
    boundary = "----WorkerUploadBoundary"
    body_parts = []

    # Metadata
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="metadata"; filename="metadata.json"')
    body_parts.append("Content-Type: application/json")
    body_parts.append("")
    body_parts.append(json.dumps(metadata))

    # Worker script
    body_parts.append(f"--{boundary}")
    body_parts.append('Content-Disposition: form-data; name="worker.js"; filename="worker.js"')
    body_parts.append("Content-Type: application/javascript+module")
    body_parts.append("")
    body_parts.append(js_content)

    # Extra files (payment-client.js, etc.)
    if extra_files:
        for fname, fcontent in extra_files.items():
            body_parts.append(f"--{boundary}")
            body_parts.append(f'Content-Disposition: form-data; name="{fname}"; filename="{fname}"')
            body_parts.append("Content-Type: application/javascript+module")
            body_parts.append("")
            body_parts.append(fcontent)

    body_parts.append(f"--{boundary}--")
    body_str = "\r\n".join(body_parts)

    url = f"{BASE_API}/accounts/{ACCOUNT_ID}/workers/scripts/{script_name}"
    req = urllib.request.Request(url, data=body_str.encode(), method="PUT")
    req.add_header("Authorization", f"Bearer {CF_TOKEN}")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def register_stripe_webhook(worker_url):
    """Register a Stripe webhook endpoint for an MVP worker via API."""
    webhook_url = f"{worker_url}/webhook"
    
    # Check if webhook already exists for this URL
    existing = stripe_api("GET", "webhook_endpoints")
    for endpoint in existing.get("data", []):
        if endpoint.get("url") == webhook_url:
            print(f"  Webhook already registered: {endpoint['id']}")
            return endpoint["id"], endpoint.get("secret", "")
    
    # Create new webhook endpoint
    result = stripe_api("POST", "webhook_endpoints", {
        "url": webhook_url,
        "enabled_events[]": "checkout.session.completed",
        "api_version": "2024-06-20",
    })
    webhook_id = result["id"]
    webhook_secret = result.get("secret", "")
    print(f"  Webhook registered: {webhook_id}")
    print(f"  Webhook secret: {webhook_secret}")
    return webhook_id, webhook_secret


def enable_subdomain(script_name):
    """Enable workers.dev subdomain for a worker."""
    result = cf_api("POST", f"/accounts/{ACCOUNT_ID}/workers/scripts/{script_name}/subdomain",
                    {"enabled": True})
    return result.get("success", False)

def worker_exists(script_name):
    """Check if a worker already exists."""
    url = f"{BASE_API}/accounts/{ACCOUNT_ID}/workers/scripts/{script_name}"
    headers = {"Authorization": f"Bearer {CF_TOKEN}"}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status == 200
    except urllib.error.HTTPError:
        return False

def generate_hmac_secret():
    """Generate a random HMAC secret for MVP <-> proxy auth."""
    return secrets.token_hex(32)

def get_or_create_kv(title):
    """Get existing KV namespace by title, or create if not found. Returns namespace ID."""
    # List existing namespaces
    result = cf_api("GET", f"/accounts/{ACCOUNT_ID}/storage/kv/namespaces?per_page=100")
    for ns in result.get("result", []):
        if ns.get("title") == title:
            print(f"  KV namespace exists: {ns['id']} (reusing)")
            return ns["id"]
    # Create new
    kv = cf_api("POST", f"/accounts/{ACCOUNT_ID}/storage/kv/namespaces", {"title": title})
    print(f"  KV namespace created: {kv['result']['id']}")
    return kv["result"]["id"]

def setup_custom_domain(script_name):
    """Set up DNS CNAME + worker route for {script_name}.yourdomain.com."""
    print(f"\nSetting up custom domain: {script_name}.{CUSTOM_DOMAIN}")
    custom_url = f"https://{script_name}.{CUSTOM_DOMAIN}"

    # 1. Create DNS CNAME (proxied)
    try:
        dns_url = f"{BASE_API}/zones/{ZONE_ID}/dns_records"
        dns_headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}
        dns_body = json.dumps({
            "type": "CNAME",
            "name": script_name,
            "content": f"{script_name}.{your-account}.workers.dev",
            "proxied": True
        }).encode()
        req = urllib.request.Request(dns_url, data=dns_body, headers=dns_headers, method="POST")
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            if result.get("success"):
                print(f"  DNS CNAME created ✓")
            else:
                print(f"  DNS warning: {result.get('errors', 'unknown')}")
    except urllib.error.HTTPError as e:
        print(f"  DNS: {e.code} (may already exist)")

    # 2. Create worker route (check existing first, then create if needed)
    try:
        route_url = f"{BASE_API}/zones/{ZONE_ID}/workers/routes"
        route_headers = {"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"}

        # Check if route already exists
        list_req = urllib.request.Request(route_url, headers={"Authorization": f"Bearer {CF_TOKEN}"})
        route_exists = False
        existing_route_id = None
        try:
            with urllib.request.urlopen(list_req) as resp:
                routes = json.loads(resp.read())
                for r in routes.get("result", []):
                    if r.get("pattern") == f"{script_name}.{CUSTOM_DOMAIN}/*":
                        route_exists = True
                        existing_route_id = r.get("id")
                        break
        except Exception:
            pass

        if route_exists:
            # Route exists but might point to wrong script — update it
            if existing_route_id:
                patch_body = json.dumps({
                    "pattern": f"{script_name}.{CUSTOM_DOMAIN}/*",
                    "script": script_name
                }).encode()
                patch_req = urllib.request.Request(
                    f"{route_url}/{existing_route_id}",
                    data=patch_body,
                    headers=route_headers,
                    method="PUT"
                )
                try:
                    with urllib.request.urlopen(patch_req) as resp:
                        result = json.loads(resp.read())
                        if result.get("success"):
                            print(f"  Worker route updated ✓")
                except Exception:
                    print(f"  Worker route exists ✓")
            else:
                print(f"  Worker route exists ✓")
        else:
            # Create new route
            route_body = json.dumps({
                "pattern": f"{script_name}.{CUSTOM_DOMAIN}/*",
                "script": script_name
            }).encode()
            req = urllib.request.Request(route_url, data=route_body, headers=route_headers, method="POST")
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read())
                if result.get("success"):
                    print(f"  Worker route created ✓")
                else:
                    err_detail = json.dumps(result.get("errors", []))
                    print(f"  Route creation failed: {err_detail}")
                    sys.exit(1)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        if e.code == 409:
            print(f"  Worker route exists ✓")
        else:
            print(f"  Route error {e.code}: {error_body}")
            sys.exit(1)

    print(f"  URL: {custom_url}")
    return custom_url

# ─── Security Scan ───
def security_scan(script_name, js_content):
    warnings = []
    critical = []

    for pattern, label in [
        (r'sk_live_[a-zA-Z0-9]{20,}', 'Stripe live key'),
        (r'sk_test_[a-zA-Z0-9]{20,}', 'Stripe test key'),
        (r'whsec_[a-zA-Z0-9]{20,}', 'Stripe webhook secret'),
        (r'sk_[a-zA-Z0-9]{20,}', 'Stripe key'),
    ]:
        if re.search(pattern, js_content):
            critical.append(f"HARDCODED SECRET: {label} found in worker JS")

    if re.search(r'Domain=\.[a-z]+\.biz', js_content, re.IGNORECASE):
        critical.append("COOKIE SCOPE: Cookie set on apex domain (.yourdomain.com)")
    if re.search(r'Domain=\.{your-account}', js_content, re.IGNORECASE):
        warnings.append("COOKIE SCOPE: Cookie on .{your-account}.workers.dev -- prefer exact subdomain")

    cookie_sets = re.findall(r'Set-Cookie.*?["\']', js_content)
    for cs in cookie_sets:
        if 'Secure' not in cs:
            warnings.append(f"COOKIE SECURITY: Missing Secure flag: {cs[:60]}...")
        if 'HttpOnly' not in cs:
            warnings.append(f"COOKIE SECURITY: Missing HttpOnly flag: {cs[:60]}...")
        if 'SameSite' not in cs:
            warnings.append(f"COOKIE SECURITY: Missing SameSite flag: {cs[:60]}...")

    if 'X-Content-Type-Options' not in js_content:
        warnings.append("HEADERS: Missing X-Content-Type-Options")
    if 'X-Frame-Options' not in js_content:
        warnings.append("HEADERS: Missing X-Frame-Options")

    other_mvps = re.findall(r'https?://[\w-]+\.{your-account}\.workers\.dev', js_content)
    other_mvps = [u for u in other_mvps if script_name not in u]
    if other_mvps:
        warnings.append(f"CROSS-MVP: References other MVP URLs: {other_mvps}")

    if critical:
        print("\n!!! CRITICAL SECURITY ISSUES !!!")
        for c in critical:
            print(f"  [CRITICAL] {c}")
        print()

    if warnings:
        print("Security warnings:")
        for w in warnings:
            print(f"  [WARN] {w}")
        print()

    if not critical and not warnings:
        print("Security scan: CLEAN")

    return len(critical) == 0

# ─── Deploy: Market Testing Worker ───
def deploy_market_testing(script_name, js_path, product_name="My Product"):
    """Deploy a lightweight landing page + email capture worker. No Stripe.
    
    js_path: path to the pre-built worker JS with all copy filled in.
    Build the worker first using build_market_testing_worker(), fill in copy,
    then pass the path here.
    """
    # 1. Read worker JS (user has already filled in all copy)
    with open(js_path, "r") as f:
        worker_js = f.read()

    # 2. Check for unfilled placeholders
    import re
    placeholders = re.findall(r'\{\{[A-Z_]+\}\}', worker_js)
    placeholders = [p for p in placeholders if 'PLACEHOLDER' not in p]
    if placeholders:
        print(f"\nWARNING: {len(placeholders)} unfilled placeholders found:")
        for p in set(placeholders):
            print(f"  {p}")
        print("Fill these in before deploying. Deploying anyway...\n")

    # 3. Get or create signups KV namespace
    print(f"KV namespace: {script_name}-signups")
    signups_kv_id = get_or_create_kv(f"{script_name}-signups")

    # 4. Set up custom domain
    custom_url = setup_custom_domain(script_name)
    worker_url = custom_url if custom_url else f"https://{script_name}.{your-account}.workers.dev"

    # 5. Upload worker (KV + BASE_URL only — no Stripe, no proxy)
    metadata = {
        "main_module": "worker.js",
        "bindings": [
            {"type": "kv_namespace", "name": "SIGNUPS", "namespace_id": signups_kv_id},
            {"type": "plain_text", "name": "BASE_URL", "text": worker_url},
        ]
    }

    print(f"Deploying market-testing worker: {script_name}")
    result = multipart_upload(script_name, metadata, worker_js)

    if result.get("success"):
        enable_subdomain(script_name)

        deploy_info = {
            "worker_url": worker_url,
            "signups_kv_id": signups_kv_id,
            "deploy_mode": "market-testing",
        }

        # Save source + metadata to local repo
        print(f"Saving to local repo...")
        repo_dir = ensure_local_repo(script_name)
        save_deploy_metadata(repo_dir, script_name, worker_js, deploy_info, mode="market-testing")

        # Update business-ideas.json
        update_ideas_db(script_name, deploy_info, "market-testing")

        print(f"\nMarket-testing deployed successfully!")
        print(f"  URL: {worker_url}")
        print(f"  KV (signups): {signups_kv_id}")
        print(f"  Mode: market-testing (email capture, no Stripe)")
        print(f"  Local repo: {repo_dir}")
        return deploy_info
    else:
        errors = result.get("errors", [])
        print(f"Deploy failed: {[e.get('message','unknown') for e in errors]}")
        sys.exit(1)

def build_market_testing_worker(script_name, product_name):
    """Generate a market-testing worker JS in the local repo with templates filled.
    
    Call this FIRST, then fill in the copy placeholders, THEN deploy.
    """
    from datetime import datetime

    skill_dir = os.path.join(os.path.dirname(__file__), "..")
    alt_skill_dir = os.path.expanduser("~/.hermes/skills/business/mvp-storefront")

    def read_template(rel_path):
        for base in [skill_dir, alt_skill_dir]:
            p = os.path.join(base, rel_path)
            if os.path.exists(p):
                with open(p) as f:
                    return f.read()
        print(f"ERROR: Template not found: {rel_path}"); sys.exit(1)

    worker_template = read_template("assets/market-testing-worker.js")
    landing_html = read_template("assets/market-testing-landing.html")
    privacy_html = read_template("assets/privacy-policy.html")
    terms_html = read_template("assets/terms-of-service.html")

    today_str = datetime.now().strftime("%B %d, %Y")
    year_str = str(datetime.now().year)

    landing_html = landing_html.replace("{{PRODUCT_NAME}}", product_name)
    landing_html = landing_html.replace("{{HEADLINE}}", f"Be First to {product_name}")
    landing_html = landing_html.replace("{{SUBHEAD}}", "We're building something. Sign up to get early access when it's ready.")
    landing_html = landing_html.replace("{{CTA_TEXT}}", "Get Early Access")
    landing_html = landing_html.replace("{{FORM_NOTE}}", "No spam. Just a heads up when it's ready.")
    landing_html = landing_html.replace("{{META_DESCRIPTION}}", f"Early access to {product_name} by ALLMIND")
    landing_html = landing_html.replace("{{LOGO_URL}}", "/static/logo.png")
    landing_html = landing_html.replace("{{YEAR}}", year_str)

    privacy_html = privacy_html.replace("{{PRODUCT_NAME}}", product_name).replace("{{DATE}}", today_str)
    terms_html = terms_html.replace("{{PRODUCT_NAME}}", product_name).replace("{{DATE}}", today_str)

    def escape_for_js(html):
        return html.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    worker_js = worker_template
    worker_js = worker_js.replace("LANDING_PAGE_HTML", f"`{escape_for_js(landing_html)}`")
    worker_js = worker_js.replace("PRIVACY_HTML", f"`{escape_for_js(privacy_html)}`")
    worker_js = worker_js.replace("TERMS_HTML", f"`{escape_for_js(terms_html)}`")

    # Write to local repo
    repo_dir = ensure_local_repo(script_name)
    src_path = os.path.join(repo_dir, "src", "worker.js")
    with open(src_path, "w") as f:
        f.write(worker_js)

    print(f"Worker generated at: {src_path}")
    print(f"\nRemaining placeholders to fill:")
    remaining = [p for p in sorted(set(re.findall(r'\{\{[A-Z_]+\}\}', worker_js))) if 'PLACEHOLDER' not in p]
    for p in remaining:
        print(f"  {p}")
    print(f"\nSteps:")
    print(f"  1. Edit {src_path}")
    print(f"  2. Replace all placeholders with product copy")
    print(f"  3. Deploy: python3 deploy_worker.py market-testing {script_name} {src_path} \"{product_name}\"")
    return src_path

# ─── Deploy: Payment Proxy ───
def deploy_proxy():
    """Deploy the central payment proxy. Run ONCE."""
    if not STRIPE_KEY:
        print("ERROR: STRIPE_SECRET_KEY required for proxy deploy"); sys.exit(1)

    proxy_js_path = os.path.join(os.path.dirname(__file__), "..", "assets", "payment-proxy.js")
    if not os.path.exists(proxy_js_path):
        # Fallback: look relative to skill dir
        proxy_js_path = os.path.expanduser("~/.hermes/skills/business/mvp-storefront/assets/payment-proxy.js")
    if not os.path.exists(proxy_js_path):
        print("ERROR: payment-proxy.js not found"); sys.exit(1)

    with open(proxy_js_path) as f:
        proxy_js = f.read()

    # Generate shared HMAC secret (used by all MVPs to auth with proxy)
    hmac_secret = generate_hmac_secret()

    print(f"Deploying payment proxy: {PROXY_NAME}")

    metadata = {
        "main_module": "worker.js",
        "bindings": [
            {"type": "secret_text", "name": "STRIPE_SECRET_KEY", "text": STRIPE_KEY},
            {"type": "secret_text", "name": "PAYMENT_HMAC_SECRET", "text": hmac_secret},
        ]
    }

    result = multipart_upload(PROXY_NAME, metadata, proxy_js)

    if result.get("success"):
        enable_subdomain(PROXY_NAME)
        proxy_url = f"https://{PROXY_NAME}.{your-account}.workers.dev"
        print(f"\nProxy deployed: {proxy_url}")
        print(f"HMAC Secret: {hmac_secret}")
        print(f"\n*** SAVE THIS HMAC SECRET — MVPs need it to authenticate ***")
        print(f"Set in env as PAYMENT_HMAC_SECRET for MVP deploys.\n")
        return {"proxy_url": proxy_url, "hmac_secret": hmac_secret}
    else:
        errors = result.get("errors", [])
        print(f"Proxy deploy failed: {[e.get('message','unknown') for e in errors]}")
        sys.exit(1)

# ─── Deploy: MVP Worker ───
def deploy_mvp(script_name, js_path, product_name="My Product", price_cents=500):
    """Deploy an MVP worker that uses the payment proxy via Service Binding."""
    import urllib.parse

    hmac_secret = os.environ.get("PAYMENT_HMAC_SECRET")
    if not hmac_secret:
        print("ERROR: PAYMENT_HMAC_SECRET not in env")
        print("Set it from the proxy deploy output, or generate one and re-deploy the proxy.")
        sys.exit(1)

    # 1. Ensure proxy exists
    if not worker_exists(PROXY_NAME):
        print(f"Proxy '{PROXY_NAME}' not found. Deploy it first:")
        print(f"  python3 deploy_worker.py proxy")
        sys.exit(1)
    print(f"Proxy '{PROXY_NAME}' found ✓")

    # 2. Get or create KV namespaces (idempotent)
    print(f"\nKV namespace: {script_name}-customers")
    kv_id = get_or_create_kv(f"{script_name}-customers")

    print(f"KV namespace: {script_name}-sales-tracking")
    sales_kv_id = get_or_create_kv(f"{script_name}-sales-tracking")

    # 3. Check for existing Stripe product/price (avoids orphaned products on redeploy)
    metadata_path = os.path.join(os.path.expanduser("~/.hermes/mvps"), script_name, "deploy-metadata.json")
    existing_product_id = None
    existing_price_id = None
    if os.path.exists(metadata_path):
        with open(metadata_path) as f:
            existing_meta = json.load(f)
        existing_product_id = existing_meta.get("stripe_product_id", "")
        existing_price_id = existing_meta.get("stripe_price_id", "")

    if existing_product_id and existing_price_id:
        # Reuse existing product and price
        print(f"\nReusing existing Stripe product: {existing_product_id}")
        print(f"  Price ID: {existing_price_id}")
        price = {"id": existing_price_id}
        product = {"id": existing_product_id}
    else:
        # Create new Stripe product + one-time price
        print(f"\nCreating Stripe product: {product_name}")
        product = stripe_api("POST", "products", {"name": product_name})
        print(f"  Product ID: {product['id']}")

        price = stripe_api("POST", "prices", {
            "product": product["id"],
            "unit_amount": str(price_cents),
            "currency": "usd"
        })
        print(f"  Price ID: {price['id']}")

    # 4. Read worker JS and run security scan
    with open(js_path, "r") as f:
        worker_js = f.read()

    # Extract Meta Pixel ID if present (for tracking/ads reference)
    pixel_match = re.search(r"fbq\('init',\s*'(\d+)'\)", worker_js)
    meta_pixel_id = pixel_match.group(1) if pixel_match else None

    print(f"\nRunning pre-deploy security scan...")
    security_scan(script_name, worker_js)

    # Check that worker doesn't directly use Stripe (should use proxy)
    if 'env.STRIPE_SECRET_KEY' in worker_js:
        print("\n[CRITICAL] Worker references STRIPE_SECRET_KEY directly!")
        print("  MVP workers should use the payment proxy via Service Binding.")
        print("  Use payment-client.js functions instead of direct Stripe calls.")
        print("  Continuing anyway...\n")

    # 5. Set up custom domain first (so BASE_URL uses yourdomain.com)
    custom_url = setup_custom_domain(script_name)
    worker_url = custom_url if custom_url else f"https://{script_name}.{your-account}.workers.dev"

    # 6. Upload worker with Service Binding to proxy
    metadata = {
        "main_module": "worker.js",
        "bindings": [
            # KV namespaces (MVP-specific)
            {"type": "kv_namespace", "name": "CUSTOMERS", "namespace_id": kv_id},
            {"type": "kv_namespace", "name": "SALES_TRACKING", "namespace_id": sales_kv_id},
            # Service Binding to payment proxy (direct RPC, no HTTP)
            {"type": "service", "name": "PAYMENTS", "service": PROXY_NAME},
            # HMAC secret for proxy auth
            {"type": "secret_text", "name": "PAYMENT_HMAC_SECRET", "text": hmac_secret},
            # Stripe price ID (for checkout sessions — not a secret)
            {"type": "plain_text", "name": "STRIPE_PRICE_ID", "text": price["id"]},
            # Worker URL
            {"type": "plain_text", "name": "BASE_URL", "text": worker_url},
            # Resend API key for transactional emails
            {"type": "secret_text", "name": "RESEND_KEY", "text": os.environ.get("RESEND_KEY", "")},
        ]
    }

    print(f"\nDeploying worker: {script_name}")
    result = multipart_upload(script_name, metadata, worker_js)

    if result.get("success"):
        enable_subdomain(script_name)
        
        # Register Stripe webhook automatically
        print(f"\nRegistering Stripe webhook...")
        webhook_id, webhook_secret = register_stripe_webhook(worker_url)
        
        deploy_info = {
            "worker_url": worker_url,
            "kv_id": kv_id,
            "sales_kv_id": sales_kv_id,
            "stripe_product_id": product["id"],
            "stripe_price_id": price["id"],
            "stripe_webhook_id": webhook_id,
            "stripe_webhook_secret": webhook_secret,
            "uses_proxy": True,
            "meta_pixel_id": meta_pixel_id,
        }

        # Save source + metadata to local repo
        print(f"\nSaving to local repo...")
        repo_dir = ensure_local_repo(script_name)
        save_deploy_metadata(repo_dir, script_name, worker_js, deploy_info, mode="full")

        # Update business-ideas.json
        update_ideas_db(script_name, deploy_info, "full")

        print(f"\nDeployed successfully!")
        print(f"  URL: {worker_url}")
        print(f"  KV (customers):  {kv_id}")
        print(f"  KV (sales):      {sales_kv_id}")
        print(f"  Stripe Product: {product['id']}")
        print(f"  Stripe Price:   {price['id']}")
        print(f"  Webhook:        {webhook_id}")
        print(f"  Payments via:   Service Binding → {PROXY_NAME}")
        print(f"  Local repo:     {repo_dir}")
        print(f"  NO Stripe key in this worker ✓")
        return deploy_info
    else:
        errors = result.get("errors", [])
        print(f"Deploy failed: {[e.get('message','unknown') for e in errors]}")
        sys.exit(1)

# ─── Local Repo Management ───
MVPS_DIR = os.path.expanduser("~/.hermes/mvps")

def ensure_local_repo(script_name):
    """Create local MVP repo structure if it doesn't exist."""
    repo_dir = os.path.join(MVPS_DIR, script_name)
    src_dir = os.path.join(repo_dir, "src")
    os.makedirs(src_dir, exist_ok=True)
    return repo_dir

def save_deploy_metadata(repo_dir, script_name, worker_js, deploy_info, mode="full"):
    """Write deploy-metadata.json and copy source to local repo."""
    # Copy worker source to local repo
    src_path = os.path.join(repo_dir, "src", "worker.js")
    with open(src_path, "w") as f:
        f.write(worker_js)
    print(f"  Source saved: {src_path}")

    # Write deploy metadata
    import hashlib
    source_hash = hashlib.sha256(worker_js.encode()).hexdigest()
    from datetime import datetime
    metadata = {
        "script_name": script_name,
        "deploy_mode": mode,
        "worker_url": deploy_info.get("worker_url", ""),
        "signups_kv_id": deploy_info.get("signups_kv_id", ""),
        "kv_customers_id": deploy_info.get("kv_id", ""),
        "kv_sales_id": deploy_info.get("sales_kv_id", ""),
        "stripe_product_id": deploy_info.get("stripe_product_id", ""),
        "stripe_price_id": deploy_info.get("stripe_price_id", ""),
        "stripe_webhook_id": deploy_info.get("stripe_webhook_id", ""),
        "meta_pixel_id": deploy_info.get("meta_pixel_id", ""),
        "deployed_at": datetime.now().strftime("%Y-%m-%d"),
        "last_deploy_source_hash": source_hash,
    }
    meta_path = os.path.join(repo_dir, "deploy-metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"  Metadata saved: {meta_path}")

    # Create README if missing
    readme_path = os.path.join(repo_dir, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w") as f:
            f.write(f"# {script_name.replace('-', ' ').title()}\n\n")
            f.write(f"Deployed: {deploy_info.get('worker_url', 'N/A')}\n\n")
            f.write(f"## Redeploy\n```bash\n")
            f.write(f"python3 ~/.hermes/skills/business/mvp-storefront/scripts/deploy_worker.py mvp {script_name} ~/.hermes/mvps/{script_name}/src/worker.js\n")
            f.write(f"```\n")
        print(f"  README created: {readme_path}")

# ─── Main ───
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 deploy_worker.py proxy                                        # Deploy payment proxy (once)")
        print("  python3 deploy_worker.py build <name> [product-name]                  # Generate worker JS (fill copy, then deploy)")
        print("  python3 deploy_worker.py market-testing <name> <js-path> [name]       # Deploy pre-built worker")
        print("  python3 deploy_worker.py mvp <script-name> <js> [name] [cents]        # Full storefront (Stripe)")
        print("  python3 deploy_worker.py download <script-name>                       # Download source")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "proxy":
        deploy_proxy()
    elif mode == "build":
        if len(sys.argv) < 3:
            print("Usage: python3 deploy_worker.py build <script-name> [product-name]")
            sys.exit(1)
        name = sys.argv[2]
        pname = sys.argv[3] if len(sys.argv) > 3 else name.replace("-", " ").title()
        build_market_testing_worker(name, pname)
    elif mode == "market-testing":
        if len(sys.argv) < 4:
            print("Usage: python3 deploy_worker.py market-testing <script-name> <worker.js> [product-name]")
            sys.exit(1)
        name = sys.argv[2]
        js = sys.argv[3]
        pname = sys.argv[4] if len(sys.argv) > 4 else name.replace("-", " ").title()
        deploy_market_testing(name, js, pname)
    elif mode == "mvp":
        if len(sys.argv) < 4:
            print("Usage: python3 deploy_worker.py mvp <script-name> <worker.js> [product-name] [price-cents]")
            sys.exit(1)
        name = sys.argv[2]
        js = sys.argv[3]
        pname = sys.argv[4] if len(sys.argv) > 4 else name.replace("-", " ").title()
        pcents = int(sys.argv[5]) if len(sys.argv) > 5 else 500
        deploy_mvp(name, js, pname, pcents)
    elif mode == "download":
        # Download deployed worker source to local repo
        if len(sys.argv) < 3:
            print("Usage: python3 deploy_worker.py download <script-name>")
            sys.exit(1)
        script_name = sys.argv[2]
        url = f"{BASE_API}/accounts/{ACCOUNT_ID}/workers/scripts/{script_name}"
        headers = {"Authorization": f"Bearer {CF_TOKEN}"}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            print(f"Failed to download: {e.code}")
            sys.exit(1)

        # Parse multipart to extract worker.js
        text = raw.decode("utf-8", errors="replace")
        js_content = None
        parts = text.split('name="worker.js"')
        if len(parts) > 1:
            js_part = parts[1]
            for sep in ["\r\n\r\n", "\n\n"]:
                blank_idx = js_part.find(sep)
                if blank_idx > 0:
                    js_content = js_part[blank_idx + len(sep):]
                    for marker in ["\r\n------", "\n------"]:
                        end = js_content.find(marker)
                        if end > 0:
                            js_content = js_content[:end]
                    break

        if not js_content:
            print("Could not parse worker.js from CF response")
            sys.exit(1)

        repo_dir = ensure_local_repo(script_name)
        src_path = os.path.join(repo_dir, "src", "worker.js")
        with open(src_path, "w") as f:
            f.write(js_content)
        print(f"Downloaded {len(js_content)} chars → {src_path}")
    else:
        print(f"Unknown mode: {mode}. Use 'proxy', 'mvp', or 'download'.")
        sys.exit(1)
