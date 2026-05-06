# Meta Ads API Credentials Setup

This guide walks through obtaining all credentials required for the Meta (Facebook/Instagram) Ads API integration.

---

## Credential Storage

All credentials live in **`~/.hermes/.env`** as environment variables. Hermes reads them via `os.getenv()` in `terminal` tool calls. **Never** create a separate JSON or credential file.

Required variables:

```bash
META_ADS_ACCESS_TOKEN=your_long_lived_token
META_ADS_ACCOUNT_ID=act_1234567890
META_ADS_PAGE_ID=123456789
META_ADS_PIXEL_ID=123456789012345
```

---

## Step 1: Create a Meta Developer App

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Sign in with the Facebook account linked to the Almi business
3. Click **My Apps > Create App**
4. Select App type: **Business**
5. App name: **Almi Ads Manager**
6. Enter a contact email and select your Business Portfolio (Meta Business Account) if prompted
7. Click **Create App**
8. Once created, go to **App Settings > Basic**
9. Note both values:
   - **App ID** (numeric)
   - **App Secret** (click Show to reveal)

---

## Step 2: Get a System User Access Token (Preferred)

System User tokens are **recommended** — they never expire and are not tied to any individual person's account.

1. Go to [business.facebook.com](https://business.facebook.com)
2. Navigate to **Business Settings** (gear icon, bottom-left)
3. In the left sidebar, go to **Users > System Users**
4. Click **Add** and configure:
   - Name: `Almi Ads API`
   - Role: **Admin**
5. Click **Create System User**
6. Select the newly created system user, then click **Generate New Token**
7. Select your app: **Almi Ads Manager**
8. Enable the following permissions:
   - `ads_management`
   - `ads_read`
   - `pages_read_engagement`
   - `pages_show_list`
9. Click **Generate Token** and **copy it immediately** — it will not be shown again

> System User tokens do not expire unless manually revoked. This is strongly preferred over personal user tokens or short-lived tokens for automated integrations.

---

## Step 3: Get Your Ad Account ID

1. Go to [business.facebook.com](https://business.facebook.com)
2. Navigate to **Business Settings > Accounts > Ad Accounts**
3. Click on your ad account
4. The **Account ID** is displayed — it is a numeric string (e.g., `1234567890`)
5. Prepend `act_` to it for use in API calls: `act_1234567890`

> If you do not yet have an ad account, create one via **Business Settings > Accounts > Ad Accounts > Add > Create a New Ad Account**.

---

## Step 4: Get Your Page ID

1. Go to your **Facebook Business Page**
2. Click **About** in the left sidebar (or navigate to the page's About section)
3. Scroll down to find **Page ID** — it is a numeric string
4. Copy this value

Alternatively, via Business Settings:
1. Go to **Business Settings > Accounts > Pages**
2. Click your page — the Page ID is shown in the details panel on the right

---

## Step 5: Create a Meta Pixel

The Meta Pixel enables conversion tracking and retargeting audiences.

1. Go to [business.facebook.com](https://business.facebook.com) > **Events Manager**
2. Click **Connect Data Sources** (the **+** icon)
3. Select **Web** > Click **Connect**
4. Choose **Facebook Pixel** > Click **Connect**
5. Name the pixel: **Almi Pixel** (or similar)
6. Enter your website URL and click **Continue**
7. Copy the **Pixel ID** that is generated (numeric string)

### Add the Pixel to Your Cloudflare Pages Deployments

Add the pixel base code to the `<head>` of every page across all Cloudflare Pages deployments. Replace `YOUR_PIXEL_ID` with your actual Pixel ID:

```html
<!-- Meta Pixel Code -->
<script>
!function(f,b,e,v,n,t,s)
{if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};
if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];
s.parentNode.insertBefore(t,s)}(window, document,'script',
'https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'YOUR_PIXEL_ID');
fbq('track', 'PageView');
</script>
<noscript>
  <img height="1" width="1" style="display:none"
    src="https://www.facebook.com/tr?id=YOUR_PIXEL_ID&ev=PageView&noscript=1"/>
</noscript>
<!-- End Meta Pixel Code -->
```

> Add this code to the `<head>` section, ideally as early as possible. For Cloudflare Pages, add it to your base layout template so it is included on every page automatically.

---

## Step 6: Write Credentials to ~/.hermes/.env

Open `~/.hermes/.env` and add the following lines (create the file if it does not exist):

```bash
META_ADS_ACCESS_TOKEN=your_long_lived_token_here
META_ADS_ACCOUNT_ID=act_your_ad_account_id_here
META_ADS_PAGE_ID=your_page_id_here
META_ADS_PIXEL_ID=your_pixel_id_here
```

Set restrictive permissions on the file:

```bash
chmod 600 ~/.hermes/.env
```

---

## Token Refresh (Short-Lived Tokens Only)

If you used a **short-lived user token** instead of a System User token, it expires in ~1 hour. Exchange it for a long-lived token (valid ~60 days) with this curl command:

```bash
curl -G \
  "https://graph.facebook.com/oauth/access_token" \
  --data-urlencode "grant_type=fb_exchange_token" \
  --data-urlencode "client_id=YOUR_APP_ID" \
  --data-urlencode "client_secret=YOUR_APP_SECRET" \
  --data-urlencode "fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

The response JSON will contain a new `access_token` — update `META_ADS_ACCESS_TOKEN` in `~/.hermes/.env` with it.

> Long-lived tokens still expire after ~60 days. **Use a System User token (Step 2) to avoid this entirely.**

---

## Verify the Access Token

Run this curl command to confirm the token is valid and see which user or system user it belongs to:

```bash
curl -G "https://graph.facebook.com/me" \
  --data-urlencode "access_token=$META_ADS_ACCESS_TOKEN"
```

A successful response will return JSON with an `id` and `name`. An invalid or expired token will return an error object with `code: 190`.

To also verify ad account access:

```bash
curl -G "https://graph.facebook.com/v19.0/$META_ADS_ACCOUNT_ID" \
  --data-urlencode "fields=name,account_status,currency" \
  --data-urlencode "access_token=$META_ADS_ACCESS_TOKEN"
```

---

## Notes

- Never commit `.env` to version control — it is already in `.gitignore` by Hermes convention
- The `META_ADS_ACCOUNT_ID` must always include the `act_` prefix when used in API calls
- The `ads_management` permission allows creating, editing, and deleting campaigns — treat the token with the same care as a password
- If you ever revoke or rotate the System User token, update `~/.hermes/.env` and re-run `chmod 600`
- The Meta API version in URLs (e.g., `v19.0`) should be updated periodically as older versions are deprecated — check [developers.facebook.com/docs/graph-api/changelog](https://developers.facebook.com/docs/graph-api/changelog) for the current stable version
