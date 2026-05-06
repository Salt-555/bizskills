# Google Ads API Credentials Setup

This guide walks through obtaining all credentials required for the Google Ads API integration.

---

## Credential Storage

All credentials live in **`~/.hermes/.env`** as environment variables. Hermes reads them via `os.getenv()` in `terminal` tool calls. **Never** create a separate YAML or credential file.

Required variables:

```bash
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token
GOOGLE_ADS_CLIENT_ID=your_oauth_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_oauth_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_LOGIN_CUSTOMER_ID=1234567890
```

---

## Step 1: Create a Manager Account (MCC)

A Google Ads Manager Account (MCC) is **required** to obtain a developer token.

1. Go to [ads.google.com](https://ads.google.com)
2. Sign in with the Google account you want to use for the Almi Empire ad management
3. If prompted to create a new account, look for the option **"Create a Manager account"** — do not create a standard advertiser account
4. Name it something like **Almi Empire Manager**
5. Complete the setup; you can skip billing for the manager account itself

> If you already have a standard Google Ads account, you cannot convert it to an MCC. You will need to create a new Google account or use the existing MCC option in the account switcher.

---

## Step 2: Get Your Developer Token

The developer token identifies your application to the Google Ads API.

1. Inside your **Manager Account**, click **Tools** (wrench icon) in the top navigation
2. Under the **Setup** section, select **API Center**
3. You will see your developer token (partially masked) — click to reveal and copy it
4. Note your **access level**:
   - **Test Account access** — granted immediately, works only against test accounts, sufficient for development
   - **Standard access** — required for live production campaigns; click **Apply for Standard access** and submit the form

> **Review timeline:** Standard access approval typically takes **24–48 hours** but can occasionally take up to a week. Google may email follow-up questions. Test access works immediately and is fully functional for building and testing the integration before approval.

---

## Step 3: Google Cloud Console — OAuth Credentials

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top and select **New Project**
3. Name it **Almi Empire** — click **Create**
4. With the project selected, go to **APIs & Services > Library**
5. Search for **Google Ads API** and click **Enable**
6. Go to **APIs & Services > Credentials**
7. Click **Create Credentials > OAuth 2.0 Client ID**
8. If prompted, configure the **OAuth consent screen** first:
   - User type: **External** (or Internal if using Google Workspace)
   - App name: `Almi Ads Manager`
   - Add your email as a test user
9. Back on Create OAuth Client ID:
   - Application type: **Desktop app**
   - Name: `Almi Ads Manager Desktop`
   - Click **Create**
10. A dialog shows your credentials — **copy and save both**:
    - `client_id` (ends in `.apps.googleusercontent.com`)
    - `client_secret`

---

## Step 4: Generate Your Refresh Token

Tell Almi: "set up Google Ads credentials" and provide your developer_token, client_id, client_secret, and login_customer_id (MCC account ID, digits only).

Almi will:
- Build the OAuth2 authorization URL (scope: adwords, access_type: offline)
- Give you the URL to open in a browser and authorize
- Exchange the resulting code for a refresh_token via the Google OAuth2 token endpoint
- Write the completed credentials to `~/.hermes/.env` as `GOOGLE_ADS_REFRESH_TOKEN`

---

## Step 5: Write Credentials to ~/.hermes/.env

Open `~/.hermes/.env` and add the following lines (create the file if it does not exist):

```bash
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token_here
GOOGLE_ADS_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_client_secret_here
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token_here
GOOGLE_ADS_LOGIN_CUSTOMER_ID=your_mcc_account_id_digits_only
```

Set restrictive permissions on the file:

```bash
chmod 600 ~/.hermes/.env
```

---

## Step 6: Verify the Connection

Tell Almi: "verify Google Ads credentials". Almi will exchange the refresh token for an access token and hit the `customers:listAccessibleCustomers` endpoint. A successful response lists your accessible accounts. If it returns `AUTHENTICATION_ERROR` or `DEVELOPER_TOKEN_NOT_APPROVED`, re-check your token access level (Step 2).

---

## Conversion Tracking Setup

After credentials are working, set up conversion tracking so campaign performance data flows back accurately.

1. In Google Ads (Manager or client account), go to **Tools > Measurement > Conversions**
2. Click **New conversion action**
3. Select **Website**
4. Enter your website URL and click **Scan** (or configure manually)
5. Set the following:
   - **Conversion name:** `Submit lead form`
   - **Category:** Lead
   - **Value:** Use the same value for each conversion (or set a fixed value per lead)
   - **Count:** One (one conversion per form submission)
6. Click **Save and continue**
7. Choose **Use Google Tag Manager** or **Install the tag yourself**
8. The conversion fires on the **`/thank-you`** page URL — configure your tag or event rule to trigger on that page load
9. Copy the **Conversion ID** and **Conversion Label** — these are needed if configuring the tag manually or via GTM

> The `/thank-you` URL-based trigger is the simplest reliable method. Ensure your thank-you page is only reachable after a genuine form submission (not directly navigable) to avoid inflated conversion counts.

---

## Notes

- Never commit `.env` to version control — it is already in `.gitignore` by Hermes convention
- The `GOOGLE_ADS_LOGIN_CUSTOMER_ID` must be your **MCC account ID** (no dashes), not a client account ID
- If you manage multiple client accounts under the MCC, the API will use the MCC account to authenticate and you can query any child account by passing its `customer_id` in API calls
- Developer token access level only restricts which _customer accounts_ you can query — Test access is limited to test accounts, Standard access works on all real accounts
- Refresh tokens do not expire unless revoked or unused for 6 months; rotating them is not required unless there is a security concern
