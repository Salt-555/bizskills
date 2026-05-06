# API Call Templates for Ad Results Review

## Meta Ads API

### Check campaign status
```bash
curl -s "https://graph.facebook.com/v19.0/{campaign_id}?fields=id,status,effective_status" \
  -d "access_token=$META_ADS_ACCESS_TOKEN"
```

### Get insights for a specific date
```bash
TIME_RANGE=$(python3 -c "import urllib.parse, os; d=os.getenv('YESTERDATE'); print(urllib.parse.quote('{\"since\":\"'+d+'\",\"until\":\"'+d+'\"}'))")
curl -s "https://graph.facebook.com/v19.0/{campaign_id}/insights?fields=impressions,clicks,ctr,spend,actions&time_range=$TIME_RANGE&access_token=$META_ADS_ACCESS_TOKEN"
```

## Stripe API

### Get charges for a specific date
```bash
export STRIPE_KEY="$STRIPE_SECRET_KEY"
export YEAR=2026
export MONTH=5
export DAY=3
UNIX_START=$(python3 -c "import datetime, os; y,m,d=int(os.environ['YEAR']),int(os.environ['MONTH']),int(os.environ['DAY']); print(int(datetime.datetime(y,m,d,0,0,0).timestamp()))")
UNIX_END=$(python3 -c "import datetime, os; y,m,d=int(os.environ['YEAR']),int(os.environ['MONTH']),int(os.environ['DAY']); print(int(datetime.datetime(y,m,d+1,0,0,0).timestamp()))")
curl -s "https://api.stripe.com/v1/charges?limit=100&created%5Bgte%5D=$UNIX_START&created%5Blt%5D=$UNIX_END" -u "$STRIPE_SECRET_KEY:"
```

## Cloudflare Analytics API (if tracker is installed)

### Get daily analytics summary
```bash
curl -s "https://yourdomain.com/track/analytics?days=1"
```

### Get raw events for a date
```bash
curl -s "https://yourdomain.com/track/events?date=YYYY-MM-DD"
```