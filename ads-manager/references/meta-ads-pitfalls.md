# Meta Ads API Pitfalls (Verified April 2026)

## Campaign & Ad Set Creation

- **`advantage_audience` REQUIRED** — Add `"targeting_automation": {"advantage_audience": 0}` inside the targeting spec. 0 = custom targeting, 1 = Advantage+ (auto). Without this, all ad set creation fails with error 1870227.
- **`is_adset_budget_sharing_enabled` required** — When creating campaigns without `campaign_budget_optimization`, you must pass `is_adset_budget_sharing_enabled=false`. Without it, campaign creation fails with error 4834011.
- **Campaign starts PAUSED** — Create campaigns/adsets/ads as PAUSED, then activate separately with a PATCH. This gives you a review window before spend begins.

## Budget Placement

- **Budget placement matters** — For CBO (Campaign Budget Optimization), budget goes on campaign. For ad-set-level budget, set `daily_budget` or `lifetime_budget` (in cents) on the ad set, not the campaign. Cannot mix.
- **Can't switch daily↔lifetime after creation** — Once an ad set is created with `daily_budget`, you CANNOT switch to `lifetime_budget` via update. Must create a new ad set and migrate ads. Pause old ad set.
- **Lifetime budget: cents + unix timestamp** — `lifetime_budget` is in cents (e.g., 3000 for $30). `end_time` is a unix timestamp (seconds since epoch), NOT ISO format. Ad set `status` must be `ACTIVE` (not PAUSED) to run immediately.

## Creative & Ad Creation

- **Creative spec: use `title` not `name`** — In `object_story_spec.link_data`, the field is `title` (max 40 chars), not `name`. Also `call_to_action` goes at top level of `link_data`, not nested.
- **Format: `STORY` for link+traffic** — When using `OUTCOME_TRAFFIC` with link ads, creative `format` must be `STORY`. `SINGLE_IMAGE` and `CAROUSEL` may fail with confusing errors.
- **Create creative first, then reference by ID** — Create the ad creative via `/act_{id}/adcreatives`, get back `creative_id`, then pass `creative: {creative_id: "..."}` in the ad creation call. Don't pass the creative object inline.
- **`image_hash` via `/act_{id}/adimages`** — Upload images via the adimages endpoint to get the hash. Then use `image_hash` in `asset_feed_spec.images` or `object_story_spec.link_data.picture`. The hash is NOT the file hash — it's Meta's internal identifier.
- **Retrieve creative image via API** — `GET /{creative_id}?fields=image_url` returns the CDN URL of the uploaded image. Useful for recovering ad images when local copy is lost.

## Targeting & Tracking

- **Interest IDs may be deprecated** — Always validate interest IDs via `/search?type=adinterest&q={term}` before using them. Many witchy/occult interests return empty or have been merged. Use the returned IDs, not guessed ones.
- **`event_source_id` for tracking** — Add `"tracking_specs": [{"event_source_id": PIXEL_ID}]` to the ad for conversion tracking. Without this, pixel fires but aren't attributed to the ad.
- **Campaign objective controls what gets counted** — If the campaign objective is `OUTCOME_TRAFFIC` (optimizing for `LINK_CLICKS`), Meta will NOT report or optimize for `Purchase` events even if the Pixel fires them correctly. The dashboard may show zero purchases despite a working Pixel. Two fixes: (1) Create a **Custom Conversion** via `/act_{id}/customconversions` that triggers on the `Purchase` event (or URL contains `/success`), then attach it to the ad set's `promoted_object`; (2) Change the campaign objective to `OUTCOME_SALES` and set `optimization_goal=PURCHASES`. Without one of these, you are paying for traffic, not buyers.
- **Custom Conversion URL rules** — When creating a custom conversion via API, `rule` is a JSON object (e.g. `{"url":{"i_contains":"/success"}}`). The `i_contains` operator is case-insensitive. The conversion must be explicitly attached to the ad set or campaign to be used for reporting.
- **Pixel `Purchase` fires != Meta counts it** — Always verify the campaign objective matches the business goal. A traffic campaign with a purchase Pixel is a common silent failure mode: the landing page works, the Pixel loads, the event fires, but Meta never attributes it because the campaign wasn't told to care about purchases.

## Scheduling & Auto-Stop

- **`end_time` is clamped to the nearest day boundary in the account timezone** — When you POST `end_time` to an ad set (e.g. `2026-04-28T00:00:00`), Meta stores it as the *previous* day at 18:00 in the account timezone (e.g. `2026-04-27T18:00:00-0600`). This means setting `2026-04-30` may result in `2026-04-29T18:00:00-0600`. Always **read back** the ad set after setting `end_time` and update your local database with the actual stored value. Don't assume the value you sent is what Meta kept.
- **Always verify `stop_time` on the campaign too** — When `end_time` is set on the ad set, the parent campaign gets a `stop_time` that may differ from both your input and the ad set's `end_time`. Read both objects and reconcile.

## Account Hygiene

- **Ghost / orphan campaigns accumulate** — Duplicate launches, failed experiments, or campaigns created outside the ads-manager pipeline can leave active or paused campaigns in your Meta account that aren't tracked in local `campaigns.json`. Periodically list all campaigns via `GET /act_{id}/campaigns?fields=id,name,effective_status` and compare against your local database. Untracked campaigns waste budget (if active) or clutter reporting (if paused). Archive or document them.


## API Request Format

- **Image upload: use `image_file` not `image[file]`** — The `image_file` form field name works reliably for ad image uploads. `image[file]` may fail with OAuth code 1.
- **JSON body must include access_token** — When using `Content-Type: application/json`, the access_token must be inside the JSON body, not as a separate form parameter. Mixing `-d` flags with `-H "Content-Type: application/json"` causes malformed requests.
